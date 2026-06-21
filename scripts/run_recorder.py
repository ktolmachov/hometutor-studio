"""Append-only recorder for autonomous run state transitions."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pipeline_events import AUTONOMOUS_RUNS_ROOT, emit, ensure_run_dir


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_").lower()
    return slug or "state"


def _next_seq(snapshot_dir: Path) -> int:
    max_seen = 0
    if snapshot_dir.is_dir():
        for path in snapshot_dir.glob("*.json"):
            prefix = path.name.split("_", 1)[0]
            if prefix.isdigit():
                max_seen = max(max_seen, int(prefix))
    return max_seen + 1


def record_state_snapshot(
    run_id: str,
    event_name: str,
    *,
    state_path: Path | None = None,
) -> Path:
    """Copy pipeline_state.json into state_snapshots/{seq}_{event}.json and log it."""
    run_dir = ensure_run_dir(run_id)
    source = state_path or AUTONOMOUS_RUNS_ROOT / run_id / "pipeline_state.json"
    if not source.exists():
        raise FileNotFoundError(source)

    snapshot_dir = run_dir / "state_snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    seq = _next_seq(snapshot_dir)
    snapshot = snapshot_dir / f"{seq:04d}_{_slug(event_name)}.json"

    state = json.loads(source.read_text(encoding="utf-8"))
    snapshot.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    emit(
        event_name,
        {
            "snapshot": str(snapshot.relative_to(run_dir)).replace("\\", "/"),
            "seq": seq,
        },
        run_id=run_id,
    )
    return snapshot


def load_snapshots(run_id: str) -> list[dict[str, Any]]:
    """Load snapshots in replay order."""
    snapshot_dir = AUTONOMOUS_RUNS_ROOT / run_id / "state_snapshots"
    snapshots: list[dict[str, Any]] = []
    if not snapshot_dir.is_dir():
        return snapshots
    for path in sorted(snapshot_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        snapshots.append({"path": path, "state": data})
    return snapshots


def build_replay_manifest(run_id: str) -> dict[str, Any]:
    """Build a structural replay manifest from current run artifacts."""
    run_dir = ensure_run_dir(run_id)
    snapshots = load_snapshots(run_id)
    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "event_log": str(run_dir / "event_log.jsonl"),
        "snapshots": [
            {
                "path": str(item["path"]),
                "phase": item["state"].get("phase"),
                "updated_at": item["state"].get("updated_at"),
            }
            for item in snapshots
        ],
    }


def validate_replay_manifest(manifest: dict[str, Any]) -> list[str]:
    """Minimal schema validation without an external jsonschema dependency."""
    errors: list[str] = []
    if not isinstance(manifest.get("run_id"), str) or not manifest["run_id"]:
        errors.append("run_id must be a non-empty string")
    snapshots = manifest.get("snapshots")
    if not isinstance(snapshots, list):
        errors.append("snapshots must be a list")
        return errors
    for idx, item in enumerate(snapshots, start=1):
        if not isinstance(item, dict):
            errors.append(f"snapshots[{idx}] must be an object")
            continue
        path = item.get("path")
        if not isinstance(path, str) or not Path(path).exists():
            errors.append(f"snapshots[{idx}].path must point to an existing file")
    return errors
