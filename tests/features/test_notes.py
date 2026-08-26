"""
노트 API 단위 테스트

테스트 대상:
- 노트 생성 (CRUD)
- 노트 조회
- 노트 수정 (버전 관리)
- 노트 삭제
- 노트 검색
- 권한 검증
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime


class TestCreateNote:
    """노트 생성 테스트"""

    def test_create_note_success(
        self, client: TestClient, auth_headers, test_note_data
    ):
        """
        노트 생성 성공

        POST /api/notes
        요청: {title, content, category, tags, is_public}
        응답: 201 Created + note_data
        """
        # When: 노트 생성 요청
        response = client.post(
            "/api/notes",
            json=test_note_data,
            headers=auth_headers
        )

        # Then: 201 Created
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == 201
        assert data["data"]["title"] == test_note_data["title"]
        assert data["data"]["content"] == test_note_data["content"]
        assert data["data"]["category"] == test_note_data["category"]
        assert data["data"]["tags"] == test_note_data["tags"]
        assert data["data"]["is_public"] is False
        assert "id" in data["data"]

    def test_create_note_without_auth(self, client: TestClient, test_note_data):
        """
        인증 없이 노트 생성 시도

        POST /api/notes
        응답: 403 Forbidden
        """
        # When: 인증 없이 노트 생성
        response = client.post("/api/notes", json=test_note_data)

        # Then: 403 Forbidden
        assert response.status_code in [401, 403]

    def test_create_note_missing_title(self, client: TestClient, auth_headers):
        """
        제목 없이 노트 생성 시도

        POST /api/notes
        응답: 422 Unprocessable Entity
        """
        # Given: 제목이 없는 노트 데이터
        invalid_data = {
            "content": "Test content",
            "category": "Test",
            "tags": ["test"],
        }

        # When: 노트 생성 요청
        response = client.post(
            "/api/notes",
            json=invalid_data,
            headers=auth_headers
        )

        # Then: 422 Validation Error
        assert response.status_code == 422

    def test_create_public_note(self, client: TestClient, auth_headers):
        """
        공개 노트 생성

        POST /api/notes
        요청: {is_public: True}
        """
        # Given: 공개 설정
        note_data = {
            "title": "Public Note",
            "content": "This is a public note",
            "is_public": True,
        }

        # When: 노트 생성
        response = client.post(
            "/api/notes",
            json=note_data,
            headers=auth_headers
        )

        # Then: is_public = True
        assert response.status_code == 201
        assert response.json()["data"]["is_public"] is True


class TestGetNote:
    """노트 조회 테스트"""

    def test_get_own_note_success(
        self, client: TestClient, auth_headers, test_note
    ):
        """
        자신의 노트 조회 성공

        GET /api/notes/{note_id}
        응답: 200 OK + note_data
        """
        # When: 노트 조회
        response = client.get(
            f"/api/notes/{test_note.id}",
            headers=auth_headers
        )

        # Then: 200 OK
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == test_note.id
        assert data["data"]["title"] == test_note.title

    def test_get_nonexistent_note(self, client: TestClient, auth_headers):
        """
        존재하지 않는 노트 조회

        GET /api/notes/999
        응답: 404 Not Found
        """
        # When: 존재하지 않는 노트 조회
        response = client.get(
            "/api/notes/999",
            headers=auth_headers
        )

        # Then: 404 Not Found
        assert response.status_code == 404

    def test_get_private_note_unauthorized(
        self, client: TestClient, test_note, test_another_user
    ):
        """
        다른 사용자의 비공개 노트 조회 시도

        GET /api/notes/{note_id}
        응답: 404 Not Found (권한 없음)
        """
        from conftest import get_auth_headers

        # Given: 다른 사용자의 인증 정보
        other_headers = get_auth_headers(test_another_user.id, test_another_user.username)

        # When: 다른 사용자의 비공개 노트 조회
        response = client.get(
            f"/api/notes/{test_note.id}",
            headers=other_headers
        )

        # Then: 404 Not Found (권한 없음)
        assert response.status_code == 404

    def test_get_public_note_without_auth(self, client: TestClient, db: Session, test_user):
        """
        공개 노트를 인증 없이 조회

        GET /api/notes/{note_id}
        응답: 200 OK
        """
        from tests.conftest import create_test_note

        # Given: 공개 노트
        public_note = create_test_note(
            db,
            test_user.id,
            title="Public Note",
            is_public=True
        )

        # When: 인증 없이 공개 노트 조회
        response = client.get(f"/api/notes/{public_note.id}")

        # Then: 200 OK
        assert response.status_code == 200

    def test_note_view_count_increases(
        self, client: TestClient, auth_headers, test_note
    ):
        """
        노트 조회 시 조회수 증가

        GET /api/notes/{note_id}
        """
        # Given: 초기 조회수
        initial_view_count = test_note.view_count

        # When: 노트 조회
        response = client.get(
            f"/api/notes/{test_note.id}",
            headers=auth_headers
        )

        # Then: 조회수 증가
        assert response.status_code == 200
        assert response.json()["data"]["view_count"] > initial_view_count


class TestUpdateNote:
    """노트 수정 테스트"""

    def test_update_note_success(
        self, client: TestClient, auth_headers, test_note
    ):
        """
        노트 수정 성공

        PUT /api/notes/{note_id}
        요청: {title, content, ...}
        응답: 200 OK + updated_note
        """
        # Given: 수정 데이터
        update_data = {
            "title": "Updated Title",
            "content": "# Updated Content\n\nNew content here.",
            "category": "Updated",
            "tags": ["updated", "modified"],
        }

        # When: 노트 수정 요청
        response = client.put(
            f"/api/notes/{test_note.id}",
            json=update_data,
            headers=auth_headers
        )

        # Then: 200 OK
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["title"] == "Updated Title"
        assert data["data"]["category"] == "Updated"

    def test_update_others_note_forbidden(
        self, client: TestClient, test_note, test_another_user
    ):
        """
        다른 사용자의 노트 수정 시도

        PUT /api/notes/{note_id}
        응답: 403 Forbidden
        """
        from conftest import get_auth_headers

        # Given: 다른 사용자의 인증
        other_headers = get_auth_headers(test_another_user.id, test_another_user.username)

        update_data = {
            "title": "Malicious Title",
        }

        # When: 다른 사용자의 노트 수정 시도
        response = client.put(
            f"/api/notes/{test_note.id}",
            json=update_data,
            headers=other_headers
        )

        # Then: 403 Forbidden
        assert response.status_code == 403

    def test_update_without_auth(self, client: TestClient, test_note):
        """
        인증 없이 노트 수정 시도

        PUT /api/notes/{note_id}
        응답: 403 Forbidden
        """
        update_data = {"title": "Hacked"}

        # When: 인증 없이 수정 시도
        response = client.put(
            f"/api/notes/{test_note.id}",
            json=update_data
        )

        # Then: 403 Forbidden
        assert response.status_code in [401, 403]


class TestDeleteNote:
    """노트 삭제 테스트"""

    def test_delete_note_success(
        self, client: TestClient, auth_headers, test_note
    ):
        """
        노트 삭제 성공 (소프트 삭제)

        DELETE /api/notes/{note_id}
        응답: 200 OK
        """
        # When: 노트 삭제 요청
        response = client.delete(
            f"/api/notes/{test_note.id}",
            headers=auth_headers
        )

        # Then: 200 OK
        assert response.status_code == 200
        assert response.json()["message"] == "Note deleted successfully"

    def test_delete_others_note_forbidden(
        self, client: TestClient, test_note, test_another_user
    ):
        """
        다른 사용자의 노트 삭제 시도

        DELETE /api/notes/{note_id}
        응답: 403 Forbidden
        """
        from conftest import get_auth_headers

        other_headers = get_auth_headers(test_another_user.id, test_another_user.username)

        # When: 다른 사용자의 노트 삭제 시도
        response = client.delete(
            f"/api/notes/{test_note.id}",
            headers=other_headers
        )

        # Then: 403 Forbidden
        assert response.status_code == 403

    def test_delete_nonexistent_note(self, client: TestClient, auth_headers):
        """
        존재하지 않는 노트 삭제

        DELETE /api/notes/999
        응답: 403 Forbidden (또는 404)
        """
        # When: 존재하지 않는 노트 삭제
        response = client.delete(
            "/api/notes/999",
            headers=auth_headers
        )

        # Then: 403 또는 404
        assert response.status_code in [403, 404]


class TestSearchNotes:
    """노트 검색 테스트"""

    def test_search_by_title(self, client: TestClient, auth_headers, test_note, db: Session, test_user):
        """
        제목으로 노트 검색

        GET /api/notes/search/q?q=Test
        응답: 200 OK + matching_notes
        """
        # When: 검색 요청
        response = client.get(
            "/api/notes/search/q?q=Test",
            headers=auth_headers
        )

        # Then: 200 OK
        assert response.status_code == 200
        data = response.json()
        assert "notes" in data["data"]
        # 검색 결과에 test_note가 포함되어야 함
        assert any(note["id"] == test_note.id for note in data["data"]["notes"])

    def test_search_by_content(self, client: TestClient, auth_headers, test_note):
        """
        내용으로 노트 검색

        GET /api/notes/search/q?q=content
        """
        # When: 내용 검색
        response = client.get(
            "/api/notes/search/q?q=content",
            headers=auth_headers
        )

        # Then: 200 OK
        assert response.status_code == 200

    def test_search_empty_result(self, client: TestClient, auth_headers):
        """
        검색 결과가 없는 경우

        GET /api/notes/search/q?q=nonexistent
        응답: 200 OK + empty_notes
        """
        # When: 존재하지 않는 키워드 검색
        response = client.get(
            "/api/notes/search/q?q=nonexistentKeyword12345",
            headers=auth_headers
        )

        # Then: 200 OK but empty
        assert response.status_code == 200
        assert len(response.json()["data"]["notes"]) == 0

    def test_search_pagination(self, client: TestClient, auth_headers):
        """
        페이지네이션과 함께 검색

        GET /api/notes/search/q?q=test&page=1&limit=5
        """
        # When: 페이지네이션과 함께 검색
        response = client.get(
            "/api/notes/search/q?q=test&page=1&limit=5",
            headers=auth_headers
        )

        # Then: 200 OK
        assert response.status_code == 200
        assert "pagination" in response.json()["data"]


class TestNoteVersioning:
    """노트 버전 관리 테스트"""

    def test_version_created_on_create(self, client: TestClient, auth_headers, db: Session):
        """
        노트 생성 시 버전 1 자동 생성

        POST /api/notes
        → note_versions 테이블에 version_number=1 생성
        """
        from features.notes.models import NoteVersion

        # Given: 새로운 노트 데이터
        note_data = {
            "title": "Version Test",
            "content": "Original content",
        }

        # When: 노트 생성
        response = client.post(
            "/api/notes",
            json=note_data,
            headers=auth_headers
        )

        # Then: 버전이 생성됨
        assert response.status_code == 201
        note_id = response.json()["data"]["id"]

        # 데이터베이스에서 버전 확인
        version = db.query(NoteVersion).filter(
            NoteVersion.note_id == note_id,
            NoteVersion.version_number == 1
        ).first()

        assert version is not None
        assert version.content == "Original content"

    def test_version_incremented_on_update(
        self, client: TestClient, auth_headers, test_note, db: Session
    ):
        """
        노트 수정 시 버전 번호 증가

        PUT /api/notes/{note_id}
        → version_number가 2로 증가
        """
        from features.notes.models import NoteVersion

        # Given: 수정 데이터
        update_data = {
            "title": "Modified Title",
            "content": "Modified content",
        }

        # When: 노트 수정
        response = client.put(
            f"/api/notes/{test_note.id}",
            json=update_data,
            headers=auth_headers
        )

        # Then: 새 버전 생성됨
        assert response.status_code == 200

        # 데이터베이스에서 버전 확인
        versions = db.query(NoteVersion).filter(
            NoteVersion.note_id == test_note.id
        ).order_by(NoteVersion.version_number).all()

        assert len(versions) == 2
        assert versions[0].version_number == 1
        assert versions[1].version_number == 2
        assert versions[1].content == "Modified content"


class TestNoteFiltering:
    """노트 필터링 테스트"""

    def test_filter_by_category(self, client: TestClient, auth_headers, test_note):
        """
        카테고리로 필터링

        GET /api/notes?category=Test
        """
        # When: 카테고리 필터링
        response = client.get(
            f"/api/notes?category={test_note.category}",
            headers=auth_headers
        )

        # Then: 200 OK
        assert response.status_code == 200
        notes = response.json()["data"]["notes"]
        assert all(note["category"] == test_note.category for note in notes)

    def test_filter_by_tag(self, client: TestClient, auth_headers, test_note):
        """
        태그로 필터링

        GET /api/notes?tag=test
        """
        # When: 태그 필터링
        response = client.get(
            f"/api/notes?tag={test_note.tags[0]}",
            headers=auth_headers
        )

        # Then: 200 OK
        assert response.status_code == 200


class TestNoteList:
    """노트 목록 조회 테스트"""

    def test_get_notes_list_success(self, client: TestClient, auth_headers, test_note):
        """
        노트 목록 조회 성공

        GET /api/notes
        응답: 200 OK + notes_list
        """
        # When: 노트 목록 조회
        response = client.get(
            "/api/notes",
            headers=auth_headers
        )

        # Then: 200 OK
        assert response.status_code == 200
        data = response.json()
        assert "notes" in data["data"]
        assert "pagination" in data["data"]
        assert "total" in data["data"]["pagination"]

    def test_pagination_works(self, client: TestClient, auth_headers):
        """
        페이지네이션 작동 확인

        GET /api/notes?page=1&limit=10
        """
        # When: 페이지네이션과 함께 조회
        response = client.get(
            "/api/notes?page=1&limit=10",
            headers=auth_headers
        )

        # Then: 200 OK
        assert response.status_code == 200
        pagination = response.json()["data"]["pagination"]
        assert pagination["page"] == 1
        assert pagination["limit"] == 10
