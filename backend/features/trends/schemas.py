"""
Trends 요청/응답 스키마
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TrendSourceInfo(BaseModel):
    """수집 소스 정보"""

    key: str = Field(..., description="소스 식별자")
    name: str = Field(..., description="소스 이름")
    url: str = Field(..., description="피드/API 주소")
    kind: str = Field("rss", description="rss 또는 newsapi")
    category: str = Field("tech", description="소스 분류")


class TrendItemResponse(BaseModel):
    """트렌드 항목 응답"""

    id: Optional[int] = Field(None, description="저장된 항목 ID")
    title: str = Field(..., description="제목")
    summary: str = Field("", description="요약")
    url: str = Field(..., description="원문 링크")
    source_key: str = Field(..., description="소스 식별자")
    source_name: Optional[str] = Field(None, description="소스 이름")
    category: Optional[str] = Field(None, description="분류")
    author: Optional[str] = Field(None, description="작성자")
    image_url: Optional[str] = Field(None, description="대표 이미지")
    tags: List[str] = Field(default_factory=list, description="태그")
    is_saved: bool = Field(False, description="노트로 저장했는지 여부")
    published_at: Optional[datetime] = Field(None, description="발행 시각")
    fetched_at: Optional[datetime] = Field(None, description="수집 시각")

    class Config:
        from_attributes = True


class RefreshRequest(BaseModel):
    """트렌드 수집(갱신) 요청"""

    sources: Optional[List[str]] = Field(
        None, description="수집할 소스 key 목록 (미지정 시 전체)"
    )
    keywords: Optional[List[str]] = Field(
        None, description="제목/요약에 포함되어야 하는 키워드 필터"
    )
    limit_per_source: int = Field(
        30, ge=1, le=100, description="소스당 최대 저장 항목 수"
    )
    persist: bool = Field(
        True, description="수집 결과를 DB에 저장할지 여부 (False면 조회만)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "sources": ["hackernews", "arxiv_ai"],
                "keywords": ["llm", "agent"],
                "limit_per_source": 20,
            }
        }


class RefreshResponse(BaseModel):
    """트렌드 수집 결과"""

    fetched: int = Field(0, description="외부에서 가져온 총 항목 수")
    saved: int = Field(0, description="새로 저장한 항목 수")
    duplicates: int = Field(0, description="이미 저장되어 있어 건너뛴 항목 수")
    sources_used: List[str] = Field(default_factory=list, description="사용한 소스 key")
    errors: List[str] = Field(default_factory=list, description="소스별 오류 메시지")
    items: List[TrendItemResponse] = Field(
        default_factory=list, description="수집된 항목"
    )


class TrendListResponse(BaseModel):
    """저장된 트렌드 목록 응답"""

    items: List[TrendItemResponse] = Field(default_factory=list)
    total: int = Field(0, description="전체 항목 수")
    page: int = Field(1, description="현재 페이지")
    limit: int = Field(20, description="페이지당 항목 수")


class SaveTrendRequest(BaseModel):
    """트렌드 항목을 노트로 저장하는 요청"""

    trend_id: int = Field(..., description="저장할 트렌드 항목 ID")
    category: Optional[str] = Field(None, description="노트 카테고리 (미지정 시 소스 분류)")
    extra_tags: Optional[List[str]] = Field(None, description="추가할 태그")
