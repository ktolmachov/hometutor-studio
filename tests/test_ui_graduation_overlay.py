"""UI/логика celebration overlay (package ux-mastery-celebration-analytics)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app import gamification_service as gs
from app.ui import graduation_overlay as go
from app.ui.graduation_overlay import (
    build_graduation_celebration_view_model,
    graduation_headline,
    log_concept_graduation_stub,
    mastery_qualifies_for_celebration,
    render_skippable_graduation_celebration,
)


def test_graduation_headline_default():
    assert "концепт" in graduation_headline("")


def test_graduation_headline_custom():
    assert "RAG" in graduation_headline("RAG")


def test_log_concept_graduation_stub_invokes_metrics():
    with patch("app.ui.graduation_overlay.record_course_workflow_event") as m:
        log_concept_graduation_stub({"active": True, "folder_rel": "ml"}, concept_title="X")
        m.assert_called_once()
        args, kwargs = m.call_args
        assert args[0] == "concept_graduation_event"
        assert kwargs["payload"]["stub"] is True


def test_mastery_qualifies_threshold():
    assert mastery_qualifies_for_celebration(80.0) is True
    assert mastery_qualifies_for_celebration(79.9) is False
    assert mastery_qualifies_for_celebration(None) is False


def test_build_view_model_includes_topic_mastery_ctas():
    vm = build_graduation_celebration_view_model(
        concept_title="RAG",
        mastery_pct=88.0,
        session_count=2,
        minutes_spent=30.0,
    )
    assert "RAG" in vm["headline"]
    assert any("88" in x for x in vm["detail_lines"])
    assert vm["primary_cta_labels"] == [
        "Следующая тема",
        "Разобрать слабые места",
        "На главную",
    ]
    assert vm["degraded_simple"] is False


def test_build_view_model_degrades_when_metrics_missing():
    vm = build_graduation_celebration_view_model(concept_title="", mastery_pct=90.0)
    assert vm["degraded_simple"] is True
    assert any("краткое" in line.lower() or "поздрав" in line.lower() for line in vm["detail_lines"])


@pytest.fixture
def isolated_gamification_kv(monkeypatch):
    store: dict[str, str] = {}

    def _get(k: str) -> str | None:
        return store.get(k)

    def _set(k: str, v: str) -> None:
        store[k] = v

    monkeypatch.setattr(gs, "get_kv", _get)
    monkeypatch.setattr(gs, "set_kv", _set)
    yield store
    store.clear()


def test_record_concept_graduation_badge_idempotent(isolated_gamification_kv):
    r1 = gs.record_concept_graduation_badge()
    assert len(r1["new_badges"]) == 1
    assert gs.CONCEPT_GRADUATION_BADGE_ID in r1["badges_all"]
    raw = isolated_gamification_kv[gs._KV_KEY]  # noqa: SLF001
    data = json.loads(raw)
    assert gs.CONCEPT_GRADUATION_BADGE_ID in data["badges"]

    r2 = gs.record_concept_graduation_badge()
    assert r2["new_badges"] == []
    assert gs.CONCEPT_GRADUATION_BADGE_ID in r2["badges_all"]


def test_render_skippable_graduation_early_exit_below_threshold():
    mock_st = MagicMock()
    mock_st.session_state = {}
    with patch.object(go, "st", mock_st):
        render_skippable_graduation_celebration(mastery_pct=40.0)
    mock_st.success.assert_not_called()


def test_render_skippable_graduation_renders_when_qualified():
    mock_st = MagicMock()
    mock_st.session_state = {}
    col = MagicMock()
    mock_st.columns.return_value = (col, col, col)

    with patch.object(go, "st", mock_st):
        with patch.object(go, "record_concept_graduation_badge", return_value={"new_badges": []}):
            render_skippable_graduation_celebration(
                concept_title="T",
                mastery_pct=90.0,
                session_count=1,
                minutes_spent=5.0,
            )
    mock_st.success.assert_called_once()
    mock_st.button.assert_called()
    mock_st.columns.assert_called_once_with(3)
