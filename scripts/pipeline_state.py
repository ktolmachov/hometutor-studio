"""Atomic pipeline_state.json updates under logs/autonomous_runs/<run_id>/."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline_events import AUTONOMOUS_RUNS_ROOT, ensure_run_dir


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _record_snapshot(run_id: str, event_name: str, state_path: Path) -> None:
    try:
        from run_recorder import record_state_snapshot

        record_state_snapshot(run_id, event_name, state_path=state_path)
    except OSError:
        raise


def bootstrap(
    run_id: str,
    *,
    package_id: str | None,
    initial_phase: str,
    chain_step: int = 0,
) -> None:
    """Create or refresh baseline pipeline_state for a new top-level invocation."""
    ensure_run_dir(run_id)
    path = AUTONOMOUS_RUNS_ROOT / run_id / "pipeline_state.json"
    existing: dict[str, Any] = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    base = {
        "run_id": run_id,
        "package_id": package_id,
        "phase": initial_phase,
        "attempt": int(existing.get("attempt", 0)),
        "last_event_id": str(existing.get("last_event_id", "")),
        "proof_status": existing.get("proof_status", "missing"),
        # Persist chain_step so post_agent can recover it even when argv is stale.
        "chain_step": max(chain_step, int(existing.get("chain_step", 0))),
        "updated_at": _utc_iso(),
    }
    _atomic_write_json(path, base)
    _record_snapshot(run_id, "phase_change", path)


def update(run_id: str, **fields: Any) -> None:
    """Merge fields into pipeline_state.json (atomic replace)."""
    ensure_run_dir(run_id)
    path = AUTONOMOUS_RUNS_ROOT / run_id / "pipeline_state.json"
    data: dict[str, Any] = {
        "package_id": None,
        "phase": "execution",
        "attempt": 0,
        "chain_step": 0,
        "last_event_id": "",
        "proof_status": "missing",
    }
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                data.update(existing)
        except json.JSONDecodeError:
            pass
    data.update({k: v for k, v in fields.items() if v is not None})
    data["run_id"] = run_id
    data.setdefault("attempt", 0)
    data.setdefault("chain_step", 0)
    data.setdefault("last_event_id", "")
    data.setdefault("proof_status", "missing")
    data["updated_at"] = _utc_iso()
    _atomic_write_json(path, data)
    event_name = str(fields.get("last_event_id") or fields.get("phase") or "state_update")
    _record_snapshot(run_id, event_name, path)


def read_chain_step(run_id: str) -> int:
    """Read persisted chain_step from pipeline_state.json for the given run.

    Returns 0 if not found or unreadable (safe default — does not block progress).
    Called from post_agent to recover the accurate chain_step when the argv-embedded
    value is stale (e.g. agent re-ran with a footer command from an earlier iteration).
    """
    path = AUTONOMOUS_RUNS_ROOT / run_id / "pipeline_state.json"
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return int(data.get("chain_step", 0))
    except (json.JSONDecodeError, TypeError, ValueError):
        return 0


def finalize_for_exit(run_id: str, *, exit_code: int) -> None:
    """Mark terminal phase from process exit code."""
    ensure_run_dir(run_id)
    path = AUTONOMOUS_RUNS_ROOT / run_id / "pipeline_state.json"
    data: dict[str, Any] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    else:
        data = {
            "package_id": None,
            "attempt": 0,
            "last_event_id": "",
            "proof_status": "missing",
        }
    data["run_id"] = run_id
    data["phase"] = "closed" if exit_code == 0 else "failed"
    data.setdefault("attempt", 0)
    data.setdefault("last_event_id", "")
    data.setdefault("proof_status", "missing")
    data["updated_at"] = _utc_iso()
    _atomic_write_json(path, data)
    _record_snapshot(run_id, str(data["phase"]), path)
