"""Circuit breaker behaviour for the local SSR LLM endpoint."""

from __future__ import annotations

import pytest

from app import llm_local_circuit


@pytest.fixture(autouse=True)
def _reset_circuit() -> None:
    llm_local_circuit.reset_all()
    yield
    llm_local_circuit.reset_all()


def test_is_open_returns_false_for_unknown_base() -> None:
    assert llm_local_circuit.is_open("http://127.0.0.1:8787") is False


def test_is_open_after_threshold_failures_within_window() -> None:
    base = "http://127.0.0.1:8787"
    for _ in range(3):
        llm_local_circuit.record_failure(
            base, error_type="APIConnectionError", failure_threshold=3, failure_window_sec=30.0
        )
    assert llm_local_circuit.is_open(base, reset_after_sec=60.0) is True


def test_two_failures_do_not_open_circuit() -> None:
    base = "http://127.0.0.1:8787"
    for _ in range(2):
        llm_local_circuit.record_failure(
            base, error_type="APIConnectionError", failure_threshold=3, failure_window_sec=30.0
        )
    assert llm_local_circuit.is_open(base, reset_after_sec=60.0) is False


def test_failures_outside_window_do_not_accumulate() -> None:
    base = "http://127.0.0.1:8787"
    # First two failures at t=0 fall out of a 10s window before the third at t=20.
    llm_local_circuit.record_failure(
        base, error_type="X", failure_threshold=3, failure_window_sec=10.0, now=0.0
    )
    llm_local_circuit.record_failure(
        base, error_type="X", failure_threshold=3, failure_window_sec=10.0, now=0.5
    )
    just_opened = llm_local_circuit.record_failure(
        base, error_type="X", failure_threshold=3, failure_window_sec=10.0, now=20.0
    )
    assert just_opened is False


def test_record_success_closes_open_circuit() -> None:
    base = "http://127.0.0.1:8787"
    for _ in range(3):
        llm_local_circuit.record_failure(
            base, error_type="X", failure_threshold=3, failure_window_sec=30.0
        )
    assert llm_local_circuit.is_open(base) is True
    llm_local_circuit.record_success(base)
    assert llm_local_circuit.is_open(base) is False


def test_circuit_auto_half_open_after_reset_window() -> None:
    base = "http://127.0.0.1:8787"
    for _ in range(3):
        llm_local_circuit.record_failure(
            base, error_type="X", failure_threshold=3, failure_window_sec=30.0, now=0.0
        )
    assert llm_local_circuit.is_open(base, reset_after_sec=60.0, now=10.0) is True
    # After reset window elapses, a single new probe is allowed (returns closed).
    assert llm_local_circuit.is_open(base, reset_after_sec=60.0, now=100.0) is False


def test_base_url_normalised_case_insensitive_trailing_slash() -> None:
    for _ in range(3):
        llm_local_circuit.record_failure(
            "HTTP://127.0.0.1:8787/", error_type="X",
            failure_threshold=3, failure_window_sec=30.0,
        )
    assert llm_local_circuit.is_open("http://127.0.0.1:8787") is True


def test_empty_base_url_is_noop() -> None:
    assert llm_local_circuit.is_open(None) is False
    llm_local_circuit.record_failure(None, error_type="X")
    assert llm_local_circuit.snapshot() == {}
