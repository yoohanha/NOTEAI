"""
논문 검색 비즈니스 로직
- 일반 검색어 및 (하위 호환) /mycode (검색어) 파싱
- arXiv 검색 + (선택) 초록 기반 인사이트
"""

import re
from typing import Optional

from features.papers.client import attach_citations, search_arxiv
from features.papers.llm import generate_insight
from features.papers.schemas import SearchPapersResponse

# 예전 UI가 쓰던 접두사. 지금은 선택이며, 있으면 괄호 안만 꺼냅니다.
_COMMAND_RE = re.compile(
    r"^\s*/mycode\s*\(\s*(.+)\s*\)\s*$",
    re.IGNORECASE | re.DOTALL,
)
_TOPIC_KEEP_RE = re.compile(r"[^\w\s.+#\-]", re.UNICODE)


class PaperQueryError(ValueError):
    """검색어가 비어 있음"""


def extract_topic(raw: str) -> str:
    """
    사용자 입력에서 실제 검색어를 꺼냅니다.

    일반 키워드(text-to-3d)를 그대로 쓰고,
    예전 `/mycode (검색어)` 형식도 괄호 안만 추출합니다.

    Args:
        raw: 원문 검색어

    Returns:
        정규화된 토픽 문자열

    Raises:
        PaperQueryError: 검색어가 비어 있는 경우
    """
    text = (raw or "").strip()

    if not text:
        raise PaperQueryError("검색어를 입력하세요. 예: text-to-3d")

    match = _COMMAND_RE.fullmatch(text)
    if match:
        topic = _normalize_topic(match.group(1))
        if not topic:
            raise PaperQueryError("검색어를 입력하세요. 예: text-to-3d")
        return topic

    if text.lower().startswith("/mycode"):
        rest = text[7:].strip().strip("()")
        topic = _normalize_topic(rest)
        if not topic:
            raise PaperQueryError("검색어를 입력하세요. 예: text-to-3d")
        return topic

    topic = _normalize_topic(text)
    if not topic:
        raise PaperQueryError("검색어를 입력하세요. 예: text-to-3d")
    return topic


def _normalize_topic(raw: str) -> str:
    """
    검색어의 공백을 정리하고, 하이픈(-)은 그대로 남깁니다.
    """
    text = " ".join((raw or "").split())
    # 제어문자만 제거하고 하이픈·점·샵은 유지
    text = _TOPIC_KEEP_RE.sub(" ", text)
    return " ".join(text.split())


class PaperService:
    """논문 검색 서비스"""

    async def search(
        self,
        raw_query: str,
        limit: int = 8,
        question: Optional[str] = None,
        with_insight: bool = True,
    ) -> SearchPapersResponse:
        """
        arXiv에서 논문을 검색하고, 질문이 있으면 초록 기반 답변을 붙입니다.

        Args:
            raw_query: 사용자 입력
            limit: 최대 결과 수
            question: LLM에 넘길 질문
            with_insight: False면 검색만 수행

        Returns:
            SearchPapersResponse
        """
        topic = extract_topic(raw_query)
        papers = attach_citations(await search_arxiv(topic, limit=limit))
        bibliography = [paper.citation for paper in papers if paper.citation]

        insight = None
        if with_insight and papers:
            insight = await generate_insight(topic, papers, question)

        return SearchPapersResponse(
            query=topic,
            raw_query=raw_query.strip(),
            total=len(papers),
            papers=papers,
            bibliography=bibliography,
            insight=insight,
        )


paper_service = PaperService()
