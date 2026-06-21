"""Evaluation harness scaffold for SSR Level 1 ML reranking (contract + dataset)."""

from __future__ import annotations

import json
import subprocess
import sys

from app.ssr_ai import eval_harness as eh
from tests.studio_layout import product_app_path


def _load_cases() -> list[dict]:
    return json.loads(eh.CASES_PATH.read_text(encoding="utf-8"))


def _ensure_forgetting_curve_datasets() -> None:
    if eh.TRAIN_DATA_PATH.exists() and eh.TEST_DATA_PATH.exists():
        return
    subprocess.run(
        [sys.executable, str(eh.DATA_SCRIPT_PATH), "--seed", "42"],
        cwd=eh.ROOT,
        check=True,
    )


def test_ssr_ml_reranking_eval_contract_artifacts_exist() -> None:
    _ensure_forgetting_curve_datasets()
    assert eh.CONTRACT_PATH.exists()
    assert eh.ML_PACKAGE_PATH.exists()
    assert eh.RUBRIC_PATH.exists()
    assert eh.CASES_PATH.exists()
    assert eh.DATA_SCRIPT_PATH.exists()
    assert eh.TRAIN_SCRIPT_PATH.exists()
    assert eh.EVAL_SCRIPT_PATH.exists()
    assert eh.TRAIN_DATA_PATH.exists()
    assert eh.TEST_DATA_PATH.exists()
    assert eh.MODEL_PATH.exists()
    assert eh.REPORT_PATH.exists()
    text = eh.RUBRIC_PATH.read_text(encoding="utf-8")
    assert "AUC-ROC" in text
    assert "cards_due completion" in text
    report = eh.REPORT_PATH.read_text(encoding="utf-8")
    assert "Macro AUC-ROC" in report
    assert "Precision@5" in report
    assert "Recall@5" in report
    assert "Serving mode" in report


def test_ssr_ml_reranking_test_set_has_100_local_scenarios() -> None:
    cases = _load_cases()
    assert len(cases) == 100
    assert {c["ground_truth_best_hint_kind"] for c in cases} == eh.HINT_KINDS
    for case in cases:
        assert case["id"].startswith(eh.CASE_ID_PREFIX)
        assert case["ground_truth_best_hint_kind"] in eh.HINT_KINDS
        assert case["retention_probability_label"] in (0, 1)
        feats = case["features"]
        assert eh.REQUIRED_FEATURE_KEYS <= set(feats.keys())
        assert isinstance(feats["quiz_failed_recent"], bool)
        assert isinstance(feats["tutor_stub_active"], bool)


def test_ssr_ml_contract_declares_ab_and_monitoring_infrastructure() -> None:
    pfx = "".join(("s", "s", "r"))
    module = product_app_path(f"{pfx}_ml_monitoring.py").read_text(encoding="utf-8")
    telemetry = product_app_path("ssr_ai", "telemetry.py").read_text(encoding="utf-8")
    assert "record_cards_due_completion" in module
    assert "summarize_cards_due_completion_ab" in module
    assert "summarize_ml_inference_events" in module
    assert "inference_latency_p95_ms" in telemetry
    assert "fallback_rate" in telemetry
