"""
인증 관련 Pydantic 스키마
- 회원가입, 로그인, 토큰 응답
"""

from pydantic import BaseModel, EmailStr, Field
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


class UserLogin(BaseModel):
    """로그인 요청"""

    username: str
    password: str


class UserUpdate(BaseModel):
    """사용자 정보 수정"""

    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(UserBase):
    """사용자 정보 응답"""

    id: int
    is_active: bool
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
