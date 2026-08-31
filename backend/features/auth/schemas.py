"""
인증 관련 Pydantic 스키마
- 회원가입, 로그인, 토큰 응답
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    """사용자 기본 정보"""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)


class UserCreate(UserBase):
    """회원가입 요청"""

    password: str = Field(..., min_length=8)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        username = (value or "").strip().lower()
        if len(username) < 3:
            raise ValueError("사용자명은 3자 이상이어야 합니다.")
        return username

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return str(value).strip().lower()


class UserLogin(BaseModel):
    """로그인 요청"""

    username: str = Field(..., min_length=1, description="사용자명 또는 이메일")
    password: str

    @field_validator("username")
    @classmethod
    def strip_username(cls, value: str) -> str:
        return (value or "").strip()


class UserUpdate(BaseModel):
    """사용자 정보 수정"""

    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(UserBase):
    """사용자 정보 응답"""

    id: int
    is_active: bool
    is_admin: bool = False
    avatar_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """토큰 응답"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """토큰 내부 데이터"""

    user_id: int
    username: str
    exp: datetime


class AuthResponse(BaseModel):
    """인증 응답 (로그인/회원가입)"""

    status: int
    data: dict  # token, user 정보
    message: str
