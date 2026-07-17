"""Regression guard for the archived SSR weekly planner surface."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def test_ssr_weekly_planner_runtime_module_stays_archived() -> None:
    """C2 removed this ghost surface from ``app/``; keep it out of imports."""
    assert importlib.util.find_spec("app.ssr_weekly_planner") is None


def test_ssr_weekly_planner_archive_source_is_kept_for_audit() -> None:
    archive = (
        Path(__file__).resolve().parents[1].parent
        / "hometutor"
        / "doc"
        / "archive"
        / "code"
        / "ssr_weekly_planner.py"
    )
    assert archive.is_file()
    text = archive.read_text(encoding="utf-8")
    assert "ARCHIVED" in text
    assert "generate_weekly_study_plan" in text
