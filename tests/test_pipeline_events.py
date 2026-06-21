"""Tests for collision-safe run_id, run dirs, PID registry, orphan log."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


@pytest.fixture()
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Redirect autonomous logs under tmp_path."""
    import pipeline_events as pe

    fake_root = tmp_path / "repo"
    fake_root.mkdir()
    pe.ROOT = fake_root
    pe.AUTONOMOUS_RUNS_ROOT = fake_root / "logs" / "autonomous_runs"
    pe.CURRENT_DIR = pe.AUTONOMOUS_RUNS_ROOT / "current"
    pe.ORPHAN_DIR = pe.AUTONOMOUS_RUNS_ROOT / "_orphan"
    monkeypatch.chdir(fake_root)
    return pe


def test_get_or_create_run_id_reuses_existing(isolated_env):
    pe = isolated_env
    env = {"HOME_RAG_RUN_ID": "preset-abc"}
    assert pe.get_or_create_run_id(env) == "preset-abc"


def test_get_or_create_run_id_collision_resistant(isolated_env):
    pe = isolated_env
    seen: set[str] = set()
    for _ in range(40):
        env: dict[str, str] = {}
        rid = pe.get_or_create_run_id(env)
        assert rid not in seen
        seen.add(rid)
        assert env["HOME_RAG_RUN_ID"] == rid
        assert "-" in rid


def test_ensure_run_dir_and_result(isolated_env):
    pe = isolated_env
    rid = "test-run-1"
    d = pe.ensure_run_dir(rid)
    assert d.is_dir()
    pe.write_run_result(run_id=rid, exit_code=0, package_id=None, argv=["a", "b"])
    result_path = d / "result.json"
    data = json.loads(result_path.read_text(encoding="utf-8"))
    req = json.loads((ROOT / "schemas" / "pipeline_result.schema.json").read_text(encoding="utf-8"))[
        "required"
    ]
    for k in req:
        assert k in data
    assert data["failure_class"]["name"] == "success"


def test_orphan_emit_appends_jsonl(isolated_env):
    pe = isolated_env
    pe.emit_orphan_event({"event": "unit-test", "n": 1})
    path = pe.orphan_log_path_today()
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert lines
    last = json.loads(lines[-1])
    assert last["event"] == "unit-test"


def test_emit_falls_back_to_orphan_without_run_id(isolated_env):
    pe = isolated_env
    path = pe.emit("PROOF_MISSING", {"package_id": "epoch-demo"}, env={})
    assert path.parent == pe.ORPHAN_DIR
    last = json.loads(path.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert last["event"] == "PROOF_MISSING"
    assert "run_id" not in last


def test_emit_writes_run_event_log_with_run_id(isolated_env):
    pe = isolated_env
    path = pe.emit("phase_change", {"phase": "post_agent"}, run_id="rid-1")
    assert path == pe.AUTONOMOUS_RUNS_ROOT / "rid-1" / "event_log.jsonl"
    last = json.loads(path.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert last["event"] == "phase_change"
    assert last["run_id"] == "rid-1"


def test_pid_registry_cleanup_removes_dead_pid(isolated_env, monkeypatch: pytest.MonkeyPatch):
    pe = isolated_env
    pe.CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    dead = 999_001_999
    fake_file = pe.CURRENT_DIR / f"{dead}.json"
    fake_file.write_text(
        json.dumps({"run_id": "x", "pid": dead, "package_id": None, "started_at": "t"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(pe, "is_pid_alive", lambda _pid: False)
    pe.cleanup_stale_pid_registrations()
    assert not fake_file.exists()


def test_current_runs_filters_stale_and_package(isolated_env, monkeypatch: pytest.MonkeyPatch):
    pe = isolated_env
    pe.write_pid_registry("run-a", 101, package_id="epoch-a")
    pe.write_pid_registry("run-b", 202, package_id="epoch-b")
    monkeypatch.setattr(pe, "is_pid_alive", lambda pid: pid == 202)

    entries = pe.current_runs(package_id="epoch-b")

    assert [entry["run_id"] for entry in entries] == ["run-b"]
    assert not (pe.CURRENT_DIR / "101.json").exists()


def test_pipeline_state_bootstrap_and_finalize(isolated_env, monkeypatch: pytest.MonkeyPatch):
    pe = isolated_env
    sys.path.insert(0, str(SCRIPTS))
    import pipeline_state as ps

    monkeypatch.setattr(ps, "AUTONOMOUS_RUNS_ROOT", pe.AUTONOMOUS_RUNS_ROOT)
    monkeypatch.setattr(ps, "ensure_run_dir", pe.ensure_run_dir)

    rid = "state-1"
    ps.bootstrap(rid, package_id="epoch-demo", initial_phase="execution")
    st_path = pe.AUTONOMOUS_RUNS_ROOT / rid / "pipeline_state.json"
    st = json.loads(st_path.read_text(encoding="utf-8"))
    req = json.loads((ROOT / "schemas" / "pipeline_state.schema.json").read_text(encoding="utf-8"))[
        "required"
    ]
    for k in req:
        assert k in st
    ps.finalize_for_exit(rid, exit_code=0)
    st2 = json.loads(st_path.read_text(encoding="utf-8"))
    assert st2["phase"] == "closed"
    ps.finalize_for_exit(rid, exit_code=3)
    st3 = json.loads(st_path.read_text(encoding="utf-8"))
    assert st3["phase"] == "failed"


def test_pipeline_state_update_creates_required_defaults(isolated_env, monkeypatch: pytest.MonkeyPatch):
    pe = isolated_env
    sys.path.insert(0, str(SCRIPTS))
    import pipeline_state as ps

    monkeypatch.setattr(ps, "AUTONOMOUS_RUNS_ROOT", pe.AUTONOMOUS_RUNS_ROOT)
    monkeypatch.setattr(ps, "ensure_run_dir", pe.ensure_run_dir)

    ps.update("state-2", package_id="epoch-demo", last_event_id="evt-1")
    st_path = pe.AUTONOMOUS_RUNS_ROOT / "state-2" / "pipeline_state.json"
    st = json.loads(st_path.read_text(encoding="utf-8"))
    req = json.loads((ROOT / "schemas" / "pipeline_state.schema.json").read_text(encoding="utf-8"))[
        "required"
    ]
    for k in req:
        assert k in st
    assert st["phase"] == "execution"
    assert st["last_event_id"] == "evt-1"
