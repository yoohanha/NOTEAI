"""
인증 서비스
- 사용자 등록, 로그인, 토큰 관리
"""

from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.security import hash_password, verify_password, create_access_token
from features.auth.models import User
from features.auth.schemas import UserCreate


DUPLICATE_ACCOUNT_MESSAGE = "이미 가입된 계정입니다. 로그인해주세요."


class DuplicateAccountError(ValueError):
    """아이디 또는 이메일이 이미 등록된 경우"""


def normalize_identity(value: str) -> str:
    """사용자명/이메일을 비교·저장용으로 정규화합니다."""
    return (value or "").strip().lower()


class AuthService:
    """인증 관련 비즈니스 로직"""

    @staticmethod
    def find_by_username_or_email(db: Session, identity: str) -> Optional[User]:
        """
        사용자명 또는 이메일로 계정을 찾습니다. 대소문자는 무시합니다.
        """
        ident = normalize_identity(identity)
        if not ident:
            return None

        return (
            db.query(User)
            .filter(
                or_(
                    func.lower(User.username) == ident,
                    func.lower(User.email) == ident,
                )
            )
            .first()
        )

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
            DuplicateAccountError: 아이디 또는 이메일이 이미 존재
        """
        username = normalize_identity(user_data.username)
        email = normalize_identity(user_data.email)

        existing_user = AuthService.find_by_username_or_email(db, username)
        if existing_user is None and email != username:
            existing_user = AuthService.find_by_username_or_email(db, email)

        if existing_user:
            raise DuplicateAccountError(DUPLICATE_ACCOUNT_MESSAGE)

        user = User(
            username=username,
            email=email,
            password_hash=hash_password(user_data.password),
            full_name=user_data.full_name or user_data.username,
        )

        db.add(user)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise DuplicateAccountError(DUPLICATE_ACCOUNT_MESSAGE) from exc

        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        """
        사용자 인증 (로그인)

        사용자명 또는 이메일 모두 허용합니다.

        Args:
            db: 데이터베이스 세션
            username: 사용자명 또는 이메일
            password: 비밀번호

        Returns:
            인증된 사용자 객체, 실패 시 None
        """
        user = AuthService.find_by_username_or_email(db, username)

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
            db: DB 세션
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
            db: DB 세션
            username: 사용자명

        Returns:
            사용자 객체
        """
        return AuthService.find_by_username_or_email(db, username)


# 서비스 인스턴스
auth_service = AuthService()
