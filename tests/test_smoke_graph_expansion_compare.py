import json
import sys

from scripts import smoke_graph_expansion_compare as smoke_compare


def _load_json_from_stdout(text: str) -> dict:
    start = text.find("{")
    assert start >= 0
    return json.loads(text[start:])


def test_smoke_compare_main_generates_off_and_on(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "smoke_graph_expansion_compare.py",
            "--out-dir",
            str(tmp_path),
            "--requests",
            "10",
            "--json-out",
        ],
    )
    rc = smoke_compare.main()
    payload = _load_json_from_stdout(capsys.readouterr().out)
    assert rc == 0
    assert payload["baseline_smoke"]["graph_mode"] == "off"
    assert payload["candidate_smoke"]["graph_mode"] == "on"
    compare = payload["compare"]
    assert compare["baseline"]["graph_expansion"]["applied_rate"] == 0.0
    assert compare["candidate"]["graph_expansion"]["applied_rate"] > 0.0
    assert compare["delta"]["graph_expansion"]["applied_rate"]["verdict"] == "better"
    assert compare["query_type_compare"]["synthesis"]["delta"]["applied_rate"]["verdict"] == "better"
    assert compare["compare_gate"]["passed"] is True


def test_smoke_compare_enforce_gate_returns_2_when_thresholds_are_too_strict(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "smoke_graph_expansion_compare.py",
            "--out-dir",
            str(tmp_path),
            "--requests",
            "10",
            "--profile",
            "local",
            "--max-p95-total-answer-regression-pct",
            "1",
            "--min-applied-rate-lift",
            "0.95",
            "--enforce-gate",
            "--json-out",
        ],
    )
    rc = smoke_compare.main()
    payload = _load_json_from_stdout(capsys.readouterr().out)
    assert rc == 2
    assert payload["compare"]["compare_gate"]["passed"] is False


def test_smoke_compare_accepts_gate_query_type(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "smoke_graph_expansion_compare.py",
            "--out-dir",
            str(tmp_path),
            # Ниже 20 synthesis-событий в окне gate по synthesis часто не проходит compare_gate
            "--requests",
            "20",
            "--gate-query-type",
            "synthesis",
            "--json-out",
        ],
    )
    rc = smoke_compare.main()
    payload = _load_json_from_stdout(capsys.readouterr().out)
    assert rc == 0
    assert payload["compare"]["compare_gate_query_types"] == ["synthesis"]
    assert payload["compare"]["compare_gate"]["query_type_checks"]["synthesis"]["passed"] is True


def test_smoke_compare_accepts_query_type_profile(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "smoke_graph_expansion_compare.py",
            "--out-dir",
            str(tmp_path),
            "--requests",
            "10",
            "--gate-query-type-profile",
            "synthesis=strict",
            "--json-out",
        ],
    )
    rc = smoke_compare.main()
    payload = _load_json_from_stdout(capsys.readouterr().out)
    assert rc == 0
    assert payload["compare"]["compare_gate_query_types"] == ["synthesis"]
    assert payload["compare"]["compare_gate_query_type_profiles"] == {"synthesis": "strict"}
    assert payload["compare"]["compare_gate"]["query_type_checks"]["synthesis"]["thresholds"]["min_applied_rate_lift"] == 0.2


def test_smoke_compare_accepts_named_preset_and_custom_query_types(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "smoke_graph_expansion_compare.py",
            "--out-dir",
            str(tmp_path),
            "--requests",
            "8",
            "--preset",
            "learning-plan-local",
            "--query-types",
            "synthesis,learning_plan",
            "--json-out",
        ],
    )
    rc = smoke_compare.main()
    payload = _load_json_from_stdout(capsys.readouterr().out)
    assert rc == 0
    assert payload["baseline_smoke"]["query_types"] == ["synthesis", "learning_plan"]
    assert payload["compare"]["compare_gate_preset"] == "learning-plan-local"
    assert payload["compare"]["compare_gate_query_types"] == ["learning_plan"]
