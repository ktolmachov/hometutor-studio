from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_evaluation_contract.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("validate_evaluation_contract", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_valid_example_contract_passes() -> None:
    module = _load_module()
    path = ROOT / "doc" / "team_workflow" / "examples" / "ssr_level2_eval_contract_example.yaml"
    assert module.validate_file(path) == []


def test_missing_primary_metric_fails() -> None:
    module = _load_module()
    contract = {
        "evaluation_contract": {
            "feature": "Synthetic",
            "owner_decision": "proposed",
            "metrics": {
                "primary": {"type": "offline_eval", "baseline": "0", "target": "1", "test_set": "fixture"},
                "secondary": [{"name": "latency_p95", "target": "< 1s"}],
            },
            "test_harness": {"script": "tests/eval/test_x.py", "data": "tests/eval/x.json", "command": "pytest"},
            "success_criteria": ["passes"],
            "failure_plan": [{"condition": "miss", "action": "iterate"}],
            "fallback": {"mode": "rule_based", "trigger": "miss", "user_visible_trace": "baseline"},
        }
    }
    errors = module.validate_contract(contract)
    assert "missing or empty: evaluation_contract.metrics.primary.name" in errors


def test_cli_returns_nonzero_for_invalid_contract(tmp_path: Path) -> None:
    module = _load_module()
    path = tmp_path / "bad.yaml"
    path.write_text("evaluation_contract:\n  feature: Bad\n", encoding="utf-8")
    assert module.main([str(path)]) == 2
