"""
노트 서비스
- CRUD 작업
- 버전 관리
- 검색
"""

import re

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from features.notes.models import Note, NoteVersion, AISummary
from features.notes.schemas import NoteCreate, NoteUpdate
from features.auth.models import User
from datetime import datetime
from typing import List, Optional, Tuple

# 트렌드에서 저장한 노트 본문의 마크다운 링크 (https://...) 를 찾습니다.
_MARKDOWN_URL_RE = re.compile(r"\((https?://[^\s)]+)\)")


class NoteService:
    """노트 관련 비즈니스 로직"""

    @staticmethod
    def create_note(
        db: Session,
        note_data: NoteCreate,
        user: User
    ) -> Note:
        """
        노트 생성

        Args:
            db: 데이터베이스 세션
            note_data: 노트 정보
            user: 작성자

        Returns:
            생성된 노트
        """
        # 노트 생성
        note = Note(
            user_id=user.id,
            title=note_data.title,
            content=note_data.content,
            category=note_data.category,
            tags=note_data.tags or [],
            is_public=note_data.is_public,
        )

        db.add(note)
        db.commit()
        db.refresh(note)

        # 초기 버전 생성 (v1)
        NoteService.create_version(db, note, 1, user.id)

        return note

    @staticmethod
    def get_note(db: Session, note_id: int, user: Optional[User] = None) -> Optional[Note]:
        """
        노트 조회 (권한 검사)

        Args:
            db: 데이터베이스 세션
            note_id: 노트 ID
            user: 현재 사용자 (권한 검사용)

        Returns:
            노트 객체
        """
        note = db.query(Note).filter(Note.id == note_id, Note.deleted_at.is_(None)).first()

        if not note:
            return None

        # 로그인 사용자는 공유 노트를 모두 열람할 수 있습니다.
        if user is None and not note.is_public:
            return None

        # 조회수 증가
        note.view_count += 1
        db.commit()

        return note

    @staticmethod
    def update_note(
        db: Session,
        note_id: int,
        note_data: NoteUpdate,
        user: User
    ) -> Optional[Note]:
        """
        노트 수정

        Args:
            db: 데이터베이스 세션
            note_id: 노트 ID
            note_data: 수정 정보
            user: 현재 사용자 (소유자만 가능)

        Returns:
            수정된 노트
        """
        note = db.query(Note).filter(
            and_(
                Note.id == note_id,
                Note.user_id == user.id,
                Note.deleted_at.is_(None)
            )
        ).first()

        if not note:
            return None

        # 정보 업데이트
        if note_data.title:
            note.title = note_data.title
        if note_data.content:
            note.content = note_data.content
        if note_data.category:
            note.category = note_data.category
        if note_data.tags is not None:
            note.tags = note_data.tags
        if note_data.is_public is not None:
            note.is_public = note_data.is_public

        note.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(note)

        # 새 버전 저장
        # 반드시 필드 수정 이후에 호출해야 합니다.
        # 생성 시 v1이 "생성 직후 상태"를 담으므로, 각 버전은 그 시점의
        # 결과 상태를 나타내는 스냅샷입니다. 수정 전에 호출하면 v2가
        # v1과 동일한 내용이 되어 새 내용이 어디에도 기록되지 않습니다.
        latest_version = db.query(func.max(NoteVersion.version_number)).filter(
            NoteVersion.note_id == note_id
        ).scalar() or 0

        NoteService.create_version(db, note, latest_version + 1, user.id)

        return note

    @staticmethod
    def delete_note(db: Session, note_id: int, user: User) -> bool:
        """
        노트 삭제 (소프트 삭제). 호출부는 관리자만 허용합니다.

        Args:
            db: 데이터베이스 세션
            note_id: 노트 ID
            user: 관리자 (라우트에서 이미 검증)

        Returns:
            성공 여부
        """
        note = db.query(Note).filter(
            and_(
                Note.id == note_id,
                Note.deleted_at.is_(None)
            )
        ).first()

        if not note:
            return False

        note.deleted_at = datetime.utcnow()
        # 트렌드에서 담은 노트면 해당 항목을 다시 저장할 수 있게 표시를 해제합니다.
        NoteService._unmark_related_trends(db, note)
        db.commit()

        return True

    @staticmethod
    def _unmark_related_trends(db: Session, note: Note) -> None:
        """
        삭제된 노트와 연결된 트렌드 항목의 is_saved 표시를 해제합니다.

        트렌드 → 노트 저장 시 본문에 원문 URL을 넣으므로, 그 URL로 매칭합니다.
        URL이 없으면 트렌드에서 저장한 형식(출처 문구)일 때만 제목으로 찾습니다.
        """
        from features.trends.models import TrendItem

        urls = _MARKDOWN_URL_RE.findall(note.content or "")
        query = db.query(TrendItem).filter(TrendItem.is_saved.is_(True))

        if urls:
            query = query.filter(TrendItem.url.in_(urls))
        elif "출처:" in (note.content or "") and note.title:
            query = query.filter(TrendItem.title == note.title)
        else:
            return

        query.update({TrendItem.is_saved: False}, synchronize_session=False)

    @staticmethod
    def get_user_notes(
        db: Session,
        user: User,
        skip: int = 0,
        limit: int = 10,
        category: Optional[str] = None,
        tag: Optional[str] = None
    ) -> Tuple[List[Note], int]:
        """
        사용자의 노트 목록 조회

        Args:
            db: 데이터베이스 세션
            user: 사용자
            skip: 스킵할 항목 수
            limit: 반환할 최대 항목 수
            category: 카테고리 필터
            tag: 태그 필터

        Returns:
            (노트 리스트, 전체 개수)
        """
        query = db.query(Note).filter(Note.deleted_at.is_(None))

        # 필터 적용
        if category:
            query = query.filter(Note.category == category)
        if tag:
            query = query.filter(Note.tags.contains([tag]))

        # 전체 개수
        total = query.count()

        # 페이지네이션
        notes = query.order_by(Note.created_at.desc()).offset(skip).limit(limit).all()

        return notes, total

    @staticmethod
    def search_notes(
        db: Session,
        query_str: str,
        user: Optional[User] = None,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[Note], int]:
        """
        노트 검색 (전문 검색)

        Args:
            db: 데이터베이스 세션
            query_str: 검색어
            user: 현재 사용자 (소유 노트만 검색)
            skip: 스킵할 항목 수
            limit: 반환할 최대 항목 수

        Returns:
            (노트 리스트, 전체 개수)
        """
        # 기본적인 LIKE 검색 (실제로는 전문 검색 엔진 사용)
        filters = [
            Note.deleted_at.is_(None),
            or_(
                Note.title.ilike(f"%{query_str}%"),
                Note.content.ilike(f"%{query_str}%")
            )
        ]

        if user is None:
            filters.append(Note.is_public == True)

        query = db.query(Note).filter(and_(*filters))
        total = query.count()

        notes = query.order_by(Note.updated_at.desc()).offset(skip).limit(limit).all()

        return notes, total

    @staticmethod
    def create_version(
        db: Session,
        note: Note,
        version_number: int,
        user_id: int
    ) -> NoteVersion:
        """
        노트 버전 생성

        Args:
            db: 데이터베이스 세션
            note: 노트 객체
            version_number: 버전 번호
            user_id: 작성자 ID

        Returns:
            생성된 버전
        """
        version = NoteVersion(
            note_id=note.id,
            title=note.title,
            content=note.content,
            version_number=version_number,
            created_by=user_id
        )

        db.add(version)
        db.commit()
        db.refresh(version)

        return version

    @staticmethod
    def get_note_versions(db: Session, note_id: int) -> List[NoteVersion]:
        """
        노트의 모든 버전 조회

        Args:
            db: 데이터베이스 세션
            note_id: 노트 ID

        Returns:
            버전 리스트
        """
        return db.query(NoteVersion).filter(
            NoteVersion.note_id == note_id
        ).order_by(NoteVersion.version_number.desc()).all()


# 서비스 인스턴스
note_service = NoteService()
