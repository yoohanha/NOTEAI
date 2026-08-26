"""
데이터베이스 설정 모듈
- SQLAlchemy 엔진 설정
- 세션 관리
- Base 클래스
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from core.config import settings
from typing import Generator

# 데이터베이스 엔진 생성
# SQLite 사용 시 check_same_thread=False 필요
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    poolclass=StaticPool if "sqlite" in settings.DATABASE_URL else None,
    echo=settings.DEBUG,
)

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 선언적 기본 클래스 (모든 ORM 모델의 기본)
Base = declarative_base()


def get_db() -> Generator:
    """
    데이터베이스 세션 의존성

    FastAPI 라우트에서 사용:
    async def get_notes(db: Session = Depends(get_db)):
        ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def register_models():
    """
    모든 ORM 모델을 import하여 SQLAlchemy 레지스트리에 등록

    모델 간 relationship은 문자열 이름("User" 등)으로 참조되므로,
    한 모델만 import한 채 쿼리하면 매퍼 설정 단계에서
    InvalidRequestError가 발생합니다. 테이블 생성 없이 조회만 하는
    스크립트(예: monitor_worker.py --status)는 이 함수만 호출하면 됩니다.
    """
    # 모든 feature 모듈의 models import 필요
    from features.auth.models import User
    from features.notes.models import Note, NoteVersion, AISummary
    from features.comments.models import Comment
    from features.teams.models import Team, TeamMember
    from features.collaborators.models import NoteCollaborator
    from features.trends.models import TrendItem
    from features.monitor.models import CollectionRun


def init_db():
    """
    데이터베이스 초기화 (애플리케이션 시작 시 호출)
    모든 테이블 생성
    """
    register_models()

    Base.metadata.create_all(bind=engine)
    print("✅ 데이터베이스 초기화 완료")
