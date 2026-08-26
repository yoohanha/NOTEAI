"""
로깅 설정 모듈
- 회전 파일 핸들러 + 콘솔 핸들러 구성
- 자가 진단 루틴이 파싱할 수 있도록 고정된 로그 포맷 사용

로그 한 줄의 형식은 diagnostics.py의 파서와 짝을 이룹니다.
포맷을 바꾸면 diagnostics._LOG_LINE_RE도 함께 수정해야 합니다.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from core.config import settings

# 자가 진단 파서와 약속된 로그 포맷
# 예) 2026-08-26 11:30:00 | ERROR | monitor.worker | 수집 실패: timeout
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_log_path() -> Path:
    """
    로그 파일의 절대 경로를 반환 (디렉토리가 없으면 생성)

    Returns:
        로그 파일 경로
    """
    log_dir = Path(settings.MONITOR_LOG_DIR).expanduser()
    log_dir.mkdir(parents=True, exist_ok=True)

    return log_dir / settings.MONITOR_LOG_FILE


def setup_logging(
    name: str = "monitor",
    level: int = logging.INFO,
    to_console: bool = True,
) -> logging.Logger:
    """
    회전 파일 로거를 구성하여 반환

    이미 핸들러가 붙어 있으면 중복 추가하지 않으므로
    여러 번 호출해도 안전합니다.

    Args:
        name: 로거 이름 (계층 구분에 사용)
        level: 로그 레벨
        to_console: 콘솔 출력 여부

    Returns:
        구성된 로거
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 루트 로거로 전파되면 메시지가 두 번 찍히므로 차단
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # 회전 파일 핸들러 - 24시간 연속 운영 시 디스크 고갈 방지
    file_handler = RotatingFileHandler(
        filename=str(get_log_path()),
        maxBytes=settings.MONITOR_LOG_MAX_BYTES,
        backupCount=settings.MONITOR_LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    if to_console:
        # Windows 콘솔의 기본 코드페이지가 cp949라 이모지/한글이 깨질 수 있으므로
        # 인코딩 오류가 나도 프로세스가 죽지 않도록 errors="replace" 스트림 사용
        stream = sys.stdout

        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            # reconfigure를 지원하지 않는 스트림은 그대로 사용
            pass

        console_handler = logging.StreamHandler(stream)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    이미 구성된 로거의 자식 로거를 반환

    Args:
        name: 하위 로거 이름 (예: "worker" -> "monitor.worker")

    Returns:
        로거 인스턴스
    """
    if name is None:
        return logging.getLogger("monitor")

    return logging.getLogger(f"monitor.{name}")
