"""
E2E smoke по CJM (moments of truth): HTTP-контур без браузера.

Покрывает: preflight env script, health, статус индексации, первый ответ с SLO,
micro-quiz evaluate, due reviews. LLM и тяжёлый ingest мокируются или обходятся лёгкими фикстурами.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.api as api
import app.api_services as api_services
from app.config import reset_settings_cache
from app.knowledge_graph import JsonKnowledgeGraph
from app.spaced_repetition import update_spaced_repetition
from app.user_state import reset_schema_cache_for_tests

REPO_ROOT = Path(__file__).resolve().parents[1]

# US-3.1 / E8.1: «первый ответ» должен укладываться в SLO при отсутствии искусственных задержек в сервисном слое.
FIRST_ANSWER_SLO_SEC = 5.0


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "e2e_us.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


def _client() -> TestClient:
    return TestClient(api.app)


def test_cjm_health_ok():
    client = _client()
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_cjm_check_env_script_ok_with_dummy_key():
    env = {**os.environ, "OPENAI_API_KEY": "sk-e2e-dummy-key-012345678901234567890"}
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "check_env.py")],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_cjm_reindex_status_observable():
    """Proxy для стадии Ingest: API отдаёт состояние пайплайна индексации (polling UI)."""
    client = _client()
    r = client.get("/reindex/status")
    assert r.status_code == 200
    body = r.json()
    assert "status" in body


def test_cjm_first_question_under_latency_slo_with_sources(monkeypatch):
    def fake_answer_question(question, options):
        return {
            "answer": "E2E synthetic answer",
            "sources": [
                {
                    "file_name": "demo.md",
                    "relative_path": "demo.md",
                    "text": "Synthetic chunk for e2e SLO test.",
                }
            ],
            "debug": {},
        }

    monkeypatch.setattr(api_services, "answer_question", fake_answer_question)
    monkeypatch.setattr(api_services, "append_history_entry", lambda **kwargs: kwargs)
    monkeypatch.setattr(api_services, "record_request", lambda **kwargs: None)
    monkeypatch.setattr(api_services.faq_memory, "save_interaction", lambda *args, **kwargs: None)
    
    client = _client()
    t0 = time.perf_counter()
    r = client.post("/ask", json={"question": "What is in my notes?"})
    elapsed = time.perf_counter() - t0

    assert r.status_code == 200
    data = r.json()
    assert data.get("answer")
    assert isinstance(data.get("sources"), list) and len(data["sources"]) >= 1
    assert elapsed < FIRST_ANSWER_SLO_SEC, f"wall-clock {elapsed:.3f}s exceeds SLO {FIRST_ANSWER_SLO_SEC}s"


def test_cjm_micro_quiz_evaluate_roundtrip():
    client = _client()
    body = {
        "quiz_question": {
            "type": "application",
            "correct_option": "B",
            "prompt": "Test?",
            "options": {"A": "a", "B": "b", "C": "c", "D": "d"},
        },
        "user_answer_letter": "B",
        "current_topic": "e2e_topic",
        "current_mastery": "intermediate",
    }
    r = client.post("/quiz/evaluate", json=body)
    assert r.status_code == 200
    out = r.json()
    assert "quiz_feedback" in out
    assert out["quiz_feedback"].get("status") == "correct"


def test_cjm_review_due_endpoint(isolated_user_db, monkeypatch):
    p = isolated_user_db.parent / "review_graph_e2e.json"
    p.write_text(
        '{"concepts":{"E2E":{"description":"","prerequisites":[]}},"documents":{},"edges":{}}',
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(p)
    monkeypatch.setattr("app.routers.review.get_active_knowledge_graph", lambda: kg)

    update_spaced_repetition("E2E", 5)

    def _force_due():
        from app.user_state import _with_db

        def _work(conn):
            conn.execute(
                "UPDATE spaced_repetition SET next_review = ? WHERE concept = ?",
                ("2000-01-01T00:00:00+00:00", "E2E"),
            )
            conn.commit()

        _with_db(_work)

    _force_due()

    client = _client()
    r = client.get("/review/due")
    assert r.status_code == 200
    data = r.json()
    assert data.get("count", 0) >= 1
    assert any(row.get("concept") == "E2E" for row in data.get("due_reviews", []))
