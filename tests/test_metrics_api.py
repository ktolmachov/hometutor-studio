"""HTTP-facing metrics observability checks (narrow DoD: stage cost rollups wired to `/metrics/cost`)."""

import importlib
from pathlib import Path

from fastapi.testclient import TestClient

import app.api as api
import app.metrics as metrics
from app.config import reset_settings_cache
from app.user_state import reset_schema_cache_for_tests


def test_metrics_cost_http_includes_estimated_cost_by_stage(tmp_path):
    module = importlib.reload(metrics)
    module.METRICS_STORE_PATH = tmp_path / "metrics_store_stage_cost.jsonl"

    module.record_request(
        request_id="api-s1",
        question="q",
        query_type="qa",
        total_answer_ms=100.0,
        pipeline_ms=10.0,
        engine_acquire_ms=2.0,
        query_execute_ms=50.0,
        source_count=1,
        fallback_applied=False,
        estimated_cost_usd=0.01,
        estimated_cost_stages_usd={
            "classify": 0.001,
            "rewrite": 0.002,
            "retrieval": 0.003,
            "generation": 0.004,
            "judge": None,
        },
        answer_empty=False,
    )

    client = TestClient(api.app)
    response = client.get("/metrics/cost", params={"limit": 10, "top_n": 3})
    assert response.status_code == 200
    body = response.json()
    by_stage = body["estimated_cost_by_stage_usd"]
    assert by_stage["classify"]["total_usd"] == 0.001
    assert by_stage["retrieval"]["samples"] == 1
    assert by_stage["generation"]["avg_per_request"] == 0.004


def test_metrics_educational_http_schema(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("USER_STATE_DB", str(tmp_path / "metrics_edu.db"))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    client = TestClient(api.app)
    response = client.get("/metrics/educational", params={"limit_quiz_rows": 10})
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == 1
    assert "quiz_correctness" in body


def test_metrics_mastery_validation_http_schema(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("USER_STATE_DB", str(tmp_path / "metrics_mv.db"))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    client = TestClient(api.app)
    response = client.get("/metrics/mastery-validation", params={"limit_quiz_rows": 10})
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == 1
    assert "mastery_correlation" in body
