"""
워커 중복 실행 방지용 잠금 파일

24시간 상주 워커가 두 개 이상 뜨면 외부 API를 중복 호출하고
SQLite 쓰기 충돌(database is locked)을 유발하므로, PID 기반 잠금으로
단일 인스턴스를 보장합니다.

주의: Windows의 os.kill(pid, 0)은 POSIX와 달리 생존 확인이 아니라
TerminateProcess를 호출해 대상 프로세스를 실제로 종료시킵니다.
따라서 플랫폼별로 다른 생존 확인 방법을 사용합니다.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from core.config import settings

_IS_WINDOWS = sys.platform == "win32"


class LockError(Exception):
    """잠금 획득 실패 (이미 다른 워커가 실행 중)"""


def get_lock_path() -> Path:
    """
    잠금 파일 경로를 반환 (부모 디렉토리가 없으면 생성)

    Returns:
        잠금 파일 경로
    """
    path = Path(settings.MONITOR_LOCK_FILE).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)

    return path


def is_process_alive(pid: int) -> bool:
    """
    지정한 PID의 프로세스가 살아 있는지 확인

    Args:
        pid: 확인할 프로세스 ID

    Returns:
        살아 있으면 True
    """
    if pid <= 0:
        return False

    if _IS_WINDOWS:
        return _is_alive_windows(pid)

    return _is_alive_posix(pid)


def _is_alive_windows(pid: int) -> bool:
    """
    Windows에서 OpenProcess로 프로세스 생존 확인

    os.kill을 쓰면 프로세스가 종료되므로 절대 사용하지 않습니다.

    Args:
        pid: 프로세스 ID

    Returns:
        살아 있으면 True
    """
    import ctypes
    from ctypes import wintypes

    # PROCESS_QUERY_LIMITED_INFORMATION - 최소 권한으로 상태만 조회
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    handle = kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION, False, pid
    )

    if not handle:
        # 핸들을 열 수 없으면 프로세스가 없는 것으로 간주
        return False

    try:
        exit_code = wintypes.DWORD()

        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return False

        # 종료 코드가 STILL_ACTIVE면 아직 실행 중
        return exit_code.value == STILL_ACTIVE

    finally:
        kernel32.CloseHandle(handle)


def _is_alive_posix(pid: int) -> bool:
    """
    POSIX에서 시그널 0으로 프로세스 생존 확인

    Args:
        pid: 프로세스 ID

    Returns:
        살아 있으면 True
    """
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # 권한이 없다는 것은 프로세스가 존재한다는 뜻
        return True
    except OSError:
        return False


def read_lock() -> Tuple[Optional[int], Optional[datetime]]:
    """
    잠금 파일에서 PID와 기록 시각을 읽음

    Args:
        없음

    Returns:
        (PID, 기록 시각). 파일이 없거나 손상되었으면 (None, None)
    """
    path = get_lock_path()

    if not path.exists():
        return None, None

    try:
        content = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None, None

    if not content:
        return None, None

    # 형식: "<pid>\n<ISO 시각>"
    parts = content.splitlines()

    try:
        pid = int(parts[0].strip())
    except (ValueError, IndexError):
        return None, None

    started_at = None

    if len(parts) > 1:
        try:
            started_at = datetime.fromisoformat(parts[1].strip())
        except ValueError:
            started_at = None

    return pid, started_at


def get_active_worker_pid() -> Optional[int]:
    """
    현재 살아 있는 워커의 PID를 반환

    잠금 파일이 남아 있어도 프로세스가 죽었으면 None을 반환합니다.

    Returns:
        활성 워커 PID 또는 None
    """
    pid, _ = read_lock()

    if pid is None:
        return None

    return pid if is_process_alive(pid) else None


def acquire() -> int:
    """
    잠금을 획득하고 현재 프로세스 PID를 기록

    잠금 파일이 이미 있어도 해당 프로세스가 죽었다면
    오래된 잠금으로 판단하고 회수합니다.

    Returns:
        획득한 PID (현재 프로세스)

    Raises:
        LockError: 다른 워커가 실행 중인 경우
    """
    path = get_lock_path()
    existing_pid, _ = read_lock()

    if existing_pid is not None:
        if is_process_alive(existing_pid):
            raise LockError(
                f"이미 워커가 실행 중입니다 (PID {existing_pid}). "
                f"중복 실행을 막기 위해 종료합니다."
            )

        # 죽은 프로세스가 남긴 오래된 잠금은 회수
        try:
            path.unlink()
        except OSError:
            pass

    pid = os.getpid()

    try:
        # O_EXCL로 원자적 생성 - 두 워커가 동시에 시작해도 하나만 성공
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise LockError("다른 워커가 동시에 잠금을 획득했습니다.")
    except OSError as exc:
        raise LockError(f"잠금 파일을 만들 수 없습니다: {exc}") from exc

    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(f"{pid}\n{datetime.now().isoformat()}\n")

    return pid


def release() -> None:
    """
    현재 프로세스가 소유한 잠금을 해제

    다른 프로세스의 잠금은 건드리지 않습니다.
    """
    path = get_lock_path()
    pid, _ = read_lock()

    # 내 잠금일 때만 삭제
    if pid == os.getpid():
        try:
            path.unlink()
        except OSError:
            pass
