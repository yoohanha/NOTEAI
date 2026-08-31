"""
인증 API 단위 테스트

테스트 대상:
- 회원가입 (회성공, 중복 확인)
- 로그인 (성공, 실패)
- 토큰 검증
- 현재 사용자 조회
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestAuthRegister:
    """회원가입 테스트"""

    def test_register_success(self, client: TestClient, db: Session):
        """
        회원가입 성공

        POST /api/auth/register
        요청: {username, email, password, full_name}
        응답: 201 Created + token
        """
        # Given: 신규 사용자 정보
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePassword123",
            "full_name": "New User",
        }

        # When: 회원가입 요청
        response = client.post("/api/auth/register", json=user_data)

        # Then: 201 Created 응답
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == 201
        assert "data" in data
        assert "access_token" in data["data"]
        assert data["data"]["user"]["username"] == "newuser"
        assert data["data"]["user"]["email"] == "newuser@example.com"

    def test_register_duplicate_username(self, client: TestClient, test_user):
        """
        중복된 사용자명으로 회원가입 시도

        POST /api/auth/register
        응답: 400 Bad Request
        """
        # Given: 기존 사용자와 동일한 사용자명
        user_data = {
            "username": test_user.username,  # 이미 존재하는 사용자명
            "email": "different@example.com",
            "password": "SecurePassword123",
            "full_name": "Another User",
        }

        # When: 회원가입 요청
        response = client.post("/api/auth/register", json=user_data)

        # Then: 409 Conflict
        assert response.status_code == 409
        assert "이미 가입된 계정입니다. 로그인해주세요." in response.json()["detail"]

    def test_register_duplicate_email(self, client: TestClient, test_user):
        """같은 이메일이면 사용자명이 달라도 가입을 막습니다."""
        response = client.post("/api/auth/register", json={
            "username": "anotheruser",
            "email": test_user.email,
            "password": "SecurePassword123",
        })

        assert response.status_code == 409
        assert "이미 가입된 계정입니다. 로그인해주세요." in response.json()["detail"]

    def test_register_duplicate_case_insensitive(self, client: TestClient, test_user):
        """대소문자만 다른 아이디/이메일도 중복으로 처리합니다."""
        response = client.post("/api/auth/register", json={
            "username": test_user.username.upper(),
            "email": "other@example.com",
            "password": "SecurePassword123",
        })

        assert response.status_code == 409

    def test_register_invalid_password(self, client: TestClient):
        """
        조건을 만족하지 않는 비밀번호로 회원가입 시도

        비밀번호 요구사항: 최소 8자
        응답: 422 Unprocessable Entity
        """
        # Given: 짧은 비밀번호
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "short",  # 8자 미만
            "full_name": "New User",
        }

        # When: 회원가입 요청
        response = client.post("/api/auth/register", json=user_data)

        # Then: 422 Validation Error
        assert response.status_code == 422

    def test_register_invalid_email(self, client: TestClient):
        """
        유효하지 않은 이메일로 회원가입 시도

        응답: 422 Unprocessable Entity
        """
        # Given: 유효하지 않은 이메일
        user_data = {
            "username": "newuser",
            "email": "invalid-email",  # 유효한 이메일 형식 아님
            "password": "SecurePassword123",
            "full_name": "New User",
        }

        # When: 회원가입 요청
        response = client.post("/api/auth/register", json=user_data)

        # Then: 422 Validation Error
        assert response.status_code == 422


class TestAuthLogin:
    """로그인 테스트"""

    def test_login_success(self, client: TestClient, test_user, test_user_data):
        """
        로그인 성공

        POST /api/auth/login
        요청: {username, password}
        응답: 200 OK + token
        """
        # Given: 존재하는 사용자 정보
        login_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"],
        }

        # When: 로그인 요청
        response = client.post("/api/auth/login", json=login_data)

        # Then: 200 OK
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == 200
        assert "access_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
        assert data["data"]["user"]["username"] == test_user.username

    def test_login_with_email(self, client: TestClient, test_user, test_user_data):
        """이메일로도 로그인할 수 있습니다."""
        response = client.post("/api/auth/login", json={
            "username": test_user.email,
            "password": test_user_data["password"],
        })

        assert response.status_code == 200
        assert response.json()["data"]["user"]["id"] == test_user.id

    def test_login_case_insensitive_username(
        self, client: TestClient, test_user, test_user_data
    ):
        """사용자명 대소문자가 달라도 로그인됩니다."""
        response = client.post("/api/auth/login", json={
            "username": test_user_data["username"].upper(),
            "password": test_user_data["password"],
        })

        assert response.status_code == 200

    def test_login_invalid_username(self, client: TestClient):
        """
        존재하지 않는 사용자명으로 로그인 시도

        POST /api/auth/login
        응답: 401 Unauthorized
        """
        # Given: 존재하지 않는 사용자명
        login_data = {
            "username": "nonexistent",
            "password": "AnyPassword123",
        }

        # When: 로그인 요청
        response = client.post("/api/auth/login", json=login_data)

        # Then: 401 Unauthorized
        assert response.status_code == 401
        assert "사용자명 또는 비밀번호가 올바르지 않습니다." in response.json()["detail"]

    def test_login_invalid_password(self, client: TestClient, test_user, test_user_data):
        """
        잘못된 비밀번호로 로그인 시도

        POST /api/auth/login
        응답: 401 Unauthorized
        """
        # Given: 올바른 사용자명, 잘못된 비밀번호
        login_data = {
            "username": test_user_data["username"],
            "password": "WrongPassword123",
        }

        # When: 로그인 요청
        response = client.post("/api/auth/login", json=login_data)

        # Then: 401 Unauthorized
        assert response.status_code == 401
        assert "사용자명 또는 비밀번호가 올바르지 않습니다." in response.json()["detail"]

    def test_login_inactive_user(self, client: TestClient, db: Session, test_user_data):
        """
        비활성 사용자로 로그인 시도

        POST /api/auth/login
        응답: 401 Unauthorized
        """
        from features.auth.models import User
        from core.security import hash_password

        # Given: 비활성 사용자
        inactive_user = User(
            username="inactive_user",
            email="inactive@example.com",
            password_hash=hash_password("Password123"),
            is_active=False,  # 비활성
        )

        db.add(inactive_user)
        db.commit()

        login_data = {
            "username": "inactive_user",
            "password": "Password123",
        }

        # When: 로그인 요청
        response = client.post("/api/auth/login", json=login_data)

        # Then: 401 Unauthorized
        assert response.status_code == 401


class TestAuthLogout:
    """로그아웃 테스트"""

    def test_logout_success(self, client: TestClient, auth_headers):
        """
        로그아웃 성공

        POST /api/auth/logout
        응답: 200 OK
        """
        # When: 로그아웃 요청 (인증 필수)
        response = client.post("/api/auth/logout", headers=auth_headers)

        # Then: 200 OK
        assert response.status_code == 200
        assert response.json()["message"] == "Logout successful"

    def test_logout_without_auth(self, client: TestClient):
        """
        인증 없이 로그아웃 시도

        POST /api/auth/logout
        응답: 403 Forbidden
        """
        # When: 인증 없이 로그아웃 요청
        response = client.post("/api/auth/logout")

        # Then: 403 Forbidden (또는 401 Unauthorized)
        assert response.status_code in [401, 403]


class TestAuthGetCurrentUser:
    """현재 사용자 정보 조회 테스트"""

    def test_get_current_user_success(
        self, client: TestClient, auth_headers, test_user
    ):
        """
        현재 사용자 정보 조회 성공

        GET /api/auth/me
        응답: 200 OK + user_info
        """
        # When: 현재 사용자 정보 조회 (인증 필수)
        response = client.get("/api/auth/me", headers=auth_headers)

        # Then: 200 OK
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == 200
        assert data["data"]["username"] == test_user.username
        assert data["data"]["email"] == test_user.email
        assert data["data"]["is_active"] is True
        assert data["data"]["is_admin"] is False

    def test_get_current_user_without_auth(self, client: TestClient):
        """
        인증 없이 현재 사용자 정보 조회 시도

        GET /api/auth/me
        응답: 403 Forbidden
        """
        # When: 인증 없이 사용자 정보 조회
        response = client.get("/api/auth/me")

        # Then: 403 Forbidden (또는 401 Unauthorized)
        assert response.status_code in [401, 403]

    def test_get_current_user_invalid_token(self, client: TestClient):
        """
        유효하지 않은 토큰으로 사용자 정보 조회 시도

        GET /api/auth/me
        응답: 401 Unauthorized
        """
        # Given: 유효하지 않은 토큰
        headers = {"Authorization": "Bearer invalid.token.here"}

        # When: 유효하지 않은 토큰으로 요청
        response = client.get("/api/auth/me", headers=headers)

        # Then: 401 Unauthorized
        assert response.status_code == 401


class TestJWTToken:
    """JWT 토큰 검증 테스트"""

    def test_token_expires(self, client: TestClient, test_user_token):
        """
        토큰 만료 시간 확인

        토큰에 exp 클레임이 포함되어야 함
        """
        from core.security import decode_token

        # When: 토큰 디코드
        payload = decode_token(test_user_token)

        # Then: exp 클레임 포함
        assert payload is not None
        assert "exp" in payload
        assert "user_id" in payload
        assert "username" in payload

    def test_malformed_token(self, client: TestClient):
        """
        손상된 토큰 처리

        GET /api/auth/me
        응답: 401 Unauthorized
        """
        # Given: 잘못된 형식의 토큰
        headers = {"Authorization": "Bearer not.a.valid.jwt"}

        # When: 손상된 토큰으로 요청
        response = client.get("/api/auth/me", headers=headers)

        # Then: 401 Unauthorized
        assert response.status_code == 401

    def test_missing_authorization_header(self, client: TestClient):
        """
        Authorization 헤더 누락

        GET /api/auth/me
        응답: 403 Forbidden
        """
        # When: Authorization 헤더 없이 요청
        response = client.get("/api/auth/me")

        # Then: 403 Forbidden (또는 401)
        assert response.status_code in [401, 403]


# ============ 통합 테스트 ============

class TestAuthFlow:
    """인증 흐름 통합 테스트"""

    def test_full_auth_flow(self, client: TestClient, db: Session):
        """
        전체 인증 흐름 테스트

        1. 회원가입
        2. 로그인
        3. 현재 사용자 조회
        """
        # Step 1: 회원가입
        register_data = {
            "username": "integrationuser",
            "email": "integration@example.com",
            "password": "IntegrationPassword123",
            "full_name": "Integration User",
        }

        register_response = client.post("/api/auth/register", json=register_data)
        assert register_response.status_code == 201

        # Step 2: 로그인
        login_data = {
            "username": "integrationuser",
            "password": "IntegrationPassword123",
        }

        login_response = client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200

        # Step 3: 토큰으로 사용자 정보 조회
        token = login_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        assert me_response.status_code == 200
        assert me_response.json()["data"]["username"] == "integrationuser"
