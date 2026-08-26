"""
Vault 서비스
- 디렉토리 스캔 실행
- 스캔 결과를 Note 테이블로 가져오기(import)
"""

from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from features.auth.models import User
from features.notes.models import Note
from features.vault.parser import content_hash
from features.vault.scanner import VaultScanError, scan_directory
from features.vault.schemas import ImportRequest, ScanRequest


class VaultService:
    """로컬 노트 저장소 관련 비즈니스 로직"""

    @staticmethod
    def scan(request: ScanRequest) -> Dict[str, Any]:
        """
        디렉토리를 스캔하여 노트 목록과 통계를 반환

        Args:
            request: 스캔 요청 (경로 및 필터 옵션)

        Returns:
            scan_directory의 결과 딕셔너리

        Raises:
            VaultScanError: 경로 검증 실패 시
        """
        return scan_directory(
            raw_path=request.path,
            extensions=request.extensions,
            include_patterns=request.include_patterns,
            exclude_patterns=request.exclude_patterns,
            include_hidden=request.include_hidden,
            max_depth=request.max_depth,
            max_files=request.max_files,
            include_content=request.include_content,
        )

    @staticmethod
    def import_notes(
        db: Session,
        request: ImportRequest,
        user: User,
    ) -> Dict[str, Any]:
        """
        스캔된 노트를 사용자 노트로 가져오기

        중복 판정은 두 단계로 수행합니다:
          1) 본문 해시가 같은 기존 노트가 있으면 내용이 동일한 것으로 간주
          2) 제목이 같은 노트가 있으면 update_existing 옵션에 따라 갱신/건너뜀

        Args:
            db: 데이터베이스 세션
            request: 가져오기 요청
            user: 노트 소유자

        Returns:
            생성/갱신/건너뜀/실패 건수와 항목별 결과

        Raises:
            VaultScanError: 경로 검증 실패 시
        """
        # 본문 저장이 필요하므로 항상 content를 포함해 스캔
        scan_request = request.model_copy(update={"include_content": True})
        scan_result = VaultService.scan(scan_request)

        scanned_notes: List[Dict[str, Any]] = scan_result["notes"]

        # 기존 노트를 미리 로드해 파일마다 쿼리하지 않도록 함
        existing_notes = (
            db.query(Note)
            .filter(Note.user_id == user.id, Note.deleted_at.is_(None))
            .all()
        )

        # 제목 -> 노트, 본문해시 -> 노트 인덱스 구성
        by_title: Dict[str, Note] = {}
        by_hash: Dict[str, Note] = {}

        for note in existing_notes:
            by_title.setdefault(note.title, note)
            by_hash.setdefault(content_hash(note.content or ""), note)

        items: List[Dict[str, Any]] = []
        counts = {"created": 0, "updated": 0, "skipped": 0, "failed": 0}

        for scanned in scanned_notes:
            relative_path = scanned["relative_path"]
            title = scanned["title"]
            body = scanned.get("content") or ""

            # 빈 노트는 저장할 가치가 없으므로 건너뜀
            if not body.strip():
                counts["skipped"] += 1
                items.append(
                    {
                        "relative_path": relative_path,
                        "title": title,
                        "action": "skipped",
                        "note_id": None,
                        "reason": "본문이 비어 있음",
                    }
                )
                continue

            file_hash = scanned["content_hash"]

            # 1) 내용이 완전히 동일한 노트가 이미 있는 경우
            duplicate = by_hash.get(file_hash)
            if duplicate is not None and request.skip_duplicates:
                counts["skipped"] += 1
                items.append(
                    {
                        "relative_path": relative_path,
                        "title": title,
                        "action": "skipped",
                        "note_id": duplicate.id,
                        "reason": "내용이 동일한 노트가 이미 존재",
                    }
                )
                continue

            category = scanned.get("category") or request.default_category
            tags = scanned.get("tags") or []

            # 2) 제목이 같은 노트가 있는 경우
            existing = by_title.get(title)

            if existing is not None and not request.update_existing:
                counts["skipped"] += 1
                items.append(
                    {
                        "relative_path": relative_path,
                        "title": title,
                        "action": "skipped",
                        "note_id": existing.id,
                        "reason": "같은 제목의 노트 존재 (update_existing=false)",
                    }
                )
                continue

            try:
                if existing is not None:
                    # 기존 노트 갱신
                    if not request.dry_run:
                        existing.content = body
                        existing.category = category
                        existing.tags = tags
                        existing.updated_at = datetime.utcnow()
                        db.add(existing)

                    counts["updated"] += 1
                    items.append(
                        {
                            "relative_path": relative_path,
                            "title": title,
                            "action": "updated",
                            "note_id": existing.id,
                            "reason": None,
                        }
                    )

                    # 인덱스 갱신 (같은 배치 내 후속 중복 판정에 반영)
                    by_hash[file_hash] = existing
                else:
                    # 신규 노트 생성
                    note = Note(
                        user_id=user.id,
                        title=title,
                        content=body,
                        category=category,
                        tags=tags,
                        is_public=False,
                    )

                    if not request.dry_run:
                        db.add(note)
                        # ID를 결과에 담기 위해 flush로 PK만 확보 (커밋은 마지막에 한 번)
                        db.flush()

                    counts["created"] += 1
                    items.append(
                        {
                            "relative_path": relative_path,
                            "title": title,
                            "action": "created",
                            "note_id": note.id,
                            "reason": None,
                        }
                    )

                    by_title[title] = note
                    by_hash[file_hash] = note

            except Exception as exc:
                # 개별 실패가 전체 배치를 중단시키지 않도록 기록만 하고 계속 진행
                counts["failed"] += 1
                items.append(
                    {
                        "relative_path": relative_path,
                        "title": title,
                        "action": "failed",
                        "note_id": None,
                        "reason": str(exc),
                    }
                )

        # 미리보기가 아니면 한 번에 커밋 (실패 시 전체 롤백)
        if not request.dry_run:
            try:
                db.commit()
            except Exception:
                db.rollback()
                raise

        return {
            "root": scan_result["root"],
            "dry_run": request.dry_run,
            "created": counts["created"],
            "updated": counts["updated"],
            "skipped": counts["skipped"],
            "failed": counts["failed"],
            "items": items,
        }


# 서비스 인스턴스
vault_service = VaultService()
