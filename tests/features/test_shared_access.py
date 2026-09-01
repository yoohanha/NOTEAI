"""
공유 열람 / 업로드 개방 / 삭제 관리자 전용 계약 테스트

요구사항:
- 조회(Read)와 업로드(Create)는 로그인한 모든 유저에게 열려 있어야 한다.
- 삭제(Delete)는 관리자 이메일 계정만 가능하고, 그 외에는 403이어야 한다.

개별 기능 테스트(test_media / test_lectures / test_vita / test_notes)가
각 API를 따로 검증하므로, 이 파일은 "일반 유저가 남이 올린 것을
보고 거기에 올릴 수 있는가"라는 교차 시나리오만 확인합니다.
"""

from io import BytesIO


PNG_BYTES = bytes.fromhex("89504e470d0a1a0a") + b"x" * 40
PDF_BYTES = b"%PDF-1.4\n" + b"y" * 60


class TestRegularUserCanRead:
    """일반 유저도 관리자가 올린 자료를 전부 볼 수 있어야 합니다."""

    def test_sees_admin_media(self, client, auth_headers, admin_headers):
        created = client.post(
            "/api/media",
            headers=admin_headers,
            files={"file": ("admin.png", BytesIO(PNG_BYTES), "image/png")},
        ).json()["data"]

        items = client.get("/api/media", headers=auth_headers).json()["data"]["items"]
        assert created["id"] in {item["id"] for item in items}

    def test_opens_admin_media_file(self, client, auth_headers, admin_headers):
        created = client.post(
            "/api/media",
            headers=admin_headers,
            files={"file": ("admin.png", BytesIO(PNG_BYTES), "image/png")},
        ).json()["data"]

        response = client.get(
            f"/api/media/{created['id']}/file",
            headers=auth_headers,
            follow_redirects=False,
        )
        assert response.status_code in (200, 307)

    def test_sees_admin_lecture_course_and_files(
        self, client, auth_headers, admin_headers
    ):
        course = client.post(
            "/api/lectures", headers=admin_headers, json={"name": "관리자 강좌"}
        ).json()["data"]
        client.post(
            f"/api/lectures/{course['id']}/files",
            headers=admin_headers,
            files={"file": ("note.pdf", BytesIO(PDF_BYTES), "application/pdf")},
        )

        detail = client.get(f"/api/lectures/{course['id']}", headers=auth_headers)
        assert detail.status_code == 200
        assert len(detail.json()["data"]["files"]) == 1

    def test_sees_admin_vita_entries(self, client, auth_headers, admin_headers):
        created = client.post(
            "/api/vita/publications", headers=admin_headers, json={"title": "관리자 논문"}
        ).json()["data"]

        data = client.get("/api/vita", headers=auth_headers).json()["data"]
        assert created["id"] in {row["id"] for row in data["publications"]}


class TestRegularUserCanCreate:
    """업로드/등록은 일반 유저에게도 열려 있어야 합니다."""

    def test_uploads_media(self, client, auth_headers):
        response = client.post(
            "/api/media",
            headers=auth_headers,
            files={"file": ("user.png", BytesIO(PNG_BYTES), "image/png")},
        )
        assert response.status_code == 201

    def test_uploads_into_admin_course(self, client, auth_headers, admin_headers):
        course = client.post(
            "/api/lectures", headers=admin_headers, json={"name": "관리자 강좌"}
        ).json()["data"]

        response = client.post(
            f"/api/lectures/{course['id']}/files",
            headers=auth_headers,
            files={"file": ("user.pdf", BytesIO(PDF_BYTES), "application/pdf")},
        )
        assert response.status_code == 201

    def test_creates_note_and_vita_entry(self, client, auth_headers):
        note = client.post(
            "/api/notes",
            headers=auth_headers,
            json={"title": "일반 노트", "content": "본문"},
        )
        assert note.status_code == 201

        vita = client.post(
            "/api/vita/certificates", headers=auth_headers, json={"name": "정보처리기사"}
        )
        assert vita.status_code == 201


class TestOnlyAdminCanDelete:
    """일반 유저의 모든 DELETE는 403이어야 합니다."""

    def test_media_delete_forbidden(self, client, auth_headers):
        created = client.post(
            "/api/media",
            headers=auth_headers,
            files={"file": ("user.png", BytesIO(PNG_BYTES), "image/png")},
        ).json()["data"]

        response = client.delete(f"/api/media/{created['id']}", headers=auth_headers)
        assert response.status_code == 403

    def test_lecture_file_delete_forbidden(self, client, auth_headers):
        course = client.post(
            "/api/lectures", headers=auth_headers, json={"name": "내 강좌"}
        ).json()["data"]
        material = client.post(
            f"/api/lectures/{course['id']}/files",
            headers=auth_headers,
            files={"file": ("user.pdf", BytesIO(PDF_BYTES), "application/pdf")},
        ).json()["data"]

        response = client.delete(
            f"/api/lectures/{course['id']}/files/{material['id']}", headers=auth_headers
        )
        assert response.status_code == 403

    def test_vita_delete_forbidden(self, client, auth_headers):
        created = client.post(
            "/api/vita/teachings", headers=auth_headers, json={"institution": "OO대학교"}
        ).json()["data"]

        response = client.delete(
            f"/api/vita/teachings/{created['id']}", headers=auth_headers
        )
        assert response.status_code == 403

    def test_admin_can_delete_regular_user_content(
        self, client, auth_headers, admin_headers
    ):
        created = client.post(
            "/api/media",
            headers=auth_headers,
            files={"file": ("user.png", BytesIO(PNG_BYTES), "image/png")},
        ).json()["data"]

        response = client.delete(f"/api/media/{created['id']}", headers=admin_headers)
        assert response.status_code == 200


class TestIsAdminFlagDrivesTheUI:
    """
    프론트엔드는 is_admin 하나로 삭제 버튼과 관리자모드 버튼을 그립니다.
    이 플래그가 응답에서 빠지면 화면 권한이 통째로 무너집니다.
    """

    def test_me_returns_flag_for_regular_user(self, client, auth_headers):
        data = client.get("/api/auth/me", headers=auth_headers).json()["data"]
        assert data["is_admin"] is False

    def test_me_returns_flag_for_admin(self, client, admin_headers):
        data = client.get("/api/auth/me", headers=admin_headers).json()["data"]
        assert data["is_admin"] is True

    def test_register_response_includes_flag(self, client):
        data = client.post(
            "/api/auth/register",
            json={
                "username": "freshuser",
                "email": "fresh@example.com",
                "password": "FreshPass123",
            },
        ).json()["data"]
        assert data["user"]["is_admin"] is False
