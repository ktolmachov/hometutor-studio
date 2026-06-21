"""Юнит-тесты каркаса Course Cockpit v2 (без Streamlit runtime для чистой логики)."""

from types import SimpleNamespace

import pytest

from app.course_metrics import course_daily_runway_summary
from app.ui.course_cockpit import (
    CONFIDENCE_DIP_SESSION_KEY,
    cockpit_feature_enabled,
    cockpit_scope_ready,
    current_pace_mode_label,
)


def test_cockpit_scope_ready_requires_active():
    assert cockpit_scope_ready(None) is False
    assert cockpit_scope_ready({}) is False
    assert cockpit_scope_ready({"active": False}) is False
    assert cockpit_scope_ready({"active": True, "folder_rel": "ml"}) is True


def test_cockpit_feature_enabled_reads_settings_flag():
    assert cockpit_feature_enabled(SimpleNamespace(rag_course_cockpit_v2=False)) is False
    assert cockpit_feature_enabled(SimpleNamespace(rag_course_cockpit_v2=True)) is True
    assert cockpit_feature_enabled(SimpleNamespace()) is False


def test_get_settings_has_rag_course_cockpit_v2_default_off():
    from app.config import get_settings

    s = get_settings()
    assert hasattr(s, "rag_course_cockpit_v2")
    assert isinstance(s.rag_course_cockpit_v2, bool)


def test_current_pace_mode_label_reads_plan_v2() -> None:
    scope = {"active": True, "learning_plan": {"plan": {"v2": {"pace_mode": "sprint"}}}}
    assert current_pace_mode_label(scope) == "Sprint"


def test_current_pace_mode_label_falls_back_to_default() -> None:
    assert current_pace_mode_label({"active": True}) == "Steady"


def test_course_daily_runway_inactive_scope(monkeypatch: pytest.MonkeyPatch):
    from app import course_metrics as cm

    def _inactive(_scope):
        return {"active": False}

    monkeypatch.setattr(cm, "collect_course_progress", _inactive)
    r = course_daily_runway_summary({"active": True, "id": "x"})
    assert r["active"] is False
    assert r["streak_days"] == 0


def test_course_daily_runway_due_and_streak(monkeypatch: pytest.MonkeyPatch):
    from app import course_metrics as cm

    def _prog(_scope):
        return {
            "active": True,
            "course_title": "C",
            "due_today": 12,
        }

    monkeypatch.setattr(cm, "collect_course_progress", _prog)
    monkeypatch.setattr("app.gamification_service.get_streak", lambda _uid=None: 4)
    r = course_daily_runway_summary({"active": True, "id": "c1"}, micro_cap=5)
    assert r["active"] is True
    assert r["due_today"] == 12
    assert r["recommended_micro_target"] == 5
    assert r["micro_target"] == 5
    assert r["streak_days"] == 4
    assert "5" in r["goal_line"] and "12" in r["goal_line"]


def test_course_daily_runway_zero_due(monkeypatch: pytest.MonkeyPatch):
    from app import course_metrics as cm

    def _prog(_scope):
        return {"active": True, "due_today": 0}

    monkeypatch.setattr(cm, "collect_course_progress", _prog)
    monkeypatch.setattr("app.gamification_service.get_streak", lambda _uid=None: 1)
    r = course_daily_runway_summary({"active": True, "id": "c1"})
    assert r["micro_target"] == 0
    assert "пуста" in (r.get("goal_line") or "")


def test_course_daily_runway_recovery_budget_override(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import course_metrics as cm

    def _prog(_scope):
        return {
            "active": True,
            "course_title": "C",
            "due_today": 12,
        }

    monkeypatch.setattr(cm, "collect_course_progress", _prog)
    monkeypatch.setattr("app.gamification_service.get_streak", lambda _uid=None: 0)
    low = cm.course_daily_runway_summary({"active": True, "id": "c_rb"}, recovery_catch_up_today=2)
    assert low["recommended_micro_target"] == 5
    assert low["micro_target"] == 2
    assert "(рекомендация системы" in low["goal_line"]
    assert "вне этого дневного блока" in (low.get("recovery_backlog_caption") or "")


def test_confidence_dip_session_key_stable():
    assert CONFIDENCE_DIP_SESSION_KEY == "course_confidence_dip_state_v1"


def test_format_next_session_promise_text_includes_runway_and_slot():
    from app.ui.course_cockpit import format_next_session_promise_text

    s = format_next_session_promise_text(
        title="Demo",
        runway_goal="Сегодня: **2** из 5",
        micro_target=2,
        due_today=5,
        active_slot="micro_quiz",
        pace_label="Steady",
    )
    assert "Demo" in s
    assert "Steady" in s
    assert "5" in s
    assert "micro_quiz" in s


def test_playbook_kv_key_scoped():
    from app.ui.course_cockpit import HOMEWORK_PLAYBOOK_KV_PREFIX, playbook_kv_key

    assert playbook_kv_key("ab12cd") == f"{HOMEWORK_PLAYBOOK_KV_PREFIX}_ab12cd"


def test_parse_playbook_steps_from_answer_json_fence():
    from app.ui.course_cockpit import parse_playbook_steps_from_answer

    txt = '```json\n[{"action":"Сделать X","self_check":"Вижу Y"}]\n```'
    steps = parse_playbook_steps_from_answer(txt)
    assert len(steps) == 1
    assert steps[0]["action"] == "Сделать X"
    assert steps[0]["self_check"] == "Вижу Y"


def test_parse_playbook_steps_from_answer_wrap_object():
    from app.ui.course_cockpit import parse_playbook_steps_from_answer

    raw = '{"steps": [{"action": "a", "self_check": "b"}]}'
    assert parse_playbook_steps_from_answer(raw) == [
        {"action": "a", "self_check": "b"},
    ]


def test_build_playbook_ask_question_contains_json_contract():
    from app.ui.course_cockpit import build_playbook_ask_question

    q = build_playbook_ask_question(
        course_title="Курс",
        statement="Задача 1",
        topic_label="Тема",
        brief_mode=True,
    )
    assert "```json" in q
    assert "кратко" in q.lower()
    assert "Задача 1" in q
    assert "Тема" in q
