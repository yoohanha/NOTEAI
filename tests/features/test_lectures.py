"""NOTE_LECTURE 강좌 폴더 / 교안 API 테스트"""

from io import BytesIO


def test_lectures_require_auth(client):
    assert client.get("/api/lectures").status_code in (401, 403)


def test_create_list_and_delete_course(client, auth_headers):
    created = client.post(
        "/api/lectures",
        json={"name": "  머신러닝 개론  "},
        headers=auth_headers,
    )
    assert created.status_code == 201
    course = created.json()["data"]
    assert course["name"] == "머신러닝 개론"
    assert course["file_count"] == 0

    listed = client.get("/api/lectures", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] == 1

    deleted = client.delete(f"/api/lectures/{course['id']}", headers=auth_headers)
    assert deleted.status_code == 200
    assert client.get("/api/lectures", headers=auth_headers).json()["data"]["total"] == 0


def test_rejects_empty_course_name(client, auth_headers):
    response = client.post("/api/lectures", json={"name": "   "}, headers=auth_headers)
    assert response.status_code == 400


def test_upload_list_preview_and_delete_file(client, auth_headers):
    course = client.post(
        "/api/lectures",
        json={"name": "자료구조"},
        headers=auth_headers,
    ).json()["data"]

    files = {"file": ("week1.pdf", BytesIO(b"%PDF-1.4 fake"), "application/pdf")}
    uploaded = client.post(
        f"/api/lectures/{course['id']}/files",
        files=files,
        headers=auth_headers,
    )
    assert uploaded.status_code == 201
    material = uploaded.json()["data"]
    assert material["extension"] == "pdf"
    assert material["original_name"] == "week1.pdf"
    assert "public_url" in material

    detail = client.get(f"/api/lectures/{course['id']}", headers=auth_headers)
    assert detail.status_code == 200
    payload = detail.json()["data"]
    assert payload["course"]["file_count"] == 1
    assert payload["files"][0]["id"] == material["id"]

    downloaded = client.get(
        f"/api/lectures/{course['id']}/files/{material['id']}",
        headers=auth_headers,
    )
    assert downloaded.status_code == 200

    removed = client.delete(
        f"/api/lectures/{course['id']}/files/{material['id']}",
        headers=auth_headers,
    )
    assert removed.status_code == 200
    leftover = client.get(f"/api/lectures/{course['id']}", headers=auth_headers)
    assert leftover.json()["data"]["course"]["file_count"] == 0


def test_rejects_unsupported_lecture_file(client, auth_headers):
    course = client.post(
        "/api/lectures",
        json={"name": "보안"},
        headers=auth_headers,
    ).json()["data"]
    files = {"file": ("malware.exe", BytesIO(b"binary"), "application/octet-stream")}
    response = client.post(
        f"/api/lectures/{course['id']}/files",
        files=files,
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_delete_course_removes_files(client, auth_headers):
    course = client.post(
        "/api/lectures",
        json={"name": "운영체제"},
        headers=auth_headers,
    ).json()["data"]
    files = {"file": ("ch1.pptx", BytesIO(b"PK fake"), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
    uploaded = client.post(
        f"/api/lectures/{course['id']}/files",
        files=files,
        headers=auth_headers,
    )
    file_id = uploaded.json()["data"]["id"]

    assert client.delete(f"/api/lectures/{course['id']}", headers=auth_headers).status_code == 200
    missing = client.get(
        f"/api/lectures/{course['id']}/files/{file_id}",
        headers=auth_headers,
    )
    assert missing.status_code == 404


def test_stores_cloudinary_url_for_lecture_file(client, auth_headers, monkeypatch):
    def fake_upload(payload, *, folder, resource_type, filename):
        return {
            "url": "https://res.cloudinary.com/demo/raw/upload/week1.pdf",
            "public_id": f"{folder}/cloud-id",
            "storage": "cloudinary",
            "resource_type": resource_type,
        }

    monkeypatch.setattr("features.lectures.service.upload_bytes", fake_upload)
    course = client.post(
        "/api/lectures",
        json={"name": "클라우드 교안"},
        headers=auth_headers,
    ).json()["data"]
    files = {"file": ("week1.pdf", BytesIO(b"%PDF-1.4 fake"), "application/pdf")}
    uploaded = client.post(
        f"/api/lectures/{course['id']}/files",
        files=files,
        headers=auth_headers,
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["data"]["public_url"].startswith("https://res.cloudinary.com/")
