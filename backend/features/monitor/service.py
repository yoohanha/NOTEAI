"""
모니터링 서비스
- 수집 사이클 실행 이력 기록/조회
- 워커 생존 상태 판정
- 대시보드용 통합 상태 집계
- 오래된 이력 정리
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from core.config import settings
from features.monitor import diagnostics, lockfile
from features.monitor.models import CollectionRun
from features.trends.models import TrendItem


class MonitorService:
    """백그라운드 수집 모니터링 비즈니스 로직"""

    @staticmethod
    def record_run(
        db: Session,
        status: str,
        started_at: datetime,
        finished_at: datetime,
        fetched: int = 0,
        saved: int = 0,
        duplicates: int = 0,
        sources_used: Optional[List[str]] = None,
        errors: Optional[List[str]] = None,
        error_message: Optional[str] = None,
        consecutive_failures: int = 0,
    ) -> CollectionRun:
        """
        수집 사이클 1회의 실행 결과를 기록

        Args:
            db: 데이터베이스 세션
            status: success | partial | failed
            started_at: 시작 시각
            finished_at: 종료 시각
            fetched: 수집 시도 항목 수
            saved: 신규 저장 수
            duplicates: 중복 수
            sources_used: 사용한 소스 key 목록
            errors: 소스별 오류 메시지
            error_message: 사이클 전체 실패 시 예외 메시지
            consecutive_failures: 현재 연속 실패 횟수

        Returns:
            저장된 실행 기록
        """
        run = CollectionRun(
            status=status,
            fetched=fetched,
            saved=saved,
            duplicates=duplicates,
            sources_used=sources_used or [],
            errors=errors or [],
            error_message=error_message,
            duration_seconds=(finished_at - started_at).total_seconds(),
            consecutive_failures=consecutive_failures,
            started_at=started_at,
            finished_at=finished_at,
        )

        db.add(run)

        try:
            db.commit()
            db.refresh(run)
        except Exception:
            db.rollback()
            raise

        return run

    @staticmethod
    def cleanup_old_runs(db: Session, retention_days: Optional[int] = None) -> int:
        """
        보관 기간이 지난 실행 이력을 삭제

        24시간 상주 워커는 이력을 무한히 쌓으므로 주기적 정리가 필요합니다.

        Args:
            db: 데이터베이스 세션
            retention_days: 보관 일수 (None이면 설정값)

        Returns:
            삭제된 행 수
        """
        days = retention_days or settings.MONITOR_RETENTION_DAYS
        cutoff = datetime.utcnow() - timedelta(days=days)

        deleted = (
            db.query(CollectionRun)
            .filter(CollectionRun.started_at < cutoff)
            .delete(synchronize_session=False)
        )

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        return int(deleted or 0)

    @staticmethod
    def get_recent_runs(db: Session, limit: int = 20) -> List[CollectionRun]:
        """
        최근 실행 이력 조회 (최신순)

        Args:
            db: 데이터베이스 세션
            limit: 조회할 개수

        Returns:
            실행 기록 목록
        """
        return (
            db.query(CollectionRun)
            .order_by(desc(CollectionRun.started_at))
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_stats(db: Session, hours: int = 24) -> Dict[str, Any]:
        """
        최근 N시간의 수집 통계 집계

        Args:
            db: 데이터베이스 세션
            hours: 집계 기간

        Returns:
            통계 딕셔너리
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        rows = (
            db.query(
                CollectionRun.status,
                func.count(CollectionRun.id),
                func.coalesce(func.sum(CollectionRun.saved), 0),
                func.coalesce(func.sum(CollectionRun.fetched), 0),
                func.coalesce(func.avg(CollectionRun.duration_seconds), 0.0),
            )
            .filter(CollectionRun.started_at >= cutoff)
            .group_by(CollectionRun.status)
            .all()
        )

        by_status = {"success": 0, "partial": 0, "failed": 0}
        total_saved = 0
        total_fetched = 0
        weighted_duration = 0.0
        total_runs = 0

        for status, count, saved, fetched, avg_duration in rows:
            by_status[status] = int(count)
            total_runs += int(count)
            total_saved += int(saved or 0)
            total_fetched += int(fetched or 0)
            weighted_duration += float(avg_duration or 0.0) * int(count)

        # 성공률은 partial도 수집 자체는 성공한 것으로 계산
        succeeded = by_status["success"] + by_status["partial"]
        success_rate = (succeeded / total_runs) if total_runs else 0.0

        return {
            "window_hours": hours,
            "total_runs": total_runs,
            "success_runs": by_status["success"],
            "partial_runs": by_status["partial"],
            "failed_runs": by_status["failed"],
            "success_rate": round(success_rate, 4),
            "total_saved": total_saved,
            "total_fetched": total_fetched,
            "avg_duration_seconds": round(
                weighted_duration / total_runs if total_runs else 0.0, 3
            ),
        }

    @staticmethod
    def get_worker_state(db: Session) -> Dict[str, Any]:
        """
        워커 프로세스의 현재 상태를 판정

        잠금 파일의 PID로 생존을 확인하고, 마지막 실행 시각이
        예상 주기를 크게 넘겼으면 stale로 표시합니다.

        Args:
            db: 데이터베이스 세션

        Returns:
            워커 상태 딕셔너리
        """
        pid = lockfile.get_active_worker_pid()

        last_run = (
            db.query(CollectionRun)
            .order_by(desc(CollectionRun.started_at))
            .first()
        )

        last_run_at = last_run.started_at if last_run else None
        last_status = last_run.status if last_run else None
        consecutive_failures = last_run.consecutive_failures if last_run else 0

        interval = settings.MONITOR_INTERVAL_SECONDS
        next_run_estimate = None
        stale = False

        if last_run_at is not None:
            next_run_estimate = last_run_at + timedelta(seconds=interval)

            # 예상 주기의 2배를 넘겨도 실행되지 않았으면 정체된 것으로 판단
            deadline = last_run_at + timedelta(seconds=interval * 2)
            stale = datetime.utcnow() > deadline

        return {
            "running": pid is not None,
            "pid": pid,
            "last_run_at": last_run_at,
            "last_status": last_status,
            "next_run_estimate": next_run_estimate,
            "consecutive_failures": consecutive_failures,
            "stale": stale,
        }

    @staticmethod
    def get_status(
        db: Session,
        hours: int = 24,
        recent_limit: int = 10,
    ) -> Dict[str, Any]:
        """
        대시보드용 통합 상태 조회

        워커 상태 + 수집 통계 + 자가 진단 + 최근 이력을 한 번에 반환하여
        대시보드가 여러 번 요청하지 않도록 합니다.

        Args:
            db: 데이터베이스 세션
            hours: 집계/진단 기간
            recent_limit: 최근 이력 개수

        Returns:
            통합 상태 딕셔너리
        """
        runs = MonitorService.get_recent_runs(db, limit=recent_limit)

        return {
            "worker": MonitorService.get_worker_state(db),
            "stats": MonitorService.get_stats(db, hours=hours),
            "diagnosis": diagnostics.diagnose(hours=hours),
            "recent_runs": [MonitorService._run_to_dict(run) for run in runs],
            "total_trends": db.query(func.count(TrendItem.id)).scalar() or 0,
            "checked_at": datetime.utcnow(),
        }

    @staticmethod
    def _run_to_dict(run: CollectionRun) -> Dict[str, Any]:
        """
        CollectionRun ORM 객체를 직렬화 가능한 딕셔너리로 변환

        Args:
            run: 실행 기록

        Returns:
            딕셔너리
        """
        return {
            "id": run.id,
            "status": run.status,
            "fetched": run.fetched or 0,
            "saved": run.saved or 0,
            "duplicates": run.duplicates or 0,
            "sources_used": run.sources_used or [],
            "errors": run.errors or [],
            "error_message": run.error_message,
            "duration_seconds": run.duration_seconds or 0.0,
            "consecutive_failures": run.consecutive_failures or 0,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
        }


# 서비스 인스턴스
monitor_service = MonitorService()
