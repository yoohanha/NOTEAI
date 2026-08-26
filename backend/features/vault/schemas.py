"""
Vault 요청/응답 스키마
- 디렉토리 스캔 요청/응답
- 노트 가져오기(import) 요청/응답
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    """디렉토리 스캔 요청"""

    path: str = Field(..., description="스캔할 로컬 디렉토리 경로", min_length=1)
    extensions: Optional[List[str]] = Field(
        None, description="대상 확장자 목록 (예: ['.md', '.txt'])"
    )
    include_patterns: Optional[List[str]] = Field(
        None, description="포함할 glob 패턴 (지정 시 화이트리스트로 동작)"
    )
    exclude_patterns: Optional[List[str]] = Field(
        None, description="제외할 glob 패턴 (예: ['drafts/*'])"
    )
    include_hidden: bool = Field(False, description="숨김 파일/디렉토리 포함 여부")
    max_depth: Optional[int] = Field(
        None, ge=0, le=20, description="최대 탐색 깊이 (0이면 루트만)"
    )
    max_files: int = Field(
        1000, ge=1, le=10000, description="수집할 최대 파일 수"
    )
    include_content: bool = Field(
        False, description="응답에 본문 전체 포함 여부 (응답 크기 주의)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "path": "C:/Users/me/Documents/research-notes",
                "extensions": [".md"],
                "exclude_patterns": ["archive/*"],
                "max_files": 500,
            }
        }


class ScannedNote(BaseModel):
    """스캔된 노트 한 건"""

    path: str = Field(..., description="파일 절대 경로")
    relative_path: str = Field(..., description="스캔 루트 기준 상대 경로")
    file_name: str = Field(..., description="파일명")
    extension: str = Field(..., description="확장자")
    title: str = Field(..., description="추출된 제목")
    excerpt: str = Field("", description="본문 미리보기")
    content: Optional[str] = Field(None, description="본문 (include_content=True일 때)")
    category: Optional[str] = Field(None, description="추출된 카테고리")
    tags: List[str] = Field(default_factory=list, description="태그 목록")
    wikilinks: List[str] = Field(default_factory=list, description="위키링크 대상")
    urls: List[str] = Field(default_factory=list, description="외부 링크")
    frontmatter: Dict[str, Any] = Field(
        default_factory=dict, description="파싱된 프론트매터"
    )
    word_count: int = Field(0, description="단어 수")
    char_count: int = Field(0, description="글자 수")
    size_bytes: int = Field(0, description="파일 크기(바이트)")
    content_hash: str = Field(..., description="본문 SHA-256 해시")
    modified_at: datetime = Field(..., description="최종 수정 시각")


class ScanError(BaseModel):
    """개별 파일 처리 실패 정보"""

    path: str = Field(..., description="실패한 파일 경로")
    error: str = Field(..., description="실패 사유")


class TagCount(BaseModel):
    """태그 사용 빈도"""

    tag: str
    count: int


class ScanStats(BaseModel):
    """스캔 통계"""

    total_files: int = Field(0, description="성공적으로 파싱한 파일 수")
    total_bytes: int = Field(0, description="총 바이트 수")
    total_words: int = Field(0, description="총 단어 수")
    error_count: int = Field(0, description="실패한 파일 수")
    duplicate_groups: int = Field(0, description="내용이 동일한 파일 그룹 수")
    unique_tags: int = Field(0, description="고유 태그 수")
    top_tags: List[TagCount] = Field(default_factory=list, description="상위 태그")
    truncated: bool = Field(False, description="max_files 제한으로 잘렸는지 여부")


class ScanResponse(BaseModel):
    """스캔 결과"""

    root: str = Field(..., description="검증된 스캔 루트 경로")
    notes: List[ScannedNote] = Field(default_factory=list)
    errors: List[ScanError] = Field(default_factory=list)
    duplicates: List[List[str]] = Field(
        default_factory=list, description="내용이 같은 파일 경로 그룹"
    )
    stats: ScanStats


class ImportRequest(ScanRequest):
    """
    스캔 결과를 NOTEAI 노트로 가져오기 요청

    ScanRequest의 모든 필터 옵션을 그대로 사용하며,
    중복 처리 정책 옵션이 추가됩니다.
    """

    skip_duplicates: bool = Field(
        True, description="이미 같은 내용의 노트가 있으면 건너뛸지 여부"
    )
    update_existing: bool = Field(
        False, description="제목이 같은 기존 노트를 갱신할지 여부"
    )
    default_category: Optional[str] = Field(
        None, description="카테고리를 추출하지 못한 노트에 적용할 기본값"
    )
    dry_run: bool = Field(
        False, description="True면 실제 저장 없이 결과만 미리 확인"
    )


class ImportResultItem(BaseModel):
    """가져오기 처리 결과 한 건"""

    relative_path: str = Field(..., description="스캔 루트 기준 상대 경로")
    title: str = Field(..., description="노트 제목")
    action: str = Field(..., description="created / updated / skipped / failed")
    note_id: Optional[int] = Field(None, description="생성/수정된 노트 ID")
    reason: Optional[str] = Field(None, description="건너뛰거나 실패한 사유")


class ImportResponse(BaseModel):
    """가져오기 결과 요약"""

    root: str = Field(..., description="스캔 루트 경로")
    dry_run: bool = Field(False, description="미리보기 실행 여부")
    created: int = Field(0, description="새로 만든 노트 수")
    updated: int = Field(0, description="갱신한 노트 수")
    skipped: int = Field(0, description="건너뛴 노트 수")
    failed: int = Field(0, description="실패한 노트 수")
    items: List[ImportResultItem] = Field(default_factory=list)
