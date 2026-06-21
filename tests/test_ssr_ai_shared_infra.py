"""Shared SSR AI infra: telemetry rollup, eval paths, fallback constants."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.ssr_ai import eval_harness, fallback
from app.ssr_ai.dataset import repo_root
from app.ssr_ai.telemetry import (
    append_kv_events,
    record_ssr_ai_auxiliary_event,
    summarize_ml_inference_events,
)

_GATE_DOC_REL = Path(
    "doc/team_workflow/ssr_ai_vision/ssr_ai_vision_level2_level3_readiness_gate.md"
)


def test_repo_root_matches_eval_harness() -> None:
    assert repo_root().resolve() == eval_harness.ROOT.resolve()


def test_append_kv_inference_shape_roundtrip() -> None:
    conn = MagicMock()
    blobs: dict[str, str] = {}

    def exec_sql(sql: str, args=()) -> MagicMock:
        key_s = str(args[0])
        if "SELECT value FROM app_kv" in sql:
            raw = blobs.get(key_s)
            if raw is None:
                return MagicMock(fetchone=lambda: None)
            return MagicMock(fetchone=lambda: {"value": raw})

        if "INSERT INTO app_kv" in sql:
            blobs[key_s] = str(args[1])
            return MagicMock()

        return MagicMock(fetchone=lambda: None)

    conn.execute.side_effect = exec_sql

    append_kv_events(
        conn,
        key="ssr_ml_monitoring_v1",
        event={
            "ts": "t",
            "latency_ms": 1.0,
            "confidence": 0.7,
            "fallback": False,
            "reason": "applied",
        },
        max_events=10,
    )
    stored = json.loads(blobs["ssr_ml_monitoring_v1"])
    events_out = stored.get("events") or []
    assert len(events_out) == 1
    summary = summarize_ml_inference_events(list(events_out))
    assert summary["events"] == 1


def test_summarize_ml_inference_events_empty() -> None:
    summary = summarize_ml_inference_events([])
    assert summary["events"] == 0
    assert summary["inference_latency_p95_ms"] == 0.0


def test_summarize_ml_inference_events_sample() -> None:
    rows = [
        {"latency_ms": 10.0, "confidence": 0.7, "fallback": False},
        {"latency_ms": 20.0, "confidence": 0.5, "fallback": True},
        {"latency_ms": 30.0, "confidence": None, "fallback": True},
    ]
    summary = summarize_ml_inference_events(rows)
    assert summary["events"] == 3
    assert summary["fallback_rate"] > 0


def test_fallback_reason_strings_stable() -> None:
    """Contract for ``smart_study_ssr_ml`` telemetry reasons."""
    assert fallback.INFERENCE_EXCEPTION == "inference_exception"
    assert fallback.NO_ALLOWED_PROBABILITIES == "no_allowed_probabilities"


def test_eval_harness_paths_exist() -> None:
    """Same contract as ``tests/eval/test_ssr_ml_reranking`` — paths via shared module."""
    assert eval_harness.CONTRACT_PATH.exists()
    assert eval_harness.CASES_PATH.exists()
    cases = json.loads(eval_harness.CASES_PATH.read_text(encoding="utf-8"))
    assert isinstance(cases, list) and cases
    assert str(cases[0]["id"]).startswith(eval_harness.CASE_ID_PREFIX)


@pytest.mark.parametrize("level", ["L2", "L3"])
def test_auxiliary_round_trip_via_with_db_stub(level: str) -> None:
    blobs: dict[str, str] = {}

    def exec_sql(sql: str, args=()) -> MagicMock:
        key_s = str(args[0])
        if "SELECT value FROM app_kv" in sql:
            raw = blobs.get(key_s)
            if raw is None:
                return MagicMock(fetchone=lambda: None)
            return MagicMock(fetchone=lambda: {"value": raw})

        if "INSERT INTO app_kv" in sql:
            blobs[key_s] = str(args[1])
            return MagicMock()

        return MagicMock(fetchone=lambda: None)

    mock_conn = MagicMock()
    mock_conn.execute.side_effect = exec_sql

    def fake_with_db(cb, *, write: bool):
        return cb(mock_conn)

    with patch("app.user_state._with_db", side_effect=fake_with_db):
        record_ssr_ai_auxiliary_event(level=level, category="unittest", detail={"k": "v"})

    aux = blobs.get("ssr_ai_auxiliary_telemetry_v1", "")
    assert "unittest" in aux
    assert '"level"' in aux


def test_level2_level3_readiness_gate_doc_present() -> None:
    doc = repo_root() / _GATE_DOC_REL
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    assert "## 1. L1" in text
    assert "## 2. L2" in text
    assert "## 3. L3" in text
    assert "CONDITIONAL GO" in text
