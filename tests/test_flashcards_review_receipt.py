"""Tests for flashcard review progress receipt pure module (sp1)."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from app.flashcards_review_receipt import (
    FC_REVIEW_RECEIPT_BASELINE_TTL_SEC,
    build_fc_review_receipt_html,
    build_fc_review_receipt_lines,
    capture_fc_review_receipt_baseline,
)


@pytest.fixture
def empty_queue():
    """No baseline payload — receipt builder returns empty (UI gate in sp2)."""
    return {}, {}


@pytest.fixture
def single_card():
    before = {
        "fc_due": 1,
        "daily_streak": 2,
        "weekly_done_reviews": 3,
        "weekly_target_reviews": 10,
        "week_id": "2026-W22",
    }
    after = {
        "fc_due": 0,
        "daily_streak": 2,
        "weekly_done_reviews": 4,
        "weekly_target_reviews": 10,
        "week_id": "2026-W22",
    }
    return before, after


@pytest.fixture
def multi_card():
    before = {
        "fc_due": 3,
        "daily_streak": 1,
        "weekly_done_reviews": 0,
        "weekly_target_reviews": 5,
        "week_id": "2026-W22",
    }
    after = {
        "fc_due": 0,
        "daily_streak": 1,
        "weekly_done_reviews": 3,
        "weekly_target_reviews": 5,
        "week_id": "2026-W22",
    }
    return before, after


@pytest.fixture
def no_overclaim():
    before = {
        "fc_due": 2,
        "daily_streak": 5,
        "weekly_done_reviews": 2,
        "weekly_target_reviews": 8,
        "week_id": "2026-W22",
    }
    after = {
        "fc_due": 1,
        "daily_streak": 5,
        "weekly_done_reviews": 2,
        "weekly_target_reviews": 8,
        "week_id": "2026-W22",
    }
    return before, after


@pytest.fixture
def due_unchanged():
    snap = {
        "fc_due": 4,
        "daily_streak": 3,
        "weekly_done_reviews": 1,
        "weekly_target_reviews": 7,
        "week_id": "2026-W22",
    }
    return dict(snap), dict(snap)


@pytest.fixture
def week_id_rollover():
    before = {
        "fc_due": 2,
        "daily_streak": 1,
        "weekly_done_reviews": 9,
        "weekly_target_reviews": 10,
        "week_id": "2026-W21",
    }
    after = {
        "fc_due": 0,
        "daily_streak": 1,
        "weekly_done_reviews": 1,
        "weekly_target_reviews": 10,
        "week_id": "2026-W22",
    }
    return before, after


def test_empty_queue_no_receipt_gate(empty_queue):
    before, after = empty_queue
    lines, measurable = build_fc_review_receipt_lines(before, after)
    assert lines == []
    assert measurable is False


def test_single_card_delta_and_next_review_hint(single_card):
    before, after = single_card
    nr = "2026-06-01T12:00:00+00:00"
    lines, measurable = build_fc_review_receipt_lines(before, after, next_review_min=nr)
    assert measurable is True
    assert any("было 1 → стало 0" in ln for ln in lines)
    assert any("Повторения за неделю: 4/10" in ln for ln in lines)
    assert any("Ближайшее повторение" in ln for ln in lines)


def test_multi_card_delta_at_least_three(multi_card):
    before, after = multi_card
    lines, measurable = build_fc_review_receipt_lines(before, after)
    assert measurable is True
    assert any("было 3 → стало 0" in ln for ln in lines)
    assert any("Повторения за неделю: 3/5" in ln for ln in lines)


def test_no_overclaim_skips_unchanged_streak_and_weekly(no_overclaim):
    before, after = no_overclaim
    lines, measurable = build_fc_review_receipt_lines(before, after)
    assert measurable is True
    assert any("было 2 → стало 1" in ln for ln in lines)
    assert not any("Стрик:" in ln for ln in lines)
    assert not any("Повторения за неделю" in ln for ln in lines)


def test_due_unchanged_calm_fallback(due_unchanged):
    before, after = due_unchanged
    lines, measurable = build_fc_review_receipt_lines(before, after)
    assert measurable is False
    assert lines == ["Очередь due без изменений."]


def test_week_id_rollover_suppresses_weekly_delta(week_id_rollover):
    before, after = week_id_rollover
    lines, measurable = build_fc_review_receipt_lines(before, after)
    assert measurable is True
    assert any("было 2 → стало 0" in ln for ln in lines)
    assert not any("Повторения за неделю" in ln for ln in lines)


def test_streak_line_only_on_truthful_diff():
    before = {"fc_due": 1, "daily_streak": 2, "week_id": "2026-W22", "weekly_done_reviews": 0}
    after = {"fc_due": 0, "daily_streak": 3, "week_id": "2026-W22", "weekly_done_reviews": 0}
    lines, measurable = build_fc_review_receipt_lines(before, after)
    assert measurable is True
    assert any("Стрик: 2 → 3 дн." in ln for ln in lines)


def test_capture_baseline_includes_scope_and_ttl_constant():
    assert FC_REVIEW_RECEIPT_BASELINE_TTL_SEC == 600
    live = {
        "fc_due": 5,
        "daily_streak": 1,
        "weekly_done_reviews": 2,
        "weekly_target_reviews": 10,
        "week_id": "2026-W22",
        "scope_signature": "deck:1",
        "ts": time.time(),
    }
    with patch(
        "app.flashcards_review_receipt.build_fc_review_metric_dict_live",
        return_value=dict(live),
    ):
        baseline = capture_fc_review_receipt_baseline("deck:1")
    assert baseline["scope_signature"] == "deck:1"
    assert baseline["fc_due"] == 5


def test_build_html_has_testid_and_escapes():
    lines = ['Карточки к повторению: было 1 → стало 0.', 'Стрик: 1 → 2 дн.']
    html = build_fc_review_receipt_html(lines, measurable=True, next_review_min=None)
    assert 'data-testid="e2e-fc-review-progress-receipt"' in html
    assert "fc-review-progress-receipt" in html
    assert "📊 Прогресс после повторения" in html


def test_build_fc_review_receipt_html_p95_under_50ms():
    lines, measurable = build_fc_review_receipt_lines(
        {"fc_due": 3, "daily_streak": 1, "weekly_done_reviews": 0, "week_id": "2026-W22"},
        {"fc_due": 0, "daily_streak": 2, "weekly_done_reviews": 3, "week_id": "2026-W22", "weekly_target_reviews": 5},
        next_review_min="2026-06-01T12:00:00+00:00",
    )
    timings: list[float] = []
    for _ in range(200):
        t0 = time.perf_counter()
        build_fc_review_receipt_html(lines, measurable=measurable, next_review_min="2026-06-01T12:00:00+00:00")
        timings.append((time.perf_counter() - t0) * 1000.0)
    timings.sort()
    p95 = timings[189]
    assert p95 < 50.0, f"p95={p95:.2f}ms"
