"""Тесты daily briefing stub (E30 B2)."""

from unittest.mock import patch

from app.ui.daily_briefing import briefing_title, log_briefing_stub


def test_briefing_title_morning():
    assert "Утрен" in briefing_title("morning")


def test_briefing_title_evening():
    assert "Вечер" in briefing_title("evening")


def test_log_briefing_stub_calls_metrics():
    with patch("app.ui.daily_briefing.record_course_workflow_event") as m:
        log_briefing_stub({"active": True, "folder_rel": "x"}, period="evening")
        m.assert_called_once()
        _a, kwargs = m.call_args
        assert kwargs["payload"]["period"] == "evening"
