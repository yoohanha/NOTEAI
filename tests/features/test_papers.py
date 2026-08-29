"""
논문 검색(arXiv) 단위 및 API 테스트

실제 arXiv / LLM 네트워크는 호출하지 않습니다.
Atom XML 파싱과 `/mycode (검색어)` 형식, 엔드포인트 계약을 검증합니다.
"""

import pytest

from features.papers.client import ArxivFetchError, parse_arxiv_feed
from features.papers.llm import build_paper_context, generate_insight
from features.papers.schemas import PaperItem
from features.papers.service import PaperQueryError, extract_topic


ARXIV_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2209.14988v1</id>
    <title>DreamFusion: Text-to-3D using 2D Diffusion</title>
    <summary>
      We present a method for text-to-3D generation using a pretrained 2D
      text-to-image diffusion model.
    </summary>
    <published>2022-09-29T17:00:00Z</published>
    <author><name>Ben Poole</name></author>
    <author><name>Ajay Jain</name></author>
    <link href="http://arxiv.org/abs/2209.14988v1" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/2209.14988v1.pdf" rel="related" type="application/pdf"/>
    <arxiv:primary_category term="cs.CV"/>
    <category term="cs.CV" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2312.12345v2</id>
    <title>Gaussian Splatting for Real-Time Radiance Field Rendering</title>
    <summary>3D Gaussian Splatting enables real-time radiance field rendering.</summary>
    <published>2023-12-01T00:00:00Z</published>
    <author><name>Alice Kim</name></author>
    <link href="http://arxiv.org/abs/2312.12345v2" rel="alternate" type="text/html"/>
    <category term="cs.GR"/>
  </entry>
</feed>
"""

SAMPLE_PAPERS = [
    PaperItem(
        arxiv_id="2209.14988v1",
        title="DreamFusion: Text-to-3D using 2D Diffusion",
        abstract="We present a method for text-to-3D generation using diffusion.",
        authors=["Ben Poole", "Ajay Jain"],
        pdf_url="http://arxiv.org/pdf/2209.14988v1.pdf",
        abs_url="http://arxiv.org/abs/2209.14988v1",
        published_at="2022-09-29T17:00:00Z",
        categories=["cs.CV"],
    )
]


# ============ 검색어 파싱 ============


class TestExtractTopic:
    """`/mycode (검색어)` 형식"""

    def test_parses_command(self):
        assert extract_topic("/mycode (Text-to-3D)") == "Text-to-3D"

    def test_trims_inner_whitespace(self):
        assert extract_topic("/mycode (  Gaussian Splatting  )") == "Gaussian Splatting"

    def test_plain_query_passthrough(self):
        assert extract_topic("Text-to-3D") == "Text-to-3D"

    def test_rejects_empty(self):
        with pytest.raises(PaperQueryError):
            extract_topic("   ")

    def test_rejects_malformed_command(self):
        with pytest.raises(PaperQueryError):
            extract_topic("/mycode Text-to-3D")

    def test_rejects_empty_parentheses(self):
        with pytest.raises(PaperQueryError):
            extract_topic("/mycode ()")


# ============ Atom 파싱 ============


class TestParseArxivFeed:
    """arXiv Atom XML"""

    def test_parses_title_abstract_authors_pdf(self):
        papers = parse_arxiv_feed(ARXIV_SAMPLE)

        assert len(papers) == 2
        first = papers[0]
        assert first.title.startswith("DreamFusion")
        assert "text-to-3D" in first.abstract
        assert first.authors == ["Ben Poole", "Ajay Jain"]
        assert first.pdf_url.endswith(".pdf")
        assert "2209.14988" in first.arxiv_id
        assert first.abs_url.endswith("2209.14988v1")

    def test_builds_pdf_when_link_missing(self):
        papers = parse_arxiv_feed(ARXIV_SAMPLE)
        second = papers[1]
        assert second.pdf_url == "https://arxiv.org/pdf/2312.12345v2.pdf"

    def test_malformed_xml_raises(self):
        with pytest.raises(ArxivFetchError):
            parse_arxiv_feed("<not-xml")


# ============ LLM 프롬프트 ============


class TestPaperInsight:
    """초록 컨텍스트 주입 및 로컬 폴백"""

    def test_context_includes_abstract(self):
        context = build_paper_context(SAMPLE_PAPERS)
        assert "DreamFusion" in context
        assert "text-to-3D" in context
        assert "Ben Poole" in context

    @pytest.mark.asyncio
    async def test_local_fallback_without_api_key(self, monkeypatch):
        monkeypatch.setattr(
            "features.papers.llm.settings.LLM_API_KEY",
            "",
            raising=False,
        )
        insight = await generate_insight(
            "Text-to-3D",
            SAMPLE_PAPERS,
            "핵심 논문을 추천해 줘",
        )
        assert insight.provider == "local"
        assert "DreamFusion" in insight.answer or "Text-to-3D" in insight.answer
        assert "논문 초록 컨텍스트" in insight.prompt


# ============ API ============


@pytest.fixture
def stub_arxiv(monkeypatch):
    """arXiv HTTP를 고정 결과로 대체하고 LLM 키를 비웁니다."""

    async def fake_search(query, limit=8):
        return SAMPLE_PAPERS[:limit]

    monkeypatch.setattr("features.papers.service.search_arxiv", fake_search)
    monkeypatch.setattr(
        "features.papers.llm.settings.LLM_API_KEY",
        "",
        raising=False,
    )


class TestSearchPapersApi:
    """GET/POST /api/search-papers"""

    def test_requires_auth(self, client):
        response = client.get("/api/search-papers", params={"q": "/mycode (Text-to-3D)"})
        assert response.status_code in (401, 403)

    def test_get_with_command(self, client, auth_headers, stub_arxiv):
        response = client.get(
            "/api/search-papers",
            params={"q": "/mycode (Text-to-3D)", "limit": 8},
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == 200
        data = body["data"]
        assert data["query"] == "Text-to-3D"
        assert data["total"] == 1
        paper = data["papers"][0]
        assert paper["title"].startswith("DreamFusion")
        assert paper["abstract"]
        assert paper["authors"]
        assert paper["pdf_url"]
        assert data["insight"]["provider"] == "local"

    def test_post_with_question(self, client, auth_headers, stub_arxiv):
        response = client.post(
            "/api/search-papers",
            json={
                "query": "/mycode (Gaussian Splatting)",
                "limit": 5,
                "question": "먼저 읽으면 좋은 논문을 추천해 줘",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["query"] == "Gaussian Splatting"
        assert data["insight"]["answer"]
        assert "논문 초록 컨텍스트" in data["insight"]["prompt"]

    def test_malformed_command_returns_400(self, client, auth_headers, stub_arxiv):
        response = client.post(
            "/api/search-papers",
            json={"query": "/mycode Text-to-3D"},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "형식" in response.json()["detail"]
