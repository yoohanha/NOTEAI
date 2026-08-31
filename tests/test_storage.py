"""Cloudinary 업로드 및 호스팅 폴백 차단"""

from io import BytesIO
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from core.storage import require_persistent_storage, upload_bytes


def test_hosted_runtime_requires_cloudinary(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setattr("core.storage.is_cloudinary_configured", lambda: False)
    with pytest.raises(RuntimeError, match="Cloudinary"):
        require_persistent_storage()


def test_hosted_upload_refuses_local_fallback(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setattr("core.storage.is_cloudinary_configured", lambda: False)
    with pytest.raises(ValueError, match="Cloudinary"):
        upload_bytes(
            b"png-bytes",
            folder="noteai/media/1",
            resource_type="image",
            filename="shot.png",
        )


def test_cloudinary_upload_sends_bytesio(monkeypatch):
    captured = {}

    def fake_upload(fileobj, **_kwargs):
        captured["file"] = fileobj
        return {
            "secure_url": "https://res.cloudinary.com/demo/image/upload/shot.png",
            "public_id": "noteai/media/1/abc",
            "resource_type": "image",
        }

    monkeypatch.setattr("core.storage.is_cloudinary_configured", lambda: True)
    monkeypatch.setattr("core.storage._configure", lambda: None)
    monkeypatch.setattr("cloudinary.uploader.upload", fake_upload)

    result = upload_bytes(
        b"png-bytes",
        folder="noteai/media/1",
        resource_type="image",
        filename="shot.png",
    )

    assert isinstance(captured["file"], BytesIO)
    assert captured["file"].getvalue() == b"png-bytes"
    assert result["storage"] == "cloudinary"
    assert result["url"].startswith("https://res.cloudinary.com/")


def test_health_reports_persistence(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["persistence"]["database"] in ("sqlite", "postgresql")
    assert isinstance(body["persistence"]["cloudinary"], bool)
