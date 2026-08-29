"""
논문 검색 요청/응답 스키마
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PaperItem(BaseModel):
    """arXiv 논문 한 건"""

    arxiv_id: str = Field(..., description="arXiv 식별자 (예: 2312.12345)")
    title: str = Field(..., description="논문 제목")
    abstract: str = Field(..., description="초록")
    authors: List[str] = Field(default_factory=list, description="저자 목록")
    pdf_url: str = Field(..., description="PDF 링크")
    abs_url: str = Field(..., description="초록 페이지 링크")
    published_at: Optional[str] = Field(None, description="공개일 (ISO)")
    categories: List[str] = Field(default_factory=list, description="arXiv 분류")
    journal: Optional[str] = Field(None, description="저널/학회명 (없으면 arXiv preprint)")
    year: Optional[int] = Field(None, description="발행 연도")
    citation: str = Field("", description="번호 포함 참고문헌 한 줄")


class SearchPapersRequest(BaseModel):
    """논문 검색 요청"""

    query: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="검색어 (예: text-to-3d)",
    )
    limit: int = Field(8, ge=1, le=25, description="최대 결과 수")
    question: Optional[str] = Field(
        None,
        max_length=500,
        description="논문 초록을 근거로 답할 사용자 질문 (없으면 검색만)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "text-to-3d",
                "limit": 8,
                "question": "이 분야에서 가장 중요한 논문을 추천해 줘",
            }
        }
    )


class PaperInsight(BaseModel):
    """초록을 주입한 LLM(또는 로컬 폴백) 분석 결과"""

    answer: str = Field(..., description="질문에 대한 요약·추천 답변")
    provider: str = Field(..., description="llm 또는 local")
    prompt: str = Field(..., description="실제로 구성한 프롬프트 (디버깅/재사용)")


class SearchPapersResponse(BaseModel):
    """논문 검색 응답"""

    query: str = Field(..., description="정규화된 검색어")
    raw_query: str = Field(..., description="사용자가 보낸 원문")
    total: int = Field(0, description="반환된 논문 수")
    papers: List[PaperItem] = Field(default_factory=list)
    bibliography: List[str] = Field(
        default_factory=list,
        description="번호 매긴 참고문헌 목록",
    )
    insight: Optional[PaperInsight] = None
