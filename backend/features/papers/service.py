"""
논문 검색 비즈니스 로직
- /mycode (검색어) 형식 검증
- arXiv 검색 + (선택) 초록 기반 인사이트
"""

import re
from typing import Optional

from features.papers.client import search_arxiv
from features.papers.llm import generate_insight
from features.papers.schemas import SearchPapersResponse

# 예: /mycode (Text-to-3D)  — 하이픈·공백·괄호를 포함한 검색어
# 탐욕 매칭으로 마지막 ')' 까지 잡아 CLIP (vision) 같은 내부 괄호도 허용합니다.
_COMMAND_RE = re.compile(
    r"^\s*/mycode\s*\(\s*(.+)\s*\)\s*$",
    re.IGNORECASE | re.DOTALL,
)
_TOPIC_KEEP_RE = re.compile(r"[^\w\s.+#\-]", re.UNICODE)


class PaperQueryError(ValueError):
    """검색 명령 형식이 올바르지 않음"""


def extract_topic(raw: str) -> str:
    """
    사용자 입력에서 실제 검색어를 꺼냅니다.

    권장 형식은 `/mycode (Text-to-3D)` 입니다.
    `/mycode`로 시작했는데 괄호 형식이 아니면 시스템 오류로 처리합니다.
    일반 검색어만 온 경우에는 API 호환을 위해 그대로 사용합니다.

    Args:
        raw: 원문 검색어

    Returns:
        정규화된 토픽 문자열

    Raises:
        PaperQueryError: 비었거나 /mycode 형식이 잘못된 경우
    """
    text = (raw or "").strip()

    if not text:
        raise PaperQueryError(
            "검색어가 비어 있습니다. /mycode (검색어) 형식으로 입력하세요."
        )

    match = _COMMAND_RE.fullmatch(text)
    if match:
        topic = _normalize_topic(match.group(1))
        if not topic:
            raise PaperQueryError(
                "괄호 안에 검색어가 없습니다. 예: /mycode (Text-to-3D)"
            )
        return topic

    if text.lower().startswith("/mycode"):
        raise PaperQueryError(
            "명령 형식이 올바르지 않습니다. /mycode (검색어) 형태로 입력하세요."
        )

    topic = _normalize_topic(text)
    if not topic:
        raise PaperQueryError(
            "검색어가 비어 있습니다. /mycode (검색어) 형식으로 입력하세요."
        )
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
        papers = await search_arxiv(topic, limit=limit)

        insight = None
        if with_insight and papers:
            insight = await generate_insight(topic, papers, question)

        return SearchPapersResponse(
            query=topic,
            raw_query=raw_query.strip(),
            total=len(papers),
            papers=papers,
            insight=insight,
        )


paper_service = PaperService()
