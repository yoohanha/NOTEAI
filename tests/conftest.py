"""
pytest 설정 및 공유 fixtures

이 파일은 모든 테스트에서 사용하는 설정과 fixtures를 정의합니다.
"""

import pytest
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# 테스트에서 앱을 올릴 때 외부 RSS를 긁지 않도록 워커를 끕니다.
# main.py를 import하기 전에 설정해야 startup 훅이 이를 읽습니다.
os.environ["NOTEAI_DISABLE_WORKER"] = "1"

# backend 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from main import app
from core.database import Base, get_db
from core.config import settings
from features.auth.models import User
from features.notes.models import Note, NoteVersion, AISummary
from features.media.models import MediaAsset  # noqa: F401
from features.lectures.models import LectureCourse, LectureMaterial  # noqa: F401
from features.vita.models import VitaCertificate, VitaPublication, VitaTeaching  # noqa: F401
from features.comments.models import Comment
from features.teams.models import Team, TeamMember
from features.collaborators.models import NoteCollaborator
from core.security import hash_password, create_access_token


@pytest.fixture(autouse=True)
def _use_local_storage_in_tests(monkeypatch):
    """테스트는 실제 Cloudinary 네트워크를 타지 않고 로컬 폴백을 씁니다."""
    monkeypatch.setattr("core.storage.is_cloudinary_configured", lambda: False)


# ============ 테스트 DB 설정 ============

# 테스트용 SQLite DB (메모리)
TEST_DATABASE_URL = "sqlite:///:memory:"

# 테스트 DB 엔진
#
# StaticPool이 반드시 필요합니다.
# SQLite의 :memory: DB는 커넥션마다 완전히 별개의 데이터베이스입니다.
# 기본 풀을 쓰면 create_all()이 만든 테이블과 TestClient(별도 스레드에서 실행)가
# 사용하는 커넥션이 서로 다른 DB를 보게 되어 "no such table" 오류가 납니다.
# StaticPool은 단일 커넥션을 모든 요청에서 재사용하므로 같은 DB를 공유합니다.
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# 테스트 세션 팩토리
TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


# ============ Fixtures ============

@pytest.fixture(scope="function")
def db():
    """
    테스트용 DB 세션 fixture
    각 테스트마다 새로운 DB를 생성하고 테스트 후 제거합니다.
    """
    # DB 테이블 생성
    Base.metadata.create_all(bind=test_engine)

    # 세션 생성
    db_session = TestSessionLocal()

    yield db_session

    # 테스트 후 정리
    db_session.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db: Session):
    """
    FastAPI TestClient fixture
    의존성을 테스트 DB로 오버라이드합니다.
    """
    def override_get_db():
        """테스트 DB를 의존성으로 제공"""
        yield db

    # get_db 의존성 오버라이드
    app.dependency_overrides[get_db] = override_get_db

    # TestClient 생성
    test_client = TestClient(app)

    yield test_client

    # 의존성 오버라이드 제거
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user_data():
    """테스트용 사용자 데이터"""
    return {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "TestPassword123",
        "full_name": "Test User",
    }


@pytest.fixture(scope="function")
def test_user(db: Session, test_user_data):
    """
    테스트용 사용자 생성 fixture
    DB에 실제로 생성됩니다.
    """
    user = User(
        username=test_user_data["username"],
        email=test_user_data["email"],
        password_hash=hash_password(test_user_data["password"]),
        full_name=test_user_data["full_name"],
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@pytest.fixture(scope="function")
def test_user_token(test_user):
    """
    테스트용 사용자의 JWT 토큰
    API 요청 시 사용됩니다.
    """
    token_data = {
        "user_id": test_user.id,
        "username": test_user.username,
    }
    return create_access_token(token_data)


@pytest.fixture(scope="function")
def auth_headers(test_user_token):
    """
    인증 헤더 fixture
    Authorization: Bearer <token>
    """
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture(scope="function")
def admin_user(db: Session):
    """관리자 이메일 계정. 삭제 API 테스트에 사용합니다."""
    user = User(
        username="yuhanadmin",
        email=settings.ADMIN_EMAIL,
        password_hash=hash_password("AdminPass123"),
        full_name="Admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def admin_headers(admin_user):
    """관리자 JWT 헤더"""
    token = create_access_token(
        {"user_id": admin_user.id, "username": admin_user.username}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def test_note_data():
    """테스트용 노트 데이터"""
    return {
        "title": "Test Note",
        "content": "# Test Note\n\nThis is a test note content.",
        "category": "Test",
        "tags": ["test", "example"],
        "is_public": False,
    }


@pytest.fixture(scope="function")
def test_note(db: Session, test_user, test_note_data):
    """
    테스트용 노트 생성 fixture
    DB에 실제로 생성됩니다.
    """
    note = Note(
        user_id=test_user.id,
        title=test_note_data["title"],
        content=test_note_data["content"],
        category=test_note_data["category"],
        tags=test_note_data["tags"],
        is_public=test_note_data["is_public"],
    )

    db.add(note)
    db.commit()
    db.refresh(note)

    # 초기 버전 생성
    version = NoteVersion(
        note_id=note.id,
        title=note.title,
        content=note.content,
        version_number=1,
        created_by=test_user.id,
    )

    db.add(version)
    db.commit()

    return note


@pytest.fixture(scope="function")
def test_another_user(db: Session):
    """다른 사용자 생성 fixture (협업 테스트용)"""
    user = User(
        username="otheruser",
        email="otheruser@example.com",
        password_hash=hash_password("OtherPassword123"),
        full_name="Other User",
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# ============ 헬퍼 함수 ============

def get_auth_headers(user_id: int, username: str):
    """
    특정 사용자의 인증 헤더 생성

    Args:
        user_id: 사용자 ID
        username: 사용자명

    Returns:
        인증 헤더 딕셔너리
    """
    token_data = {
        "user_id": user_id,
        "username": username,
    }
    token = create_access_token(token_data)
    return {"Authorization": f"Bearer {token}"}


def create_test_user(db: Session, username: str, email: str, password: str):
    """
    테스트 사용자 생성 헬퍼 함수

    Args:
        db: DB 세션
        username: 사용자명
        email: 이메일
        password: 비밀번호 (평문)

    Returns:
        생성된 User 객체
    """
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def create_test_note(
    db: Session,
    user_id: int,
    title: str = "Test Note",
    content: str = "Test content",
    is_public: bool = False,
) -> Note:
    """
    테스트 노트 생성 헬퍼 함수

    Args:
        db: DB 세션
        user_id: 작성자 ID
        title: 노트 제목
        content: 노트 내용
        is_public: 공개 여부

    Returns:
        생성된 Note 객체
    """
    note = Note(
        user_id=user_id,
        title=title,
        content=content,
        is_public=is_public,
    )

    db.add(note)
    db.commit()
    db.refresh(note)

    # 버전 생성
    version = NoteVersion(
        note_id=note.id,
        title=note.title,
        content=note.content,
        version_number=1,
        created_by=user_id,
    )

    db.add(version)
    db.commit()

    return note
