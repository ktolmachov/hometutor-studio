import json
import sys

from scripts import smoke_graph_expansion_gate as smoke_gate


def test_generate_graph_expansion_smoke_events_creates_jsonl(tmp_path):
    path = tmp_path / "graph_smoke.jsonl"
    result = smoke_gate.generate_graph_expansion_smoke_events(jsonl_path=path, request_count=4)
    assert result["request_count"] == 4
    assert result["query_types"] == ["synthesis", "learning_plan"]
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 4
    payloads = [json.loads(line) for line in lines]
    assert all(item["event_type"] == "request" for item in payloads)
    assert any(item.get("graph_expansion", {}).get("ok") is True for item in payloads)
    assert {item.get("query_type") for item in payloads} == {"synthesis", "learning_plan"}


def test_generate_graph_expansion_smoke_events_off_mode_creates_skipped_trace(tmp_path):
    path = tmp_path / "graph_smoke_off.jsonl"
    result = smoke_gate.generate_graph_expansion_smoke_events(jsonl_path=path, request_count=4, graph_mode="off")
    assert result["graph_mode"] == "off"
    payloads = [json.loads(line) for line in path.read_text(encoding="utf-8").strip().splitlines()]
    assert all(item.get("graph_expansion", {}).get("skipped") is True for item in payloads)
    assert all(item.get("graph_expansion", {}).get("reason") == "feature_disabled" for item in payloads)


def test_generate_graph_expansion_smoke_events_supports_custom_query_types(tmp_path):
    path = tmp_path / "graph_smoke_custom.jsonl"
    result = smoke_gate.generate_graph_expansion_smoke_events(
        jsonl_path=path,
        request_count=4,
        query_types="synthesis,qa",
    )
    assert result["query_types"] == ["synthesis", "qa"]
    payloads = [json.loads(line) for line in path.read_text(encoding="utf-8").strip().splitlines()]
    assert {item.get("query_type") for item in payloads} == {"synthesis", "qa"}
    assert any(item.get("graph_expansion", {}).get("ok") is True for item in payloads)
    qa_items = [item for item in payloads if item.get("query_type") == "qa"]
    assert qa_items
    assert all(item.get("graph_expansion", {}).get("reason") == "query_type" for item in qa_items)


def test_smoke_main_runs_gate(tmp_path, monkeypatch, capsys):
    path = tmp_path / "graph_smoke.jsonl"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "smoke_graph_expansion_gate.py",
            "--jsonl-out",
            str(path),
            "--requests",
            "10",
            "--profile",
            "local",
            "--json-out",
        ],
    )
    rc = smoke_gate.main()
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    assert payload["smoke"]["request_count"] == 10
    assert payload["gate"]["quality_gate"]["passed"] is True
    assert payload["gate"]["graph_expansion"]["events_total"] == 10


def test_smoke_main_strict_profile_auto_expands_requests(tmp_path, monkeypatch, capsys):
    """Strict gate: без этого тест гоняет ≥30 HTTP /ask (STRICT min_events). Для скорости CI — override порога."""
    path = tmp_path / "graph_smoke_strict.jsonl"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "smoke_graph_expansion_gate.py",
            "--jsonl-out",
            str(path),
            "--profile",
            "strict",
            # Иначе max(default requests 12, STRICT min_events 30) → 30 вызовов TestClient
            "--min-events",
            "12",
            "--requests",
            "12",
            "--json-out",
        ],
    )
    rc = smoke_gate.main()
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    assert payload["smoke"]["request_count"] == 12
    assert payload["gate"]["quality_gate"]["passed"] is True
    assert payload["gate"]["graph_expansion"]["events_total"] == 12
