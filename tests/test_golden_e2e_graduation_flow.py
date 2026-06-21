"""Deterministic step machine for the golden E2E graduation delight loop.

Simulates: Q&A → Tutor → Quiz → Card → Review → Graduation
Asserts: tape contains e2e_graduation with correct llm_model/llm_source/fallback_used.
Privacy: no raw answer text written to tape.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.course_graduation import emit_e2e_graduation_event
from app.session_replay import iter_events
from app.session_tape import (
    append_event,
    ensure_session_started,
    reset_session_started_cache_for_tests,
)


def _sessions_dir(tmp_path: Path) -> Path:
    d = tmp_path / "sessions"
    d.mkdir()
    return d


def _read_tape(session_id: str, sessions_dir: Path) -> list[dict]:
    path = sessions_dir / f"{session_id}.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


DELIGHT_STEPS = ["Q&A", "Tutor", "Quiz", "Card", "Review", "Graduation"]


class DelightLoopStateMachine:
    """Deterministic step machine for the golden delight loop.

    Simulates each step emitting the relevant tape event,
    then fires e2e_graduation at the end.
    """

    def __init__(
        self,
        session_id: str,
        sessions_dir: Path,
        llm_model: str = "qwen/qwen3.6-27b",
        llm_source: str = "local",
        fallback_used: bool = False,
        course_id: str = "course/golden-test",
    ) -> None:
        self.session_id = session_id
        self.sessions_dir = sessions_dir
        self.llm_model = llm_model
        self.llm_source = llm_source
        self.fallback_used = fallback_used
        self.course_id = course_id
        self.completed: list[str] = []

    def _kw(self) -> dict:
        return {"course_id": self.course_id, "sessions_dir": self.sessions_dir}

    def step_session_start(self) -> None:
        ensure_session_started(
            self.session_id,
            entry_surface="mission_control",
            **self._kw(),
        )
        self.completed.append("session_start")

    def step_qa(self) -> None:
        append_event(
            self.session_id,
            "question_asked",
            {"question_hash": "qa_hash_001", "char_length": 42, "surface": "ask"},
            **self._kw(),
        )
        append_event(
            self.session_id,
            "answer_surfaced",
            {"confidence": 0.85, "source_count": 3, "total_answer_ms": 320.0},
            **self._kw(),
        )
        self.completed.append("Q&A")

    def step_tutor(self) -> None:
        append_event(
            self.session_id,
            "quiz_attempt",
            {
                "quiz_kind": "tutor",
                "topic": "test-topic",
                "correct": True,
                "difficulty_band": "easy",
            },
            **self._kw(),
        )
        self.completed.append("Tutor")

    def step_quiz(self) -> None:
        append_event(
            self.session_id,
            "quiz_attempt",
            {
                "quiz_kind": "micro",
                "topic": "test-topic",
                "correct": True,
                "difficulty_band": "medium",
            },
            **self._kw(),
        )
        self.completed.append("Quiz")

    def step_card(self) -> None:
        # Card creation is tracked externally; tape records retrieval
        append_event(
            self.session_id,
            "retrieval_completed",
            {"source_count": 2, "retrieval_mode": "hybrid", "latency_ms": 45.0},
            **self._kw(),
        )
        self.completed.append("Card")

    def step_review(self) -> None:
        append_event(
            self.session_id,
            "quiz_attempt",
            {
                "quiz_kind": "review",
                "topic": "test-topic",
                "correct": True,
                "difficulty_band": "hard",
            },
            **self._kw(),
        )
        self.completed.append("Review")

    def step_graduation(self) -> None:
        emit_e2e_graduation_event(
            self.session_id,
            llm_model=self.llm_model,
            llm_source=self.llm_source,
            fallback_used=self.fallback_used,
            **self._kw(),
        )
        self.completed.append("Graduation")

    def run_full_loop(self) -> None:
        self.step_session_start()
        self.step_qa()
        self.step_tutor()
        self.step_quiz()
        self.step_card()
        self.step_review()
        self.step_graduation()


@pytest.fixture(autouse=True)
def _reset_tape_cache() -> None:
    reset_session_started_cache_for_tests()


def test_full_delight_loop_completes_all_steps(tmp_path: Path) -> None:
    sessions_dir = _sessions_dir(tmp_path)
    machine = DelightLoopStateMachine("golden-sess-001", sessions_dir)
    machine.run_full_loop()

    assert set(DELIGHT_STEPS) <= set(machine.completed)


def test_tape_contains_e2e_graduation_event(tmp_path: Path) -> None:
    sessions_dir = _sessions_dir(tmp_path)
    machine = DelightLoopStateMachine("golden-sess-002", sessions_dir)
    machine.run_full_loop()

    events = list(iter_events("golden-sess-002", sessions_dir=sessions_dir))
    grad_events = [e for e in events if e["event"] == "e2e_graduation"]
    assert len(grad_events) == 1


def test_graduation_event_has_required_fields(tmp_path: Path) -> None:
    sessions_dir = _sessions_dir(tmp_path)
    machine = DelightLoopStateMachine(
        "golden-sess-003",
        sessions_dir,
        llm_model="qwen/qwen3.6-27b",
        llm_source="local",
        fallback_used=False,
    )
    machine.run_full_loop()

    rows = _read_tape("golden-sess-003", sessions_dir)
    grad = next(r for r in rows if r["event"] == "e2e_graduation")
    payload = grad["payload"]

    assert payload["llm_model"] == "qwen/qwen3.6-27b"
    assert payload["llm_source"] == "local"
    assert payload["fallback_used"] is False


def test_graduation_event_has_no_raw_answer_text(tmp_path: Path) -> None:
    """Privacy: raw answer text must not be written to tape."""
    sessions_dir = _sessions_dir(tmp_path)
    machine = DelightLoopStateMachine("golden-sess-004", sessions_dir)
    machine.run_full_loop()

    rows = _read_tape("golden-sess-004", sessions_dir)
    grad = next(r for r in rows if r["event"] == "e2e_graduation")
    payload = grad["payload"]

    assert "raw_text" not in payload
    assert "text" not in payload
    assert "answer" not in payload


def test_fallback_used_false_asserts_local_routing(tmp_path: Path) -> None:
    """When fallback_used=False, confirm tape records it correctly (no silent cloud switch)."""
    sessions_dir = _sessions_dir(tmp_path)
    machine = DelightLoopStateMachine(
        "golden-sess-005",
        sessions_dir,
        llm_model="qwen/qwen3.6-27b",
        llm_source="local",
        fallback_used=False,
    )
    machine.run_full_loop()

    rows = _read_tape("golden-sess-005", sessions_dir)
    grad = next(r for r in rows if r["event"] == "e2e_graduation")
    assert grad["payload"]["fallback_used"] is False
    assert grad["payload"]["llm_source"] == "local"


def test_graduation_event_order_is_last(tmp_path: Path) -> None:
    """Graduation must be the final event in the tape."""
    sessions_dir = _sessions_dir(tmp_path)
    machine = DelightLoopStateMachine("golden-sess-006", sessions_dir)
    machine.run_full_loop()

    rows = _read_tape("golden-sess-006", sessions_dir)
    assert rows[-1]["event"] == "e2e_graduation"


def test_delight_loop_steps_order_in_completed(tmp_path: Path) -> None:
    sessions_dir = _sessions_dir(tmp_path)
    machine = DelightLoopStateMachine("golden-sess-007", sessions_dir)
    machine.run_full_loop()

    # Verify each delight step appears in correct order within completed list
    step_indices = [machine.completed.index(s) for s in DELIGHT_STEPS if s in machine.completed]
    assert step_indices == sorted(step_indices)
