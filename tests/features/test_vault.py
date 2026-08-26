"""
Vault(로컬 노트 스캔/파싱) 단위 및 통합 테스트

- parser: 프론트매터, 제목 우선순위, 태그/링크 추출, 코드블록 오탐 방지
- scanner: 디렉토리 순회, 제외 규칙, 경로 검증, 인코딩
- routes: 스캔/미리보기/가져오기 API
"""

import pytest
from pathlib import Path

from features.vault import parser
from features.vault.scanner import (
    VaultScanError,
    resolve_vault_root,
    scan_directory,
)


# ============ Fixtures ============

@pytest.fixture
def vault_dir(tmp_path: Path) -> Path:
    """테스트용 노트 디렉토리를 구성합니다."""
    # 프론트매터가 있는 노트
    (tmp_path / "research.md").write_text(
        "---\n"
        "title: 트랜스포머 연구\n"
        "tags: [ai, nlp]\n"
        "category: research\n"
        "---\n\n"
        "# 무시되는 제목\n\n"
        "본문 #딥러닝 입니다. [[other]] 참고.\n\n"
        "```python\n"
        "# 코드 안의 #가짜태그\n"
        "```\n\n"
        "[링크](https://example.com)\n",
        encoding="utf-8",
    )

    # 프론트매터 없이 H1만 있는 노트
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "other.md").write_text(
        "# 두번째 노트\n\n내용 #ml\n", encoding="utf-8"
    )

    # 제목 없는 노트 (파일명 fallback 확인용)
    (tmp_path / "no-title-here.md").write_text("제목 없는 본문\n", encoding="utf-8")

    # 스캔에서 제외되어야 하는 것들
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config.md").write_text("제외 대상", encoding="utf-8")
    (tmp_path / "image.png").write_bytes(b"\x89PNG")

    return tmp_path


# ============ parser 단위 테스트 ============

class TestFrontmatter:
    """프론트매터 파싱"""

    def test_parses_frontmatter_and_strips_it_from_body(self):
        """프론트매터가 본문에서 분리되어야 합니다."""
        text = "---\ntitle: 제목\ntags: [a, b]\n---\n\n본문\n"
        front, body = parser.split_frontmatter(text)

        assert front["title"] == "제목"
        assert front["tags"] == ["a", "b"]
        assert "title:" not in body
        assert "본문" in body

    def test_returns_empty_when_no_frontmatter(self):
        """프론트매터가 없으면 원본을 그대로 돌려줘야 합니다."""
        front, body = parser.split_frontmatter("# 제목\n본문\n")

        assert front == {}
        assert body.startswith("# 제목")

    def test_block_list_frontmatter(self):
        """블록 형식 리스트도 파싱되어야 합니다."""
        text = "---\ntags:\n  - alpha\n  - beta\n---\n본문\n"
        front, _ = parser.split_frontmatter(text)

        assert front["tags"] == ["alpha", "beta"]

    def test_malformed_frontmatter_does_not_raise(self):
        """깨진 프론트매터가 예외를 던지면 안 됩니다."""
        text = "---\n{{{ 잘못된 내용\n---\n본문\n"
        front, body = parser.split_frontmatter(text)

        assert isinstance(front, dict)
        assert "본문" in body


class TestTitleExtraction:
    """제목 추출 우선순위: 프론트매터 > H1 > 파일명"""

    def test_frontmatter_title_wins(self):
        result = parser.parse_note_text(
            "---\ntitle: 우선순위1\n---\n\n# H1제목\n", Path("file.md")
        )
        assert result["title"] == "우선순위1"

    def test_falls_back_to_h1(self):
        result = parser.parse_note_text("# H1제목\n\n본문\n", Path("file.md"))
        assert result["title"] == "H1제목"

    def test_falls_back_to_filename(self):
        """구분자는 공백으로 바뀌어야 합니다."""
        result = parser.parse_note_text("본문만 있음\n", Path("my_note-name.md"))
        assert result["title"] == "my note name"

    def test_ignores_h1_inside_code_block(self):
        """코드블록 안의 #은 제목이 아닙니다."""
        text = "```\n# 코드 속 제목\n```\n\n# 진짜 제목\n"
        result = parser.parse_note_text(text, Path("f.md"))
        assert result["title"] == "진짜 제목"


class TestTagExtraction:
    """태그 추출"""

    def test_merges_frontmatter_and_hashtags(self):
        text = "---\ntags: [ai]\n---\n\n본문 #ml 입니다\n"
        result = parser.parse_note_text(text, Path("f.md"))

        assert "ai" in result["tags"]
        assert "ml" in result["tags"]

    def test_excludes_hashtags_in_code(self):
        """코드블록 안의 해시태그는 제외되어야 합니다."""
        text = "본문 #real\n\n```\n#fake\n```\n"
        result = parser.parse_note_text(text, Path("f.md"))

        assert "real" in result["tags"]
        assert "fake" not in result["tags"]

    def test_tags_are_lowercased_and_deduped(self):
        text = "---\ntags: [AI, ai, Ai]\n---\n본문\n"
        result = parser.parse_note_text(text, Path("f.md"))

        assert result["tags"] == ["ai"]


class TestLinkExtraction:
    """링크 추출"""

    def test_extracts_wikilinks_urls_and_images(self):
        text = (
            "[[노트A]] 와 [[노트B|별칭]]\n"
            "[링크](https://example.com)\n"
            "![그림](https://img.com/a.png)\n"
        )
        result = parser.parse_note_text(text, Path("f.md"))

        assert result["wikilinks"] == ["노트A", "노트B"]
        assert "https://example.com" in result["urls"]
        assert "https://img.com/a.png" in result["images"]
        # 이미지가 일반 링크 목록에 섞이면 안 됩니다
        assert "https://img.com/a.png" not in result["urls"]


class TestContentHash:
    """콘텐츠 해시 (중복 감지 기반)"""

    def test_same_content_same_hash(self):
        assert parser.content_hash("동일") == parser.content_hash("동일")

    def test_different_content_different_hash(self):
        assert parser.content_hash("A") != parser.content_hash("B")


# ============ scanner 단위 테스트 ============

class TestScanner:
    """디렉토리 스캔"""

    def test_scans_markdown_files_recursively(self, vault_dir: Path):
        result = scan_directory(str(vault_dir))

        names = {note["file_name"] for note in result["notes"]}
        assert names == {"research.md", "other.md", "no-title-here.md"}

    def test_excludes_vcs_dirs_and_non_note_files(self, vault_dir: Path):
        """.git 디렉토리와 비대상 확장자는 제외되어야 합니다."""
        result = scan_directory(str(vault_dir))

        paths = {note["relative_path"] for note in result["notes"]}
        assert not any(p.startswith(".git") for p in paths)
        assert not any(p.endswith(".png") for p in paths)

    def test_max_depth_limits_recursion(self, vault_dir: Path):
        """깊이 0이면 루트 파일만 수집해야 합니다."""
        result = scan_directory(str(vault_dir), max_depth=0)

        paths = {note["relative_path"] for note in result["notes"]}
        assert "sub/other.md" not in paths

    def test_exclude_patterns(self, vault_dir: Path):
        result = scan_directory(str(vault_dir), exclude_patterns=["sub/*"])

        paths = {note["relative_path"] for note in result["notes"]}
        assert "sub/other.md" not in paths
        assert "research.md" in paths

    def test_max_files_marks_truncated(self, vault_dir: Path):
        result = scan_directory(str(vault_dir), max_files=1)

        assert result["stats"]["total_files"] == 1
        assert result["stats"]["truncated"] is True

    def test_content_excluded_by_default(self, vault_dir: Path):
        """응답 비대화를 막기 위해 본문은 기본적으로 빠져야 합니다."""
        result = scan_directory(str(vault_dir))
        assert "content" not in result["notes"][0]

        with_content = scan_directory(str(vault_dir), include_content=True)
        assert "content" in with_content["notes"][0]

    def test_detects_duplicate_content(self, tmp_path: Path):
        """내용이 같은 파일은 중복 그룹으로 보고되어야 합니다."""
        (tmp_path / "a.md").write_text("같은 내용\n", encoding="utf-8")
        (tmp_path / "b.md").write_text("같은 내용\n", encoding="utf-8")

        result = scan_directory(str(tmp_path))
        assert result["stats"]["duplicate_groups"] == 1

    def test_reads_cp949_encoded_file(self, tmp_path: Path):
        """한글 Windows 환경의 CP949 파일도 읽어야 합니다."""
        (tmp_path / "cp949.md").write_bytes("# 한글 제목\n본문\n".encode("cp949"))

        result = scan_directory(str(tmp_path))
        assert result["notes"][0]["title"] == "한글 제목"

    def test_aggregates_tag_counts(self, vault_dir: Path):
        result = scan_directory(str(vault_dir))
        tags = {item["tag"] for item in result["stats"]["top_tags"]}

        assert "ai" in tags


class TestPathValidation:
    """경로 검증 (디렉토리 탈출 차단)"""

    def test_rejects_missing_path(self, tmp_path: Path):
        with pytest.raises(VaultScanError):
            resolve_vault_root(str(tmp_path / "없는경로"))

    def test_rejects_file_as_root(self, tmp_path: Path):
        target = tmp_path / "file.md"
        target.write_text("본문", encoding="utf-8")

        with pytest.raises(VaultScanError):
            resolve_vault_root(str(target))

    def test_rejects_empty_path(self):
        with pytest.raises(VaultScanError):
            resolve_vault_root("   ")

    def test_rejects_path_outside_allowed_roots(self, tmp_path: Path, monkeypatch):
        """허용 루트 밖의 경로는 거부되어야 합니다."""
        from core.config import settings

        allowed = tmp_path / "allowed"
        allowed.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()

        monkeypatch.setattr(settings, "VAULT_ALLOWED_ROOTS", [str(allowed)])

        # 허용 루트 안은 통과
        assert resolve_vault_root(str(allowed)) == allowed.resolve()

        # 밖은 차단
        with pytest.raises(VaultScanError):
            resolve_vault_root(str(outside))


# ============ 통합 테스트 (API) ============

class TestVaultAPI:
    """Vault API 엔드포인트"""

    def test_scan_requires_auth(self, client):
        response = client.post("/api/vault/scan", json={"path": "."})
        assert response.status_code in (401, 403)

    def test_scan_returns_notes(self, client, auth_headers, vault_dir: Path):
        response = client.post(
            "/api/vault/scan",
            json={"path": str(vault_dir)},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["stats"]["total_files"] == 3

    def test_scan_rejects_invalid_path(self, client, auth_headers):
        response = client.post(
            "/api/vault/scan",
            json={"path": "/존재하지/않는/경로"},
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_config_endpoint(self, client, auth_headers):
        response = client.get("/api/vault/config", headers=auth_headers)

        assert response.status_code == 200
        assert ".md" in response.json()["data"]["supported_extensions"]

    def test_import_dry_run_creates_nothing(self, client, auth_headers, vault_dir: Path, db):
        """dry_run은 실제로 저장하지 않아야 합니다."""
        from features.notes.models import Note

        before = db.query(Note).count()

        response = client.post(
            "/api/vault/import",
            json={"path": str(vault_dir), "dry_run": True},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["data"]["created"] == 3
        assert db.query(Note).count() == before

    def test_import_creates_notes_then_skips_duplicates(
        self, client, auth_headers, vault_dir: Path
    ):
        """두 번째 가져오기는 전부 중복으로 건너뛰어야 합니다."""
        first = client.post(
            "/api/vault/import",
            json={"path": str(vault_dir)},
            headers=auth_headers,
        )
        assert first.json()["data"]["created"] == 3

        second = client.post(
            "/api/vault/import",
            json={"path": str(vault_dir)},
            headers=auth_headers,
        )
        assert second.json()["data"]["created"] == 0
        assert second.json()["data"]["skipped"] == 3
