"""
Monitor(백그라운드 수집 모니터링) 단위 및 통합 테스트

- diagnostics: 로그 파싱, 증상 분류, 판정
- lockfile: 프로세스 생존 확인, 중복 실행 차단
- service: 실행 이력 기록, 통계 집계, 워커 상태 판정
- worker: 백오프 계산, 정상 종료
- routes: 모니터링 API
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from features.monitor import diagnostics, lockfile
from features.monitor.models import CollectionRun
from features.monitor.service import monitor_service


# ============ Fixtures ============

@pytest.fixture
def log_file(tmp_path: Path) -> Path:
    """진단 대상 로그 파일 경로"""
    return tmp_path / "monitor.log"


def write_log(path: Path, entries: list) -> None:
    """
    테스트용 로그 파일을 작성합니다.

    Args:
        path: 로그 파일 경로
        entries: (레벨, 메시지) 튜플 목록. 시각은 현재 시각으로 기록됩니다.
    """
    now = datetime.utcnow()
    lines = [
        f"{now.strftime('%Y-%m-%d %H:%M:%S')} | {level} | monitor.worker | {message}"
        for level, message in entries
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ============ diagnostics 단위 테스트 ============

class TestLogParsing:
    """로그 파싱"""

    def test_reads_and_parses_entries(self, log_file: Path):
        write_log(log_file, [("INFO", "시작"), ("ERROR", "실패")])

        entries = diagnostics.read_recent_logs(log_path=log_file)

        assert len(entries) == 2
        assert entries[0].level == "INFO"
        assert entries[1].message == "실패"

    def test_missing_file_returns_empty(self, tmp_path: Path):
        entries = diagnostics.read_recent_logs(log_path=tmp_path / "없음.log")
        assert entries == []

    def test_appends_traceback_lines_to_previous_entry(self, log_file: Path):
        """포맷에 맞지 않는 스택 트레이스는 직전 항목에 이어붙어야 합니다."""
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write_text(
            f"{now} | ERROR | monitor | 수집 실패\n"
            "Traceback (most recent call last):\n"
            "  File 'x.py', line 1\n",
            encoding="utf-8",
        )

        entries = diagnostics.read_recent_logs(log_path=log_file)

        assert len(entries) == 1
        assert "Traceback" in entries[0].message

    def test_filters_by_since(self, log_file: Path):
        """기간 밖의 로그는 제외되어야 합니다."""
        old = (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        new = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        log_file.write_text(
            f"{old} | ERROR | monitor | 오래된 오류\n"
            f"{new} | ERROR | monitor | 최근 오류\n",
            encoding="utf-8",
        )

        entries = diagnostics.read_recent_logs(
            since=datetime.utcnow() - timedelta(hours=1), log_path=log_file
        )

        assert len(entries) == 1
        assert entries[0].message == "최근 오류"


class TestClassification:
    """오류 증상 분류"""

    @pytest.mark.parametrize("message,expected_code", [
        ("database is locked", "DB_LOCKED"),
        ("no such table: notes", "DB_SCHEMA_MISSING"),
        ("소스 실패: HTTP 401", "AUTH_FAILED"),
        ("HTTP 429 rate limit", "RATE_LIMITED"),
        ("소스 실패: HTTP 404", "FEED_NOT_FOUND"),
        ("HTTP 503", "SERVER_ERROR"),
        ("요청 시간 초과", "NETWORK_TIMEOUT"),
        ("네트워크 오류 (ConnectError)", "NETWORK_UNREACHABLE"),
        ("피드 XML 파싱 실패", "XML_PARSE_ERROR"),
        ("No space left on device", "DISK_FULL"),
        ("Permission denied", "PERMISSION_DENIED"),
    ])
    def test_classifies_known_symptoms(self, message, expected_code):
        symptom = diagnostics.classify(message)

        assert symptom is not None
        assert symptom.code == expected_code

    def test_unknown_message_returns_none(self):
        assert diagnostics.classify("완전히 처음 보는 오류") is None


class TestDiagnose:
    """종합 진단"""

    def test_healthy_when_no_problems(self, log_file: Path):
        write_log(log_file, [("INFO", "수집 완료"), ("INFO", "대기")])

        report = diagnostics.diagnose(log_path=log_file)

        assert report["verdict"] == "healthy"
        assert report["findings"] == []

    def test_unknown_when_no_logs(self, tmp_path: Path):
        report = diagnostics.diagnose(log_path=tmp_path / "없음.log")
        assert report["verdict"] == "unknown"

    def test_unhealthy_on_critical(self, log_file: Path):
        write_log(log_file, [("ERROR", "no such table: notes")])

        report = diagnostics.diagnose(log_path=log_file)

        assert report["verdict"] == "unhealthy"
        assert report["findings"][0]["severity"] == "critical"

    def test_degraded_on_transient_only(self, log_file: Path):
        """일시적 장애만 있으면 unhealthy가 아니라 degraded여야 합니다."""
        write_log(log_file, [("WARNING", "요청 시간 초과")])

        report = diagnostics.diagnose(log_path=log_file)

        assert report["verdict"] == "degraded"
        assert report["findings"][0]["transient"] is True

    def test_orders_findings_by_severity(self, log_file: Path):
        write_log(log_file, [
            ("WARNING", "HTTP 503"),            # low
            ("ERROR", "no such table: users"),  # critical
            ("ERROR", "HTTP 401"),              # high
        ])

        report = diagnostics.diagnose(log_path=log_file)
        severities = [f["severity"] for f in report["findings"]]

        assert severities == ["critical", "high", "low"]

    def test_counts_repeated_symptoms(self, log_file: Path):
        write_log(log_file, [("WARNING", "요청 시간 초과")] * 5)

        report = diagnostics.diagnose(log_path=log_file)

        assert report["findings"][0]["count"] == 5
        # 샘플은 최대 3건만 보관해 결과가 비대해지지 않아야 합니다
        assert len(report["findings"][0]["samples"]) <= 3

    def test_collects_unclassified_errors(self, log_file: Path):
        write_log(log_file, [("ERROR", "듣도 보도 못한 오류")])

        report = diagnostics.diagnose(log_path=log_file)

        assert report["verdict"] == "degraded"
        assert len(report["unclassified"]) == 1

    def test_summary_reports_warnings_when_no_errors(self, log_file: Path):
        """오류가 0건이면 경고 건수로 요약해야 합니다."""
        write_log(log_file, [("WARNING", "요청 시간 초과")])

        report = diagnostics.diagnose(log_path=log_file)

        assert "경고 1건" in report["summary"]


# ============ lockfile 단위 테스트 ============

class TestLockfile:
    """중복 실행 방지 잠금"""

    @pytest.fixture(autouse=True)
    def isolated_lock(self, tmp_path, monkeypatch):
        """테스트마다 격리된 잠금 파일을 사용합니다."""
        from core.config import settings
        monkeypatch.setattr(
            settings, "MONITOR_LOCK_FILE", str(tmp_path / "test.lock")
        )

    def test_current_process_is_alive(self):
        assert lockfile.is_process_alive(os.getpid()) is True

    def test_nonexistent_pid_is_not_alive(self):
        """존재하지 않는 PID는 죽은 것으로 판정되어야 합니다."""
        assert lockfile.is_process_alive(999999) is False

    def test_invalid_pid_is_not_alive(self):
        assert lockfile.is_process_alive(0) is False
        assert lockfile.is_process_alive(-1) is False

    def test_acquire_and_release(self):
        pid = lockfile.acquire()

        assert pid == os.getpid()
        assert lockfile.get_active_worker_pid() == os.getpid()

        lockfile.release()
        assert lockfile.get_active_worker_pid() is None

    def test_second_acquire_blocked(self):
        """잠금이 살아 있으면 두 번째 획득은 실패해야 합니다."""
        lockfile.acquire()

        try:
            with pytest.raises(lockfile.LockError):
                lockfile.acquire()
        finally:
            lockfile.release()

    def test_stale_lock_is_reclaimed(self):
        """죽은 프로세스가 남긴 잠금은 회수되어야 합니다."""
        path = lockfile.get_lock_path()
        path.write_text("999999\n2026-01-01T00:00:00\n", encoding="utf-8")

        # 죽은 PID이므로 획득에 성공해야 합니다
        assert lockfile.acquire() == os.getpid()
        lockfile.release()

    def test_corrupt_lock_file_is_tolerated(self):
        path = lockfile.get_lock_path()
        path.write_text("이건 PID가 아님\n", encoding="utf-8")

        assert lockfile.read_lock() == (None, None)
        assert lockfile.get_active_worker_pid() is None


# ============ service 통합 테스트 ============

class TestMonitorService:
    """실행 이력 및 상태 집계"""

    def test_record_run(self, db):
        started = datetime.utcnow()
        finished = started + timedelta(seconds=12)

        run = monitor_service.record_run(
            db, status="success", started_at=started, finished_at=finished,
            fetched=100, saved=10, duplicates=90, sources_used=["hackernews"],
        )

        assert run.id is not None
        assert run.duration_seconds == pytest.approx(12.0, abs=0.1)

    def test_stats_aggregation(self, db):
        now = datetime.utcnow()

        for status, saved in [("success", 10), ("partial", 5), ("failed", 0)]:
            monitor_service.record_run(
                db, status=status, started_at=now, finished_at=now,
                fetched=100, saved=saved,
            )

        stats = monitor_service.get_stats(db, hours=24)

        assert stats["total_runs"] == 3
        assert stats["success_runs"] == 1
        assert stats["partial_runs"] == 1
        assert stats["failed_runs"] == 1
        assert stats["total_saved"] == 15
        # partial도 수집 자체는 성공이므로 성공률에 포함됩니다
        # 서비스가 소수 4자리로 반올림하므로 허용오차를 그에 맞춥니다
        assert stats["success_rate"] == pytest.approx(2 / 3, abs=1e-4)

    def test_stats_excludes_old_runs(self, db):
        old = datetime.utcnow() - timedelta(days=5)
        monitor_service.record_run(
            db, status="success", started_at=old, finished_at=old, saved=99
        )

        stats = monitor_service.get_stats(db, hours=24)
        assert stats["total_runs"] == 0

    def test_cleanup_removes_old_runs(self, db):
        old = datetime.utcnow() - timedelta(days=30)
        recent = datetime.utcnow()

        monitor_service.record_run(db, status="success", started_at=old, finished_at=old)
        monitor_service.record_run(
            db, status="success", started_at=recent, finished_at=recent
        )

        deleted = monitor_service.cleanup_old_runs(db, retention_days=14)

        assert deleted == 1
        assert db.query(CollectionRun).count() == 1

    def test_worker_state_when_stopped(self, db, tmp_path, monkeypatch):
        from core.config import settings
        monkeypatch.setattr(
            settings, "MONITOR_LOCK_FILE", str(tmp_path / "none.lock")
        )

        state = monitor_service.get_worker_state(db)

        assert state["running"] is False
        assert state["pid"] is None

    def test_worker_state_detects_stale(self, db, tmp_path, monkeypatch):
        """주기의 2배를 넘겨 실행되지 않으면 정체로 판정해야 합니다."""
        from core.config import settings
        monkeypatch.setattr(settings, "MONITOR_LOCK_FILE", str(tmp_path / "n.lock"))
        monkeypatch.setattr(settings, "MONITOR_INTERVAL_SECONDS", 60)

        long_ago = datetime.utcnow() - timedelta(seconds=300)
        monitor_service.record_run(
            db, status="success", started_at=long_ago, finished_at=long_ago
        )

        assert monitor_service.get_worker_state(db)["stale"] is True

    def test_get_status_bundles_everything(self, db, tmp_path, monkeypatch):
        from core.config import settings
        monkeypatch.setattr(settings, "MONITOR_LOCK_FILE", str(tmp_path / "n.lock"))

        now = datetime.utcnow()
        monitor_service.record_run(
            db, status="success", started_at=now, finished_at=now, saved=5
        )

        status = monitor_service.get_status(db)

        assert "worker" in status
        assert "stats" in status
        assert "diagnosis" in status
        assert len(status["recent_runs"]) == 1


# ============ 워커 단위 테스트 ============

class TestWorkerBackoff:
    """백오프 및 종료 처리"""

    @pytest.fixture
    def worker(self):
        from monitor_worker import CollectorWorker
        return CollectorWorker(interval=1800)

    def test_normal_delay_near_interval(self, worker):
        """정상 시에는 주기 ±10% 범위여야 합니다."""
        for _ in range(20):
            delay = worker.compute_delay()
            assert 1620 <= delay <= 1980

    def test_backoff_grows_with_failures(self, worker):
        worker.consecutive_failures = 1
        first = worker.compute_delay()

        worker.consecutive_failures = 3
        third = worker.compute_delay()

        assert third > first

    def test_backoff_respects_ceiling(self, worker):
        """실패가 아무리 쌓여도 상한을 크게 넘지 않아야 합니다."""
        from core.config import settings

        worker.consecutive_failures = 50
        # 지터(±10%)를 감안한 상한
        assert worker.compute_delay() <= settings.MONITOR_BACKOFF_MAX * 1.1

    def test_delay_never_below_floor(self, worker):
        """busy loop을 막기 위한 최소 대기가 보장되어야 합니다."""
        worker.interval = 1
        worker.consecutive_failures = 0
        assert worker.compute_delay() >= 5.0

    def test_shutdown_flag_is_set(self, worker):
        assert worker._shutdown.is_set() is False

        worker.request_shutdown()
        assert worker._shutdown.is_set() is True


class TestEmbeddedAutostart:
    """FastAPI 내장 워커 기동 조건"""

    def test_disabled_by_env(self, monkeypatch):
        from monitor_worker import _should_autostart_worker

        monkeypatch.setenv("NOTEAI_DISABLE_WORKER", "1")
        assert _should_autostart_worker() is False


# ============ API 통합 테스트 ============

class TestMonitorAPI:
    """모니터링 API 엔드포인트"""

    def test_status_requires_auth(self, client):
        assert client.get("/api/monitor/status").status_code in (401, 403)

    def test_status_returns_bundle(self, client, auth_headers):
        response = client.get("/api/monitor/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert "worker" in data and "stats" in data and "diagnosis" in data

    def test_runs_endpoint(self, client, auth_headers, db):
        now = datetime.utcnow()
        monitor_service.record_run(
            db, status="success", started_at=now, finished_at=now, saved=3
        )

        response = client.get("/api/monitor/runs?limit=5", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["data"]["total"] == 1

    def test_diagnose_endpoint(self, client, auth_headers):
        response = client.get("/api/monitor/diagnose?hours=24", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["data"]["verdict"] in (
            "healthy", "degraded", "unhealthy", "unknown"
        )

    def test_rejects_out_of_range_params(self, client, auth_headers):
        """검증 범위를 벗어난 파라미터는 422여야 합니다."""
        assert client.get(
            "/api/monitor/status?hours=99999", headers=auth_headers
        ).status_code == 422
