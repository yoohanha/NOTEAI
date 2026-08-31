"""The Matrix 관리자 회원 조회 API 테스트"""

from core.config import settings
from core.security import hash_password
from features.auth.models import User


def test_admin_users_require_auth(client):
    assert client.get("/api/admin/users").status_code in (401, 403)


def test_regular_user_cannot_list_members(client, auth_headers):
    response = client.get("/api/admin/users", headers=auth_headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "접근 권한이 없습니다"


def test_admin_email_can_list_members(client, db, test_user, auth_headers):
    admin = User(
        username="yuhanadmin",
        email=settings.ADMIN_EMAIL,
        password_hash=hash_password("AdminPass123"),
        full_name="Admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    login = client.post(
        "/api/auth/login",
        json={"username": admin.username, "password": "AdminPass123"},
    )
    assert login.status_code == 200
    assert login.json()["data"]["user"]["is_admin"] is True

    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    listed = client.get("/api/admin/users", headers=headers)
    assert listed.status_code == 200
    emails = {row["email"] for row in listed.json()["data"]["items"]}
    assert test_user.email in emails
    assert settings.ADMIN_EMAIL in emails
    assert all("password" not in row for row in listed.json()["data"]["items"])
