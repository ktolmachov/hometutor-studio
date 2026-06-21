"""Tests for Graph-Tutor integration: build_tutor_prompt_for_concept."""
from __future__ import annotations

import pytest

from app.ui.dashboards_graph import build_tutor_prompt_for_concept, _TUTOR_MODES

_INFO = {"level": "intermediate", "description": "Classes and objects."}
_PREREQS = ["Basics", "Functions"]


def _prompt(mode: str = "explain", **kw) -> str:
    defaults = dict(
        info=_INFO,
        mastery_pct=35.0,
        prereqs=_PREREQS,
        related_docs_count=2,
        is_frontier=False,
        mode=mode,
    )
    defaults.update(kw)
    return build_tutor_prompt_for_concept("OOP", **defaults)


# ── mode coverage ──────────────────────────────────────────────────────

def test_all_modes_produce_output():
    for mode in _TUTOR_MODES:
        p = _prompt(mode=mode)
        assert isinstance(p, str) and len(p) > 40


def test_all_modes_contain_concept_name():
    for mode in _TUTOR_MODES:
        assert "OOP" in _prompt(mode=mode)


def test_explain_contains_mastery():
    p = _prompt("explain")
    assert "35%" in p or "35" in p


def test_explain_mentions_level():
    p = _prompt("explain")
    assert "intermediate" in p


def test_explain_mentions_prereqs():
    p = _prompt("explain")
    assert "Basics" in p or "Functions" in p


def test_practice_asks_for_tasks():
    p = _prompt("practice")
    assert "задани" in p.lower() or "упражнени" in p.lower() or "практическ" in p.lower()


def test_quiz_asks_questions():
    p = _prompt("quiz")
    assert "вопрос" in p.lower() or "проверь" in p.lower()


def test_compare_mode_mentions_prereq():
    p = _prompt("compare")
    # Should mention the last prereq for comparison
    assert "Functions" in p or "Basics" in p


def test_compare_without_prereqs_gives_fallback():
    p = _prompt("compare", prereqs=[])
    assert "OOP" in p
    assert isinstance(p, str)


def test_frontier_flag_adds_line():
    p_frontier = _prompt("explain", is_frontier=True)
    p_normal   = _prompt("explain", is_frontier=False)
    assert "готов" in p_frontier or "освоены" in p_frontier
    assert len(p_frontier) >= len(p_normal)


def test_zero_docs_no_crash():
    p = _prompt("explain", related_docs_count=0)
    assert "OOP" in p


def test_long_description_truncated_gracefully():
    long_desc = "x" * 1000
    p = _prompt("explain", info={"level": "beginner", "description": long_desc})
    assert len(p) < 3000  # description capped at 300 chars in prompt


def test_no_prereqs_says_starting_point():
    p = _prompt("explain", prereqs=[])
    assert "стартовый" in p.lower() or "без пресреквизитов" in p.lower()


# ── mode labels registry ───────────────────────────────────────────────

def test_all_mode_keys_have_labels():
    assert set(_TUTOR_MODES.keys()) == {"explain", "practice", "quiz", "compare"}
    for label in _TUTOR_MODES.values():
        assert len(label) > 0
