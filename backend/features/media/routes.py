"""
NOTE_3D 미디어 API

- GET    /api/media            내 미디어 목록
- POST   /api/media            이미지/동영상 업로드
- GET    /api/media/{id}/file  파일 본문
- DELETE /api/media/{id}       삭제
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from core.database import get_db
from features.auth.deps import get_current_admin, get_current_user
from features.auth.models import User
from features.media.schemas import MediaAssetResponse
from features.media.service import media_service

router = APIRouter(prefix="/media", tags=["media"])


def _to_dict(asset) -> dict:
    data = MediaAssetResponse.from_orm(asset).dict()
    created = data.get("created_at")
    if hasattr(created, "isoformat"):
        data["created_at"] = created.isoformat()
    return data


@router.get("", response_model=dict)
async def list_media(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """현재 사용자가 올린 NOTE_3D 미디어 목록"""
    items = media_service.list_assets(db, current_user)
    return {
        "status": 200,
        "data": {"items": [_to_dict(item) for item in items], "total": len(items)},
        "message": f"{len(items)}건의 미디어",
    }


@router.post("", status_code=status.HTTP_201_CREATED, response_model=dict)
async def upload_media(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """이미지 또는 동영상을 업로드합니다."""
    try:
        asset = await media_service.save_upload(db, current_user, file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return {
        "status": 201,
        "data": _to_dict(asset),
        "message": "파일을 올렸습니다",
    }


@router.get("/{asset_id}/file")
async def download_media(
    asset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """소유한 미디어 파일 본문 또는 클라우드 주소로 보냅니다."""
    asset = media_service.get_owned(db, current_user, asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="파일을 찾을 수 없습니다")

    if getattr(asset, "public_url", ""):
        return RedirectResponse(asset.public_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    path = media_service.file_path(asset)
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="저장된 파일이 없습니다")

    return FileResponse(
        path,
        media_type=asset.mime_type,
        filename=asset.original_name,
    )


@router.delete("/{asset_id}", response_model=dict)
async def delete_media(
    asset_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    """미디어 삭제는 관리자만 할 수 있습니다."""
    deleted = media_service.delete_asset(db, current_user, asset_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="삭제할 파일을 찾을 수 없습니다",
        )

    return {
        "status": 200,
        "data": {"id": asset_id, "deleted": True},
        "message": "파일을 삭제했습니다",
    }
