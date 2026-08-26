"""
트렌드 수집 소스 정의
- 기본 RSS/Atom 피드 목록
- NewsAPI 등 API 키가 필요한 소스 정의

API 키가 필요 없는 RSS 소스만으로도 즉시 동작하며,
설정에 NEWSAPI_KEY가 있으면 뉴스 API 소스가 자동으로 활성화됩니다.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.config import settings


@dataclass(frozen=True)
class TrendSource:
    """수집 소스 한 건의 정의"""

    key: str  # 내부 식별자 (API 파라미터로 사용)
    name: str  # 사람이 읽는 이름
    url: str  # 피드 또는 API 엔드포인트
    kind: str = "rss"  # rss | newsapi
    category: str = "tech"  # 소스 분류
    enabled: bool = True
    # API 키 등 요청 시 붙일 쿼리 파라미터
    params: Dict[str, str] = field(default_factory=dict)


# ============ 기본 RSS 소스 (API 키 불필요) ============
DEFAULT_RSS_SOURCES: List[TrendSource] = [
    TrendSource(
        key="hackernews",
        name="Hacker News Front Page",
        url="https://hnrss.org/frontpage",
        category="tech",
    ),
    TrendSource(
        key="arxiv_ai",
        name="arXiv cs.AI 최신 논문",
        url="http://export.arxiv.org/rss/cs.AI",
        category="research",
    ),
    TrendSource(
        key="arxiv_ml",
        name="arXiv cs.LG 최신 논문",
        url="http://export.arxiv.org/rss/cs.LG",
        category="research",
    ),
    TrendSource(
        key="github_blog",
        name="GitHub Blog",
        url="https://github.blog/feed/",
        category="engineering",
    ),
    TrendSource(
        key="dev_to",
        name="DEV Community",
        url="https://dev.to/feed",
        category="engineering",
    ),
    TrendSource(
        key="python_insider",
        name="Python Insider",
        url="https://feeds.feedburner.com/PythonInsider",
        category="language",
    ),
]


def _newsapi_source() -> Optional[TrendSource]:
    """
    NewsAPI 소스 생성 (API 키가 설정된 경우에만)

    Returns:
        API 키가 있으면 TrendSource, 없으면 None
    """
    api_key = getattr(settings, "NEWSAPI_KEY", "") or ""

    if not api_key.strip():
        return None

    return TrendSource(
        key="newsapi",
        name="NewsAPI 기술 헤드라인",
        url="https://newsapi.org/v2/top-headlines",
        kind="newsapi",
        category="news",
        params={
            "category": "technology",
            "language": getattr(settings, "NEWSAPI_LANGUAGE", "en"),
            "pageSize": "30",
            "apiKey": api_key,
        },
    )


def get_sources(keys: Optional[List[str]] = None) -> List[TrendSource]:
    """
    사용 가능한 수집 소스 목록 반환

    Args:
        keys: 특정 소스만 선택할 때 지정하는 key 목록 (None이면 전체)

    Returns:
        활성화된 소스 목록
    """
    sources = list(DEFAULT_RSS_SOURCES)

    # 설정에서 비활성화한 소스 제외
    disabled = set(getattr(settings, "TRENDS_DISABLED_SOURCES", []) or [])
    sources = [source for source in sources if source.key not in disabled]

    # 사용자가 추가한 커스텀 피드 (설정: TRENDS_CUSTOM_FEEDS=["https://..."])
    for index, url in enumerate(getattr(settings, "TRENDS_CUSTOM_FEEDS", []) or []):
        sources.append(
            TrendSource(
                key=f"custom_{index + 1}",
                name=f"사용자 피드 {index + 1}",
                url=str(url),
                category="custom",
            )
        )

    # API 키가 있으면 뉴스 API 소스 추가
    news_source = _newsapi_source()
    if news_source is not None:
        sources.append(news_source)

    if keys:
        requested = set(keys)
        sources = [source for source in sources if source.key in requested]

    return [source for source in sources if source.enabled]


def get_source(key: str) -> Optional[TrendSource]:
    """
    key로 단일 소스 조회

    Args:
        key: 소스 식별자

    Returns:
        일치하는 소스 또는 None
    """
    for source in get_sources():
        if source.key == key:
            return source

    return None
