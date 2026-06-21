"""SQLite UI events (отдельно от app.metrics)."""

import json
import sqlite3

import pytest


def test_track_event_inserts_row(monkeypatch, tmp_path):
    import app.ui_events as ue

    monkeypatch.setattr(ue, "DATA_DIR", tmp_path)
    ue.track_event("test_event", {"k": "v"})
    db_path = tmp_path / "ui_events.db"
    assert db_path.exists()
    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT event_name, payload_json FROM ui_events ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    assert row[0] == "test_event"
    assert json.loads(row[1]) == {"k": "v"}


@pytest.mark.parametrize(
    "fn_name,args",
    [
        ("track_cta_click", ("Проверь меня",)),
        ("track_micro_quiz_started", ()),
        ("track_micro_quiz_completed", ("correct",)),
        ("track_resume_clicked", ()),
        ("track_due_review_started", ("topic_a",)),
        ("track_trust_panel_opened", ()),
    ],
)
def test_wrapper_events(monkeypatch, tmp_path, fn_name, args):
    import app.ui_events as ue

    monkeypatch.setattr(ue, "DATA_DIR", tmp_path)
    fn = getattr(ue, fn_name)
    fn(*args)
    conn = sqlite3.connect(str(tmp_path / "ui_events.db"))
    row = conn.execute("SELECT COUNT(*) FROM ui_events").fetchone()[0]
    conn.close()
    assert row >= 1
