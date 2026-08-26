"""
인증 서비스
- 사용자 등록, 로그인, 토큰 관리
"""

from sqlalchemy.orm import Session
from core.security import hash_password, verify_password, create_access_token
from features.auth.models import User
from features.auth.schemas import UserCreate, UserLogin
from typing import Optional
from datetime import timedelta


class AuthService:
    """인증 관련 비즈니스 로직"""

    @staticmethod
    def register_user(db: Session, user_data: UserCreate) -> User:
        """
        사용자 등록

        Args:
            db: 데이터베이스 세션
            user_data: 사용자 정보

        Returns:
            생성된 사용자 객체

        Raises:
            ValueError: 중복된 사용자명 또는 이메일
        """
        # 중복 확인
        existing_user = db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()

        if existing_user:
            raise ValueError("Username or email already exists")

        # 새 사용자 생성
        user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            full_name=user_data.full_name or user_data.username,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        """
        사용자 인증 (로그인)

        Args:
            db: 데이터베이스 세션
            username: 사용자명
            password: 비밀번호

        Returns:
            인증된 사용자 객체, 실패 시 None
        """
        user = db.query(User).filter(User.username == username).first()

        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None

        if not user.is_active:
            return None

        return user

    @staticmethod
    def create_access_token_for_user(user: User) -> str:
        """
        사용자를 위한 액세스 토큰 생성

        Args:
            user: 사용자 객체

        Returns:
            JWT 토큰
        """
        token_data = {
            "user_id": user.id,
            "username": user.username,
        }

        access_token = create_access_token(token_data)
        return access_token

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """
        사용자 ID로 사용자 조회

        Args:
            db: 데이터베이스 세션
            user_id: 사용자 ID

        Returns:
            사용자 객체
        """
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """
        사용자명으로 사용자 조회

        Args:
            db: 데이터베이스 세션
            username: 사용자명

        Returns:
            사용자 객체
        """
        return db.query(User).filter(User.username == username).first()


# 서비스 인스턴스
auth_service = AuthService()
