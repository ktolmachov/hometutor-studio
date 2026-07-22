"""Tests for token registry JSON and check_readset integration."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import scripts.lint_agent_prompts as lint_agent_prompts

ROOT = Path(__file__).resolve().parents[1]


def test_token_safety_registry_schema() -> None:
    p = ROOT / "doc" / "token_safety_registry.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["budgets"]["hard_input_tokens"] == 20_000
    assert data["files"]["app/prompts/_impl.py"]["full_read"] == "forbidden"
    assert data["files"]["doc/epochs/e4.md"]["est_tokens"] > 10_000


def test_ingestion_loader_token_safety_registry_entry() -> None:
    """epoch-ingestion-loader-token-registry: loader module stays forbidden full-read with grep hint."""
    data = json.loads((ROOT / "doc" / "token_safety_registry.json").read_text(encoding="utf-8"))
    entry = data["files"]["app/ingestion_loader.py"]
    assert entry["full_read"] == "forbidden"
    assert entry["est_tokens"] > 1000
    assert "ingestion_loader.py" in entry["safe_hint"]


def test_generate_orchestration_prompt_token_safety_registry_entry() -> None:
    """Orchestration prompt generator is measured and forbidden full-read with grep hint."""
    data = json.loads((ROOT / "doc" / "token_safety_registry.json").read_text(encoding="utf-8"))
    entry = data["files"]["scripts/generate_orchestration_prompt.py"]
    assert entry["full_read"] == "forbidden"
    assert entry["est_tokens"] > 1000
    assert "generate_orchestration_prompt.py" in entry["safe_hint"]


def test_check_backlog_drift_token_safety_registry_entry() -> None:
    """PLAN_NEXT drift guard script is measured in token_safety_registry.json."""
    data = json.loads((ROOT / "doc" / "token_safety_registry.json").read_text(encoding="utf-8"))
    assert "scripts/check_backlog_drift.py" in data["files"]
    entry = data["files"]["scripts/check_backlog_drift.py"]
    assert entry["est_tokens"] > 500


_METADATA_FIELD_NAMES = {"lines", "bytes", "est_tokens", "full_read", "safe_hint", "missing"}


def test_registry_structure_no_dropped_keys() -> None:
    """Guard the exact corruption the 2026-07 audit found: a dropped file key made
    metadata fields (lines/bytes/...) leak as top-level ``files`` keys, which parsed
    as valid JSON but silently merged one entry into another."""
    data = json.loads((ROOT / "doc" / "token_safety_registry.json").read_text(encoding="utf-8"))
    files = data["files"]
    assert isinstance(files, dict) and files
    for key, meta in files.items():
        assert key not in _METADATA_FIELD_NAMES, f"metadata field '{key}' leaked as a file key (dropped-key corruption)"
        assert isinstance(meta, dict), f"{key}: entry must be an object"
        for field in ("lines", "bytes", "est_tokens"):
            assert isinstance(meta.get(field), int), f"{key}: '{field}' must be an int"


def test_registry_metadata_fresh_for_local_files() -> None:
    """Every entry whose file exists in THIS repo must match a fresh measurement.

    Catches stale sizes/token estimates (the audit's second Log-2 finding). CODE_ROOT
    files (app/*, requirements.txt) are absent here and are skipped — the merge-safe
    generator preserves their numbers. Regenerate with:
        python scripts/measure_token_registry.py --write
    """
    import scripts.measure_token_registry as measure_mod

    data = json.loads((ROOT / "doc" / "token_safety_registry.json").read_text(encoding="utf-8"))
    stale: list[str] = []
    for rel, meta in data["files"].items():
        if not (ROOT / rel.replace("/", "\\")).is_file() and not (ROOT / rel).is_file():
            continue  # CODE_ROOT / cross-repo file, not measurable here
        fresh = measure_mod.measure(rel, meta)
        for field in ("lines", "bytes", "est_tokens"):
            if meta.get(field) != fresh.get(field):
                stale.append(f"{rel}.{field}: registry={meta.get(field)} actual={fresh.get(field)}")
    assert not stale, "Stale token_safety_registry.json entries (run measure_token_registry.py --write):\n" + "\n".join(stale)


def test_check_readset_merges_registry() -> None:
    registry = json.loads((ROOT / "doc" / "token_safety_registry.json").read_text(encoding="utf-8"))
    forbidden_from_registry = next(
        (
            rel_path
            for rel_path, meta in registry.get("files", {}).items()
            if meta.get("full_read") == "forbidden"
            and (
                (ROOT / rel_path.replace("/", "\\")).exists()
                or (ROOT / rel_path).exists()
            )
        ),
        None,
    )
    assert forbidden_from_registry, "Expected at least one existing forbidden file in token_safety_registry.json"

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_readset.py"), forbidden_from_registry],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "FORBIDDEN" in proc.stdout or "forbidden" in proc.stdout.lower()


def test_check_readset_signatures_on_forbidden_is_safe() -> None:
    """With --signatures, forbidden entries are acknowledged without BLOCK (planned full-read)."""
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "check_readset.py"),
            "--signatures",
            "app/query_service.py",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "SAFE" in proc.stdout


def test_check_readset_profile_flag_is_reported() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "check_readset.py"),
            "--profile",
            "relaxed",
            "scripts/prompt_utils.py",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode in {0, 1, 2}, proc.stdout + proc.stderr
    assert "Profile: relaxed" in proc.stdout


def test_lint_agent_prompts_ok() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "lint_agent_prompts.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_workflow_lint_catches_ascii_20k_budget_drift(tmp_path, monkeypatch) -> None:
    doc = tmp_path / "workflow.md"
    doc.write_text(
        "\n".join(
            [
                "Target <=20k input tokens.",
                "target <= 20k input tokens.",
                "Token budget: <= 20k input tokens.",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(lint_agent_prompts, "ROOT", tmp_path)
    monkeypatch.setattr(lint_agent_prompts, "WORKFLOW_DOC_PATHS", ("workflow.md",))

    errs = lint_agent_prompts.lint_workflow_docs()

    assert len([err for err in errs if "stale token budget wording" in err]) == 3


def test_lint_catches_out_file_execution_contract_without_utf8(tmp_path, monkeypatch) -> None:
    script = tmp_path / "scripts" / "run_autonomous.py"
    script.parent.mkdir()
    script.write_text(
        "'STARTED' | Out-File archive/team_artifacts/pkg/execution_contract.md\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(lint_agent_prompts, "ROOT", tmp_path)
    monkeypatch.setattr(
        lint_agent_prompts,
        "EXECUTION_CONTRACT_PROMPT_PATHS",
        ("scripts/run_autonomous.py",),
    )

    errs = lint_agent_prompts.lint_execution_contract_encoding_commands()

    assert len(errs) == 1
    assert "must specify UTF-8" in errs[0]


def test_lint_allows_utf8_execution_contract_write(tmp_path, monkeypatch) -> None:
    script = tmp_path / "scripts" / "run_autonomous.py"
    script.parent.mkdir()
    script.write_text(
        "Set-Content -Path archive/team_artifacts/pkg/execution_contract.md "
        "-Value 'STARTED' -Encoding utf8\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(lint_agent_prompts, "ROOT", tmp_path)
    monkeypatch.setattr(
        lint_agent_prompts,
        "EXECUTION_CONTRACT_PROMPT_PATHS",
        ("scripts/run_autonomous.py",),
    )

    assert lint_agent_prompts.lint_execution_contract_encoding_commands() == []
