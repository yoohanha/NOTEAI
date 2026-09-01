"""
데이터베이스 설정 모듈
- SQLAlchemy 엔진 설정
- 세션 관리
- Base 클래스
"""

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool, StaticPool

from core.config import settings
from core.storage import (
    is_cloudinary_configured,
    is_hosted_runtime,
    require_persistent_storage,
)


def resolve_database_url(raw_url: str) -> str:
    """
    DB URL을 SQLAlchemy가 바로 쓸 수 있는 형태로 정규화합니다.

    - Render/Heroku의 postgres:// 를 postgresql+psycopg2:// 로 바꿉니다.
    - Supabase 호스트에는 sslmode=require 를 붙입니다.
    - 파일 SQLite는 backend/data/ 아래 절대 경로로 고정합니다.
    """
    url = (raw_url or "").strip()
    if not url:
        url = "sqlite:///./noteai.db"

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]

    parsed = make_url(url)
    driver = str(parsed.drivername)

    if driver.startswith("sqlite"):
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

    if driver in ("postgresql", "postgres"):
        parsed = parsed.set(drivername="postgresql+psycopg2")

    host = (parsed.host or "").lower()
    query = dict(parsed.query)
    if "supabase" in host and "sslmode" not in query:
        query["sslmode"] = "require"
        parsed = parsed.set(query=query)

    return parsed.render_as_string(hide_password=False)


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
else:
    # Postgres는 연결이 끊겨도 다시 붙도록 풀을 점검합니다.
    _engine_kwargs["pool_pre_ping"] = True
    _engine_kwargs["pool_recycle"] = 280
    _engine_kwargs["pool_size"] = 5
    _engine_kwargs["max_overflow"] = 5

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


def require_persistent_database() -> None:
    """
    Render처럼 디스크가 날아가는 환경에서 SQLite를 쓰면
    회원/노트/이력이 재배포마다 사라집니다. 기동을 막아 실수를 알립니다.
    """
    if not is_hosted_runtime():
        return
    if _IS_SQLITE:
        raise RuntimeError(
            "호스팅 환경에서 SQLite는 재배포마다 회원 데이터가 사라집니다. "
            "Render Postgres 또는 Supabase의 DATABASE_URL(postgresql://...)을 설정하세요."
        )


def database_kind() -> str:
    """헬스 체크용 DB 종류. 비밀번호는 넣지 않습니다."""
    return "sqlite" if _IS_SQLITE else "postgresql"


def _describe_database() -> str:
    """로그에 비밀번호 없이 DB 종류를 남깁니다."""
    parsed = make_url(DATABASE_URL)
    if str(parsed.drivername).startswith("sqlite"):
        return f"SQLite file={parsed.database}"
    return (
        f"PostgreSQL host={parsed.host} db={parsed.database} "
        f"user={parsed.username}"
    )


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
    from features.vita.models import VitaCertificate, VitaPublication, VitaTeaching


def _ensure_upload_url_columns():
    """
    이미 만들어진 테이블에 Cloudinary URL 컬럼을 추가합니다.

    create_all은 새 테이블만 만들고 기존 테이블에는 컬럼을 넣지 않습니다.
    """
    inspector = inspect(engine)
    specs = (
        ("media_assets", "public_url", "VARCHAR(1024) DEFAULT ''"),
        ("media_assets", "cloudinary_id", "VARCHAR(255) DEFAULT ''"),
        ("lecture_materials", "public_url", "VARCHAR(1024) DEFAULT ''"),
        ("lecture_materials", "cloudinary_id", "VARCHAR(255) DEFAULT ''"),
    )
    existing_tables = set(inspector.get_table_names())
    for table, column, ddl in specs:
        if table not in existing_tables:
            continue
        columns = {col["name"] for col in inspector.get_columns(table)}
        if column in columns:
            continue
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))

    # 기존 Postgres 컬럼이 VARCHAR(512)이면 Cloudinary URL이 잘릴 수 있습니다.
    #
    # 주의: 이 ALTER를 재배포마다 무조건 실행하면 테이블을 통째로 다시 쓰고,
    # DDL 권한이 없는 DB에서는 예외가 나서 init_db() 전체가 실패합니다.
    # (그러면 앱이 아예 뜨지 않아 "데이터가 사라진 것처럼" 보입니다.)
    # 그래서 실제로 길이가 모자랄 때만 딱 한 번 넓히고, 실패해도 기동은 계속합니다.
    if _IS_SQLITE:
        return

    inspector = inspect(engine)  # ADD COLUMN 이후 상태를 다시 읽습니다.
    for table in ("media_assets", "lecture_materials"):
        if table not in existing_tables:
            continue

        current_length = None
        for col in inspector.get_columns(table):
            if col["name"] == "public_url":
                current_length = getattr(col["type"], "length", None)
                break

        # length가 None이면 TEXT처럼 제한이 없다는 뜻이므로 건드리지 않습니다.
        if current_length is None or current_length >= 1024:
            continue

        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        f"ALTER TABLE {table} ALTER COLUMN public_url TYPE VARCHAR(1024)"
                    )
                )
        except Exception as exc:  # noqa: BLE001 - 기동을 막지 않습니다
            print(f"⚠️ {table}.public_url 길이 확장을 건너뜁니다: {exc}")


def init_db():
    """
    데이터베이스 초기화 (애플리케이션 시작 시 호출)
    모든 테이블 생성
    """
    require_persistent_database()
    require_persistent_storage()
    register_models()

    Base.metadata.create_all(bind=engine)
    _ensure_upload_url_columns()
    print("✅ 데이터베이스 초기화 완료")
    print(f"💾 {_describe_database()}")

    # 재배포 후 데이터가 남는지 로그만 보고 판단할 수 있게 저장 위치를 찍습니다.
    if is_cloudinary_configured():
        print("☁️ 업로드 저장소: Cloudinary (재배포 후에도 파일 유지)")
    else:
        print("📁 업로드 저장소: 로컬 uploads/ (개발 전용 - 호스팅에서는 사라집니다)")
