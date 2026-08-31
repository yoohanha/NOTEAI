"""
NOTE_LECTURE 강좌 폴더와 교안 파일 저장/조회/삭제

교안 본문은 Cloudinary(raw)에 올리고 DB에는 secure_url을 저장합니다.
키가 없으면 개발용 로컬 폴백을 씁니다.
"""

from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy.orm import Session

from core.config import settings
from core.storage import delete_stored, local_file_path, upload_bytes
from features.auth.models import User
from features.lectures.models import LectureCourse, LectureMaterial

# 강의 교안으로 허용하는 확장자와 MIME
ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".odp": "application/vnd.oasis.opendocument.presentation",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".txt": "text/plain",
    ".md": "text/markdown",
}


def classify_file(filename: str, content_type: Optional[str]) -> Tuple[str, str]:
    """확장자로 MIME을 결정합니다."""
    suffix = Path(filename or "").suffix.lower()
    if suffix not in ALLOWED_TYPES:
        raise ValueError(
            "교안 파일(PDF, PPT, PPTX, DOC, DOCX, ODP, ODT, TXT, MD)만 올릴 수 있습니다."
        )

    mime = ALLOWED_TYPES[suffix]
    declared = (content_type or "").split(";")[0].strip().lower()
    if (
        declared
        and declared not in ("application/octet-stream", "")
        and declared not in ALLOWED_TYPES.values()
        and not declared.startswith("application/")
        and not declared.startswith("text/")
    ):
        raise ValueError("파일 형식이 허용 목록과 맞지 않습니다.")

    return suffix, mime


def normalize_course_name(name: Optional[str]) -> str:
    """강좌 이름을 정리하고 길이를 검사합니다."""
    cleaned = (name or "").strip()
    if not cleaned:
        raise ValueError("강좌 이름을 입력하세요.")
    if len(cleaned) > 80:
        raise ValueError("강좌 이름은 80자 이하로 입력하세요.")
    return cleaned


class LectureService:
    """강좌 폴더와 교안 CRUD"""

    @staticmethod
    def list_courses(db: Session, user: User = None) -> List[Tuple[LectureCourse, int]]:
        """공유 강좌와 파일 개수를 최신순으로 반환합니다."""
        courses = (
            db.query(LectureCourse)
            .order_by(LectureCourse.created_at.desc())
            .all()
        )
        result = []
        for course in courses:
            count = (
                db.query(LectureMaterial)
                .filter(LectureMaterial.course_id == course.id)
                .count()
            )
            result.append((course, count))
        return result

    @staticmethod
    def create_course(db: Session, user: User, name: str) -> LectureCourse:
        """새 강좌 폴더를 만듭니다."""
        course = LectureCourse(user_id=user.id, name=normalize_course_name(name))
        db.add(course)
        db.commit()
        db.refresh(course)
        return course

    @staticmethod
    def get_course(db: Session, course_id: int) -> Optional[LectureCourse]:
        return db.query(LectureCourse).filter(LectureCourse.id == course_id).first()

    @staticmethod
    def get_owned_course(
        db: Session, user: User, course_id: int
    ) -> Optional[LectureCourse]:
        """하위 호환: 소유와 무관하게 강좌를 조회합니다."""
        return LectureService.get_course(db, course_id)

    @staticmethod
    def list_materials(
        db: Session, user: User, course_id: int
    ) -> List[LectureMaterial]:
        """강좌 안의 교안을 최신순으로 반환합니다."""
        return (
            db.query(LectureMaterial)
            .filter(LectureMaterial.course_id == course_id)
            .order_by(LectureMaterial.created_at.desc())
            .all()
        )

    @staticmethod
    def get_material(
        db: Session, course_id: int, material_id: int
    ) -> Optional[LectureMaterial]:
        return (
            db.query(LectureMaterial)
            .filter(
                LectureMaterial.id == material_id,
                LectureMaterial.course_id == course_id,
            )
            .first()
        )

    @staticmethod
    def get_owned_material(
        db: Session, user: User, course_id: int, material_id: int
    ) -> Optional[LectureMaterial]:
        return LectureService.get_material(db, course_id, material_id)

    @staticmethod
    async def save_upload(
        db: Session, user: User, course: LectureCourse, file: UploadFile
    ) -> LectureMaterial:
        """교안 파일을 검증한 뒤 Cloudinary(또는 로컬)와 DB에 저장합니다."""
        suffix, mime = classify_file(file.filename, file.content_type)
        payload = await file.read()
        max_size = getattr(settings, "LECTURE_MAX_UPLOAD_SIZE", 80 * 1024 * 1024)

        if not payload:
            raise ValueError("빈 파일은 올릴 수 없습니다.")
        if len(payload) > max_size:
            raise ValueError("파일이 너무 큽니다. 80MB 이하만 올릴 수 있습니다.")

        stored = upload_bytes(
            payload,
            folder=f"noteai/lectures/{user.id}/{course.id}",
            resource_type="raw",
            filename=file.filename or f"untitled{suffix}",
        )

        material = LectureMaterial(
            course_id=course.id,
            user_id=user.id,
            original_name=(file.filename or f"untitled{suffix}")[:255],
            stored_name=stored["public_id"][:255],
            public_url=(stored.get("url") or "")[:1024],
            cloudinary_id=stored["public_id"][:255] if stored.get("storage") == "cloudinary" else "",
            mime_type=mime,
            extension=suffix.lstrip("."),
            size_bytes=len(payload),
        )
        db.add(material)
        db.commit()
        db.refresh(material)
        return material

    @staticmethod
    def file_path(material: LectureMaterial) -> Optional[Path]:
        """로컬 폴백 파일이 있으면 경로를 반환합니다."""
        if getattr(material, "public_url", ""):
            return None
        return local_file_path(material.stored_name)

    @staticmethod
    def delete_material(
        db: Session, user: User, course_id: int, material_id: int
    ) -> bool:
        """교안 한 건을 DB와 클라우드/디스크에서 삭제합니다."""
        material = LectureService.get_material(db, course_id, material_id)
        if not material:
            return False

        delete_stored(material.cloudinary_id or material.stored_name, "raw")
        db.delete(material)
        db.commit()
        return True

    @staticmethod
    def delete_course(db: Session, user: User, course_id: int) -> bool:
        """강좌와 안의 교안을 모두 삭제합니다."""
        course = LectureService.get_course(db, course_id)
        if not course:
            return False

        materials = LectureService.list_materials(db, user, course_id)
        for material in materials:
            delete_stored(material.cloudinary_id or material.stored_name, "raw")
            db.delete(material)

        db.delete(course)
        db.commit()
        return True


lecture_service = LectureService()
