"""
트렌드 서비스
- 외부 소스에서 수집 후 중복 제거하여 저장
- 저장된 트렌드 조회 및 필터링
- 트렌드 항목을 노트로 변환
"""

import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from core.config import settings
from core.database import varchar_limit
from features.auth.models import User
from features.notes.models import Note
from features.trends.client import fetch_all
from features.trends.models import TrendItem
from features.trends.schemas import RefreshRequest
from features.trends.sources import get_sources

# 컬럼이 TEXT여도 한 항목이 비정상적으로 커지지 않게 상한을 둡니다.
_TITLE_MAX = 2000
_URL_MAX = 2000
_IMAGE_URL_MAX = 2000
_AUTHOR_MAX = 500
_SOURCE_NAME_MAX = 255
_SOURCE_KEY_MAX = 80
_CATEGORY_MAX = 80
_SUMMARY_MAX = 8000


def clip_text(value: Optional[str], limit: int) -> str:
    """None과 공백을 정리한 뒤 글자 수 상한으로 자릅니다."""
    text = "" if value is None else str(value)
    if limit <= 0:
        return text
    return text[:limit]


def url_hash(url: str) -> str:
    """
    URL을 정규화하여 해시 계산 (중복 판정 키)

    쿼리스트링의 추적 파라미터 때문에 같은 기사가 다르게 보이는 것을
    막기 위해 utm_* 파라미터를 제거한 뒤 해시를 계산합니다.

    Args:
        url: 원문 링크

    Returns:
        SHA-256 16진수 문자열
    """
    normalized = url.strip().rstrip("/")

    # 추적 파라미터 제거
    if "?" in normalized:
        base, _, query = normalized.partition("?")
        kept = [
            param
            for param in query.split("&")
            if param and not param.lower().startswith(("utm_", "fbclid", "gclid"))
        ]
        normalized = f"{base}?{'&'.join(kept)}" if kept else base

    return hashlib.sha256(normalized.lower().encode("utf-8")).hexdigest()


class TrendService:
    """기술 트렌드 수집 관련 비즈니스 로직"""

    @staticmethod
    async def refresh(
        db: Session,
        request: RefreshRequest,
    ) -> Dict[str, Any]:
        """
        외부 소스에서 트렌드를 수집하고 새 항목만 저장

        Args:
            db: 데이터베이스 세션
            request: 수집 요청 (소스/키워드/제한)

        Returns:
            수집 통계와 항목 목록
        """
        sources = get_sources(request.sources)

        if not sources:
            return {
                "fetched": 0,
                "saved": 0,
                "duplicates": 0,
                "sources_used": [],
                "errors": ["사용 가능한 소스가 없습니다"],
                "items": [],
            }

        raw_items, errors = await fetch_all(sources)

        # 소스별 개수 제한 및 키워드 필터 적용
        filtered = TrendService._apply_filters(
            raw_items,
            keywords=request.keywords,
            limit_per_source=request.limit_per_source,
        )

        if not request.persist:
            # 저장하지 않고 조회만 하는 경우
            return {
                "fetched": len(raw_items),
                "saved": 0,
                "duplicates": 0,
                "sources_used": [source.key for source in sources],
                "errors": errors,
                "items": filtered,
            }

        saved, duplicates, stored_items, persist_errors = TrendService._persist(
            db, filtered
        )
        errors.extend(persist_errors)

        return {
            "fetched": len(raw_items),
            "saved": saved,
            "duplicates": duplicates,
            "sources_used": [source.key for source in sources],
            "errors": errors,
            "items": stored_items,
        }

    @staticmethod
    def _apply_filters(
        items: List[Dict[str, Any]],
        keywords: Optional[List[str]],
        limit_per_source: int,
    ) -> List[Dict[str, Any]]:
        """
        키워드 필터와 소스별 개수 제한을 적용

        Args:
            items: 수집된 원본 항목
            keywords: 제목/요약에 포함되어야 할 키워드 (하나라도 일치하면 통과)
            limit_per_source: 소스당 최대 항목 수

        Returns:
            필터링된 항목 목록
        """
        lowered_keywords = [kw.lower().strip() for kw in (keywords or []) if kw.strip()]

        per_source_count: Dict[str, int] = {}
        result: List[Dict[str, Any]] = []

        # 같은 배치 안에서의 중복 URL도 걸러냄
        seen_hashes = set()

        for item in items:
            source_key = item["source_key"]

            if per_source_count.get(source_key, 0) >= limit_per_source:
                continue

            if lowered_keywords:
                haystack = f"{item['title']} {item['summary']}".lower()
                if not any(kw in haystack for kw in lowered_keywords):
                    continue

            item_hash = url_hash(item["url"])

            if item_hash in seen_hashes:
                continue

            seen_hashes.add(item_hash)
            item["url_hash"] = item_hash

            result.append(item)
            per_source_count[source_key] = per_source_count.get(source_key, 0) + 1

        return result

    @staticmethod
    def _persist(
        db: Session,
        items: List[Dict[str, Any]],
    ) -> Tuple[int, int, List[Dict[str, Any]]]:
        """
        새 항목만 DB에 저장

        Args:
            db: 데이터베이스 세션
            items: 필터링된 항목 목록

        Returns:
            (저장 건수, 중복 건수, 저장/조회된 항목 목록, 항목별 오류)
        """
        if not items:
            return 0, 0, [], []

        hashes = [item["url_hash"] for item in items]

        # 이미 저장된 해시를 한 번의 쿼리로 조회
        existing_hashes = {
            row[0]
            for row in db.query(TrendItem.url_hash)
            .filter(TrendItem.url_hash.in_(hashes))
            .all()
        }

        saved = 0
        duplicates = 0
        persist_errors: List[str] = []
        new_records: List[TrendItem] = []

        # 실제 DB 컬럼이 모델보다 짧을 수 있으므로, 조회한 길이와 상한 중 작은 쪽을 씁니다.
        title_limit = varchar_limit("trend_items", "title", _TITLE_MAX)
        url_limit = varchar_limit("trend_items", "url", _URL_MAX)
        image_limit = varchar_limit("trend_items", "image_url", _IMAGE_URL_MAX)
        author_limit = varchar_limit("trend_items", "author", _AUTHOR_MAX)
        source_name_limit = varchar_limit(
            "trend_items", "source_name", _SOURCE_NAME_MAX
        )
        source_key_limit = varchar_limit("trend_items", "source_key", _SOURCE_KEY_MAX)
        category_limit = varchar_limit("trend_items", "category", _CATEGORY_MAX)

        for item in items:
            if item["url_hash"] in existing_hashes:
                duplicates += 1
                continue

            image_url = clip_text(item.get("image_url"), image_limit) or None
            record = TrendItem(
                title=clip_text(item.get("title"), title_limit) or "(제목 없음)",
                summary=clip_text(item.get("summary"), _SUMMARY_MAX),
                url=clip_text(item.get("url"), url_limit),
                url_hash=clip_text(item.get("url_hash"), 64),
                source_key=clip_text(item.get("source_key"), source_key_limit),
                source_name=clip_text(item.get("source_name"), source_name_limit) or None,
                category=clip_text(item.get("category"), category_limit) or None,
                author=clip_text(item.get("author"), author_limit) or None,
                image_url=image_url,
                tags=item.get("tags") or [],
                published_at=item.get("published_at"),
                fetched_at=datetime.utcnow(),
                is_saved=False,
            )

            # 한 항목의 길이/유니크 오류가 배치 전체를 롤백하지 않게 세이브포인트를 씁니다.
            try:
                with db.begin_nested():
                    db.add(record)
                    db.flush()
                new_records.append(record)
                saved += 1
                existing_hashes.add(item["url_hash"])
            except IntegrityError:
                duplicates += 1
                existing_hashes.add(item["url_hash"])
            except DataError as exc:
                persist_errors.append(
                    f"{item.get('title') or '항목'}: 컬럼 길이 초과를 건너뜀 ({exc})"
                )
            except Exception as exc:  # noqa: BLE001 - 한 건 실패로 수집을 멈추지 않습니다
                persist_errors.append(
                    f"{item.get('title') or '항목'}: 저장 실패 ({exc})"
                )

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        # 커밋 후 ID가 채워진 상태로 직렬화
        for record in new_records:
            db.refresh(record)

        return (
            saved,
            duplicates,
            [TrendService._to_dict(r) for r in new_records],
            persist_errors,
        )

    @staticmethod
    def _to_dict(record: TrendItem) -> Dict[str, Any]:
        """
        TrendItem ORM 객체를 응답용 딕셔너리로 변환

        Args:
            record: 트렌드 항목

        Returns:
            직렬화 가능한 딕셔너리
        """
        return {
            "id": record.id,
            "title": record.title,
            "summary": record.summary or "",
            "url": record.url,
            "source_key": record.source_key,
            "source_name": record.source_name,
            "category": record.category,
            "author": record.author,
            "image_url": record.image_url,
            "tags": record.tags or [],
            "is_saved": bool(record.is_saved),
            "published_at": record.published_at,
            "fetched_at": record.fetched_at,
        }

    @staticmethod
    def list_trends(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        source_key: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        days: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        저장된 트렌드 목록 조회

        Args:
            db: 데이터베이스 세션
            skip: 건너뛸 항목 수
            limit: 조회할 항목 수
            source_key: 소스 필터
            category: 분류 필터
            search: 제목 부분 일치 검색어
            days: 최근 N일 이내 항목만 조회

        Returns:
            (항목 목록, 전체 개수)
        """
        query = db.query(TrendItem)

        if source_key:
            query = query.filter(TrendItem.source_key == source_key)

        if category:
            query = query.filter(TrendItem.category == category)

        if search:
            query = query.filter(TrendItem.title.ilike(f"%{search}%"))

        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.filter(TrendItem.fetched_at >= cutoff)

        total = query.count()

        # 발행 시각이 없는 항목도 뒤로 밀리도록 수집 시각을 보조 정렬 키로 사용
        records = (
            query.order_by(desc(TrendItem.published_at), desc(TrendItem.fetched_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

        return [TrendService._to_dict(record) for record in records], total

    @staticmethod
    def get_trend(db: Session, trend_id: int) -> Optional[TrendItem]:
        """
        단일 트렌드 항목 조회

        Args:
            db: 데이터베이스 세션
            trend_id: 항목 ID

        Returns:
            트렌드 항목 또는 None
        """
        return db.query(TrendItem).filter(TrendItem.id == trend_id).first()

    @staticmethod
    def save_as_note(
        db: Session,
        trend: TrendItem,
        user: User,
        category: Optional[str] = None,
        extra_tags: Optional[List[str]] = None,
    ) -> Note:
        """
        트렌드 항목을 사용자의 노트로 저장

        Args:
            db: 데이터베이스 세션
            trend: 저장할 트렌드 항목
            user: 노트 소유자
            category: 노트 카테고리 (미지정 시 트렌드 분류 사용)
            extra_tags: 추가 태그

        Returns:
            생성된 노트
        """
        # 원문 링크와 출처를 남긴 마크다운 본문 구성
        published = (
            trend.published_at.strftime("%Y-%m-%d")
            if trend.published_at
            else "발행일 미상"
        )

        content_lines = [
            f"# {trend.title}",
            "",
            f"> 출처: [{trend.source_name or trend.source_key}]({trend.url})",
            f"> 발행일: {published}",
        ]

        if trend.author:
            content_lines.append(f"> 작성자: {trend.author}")

        content_lines.extend(["", trend.summary or "_요약 없음_", "", "---", "", "## 메모", ""])

        # 태그 병합 (트렌드 태그 + 소스 key + 사용자 지정 태그)
        tags = list(trend.tags or [])
        tags.append(trend.source_key)
        tags.extend(extra_tags or [])

        # 중복 제거 (순서 유지)
        seen = set()
        merged_tags = []
        for tag in tags:
            normalized = str(tag).strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                merged_tags.append(normalized)

        note = Note(
            user_id=user.id,
            title=trend.title[:255],
            content="\n".join(content_lines),
            category=category or trend.category or "trend",
            tags=merged_tags,
            is_public=False,
        )

        db.add(note)

        # 같은 항목을 다시 저장하지 않도록 표시
        trend.is_saved = True
        db.add(trend)

        try:
            db.commit()
            db.refresh(note)
        except Exception:
            db.rollback()
            raise

        return note


# 서비스 인스턴스
trend_service = TrendService()
