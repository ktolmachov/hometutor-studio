from __future__ import annotations

import sys
from pathlib import Path
import tempfile
from types import SimpleNamespace
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prompt_utils import extract_dod_commands
import run_autonomous as ra


def _closure_resolution(
    mode: str,
    *,
    base_mode: str | None = None,
    matched: tuple[str, ...] = (),
    upgrade_reason: str | None = None,
):
    from prompt_utils import ClosureModeResolution

    paths = frozenset(matched)
    return ClosureModeResolution(
        mode=mode,
        base_mode=base_mode or mode,
        delivery_paths=paths,
        matched_write_set=paths,
        upgrade_reason=upgrade_reason,
    )


def test_capture_generated_prompt_uses_existing_orchestration_on_duplicate(
    tmp_path, monkeypatch
):
    pkg = "epoch-existing-orch"
    artifacts = tmp_path / "archive" / "team_artifacts" / pkg
    artifacts.mkdir(parents=True)
    orch = artifacts / "orchestration_cursor_ai.md"
    orch.write_text("# Existing orchestration\n\nDo the work.\n", encoding="utf-8")

    monkeypatch.setattr(ra, "ROOT", tmp_path)
    monkeypatch.setattr(ra, "TASK_FILE", tmp_path / "doc" / "current_task.md")
    monkeypatch.setattr(
        ra,
        "safe_run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="STOP: orchestration_cursor_ai.md already exists",
        ),
    )

    prompt = ra.capture_generated_prompt(
        [
            "python",
            "scripts/generate_orchestration_prompt.py",
            "--agent",
            "cursor_ai",
            "--package",
            pkg,
        ]
    )

    assert prompt == "# Existing orchestration\n\nDo the work."


def _patch_git(
    monkeypatch,
    diff_stdout: str = "",
    status_stdout: str = "",
    changed_paths: str = "app/flashcards.py\n",
):
    import prompt_utils as pu

    def _fake_run(args, **kwargs):
        if args[:3] == ["git", "diff", "HEAD"]:
            return SimpleNamespace(stdout=diff_stdout, returncode=0)
        if args[:2] == ["git", "status"]:
            return SimpleNamespace(stdout=status_stdout, returncode=0)
        if args[:3] == ["git", "rev-parse", "--verify"]:
            return SimpleNamespace(stdout="", returncode=0)
        if args[:3] == ["git", "cat-file", "-e"]:
            return SimpleNamespace(stdout="", returncode=0)
        if args[:3] == ["git", "diff-tree", "--no-commit-id"]:
            return SimpleNamespace(stdout=changed_paths, returncode=0)
        return SimpleNamespace(stdout="", returncode=0)

    monkeypatch.setattr(pu.subprocess, "run", _fake_run)
    monkeypatch.setattr(ra.subprocess, "run", _fake_run)


def test_detect_closure_mode_does_not_treat_execution_contract_as_execution(monkeypatch):
    root = Path(tempfile.mkdtemp())
    exec_contract = root / "archive" / "team_artifacts" / "epoch-demo" / "execution_contract.md"
    exec_contract.parent.mkdir(parents=True)
    exec_contract.write_text(
        "Changed files: no changes; implementation pre-existed.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(ra, "ROOT", root)
    _patch_git(monkeypatch, diff_stdout="tests/test_pipeline_guard.py\n")

    mode = ra._detect_closure_mode(
        "epoch-demo",
        {"PACKAGE_ID": "epoch-demo", "OUTCOMES": "Deliver new capability"},
    )

    # With the hardened validator, evidence without a commit SHA cannot be
    # classified as verification_only. It MUST fall through to 'unknown' so
    # the downstream gate blocks closure.
    assert mode == "unknown"


def test_detect_closure_mode_ignores_unrelated_source_changes_when_write_set_known(monkeypatch):
    root = Path(tempfile.mkdtemp())
    exec_contract = root / "archive" / "team_artifacts" / "epoch-demo" / "execution_contract.md"
    exec_contract.parent.mkdir(parents=True)
    exec_contract.write_text(
        "Changed files: no changes; implementation pre-existed.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(ra, "ROOT", root)
    _patch_git(monkeypatch, diff_stdout="tests/test_pipeline_guard.py\n")

    mode = ra._detect_closure_mode(
        "epoch-demo",
        {
            "PACKAGE_ID": "epoch-demo",
            "TARGET_ARTIFACTS": "`app/flashcards.py`",
        },
    )

    # Write-set known, no overlap, evidence invalid → 'unknown' (block).
    assert mode == "unknown"


def test_detect_closure_mode_accepts_valid_verification_only_evidence(monkeypatch):
    root = Path(tempfile.mkdtemp())
    exec_contract = root / "archive" / "team_artifacts" / "epoch-demo" / "execution_contract.md"
    exec_contract.parent.mkdir(parents=True)
    # Create a real file so validator's file-existence check passes.
    target = root / "app" / "flashcards.py"
    target.parent.mkdir(parents=True)
    target.write_text("# stub\n", encoding="utf-8")
    exec_contract.write_text(
        "Pre-existing delivery evidence:\n"
        "- commit: abc1234\n"
        "- files: app/flashcards.py\n"
        "- note: evidence_inconclusive_allowed\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(ra, "ROOT", root)
    _patch_git(monkeypatch, diff_stdout="", status_stdout="")

    mode = ra._detect_closure_mode(
        "epoch-demo",
        {"PACKAGE_ID": "epoch-demo", "TARGET_ARTIFACTS": "`app/flashcards.py`"},
    )

    assert mode == "verification_only"


def test_detect_closure_mode_treats_scripts_write_set_as_execution(monkeypatch):
    root = Path(tempfile.mkdtemp())
    exec_contract = root / "archive" / "team_artifacts" / "epoch-demo" / "execution_contract.md"
    exec_contract.parent.mkdir(parents=True)
    exec_contract.write_text(
        "Changed files: scripts/close_package.py\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(ra, "ROOT", root)
    _patch_git(monkeypatch, diff_stdout="scripts/close_package.py\n")

    mode = ra._detect_closure_mode(
        "epoch-demo",
        {"PACKAGE_ID": "epoch-demo", "TARGET_ARTIFACTS": "`scripts/close_package.py`"},
    )

    assert mode == "execution"


def test_plan_footer_uses_selected_agent_and_fresh_session_note():
    text = ra._self_close_footer_plan("strict", next_agent="kilo")
    assert f"{ra.DISPLAY_PYTHON} scripts/run_autonomous.py --agent kilo --budget-profile strict" in text
    assert "fresh Kilo session" in text


def test_execute_footer_uses_selected_agent():
    text = ra._self_close_footer_execute("epoch-demo", "strict", next_agent="kilo")
    assert (
        f"{ra.DISPLAY_PYTHON} scripts/run_autonomous.py "
        "--post-agent --package epoch-demo --budget-profile strict"
    ) in text
    assert "fresh Kilo session" in text


def test_execute_footer_non_stop_default_max_next_tasks_is_50():
    text = ra._self_close_footer_execute("epoch-demo", "strict", non_stop=True)
    assert "--non-stop-max-next-tasks 50" in text


def test_execute_footer_non_stop_allows_only_safe_wave_exit_one():
    text = ra._self_close_footer_execute("epoch-demo", "strict", non_stop=True)

    assert "-AllowedExitCodes @(0,1,10)" in text
    assert "Auto-promoting next package" in text
    assert "Now empty and no ready wave packages found" in text
    assert "without safe non-stop marker" in text


def test_execute_footer_sets_powershell_utf8_bootstrap():
    text = ra._self_close_footer_execute("epoch-demo", "strict", non_stop=True)

    assert "[Console]::OutputEncoding = $Utf8NoBom" in text
    assert '$env:PYTHONIOENCODING = "utf-8:replace"' in text
    assert "chcp 65001" in text


def test_execute_footer_regular_mode_still_fails_on_any_nonzero_exit():
    text = ra._self_close_footer_execute("epoch-demo", "strict", non_stop=False)

    assert "-AllowedExitCodes @(0,1)" not in text
    assert "[int[]]$AllowedExitCodes = @(0)" in text
    assert "if ($AllowedExitCodes -notcontains $rc)" in text


def test_plan_next_contract_rules_include_relaxed_readset_drift_guard():
    text = ra._self_close_footer_plan("strict", non_stop=True)

    assert "check_readset.py --profile strict" in text
    assert "--profile relaxed" in text
    assert "post-agent drift" in text


def test_write_post_closure_audit_task_archives_before_current_pointer(monkeypatch, tmp_path):
    root = tmp_path
    task_file = root / "doc" / "current_task.md"
    task_file.parent.mkdir(parents=True)

    monkeypatch.setattr(ra, "ROOT", root)
    monkeypatch.setattr(ra, "TASK_FILE", task_file)

    archive_path = ra._write_post_closure_audit_task("epoch-demo", "# audit\n")

    assert archive_path == root / "archive" / "team_artifacts" / "epoch-demo" / "post_closure_audit_task.md"
    assert archive_path.read_text(encoding="utf-8") == "# audit\n"
    assert task_file.read_text(encoding="utf-8") == "# audit\n"


def test_demo_wave_dod_uses_scenario_specific_commands():
    text = ra._wave_package_dod_commands("epoch-demo-scenario-08-trust")

    assert "pytest tests/" not in text
    assert "npm run demo:validate" in text
    assert "DEMO_SHOT_RUN='2026-01-08'" in text
    assert 'npm run test:e2e:demo -- --grep \'@demo Scenario 08\'' in text
    assert (
        f"{ra.DISPLAY_PYTHON} scripts\\validate_demo_contract.py "
        "--screenshots-dir doc\\screenshots\\2026-01-08 "
        "--require-screenshots --strict-captures --require-unique-shots"
    ) in text
    assert (
        f"{ra.DISPLAY_PYTHON} scripts\\generate_demo_doc.py "
        "--screenshots-dir doc\\screenshots\\2026-01-08 "
        "--output doc\\quickstart_demo.preview.md --no-final-sync"
    ) in text


def test_demo_wave_dod_is_split_into_four_commands():
    text = ra._wave_package_dod_commands("epoch-demo-scenario-08-trust")

    assert len(extract_dod_commands(text)) == 4


def test_non_demo_wave_dod_does_not_use_full_pytest():
    text = ra._wave_package_dod_commands("epoch-demo-pipeline-hardening")

    assert text == f"{ra.DISPLAY_PYTHON} scripts/check_backlog_drift.py"


def test_post_agent_blocks_verification_only_without_delivery_evidence(monkeypatch):
    root = Path(tempfile.mkdtemp())
    exec_contract = root / "archive" / "team_artifacts" / "epoch-demo" / "execution_contract.md"
    exec_contract.parent.mkdir(parents=True)
    exec_contract.write_text(
        "Changed files: no changes; implementation pre-existed.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(ra, "ROOT", root)
    monkeypatch.setattr(ra, "TASK_FILE", root / "doc" / "current_task.md")
    monkeypatch.setattr(
        ra,
        "load_state",
        lambda package_id: {
            "package": {"id": package_id},
            "contract": {"PACKAGE_ID": package_id, "OUTCOMES": "Deliver new capability"},
        },
    )
    monkeypatch.setattr(ra, "_normalize_text_file_to_utf8", lambda path: None)
    monkeypatch.setattr(ra, "_detect_dod_drift_from_exec_prompt", lambda *args, **kwargs: (False, None))
    monkeypatch.setattr(ra, "_append_verified_diff_to_exec_contract", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        ra,
        "_resolve_closure_mode",
        lambda *args, **kwargs: _closure_resolution("verification_only"),
    )

    called = {"run_dod": False}

    def _unexpected_run_dod(*args, **kwargs):
        called["run_dod"] = True
        return True

    monkeypatch.setattr(ra, "run_dod_loop", _unexpected_run_dod)

    rc = ra.post_agent("epoch-demo")

    assert rc == 5
    assert called["run_dod"] is False


def test_post_agent_treats_evidence_commit_write_set_overlap_as_execution(monkeypatch, tmp_path, capsys):
    pkg = "pkg-evidence-delivered"
    root = tmp_path
    (root / "app").mkdir(parents=True)
    (root / "app" / "x.py").write_text("# delivered\n", encoding="utf-8")
    (root / "doc").mkdir(parents=True)
    exec_contract = root / "archive" / "team_artifacts" / pkg / "execution_contract.md"
    exec_contract.parent.mkdir(parents=True)
    exec_contract.write_text(
        "Pre-existing delivery evidence:\n"
        "- commit: abc1234\n"
        "- files: app/x.py\n",
        encoding="utf-8",
    )

    _patch_git(monkeypatch, changed_paths="app/x.py\n")
    monkeypatch.setattr(ra, "ROOT", root)
    monkeypatch.setattr(ra, "TASK_FILE", root / "doc" / "current_task.md")
    monkeypatch.setattr(
        ra,
        "load_state",
        lambda package_id: {
            "package": {"id": package_id},
            "contract": {
                "PACKAGE_ID": package_id,
                "TARGET_ARTIFACTS": "`app/x.py`",
                "DOD_COMMANDS": f"{ra.DISPLAY_PYTHON} -m py_compile app/x.py",
            },
        },
    )
    monkeypatch.setattr(ra, "_run_quality_gates", lambda **kw: {})
    monkeypatch.setattr(ra, "_blocking_quality_gates", lambda _gates: [])
    monkeypatch.setattr(ra, "_normalize_text_file_to_utf8", lambda path: None)
    monkeypatch.setattr(ra, "_detect_dod_drift_from_exec_prompt", lambda *a, **k: (False, None))
    monkeypatch.setattr(ra, "_append_verified_diff_to_exec_contract", lambda *a, **k: None)
    monkeypatch.setattr(
        ra,
        "_resolve_closure_mode",
        lambda *a, **k: _closure_resolution(
            "execution",
            base_mode="verification_only",
            matched=("app/x.py",),
            upgrade_reason="evidence_commit",
        ),
    )
    monkeypatch.setattr(ra, "run_dod_loop", lambda *a, **k: True)
    monkeypatch.setattr(ra, "_build_proof_bundle", lambda *a, **k: None)
    monkeypatch.setattr(ra, "_wave_auto_continue", lambda *a, **k: None)
    monkeypatch.setattr(ra, "get_or_create_run_id", lambda: "test-run-evidence")

    closed_modes: list[str] = []

    def _fake_close(args):
        closed_modes.append(args.closure_mode)
        return 0

    monkeypatch.setattr(ra, "run_close_package_impl", _fake_close)

    rc = ra.post_agent(pkg)
    out = capsys.readouterr().out

    assert rc == 0
    assert closed_modes == ["execution"]
    assert "Evidence commit contains write-set paths" in out


def test_post_agent_blocks_started_marker_execution_contract(monkeypatch, tmp_path, capsys):
    pkg = "pkg-started-only"
    root = tmp_path
    (root / "doc").mkdir(parents=True)
    exec_contract = root / "archive" / "team_artifacts" / pkg / "execution_contract.md"
    exec_contract.parent.mkdir(parents=True)
    exec_contract.write_text("STARTED\n", encoding="utf-8")

    monkeypatch.setattr(ra, "ROOT", root)
    monkeypatch.setattr(ra, "TASK_FILE", root / "doc" / "current_task.md")
    monkeypatch.setattr(
        ra,
        "load_state",
        lambda package_id: {
            "package": {"id": package_id},
            "contract": {"PACKAGE_ID": package_id, "OUTCOMES": "- touchpoints: `app/x.py`"},
        },
    )
    monkeypatch.setattr(ra, "_run_quality_gates", lambda **kw: {})
    monkeypatch.setattr(ra, "_blocking_quality_gates", lambda _gates: [])
    monkeypatch.setattr(ra, "_normalize_text_file_to_utf8", lambda path: None)

    called = {"dod": False, "mode": False}

    def _unexpected_dod(*args, **kwargs):
        called["dod"] = True
        return True

    def _unexpected_mode(*args, **kwargs):
        called["mode"] = True
        return _closure_resolution("execution")

    monkeypatch.setattr(ra, "run_dod_loop", _unexpected_dod)
    monkeypatch.setattr(ra, "_resolve_closure_mode", _unexpected_mode)

    rc = ra.post_agent(pkg)
    out = capsys.readouterr().out

    assert rc == 3
    assert "STARTED marker" in out
    assert called == {"dod": False, "mode": False}


def test_post_agent_non_stop_returns_continue_after_mocked_close(monkeypatch, tmp_path):
    """Full post_agent path closing with DoD mocked; verifies EXIT_NON_STOP_CONTINUE (10)."""
    pkg = "pkg-nonstop-rc"
    root = tmp_path
    (root / "app").mkdir(parents=True)
    (root / "app" / "x.py").write_text("# x\n", encoding="utf-8")
    (root / "doc").mkdir(parents=True)
    task_file = root / "doc" / "current_task.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    exec_contract = root / "archive" / "team_artifacts" / pkg / "execution_contract.md"
    exec_contract.parent.mkdir(parents=True, exist_ok=True)
    exec_contract.write_text(
        "Changed files:\n"
        "- app/x.py implementation done.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(ra, "ROOT", root)
    monkeypatch.setattr(ra, "TASK_FILE", task_file)
    monkeypatch.setattr(
        ra,
        "load_state",
        lambda _pid: {
            "package": {"id": pkg},
            "contract": {
                "PACKAGE_ID": pkg,
                "TARGET_ARTIFACTS": "`app/x.py`",
                "DOD_COMMANDS": f"{ra.DISPLAY_PYTHON} -m py_compile app/x.py",
            },
        },
    )
    monkeypatch.setattr(ra, "_run_quality_gates", lambda **kw: {})
    monkeypatch.setattr(ra, "_blocking_quality_gates", lambda _gates: [])
    monkeypatch.setattr(ra, "_detect_dod_drift_from_exec_prompt", lambda *a, **k: (False, None))
    snap = ra._GitWorktreeSnapshot(all_paths=("app/x.py",))
    monkeypatch.setattr(ra, "_fetch_git_worktree_snapshot", lambda: snap)
    monkeypatch.setattr(ra, "_append_verified_diff_to_exec_contract", lambda *a, **k: None)
    monkeypatch.setattr(ra, "run_dod_loop", lambda *a, **k: True)
    monkeypatch.setattr(ra, "_build_proof_bundle", lambda *a, **k: None)
    monkeypatch.setattr(ra, "run_close_package_impl", lambda *_a, **_k: 0)
    monkeypatch.setattr(ra, "_wave_auto_continue", lambda *_a, **_k: None)
    monkeypatch.setattr(ra, "get_or_create_run_id", lambda: "test-run-ns")

    import pipeline_state as _pipeline_state_module

    monkeypatch.setattr(_pipeline_state_module, "update", lambda *_a, **_k: None)

    rc = ra.post_agent(
        pkg,
        non_stop=True,
        non_stop_max_next_tasks=5,
        non_stop_chain_step=0,
    )

    assert rc == ra.EXIT_NON_STOP_CONTINUE
    assert "TASK: Post-Closure SSoT Audit" in task_file.read_text(encoding="utf-8")


def test_post_agent_non_stop_returns_zero_when_chain_limit_hit(monkeypatch, tmp_path):
    pkg = "pkg-ns-limit"
    root = tmp_path
    (root / "app").mkdir(parents=True)
    (root / "app" / "x.py").write_text("# x\n", encoding="utf-8")
    (root / "doc").mkdir(parents=True)
    task_file = root / "doc" / "current_task.md"
    exec_contract = root / "archive" / "team_artifacts" / pkg / "execution_contract.md"
    exec_contract.parent.mkdir(parents=True, exist_ok=True)
    exec_contract.write_text("Changed files:\n- app/x.py\n", encoding="utf-8")

    monkeypatch.setattr(ra, "ROOT", root)
    monkeypatch.setattr(ra, "TASK_FILE", task_file)
    monkeypatch.setattr(
        ra,
        "load_state",
        lambda _pid: {
            "package": {"id": pkg},
            "contract": {
                "PACKAGE_ID": pkg,
                "TARGET_ARTIFACTS": "`app/x.py`",
                "DOD_COMMANDS": f"{ra.DISPLAY_PYTHON} -m py_compile app/x.py",
            },
        },
    )
    monkeypatch.setattr(ra, "_run_quality_gates", lambda **kw: {})
    monkeypatch.setattr(ra, "_blocking_quality_gates", lambda _gates: [])
    monkeypatch.setattr(ra, "_detect_dod_drift_from_exec_prompt", lambda *a, **k: (False, None))
    snap = ra._GitWorktreeSnapshot(all_paths=("app/x.py",))
    monkeypatch.setattr(ra, "_fetch_git_worktree_snapshot", lambda: snap)
    monkeypatch.setattr(ra, "_append_verified_diff_to_exec_contract", lambda *a, **k: None)
    monkeypatch.setattr(ra, "run_dod_loop", lambda *a, **k: True)
    monkeypatch.setattr(ra, "_build_proof_bundle", lambda *a, **k: None)
    monkeypatch.setattr(ra, "run_close_package_impl", lambda *_a, **_k: 0)
    monkeypatch.setattr(ra, "_wave_auto_continue", lambda *_a, **_k: None)
    monkeypatch.setattr(ra, "get_or_create_run_id", lambda: "test-run-limit")

    import pipeline_state as _pipeline_state_module

    monkeypatch.setattr(_pipeline_state_module, "update", lambda *_a, **_k: None)

    rc = ra.post_agent(
        pkg,
        non_stop=True,
        non_stop_max_next_tasks=3,
        non_stop_chain_step=3,
    )

    assert rc == ra.EXIT_SUCCESS


def test_post_agent_handoffs_deepseek_chat_api_blocked_contract(monkeypatch, capsys):
    """DeepSeek REST bridge cannot edit the repo; BLOCKED contracts skip closure (exit 11)."""
    root = Path(tempfile.mkdtemp())
    exec_contract = root / "archive" / "team_artifacts" / "epoch-demo" / "execution_contract.md"
    exec_contract.parent.mkdir(parents=True)
    exec_contract.write_text(
        "---\n"
        "generated_by: deepseek_agent_trigger.ts\n"
        "model: deepseek-v4-flash\n"
        "---\n\n"
        "BLOCKED: no local tool access\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(ra, "ROOT", root)
    monkeypatch.setattr(ra, "TASK_FILE", root / "doc" / "current_task.md")
    monkeypatch.setattr(
        ra,
        "load_state",
        lambda package_id: {
            "package": {"id": package_id},
            "contract": {"PACKAGE_ID": package_id, "OUTCOMES": "Deliver new capability"},
        },
    )
    monkeypatch.setattr(ra, "_run_quality_gates", lambda **kw: {})
    monkeypatch.setattr(ra, "_blocking_quality_gates", lambda _gates: [])
    monkeypatch.setattr(ra, "_normalize_text_file_to_utf8", lambda path: None)
    monkeypatch.setattr(ra, "_detect_dod_drift_from_exec_prompt", lambda *args, **kwargs: (False, None))
    monkeypatch.setattr(ra, "_append_verified_diff_to_exec_contract", lambda *args, **kwargs: None)

    called = {"run_dod": False}

    def _unexpected_run_dod(*args, **kwargs):
        called["run_dod"] = True
        return True

    monkeypatch.setattr(ra, "run_dod_loop", _unexpected_run_dod)

    rc = ra.post_agent("epoch-demo")
    out = capsys.readouterr().out

    assert rc == ra.EXIT_POST_AGENT_CHAT_API_HANDOFF
    assert called["run_dod"] is False
    assert "[HANDOFF]" in out
    assert "не закрывается" in out


def test_execution_contract_body_detects_deepseek_blocked_after_appendix() -> None:
    text = (
        "---\n"
        "generated_by: deepseek_agent_trigger.ts\n"
        "---\n\n"
        "BLOCKED: no local tool access\n\n"
        "## Pipeline-verified changed files (auto-appended by --post-agent)\n\n"
        "**Product files** _none_\n"
    )
    assert ra._execution_contract_is_deepseek_chat_api_blocked(text) is True


def test_post_agent_blocks_unknown_mode_and_mentions_inconclusive_marker(monkeypatch, capsys):
    root = Path(tempfile.mkdtemp())
    exec_contract = root / "archive" / "team_artifacts" / "epoch-demo" / "execution_contract.md"
    exec_contract.parent.mkdir(parents=True)
    exec_contract.write_text(
        "Changed files: no changes; implementation pre-existed.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(ra, "ROOT", root)
    monkeypatch.setattr(ra, "TASK_FILE", root / "doc" / "current_task.md")
    monkeypatch.setattr(
        ra,
        "load_state",
        lambda package_id: {
            "package": {"id": package_id},
            "contract": {"PACKAGE_ID": package_id, "OUTCOMES": "Deliver new capability"},
        },
    )
    monkeypatch.setattr(ra, "_normalize_text_file_to_utf8", lambda path: None)
    monkeypatch.setattr(ra, "_detect_dod_drift_from_exec_prompt", lambda *args, **kwargs: (False, None))
    monkeypatch.setattr(ra, "_append_verified_diff_to_exec_contract", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        ra,
        "_resolve_closure_mode",
        lambda *args, **kwargs: _closure_resolution("unknown", base_mode="unknown"),
    )

    called = {"run_dod": False}

    def _unexpected_run_dod(*args, **kwargs):
        called["run_dod"] = True
        return True

    monkeypatch.setattr(ra, "run_dod_loop", _unexpected_run_dod)

    rc = ra.post_agent("epoch-demo")
    err = capsys.readouterr().err

    assert rc == 6
    assert called["run_dod"] is False
    assert "evidence_inconclusive_allowed" in err


def test_post_agent_upgrades_unknown_to_execution_when_head_commit_has_write_set(monkeypatch, capsys):
    """When mode=unknown but HEAD commit changed write-set paths, upgrade to execution."""
    import tempfile
    root = Path(tempfile.mkdtemp())
    exec_contract = root / "archive" / "team_artifacts" / "epoch-demo" / "execution_contract.md"
    exec_contract.parent.mkdir(parents=True)
    exec_contract.write_text("Changed: app/foo.py — refactored.\n", encoding="utf-8")
    (root / "doc").mkdir(parents=True)

    monkeypatch.setattr(ra, "ROOT", root)
    monkeypatch.setattr(ra, "TASK_FILE", root / "doc" / "current_task.md")
    monkeypatch.setattr(
        ra,
        "load_state",
        lambda package_id: {
            "package": {"id": package_id},
            "contract": {
                "PACKAGE_ID": package_id,
                "OUTCOMES": "- touchpoints: `app/foo.py`",
            },
        },
    )
    monkeypatch.setattr(ra, "_normalize_text_file_to_utf8", lambda path: None)
    monkeypatch.setattr(ra, "_detect_dod_drift_from_exec_prompt", lambda *a, **kw: (False, None))
    monkeypatch.setattr(ra, "_append_verified_diff_to_exec_contract", lambda *a, **kw: None)
    from prompt_utils import ClosureModeResolution

    monkeypatch.setattr(
        ra,
        "_resolve_closure_mode",
        lambda *a, **kw: ClosureModeResolution(
            mode="execution",
            base_mode="unknown",
            delivery_paths=frozenset({"app/foo.py"}),
            matched_write_set=frozenset({"app/foo.py"}),
            upgrade_reason="head_commit",
        ),
    )
    monkeypatch.setattr(ra, "_fetch_git_worktree_snapshot", lambda: None)

    dod_called = {"v": False}

    def _mock_run_dod(*args, **kwargs):
        dod_called["v"] = True
        return True

    monkeypatch.setattr(ra, "run_dod_loop", _mock_run_dod)
    monkeypatch.setattr(ra, "run_close_package_impl", lambda *a, **kw: 0)
    # Return a fake path so .relative_to(ROOT) doesn't fail
    monkeypatch.setattr(
        ra, "_write_post_closure_audit_task",
        lambda *a, **kw: root / "archive" / "audit_task.md",
    )
    monkeypatch.setattr(ra, "_wave_auto_continue", lambda *a, **kw: None)

    rc = ra.post_agent("epoch-demo")
    out = capsys.readouterr().out

    assert rc == 0, f"expected 0, got {rc}"
    assert dod_called["v"], "DoD should run after upgrade to execution mode"
    assert "upgrading to execution mode" in out.lower() or "upgraded" in out.lower() or "execution" in out


def test_compute_dod_cache_key_changes_when_conftest_changes(monkeypatch, tmp_path):
    # Isolate ROOT so the test doesn't depend on repo files.
    root = tmp_path
    (root / "app").mkdir()
    (root / "tests").mkdir()
    (root / "app" / "x.py").write_text("print('x')\n", encoding="utf-8")
    conftest = root / "tests" / "conftest.py"
    conftest.write_text("# v1\n", encoding="utf-8")

    monkeypatch.setattr(ra, "ROOT", root)

    def _fake_run(args, **kwargs):
        if args[:3] == ["git", "rev-parse", "HEAD"]:
            return SimpleNamespace(stdout="deadbeef\n", returncode=0)
        if args[:2] == ["git", "status"]:
            return SimpleNamespace(stdout="", returncode=0)
        return SimpleNamespace(stdout="", returncode=0)

    monkeypatch.setattr(ra.subprocess, "run", _fake_run)
    monkeypatch.setattr(ra, "_has_pytest_xdist", lambda: False)
    monkeypatch.setattr(ra, "_contract_allows_pytest_parallel", lambda _c: False)

    contract = {"TARGET_ARTIFACTS": "`app/x.py`"}
    key1 = ra._compute_dod_cache_key(contract, [".\\.venv\\Scripts\\python.exe -m py_compile app/x.py"])
    conftest.write_text("# v2\n", encoding="utf-8")
    key2 = ra._compute_dod_cache_key(contract, [".\\.venv\\Scripts\\python.exe -m py_compile app/x.py"])

    assert key1 != key2


def test_main_does_not_override_existing_home_rag_run_id(monkeypatch):
    monkeypatch.setenv("HOME_RAG_RUN_ID", "parent_run")

    class _NoOpTimer:
        def reset(self):  # noqa: D401
            return None

        def print_summary(self):
            return None

        def flush(self):
            return None

    monkeypatch.setattr(ra, "_TIMER", _NoOpTimer())
    monkeypatch.setattr(ra, "cleanup_old_logs", lambda *a, **k: None)
    monkeypatch.setattr(ra, "_main_impl", lambda: 0)

    rc = ra.main()
    assert rc == 0
    assert ra.os.environ.get("HOME_RAG_RUN_ID") == "parent_run"


def test_main_blocks_when_same_package_run_is_live(monkeypatch, capsys):
    monkeypatch.setattr(ra.sys, "argv", ["run_autonomous.py", "--package", "epoch-demo"])
    monkeypatch.setattr(
        ra,
        "package_run_conflict",
        lambda package: {"pid": 123, "run_id": "run-1"} if package == "epoch-demo" else None,
    )

    rc = ra.main()
    captured = capsys.readouterr()

    assert rc == ra.EXIT_LOCK_CONFLICT
    assert "package run lock" in captured.err
    assert "run-1" in captured.err


def test_main_converts_internal_system_exit_to_return_code(monkeypatch):
    class _NoOpTimer:
        def reset(self):  # noqa: D401
            return None

        def print_summary(self):
            return None

        def flush(self):
            return None

    monkeypatch.setattr(ra, "_TIMER", _NoOpTimer())
    monkeypatch.setattr(ra, "cleanup_old_logs", lambda *a, **k: None)
    monkeypatch.setattr(ra, "cleanup_stale_pid_registrations", lambda *a, **k: None)
    monkeypatch.setattr(ra, "_pipeline_finalize_for_exit", lambda *a, **k: None)
    monkeypatch.setattr(ra, "write_run_result", lambda *a, **k: None)
    monkeypatch.setattr(ra, "_main_impl", lambda: (_ for _ in ()).throw(SystemExit(7)))

    assert ra.main() == 7


def test_run_agent_headless_blocks_when_current_task_lock_held(monkeypatch, tmp_path):
    # Force lock to exist so the lock acquisition fails.
    doc_dir = tmp_path / "doc"
    doc_dir.mkdir()
    lock_path = doc_dir / "current_task.md.lock"
    lock_path.write_text("pid=123\n", encoding="utf-8")

    monkeypatch.setattr(ra, "TASK_LOCK_FILE", lock_path)
    monkeypatch.setattr(ra, "TASK_FILE", doc_dir / "current_task.md")
    monkeypatch.setattr(ra, "_self_close_footer_execute", lambda *a, **k: "")
    monkeypatch.setattr(ra, "_self_close_footer_plan", lambda *a, **k: "")
    monkeypatch.setattr(ra, "write_task_file_for_cursor", lambda *a, **k: True)

    with pytest.raises(SystemExit) as exc:
        ra.run_agent_headless(
            "cursor_ai",
            "hi",
            "epoch-demo",
            budget_profile="strict",
        )
    assert int(exc.value.code) == ra.EXIT_LOCK_CONFLICT


def test_run_agent_headless_windows_contract_command_is_utf8(monkeypatch, tmp_path):
    doc_dir = tmp_path / "doc"
    doc_dir.mkdir()
    captured = {}

    monkeypatch.setattr(ra, "ROOT", tmp_path)
    monkeypatch.setattr(ra, "TASK_LOCK_FILE", doc_dir / "current_task.md.lock")
    monkeypatch.setattr(ra, "TASK_FILE", doc_dir / "current_task.md")
    monkeypatch.setattr(ra, "_self_close_footer_execute", lambda *a, **k: "")

    def _capture_task(**kwargs):
        captured.update(kwargs)
        return True

    monkeypatch.setattr(ra, "write_task_file_for_cursor", _capture_task)

    result = ra.run_agent_headless(
        "cursor_ai",
        "Do the work.",
        "epoch-demo",
        budget_profile="strict",
    )

    assert result is False
    banner = captured["no_pause_banner"]
    assert "Set-Content -Path archive/team_artifacts/epoch-demo/execution_contract.md" in banner
    assert "-Encoding utf8" in banner
    assert "Out-File archive/team_artifacts/epoch-demo/execution_contract.md" not in banner


def test_sync_main_returns_failed_close_package_code(monkeypatch):
    root = Path(tempfile.mkdtemp())
    monkeypatch.setattr(ra, "ROOT", root)
    monkeypatch.setattr(ra.sys, "argv", ["run_autonomous.py", "--max-loops", "1"])
    monkeypatch.setattr(
        ra,
        "load_state",
        lambda package=None: {
            "package": "epoch-demo",
            "contract": {"PACKAGE_ID": "epoch-demo", "TARGET_ARTIFACTS": "`app/demo.py`"},
        },
    )
    monkeypatch.setattr(
        ra,
        "decide_next_step",
        lambda state, agent, package=None: {"action": "EXECUTION_AUTO", "command": ["noop"], "reasons": []},
    )
    monkeypatch.setattr(ra, "capture_generated_prompt", lambda *args, **kwargs: "prompt")
    monkeypatch.setattr(ra, "run_agent_headless", lambda *args, **kwargs: True)
    monkeypatch.setattr(ra, "run_dod_loop", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        ra,
        "_resolve_closure_mode",
        lambda *args, **kwargs: _closure_resolution("execution", matched=("app/demo.py",)),
    )
    monkeypatch.setattr(
        ra,
        "_fetch_git_worktree_snapshot",
        lambda: ra._GitWorktreeSnapshot(all_paths=()),
    )

    def _fake_run(args, **kwargs):
        if "scripts/close_package.py" in args:
            return SimpleNamespace(returncode=2, stdout="", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(ra.subprocess, "run", _fake_run)
    monkeypatch.setattr(
        "scripts.prompt_utils.git_head_commit_src_files",
        lambda root=None: set(),
    )

    assert ra.main() == 2
