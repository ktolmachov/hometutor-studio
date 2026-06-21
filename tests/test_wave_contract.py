"""
epoch-wave-contract acceptance tests — schema v2 structure and cross-ref validation.

Tests cover:
- backlog_registry.yaml has schema_version: 2
- waves: block present with required fields
- INV5: items with wave_id reference existing waves
- INV6: wave.packages reference items with matching wave_id
- backlog_registry_lint.py --strict passes on real registry
- post_agent wave auto-continue logic (unit-tested with fixtures)
- wave lifecycle status transitions
"""

from __future__ import annotations

import json
import textwrap
from copy import deepcopy
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "doc" / "backlog_registry.yaml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_registry() -> dict:
    import yaml

    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _make_registry(waves: list[dict], items: list[dict], schema_version: int = 2) -> dict:
    """Build a minimal in-memory registry for unit tests."""
    return {
        "schema_version": schema_version,
        "user_stories_index": "doc/user_stories_index.json",
        "waves": waves,
        "items": items,
    }


# ---------------------------------------------------------------------------
# Real registry: schema v2 structural checks
# ---------------------------------------------------------------------------


class TestRealRegistrySchemaV2:
    def test_schema_version_is_2(self):
        reg = _load_registry()
        assert reg.get("schema_version") == 2

    def test_waves_block_present(self):
        reg = _load_registry()
        assert "waves" in reg
        assert isinstance(reg["waves"], list)
        assert len(reg["waves"]) >= 1

    def test_each_wave_has_required_fields(self):
        reg = _load_registry()
        for wave in reg["waves"]:
            assert "id" in wave, f"wave missing 'id': {wave}"
            assert "theme" in wave, f"wave {wave['id']!r} missing 'theme'"
            assert "status" in wave, f"wave {wave['id']!r} missing 'status'"
            assert "packages" in wave, f"wave {wave['id']!r} missing 'packages'"

    def test_wave_status_values_valid(self):
        allowed = {"proposed", "ready", "wip", "completed", "frozen"}
        reg = _load_registry()
        for wave in reg["waves"]:
            assert wave.get("status") in allowed, (
                f"wave {wave['id']!r} has invalid status {wave['status']!r}"
            )

    def test_proposed_items_with_wave_id_reference_real_waves(self):
        reg = _load_registry()
        wave_ids = {w["id"] for w in reg["waves"]}
        for item in reg.get("items") or []:
            wid = item.get("wave_id")
            if wid is not None:
                assert wid in wave_ids, (
                    f"item {item['id']!r} wave_id={wid!r} not in waves"
                )

    def test_wave_packages_reference_existing_items(self):
        reg = _load_registry()
        item_ids = {it["id"] for it in (reg.get("items") or []) if "id" in it}
        for wave in reg["waves"]:
            for pkg in wave.get("packages") or []:
                assert pkg in item_ids, (
                    f"wave {wave['id']!r} references unknown package {pkg!r}"
                )

    def test_wave_packages_items_have_matching_wave_id(self):
        reg = _load_registry()
        item_map = {it["id"]: it for it in (reg.get("items") or []) if "id" in it}
        for wave in reg["waves"]:
            wid = wave["id"]
            for pkg_id in wave.get("packages") or []:
                item = item_map.get(pkg_id)
                if item:
                    assert str(item.get("wave_id", "")) == wid, (
                        f"item {pkg_id!r} wave_id={item.get('wave_id')!r} != wave {wid!r}"
                    )

    def test_wave_positions_are_sequential(self):
        """wave_position must be consecutive 1..N for packages in a wave."""
        reg = _load_registry()
        item_map = {it["id"]: it for it in (reg.get("items") or []) if "id" in it}
        for wave in reg["waves"]:
            positions = []
            for pkg_id in wave.get("packages") or []:
                item = item_map.get(pkg_id)
                if item and item.get("wave_position") is not None:
                    positions.append(item["wave_position"])
            if positions:
                assert positions == list(range(1, len(positions) + 1)), (
                    f"wave {wave['id']!r} positions not sequential: {positions}"
                )

    def test_lint_strict_passes_on_real_registry(self):
        """backlog_registry_lint.py --strict must exit 0."""
        import subprocess, sys

        result = subprocess.run(
            [sys.executable, "scripts/backlog_registry_lint.py", "--strict"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, (
            f"lint --strict failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )


# ---------------------------------------------------------------------------
# lint_strict unit tests with synthetic registries
# ---------------------------------------------------------------------------


class TestLintStrictUnit:
    def _lint(self, registry: dict) -> tuple[list[str], list[str]]:
        from scripts.backlog_registry_lint import lint_strict

        return lint_strict(registry)

    def test_valid_wave_registry_passes(self):
        reg = _make_registry(
            waves=[{"id": "wave-a", "packages": ["pkg-1", "pkg-2"], "north_star": "x", "status": "proposed"}],
            items=[
                {"id": "pkg-1", "wave_id": "wave-a", "wave_position": 1, "status": "proposed"},
                {"id": "pkg-2", "wave_id": "wave-a", "wave_position": 2, "status": "proposed"},
            ],
        )
        errors, _ = self._lint(reg)
        assert errors == []

    def test_inv5_item_references_unknown_wave(self):
        reg = _make_registry(
            waves=[],
            items=[{"id": "pkg-1", "wave_id": "wave-nonexistent", "wave_position": 1, "status": "proposed"}],
        )
        errors, _ = self._lint(reg)
        assert any("wave_id" in e and "wave-nonexistent" in e for e in errors)

    def test_inv6_wave_references_unknown_package(self):
        reg = _make_registry(
            waves=[{"id": "wave-a", "packages": ["pkg-missing"], "status": "proposed"}],
            items=[],
        )
        errors, _ = self._lint(reg)
        assert any("pkg-missing" in e for e in errors)

    def test_inv6_package_wave_id_mismatch(self):
        reg = _make_registry(
            waves=[
                {"id": "wave-a", "packages": ["pkg-1"], "status": "proposed"},
                {"id": "wave-b", "packages": [], "status": "proposed"},
            ],
            items=[
                {"id": "pkg-1", "wave_id": "wave-b", "wave_position": 1, "status": "proposed"},
            ],
        )
        errors, _ = self._lint(reg)
        assert any("wave_id" in e or "wave-a" in e for e in errors)

    def test_wave_position_non_positive_fails(self):
        reg = _make_registry(
            waves=[{"id": "wave-a", "packages": ["pkg-1"], "status": "proposed"}],
            items=[{"id": "pkg-1", "wave_id": "wave-a", "wave_position": 0, "status": "proposed"}],
        )
        errors, _ = self._lint(reg)
        assert any("wave_position" in e for e in errors)

    def test_schema_v1_skips_wave_validation(self):
        """lint_strict is silently skipped for schema_version < 2."""
        reg = _make_registry(waves=[], items=[], schema_version=1)
        # Even with a bad items entry, no errors because schema < 2
        reg["items"].append({"id": "pkg-1", "wave_id": "nonexistent", "wave_position": 1, "status": "proposed"})
        errors, _ = self._lint(reg)
        assert errors == []

    def test_duplicate_wave_id_fails(self):
        reg = _make_registry(
            waves=[
                {"id": "wave-dup", "packages": [], "status": "proposed"},
                {"id": "wave-dup", "packages": [], "status": "proposed"},
            ],
            items=[],
        )
        errors, _ = self._lint(reg)
        assert any("duplicate" in e.lower() for e in errors)

    def test_invalid_wave_status_fails(self):
        reg = _make_registry(
            waves=[{"id": "wave-a", "packages": [], "status": "active"}],
            items=[],
        )
        errors, _ = self._lint(reg)
        assert any("status" in e for e in errors)


# ---------------------------------------------------------------------------
# wave auto-continue logic
# ---------------------------------------------------------------------------


class TestWaveAutoContinue:
    """Unit tests for _wave_auto_continue() in run_autonomous.py."""

    def _setup(self, tmp_path: Path) -> tuple[Path, Path]:
        """Create doc/ subdirectory and return (registry_path, tasklist_path)."""
        doc = tmp_path / "doc"
        doc.mkdir(exist_ok=True)
        tl = doc / "tasklist.md"
        tl.write_text(
            "# Tasklist\n\n## § Now\n\n### Truth View\n\n"
            "| Package | Status | CJM | Primary US | Owner | Notes |\n"
            "|---|---|---|---|---|---|\n",
            encoding="utf-8",
        )
        return doc / "backlog_registry.yaml", tl

    def _make_registry_yaml(
        self, tmp_path: Path, wave_pkgs: list[str], closed_idx: int
    ) -> Path:
        import yaml

        reg_path, _ = self._setup(tmp_path)
        items = [
            {
                "id": pkg,
                "wave_id": "wave-test",
                "wave_position": i + 1,
                "status": "closed" if i <= closed_idx else "proposed",
                "cjm_moments": [],
                "user_stories": [],
                "impact": "infra",
                "blocks": f"pkg {pkg}",
                "cost_estimate": "S",
                "write_set_max": 3,
                "read_set_hint": [],
                "dod_commands": [".\\.venv\\Scripts\\python.exe -m pytest -q"],
            }
            for i, pkg in enumerate(wave_pkgs)
        ]
        reg = {
            "schema_version": 2,
            "user_stories_index": "doc/user_stories_index.json",
            "waves": [
                {
                    "id": "wave-test",
                    "theme": "Test wave",
                    "north_star": "Test north star",
                    "entry_mot": "infra",
                    "exit_mot": "infra",
                    "packages": wave_pkgs,
                    "kill_switch": None,
                    "status": "proposed",
                }
            ],
            "items": items,
        }
        with open(reg_path, "w", encoding="utf-8") as f:
            # sort_keys=False + id first in each item dict: matches hand-maintained
            # doc/backlog_registry.yaml shape (`- id: …` is the first list line).
            yaml.dump(reg, f, allow_unicode=True, sort_keys=False)
        return reg_path

    def test_returns_next_package_when_more_in_wave(self, tmp_path, monkeypatch):
        import run_autonomous as ra

        wave_pkgs = ["pkg-a", "pkg-b", "pkg-c"]
        self._make_registry_yaml(tmp_path, wave_pkgs, closed_idx=0)

        monkeypatch.setattr(ra, "ROOT", tmp_path)
        monkeypatch.setattr(ra, "_mark_wave_wip", lambda *a, **kw: None)

        result = ra._wave_auto_continue("pkg-a")
        assert result == "pkg-b"
        # Truth View is written as `ready`; registry item must follow (see roadmap_sync_check).
        import yaml

        reg_path = tmp_path / "doc" / "backlog_registry.yaml"
        with open(reg_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        by_id = {it["id"]: it for it in data["items"]}
        assert by_id["pkg-b"]["status"] == "ready"

    def test_returns_none_for_last_package_in_wave(self, tmp_path, monkeypatch):
        import run_autonomous as ra

        wave_pkgs = ["pkg-a", "pkg-b"]
        self._make_registry_yaml(tmp_path, wave_pkgs, closed_idx=1)

        monkeypatch.setattr(ra, "ROOT", tmp_path)
        monkeypatch.setattr(ra, "_mark_wave_completed", lambda *a, **kw: None)

        result = ra._wave_auto_continue("pkg-b")
        assert result is None

    def test_returns_none_for_package_not_in_wave(self, tmp_path, monkeypatch):
        import run_autonomous as ra

        wave_pkgs = ["pkg-a", "pkg-b"]
        self._make_registry_yaml(tmp_path, wave_pkgs, closed_idx=0)

        monkeypatch.setattr(ra, "ROOT", tmp_path)
        monkeypatch.setattr(ra, "_mark_wave_wip", lambda *a, **kw: None)

        result = ra._wave_auto_continue("pkg-standalone")
        assert result is None

    def test_returns_none_for_schema_v1_registry(self, tmp_path, monkeypatch):
        import yaml, run_autonomous as ra

        doc = tmp_path / "doc"
        doc.mkdir(exist_ok=True)
        reg = {"schema_version": 1, "items": [], "waves": []}
        reg_path = doc / "backlog_registry.yaml"
        with open(reg_path, "w", encoding="utf-8") as f:
            yaml.dump(reg, f)

        monkeypatch.setattr(ra, "ROOT", tmp_path)

        result = ra._wave_auto_continue("pkg-a")
        assert result is None

    def test_wave_completed_when_last_package_closed(self, tmp_path, monkeypatch):
        import run_autonomous as ra

        wave_pkgs = ["pkg-a"]
        self._make_registry_yaml(tmp_path, wave_pkgs, closed_idx=0)

        completed = []
        monkeypatch.setattr(ra, "ROOT", tmp_path)
        monkeypatch.setattr(ra, "_mark_wave_completed", lambda path, wid: completed.append(wid))

        ra._wave_auto_continue("pkg-a")
        assert "wave-test" in completed

    def test_promote_next_no_warning_when_already_ready(self, tmp_path, monkeypatch, capsys):
        """Next wave package already ``ready`` — idempotent promote must not print drift."""
        import run_autonomous as ra
        import yaml

        wave_pkgs = ["pkg-a", "pkg-b"]
        reg_path = self._make_registry_yaml(tmp_path, wave_pkgs, closed_idx=0)
        with open(reg_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for it in data["items"]:
            if it["id"] == "pkg-b":
                it["status"] = "ready"
        with open(reg_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

        monkeypatch.setattr(ra, "ROOT", tmp_path)
        monkeypatch.setattr(ra, "_mark_wave_wip", lambda *a, **kw: None)

        def _noop_sync(cmd, **kwargs):  # noqa: ARG001
            class _R:
                returncode = 0
                stdout = ""
                stderr = ""

            return _R()

        monkeypatch.setattr(ra.subprocess, "run", _noop_sync)

        result = ra._wave_auto_continue("pkg-a")
        assert result == "pkg-b"
        out = capsys.readouterr().out
        assert "may drift" not in out

    def test_stays_proposed_when_missing_dod_commands(self, tmp_path, monkeypatch, capsys):
        """Wave continue must not force ready (and must not fail lint) without dod_commands."""
        import run_autonomous as ra
        import yaml

        wave_pkgs = ["pkg-a", "pkg-b"]
        reg_path = self._make_registry_yaml(tmp_path, wave_pkgs, closed_idx=0)
        with open(reg_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for it in data["items"]:
            if it["id"] == "pkg-b":
                it.pop("dod_commands", None)
                it["impact"] = "loop-improvement"
                it["user_stories"] = ["US-1.1"]
        with open(reg_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

        monkeypatch.setattr(ra, "ROOT", tmp_path)
        monkeypatch.setattr(ra, "_mark_wave_wip", lambda *a, **kw: None)
        lint_calls: list = []
        monkeypatch.setattr(
            ra.subprocess,
            "run",
            lambda *a, **kw: lint_calls.append(a) or ra.subprocess.CompletedProcess(args=a, returncode=0),
        )

        result = ra._wave_auto_continue("pkg-a")
        assert result == "pkg-b"
        with open(reg_path, encoding="utf-8") as f:
            by_id = {it["id"]: it for it in yaml.safe_load(f)["items"]}
        assert by_id["pkg-b"]["status"] == "proposed"
        out = capsys.readouterr().out
        assert "not promoted to ready" in out
        assert lint_calls, "proposed next package should still run lint sync"

    def test_skips_lint_sync_when_ready_but_contract_incomplete(self, tmp_path, monkeypatch, capsys):
        import run_autonomous as ra
        import yaml

        wave_pkgs = ["pkg-a", "pkg-b"]
        reg_path = self._make_registry_yaml(tmp_path, wave_pkgs, closed_idx=0)
        with open(reg_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for it in data["items"]:
            if it["id"] == "pkg-b":
                it["status"] = "ready"
                it.pop("dod_commands", None)
                it["impact"] = "loop-improvement"
                it["user_stories"] = ["US-1.1"]
        with open(reg_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

        monkeypatch.setattr(ra, "ROOT", tmp_path)
        monkeypatch.setattr(ra, "_mark_wave_wip", lambda *a, **kw: None)
        lint_calls: list = []
        monkeypatch.setattr(
            ra.subprocess,
            "run",
            lambda *a, **kw: lint_calls.append(a) or ra.subprocess.CompletedProcess(args=a, returncode=0),
        )

        result = ra._wave_auto_continue("pkg-a")
        assert result == "pkg-b"
        assert not lint_calls
        out = capsys.readouterr().out
        assert "Skipping tasklist sync" in out
