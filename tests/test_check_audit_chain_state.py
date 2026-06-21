"""Unit tests for scripts/check_audit_chain_state.py (audit chain control plane)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_audit_chain_state.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_audit_chain_state", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def chain_mod():
    return _load_module()


def test_replace_next_action_with_following_header(chain_mod, tmp_path: Path) -> None:
    before = "intro\n\n## Next Action\nold\n\n## Other\nkeep\n"
    new_block = "## Next Action\nnew\n"
    after = chain_mod.replace_next_action_block(before, new_block)
    assert "## Other\nkeep" in after
    assert "old" not in after
    assert "new" in after


def test_replace_next_action_last_section(chain_mod) -> None:
    before = "intro\n\n## Next Action\nold tail\n"
    new_block = "## Next Action\nfresh\n"
    after = chain_mod.replace_next_action_block(before, new_block)
    assert after.startswith("intro")
    assert "fresh" in after
    assert "old tail" not in after
    assert after.count("## Next Action") == 1


def test_replace_next_action_inserts_when_missing(chain_mod) -> None:
    before = "## Other first\nbody\n"
    new_block = "## Next Action\nx\n"
    after = chain_mod.replace_next_action_block(before, new_block)
    assert after.startswith("## Next Action")


def test_write_final_summary_collects_package_commands(chain_mod, tmp_path: Path) -> None:
    out = tmp_path / "final.md"
    fake_report = tmp_path / "group_01_dod_coverage_report.md"
    fake_report.write_text("# r\n", encoding="utf-8")
    group_file = tmp_path / "group_01_x.md"
    group_file.write_text("x", encoding="utf-8")
    coverage_groups = {
        "group_01": {
            "packages": [
                {"package_id": "p1", "coverage_result": "FAIL", "commands_run": ["pytest tests/x.py"]},
                {"package_id": "p2", "coverage_result": "FAIL", "commands_run": ["pytest tests/x.py"]},
            ],
        },
    }
    chain_mod.write_final_summary(
        path=out,
        period="2026-04",
        target_agent="cursor_ai",
        group_files=[group_file],
        coverage_groups=coverage_groups,
        report_files=[fake_report],
        coverage_analysis=tmp_path / "analysis.md",
        raw_json=tmp_path / "raw.json",
        next_group_file=None,
        warnings=[],
        errors=[],
        root=tmp_path,
    )
    text = out.read_text(encoding="utf-8")
    assert "## Commands Run" in text
    assert "pytest tests/x.py" in text
    assert "none recorded" not in text


def _write_min_audit_tree(root: Path) -> None:
    tw = root / "doc" / "team_workflow"
    tw.mkdir(parents=True)
    ag = tw / "audit_groups_2026-04_cursor_ai"
    ag.mkdir(parents=True)
    archive = root / "archive" / "team_artifacts" / "audit_2026-04"
    archive.mkdir(parents=True)

    body = """# g
## Coverage Completion Prompt
x
## Raw JSON Update
x
## Coverage Analysis Refresh
x
"""
    (ag / "group_01_one.md").write_text(body, encoding="utf-8")
    (ag / "group_02_two.md").write_text(body, encoding="utf-8")
    (ag / "coverage_dod_analysis.md").write_text("# analysis\n", encoding="utf-8")

    runbook = """# rb
## Next Action
Read doc/team_workflow/audit_groups_2026-04_cursor_ai/group_02_two.md
## Coverage Analysis Refresh
x
"""
    (ag / "run_next_group_coverage_audit.md").write_text(runbook, encoding="utf-8")
    (tw / "audit_prompt_2026-04_cursor_ai.md").write_text("# p\n", encoding="utf-8")
    (tw / "audit_coverage_prompt_2026-04_cursor_ai.md").write_text("# c\n", encoding="utf-8")

    raw = {
        "coverage_groups": {
            "group_01": {
                "packages": [{"package_id": "only", "coverage_result": "FAIL"}],
            },
        },
        "summary": {"coverage_packages_total": 99},
    }
    (archive / "_audit_raw.json").write_text(json.dumps(raw), encoding="utf-8")
    (archive / "group_01_dod_coverage_report.md").write_text("# r\n", encoding="utf-8")


def test_main_auto_heals_coverage_packages_total_with_write_raw_check(
    chain_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_min_audit_tree(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_audit_chain_state.py",
            "--period",
            "2026-04",
            "--target-agent",
            "cursor_ai",
            "--write-raw-check",
        ],
    )
    assert chain_mod.main() == 0
    raw_path = tmp_path / "archive/team_artifacts/audit_2026-04/_audit_raw.json"
    data = json.loads(raw_path.read_text(encoding="utf-8"))
    assert data["summary"]["coverage_packages_total"] == 1
    assert "last_chain_check" in data
