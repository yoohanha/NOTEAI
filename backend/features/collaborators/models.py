"""
협업자 모델
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class NoteCollaborator(Base):
    """노트 협업자"""

    __tablename__ = "note_collaborators"

    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(Integer, ForeignKey("notes.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    permission = Column(String(20), default="read")  # read, edit, admin
    added_at = Column(DateTime, default=datetime.utcnow)

    # 관계
    note = relationship("Note", back_populates="collaborators")
    user = relationship("User")

    def __repr__(self):
        return f"<NoteCollaborator(note_id={self.note_id}, user_id={self.user_id})>"
