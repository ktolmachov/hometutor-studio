"""US-10.2 sync-service contract tests."""

from pathlib import Path

import pytest

from app.config import reset_settings_cache
from app.quiz_adaptive import update_mastery_after_score
from app.sync_service import export_bundle_to_dict, import_bundle_from_dict
from app.user_state import _with_db, reset_schema_cache_for_tests


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "sync_service.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


def test_import_bundle_from_dict_rejects_unsupported_version(isolated_user_db) -> None:
    with pytest.raises(ValueError, match="unsupported sync_version"):
        import_bundle_from_dict({"sync_version": 999, "tables": {}})


def test_import_bundle_from_dict_restore_returns_insert_summary(
    isolated_user_db, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("app.quiz_stats._STATS_FILE", tmp_path / "quiz_ui_stats.json")
    update_mastery_after_score("sync-topic", 1.0)
    bundle = export_bundle_to_dict()

    def _clear(conn):
        conn.execute("DELETE FROM quiz_mastery")
        conn.commit()

    _with_db(_clear)
    result = import_bundle_from_dict(bundle)

    assert result["sync_version"] == 1
    assert int(result["rows_inserted"]) >= 1
