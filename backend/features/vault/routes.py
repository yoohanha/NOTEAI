"""
Vault API 엔드포인트
- 로컬 노트 디렉토리 스캔
- 스캔 결과를 NOTEAI 노트로 가져오기
- 단일 파일 파싱 미리보기
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from features.auth.deps import get_current_user
from features.auth.models import User
from features.vault.parser import parse_note_text
from features.vault.scanner import (
    DEFAULT_EXCLUDE_DIRS,
    DEFAULT_EXTENSIONS,
    VaultScanError,
    read_note_file,
    resolve_vault_root,
)
from features.vault.schemas import (
    ImportRequest,
    ImportResponse,
    ScanRequest,
    ScanResponse,
)
from features.vault.service import vault_service

# 라우터 생성
router = APIRouter(prefix="/vault", tags=["vault"])


@router.get("/config", response_model=dict)
async def get_vault_config(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    스캔 설정 조회 (허용 루트, 지원 확장자, 제한값)

    프론트엔드가 경로 입력 UI를 구성할 때 사용합니다.

    Args:
        current_user: 현재 사용자

    Returns:
        스캐너 설정 정보
    """
    return {
        "status": 200,
        "data": {
            "allowed_roots": list(getattr(settings, "VAULT_ALLOWED_ROOTS", []) or []),
            "supported_extensions": list(DEFAULT_EXTENSIONS),
            "excluded_directories": sorted(DEFAULT_EXCLUDE_DIRS),
            "max_file_size": getattr(settings, "VAULT_MAX_FILE_SIZE", 0),
            "restricted": bool(getattr(settings, "VAULT_ALLOWED_ROOTS", [])),
        },
        "message": "스캔 설정 조회 성공",
    }


@router.post("/scan", response_model=dict)
async def scan_vault(
    request: ScanRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    로컬 노트 디렉토리를 스캔하여 노트 목록과 통계를 반환

    데이터베이스에 저장하지 않는 읽기 전용 작업입니다.

    Args:
        request: 스캔 요청 (경로 및 필터 옵션)
        current_user: 현재 사용자

    Returns:
        스캔된 노트 목록, 실패 항목, 통계

    Raises:
        HTTPException: 경로가 잘못되었거나 허용 범위를 벗어난 경우 400
    """
    try:
        result = vault_service.scan(request)
    except VaultScanError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return {
        "status": 200,
        "data": ScanResponse(**result).model_dump(),
        "message": f"{result['stats']['total_files']}개 노트를 스캔했습니다",
    }


@router.post("/preview", response_model=dict)
async def preview_file(
    path: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    단일 파일을 파싱하여 결과를 미리보기

    스캔 전에 파서가 제목/태그를 어떻게 인식하는지 확인할 때 사용합니다.

    Args:
        path: 파일 절대 경로
        current_user: 현재 사용자

    Returns:
        파싱 결과

    Raises:
        HTTPException: 파일이 없거나 허용 범위 밖이면 400
    """
    file_path = Path(path)

    try:
        # 상위 디렉토리를 화이트리스트로 검증해 임의 파일 접근을 차단
        resolve_vault_root(str(file_path.parent))

        if not file_path.is_file():
            raise VaultScanError(f"파일이 아닙니다: {path}")

        max_size = getattr(settings, "VAULT_MAX_FILE_SIZE", 2 * 1024 * 1024)
        text = read_note_file(file_path, max_size)
    except VaultScanError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    parsed = parse_note_text(text, file_path)

    return {
        "status": 200,
        "data": parsed,
        "message": "파일 파싱 성공",
    }


@router.post("/import", response_model=dict)
async def import_vault(
    request: ImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    스캔된 로컬 노트를 현재 사용자의 노트로 가져오기

    `dry_run=true`로 먼저 실행해 어떤 노트가 생성/갱신/건너뛰기 되는지
    확인한 뒤 실제 실행하는 것을 권장합니다.

    Args:
        request: 가져오기 요청
        current_user: 노트 소유자
        db: 데이터베이스 세션

    Returns:
        생성/갱신/건너뜀/실패 건수와 항목별 결과

    Raises:
        HTTPException: 경로 오류 400, 저장 실패 500
    """
    try:
        result = vault_service.import_notes(db, request, current_user)
    except VaultScanError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"노트 가져오기 실패: {exc}",
        )

    action = "미리보기" if result["dry_run"] else "가져오기"

    return {
        "status": 200,
        "data": ImportResponse(**result).model_dump(),
        "message": (
            f"{action} 완료 - 생성 {result['created']}건, "
            f"갱신 {result['updated']}건, 건너뜀 {result['skipped']}건"
        ),
    }
