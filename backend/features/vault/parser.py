"""
마크다운 노트 파서
- YAML 프론트매터 분리 및 파싱
- 제목/태그/위키링크/본문 추출
- 콘텐츠 해시 계산 (중복 및 변경 감지용)

외부 의존성 없이 동작하며, PyYAML이 설치되어 있으면 프론트매터를
정식 YAML로 파싱하고 없으면 내장 fallback 파서를 사용합니다.
"""

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# PyYAML은 선택 의존성 - 없으면 fallback 파서 사용
try:
    import yaml  # type: ignore

    _HAS_YAML = True
except ImportError:  # pragma: no cover - 실행 환경에 따라 달라짐
    yaml = None  # type: ignore
    _HAS_YAML = False


# ============ 정규식 상수 ============

# 프론트매터 구분자 (--- 또는 +++ 로 감싸인 최상단 블록)
_FRONTMATTER_RE = re.compile(
    r"\A﻿?(?:---|\+\+\+)[ \t]*\r?\n(.*?)\r?\n(?:---|\+\+\+)[ \t]*(?:\r?\n|\Z)",
    re.DOTALL,
)

# 펜스 코드블록 (``` 또는 ~~~) - 태그/링크 추출 시 제외 대상
_FENCED_CODE_RE = re.compile(r"(?:^|\n)(?:```|~~~).*?(?:\n(?:```|~~~)|\Z)", re.DOTALL)

# 인라인 코드
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")

# ATX 제목 (# ~ ######)
_ATX_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)

# Setext 제목 (제목 아래 === 줄)
_SETEXT_H1_RE = re.compile(r"^(?!\s*$)(.+)\r?\n=+[ \t]*$", re.MULTILINE)

# 해시태그 (#ai, #machine-learning, #연구/딥러닝)
# 앞이 줄 시작 또는 공백이어야 하므로 색상코드(#fff)나 제목(# 텍스트)과 구분됨
_HASHTAG_RE = re.compile(r"(?:(?<=\s)|(?<=^))#([A-Za-z가-힣][\w가-힣/\-]{0,49})")

# 위키링크 [[노트 제목]] 또는 [[노트|별칭]]
_WIKILINK_RE = re.compile(r"\[\[([^\[\]|]+?)(?:\|[^\[\]]*?)?\]\]")

# 마크다운 링크 [텍스트](주소)
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")

# 이미지 ![alt](주소)
_MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")

# 마크다운 장식 문자 (플레인 텍스트 변환용)
_MD_DECORATION_RE = re.compile(r"[*_~>`]|^\s*[-+*]\s+|^\s*\d+\.\s+", re.MULTILINE)

# 따옴표 문자 집합 (프론트매터 스칼라 정리용)
_QUOTE_CHARS = "\"'"


def _parse_frontmatter_fallback(raw: str) -> Dict[str, Any]:
    """
    PyYAML이 없을 때 사용하는 최소 프론트매터 파서

    지원 형식:
        title: 제목
        tags: [a, b, c]
        tags:
          - a
          - b
        draft: true

    Args:
        raw: 구분자 사이의 프론트매터 본문 문자열

    Returns:
        키-값 딕셔너리 (파싱 실패한 줄은 무시)
    """
    result: Dict[str, Any] = {}
    current_key: Optional[str] = None

    for line in raw.splitlines():
        stripped = line.strip()

        # 빈 줄 및 주석 건너뛰기
        if not stripped or stripped.startswith("#"):
            continue

        # 블록 리스트 항목 ("  - value")
        if stripped.startswith("- ") and current_key is not None:
            value = _coerce_scalar(stripped[2:].strip())
            existing = result.get(current_key)
            if isinstance(existing, list):
                existing.append(value)
            else:
                result[current_key] = [value]
            continue

        # "key: value" 형태가 아니면 건너뜀
        if ":" not in stripped:
            continue

        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()

        if not key:
            continue

        current_key = key

        if not value:
            # 다음 줄부터 블록 리스트가 이어질 수 있음
            result[key] = []
            continue

        # 인라인 리스트 [a, b, c]
        if value.startswith("[") and value.endswith("]"):
            items = [item.strip() for item in value[1:-1].split(",")]
            result[key] = [_coerce_scalar(item) for item in items if item]
        else:
            result[key] = _coerce_scalar(value)

    return result


def _coerce_scalar(value: str) -> Any:
    """
    문자열 스칼라를 적절한 파이썬 타입으로 변환

    Args:
        value: 원본 문자열

    Returns:
        bool / int / float / None / str 중 하나
    """
    # 감싸는 따옴표 제거
    if len(value) >= 2 and value[0] == value[-1] and value[0] in _QUOTE_CHARS:
        return value[1:-1]

    lowered = value.lower()

    if lowered in ("true", "yes"):
        return True
    if lowered in ("false", "no"):
        return False
    if lowered in ("null", "~", ""):
        return None

    # 숫자 변환 시도
    if re.fullmatch(r"[-+]?\d+", value):
        return int(value)
    if re.fullmatch(r"[-+]?\d*\.\d+", value):
        return float(value)

    return value


def split_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """
    본문에서 프론트매터를 분리

    Args:
        text: 파일 전체 텍스트

    Returns:
        (프론트매터 딕셔너리, 프론트매터를 제거한 본문)
        프론트매터가 없으면 ({}, 원본 텍스트)
    """
    match = _FRONTMATTER_RE.match(text)

    if not match:
        return {}, text

    raw = match.group(1)
    body = text[match.end():]

    # PyYAML 우선, 실패하면 fallback 파서로 재시도
    if _HAS_YAML:
        try:
            parsed = yaml.safe_load(raw)
            if isinstance(parsed, dict):
                return parsed, body
        except Exception:
            # 잘못된 YAML은 예외를 삼키고 fallback 처리
            pass

    return _parse_frontmatter_fallback(raw), body


def strip_code(text: str) -> str:
    """
    태그/링크 오탐을 막기 위해 코드블록과 인라인 코드를 제거

    Args:
        text: 마크다운 본문

    Returns:
        코드가 제거된 텍스트
    """
    without_fenced = _FENCED_CODE_RE.sub("\n", text)
    return _INLINE_CODE_RE.sub(" ", without_fenced)


def extract_title(
    frontmatter: Dict[str, Any],
    body: str,
    file_path: Path,
) -> str:
    """
    노트 제목 추출 (우선순위: 프론트매터 > 첫 H1 > 파일명)

    Args:
        frontmatter: 파싱된 프론트매터
        body: 프론트매터를 제외한 본문
        file_path: 원본 파일 경로

    Returns:
        제목 문자열 (Note.title 컬럼 길이에 맞춰 최대 255자)
    """
    # 1순위: 프론트매터의 title
    fm_title = frontmatter.get("title")
    if isinstance(fm_title, str) and fm_title.strip():
        return fm_title.strip()[:255]

    # 2순위: 본문의 첫 번째 H1 (코드블록 내부 제외)
    clean_body = _FENCED_CODE_RE.sub("\n", body)

    for match in _ATX_HEADING_RE.finditer(clean_body):
        if len(match.group(1)) == 1:
            heading = match.group(2).strip()
            if heading:
                return heading[:255]

    # 2-1순위: Setext 스타일 H1
    setext = _SETEXT_H1_RE.search(clean_body)
    if setext:
        heading = setext.group(1).strip()
        if heading:
            return heading[:255]

    # 3순위: 파일명 (확장자 제거, 구분자를 공백으로)
    stem = file_path.stem.replace("_", " ").replace("-", " ").strip()
    return (stem or file_path.name)[:255]


def extract_tags(frontmatter: Dict[str, Any], body: str) -> List[str]:
    """
    태그 추출 (프론트매터 tags/keywords + 본문 해시태그)

    Args:
        frontmatter: 파싱된 프론트매터
        body: 프론트매터를 제외한 본문

    Returns:
        중복이 제거된 소문자 태그 목록 (등장 순서 유지)
    """
    tags: List[str] = []

    # 프론트매터의 tags / keywords / tag 키를 모두 수집
    for key in ("tags", "keywords", "tag"):
        value = frontmatter.get(key)

        if isinstance(value, str):
            # "ai, ml" 또는 "ai ml" 형태 모두 지원
            parts = re.split(r"[,\s]+", value)
            tags.extend(part for part in parts if part)
        elif isinstance(value, (list, tuple)):
            tags.extend(str(item) for item in value if item is not None)

    # 본문 해시태그 (코드 영역 제외)
    tags.extend(_HASHTAG_RE.findall(strip_code(body)))

    # 정규화 + 중복 제거 (순서 유지)
    seen = set()
    normalized: List[str] = []

    for tag in tags:
        cleaned = str(tag).strip().lstrip("#").lower()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)

    return normalized


def _dedupe(items: List[str]) -> List[str]:
    """순서를 유지하며 중복 제거"""
    seen = set()
    result: List[str] = []

    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result


def extract_links(body: str) -> Dict[str, List[str]]:
    """
    노트 간 연결 정보 추출

    Args:
        body: 프론트매터를 제외한 본문

    Returns:
        {"wikilinks": [...], "urls": [...], "images": [...]}
    """
    clean = strip_code(body)

    # 위키링크 [[노트]]
    wikilinks = [link.strip() for link in _WIKILINK_RE.findall(clean) if link.strip()]

    # 이미지를 먼저 추출한 뒤 본문에서 제거해야 링크 목록에 섞이지 않음
    images = [url for _, url in _MD_IMAGE_RE.findall(clean)]
    without_images = _MD_IMAGE_RE.sub(" ", clean)
    urls = [url for _, url in _MD_LINK_RE.findall(without_images)]

    return {
        "wikilinks": _dedupe(wikilinks),
        "urls": _dedupe(urls),
        "images": _dedupe(images),
    }


def to_plain_text(body: str) -> str:
    """
    마크다운을 검색/요약용 플레인 텍스트로 변환

    Args:
        body: 마크다운 본문

    Returns:
        마크다운 문법이 제거된 텍스트
    """
    text = _FENCED_CODE_RE.sub(" ", body)
    text = _MD_IMAGE_RE.sub(" ", text)
    text = _MD_LINK_RE.sub(r"\1", text)       # [텍스트](주소) -> 텍스트
    text = _WIKILINK_RE.sub(r"\1", text)      # [[노트]] -> 노트
    text = _ATX_HEADING_RE.sub(r"\2", text)   # ## 제목 -> 제목
    text = _INLINE_CODE_RE.sub(" ", text)
    text = _MD_DECORATION_RE.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def make_excerpt(plain_text: str, length: int = 200) -> str:
    """
    본문 미리보기(발췌) 생성

    Args:
        plain_text: 플레인 텍스트 본문
        length: 최대 길이

    Returns:
        길이를 넘으면 말줄임표가 붙은 발췌문
    """
    collapsed = re.sub(r"\s+", " ", plain_text).strip()

    if len(collapsed) <= length:
        return collapsed

    # 단어 중간에서 잘리지 않도록 마지막 공백에서 절단
    cut = collapsed[:length]
    last_space = cut.rfind(" ")

    if last_space > length * 0.6:
        cut = cut[:last_space]

    return cut.rstrip() + "…"


def content_hash(text: str) -> str:
    """
    콘텐츠 해시 계산 (중복 파일 및 변경 감지용)

    Args:
        text: 해시 대상 텍스트

    Returns:
        SHA-256 16진수 문자열
    """
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def parse_note_text(text: str, file_path: Path) -> Dict[str, Any]:
    """
    노트 텍스트 전체를 파싱하여 구조화된 딕셔너리로 반환

    Args:
        text: 파일 전체 텍스트
        file_path: 원본 파일 경로 (제목 fallback에 사용)

    Returns:
        제목/본문/태그/링크/통계를 담은 파싱 결과
    """
    frontmatter, body = split_frontmatter(text)
    body = body.strip()

    plain = to_plain_text(body)
    links = extract_links(body)
    tags = extract_tags(frontmatter, body)

    # 카테고리: 프론트매터 category/type > 첫 번째 태그 > None
    category = frontmatter.get("category") or frontmatter.get("type")

    if isinstance(category, str) and category.strip():
        category = category.strip()[:50]
    else:
        category = tags[0][:50] if tags else None

    return {
        "title": extract_title(frontmatter, body, file_path),
        "content": body,
        "plain_text": plain,
        "excerpt": make_excerpt(plain),
        "frontmatter": frontmatter,
        "tags": tags,
        "category": category,
        "wikilinks": links["wikilinks"],
        "urls": links["urls"],
        "images": links["images"],
        "word_count": len(plain.split()),
        "char_count": len(plain),
        "content_hash": content_hash(body),
    }
