"""Durable run directories, collision-safe run_id, and PID registry for autonomous pipeline."""

from __future__ import annotations

import json
import os
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, MutableMapping

from failure_classifier import classify_exit_code

ROOT = Path(__file__).resolve().parents[1]
AUTONOMOUS_RUNS_ROOT = ROOT / "logs" / "autonomous_runs"
CURRENT_DIR = AUTONOMOUS_RUNS_ROOT / "current"
ORPHAN_DIR = AUTONOMOUS_RUNS_ROOT / "_orphan"
RUN_ID_ENV = "HOME_RAG_RUN_ID"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_pid_alive(pid: int) -> bool:
    """Best-effort: True if process `pid` appears to be running."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            SYNCHRONIZE = 0x00100000
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(
                SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, False, pid
            )
            if not handle:
                return False
            try:
                WAIT_OBJECT_0 = 0
                WAIT_TIMEOUT = 0x00000102
                ret = kernel32.WaitForSingleObject(handle, 0)
                return ret == WAIT_TIMEOUT
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def get_or_create_run_id(
    env: MutableMapping[str, str] | None = None,
) -> str:
    """Reuse HOME_RAG_RUN_ID if set; otherwise ms timestamp + hex suffix (exported to env)."""
    target = env if env is not None else os.environ
    existing = (target.get(RUN_ID_ENV) or "").strip()
    if existing:
        return existing
    rid = f"{int(time.time() * 1000)}-{secrets.token_hex(3)}"
    target[RUN_ID_ENV] = rid
    return rid


def ensure_run_dir(run_id: str | None) -> Path:
    """Per-run workspace, or the orphan directory when no correlation id exists."""
    if run_id is None or not str(run_id).strip():
        ORPHAN_DIR.mkdir(parents=True, exist_ok=True)
        return ORPHAN_DIR
    d = AUTONOMOUS_RUNS_ROOT / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def orphan_log_path_today() -> Path:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ORPHAN_DIR.mkdir(parents=True, exist_ok=True)
    return ORPHAN_DIR / f"{day}.jsonl"


def emit_orphan_event(payload: dict[str, Any]) -> None:
    """Append one JSON line when no run correlation is available (manual tooling)."""
    line = json.dumps({"ts": _utc_iso(), **payload}, ensure_ascii=False)
    path = orphan_log_path_today()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def emit(
    event: str,
    payload: Mapping[str, Any] | None = None,
    *,
    run_id: str | None = None,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Append an event to a run log, falling back to the orphan log if no run id exists."""
    source_env = env if env is not None else os.environ
    resolved_run_id = (run_id or source_env.get(RUN_ID_ENV) or "").strip()
    record = {
        "ts": _utc_iso(),
        "event": event,
        **dict(payload or {}),
    }
    if not resolved_run_id:
        path = orphan_log_path_today()
    else:
        path = ensure_run_dir(resolved_run_id) / "event_log.jsonl"
        record["run_id"] = resolved_run_id
    line = json.dumps(record, ensure_ascii=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return path


def write_pid_registry(
    run_id: str,
    pid: int,
    *,
    package_id: str | None = None,
) -> None:
    CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "pid": pid,
        "package_id": package_id,
        "started_at": _utc_iso(),
    }
    path = CURRENT_DIR / f"{pid}.json"
    _atomic_write_json(path, payload)


def cleanup_stale_pid_registrations() -> None:
    """Remove current/<pid>.json entries for dead processes."""
    if not CURRENT_DIR.is_dir():
        return
    for p in CURRENT_DIR.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            pid = int(data.get("pid", -1))
        except (OSError, ValueError, json.JSONDecodeError):
            try:
                p.unlink()
            except OSError:
                pass
            continue
        if not is_pid_alive(pid):
            try:
                p.unlink()
            except OSError:
                pass


def current_runs(*, package_id: str | None = None) -> list[dict[str, Any]]:
    """Return live PID registry entries, newest first; stale/corrupt entries are removed."""
    cleanup_stale_pid_registrations()
    if not CURRENT_DIR.is_dir():
        return []
    entries: list[dict[str, Any]] = []
    for p in CURRENT_DIR.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            pid = int(data.get("pid", -1))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if not is_pid_alive(pid):
            continue
        if package_id is not None and data.get("package_id") != package_id:
            continue
        data["pid"] = pid
        entries.append(data)
    return sorted(entries, key=lambda item: str(item.get("started_at", "")), reverse=True)


def _atomic_write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def write_run_result(
    *,
    run_id: str,
    exit_code: int,
    package_id: str | None = None,
    argv: list[str] | None = None,
) -> None:
    """Write logs/autonomous_runs/<run_id>/result.json (atomic)."""
    ensure_run_dir(run_id)
    payload: dict[str, Any] = {
        "run_id": run_id,
        "exit_code": exit_code,
        "failure_class": classify_exit_code(exit_code).as_dict(),
        "finished_at": _utc_iso(),
        "package_id": package_id,
        "argv": list(argv) if argv is not None else [],
    }
    _atomic_write_json(AUTONOMOUS_RUNS_ROOT / run_id / "result.json", payload)


def load_schema_required_keys(relative_name: str) -> set[str]:
    """Load `required` array from repo schema (tests only)."""
    path = ROOT / "schemas" / relative_name
    doc = json.loads(path.read_text(encoding="utf-8"))
    return set(doc.get("required", []))
