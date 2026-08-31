"""DATABASE_URL 정규화 및 호스팅 SQLite 차단"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from core.database import require_persistent_database, resolve_database_url


def test_postgres_url_uses_psycopg2():
    url = resolve_database_url("postgres://noteai:secret@db.example:5432/noteai")
    assert url.startswith("postgresql+psycopg2://")
    assert "secret" in url
    assert "db.example" in url


def test_supabase_url_adds_ssl():
    url = resolve_database_url(
        "postgresql://postgres.abc:pw@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres"
    )
    assert "sslmode=require" in url
    assert url.startswith("postgresql+psycopg2://")


def test_hosted_runtime_rejects_sqlite(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    try:
        require_persistent_database()
    except RuntimeError as exc:
        message = str(exc)
        assert "SQLite" in message
        assert "DATABASE_URL" in message
    finally:
        monkeypatch.delenv("RENDER", raising=False)
