from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "kilo_budget_gate.py"


def _load_gate_module():
    spec = importlib.util.spec_from_file_location("kilo_budget_gate_test", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_evaluate_launcher_uses_staged_snapshot_outside_dry_run(monkeypatch):
    gate = _load_gate_module()

    monkeypatch.setattr(gate, "_git_show", lambda ref, path: "HEAD launcher" if ref == "HEAD" else None)

    candidate_calls: list[bool] = []

    def fake_read_candidate(path: str, *, dry_run: bool):
        candidate_calls.append(dry_run)
        return ("STAGED launcher", "staged")

    monkeypatch.setattr(gate, "_read_candidate", fake_read_candidate)

    fixture = {"messages": [], "tools": [], "model": "test-model"}
    row = gate.evaluate_launcher("planning", "doc/team_workflow/generate_plan_next_prompt.md", fixture, gate.GuardThresholds(), dry_run=False)

    assert candidate_calls == [False]
    assert row["candidate_source"] == "staged"
    assert row["head"]["launcher_chars"] == len("HEAD launcher")
    assert row["work"]["launcher_chars"] == len("STAGED launcher")


def test_evaluate_launcher_uses_worktree_snapshot_in_dry_run(monkeypatch):
    gate = _load_gate_module()

    monkeypatch.setattr(gate, "_git_show", lambda ref, path: "HEAD launcher" if ref == "HEAD" else None)
    monkeypatch.setattr(gate, "_read_candidate", lambda path, *, dry_run: ("WORKTREE launcher", "worktree"))

    fixture = {"messages": [], "tools": [], "model": "test-model"}
    row = gate.evaluate_launcher("planning", "doc/team_workflow/generate_plan_next_prompt.md", fixture, gate.GuardThresholds(), dry_run=True)

    assert row["candidate_source"] == "worktree"
    assert row["work"]["launcher_chars"] == len("WORKTREE launcher")


def test_main_uses_staged_fixture_snapshot_for_json_mode(monkeypatch, capsys):
    gate = _load_gate_module()

    monkeypatch.setattr(gate, "preflight", lambda: [])
    monkeypatch.setattr(gate, "_get_staged_files", lambda: ["fixtures/kilo_injection_baseline.json"])

    def fake_read_candidate(path: str, *, dry_run: bool):
        if path == "fixtures/kilo_injection_baseline.json":
            return (
                json.dumps({"messages": [{"role": "system", "content": "fixture from index"}], "tools": [], "model": "test-model"}),
                "staged",
            )
        return ("launcher from index", "staged")

    monkeypatch.setattr(gate, "_read_candidate", fake_read_candidate)
    monkeypatch.setattr(gate, "_git_show", lambda ref, path: "launcher from head" if ref == "HEAD" else None)

    exit_code = gate.main(["--json"])
    assert exit_code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["fixture_source"] == "staged"
    assert payload["fixture_authority"] in {"captured_relay_fixture", "legacy_calibrated_baseline"}
    assert payload["budget_sensitive_staged"] == ["fixtures/kilo_injection_baseline.json"]
    assert payload["launchers"][0]["candidate_source"] == "staged"


def test_evaluate_launcher_marks_dependency_only_trigger(monkeypatch):
    gate = _load_gate_module()

    monkeypatch.setattr(gate, "_git_show", lambda ref, path: "launcher text")
    monkeypatch.setattr(gate, "_read_candidate", lambda path, *, dry_run: ("launcher text", "staged"))
    fixture = {"messages": [], "tools": [], "model": "test-model"}

    row = gate.evaluate_launcher(
        "planning",
        "doc/team_workflow/generate_plan_next_prompt.md",
        fixture,
        gate.GuardThresholds(),
        dry_run=False,
        staged_files=["scripts/_kilo_guard.py"],
    )

    assert row["trigger_reason"] == "dependency_only"
