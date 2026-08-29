"""
논문 초록을 LLM 컨텍스트에 주입하는 프롬프트 계층

LLM_API_KEY가 있으면 OpenAI 호환 Chat Completions를 호출하고,
키가 없으면 기존 그래프 분석기(추출 요약)로 폴백합니다.
"""

from typing import List, Optional

import httpx

from core.config import settings
from features.graph.analyzer import (
    SourceDocument,
    extract_keywords,
    score_documents,
    summarize,
)
from features.papers.schemas import PaperInsight, PaperItem

SYSTEM_PROMPT = (
    "당신은 NOTEAI의 학술 연구 어시스턴트입니다. "
    "아래에 제공된 논문 초록만을 근거로 사용자의 질문에 답하세요. "
    "초록에 없는 사실은 추측하지 말고, 추천할 때는 논문 제목을 명시하세요. "
    "한국어로 간결하게 답하세요."
)


def build_paper_context(papers: List[PaperItem]) -> str:
    """논문 목록을 LLM에 넣을 컨텍스트 문자열로 만듭니다."""
    blocks = []

    for index, paper in enumerate(papers, start=1):
        authors = ", ".join(paper.authors) if paper.authors else "저자 미상"
        blocks.append(
            f"[{index}] Title: {paper.title}\n"
            f"Authors: {authors}\n"
            f"Citation: {paper.citation or paper.title}\n"
            f"PDF: {paper.pdf_url}\n"
            f"Abstract: {paper.abstract}"
        )

    return "\n\n".join(blocks)


def build_user_prompt(query: str, question: str, context: str) -> str:
    """검색어·질문·초록 컨텍스트를 하나의 사용자 메시지로 묶습니다."""
    return (
        f"검색어: {query}\n"
        f"사용자 질문: {question}\n\n"
        f"--- 논문 초록 컨텍스트 ---\n{context}\n--- 끝 ---"
    )


def _local_insight(query: str, question: str, papers: List[PaperItem], prompt: str) -> PaperInsight:
    """
    LLM 키가 없을 때 쓰는 추출 요약 폴백입니다.

    그래프 분석기와 같은 TF-IDF 추출 요약을 써서
    외부 모델 없이도 추천 문장을 만듭니다.
    """
    documents = [
        SourceDocument(
            id=f"arxiv:{paper.arxiv_id}",
            doc_type="trend",
            title=paper.title,
            body=paper.abstract,
            tags=paper.categories,
            meta={"url": paper.pdf_url},
        )
        for paper in papers
    ]
    topic = f"{query} {question}".strip()
    scored = score_documents(topic, documents)
    keywords = extract_keywords(scored, top_n=8)
    summary = summarize(scored, keywords, max_sentences=4)

    top = scored[:3]
    rec_lines = []
    for item in top:
        rec_lines.append(f"- {item.source.title}")

    answer_parts = [
        f"검색어 '{query}' 관련 논문 {len(papers)}편을 바탕으로 정리했습니다.",
    ]
    if summary:
        answer_parts.append(summary)
    if rec_lines:
        answer_parts.append("추천 논문:\n" + "\n".join(rec_lines))
    if not summary and not rec_lines:
        answer_parts.append("초록에서 추천할 문장을 충분히 찾지 못했습니다.")

    return PaperInsight(
        answer="\n\n".join(answer_parts),
        provider="local",
        prompt=prompt,
    )


async def generate_insight(
    query: str,
    papers: List[PaperItem],
    question: Optional[str] = None,
) -> PaperInsight:
    """
    초록을 프롬프트에 주입해 요약·추천을 생성합니다.

    Args:
        query: 정규화된 검색어
        papers: 검색된 논문
        question: 사용자 질문 (없으면 기본 추천 질문 사용)

    Returns:
        PaperInsight
    """
    asked = (question or "").strip() or (
        f"'{query}' 분야의 핵심 흐름을 요약하고, 먼저 읽으면 좋은 논문을 추천해 주세요."
    )
    context = build_paper_context(papers)
    prompt = build_user_prompt(query, asked, context)

    api_key = (getattr(settings, "LLM_API_KEY", "") or "").strip()
    if not api_key or not papers:
        return _local_insight(query, asked, papers, prompt)

    base = (getattr(settings, "LLM_API_BASE", "") or "https://api.openai.com/v1").rstrip("/")
    model = getattr(settings, "LLM_MODEL", "") or "gpt-4o-mini"
    url = f"{base}/chat/completions"

    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        answer = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not answer:
            return _local_insight(query, asked, papers, prompt)
        return PaperInsight(answer=answer, provider="llm", prompt=prompt)
    except Exception:
        # 외부 LLM 실패 시에도 검색 결과는 보여 주도록 폴백
        return _local_insight(query, asked, papers, prompt)
