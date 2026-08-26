"""
노트 API 엔드포인트
- CRUD 작업
- 검색
- 버전 관리
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from core.database import get_db
from features.auth.models import User
from features.auth.deps import get_current_user, get_current_user_optional
from features.notes.models import Note
from features.notes.schemas import (
    NoteCreate,
    NoteUpdate,
    NoteResponse,
    SummarizeRequest,
)
from features.notes.service import note_service
from typing import Optional

# 라우터 생성
router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("", response_model=dict)
async def get_notes(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    category: Optional[str] = None,
    tag: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    사용자의 노트 목록 조회

    Args:
        page: 페이지 번호
        limit: 페이지당 아이템 수
        category: 카테고리 필터
        tag: 태그 필터
        current_user: 현재 사용자
        db: 데이터베이스 세션

    Returns:
        노트 리스트
    """
    skip = (page - 1) * limit
    notes, total = note_service.get_user_notes(
        db,
        current_user,
        skip=skip,
        limit=limit,
        category=category,
        tag=tag
    )

    return {
        "status": 200,
        "data": {
            "notes": [NoteResponse.from_orm(note).dict() for note in notes],
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": (total + limit - 1) // limit,
            },
        },
        "message": "Notes retrieved",
    }


@router.post("", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_note(
    note_data: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    새 노트 생성

    Args:
        note_data: 노트 정보
        current_user: 현재 사용자
        db: 데이터베이스 세션

    Returns:
        생성된 노트
    """
    note = note_service.create_note(db, note_data, current_user)

    return {
        "status": 201,
        "data": NoteResponse.from_orm(note).dict(),
        "message": "Note created successfully",
    }


@router.get("/{note_id}", response_model=dict)
async def get_note(
    note_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> dict:
    """
    특정 노트 조회

    공개 노트는 비로그인 사용자도 조회할 수 있습니다.
    인증 필수 의존성을 쓰면 헤더가 없을 때 403이 나므로
    get_current_user_optional을 사용합니다.

    Args:
        note_id: 노트 ID
        current_user: 현재 사용자 (선택)
        db: 데이터베이스 세션

    Returns:
        노트 정보
    """
    note = note_service.get_note(db, note_id, current_user)

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    return {
        "status": 200,
        "data": NoteResponse.from_orm(note).dict(),
        "message": "Note retrieved",
    }


@router.put("/{note_id}", response_model=dict)
async def update_note(
    note_id: int,
    note_data: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    노트 수정 (작성자만 가능)

    Args:
        note_id: 노트 ID
        note_data: 수정 정보
        current_user: 현재 사용자
        db: 데이터베이스 세션

    Returns:
        수정된 노트
    """
    note = note_service.update_note(db, note_id, note_data, current_user)

    if not note:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this note",
        )

    return {
        "status": 200,
        "data": NoteResponse.from_orm(note).dict(),
        "message": "Note updated successfully",
    }


@router.delete("/{note_id}", response_model=dict)
async def delete_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    노트 삭제 (작성자만 가능)

    Args:
        note_id: 노트 ID
        current_user: 현재 사용자
        db: 데이터베이스 세션

    Returns:
        성공 메시지
    """
    success = note_service.delete_note(db, note_id, current_user)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this note",
        )

    return {
        "status": 200,
        "message": "Note deleted successfully",
    }


@router.get("/search/q", response_model=dict)
async def search_notes(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    노트 검색

    Args:
        q: 검색어
        page: 페이지 번호
        limit: 페이지당 아이템 수
        current_user: 현재 사용자
        db: 데이터베이스 세션

    Returns:
        검색 결과
    """
    skip = (page - 1) * limit
    notes, total = note_service.search_notes(
        db,
        q,
        user=current_user,
        skip=skip,
        limit=limit
    )

    return {
        "status": 200,
        "data": {
            "notes": [NoteResponse.from_orm(note).dict() for note in notes],
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
            },
        },
        "message": "Search completed",
    }


@router.post("/{note_id}/summarize", response_model=dict)
async def summarize_note(
    note_id: int,
    summarize_req: SummarizeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    노트 자동 요약 (AI)

    Args:
        note_id: 노트 ID
        summarize_req: 요약 요청
        current_user: 현재 사용자
        db: 데이터베이스 세션

    Returns:
        요약 결과
    """
    note = note_service.get_note(db, note_id, current_user)

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    # AI 요약 (현재는 더미 구현)
    summary = {
        "summary_text": note.content[:200] + "...",  # 간단한 요약 (실제로는 AI 모델 사용)
        "generated_at": datetime.utcnow(),
    }

    return {
        "status": 200,
        "data": summary,
        "message": "Summary generated",
    }


from datetime import datetime
