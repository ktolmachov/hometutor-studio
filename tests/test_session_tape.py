"""Unit tests for session tape writer/reader and debug replay API."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.api as api
import app.session_tape as session_tape
from app.config import reset_settings_cache
from app.session_replay import iter_events
from app.session_tape import (
    append_event,
    ensure_session_started,
    end_session,
    offline_payload_tag,
    reset_session_started_cache_for_tests,
    sanitize_session_id,
)


@pytest.fixture(autouse=True)
def _reset_tape_state() -> None:
    reset_session_started_cache_for_tests()


def _sessions_dir(tmp_path: Path) -> Path:
    return tmp_path / "sessions"


def _read_lines(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def test_append_atomicity_and_round_trip(tmp_path: Path) -> None:
    sessions_dir = _sessions_dir(tmp_path)
    session_id = "11111111-1111-4111-8111-111111111111"

    append_event(
        session_id,
        "question_asked",
        {"question_hash": "abc123", "char_length": 12, "surface": "ask"},
        course_id="course/demo",
        surface="ask",
        sessions_dir=sessions_dir,
    )
    append_event(
        session_id,
        "answer_surfaced",
        {"confidence": 0.9, "source_count": 2, "total_answer_ms": 150.0},
        sessions_dir=sessions_dir,
    )

    tape_path = sessions_dir / f"{session_id}.jsonl"
    rows = _read_lines(tape_path)
    assert len(rows) == 2
    assert rows[0]["event"] == "question_asked"
    assert rows[0]["schema_version"] == 1
    assert rows[0]["course_id"] == "course/demo"
    assert rows[1]["event"] == "answer_surfaced"

    replayed = list(iter_events(session_id, sessions_dir=sessions_dir))
    assert replayed == rows


def test_schema_validation_rejects_missing_fields(tmp_path: Path) -> None:
    sessions_dir = _sessions_dir(tmp_path)
    with pytest.raises(ValueError, match="missing required payload fields"):
        append_event(
            "sess-schema",
            "session_started",
            {},
            sessions_dir=sessions_dir,
        )


def test_schema_validation_rejects_reserved_events(tmp_path: Path) -> None:
    sessions_dir = _sessions_dir(tmp_path)
    with pytest.raises(ValueError, match="reserved"):
        append_event(
            "sess-reserved",
            "card_created",
            {"card_id": "x"},
            sessions_dir=sessions_dir,
        )


def test_forbidden_keys_stripped_at_write_time(tmp_path: Path) -> None:
    sessions_dir = _sessions_dir(tmp_path)
    session_id = "sess-privacy"
    append_event(
        session_id,
        "question_asked",
        {
            "question_hash": "h1",
            "char_length": 5,
            "surface": "ask",
            "answer": "secret answer",
            "raw_text": "leak",
        },
        sessions_dir=sessions_dir,
    )
    row = _read_lines(sessions_dir / f"{session_id}.jsonl")[0]
    assert "answer" not in row["payload"]
    assert "raw_text" not in row["payload"]


def test_reader_skips_malformed_and_partial_lines(tmp_path: Path) -> None:
    sessions_dir = _sessions_dir(tmp_path)
    session_id = "sess-reader"
    tape_path = sessions_dir / f"{session_id}.jsonl"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    good = {
        "ts": "2026-05-24T12:00:00Z",
        "event": "session_started",
        "session_id": session_id,
        "schema_version": 1,
        "payload": {"entry_surface": "mission_control"},
    }
    tape_path.write_text(
        json.dumps(good) + "\n"
        "{not-json\n"
        '{"partial": true',
        encoding="utf-8",
    )

    rows = list(iter_events(session_id, sessions_dir=sessions_dir))
    assert rows == [good]


def test_reader_empty_file_ok(tmp_path: Path) -> None:
    sessions_dir = _sessions_dir(tmp_path)
    session_id = "sess-empty"
    assert list(iter_events(session_id, sessions_dir=sessions_dir)) == []


def test_filename_sanitization_rejects_path_separators() -> None:
    unsafe = "../evil/session"
    assert sanitize_session_id(unsafe) == hashlib.sha256(unsafe.encode("utf-8")).hexdigest()
    assert "/" not in sanitize_session_id("a/b")
    assert "\\" not in sanitize_session_id("a\\b")


def test_ensure_session_started_dedup(tmp_path: Path) -> None:
    sessions_dir = _sessions_dir(tmp_path)
    session_id = "sess-dedup"
    ensure_session_started(
        session_id,
        entry_surface="mission_control",
        sessions_dir=sessions_dir,
    )
    ensure_session_started(
        session_id,
        entry_surface="mission_control",
        sessions_dir=sessions_dir,
    )
    rows = _read_lines(sessions_dir / f"{session_id}.jsonl")
    assert len(rows) == 1
    assert rows[0]["event"] == "session_started"


def test_end_session_appends_and_clears_dedup(tmp_path: Path) -> None:
    sessions_dir = _sessions_dir(tmp_path)
    session_id = "sess-end"
    ensure_session_started(
        session_id,
        entry_surface="tutor",
        sessions_dir=sessions_dir,
    )
    end_session(session_id, reason="explicit_new_session", sessions_dir=sessions_dir)
    rows = _read_lines(sessions_dir / f"{session_id}.jsonl")
    assert [row["event"] for row in rows] == ["session_started", "session_ended"]

    ensure_session_started(
        session_id,
        entry_surface="tutor",
        sessions_dir=sessions_dir,
    )
    rows = _read_lines(sessions_dir / f"{session_id}.jsonl")
    assert len(rows) == 3


def test_offline_payload_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME_RAG_E2E_OFFLINE", "true")
    reset_settings_cache()
    assert offline_payload_tag() == {"offline": True}

    monkeypatch.delenv("HOME_RAG_E2E_OFFLINE", raising=False)
    monkeypatch.setenv("HOME_RAG_MICRO_QUIZ_OFFLINE", "true")
    reset_settings_cache()
    assert offline_payload_tag() == {"offline": True}

    monkeypatch.delenv("HOME_RAG_MICRO_QUIZ_OFFLINE", raising=False)
    reset_settings_cache()
    assert offline_payload_tag() == {}


def test_offline_tag_merged_into_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sessions_dir = _sessions_dir(tmp_path)
    monkeypatch.setenv("HOME_RAG_E2E_OFFLINE", "true")
    reset_settings_cache()
    session_id = "sess-offline"
    append_event(
        session_id,
        "quiz_attempt",
        {
            "quiz_kind": "micro",
            "topic": "algebra",
            "correct": True,
            "difficulty_band": "medium",
        },
        sessions_dir=sessions_dir,
    )
    row = _read_lines(sessions_dir / f"{session_id}.jsonl")[0]
    assert row["payload"]["offline"] is True


def test_debug_replay_api_flag_disabled_returns_404() -> None:
    client = TestClient(api.app)
    response = client.get("/debug/session-tape/test-session")
    assert response.status_code == 404


def test_debug_replay_api_flag_enabled_returns_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SESSION_TAPE_DEBUG_REPLAY_ENABLED", "true")
    reset_settings_cache()
    sessions_dir = _sessions_dir(tmp_path)
    monkeypatch.setattr(session_tape, "SESSIONS_DIR", sessions_dir)

    session_id = "sess-debug-api"
    ensure_session_started(
        session_id,
        entry_surface="ask",
        sessions_dir=sessions_dir,
    )

    client = TestClient(api.app)
    response = client.get(f"/debug/session-tape/{session_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == session_id
    assert len(body["events"]) == 1
    assert body["events"][0]["event"] == "session_started"

    monkeypatch.delenv("SESSION_TAPE_DEBUG_REPLAY_ENABLED", raising=False)
    reset_settings_cache()


def test_e2e_graduation_append_and_required_fields(tmp_path: Path) -> None:
    sessions_dir = _sessions_dir(tmp_path)
    session_id = "grad-session-0001"

    append_event(
        session_id,
        "e2e_graduation",
        {
            "llm_model": "qwen/qwen3.6-27b",
            "llm_source": "local",
            "fallback_used": False,
        },
        course_id="course/test",
        sessions_dir=sessions_dir,
    )

    rows = _read_lines(sessions_dir / f"{session_id}.jsonl")
    assert len(rows) == 1
    ev = rows[0]
    assert ev["event"] == "e2e_graduation"
    assert ev["payload"]["llm_model"] == "qwen/qwen3.6-27b"
    assert ev["payload"]["llm_source"] == "local"
    assert ev["payload"]["fallback_used"] is False
    assert ev["course_id"] == "course/test"


def test_e2e_graduation_rejects_missing_fields(tmp_path: Path) -> None:
    sessions_dir = _sessions_dir(tmp_path)
    with pytest.raises(ValueError, match="missing required payload fields"):
        append_event(
            "grad-session-bad",
            "e2e_graduation",
            {"llm_model": "qwen/qwen3.6-27b"},
            sessions_dir=sessions_dir,
        )
