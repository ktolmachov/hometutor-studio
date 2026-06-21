from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts import eval_ci_gate


def test_evaluate_gate_detects_threshold_and_case_regressions():
    report = {
        "mode": "live",
        "comparable_to_baseline": True,
        "summary": {
            "source_precision_at_3": 0.55,
            "latency_p95_sec": 12.0,
            "answer_groundedness": 2.2,
            "tutor_coherence": 1.8,
        },
        "cases": [
            {
                "id": "gqa01",
                "source_precision_at_3": 0.0,
                "answer_groundedness": 1.0,
                "tutor_coherence": 1.0,
                "latency_sec": 3.0,
            }
        ],
    }
    baseline = {
        "comparable_to_baseline": True,
        "summary": {
            "source_precision_at_3": 1.0,
            "latency_p95_sec": 1.0,
            "answer_groundedness": 3.0,
            "tutor_coherence": 2.5,
        },
        "cases": [
            {
                "id": "gqa01",
                "source_precision_at_3": 1.0,
                "answer_groundedness": 2.5,
                "tutor_coherence": 1.6,
                "latency_sec": 1.0,
            }
        ],
    }
    thresholds = {
        "thresholds": {
            "source_precision_at_3": 0.6,
            "latency_p95_sec": 10.0,
            "answer_groundedness": 2.0,
            "tutor_coherence": 1.5,
        },
        "baseline_tolerance": {
            "source_precision_at_3_drop": 0.0,
            "answer_groundedness_drop": 0.25,
            "tutor_coherence_drop": 0.25,
            "per_case_latency_sec_increase": 1.0,
        },
    }

    payload, rc = eval_ci_gate.evaluate_gate(report=report, baseline=baseline, thresholds=thresholds)

    assert rc == eval_ci_gate.EXIT_FAILED
    assert payload["status"] == "fail"
    assert any(item["metric"] == "source_precision_at_3" and item["threshold"] == 0.6 for item in payload["threshold_failures"])
    assert any(item["case_id"] is None and item["baseline"] is None for item in payload["threshold_failures"])
    assert any(item["component"] == "retrieval" for item in payload["summary_regression_failures"])
    assert any(item["component"] == "generation" for item in payload["summary_regression_failures"])
    assert any(item["component"] == "tutor_coherence" for item in payload["summary_regression_failures"])
    assert any(item["component"] == "latency" for item in payload["summary_regression_failures"])
    assert any(item["component"] == "retrieval" for item in payload["regression_failures"])
    assert any(item["component"] == "generation" for item in payload["regression_failures"])
    assert any(item["component"] == "tutor_coherence" for item in payload["regression_failures"])
    assert any(item["component"] == "latency" for item in payload["regression_failures"])


def test_evaluate_gate_skips_baseline_delta_for_mock_reports():
    report = {
        "mode": "mock",
        "comparable_to_baseline": False,
        "summary": {
            "source_precision_at_3": 1.0,
            "latency_p95_sec": 0.05,
            "answer_groundedness": None,
            "tutor_coherence": None,
        },
        "cases": [],
    }
    thresholds = {
        "thresholds": {
            "source_precision_at_3": 0.6,
            "latency_p95_sec": 10.0,
        }
    }

    payload, rc = eval_ci_gate.evaluate_gate(report=report, baseline=None, thresholds=thresholds)

    assert rc == eval_ci_gate.EXIT_OK
    assert payload["status"] == "warn"
    assert payload["comparable_to_baseline"] is False
    assert payload["regression_failures"] == []


def test_eval_ci_gate_main_writes_json_report(tmp_path, monkeypatch):
    baseline_path = tmp_path / "baseline.json"
    thresholds_path = tmp_path / "thresholds.json"
    report_path = tmp_path / "gate.json"
    baseline_path.write_text(
        json.dumps({"comparable_to_baseline": False, "summary": {}, "cases": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    thresholds_path.write_text(
        json.dumps({"thresholds": {"source_precision_at_3": 0.6, "latency_p95_sec": 10.0}}, ensure_ascii=False),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        eval_ci_gate,
        "_run_eval_command",
        lambda **kwargs: (
            0,
            {
                "mode": "mock",
                "comparable_to_baseline": False,
                "summary": {
                    "source_precision_at_3": 1.0,
                    "latency_p95_sec": 0.02,
                    "answer_groundedness": None,
                    "tutor_coherence": None,
                },
                "cases": [],
            },
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "eval_ci_gate.py",
            "--baseline",
            str(baseline_path),
            "--thresholds",
            str(thresholds_path),
            "--report-json",
            str(report_path),
        ],
    )

    rc = eval_ci_gate.main()
    payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert rc == eval_ci_gate.EXIT_OK
    assert payload["status"] == "warn"
