"""
Monitor 요청/응답 스키마
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CollectionRunResponse(BaseModel):
    """수집 사이클 1회 실행 기록"""

    id: int
    status: str = Field(..., description="success | partial | failed")
    fetched: int = 0
    saved: int = 0
    duplicates: int = 0
    sources_used: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    consecutive_failures: int = 0
    started_at: datetime
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkerState(BaseModel):
    """수집 워커의 현재 상태"""

    running: bool = Field(..., description="워커 프로세스가 살아 있는지 여부")
    pid: Optional[int] = Field(None, description="워커 프로세스 ID")
    last_run_at: Optional[datetime] = Field(None, description="마지막 실행 시각")
    last_status: Optional[str] = Field(None, description="마지막 실행 결과")
    next_run_estimate: Optional[datetime] = Field(
        None, description="다음 실행 예상 시각"
    )
    consecutive_failures: int = Field(0, description="현재 연속 실패 횟수")
    stale: bool = Field(
        False, description="예상 주기를 크게 넘겨 실행되지 않았는지 여부"
    )


class CollectionStats(BaseModel):
    """최근 수집 통계 집계"""

    window_hours: int = Field(24, description="집계 기간")
    total_runs: int = 0
    success_runs: int = 0
    partial_runs: int = 0
    failed_runs: int = 0
    success_rate: float = Field(0.0, description="성공률 (0~1)")
    total_saved: int = Field(0, description="신규 저장 항목 수")
    total_fetched: int = Field(0, description="수집 시도 항목 수")
    avg_duration_seconds: float = 0.0


class DiagnosisFinding(BaseModel):
    """자가 진단 항목"""

    code: str = Field(..., description="증상 코드")
    label: str = Field(..., description="증상 이름")
    severity: str = Field(..., description="critical | high | medium | low")
    count: int = Field(0, description="발생 횟수")
    cause: str = Field(..., description="추정 원인")
    action: str = Field(..., description="권장 조치")
    transient: bool = Field(False, description="재시도로 해결 가능한 일시적 장애인지")
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    samples: List[str] = Field(default_factory=list)


class DiagnosisResponse(BaseModel):
    """자가 진단 결과"""

    verdict: str = Field(..., description="healthy | degraded | unhealthy | unknown")
    summary: str = Field(..., description="한 줄 요약")
    findings: List[DiagnosisFinding] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)
    unclassified: List[str] = Field(
        default_factory=list, description="증상 사전에 없는 오류 메시지"
    )


class MonitorStatusResponse(BaseModel):
    """대시보드용 통합 상태"""

    worker: WorkerState
    stats: CollectionStats
    diagnosis: DiagnosisResponse
    recent_runs: List[CollectionRunResponse] = Field(default_factory=list)
    total_trends: int = Field(0, description="저장된 트렌드 총 개수")
    checked_at: datetime = Field(..., description="상태 조회 시각")
