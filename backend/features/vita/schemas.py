"""NOTE_PAPER 이력 API 스키마"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PublicationCreate(BaseModel):
    """논문 추가 요청"""

    title: str = Field(..., min_length=1, max_length=300)
    venue: str = Field("", max_length=200)
    year: str = Field("", max_length=16)
    role: str = Field("", max_length=80)
    link_or_status: str = Field("", max_length=400)


class CertificateCreate(BaseModel):
    """자격증 추가 요청"""

    name: str = Field(..., min_length=1, max_length=200)
    organization: str = Field("", max_length=200)
    acquired_on: str = Field("", max_length=32)


class TeachingCreate(BaseModel):
    """교육 경력 추가 요청"""

    institution: str = Field(..., min_length=1, max_length=200)
    course: str = Field("", max_length=200)
    period: str = Field("", max_length=80)
    role: str = Field("", max_length=80)


class PublicationResponse(BaseModel):
    id: int
    title: str
    venue: str
    year: str
    role: str
    link_or_status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CertificateResponse(BaseModel):
    id: int
    name: str
    organization: str
    acquired_on: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TeachingResponse(BaseModel):
    id: int
    institution: str
    course: str
    period: str
    role: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
