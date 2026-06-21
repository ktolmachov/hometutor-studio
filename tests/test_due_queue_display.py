"""Unit tests for shared due-queue display contract."""

from __future__ import annotations

from app.due_queue_display import (
    DUE_QUEUE_OVERFLOW_THRESHOLD,
    DUE_QUEUE_TOP_LIMIT,
    due_queue_overflow_caption,
    due_queue_preview_caption,
    is_soft_recovery_overflow,
)


def test_due_queue_constants():
    assert DUE_QUEUE_TOP_LIMIT == 7
    assert DUE_QUEUE_OVERFLOW_THRESHOLD == 50


def test_due_queue_overflow_caption_empty_when_no_deferred():
    assert due_queue_overflow_caption(7, 7) == ""
    assert due_queue_overflow_caption(5, 5) == ""


def test_due_queue_overflow_caption_shown_less_than_seven():
    assert due_queue_overflow_caption(10, 3) == "ещё 7 отложено"


def test_is_soft_recovery_overflow_threshold_strict():
    assert is_soft_recovery_overflow(50) is False
    assert is_soft_recovery_overflow(51) is True
    assert is_soft_recovery_overflow(120) is True


def test_due_queue_preview_caption_joins_concepts_and_overflow():
    rows = [{"concept": f"c{i}"} for i in range(1, 8)]
    text = due_queue_preview_caption(rows, 120)
    assert text.startswith("c1 · c2 · c3 · c4 · c5 · c6 · c7")
    assert "ещё 113 отложено" in text


def test_due_queue_preview_caption_no_overflow_when_all_shown():
    rows = [{"concept": f"c{i}"} for i in range(1, 6)]
    text = due_queue_preview_caption(rows, 5)
    assert " · " in text
    assert "отложено" not in text
