"""
NOTEAI 24시간 백그라운드 수집 워커

주기적으로 외부 RSS/뉴스 API에서 기술 트렌드를 수집하여 DB를 갱신하고,
대시보드가 항상 최신 데이터를 읽을 수 있도록 유지합니다.
오류가 발생하면 로그 자가 진단을 실행해 원인과 조치를 로그에 남깁니다.

실행:
    python monitor_worker.py                  # 기본 주기로 상주 실행
    python monitor_worker.py --once           # 1회만 수집하고 종료
    python monitor_worker.py --interval 600   # 10분 주기로 실행
    python monitor_worker.py --diagnose       # 진단만 실행하고 종료
    python monitor_worker.py --status         # 현재 상태 출력 후 종료

종료:
    Ctrl+C (SIGINT) 또는 SIGTERM - 진행 중인 사이클을 마치고 안전하게 종료

설계 요점:
  - 단일 인스턴스 보장: PID 잠금 파일로 중복 실행 차단
  - 지수 백오프: 연속 실패 시 대기 시간을 늘려 외부 API 부하를 줄임
  - 지터: 주기에 무작위 편차를 주어 요청이 한 시점에 몰리지 않게 함
  - 오류 격리: 한 사이클의 실패가 워커 전체를 중단시키지 않음
  - 자가 진단: 실패 시 로그를 분석해 원인/조치를 제시
"""

import argparse
import asyncio
import json
import os
import random
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# 이 스크립트는 backend/ 에서 직접 실행되므로 모듈 경로를 보장
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.config import settings                       # noqa: E402
from core.database import SessionLocal, init_db, register_models  # noqa: E402
from core.logging_config import setup_logging          # noqa: E402
from features.monitor import diagnostics, lockfile     # noqa: E402
from features.monitor.service import monitor_service   # noqa: E402
from features.trends.schemas import RefreshRequest     # noqa: E402
from features.trends.service import trend_service      # noqa: E402

logger = setup_logging("monitor")


class CollectorWorker:
    """주기적 수집을 수행하는 상주 워커"""

    def __init__(
        self,
        interval: Optional[int] = None,
        limit_per_source: Optional[int] = None,
        run_once: bool = False,
    ):
        """
        Args:
            interval: 수집 주기 (초). None이면 설정값 사용
            limit_per_source: 소스당 최대 수집 항목 수
            run_once: True면 1회만 실행하고 종료
        """
        self.interval = interval or settings.MONITOR_INTERVAL_SECONDS
        self.limit_per_source = limit_per_source or settings.MONITOR_LIMIT_PER_SOURCE
        self.run_once = run_once

        # 연속 실패 횟수 - 백오프 계산과 진단 트리거에 사용
        self.consecutive_failures = 0

        # 종료 신호를 받으면 set 되어 대기 중이던 sleep을 즉시 깨움
        self._shutdown = asyncio.Event()

        # 통계 (프로세스 생존 기간 기준)
        self.cycles_completed = 0
        self.total_saved = 0
        self.started_at = datetime.utcnow()

    # ============ 종료 처리 ============

    def request_shutdown(self, signum=None, frame=None) -> None:
        """
        종료 요청 처리 (시그널 핸들러)

        진행 중인 사이클을 강제로 끊지 않고, 사이클 종료 후 빠져나가도록
        플래그만 세웁니다.

        Args:
            signum: 시그널 번호
            frame: 스택 프레임 (사용하지 않음)
        """
        if self._shutdown.is_set():
            return

        name = signal.Signals(signum).name if signum else "요청"
        logger.info("종료 신호 수신(%s) - 현재 사이클을 마치고 종료합니다", name)

        self._shutdown.set()

    def install_signal_handlers(self) -> None:
        """
        플랫폼이 지원하는 종료 시그널에 핸들러를 등록

        Windows는 SIGTERM/SIGHUP을 지원하지 않으므로 지원되는 것만 등록합니다.
        """
        loop = asyncio.get_running_loop()

        for sig_name in ("SIGINT", "SIGTERM", "SIGBREAK"):
            sig = getattr(signal, sig_name, None)

            if sig is None:
                continue

            try:
                # POSIX에서는 이벤트 루프에 직접 등록하는 편이 안전
                loop.add_signal_handler(sig, self.request_shutdown, sig, None)
            except (NotImplementedError, RuntimeError, ValueError, AttributeError):
                # Windows 등 add_signal_handler 미지원 환경은 signal.signal로 대체
                try:
                    signal.signal(sig, self.request_shutdown)
                except (OSError, ValueError, RuntimeError):
                    # 등록할 수 없는 시그널은 건너뜀
                    continue

    # ============ 백오프 계산 ============

    def compute_delay(self) -> float:
        """
        다음 사이클까지의 대기 시간을 계산

        정상 시에는 설정 주기에 지터를 적용하고, 연속 실패 시에는
        지수 백오프로 대기 시간을 늘려 외부 API 부하와 로그 폭주를 막습니다.

        Returns:
            대기 시간 (초)
        """
        if self.consecutive_failures == 0:
            base = float(self.interval)
        else:
            # 2^(실패횟수-1) 배씩 증가, 상한으로 제한
            multiplier = 2 ** (self.consecutive_failures - 1)
            base = float(
                min(
                    settings.MONITOR_BACKOFF_BASE * multiplier,
                    settings.MONITOR_BACKOFF_MAX,
                )
            )

        # 지터 적용 (±ratio) - 여러 인스턴스의 요청 시점 분산
        ratio = max(0.0, min(settings.MONITOR_JITTER_RATIO, 0.5))
        jitter = base * ratio * random.uniform(-1.0, 1.0)

        # 최소 5초는 보장하여 과도한 busy loop 방지
        return max(5.0, base + jitter)

    # ============ 수집 사이클 ============

    async def run_cycle(self) -> bool:
        """
        수집 사이클 1회 실행

        예외를 절대 밖으로 던지지 않습니다. 사이클 실패는 기록하고
        다음 주기에 재시도합니다.

        Returns:
            수집이 성공(또는 부분 성공)했으면 True
        """
        started_at = datetime.utcnow()
        db = SessionLocal()

        status = "failed"
        error_message = None
        result = None

        try:
            logger.info(
                "수집 사이클 시작 (소스당 최대 %d건)", self.limit_per_source
            )

            result = await trend_service.refresh(
                db,
                RefreshRequest(
                    limit_per_source=self.limit_per_source,
                    persist=True,
                ),
            )

            # 일부 소스만 실패한 경우 partial - 수집 자체는 성공으로 취급
            status = "partial" if result["errors"] else "success"

            logger.info(
                "수집 완료 [%s] 시도 %d건 / 저장 %d건 / 중복 %d건 / 소스 %d개",
                status,
                result["fetched"],
                result["saved"],
                result["duplicates"],
                len(result["sources_used"]),
            )

            # 소스별 실패는 경고로 남겨 진단 루틴이 집계할 수 있게 함
            for error in result["errors"]:
                logger.warning("소스 수집 실패: %s", error)

            self.total_saved += result["saved"]

        except Exception as exc:
            status = "failed"
            error_message = f"{type(exc).__name__}: {exc}"

            # 스택 트레이스를 남겨야 원인 추적이 가능
            logger.error("수집 사이클 실패: %s", error_message, exc_info=True)

        finally:
            finished_at = datetime.utcnow()

            # 실패 횟수는 이력 기록 전에 갱신해야 올바른 값이 저장됨
            if status == "failed":
                self.consecutive_failures += 1
            else:
                self.consecutive_failures = 0

            try:
                monitor_service.record_run(
                    db,
                    status=status,
                    started_at=started_at,
                    finished_at=finished_at,
                    fetched=result["fetched"] if result else 0,
                    saved=result["saved"] if result else 0,
                    duplicates=result["duplicates"] if result else 0,
                    sources_used=result["sources_used"] if result else [],
                    errors=result["errors"] if result else [],
                    error_message=error_message,
                    consecutive_failures=self.consecutive_failures,
                )
            except Exception as exc:
                # 이력 기록 실패가 워커를 멈추면 안 됨
                logger.error("실행 이력 기록 실패: %s", exc)

            db.close()

            self.cycles_completed += 1

        return status != "failed"

    # ============ 자가 진단 ============

    def self_diagnose(self, reason: str) -> dict:
        """
        로그 자가 진단을 실행하고 결과를 로그에 남김

        Args:
            reason: 진단을 트리거한 사유 (로그에 기록)

        Returns:
            진단 결과 딕셔너리
        """
        logger.info("자가 진단 실행 (사유: %s)", reason)

        try:
            report = diagnostics.diagnose(hours=24)
        except Exception as exc:
            # 진단 자체가 실패해도 워커는 계속 돌아야 함
            logger.error("자가 진단 실패: %s", exc, exc_info=True)
            return {"verdict": "unknown", "summary": str(exc), "findings": []}

        verdict = report["verdict"]
        logger.info("진단 결과 [%s] %s", verdict.upper(), report["summary"])

        for finding in report["findings"]:
            logger.info(
                "  · [%s/%s] %s %d건 | 원인: %s | 조치: %s",
                finding["severity"].upper(),
                finding["code"],
                finding["label"],
                finding["count"],
                finding["cause"],
                finding["action"],
            )

        for message in report["unclassified"]:
            logger.info("  · [미분류] %s", message)

        if verdict == "unhealthy":
            logger.critical(
                "수집기가 비정상 상태입니다. 위 권장 조치를 확인하세요."
            )

        return report

    # ============ 유지보수 ============

    def housekeeping(self) -> None:
        """
        오래된 실행 이력 정리

        24시간 상주 운영에서 이력이 무한히 쌓이는 것을 방지합니다.
        """
        db = SessionLocal()

        try:
            deleted = monitor_service.cleanup_old_runs(db)

            if deleted:
                logger.info(
                    "오래된 실행 이력 %d건 정리 (보관 %d일)",
                    deleted,
                    settings.MONITOR_RETENTION_DAYS,
                )
        except Exception as exc:
            logger.warning("이력 정리 실패: %s", exc)
        finally:
            db.close()

    # ============ 메인 루프 ============

    async def run(self, install_signals: bool = True) -> int:
        """
        워커 메인 루프

        Args:
            install_signals: True면 SIGINT/SIGTERM 핸들러를 등록합니다.
                FastAPI에 내장될 때는 uvicorn이 시그널을 처리하므로 False.

        Returns:
            프로세스 종료 코드 (0 정상)
        """
        if install_signals:
            self.install_signal_handlers()

        logger.info("=" * 62)
        logger.info(
            "NOTEAI 수집 워커 시작 | PID %d | 주기 %d초 | 소스당 %d건",
            lockfile.read_lock()[0] or -1,
            self.interval,
            self.limit_per_source,
        )
        logger.info("=" * 62)

        # 테이블이 없으면 첫 사이클이 통째로 실패하므로 먼저 보장
        try:
            init_db()
        except Exception as exc:
            logger.critical("데이터베이스 초기화 실패: %s", exc, exc_info=True)
            self.self_diagnose("DB 초기화 실패")
            return 1

        cycle_index = 0

        while not self._shutdown.is_set():
            cycle_index += 1
            succeeded = await self.run_cycle()

            # 실패가 임계치에 도달하면 자가 진단으로 원인을 규명
            if not succeeded:
                if self.consecutive_failures >= settings.MONITOR_MAX_CONSECUTIVE_FAILURES:
                    self.self_diagnose(
                        f"연속 실패 {self.consecutive_failures}회"
                    )
                else:
                    logger.warning(
                        "연속 실패 %d회 (임계치 %d회)",
                        self.consecutive_failures,
                        settings.MONITOR_MAX_CONSECUTIVE_FAILURES,
                    )

            # 10 사이클마다 이력 정리
            if cycle_index % 10 == 0:
                self.housekeeping()

            if self.run_once:
                logger.info("--once 모드이므로 1회 실행 후 종료합니다")
                break

            if self._shutdown.is_set():
                break

            delay = self.compute_delay()

            if self.consecutive_failures:
                logger.info(
                    "백오프 대기 %.0f초 (연속 실패 %d회)",
                    delay,
                    self.consecutive_failures,
                )
            else:
                logger.info("다음 수집까지 %.0f초 대기", delay)

            # 종료 신호가 오면 대기를 즉시 중단 (타임아웃은 정상 경로)
            try:
                await asyncio.wait_for(self._shutdown.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass

        uptime = (datetime.utcnow() - self.started_at).total_seconds()

        logger.info("=" * 62)
        logger.info(
            "워커 종료 | 가동 %.0f초 | 사이클 %d회 | 누적 저장 %d건",
            uptime,
            self.cycles_completed,
            self.total_saved,
        )
        logger.info("=" * 62)

        return 0


# ============ FastAPI 내장 기동 ============

# 웹 서버와 같은 프로세스에서 돌릴 때의 핸들
_embedded_worker: Optional[CollectorWorker] = None
_embedded_task: Optional[asyncio.Task] = None


def _should_autostart_worker() -> bool:
    """
    내장 워커를 띄울지 결정합니다.

    테스트(pytest)나 명시적 비활성 플래그가 있으면 외부 API를
    호출하지 않도록 건너뜁니다.
    """
    if not settings.MONITOR_AUTOSTART:
        return False

    if os.environ.get("NOTEAI_DISABLE_WORKER") == "1":
        return False

    # pytest가 앱을 올리는 동안에는 수집 사이클을 돌리지 않음
    if os.environ.get("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
        return False

    return True


async def start_embedded_worker() -> None:
    """
    FastAPI 프로세스 안에서 수집 워커를 백그라운드 태스크로 띄웁니다.

    잠금 파일을 잡아 대시보드가 '워커 실행 중'으로 표시하게 하고,
    기동 직후 첫 수집 사이클을 돌립니다.
    """
    global _embedded_worker, _embedded_task

    if not _should_autostart_worker():
        logger.info("내장 수집 워커를 건너뜁니다 (비활성 또는 테스트 환경)")
        return

    try:
        pid = lockfile.acquire()
    except lockfile.LockError as exc:
        # 이미 별도 프로세스로 워커가 떠 있으면 API만 제공하면 됨
        logger.warning("내장 수집 워커를 건너뜁니다: %s", exc)
        return

    worker = CollectorWorker()
    _embedded_worker = worker
    _embedded_task = asyncio.create_task(
        _run_embedded(worker),
        name="noteai-collector",
    )
    logger.info("내장 수집 워커를 시작했습니다 (PID %d)", pid)


async def _run_embedded(worker: CollectorWorker) -> None:
    """내장 워커 태스크 본체 - 종료 시 잠금을 반드시 회수합니다."""
    try:
        await worker.run(install_signals=False)
    except Exception:
        logger.critical("내장 수집 워커가 예기치 못하게 중단되었습니다", exc_info=True)
    finally:
        lockfile.release()


async def stop_embedded_worker() -> None:
    """내장 워커에 종료를 요청하고 짧게 기다립니다."""
    global _embedded_worker, _embedded_task

    if _embedded_worker is not None:
        _embedded_worker.request_shutdown()

    task = _embedded_task
    _embedded_task = None
    _embedded_worker = None

    if task is None:
        lockfile.release()
        return

    try:
        await asyncio.wait_for(task, timeout=20)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        task.cancel()
        logger.warning("내장 수집 워커가 제한 시간 안에 끝나지 않아 취소합니다")

    lockfile.release()


# ============ CLI ============

def print_status() -> int:
    """
    현재 모니터링 상태를 콘솔에 출력 (워커를 띄우지 않음)

    Returns:
        종료 코드
    """
    # 조회만 하더라도 relationship 해석을 위해 전체 모델 등록이 필요
    register_models()

    db = SessionLocal()

    try:
        state = monitor_service.get_worker_state(db)
        stats = monitor_service.get_stats(db, hours=24)

        print("=" * 58)
        print("NOTEAI 수집 워커 상태")
        print("=" * 58)
        print(f"  실행 중       : {'예' if state['running'] else '아니오'}")
        print(f"  PID           : {state['pid'] or '-'}")
        print(f"  마지막 실행   : {state['last_run_at'] or '-'} ({state['last_status'] or '-'})")
        print(f"  다음 실행 예상: {state['next_run_estimate'] or '-'}")
        print(f"  연속 실패     : {state['consecutive_failures']}회")
        print(f"  정체 여부     : {'예' if state['stale'] else '아니오'}")
        print("-" * 58)
        print(f"  최근 24시간   : {stats['total_runs']}회 실행 "
              f"(성공 {stats['success_runs']} / 부분 {stats['partial_runs']} / 실패 {stats['failed_runs']})")
        print(f"  성공률        : {stats['success_rate'] * 100:.1f}%")
        print(f"  신규 저장     : {stats['total_saved']}건")
        print(f"  평균 소요     : {stats['avg_duration_seconds']:.2f}초")
        print("=" * 58)

        return 0

    finally:
        db.close()


def print_diagnosis(hours: int, as_json: bool) -> int:
    """
    자가 진단만 실행하고 결과를 출력

    Args:
        hours: 분석 기간
        as_json: JSON으로 출력할지 여부

    Returns:
        진단 결과에 따른 종료 코드 (unhealthy면 1)
    """
    report = diagnostics.diagnose(hours=hours)

    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return 1 if report["verdict"] == "unhealthy" else 0

    print("=" * 58)
    print(f"자가 진단 결과: {report['verdict'].upper()}")
    print("=" * 58)
    print(f"  {report['summary']}")
    print(f"  분석 로그 {report['stats']['analyzed_lines']}줄 / "
          f"오류 {report['stats']['error_count']}건 / "
          f"경고 {report['stats']['warning_count']}건")

    if report["findings"]:
        print("-" * 58)

        for finding in report["findings"]:
            print(f"\n  [{finding['severity'].upper()}] {finding['label']} "
                  f"({finding['count']}건)")
            print(f"    원인: {finding['cause']}")
            print(f"    조치: {finding['action']}")

            if finding["samples"]:
                print(f"    예시: {finding['samples'][0]}")

    if report["unclassified"]:
        print("\n  [미분류 오류]")
        for message in report["unclassified"]:
            print(f"    - {message}")

    print("=" * 58)

    return 1 if report["verdict"] == "unhealthy" else 0


def parse_args() -> argparse.Namespace:
    """
    명령행 인자 파싱

    Returns:
        파싱된 인자
    """
    parser = argparse.ArgumentParser(
        description="NOTEAI 24시간 백그라운드 수집 워커",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--interval", type=int, default=None,
        help=f"수집 주기(초). 기본 {settings.MONITOR_INTERVAL_SECONDS}초",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help=f"소스당 최대 수집 항목 수. 기본 {settings.MONITOR_LIMIT_PER_SOURCE}건",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="1회만 수집하고 종료 (cron/작업 스케줄러 연동용)",
    )
    parser.add_argument(
        "--diagnose", action="store_true",
        help="수집하지 않고 로그 자가 진단만 실행",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="현재 워커 상태를 출력하고 종료",
    )
    parser.add_argument(
        "--hours", type=int, default=24,
        help="진단 대상 기간(시간). 기본 24",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="진단 결과를 JSON으로 출력",
    )

    return parser.parse_args()


def main() -> int:
    """
    진입점

    Returns:
        프로세스 종료 코드
    """
    args = parse_args()

    # 조회 전용 모드는 잠금이 필요 없음
    if args.status:
        return print_status()

    if args.diagnose:
        return print_diagnosis(args.hours, args.json)

    # 중복 실행 방지 - 24시간 워커가 두 개 뜨면 API 중복 호출과 DB 잠금 충돌 발생
    try:
        lockfile.acquire()
    except lockfile.LockError as exc:
        logger.error("%s", exc)
        return 2

    try:
        worker = CollectorWorker(
            interval=args.interval,
            limit_per_source=args.limit,
            run_once=args.once,
        )

        return asyncio.run(worker.run())

    except KeyboardInterrupt:
        # add_signal_handler가 없는 환경에서 Ctrl+C가 여기까지 올라올 수 있음
        logger.info("사용자 중단으로 종료합니다")
        return 0

    except Exception as exc:
        logger.critical("워커가 예기치 못하게 중단되었습니다: %s", exc, exc_info=True)

        # 마지막으로 원인을 남기기 위해 진단 실행
        try:
            diagnostics.diagnose(hours=1)
        except Exception:
            pass

        return 1

    finally:
        # 잠금은 어떤 경로로 끝나든 반드시 회수
        lockfile.release()


if __name__ == "__main__":
    sys.exit(main())
