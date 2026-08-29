"""
논문 검색 API

- GET  /api/search-papers?q=text-to-3d
- POST /api/search-papers  { "query": "Gaussian Splatting", "question": "..." }
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from features.auth.deps import get_current_user
from features.auth.models import User
from features.papers.client import ArxivFetchError
from features.papers.schemas import SearchPapersRequest, SearchPapersResponse
from features.papers.service import PaperQueryError, paper_service

router = APIRouter(tags=["papers"])


def _error(status_code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


async def _run_search(
    raw_query: str,
    limit: int,
    question: Optional[str],
) -> dict:
    try:
        result: SearchPapersResponse = await paper_service.search(
            raw_query=raw_query,
            limit=limit,
            question=question,
            with_insight=True,
        )
    except PaperQueryError as exc:
        raise _error(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except ArxivFetchError as exc:
        raise _error(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    except Exception as exc:
        raise _error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"논문 검색 실패: {exc}",
        ) from exc

    return {
        "status": 200,
        "data": result.model_dump(mode="json"),
        "message": f"'{result.query}' 관련 논문 {result.total}편을 찾았습니다",
    }


@router.get("/search-papers")
async def search_papers_get(
    q: str = Query(..., min_length=1, max_length=200, description="검색어 (예: text-to-3d)"),
    limit: int = Query(8, ge=1, le=25),
    question: Optional[str] = Query(None, max_length=500),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    arXiv에서 논문을 실시간 검색합니다. (GET)

    요청 예시:
        GET /api/search-papers?q=text-to-3d&limit=8

    응답 data.papers[].title / abstract / authors / pdf_url
    """
    return await _run_search(q, limit, question)


@router.post("/search-papers")
async def search_papers_post(
    request: SearchPapersRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    arXiv에서 논문을 실시간 검색하고 초록 기반 요약을 붙입니다. (POST)

    요청 예시:
        {
            "query": "text-to-3d",
            "limit": 8,
            "question": "먼저 읽으면 좋은 논문을 추천해 줘"
        }
    """
    return await _run_search(request.query, request.limit, request.question)
