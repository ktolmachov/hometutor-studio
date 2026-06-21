from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import close_package as cp  # noqa: E402


def test_gate_team_artifacts_skips_when_no_canonical_files(tmp_path, monkeypatch):
    monkeypatch.setattr(cp, "ROOT", tmp_path)
    ta = tmp_path / "archive" / "team_artifacts"
    monkeypatch.setattr(cp, "TEAM_ARTIFACTS", ta)
    pkg_dir = ta / "pkg"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "execution_contract.md").write_text("x", encoding="utf-8")

    rc = cp.gate_team_artifacts_for_close("pkg", cp.ClosePackageArgs())

    assert rc == 0


def test_gate_team_artifacts_blocks_on_bad_po(tmp_path, monkeypatch):
    monkeypatch.setattr(cp, "ROOT", tmp_path)
    ta = tmp_path / "archive" / "team_artifacts"
    monkeypatch.setattr(cp, "TEAM_ARTIFACTS", ta)
    pkg_dir = ta / "pkg"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "1_po_package.md").write_text("# bad\nno user story\n", encoding="utf-8")

    rc = cp.gate_team_artifacts_for_close("pkg", cp.ClosePackageArgs())

    assert rc == 1


def test_gate_team_artifacts_skip_flag_ignores_bad_po(tmp_path, monkeypatch):
    monkeypatch.setattr(cp, "ROOT", tmp_path)
    ta = tmp_path / "archive" / "team_artifacts"
    monkeypatch.setattr(cp, "TEAM_ARTIFACTS", ta)
    pkg_dir = ta / "pkg"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "1_po_package.md").write_text("# bad\n", encoding="utf-8")

    rc = cp.gate_team_artifacts_for_close(
        "pkg",
        cp.ClosePackageArgs(skip_team_artifacts_check=True),
    )

    assert rc == 0


def test_gate_team_artifacts_force_allows_bad_po(tmp_path, monkeypatch):
    monkeypatch.setattr(cp, "ROOT", tmp_path)
    ta = tmp_path / "archive" / "team_artifacts"
    monkeypatch.setattr(cp, "TEAM_ARTIFACTS", ta)
    pkg_dir = ta / "pkg"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "1_po_package.md").write_text("# bad\n", encoding="utf-8")

    rc = cp.gate_team_artifacts_for_close("pkg", cp.ClosePackageArgs(force=True))

    assert rc == 0
