import json

from scripts import check_graph_expansion_gate as gate


def test_resolve_thresholds_uses_profile_defaults():
    local = gate.resolve_thresholds(profile="local")
    strict = gate.resolve_thresholds(profile="strict")
    assert local["min_events"] == 10
    assert strict["min_events"] == 30
    assert strict["max_error_rate"] < local["max_error_rate"]


def test_run_gate_returns_fail_for_strict_profile(tmp_path):
    path = tmp_path / "metrics_store.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "request",
                        "graph_expansion": {"ok": True, "graph_expansion_ms": 70.0, "extra_chunk_count": 1},
                    }
                )
                for _ in range(12)
            ]
        ),
        encoding="utf-8",
    )
    report, rc = gate.run_gate(jsonl_path=path, limit=0, profile="strict")
    assert rc == 2
    assert report["quality_gate"]["passed"] is False
    assert any(item["metric"] == "min_events" or item["metric"] == "events_total" for item in report["quality_gate"]["checks"])


def test_run_gate_returns_pass_for_local_profile(tmp_path):
    path = tmp_path / "metrics_store.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "request",
                        "graph_expansion": {"ok": True, "graph_expansion_ms": 40.0, "extra_chunk_count": 2},
                    }
                )
                for _ in range(12)
            ]
        ),
        encoding="utf-8",
    )
    report, rc = gate.run_gate(jsonl_path=path, limit=0, profile="local")
    assert rc == 0
    assert report["quality_gate"]["passed"] is True
    assert report["graph_expansion"]["applied_rate"] == 1.0
