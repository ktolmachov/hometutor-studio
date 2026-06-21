import json
import sys

from scripts import smoke_tutor_regression_gate as smoke_gate


def test_generate_tutor_regression_smoke_baseline_writes_file(monkeypatch, tmp_path):
    source = tmp_path / "source_baseline.json"
    source.write_text(
        json.dumps(
            {
                "summary": {"avg_tutor_score": 0.71, "avg_latency_sec": 0.9},
                "dataset_version": "v-test",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    target = tmp_path / "baseline.json"
    result = smoke_gate.generate_tutor_regression_smoke_baseline(
        baseline_path=str(target),
        mode="healthy",
        source_baseline_path=str(source),
    )
    assert result["mode"] == "healthy"
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["summary"]["avg_tutor_score"] == 0.71


def test_main_healthy_pass(monkeypatch, capsys, tmp_path):
    baseline_file = tmp_path / "smoke.json"
    monkeypatch.setattr(
        smoke_gate,
        "generate_tutor_regression_smoke_baseline",
        lambda **kwargs: {"baseline_path": str(baseline_file), "mode": "healthy"},
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["smoke_tutor_regression_gate.py", "--mode", "healthy", "--json-out"],
    )
    rc = smoke_gate.main()
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    assert payload["expectation"]["matched"] is True
    assert payload["expectation"]["actual_rc"] == 0
    assert payload["diagnostic_summary"]["result_label"] == "healthy_pass"
    assert payload["diagnostic_summary"]["gate_status"] == "pass"
    assert payload["diagnostic_summary"]["recommended_next_action"] == "noop"
    assert payload["gate"]["triage"]["next_action"] == "noop"


def test_main_degraded_fail(monkeypatch, capsys, tmp_path):
    baseline_file = tmp_path / "smoke.json"
    monkeypatch.setattr(
        smoke_gate,
        "generate_tutor_regression_smoke_baseline",
        lambda **kwargs: {"baseline_path": str(baseline_file), "mode": "degraded"},
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["smoke_tutor_regression_gate.py", "--mode", "degraded", "--json-out"],
    )
    rc = smoke_gate.main()
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    assert payload["expectation"]["matched"] is True
    assert payload["expectation"]["actual_rc"] == 2
    assert payload["diagnostic_summary"]["result_label"] == "degraded_expected_fail"
    assert payload["diagnostic_summary"]["gate_status"] == "regression_fail"
    assert payload["diagnostic_summary"]["recommended_next_action"] == "fix_baseline_or_tutor_quality"


def test_main_online_mode_calls_run_gate(monkeypatch, capsys, tmp_path):
    baseline_file = tmp_path / "smoke.json"
    monkeypatch.setattr(
        smoke_gate,
        "generate_tutor_regression_smoke_baseline",
        lambda **kwargs: {"baseline_path": str(baseline_file), "mode": "healthy"},
    )
    monkeypatch.setattr(
        "scripts.check_tutor_regression_gate.run_gate",
        lambda **kwargs: (
            {
                "status": "pass",
                "baseline_comparison": {"passed": True},
                "summary": {"cases": 5},
                "passed": True,
            },
            0,
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["smoke_tutor_regression_gate.py", "--mode", "healthy", "--no-offline", "--json-out"],
    )
    rc = smoke_gate.main()
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    assert payload["gate"]["summary"]["cases"] == 5
    assert payload["diagnostic_summary"]["offline"] is False
    assert payload["gate"]["triage"]["next_action"] == "noop"


def test_build_smoke_diagnostic_summary_for_unexpected_outcome():
    summary = smoke_gate.build_smoke_diagnostic_summary(
        mode="healthy",
        gate_report={"status": "infra_fail", "error_kind": "provider_error"},
        expected_rc=0,
        actual_rc=3,
        expectation_ok=False,
        offline=False,
    )
    assert summary["result_label"] == "unexpected_outcome"
    assert summary["gate_status"] == "infra_fail"
    assert summary["gate_error_kind"] == "provider_error"
