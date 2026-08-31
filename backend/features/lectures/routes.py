"""
NOTE_LECTURE API

- GET    /api/lectures                         내 강좌 목록
- POST   /api/lectures                         강좌 폴더 생성
- GET    /api/lectures/{id}                    강좌와 교안 목록
- DELETE /api/lectures/{id}                    강좌 폴더 삭제
- POST   /api/lectures/{id}/files              교안 업로드
- GET    /api/lectures/{id}/files/{file_id}    교안 본문
- DELETE /api/lectures/{id}/files/{file_id}    교안 삭제
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from core.database import get_db
from features.auth.deps import get_current_admin, get_current_user
from features.auth.models import User
from features.lectures.schemas import CourseCreate, CourseResponse, MaterialResponse
from features.lectures.service import lecture_service

router = APIRouter(prefix="/lectures", tags=["lectures"])


def _iso(value):
    """datetime을 ISO 문자열로 바꿉니다."""
    return value.isoformat() if hasattr(value, "isoformat") else value


def _course_dict(course, file_count: int = 0) -> dict:
    data = CourseResponse.from_orm(course).dict()
    data["file_count"] = file_count
    data["created_at"] = _iso(data.get("created_at"))
    return data


def _material_dict(material) -> dict:
    data = MaterialResponse.from_orm(material).dict()
    data["created_at"] = _iso(data.get("created_at"))
    return data


@router.get("", response_model=dict)
async def list_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """현재 사용자의 강좌 폴더 목록"""
    rows = lecture_service.list_courses(db, current_user)
    items = [_course_dict(course, count) for course, count in rows]
    return {
        "status": 200,
        "data": {"items": items, "total": len(items)},
        "message": f"{len(items)}개의 강좌",
    }


@router.post("", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_course(
    payload: CourseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """강좌 이름을 받아 새 폴더를 만듭니다."""
    try:
        course = lecture_service.create_course(db, current_user, payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return {
        "status": 201,
        "data": _course_dict(course, 0),
        "message": "강좌 폴더를 만들었습니다",
    }


@router.get("/{course_id}", response_model=dict)
async def get_course(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """강좌 상세와 교안 목록"""
    course = lecture_service.get_owned_course(db, current_user, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="강좌를 찾을 수 없습니다")

    files = lecture_service.list_materials(db, current_user, course_id)
    return {
        "status": 200,
        "data": {
            "course": _course_dict(course, len(files)),
            "files": [_material_dict(item) for item in files],
        },
        "message": "강좌 상세",
    }


@router.delete("/{course_id}", response_model=dict)
async def delete_course(
    course_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    """강좌 폴더 삭제는 관리자만 할 수 있습니다."""
    deleted = lecture_service.delete_course(db, current_user, course_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="삭제할 강좌를 찾을 수 없습니다",
        )

    return {
        "status": 200,
        "data": {"id": course_id, "deleted": True},
        "message": "강좌 폴더를 삭제했습니다",
    }


@router.post("/{course_id}/files", status_code=status.HTTP_201_CREATED, response_model=dict)
async def upload_material(
    course_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """선택한 강좌에 교안 파일을 올립니다."""
    course = lecture_service.get_owned_course(db, current_user, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="강좌를 찾을 수 없습니다")

    try:
        material = await lecture_service.save_upload(db, current_user, course, file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return {
        "status": 201,
        "data": _material_dict(material),
        "message": "교안을 올렸습니다",
    }


@router.get("/{course_id}/files/{file_id}")
async def download_material(
    course_id: int,
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """소유한 교안 본문 또는 클라우드 주소로 보냅니다."""
    material = lecture_service.get_owned_material(db, current_user, course_id, file_id)
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="파일을 찾을 수 없습니다")

    if getattr(material, "public_url", ""):
        return RedirectResponse(material.public_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    path = lecture_service.file_path(material)
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="저장된 파일이 없습니다")

    return FileResponse(
        path,
        media_type=material.mime_type,
        filename=material.original_name,
    )


@router.delete("/{course_id}/files/{file_id}", response_model=dict)
async def delete_material(
    course_id: int,
    file_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    """교안 삭제는 관리자만 할 수 있습니다."""
    deleted = lecture_service.delete_material(db, current_user, course_id, file_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="삭제할 파일을 찾을 수 없습니다",
        )

    return {
        "status": 200,
        "data": {"id": file_id, "deleted": True},
        "message": "교안을 삭제했습니다",
    }
