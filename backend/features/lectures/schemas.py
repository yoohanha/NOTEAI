"""NOTE_LECTURE API 스키마"""

from datetime import datetime

from pydantic import BaseModel, Field


class CourseCreate(BaseModel):
    """강좌 폴더 생성 요청"""

    name: str = Field(..., min_length=1, max_length=80, description="강좌 이름")


class CourseResponse(BaseModel):
    """강좌 폴더 한 건"""

    id: int
    name: str
    file_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class MaterialResponse(BaseModel):
    """교안 파일 한 건"""

    id: int
    course_id: int
    original_name: str
    mime_type: str
    extension: str
    size_bytes: int
    public_url: str = ""
    created_at: datetime

    class Config:
        from_attributes = True
