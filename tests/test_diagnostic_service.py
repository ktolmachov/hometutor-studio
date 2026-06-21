"""Регрессия после снятия standalone `app/diagnostic_service.py` (AR-2026-04-29-004).

Диагностика состояния обучения — через `user_state.get_learner_state_diagnostics` и admin API (`/learner-state/diagnostics`).
"""

from __future__ import annotations

from app import user_state
from app.config import reset_settings_cache


def test_get_learner_state_diagnostics_minimal_db(tmp_path, monkeypatch):
    db = tmp_path / "diag_orphan_regression.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()

    monkeypatch.setattr(
        user_state,
        "get_current_learner_state_lineage",
        lambda: {"generation_id": "g-test", "index_version": 1},
    )

    diag = user_state.get_learner_state_diagnostics(recent_limit=3)
    assert diag["current_lineage"]["generation_id"] == "g-test"
    assert diag["live_counts"]["quiz_results"] == 0
    assert diag["archive_counts"]["total"] == 0
    assert diag["has_archived_state"] is False
    assert isinstance(diag["recent_archive"], list)
