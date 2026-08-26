"""
인증 관련 데이터 모델
- User: 사용자 정보
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class User(Base):
    """사용자 모델"""

    __tablename__ = "users"

    # 기본 정보
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # 프로필
    full_name = Column(String(100))
    bio = Column(String(500))
    avatar_url = Column(String(255))

    # 상태
    is_active = Column(Boolean, default=True)

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계
    notes = relationship("Note", back_populates="author", foreign_keys="Note.user_id")
    comments = relationship("Comment", back_populates="author")
    teams = relationship("Team", back_populates="owner")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"
