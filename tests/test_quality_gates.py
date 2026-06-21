from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from quality_gates import GateResult, blocking_results, run_all, summarize


def test_run_all_returns_named_gate_results(tmp_path: Path) -> None:
    task = tmp_path / "doc" / "current_task.md"
    task.parent.mkdir(parents=True)
    task.write_text("## Write-Set\n- app/demo.py\n", encoding="utf-8")

    results = run_all(
        package_id="epoch-demo",
        root=tmp_path,
        include_proof=False,
    )

    assert [r.name for r in results] == ["pipeline_guard"]
    assert results[0].ok is True


def test_run_all_uses_explicit_current_task_path(tmp_path: Path) -> None:
    task = tmp_path / "custom_task.md"
    task.write_text("## Write-Set\n- app/demo.py\n", encoding="utf-8")

    results = run_all(
        package_id="epoch-demo",
        root=tmp_path,
        current_task_path=task,
        include_proof=False,
    )

    assert results[0].ok is True


def test_run_all_can_include_proof_validator(tmp_path: Path) -> None:
    results = run_all(
        package_id="epoch-demo",
        run_id="run-1",
        root=tmp_path,
        proof_validator=lambda package_id, run_id=None: (False, f"{package_id}:{run_id}:missing"),
    )

    proof = [r for r in results if r.name == "proof_bundle"][0]
    assert proof.ok is False
    assert proof.reason == "epoch-demo:run-1:missing"


def test_gate_matrix_summary_separates_shadow_from_blockers() -> None:
    results = [
        GateResult(name="pipeline_guard", ok=True, reason="write-set drift", shadow=True),
        GateResult(name="proof_bundle", ok=False, reason="missing manifest"),
    ]

    summary = summarize(results)

    assert summary["ok"] is False
    assert summary["blocker_count"] == 1
    assert summary["shadow_count"] == 1
    assert blocking_results(results) == [results[1]]
    assert summary["gates"][1]["blocking"] is True
