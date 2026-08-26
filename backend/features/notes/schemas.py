"""
노트 관련 Pydantic 스키마
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class NoteCreate(BaseModel):
    """노트 생성 요청"""

    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    category: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = Field(default_factory=list, max_items=10)
    is_public: bool = False


class NoteUpdate(BaseModel):
    """노트 수정 요청"""

    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    category: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None


class NoteResponse(BaseModel):
    """노트 응답"""

    id: int
    user_id: int
    title: str
    content: str
    category: Optional[str]
    tags: List[str]
    is_public: bool
    view_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NoteSummary(BaseModel):
    """노트 요약 정보"""

    id: int
    title: str
    content: str  # 처음 200자만 반환
    category: Optional[str]
    tags: List[str]
    view_count: int
    created_at: datetime


class AISummaryResponse(BaseModel):
    """AI 요약 응답"""

    summary_text: str
    keywords: List[dict]  # [{"word": "ai", "weight": 0.95}]
    category: Optional[str]
    generated_at: datetime

    class Config:
        from_attributes = True


class SummarizeRequest(BaseModel):
    """자동 요약 요청"""

    length: str = Field(default="medium", pattern="^(short|medium|long)$")


class KeywordResponse(BaseModel):
    """키워드 추출 응답"""

    keywords: List[dict]  # [{"word": "key", "weight": 0.95}]


class ClassifyResponse(BaseModel):
    """자동 분류 응답"""

    categories: List[dict]  # [{"name": "Research", "confidence": 0.92}]


class SearchRequest(BaseModel):
    """검색 요청"""

    query: str = Field(..., min_length=1)
    category: Optional[str] = None
    tag: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


class SemanticSearchRequest(BaseModel):
    """시맨틱 검색 요청"""

    query: str = Field(..., min_length=1)
    limit: int = Field(default=10, le=50)
