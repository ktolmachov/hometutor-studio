"""Тесты UX ожидания первого ответа (MoT #2), без Streamlit runtime."""

from __future__ import annotations

import pytest

from app.ui.qa_wait_ux import (
    FAST_ANSWER_MS_THRESHOLD,
    WAIT_STAGE_LABELS_RU,
    answer_column_skeleton_placeholder_html,
    answer_qualifies_for_fast_success_reinforcement,
    fast_success_reinforcement_phrase,
    progressive_reveal_markup,
    wait_runway_message_for_question,
    wait_stage_message_for_question,
)


def test_wait_stage_labels_non_empty_stable() -> None:
    assert len(WAIT_STAGE_LABELS_RU) >= 3
    for label in WAIT_STAGE_LABELS_RU:
        assert label.strip()


@pytest.mark.parametrize("q", ["Как связаны X и Y?", "  trim me  ", ""])
def test_wait_runway_and_stage_are_deterministic(q: str) -> None:
    r1 = wait_runway_message_for_question(q)
    r2 = wait_runway_message_for_question(q)
    s1 = wait_stage_message_for_question(q)
    s2 = wait_stage_message_for_question(q)
    assert r1 == r2
    assert s1 == s2


def test_wait_stage_message_in_allowed_set() -> None:
    msg = wait_stage_message_for_question("deterministic-stage-pick")
    assert msg in WAIT_STAGE_LABELS_RU


def test_wait_runway_rotates_over_questions() -> None:
    seen_runway = {wait_runway_message_for_question(f"q{n}") for n in range(48)}
    assert len(seen_runway) > 1


def test_answer_column_skeleton_has_stable_markers() -> None:
    html = answer_column_skeleton_placeholder_html()
    assert 'class="qa-answer-skeleton"' in html
    assert 'data-qa-wait-skeleton="1"' in html
    assert "min-height:12rem" in html


def test_progressive_reveal_instant_fallback_no_wrapper_marker() -> None:
    body = "## Заголовок\nТекст."
    assert progressive_reveal_markup(body, prefer_instant=True) == body


def test_progressive_reveal_non_instant_adds_marker() -> None:
    body = "Ответ"
    out = progressive_reveal_markup(body, prefer_instant=False)
    assert "<!-- qa-progressive-reveal -->" in out
    assert out.endswith(body)


def test_fast_success_reinforcement_phrase_deterministic() -> None:
    q = "same"
    assert fast_success_reinforcement_phrase(q) == fast_success_reinforcement_phrase(q)


def test_answer_qualifies_for_fast_success_timing_and_trust() -> None:
    assert not answer_qualifies_for_fast_success_reinforcement(
        total_answer_ms=None,
        confidence={"level": "high"},
        sources=[{"x": 1}],
    )
    assert not answer_qualifies_for_fast_success_reinforcement(
        total_answer_ms=FAST_ANSWER_MS_THRESHOLD,
        confidence={"level": "high"},
        sources=[{"x": 1}],
    )
    assert not answer_qualifies_for_fast_success_reinforcement(
        total_answer_ms=100.0,
        confidence={"level": "low"},
        sources=[{"x": 1}],
    )
    assert not answer_qualifies_for_fast_success_reinforcement(
        total_answer_ms=100.0,
        confidence={"level": "high"},
        sources=[],
    )
    assert answer_qualifies_for_fast_success_reinforcement(
        total_answer_ms=100.0,
        confidence={"level": "high"},
        sources=[{"x": 1}],
    )
