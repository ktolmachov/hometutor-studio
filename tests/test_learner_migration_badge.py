"""US-8.2: строки migration badge без полного Streamlit runtime."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def patch_st(monkeypatch):
    monkeypatch.setattr(
        "app.ui.tutor_mastery_forecast_panel.st.session_state",
        MagicMock(get=MagicMock(return_value="local")),
    )
    calls: list[tuple[str, str | None]] = []

    def _info(msg: str, icon: str | None = None) -> None:
        calls.append((msg, icon))

    monkeypatch.setattr("app.ui.tutor_mastery_forecast_panel.st.info", _info)
    # US-8.2 rehydrate: единая отрисовка в learner_profile_panel
    monkeypatch.setattr("app.ui.learner_profile_panel.st.info", _info)
    return calls


def test_migration_badge_history_rehydrated(patch_st, monkeypatch):
    from app.ui.tutor_mastery_forecast_panel import render_learner_profile_migration_badge

    profile = SimpleNamespace(
        state_migration={
            "history_rehydrated": True,
            "history_rehydrated_source_generation_id": "gen-old",
        },
        index_context={"activated_at": "2026-04-10T12:00:00+00:00"},
    )
    monkeypatch.setattr(
        "app.ui.tutor_mastery_forecast_panel.get_personalized_learner_profile",
        lambda uid, session_id=None: profile,
    )

    render_learner_profile_migration_badge()
    assert patch_st
    msg, icon = patch_st[0]
    assert "Профиль обновлён после переиндексации" in msg
    assert "10.04.2026" in msg
    assert icon == "🔄"


def test_migration_badge_index_changed_generations(patch_st, monkeypatch):
    from app.ui.tutor_mastery_forecast_panel import render_learner_profile_migration_badge

    profile = SimpleNamespace(
        state_migration={
            "index_changed": True,
            "source_generation_id": "g1",
            "current_generation_id": "g2",
        }
    )
    monkeypatch.setattr(
        "app.ui.tutor_mastery_forecast_panel.get_personalized_learner_profile",
        lambda uid, session_id=None: profile,
    )

    render_learner_profile_migration_badge()
    assert patch_st
    msg = patch_st[0][0]
    assert "g1" in msg and "g2" in msg
