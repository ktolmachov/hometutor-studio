"""Baseline serialization, promotion и regression-gate для defense eval (US-12.7)."""

from __future__ import annotations

import json
from pathlib import Path

import app.eval_service as eval_service


def test_baseline_report_roundtrip_json_stable():
    summary = {
        "cases": 3,
        "dataset_version": "fixture:v1",
        "avg_answer_relevancy": 0.81,
        "route_match_rate": 0.9,
        "avg_tutor_score": 0.77,
    }
    doc = eval_service.build_promotable_baseline_document(
        summary,
        dataset_version="fixture:v1",
        eval_kind="rag_eval",
        promoted_from="/tmp/run.json",
        notes="unit",
    )
    text_a = eval_service.serialize_baseline_report(doc)
    text_b = eval_service.serialize_baseline_report(json.loads(text_a))
    assert text_a == text_b
    assert '"baseline_schema_version"' in text_a


def test_promote_eval_artifact_to_baseline_writes_expected_schema(tmp_path: Path):
    src = tmp_path / "eval_full.json"
    src.write_text(
        json.dumps(
            {
                "artifact_version": 2,
                "dataset_version": "ds-x",
                "summary": {
                    "cases": 2,
                    "dataset_version": "ds-x",
                    "avg_faithfulness": 0.91,
                    "route_match_rate": 0.85,
                },
                "results": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    dest = tmp_path / "baseline.json"
    meta = eval_service.promote_eval_artifact_to_baseline(src, dest, notes="promote-test")
    loaded = json.loads(dest.read_text(encoding="utf-8"))
    assert meta["baseline_path"] == str(dest.resolve())
    assert loaded["baseline_schema_version"] == eval_service.DEFENSE_BASELINE_SCHEMA_VERSION
    assert loaded["eval_kind"] == "rag_eval"
    assert loaded["summary"]["avg_faithfulness"] == 0.91


def test_promote_preserves_tutor_eval_kind(tmp_path: Path):
    src = tmp_path / "tutor.json"
    src.write_text(
        json.dumps(
            {
                "eval_kind": "tutor_regression",
                "summary": {"cases": 1, "avg_tutor_score": 0.8},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    dest = tmp_path / "tb.json"
    eval_service.promote_eval_artifact_to_baseline(src, dest)
    loaded = json.loads(dest.read_text(encoding="utf-8"))
    assert loaded["eval_kind"] == "tutor_regression"
    assert loaded["summary"]["avg_tutor_score"] == 0.8


def test_regression_gate_payload_skips_when_no_baseline_comparison_branch():
    payload = eval_service.build_defense_regression_gate_payload(
        {"summary": {"cases": 1, "dataset_version": "x"}},
        gate_kind="defense_eval",
    )
    assert payload["passed"] is True
    assert payload["exit_code"] == 0
    assert payload["regressions"] == []
    assert payload["metric_deltas"] == []
    assert payload["schema_version"] == eval_service.DEFENSE_REGRESSION_GATE_SCHEMA_VERSION


def test_regression_gate_payload_actionable_on_regression():
    eval_out = {
        "summary": {"cases": 4, "dataset_version": "golden:v2"},
        "baseline_comparison": {
            "passed": False,
            "baseline_path": "/b.json",
            "regressions": ["avg_answer_relevancy"],
            "comparisons": {
                "avg_answer_relevancy": {
                    "current": 0.7,
                    "baseline": 0.8,
                    "delta": -0.1,
                    "relative_change": -0.125,
                    "regression": True,
                },
                "avg_faithfulness": {
                    "current": 0.9,
                    "baseline": 0.9,
                    "delta": 0.0,
                    "relative_change": 0.0,
                    "regression": False,
                },
            },
        },
    }
    payload = eval_service.build_defense_regression_gate_payload(eval_out)
    assert payload["passed"] is False
    assert payload["exit_code"] == 2
    assert payload["regressions"] == ["avg_answer_relevancy"]
    metrics_in_deltas = [d["metric"] for d in payload["metric_deltas"]]
    assert metrics_in_deltas == sorted(metrics_in_deltas)


def test_compare_to_baseline_detects_avg_tutor_score_regression():
    summary = {"avg_tutor_score": 0.65}
    baseline = {
        "artifact_path": "tutor_baseline.json",
        "summary": {"avg_tutor_score": 0.8},
    }
    comp = eval_service._compare_to_baseline(summary, baseline)
    assert comp is not None
    assert comp["passed"] is False
    assert "avg_tutor_score" in comp["regressions"]
