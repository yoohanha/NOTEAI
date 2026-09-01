"""
기동 복원력 테스트

배경:
startup 이벤트에서 예외가 나면 uvicorn이 종료 코드 3(STARTUP_FAILURE)으로
죽습니다. Render는 그 배포를 실패 처리하고 **직전에 성공한 빌드를 계속
서빙**하므로, 설정 실수 하나가 "새 코드가 영영 반영되지 않는" 상태를
만듭니다. 그래서 설정 문제는 예외가 아니라 degraded 상태로 드러내야 합니다.

데이터 유실 방어는 기동을 막는 대신 upload_bytes()가 담당합니다.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import core.database as db_module
import core.storage as storage_module
from core.database import check_persistent_database
from core.storage import check_persistent_storage, upload_bytes


class TestChecksReportInsteadOfRaising:
    """설정 점검 함수는 예외 대신 설명을 돌려줘야 합니다."""

    def test_storage_check_returns_text_when_hosted_without_cloudinary(self, monkeypatch):
        monkeypatch.setenv("RENDER", "true")
        monkeypatch.setattr(storage_module, "is_cloudinary_configured", lambda: False)

        problem = check_persistent_storage()

        assert problem is not None
        # 어떤 키가 비었는지 이름이 들어 있어야 조치가 가능합니다.
        assert "CLOUDINARY_CLOUD_NAME" in problem

    def test_storage_check_is_quiet_when_configured(self, monkeypatch):
        monkeypatch.setenv("RENDER", "true")
        monkeypatch.setattr(storage_module, "is_cloudinary_configured", lambda: True)

        assert check_persistent_storage() is None

    def test_storage_check_is_quiet_off_hosting(self, monkeypatch):
        monkeypatch.delenv("RENDER", raising=False)
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        monkeypatch.delenv("FLY_APP_NAME", raising=False)
        monkeypatch.setattr(storage_module, "is_cloudinary_configured", lambda: False)

        assert check_persistent_storage() is None

    def test_database_check_returns_text_for_sqlite_on_hosting(self, monkeypatch):
        monkeypatch.setenv("RENDER", "true")
        monkeypatch.setattr(db_module, "_IS_SQLITE", True)

        problem = check_persistent_database()

        assert problem is not None
        assert "DATABASE_URL" in problem

    def test_database_check_is_quiet_on_postgres(self, monkeypatch):
        monkeypatch.setenv("RENDER", "true")
        monkeypatch.setattr(db_module, "_IS_SQLITE", False)

        assert check_persistent_database() is None


class TestDataLossStillBlocked:
    """
    기동을 허용한 대신, 실제로 데이터를 잃는 지점은 그대로 막혀 있어야 합니다.
    """

    def test_hosted_upload_still_refuses_local_disk(self, monkeypatch):
        monkeypatch.setenv("RENDER", "true")
        monkeypatch.setattr(storage_module, "is_cloudinary_configured", lambda: False)

        # 로컬 디스크에 조용히 쓰는 대신 오류를 내야 합니다.
        with pytest.raises(ValueError, match="Cloudinary"):
            upload_bytes(
                b"png-bytes",
                folder="noteai/media/1",
                resource_type="image",
                filename="shot.png",
            )


class TestHealthReportsDegraded:
    """
    /api/health 는 문제가 있어도 200을 돌려줘야 합니다.
    (render.yaml의 healthCheckPath가 여기라, 500이면 배포가 실패합니다.)
    """

    def test_healthy_when_no_problems(self, client):
        import main

        monkeyed = list(main.STARTUP_PROBLEMS)
        main.STARTUP_PROBLEMS.clear()
        try:
            response = client.get("/api/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
            assert response.json()["problems"] == []
        finally:
            main.STARTUP_PROBLEMS.extend(monkeyed)

    def test_degraded_but_still_200_when_problems(self, client):
        import main

        original = list(main.STARTUP_PROBLEMS)
        main.STARTUP_PROBLEMS.clear()
        main.STARTUP_PROBLEMS.append("DATABASE_URL 이 비었습니다")
        try:
            response = client.get("/api/health")

            # 200이어야 Render 헬스체크를 통과해 배포가 살아남습니다.
            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "degraded"
            assert body["problems"] == ["DATABASE_URL 이 비었습니다"]
        finally:
            main.STARTUP_PROBLEMS.clear()
            main.STARTUP_PROBLEMS.extend(original)

    def test_reports_running_commit(self, client):
        body = client.get("/api/health").json()

        # 배포가 실제로 나갔는지 판별하는 값이라 비어 있으면 안 됩니다.
        assert body["commit"]
        assert body["commit"] != ""
