"""
NOTE_PAPER 이력 API

- GET    /api/vita                      논문/자격증/교육 경력 전체
- POST   /api/vita/publications         논문 추가
- DELETE /api/vita/publications/{id}    논문 삭제
- POST   /api/vita/certificates         자격증 추가
- DELETE /api/vita/certificates/{id}    자격증 삭제
- POST   /api/vita/teachings            교육 경력 추가
- DELETE /api/vita/teachings/{id}       교육 경력 삭제
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from features.auth.deps import get_current_admin, get_current_user
from features.auth.models import User
from features.vita.models import VitaCertificate, VitaPublication, VitaTeaching
from features.vita.schemas import (
    CertificateCreate,
    CertificateResponse,
    PublicationCreate,
    PublicationResponse,
    TeachingCreate,
    TeachingResponse,
)
from features.vita.service import vita_service

router = APIRouter(prefix="/vita", tags=["vita"])


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def _dump(schema, row) -> dict:
    data = schema.from_orm(row).dict()
    data["created_at"] = _iso(data.get("created_at"))
    return data


@router.get("", response_model=dict)
async def list_vita(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """현재 사용자의 이력 세 섹션을 반환합니다."""
    bundle = vita_service.list_all(db, current_user)
    data = {
        "publications": [_dump(PublicationResponse, row) for row in bundle["publications"]],
        "certificates": [_dump(CertificateResponse, row) for row in bundle["certificates"]],
        "teachings": [_dump(TeachingResponse, row) for row in bundle["teachings"]],
    }
    return {"status": 200, "data": data, "message": "이력 목록"}


@router.post("/publications", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_publication(
    payload: PublicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """논문 한 건을 추가합니다."""
    try:
        row = vita_service.add_publication(db, current_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"status": 201, "data": _dump(PublicationResponse, row), "message": "논문을 추가했습니다"}


@router.delete("/publications/{item_id}", response_model=dict)
async def delete_publication(
    item_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    """논문 삭제는 관리자만 할 수 있습니다."""
    if not vita_service.delete_owned(db, current_user, VitaPublication, item_id):
        raise HTTPException(status_code=404, detail="삭제할 논문을 찾을 수 없습니다")
    return {"status": 200, "data": {"id": item_id, "deleted": True}, "message": "논문을 삭제했습니다"}


@router.post("/certificates", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_certificate(
    payload: CertificateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """자격증 한 건을 추가합니다."""
    try:
        row = vita_service.add_certificate(db, current_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"status": 201, "data": _dump(CertificateResponse, row), "message": "자격증을 추가했습니다"}


@router.delete("/certificates/{item_id}", response_model=dict)
async def delete_certificate(
    item_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    """자격증 삭제는 관리자만 할 수 있습니다."""
    if not vita_service.delete_owned(db, current_user, VitaCertificate, item_id):
        raise HTTPException(status_code=404, detail="삭제할 자격증을 찾을 수 없습니다")
    return {"status": 200, "data": {"id": item_id, "deleted": True}, "message": "자격증을 삭제했습니다"}


@router.post("/teachings", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_teaching(
    payload: TeachingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """교육 경력 한 건을 추가합니다."""
    try:
        row = vita_service.add_teaching(db, current_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"status": 201, "data": _dump(TeachingResponse, row), "message": "교육 경력을 추가했습니다"}


@router.delete("/teachings/{item_id}", response_model=dict)
async def delete_teaching(
    item_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    """교육 경력 삭제는 관리자만 할 수 있습니다."""
    if not vita_service.delete_owned(db, current_user, VitaTeaching, item_id):
        raise HTTPException(status_code=404, detail="삭제할 교육 경력을 찾을 수 없습니다")
    return {"status": 200, "data": {"id": item_id, "deleted": True}, "message": "교육 경력을 삭제했습니다"}
