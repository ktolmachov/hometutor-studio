"""Shared pipeline final-step gate logic for hooks and runners."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from pipeline_events import RUN_ID_ENV, emit
from write_set_check import WriteSetResult, check_current_task

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = ROOT / "policies" / "pipeline_gate_policy.yaml"


@dataclass(frozen=True)
class GateContext:
    package_id: str | None = None
    run_id: str | None = None
    root: Path = ROOT
    current_task_path: Path | None = None
    result_path: Path | None = None
    attempt: int = 0
    changed_paths: list[str] | None = None


@dataclass(frozen=True)
class GateVerdict:
    ok: bool
    mode: str
    violations: tuple[str, ...]
    shadow: bool
    followup_message: str = ""


def load_policy(path: Path | str = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _result_is_stale(ctx: GateContext, max_age_seconds: int) -> bool:
    result = ctx.result_path
    if result is None and ctx.run_id:
        result = ctx.root / "logs" / "autonomous_runs" / ctx.run_id / "result.json"
    if result is None or not result.exists():
        return False
    try:
        if (time.time() - result.stat().st_mtime) > max_age_seconds:
            return True
        task_path = ctx.current_task_path or ctx.root / "doc" / "current_task.md"
        if task_path.exists() and result.stat().st_mtime < task_path.stat().st_mtime:
            return True
    except OSError:
        return False
    return False


def _write_set_violations(result: WriteSetResult) -> list[str]:
    if result.missing_write_set:
        return ["current task has no ## Write-Set section"]
    if result.out_of_scope:
        return [
            "write-set drift: "
            + ", ".join(result.out_of_scope[:8])
            + (" ..." if len(result.out_of_scope) > 8 else "")
        ]
    return []


def evaluate(
    ctx: GateContext,
    *,
    policy: Mapping[str, Any] | None = None,
    write_set_result: WriteSetResult | None = None,
    log_event: bool = True,
) -> GateVerdict:
    """Evaluate gate policy. Shadow mode logs but does not block."""
    doc = dict(policy or load_policy())
    mode = str(doc.get("gate_mode", "shadow")).casefold()
    max_retry_attempts = int(doc.get("max_retry_attempts", 1))
    result_freshness_seconds = int(doc.get("result_freshness_seconds", 7200))

    ws_result = write_set_result or check_current_task(
        ctx.current_task_path,
        root=ctx.root,
        changed_paths=ctx.changed_paths,
    )
    violations = _write_set_violations(ws_result)
    if ctx.attempt > max_retry_attempts:
        violations.append(f"retry budget exceeded: attempt={ctx.attempt}")
    if _result_is_stale(ctx, result_freshness_seconds):
        violations.append("result.json is stale")

    shadow = mode != "enforcing"
    ok = not violations or shadow
    followup = ""
    if violations:
        followup = "Pipeline guard found issues:\n" + "\n".join(f"- {v}" for v in violations)
        event_name = "GATE_VIOLATION_SHADOW" if shadow else "GATE_VIOLATION"
        if log_event:
            emit(
                event_name,
                {
                    "package_id": ctx.package_id,
                    "violations": list(violations),
                    "gate_mode": mode,
                },
                run_id=ctx.run_id or os.environ.get(RUN_ID_ENV),
            )

    return GateVerdict(
        ok=ok,
        mode=mode,
        violations=tuple(violations),
        shadow=shadow,
        followup_message=followup,
    )
