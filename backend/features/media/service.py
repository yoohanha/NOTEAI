"""
NOTE_3D 미디어 저장/조회/삭제

파일 본문은 Cloudinary에 올리고 DB에는 secure_url을 저장합니다.
Cloudinary 키가 없으면 개발용으로 로컬 디스크에 폴백합니다.
"""

from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy.orm import Session

from core.config import settings
from core.storage import delete_stored, local_file_path, upload_bytes
from features.auth.models import User
from features.media.models import MediaAsset

# 허용 확장자와 MIME
IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
VIDEO_TYPES = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
}
ALLOWED_TYPES = {**IMAGE_TYPES, **VIDEO_TYPES}


def classify_file(filename: str, content_type: Optional[str]) -> Tuple[str, str, str]:
    """
    확장자로 종류와 MIME을 결정합니다.

    Returns:
        (확장자, kind, mime_type)
    """
    suffix = Path(filename or "").suffix.lower()
    if suffix not in ALLOWED_TYPES:
        raise ValueError("이미지(PNG, JPG, WEBP, GIF) 또는 동영상(MP4, WEBM, MOV)만 올릴 수 있습니다.")

    kind = "image" if suffix in IMAGE_TYPES else "video"
    mime = ALLOWED_TYPES[suffix]
    declared = (content_type or "").split(";")[0].strip().lower()
    if declared and declared != "application/octet-stream" and not declared.startswith(kind):
        if declared not in ALLOWED_TYPES.values():
            raise ValueError("파일 형식이 허용 목록과 맞지 않습니다.")

    return suffix, kind, mime


class MediaService:
    """미디어 자산 CRUD"""

    @staticmethod
    async def save_upload(db: Session, user: User, file: UploadFile) -> MediaAsset:
        """업로드 파일을 검증한 뒤 Cloudinary(또는 로컬)와 DB에 저장합니다."""
        suffix, kind, mime = classify_file(file.filename, file.content_type)
        payload = await file.read()
        max_size = getattr(settings, "MEDIA_MAX_UPLOAD_SIZE", 40 * 1024 * 1024)

        if not payload:
            raise ValueError("빈 파일은 올릴 수 없습니다.")
        if len(payload) > max_size:
            raise ValueError("파일이 너무 큽니다. 40MB 이하만 올릴 수 있습니다.")

        stored = upload_bytes(
            payload,
            folder=f"noteai/media/{user.id}",
            resource_type="video" if kind == "video" else "image",
            filename=file.filename or f"untitled{suffix}",
        )

        asset = MediaAsset(
            user_id=user.id,
            original_name=(file.filename or f"untitled{suffix}")[:255],
            stored_name=stored["public_id"][:255],
            public_url=(stored.get("url") or "")[:1024],
            cloudinary_id=stored["public_id"][:255] if stored.get("storage") == "cloudinary" else "",
            mime_type=mime,
            kind=kind,
            size_bytes=len(payload),
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset

    @staticmethod
    def list_assets(db: Session, user: User) -> List[MediaAsset]:
        """현재 사용자의 미디어를 최신순으로 반환합니다."""
        return (
            db.query(MediaAsset)
            .filter(MediaAsset.user_id == user.id)
            .order_by(MediaAsset.created_at.desc())
            .all()
        )

    @staticmethod
    def get_owned(db: Session, user: User, asset_id: int) -> Optional[MediaAsset]:
        return (
            db.query(MediaAsset)
            .filter(MediaAsset.id == asset_id, MediaAsset.user_id == user.id)
            .first()
        )

    @staticmethod
    def file_path(asset: MediaAsset) -> Optional[Path]:
        """로컬 폴백 파일이 있으면 경로를 반환합니다."""
        if getattr(asset, "public_url", ""):
            return None
        return local_file_path(asset.stored_name)

    @staticmethod
    def delete_asset(db: Session, user: User, asset_id: int) -> bool:
        """소유한 미디어를 DB와 클라우드/디스크에서 삭제합니다."""
        asset = MediaService.get_owned(db, user, asset_id)
        if not asset:
            return False

        resource_type = "video" if asset.kind == "video" else "image"
        delete_stored(asset.cloudinary_id or asset.stored_name, resource_type)

        db.delete(asset)
        db.commit()
        return True


media_service = MediaService()
