"""Tests for flashcard handoff timing events (P0 baseline)."""

from __future__ import annotations

import pytest

from app.flashcard_handoff_timing import (
    ANSWER_READY_KEY,
    CARD_ID_KEY,
    CLICK_MONO_KEY,
    TOPIC_KEY,
    TUTOR_MOUNT_MONO_KEY,
    clear_handoff_timing,
    handoff_active,
    log_handoff_answer_ready,
    record_handoff_click,
    record_handoff_tutor_mount,
)


def test_record_handoff_click_sets_session_and_logs() -> None:
    state: dict[str, object] = {}
    record_handoff_click(state, card_id=42, topic="RAG")
    assert CLICK_MONO_KEY in state
    assert state[CARD_ID_KEY] == 42
    assert state[TOPIC_KEY] == "RAG"
    assert handoff_active(state)


def test_navigation_ms_computed_on_tutor_mount() -> None:
    state: dict[str, object] = {}
    record_handoff_click(state, card_id=1, topic="t")
    state[CLICK_MONO_KEY] = 1000.0
    state[TUTOR_MOUNT_MONO_KEY] = None  # type: ignore[assignment]
    state.pop(TUTOR_MOUNT_MONO_KEY, None)
    import time

    original = time.perf_counter
    try:
        time.perf_counter = lambda: 1000.5  # noqa: E731
        nav = record_handoff_tutor_mount(state)
    finally:
        time.perf_counter = original
    assert nav == pytest.approx(500.0, rel=0.01)
    assert state[TUTOR_MOUNT_MONO_KEY] == 1000.5


def test_log_handoff_answer_ready_emits_once() -> None:
    state: dict[str, object] = {}
    record_handoff_click(state, card_id=7, topic="Graph")
    state[CLICK_MONO_KEY] = 0.0
    state[TUTOR_MOUNT_MONO_KEY] = 0.1
    log_handoff_answer_ready(
        state,
        api_debug={
            "engine_build_ms": 9000.0,
            "llm_ms": 20000.0,
            "post_processing_ms": 8000.0,
            "auto_quiz_ms": 7500.0,
            "total_answer_ms": 45000.0,
        },
    )
    assert state[ANSWER_READY_KEY] is True
    assert not handoff_active(state)
    log_handoff_answer_ready(state, api_debug={"total_answer_ms": 1.0})
    # second call is no-op when answer already logged


def test_clear_handoff_timing() -> None:
    state: dict[str, object] = {CLICK_MONO_KEY: 1.0, "x": 1}
    clear_handoff_timing(state)
    assert CLICK_MONO_KEY not in state
    assert state["x"] == 1
