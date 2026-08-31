"""
데이터베이스 설정 모듈
- SQLAlchemy 엔진 설정
- 세션 관리
- Base 클래스
"""

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool, StaticPool

from core.config import settings


def resolve_database_url(raw_url: str) -> str:
    """
    DB URL을 SQLAlchemy가 바로 쓸 수 있는 형태로 정규화합니다.

    - Render/Heroku의 postgres:// 를 postgresql:// 로 바꿉니다.
    - 파일 SQLite는 backend/data/ 아래 절대 경로로 고정해
      작업 디렉터리가 바뀌어도 같은 DB 파일을 보게 합니다.
    """
    url = (raw_url or "").strip()
    if not url:
        url = "sqlite:///./noteai.db"

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]

    parsed = make_url(url)
    if not str(parsed.drivername).startswith("sqlite"):
        return url

    database = parsed.database or ""
    if not database or database == ":memory:":
        return url

    db_path = Path(database)
    if not db_path.is_absolute():
        backend_root = Path(__file__).resolve().parent.parent
        data_dir = Path(settings.DATA_DIR)
        if not data_dir.is_absolute():
            data_dir = backend_root / data_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = data_dir / db_path.name

    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path.resolve().as_posix()}"


DATABASE_URL = resolve_database_url(settings.DATABASE_URL)
_IS_SQLITE = DATABASE_URL.startswith("sqlite")
_IS_MEMORY_SQLITE = _IS_SQLITE and ":memory:" in DATABASE_URL

_engine_kwargs = {"echo": settings.DEBUG}
_connect_args = {}

if _IS_SQLITE:
    # SQLite는 스레드 검사가 기본이라 FastAPI 워커와 충돌합니다.
    _connect_args["check_same_thread"] = False
    if _IS_MEMORY_SQLITE:
        # :memory: 는 연결마다 DB가 달라지므로 단일 연결을 재사용합니다.
        _engine_kwargs["poolclass"] = StaticPool
    else:
        # 파일 DB는 요청이 끝날 때 연결을 닫아 커밋이 디스크에 반영되게 합니다.
        _engine_kwargs["poolclass"] = NullPool

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    **_engine_kwargs,
)

if _IS_SQLITE:

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        """외래키와 WAL을 켜 계정 데이터가 유실되지 않게 합니다."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        # OneDrive 등 클라우드 동기화 폴더에서는 WAL이 유실/충돌을 일으킬 수 있어
        # 단일 저널 모드로 커밋이 같은 파일에 바로 반영되게 합니다.
        cursor.execute("PRAGMA journal_mode=DELETE")
        cursor.execute("PRAGMA synchronous=FULL")
        cursor.close()


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
    from features.media.models import MediaAsset
    from features.lectures.models import LectureCourse, LectureMaterial


def init_db():
    """
    데이터베이스 초기화 (애플리케이션 시작 시 호출)
    모든 테이블 생성
    """
    register_models()

    Base.metadata.create_all(bind=engine)
    print("✅ 데이터베이스 초기화 완료")
    if _IS_SQLITE and not _IS_MEMORY_SQLITE:
        print(f"💾 SQLite 파일: {DATABASE_URL}")
