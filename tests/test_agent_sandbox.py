from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import agent_sandbox
from agent_sandbox import SandboxViolationError


def test_safe_run_blocks_before_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def fake_run(*_args, **_kwargs):
        nonlocal called
        called = True
        return subprocess.CompletedProcess(["git"], 0)

    monkeypatch.setattr(agent_sandbox.subprocess, "run", fake_run)

    with pytest.raises(SandboxViolationError):
        agent_sandbox.safe_run(
            ["git", "reset", "--hard"],
            policy={"blocked_commands": [{"prefix": ["git", "reset", "--hard"]}]},
        )

    assert called is False


def test_safe_run_allows_and_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(agent_sandbox.subprocess, "run", fake_run)

    result = agent_sandbox.safe_run(
        ["python", "-m", "pytest", "tests/test_command_guard.py", "-v"],
        policy={"blocked_commands": []},
    )

    assert result.returncode == 0
    assert seen == [["python", "-m", "pytest", "tests/test_command_guard.py", "-v"]]


def test_safe_run_text_mode_defaults_to_utf8_replace(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_kw: dict[str, object] = {}

    def fake_run(cmd, **kw):
        captured_kw.update(kw)
        return subprocess.CompletedProcess(cmd, 0, stdout="")

    monkeypatch.setattr(agent_sandbox.subprocess, "run", fake_run)

    agent_sandbox.safe_run(
        ["python", "-c", "print('ok')"],
        policy={"blocked_commands": []},
        capture_output=True,
        text=True,
    )

    assert captured_kw["encoding"] == "utf-8"
    assert captured_kw["errors"] == "replace"


def test_tokenize_shell_command_strips_grouping_quotes_preserving_windows_paths() -> None:
    tokens = agent_sandbox.tokenize_shell_command(
        r'.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py '
        r'-v -k "simulator or what_if" --tb=short'
    )

    assert tokens == [
        r".\.venv\Scripts\python.exe",
        "-m",
        "pytest",
        "tests/test_smart_study_router.py",
        "-v",
        "-k",
        "simulator or what_if",
        "--tb=short",
    ]


def test_tokenize_shell_command_strips_python_c_quotes() -> None:
    tokens = agent_sandbox.tokenize_shell_command(
        ".\\.venv\\Scripts\\python.exe -c \"print('e2e')\""
    )

    assert tokens == [r".\.venv\Scripts\python.exe", "-c", "print('e2e')"]


def test_safe_run_shell_win32_npm_merges_streams(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    captured_kw: dict[str, object] = {}

    def fake_run(cmd, **kw):
        captured_kw.update(kw)
        return subprocess.CompletedProcess(cmd, 7, stdout="npm-child-out\n")

    monkeypatch.setattr(agent_sandbox.sys, "platform", "win32")
    monkeypatch.setattr(agent_sandbox.subprocess, "run", fake_run)
    monkeypatch.setattr(agent_sandbox.shutil, "which", lambda _: r"C:\node\npm.cmd")

    policy = {"blocked_commands": []}
    result = agent_sandbox.safe_run_shell("npm run e2e -- --grep smoke", cwd=str(ROOT), policy=policy)

    assert result.returncode == 7
    assert captured_kw["stderr"] == subprocess.STDOUT
    assert captured_kw["stdout"] == subprocess.PIPE
    assert captured_kw["cwd"] == str(ROOT)
    assert capsys.readouterr().out == "npm-child-out\n"


def test_close_package_dod_blocks_agent_controlled_dangerous_command() -> None:
    import close_package

    passed, results = close_package.run_dod(["git reset --hard"])

    assert passed is False
    assert results[0][1] == 2
    assert "sandbox blocked" in results[0][2]


def test_run_autonomous_dod_blocks_agent_controlled_dangerous_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import run_autonomous

    monkeypatch.setattr(run_autonomous, "_load_dod_cache", lambda _path: {})
    contract = {"DOD_COMMANDS": "git reset --hard"}

    assert run_autonomous.run_dod_loop("epoch-test", contract, use_dod_cache=False) is False
