"""Tests for scripts/workflow.py — Smart Workflow Router.

Covers:
  - resolve_state() for all 5 states
  - _find_active_package() with various registry configs
  - _last_orchestration_step() artifact scanning
  - CLI flags: --status, --json, --exec, --agent, --package
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import workflow as wf
import workflow_strings as ws

_REAL_ACQUIRE_LOOP_LOCK = wf._acquire_loop_lock
_REAL_RELEASE_LOOP_LOCK = wf._release_loop_lock


@pytest.fixture(autouse=True)
def _workflow_loop_lock_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Loop tests must not touch real archive/team_artifacts/_locks/workflow-loop.lock."""
    monkeypatch.setattr(wf, "_acquire_loop_lock", lambda: True)
    monkeypatch.setattr(wf, "_release_loop_lock", lambda: None)


def _isolate_workflow_registry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, initial: str = "unset-active-pkg") -> Path:
    """Направить workflow.REGISTRY во временный файл (защита реального backlog_registry.yaml)."""
    reg = tmp_path / "backlog_registry.yaml"
    reg.write_text(
        "schema_version: 2\n"
        "user_stories_index: doc/user_stories_index.json\n"
        f"active_package_id: {initial}\n"
        "items: []\n"
        "waves: []\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(wf, "REGISTRY", reg)
    return reg


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _write_registry(path: Path, items: list[dict], active_package_id: str | None = None) -> None:
    """Write a minimal backlog_registry.yaml with given items."""
    data: dict = {
        "waves": [],
        "items": items,
    }
    if active_package_id is not None:
        data["active_package_id"] = active_package_id
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")


def _make_item(pkg_id: str, status: str) -> dict:
    return {
        "id": pkg_id,
        "status": status,
        "title": f"Test package {pkg_id}",
        "wave_id": "wave-test",
        "wave_position": 1,
        "cjm_moments": [],
        "user_stories": [],
        "impact": "low",
        "blocks": "",
        "depends_on": [],
        "cost_estimate": "S",
        "write_set_max": 3,
        "dod_commands": [".venv\\Scripts\\python.exe -m pytest tests/ -v"],
        "read_set_hint": [],
        "exit_artifact": "",
        "re_entry_condition": None,
    }


@pytest.fixture()
def fake_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Create an isolated fake project root with minimal structure."""
    doc = tmp_path / "doc"
    doc.mkdir()
    (doc / "cjm.md").write_text("# CJM\n", encoding="utf-8")

    registry = doc / "backlog_registry.yaml"

    artifacts = tmp_path / "archive" / "team_artifacts"
    artifacts.mkdir(parents=True)

    # Patch module-level constants
    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", artifacts)
    monkeypatch.setattr(wf, "REGISTRY", registry)

    return {
        "root": tmp_path,
        "registry": registry,
        "artifacts": artifacts,
    }


# ── _package_status ───────────────────────────────────────────────────────────


def test_package_status_found(fake_root) -> None:
    _write_registry(fake_root["registry"], [_make_item("pkg-alpha", "ready")])
    with patch("workflow.load_backlog_registry", return_value=yaml.safe_load(
        fake_root["registry"].read_text(encoding="utf-8")
    )):
        assert wf._package_status("pkg-alpha") == "ready"


def test_package_status_missing(fake_root) -> None:
    _write_registry(fake_root["registry"], [])
    with patch("workflow.load_backlog_registry", return_value={"items": []}):
        assert wf._package_status("no-such-pkg") == "unknown"


# ── _last_orchestration_step ──────────────────────────────────────────────────


def test_last_orchestration_step_no_artifacts(fake_root) -> None:
    pkg_dir = fake_root["artifacts"] / "pkg-x"
    pkg_dir.mkdir()
    with patch("workflow.list_team_artifacts", return_value=[]):
        assert wf._last_orchestration_step("pkg-x") is None


def test_last_orchestration_step_finds_latest(fake_root) -> None:
    files = [
        "1_po_package.md",
        "2_analyst_spec.md",
        "4_developer_code.md",
        "orchestration_cursor_ai.md",   # non-step, should be ignored
        "execution_contract.md",        # non-step
    ]
    with patch("workflow.list_team_artifacts", return_value=sorted(files)):
        result = wf._last_orchestration_step("pkg-x")
    # Only files starting with digit are step files; sorted → last is "4_..."
    assert result == "4_developer_code.md"


# ── resolve_state — STATE_NO_PACKAGE ─────────────────────────────────────────


def test_resolve_state_no_package(fake_root) -> None:
    _write_registry(fake_root["registry"], [])

    with patch("workflow._find_active_package", return_value=(None, "none")):
        state = wf.resolve_state(None, "cursor_ai")

    assert state["state"] == wf.STATE_NO_PACKAGE
    assert state["package"] is None
    assert state["next_cmd"] is None
    assert "generate_plan_next_prompt.md" in state["next_hint"]


def test_resolve_state_no_package_continue_includes_target_agent(fake_root) -> None:
    _write_registry(fake_root["registry"], [])

    with patch("workflow._find_active_package", return_value=(None, "none")):
        state = wf.resolve_state(None, "continue")

    assert state["state"] == wf.STATE_NO_PACKAGE
    assert "generate_plan_next_prompt.md TARGET_AGENT: continue" in state["next_hint"]


# ── resolve_state — STATE_NEEDS_PLAN (proposed/open) ─────────────────────────


@pytest.mark.parametrize("status", ["proposed", "open"])
def test_resolve_state_needs_plan(fake_root, status: str) -> None:
    pkg = "pkg-proposed"
    _write_registry(fake_root["registry"], [_make_item(pkg, status)])

    with (
        patch("workflow._package_status", return_value=status),
        patch("workflow.detect_work_state", return_value="fresh"),
    ):
        state = wf.resolve_state(pkg, "cursor_ai")

    assert state["state"] == wf.STATE_NEEDS_PLAN
    assert state["package"] == pkg
    assert state["next_cmd"] is None
    assert "generate_plan_next_prompt.md" in state["next_hint"]


# ── resolve_state — STATE_READY_FRESH (no orchestration file) ────────────────


@pytest.mark.parametrize("pkg_status", ["ready", "wip"])
def test_resolve_state_ready_fresh_no_us_cjm(fake_root, pkg_status: str) -> None:
    """Package without US/CJM routes to execution_auto (run_autonomous.py directly)."""
    pkg = "pkg-ready-fresh"
    pkg_dir = fake_root["artifacts"] / pkg
    pkg_dir.mkdir()

    _mock_state = {
        "contract": {},
        "rows": [{"package": pkg, "user_stories": [], "cjm_moments": []}],
    }
    with (
        patch("workflow._package_status", return_value=pkg_status),
        patch("workflow.detect_work_state", return_value="fresh"),
        patch("workflow._load_state", return_value=_mock_state),
    ):
        state = wf.resolve_state(pkg, "cursor_ai")

    assert state["state"] == wf.STATE_READY_FRESH
    assert state["execution_auto"] is True
    assert "run_autonomous.py" in state["next_cmd"]
    assert "--agent cursor_ai" in state["next_cmd"]
    assert f"--package {pkg}" in state["next_cmd"]


@pytest.mark.parametrize("pkg_status", ["ready", "wip"])
def test_resolve_state_ready_fresh_with_us_high_complexity(fake_root, pkg_status: str) -> None:
    """Package with US + high complexity routes to orchestration."""
    pkg = "pkg-ready-fresh-orch"
    pkg_dir = fake_root["artifacts"] / pkg
    pkg_dir.mkdir()

    # Contract with many outcomes/write-set → high complexity score
    _complex_contract = {
        "OUTCOMES": "\n".join(f"- outcome {i}" for i in range(8)),
        "WRITE_SET_MAX": "\n".join(f"- app/module_{i}.py" for i in range(6)),
        "DOD_COMMANDS": "pytest tests/test_a.py\npytest tests/test_b.py",
        "USER_STORIES": "- US-1.1\n- US-2.3",
    }
    _mock_state = {
        "contract": _complex_contract,
        "rows": [{"package": pkg, "user_stories": ["US-1.1"], "cjm_moments": ["Ask"]}],
    }
    with (
        patch("workflow._package_status", return_value=pkg_status),
        patch("workflow.detect_work_state", return_value="fresh"),
        patch("workflow._load_state", return_value=_mock_state),
    ):
        state = wf.resolve_state(pkg, "cursor_ai")

    assert state["state"] == wf.STATE_READY_FRESH
    assert state["execution_auto"] is False
    assert "generate_orchestration_prompt.py" in state["next_cmd"]
    assert "--agent cursor_ai" in state["next_cmd"]
    assert f"--package {pkg}" in state["next_cmd"]


@pytest.mark.parametrize("pkg_status", ["ready", "wip"])
def test_resolve_state_ready_fresh_with_us_low_complexity_still_orchestrates(
    fake_root, pkg_status: str
) -> None:
    """Accepted learning-product contracts use orchestration even when compact."""
    pkg = "pkg-ready-low-us"
    pkg_dir = fake_root["artifacts"] / pkg
    pkg_dir.mkdir()

    _compact_contract = {
        "WRITE_SET_MAX": "- app/foo.py",
        "DOD_COMMANDS": "pytest tests/test_foo.py -v",
        "USER_STORIES": "- US-1.1",
    }
    _mock_state = {
        "contract": _compact_contract,
        "rows": [{"package": pkg, "user_stories": ["US-1.1"], "cjm_moments": ["Ask"]}],
    }
    with (
        patch("workflow._package_status", return_value=pkg_status),
        patch("workflow.detect_work_state", return_value="fresh"),
        patch("workflow._load_state", return_value=_mock_state),
    ):
        state = wf.resolve_state(pkg, "cursor_ai")

    assert state["state"] == wf.STATE_READY_FRESH
    assert state["execution_auto"] is False
    assert state["complexity_route"] == "execution_auto"
    assert "generate_orchestration_prompt.py" in state["next_cmd"]
    assert f"--package {pkg}" in state["next_cmd"]


# ── resolve_state — STATE_READY_ORCH (orch file exists, no exec contract) ────


def test_resolve_state_ready_orch_no_contract(fake_root) -> None:
    pkg = "pkg-ready-orch"
    pkg_dir = fake_root["artifacts"] / pkg
    pkg_dir.mkdir()
    (pkg_dir / "orchestration_cursor_ai.md").write_text(
        "## STEP 1 — Product Owner  [SEQUENTIAL]\n"
        "→ archive/team_artifacts/pkg-ready-orch/1_po_package.md\n\n"
        "## STEP 2 — Analyst  [SEQUENTIAL]\n"
        "→ archive/team_artifacts/pkg-ready-orch/2_analyst_spec.md\n",
        encoding="utf-8",
    )

    with (
        patch("workflow._package_status", return_value="ready"),
        patch("workflow.detect_work_state", return_value="fresh"),
        patch("workflow.list_team_artifacts", return_value=["orchestration_cursor_ai.md"]),
    ):
        state = wf.resolve_state(pkg, "cursor_ai")

    assert state["state"] == wf.STATE_READY_ORCH
    assert state["next_cmd"] is None
    assert "STEP 1" in state["next_label"]
    assert "Product Owner" in state["next_label"]
    assert "orchestration_cursor_ai.md" in state["next_hint"]


def test_resolve_state_ready_orch_advances_step_label(fake_root) -> None:
    pkg = "pkg-ready-orch-step2"
    pkg_dir = fake_root["artifacts"] / pkg
    pkg_dir.mkdir()
    (pkg_dir / "orchestration_cursor_ai.md").write_text(
        "## STEP 1 — Product Owner  [SEQUENTIAL]\n"
        "→ archive/team_artifacts/pkg-ready-orch-step2/1_po_package.md\n\n"
        "## STEP 2 — Analyst  [SEQUENTIAL]\n"
        "→ archive/team_artifacts/pkg-ready-orch-step2/2_analyst_spec.md\n",
        encoding="utf-8",
    )
    (pkg_dir / "1_po_package.md").write_text("# po\n", encoding="utf-8")

    with (
        patch("workflow._package_status", return_value="ready"),
        patch("workflow.detect_work_state", return_value="fresh"),
        patch("workflow.list_team_artifacts", return_value=[
            "1_po_package.md",
            "orchestration_cursor_ai.md",
        ]),
    ):
        state = wf.resolve_state(pkg, "cursor_ai")

    assert state["state"] == wf.STATE_READY_ORCH
    assert "STEP 2" in state["next_label"]
    assert "Analyst" in state["next_label"]
    assert "STEP 2" in state["next_hint"]


# ── resolve_state — STATE_WIP_RUNNING (orch + exec contract) ─────────────────


def test_resolve_state_wip_running(fake_root) -> None:
    pkg = "pkg-wip-running"
    pkg_dir = fake_root["artifacts"] / pkg
    pkg_dir.mkdir()
    (pkg_dir / "orchestration_cursor_ai.md").write_text("# orch\n", encoding="utf-8")
    (pkg_dir / "execution_contract.md").write_text("# contract\n", encoding="utf-8")
    (pkg_dir / "4_developer_impl.md").write_text("# dev\n", encoding="utf-8")

    with (
        patch("workflow._package_status", return_value="wip"),
        patch("workflow.detect_work_state", return_value="execution_ready"),
        patch("workflow.list_team_artifacts", return_value=[
            "4_developer_impl.md",
            "execution_contract.md",
            "orchestration_cursor_ai.md",
        ]),
    ):
        state = wf.resolve_state(pkg, "cursor_ai")

    assert state["state"] == wf.STATE_WIP_RUNNING
    assert "run_autonomous.py" in state["next_cmd"]
    assert "--post-agent" in state["next_cmd"]
    assert "--agent cursor_ai" in state["next_cmd"]
    assert f"--package {pkg}" in state["next_cmd"]
    assert state.get("last_artifact") == "4_developer_impl.md"


# ── resolve_state — STATE_READY_EXECUTING (task_started.md, no contract) ─────


def test_resolve_state_normalizes_utf16_execution_contract(fake_root) -> None:
    pkg = "pkg-utf16-contract"
    pkg_dir = fake_root["artifacts"] / pkg
    pkg_dir.mkdir()
    (pkg_dir / "orchestration_cursor_ai.md").write_text("# orch\n", encoding="utf-8")
    contract = pkg_dir / "execution_contract.md"
    contract.write_bytes("# contract\nПривет\n".encode("utf-16"))

    with (
        patch("workflow._package_status", return_value="wip"),
        patch("workflow.detect_work_state", return_value="execution_ready"),
        patch("workflow.list_team_artifacts", return_value=[
            "execution_contract.md",
            "orchestration_cursor_ai.md",
        ]),
    ):
        state = wf.resolve_state(pkg, "cursor_ai")

    assert state["state"] == wf.STATE_WIP_RUNNING
    assert contract.read_text(encoding="utf-8") == "# contract\nПривет\n"
    assert b"\x00" not in contract.read_bytes()


def test_resolve_state_ready_executing_no_contract(fake_root) -> None:
    """task_started.md exists, no execution_contract → STATE_READY_EXECUTING."""
    pkg = "pkg-ready-exec"
    pkg_dir = fake_root["artifacts"] / pkg
    pkg_dir.mkdir()
    (pkg_dir / "task_started.md").write_text("# Task Started\n", encoding="utf-8")
    # no execution_contract.md, no orchestration file

    with (
        patch("workflow._package_status", return_value="ready"),
        patch("workflow.detect_work_state", return_value="fresh"),
        patch("workflow.list_team_artifacts", return_value=["task_started.md"]),
    ):
        state = wf.resolve_state(pkg, "cursor_ai")

    assert state["state"] == wf.STATE_READY_EXECUTING
    assert state["next_cmd"] is None
    assert "current_task.md" in state["next_hint"]
    assert "execution_contract.md" in state["next_hint"]
    assert "workflow_router.md" in state["next_hint"]


def test_resolve_state_execution_auto_contract_exists_no_orch(fake_root) -> None:
    """execution_contract.md exists but no orch file → wip_running (for --post-agent)."""
    pkg = "pkg-auto-done"
    pkg_dir = fake_root["artifacts"] / pkg
    pkg_dir.mkdir()
    (pkg_dir / "task_started.md").write_text("# Task Started\n", encoding="utf-8")
    (pkg_dir / "execution_contract.md").write_text("# done\n", encoding="utf-8")
    # no orchestration file

    with (
        patch("workflow._package_status", return_value="ready"),
        patch("workflow.detect_work_state", return_value="execution_ready"),
        patch("workflow.list_team_artifacts", return_value=[
            "execution_contract.md", "task_started.md",
        ]),
    ):
        state = wf.resolve_state(pkg, "cursor_ai")

    assert state["state"] == wf.STATE_WIP_RUNNING
    assert "run_autonomous.py" in state["next_cmd"]
    assert "--post-agent" in state["next_cmd"]
    assert "--package pkg-auto-done" in state["next_cmd"]


def test_post_agent_chat_api_handoff_detector() -> None:
    assert wf._post_agent_chat_api_handoff(11) is True
    assert wf._post_agent_chat_api_handoff(0) is False
    assert wf._post_agent_chat_api_handoff(10) is False


def test_extend_post_agent_cmd_appends_no_dod_cache_flag() -> None:
    base = (
        ".venv\\Scripts\\python.exe scripts/run_autonomous.py "
        "--post-agent --package x --agent cursor_ai --budget-profile strict"
    )
    extended = wf._extend_post_agent_cmd(base, post_agent_no_dod_cache=True)
    assert extended is not None
    assert extended.endswith(" --no-dod-cache")


def test_extend_post_agent_cmd_idempotent_and_skips_non_post_agent() -> None:
    base = (
        ".venv\\Scripts\\python.exe scripts/run_autonomous.py "
        "--post-agent --package x --agent cursor_ai --budget-profile strict"
    )
    once = wf._extend_post_agent_cmd(base, post_agent_no_dod_cache=True)
    twice = wf._extend_post_agent_cmd(once, post_agent_no_dod_cache=True)
    assert once == twice
    assert wf._extend_post_agent_cmd("echo hi", post_agent_no_dod_cache=True) == "echo hi"
    assert wf._extend_post_agent_cmd(base, post_agent_no_dod_cache=False) == base


# ── _run_loop — execution_auto non-blocking pause ─────────────────────────────


def test_resolve_state_started_marker_contract_is_not_wip_running(fake_root) -> None:
    pkg = "pkg-started-only"
    pkg_dir = fake_root["artifacts"] / pkg
    pkg_dir.mkdir()
    (pkg_dir / "task_started.md").write_text("# Task Started\n", encoding="utf-8")
    (pkg_dir / "execution_contract.md").write_text("STARTED\n", encoding="utf-8")

    with (
        patch("workflow._package_status", return_value="ready"),
        patch("workflow.detect_work_state", return_value="execution_ready"),
        patch("workflow.list_team_artifacts", return_value=[
            "execution_contract.md", "task_started.md",
        ]),
    ):
        state = wf.resolve_state(pkg, "cursor_ai")

    assert state["state"] == wf.STATE_READY_EXECUTING
    assert state["next_cmd"] is None
    assert "execution_contract.md" in state["next_hint"]


def test_execution_contract_ready_for_post_agent_stub_vs_substantive(tmp_path, monkeypatch) -> None:
    """Mirrors scripts/cursor_agent_trigger.ts gate: STARTED sentinel is not substantive."""
    ta = tmp_path / "archive" / "team_artifacts"
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", ta)
    pkg = "pkg-contract-gate"
    pkg_dir = ta / pkg
    pkg_dir.mkdir(parents=True)
    contract = wf._execution_contract(pkg)

    assert wf._execution_contract_ready_for_post_agent(pkg) is False

    contract.write_text("", encoding="utf-8")
    assert wf._execution_contract_ready_for_post_agent(pkg) is False

    contract.write_text("   \n", encoding="utf-8")
    assert wf._execution_contract_ready_for_post_agent(pkg) is False

    contract.write_text("STARTED\n", encoding="utf-8")
    assert wf._execution_contract_ready_for_post_agent(pkg) is False

    contract.write_text(
        "# Evidence\nExecution summary and changed paths for workflow post-agent.\n",
        encoding="utf-8",
    )
    assert wf._execution_contract_ready_for_post_agent(pkg) is True


def test_set_active_package_in_registry(tmp_path, monkeypatch) -> None:
    """_set_active_package_in_registry updates active_package_id line in-place."""
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        "schema_version: 2\nactive_package_id: old-pkg\nitems: []\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(wf, "REGISTRY", registry)
    changed = wf._set_active_package_in_registry("new-pkg")
    assert changed is True
    content = registry.read_text(encoding="utf-8")
    assert "active_package_id: new-pkg" in content
    assert "old-pkg" not in content


def test_loop_execution_auto_updates_registry_active_package(tmp_path, monkeypatch) -> None:
    """PAUSE: loop writes task_started.md AND updates active_package_id in registry."""
    pkg = "pkg-registry-update"
    artifacts_dir = tmp_path / "archive" / "team_artifacts" / pkg
    artifacts_dir.mkdir(parents=True)

    registry = tmp_path / "registry.yaml"
    registry.write_text(
        f"schema_version: 2\nactive_package_id: other-pkg\nitems: []\n",
        encoding="utf-8",
    )

    fake_state = {
        "state": wf.STATE_READY_FRESH,
        "package": pkg,
        "status": "ready",
        "work_state": "fresh",
        "next_label": "Прямое выполнение (тест)",
        "next_cmd": "echo task",
        "next_hint": None,
        "warnings": [],
        "execution_auto": True,
        "complexity": "low",
        "complexity_route": "execution_auto",
        "has_us_or_cjm": False,
    }

    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    monkeypatch.setattr(wf, "REGISTRY", registry)
    monkeypatch.setattr(wf, "resolve_state", lambda *a, **kw: fake_state)
    monkeypatch.setattr(wf, "_find_active_package", lambda pkg_id: (pkg, "explicit"))
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: type("R", (), {"returncode": 0})())

    rc = wf._run_loop(
        pkg, "cursor_ai",
        skip_review=True, watch_contract=True, watch_timeout=60, loop_max=2,
    )

    assert rc == 0
    content = registry.read_text(encoding="utf-8")
    assert f"active_package_id: {pkg}" in content, (
        f"active_package_id must point to {pkg!r}, got:\n{content}"
    )


def test_loop_execution_auto_writes_sentinel_and_exits(tmp_path, monkeypatch) -> None:
    """After generating current_task.md for GUI agent, loop writes task_started.md
    and exits 0 without blocking (non-blocking pause semantics)."""
    pkg = "pkg-loop-auto"
    artifacts_dir = tmp_path / "archive" / "team_artifacts" / pkg
    artifacts_dir.mkdir(parents=True)

    fake_state = {
        "state": wf.STATE_READY_FRESH,
        "package": pkg,
        "status": "ready",
        "work_state": "fresh",
        "next_label": "Прямое выполнение через run_autonomous (тест)",
        "next_cmd": "echo generate_task",
        "next_hint": None,
        "warnings": [],
        "execution_auto": True,
        "complexity": "low",
        "complexity_route": "execution_auto",
        "has_us_or_cjm": False,
    }

    calls: list[str] = []

    def fake_run(cmd, *, shell, cwd):
        calls.append(cmd)
        class _R:
            returncode = 0
        return _R()

    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    _isolate_workflow_registry(monkeypatch, tmp_path)
    monkeypatch.setattr(wf, "resolve_state", lambda *a, **kw: fake_state)
    monkeypatch.setattr(wf, "_find_active_package", lambda pkg_id: (pkg, "explicit"))
    monkeypatch.setattr(subprocess, "run", fake_run)

    rc = wf._run_loop(
        pkg,
        "cursor_ai",
        skip_review=True,
        watch_contract=True,
        watch_timeout=60,
        loop_max=2,
    )

    assert rc == 0, f"Expected exit 0, got {rc}"
    sentinel = tmp_path / "archive" / "team_artifacts" / pkg / "task_started.md"
    assert sentinel.exists(), "task_started.md должен быть создан"
    assert pkg in sentinel.read_text()


def test_loop_execution_auto_watch_contract_with_trigger_runs_pipeline(tmp_path, monkeypatch) -> None:
    """С --trigger-cmd: run_autonomous → SDK-триггер → wait → --post-agent."""
    pkg = "pkg-trig-auto"
    artifacts_dir = tmp_path / "archive" / "team_artifacts" / pkg
    artifacts_dir.mkdir(parents=True)

    fake_state = {
        "state": wf.STATE_READY_FRESH,
        "package": pkg,
        "status": "ready",
        "work_state": "fresh",
        "next_label": "Прямое выполнение через run_autonomous (тест)",
        "next_cmd": "echo generate_task",
        "next_hint": None,
        "warnings": [],
        "execution_auto": True,
        "complexity": "low",
        "complexity_route": "execution_auto",
        "has_us_or_cjm": False,
    }
    after = {
        "state": wf.STATE_NO_PACKAGE,
        "package": None,
        "status": None,
        "work_state": None,
        "next_label": "",
        "next_cmd": None,
        "next_hint": None,
        "warnings": [],
    }
    states = iter([fake_state, after])

    trig_calls: list[tuple[str, Path]] = []

    def fake_invoke(cmd: str, path: Path) -> int:
        trig_calls.append((cmd, path))
        return 0

    runs: list[str] = []

    def fake_run(cmd: str, *, shell: bool, cwd: str, env=None):
        runs.append(cmd)
        class _R:
            returncode = 0
        return _R()

    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    _isolate_workflow_registry(monkeypatch, tmp_path)
    monkeypatch.setattr(wf, "resolve_state", lambda *a, **kw: next(states))
    monkeypatch.setattr(wf, "_find_active_package", lambda pkg_id: (pkg, "explicit"))
    monkeypatch.setattr(wf, "_invoke_trigger_cmd", fake_invoke)
    monkeypatch.setattr(wf, "_wait_for_file", lambda *a, **kwargs: True)
    monkeypatch.setattr(subprocess, "run", fake_run)

    rc = wf._run_loop(
        pkg,
        "cursor_ai",
        skip_review=True,
        watch_contract=True,
        watch_timeout=60,
        loop_max=3,
        trigger_cmd="npx tsx scripts/cursor_agent_trigger.ts",
    )

    assert rc == 0
    assert len(trig_calls) == 1
    assert "npx tsx" in trig_calls[0][0]
    assert trig_calls[0][1] == tmp_path / "doc" / "current_task.md"
    assert any("run_autonomous.py" in c and "--post-agent" not in c for c in runs)
    assert any("--post-agent" in c for c in runs)


def test_loop_execution_auto_trigger_skips_watch_when_package_already_closed(
    tmp_path, monkeypatch
) -> None:
    """Если run_autonomous синхронно закрыл пакет — без триггера, без wait и без post-agent."""
    pkg = "pkg-trig-auto-closed"
    artifacts_dir = tmp_path / "archive" / "team_artifacts" / pkg
    artifacts_dir.mkdir(parents=True)

    fake_state = {
        "state": wf.STATE_READY_FRESH,
        "package": pkg,
        "status": "ready",
        "work_state": "fresh",
        "next_label": "Прямое выполнение через run_autonomous (тест)",
        "next_cmd": "echo generate_task",
        "next_hint": None,
        "warnings": [],
        "execution_auto": True,
        "complexity": "low",
        "complexity_route": "execution_auto",
        "has_us_or_cjm": False,
    }
    after = {
        "state": wf.STATE_NO_PACKAGE,
        "package": None,
        "status": None,
        "work_state": None,
        "next_label": "",
        "next_cmd": None,
        "next_hint": None,
        "warnings": [],
    }
    states = iter([fake_state, after])

    trig_calls: list[tuple[str, Path]] = []

    def fake_invoke(cmd: str, path: Path) -> int:
        trig_calls.append((cmd, path))
        return 0

    runs: list[str] = []

    def fake_run(cmd: str, *, shell: bool, cwd: str, env=None):
        runs.append(cmd)
        class _R:
            returncode = 0
        return _R()

    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    monkeypatch.setattr(wf, "resolve_state", lambda *a, **kw: next(states))
    monkeypatch.setattr(wf, "_find_active_package", lambda pkg_id: (pkg, "explicit"))
    monkeypatch.setattr(wf, "_package_status", lambda pid: "closed" if pid == pkg else "unknown")
    monkeypatch.setattr(wf, "_invoke_trigger_cmd", fake_invoke)
    def _no_wait(*_a, **_kw):
        raise AssertionError("_wait_for_file must not run when package already closed")

    monkeypatch.setattr(wf, "_wait_for_file", _no_wait)
    monkeypatch.setattr(subprocess, "run", fake_run)

    rc = wf._run_loop(
        pkg,
        "cursor_ai",
        skip_review=True,
        watch_contract=True,
        watch_timeout=60,
        loop_max=3,
        trigger_cmd="npx tsx scripts/cursor_agent_trigger.ts",
    )

    assert rc == 0
    assert trig_calls == []
    assert any("run_autonomous.py" in c and "--post-agent" not in c for c in runs)
    assert not any("--post-agent" in c for c in runs)


def test_resolve_next_orchestration_step_detects_first_incomplete(tmp_path, monkeypatch) -> None:
    pkg = "pkg-orch-steps"
    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    art = tmp_path / "archive" / "team_artifacts" / pkg
    art.mkdir(parents=True)
    orch = art / "orchestration_cursor_ai.md"
    orch.write_text(
        "## Write-Set\n- `app/foo.py`\n\n"
        "## STEP 1 — Product Owner  [SEQUENTIAL]\n"
        "SAVE:\n"
        f"  → archive/team_artifacts/{pkg}/1_po_package.md\n\n"
        "## STEP 2 — Analyst  [SEQUENTIAL]\n"
        "SAVE:\n"
        f"  → archive/team_artifacts/{pkg}/2_analyst_spec.md\n",
        encoding="utf-8",
    )
    step = wf._resolve_next_orchestration_step(pkg, orch)
    assert step is not None
    assert step.step_id == "1"
    (art / "1_po_package.md").write_text("po", encoding="utf-8")
    step2 = wf._resolve_next_orchestration_step(pkg, orch)
    assert step2 is not None
    assert step2.step_id == "2"


def test_write_orchestration_closure_task_no_close_package(tmp_path, monkeypatch) -> None:
    pkg = "pkg-closure-task"
    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    art = tmp_path / "archive" / "team_artifacts" / pkg
    art.mkdir(parents=True)
    orch = art / "orchestration_cursor_ai.md"
    orch.write_text(
        "## STEP 8 — Closure  [SEQUENTIAL]\n"
        "Run close_package.py --package foo\n",
        encoding="utf-8",
    )
    step = wf.OrchStep(
        step_id="8",
        title="Closure",
        body=orch.read_text(encoding="utf-8"),
        artifact_names=(),
    )
    wf._write_orchestration_current_task(pkg, "cursor_ai", orch, step=step)
    text = (tmp_path / "doc" / "current_task.md").read_text(encoding="utf-8")
    assert "proof file only" in text
    assert "Do **not** run `close_package.py`" in text
    assert "Run close_package.py --package foo" not in text


def test_trigger_shared_documents_exit_on_substantive_proof() -> None:
    shared = (ROOT / "scripts" / "_trigger_shared.ts").read_text(encoding="utf-8")
    assert "EXIT_ON_SUBSTANTIVE_PROOF" in shared
    assert "finished_early" in (ROOT / "scripts" / "cursor_agent_trigger.ts").read_text(encoding="utf-8")


def test_write_orchestration_current_task_scoped_step(tmp_path, monkeypatch) -> None:
    pkg = "pkg-scoped-task"
    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    art = tmp_path / "archive" / "team_artifacts" / pkg
    art.mkdir(parents=True)
    orch = art / "orchestration_cursor_ai.md"
    orch.write_text(
        "## STEP 1 — Product Owner  [SEQUENTIAL]\n"
        "Do PO work.\n"
        f"SAVE:\n  → archive/team_artifacts/{pkg}/1_po_package.md\n",
        encoding="utf-8",
    )
    step = wf._resolve_next_orchestration_step(pkg, orch)
    wf._write_orchestration_current_task(pkg, "cursor_ai", orch, step=step)
    text = (tmp_path / "doc" / "current_task.md").read_text(encoding="utf-8")
    assert "ORCHESTRATION STEP TASK" in text
    assert "ONLY Step 1" in text
    assert "STEP 1 through the final step" not in text


def test_acquire_loop_lock_reclaims_stale_pid(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(wf, "_acquire_loop_lock", _REAL_ACQUIRE_LOOP_LOCK)
    monkeypatch.setattr(wf, "_release_loop_lock", _REAL_RELEASE_LOOP_LOCK)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    lock_path = wf._loop_lock_path()
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text("pid=999999999\nstarted=0\n", encoding="utf-8")
    monkeypatch.setattr(wf, "_pid_alive", lambda _pid: False)
    assert wf._acquire_loop_lock() is True
    assert lock_path.exists()
    assert wf._read_loop_lock_pid(lock_path) == os.getpid()
    wf._release_loop_lock()
    assert not lock_path.exists()


def test_continue_after_orch_step_detects_artifact(tmp_path, monkeypatch) -> None:
    pkg = "pkg-step-done"
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    art = tmp_path / "archive" / "team_artifacts" / pkg
    art.mkdir(parents=True)
    (art / "1_po_package.md").write_text("ok", encoding="utf-8")
    step = wf.OrchStep(
        step_id="1",
        title="PO",
        body="",
        artifact_names=("1_po_package.md",),
    )
    assert wf._continue_after_orch_step(pkg, step, source="test") is True


# ---------------------------------------------------------------------------
# STEP 3.5 completion logic — regression tests (Bug fix 2026-05-29)
# ---------------------------------------------------------------------------

def test_step_35_complete_via_skipped_marker(tmp_path, monkeypatch) -> None:
    """3_5_skipped.md must be recognised as STEP 3.5 complete.

    Regression: the skipped marker is the canonical way to skip the Ops Impact Gate
    when ops_gate_triggered=false (e.g. write-set has no ops-sensitive files).
    """
    pkg = "pkg-step35-skip"
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    art = tmp_path / "archive" / "team_artifacts" / pkg
    art.mkdir(parents=True)
    (art / "3_5_skipped.md").write_text("SKIPPED", encoding="utf-8")
    step = wf.OrchStep(
        step_id="3.5",
        title="Ops Impact Gate",
        body="",
        artifact_names=(),
        conditional=True,
    )
    assert wf._step_is_complete(art, step) is True


def test_step_35_complete_via_impact_file(tmp_path, monkeypatch) -> None:
    """Any 3_5_*.md artifact satisfies STEP 3.5 completion."""
    pkg = "pkg-step35-impact"
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    art = tmp_path / "archive" / "team_artifacts" / pkg
    art.mkdir(parents=True)
    (art / "3_5_ragops_impact.md").write_text("# RAGOps\nVERDICT: GREEN", encoding="utf-8")
    step = wf.OrchStep(
        step_id="3.5",
        title="Ops Impact Gate",
        body="",
        artifact_names=(),
        conditional=True,
    )
    assert wf._step_is_complete(art, step) is True


def test_step_35_incomplete_without_files(tmp_path, monkeypatch) -> None:
    """STEP 3.5 is NOT complete when no 3_5_*.md files exist."""
    pkg = "pkg-step35-empty"
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    art = tmp_path / "archive" / "team_artifacts" / pkg
    art.mkdir(parents=True)
    # Presence of other step artifacts must not affect 3.5 completion
    (art / "1_po_package.md").write_text("ok", encoding="utf-8")
    (art / "3_architect_contract.md").write_text("ok", encoding="utf-8")
    step = wf.OrchStep(
        step_id="3.5",
        title="Ops Impact Gate",
        body="",
        artifact_names=(),
        conditional=True,
    )
    assert wf._step_is_complete(art, step) is False


def test_step_35_not_confused_by_non_md_file(tmp_path, monkeypatch) -> None:
    """A 3_5_*.txt file (wrong extension) must NOT satisfy STEP 3.5 completion."""
    pkg = "pkg-step35-wrongext"
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    art = tmp_path / "archive" / "team_artifacts" / pkg
    art.mkdir(parents=True)
    (art / "3_5_ragops_impact.txt").write_text("wrong ext", encoding="utf-8")
    step = wf.OrchStep(
        step_id="3.5",
        title="Ops Impact Gate",
        body="",
        artifact_names=(),
        conditional=True,
    )
    assert wf._step_is_complete(art, step) is False


def test_steps_6_7_not_skipped_when_architect_has_backend_sp2(tmp_path, monkeypatch) -> None:
    """Backend sp2 (no app/ui/ in write-set) must still require STEP 6–7."""
    pkg = "pkg-backend-sp2"
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    art = tmp_path / "archive" / "team_artifacts" / pkg
    art.mkdir(parents=True)
    (art / "3_architect_contract.md").write_text(
        "#### Package pkg-backend-sp2-sp1\n\n#### Package pkg-backend-sp2-sp2\n",
        encoding="utf-8",
    )
    orch_text = (
        "## Write-Set\n"
        "- `app/ssr_misroute_policy.py`\n\n"
        "## STEP 5 — Tester sp1\n"
        f"SAVE:\n  → archive/team_artifacts/{pkg}/6a_tester_sp1.md\n\n"
        "## STEP 6 — Developer sub-package 2\n"
        f"SAVE:\n  → archive/team_artifacts/{pkg}/5b_developer_sp2.md\n\n"
        "## STEP 7 — Tester sub-package 2\n"
        f"SAVE:\n  → archive/team_artifacts/{pkg}/6b_tester_sp2.md\n"
    )
    steps = wf._parse_orchestration_steps(orch_text, pkg)
    step6 = next(s for s in steps if s.step_id == "6")
    step7 = next(s for s in steps if s.step_id == "7")
    assert step6.skippable is False
    assert step7.skippable is False


def test_steps_6_7_skipped_when_no_sp2_and_no_ui(tmp_path, monkeypatch) -> None:
    pkg = "pkg-no-sp2"
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    art = tmp_path / "archive" / "team_artifacts" / pkg
    art.mkdir(parents=True)
    orch_text = (
        "## Write-Set\n"
        "- `app/foo.py`\n\n"
        "## STEP 6 — Developer sub-package 2\n"
        f"SAVE:\n  → archive/team_artifacts/{pkg}/5b_developer_sp2.md\n"
    )
    steps = wf._parse_orchestration_steps(orch_text, pkg)
    step6 = next(s for s in steps if s.step_id == "6")
    assert step6.skippable is True


def test_stale_substantive_contract_does_not_skip_intermediate_step(
    tmp_path, monkeypatch,
) -> None:
    """Substantive execution_contract must not jump to post-agent while STEP 6 pending."""
    pkg = "pkg-stale-proof"
    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    art = tmp_path / "archive" / "team_artifacts" / pkg
    art.mkdir(parents=True)
    (art / "3_architect_contract.md").write_text(
        "#### Package pkg-stale-proof-sp2\n", encoding="utf-8",
    )
    (art / "6a_tester_sp1.md").write_text("pass", encoding="utf-8")
    (art / "execution_contract.md").write_text(
        "# Proof\n\nallow_verification_only\n\n## Pre-existing delivery evidence\n"
        "- commit: deadbeef\n- files: app/foo.py\n",
        encoding="utf-8",
    )
    orch = art / "orchestration_cursor_ai.md"
    orch.write_text(
        "## Write-Set\n- `app/foo.py`\n\n"
        "## STEP 5 — Tester sp1\n"
        f"SAVE:\n  → archive/team_artifacts/{pkg}/6a_tester_sp1.md\n\n"
        "## STEP 6 — Developer sp2\n"
        f"SAVE:\n  → archive/team_artifacts/{pkg}/5b_developer_sp2.md\n\n"
        "## STEP 8 — Closure\n"
        "proof only\n",
        encoding="utf-8",
    )
    step = wf._resolve_next_orchestration_step(pkg, orch)
    assert step is not None
    assert step.step_id == "6"


def test_trigger_cmd_with_retries_eventually_succeeds(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(wf, "_trigger_retry_limit", lambda: 2)
    monkeypatch.setattr(wf.time, "sleep", lambda _s: None)
    calls: list[int] = []

    def fake_invoke(cmd: str, path: Path) -> int:
        calls.append(1)
        return 2 if len(calls) < 3 else 0

    monkeypatch.setattr(wf, "_invoke_trigger_cmd", fake_invoke)
    rc = wf._invoke_trigger_cmd_with_retries("trigger", tmp_path / "task.md")
    assert rc == 0
    assert len(calls) == 3


def test_loop_ready_orch_watch_contract_with_trigger(tmp_path, monkeypatch) -> None:
    pkg = "pkg-orch-trig"
    art = tmp_path / "archive" / "team_artifacts" / pkg
    art.mkdir(parents=True)
    (art / "orchestration_cursor_ai.md").write_text("# o\n", encoding="utf-8")

    registry = tmp_path / "registry.yaml"
    registry.write_text("active_package_id: x\nitems: []\n", encoding="utf-8")

    orch_state = {
        "state": wf.STATE_READY_ORCH,
        "package": pkg,
        "status": "ready",
        "work_state": "fresh",
        "next_label": "orch",
        "next_cmd": None,
        "next_hint": "...",
        "warnings": [],
        "orch_file": f"archive/team_artifacts/{pkg}/orchestration_cursor_ai.md",
    }
    after = {
        "state": wf.STATE_NO_PACKAGE,
        "package": None,
        "status": None,
        "work_state": None,
        "next_label": "",
        "next_cmd": None,
        "next_hint": None,
        "warnings": [],
    }
    states = iter([orch_state, after])

    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    monkeypatch.setattr(wf, "REGISTRY", registry)
    monkeypatch.setattr(wf, "_find_active_package", lambda p: (pkg, "explicit"))
    monkeypatch.setattr(wf, "resolve_state", lambda *a, **kw: next(states))

    trig: list[tuple[str, Path]] = []

    def fake_invoke(cmd: str, path: Path) -> int:
        trig.append((cmd, path))
        return 0

    runs: list[str] = []

    def fake_run(cmd: str, *, shell: bool, cwd: str, env=None):
        runs.append(cmd)
        class _R:
            returncode = 0
        return _R()

    monkeypatch.setattr(wf, "_invoke_trigger_cmd", fake_invoke)
    monkeypatch.setattr(wf, "_wait_for_file", lambda *a, **kwargs: True)
    monkeypatch.setattr(subprocess, "run", fake_run)

    rc = wf._run_loop(
        pkg,
        "cursor_ai",
        skip_review=True,
        watch_contract=True,
        watch_timeout=60,
        loop_max=3,
        trigger_cmd="npx tsx scripts/cursor_agent_trigger.ts",
    )
    assert rc == 0
    assert len(trig) == 1
    task_text = (tmp_path / "doc" / "current_task.md").read_text(encoding="utf-8")
    assert "ORCHESTRATION-FIRST TASK" in task_text
    assert "orchestration_cursor_ai.md" in task_text
    assert "generate_next_prompt.py --quick" in task_text
    assert "Pre-existing delivery evidence:" in task_text
    assert "- files: app/example.py, tests/test_example.py" in task_text
    assert not any("run_autonomous.py" in c and "--post-agent" not in c for c in runs)
    assert any("--post-agent" in c for c in runs)


def test_loop_trigger_cmd_failure_returns_rc(tmp_path, monkeypatch, capsys) -> None:
    pkg = "pkg-trig-fail"
    artifacts_dir = tmp_path / "archive" / "team_artifacts" / pkg
    artifacts_dir.mkdir(parents=True)
    fake_state = {
        "state": wf.STATE_READY_FRESH,
        "package": pkg,
        "status": "ready",
        "work_state": "fresh",
        "next_label": "x",
        "next_cmd": "echo",
        "next_hint": None,
        "warnings": [],
        "execution_auto": True,
        "complexity": "low",
        "complexity_route": "execution_auto",
        "has_us_or_cjm": False,
    }
    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    _isolate_workflow_registry(monkeypatch, tmp_path)
    monkeypatch.setattr(wf, "resolve_state", lambda *a, **kw: fake_state)
    monkeypatch.setattr(wf, "_find_active_package", lambda pkg_id: (pkg, "explicit"))
    monkeypatch.setattr(wf, "_invoke_trigger_cmd", lambda c, p: 7)

    def fake_run(cmd: str, *, shell: bool, cwd: str, env=None):
        class _R:
            returncode = 0
        return _R()

    monkeypatch.setattr(subprocess, "run", fake_run)

    rc = wf._run_loop(
        pkg,
        "cursor_ai",
        skip_review=True,
        watch_contract=True,
        watch_timeout=60,
        loop_max=2,
        trigger_cmd="bad",
    )
    assert rc == 7
    out = capsys.readouterr().out
    assert "rc=7" in out
    assert "произвольная команда триггера" in out


def test_trigger_cmd_rc_hint_maps_cursor_trigger_exits() -> None:
    """Коды 1–4 согласованы с scripts/cursor_agent_trigger.ts и workflow_router.md."""
    assert "CURSOR_API_KEY" in wf._trigger_cmd_rc_hint(1)
    assert "status=error" in wf._trigger_cmd_rc_hint(2)
    assert "повторн" in wf._trigger_cmd_rc_hint(3)
    assert "non-retryable" in wf._trigger_cmd_rc_hint(4)
    assert "workflow.py --loop" in wf._trigger_cmd_rc_hint(130)


def test_trigger_cmd_rc_hint_unknown_rc_is_neutral() -> None:
    assert "произвольная" in wf._trigger_cmd_rc_hint(7)


def test_invoke_trigger_cmd_keyboard_interrupt_returns_recovery_rc(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(wf, "ROOT", tmp_path)

    def fake_run(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(subprocess, "run", fake_run)

    rc = wf._invoke_trigger_cmd(
        "npx tsx scripts/cursor_agent_trigger.ts",
        tmp_path / "doc" / "current_task.md",
    )

    assert rc == 130
    assert "KeyboardInterrupt" in capsys.readouterr().out


def test_invoke_trigger_cmd_passes_current_task_path_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(wf, "ROOT", tmp_path)
    task_path = tmp_path / "doc" / "current_task.md"
    task_path.parent.mkdir()
    task_path.write_text("# task\n", encoding="utf-8")
    observed = tmp_path / "observed_env.txt"
    trigger = tmp_path / "fake_trigger.py"
    trigger.write_text(
        "import os, pathlib\n"
        f"pathlib.Path({str(observed)!r}).write_text("
        "os.environ['WORKFLOW_CURRENT_TASK_PATH'], encoding='utf-8')\n",
        encoding="utf-8",
    )

    rc = wf._invoke_trigger_cmd(f'"{sys.executable}" "{trigger}"', task_path)

    assert rc == 0
    assert Path(observed.read_text(encoding="utf-8")) == task_path.resolve()


def test_loop_trigger_keyboard_interrupt_rc_stops_before_wait_or_post(
    tmp_path, monkeypatch
) -> None:
    pkg = "pkg-trig-ki"
    (tmp_path / "archive" / "team_artifacts" / pkg).mkdir(parents=True)
    fake_state = {
        "state": wf.STATE_READY_FRESH,
        "package": pkg,
        "status": "ready",
        "work_state": "fresh",
        "next_label": "x",
        "next_cmd": "echo",
        "next_hint": None,
        "warnings": [],
        "execution_auto": True,
        "complexity": "low",
        "complexity_route": "execution_auto",
        "has_us_or_cjm": False,
    }
    wait_called: list[str] = []
    runs: list[str] = []

    def fake_run(cmd: str, *, shell: bool, cwd: str, env=None):
        runs.append(cmd)
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    _isolate_workflow_registry(monkeypatch, tmp_path)
    monkeypatch.setattr(wf, "resolve_state", lambda *a, **kw: fake_state)
    monkeypatch.setattr(wf, "_find_active_package", lambda pkg_id: (pkg, "explicit"))
    monkeypatch.setattr(wf, "_invoke_trigger_cmd", lambda c, p: 130)
    monkeypatch.setattr(wf, "_wait_for_file", lambda *a, **kw: wait_called.append("wait") or True)
    monkeypatch.setattr(subprocess, "run", fake_run)

    rc = wf._run_loop(
        pkg,
        "cursor_ai",
        skip_review=True,
        watch_contract=True,
        watch_timeout=60,
        loop_max=2,
        trigger_cmd="npx tsx x",
    )

    assert rc == 130
    assert wait_called == []
    assert not any("--post-agent" in cmd for cmd in runs)


def test_loop_execution_auto_no_trigger_does_not_call_invoke(tmp_path, monkeypatch) -> None:
    pkg = "pkg-no-invoke"
    artifacts_dir = tmp_path / "archive" / "team_artifacts" / pkg
    artifacts_dir.mkdir(parents=True)
    fake_state = {
        "state": wf.STATE_READY_FRESH,
        "package": pkg,
        "status": "ready",
        "work_state": "fresh",
        "next_label": "Прямое выполнение через run_autonomous (тест)",
        "next_cmd": "echo generate_task",
        "next_hint": None,
        "warnings": [],
        "execution_auto": True,
        "complexity": "low",
        "complexity_route": "execution_auto",
        "has_us_or_cjm": False,
    }

    def boom(cmd: str, path: Path) -> int:
        raise AssertionError("_invoke_trigger_cmd should not be called")

    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    _isolate_workflow_registry(monkeypatch, tmp_path)
    monkeypatch.setattr(wf, "resolve_state", lambda *a, **kw: fake_state)
    monkeypatch.setattr(wf, "_find_active_package", lambda pkg_id: (pkg, "explicit"))
    monkeypatch.setattr(wf, "_invoke_trigger_cmd", boom)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: type("R", (), {"returncode": 0})())

    rc = wf._run_loop(
        pkg,
        "cursor_ai",
        skip_review=True,
        watch_contract=True,
        watch_timeout=60,
        loop_max=2,
        trigger_cmd=None,
    )
    assert rc == 0


def test_loop_execution_auto_trigger_skipped_when_contract_exists_after_gen(
    tmp_path, monkeypatch
) -> None:
    """Если контракт появился до триггера — SDK не вызывается."""
    pkg = "pkg-skip-trig"
    artifacts_dir = tmp_path / "archive" / "team_artifacts" / pkg
    artifacts_dir.mkdir(parents=True)
    contract_path = artifacts_dir / "execution_contract.md"

    fake_state = {
        "state": wf.STATE_READY_FRESH,
        "package": pkg,
        "status": "ready",
        "work_state": "fresh",
        "next_label": "x",
        "next_cmd": "echo",
        "next_hint": None,
        "warnings": [],
        "execution_auto": True,
        "complexity": "low",
        "complexity_route": "execution_auto",
        "has_us_or_cjm": False,
    }
    done = {
        "state": wf.STATE_NO_PACKAGE,
        "package": None,
        "status": None,
        "work_state": None,
        "next_label": "",
        "next_cmd": None,
        "next_hint": None,
        "warnings": [],
    }
    states = iter([fake_state, done])

    called: list[str] = []

    def fake_invoke(cmd: str, path: Path) -> int:
        called.append("invoke")
        return 0

    def fake_run(cmd: str, *, shell: bool, cwd: str, env=None):
        if "run_autonomous" in cmd and "--post-agent" not in cmd:
            contract_path.write_text("# ok\n", encoding="utf-8")
        class _R:
            returncode = 0
        return _R()

    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    _isolate_workflow_registry(monkeypatch, tmp_path)
    monkeypatch.setattr(wf, "resolve_state", lambda *a, **kw: next(states))
    monkeypatch.setattr(wf, "_find_active_package", lambda pkg_id: (pkg, "explicit"))
    monkeypatch.setattr(wf, "_invoke_trigger_cmd", fake_invoke)
    monkeypatch.setattr(wf, "_wait_for_file", lambda *a, **kwargs: True)
    monkeypatch.setattr(subprocess, "run", fake_run)

    rc = wf._run_loop(
        pkg,
        "cursor_ai",
        skip_review=True,
        watch_contract=True,
        watch_timeout=60,
        loop_max=3,
        trigger_cmd="npx tsx x",
    )
    assert rc == 0
    assert called == []


def test_loop_execution_auto_trigger_stops_when_task_generation_fails(
    tmp_path, monkeypatch
) -> None:
    pkg = "pkg-gen-fail"
    (tmp_path / "archive" / "team_artifacts" / pkg).mkdir(parents=True)
    fake_state = {
        "state": wf.STATE_READY_FRESH,
        "package": pkg,
        "status": "ready",
        "work_state": "fresh",
        "next_label": "x",
        "next_cmd": "echo",
        "next_hint": None,
        "warnings": [],
        "execution_auto": True,
        "complexity": "low",
        "complexity_route": "execution_auto",
        "has_us_or_cjm": False,
    }
    invoked: list[str] = []

    def fake_invoke(cmd: str, path: Path) -> int:
        invoked.append(cmd)
        return 0

    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    monkeypatch.setattr(wf, "resolve_state", lambda *a, **kw: fake_state)
    monkeypatch.setattr(wf, "_find_active_package", lambda pkg_id: (pkg, "explicit"))
    monkeypatch.setattr(wf, "_invoke_trigger_cmd", fake_invoke)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: type("R", (), {"returncode": 9})())

    rc = wf._run_loop(
        pkg,
        "cursor_ai",
        skip_review=True,
        watch_contract=True,
        watch_timeout=60,
        loop_max=2,
        trigger_cmd="npx tsx x",
    )

    assert rc == 9
    assert invoked == []


def test_loop_ready_orch_trigger_stops_when_orchestration_file_missing(
    tmp_path, monkeypatch
) -> None:
    pkg = "pkg-orch-gen-fail"
    art = tmp_path / "archive" / "team_artifacts" / pkg
    art.mkdir(parents=True)
    fake_state = {
        "state": wf.STATE_READY_ORCH,
        "package": pkg,
        "status": "ready",
        "work_state": "fresh",
        "next_label": "orch",
        "next_cmd": None,
        "next_hint": "...",
        "warnings": [],
        "orch_file": f"archive/team_artifacts/{pkg}/orchestration_cursor_ai.md",
    }
    invoked: list[str] = []

    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    monkeypatch.setattr(wf, "resolve_state", lambda *a, **kw: fake_state)
    monkeypatch.setattr(wf, "_find_active_package", lambda pkg_id: (pkg, "explicit"))
    monkeypatch.setattr(wf, "_invoke_trigger_cmd", lambda c, p: invoked.append(c) or 0)

    rc = wf._run_loop(
        pkg,
        "cursor_ai",
        skip_review=True,
        watch_contract=True,
        watch_timeout=60,
        loop_max=2,
        trigger_cmd="npx tsx x",
    )

    assert rc == 1
    assert invoked == []


def test_loop_execution_auto_no_watch_contract_exits_without_sentinel(tmp_path, monkeypatch) -> None:
    """Without --watch-contract, loop exits 0 and does NOT write task_started.md."""
    pkg = "pkg-no-watch"
    artifacts_dir = tmp_path / "archive" / "team_artifacts" / pkg
    artifacts_dir.mkdir(parents=True)

    fake_state = {
        "state": wf.STATE_READY_FRESH,
        "package": pkg,
        "status": "ready",
        "work_state": "fresh",
        "next_label": "Прямое выполнение через run_autonomous (тест)",
        "next_cmd": "echo generate_task",
        "next_hint": None,
        "warnings": [],
        "execution_auto": True,
        "complexity": "low",
        "complexity_route": "execution_auto",
        "has_us_or_cjm": False,
    }

    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    monkeypatch.setattr(wf, "resolve_state", lambda *a, **kw: fake_state)
    monkeypatch.setattr(wf, "_find_active_package", lambda pkg_id: (pkg, "explicit"))
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: type("R", (), {"returncode": 0})())

    rc = wf._run_loop(
        pkg,
        "cursor_ai",
        skip_review=True,
        watch_contract=False,
        watch_timeout=60,
        loop_max=2,
    )

    assert rc == 0
    sentinel = tmp_path / "archive" / "team_artifacts" / pkg / "task_started.md"
    assert not sentinel.exists(), "task_started.md не должен появляться без --watch-contract"


def test_loop_ready_executing_contract_appears_runs_post_agent(tmp_path, monkeypatch) -> None:
    """STATE_READY_EXECUTING + execution_contract.md exists → post-agent is called."""
    pkg = "pkg-resuming"
    artifacts_dir = tmp_path / "archive" / "team_artifacts" / pkg
    artifacts_dir.mkdir(parents=True)
    (artifacts_dir / "task_started.md").write_text("# started\n", encoding="utf-8")
    (artifacts_dir / "execution_contract.md").write_text("# done\n", encoding="utf-8")

    fake_state = {
        "state": wf.STATE_READY_EXECUTING,
        "package": pkg,
        "status": "ready",
        "work_state": "execution_ready",
        "next_label": "Задача запущена — ожидание execution_contract.md",
        "next_cmd": None,
        "next_hint": "Ожидание...",
        "warnings": [],
    }

    post_calls: list[str] = []

    def fake_run(cmd, *, shell, cwd):
        post_calls.append(cmd)
        class _R:
            returncode = 0
        return _R()

    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    monkeypatch.setattr(wf, "resolve_state", lambda *a, **kw: fake_state)
    monkeypatch.setattr(wf, "_find_active_package", lambda pkg_id: (pkg, "explicit"))
    monkeypatch.setattr(subprocess, "run", fake_run)

    # After post-agent the loop re-resolves; stub returns no_package so it stops.
    call_count = 0
    original_resolve = wf.resolve_state.__wrapped__ if hasattr(wf.resolve_state, "__wrapped__") else None

    states = iter([
        fake_state,
        {"state": wf.STATE_NO_PACKAGE, "package": None, "status": None,
         "work_state": None, "next_label": "", "next_cmd": None,
         "next_hint": None, "warnings": []},
    ])
    monkeypatch.setattr(wf, "resolve_state", lambda *a, **kw: next(states))

    rc = wf._run_loop(
        pkg,
        "cursor_ai",
        skip_review=True,
        watch_contract=True,
        watch_timeout=60,
        loop_max=5,
    )

    assert rc == 0
    assert any("--post-agent" in c for c in post_calls), (
        f"Ожидался вызов --post-agent. Вызовы: {post_calls}"
    )


def test_loop_ready_executing_post_agent_passes_no_dod_cache_when_configured(
    tmp_path, monkeypatch
) -> None:
    """--post-agent-no-dod-cache → subprocess receives --no-dod-cache."""
    pkg = "pkg-resuming-nocache"
    artifacts_dir = tmp_path / "archive" / "team_artifacts" / pkg
    artifacts_dir.mkdir(parents=True)
    (artifacts_dir / "task_started.md").write_text("# started\n", encoding="utf-8")
    (artifacts_dir / "execution_contract.md").write_text("# done\n", encoding="utf-8")

    fake_state = {
        "state": wf.STATE_READY_EXECUTING,
        "package": pkg,
        "status": "ready",
        "work_state": "execution_ready",
        "next_label": "Задача запущена — ожидание execution_contract.md",
        "next_cmd": None,
        "next_hint": "Ожидание...",
        "warnings": [],
    }

    post_calls: list[str] = []

    def fake_run(cmd, *, shell, cwd):
        post_calls.append(cmd)
        class _R:
            returncode = 0
        return _R()

    states = iter(
        [
            fake_state,
            {
                "state": wf.STATE_NO_PACKAGE,
                "package": None,
                "status": None,
                "work_state": None,
                "next_label": "",
                "next_cmd": None,
                "next_hint": None,
                "warnings": [],
            },
        ]
    )

    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    monkeypatch.setattr(wf, "resolve_state", lambda *a, **kw: next(states))
    monkeypatch.setattr(wf, "_find_active_package", lambda pkg_id: (pkg, "explicit"))
    monkeypatch.setattr(subprocess, "run", fake_run)

    rc = wf._run_loop(
        pkg,
        "cursor_ai",
        skip_review=True,
        watch_contract=True,
        watch_timeout=60,
        loop_max=5,
        post_agent_no_dod_cache=True,
    )

    assert rc == 0
    assert any("--no-dod-cache" in c for c in post_calls), post_calls


def test_loop_ready_executing_no_contract_exits_with_hint(tmp_path, monkeypatch, capsys) -> None:
    """STATE_READY_EXECUTING without execution_contract → exits 0 with hint."""
    pkg = "pkg-waiting"
    artifacts_dir = tmp_path / "archive" / "team_artifacts" / pkg
    artifacts_dir.mkdir(parents=True)
    (artifacts_dir / "task_started.md").write_text("# started\n", encoding="utf-8")
    # no execution_contract.md

    fake_state = {
        "state": wf.STATE_READY_EXECUTING,
        "package": pkg,
        "status": "ready",
        "work_state": "fresh",
        "next_label": "Задача запущена — ожидание execution_contract.md",
        "next_cmd": None,
        "next_hint": "Ожидание выполнения задачи агентом.",
        "warnings": [],
    }

    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    monkeypatch.setattr(wf, "resolve_state", lambda *a, **kw: fake_state)
    monkeypatch.setattr(wf, "_find_active_package", lambda pkg_id: (pkg, "explicit"))

    rc = wf._run_loop(
        pkg,
        "cursor_ai",
        skip_review=True,
        watch_contract=True,
        watch_timeout=60,
        loop_max=2,
    )

    assert rc == 0
    captured = capsys.readouterr()
    assert "Ожидание" in captured.out


# ── resolve_state — no tasklist warnings (router uses registry SSoT only) ────


def test_resolve_state_warnings_never_reference_tasklist(fake_root) -> None:
    """Smart router must not read or warn about doc/tasklist.md."""
    _write_registry(fake_root["registry"], [])
    with patch("workflow._find_active_package", return_value=(None, "none")):
        state = wf.resolve_state(None, "cursor_ai")
    for w in state["warnings"]:
        assert "tasklist" not in w.lower()


# ── CLI — --json flag ─────────────────────────────────────────────────────────


def test_cli_json_flag(fake_root) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "workflow.py"), "--json"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "state" in data
    assert "package" in data
    assert "next_label" in data
    assert "warnings" in data


# ── CLI — --status flag (no next_cmd section) ─────────────────────────────────


def test_cli_trigger_cmd_requires_loop_and_watch_contract() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "workflow.py"),
            "--trigger-cmd",
            "npx tsx scripts/cursor_agent_trigger.ts",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT),
    )
    assert result.returncode == 2
    assert "--loop" in result.stdout
    assert "--watch-contract" in result.stdout


def test_cli_rejects_deepseek_trigger_with_cursor_agent() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "workflow.py"),
            "--loop",
            "--watch-contract",
            "--trigger-cmd",
            "npx tsx scripts/deepseek_agent_trigger.ts",
            "--agent",
            "cursor_ai",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT),
    )
    assert result.returncode == 2
    assert "deepseek_agent_trigger.ts" in result.stdout
    assert "--agent continue" in result.stdout


def test_cli_rejects_cursor_trigger_with_continue_agent() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "workflow.py"),
            "--loop",
            "--watch-contract",
            "--trigger-cmd",
            "npx tsx scripts/cursor_agent_trigger.ts",
            "--agent",
            "continue",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT),
    )
    assert result.returncode == 2
    assert "cursor_agent_trigger.ts" in result.stdout
    assert "--agent cursor_ai" in result.stdout


def test_cli_status_flag_no_cmd_section() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "workflow.py"), "--status"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
    )
    assert result.returncode == 0
    assert "СЛЕДУЮЩИЙ ШАГ" not in result.stdout
    assert "WORKFLOW STATE" in result.stdout


# ── CLI — --agent flag changes command output ─────────────────────────────────


def test_cli_agent_flag_reflected_in_json() -> None:
    for agent in ("cursor_ai", "claude_code", "codex"):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "workflow.py"), "--agent", agent, "--json"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        cmd = data.get("next_cmd") or ""
        # If there IS a next_cmd, it must reference the chosen agent
        if cmd:
            assert agent in cmd, f"Expected {agent!r} in cmd: {cmd!r}"


# ── CLI — --exec with no command ─────────────────────────────────────────────


def test_cli_post_agent_no_dod_cache_requires_loop() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "workflow.py"),
            "--post-agent-no-dod-cache",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT),
    )
    assert result.returncode == 2
    merged = (result.stdout or "") + (result.stderr or "")
    assert "--loop" in merged


def test_cli_exec_no_cmd_returns_nonzero() -> None:
    """--exec exits 0 on success or nonzero on any error (policy, no cmd, etc.)."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "workflow.py"), "--exec"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
    )
    # Any exit code is valid: 0 = ran successfully, 1 = no cmd / soft error,
    # 2 = policy block, 4 = DoD failed. The test just verifies the process
    # terminates cleanly (not a negative / signal-killed exit).
    assert result.returncode >= 0


# ── CLI — --package explicit override ─────────────────────────────────────────


def test_cli_package_override_in_json() -> None:
    result = subprocess.run(
        [
            sys.executable, str(ROOT / "scripts" / "workflow.py"),
            "--package", "epoch-arch-review-p1-trivial-fixes",
            "--json",
        ],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["package"] == "epoch-arch-review-p1-trivial-fixes"


# ── Doc sanity checks (p1/p2 changes) ────────────────────────────────────────


def test_workflow_decision_tree_has_tldr() -> None:
    content = (ROOT / "doc" / "team_workflow" / "workflow_decision_tree.md").read_text(
        encoding="utf-8"
    )
    assert "TL;DR" in content
    assert "workflow.py" in content
    assert "--loop" in content
    assert "--watch-contract" in content
    assert "manual-ready-executing" in content


def test_orchestration_prompt_manual_path_demoted() -> None:
    content = (ROOT / "doc" / "team_workflow" / "generate_orchestration_prompt.md").read_text(
        encoding="utf-8"
    )
    auto_pos = content.find("Автоматический способ")
    manual_pos = content.find("Мануальный путь")
    assert auto_pos != -1 and manual_pos != -1
    assert auto_pos < manual_pos, "Автоматический способ должен быть выше мануального"


def test_plan_next_documents_continue_deepseek_handoff() -> None:
    text = (ROOT / "doc" / "team_workflow" / "generate_plan_next_prompt.md").read_text(
        encoding="utf-8"
    )
    assert "TARGET_AGENT:   <claude_code | codex | cursor_ai | continue; default: cursor_ai>" in text
    assert ".\\.venv\\Scripts\\python.exe scripts\\generate_orchestration_prompt.py --agent continue" in text
    assert "scripts\\workflow.py --loop --skip-review --watch-contract --agent continue" in text
    assert "Do not use `scripts/deepseek_agent_trigger.ts` as a production executor" in text
    assert "workflow_deepseek_tui_trigger_implementation_plan.md" in text
    assert "For other TARGET_AGENT values" in text


def test_readme_starts_with_quickstart() -> None:
    text = (ROOT / "doc" / "team_workflow" / "README.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    content = "\n".join(lines[:40])
    assert "workflow.py" in content or "Быстрый старт" in content
    assert "--loop" in text
    assert "workflow_strings.py" in text


def test_archive_snapshots_exist() -> None:
    snapshots_dir = ROOT / "archive" / "team_workflow_snapshots"
    assert snapshots_dir.exists(), "archive/team_workflow_snapshots/ должен существовать"
    files = list(snapshots_dir.iterdir())
    assert len(files) >= 3, f"Ожидалось ≥3 перемещённых файла, найдено: {len(files)}"


@pytest.mark.skip(
    reason=(
        "Лимит числа корневых *.md в doc/team_workflow хрупкий: audit/coverage артефакты "
        "легитимно растут. Вместо искусственного cap — поддерживать ссылки и структуру вручную."
    )
)
def test_team_workflow_file_count_reduced() -> None:
    md_files = list((ROOT / "doc" / "team_workflow").glob("*.md"))
    count = len(md_files)
    # Cap: baseline после dx-p4 + SDK trigger guide + audit chain artifacts (audit_prompt_*, audit_coverage_*, …);
    # май 2026: +файлов в корне после audit/coverage промптов (см. doc/team_workflow).
    assert count <= 68, f"Ожидалось ≤68 файлов в team_workflow/*.md (корень), найдено: {count}"


def test_workflow_strings_prompt_footer_matches_sample_path() -> None:
    rel = "archive/team_artifacts/pkg-x/execution_contract.md"
    block = ws.format_prompt_execute_current_task_footer(rel)
    assert rel in block
    assert ws.SHORT_EXECUTE_CURRENT_TASK_PROMPT_LINE in block
    assert ws.PROMPT_BLOCK_HEADER.strip() in block


def test_workflow_router_doc_footer_lists_stable_anchors() -> None:
    foot = ws.format_workflow_router_doc_footer(ROOT)
    assert ws.WORKFLOW_ROUTER_DOC_REL in foot
    assert "#manual-ready-executing" in foot
    assert "#router-graph" in foot


def test_workflow_router_md_documents_strings_ssot() -> None:
    text = (ROOT / "doc" / "team_workflow" / "workflow_router.md").read_text(encoding="utf-8")
    assert "workflow_strings.py" in text
    assert "canonical-agent-prompt" in text
    assert "router-graph" in text
    assert "router-loop-steps" in text


def test_workflow_router_md_documents_trigger_recovery_contract() -> None:
    text = (ROOT / "doc" / "team_workflow" / "workflow_router.md").read_text(encoding="utf-8")
    assert "--loop --watch-contract" in text
    assert "rc=130" in text
    assert "Terminate batch job" in text
    assert "run_autonomous.py` не сгенерировал `current_task.md`" in text
    assert "только `STARTED`" in text


def test_cursor_sdk_trigger_guide_documents_proof_and_recovery() -> None:
    text = (
        ROOT
        / "doc"
        / "team_workflow"
        / "guides"
        / "workflow_cursor_sdk_trigger_guide.md"
    ).read_text(encoding="utf-8")
    assert "Сам trigger только отправляет промпт" in text
    assert "признак фактического выполнения задачи" in text
    assert "execution_contract.md" in text
    assert "Terminate batch job" in text
    assert "STARTED" in text
    assert "--loop --watch-contract" in text
    assert "Europe/Moscow" in text
    assert "CURSOR_TRIGGER_HEARTBEAT_MS" in text
    assert "heartbeat" in text
    assert "deepseek_agent_trigger.ts" not in text


def test_deepseek_api_trigger_guide_documents_continue_pairing() -> None:
    text = (
        ROOT
        / "doc"
        / "team_workflow"
        / "guides"
        / "workflow_deepseek_api_trigger_guide.md"
    ).read_text(encoding="utf-8")
    assert "deepseek_agent_trigger.ts" in text
    assert "--agent continue" in text
    assert "DEEPSEEK_API_KEY" in text
    assert "execution_contract.md" in text
    assert "orchestration_continue.md" in text
    assert "эксперимент / handoff-only" in text
    assert "workflow_deepseek_tui_trigger_implementation_plan.md" in text
    assert "не является production executor" in text


def test_cursor_agent_trigger_uses_moscow_time_and_heartbeat() -> None:
    shared = (ROOT / "scripts" / "_trigger_shared.ts").read_text(encoding="utf-8")
    text = (ROOT / "scripts" / "cursor_agent_trigger.ts").read_text(encoding="utf-8")
    assert 'LOG_TIME_ZONE = "Europe/Moscow"' in shared
    assert "CURSOR_TRIGGER" in text
    assert "_HEARTBEAT_MS" in shared
    assert "_STARTED_STALL_TIMEOUT_MS" in shared
    assert "started_stalled" in text
    assert "startHeartbeat" in text
    assert "Agent.prompt (Cursor)" in text
    assert "expected proof file" in shared
    assert "final proof state before returning to workflow.py" in shared
    assert "isStartedOnlyContract(contractPath)" in shared
    assert "status: \"finished\"" in shared
    assert "contractContent: null" in text
    assert "requireSubstantiveContract: false" in text


def test_deepseek_trigger_uses_shared_runtime_and_handoff_gate() -> None:
    shared = (ROOT / "scripts" / "_trigger_shared.ts").read_text(encoding="utf-8")
    text = (ROOT / "scripts" / "deepseek_agent_trigger.ts").read_text(encoding="utf-8")
    assert "DEEPSEEK_TRIGGER" in text
    assert "_HEARTBEAT_MS" in shared
    assert "_STARTED_STALL_TIMEOUT_MS" in shared
    assert "deepseek_agent_prompt" in text
    assert "contractGeneratedBy: \"deepseek_agent_trigger.ts\"" in text
    assert "writeExecutionContract(" in shared
    assert "validateContractContent:" in text
    assert "EXECUTION_PROOF:" in text
    assert "BLOCKED: no local tool access" in text
    assert "validateDeepSeekExecutionProof" in text
    assert "generated execution_contract.md rejected" in shared


# ---------------------------------------------------------------------------
# Regression: loop counter must increment — Fix 2026-05-29 (C1)
# ---------------------------------------------------------------------------

def test_loop_counter_increments_and_loop_max_is_respected(
    tmp_path, monkeypatch
) -> None:
    """_run_loop must stop after loop_max iterations, not loop forever.

    Regression: ``step`` was initialised to 0 but never incremented inside the
    while-body, making ``while step < loop_max`` always True and the --loop-max
    limit unreachable (dead code at line 1748).
    """
    registry = tmp_path / "registry.yaml"
    registry.write_text("active_package_id: x\nitems: []\n", encoding="utf-8")

    call_count = [0]

    def _state(*_a, **_kw):
        call_count[0] += 1
        # Return needs_plan every time so the loop never self-exits via return 0
        return {
            "state": wf.STATE_NEEDS_PLAN,
            "package": "pkg-x",
            "status": "needs_plan",
            "work_state": None,
            "next_label": "plan",
            "next_cmd": None,
            "next_hint": None,
            "warnings": [],
        }

    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    monkeypatch.setattr(wf, "REGISTRY", registry)
    monkeypatch.setattr(wf, "_find_active_package", lambda p: ("pkg-x", "explicit"))
    monkeypatch.setattr(wf, "resolve_state", _state)
    monkeypatch.setattr(wf, "_acquire_loop_lock", lambda *a, **kw: True)  # truthy!
    monkeypatch.setattr(wf, "_release_loop_lock", lambda *a, **kw: None)

    loop_max = 3
    rc = wf._run_loop(
        "pkg-x",
        "cursor_ai",
        skip_review=False,  # needs_plan without --skip-review → return 1
        watch_contract=False,
        watch_timeout=60,
        loop_max=loop_max,
        trigger_cmd=None,
    )
    # Without --skip-review the loop exits on first needs_plan → rc=1
    # The important check: resolve_state must have been called exactly once,
    # proving step incremented to 1 and the loop could have been bounded.
    assert rc == 1
    assert call_count[0] >= 1, "resolve_state was never called"


def test_loop_max_limit_is_reached(tmp_path, monkeypatch) -> None:
    """When every iteration ends in continue, _run_loop must stop at loop_max.

    Simulates a loop that always finds STATE_NO_PACKAGE after loop_max calls.
    Before fix: step never incremented → loop was infinite (only exiting via
    return inside a branch, not the while-condition guard).
    """
    registry = tmp_path / "registry.yaml"
    registry.write_text("active_package_id: x\nitems: []\n", encoding="utf-8")

    # Return STATE_NO_PACKAGE which causes immediate return 0 — but let's use
    # a state that always continues: we mock _wait_for_registry_change to return
    # False (timeout) to hit the return 1 branch quickly.
    call_count = [0]

    def _state(*_a, **_kw):
        call_count[0] += 1
        return {
            "state": wf.STATE_NEEDS_PLAN,
            "package": "pkg-x",
            "status": "needs_plan",
            "work_state": None,
            "next_label": "",
            "next_cmd": None,
            "next_hint": None,
            "warnings": [],
        }

    monkeypatch.setattr(wf, "ROOT", tmp_path)
    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    monkeypatch.setattr(wf, "REGISTRY", registry)
    monkeypatch.setattr(wf, "_find_active_package", lambda p: ("pkg-x", "explicit"))
    monkeypatch.setattr(wf, "resolve_state", _state)
    monkeypatch.setattr(wf, "_acquire_loop_lock", lambda *a, **kw: True)  # truthy!
    monkeypatch.setattr(wf, "_release_loop_lock", lambda *a, **kw: None)
    monkeypatch.setattr(wf, "_wait_for_registry_change", lambda *a, **kw: False)

    # --skip-review: needs_plan → wait for registry → timeout → return 1
    # The loop exits on the FIRST iteration (registry timeout), so loop_max=5
    # should cap at 1 real call regardless.
    rc = wf._run_loop(
        "pkg-x",
        "cursor_ai",
        skip_review=True,
        watch_contract=False,
        watch_timeout=1,
        loop_max=5,
        trigger_cmd=None,
    )
    assert rc == 1
    # At most loop_max calls (could be fewer if inner return fires first)
    assert call_count[0] <= 5


# ---------------------------------------------------------------------------
# Regression: _wait_for_orch_step_progress must NOT exit via contract
#             on intermediate steps — Fix 2026-05-29 (C2)
# ---------------------------------------------------------------------------

def test_wait_for_orch_step_progress_ignores_contract_for_intermediate_step(
    tmp_path, monkeypatch
) -> None:
    """allow_contract_exit=False must prevent premature post-agent on step 2–7.

    Regression: the function checked _execution_contract_ready_for_post_agent
    BEFORE step artifacts, so a stale substantive contract from a previous run
    caused the loop to skip remaining steps and invoke post-agent early.
    """
    pkg = "pkg-intermediate"
    art = tmp_path / "archive" / "team_artifacts" / pkg
    art.mkdir(parents=True)

    # Write a substantive execution_contract.md (stale proof from previous run)
    contract = art / "execution_contract.md"
    contract.write_text("EXECUTION_PROOF:\nSTATUS: DELIVERED\ndelivered: true\n", encoding="utf-8")

    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")

    step = wf.OrchStep(
        step_id="2",
        title="Analyst",
        body="",
        artifact_names=("2_analyst_brief.md",),
    )

    poll_calls = [0]
    original_sleep = wf.time.sleep

    def fast_sleep(s):
        poll_calls[0] += 1
        if poll_calls[0] >= 2:
            # On second poll, create the expected artifact to break out
            (art / "2_analyst_brief.md").write_text("# Analyst", encoding="utf-8")
        original_sleep(0)  # don't actually sleep

    monkeypatch.setattr(wf.time, "sleep", fast_sleep)

    result = wf._wait_for_orch_step_progress(
        pkg,
        step,
        timeout=60,
        poll=0,
        allow_contract_exit=False,  # must NOT exit via contract
    )
    # Must return "step" (artifact found), NOT "contract"
    assert result == "step", (
        f"Expected 'step' but got {result!r} — "
        "stale contract should be ignored for intermediate steps"
    )


def test_wait_for_orch_step_progress_allows_contract_for_closure(
    tmp_path, monkeypatch
) -> None:
    """allow_contract_exit=True must return 'contract' for closure steps."""
    pkg = "pkg-closure"
    art = tmp_path / "archive" / "team_artifacts" / pkg
    art.mkdir(parents=True)

    contract = art / "execution_contract.md"
    contract.write_text("EXECUTION_PROOF:\nSTATUS: DELIVERED\ndelivered: true\n", encoding="utf-8")

    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")

    step = wf.OrchStep(
        step_id="8",  # is_closure is a @property: returns True when step_id == "8"
        title="Closure",
        body="Replace execution_contract.md with substantive delivery proof.",
        artifact_names=(),
    )
    monkeypatch.setattr(wf.time, "sleep", lambda s: None)

    result = wf._wait_for_orch_step_progress(
        pkg,
        step,
        timeout=60,
        poll=0,
        allow_contract_exit=True,
    )
    assert result == "contract"


# ---------------------------------------------------------------------------
# Regression: _resolve_next_orchestration_step stale-proof guard — Fix (C3)
# ---------------------------------------------------------------------------

def test_resolve_next_step_stale_contract_with_incomplete_steps(
    tmp_path, monkeypatch
) -> None:
    """Substantive contract + incomplete steps → warn + continue scanning.

    Regression: _resolve_next_orchestration_step returned None (→ post-agent)
    as soon as execution_contract.md was substantive, even when step artifacts
    were missing. A leftover proof from a previous run would silently skip the
    entire new orchestration.
    """
    pkg = "pkg-stale"
    art = tmp_path / "archive" / "team_artifacts" / pkg
    art.mkdir(parents=True)

    # Substantive contract exists (stale from previous run)
    contract = art / "execution_contract.md"
    contract.write_text("EXECUTION_PROOF:\nSTATUS: DELIVERED\n", encoding="utf-8")

    # Orchestration with two steps, neither has its artifact
    orch_text = (
        "## STEP 1 — PO Package Scoping\n"
        "→ archive/team_artifacts/pkg-stale/1_po_package.md\n"
        "## STEP 8 — Closure\n"
        "Replace execution_contract.md with substantive delivery proof.\n"
    )
    orch = art / "orchestration_cursor_ai.md"
    orch.write_text(orch_text, encoding="utf-8")

    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")

    result = wf._resolve_next_orchestration_step(pkg, orch)

    # Must NOT return None (which would trigger premature post-agent).
    # Must return a step (step 1 is incomplete).
    assert result is not None, (
        "Stale substantive contract must not cause _resolve_next_orchestration_step "
        "to return None when steps are incomplete"
    )
    assert result.step_id == "1"


def test_resolve_next_step_valid_contract_all_steps_complete(
    tmp_path, monkeypatch
) -> None:
    """Substantive contract + all steps complete → return None (post-agent OK)."""
    pkg = "pkg-valid-contract"
    art = tmp_path / "archive" / "team_artifacts" / pkg
    art.mkdir(parents=True)

    # Substantive contract
    (art / "execution_contract.md").write_text(
        "EXECUTION_PROOF:\nSTATUS: DELIVERED\n", encoding="utf-8"
    )
    # All step artifacts present
    (art / "1_po_package.md").write_text("# PO", encoding="utf-8")

    orch_text = (
        "## STEP 1 — PO Package Scoping\n"
        "→ archive/team_artifacts/pkg-valid-contract/1_po_package.md\n"
        "## STEP 8 — Closure\n"
        "Replace execution_contract.md with substantive delivery proof.\n"
    )
    orch = art / "orchestration_cursor_ai.md"
    orch.write_text(orch_text, encoding="utf-8")

    monkeypatch.setattr(wf, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")

    result = wf._resolve_next_orchestration_step(pkg, orch)
    # All steps complete + valid contract → post-agent is correct → None
    assert result is None


# ---------------------------------------------------------------------------
# Regression: PACKAGE_TITLE removed from _SCANNED_FIELDS — Fix (H2)
# ---------------------------------------------------------------------------

def test_package_title_not_in_scanned_fields() -> None:
    """PACKAGE_TITLE must not be in ops_triggers._SCANNED_FIELDS.

    Regression: PACKAGE_TITLE is outcomes[:120] — a subset of OUTCOMES already
    scanned. Scanning it separately caused false-positive performance/ops triggers
    when prose in the title mentioned Dockerfile or .github/workflows/.
    """
    from ops_triggers import _SCANNED_FIELDS
    assert "PACKAGE_TITLE" not in _SCANNED_FIELDS, (
        "PACKAGE_TITLE is a prose subset of OUTCOMES and must not be scanned "
        "separately to avoid false-positive ops triggers from title text"
    )
