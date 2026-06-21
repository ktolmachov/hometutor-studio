"""E24-B: HTTP + SQLite persistence для learner goal snapshot; см. E24-B-2-1 для подстановки в POST /ask."""

from __future__ import annotations

from fastapi.testclient import TestClient

import app.api as api
from app.config import reset_settings_cache
from app.user_state import reset_schema_cache_for_tests


def _client() -> TestClient:
    return TestClient(api.app)


def test_get_goal_snapshot_empty_db_no_crash(tmp_path, monkeypatch):
    db = tmp_path / "e24_empty.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()

    r = _client().get("/learner/goal-snapshot")
    assert r.status_code == 200
    data = r.json()
    assert data["goal_context"] is None
    assert data["schema_version"] is None
    assert data["updated_at"] is None


def test_http_put_get_survives_new_client_same_db(tmp_path, monkeypatch):
    """Имитация перезапуска процесса: новый TestClient, тот же файл БД."""
    db = tmp_path / "e24_persist.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()

    c1 = _client()
    put = c1.put(
        "/learner/goal-snapshot",
        json={
            "topic": "algebra",
            "subtopic": "linear",
            "time_budget_min": 15,
            "desired_outcome": "solve systems",
        },
    )
    assert put.status_code == 200
    assert put.json()["goal_context"]["topic"] == "algebra"
    assert put.json()["goal_context"]["time_budget_min"] == 15

    reset_settings_cache()
    reset_schema_cache_for_tests()
    c2 = _client()
    got = c2.get("/learner/goal-snapshot")
    assert got.status_code == 200
    gc = got.json()["goal_context"]
    assert gc["topic"] == "algebra"
    assert gc["subtopic"] == "linear"
    assert gc["desired_outcome"] == "solve systems"
    assert gc["time_budget_min"] == 15


def test_delete_goal_snapshot(tmp_path, monkeypatch):
    db = tmp_path / "e24_del.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()

    cl = _client()
    assert cl.put("/learner/goal-snapshot", json={"topic": "x"}).status_code == 200
    assert cl.delete("/learner/goal-snapshot").json() == {"status": "cleared"}
    empty = cl.get("/learner/goal-snapshot").json()
    assert empty["goal_context"] is None
