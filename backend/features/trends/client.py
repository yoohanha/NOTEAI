"""
외부 피드/API 클라이언트
- RSS 2.0 및 Atom 피드 파싱 (표준 라이브러리 xml.etree 사용)
- NewsAPI JSON 응답 파싱
- 비동기 병렬 수집, 타임아웃/오류 격리

XML 파싱은 외부 입력을 다루므로 defusedxml이 설치되어 있으면
그것을 우선 사용하여 XXE/폭탄 공격을 방어합니다.
"""

import asyncio
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx

from core.config import settings
from features.trends.sources import TrendSource

# 외부 XML을 안전하게 파싱하기 위해 defusedxml 우선 사용
try:
    from defusedxml import ElementTree as SafeET  # type: ignore

    _XML_PARSER = SafeET
except ImportError:  # pragma: no cover - 설치 여부에 따라 달라짐
    import xml.etree.ElementTree as _StdET

    _XML_PARSER = _StdET

# Atom 네임스페이스
_ATOM_NS = "{http://www.w3.org/2005/Atom}"

# HTML 태그 제거용
_HTML_TAG_RE = re.compile(r"<[^>]+>")

# HTML 엔티티 중 자주 쓰이는 것만 치환
_HTML_ENTITIES = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&#39;": "'",
    "&apos;": "'",
    "&nbsp;": " ",
}

# ISO 8601 파싱 시 시도할 포맷
_ISO_FORMATS = (
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
)


class TrendFetchError(Exception):
    """피드 수집 실패 (개별 소스 단위로 격리됨)"""


def clean_html(text: Optional[str], limit: int = 500) -> str:
    """
    피드 요약문에서 HTML 태그와 엔티티를 제거

    Args:
        text: 원본 문자열 (None 허용)
        limit: 최대 길이

    Returns:
        정리된 플레인 텍스트
    """
    if not text:
        return ""

    plain = _HTML_TAG_RE.sub(" ", text)

    for entity, char in _HTML_ENTITIES.items():
        plain = plain.replace(entity, char)

    plain = re.sub(r"\s+", " ", plain).strip()

    if len(plain) > limit:
        plain = plain[:limit].rstrip() + "…"

    return plain


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """
    RSS(RFC 822) 또는 Atom(ISO 8601) 날짜 문자열을 파싱

    Args:
        value: 날짜 문자열

    Returns:
        타임존 정보를 제거한 UTC naive datetime (DB 컬럼과 일치), 실패 시 None
    """
    if not value or not value.strip():
        return None

    raw = value.strip()

    # RSS의 RFC 822 형식 (Mon, 01 Jan 2026 12:00:00 +0000)
    try:
        parsed = parsedate_to_datetime(raw)
        if parsed is not None:
            return _to_naive_utc(parsed)
    except (TypeError, ValueError):
        pass

    # Atom의 ISO 8601 형식
    for fmt in _ISO_FORMATS:
        try:
            return _to_naive_utc(datetime.strptime(raw, fmt))
        except ValueError:
            continue

    # 파이썬 3.11+ 의 관대한 ISO 파서로 마지막 시도
    try:
        return _to_naive_utc(datetime.fromisoformat(raw.replace("Z", "+00:00")))
    except ValueError:
        return None


def _to_naive_utc(value: datetime) -> datetime:
    """
    타임존이 있는 datetime을 UTC 기준 naive datetime으로 변환

    DB의 다른 타임스탬프 컬럼이 모두 naive UTC(datetime.utcnow)이므로
    비교 시 오류가 나지 않도록 통일합니다.

    Args:
        value: 변환할 datetime

    Returns:
        타임존 정보가 제거된 UTC datetime
    """
    if value.tzinfo is None:
        return value

    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _text_of(element, *tag_names: str) -> Optional[str]:
    """
    자식 엘리먼트 중 첫 번째로 발견되는 태그의 텍스트를 반환

    Args:
        element: 부모 XML 엘리먼트
        tag_names: 찾을 태그 이름들 (우선순위 순)

    Returns:
        텍스트 또는 None
    """
    for tag in tag_names:
        found = element.find(tag)
        if found is not None:
            # Atom의 <link href="..."> 처럼 값이 속성에 있는 경우 처리
            if found.text and found.text.strip():
                return found.text.strip()
            href = found.get("href")
            if href:
                return href.strip()

    return None


def parse_feed(xml_text: str, source: TrendSource) -> List[Dict[str, Any]]:
    """
    RSS 2.0 또는 Atom 피드 XML을 항목 리스트로 파싱

    Args:
        xml_text: 피드 XML 문자열
        source: 출처 정의 (결과에 메타데이터로 부착)

    Returns:
        트렌드 항목 딕셔너리 목록

    Raises:
        TrendFetchError: XML 파싱 실패 시
    """
    try:
        root = _XML_PARSER.fromstring(xml_text)
    except Exception as exc:
        raise TrendFetchError(f"피드 XML 파싱 실패: {exc}") from exc

    items: List[Dict[str, Any]] = []

    # RSS 2.0: <rss><channel><item>, RDF: <item>
    rss_items = root.findall(".//item")

    # Atom: <feed><entry>
    atom_items = root.findall(f".//{_ATOM_NS}entry")

    for element in rss_items:
        title = _text_of(element, "title")
        link = _text_of(element, "link", "guid")

        if not title or not link:
            # 제목이나 링크가 없으면 노트로서 가치가 없으므로 제외
            continue

        items.append(
            _build_item(
                source=source,
                title=title,
                url=link,
                summary=_text_of(element, "description", "summary"),
                author=_text_of(element, "author", "{http://purl.org/dc/elements/1.1/}creator"),
                published_raw=_text_of(
                    element, "pubDate", "{http://purl.org/dc/elements/1.1/}date"
                ),
                categories=[
                    cat.text.strip()
                    for cat in element.findall("category")
                    if cat.text and cat.text.strip()
                ],
            )
        )

    for element in atom_items:
        title = _text_of(element, f"{_ATOM_NS}title")
        link = _text_of(element, f"{_ATOM_NS}link", f"{_ATOM_NS}id")

        if not title or not link:
            continue

        items.append(
            _build_item(
                source=source,
                title=title,
                url=link,
                summary=_text_of(
                    element, f"{_ATOM_NS}summary", f"{_ATOM_NS}content"
                ),
                author=_text_of(element, f"{_ATOM_NS}author/{_ATOM_NS}name"),
                published_raw=_text_of(
                    element, f"{_ATOM_NS}published", f"{_ATOM_NS}updated"
                ),
                categories=[
                    cat.get("term", "").strip()
                    for cat in element.findall(f"{_ATOM_NS}category")
                    if cat.get("term")
                ],
            )
        )

    return items


def parse_newsapi(payload: Dict[str, Any], source: TrendSource) -> List[Dict[str, Any]]:
    """
    NewsAPI JSON 응답을 항목 리스트로 파싱

    Args:
        payload: NewsAPI 응답 JSON
        source: 출처 정의

    Returns:
        트렌드 항목 목록

    Raises:
        TrendFetchError: API가 오류 상태를 반환한 경우
    """
    if payload.get("status") != "ok":
        raise TrendFetchError(
            f"NewsAPI 오류: {payload.get('code')} - {payload.get('message')}"
        )

    items: List[Dict[str, Any]] = []

    for article in payload.get("articles", []):
        title = (article.get("title") or "").strip()
        url = (article.get("url") or "").strip()

        if not title or not url:
            continue

        items.append(
            _build_item(
                source=source,
                title=title,
                url=url,
                summary=article.get("description"),
                author=article.get("author"),
                published_raw=article.get("publishedAt"),
                categories=[],
                image_url=article.get("urlToImage"),
                origin=(article.get("source") or {}).get("name"),
            )
        )

    return items


def _build_item(
    source: TrendSource,
    title: str,
    url: str,
    summary: Optional[str],
    author: Optional[str],
    published_raw: Optional[str],
    categories: List[str],
    image_url: Optional[str] = None,
    origin: Optional[str] = None,
) -> Dict[str, Any]:
    """
    수집 항목을 표준 딕셔너리 형태로 정규화

    Args:
        source: 출처 정의
        title: 제목
        url: 원문 링크
        summary: 요약문 (HTML 포함 가능)
        author: 작성자
        published_raw: 발행 시각 원문
        categories: 카테고리/태그 목록
        image_url: 대표 이미지 주소
        origin: 실제 매체명 (NewsAPI 등)

    Returns:
        정규화된 항목 딕셔너리
    """
    return {
        "source_key": source.key,
        "source_name": origin or source.name,
        "category": source.category,
        "title": clean_html(title, limit=255),
        "url": url,
        "summary": clean_html(summary),
        "author": clean_html(author, limit=100) or None,
        "published_at": parse_datetime(published_raw),
        "tags": [tag.lower() for tag in categories if tag][:10],
        "image_url": image_url,
    }


async def fetch_source(
    client: httpx.AsyncClient,
    source: TrendSource,
) -> Tuple[TrendSource, List[Dict[str, Any]], Optional[str]]:
    """
    단일 소스에서 항목을 수집

    Args:
        client: 재사용할 httpx 비동기 클라이언트
        source: 수집 대상 소스

    Returns:
        (소스, 수집된 항목 목록, 오류 메시지 또는 None)
        오류가 발생해도 예외를 던지지 않고 튜플로 반환하여
        다른 소스 수집이 중단되지 않도록 합니다.
    """
    try:
        response = await client.get(source.url, params=source.params or None)
        response.raise_for_status()

        if source.kind == "newsapi":
            items = parse_newsapi(response.json(), source)
        else:
            items = parse_feed(response.text, source)

        return source, items, None

    except httpx.TimeoutException:
        return source, [], f"{source.name}: 요청 시간 초과"
    except httpx.HTTPStatusError as exc:
        return source, [], f"{source.name}: HTTP {exc.response.status_code}"
    except httpx.HTTPError as exc:
        return source, [], f"{source.name}: 네트워크 오류 ({exc})"
    except TrendFetchError as exc:
        return source, [], f"{source.name}: {exc}"
    except Exception as exc:
        return source, [], f"{source.name}: 예기치 못한 오류 ({exc})"


async def fetch_all(
    sources: List[TrendSource],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    여러 소스를 병렬로 수집

    Args:
        sources: 수집할 소스 목록

    Returns:
        (전체 항목 목록, 오류 메시지 목록)
    """
    if not sources:
        return [], []

    timeout = getattr(settings, "TRENDS_TIMEOUT_SECONDS", 10.0)
    user_agent = getattr(
        settings, "TRENDS_USER_AGENT", "NOTEAI/1.0 (+https://github.com/yoohanha/NOTEAI)"
    )

    limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        limits=limits,
        headers={"User-Agent": user_agent},
    ) as client:
        results = await asyncio.gather(
            *(fetch_source(client, source) for source in sources)
        )

    items: List[Dict[str, Any]] = []
    errors: List[str] = []

    for _, source_items, error in results:
        if error:
            errors.append(error)
        items.extend(source_items)

    return items, errors
