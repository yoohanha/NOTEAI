"""
arXiv 공식 API 클라이언트

문서: https://info.arxiv.org/help/api/user-manual.html
엔드포인트: http://export.arxiv.org/api/query

외부 XML이므로 defusedxml이 있으면 우선 사용합니다.
"""

import re
from typing import List
from urllib.parse import quote_plus, urlencode
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


class ArxivFetchError(Exception):
    """arXiv API 호출 또는 파싱 실패"""


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
        categories = [
            (cat.get("term") or "").strip()
            for cat in entry.findall(f"{_ARXIV}primary_category")
            + entry.findall(f"{_ATOM}category")
            if (cat.get("term") or "").strip()
        ]
        # 중복 분류 제거 (순서 유지)
        unique_cats = list(dict.fromkeys(categories))

        papers.append(
            PaperItem(
                arxiv_id=arxiv_id,
                title=title,
                abstract=abstract,
                authors=_authors(entry),
                pdf_url=pdf_url,
                abs_url=abs_url,
                published_at=published or None,
                categories=unique_cats,
            )
        )

    return papers


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
        "search_query": f'all:"{query}"',
        "start": 0,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    url = f"{_ARXIV_API}?{urlencode(params, quote_via=quote_plus)}"
    headers = {
        "User-Agent": settings.TRENDS_USER_AGENT,
        "Accept": "application/atom+xml, application/xml, text/xml",
    }
    timeout = settings.TRENDS_TIMEOUT_SECONDS

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise ArxivFetchError("arXiv API 응답이 시간 초과되었습니다.") from exc
    except httpx.HTTPError as exc:
        raise ArxivFetchError(f"arXiv API 호출 실패: {exc}") from exc

    return parse_arxiv_feed(response.text)
