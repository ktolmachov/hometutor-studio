import json
import sys

from scripts import graph_expansion_compare as compare


def test_resolve_compare_gate_preset_returns_expected_defaults():
    preset = compare.resolve_compare_gate_preset("synthesis-strict")
    assert preset["profile"] == "local"
    assert preset["gate_query_types"] == ["synthesis"]
    assert preset["gate_query_type_profiles"] == {"synthesis": "strict"}

    dual = compare.resolve_compare_gate_preset("dual-strict")
    assert dual["profile"] == "local"
    assert dual["gate_query_types"] == ["synthesis", "learning_plan"]
    assert dual["gate_query_type_profiles"] == {"synthesis": "strict", "learning_plan": "strict"}


def test_build_compare_report_marks_better_and_worse():
    report = compare.build_compare_report(
        baseline={
            "latency_ms": {"p95_total_answer_ms": 120.0, "avg_total_answer_ms": 100.0},
            "graph_expansion": {
                "events_total": 10,
                "p95_graph_expansion_ms": 55.0,
                "applied_rate": 0.2,
                "skipped_rate": 0.7,
                "error_rate": 0.1,
                "avg_extra_chunks_when_applied": 1.0,
                "skip_reasons": {"query_type": 7},
                "by_query_type": {
                    "synthesis": {
                        "events_total": 6,
                        "applied_rate": 0.3,
                        "skipped_rate": 0.5,
                        "error_rate": 0.0,
                        "skip_reasons": {"query_type": 3},
                    }
                },
            },
        },
        candidate={
            "latency_ms": {"p95_total_answer_ms": 90.0, "avg_total_answer_ms": 96.0},
            "graph_expansion": {
                "events_total": 12,
                "p95_graph_expansion_ms": 40.0,
                "applied_rate": 0.4,
                "skipped_rate": 0.6,
                "error_rate": 0.0,
                "avg_extra_chunks_when_applied": 2.0,
                "skip_reasons": {"query_type": 6},
                "by_query_type": {
                    "synthesis": {
                        "events_total": 8,
                        "applied_rate": 0.5,
                        "skipped_rate": 0.4,
                        "error_rate": 0.0,
                        "skip_reasons": {"query_type": 2},
                    }
                },
            },
        },
        baseline_label="off",
        candidate_label="on",
    )
    assert report["delta"]["latency_ms"]["p95_total_answer_ms"]["verdict"] == "better"
    assert report["delta"]["graph_expansion"]["applied_rate"]["verdict"] == "better"
    assert report["delta"]["graph_expansion"]["skipped_rate"]["verdict"] == "better"
    assert report["delta"]["graph_expansion"]["error_rate"]["verdict"] == "better"
    assert report["graph_expansion_counter_compare"]["skip_reasons"]["query_type"]["verdict"] == "better"
    assert report["query_type_compare"]["synthesis"]["delta"]["applied_rate"]["verdict"] == "better"
    assert report["query_type_compare"]["synthesis"]["counter_compare"]["skip_reasons"]["query_type"]["verdict"] == "better"


def test_evaluate_compare_gate_passes_when_applied_lift_justifies_latency_regression():
    report = compare.build_compare_report(
        baseline={
            "latency_ms": {"p95_total_answer_ms": 100.0, "avg_total_answer_ms": 90.0},
            "graph_expansion": {"events_total": 32, "applied_rate": 0.0, "error_rate": 0.0},
        },
        candidate={
            "latency_ms": {"p95_total_answer_ms": 112.0, "avg_total_answer_ms": 95.0},
            "graph_expansion": {"events_total": 32, "applied_rate": 0.45, "error_rate": 0.0},
        },
        baseline_label="off",
        candidate_label="on",
    )
    gate = compare.evaluate_compare_gate(
        report,
        min_events_each=10,
        max_p95_total_answer_regression_pct=5.0,
        min_applied_rate_lift=0.20,
        max_error_rate_increase=0.01,
    )
    assert gate["passed"] is True
    assert gate["checks"]["p95_total_answer_regression"]["justified_by_applied_rate_lift"] is True


def test_evaluate_compare_gate_fails_when_latency_regression_is_not_justified():
    report = compare.build_compare_report(
        baseline={
            "latency_ms": {"p95_total_answer_ms": 100.0, "avg_total_answer_ms": 90.0},
            "graph_expansion": {"events_total": 32, "applied_rate": 0.0, "error_rate": 0.0},
        },
        candidate={
            "latency_ms": {"p95_total_answer_ms": 118.0, "avg_total_answer_ms": 94.0},
            "graph_expansion": {"events_total": 32, "applied_rate": 0.05, "error_rate": 0.0},
        },
        baseline_label="off",
        candidate_label="on",
    )
    gate = compare.evaluate_compare_gate(
        report,
        min_events_each=10,
        max_p95_total_answer_regression_pct=5.0,
        min_applied_rate_lift=0.20,
        max_error_rate_increase=0.01,
    )
    assert gate["passed"] is False
    assert gate["checks"]["p95_total_answer_regression"]["passed"] is False


def test_evaluate_compare_gate_can_fail_on_specific_query_type():
    report = compare.build_compare_report(
        baseline={
            "latency_ms": {"p95_total_answer_ms": 100.0, "avg_total_answer_ms": 90.0},
            "graph_expansion": {
                "events_total": 40,
                "applied_rate": 0.10,
                "error_rate": 0.0,
                "by_query_type": {
                    "synthesis": {"events_total": 20, "applied_rate": 0.10, "error_rate": 0.0},
                },
            },
        },
        candidate={
            "latency_ms": {"p95_total_answer_ms": 108.0, "avg_total_answer_ms": 95.0},
            "graph_expansion": {
                "events_total": 40,
                "applied_rate": 0.35,
                "error_rate": 0.0,
                "by_query_type": {
                    "synthesis": {"events_total": 20, "applied_rate": 0.15, "error_rate": 0.0},
                },
            },
        },
        baseline_label="off",
        candidate_label="on",
    )
    gate = compare.evaluate_compare_gate(
        report,
        min_events_each=10,
        max_p95_total_answer_regression_pct=5.0,
        min_applied_rate_lift=0.20,
        max_error_rate_increase=0.01,
        gate_query_types=["synthesis"],
    )
    assert gate["checks"]["p95_total_answer_regression"]["passed"] is True
    assert gate["query_type_checks"]["synthesis"]["passed"] is False
    assert gate["passed"] is False


def test_evaluate_compare_gate_can_use_stricter_profile_for_query_type():
    report = compare.build_compare_report(
        baseline={
            "latency_ms": {"p95_total_answer_ms": 100.0, "avg_total_answer_ms": 90.0},
            "graph_expansion": {
                "events_total": 60,
                "applied_rate": 0.10,
                "error_rate": 0.0,
                "by_query_type": {
                    "synthesis": {"events_total": 30, "applied_rate": 0.10, "error_rate": 0.0},
                },
            },
        },
        candidate={
            "latency_ms": {"p95_total_answer_ms": 108.0, "avg_total_answer_ms": 94.0},
            "graph_expansion": {
                "events_total": 60,
                "applied_rate": 0.35,
                "error_rate": 0.0,
                "by_query_type": {
                    "synthesis": {"events_total": 30, "applied_rate": 0.25, "error_rate": 0.0},
                },
            },
        },
        baseline_label="off",
        candidate_label="on",
    )
    local_thresholds = compare.resolve_compare_gate_thresholds(profile="local")
    strict_thresholds = compare.resolve_compare_gate_thresholds(profile="strict")
    gate = compare.evaluate_compare_gate(
        report,
        gate_query_types=["synthesis"],
        query_type_threshold_overrides={"synthesis": strict_thresholds},
        **local_thresholds,
    )
    assert gate["passed"] is False
    assert gate["thresholds"]["max_p95_total_answer_regression_pct"] == 10.0
    assert gate["query_type_checks"]["synthesis"]["thresholds"]["max_p95_total_answer_regression_pct"] == 5.0
    assert gate["query_type_checks"]["synthesis"]["checks"]["p95_total_answer_regression"]["passed"] is False


def test_build_summary_from_jsonl_path(tmp_path):
    path = tmp_path / "window.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "synthesis",
                        "latency_ms": {"total_answer_ms": 100.0, "pipeline_ms": 40.0},
                        "graph_expansion": {"ok": True, "graph_expansion_ms": 30.0, "extra_chunk_count": 2},
                    }
                ),
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "qa",
                        "latency_ms": {"total_answer_ms": 120.0, "pipeline_ms": 50.0},
                        "graph_expansion": {"skipped": True, "graph_expansion_ms": 8.0, "reason": "query_type"},
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    summary = compare.build_summary_from_jsonl_path(path, limit_last=None)
    assert summary["request_events_in_window"] == 2
    assert summary["latency_ms"]["p95_total_answer_ms"] == 120.0
    assert summary["graph_expansion"]["applied_total"] == 1
    assert summary["graph_expansion"]["by_query_type"]["qa"]["skip_reasons"] == {"query_type": 1}


def test_main_outputs_json(tmp_path, monkeypatch, capsys):
    base = tmp_path / "base.jsonl"
    cand = tmp_path / "cand.jsonl"
    base.write_text(
        json.dumps(
            {
                "event_type": "request",
                "query_type": "qa",
                "latency_ms": {"total_answer_ms": 140.0, "pipeline_ms": 60.0},
                "graph_expansion": {"skipped": True, "graph_expansion_ms": 9.0, "reason": "query_type"},
            }
        ),
        encoding="utf-8",
    )
    cand.write_text(
        json.dumps(
            {
                "event_type": "request",
                "query_type": "synthesis",
                "latency_ms": {"total_answer_ms": 110.0, "pipeline_ms": 48.0},
                "graph_expansion": {"ok": True, "graph_expansion_ms": 35.0, "extra_chunk_count": 2},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "graph_expansion_compare.py",
            "--baseline-jsonl",
            str(base),
            "--candidate-jsonl",
            str(cand),
            "--baseline-label",
            "off",
            "--candidate-label",
            "on",
            "--json-out",
        ],
    )
    rc = compare.main()
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["baseline_label"] == "off"
    assert payload["candidate_label"] == "on"
    assert payload["delta"]["latency_ms"]["p95_total_answer_ms"]["verdict"] == "better"
    assert payload["query_type_compare"]["qa"]["counter_compare"]["skip_reasons"]["query_type"]["baseline"] == 1.0
    assert payload["query_type_compare"]["synthesis"]["delta"]["applied_rate"]["candidate"] == 1.0


def test_main_enforce_gate_returns_2_on_unjustified_regression(tmp_path, monkeypatch, capsys):
    base = tmp_path / "base.jsonl"
    cand = tmp_path / "cand.jsonl"
    base.write_text(
        json.dumps(
            {
                "event_type": "request",
                "latency_ms": {"total_answer_ms": 100.0, "pipeline_ms": 40.0},
                "graph_expansion": {"skipped": True, "graph_expansion_ms": 2.0, "reason": "feature_disabled"},
            }
        ),
        encoding="utf-8",
    )
    cand.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "request",
                        "latency_ms": {"total_answer_ms": 120.0, "pipeline_ms": 50.0},
                        "graph_expansion": {"ok": True, "graph_expansion_ms": 30.0, "extra_chunk_count": 1},
                    }
                )
                for _ in range(10)
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "graph_expansion_compare.py",
            "--baseline-jsonl",
            str(base),
            "--candidate-jsonl",
            str(cand),
            "--profile",
            "local",
            "--min-events-each",
            "1",
            "--max-p95-total-answer-regression-pct",
            "5",
            "--min-applied-rate-lift",
            "1.1",
            "--enforce-gate",
            "--json-out",
        ],
    )
    rc = compare.main()
    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert payload["compare_gate"]["passed"] is False


def test_main_enforce_gate_can_target_query_type(tmp_path, monkeypatch, capsys):
    base = tmp_path / "base_qt.jsonl"
    cand = tmp_path / "cand_qt.jsonl"
    base.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "synthesis",
                        "latency_ms": {"total_answer_ms": 100.0, "pipeline_ms": 40.0},
                        "graph_expansion": {"ok": True, "graph_expansion_ms": 20.0, "extra_chunk_count": 1},
                    }
                )
                for _ in range(10)
            ]
            + [
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "qa",
                        "latency_ms": {"total_answer_ms": 100.0, "pipeline_ms": 40.0},
                        "graph_expansion": {"skipped": True, "graph_expansion_ms": 8.0, "reason": "query_type"},
                    }
                )
                for _ in range(20)
            ],
        ),
        encoding="utf-8",
    )
    cand.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "synthesis",
                        "latency_ms": {"total_answer_ms": 108.0, "pipeline_ms": 42.0},
                        "graph_expansion": {"ok": True, "graph_expansion_ms": 24.0, "extra_chunk_count": 1},
                    }
                )
                for _ in range(10)
            ]
            + [
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "qa",
                        "latency_ms": {"total_answer_ms": 108.0, "pipeline_ms": 42.0},
                        "graph_expansion": {"ok": True, "graph_expansion_ms": 24.0, "extra_chunk_count": 1},
                    }
                )
                for _ in range(20)
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "graph_expansion_compare.py",
            "--baseline-jsonl",
            str(base),
            "--candidate-jsonl",
            str(cand),
            "--profile",
            "local",
            "--gate-query-type",
            "synthesis",
            "--max-p95-total-answer-regression-pct",
            "5",
            "--min-applied-rate-lift",
            "0.2",
            "--min-events-each",
            "10",
            "--enforce-gate",
            "--json-out",
        ],
    )
    rc = compare.main()
    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert payload["compare_gate_query_types"] == ["synthesis"]
    assert payload["compare_gate"]["query_type_checks"]["synthesis"]["passed"] is False


def test_main_can_use_query_type_profile_without_explicit_gate_query_type(tmp_path, monkeypatch, capsys):
    base = tmp_path / "base_profile.jsonl"
    cand = tmp_path / "cand_profile.jsonl"
    base.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "synthesis",
                        "latency_ms": {"total_answer_ms": 100.0, "pipeline_ms": 40.0},
                        "graph_expansion": {"ok": True, "graph_expansion_ms": 20.0, "extra_chunk_count": 1},
                    }
                )
                for _ in range(30)
            ]
            + [
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "qa",
                        "latency_ms": {"total_answer_ms": 100.0, "pipeline_ms": 40.0},
                        "graph_expansion": {"skipped": True, "graph_expansion_ms": 8.0, "reason": "query_type"},
                    }
                )
                for _ in range(30)
            ]
        ),
        encoding="utf-8",
    )
    cand.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "synthesis",
                        "latency_ms": {"total_answer_ms": 108.0, "pipeline_ms": 42.0},
                        "graph_expansion": {"ok": True, "graph_expansion_ms": 24.0, "extra_chunk_count": 1},
                    }
                )
                for _ in range(30)
            ]
            + [
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "qa",
                        "latency_ms": {"total_answer_ms": 108.0, "pipeline_ms": 42.0},
                        "graph_expansion": {"ok": True, "graph_expansion_ms": 24.0, "extra_chunk_count": 1},
                    }
                )
                for _ in range(30)
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "graph_expansion_compare.py",
            "--baseline-jsonl",
            str(base),
            "--candidate-jsonl",
            str(cand),
            "--profile",
            "local",
            "--gate-query-type-profile",
            "synthesis=strict",
            "--enforce-gate",
            "--json-out",
        ],
    )
    rc = compare.main()
    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert payload["compare_gate_query_types"] == ["synthesis"]
    assert payload["compare_gate_query_type_profiles"] == {"synthesis": "strict"}
    assert payload["compare_gate"]["query_type_checks"]["synthesis"]["thresholds"]["min_applied_rate_lift"] == 0.2


def test_main_can_use_named_preset(tmp_path, monkeypatch, capsys):
    base = tmp_path / "base_preset.jsonl"
    cand = tmp_path / "cand_preset.jsonl"
    base.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "synthesis",
                        "latency_ms": {"total_answer_ms": 100.0, "pipeline_ms": 40.0},
                        "graph_expansion": {"ok": True, "graph_expansion_ms": 20.0, "extra_chunk_count": 1},
                    }
                )
                for _ in range(30)
            ]
            + [
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "learning_plan",
                        "latency_ms": {"total_answer_ms": 100.0, "pipeline_ms": 40.0},
                        "graph_expansion": {"ok": True, "graph_expansion_ms": 22.0, "extra_chunk_count": 1},
                    }
                )
                for _ in range(30)
            ]
        ),
        encoding="utf-8",
    )
    cand.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "synthesis",
                        "latency_ms": {"total_answer_ms": 108.0, "pipeline_ms": 42.0},
                        "graph_expansion": {"ok": True, "graph_expansion_ms": 24.0, "extra_chunk_count": 1},
                    }
                )
                for _ in range(30)
            ]
            + [
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "learning_plan",
                        "latency_ms": {"total_answer_ms": 108.0, "pipeline_ms": 42.0},
                        "graph_expansion": {"ok": True, "graph_expansion_ms": 24.0, "extra_chunk_count": 1},
                    }
                )
                for _ in range(30)
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "graph_expansion_compare.py",
            "--baseline-jsonl",
            str(base),
            "--candidate-jsonl",
            str(cand),
            "--preset",
            "synthesis-strict",
            "--enforce-gate",
            "--json-out",
        ],
    )
    rc = compare.main()
    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert payload["compare_gate_preset"] == "synthesis-strict"
    assert payload["compare_gate_query_types"] == ["synthesis"]
    assert payload["compare_gate_query_type_profiles"] == {"synthesis": "strict"}


def test_main_can_use_dual_preset(tmp_path, monkeypatch, capsys):
    base = tmp_path / "base_dual.jsonl"
    cand = tmp_path / "cand_dual.jsonl"
    base.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "synthesis",
                        "latency_ms": {"total_answer_ms": 100.0, "pipeline_ms": 40.0},
                        "graph_expansion": {"skipped": True, "graph_expansion_ms": 8.0, "reason": "query_type"},
                    }
                )
                for _ in range(10)
            ]
            + [
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "learning_plan",
                        "latency_ms": {"total_answer_ms": 100.0, "pipeline_ms": 40.0},
                        "graph_expansion": {"skipped": True, "graph_expansion_ms": 8.0, "reason": "query_type"},
                    }
                )
                for _ in range(10)
            ]
        ),
        encoding="utf-8",
    )
    cand.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "synthesis",
                        "latency_ms": {"total_answer_ms": 100.0, "pipeline_ms": 40.0},
                        "graph_expansion": {"ok": True, "graph_expansion_ms": 20.0, "extra_chunk_count": 1},
                    }
                )
                for _ in range(10)
            ]
            + [
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "learning_plan",
                        "latency_ms": {"total_answer_ms": 100.0, "pipeline_ms": 40.0},
                        "graph_expansion": {"ok": True, "graph_expansion_ms": 22.0, "extra_chunk_count": 1},
                    }
                )
                for _ in range(10)
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "graph_expansion_compare.py",
            "--baseline-jsonl",
            str(base),
            "--candidate-jsonl",
            str(cand),
            "--preset",
            "dual-local",
            "--enforce-gate",
            "--json-out",
        ],
    )
    rc = compare.main()
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["compare_gate_preset"] == "dual-local"
    assert payload["compare_gate_query_types"] == ["synthesis", "learning_plan"]
    assert payload["compare_gate"]["query_type_checks"]["synthesis"]["passed"] is True
    assert payload["compare_gate"]["query_type_checks"]["learning_plan"]["passed"] is True
