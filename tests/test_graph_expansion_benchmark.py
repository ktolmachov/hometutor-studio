import json
import sys

from scripts import graph_expansion_benchmark as benchmark


def test_normalize_graph_expansion_summary_derives_rates():
    result = benchmark.normalize_graph_expansion_summary(
        {
            "events_total": 4,
            "applied_total": 2,
            "skipped_total": 1,
            "error_total": 1,
            "unknown_outcome_total": 0,
            "skip_reasons": {"query_type": 1},
            "error_types": {"runtimeerror": 1},
            "by_query_type": {
                "synthesis": {
                    "events_total": 2,
                    "applied_total": 2,
                    "skipped_total": 0,
                    "error_total": 0,
                    "unknown_outcome_total": 0,
                }
            },
        }
    )
    assert result["applied_rate"] == 0.5
    assert result["skipped_rate"] == 0.25
    assert result["error_rate"] == 0.25
    assert result["unknown_outcome_rate"] == 0.0
    assert result["skip_reasons"] == {"query_type": 1}
    assert result["error_types"] == {"runtimeerror": 1}
    assert result["by_query_type"]["synthesis"]["applied_rate"] == 1.0


def test_evaluate_quality_gate_marks_failed_checks():
    gate = benchmark.evaluate_quality_gate(
        {
            "events_total": 4,
            "applied_total": 1,
            "skipped_total": 2,
            "error_total": 1,
            "p95_graph_expansion_ms": 48.0,
            "avg_extra_chunks_when_applied": 1.0,
        },
        min_events=3,
        max_p95_ms=40.0,
        min_applied_rate=0.4,
        max_error_rate=0.2,
        min_avg_extra_chunks=1.5,
    )
    assert gate["configured"] is True
    assert gate["passed"] is False
    assert {item["metric"] for item in gate["failed_checks"]} == {
        "p95_graph_expansion_ms",
        "applied_rate",
        "error_rate",
        "avg_extra_chunks_when_applied",
    }


def test_main_jsonl_returns_exit_code_2_on_gate_failure(tmp_path, monkeypatch, capsys):
    path = tmp_path / "metrics_store.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "synthesis",
                        "graph_expansion": {"ok": True, "graph_expansion_ms": 60.0, "extra_chunk_count": 1},
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "event_type": "request",
                        "query_type": "qa",
                        "graph_expansion": {"skipped": True, "graph_expansion_ms": 10.0, "reason": "query_type"},
                    },
                    ensure_ascii=False,
                ),
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "graph_expansion_benchmark.py",
            "--jsonl",
            str(path),
            "--max-p95-ms",
            "50",
            "--json-out",
        ],
    )

    rc = benchmark.main()
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert rc == 2
    assert payload["quality_gate"]["passed"] is False
    assert payload["graph_expansion"]["p95_graph_expansion_ms"] == 60.0
    assert payload["graph_expansion"]["by_query_type"]["qa"]["skip_reasons"] == {"query_type": 1}
