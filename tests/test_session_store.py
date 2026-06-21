"""SessionStore: SQLite + LRU, UPSERT сохраняет created_at."""

import json
import logging
import sqlite3

import pytest

from app.models import Message
from app.session_store import SessionStore


@pytest.fixture
def store(tmp_path):
    return SessionStore(db_path=tmp_path / "sessions.db", cache_maxsize=3)


def test_get_empty_unknown_session(store):
    assert store.get("") == []
    assert store.get("missing") == []


def test_save_roundtrip(store):
    msgs = [
        Message(role="user", content="hi"),
        Message(role="assistant", content="hello"),
    ]
    store.save("s1", msgs)
    loaded = store.get("s1")
    assert len(loaded) == 2
    assert loaded[0].role == "user" and loaded[0].content == "hi"
    assert loaded[1].role == "assistant"


def test_upsert_preserves_created_at(store):
    store.save("s2", [Message(role="user", content="a")])
    with sqlite3.connect(str(store.db_path)) as conn:
        row = conn.execute(
            "SELECT created_at, last_updated FROM sessions WHERE session_id=?",
            ("s2",),
        ).fetchone()
        created_first, updated_first = row

    store.save("s2", [Message(role="user", content="b")])
    with sqlite3.connect(str(store.db_path)) as conn:
        row = conn.execute(
            "SELECT created_at, last_updated FROM sessions WHERE session_id=?",
            ("s2",),
        ).fetchone()
        created_second, updated_second = row

    assert created_first == created_second
    assert updated_second >= updated_first


def test_delete_removes_db_and_cache(store):
    store.save("s3", [Message(role="user", content="x")])
    assert len(store.get("s3")) == 1
    store.delete("s3")
    assert store.get("s3") == []


def test_list_sessions_includes_created_at(store):
    store.save("a", [Message(role="user", content="1")])
    store.save("b", [Message(role="user", content="2")])
    rows = store.list_sessions(limit=10)
    ids = {r["session_id"] for r in rows}
    assert ids >= {"a", "b"}
    assert all("created_at" in r and "last_updated" in r for r in rows)
    assert all("last_user_preview" in r for r in rows)
    by_id = {r["session_id"]: r for r in rows}
    assert by_id["a"]["last_user_preview"] == "1"
    assert by_id["b"]["last_user_preview"] == "2"


def test_corrupt_json_returns_empty(store, caplog):
    store.save("bad", [Message(role="user", content="ok")])
    with sqlite3.connect(str(store.db_path)) as conn:
        conn.execute(
            "UPDATE sessions SET messages = ? WHERE session_id = ?",
            ("not-json", "bad"),
        )
    store._memory_cache.pop("bad", None)  # принудительно читаем из БД
    app_logger = logging.getLogger("app")
    app_logger.addHandler(caplog.handler)
    caplog.set_level("WARNING")
    try:
        assert store.get("bad") == []
        assert "Corrupt session JSON" in caplog.text
    finally:
        app_logger.removeHandler(caplog.handler)


def test_lru_eviction(store):
    for i in range(4):
        store.save(f"sid{i}", [Message(role="user", content=str(i))])
    # cache_maxsize=3 — одна сессия вытеснена из RAM
    assert len(store._memory_cache) <= 3
    # данные всё ещё в SQLite
    assert store.get("sid0")[0].content == "0"


def test_bounded_history_trims_messages(monkeypatch, tmp_path):
    import importlib

    ss_mod = importlib.import_module("app.session_store")

    class _S:
        session_history_max_messages = 4

    monkeypatch.setattr(ss_mod, "get_settings", lambda: _S())
    s = SessionStore(db_path=tmp_path / "bounded.db")
    msgs = [Message(role="user", content=str(i)) for i in range(10)]
    stats = s.save("b1", msgs)
    assert stats["session_history_trimmed"] is True
    assert stats["session_history_stored"] == 4
    loaded = s.get("b1")
    assert len(loaded) == 4
    assert loaded[0].content == "6"


def test_get_record_and_patch_metadata(tmp_path):
    s = SessionStore(db_path=tmp_path / "meta.db")
    s.save("m1", [Message(role="user", content="hi")])
    rec = s.get_record("m1")
    assert rec is not None
    assert rec["session_id"] == "m1"
    assert len(rec["messages"]) == 1
    assert "turn_count" in rec["metadata"]
    assert rec["metadata"].get("last_user_preview") == "hi"
    merged = s.patch_metadata("m1", {"title": "T1"})
    assert merged.get("title") == "T1"
    assert s.get_record("m1")["metadata"].get("title") == "T1"
