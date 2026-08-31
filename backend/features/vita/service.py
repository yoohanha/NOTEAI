"""NOTE_PAPER 이력 항목의 조회/추가/삭제"""

from typing import Optional, Type

from sqlalchemy.orm import Session

from features.auth.models import User
from features.vita.models import VitaCertificate, VitaPublication, VitaTeaching


def _clean(value: Optional[str], limit: int) -> str:
    return (value or "").strip()[:limit]


class VitaService:
    """사용자별 논문/자격증/교육 경력 CRUD"""

    @staticmethod
    def list_all(db: Session, user: User = None) -> dict:
        """공유 이력 세 섹션을 한 번에 반환합니다."""
        return {
            "publications": VitaService._list(db, VitaPublication),
            "certificates": VitaService._list(db, VitaCertificate),
            "teachings": VitaService._list(db, VitaTeaching),
        }

    @staticmethod
    def _list(db: Session, model: Type) -> list:
        return (
            db.query(model)
            .order_by(model.created_at.desc())
            .all()
        )

    @staticmethod
    def add_publication(db: Session, user: User, payload) -> VitaPublication:
        title = _clean(payload.title, 300)
        if not title:
            raise ValueError("논문 제목을 입력하세요.")
        row = VitaPublication(
            user_id=user.id,
            title=title,
            venue=_clean(payload.venue, 200),
            year=_clean(payload.year, 16),
            role=_clean(payload.role, 80),
            link_or_status=_clean(payload.link_or_status, 400),
        )
        return VitaService._save(db, row)

    @staticmethod
    def add_certificate(db: Session, user: User, payload) -> VitaCertificate:
        name = _clean(payload.name, 200)
        if not name:
            raise ValueError("자격증명을 입력하세요.")
        row = VitaCertificate(
            user_id=user.id,
            name=name,
            organization=_clean(payload.organization, 200),
            acquired_on=_clean(payload.acquired_on, 32),
        )
        return VitaService._save(db, row)

    @staticmethod
    def add_teaching(db: Session, user: User, payload) -> VitaTeaching:
        institution = _clean(payload.institution, 200)
        if not institution:
            raise ValueError("기관/학교명을 입력하세요.")
        row = VitaTeaching(
            user_id=user.id,
            institution=institution,
            course=_clean(payload.course, 200),
            period=_clean(payload.period, 80),
            role=_clean(payload.role, 80),
        )
        return VitaService._save(db, row)

    @staticmethod
    def _save(db: Session, row):
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def delete_owned(db: Session, user: User, model: Type, item_id: int) -> bool:
        """항목을 id로 삭제합니다. 호출부는 관리자만 허용합니다."""
        row = (
            db.query(model)
            .filter(model.id == item_id)
            .first()
        )
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True


vita_service = VitaService()
