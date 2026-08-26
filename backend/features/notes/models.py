"""
노트 관련 데이터 모델
- Note: 노트 정보
- NoteVersion: 노트 버전 관리
- AISummary: AI 생성 요약
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class Note(Base):
    """노트 모델"""

    __tablename__ = "notes"

    # 기본 정보
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)  # 마크다운

    # 분류
    category = Column(String(50))
    tags = Column(JSON, default=[])  # ["ai", "ml", "research"]

    # 공개 설정
    is_public = Column(Boolean, default=False, index=True)

    # 통계
    view_count = Column(Integer, default=0)

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)  # 소프트 삭제

    # 관계
    author = relationship("User", back_populates="notes", foreign_keys=[user_id])
    versions = relationship("NoteVersion", back_populates="note", cascade="all, delete-orphan")
    ai_summary = relationship("AISummary", back_populates="note", uselist=False)
    comments = relationship("Comment", back_populates="note", cascade="all, delete-orphan")
    collaborators = relationship("NoteCollaborator", back_populates="note", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Note(id={self.id}, title={self.title}, user_id={self.user_id})>"


class NoteVersion(Base):
    """노트 버전 (변경 이력)"""

    __tablename__ = "note_versions"

    # 기본 정보
    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(Integer, ForeignKey("notes.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    # 버전 정보
    version_number = Column(Integer, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # 관계
    note = relationship("Note", back_populates="versions")

    def __repr__(self):
        return f"<NoteVersion(note_id={self.note_id}, version={self.version_number})>"


class AISummary(Base):
    """AI 생성 요약"""

    __tablename__ = "ai_summaries"

    # 기본 정보
    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(Integer, ForeignKey("notes.id"), unique=True, nullable=False)
    summary_text = Column(Text, nullable=False)

    # 추출 정보
    keywords = Column(JSON, default=[])  # [{"word": "ai", "weight": 0.95}, ...]
    category = Column(String(50))  # 자동 분류 카테고리

    # 생성 정보
    generated_at = Column(DateTime, default=datetime.utcnow)

    # 관계
    note = relationship("Note", back_populates="ai_summary")

    def __repr__(self):
        return f"<AISummary(note_id={self.note_id})>"
