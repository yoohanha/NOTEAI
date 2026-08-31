"""NOTE_3D 미디어 업로드 API 테스트"""

from io import BytesIO


def test_media_requires_auth(client):
    assert client.get("/api/media").status_code in (401, 403)


def test_upload_list_and_delete_image(client, admin_headers):
    files = {"file": ("sample.png", BytesIO(b"\x89PNG\r\n\x1a\nfake"), "image/png")}
    created = client.post("/api/media", files=files, headers=admin_headers)

    assert created.status_code == 201
    asset = created.json()["data"]
    assert asset["kind"] == "image"
    assert asset["original_name"] == "sample.png"
    assert "public_url" in asset

    listed = client.get("/api/media", headers=admin_headers)
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] == 1

    file_res = client.get(f"/api/media/{asset['id']}/file", headers=admin_headers)
    assert file_res.status_code == 200

    deleted = client.delete(f"/api/media/{asset['id']}", headers=admin_headers)
    assert deleted.status_code == 200
    assert client.get("/api/media", headers=admin_headers).json()["data"]["total"] == 0


def test_regular_user_cannot_delete_media(client, auth_headers):
    files = {"file": ("sample.png", BytesIO(b"\x89PNG\r\n\x1a\nfake"), "image/png")}
    created = client.post("/api/media", files=files, headers=auth_headers)
    assert created.status_code == 201
    asset_id = created.json()["data"]["id"]
    blocked = client.delete(f"/api/media/{asset_id}", headers=auth_headers)
    assert blocked.status_code == 403
    assert client.get("/api/media", headers=auth_headers).json()["data"]["total"] == 1


def test_rejects_unsupported_type(client, auth_headers):
    files = {"file": ("notes.exe", BytesIO(b"binary"), "application/octet-stream")}
    response = client.post("/api/media", files=files, headers=auth_headers)
    assert response.status_code == 400


def test_stores_cloudinary_url_when_configured(client, auth_headers, monkeypatch):
    def fake_upload(payload, *, folder, resource_type, filename):
        return {
            "url": "https://res.cloudinary.com/demo/image/upload/sample.png",
            "public_id": f"{folder}/cloud-id",
            "storage": "cloudinary",
            "resource_type": resource_type,
        }

    monkeypatch.setattr("features.media.service.upload_bytes", fake_upload)
    files = {"file": ("sample.png", BytesIO(b"\x89PNG\r\n\x1a\nfake"), "image/png")}
    created = client.post("/api/media", files=files, headers=auth_headers)
    assert created.status_code == 201
    assert created.json()["data"]["public_url"].startswith("https://res.cloudinary.com/")
