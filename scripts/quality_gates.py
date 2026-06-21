"""Unified quality gate facade for autonomous pipeline pre-closure checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from pipeline_guard_logic import GateContext, evaluate as evaluate_pipeline_guard
from proof_bundle import validate as validate_proof_bundle


@dataclass(frozen=True)
class GateResult:
    name: str
    ok: bool
    reason: str = ""
    shadow: bool = False
    followup_message: str = ""

    @property
    def is_blocking(self) -> bool:
        """True when this gate should stop a runner."""
        return not self.ok and not self.shadow

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "ok": self.ok,
            "reason": self.reason,
            "shadow": self.shadow,
            "blocking": self.is_blocking,
            "followup_message": self.followup_message,
        }


def blocking_results(results: list[GateResult]) -> list[GateResult]:
    """Return only gates that should block the caller."""
    return [result for result in results if result.is_blocking]


def summarize(results: list[GateResult]) -> dict[str, object]:
    """Build a JSON-friendly quality gate matrix summary."""
    blockers = blocking_results(results)
    shadow_findings = [
        result
        for result in results
        if result.shadow and (not result.ok or result.reason or result.followup_message)
    ]
    return {
        "ok": not blockers,
        "blocker_count": len(blockers),
        "shadow_count": len(shadow_findings),
        "gates": [result.as_dict() for result in results],
    }


def run_all(
    *,
    package_id: str | None,
    run_id: str | None = None,
    root: Path | None = None,
    current_task_path: Path | None = None,
    include_proof: bool = True,
    proof_validator: Callable[..., tuple[bool, str]] = validate_proof_bundle,
) -> list[GateResult]:
    """Run the current pre-closure gate matrix.

    The matrix is intentionally additive: callers can inspect results without
    changing legacy exit-code behavior until they opt into enforcement.
    """
    guard_ctx = GateContext(
        package_id=package_id,
        run_id=run_id,
        root=root or GateContext().root,
        current_task_path=current_task_path,
    )
    guard = evaluate_pipeline_guard(guard_ctx)
    results = [
        GateResult(
            name="pipeline_guard",
            ok=guard.ok,
            reason="; ".join(guard.violations),
            shadow=guard.shadow,
            followup_message=guard.followup_message,
        )
    ]
    if include_proof and run_id:
        ok, reason = proof_validator(package_id, run_id=run_id)
        results.append(GateResult(name="proof_bundle", ok=ok, reason=reason))
    return results
