"""
인증 API 엔드포인트
- 회원가입, 로그인, 로그아웃, 현재 사용자 조회
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.database import get_db
from features.auth.models import User
from features.auth.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
)
from features.auth.service import DuplicateAccountError, auth_service
from features.auth.deps import get_current_user
from core.config import settings

# 라우터 생성
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
) -> dict:
    """
    사용자 회원가입

    Args:
        user_data: 사용자 정보
        db: 데이터베이스 세션

    Returns:
        사용자 정보 및 토큰

    Raises:
        HTTPException: 사용자명 또는 이메일 중복
    """
    try:
        # 아이디/이메일 중복을 DB에서 확인한 뒤 저장합니다.
        user = auth_service.register_user(db, user_data)

        # 가입과 동시에 JWT를 발급해 바로 세션을 시작합니다.
        access_token = auth_service.create_access_token_for_user(user)

        return {
            "status": 201,
            "data": {
                "user": UserResponse.from_orm(user).dict(),
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            },
            "message": "회원가입이 완료되었습니다.",
        }
    except DuplicateAccountError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login")
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
) -> dict:
    """
    사용자 로그인

    Args:
        credentials: 사용자명과 비밀번호
        db: 데이터베이스 세션

    Returns:
        토큰 및 사용자 정보

    Raises:
        HTTPException: 자격증명 오류
    """
    # 사용자 인증
    user = auth_service.authenticate_user(
        db,
        credentials.username,
        credentials.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자명 또는 비밀번호가 올바르지 않습니다.",
        )

    # 토큰 생성
    access_token = auth_service.create_access_token_for_user(user)

    return {
        "status": 200,
        "data": {
            "user": UserResponse.from_orm(user).dict(),
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        },
        "message": "로그인되었습니다.",
    }


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)) -> dict:
    """
    사용자 로그아웃
    (클라이언트에서 토큰 제거)

    Args:
        current_user: 현재 사용자

    Returns:
        성공 메시지
    """
    return {
        "status": 200,
        "message": "Logout successful",
    }


@router.get("/me", response_model=dict)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    현재 인증된 사용자 정보 조회

    Args:
        current_user: 현재 사용자

    Returns:
        사용자 정보
    """
    return {
        "status": 200,
        "data": UserResponse.from_orm(current_user).dict(),
        "message": "User info retrieved",
    }
