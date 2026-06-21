"""Tests for micro-quiz progress receipt pure module (sp1)."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from app.quiz_micro_receipt import (
    MICRO_QUIZ_RECEIPT_BASELINE_TTL_SEC,
    build_micro_quiz_receipt_html,
    build_micro_quiz_receipt_lines,
    capture_micro_quiz_receipt_baseline,
)


@pytest.fixture
def pass_correct():
    before = {"fc_due": 2, "sm2_due": 5, "weak_top": "algebra", "plan_teaser": "Повторить тему A"}
    after = {
        "fc_due": 1,
        "sm2_due": 4,
        "weak_top": "algebra",
        "plan_teaser": "Повторить тему A",
    }
    return before, after, "correct"


@pytest.fixture
def fail_incorrect():
    before = {"fc_due": 3, "sm2_due": 2, "weak_top": "limits", "plan_teaser": "Шаг 1"}
    after = {"fc_due": 3, "sm2_due": 2, "weak_top": "derivatives", "plan_teaser": "Шаг 2"}
    return before, after, "incorrect"


@pytest.fixture
def partial_status():
    before = {"fc_due": 1, "sm2_due": 1, "weak_top": None, "plan_teaser": ""}
    after = {"fc_due": 1, "sm2_due": 1, "weak_top": None, "plan_teaser": ""}
    return before, after, "partial"


@pytest.fixture
def no_overclaim():
    before = {
        "fc_due": 4,
        "sm2_due": 4,
        "weak_top": "topic_a",
        "plan_teaser": "Дальше",
        "daily_streak": 7,
        "weekly_done_reviews": 3,
        "mastery_pct": 42.5,
    }
    after = {
        "fc_due": 3,
        "sm2_due": 4,
        "weak_top": "topic_a",
        "plan_teaser": "Дальше",
        "daily_streak": 7,
        "weekly_done_reviews": 3,
        "mastery_pct": 55.0,
    }
    return before, after


@pytest.fixture
def due_delta():
    before = {"fc_due": 2, "sm2_due": 5, "weak_top": "x", "plan_teaser": "same"}
    after = {"fc_due": 2, "sm2_due": 4, "weak_top": "x", "plan_teaser": "same"}
    return before, after


@pytest.fixture
def calm_fallback():
    snap = {"fc_due": 2, "sm2_due": 3, "weak_top": "a", "plan_teaser": "plan"}
    return dict(snap), dict(snap)


def test_pass_correct_measurable_due_line(pass_correct):
    before, after, status = pass_correct
    lines, measurable = build_micro_quiz_receipt_lines(before, after, feedback_status=status)
    assert measurable is True
    assert any("было 5 → стало 4" in ln for ln in lines)
    assert any("было 2 → стало 1" in ln for ln in lines)
    html = build_micro_quiz_receipt_html(lines, measurable=measurable, feedback_status=status)
    assert "Верно" in html
    assert 'data-testid="e2e-micro-quiz-progress-receipt"' in html


def test_fail_incorrect_weak_and_plan_lines(fail_incorrect):
    before, after, status = fail_incorrect
    lines, measurable = build_micro_quiz_receipt_lines(before, after, feedback_status=status)
    assert measurable is True
    assert any("limits" in ln and "derivatives" in ln for ln in lines)
    assert any("Шаг 1" in ln and "Шаг 2" in ln for ln in lines)
    html = build_micro_quiz_receipt_html(lines, measurable=measurable, feedback_status=status)
    assert "Неверно" in html


def test_partial_status_in_html_wrapper(partial_status):
    before, after, status = partial_status
    lines, measurable = build_micro_quiz_receipt_lines(before, after, feedback_status=status)
    assert measurable is False
    html = build_micro_quiz_receipt_html(lines, measurable=measurable, feedback_status=status)
    assert "Частично" in html
    assert "micro-quiz-progress-receipt" in html


def test_no_overclaim_skips_streak_weekly_mastery(no_overclaim):
    before, after = no_overclaim
    lines, measurable = build_micro_quiz_receipt_lines(before, after)
    assert measurable is True
    assert any("было 4 → стало 3" in ln for ln in lines)
    joined = "\n".join(lines)
    assert "Стрик" not in joined
    assert "недел" not in joined.lower()
    assert "mastery" not in joined.lower()
    assert "%" not in joined


def test_due_delta_sm2_measurable(due_delta):
    before, after = due_delta
    lines, measurable = build_micro_quiz_receipt_lines(before, after)
    assert measurable is True
    assert any("было 5 → стало 4" in ln for ln in lines)
    assert len(lines) == 1


def test_calm_fallback_measurable_false(calm_fallback):
    before, after = calm_fallback
    lines, measurable = build_micro_quiz_receipt_lines(before, after)
    assert measurable is False
    assert lines == []
    html = build_micro_quiz_receipt_html(lines, measurable=measurable)
    assert "Локальные метрики без изменений" in html


def test_capture_baseline_includes_scope_and_ttl_constant():
    assert MICRO_QUIZ_RECEIPT_BASELINE_TTL_SEC == 600
    live = {
        "fc_due": 1,
        "sm2_due": 2,
        "weak_top": "w",
        "plan_teaser": "p",
        "topic": "t",
        "ts": time.time(),
    }
    with patch(
        "app.quiz_micro_receipt.build_micro_quiz_metric_dict_live",
        return_value=dict(live),
    ):
        baseline = capture_micro_quiz_receipt_baseline("tutor_mq_abc12345", topic="t")
    assert baseline["scope_key"] == "tutor_mq_abc12345"
    assert baseline["topic"] == "t"


def test_build_html_escapes_dynamic_copy():
    lines = ['Верх слабых концептов: было «<b>» → «&».»']
    html = build_micro_quiz_receipt_html(lines, measurable=True, feedback_status="correct")
    assert "&lt;b&gt;" in html
    assert "&amp;" in html


def test_build_micro_quiz_receipt_html_p95_under_50ms():
    lines, measurable = build_micro_quiz_receipt_lines(
        {"fc_due": 3, "sm2_due": 5, "weak_top": "a", "plan_teaser": "old"},
        {"fc_due": 1, "sm2_due": 4, "weak_top": "b", "plan_teaser": "new"},
        feedback_status="correct",
    )
    timings: list[float] = []
    for _ in range(200):
        t0 = time.perf_counter()
        build_micro_quiz_receipt_html(lines, measurable=measurable, feedback_status="correct")
        timings.append((time.perf_counter() - t0) * 1000.0)
    timings.sort()
    p95 = timings[189]
    assert p95 < 50.0, f"p95={p95:.2f}ms"
