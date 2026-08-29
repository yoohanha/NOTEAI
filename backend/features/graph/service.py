"""
Graph 비즈니스 로직

DB에서 분석 대상 문헌(내 노트 + 수집 트렌드)을 모아
analyzer 모듈로 분석한 뒤, 프론트엔드가 그대로 그릴 수 있는
Node/Edge 그래프로 조립합니다.

새 테이블을 만들지 않는 stateless 연산이므로,
데이터가 갱신되면 다음 분석에 즉시 반영됩니다.
"""

from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from features.auth.models import User
from features.graph import analyzer
from features.graph.analyzer import ScoredDocument, SourceDocument
from features.notes.models import Note
from features.trends.models import TrendItem

# ============ 상수 ============

# LIKE 사전 필터로 가져올 최대 후보 수
# 파이썬 쪽 점수 계산 비용을 일정하게 유지하기 위한 상한입니다.
CANDIDATE_LIMIT = 400

# 문헌 하나가 키워드와 맺을 수 있는 최대 간선 수
# 무제한이면 문헌×키워드만큼 간선이 생겨 그래프가 읽을 수 없게 됩니다.
MAX_EDGES_PER_DOCUMENT = 5

# 본문 미리보기 길이
SNIPPET_LENGTH = 160

# 자동 태깅 후보로 제안할 키워드 수
SUGGESTED_TAG_COUNT = 8


class GraphService:
    """토픽 지식 그래프 분석 서비스"""

    # ============ 문헌 수집 ============

    @staticmethod
    def _build_like_filters(column, topic_tokens: Sequence[str]) -> List:
        """
        토픽 토큰 각각에 대한 LIKE 조건 목록을 만듭니다.

        Args:
            column: 검색할 컬럼 (문자열로 캐스팅된 상태여야 함)
            topic_tokens: 토픽에서 추출한 토큰

        Returns:
            SQLAlchemy 조건 목록
        """
        return [column.ilike(f"%{token}%") for token in topic_tokens]

    @staticmethod
    def _note_to_source(note: Note, is_own: bool) -> SourceDocument:
        """노트 ORM 객체를 분석기 입력 형식으로 변환합니다."""
        return SourceDocument(
            id=f"note:{note.id}",
            doc_type="note",
            title=note.title or "",
            body=note.content or "",
            tags=list(note.tags or []),
            meta={
                "ref_id": note.id,
                "category": note.category,
                "url": None,
                "source_name": "내 노트",
                "published_at": note.created_at,
                "is_own": is_own,
            },
        )

    @staticmethod
    def list_owned_note_ids(
        db: Session,
        user: User,
        limit: int = 50,
    ) -> List[int]:
        """
        현재 사용자가 삭제하지 않은 노트 ID를 최신순으로 반환합니다.

        태그 적용 대상과 분석 응답의 my_note_ids에 사용합니다.
        """
        rows = (
            db.query(Note.id)
            .filter(
                Note.user_id == user.id,
                Note.deleted_at.is_(None),
            )
            .order_by(Note.updated_at.desc())
            .limit(limit)
            .all()
        )
        return [row[0] for row in rows]

    @staticmethod
    def collect_notes(
        db: Session,
        user: User,
        topic_tokens: Sequence[str],
    ) -> List[SourceDocument]:
        """
        분석에 넣을 노트를 수집합니다.

        내 노트는 토픽 단어가 없어도 항상 가져옵니다.
        (큐레이션에서 담은 노트가 그래프/태그 적용에서 빠지지 않게 하기 위함)
        다른 사람의 공개 노트만 토픽 LIKE로 좁힙니다.

        Args:
            db: 데이터베이스 세션
            user: 현재 사용자
            topic_tokens: 토픽 토큰 목록

        Returns:
            SourceDocument 목록
        """
        owned_rows = (
            db.query(Note)
            .filter(
                Note.deleted_at.is_(None),
                Note.user_id == user.id,
            )
            .order_by(Note.updated_at.desc())
            .limit(CANDIDATE_LIMIT)
            .all()
        )

        public_query = db.query(Note).filter(
            Note.deleted_at.is_(None),
            Note.is_public.is_(True),
            Note.user_id != user.id,
        )

        # 제목/본문/태그 어디든 토픽 토큰이 있으면 후보로 채택
        if topic_tokens:
            conditions = []
            for column in (Note.title, Note.content, cast(Note.tags, String)):
                conditions.extend(
                    GraphService._build_like_filters(column, topic_tokens)
                )
            public_query = public_query.filter(or_(*conditions))

        public_rows = (
            public_query.order_by(Note.updated_at.desc())
            .limit(CANDIDATE_LIMIT)
            .all()
        )

        documents = [
            GraphService._note_to_source(note, is_own=True) for note in owned_rows
        ]
        documents.extend(
            GraphService._note_to_source(note, is_own=False) for note in public_rows
        )
        return documents

    @staticmethod
    def collect_trends(
        db: Session,
        topic_tokens: Sequence[str],
    ) -> List[SourceDocument]:
        """
        토픽과 관련 있을 법한 수집 트렌드를 가져옵니다.

        Args:
            db: 데이터베이스 세션
            topic_tokens: 토픽 토큰 목록

        Returns:
            SourceDocument 목록
        """
        query = db.query(TrendItem)

        if topic_tokens:
            conditions = []
            for column in (
                TrendItem.title,
                TrendItem.summary,
                cast(TrendItem.tags, String),
            ):
                conditions.extend(
                    GraphService._build_like_filters(column, topic_tokens)
                )
            query = query.filter(or_(*conditions))

        # SQLite는 DESC 정렬에서 NULL을 마지막에 두므로 발행일이 없는 항목이
        # 최신 항목을 밀어내지 않습니다.
        rows = (
            query.order_by(TrendItem.published_at.desc())
            .limit(CANDIDATE_LIMIT)
            .all()
        )

        return [
            SourceDocument(
                id=f"trend:{item.id}",
                doc_type="trend",
                title=item.title or "",
                body=item.summary or "",
                tags=list(item.tags or []),
                meta={
                    "ref_id": item.id,
                    "category": item.category,
                    "url": item.url,
                    "source_name": item.source_name or item.source_key,
                    "published_at": item.published_at or item.fetched_at,
                },
            )
            for item in rows
        ]

    @staticmethod
    def collect_documents(
        db: Session,
        topic: str,
        user: User,
        sources: Sequence[str],
    ) -> List[SourceDocument]:
        """
        지정한 소스에서 분석 후보 문헌을 모두 모읍니다.

        Args:
            db: 데이터베이스 세션
            topic: 토픽 문자열
            user: 현재 사용자
            sources: ["notes", "trends"] 중 선택

        Returns:
            SourceDocument 목록
        """
        topic_tokens = analyzer.tokenize(topic)

        # 토픽이 전부 불용어면 원문을 그대로 LIKE 검색어로 사용
        if not topic_tokens:
            fallback = topic.strip().lower()
            topic_tokens = [fallback] if fallback else []

        documents: List[SourceDocument] = []

        if "notes" in sources:
            documents.extend(
                GraphService.collect_notes(db, user, topic_tokens)
            )

        if "trends" in sources:
            documents.extend(GraphService.collect_trends(db, topic_tokens))

        return documents

    # ============ 그래프 조립 ============

    @staticmethod
    def build_graph(
        topic: str,
        scored_documents: Sequence[ScoredDocument],
        keywords: Sequence[Dict],
        pairs: Sequence[Tuple[str, str, int]],
    ) -> Dict:
        """
        문헌·키워드·공출현 정보를 Node/Edge 그래프로 조립합니다.

        구성:
            topic  --relevant--> document  --tagged--> keyword
                                                keyword --co_occurs--> keyword

        Args:
            topic: 토픽 문자열 (중심 노드가 됨)
            scored_documents: 그래프에 포함할 문헌 (이미 상위 N개로 잘린 상태)
            keywords: extract_keywords 결과
            pairs: co_occurrences 결과

        Returns:
            {"nodes": [...], "edges": [...]}
        """
        nodes: List[Dict] = []
        edges: List[Dict] = []

        # ---- 중심 토픽 노드 ----
        nodes.append(
            {
                "id": "topic",
                "label": topic,
                "type": "topic",
                "weight": 1.0,
                "meta": {"document_count": len(scored_documents)},
            }
        )

        # ---- 문헌 노드 + 토픽 연결 ----
        # 0으로 나누지 않도록 최대 점수를 1 이상으로 보정
        max_doc_score = max(
            (doc.score for doc in scored_documents), default=1.0
        ) or 1.0

        keyword_scores = {kw["word"]: kw["score"] for kw in keywords}

        for doc in scored_documents:
            normalized = round(min(doc.score / max_doc_score, 1.0), 4)

            nodes.append(
                {
                    "id": doc.source.id,
                    "label": doc.source.title[:60] or "(제목 없음)",
                    "type": doc.source.doc_type,
                    "weight": normalized,
                    "meta": {
                        "url": doc.source.meta.get("url"),
                        "source_name": doc.source.meta.get("source_name"),
                        "category": doc.source.meta.get("category"),
                        "matched": doc.matched,
                    },
                }
            )

            edges.append(
                {
                    "source": "topic",
                    "target": doc.source.id,
                    "relation": "relevant",
                    "weight": normalized,
                }
            )

        # ---- 키워드 노드 ----
        for keyword in keywords:
            nodes.append(
                {
                    "id": f"kw:{keyword['word']}",
                    "label": keyword["word"],
                    "type": "keyword",
                    "weight": round(min(keyword["score"], 1.0), 4),
                    "meta": {"doc_count": keyword["doc_count"]},
                }
            )

        # ---- 문헌 -> 키워드 간선 ----
        for doc in scored_documents:
            if not doc.tokens:
                continue

            max_freq = max(doc.tokens.values()) or 1.0

            # 이 문헌에 등장한 키워드를 빈도순 상위 N개만 연결
            present = [
                (word, doc.tokens[word])
                for word in keyword_scores
                if doc.tokens.get(word)
            ]
            present.sort(key=lambda kv: kv[1], reverse=True)

            for word, freq in present[:MAX_EDGES_PER_DOCUMENT]:
                edges.append(
                    {
                        "source": doc.source.id,
                        "target": f"kw:{word}",
                        "relation": "tagged",
                        "weight": round(min(freq / max_freq, 1.0), 4),
                    }
                )

        # ---- 키워드 <-> 키워드 간선 (공출현) ----
        max_pair_count = max((count for _, _, count in pairs), default=1) or 1

        for word_a, word_b, count in pairs:
            edges.append(
                {
                    "source": f"kw:{word_a}",
                    "target": f"kw:{word_b}",
                    "relation": "co_occurs",
                    "weight": round(min(count / max_pair_count, 1.0), 4),
                }
            )

        return {"nodes": nodes, "edges": edges}

    @staticmethod
    def _merge_owned_notes_into_scored(
        scored: List[ScoredDocument],
        candidates: Sequence[SourceDocument],
        limit: int,
    ) -> List[ScoredDocument]:
        """
        토픽 단어가 없어 점수가 0인 내 노트도 결과에서 빠지지 않게 붙입니다.

        관련 문헌을 우선하되, 문헌 상한의 절반(최소 3건)까지 내 노트를 확보합니다.
        """
        scored_ids = {item.source.id for item in scored}
        extras: List[ScoredDocument] = []

        for document in candidates:
            if document.doc_type != "note" or not document.meta.get("is_own"):
                continue
            if document.id in scored_ids:
                continue
            extras.append(
                ScoredDocument(
                    source=document,
                    score=0.01,
                    tokens=analyzer.build_weighted_tokens(document),
                    matched=[],
                )
            )

        notes = [item for item in scored if item.source.doc_type == "note"]
        others = [item for item in scored if item.source.doc_type != "note"]
        notes.extend(extras)

        if not notes:
            return scored[:limit]

        note_slots = min(len(notes), max(3, limit // 2), limit)
        kept_notes = notes[:note_slots]
        remaining = limit - len(kept_notes)
        return kept_notes + others[:remaining]

    # ============ 분석 진입점 ============

    @staticmethod
    def analyze(
        db: Session,
        topic: str,
        user: User,
        limit: int = 30,
        sources: Sequence[str] = ("notes", "trends"),
        max_keywords: int = 15,
    ) -> Dict:
        """
        토픽을 분석해 요약·키워드·자동 태그·지식 그래프를 만듭니다.

        Args:
            db: 데이터베이스 세션
            topic: 분석할 토픽
            user: 현재 사용자
            limit: 그래프에 포함할 최대 문헌 수
            sources: 분석 대상 소스
            max_keywords: 추출할 최대 키워드 수

        Returns:
            AnalyzeResponse에 대응하는 딕셔너리.
            관련 문헌이 하나도 없으면 document_count=0인 빈 결과를 반환합니다.
        """
        candidates = GraphService.collect_documents(db, topic, user, sources)
        my_note_ids = GraphService.list_owned_note_ids(db, user)

        # 관련도 점수 계산 후, 매칭되지 않은 내 노트도 상한 안에서 포함
        scored = analyzer.score_documents(topic, candidates)
        scored = GraphService._merge_owned_notes_into_scored(
            scored, candidates, limit
        )

        if not scored:
            return {
                "topic": topic,
                "summary": "",
                "document_count": 0,
                "keywords": [],
                "suggested_tags": [],
                "documents": [],
                "graph": {"nodes": [], "edges": []},
                "analyzed_at": datetime.utcnow(),
                "my_note_ids": my_note_ids,
            }

        # 토픽 자신은 키워드 목록에서 제외 (모든 문헌에 있으므로 정보량이 없음)
        topic_tokens = analyzer.tokenize(topic) or [topic.strip().lower()]

        keywords = analyzer.extract_keywords(
            scored, top_n=max_keywords, exclude=topic_tokens
        )
        summary = analyzer.summarize(scored, keywords)
        pairs = analyzer.co_occurrences(scored, keywords)

        graph = GraphService.build_graph(topic, scored, keywords, pairs)

        max_doc_score = max((doc.score for doc in scored), default=1.0) or 1.0

        documents = [
            {
                "id": doc.source.id,
                "ref_id": doc.source.meta.get("ref_id", 0),
                "type": doc.source.doc_type,
                "title": doc.source.title or "(제목 없음)",
                "score": round(min(doc.score / max_doc_score, 1.0), 4),
                "snippet": analyzer.clean_text(doc.source.body)[:SNIPPET_LENGTH],
                "url": doc.source.meta.get("url"),
                "source_name": doc.source.meta.get("source_name"),
                "tags": doc.source.tags,
                "published_at": doc.source.meta.get("published_at"),
            }
            for doc in scored
        ]

        return {
            "topic": topic,
            "summary": summary,
            "document_count": len(scored),
            "keywords": keywords,
            "suggested_tags": [kw["word"] for kw in keywords[:SUGGESTED_TAG_COUNT]],
            "documents": documents,
            "graph": graph,
            "analyzed_at": datetime.utcnow(),
            "my_note_ids": my_note_ids,
        }

    # ============ 추천 토픽 ============

    @staticmethod
    def suggest_topics(db: Session, user: User, limit: int = 12) -> List[Dict]:
        """
        보유 데이터에서 자주 등장하는 단어를 토픽 후보로 제안합니다.

        입력창 자동완성/칩 UI에 사용합니다.

        Args:
            db: 데이터베이스 세션
            user: 현재 사용자
            limit: 반환할 토픽 수

        Returns:
            [{"topic": str, "doc_count": int}] 목록
        """
        # 토픽 토큰을 비워 두면 LIKE 필터 없이 최신 문헌을 그대로 가져옵니다.
        documents = GraphService.collect_notes(db, user, [])
        documents.extend(GraphService.collect_trends(db, []))

        if not documents:
            return []

        # 점수 계산 없이 토큰만 필요하므로 ScoredDocument로 감싸 재사용
        wrapped = [
            ScoredDocument(
                source=document,
                score=1.0,
                tokens=analyzer.build_weighted_tokens(document),
            )
            for document in documents
        ]

        keywords = analyzer.extract_keywords(wrapped, top_n=limit)

        return [
            {"topic": keyword["word"], "doc_count": keyword["doc_count"]}
            for keyword in keywords
        ]

    # ============ 자동 태깅 적용 ============

    @staticmethod
    def apply_tags(
        db: Session,
        user: User,
        note_ids: Sequence[int],
        tags: Sequence[str],
    ) -> Dict:
        """
        제안된 태그를 본인 노트에 병합합니다.

        기존 태그는 유지하고 새 태그만 추가하므로 데이터 손실이 없습니다.
        소유자가 아니거나 존재하지 않는 노트는 조용히 건너뛰고
        skipped_note_ids로 알려줍니다.

        Args:
            db: 데이터베이스 세션
            user: 현재 사용자 (소유자 검증에 사용)
            note_ids: 대상 노트 ID 목록
            tags: 추가할 태그 목록

        Returns:
            {"updated_note_ids", "skipped_note_ids", "applied_tags"}
        """
        requested = list(dict.fromkeys(note_ids))

        # 대상 ID가 비어 있으면 현재 사용자의 노트 전체에 적용합니다.
        if not requested:
            requested = GraphService.list_owned_note_ids(db, user)

        if not requested:
            return {
                "updated_note_ids": [],
                "skipped_note_ids": [],
                "applied_tags": list(tags),
            }

        notes = (
            db.query(Note)
            .filter(
                Note.id.in_(requested),
                Note.user_id == user.id,
                Note.deleted_at.is_(None),
            )
            .all()
        )

        found_ids = {note.id for note in notes}
        updated: List[int] = []

        for note in notes:
            existing = list(note.tags or [])
            merged = list(existing)

            for tag in tags:
                if tag not in merged:
                    merged.append(tag)

            # 실제로 늘어난 경우에만 UPDATE 발생
            if len(merged) != len(existing):
                # JSON 컬럼은 새 리스트를 할당해야 변경이 감지됩니다.
                note.tags = merged
                updated.append(note.id)

        if updated:
            db.commit()

        return {
            "updated_note_ids": updated,
            "skipped_note_ids": [nid for nid in requested if nid not in found_ids],
            "applied_tags": list(tags),
        }


# 서비스 싱글턴 - 라우터에서 import해 사용
graph_service = GraphService()
