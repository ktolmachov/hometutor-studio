"""Tests for app/konspekt_discovery.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.konspekt_discovery import (
    CoverageSummary,
    KonspektMeta,
    coverage_summary,
    find_konspekt_for_source,
    scan_konspekts,
)


FRONTMATTER_GOOD = """\
---
source: "Урок 2 Как агент думает и дейс.txt"
presentation: "Урок №2 — AI-агенты.pdf"
generated: 2026-06-10
type: konspekt
tags: [конспект, lecture, LLM]
---

# Конспект урока 2
"""

FRONTMATTER_NO_TYPE = """\
---
source: "some.txt"
generated: 2026-06-10
---

# Обычный документ
"""

FRONTMATTER_MALFORMED = """\
---
this is not: valid: yaml: at all
  broken indent
---
"""

FRONTMATTER_MISSING = "# Документ без frontmatter\n\nТекст."


class TestScanKonspekts:
    def test_finds_konspekt_by_type_field(self, tmp_path: Path) -> None:
        (tmp_path / "урок_2.md").write_text(FRONTMATTER_GOOD, encoding="utf-8")
        results = scan_konspekts(tmp_path)
        assert len(results) == 1
        assert results[0].source == "Урок 2 Как агент думает и дейс.txt"
        assert results[0].presentation == "Урок №2 — AI-агенты.pdf"
        assert results[0].generated == "2026-06-10"

    def test_skips_file_without_type_konspekt(self, tmp_path: Path) -> None:
        (tmp_path / "other.md").write_text(FRONTMATTER_NO_TYPE, encoding="utf-8")
        assert scan_konspekts(tmp_path) == []

    def test_skips_malformed_frontmatter_gracefully(self, tmp_path: Path) -> None:
        (tmp_path / "broken.md").write_text(FRONTMATTER_MALFORMED, encoding="utf-8")
        assert scan_konspekts(tmp_path) == []

    def test_skips_file_without_frontmatter(self, tmp_path: Path) -> None:
        (tmp_path / "plain.md").write_text(FRONTMATTER_MISSING, encoding="utf-8")
        assert scan_konspekts(tmp_path) == []

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        assert scan_konspekts(tmp_path) == []

    def test_nonexistent_directory_returns_empty(self, tmp_path: Path) -> None:
        assert scan_konspekts(tmp_path / "no_such_dir") == []

    def test_tags_parsed(self, tmp_path: Path) -> None:
        (tmp_path / "k.md").write_text(FRONTMATTER_GOOD, encoding="utf-8")
        km = scan_konspekts(tmp_path)[0]
        assert "конспект" in km.tags
        assert "LLM" in km.tags


class TestFindKonspektForSource:
    def test_exact_match(self, tmp_path: Path) -> None:
        (tmp_path / "k.md").write_text(FRONTMATTER_GOOD, encoding="utf-8")
        result = find_konspekt_for_source(
            "ИИ Агенты/Урок 2 Как агент думает и дейс.txt", tmp_path
        )
        assert result is not None
        assert result.source == "Урок 2 Как агент думает и дейс.txt"

    def test_match_is_case_insensitive(self, tmp_path: Path) -> None:
        (tmp_path / "k.md").write_text(FRONTMATTER_GOOD, encoding="utf-8")
        result = find_konspekt_for_source(
            "course/урок 2 как агент думает и дейс.txt", tmp_path
        )
        assert result is not None

    def test_no_match_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / "k.md").write_text(FRONTMATTER_GOOD, encoding="utf-8")
        result = find_konspekt_for_source("course/урок 3 совсем другой.txt", tmp_path)
        assert result is None

    def test_empty_source_rel_returns_none(self, tmp_path: Path) -> None:
        assert find_konspekt_for_source("", tmp_path) is None

    def test_wrong_course_dir_returns_none(self, tmp_path: Path) -> None:
        course_a = tmp_path / "course_a"
        course_b = tmp_path / "course_b"
        course_a.mkdir()
        course_b.mkdir()
        (course_a / "k.md").write_text(FRONTMATTER_GOOD, encoding="utf-8")
        result = find_konspekt_for_source(
            "course_a/Урок 2 Как агент думает и дейс.txt", course_b
        )
        assert result is None


class TestCoverageSummary:
    def _make_course(self, tmp_path: Path) -> Path:
        course = tmp_path / "МойКурс"
        course.mkdir()
        (course / "k.md").write_text(FRONTMATTER_GOOD, encoding="utf-8")
        return course

    def test_full_coverage(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        course = self._make_course(tmp_path)
        import app.konspekt_discovery as kd
        monkeypatch.setattr(kd, "DATA_DIR", tmp_path)
        paths = ["МойКурс/Урок 2 Как агент думает и дейс.txt"]
        cov = coverage_summary(paths)
        assert cov.covered == 1
        assert cov.total == 1
        assert cov.pct == 1.0

    def test_zero_coverage(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.konspekt_discovery as kd
        monkeypatch.setattr(kd, "DATA_DIR", tmp_path)
        (tmp_path / "МойКурс").mkdir()
        paths = ["МойКурс/неизвестный.txt"]
        cov = coverage_summary(paths)
        assert cov.covered == 0
        assert cov.pct == 0.0

    def test_partial_coverage(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        course = self._make_course(tmp_path)
        import app.konspekt_discovery as kd
        monkeypatch.setattr(kd, "DATA_DIR", tmp_path)
        paths = [
            "МойКурс/Урок 2 Как агент думает и дейс.txt",
            "МойКурс/урок 5 другой.txt",
        ]
        cov = coverage_summary(paths)
        assert cov.covered == 1
        assert cov.total == 2
        assert cov.pct == 0.5

    def test_empty_paths_returns_zero_pct(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.konspekt_discovery as kd
        monkeypatch.setattr(kd, "DATA_DIR", tmp_path)
        cov = coverage_summary([])
        assert cov.total == 0
        assert cov.pct == 0.0
