"""
Trends(기술 트렌드 수집) 단위 및 통합 테스트

외부 네트워크에 의존하지 않도록 피드 응답을 고정 문자열로 주입합니다.
"""

import pytest

from features.trends import client as trends_client
from features.trends.client import (
    TrendFetchError,
    clean_html,
    parse_datetime,
    parse_feed,
    parse_newsapi,
)
from features.trends.service import trend_service, url_hash
from features.trends.sources import TrendSource, get_sources


# ============ Fixtures ============

@pytest.fixture
def source() -> TrendSource:
    """테스트용 소스 정의"""
    return TrendSource(key="test", name="테스트 소스", url="http://example.com/feed")


RSS_SAMPLE = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>RSS &amp; 첫 항목</title>
    <link>https://example.com/1?utm_source=feed</link>
    <description>&lt;p&gt;요약 &lt;b&gt;강조&lt;/b&gt;&lt;/p&gt;</description>
    <pubDate>Mon, 25 Aug 2026 12:00:00 +0000</pubDate>
    <category>AI</category>
  </item>
  <item>
    <title>두번째 항목</title>
    <link>https://example.com/2</link>
    <pubDate>Tue, 26 Aug 2026 09:30:00 +0000</pubDate>
  </item>
</channel></rss>"""

ATOM_SAMPLE = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Atom 항목</title>
    <link href="https://atom.example.com/1"/>
    <summary>아톰 요약</summary>
    <updated>2026-08-24T10:30:00Z</updated>
    <category term="ML"/>
  </entry>
</feed>"""


# ============ 파싱 단위 테스트 ============

class TestFeedParsing:
    """RSS/Atom 파싱"""

    def test_parses_rss(self, source):
        items = parse_feed(RSS_SAMPLE, source)

        assert len(items) == 2
        assert items[0]["title"] == "RSS & 첫 항목"
        assert items[0]["summary"] == "요약 강조"
        assert items[0]["tags"] == ["ai"]
        assert items[0]["source_key"] == "test"

    def test_parses_atom(self, source):
        items = parse_feed(ATOM_SAMPLE, source)

        assert len(items) == 1
        assert items[0]["title"] == "Atom 항목"
        # Atom의 링크는 href 속성에 있습니다
        assert items[0]["url"] == "https://atom.example.com/1"

    def test_skips_items_without_title_or_link(self, source):
        """제목이나 링크가 없는 항목은 버려야 합니다."""
        xml = """<?xml version="1.0"?><rss version="2.0"><channel>
        <item><description>제목 없음</description></item>
        <item><title>링크 없음</title></item>
        </channel></rss>"""

        assert parse_feed(xml, source) == []

    def test_malformed_xml_raises(self, source):
        with pytest.raises(TrendFetchError):
            parse_feed("<rss><unclosed>", source)

    def test_parses_newsapi(self):
        payload = {
            "status": "ok",
            "articles": [{
                "title": "뉴스 제목",
                "url": "https://news.example.com/1",
                "description": "설명",
                "publishedAt": "2026-08-26T01:00:00Z",
                "source": {"name": "TechCrunch"},
                "author": "홍길동",
            }],
        }
        src = TrendSource(key="n", name="N", url="http://x", kind="newsapi")
        items = parse_newsapi(payload, src)

        assert items[0]["title"] == "뉴스 제목"
        # 실제 매체명이 소스 이름을 대체해야 합니다
        assert items[0]["source_name"] == "TechCrunch"

    def test_newsapi_error_status_raises(self):
        src = TrendSource(key="n", name="N", url="http://x", kind="newsapi")

        with pytest.raises(TrendFetchError):
            parse_newsapi({"status": "error", "message": "키 오류"}, src)


class TestDateParsing:
    """발행 시각 파싱"""

    def test_parses_rfc822(self):
        result = parse_datetime("Mon, 25 Aug 2026 12:00:00 +0000")
        assert result.year == 2026 and result.hour == 12

    def test_parses_iso8601(self):
        result = parse_datetime("2026-08-24T10:30:00Z")
        assert result.year == 2026 and result.hour == 10

    def test_result_is_naive_utc(self):
        """DB의 다른 타임스탬프와 비교 가능하도록 naive여야 합니다."""
        assert parse_datetime("2026-08-24T10:30:00+09:00").tzinfo is None

    def test_returns_none_for_garbage(self):
        assert parse_datetime("어제쯤") is None
        assert parse_datetime(None) is None


class TestCleanHtml:
    """HTML 정리"""

    def test_strips_tags_and_entities(self):
        assert clean_html("<p>안녕 &amp; 반가워</p>") == "안녕 & 반가워"

    def test_truncates_long_text(self):
        result = clean_html("가" * 600, limit=100)
        assert len(result) <= 101 and result.endswith("…")

    def test_handles_none(self):
        assert clean_html(None) == ""


class TestUrlHash:
    """URL 정규화 기반 중복 판정"""

    def test_ignores_tracking_params(self):
        assert url_hash("https://a.com/1?utm_source=x") == url_hash("https://a.com/1")
        assert url_hash("https://a.com/1?fbclid=y") == url_hash("https://a.com/1")

    def test_ignores_trailing_slash_and_case(self):
        assert url_hash("https://A.com/1/") == url_hash("https://a.com/1")

    def test_keeps_meaningful_params(self):
        assert url_hash("https://a.com/1?id=5") != url_hash("https://a.com/1")


class TestSources:
    """소스 정의"""

    def test_default_sources_available(self):
        keys = {s.key for s in get_sources()}
        assert "hackernews" in keys and "arxiv_ai" in keys

    def test_filters_by_key(self):
        sources = get_sources(["hackernews"])
        assert [s.key for s in sources] == ["hackernews"]

    def test_newsapi_disabled_without_key(self, monkeypatch):
        """API 키가 없으면 NewsAPI 소스가 나오면 안 됩니다."""
        from core.config import settings
        monkeypatch.setattr(settings, "NEWSAPI_KEY", "")

        assert "newsapi" not in {s.key for s in get_sources()}

    def test_disabled_sources_are_excluded(self, monkeypatch):
        from core.config import settings
        monkeypatch.setattr(settings, "TRENDS_DISABLED_SOURCES", ["dev_to"])

        assert "dev_to" not in {s.key for s in get_sources()}


# ============ 서비스 통합 테스트 ============

@pytest.fixture
def stub_fetch(monkeypatch):
    """외부 네트워크 호출을 고정 응답으로 대체합니다."""
    async def fake_fetch_all(sources):
        src = sources[0] if sources else TrendSource(key="test", name="T", url="http://x")
        return parse_feed(RSS_SAMPLE, src), []

    monkeypatch.setattr(trends_client, "fetch_all", fake_fetch_all)
    monkeypatch.setattr("features.trends.service.fetch_all", fake_fetch_all)


class TestRefresh:
    """수집 및 저장"""

    @pytest.mark.asyncio
    async def test_saves_new_items(self, db, stub_fetch):
        from features.trends.schemas import RefreshRequest

        result = await trend_service.refresh(db, RefreshRequest(sources=["hackernews"]))

        assert result["saved"] == 2
        assert result["duplicates"] == 0

    @pytest.mark.asyncio
    async def test_second_refresh_detects_duplicates(self, db, stub_fetch):
        """같은 항목을 다시 수집하면 전부 중복이어야 합니다."""
        from features.trends.schemas import RefreshRequest

        await trend_service.refresh(db, RefreshRequest(sources=["hackernews"]))
        second = await trend_service.refresh(db, RefreshRequest(sources=["hackernews"]))

        assert second["saved"] == 0
        assert second["duplicates"] == 2

    @pytest.mark.asyncio
    async def test_persist_false_does_not_save(self, db, stub_fetch):
        from features.trends.models import TrendItem
        from features.trends.schemas import RefreshRequest

        await trend_service.refresh(
            db, RefreshRequest(sources=["hackernews"], persist=False)
        )

        assert db.query(TrendItem).count() == 0

    @pytest.mark.asyncio
    async def test_keyword_filter(self, db, stub_fetch):
        """키워드에 맞는 항목만 저장되어야 합니다."""
        from features.trends.schemas import RefreshRequest

        result = await trend_service.refresh(
            db, RefreshRequest(sources=["hackernews"], keywords=["두번째"])
        )

        assert result["saved"] == 1

    @pytest.mark.asyncio
    async def test_limit_per_source(self, db, stub_fetch):
        from features.trends.schemas import RefreshRequest

        result = await trend_service.refresh(
            db, RefreshRequest(sources=["hackernews"], limit_per_source=1)
        )

        assert result["saved"] == 1


class TestSaveAsNote:
    """트렌드를 노트로 변환"""

    def test_creates_note_and_marks_saved(self, db, test_user):
        from features.trends.models import TrendItem

        trend = TrendItem(
            title="테스트 트렌드",
            summary="요약문",
            url="https://example.com/x",
            url_hash=url_hash("https://example.com/x"),
            source_key="hackernews",
            source_name="HN",
            category="tech",
            tags=["ai"],
        )
        db.add(trend)
        db.commit()
        db.refresh(trend)

        note = trend_service.save_as_note(db, trend, test_user, extra_tags=["읽을거리"])

        assert note.title == "테스트 트렌드"
        assert "https://example.com/x" in note.content
        assert "hackernews" in note.tags
        assert "읽을거리" in note.tags
        # 같은 항목을 다시 저장하지 않도록 표시되어야 합니다
        assert trend.is_saved is True


# ============ API 통합 테스트 ============

class TestTrendsAPI:
    """Trends API 엔드포인트"""

    def test_list_requires_auth(self, client):
        assert client.get("/api/trends").status_code in (401, 403)

    def test_sources_endpoint(self, client, auth_headers):
        response = client.get("/api/trends/sources", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["data"]["total"] > 0

    def test_list_empty(self, client, auth_headers):
        response = client.get("/api/trends", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["data"]["total"] == 0

    def test_save_missing_trend_returns_404(self, client, auth_headers):
        response = client.post(
            "/api/trends/save", json={"trend_id": 9999}, headers=auth_headers
        )
        assert response.status_code == 404
