"""
팀 모델
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class Team(Base):
    """팀 정보"""

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 관계
    owner = relationship("User", back_populates="teams")
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Team(id={self.id}, name={self.name})>"


class TeamMember(Base):
    """팀 멤버"""

    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), default="member")  # member, admin
    joined_at = Column(DateTime, default=datetime.utcnow)

    # 관계
    team = relationship("Team", back_populates="members")
    user = relationship("User")

    def __repr__(self):
        return f"<TeamMember(team_id={self.team_id}, user_id={self.user_id})>"
