import json
import sys

from scripts import check_tutor_regression_gate as gate


def test_run_gate_returns_pass_without_baseline(monkeypatch):
    monkeypatch.setattr(
        "app.eval_service.run_tutor_regression",
        lambda dataset_path="tutor_regression.json", baseline_path=None: (
            "eval_results/tutor_regression_fake.json",
            {
                "summary": {"cases": 3, "avg_tutor_score": 0.8},
                "baseline_comparison": None,
            },
        ),
    )
    report, rc = gate.run_gate(dataset="tutor_regression.json", baseline=None)
    assert rc == 0
    assert report["schema_version"] == gate.GATE_SCHEMA_VERSION
    assert report["status"] == "pass"
    assert report["passed"] is True
    assert report["exit_code"] == 0
    assert report["artifact"]["eval_output_path"] == "eval_results/tutor_regression_fake.json"
    assert report["baseline_comparison"] is None
    assert report["triage"]["next_action"] == "noop"
    assert report["triage"]["rerun_recommended"] is False


def test_run_gate_returns_fail_when_baseline_comparison_failed(monkeypatch):
    monkeypatch.setattr(
        "app.eval_service.run_tutor_regression",
        lambda dataset_path="tutor_regression.json", baseline_path=None: (
            "eval_results/tutor_regression_fake.json",
            {
                "summary": {"cases": 3, "avg_tutor_score": 0.6},
                "baseline_comparison": {"passed": False, "regressions": ["avg_tutor_score"]},
            },
        ),
    )
    report, rc = gate.run_gate(dataset="tutor_regression.json", baseline="eval_data/base.json")
    assert rc == 2
    assert report["status"] == "regression_fail"
    assert report["passed"] is False
    assert report["exit_code"] == 2
    assert report["baseline_comparison"]["passed"] is False
    assert report["triage"]["next_action"] == "fix_baseline_or_tutor_quality"
    assert report["triage"]["owner_hint"] == "tutor_contour_owner"


def test_main_json_out_prints_report(monkeypatch, capsys):
    monkeypatch.setattr(
        gate,
        "run_gate",
        lambda **kwargs: (
            {
                "gate_kind": "tutor_regression",
                "summary": {"cases": 2},
                "baseline_comparison": {"passed": True},
                "passed": True,
            },
            0,
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_tutor_regression_gate.py", "--json-out"],
    )
    rc = gate.main()
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    assert payload["gate_kind"] == "tutor_regression"
    assert payload["passed"] is True


def test_run_gate_returns_infra_error_when_runtime_raises(monkeypatch):
    monkeypatch.setattr(
        "app.eval_service.run_tutor_regression",
        lambda dataset_path="tutor_regression.json", baseline_path=None: (_ for _ in ()).throw(
            ValueError("No embedding data received")
        ),
    )
    report, rc = gate.run_gate(dataset="tutor_regression.json", baseline="eval_data/base.json")
    assert rc == gate.EXIT_INFRA_ERROR
    assert report["status"] == "infra_fail"
    assert report["artifact"]["eval_output_path"] is None
    assert report["exit_code"] == gate.EXIT_INFRA_ERROR
    assert report["error_kind"] == "provider_error"
    assert report["error_type"] == "ValueError"
    assert report["triage"]["next_action"] == "check_provider_keys_quota_policy"
    assert report["triage"]["rerun_recommended"] is True


def test_compute_triage_dependency_missing():
    t = gate.compute_triage(status="infra_fail", error_kind="dependency_missing")
    assert t["next_action"] == "install_missing_dependencies"
    assert t["rerun_recommended"] is False


def test_compute_triage_infra_transient():
    t = gate.compute_triage(status="infra_fail", error_kind="infra_transient")
    assert t["next_action"] == "retry_ci_job"
    assert t["rerun_recommended"] is True


def test_run_gate_infra_dependency_missing(monkeypatch):
    def _throw(*_a, **_k):
        raise ModuleNotFoundError("No module named 'x'")

    monkeypatch.setattr("app.eval_service.run_tutor_regression", _throw)
    report, rc = gate.run_gate(dataset="tutor_regression.json", baseline=None)
    assert rc == gate.EXIT_INFRA_ERROR
    assert report["triage"]["next_action"] == "install_missing_dependencies"
    assert report["error_kind"] == "dependency_missing"


def test_main_report_json_writes_file(monkeypatch, tmp_path):
    monkeypatch.setattr(
        gate,
        "run_gate",
        lambda **kwargs: (
            {
                "schema_version": gate.GATE_SCHEMA_VERSION,
                "gate_kind": "tutor_regression",
                "status": "pass",
                "passed": True,
                "exit_code": 0,
                "artifact": {"eval_output_path": "eval_results/fake.json"},
                "triage": {"next_action": "noop", "owner_hint": "none", "rerun_recommended": False},
            },
            0,
        ),
    )
    report_path = tmp_path / "gate-report.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_tutor_regression_gate.py", "--report-json", str(report_path)],
    )
    rc = gate.main()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert rc == 0
    assert payload["gate_kind"] == "tutor_regression"
    assert payload["artifact"]["eval_output_path"] == "eval_results/fake.json"

