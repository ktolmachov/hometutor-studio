"""Tests for E30 D2 focus mode helpers."""

from unittest.mock import patch

from app.ui.focus_mode import (
    build_focus_session_payload,
    deep_work_badge,
    log_pomodoro_session,
)


def test_deep_work_badge_before_goal():
    assert deep_work_badge(2) == "Pomodoro cycle 2/4"


def test_deep_work_badge_after_goal():
    assert deep_work_badge(4) == "Deep work session - 100 min"


def test_build_focus_session_payload_sets_streak_shield_on_4_cycles():
    payload = build_focus_session_payload(cycles_completed=4, interrupted=False, break_started=True)
    assert payload["focus_minutes"] == 25
    assert payload["break_minutes"] == 5
    assert payload["deep_work_achieved"] is True
    assert payload["streak_shield"] is True
    assert payload["break_started"] is True


def test_build_focus_session_payload_resets_on_interruption():
    payload = build_focus_session_payload(cycles_completed=4, interrupted=True)
    assert payload["deep_work_achieved"] is False
    assert payload["streak_shield"] is False
    assert payload["interrupted"] is True


def test_log_pomodoro_session_calls_course_metrics():
    with patch("app.ui.focus_mode.record_course_workflow_event") as m:
        log_pomodoro_session({"active": True, "folder_rel": "x"}, cycles_completed=1, interrupted=False)
        m.assert_called_once()
        args, kwargs = m.call_args
        assert args[0] == "pomodoro_session"
        assert kwargs["payload"]["cycles_completed"] == 1
