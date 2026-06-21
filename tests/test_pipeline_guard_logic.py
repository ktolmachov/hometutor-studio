from __future__ import annotations

import json
import os
import time
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from pipeline_guard_logic import GateContext, evaluate
from write_set_check import WriteSetResult


def test_shadow_mode_logs_only(tmp_path: Path, monkeypatch) -> None:
    import pipeline_events as pe

    ar = tmp_path / "logs" / "autonomous_runs"
    monkeypatch.setattr(pe, "AUTONOMOUS_RUNS_ROOT", ar)
    monkeypatch.setattr(pe, "CURRENT_DIR", ar / "current")
    monkeypatch.setattr(pe, "ORPHAN_DIR", ar / "_orphan")

    verdict = evaluate(
        GateContext(package_id="epoch-demo", run_id="run-1", root=tmp_path),
        policy={"gate_mode": "shadow", "max_retry_attempts": 1},
        write_set_result=WriteSetResult((), ("app/a.py",), ("app/a.py",), True),
    )

    assert verdict.ok is True
    assert verdict.shadow is True
    assert verdict.violations
    event_log = ar / "run-1" / "event_log.jsonl"
    assert "GATE_VIOLATION_SHADOW" in event_log.read_text(encoding="utf-8")


def test_enforcing_mode_blocks_same_state(tmp_path: Path) -> None:
    verdict = evaluate(
        GateContext(package_id="epoch-demo", run_id="run-2", root=tmp_path),
        policy={"gate_mode": "enforcing", "max_retry_attempts": 1},
        write_set_result=WriteSetResult((), ("app/a.py",), ("app/a.py",), True),
        log_event=False,
    )

    assert verdict.ok is False
    assert verdict.shadow is False


def test_result_stale_violation(tmp_path: Path) -> None:
    task = tmp_path / "doc" / "current_task.md"
    task.parent.mkdir(parents=True)
    task.write_text("## Write-Set\n- app/a.py\n", encoding="utf-8")
    result = tmp_path / "result.json"
    result.write_text(json.dumps({"exit_code": 0}), encoding="utf-8")
    old = time.time() - 10
    os.utime(result, (old, old))

    verdict = evaluate(
        GateContext(
            package_id="epoch-demo",
            root=tmp_path,
            current_task_path=task,
            result_path=result,
            changed_paths=["app/a.py"],
        ),
        policy={"gate_mode": "enforcing", "result_freshness_seconds": 7200},
        log_event=False,
    )

    assert verdict.ok is False
    assert "result.json is stale" in verdict.violations


def test_retry_budget_violation_blocks_in_enforcing_mode(tmp_path: Path) -> None:
    verdict = evaluate(
        GateContext(
            package_id="epoch-demo",
            root=tmp_path,
            attempt=2,
            changed_paths=["app/a.py"],
        ),
        policy={"gate_mode": "enforcing", "max_retry_attempts": 1},
        write_set_result=WriteSetResult(("app/a.py",), (), ("app/a.py",), False),
        log_event=False,
    )

    assert verdict.ok is False
    assert "retry budget exceeded: attempt=2" in verdict.violations


def test_write_set_drift_violation_blocks_in_enforcing_mode(tmp_path: Path) -> None:
    verdict = evaluate(
        GateContext(package_id="epoch-demo", root=tmp_path),
        policy={"gate_mode": "enforcing", "max_retry_attempts": 1},
        write_set_result=WriteSetResult(("app/a.py",), ("app/b.py",), ("app/a.py", "app/b.py"), False),
        log_event=False,
    )

    assert verdict.ok is False
    assert any("write-set drift" in violation for violation in verdict.violations)


def test_write_set_parser_accepts_generated_prompt_section() -> None:
    from write_set_check import parse_write_set

    prompt = """Implement epoch-demo only.

## Write-Set
- `app/demo.py`
- `tests/test_demo.py`

Do not touch anything else.
"""

    assert parse_write_set(prompt) == ["app/demo.py", "tests/test_demo.py"]
