"""Structured proof bundle generation and validation for autonomous closures."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline_events import AUTONOMOUS_RUNS_ROOT, RUN_ID_ENV, emit, ensure_run_dir

ROOT = Path(__file__).resolve().parents[1]


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _git_head() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
        )
    except OSError:
        return ""
    return (getattr(result, "stdout", "") or "").strip() if result.returncode == 0 else ""


def _git_diff_sha256() -> str:
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
        )
    except OSError:
        return ""
    text = (getattr(result, "stdout", "") or "") if result.returncode == 0 else ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _artifact(path: Path, kind: str) -> dict[str, str] | None:
    if not path.exists():
        return None
    return {"path": _repo_rel(path), "sha256": _sha256(path), "kind": kind}


def manifest_path(run_id: str) -> Path:
    return ensure_run_dir(run_id) / "proof_bundle" / "manifest.json"


def _sync_event_log_checksum_in_manifest(run_id: str) -> None:
    """Update event_log artifact hash in an existing manifest (event_log may grow after first build)."""
    path = manifest_path(run_id)
    if not path.exists():
        return
    run_dir = ensure_run_dir(run_id)
    ev_path = run_dir / "event_log.jsonl"
    if not ev_path.exists():
        return
    try:
        manifest: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return
    new_sha = _sha256(ev_path)
    updated = False
    for item in artifacts:
        if isinstance(item, dict) and item.get("kind") == "event_log":
            item["sha256"] = new_sha
            item["path"] = _repo_rel(ev_path)
            updated = True
            break
    if not updated:
        return
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def build(run_id: str, package_id: str) -> Path:
    """Build logs/autonomous_runs/<run_id>/proof_bundle/manifest.json."""
    run_dir = ensure_run_dir(run_id)
    artifacts: list[dict[str, str]] = []
    candidates = [
        (ROOT / "archive" / "team_artifacts" / package_id / "execution_contract.md", "execution_contract"),
        (ROOT / "archive" / "team_artifacts" / package_id / "dod_cache.json", "dod_cache"),
        (run_dir / "event_log.jsonl", "event_log"),
        (run_dir / "pipeline_state.json", "pipeline_state"),
        (run_dir / "result.json", "result"),
    ]
    for path, kind in candidates:
        item = _artifact(path, kind)
        if item is not None:
            artifacts.append(item)

    manifest = {
        "run_id": run_id,
        "package_id": package_id,
        "generated_at": _utc_iso(),
        "artifacts": artifacts,
        "git": {"head_sha": _git_head(), "diff_sha256": _git_diff_sha256()},
    }
    path = manifest_path(run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def validate(
    package_id: str,
    *,
    run_id: str | None = None,
    env: dict[str, str] | None = None,
) -> tuple[bool, str]:
    """Validate manifest artifact checksums, emitting PROOF_* events on failure."""
    source_env = env if env is not None else os.environ
    rid = (run_id or source_env.get(RUN_ID_ENV) or "").strip()
    if not rid:
        emit("PROOF_MISSING", {"package_id": package_id, "reason": "missing run_id"}, env={})
        return False, "missing run_id"

    _sync_event_log_checksum_in_manifest(rid)

    path = manifest_path(rid)
    if not path.exists():
        emit("PROOF_MISSING", {"package_id": package_id, "reason": "missing manifest"}, run_id=rid)
        return False, "missing proof_bundle/manifest.json"

    try:
        manifest: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        emit("PROOF_TAMPERED", {"package_id": package_id, "reason": "invalid manifest json"}, run_id=rid)
        return False, "invalid manifest json"

    for key in ("run_id", "package_id", "generated_at", "artifacts", "git"):
        if key not in manifest:
            emit("PROOF_TAMPERED", {"package_id": package_id, "reason": f"missing {key}"}, run_id=rid)
            return False, f"manifest missing {key}"
    if manifest.get("run_id") != rid or manifest.get("package_id") != package_id:
        emit("PROOF_TAMPERED", {"package_id": package_id, "reason": "identity mismatch"}, run_id=rid)
        return False, "manifest identity mismatch"

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        emit("PROOF_TAMPERED", {"package_id": package_id, "reason": "artifacts not list"}, run_id=rid)
        return False, "manifest artifacts must be a list"

    for item in artifacts:
        if not isinstance(item, dict):
            emit("PROOF_TAMPERED", {"package_id": package_id, "reason": "bad artifact"}, run_id=rid)
            return False, "bad artifact entry"
        rel = item.get("path")
        expected = item.get("sha256")
        if not isinstance(rel, str) or not isinstance(expected, str):
            emit("PROOF_TAMPERED", {"package_id": package_id, "reason": "bad artifact fields"}, run_id=rid)
            return False, "bad artifact fields"
        artifact_path = ROOT / rel
        if not artifact_path.exists() or _sha256(artifact_path) != expected:
            emit("PROOF_TAMPERED", {"package_id": package_id, "reason": rel}, run_id=rid)
            return False, f"artifact checksum mismatch: {rel}"

    return True, "ok"
