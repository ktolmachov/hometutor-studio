"""Экспорт/импорт локального снимка user_state."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import reset_settings_cache
from app.quiz_adaptive import update_mastery_after_score
from app.user_state import _with_db, export_full_sync_bundle, import_full_sync_bundle, reset_schema_cache_for_tests


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "sync.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


def test_export_import_roundtrip(isolated_user_db, monkeypatch, tmp_path: Path):
    monkeypatch.setattr("app.quiz_stats._STATS_FILE", tmp_path / "quiz_ui_stats.json")
    update_mastery_after_score("X", 1.0)

    def _count(conn):
        return conn.execute("SELECT COUNT(*) AS n FROM quiz_mastery").fetchone()["n"]

    assert _with_db(_count) >= 1

    bundle = export_full_sync_bundle()
    assert bundle["sync_version"] == 1
    assert "tables" in bundle and "quiz_mastery" in bundle["tables"]

    def _clear(conn):
        conn.execute("DELETE FROM quiz_mastery")
        conn.commit()

    _with_db(_clear)
    assert _with_db(_count) == 0

    import_full_sync_bundle(bundle)
    assert _with_db(_count) >= 1


def test_sync_json_serializable(isolated_user_db, monkeypatch, tmp_path: Path):
    monkeypatch.setattr("app.quiz_stats._STATS_FILE", tmp_path / "quiz_ui_stats.json")
    update_mastery_after_score("Z", 0.0)
    bundle = export_full_sync_bundle()
    assert "learner_state_diagnostics" in bundle
    s = json.dumps(bundle, ensure_ascii=False)
    back = json.loads(s)
    import_full_sync_bundle(back)
