"""
NOTE_3D 미디어 자산 모델
- 사용자별 이미지/동영상 메타데이터
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from core.database import Base


class MediaAsset(Base):
    """업로드된 이미지 또는 동영상"""

    __tablename__ = "media_assets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    # 화면에 보여줄 원본 파일명
    original_name = Column(String(255), nullable=False)
    # 디스크에 저장된 파일 이름 (uuid + 확장자)
    stored_name = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    kind = Column(String(20), nullable=False, index=True)  # image | video
    size_bytes = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<MediaAsset(id={self.id}, name={self.original_name})>"
