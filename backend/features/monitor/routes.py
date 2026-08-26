"""
Monitor API 엔드포인트
- 대시보드용 통합 상태 조회
- 수집 실행 이력 조회
- 로그 자가 진단 실행
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.database import get_db
from features.auth.deps import get_current_user
from features.auth.models import User
from features.monitor import diagnostics
from features.monitor.schemas import (
    CollectionRunResponse,
    DiagnosisResponse,
    MonitorStatusResponse,
)
from features.monitor.service import monitor_service

# 라우터 생성
router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.get("/status", response_model=dict)
async def get_status(
    hours: int = Query(24, ge=1, le=168, description="집계/진단 기간 (시간)"),
    recent_limit: int = Query(10, ge=1, le=50, description="최근 이력 개수"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    대시보드용 통합 모니터링 상태 조회

    워커 생존 여부, 수집 통계, 자가 진단 결과, 최근 실행 이력을
    한 번의 요청으로 반환합니다.

    Args:
        hours: 집계 및 진단 대상 기간
        recent_limit: 함께 반환할 최근 이력 개수
        current_user: 현재 사용자
        db: 데이터베이스 세션

    Returns:
        통합 상태
    """
    result = monitor_service.get_status(db, hours=hours, recent_limit=recent_limit)

    worker_running = result["worker"]["running"]
    verdict = result["diagnosis"]["verdict"]

    return {
        "status": 200,
        "data": MonitorStatusResponse(**result).model_dump(),
        "message": (
            f"워커 {'실행 중' if worker_running else '중지됨'} / 진단: {verdict}"
        ),
    }


@router.get("/runs", response_model=dict)
async def get_runs(
    limit: int = Query(20, ge=1, le=200, description="조회할 이력 개수"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    수집 사이클 실행 이력 조회 (최신순)

    Args:
        limit: 조회할 개수
        current_user: 현재 사용자
        db: 데이터베이스 세션

    Returns:
        실행 이력 목록
    """
    runs = monitor_service.get_recent_runs(db, limit=limit)

    items = [
        CollectionRunResponse(**monitor_service._run_to_dict(run)).model_dump()
        for run in runs
    ]

    return {
        "status": 200,
        "data": {"runs": items, "total": len(items)},
        "message": f"{len(items)}건의 실행 이력을 조회했습니다",
    }


@router.get("/diagnose", response_model=dict)
async def run_diagnosis(
    hours: int = Query(24, ge=1, le=168, description="분석 대상 기간 (시간)"),
    limit_lines: int = Query(
        2000, ge=100, le=20000, description="분석할 최대 로그 줄 수"
    ),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    로그 자가 진단을 수동 실행

    워커가 실패할 때 자동으로도 실행되지만, 이 엔드포인트로 언제든
    현재 로그 상태를 점검할 수 있습니다.

    Args:
        hours: 분석 대상 기간
        limit_lines: 분석할 최대 로그 줄 수
        current_user: 현재 사용자

    Returns:
        진단 결과 (판정, 원인, 권장 조치)
    """
    result = diagnostics.diagnose(hours=hours, limit_lines=limit_lines)

    return {
        "status": 200,
        "data": DiagnosisResponse(**result).model_dump(),
        "message": result["summary"],
    }
