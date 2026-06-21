from __future__ import annotations

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import close_package as cp  # noqa: E402
import git_mock_helpers as gm  # noqa: E402
import prompt_utils as pu  # noqa: E402


def test_pipeline_metrics_closure_row_uses_artifact_values(tmp_path, monkeypatch):
    package_id = "epoch-demo"
    team_artifacts = tmp_path / "archive" / "team_artifacts"
    package_dir = team_artifacts / package_id
    package_dir.mkdir(parents=True)
    (package_dir / "dod_cache.json").write_text(
        json.dumps({"result": "pass", "commands": ["pytest"]}),
        encoding="utf-8",
    )
    (package_dir / "execution_contract.md").write_text(
        "Execution proof\nNo follow-up work.\n",
        encoding="utf-8",
    )
    metrics_dir = team_artifacts / "_metrics"
    metrics_dir.mkdir(parents=True)
    (metrics_dir / "cursor_agent_trigger.jsonl").write_text(
        json.dumps(
            {
                "event": "cursor_agent_prompt",
                "status": "finished",
                "exit_code": 0,
                "retry_count": 1,
                "contract_path": f"archive/team_artifacts/{package_id}/execution_contract.md",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    metrics_path = tmp_path / "archive" / "pipeline_metrics.md"

    monkeypatch.setattr(cp, "TEAM_ARTIFACTS", team_artifacts)
    monkeypatch.setattr(cp, "PIPELINE_METRICS", metrics_path)
    monkeypatch.setattr(cp, "_compute_complexity_cell", lambda _package_id: "low/1.0")

    cp._append_pipeline_metrics(package_id, "2026-05-08", "execution")

    text = metrics_path.read_text(encoding="utf-8")
    assert "| epoch-demo | 2026-05-08 | execution | PASS | 1 | 0 | 0 | low/1.0 |" in text
    assert "TBD" not in text


def test_pipeline_metrics_closure_row_uses_deepseek_trigger_metrics(tmp_path, monkeypatch):
    package_id = "epoch-demo"
    team_artifacts = tmp_path / "archive" / "team_artifacts"
    package_dir = team_artifacts / package_id
    package_dir.mkdir(parents=True)
    (package_dir / "dod_cache.json").write_text(
        json.dumps({"result": "pass", "commands": ["pytest"]}),
        encoding="utf-8",
    )
    (package_dir / "execution_contract.md").write_text(
        "Execution proof\nNo follow-up work.\n",
        encoding="utf-8",
    )
    metrics_dir = team_artifacts / "_metrics"
    metrics_dir.mkdir(parents=True)
    (metrics_dir / "deepseek_agent_trigger.jsonl").write_text(
        json.dumps(
            {
                "event": "deepseek_agent_prompt",
                "status": "finished",
                "exit_code": 0,
                "retry_count": 1,
                "contract_path": f"archive/team_artifacts/{package_id}/execution_contract.md",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    metrics_path = tmp_path / "archive" / "pipeline_metrics.md"

    monkeypatch.setattr(cp, "TEAM_ARTIFACTS", team_artifacts)
    monkeypatch.setattr(cp, "PIPELINE_METRICS", metrics_path)
    monkeypatch.setattr(cp, "_compute_complexity_cell", lambda _package_id: "low/1.0")

    cp._append_pipeline_metrics(package_id, "2026-05-08", "execution")

    text = metrics_path.read_text(encoding="utf-8")
    assert "| epoch-demo | 2026-05-08 | execution | PASS | 1 | 0 | 0 | low/1.0 |" in text


def test_detect_dod_drift_from_exec_prompt(tmp_path, monkeypatch):
    archive_dir = tmp_path / "archive" / "agent_prompts"
    archive_dir.mkdir(parents=True)
    archived = archive_dir / "epoch_router_accuracy_baseline_exec_prompt_quick_2026-04-23.md"
    archived.write_text(
        "Run:\n"
        ".\\.venv\\Scripts\\python.exe scripts/run_router_eval.py\n"
        ".\\.venv\\Scripts\\python.exe -m pytest tests/test_router_eval.py -v\n"
        "Return:\n"
        "done\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cp, "ARCHIVE_DIR", archive_dir)
    monkeypatch.setattr(cp, "ROOT", tmp_path)

    drifted, reason = cp._detect_dod_drift_from_exec_prompt(
        "epoch-router-accuracy-baseline",
        [".\\.venv\\Scripts\\python.exe scripts/run_router_eval.py --limit 1 --quiet"],
    )

    assert drifted is True
    assert reason is not None
    assert "--limit 1 --quiet" in reason


def test_provider_prereq_blockers_flag_router_eval_without_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    blockers = cp._provider_prereq_blockers(
        "epoch-router-accuracy-baseline",
        [".\\.venv\\Scripts\\python.exe scripts/run_router_eval.py"],
    )

    assert len(blockers) == 1
    assert "OPENAI_API_KEY" in blockers[0]


def test_execution_contract_content_blocks_command_plan_proof() -> None:
    blockers = cp._execution_contract_content_blockers(
        "---\n"
        "generated_by: deepseek_agent_trigger.ts\n"
        "---\n"
        "I'll start by creating the execution contract with `STARTED`.\n"
        "```bash\n"
        "echo \"STARTED\" > archive/team_artifacts/epoch-demo/execution_contract.md\n"
        "cat archive/team_artifacts/epoch-demo/orchestration_continue.md\n"
        "```"
    )

    assert blockers == [
        "execution_contract.md looks like a command plan, not execution proof"
    ]


def test_execution_contract_content_allows_execution_proof() -> None:
    blockers = cp._execution_contract_content_blockers(
        "EXECUTION_PROOF:\n\n"
        "Summary: Delivered the requested behavior.\n\n"
        "Changed files:\n"
        "- app/smart_study_router.py\n"
        "- tests/test_smart_study_router.py\n\n"
        "Verification:\n"
        "- .\\.venv\\Scripts\\python.exe -m pytest tests/test_smart_study_router.py -v --tb=short: PASS\n"
    )

    assert blockers == []


def test_close_package_requires_proof_manifest_when_run_id_present(tmp_path, monkeypatch):
    import pipeline_events as pe
    import proof_bundle as pb

    package_id = "epoch-demo"
    tasklist = tmp_path / "doc" / "tasklist.md"
    tasklist.parent.mkdir(parents=True)
    tasklist.write_text("stub", encoding="utf-8")
    artifact_dir = tmp_path / "archive" / "team_artifacts" / package_id
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "execution_contract.md").write_text("proof\n", encoding="utf-8")

    runs_root = tmp_path / "logs" / "autonomous_runs"
    monkeypatch.setenv("HOME_RAG_RUN_ID", "run-missing-proof")
    monkeypatch.setattr(cp, "ROOT", tmp_path)
    monkeypatch.setattr(cp, "TASKLIST", tasklist)
    monkeypatch.setattr(cp, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    monkeypatch.setattr(pb, "ROOT", tmp_path)
    monkeypatch.setattr(pb, "AUTONOMOUS_RUNS_ROOT", runs_root)
    monkeypatch.setattr(pe, "AUTONOMOUS_RUNS_ROOT", runs_root)
    monkeypatch.setattr(pe, "CURRENT_DIR", runs_root / "current")
    monkeypatch.setattr(pe, "ORPHAN_DIR", runs_root / "_orphan")
    monkeypatch.setattr(cp, "parse_truth_view_from_registry", lambda: [{"package": package_id, "status": "wip"}])
    monkeypatch.setattr(
        cp,
        "_parse_contract",
        lambda _text, _package: {"PACKAGE_ID": package_id, "TARGET_ARTIFACTS": "`app/demo.py`"},
    )
    monkeypatch.setattr(cp, "_detect_dod_drift_from_exec_prompt", lambda *_args: (False, None))
    monkeypatch.setattr(cp, "_provider_prereq_blockers", lambda *_args: [])
    monkeypatch.setattr(cp, "_git_changed_paths_once", lambda _root: {"app/demo.py"})
    monkeypatch.setattr(
        cp,
        "_resolve_closure_mode",
        lambda *_args, **_kwargs: pu.ClosureModeResolution(
            mode="execution",
            base_mode="execution",
            delivery_paths=frozenset({"tests/test_foo.py"}),
            matched_write_set=frozenset({"tests/test_foo.py"}),
        ),
    )

    rc = cp.run_close_package_impl(
        cp.ClosePackageArgs(package=package_id, skip_dod=True, closure_mode="execution")
    )

    assert rc == 2
    event_log = runs_root / "run-missing-proof" / "event_log.jsonl"
    assert "PROOF_MISSING" in event_log.read_text(encoding="utf-8")


def test_close_without_dod_requires_hitl_approval(capsys):
    ok = cp._close_without_dod_approved(
        cp.ClosePackageArgs(approve_close_without_dod=False),
        reason="--skip-dod was requested",
    )

    assert ok is False
    assert "close_without_dod" in capsys.readouterr().err


def test_close_without_dod_accepts_explicit_hitl_approval() -> None:
    ok = cp._close_without_dod_approved(
        cp.ClosePackageArgs(approve_close_without_dod=True),
        reason="contract has no DOD_COMMANDS",
    )

    assert ok is True


def test_verification_only_evidence_requires_commit_and_files(tmp_path, monkeypatch):
    team_artifacts = tmp_path / "archive" / "team_artifacts" / "epoch-demo"
    team_artifacts.mkdir(parents=True)
    (team_artifacts / "execution_contract.md").write_text(
        "Changed files: no changes; implementation pre-existed.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cp, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")

    blockers = cp._verification_only_evidence_blockers("epoch-demo", "verification_only")

    assert blockers
    assert "Pre-existing delivery evidence" in blockers[0] or "commit SHA" in blockers[0]


def test_verification_only_evidence_blocks_when_closure_mode_unknown(tmp_path, monkeypatch):
    """Regression: caller forgot --closure-mode (default 'unknown').

    Previously `_verification_only_evidence_blockers` short-circuited to [] for
    any mode != 'verification_only', letting invalid proof slip through.
    After the fix, 'unknown' must run the same evidence validation as
    'verification_only'.
    """
    team_artifacts = tmp_path / "archive" / "team_artifacts" / "epoch-demo"
    team_artifacts.mkdir(parents=True)
    (team_artifacts / "execution_contract.md").write_text(
        "- commit: pre-existing in current branch history\n"
        "- files: app/flashcards.py\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cp, "ROOT", tmp_path)
    monkeypatch.setattr(cp, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")

    blockers = cp._verification_only_evidence_blockers("epoch-demo", "unknown")

    assert blockers, "'unknown' mode must not bypass evidence validation"


def test_verification_only_evidence_skipped_only_for_execution_mode(tmp_path, monkeypatch):
    team_artifacts = tmp_path / "archive" / "team_artifacts" / "epoch-demo"
    team_artifacts.mkdir(parents=True)
    monkeypatch.setattr(cp, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")

    assert cp._verification_only_evidence_blockers("epoch-demo", "execution") == []


def test_detect_closure_mode_returns_unknown_when_evidence_invalid(tmp_path, monkeypatch):
    """Shared helper: invalid evidence must not be labelled verification_only."""
    exec_contract = tmp_path / "archive" / "team_artifacts" / "epoch-demo" / "execution_contract.md"
    exec_contract.parent.mkdir(parents=True)
    exec_contract.write_text(
        "Pre-existing delivery evidence:\n"
        "- commit: pre-existing in current branch history\n"
        "- files: app/missing_file.py\n",
        encoding="utf-8",
    )
    gm.patch_git_clean(monkeypatch, pu.subprocess)

    mode = pu.detect_closure_mode(
        "epoch-demo",
        {"TARGET_ARTIFACTS": "`app/missing_file.py`"},
        root=tmp_path,
    )
    assert mode == "unknown"


def test_detect_closure_mode_returns_verification_only_when_evidence_valid(tmp_path, monkeypatch):
    exec_contract = tmp_path / "archive" / "team_artifacts" / "epoch-demo" / "execution_contract.md"
    exec_contract.parent.mkdir(parents=True)
    real_file = tmp_path / "app" / "real.py"
    real_file.parent.mkdir(parents=True)
    real_file.write_text("# stub\n", encoding="utf-8")
    exec_contract.write_text(
        "Pre-existing delivery evidence:\n"
        "- commit: abc1234\n"
        "- files: app/real.py\n"
        "- note: evidence_inconclusive_allowed\n",
        encoding="utf-8",
    )
    gm.patch_git_clean(monkeypatch, pu.subprocess)

    mode = pu.detect_closure_mode(
        "epoch-demo",
        {"TARGET_ARTIFACTS": "`app/real.py`"},
        root=tmp_path,
    )
    assert mode == "verification_only"


def test_detect_closure_mode_respects_precomputed_and_skips_git(
    tmp_path, monkeypatch
) -> None:
    """If precomputed_* provided, _changed_src_files (git) is not used."""
    def _should_not_call_git() -> set[str] | None:
        msg = "_changed_src_files must not run when precomputed is set"
        raise AssertionError(msg)

    monkeypatch.setattr(pu, "_changed_src_files", _should_not_call_git)
    mode = pu.detect_closure_mode(
        "epoch-demo",
        {"TARGET_ARTIFACTS": "`app/real.py`"},
        root=tmp_path,
        precomputed_src_changed=set(),
        precomputed_evidence_valid=True,
    )
    assert mode == "verification_only"


def test_detect_closure_mode_returns_verification_only_with_explicit_changed_path(tmp_path, monkeypatch):
    exec_contract = tmp_path / "archive" / "team_artifacts" / "epoch-demo" / "execution_contract.md"
    exec_contract.parent.mkdir(parents=True)
    real_file = tmp_path / "app" / "real.py"
    real_file.parent.mkdir(parents=True)
    real_file.write_text("# stub\n", encoding="utf-8")
    exec_contract.write_text(
        "Pre-existing delivery evidence:\n"
        "- commit: abc1234\n"
        "- files: app/real.py\n",
        encoding="utf-8",
    )
    gm.patch_git_with_changed_file(monkeypatch, pu.subprocess, filename="app/real.py")

    mode = pu.detect_closure_mode(
        "epoch-demo",
        {"TARGET_ARTIFACTS": "`app/real.py`"},
        root=tmp_path,
    )
    assert mode == "verification_only"


def test_verification_only_evidence_requires_existing_files(tmp_path, monkeypatch):
    team_artifacts = tmp_path / "archive" / "team_artifacts" / "epoch-demo"
    team_artifacts.mkdir(parents=True)
    (team_artifacts / "execution_contract.md").write_text(
        "Pre-existing delivery evidence:\n"
        "- commit: abc1234\n"
        "- files: app/ui/flashcard_panel.py\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cp, "ROOT", tmp_path)
    monkeypatch.setattr(cp, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    gm.patch_git_clean(monkeypatch, pu.subprocess)

    blockers = cp._verification_only_evidence_blockers("epoch-demo", "verification_only")

    assert blockers
    assert "missing file" in blockers[0]


def test_semantic_claim_blockers_detect_unproven_eval_claims():
    contract = {
        "OUTCOMES": (
            "Eval runner gives deterministic quality metrics in mock mode. "
            "CI gate fails regressions and publishes JSON report."
        )
    }
    dod_results = [
        (
            "python tests/eval/run_eval.py --mock",
            0,
            '{"summary":{"answer_groundedness":null,"tutor_coherence":null}}',
        ),
        (
            "python scripts/eval_ci_gate.py --mock",
            0,
            '{"status":"warn","comparable_to_baseline":false}',
        ),
    ]

    blockers = cp._semantic_claim_blockers(contract, dod_results)

    assert any("answer_groundedness = null" in item for item in blockers)
    assert any("skipped baseline comparison" in item for item in blockers)
    assert any("warn mode" in item for item in blockers)


def test_close_package_reports_standardized_verification_policy(monkeypatch, tmp_path, capsys):
    tasklist = tmp_path / "tasklist.md"
    tasklist.write_text("## Now\n\n| Package | Status |\n|---|---|\n| epoch-demo | ready |\n", encoding="utf-8")

    monkeypatch.setattr(cp, "TASKLIST", tasklist)
    monkeypatch.setattr(cp, "_parse_contract", lambda *_args, **_kwargs: {"PACKAGE_ID": "epoch-demo"})
    monkeypatch.setattr(cp, "_detect_dod_drift_from_exec_prompt", lambda *_args, **_kwargs: (False, None))
    monkeypatch.setattr(cp, "_provider_prereq_blockers", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        cp,
        "_resolve_closure_mode",
        lambda *_args, **_kwargs: pu.ClosureModeResolution(
            mode="verification_only",
            base_mode="verification_only",
            delivery_paths=frozenset(),
            matched_write_set=frozenset(),
        ),
    )
    monkeypatch.setattr(
        cp,
        "_verification_only_evidence_blockers",
        lambda *_args, **_kwargs: ["missing commit SHA for the pre-existing delivery"],
    )
    monkeypatch.setattr(cp.sys, "argv", ["close_package.py", "--package", "epoch-demo"])

    rc = cp.main()
    err = capsys.readouterr().err

    assert rc == 2
    assert "  verification-only closure requires commit SHA + concrete file paths" in err
    assert "evidence_inconclusive_allowed" in err


def test_close_package_accepts_execution_when_evidence_commit_touches_write_set(
    monkeypatch, tmp_path, capsys
):
    package_id = "epoch-demo"
    tasklist = tmp_path / "doc" / "tasklist.md"
    tasklist.parent.mkdir(parents=True)
    tasklist.write_text("stub", encoding="utf-8")
    app_file = tmp_path / "app" / "demo.py"
    app_file.parent.mkdir(parents=True)
    app_file.write_text("# delivered\n", encoding="utf-8")
    exec_contract = tmp_path / "archive" / "team_artifacts" / package_id / "execution_contract.md"
    exec_contract.parent.mkdir(parents=True)
    exec_contract.write_text(
        "Pre-existing delivery evidence:\n"
        "- commit: abc1234\n"
        "- files: app/demo.py\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(cp, "ROOT", tmp_path)
    monkeypatch.setattr(cp, "TASKLIST", tasklist)
    monkeypatch.setattr(cp, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    monkeypatch.setattr(cp, "parse_truth_view_from_registry", lambda: [])
    monkeypatch.setattr(cp, "_registry_item_status", lambda _pkg: "ready")
    monkeypatch.setattr(
        cp,
        "_parse_contract",
        lambda _text, _package: {
            "PACKAGE_ID": package_id,
            "USER_STORIES": "n/a (infra package)",
            "TARGET_ARTIFACTS": "`app/demo.py`",
            "DOD_COMMANDS": ".\\.venv\\Scripts\\python.exe -m py_compile app/demo.py",
        },
    )
    monkeypatch.setattr(cp, "_detect_dod_drift_from_exec_prompt", lambda *_args: (False, None))
    monkeypatch.setattr(cp, "_provider_prereq_blockers", lambda *_args: [])
    monkeypatch.setattr(cp, "_git_changed_paths_once", lambda _root: set())
    monkeypatch.setattr(
        cp,
        "_resolve_closure_mode",
        lambda *_args, **_kwargs: pu.ClosureModeResolution(
            mode="execution",
            base_mode="verification_only",
            delivery_paths=frozenset({"app/demo.py"}),
            matched_write_set=frozenset({"app/demo.py"}),
            upgrade_reason="evidence_commit",
        ),
    )
    monkeypatch.setattr(cp, "_run_quality_gates", lambda **_kwargs: [])
    monkeypatch.setattr(cp, "gate_team_artifacts_for_close", lambda *_args, **_kwargs: 0)

    rc = cp.run_close_package_impl(
        cp.ClosePackageArgs(
            package=package_id,
            verify_only=True,
            skip_dod=True,
            closure_mode="execution",
            approve_close_without_dod=True,
        )
    )
    captured = capsys.readouterr()

    assert rc == 0
    assert "Evidence commit contains write-set paths" in captured.out
    assert "upgrading to execution mode" in captured.out
    assert "caller claimed --closure-mode=execution" not in captured.err


def test_resolve_closure_mode_upgrades_unknown_via_head_commit(monkeypatch, tmp_path) -> None:
    exec_contract = tmp_path / "archive" / "team_artifacts" / "epoch-demo" / "execution_contract.md"
    exec_contract.parent.mkdir(parents=True)
    exec_contract.write_text("Delivery complete.\n", encoding="utf-8")
    gm.patch_git_clean(monkeypatch, pu.subprocess)
    monkeypatch.setattr(
        pu,
        "git_head_commit_src_files",
        lambda _root=None: {"tests/test_latency_budget.py"},
    )

    resolution = pu.resolve_closure_mode(
        "epoch-demo",
        {"TARGET_ARTIFACTS": "`tests/test_latency_budget.py`"},
        root=tmp_path,
        precomputed_src_changed=set(),
        precomputed_evidence_valid=False,
        exec_contract_text="Delivery complete.\n",
    )

    assert resolution.base_mode == "unknown"
    assert resolution.mode == "execution"
    assert resolution.upgrade_reason == "head_commit"
    assert resolution.matched_write_set == frozenset({"tests/test_latency_budget.py"})


def test_close_package_upgrades_unknown_to_execution_when_head_commit_has_write_set(
    monkeypatch, tmp_path, capsys
):
    package_id = "epoch-demo"
    tasklist = tmp_path / "doc" / "tasklist.md"
    tasklist.parent.mkdir(parents=True)
    tasklist.write_text("stub", encoding="utf-8")
    exec_contract = tmp_path / "archive" / "team_artifacts" / package_id / "execution_contract.md"
    exec_contract.parent.mkdir(parents=True)
    exec_contract.write_text("Changed: app/demo.py — refactored.\n", encoding="utf-8")

    monkeypatch.setattr(cp, "ROOT", tmp_path)
    monkeypatch.setattr(cp, "TASKLIST", tasklist)
    monkeypatch.setattr(cp, "TEAM_ARTIFACTS", tmp_path / "archive" / "team_artifacts")
    monkeypatch.setattr(cp, "parse_truth_view_from_registry", lambda: [])
    monkeypatch.setattr(cp, "_registry_item_status", lambda _pkg: "ready")
    monkeypatch.setattr(
        cp,
        "_parse_contract",
        lambda _text, _package: {
            "PACKAGE_ID": package_id,
            "USER_STORIES": "n/a (infra package)",
            "TARGET_ARTIFACTS": "`app/demo.py`",
            "DOD_COMMANDS": ".\\.venv\\Scripts\\python.exe -m py_compile app/demo.py",
        },
    )
    monkeypatch.setattr(cp, "_detect_dod_drift_from_exec_prompt", lambda *_args: (False, None))
    monkeypatch.setattr(cp, "_provider_prereq_blockers", lambda *_args: [])
    monkeypatch.setattr(cp, "_git_changed_paths_once", lambda _root: set())
    monkeypatch.setattr(
        cp,
        "_resolve_closure_mode",
        lambda *_args, **_kwargs: pu.ClosureModeResolution(
            mode="execution",
            base_mode="unknown",
            delivery_paths=frozenset({"app/demo.py"}),
            matched_write_set=frozenset({"app/demo.py"}),
            upgrade_reason="head_commit",
        ),
    )
    monkeypatch.setattr(cp, "_run_quality_gates", lambda **_kwargs: [])
    monkeypatch.setattr(cp, "gate_team_artifacts_for_close", lambda *_args, **_kwargs: 0)

    rc = cp.run_close_package_impl(
        cp.ClosePackageArgs(
            package=package_id,
            verify_only=True,
            skip_dod=True,
            closure_mode="execution",
            approve_close_without_dod=True,
        )
    )
    captured = capsys.readouterr()

    assert rc == 0
    assert "HEAD commit contains write-set paths" in captured.out
    assert "upgrading to execution mode" in captured.out
    assert "caller claimed --closure-mode=execution" not in captured.err


def test_update_us_file_skips_when_already_covered_by_other_package() -> None:
    existing = (
        '---\n'
        'us_id: "US-3.1"\n'
        'status: "closed"\n'
        'covered_by: "strong-move-first-session-cold-open-v1"\n'
        'closed_date: "2026-05-24"\n'
        '---\n\n'
        '# body\n'
    )
    assert cp._us_already_covered_by_other(existing, "strong-move-latency-budget-contracts-v1")
    updated = cp.update_us_index(
        json.dumps(
            {
                "items": [
                    {
                        "us_id": "US-3.1",
                        "status": "closed",
                        "covered_by": "strong-move-first-session-cold-open-v1",
                        "closed_date": "2026-05-24",
                    }
                ]
            }
        ),
        ["US-3.1"],
        "strong-move-latency-budget-contracts-v1",
        "2026-05-24",
    )
    data = json.loads(updated)
    item = data["items"][0]
    assert item["covered_by"] == "strong-move-first-session-cold-open-v1"
