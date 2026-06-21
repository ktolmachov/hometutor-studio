from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

from quality_gates import GateResult


ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = ROOT / ".cursor" / "hooks" / "pipeline_guard.py"


def _load_hook_module():
    spec = importlib.util.spec_from_file_location("pipeline_guard_hook_under_test", HOOK_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_hook_outputs_shared_quality_gate_summary(monkeypatch, capsys) -> None:
    hook = _load_hook_module()
    gate = GateResult(
        name="pipeline_guard",
        ok=False,
        reason="write-set drift",
        followup_message="Pipeline guard found issues:\n- write-set drift",
    )

    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
    monkeypatch.setattr(hook, "_active_ready_package", lambda: "epoch-demo")
    monkeypatch.setattr(hook, "_run_quality_gates", lambda **_: [gate])

    hook.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["followup_message"] == "Pipeline guard found issues:\n- write-set drift"
    assert payload["quality_gates"]["ok"] is False
    assert payload["quality_gates"]["gates"][0]["name"] == "pipeline_guard"


def test_hook_outputs_empty_summary_without_followup(monkeypatch, capsys) -> None:
    hook = _load_hook_module()
    gate = GateResult(name="pipeline_guard", ok=True)

    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
    monkeypatch.setattr(hook, "_active_ready_package", lambda: None)
    monkeypatch.setattr(hook, "_run_quality_gates", lambda **_: [gate])

    hook.main()

    payload = json.loads(capsys.readouterr().out)
    assert "followup_message" not in payload
    assert payload["quality_gates"]["ok"] is True
