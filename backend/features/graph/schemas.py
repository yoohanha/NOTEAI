"""
Graph 요청/응답 스키마

토픽 분석 API가 주고받는 데이터 구조를 정의합니다.
그래프는 Node/Edge 형태의 JSON으로 반환되어 프론트엔드
시각화 라이브러리(Cytoscape.js)가 그대로 소비할 수 있습니다.
"""

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

# 분석에 사용할 수 있는 데이터 소스
SourceKind = Literal["notes", "trends"]

# 그래프 노드 종류
NodeType = Literal["topic", "note", "trend", "keyword"]

# 그래프 엣지 관계
EdgeRelation = Literal["relevant", "tagged", "co_occurs"]


# ============ 요청 ============


class AnalyzeRequest(BaseModel):
    """
    토픽 분석 요청

    Example:
        {
            "topic": "transformer",
            "limit": 30,
            "sources": ["notes", "trends"],
            "max_keywords": 15
        }
    """

    topic: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="분석할 토픽/키워드",
    )
    limit: int = Field(
        30,
        ge=1,
        le=50,
        description="그래프에 포함할 최대 문헌 수 (렌더링 성능 상한)",
    )
    sources: List[SourceKind] = Field(
        default_factory=lambda: ["notes", "trends"],
        description="분석 대상 데이터 소스",
    )
    max_keywords: int = Field(
        15,
        ge=3,
        le=30,
        description="추출할 최대 키워드 수",
    )

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        """공백만 입력된 토픽을 거부하고 양끝 공백을 정리합니다."""
        stripped = value.strip()

        if not stripped:
            raise ValueError("토픽을 입력해 주세요")

        return stripped

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, value: List[str]) -> List[str]:
        """소스를 최소 1개 이상 지정했는지 확인하고 중복을 제거합니다."""
        unique = list(dict.fromkeys(value))

        if not unique:
            raise ValueError("분석할 데이터 소스를 최소 1개 선택해 주세요")

        return unique


class ApplyTagsRequest(BaseModel):
    """
    자동 태깅 적용 요청

    분석에서 제안된 태그를 지정한 노트에 병합합니다.
    기존 태그는 유지하고 새 태그만 추가합니다(덮어쓰기 없음).

    Example:
        {"note_ids": [3, 7], "tags": ["attention", "llm"]}
    """

    note_ids: List[int] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="태그를 적용할 노트 ID 목록",
    )
    tags: List[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="추가할 태그 목록",
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: List[str]) -> List[str]:
        """빈 태그를 제거하고 소문자로 정규화한 뒤 중복을 없앱니다."""
        cleaned = [tag.strip().lower() for tag in value if tag and tag.strip()]

        if not cleaned:
            raise ValueError("유효한 태그가 없습니다")

        return list(dict.fromkeys(cleaned))


# ============ 응답 ============


class GraphNode(BaseModel):
    """
    지식 그래프의 노드 하나

    Attributes:
        id: 고유 식별자 ("topic", "note:3", "trend:12", "kw:attention")
        label: 화면에 표시할 텍스트
        type: 노드 종류
        weight: 0~1 정규화 가중치 (노드 크기로 매핑)
        meta: url, source, category 등 표시용 부가 정보
    """

    id: str
    label: str
    type: NodeType
    weight: float = Field(0.5, ge=0.0, le=1.0)
    meta: Dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """
    지식 그래프의 간선 하나

    Attributes:
        source: 출발 노드 id
        target: 도착 노드 id
        relation: 관계 종류 (relevant/tagged/co_occurs)
        weight: 0~1 정규화 가중치 (선 두께로 매핑)
    """

    source: str
    target: str
    relation: EdgeRelation
    weight: float = Field(0.5, ge=0.0, le=1.0)


class GraphPayload(BaseModel):
    """노드와 간선을 담은 그래프 전체"""

    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


class KeywordItem(BaseModel):
    """추출된 키워드 하나"""

    word: str = Field(..., description="키워드")
    score: float = Field(..., description="0~1로 정규화된 TF-IDF 점수")
    doc_count: int = Field(..., description="이 키워드가 등장한 문헌 수")


class DocumentItem(BaseModel):
    """분석에 사용된 문헌 요약 정보"""

    id: str = Field(..., description="그래프 노드 id")
    ref_id: int = Field(..., description="원본 테이블의 기본키")
    type: NodeType = Field(..., description="note 또는 trend")
    title: str
    score: float = Field(..., description="토픽 관련도 (0~1 정규화)")
    snippet: str = Field("", description="본문 미리보기")
    url: Optional[str] = Field(None, description="원문 링크 (트렌드만)")
    source_name: Optional[str] = Field(None, description="출처명")
    tags: List[str] = Field(default_factory=list)
    published_at: Optional[datetime] = None


class AnalyzeResponse(BaseModel):
    """
    토픽 분석 결과

    Example:
        {
            "topic": "transformer",
            "summary": "트랜스포머는 attention 메커니즘을 ...",
            "document_count": 12,
            "keywords": [{"word": "attention", "score": 0.91, "doc_count": 7}],
            "suggested_tags": ["attention", "llm"],
            "documents": [...],
            "graph": {"nodes": [...], "edges": [...]},
            "analyzed_at": "2026-08-26T15:40:00"
        }
    """

    topic: str
    summary: str = Field("", description="추출 요약문")
    document_count: int = Field(0, description="분석에 사용된 문헌 수")
    keywords: List[KeywordItem] = Field(default_factory=list)
    suggested_tags: List[str] = Field(
        default_factory=list,
        description="자동 태깅에 쓸 수 있는 상위 키워드",
    )
    documents: List[DocumentItem] = Field(default_factory=list)
    graph: GraphPayload = Field(default_factory=GraphPayload)
    analyzed_at: datetime


class TopicSuggestion(BaseModel):
    """추천 토픽 하나"""

    topic: str
    doc_count: int = Field(..., description="이 토픽이 등장한 문헌 수")


class ApplyTagsResponse(BaseModel):
    """자동 태깅 적용 결과"""

    updated_note_ids: List[int] = Field(default_factory=list)
    skipped_note_ids: List[int] = Field(
        default_factory=list,
        description="존재하지 않거나 소유자가 아니라 건너뛴 노트",
    )
    applied_tags: List[str] = Field(default_factory=list)
