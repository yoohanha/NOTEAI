"""NOTE_3D 미디어 API 스키마"""

from datetime import datetime

from pydantic import BaseModel, Field


class MediaAssetResponse(BaseModel):
    """미디어 목록/업로드 응답 한 건"""

    id: int
    original_name: str
    mime_type: str
    kind: str = Field(..., description="image 또는 video")
    size_bytes: int
    public_url: str = ""
    created_at: datetime

    class Config:
        from_attributes = True
