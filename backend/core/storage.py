"""
클라우드 파일 저장소 (Cloudinary)

Render처럼 디스크가 휘발성인 환경에서는 업로드를 Cloudinary에 두고
DB에는 secure_url만 저장합니다. 키가 없으면 개발/테스트용으로
로컬 uploads/ 폴백을 씁니다.
"""

import uuid
from pathlib import Path
from typing import Optional

from core.config import settings


def is_cloudinary_configured() -> bool:
    """Cloudinary 세 값이 모두 있으면 클라우드에 올립니다."""
    return bool(
        (getattr(settings, "CLOUDINARY_CLOUD_NAME", "") or "").strip()
        and (getattr(settings, "CLOUDINARY_API_KEY", "") or "").strip()
        and (getattr(settings, "CLOUDINARY_API_SECRET", "") or "").strip()
    )


def _configure() -> None:
    import cloudinary

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME.strip(),
        api_key=settings.CLOUDINARY_API_KEY.strip(),
        api_secret=settings.CLOUDINARY_API_SECRET.strip(),
        secure=True,
    )


def _upload_root() -> Path:
    upload_dir = Path(settings.UPLOAD_DIR)
    if not upload_dir.is_absolute():
        upload_dir = Path(__file__).resolve().parents[1] / upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def upload_bytes(
    payload: bytes,
    *,
    folder: str,
    resource_type: str,
    filename: str,
) -> dict:
    """
    파일을 Cloudinary(또는 로컬 폴백)에 올리고 메타데이터를 반환합니다.

    Returns:
        url, public_id, storage, resource_type
    """
    suffix = Path(filename or "").suffix.lower() or ""
    public_id = uuid.uuid4().hex

    if is_cloudinary_configured():
        return _upload_cloudinary(
            payload,
            folder=folder,
            resource_type=resource_type,
            public_id=public_id,
            filename=filename,
        )

    dest_dir = _upload_root() / folder
    dest_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{public_id}{suffix}"
    dest = dest_dir / stored_name
    dest.write_bytes(payload)
    return {
        "url": "",
        "public_id": f"{folder}/{stored_name}",
        "storage": "local",
        "resource_type": resource_type,
        "local_path": str(dest),
    }


def _upload_cloudinary(
    payload: bytes,
    *,
    folder: str,
    resource_type: str,
    public_id: str,
    filename: str,
) -> dict:
    """Cloudinary signed upload. 실패하면 사용자에게 읽히는 오류로 바꿉니다."""
    import cloudinary.uploader

    _configure()
    try:
        result = cloudinary.uploader.upload(
            payload,
            folder=folder,
            public_id=public_id,
            resource_type=resource_type,
            original_filename=filename,
            use_filename=False,
            unique_filename=False,
            overwrite=False,
        )
    except Exception as exc:
        raise ValueError(f"클라우드 업로드에 실패했습니다: {exc}") from exc

    url = result.get("secure_url") or result.get("url") or ""
    if not url:
        raise ValueError("클라우드가 파일 주소를 돌려주지 않았습니다.")

    return {
        "url": url,
        "public_id": result.get("public_id") or f"{folder}/{public_id}",
        "storage": "cloudinary",
        "resource_type": result.get("resource_type") or resource_type,
    }


def delete_stored(public_id: Optional[str], resource_type: str = "image") -> None:
    """클라우드 객체와 로컬 폴백 파일을 가능하면 지웁니다."""
    if not public_id:
        return

    if is_cloudinary_configured() and "/" in public_id and not Path(public_id).is_file():
        try:
            import cloudinary.uploader

            _configure()
            cloudinary.uploader.destroy(
                public_id,
                resource_type=resource_type,
                invalidate=True,
            )
        except Exception:
            pass

    local = _upload_root() / public_id
    if local.exists() and local.is_file():
        local.unlink()
