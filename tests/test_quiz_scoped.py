"""Scoped/micro quiz latency budget integration tests (epoch-latency-budget-quiz-surface-v1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import reset_settings_cache
from app.quiz_micro import InvalidMicroQuizQuestionError, generate_micro_quiz, process_micro_quiz_outcome
from app.quiz_scoped import generate_scoped_quiz
from app.user_state import reset_schema_cache_for_tests


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "quiz_scoped_budget.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


class _BudgetFakeClock:
    def __init__(self, *, elapsed_ms: float = 0.0) -> None:
        self._calls = 0
        self._elapsed_ms = elapsed_ms

    def __call__(self) -> float:
        self._calls += 1
        if self._calls == 1:
            return 0.0
        return self._elapsed_ms / 1000.0


def _patch_budget_clock(monkeypatch, module, *, elapsed_ms: float, jsonl_path: Path) -> None:
    import app.latency_budget as latency_budget

    real_with_budget = latency_budget.with_budget

    def _wrapped(surface, fn, **kwargs):
        return real_with_budget(
            surface,
            fn,
            clock=_BudgetFakeClock(elapsed_ms=elapsed_ms),
            jsonl_path=jsonl_path,
            **kwargs,
        )

    monkeypatch.setattr(module, "with_budget", _wrapped)


def _scoped_quiz_llm_fixtures(monkeypatch):
    _one_q = (
        '{"question":"q","options":["a","b","c","d"],"correct_index":0,'
        '"difficulty":"recognition","explanation":""}'
    )

    class _FakeResp:
        text = "[" + ",".join([_one_q] * 6) + "]"
        source_nodes = []

    class _FakeLLM:
        def complete(self, prompt, **kwargs):
            return _FakeResp()

    monkeypatch.setattr(
        "app.quiz_service.get_quiz_llm_for_generation",
        lambda: _FakeLLM(),
    )

    def _fake_explain(ident: str):
        return {"content_preview": "x" * 200}

    monkeypatch.setattr("app.explain_service.explain_file", _fake_explain)


def test_generate_scoped_quiz_latency_budget_soft_breach_on_gen(monkeypatch, tmp_path):
    _scoped_quiz_llm_fixtures(monkeypatch)
    jsonl = tmp_path / "latency_budget.jsonl"
    import app.quiz_scoped as quiz_scoped_mod

    _patch_budget_clock(monkeypatch, quiz_scoped_mod, elapsed_ms=3500.0, jsonl_path=jsonl)

    out = generate_scoped_quiz("document", "notes/a.md", num_questions=6)

    assert out.get("success") is True
    budget = out.get("latency_budget") or {}
    assert budget.get("surface") == "quiz_gen"
    assert budget.get("event") == "surface_breached_soft"
    assert budget.get("target_ms") == 2000
    rows = [line for line in jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    assert json.loads(rows[0])["surface"] == "quiz_gen"


def test_generate_scoped_quiz_pre_validation_skips_budget_clock(monkeypatch, tmp_path):
    jsonl = tmp_path / "latency_budget.jsonl"
    import app.quiz_scoped as quiz_scoped_mod

    _patch_budget_clock(monkeypatch, quiz_scoped_mod, elapsed_ms=9000.0, jsonl_path=jsonl)

    out = generate_scoped_quiz("document", "", num_questions=6)

    assert out.get("success") is False
    assert "latency_budget" not in out
    assert not jsonl.is_file()


def test_process_micro_quiz_outcome_latency_budget_hard_non_preemptive(
    isolated_user_db,
    monkeypatch,
    tmp_path,
):
    jsonl = tmp_path / "latency_budget.jsonl"
    import app.quiz_micro as quiz_micro_mod

    _patch_budget_clock(monkeypatch, quiz_micro_mod, elapsed_ms=7000.0, jsonl_path=jsonl)

    qd = {
        "question": "Q",
        "options": ["A) 1", "B) 2", "C) 3", "D) 4"],
        "correct_option": "B",
        "type": "recognition",
        "difficulty": "medium",
    }
    out = process_micro_quiz_outcome(
        qd,
        "B",
        current_topic="topic_x",
        current_mastery="intermediate",
        session_id="sess-quiz-budget-1",
    )

    budget = out.get("latency_budget") or {}
    assert budget.get("surface") == "quiz_submit"
    assert budget.get("event") == "surface_breached_hard"
    assert out["quiz_feedback"].get("status") == "correct"
    assert "recommended_next" in out
    rows = [line for line in jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    assert json.loads(rows[0])["surface"] == "quiz_submit"


def test_process_micro_quiz_outcome_invalid_question_before_budget_wrap(
    isolated_user_db,
    monkeypatch,
    tmp_path,
):
    jsonl = tmp_path / "latency_budget.jsonl"
    import app.quiz_micro as quiz_micro_mod

    _patch_budget_clock(monkeypatch, quiz_micro_mod, elapsed_ms=7000.0, jsonl_path=jsonl)

    qd = {
        "question": "Q",
        "options": ["A) 1", "B) 2", "C) 3", "D) 4"],
        "correct_option": "X",
        "type": "recognition",
    }
    with pytest.raises(InvalidMicroQuizQuestionError):
        process_micro_quiz_outcome(
            qd,
            "A",
            current_topic="topic_x",
            current_mastery="intermediate",
        )
    assert not jsonl.is_file()


def test_generate_micro_quiz_latency_budget_on_llm_path(monkeypatch, tmp_path):
    jsonl = tmp_path / "latency_budget.jsonl"
    import app.quiz_micro as quiz_micro_mod

    monkeypatch.setattr(quiz_micro_mod, "_micro_quiz_force_offline", lambda: False)
    _patch_budget_clock(monkeypatch, quiz_micro_mod, elapsed_ms=3200.0, jsonl_path=jsonl)

    valid_payload = {
        "question": "What is RAG?",
        "options": ["A) x", "B) y", "C) z", "D) w"],
        "correct_option": "B",
        "explanation": "Because.",
        "difficulty": "medium",
        "type": "application",
    }

    class _FakeResp:
        text = json.dumps(valid_payload)

    class _FakeLLM:
        def complete(self, prompt, **kwargs):
            return _FakeResp()

    monkeypatch.setattr(
        "app.quiz_service.get_quiz_llm_for_generation",
        lambda: _FakeLLM(),
    )

    out = generate_micro_quiz("RAG topic", "intermediate", [], use_llm=True)

    budget = out.get("latency_budget") or {}
    assert budget.get("surface") == "quiz_gen"
    assert budget.get("event") == "surface_breached_soft"
    assert out.get("correct_option") == "B"
