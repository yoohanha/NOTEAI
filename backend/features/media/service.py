"""
NOTE_3D 미디어 저장/조회/삭제

파일 본문은 uploads/media/{user_id}/ 아래에 두고,
DB에는 목록 표시용 메타데이터만 남깁니다.
"""

import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy.orm import Session

from core.config import settings
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


def _media_root() -> Path:
    """업로드 루트를 절대 경로로 만듭니다."""
    upload_dir = Path(settings.UPLOAD_DIR)
    if not upload_dir.is_absolute():
        upload_dir = Path(__file__).resolve().parents[2] / upload_dir
    root = upload_dir / "media"
    root.mkdir(parents=True, exist_ok=True)
    return root


def user_dir(user_id: int) -> Path:
    path = _media_root() / str(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def classify_file(filename: str, content_type: Optional[str]) -> Tuple[str, str, str]:
    """
    확장자로 종류와 MIME을 결정합니다.

    Returns:
        (확장자, kind, mime_type)

    Raises:
        ValueError: 허용되지 않은 형식
    """
    suffix = Path(filename or "").suffix.lower()
    if suffix not in ALLOWED_TYPES:
        raise ValueError("이미지(PNG, JPG, WEBP, GIF) 또는 동영상(MP4, WEBM, MOV)만 올릴 수 있습니다.")

    kind = "image" if suffix in IMAGE_TYPES else "video"
    mime = ALLOWED_TYPES[suffix]
    declared = (content_type or "").split(";")[0].strip().lower()
    if declared and declared != "application/octet-stream" and not declared.startswith(kind):
        # 선언 MIME이 종류와 완전히 다르면 거부 (예: .png + text/plain)
        if declared not in ALLOWED_TYPES.values():
            raise ValueError("파일 형식이 허용 목록과 맞지 않습니다.")

    return suffix, kind, mime


class MediaService:
    """미디어 자산 CRUD"""

    @staticmethod
    async def save_upload(db: Session, user: User, file: UploadFile) -> MediaAsset:
        """
        업로드 파일을 검증한 뒤 디스크와 DB에 저장합니다.
        """
        suffix, kind, mime = classify_file(file.filename, file.content_type)
        payload = await file.read()
        max_size = getattr(settings, "MEDIA_MAX_UPLOAD_SIZE", 40 * 1024 * 1024)

        if not payload:
            raise ValueError("빈 파일은 올릴 수 없습니다.")
        if len(payload) > max_size:
            raise ValueError("파일이 너무 큽니다. 40MB 이하만 올릴 수 있습니다.")

        stored_name = f"{uuid.uuid4().hex}{suffix}"
        dest = user_dir(user.id) / stored_name
        dest.write_bytes(payload)

        asset = MediaAsset(
            user_id=user.id,
            original_name=(file.filename or f"untitled{suffix}")[:255],
            stored_name=stored_name,
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
    def file_path(user: User, asset: MediaAsset) -> Path:
        return user_dir(user.id) / asset.stored_name

    @staticmethod
    def delete_asset(db: Session, user: User, asset_id: int) -> bool:
        """소유한 미디어를 DB와 디스크에서 삭제합니다."""
        asset = MediaService.get_owned(db, user, asset_id)
        if not asset:
            return False

        path = MediaService.file_path(user, asset)
        if path.exists():
            path.unlink()

        db.delete(asset)
        db.commit()
        return True


media_service = MediaService()
