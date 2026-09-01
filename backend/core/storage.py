"""
클라우드 파일 저장소 (Cloudinary)

Render처럼 디스크가 휘발성인 환경에서는 업로드를 Cloudinary에 두고
DB에는 secure_url만 저장합니다. 키가 없으면 개발/테스트용으로
로컬 uploads/ 폴백을 씁니다. 호스팅에서는 폴백을 허용하지 않습니다.
"""

import os
import uuid
from io import BytesIO
from pathlib import Path
from typing import Optional

from core.config import settings


def is_hosted_runtime() -> bool:
    """Render / Railway / Fly 등 디스크가 휘발성인 호스팅인지 확인합니다."""
    return bool(
        os.environ.get("RENDER")
        or os.environ.get("RAILWAY_ENVIRONMENT")
        or os.environ.get("FLY_APP_NAME")
    )


def is_cloudinary_configured() -> bool:
    """Cloudinary 세 값이 모두 있으면 클라우드에 올립니다."""
    return bool(_cloudinary_value("CLOUDINARY_CLOUD_NAME")
                and _cloudinary_value("CLOUDINARY_API_KEY")
                and _cloudinary_value("CLOUDINARY_API_SECRET"))


def _cloudinary_value(name: str) -> str:
    """OS 환경 변수를 설정 객체보다 우선해 읽습니다."""
    return (
        (os.environ.get(name) or "").strip()
        or (getattr(settings, name, "") or "").strip()
    )


def require_persistent_storage() -> None:
    """
    호스팅에서 Cloudinary가 빠지면 업로드가 디스크에 쌓였다가 재배포 때 사라집니다.
    """
    if is_hosted_runtime() and not is_cloudinary_configured():
        raise RuntimeError(
            "호스팅 환경에서는 Cloudinary가 필요합니다. "
            "CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET를 설정하세요."
        )


def _configure() -> None:
    import cloudinary

    cloudinary.config(
        cloud_name=_cloudinary_value("CLOUDINARY_CLOUD_NAME"),
        api_key=_cloudinary_value("CLOUDINARY_API_KEY"),
        api_secret=_cloudinary_value("CLOUDINARY_API_SECRET"),
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
        # raw(PDF·PPTX·DOCX 등)는 Cloudinary가 확장자를 추론하지 못합니다.
        # public_id에 확장자를 붙여야 secure_url이 ".../abc123.pdf" 형태가 되고,
        # 브라우저가 application/pdf로 받아 미리보기가 열립니다.
        # image/video는 Cloudinary가 format을 붙여주므로 그대로 둡니다.
        cloud_public_id = f"{public_id}{suffix}" if resource_type == "raw" else public_id
        return _upload_cloudinary(
            payload,
            folder=folder,
            resource_type=resource_type,
            public_id=cloud_public_id,
            filename=filename,
        )

    if is_hosted_runtime():
        raise ValueError(
            "Cloudinary 환경 변수가 없어 파일을 클라우드에 올릴 수 없습니다. "
            "CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET를 설정하세요."
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


def local_file_path(stored_name: Optional[str]) -> Optional[Path]:
    """로컬 폴백으로 저장된 파일이 있으면 절대 경로를 반환합니다."""
    if not stored_name:
        return None
    path = _upload_root() / stored_name
    return path if path.exists() and path.is_file() else None


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
        buffer = BytesIO(payload)
        buffer.name = filename or "upload.bin"
        result = cloudinary.uploader.upload(
            buffer,
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
