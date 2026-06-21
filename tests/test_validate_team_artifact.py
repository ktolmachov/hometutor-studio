"""Tests for scripts/validate_team_artifact.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "validate_team_artifact.py"
VENV_PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
PYTHON = str(VENV_PYTHON) if VENV_PYTHON.is_file() else sys.executable

_SCRIPTS_DIR = str(REPO_ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
import validate_team_artifact as vta  # noqa: E402


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PYTHON, str(SCRIPT), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def test_validate_po_minimal_passes(tmp_path: Path) -> None:
    p = tmp_path / "1_po_package.md"
    p.write_text(
        "\n".join(
            [
                "### CJM Stage",
                "Discover",
                "US-1.2 preview",
                "- Outcome: do thing",
                "Acceptance criteria: foo",
                "",
            ]
        ),
        encoding="utf-8",
    )
    proc = _run(str(p))
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_validate_po_missing_us_fails(tmp_path: Path) -> None:
    p = tmp_path / "1_po_package.md"
    p.write_text(
        "### CJM Stage\nDiscover\n- Outcome: x\nAcceptance criteria: y\n",
        encoding="utf-8",
    )
    proc = _run(str(p))
    assert proc.returncode == 1


def test_validate_po_escalation_absent_ok(tmp_path: Path) -> None:
    p = tmp_path / "1_po_package.md"
    p.write_text(
        "\n".join(
            [
                "### CJM Stage",
                "X",
                "US-1.1",
                "- Outcome: a",
                "Acceptance criteria: **ESCALATION** отсутствует.",
            ]
        ),
        encoding="utf-8",
    )
    proc = _run(str(p))
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_validate_developer_changed_files_or_table(tmp_path: Path) -> None:
    p = tmp_path / "5a_developer_sp1.md"
    p.write_text(
        "## Изменения\n\n| Файл | Notes |\n|------|-------|\n| a.py | x |\n\npytest ok\n",
        encoding="utf-8",
    )
    proc = _run(str(p))
    assert proc.returncode == 0


@pytest.mark.parametrize(
    "relative",
    [
        "archive/team_artifacts/E15-A",
        "archive/team_artifacts/E16",
    ],
)
def test_real_bundle_dirs_pass(relative: str) -> None:
    d = REPO_ROOT / relative
    if not d.is_dir():
        pytest.skip(f"missing fixture dir {d}")
    proc = _run("--artifacts-dir", str(d))
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_validate_cli_empty_artifacts_dir_ok(tmp_path: Path) -> None:
    ad = tmp_path / "empty_pkg"
    ad.mkdir()
    proc = _run("--artifacts-dir", str(ad))
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_handoff_warn_when_developer_unresolved_nonempty() -> None:
    r = vta.ValidationResult()
    text = (
        "## Изменения\n\n| Файл | x |\n\npytest 1 passed\n\n"
        "## Unresolved\n\n- needs follow-up\n"
    )
    vta.validate_developer(text, r)
    assert any("HANDOFF_SIGNAL" in w for w in r.warnings)


def test_handoff_ok_when_developer_unresolved_none() -> None:
    r = vta.ValidationResult()
    text = (
        "## Изменения\n\n| Файл | x |\n\npytest 1 passed\n\n"
        "## Unresolved\n\n- Нет.\n"
    )
    vta.validate_developer(text, r)
    assert not any("HANDOFF_SIGNAL" in w for w in r.warnings)


def test_handoff_warn_when_pytest_failed_count() -> None:
    r = vta.ValidationResult()
    text = "## Изменения\n\n| Файл | x |\n\n3 failed\npytest\n"
    vta.validate_developer(text, r)
    assert any("HANDOFF_SIGNAL" in w for w in r.warnings)


def test_handoff_ok_developer_with_signal() -> None:
    r = vta.ValidationResult()
    text = (
        "## Изменения\n\n| Файл | x |\n\npytest\n\n"
        "## Unresolved\n\n- big risk\n\nHANDOFF_SIGNAL: a → layer contract\n"
    )
    vta.validate_developer(text, r)
    assert not any("HANDOFF_SIGNAL" in w for w in r.warnings)


def test_handoff_warn_tester_fail_without_signal() -> None:
    r = vta.ValidationResult()
    text = "### FAIL\n\nBlocker: tests.\n"
    vta.validate_tester(text, r)
    assert any("HANDOFF_SIGNAL" in w for w in r.warnings)


def test_handoff_ok_tester_fail_with_signal() -> None:
    r = vta.ValidationResult()
    text = "### FAIL\n\nHANDOFF_SIGNAL: x → layer tests\n"
    vta.validate_tester(text, r)
    assert not any("HANDOFF_SIGNAL" in w for w in r.warnings)


def test_analyst_checkpoint_no_po_questions_paren_net() -> None:
    r = vta.ValidationResult()
    text = (
        "Given x When y Then z\nData flow: a\n\n"
        "## Checkpoint\n"
        "- ✗ Open Questions → PO (нет)\n"
        "- ✓ Open Questions → Architect (ok)\n"
    )
    vta.validate_analyst(text, r)
    assert not r.errors


def test_analyst_open_questions_to_po_still_errors() -> None:
    r = vta.ValidationResult()
    text = "Given x When y Then z\nData flow: a\n\n- Open Questions → PO\n"
    vta.validate_analyst(text, r)
    assert any("Open Questions" in e for e in r.errors)


def test_handoff_ok_developer_unresolved_none_before_status() -> None:
    r = vta.ValidationResult()
    text = (
        "## Изменения\n\n| Файл | x |\n\npytest 1 passed\n\n"
        "## Unresolved risk\n\nNone.\n\n"
        "**Status:** `[pkg] Step 4/8 — Developer sp1: COMPLETE`\n"
    )
    vta.validate_developer(text, r)
    assert not any("HANDOFF_SIGNAL" in w for w in r.warnings)
