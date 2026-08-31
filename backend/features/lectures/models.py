"""
NOTE_LECTURE 모델
- 강좌 폴더(LectureCourse)
- 폴더 안 교안 파일(LectureMaterial)
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from core.database import Base


class LectureCourse(Base):
    """사용자가 만든 강좌 폴더"""

    __tablename__ = "lecture_courses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(80), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<LectureCourse(id={self.id}, name={self.name})>"


class LectureMaterial(Base):
    """강좌 폴더에 올린 교안 파일"""

    __tablename__ = "lecture_materials"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(255), nullable=False)
    public_url = Column(String(512), nullable=False, default="")
    cloudinary_id = Column(String(255), nullable=False, default="")
    mime_type = Column(String(120), nullable=False)
    extension = Column(String(16), nullable=False)
    size_bytes = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<LectureMaterial(id={self.id}, name={self.original_name})>"
