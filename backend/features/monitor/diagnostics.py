"""
로그 자가 진단 루틴
- 회전 로그 파일을 뒤에서부터 읽어 최근 오류를 수집
- 알려진 오류 패턴으로 분류하고 원인/조치를 제시
- 수집 이력(CollectionRun)과 교차 검증하여 심각도를 판정

워커가 실패했을 때 자동 호출되며, API(/api/monitor/diagnose)로도
수동 실행할 수 있습니다.
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import settings
from core.logging_config import DATE_FORMAT, get_log_path

# setup_logging의 LOG_FORMAT과 짝을 이루는 파서
# 2026-08-26 11:30:00 | ERROR | monitor.worker | 메시지
_LOG_LINE_RE = re.compile(
    r"^(?P<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
    r"\s*\|\s*(?P<level>[A-Z]+)"
    r"\s*\|\s*(?P<logger>[\w.]+)"
    r"\s*\|\s*(?P<message>.*)$"
)

# 진단 대상 로그 레벨
_PROBLEM_LEVELS = {"ERROR", "CRITICAL", "WARNING"}


@dataclass
class Symptom:
    """알려진 오류 증상 하나의 정의"""

    code: str                       # 증상 코드 (예: NETWORK_TIMEOUT)
    label: str                      # 사람이 읽는 이름
    pattern: re.Pattern             # 로그 메시지 매칭 정규식
    severity: str                   # critical | high | medium | low
    cause: str                      # 추정 원인
    action: str                     # 권장 조치
    transient: bool = False         # 일시적 장애 여부 (재시도로 해결 가능)


# ============ 알려진 증상 사전 ============
# 위에서부터 순서대로 매칭하므로, 더 구체적인 패턴을 앞에 둡니다.
SYMPTOMS: List[Symptom] = [
    Symptom(
        code="DB_LOCKED",
        label="데이터베이스 잠금",
        pattern=re.compile(r"database is locked|OperationalError.*locked", re.I),
        severity="high",
        cause="SQLite에 동시 쓰기가 발생했습니다. 워커가 중복 실행 중이거나 "
              "API 서버와 쓰기 시점이 겹쳤을 수 있습니다.",
        action="monitor.lock 파일로 중복 실행 여부를 확인하세요. 계속 발생하면 "
               "DATABASE_URL을 PostgreSQL로 전환하는 것을 검토하세요.",
        transient=True,
    ),
    Symptom(
        code="DB_SCHEMA_MISSING",
        label="테이블 없음",
        pattern=re.compile(r"no such table|UndefinedTable", re.I),
        severity="critical",
        cause="데이터베이스가 초기화되지 않았거나 마이그레이션이 누락되었습니다.",
        action="`python -c \"from core.database import init_db; init_db()\"`로 "
               "테이블을 생성하세요.",
    ),
    Symptom(
        code="AUTH_FAILED",
        label="외부 API 인증 실패",
        pattern=re.compile(r"HTTP 401|HTTP 403|apiKeyInvalid|unauthorized", re.I),
        severity="high",
        cause="외부 API 키가 없거나 만료되었거나 요청 한도를 초과했습니다.",
        action=".env의 NEWSAPI_KEY 값을 확인하세요. 키가 없다면 해당 소스는 "
               "자동 비활성화되므로 RSS 소스만으로도 수집은 계속됩니다.",
    ),
    Symptom(
        code="RATE_LIMITED",
        label="요청 한도 초과",
        pattern=re.compile(r"HTTP 429|rate limit|too many requests", re.I),
        severity="medium",
        cause="외부 API가 요청 빈도를 제한했습니다. 수집 주기가 너무 짧습니다.",
        action="MONITOR_INTERVAL_SECONDS를 늘리세요. 워커는 자동으로 백오프하지만 "
               "반복되면 주기 자체를 조정해야 합니다.",
        transient=True,
    ),
    Symptom(
        code="FEED_NOT_FOUND",
        label="피드 주소 없음(404)",
        pattern=re.compile(r"HTTP 404", re.I),
        severity="medium",
        cause="RSS 피드 URL이 폐기되었습니다. 소스 정의가 낡았습니다.",
        action="features/trends/sources.py에서 해당 소스의 URL을 갱신하거나 "
               "TRENDS_DISABLED_SOURCES에 추가해 비활성화하세요.",
    ),
    Symptom(
        code="SERVER_ERROR",
        label="외부 서버 오류(5xx)",
        pattern=re.compile(r"HTTP 5\d{2}", re.I),
        severity="low",
        cause="외부 소스 서버에 일시적 장애가 발생했습니다.",
        action="조치 불필요합니다. 다음 사이클에서 자동 재시도됩니다.",
        transient=True,
    ),
    Symptom(
        code="NETWORK_TIMEOUT",
        label="네트워크 시간 초과",
        pattern=re.compile(r"시간 초과|timeout|timed out|ReadTimeout", re.I),
        severity="medium",
        cause="외부 소스 응답이 느리거나 네트워크가 불안정합니다.",
        action="TRENDS_TIMEOUT_SECONDS를 늘려보세요. 특정 소스에서만 반복되면 "
               "해당 소스를 TRENDS_DISABLED_SOURCES에 추가하세요.",
        transient=True,
    ),
    Symptom(
        code="NETWORK_UNREACHABLE",
        label="네트워크 연결 불가",
        pattern=re.compile(
            r"네트워크 오류|ConnectError|ConnectionError|DNS|getaddrinfo|"
            r"Name or service not known|Temporary failure", re.I
        ),
        severity="high",
        cause="인터넷 연결이 끊겼거나 DNS 해석에 실패했습니다.",
        action="호스트의 네트워크 연결과 프록시/방화벽 설정을 확인하세요.",
        transient=True,
    ),
    Symptom(
        code="XML_PARSE_ERROR",
        label="피드 파싱 실패",
        pattern=re.compile(r"XML 파싱 실패|ParseError|not well-formed", re.I),
        severity="medium",
        cause="외부 피드가 손상된 XML을 반환했습니다. 소스 측 문제일 가능성이 큽니다.",
        action="해당 소스 URL을 브라우저로 직접 열어 응답을 확인하세요. "
               "지속되면 소스를 비활성화하세요.",
    ),
    Symptom(
        code="DISK_FULL",
        label="디스크 공간 부족",
        pattern=re.compile(r"No space left|disk full|OSError.*28", re.I),
        severity="critical",
        cause="디스크가 가득 차 로그 또는 DB 쓰기에 실패했습니다.",
        action="로그 디렉토리를 정리하고 MONITOR_LOG_BACKUP_COUNT를 줄이세요.",
    ),
    Symptom(
        code="PERMISSION_DENIED",
        label="권한 거부",
        pattern=re.compile(r"Permission denied|PermissionError|Access is denied", re.I),
        severity="high",
        cause="로그 디렉토리나 DB 파일에 쓰기 권한이 없습니다.",
        action="MONITOR_LOG_DIR과 DATABASE_URL 경로의 파일 권한을 확인하세요.",
    ),
]


@dataclass
class LogEntry:
    """파싱된 로그 한 줄"""

    timestamp: datetime
    level: str
    logger: str
    message: str


@dataclass
class Finding:
    """진단 결과 항목 하나"""

    code: str
    label: str
    severity: str
    count: int
    cause: str
    action: str
    transient: bool
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    samples: List[str] = field(default_factory=list)


def read_recent_logs(
    limit_lines: int = 2000,
    since: Optional[datetime] = None,
    log_path: Optional[Path] = None,
) -> List[LogEntry]:
    """
    로그 파일의 최근 N줄을 파싱

    회전 로그가 커질 수 있으므로 파일 전체를 메모리에 올리지 않고
    끝에서부터 필요한 만큼만 읽습니다.

    Args:
        limit_lines: 읽어들일 최대 줄 수
        since: 이 시각 이후 항목만 반환 (None이면 전체)
        log_path: 로그 파일 경로 (None이면 설정값 사용)

    Returns:
        시간순으로 정렬된 로그 항목 목록
    """
    path = log_path or get_log_path()

    if not path.exists():
        return []

    lines = _tail_lines(path, limit_lines)

    entries: List[LogEntry] = []

    for line in lines:
        match = _LOG_LINE_RE.match(line.strip())

        if not match:
            # 스택 트레이스 등 포맷에 맞지 않는 줄은 직전 항목의 메시지에 이어붙임
            if entries and line.strip():
                entries[-1].message += " " + line.strip()
            continue

        try:
            timestamp = datetime.strptime(match.group("time"), DATE_FORMAT)
        except ValueError:
            continue

        if since is not None and timestamp < since:
            continue

        entries.append(
            LogEntry(
                timestamp=timestamp,
                level=match.group("level"),
                logger=match.group("logger"),
                message=match.group("message"),
            )
        )

    return entries


def _tail_lines(path: Path, limit_lines: int, chunk_size: int = 8192) -> List[str]:
    """
    파일 끝에서부터 지정한 줄 수만큼 읽기

    Args:
        path: 대상 파일
        limit_lines: 읽을 줄 수
        chunk_size: 한 번에 읽을 바이트 수

    Returns:
        줄 목록 (파일 순서 유지)
    """
    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)  # 파일 끝으로 이동
            file_size = handle.tell()

            buffer = b""
            newline_count = 0
            position = file_size

            # 필요한 줄 수를 채울 때까지 뒤에서부터 청크 단위로 읽음
            while position > 0 and newline_count <= limit_lines:
                read_size = min(chunk_size, position)
                position -= read_size

                handle.seek(position)
                chunk = handle.read(read_size)

                buffer = chunk + buffer
                newline_count = buffer.count(b"\n")

        text = buffer.decode("utf-8", errors="replace")
        return text.splitlines()[-limit_lines:]

    except OSError:
        # 로그를 읽지 못해도 진단 자체가 죽으면 안 되므로 빈 결과 반환
        return []


def classify(message: str) -> Optional[Symptom]:
    """
    로그 메시지를 알려진 증상으로 분류

    Args:
        message: 로그 메시지

    Returns:
        일치하는 증상 정의, 없으면 None
    """
    for symptom in SYMPTOMS:
        if symptom.pattern.search(message):
            return symptom

    return None


def diagnose(
    hours: int = 24,
    limit_lines: int = 2000,
    log_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    로그를 분석하여 자가 진단 결과를 생성

    Args:
        hours: 분석 대상 기간 (최근 N시간)
        limit_lines: 읽어들일 최대 로그 줄 수
        log_path: 로그 파일 경로 (테스트용 주입)

    Returns:
        {
            "verdict": healthy | degraded | unhealthy | unknown,
            "summary": 사람이 읽는 한 줄 요약,
            "findings": [진단 항목, ...],
            "stats": {...},
            "unclassified": [분류되지 않은 오류 메시지, ...]
        }
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    entries = read_recent_logs(limit_lines=limit_lines, since=since, log_path=log_path)

    if not entries:
        return {
            "verdict": "unknown",
            "summary": "분석할 로그가 없습니다. 워커가 아직 실행되지 않았을 수 있습니다.",
            "findings": [],
            "stats": {
                "analyzed_lines": 0,
                "error_count": 0,
                "warning_count": 0,
                "window_hours": hours,
            },
            "unclassified": [],
        }

    level_counts = Counter(entry.level for entry in entries)
    problems = [entry for entry in entries if entry.level in _PROBLEM_LEVELS]

    # 증상 코드별로 집계
    grouped: Dict[str, Finding] = {}
    unclassified: List[str] = []

    for entry in problems:
        symptom = classify(entry.message)

        if symptom is None:
            # WARNING은 노이즈가 많으므로 미분류 목록에는 ERROR 이상만 담음
            if entry.level in ("ERROR", "CRITICAL"):
                unclassified.append(f"[{entry.level}] {entry.message[:200]}")
            continue

        finding = grouped.get(symptom.code)

        if finding is None:
            finding = Finding(
                code=symptom.code,
                label=symptom.label,
                severity=symptom.severity,
                count=0,
                cause=symptom.cause,
                action=symptom.action,
                transient=symptom.transient,
                first_seen=entry.timestamp,
            )
            grouped[symptom.code] = finding

        finding.count += 1
        finding.last_seen = entry.timestamp

        # 샘플은 진단 결과가 비대해지지 않도록 최대 3건만 보관
        if len(finding.samples) < 3:
            finding.samples.append(entry.message[:200])

    # 심각도 높은 순 -> 빈도 높은 순 정렬
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings = sorted(
        grouped.values(),
        key=lambda f: (severity_rank.get(f.severity, 9), -f.count),
    )

    verdict = _judge(findings, level_counts)

    return {
        "verdict": verdict,
        "summary": _summarize(verdict, findings, level_counts, hours),
        "findings": [_finding_to_dict(f) for f in findings],
        "stats": {
            "analyzed_lines": len(entries),
            "error_count": level_counts.get("ERROR", 0) + level_counts.get("CRITICAL", 0),
            "warning_count": level_counts.get("WARNING", 0),
            "window_hours": hours,
            "first_log_at": entries[0].timestamp.isoformat(),
            "last_log_at": entries[-1].timestamp.isoformat(),
        },
        # 미분류 오류는 증상 사전을 넓힐 단서이므로 최근 것 위주로 소량 노출
        "unclassified": unclassified[-5:],
    }


def _judge(findings: List[Finding], level_counts: Counter) -> str:
    """
    진단 항목을 종합해 전체 상태를 판정

    일시적 장애(transient)만 있으면 자동 복구를 기대할 수 있으므로
    한 단계 낮은 심각도로 판정합니다.

    Args:
        findings: 진단 항목 목록
        level_counts: 레벨별 로그 수

    Returns:
        healthy | degraded | unhealthy
    """
    if not findings:
        # 분류되지 않은 오류만 있어도 정상은 아님
        if level_counts.get("ERROR", 0) or level_counts.get("CRITICAL", 0):
            return "degraded"
        return "healthy"

    has_critical = any(f.severity == "critical" for f in findings)
    has_persistent_high = any(
        f.severity == "high" and not f.transient for f in findings
    )

    if has_critical or has_persistent_high:
        return "unhealthy"

    # 일시적 장애가 반복되면 방치할 수 없으므로 degraded로 승격
    return "degraded"


def _summarize(
    verdict: str,
    findings: List[Finding],
    level_counts: Counter,
    hours: int,
) -> str:
    """
    진단 결과를 한 줄 요약으로 변환

    Args:
        verdict: 판정 결과
        findings: 진단 항목
        level_counts: 레벨별 로그 수
        hours: 분석 기간

    Returns:
        요약 문자열
    """
    errors = level_counts.get("ERROR", 0) + level_counts.get("CRITICAL", 0)
    warnings = level_counts.get("WARNING", 0)

    if verdict == "healthy":
        return f"최근 {hours}시간 동안 오류 없이 정상 동작 중입니다."

    if not findings:
        return f"최근 {hours}시간 동안 분류되지 않은 오류 {errors}건이 발생했습니다."

    top = findings[0]

    # 오류 없이 경고만 있는 경우를 오류 0건으로 표현하면 오해를 부르므로 구분
    if errors:
        scale = f"오류 {errors}건"
    else:
        scale = f"경고 {warnings}건"

    return (
        f"최근 {hours}시간 동안 {scale} 발생. "
        f"주요 원인은 '{top.label}'({top.count}건)입니다."
    )


def _finding_to_dict(finding: Finding) -> Dict[str, Any]:
    """
    Finding 데이터클래스를 직렬화 가능한 딕셔너리로 변환

    Args:
        finding: 진단 항목

    Returns:
        딕셔너리
    """
    return {
        "code": finding.code,
        "label": finding.label,
        "severity": finding.severity,
        "count": finding.count,
        "cause": finding.cause,
        "action": finding.action,
        "transient": finding.transient,
        "first_seen": finding.first_seen.isoformat() if finding.first_seen else None,
        "last_seen": finding.last_seen.isoformat() if finding.last_seen else None,
        "samples": finding.samples,
    }
