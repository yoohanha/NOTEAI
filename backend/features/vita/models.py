"""
NOTE_PAPER 이력 모델
- 논문, 자격증, 교육 경력
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from core.database import Base


class VitaPublication(Base):
    """발표 논문/학회 실적"""

    __tablename__ = "vita_publications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String(300), nullable=False)
    venue = Column(String(200), nullable=False, default="")
    year = Column(String(16), nullable=False, default="")
    role = Column(String(80), nullable=False, default="")
    link_or_status = Column(String(400), nullable=False, default="")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class VitaCertificate(Base):
    """취득 자격증"""

    __tablename__ = "vita_certificates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    organization = Column(String(200), nullable=False, default="")
    acquired_on = Column(String(32), nullable=False, default="")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class VitaTeaching(Base):
    """강의·교육 경력"""

    __tablename__ = "vita_teachings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    institution = Column(String(200), nullable=False)
    course = Column(String(200), nullable=False, default="")
    period = Column(String(80), nullable=False, default="")
    role = Column(String(80), nullable=False, default="")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
