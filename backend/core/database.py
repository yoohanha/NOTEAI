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


def init_db():
    """
    데이터베이스 초기화 (애플리케이션 시작 시 호출)
    모든 테이블 생성
    """
    # 모든 feature 모듈의 models import 필요
    from features.auth.models import User
    from features.notes.models import Note, NoteVersion, AISummary
    from features.comments.models import Comment
    from features.teams.models import Team, TeamMember
    from features.collaborators.models import NoteCollaborator
    from features.trends.models import TrendItem

    Base.metadata.create_all(bind=engine)
    print("✅ 데이터베이스 초기화 완료")
