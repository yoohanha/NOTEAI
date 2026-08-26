"""
Graph(토픽 지식 그래프 분석) 단위 및 통합 테스트

외부 의존성이 없는 순수 파이썬 분석기와,
인증이 필요한 /api/graph/* 엔드포인트를 함께 검증합니다.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from features.graph import analyzer
from features.graph.analyzer import SourceDocument
from features.graph.service import graph_service
from features.notes.models import Note
from features.trends.models import TrendItem


# ============ Fixtures ============

@pytest.fixture
def sample_documents():
    """분석기 단위 테스트용 문헌 3건 (2건은 transformer 관련, 1건은 무관)"""
    return [
        SourceDocument(
            id="trend:1",
            doc_type="trend",
            title="Transformer 모델의 Attention 구조",
            body=(
                "트랜스포머는 attention 메커니즘을 핵심으로 삼는다. "
                "LLM 학습에서 attention 연산이 전체 비용을 좌우한다."
            ),
            tags=["ai", "nlp"],
        ),
        SourceDocument(
            id="trend:2",
            doc_type="trend",
            title="Transformer 파인튜닝 실전 가이드",
            body="transformer 를 파인튜닝할 때 attention layer 를 동결하면 비용이 준다.",
            tags=["llm"],
        ),
        SourceDocument(
            id="note:1",
            doc_type="note",
            title="쿠버네티스 오토스케일링",
            body="HPA 는 CPU 사용률을 기준으로 파드 수를 조절한다.",
            tags=["devops"],
        ),
    ]


@pytest.fixture
def seeded_trends(db: Session):
    """DB에 트렌드 항목을 심어 통합 테스트에서 분석 대상이 되게 합니다."""
    now = datetime.utcnow()

    items = [
        TrendItem(
            title="Transformer 아키텍처 심층 분석",
            summary="attention 메커니즘과 positional encoding 을 설명한다.",
            url="https://example.com/transformer-deep",
            url_hash="hash-transformer-1",
            source_key="test",
            source_name="테스트 피드",
            category="AI",
            tags=["ai", "nlp"],
            published_at=now - timedelta(days=1),
        ),
        TrendItem(
            title="Transformer 기반 LLM 서빙 최적화",
            summary="attention KV 캐시로 추론 지연을 줄이는 방법.",
            url="https://example.com/transformer-serving",
            url_hash="hash-transformer-2",
            source_key="test",
            source_name="테스트 피드",
            category="AI",
            tags=["llm", "serving"],
            published_at=now - timedelta(days=2),
        ),
        TrendItem(
            title="쿠버네티스 네트워크 정책 정리",
            summary="NetworkPolicy 로 파드 간 트래픽을 제한한다.",
            url="https://example.com/k8s-netpol",
            url_hash="hash-k8s-1",
            source_key="test",
            source_name="테스트 피드",
            category="DevOps",
            tags=["k8s"],
            published_at=now - timedelta(days=3),
        ),
    ]

    db.add_all(items)
    db.commit()

    return items


# ============ 분석기 단위 테스트 ============

class TestTokenizer:
    """텍스트 정제 및 토큰화"""

    def test_clean_text_removes_markdown_and_urls(self):
        """마크다운 기호, 링크, 코드블록, URL이 제거되어야 함"""
        raw = "# 제목\n[링크](https://a.b) `code` **강조** https://c.d"
        cleaned = analyzer.clean_text(raw)

        assert "https://" not in cleaned
        assert "#" not in cleaned
        assert "링크" in cleaned      # 링크는 표시 텍스트만 남음
        assert "강조" in cleaned

    def test_clean_text_handles_empty(self):
        """빈 입력에도 예외 없이 빈 문자열을 반환해야 함"""
        assert analyzer.clean_text("") == ""
        assert analyzer.clean_text(None) == ""

    def test_tokenize_mixes_korean_and_english(self):
        """한글과 영문 토큰이 함께 추출되고 소문자로 정규화되어야 함"""
        tokens = analyzer.tokenize("Transformer 모델은 Attention을 쓴다")

        assert "transformer" in tokens
        assert "attention" in tokens
        assert "모델" in tokens

    def test_tokenize_drops_stopwords(self):
        """불용어는 토큰에서 제외되어야 함"""
        tokens = analyzer.tokenize("the and 그리고 하지만 model")

        assert tokens == ["model"]

    def test_strip_particle_removes_longest_first(self):
        """조사는 긴 것부터 제거되어 '에서는'이 '에'로 잘리지 않아야 함"""
        assert analyzer.strip_particle("모델에서는") == "모델"
        assert analyzer.strip_particle("데이터를") == "데이터"

    def test_strip_particle_keeps_short_stems(self):
        """제거 후 2글자 미만이 되면 원본을 유지해야 함 (과도한 절삭 방지)"""
        assert analyzer.strip_particle("가는") == "가는"

    def test_tokenize_preserves_tech_terms(self):
        """gpt-4, c++ 처럼 기호가 섞인 기술 용어가 살아남아야 함"""
        tokens = analyzer.tokenize("GPT-4 와 c++ 비교")

        assert "gpt-4" in tokens
        assert "c++" in tokens


class TestScoring:
    """토픽 관련도 점수"""

    def test_scores_only_related_documents(self, sample_documents):
        """토픽과 무관한 문헌은 결과에서 제외되어야 함"""
        scored = analyzer.score_documents("transformer", sample_documents)

        ids = [doc.source.id for doc in scored]

        assert "trend:1" in ids
        assert "trend:2" in ids
        assert "note:1" not in ids  # 쿠버네티스 노트는 무관

    def test_sorted_by_score_desc(self, sample_documents):
        """점수 내림차순으로 정렬되어야 함"""
        scored = analyzer.score_documents("transformer", sample_documents)

        scores = [doc.score for doc in scored]

        assert scores == sorted(scores, reverse=True)

    def test_title_weighs_more_than_body(self):
        """제목에 토픽이 있는 문헌이 본문에만 있는 문헌보다 높은 점수를 받아야 함"""
        title_hit = SourceDocument(
            id="a", doc_type="note", title="Kubernetes 입문", body="컨테이너 오케스트레이션"
        )
        body_hit = SourceDocument(
            id="b", doc_type="note", title="인프라 정리", body="kubernetes 로 배포한다"
        )

        scored = analyzer.score_documents("kubernetes", [body_hit, title_hit])

        assert scored[0].source.id == "a"

    def test_empty_topic_returns_empty(self, sample_documents):
        """빈 토픽은 빈 결과를 반환해야 함"""
        assert analyzer.score_documents("", sample_documents) == []

    def test_no_match_returns_empty(self, sample_documents):
        """어디에도 없는 토픽은 빈 결과를 반환해야 함"""
        assert analyzer.score_documents("블록체인채굴장비", sample_documents) == []


class TestKeywords:
    """TF-IDF 키워드 추출"""

    def test_extracts_meaningful_keywords(self, sample_documents):
        """관련 문헌의 핵심어가 키워드로 추출되어야 함"""
        scored = analyzer.score_documents("transformer", sample_documents)
        keywords = analyzer.extract_keywords(scored, top_n=10)

        words = [kw["word"] for kw in keywords]

        assert "attention" in words

    def test_excludes_topic_itself(self, sample_documents):
        """토픽 자신은 키워드에서 제외되어야 함 (정보량이 없음)"""
        scored = analyzer.score_documents("transformer", sample_documents)
        keywords = analyzer.extract_keywords(scored, top_n=10, exclude=["transformer"])

        words = [kw["word"] for kw in keywords]

        assert "transformer" not in words

    def test_excludes_pure_numbers(self):
        """논문 ID나 버전 숫자가 키워드로 올라오면 안 됨"""
        docs = [
            SourceDocument(
                id="x", doc_type="note", title="릴리스 2608 정리", body="2608 빌드 노트"
            )
        ]
        scored = analyzer.score_documents("릴리스", docs)
        keywords = analyzer.extract_keywords(scored, top_n=10)

        words = [kw["word"] for kw in keywords]

        assert "2608" not in words

    def test_scores_normalized_to_one(self, sample_documents):
        """최상위 키워드 점수는 1.0으로 정규화되어야 함"""
        scored = analyzer.score_documents("transformer", sample_documents)
        keywords = analyzer.extract_keywords(scored, top_n=5)

        assert keywords[0]["score"] == pytest.approx(1.0)
        assert all(0.0 <= kw["score"] <= 1.0 for kw in keywords)

    def test_empty_input_returns_empty(self):
        """문헌이 없으면 빈 목록을 반환해야 함"""
        assert analyzer.extract_keywords([], top_n=5) == []


class TestSummaryAndCooccurrence:
    """추출 요약 및 공출현"""

    def test_summary_is_from_source_text(self, sample_documents):
        """요약문은 원문에서 뽑은 문장이어야 함 (생성이 아닌 추출)"""
        scored = analyzer.score_documents("transformer", sample_documents)
        keywords = analyzer.extract_keywords(scored, top_n=10)
        summary = analyzer.summarize(scored, keywords)

        assert summary
        assert "attention" in summary.lower() or "트랜스포머" in summary

    def test_summary_respects_max_sentences(self, sample_documents):
        """max_sentences 상한을 넘지 않아야 함"""
        scored = analyzer.score_documents("transformer", sample_documents)
        keywords = analyzer.extract_keywords(scored, top_n=10)
        summary = analyzer.summarize(scored, keywords, max_sentences=1)

        # 문장 1개만 선택되므로 지나치게 길 수 없음
        assert len(summary) <= 300

    def test_summary_empty_when_no_documents(self):
        """문헌이 없으면 빈 요약을 반환해야 함"""
        assert analyzer.summarize([], []) == ""

    def test_cooccurrence_pairs_are_sorted(self, sample_documents):
        """공출현 쌍은 횟수 내림차순이어야 함"""
        scored = analyzer.score_documents("transformer", sample_documents)
        keywords = analyzer.extract_keywords(scored, top_n=10)
        pairs = analyzer.co_occurrences(scored, keywords, min_count=1)

        counts = [count for _, _, count in pairs]

        assert counts == sorted(counts, reverse=True)


# ============ 서비스 계층 테스트 ============

class TestGraphService:
    """그래프 조립 및 자동 태깅"""

    def test_analyze_builds_connected_graph(
        self, db: Session, test_user, seeded_trends
    ):
        """분석 결과 그래프에 topic/trend/keyword 노드가 모두 있어야 함"""
        result = graph_service.analyze(db, topic="transformer", user=test_user)

        assert result["document_count"] == 2  # 쿠버네티스 항목은 제외

        node_types = {node["type"] for node in result["graph"]["nodes"]}

        assert "topic" in node_types
        assert "trend" in node_types
        assert "keyword" in node_types

    def test_graph_has_no_dangling_edges(
        self, db: Session, test_user, seeded_trends
    ):
        """모든 간선의 양 끝 노드가 실제로 존재해야 함"""
        result = graph_service.analyze(db, topic="transformer", user=test_user)

        node_ids = {node["id"] for node in result["graph"]["nodes"]}

        for edge in result["graph"]["edges"]:
            assert edge["source"] in node_ids
            assert edge["target"] in node_ids

    def test_analyze_respects_limit(self, db: Session, test_user, seeded_trends):
        """limit보다 많은 문헌이 그래프에 들어가면 안 됨"""
        result = graph_service.analyze(db, topic="transformer", user=test_user, limit=1)

        assert result["document_count"] == 1

    def test_analyze_source_filter(self, db: Session, test_user, seeded_trends):
        """sources=['notes']면 트렌드는 분석 대상에서 빠져야 함"""
        result = graph_service.analyze(
            db, topic="transformer", user=test_user, sources=["notes"]
        )

        assert result["document_count"] == 0

    def test_analyze_empty_result_is_well_formed(self, db: Session, test_user):
        """관련 문헌이 없어도 스키마에 맞는 빈 결과를 반환해야 함"""
        result = graph_service.analyze(db, topic="존재하지않는토픽", user=test_user)

        assert result["document_count"] == 0
        assert result["graph"] == {"nodes": [], "edges": []}
        assert result["keywords"] == []

    def test_analyze_excludes_other_users_private_notes(
        self, db: Session, test_user, test_another_user
    ):
        """다른 사용자의 비공개 노트는 분석 대상에서 제외되어야 함"""
        private_note = Note(
            user_id=test_another_user.id,
            title="Transformer 비밀 메모",
            content="attention 관련 사내 자료",
            is_public=False,
        )
        db.add(private_note)
        db.commit()

        result = graph_service.analyze(
            db, topic="transformer", user=test_user, sources=["notes"]
        )

        assert result["document_count"] == 0

    def test_analyze_includes_public_notes(
        self, db: Session, test_user, test_another_user
    ):
        """다른 사용자라도 공개 노트는 분석 대상에 포함되어야 함"""
        public_note = Note(
            user_id=test_another_user.id,
            title="Transformer 공개 정리",
            content="attention 메커니즘 요약",
            is_public=True,
        )
        db.add(public_note)
        db.commit()

        result = graph_service.analyze(
            db, topic="transformer", user=test_user, sources=["notes"]
        )

        assert result["document_count"] == 1

    def test_apply_tags_merges_without_overwriting(
        self, db: Session, test_user, test_note
    ):
        """기존 태그를 유지한 채 새 태그만 추가되어야 함"""
        original = list(test_note.tags)

        result = graph_service.apply_tags(
            db, user=test_user, note_ids=[test_note.id], tags=["attention"]
        )

        db.refresh(test_note)

        assert result["updated_note_ids"] == [test_note.id]
        assert all(tag in test_note.tags for tag in original)
        assert "attention" in test_note.tags

    def test_apply_tags_skips_other_users_notes(
        self, db: Session, test_user, test_another_user
    ):
        """남의 노트는 수정하지 않고 skipped로 보고해야 함"""
        other_note = Note(
            user_id=test_another_user.id,
            title="남의 노트",
            content="내용",
            tags=[],
        )
        db.add(other_note)
        db.commit()
        db.refresh(other_note)

        result = graph_service.apply_tags(
            db, user=test_user, note_ids=[other_note.id], tags=["attention"]
        )

        db.refresh(other_note)

        assert result["updated_note_ids"] == []
        assert result["skipped_note_ids"] == [other_note.id]
        assert other_note.tags == []

    def test_suggest_topics_returns_words(self, db: Session, test_user, seeded_trends):
        """보유 데이터에서 추천 토픽을 뽑아야 함"""
        topics = graph_service.suggest_topics(db, test_user, limit=5)

        assert len(topics) > 0
        assert all("topic" in item and "doc_count" in item for item in topics)


# ============ API 통합 테스트 ============

class TestGraphAPI:
    """/api/graph/* 엔드포인트"""

    def test_analyze_requires_auth(self, client):
        """인증 없이 호출하면 거부되어야 함"""
        response = client.post("/api/graph/analyze", json={"topic": "ai"})

        assert response.status_code in (401, 403)

    def test_analyze_returns_graph(self, client, auth_headers, seeded_trends):
        """정상 요청 시 200과 그래프 페이로드를 반환해야 함"""
        response = client.post(
            "/api/graph/analyze",
            json={"topic": "transformer", "limit": 10},
            headers=auth_headers,
        )

        assert response.status_code == 200

        body = response.json()
        data = body["data"]

        assert body["status"] == 200
        assert data["topic"] == "transformer"
        assert data["document_count"] == 2
        assert len(data["graph"]["nodes"]) > 0
        assert len(data["suggested_tags"]) > 0

    def test_analyze_rejects_blank_topic(self, client, auth_headers):
        """공백만 있는 토픽은 422로 거부되어야 함"""
        response = client.post(
            "/api/graph/analyze",
            json={"topic": "   "},
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_analyze_rejects_limit_over_max(self, client, auth_headers):
        """limit 상한(50)을 넘으면 422로 거부되어야 함"""
        response = client.post(
            "/api/graph/analyze",
            json={"topic": "ai", "limit": 999},
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_analyze_no_match_is_success(self, client, auth_headers):
        """검색 결과 없음은 오류가 아니라 200 + 빈 결과여야 함"""
        response = client.post(
            "/api/graph/analyze",
            json={"topic": "존재하지않는토픽zzz"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["data"]["document_count"] == 0

    def test_topics_endpoint(self, client, auth_headers, seeded_trends):
        """추천 토픽 목록을 반환해야 함"""
        response = client.get("/api/graph/topics?limit=5", headers=auth_headers)

        assert response.status_code == 200

        data = response.json()["data"]

        assert "topics" in data
        assert data["total"] == len(data["topics"])

    def test_apply_tags_endpoint(self, client, auth_headers, test_note):
        """태그 적용 엔드포인트가 노트를 갱신해야 함"""
        response = client.post(
            "/api/graph/apply-tags",
            json={"note_ids": [test_note.id], "tags": ["Attention", "LLM"]},
            headers=auth_headers,
        )

        assert response.status_code == 200

        data = response.json()["data"]

        assert data["updated_note_ids"] == [test_note.id]
        # 태그는 소문자로 정규화되어 저장됨
        assert data["applied_tags"] == ["attention", "llm"]

    def test_apply_tags_rejects_empty_list(self, client, auth_headers):
        """빈 note_ids는 422로 거부되어야 함"""
        response = client.post(
            "/api/graph/apply-tags",
            json={"note_ids": [], "tags": ["ai"]},
            headers=auth_headers,
        )

        assert response.status_code == 422
