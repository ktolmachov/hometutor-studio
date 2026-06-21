from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

PY = ROOT / ".venv" / "Scripts" / "python.exe"
if not PY.is_file():
    PY = Path(sys.executable)


def test_demo_workflow_list_exits_zero():
    proc = subprocess.run(
        [str(PY), "scripts/demo_workflow.py", "list"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "scenario_01" in proc.stdout


def test_resolve_path_command_finds_npm_on_windows(monkeypatch) -> None:
    import demo_workflow as workflow

    monkeypatch.setattr(workflow.shutil, "which", lambda name: f"C:/tools/{name}" if name == "npm.cmd" else None)
    monkeypatch.setattr(workflow.os, "name", "nt", raising=False)
    assert workflow._resolve_path_command("npm") == "C:/tools/npm.cmd"


def test_cmd_gifs_without_fast_flag(monkeypatch) -> None:
    import argparse

    import demo_workflow as workflow

    calls: list[list[str]] = []

    def fake_run(cmd, *, env=None, dry_run=False):
        calls.append(cmd)
        return 0

    monkeypatch.setattr(workflow, "_run", fake_run)
    monkeypatch.setattr(workflow, "_python_exe", lambda: PY)
    monkeypatch.setattr(workflow, "_resolve_run_dir", lambda _run: ("2026-06-20", ROOT / "doc/screenshots/2026-06-20"))

    args = argparse.Namespace(run="", dry_run=False)
    assert workflow.cmd_gifs(args) == 0
    assert calls[0][:2] == [str(PY), "scripts/make_demo_gifs.py"]
    assert "--no-optimize" not in calls[0]


def test_playwright_cmd_uses_resolved_npm(monkeypatch) -> None:
    import demo_workflow as workflow

    monkeypatch.setattr(workflow, "_resolve_path_command", lambda _name: "C:/tools/npm.cmd")
    cmd = workflow._playwright_cmd([])
    assert cmd[:3] == ["C:/tools/npm.cmd", "run", "test:e2e:demo"]


def test_scaffold_demo_scenario_dry_run(tmp_path, monkeypatch):
    scenarios = tmp_path / "scenarios"
    demos = tmp_path / "demos"
    scenarios.mkdir()
    demos.mkdir()

    import scaffold_demo_scenario as scaffold

    monkeypatch.setattr(scaffold, "SCENARIOS_DIR", scenarios)
    monkeypatch.setattr(scaffold, "DEMOS_DIR", demos)
    monkeypatch.setattr(scaffold, "ROOT", tmp_path)
    monkeypatch.setattr(scaffold, "GENERATE_DOC", tmp_path / "generate_demo_doc.py")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scaffold_demo_scenario.py",
            "--number",
            "99",
            "--slug",
            "test_flow",
            "--title",
            "Test Flow",
            "--dry-run",
        ],
    )
    assert scaffold.main() == 0
    assert not list(scenarios.glob("*.yaml"))
    assert not list(demos.glob("*.spec.ts"))
