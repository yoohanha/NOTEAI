"""
Trends API 엔드포인트
- 수집 소스 목록 조회
- 외부 소스에서 트렌드 수집(갱신)
- 저장된 트렌드 조회
- 트렌드를 노트로 저장
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from features.auth.deps import get_current_user
from features.auth.models import User
from features.trends.schemas import (
    RefreshRequest,
    RefreshResponse,
    SaveTrendRequest,
    TrendListResponse,
    TrendSourceInfo,
)
from features.trends.service import trend_service
from features.trends.sources import get_sources

# 라우터 생성
router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("/sources", response_model=dict)
async def list_sources(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    사용 가능한 트렌드 수집 소스 목록 조회

    Args:
        current_user: 현재 사용자

    Returns:
        소스 목록
    """
    sources = [
        TrendSourceInfo(
            key=source.key,
            name=source.name,
            url=source.url,
            kind=source.kind,
            category=source.category,
        ).model_dump()
        for source in get_sources()
    ]

    return {
        "status": 200,
        "data": {"sources": sources, "total": len(sources)},
        "message": f"{len(sources)}개 소스를 사용할 수 있습니다",
    }


@router.post("/refresh", response_model=dict)
async def refresh_trends(
    request: RefreshRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    외부 RSS/뉴스 API에서 최신 기술 트렌드를 수집

    개별 소스가 실패해도 나머지 소스 수집은 계속되며,
    실패 사유는 응답의 errors 배열에 담깁니다.

    Args:
        request: 수집 옵션 (소스/키워드/개수 제한)
        current_user: 현재 사용자
        db: 데이터베이스 세션

    Returns:
        수집 통계 및 새로 저장된 항목

    Raises:
        HTTPException: 저장 실패 시 500
    """
    try:
        result = await trend_service.refresh(db, request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"트렌드 수집 실패: {exc}",
        )

    return {
        "status": 200,
        "data": RefreshResponse(**result).model_dump(),
        "message": (
            f"{result['fetched']}건 수집, {result['saved']}건 저장, "
            f"{result['duplicates']}건 중복"
        ),
    }


@router.get("", response_model=dict)
async def list_trends(
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    source: Optional[str] = Query(None, description="소스 key 필터"),
    category: Optional[str] = Query(None, description="분류 필터"),
    search: Optional[str] = Query(None, description="제목 검색어"),
    days: Optional[int] = Query(None, ge=1, le=365, description="최근 N일 이내"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    저장된 트렌드 목록 조회 (최신순)

    Args:
        page: 페이지 번호
        limit: 페이지당 항목 수
        source: 소스 필터
        category: 분류 필터
        search: 제목 검색어
        days: 최근 N일 이내 항목만
        current_user: 현재 사용자
        db: 데이터베이스 세션

    Returns:
        트렌드 목록과 페이지 정보
    """
    skip = (page - 1) * limit

    items, total = trend_service.list_trends(
        db,
        skip=skip,
        limit=limit,
        source_key=source,
        category=category,
        search=search,
        days=days,
    )

    return {
        "status": 200,
        "data": TrendListResponse(
            items=items, total=total, page=page, limit=limit
        ).model_dump(),
        "message": f"{total}건 중 {len(items)}건 조회",
    }


@router.post("/save", response_model=dict)
async def save_trend_as_note(
    request: SaveTrendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    트렌드 항목을 내 노트로 저장

    Args:
        request: 저장할 트렌드 ID와 옵션
        current_user: 노트 소유자
        db: 데이터베이스 세션

    Returns:
        생성된 노트 정보

    Raises:
        HTTPException: 항목이 없으면 404, 저장 실패 시 500
    """
    trend = trend_service.get_trend(db, request.trend_id)

    if trend is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"트렌드 항목을 찾을 수 없습니다: id={request.trend_id}",
        )

    try:
        note = trend_service.save_as_note(
            db,
            trend,
            current_user,
            category=request.category,
            extra_tags=request.extra_tags,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"노트 저장 실패: {exc}",
        )

    return {
        "status": 200,
        "data": {
            "note_id": note.id,
            "title": note.title,
            "category": note.category,
            "tags": note.tags,
        },
        "message": "트렌드를 노트로 저장했습니다",
    }
