"""
인증 관련 의존성 주입
- 현재 사용자 조회
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import decode_token
from features.auth.service import auth_service
from features.auth.models import User
from core.config import settings

# HTTP Bearer 토큰 스키마 (인증 필수)
security = HTTPBearer()

# 선택적 인증용 스키마
# auto_error=False로 두면 Authorization 헤더가 없어도 403을 던지지 않고
# None을 넘겨주므로, 공개 리소스를 비로그인 사용자에게 제공할 수 있습니다.
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    현재 인증된 사용자 조회

    FastAPI 라우트에서 사용:
    async def get_notes(current_user: User = Depends(get_current_user)):
        ...

    Args:
        credentials: HTTP Bearer 토큰
        db: 데이터베이스 세션

    Returns:
        현재 사용자 객체

    Raises:
        HTTPException: 토큰이 유효하지 않은 경우
    """
    token = credentials.credentials

    # 토큰 검증
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 사용자 조회
    user = auth_service.get_user_by_id(db, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
        )

    return user


def is_admin_user(user: User) -> bool:
    """지정된 관리자 이메일과 대소문자 무시 비교합니다."""
    admin_email = (getattr(settings, "ADMIN_EMAIL", "") or "").strip().lower()
    user_email = (user.email or "").strip().lower()
    return bool(admin_email) and user_email == admin_email


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    관리자 이메일 계정만 통과시킵니다.

    일반 사용자가 /api/admin/* 또는 관리자 화면을 직접 열면
    403과 함께 '접근 권한이 없습니다'를 받습니다.
    """
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="접근 권한이 없습니다",
        )
    return current_user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    현재 사용자를 선택적으로 조회 (인증 없어도 통과)

    공개 노트처럼 비로그인 사용자도 접근할 수 있는 리소스에 사용합니다.
    토큰이 없거나 유효하지 않으면 예외를 던지지 않고 None을 반환하므로,
    라우트에서 리소스의 공개 여부로 권한을 판단할 수 있습니다.

    FastAPI 라우트에서 사용:
    async def get_note(current_user: Optional[User] = Depends(get_current_user_optional)):
        ...

    Args:
        credentials: HTTP Bearer 토큰 (없을 수 있음)
        db: 데이터베이스 세션

    Returns:
        인증에 성공하면 사용자 객체, 아니면 None
    """
    # 헤더가 아예 없는 경우 - 비로그인 접근
    if credentials is None:
        return None

    payload = decode_token(credentials.credentials)

    if payload is None:
        return None

    user_id = payload.get("user_id")

    if user_id is None:
        return None

    user = auth_service.get_user_by_id(db, user_id)

    # 비활성 사용자는 비로그인과 동일하게 취급
    if user is None or not user.is_active:
        return None

    return user
