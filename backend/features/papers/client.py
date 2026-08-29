"""
arXiv 공식 API 클라이언트

문서: https://info.arxiv.org/help/api/user-manual.html
엔드포인트: http://export.arxiv.org/api/query

외부 XML이므로 defusedxml이 있으면 우선 사용합니다.
"""

import re
from typing import List, Optional
from xml.etree.ElementTree import Element

import httpx

from core.config import settings
from features.papers.schemas import PaperItem

try:
    from defusedxml import ElementTree as SafeET  # type: ignore

    _XML_PARSER = SafeET
except ImportError:  # pragma: no cover
    import xml.etree.ElementTree as _StdET

    _XML_PARSER = _StdET

_ATOM = "{http://www.w3.org/2005/Atom}"
_ARXIV = "{http://arxiv.org/schemas/atom}"

_ARXIV_API = "http://export.arxiv.org/api/query"

_WHITESPACE_RE = re.compile(r"\s+")
_ID_RE = re.compile(r"arxiv\.org/abs/([^\s/]+)", re.IGNORECASE)
_VERSION_RE = re.compile(r"v\d+$", re.IGNORECASE)
_YEAR_RE = re.compile(r"^(\d{4})")
_HYPHEN_SPLIT_RE = re.compile(r"[\s\-_/]+")
_ARXIV_OPERATORS = {"and", "or", "andnot", "not"}
# 구문 검색 AND 절에서 빠져도 의미가 거의 없는 짧은 영어 단어
_ARXIV_SKIP_AND = _ARXIV_OPERATORS | {
    "a", "an", "the", "to", "of", "in", "on", "for", "and", "or",
}


class ArxivFetchError(Exception):
    """arXiv API 호출 또는 파싱 실패"""


def sanitize_search_term(query: str) -> str:
    """
    검색어에서 arXiv 쿼리를 깨는 문자만 걷어냅니다.

    하이픈과 공백, 한글/영문/숫자는 그대로 둡니다.
    큰따옴표와 콜론은 필드 연산자 주입을 막기 위해 공백으로 바꿉니다.
    """
    text = _WHITESPACE_RE.sub(" ", (query or "")).strip()
    text = text.replace('"', " ").replace(":", " ")
    return _WHITESPACE_RE.sub(" ", text).strip()


def build_arxiv_search_query(query: str) -> str:
    """
    하이픈/공백이 있는 검색어를 arXiv 문법에 맞게 조합합니다.

    arXiv(Lucene)는 따옴표 없는 `text-to-3d`의 `-`를 ANDNOT으로 읽습니다.
    그래서 원문을 구문 검색으로 넣고, 하이픈을 공백으로 바꾼 구문과
    토큰 AND를 OR로 묶습니다.

    Args:
        query: 정규화된 검색어 (예: Text-to-3D, Gaussian Splatting)

    Returns:
        search_query 파라미터 값
    """
    cleaned = sanitize_search_term(query)
    if not cleaned:
        return 'all:""'

    clauses = [f'all:"{cleaned}"']

    if "-" in cleaned:
        spaced = _WHITESPACE_RE.sub(" ", cleaned.replace("-", " ")).strip()
        if spaced and spaced != cleaned:
            clauses.append(f'all:"{spaced}"')

    tokens = [
        token
        for token in _HYPHEN_SPLIT_RE.split(cleaned)
        if token and token.lower() not in _ARXIV_SKIP_AND
    ]
    unique_tokens = list(dict.fromkeys(tokens))
    if len(unique_tokens) >= 2:
        and_parts = " AND ".join(f"all:{token}" for token in unique_tokens)
        clauses.append(f"({and_parts})")
    elif len(unique_tokens) == 1 and unique_tokens[0] != cleaned:
        clauses.append(f"all:{unique_tokens[0]}")

    return " OR ".join(clauses)


def canonical_arxiv_id(arxiv_id: str) -> str:
    """버전 접미사(v1)를 떼고 인용용 arXiv ID만 남깁니다."""
    return _VERSION_RE.sub("", (arxiv_id or "").strip())


def paper_year(published_at: Optional[str]) -> Optional[int]:
    """ISO 공개일에서 연도를 꺼냅니다."""
    if not published_at:
        return None
    match = _YEAR_RE.match(published_at.strip())
    return int(match.group(1)) if match else None


def format_author_names(authors: List[str]) -> str:
    """인용용 저자 표기. 4명 이상이면 첫 저자 et al. 입니다."""
    names = [name.strip() for name in authors if name and name.strip()]
    if not names:
        return "Unknown"
    if len(names) == 1:
        return names[0]
    if len(names) <= 3:
        return ", ".join(names)
    return f"{names[0]} et al."


def format_bibliography_line(index: int, paper: PaperItem) -> str:
    """
    학술 참고문헌 한 줄을 만듭니다.

    예: 1. Ben Poole, Ajay Jain. DreamFusion. arXiv preprint, 2022; arXiv:2209.14988.
    """
    authors = format_author_names(paper.authors)
    title = (paper.title or "(제목 없음)").rstrip(".")
    year = paper.year or paper_year(paper.published_at) or "n.d."
    venue = (paper.journal or "").strip() or "arXiv preprint"
    aid = canonical_arxiv_id(paper.arxiv_id)
    return f"{index}. {authors}. {title}. {venue}, {year}; arXiv:{aid}."


def attach_citations(papers: List[PaperItem]) -> List[PaperItem]:
    """검색 결과 순서대로 번호가 붙은 citation 필드를 채웁니다."""
    cited: List[PaperItem] = []
    for index, paper in enumerate(papers, start=1):
        year = paper.year or paper_year(paper.published_at)
        line = format_bibliography_line(index, paper)
        cited.append(paper.model_copy(update={"year": year, "citation": line}))
    return cited


def _text(node: Element, path: str) -> str:
    """Atom 자식 노드의 텍스트를 공백 정규화해 반환합니다."""
    child = node.find(f"{_ATOM}{path}")
    if child is None or child.text is None:
        return ""
    return _WHITESPACE_RE.sub(" ", child.text).strip()


def _authors(entry: Element) -> List[str]:
    names: List[str] = []
    for author in entry.findall(f"{_ATOM}author"):
        name = author.findtext(f"{_ATOM}name")
        if name:
            names.append(_WHITESPACE_RE.sub(" ", name).strip())
    return names


def _pdf_and_abs(entry: Element, arxiv_id: str) -> tuple:
    """
    PDF / 초록 페이지 URL을 추출합니다.

    link@title=pdf 가 있으면 그것을 쓰고, 없으면 id로부터 조합합니다.
    """
    pdf_url = ""
    abs_url = ""

    for link in entry.findall(f"{_ATOM}link"):
        href = (link.get("href") or "").strip()
        rel = (link.get("rel") or "").strip()
        title = (link.get("title") or "").strip().lower()
        link_type = (link.get("type") or "").strip().lower()

        if title == "pdf" or link_type == "application/pdf":
            pdf_url = href
        elif rel == "alternate" and "abs" in href:
            abs_url = href

    if not abs_url:
        abs_url = f"https://arxiv.org/abs/{arxiv_id}"
    if not pdf_url:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    return pdf_url, abs_url


def _arxiv_field(entry: Element, tag: str) -> str:
    """arXiv 확장 네임스페이스 자식 텍스트를 반환합니다."""
    child = entry.find(f"{_ARXIV}{tag}")
    if child is None or child.text is None:
        return ""
    return _WHITESPACE_RE.sub(" ", child.text).strip()


def _arxiv_id(entry: Element) -> str:
    raw_id = _text(entry, "id")
    match = _ID_RE.search(raw_id)
    if match:
        return match.group(1).replace("arxiv:", "")
    return raw_id.rsplit("/", 1)[-1]


def parse_arxiv_feed(xml_text: str) -> List[PaperItem]:
    """
    arXiv Atom 피드를 PaperItem 목록으로 변환합니다.

    Args:
        xml_text: API 응답 본문

    Returns:
        논문 목록

    Raises:
        ArxivFetchError: XML이 깨져 있으면
    """
    try:
        root = _XML_PARSER.fromstring(xml_text)
    except Exception as exc:
        raise ArxivFetchError(f"arXiv 응답을 파싱할 수 없습니다: {exc}") from exc

    papers: List[PaperItem] = []

    for entry in root.findall(f"{_ATOM}entry"):
        arxiv_id = _arxiv_id(entry)
        title = _text(entry, "title")
        abstract = _text(entry, "summary")

        if not title or not arxiv_id:
            continue

        pdf_url, abs_url = _pdf_and_abs(entry, arxiv_id)
        published = _text(entry, "published")
        journal = _arxiv_field(entry, "journal_ref")
        year = paper_year(published)
        categories = [
            (cat.get("term") or "").strip()
            for cat in entry.findall(f"{_ARXIV}primary_category")
            + entry.findall(f"{_ATOM}category")
            if (cat.get("term") or "").strip()
        ]
        unique_cats = list(dict.fromkeys(categories))

        paper = PaperItem(
            arxiv_id=arxiv_id,
            title=title,
            abstract=abstract,
            authors=_authors(entry),
            pdf_url=pdf_url,
            abs_url=abs_url,
            published_at=published or None,
            categories=unique_cats,
            journal=journal or None,
            year=year,
        )
        papers.append(paper)

    return attach_citations(papers)


async def search_arxiv(query: str, limit: int = 8) -> List[PaperItem]:
    """
    arXiv API에 검색어를 보내고 논문 목록을 반환합니다.

    Args:
        query: 정규화된 검색어 (예: Text-to-3D)
        limit: 최대 결과 수

    Returns:
        PaperItem 목록

    Raises:
        ArxivFetchError: 네트워크/HTTP/파싱 실패
    """
    params = {
        "search_query": build_arxiv_search_query(query),
        "start": 0,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    headers = {
        "User-Agent": settings.TRENDS_USER_AGENT,
        "Accept": "application/atom+xml, application/xml, text/xml",
    }
    timeout = settings.TRENDS_TIMEOUT_SECONDS

    try:
        # params를 넘기면 httpx가 공백·따옴표·하이픈을 한 번만 URL 인코딩합니다.
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(_ARXIV_API, params=params, headers=headers)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise ArxivFetchError("arXiv API 응답이 시간 초과되었습니다.") from exc
    except httpx.HTTPError as exc:
        raise ArxivFetchError(f"arXiv API 호출 실패: {exc}") from exc

    return parse_arxiv_feed(response.text)
