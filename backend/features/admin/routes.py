"""
관리자 API

- GET /api/admin/users  전체 회원 목록 (관리자 이메일만)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from features.auth.deps import get_current_admin
from features.auth.models import User

router = APIRouter(prefix="/admin", tags=["admin"])


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


@router.get("/users", response_model=dict)
async def list_all_users(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    """
    가입된 모든 회원의 아이디·이메일·가입일을 반환합니다.

    비밀번호 해시는 포함하지 않습니다.
    """
    users = db.query(User).order_by(User.created_at.desc()).all()
    items = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": _iso(user.created_at),
        }
        for user in users
    ]
    return {
        "status": 200,
        "data": {"items": items, "total": len(items)},
        "message": f"{len(items)}명의 회원",
    }
