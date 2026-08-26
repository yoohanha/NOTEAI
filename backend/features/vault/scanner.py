"""
로컬 노트 디렉토리 스캐너
- 재귀적 디렉토리 순회 및 노트 파일 수집
- 경로 화이트리스트 검증 (디렉토리 탈출 차단)
- 심볼릭 링크 순환 방지, 파일 크기/개수 상한
- 인코딩 자동 감지 (UTF-8 / UTF-8-SIG / CP949)

Filesystem MCP 서버가 연결되어 있지 않아도 동작하도록 표준 라이브러리의
pathlib/os만 사용합니다. 나중에 MCP 기반 원격 파일 접근으로 교체하려면
`read_note_file` / `iter_note_files` 두 함수만 대체하면 됩니다.
"""

import os
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from core.config import settings
from features.vault.parser import parse_note_text

# 스캔 대상에서 항상 제외할 디렉토리 이름
# (버전관리/캐시/의존성 디렉토리는 노트가 아니며 파일 수가 매우 많음)
DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".svn",
    ".hg",
    ".obsidian",
    ".trash",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
    "dist",
    "build",
}

# 지원 파일 확장자 (소문자 기준)
DEFAULT_EXTENSIONS = (".md", ".markdown", ".mdx", ".txt")

# 인코딩 자동 감지 시도 순서 (한글 Windows 환경 고려)
_ENCODING_CANDIDATES = ("utf-8-sig", "utf-8", "cp949", "euc-kr")


class VaultScanError(Exception):
    """스캔 단계에서 발생하는 오류 (라우트에서 400/403으로 변환)"""


def resolve_vault_root(raw_path: str) -> Path:
    """
    사용자가 입력한 경로를 검증하고 절대 경로로 변환

    설정의 VAULT_ALLOWED_ROOTS 가 비어 있지 않으면, 해당 루트 하위 경로만
    허용하여 임의 디렉토리 열람(경로 탈출)을 차단합니다.

    Args:
        raw_path: 사용자 입력 디렉토리 경로

    Returns:
        검증된 절대 경로

    Raises:
        VaultScanError: 경로가 없거나, 디렉토리가 아니거나, 허용 범위 밖인 경우
    """
    if not raw_path or not raw_path.strip():
        raise VaultScanError("스캔할 디렉토리 경로가 비어 있습니다")

    # 사용자 홈(~) 확장 후 심볼릭 링크까지 해석한 실제 경로 획득
    try:
        path = Path(os.path.expanduser(raw_path.strip())).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise VaultScanError(f"경로를 확인할 수 없습니다: {raw_path}") from exc

    if not path.is_dir():
        raise VaultScanError(f"디렉토리가 아닙니다: {path}")

    allowed_roots = _allowed_roots()

    # 화이트리스트가 설정된 경우에만 범위 검사 수행
    if allowed_roots and not any(_is_within(path, root) for root in allowed_roots):
        raise VaultScanError(
            f"허용되지 않은 경로입니다: {path} "
            f"(허용 루트: {', '.join(str(r) for r in allowed_roots)})"
        )

    return path


def _allowed_roots() -> List[Path]:
    """
    설정에서 허용 루트 목록을 읽어 절대 경로 리스트로 변환

    Returns:
        해석 가능한 허용 루트 목록 (설정이 비어 있으면 빈 리스트)
    """
    roots: List[Path] = []

    for raw in getattr(settings, "VAULT_ALLOWED_ROOTS", []) or []:
        try:
            roots.append(Path(os.path.expanduser(str(raw))).resolve())
        except (OSError, RuntimeError):
            # 존재하지 않는 루트 설정은 조용히 무시 (다른 루트로 계속 검사)
            continue

    return roots


def _is_within(path: Path, root: Path) -> bool:
    """
    path가 root의 하위 경로인지 확인

    Args:
        path: 검사 대상 경로 (절대 경로)
        root: 기준 루트 (절대 경로)

    Returns:
        하위 경로이거나 root 자신이면 True
    """
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _should_skip_dir(
    dir_name: str,
    exclude_dirs: set,
    include_hidden: bool,
) -> bool:
    """
    디렉토리를 순회 대상에서 제외할지 판단

    Args:
        dir_name: 디렉토리 이름 (경로 아님)
        exclude_dirs: 제외 이름 집합
        include_hidden: 숨김 디렉토리 포함 여부

    Returns:
        건너뛰어야 하면 True
    """
    if dir_name in exclude_dirs:
        return True

    if not include_hidden and dir_name.startswith("."):
        return True

    return False


def _matches_patterns(relative_path: str, patterns: List[str]) -> bool:
    """
    상대 경로가 glob 패턴 중 하나라도 일치하는지 확인

    Args:
        relative_path: 루트 기준 상대 경로 (POSIX 구분자)
        patterns: fnmatch 패턴 목록

    Returns:
        하나라도 일치하면 True
    """
    name = relative_path.rsplit("/", 1)[-1]

    return any(
        fnmatch(relative_path, pattern) or fnmatch(name, pattern)
        for pattern in patterns
    )


def iter_note_files(
    root: Path,
    extensions: Tuple[str, ...] = DEFAULT_EXTENSIONS,
    exclude_dirs: Optional[set] = None,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    include_hidden: bool = False,
    max_depth: Optional[int] = None,
    max_files: int = 5000,
) -> Iterator[Path]:
    """
    루트 디렉토리를 재귀 순회하며 노트 파일 경로를 생성(yield)

    os.walk의 followlinks 기본값(False)을 유지하고 방문한 디렉토리의
    inode를 기록해 심볼릭 링크로 인한 무한 순환을 방지합니다.

    Args:
        root: 스캔 시작 디렉토리 (절대 경로)
        extensions: 대상 확장자 튜플 (소문자, 점 포함)
        exclude_dirs: 제외할 디렉토리 이름 집합
        include_patterns: 포함할 glob 패턴 (지정 시 화이트리스트로 동작)
        exclude_patterns: 제외할 glob 패턴
        include_hidden: 숨김 파일/디렉토리 포함 여부
        max_depth: 최대 탐색 깊이 (None이면 제한 없음, 0이면 루트만)
        max_files: 수집할 최대 파일 수 (초과 시 순회 중단)

    Yields:
        조건에 맞는 파일의 절대 경로
    """
    exclude_dirs = exclude_dirs if exclude_dirs is not None else set(DEFAULT_EXCLUDE_DIRS)
    include_patterns = include_patterns or []
    exclude_patterns = exclude_patterns or []

    visited_dirs = set()
    yielded = 0

    for current_dir, sub_dirs, file_names in os.walk(root, followlinks=False):
        current_path = Path(current_dir)

        # 심볼릭 링크로 인한 순환 방지 (같은 실제 디렉토리 재방문 차단)
        try:
            stat_result = current_path.stat()
            dir_key = (stat_result.st_dev, stat_result.st_ino)
        except OSError:
            # 접근 불가 디렉토리는 건너뜀
            sub_dirs[:] = []
            continue

        if dir_key in visited_dirs:
            sub_dirs[:] = []
            continue

        visited_dirs.add(dir_key)

        # 현재 깊이 계산 (루트는 0)
        try:
            depth = len(current_path.relative_to(root).parts)
        except ValueError:
            depth = 0

        # 깊이 제한 도달 시 하위 디렉토리 순회 중단
        if max_depth is not None and depth >= max_depth:
            sub_dirs[:] = []
        else:
            # os.walk가 참조하는 리스트를 제자리 수정해야 가지치기가 적용됨
            sub_dirs[:] = [
                name
                for name in sub_dirs
                if not _should_skip_dir(name, exclude_dirs, include_hidden)
            ]
            sub_dirs.sort()

        for file_name in sorted(file_names):
            if yielded >= max_files:
                return

            if not include_hidden and file_name.startswith("."):
                continue

            if Path(file_name).suffix.lower() not in extensions:
                continue

            file_path = current_path / file_name
            relative = file_path.relative_to(root).as_posix()

            # 제외 패턴이 우선
            if exclude_patterns and _matches_patterns(relative, exclude_patterns):
                continue

            # 포함 패턴이 지정되면 화이트리스트로 동작
            if include_patterns and not _matches_patterns(relative, include_patterns):
                continue

            yield file_path
            yielded += 1


def read_note_file(file_path: Path, max_size: int) -> str:
    """
    노트 파일을 읽어 텍스트로 반환 (인코딩 자동 감지)

    Args:
        file_path: 읽을 파일 경로
        max_size: 허용 최대 바이트 수

    Returns:
        디코딩된 파일 내용

    Raises:
        VaultScanError: 크기 초과 또는 읽기 실패 시
    """
    try:
        size = file_path.stat().st_size
    except OSError as exc:
        raise VaultScanError(f"파일 정보를 읽을 수 없습니다: {exc}") from exc

    if size > max_size:
        raise VaultScanError(
            f"파일이 너무 큽니다 ({size:,} bytes > {max_size:,} bytes)"
        )

    try:
        raw = file_path.read_bytes()
    except OSError as exc:
        raise VaultScanError(f"파일을 읽을 수 없습니다: {exc}") from exc

    # 후보 인코딩을 순서대로 시도
    for encoding in _ENCODING_CANDIDATES:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue

    # 모두 실패하면 손상 문자를 대체하여 최대한 복구
    return raw.decode("utf-8", errors="replace")


def scan_file(root: Path, file_path: Path, max_size: int) -> Dict[str, Any]:
    """
    단일 파일을 읽고 파싱하여 스캔 항목 딕셔너리로 변환

    Args:
        root: 스캔 루트 (상대 경로 계산용)
        file_path: 대상 파일 절대 경로
        max_size: 허용 최대 파일 크기(바이트)

    Returns:
        파싱 결과 + 파일 메타데이터를 합친 딕셔너리

    Raises:
        VaultScanError: 읽기 실패 시
    """
    text = read_note_file(file_path, max_size)
    parsed = parse_note_text(text, file_path)

    stat_result = file_path.stat()

    # 파일시스템 메타데이터 병합
    parsed.update(
        {
            "path": str(file_path),
            "relative_path": file_path.relative_to(root).as_posix(),
            "file_name": file_path.name,
            "extension": file_path.suffix.lower(),
            "size_bytes": stat_result.st_size,
            "modified_at": datetime.fromtimestamp(stat_result.st_mtime),
            "created_at": datetime.fromtimestamp(stat_result.st_ctime),
        }
    )

    return parsed


def scan_directory(
    raw_path: str,
    extensions: Optional[List[str]] = None,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    include_hidden: bool = False,
    max_depth: Optional[int] = None,
    max_files: int = 5000,
    include_content: bool = False,
) -> Dict[str, Any]:
    """
    디렉토리를 스캔하여 노트 목록과 통계를 반환

    Args:
        raw_path: 스캔할 디렉토리 경로
        extensions: 대상 확장자 목록 (None이면 기본값)
        include_patterns: 포함할 glob 패턴
        exclude_patterns: 제외할 glob 패턴
        include_hidden: 숨김 파일 포함 여부
        max_depth: 최대 탐색 깊이
        max_files: 최대 파일 수
        include_content: 응답에 본문 전체를 포함할지 여부

    Returns:
        {
            "root": 스캔 루트 경로,
            "notes": [노트 항목, ...],
            "errors": [{"path": ..., "error": ...}, ...],
            "stats": {...}
        }

    Raises:
        VaultScanError: 루트 경로 검증 실패 시
    """
    root = resolve_vault_root(raw_path)

    # 확장자 정규화 (점 없이 들어와도 허용, 소문자 통일)
    if extensions:
        normalized_ext = tuple(
            ext.lower() if ext.startswith(".") else f".{ext.lower()}"
            for ext in extensions
        )
    else:
        normalized_ext = DEFAULT_EXTENSIONS

    max_size = getattr(settings, "VAULT_MAX_FILE_SIZE", 2 * 1024 * 1024)

    notes: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    # 콘텐츠 해시별 경로를 모아 중복 노트를 식별
    hash_to_paths: Dict[str, List[str]] = {}

    total_bytes = 0
    tag_counts: Dict[str, int] = {}

    for file_path in iter_note_files(
        root,
        extensions=normalized_ext,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        include_hidden=include_hidden,
        max_depth=max_depth,
        max_files=max_files,
    ):
        try:
            item = scan_file(root, file_path, max_size)
        except VaultScanError as exc:
            # 개별 파일 실패가 전체 스캔을 중단시키지 않도록 수집만 함
            errors.append({"path": str(file_path), "error": str(exc)})
            continue
        except OSError as exc:
            errors.append({"path": str(file_path), "error": f"OS 오류: {exc}"})
            continue

        total_bytes += item["size_bytes"]

        for tag in item["tags"]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

        hash_to_paths.setdefault(item["content_hash"], []).append(
            item["relative_path"]
        )

        # 목록 조회 시 응답이 비대해지지 않도록 기본적으로 본문 제외
        if not include_content:
            item.pop("content", None)
            item.pop("plain_text", None)

        notes.append(item)

    # 동일 해시가 2개 이상인 그룹만 중복으로 보고
    duplicates = [paths for paths in hash_to_paths.values() if len(paths) > 1]

    # 태그를 빈도 내림차순으로 정렬
    top_tags = sorted(tag_counts.items(), key=lambda pair: (-pair[1], pair[0]))

    return {
        "root": str(root),
        "notes": notes,
        "errors": errors,
        "stats": {
            "total_files": len(notes),
            "total_bytes": total_bytes,
            "total_words": sum(note["word_count"] for note in notes),
            "error_count": len(errors),
            "duplicate_groups": len(duplicates),
            "unique_tags": len(tag_counts),
            "top_tags": [
                {"tag": tag, "count": count} for tag, count in top_tags[:20]
            ],
            "truncated": len(notes) >= max_files,
        },
        "duplicates": duplicates,
    }
