from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_autonomous as ra  # noqa: E402


def test_print_llm_context_summary_passes_fail_flag(monkeypatch, capsys):
    monkeypatch.setattr(ra, "SUMMARIZE_COST_LOGS", ROOT / "scripts" / "summarize_cost_logs.py")

    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=2, stdout="summary", stderr="")

    monkeypatch.setattr(ra.subprocess, "run", fake_run)

    rc = ra._print_llm_context_summary(fail_on_context_errors=True)

    assert rc == ra.EXIT_CLI_OR_CONTEXT_POLICY
    assert "--fail-on-context-errors" in calls[0]
    out = capsys.readouterr().out
    assert "Context-length incidents detected" in out


def test_main_post_agent_escalates_summary_gate(monkeypatch):
    monkeypatch.setattr(ra, "post_agent", lambda *args, **kwargs: 0)
    monkeypatch.setattr(ra, "_print_llm_context_summary", lambda **kwargs: ra.EXIT_CLI_OR_CONTEXT_POLICY)
    monkeypatch.setattr(
        ra.sys,
        "argv",
        [
            "run_autonomous.py",
            "--post-agent",
            "--package",
            "epoch-test",
            "--fail-on-context-errors",
        ],
    )

    rc = ra.main()

    assert rc == ra.EXIT_CLI_OR_CONTEXT_POLICY


def test_main_post_agent_preserves_non_stop_continue_when_summary_ok(monkeypatch):
    monkeypatch.setattr(ra, "post_agent", lambda *args, **kwargs: ra.EXIT_NON_STOP_CONTINUE)
    monkeypatch.setattr(ra, "_print_llm_context_summary", lambda **kwargs: 0)
    monkeypatch.setattr(
        ra.sys,
        "argv",
        [
            "run_autonomous.py",
            "--post-agent",
            "--package",
            "epoch-test",
        ],
    )

    assert ra.main() == ra.EXIT_NON_STOP_CONTINUE


def test_main_post_agent_continue_escalates_context_summary_gate(monkeypatch):
    monkeypatch.setattr(ra, "post_agent", lambda *args, **kwargs: ra.EXIT_NON_STOP_CONTINUE)
    monkeypatch.setattr(ra, "_print_llm_context_summary", lambda **kwargs: ra.EXIT_CLI_OR_CONTEXT_POLICY)
    monkeypatch.setattr(
        ra.sys,
        "argv",
        [
            "run_autonomous.py",
            "--post-agent",
            "--package",
            "epoch-test",
            "--fail-on-context-errors",
        ],
    )

    assert ra.main() == ra.EXIT_CLI_OR_CONTEXT_POLICY


def test_main_post_agent_requires_package_exit_cli_policy(monkeypatch):
    monkeypatch.setattr(
        ra.sys,
        "argv",
        ["run_autonomous.py", "--post-agent"],
    )

    assert ra.main() == ra.EXIT_CLI_OR_CONTEXT_POLICY


def test_run_dod_loop_blocks_full_pytest_for_regular_package(monkeypatch, capsys):
    called = False

    def fake_run(*args, **kwargs):
        nonlocal called
        called = True
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(ra.subprocess, "run", fake_run)

    # The test is about the full-pytest hard gate, not DoD cache behavior.
    # Disable cache so the subprocess mock doesn't need to emulate git calls.
    passed = ra.run_dod_loop(
        "pkg-123",
        {"DOD_COMMANDS": "python -m pytest tests/ -v"},
        use_dod_cache=False,
    )

    assert passed is False
    assert called is False
    err = capsys.readouterr().err
    assert "Full pytest suite is forbidden" in err


def test_run_dod_loop_allows_full_pytest_for_epoch_package(monkeypatch):
    calls: list[tuple[object, dict]] = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(ra.subprocess, "run", fake_run)

    passed = ra.run_dod_loop(
        "epoch-17-tail",
        {"DOD_COMMANDS": "python -m pytest tests/ -v"},
        use_dod_cache=False,
    )

    assert passed is True
    assert len(calls) == 1


def test_detect_dod_drift_from_exec_prompt(monkeypatch, tmp_path):
    prompt_dir = tmp_path / "archive" / "agent_prompts"
    prompt_dir.mkdir(parents=True)
    archived = prompt_dir / "epoch_router_accuracy_baseline_exec_prompt_quick_2026-04-23.md"
    archived.write_text(
        "Run:\n"
        ".\\.venv\\Scripts\\python.exe scripts/run_router_eval.py\n"
        ".\\.venv\\Scripts\\python.exe -m pytest tests/test_router_eval.py -v\n"
        "Return:\n"
        "done\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ra, "ROOT", tmp_path)

    drifted, reason = ra._detect_dod_drift_from_exec_prompt(
        "epoch-router-accuracy-baseline",
        {"DOD_COMMANDS": ".\\.venv\\Scripts\\python.exe scripts/run_router_eval.py --limit 1 --quiet; .\\.venv\\Scripts\\python.exe -m pytest tests/test_router_eval.py -v"},
    )

    assert drifted is True
    assert reason is not None
    assert "--limit 1 --quiet" in reason


def test_run_dod_loop_blocks_router_eval_without_openai_key(monkeypatch, capsys):
    called = False

    def fake_run(*args, **kwargs):
        nonlocal called
        called = True
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(ra.subprocess, "run", fake_run)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # The test is about the router-eval hard gate, not DoD cache behavior.
    # Disable cache so the subprocess mock doesn't need to emulate git calls.
    passed = ra.run_dod_loop(
        "epoch-router-accuracy-baseline",
        {
            "DOD_COMMANDS": ".\\.venv\\Scripts\\python.exe scripts/run_router_eval.py; .\\.venv\\Scripts\\python.exe -m pytest tests/test_router_eval.py -v"
        },
        use_dod_cache=False,
    )

    assert passed is False
    assert called is False
    err = capsys.readouterr().err
    assert "OPENAI_API_KEY" in err
    assert "cannot silently downgrade" in err


def test_normalize_text_file_to_utf8_rewrites_utf16(tmp_path):
    path = tmp_path / "execution_contract.md"
    path.write_bytes("STARTED\nПривет\n".encode("utf-16"))

    ra._normalize_text_file_to_utf8(path)

    raw = path.read_bytes()
    assert b"\x00" not in raw
    assert path.read_text(encoding="utf-8") == "STARTED\nПривет\n"


def test_inject_pytest_parallel_flag_when_allowed(monkeypatch):
    monkeypatch.setattr(ra, "_PYTEST_XDIST_AVAILABLE", True)
    cmd = ra._inject_pytest_parallel_flag(
        "python -m pytest tests/test_x.py -v",
        {"OUTCOMES": "allow_pytest_parallel"},
    )
    assert "pytest -n auto" in cmd


def test_pre_smoke_uses_lightweight_mode(monkeypatch):
    monkeypatch.setattr(
        ra.sys,
        "argv",
        ["run_autonomous.py", "--run-smoke-check-before-pipeline", "--max-loops", "1"],
    )
    calls: list[dict[str, object]] = []

    def fake_smoke(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(ra, "run_smoke", fake_smoke)
    monkeypatch.setattr(ra, "load_state", lambda *_args, **_kwargs: {"package": None, "rows": [], "contract": {}, "work_state": None})
    monkeypatch.setattr(ra, "decide_next_step", lambda *_args, **_kwargs: {"action": "ERROR", "command": [], "reasons": ["stop"]})

    rc = ra.main()

    assert rc == 2
    assert calls
    assert calls[0]["lightweight"] is True
    assert calls[0]["auto_prepare_epoch_demo"] is False
