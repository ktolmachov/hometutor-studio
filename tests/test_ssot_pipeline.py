"""
Tests for the SSoT-refactoring of the auto-pipeline.

Covers all functions added/changed in:
  - scripts/backlog_registry_lint.py   (get_active_wave, _render_wave_queue,
                                        _render_active_contracts, _upsert_contracts_in_now,
                                        _strip_registry_generated_contracts,
                                        _reconcile_generated_contracts_in_now,
                                        dod_commands lint rule)
  - scripts/auto_promote_next_wave_package.py  (_get_active_wave_from_registry,
                                                _get_now_package_ids_from_registry,
                                                find_next_candidate, _build_contract_block)
  - scripts/generate_next_prompt.py    (_init_team_artifacts skeleton)
"""

from __future__ import annotations

import importlib.util
import json
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"


# ---------------------------------------------------------------------------
# Module loaders
# ---------------------------------------------------------------------------

def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, f"Cannot load {path}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def lint_mod():
    return _load_module("backlog_registry_lint", SCRIPTS_DIR / "backlog_registry_lint.py")


@pytest.fixture(scope="module")
def promote_mod():
    return _load_module("auto_promote_next_wave_package", SCRIPTS_DIR / "auto_promote_next_wave_package.py")


@pytest.fixture(scope="module")
def gen_mod():
    import io as _io
    # generate_next_prompt.py does `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, ...)`
    # at module level if sys.stdout has .buffer (which pytest's capture does).
    # We load the module with a no-buffer StringIO so the reassignment is skipped,
    # then restore pytest's stdout intact.
    old_out, old_err = sys.stdout, sys.stderr
    fake = _io.StringIO()
    sys.stdout, sys.stderr = fake, fake  # no .buffer → module won't replace
    try:
        if "generate_next_prompt" in sys.modules:
            mod = sys.modules["generate_next_prompt"]
        else:
            mod = _load_module("generate_next_prompt", SCRIPTS_DIR / "generate_next_prompt.py")
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    return mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wave(wid: str, status: str = "proposed", pkgs: list[str] | None = None) -> dict:
    return {"id": wid, "status": status, "packages": pkgs or [], "north_star": "x"}


def _item(
    iid: str,
    status: str = "proposed",
    wave_id: str = "wave-a",
    us: list[str] | None = None,
    dod: list[str] | None = None,
    wave_position: int = 1,
) -> dict:
    return {
        "id": iid,
        "wave_id": wave_id,
        "wave_position": wave_position,
        "status": status,
        "user_stories": us or [],
        "dod_commands": dod or [],
        "cjm_moments": ["#1 Discover"],
        "blocks": f"Outcome for {iid}",
        "exit_artifact": f"{iid}.py",
        "created": "2026-04-20",
        "last_review": "2026-04-20",
    }


def _reg(waves: list[dict], items: list[dict], active_wave_id: str | None = None) -> dict:
    d: dict[str, Any] = {
        "schema_version": 2,
        "user_stories_index": "doc/user_stories_index.json",
        "waves": waves,
        "items": items,
    }
    if active_wave_id is not None:
        d["active_wave_id"] = active_wave_id
    return d


# Minimal generated tasklist active section
_TASKLIST_TEMPLATE = """\
# Tasklist

## Now

Актуализировано: **2026-01-01**

### Truth View

| Package | Status | CJM | Primary US | Owner | Notes |
|---|---|---|---|---|---|

### Wave queue

<!-- placeholder -->

### Recent closed references

- placeholder

### Maintenance (compact)

nothing

## Deferred

### Архив Roadmap

nothing
"""


# ===========================================================================
# 1. backlog_registry_lint.get_active_wave
# ===========================================================================


class TestGetActiveWave:
    def test_explicit_active_wave_id_used(self, lint_mod):
        reg = _reg(
            waves=[
                _wave("wave-a", "completed"),
                _wave("wave-b", "wip"),
                _wave("wave-c", "proposed"),
            ],
            items=[],
            active_wave_id="wave-c",
        )
        # explicit wins even if wave-b is wip
        assert lint_mod.get_active_wave(reg) == "wave-c"

    def test_explicit_completed_wave_falls_through(self, lint_mod):
        """explicit active_wave_id pointing at completed wave should be ignored."""
        reg = _reg(
            waves=[_wave("wave-a", "completed"), _wave("wave-b", "wip")],
            items=[],
            active_wave_id="wave-a",
        )
        assert lint_mod.get_active_wave(reg) == "wave-b"

    def test_wip_has_highest_auto_priority(self, lint_mod):
        reg = _reg(
            waves=[
                _wave("wave-proposed", "proposed"),
                _wave("wave-ready", "ready"),
                _wave("wave-wip", "wip"),
            ],
            items=[],
        )
        assert lint_mod.get_active_wave(reg) == "wave-wip"

    def test_ready_beats_proposed(self, lint_mod):
        reg = _reg(
            waves=[
                _wave("wave-proposed", "proposed"),
                _wave("wave-ready", "ready"),
            ],
            items=[],
        )
        assert lint_mod.get_active_wave(reg) == "wave-ready"

    def test_proposed_returned_when_no_wip_or_ready(self, lint_mod):
        reg = _reg(waves=[_wave("wave-p", "proposed")], items=[])
        assert lint_mod.get_active_wave(reg) == "wave-p"

    def test_completed_waves_never_returned(self, lint_mod):
        reg = _reg(
            waves=[_wave("wave-a", "completed"), _wave("wave-b", "frozen")],
            items=[],
        )
        assert lint_mod.get_active_wave(reg) is None

    def test_no_waves_returns_none(self, lint_mod):
        assert lint_mod.get_active_wave({"schema_version": 2, "items": []}) is None

    def test_null_active_wave_id_falls_to_auto(self, lint_mod):
        reg = _reg(waves=[_wave("wave-x", "wip")], items=[], active_wave_id=None)
        assert lint_mod.get_active_wave(reg) == "wave-x"


# ===========================================================================
# 2. backlog_registry_lint._render_wave_queue — ACTIVE_WAVE marker
# ===========================================================================


class TestRenderWaveQueue:
    def test_active_wave_marker_present(self, lint_mod):
        reg = _reg(waves=[_wave("wave-demo", "wip", ["pkg-1"])], items=[])
        rendered = lint_mod._render_wave_queue(reg)
        assert "<!-- ACTIVE_WAVE: wave-demo -->" in rendered

    def test_no_active_wave_marker_none(self, lint_mod):
        reg = _reg(waves=[_wave("wave-done", "completed")], items=[])
        rendered = lint_mod._render_wave_queue(reg)
        assert "<!-- ACTIVE_WAVE: none -->" in rendered

    def test_active_wave_id_shown(self, lint_mod):
        reg = _reg(waves=[_wave("wave-x", "ready", ["p1"])], items=[])
        rendered = lint_mod._render_wave_queue(reg)
        assert "**Active wave:**" in rendered
        assert "`wave-x`" in rendered


# ===========================================================================
# 3. backlog_registry_lint._render_active_contracts
# ===========================================================================


class TestRenderActiveContracts:
    def test_empty_when_no_active_items(self, lint_mod):
        reg = _reg(waves=[], items=[_item("pkg-closed", "closed")])
        assert lint_mod._render_active_contracts(reg) == ""

    def test_renders_ready_item(self, lint_mod):
        reg = _reg(
            waves=[_wave("w", "wip", ["pkg-1"])],
            items=[_item("pkg-1", "ready", dod=[".venv/python -m pytest tests/test_x.py"])],
        )
        rendered = lint_mod._render_active_contracts(reg)
        assert "### pkg-1 Contract" in rendered
        assert "pytest tests/test_x.py" in rendered
        assert "GENERATED from backlog_registry.yaml" in rendered

    def test_renders_wip_item(self, lint_mod):
        reg = _reg(
            waves=[_wave("w", "wip", ["pkg-wip"])],
            items=[_item("pkg-wip", "wip", dod=["pytest tests/t.py"])],
        )
        rendered = lint_mod._render_active_contracts(reg)
        assert "### pkg-wip Contract" in rendered

    def test_epoch_prefix_kept_in_header(self, lint_mod):
        """Contract block uses full id with epoch- prefix so parse_contract can find it."""
        reg = _reg(
            waves=[_wave("w", "wip", ["epoch-e30-x1-foo"])],
            items=[_item("epoch-e30-x1-foo", "ready", dod=["pytest"])],
        )
        rendered = lint_mod._render_active_contracts(reg)
        assert "### epoch-e30-x1-foo Contract" in rendered

    def test_no_todo_placeholder_in_dod(self, lint_mod):
        reg = _reg(
            waves=[_wave("w", "wip", ["pkg-1"])],
            items=[_item("pkg-1", "ready", dod=["pytest tests/real_test.py -v"])],
        )
        rendered = lint_mod._render_active_contracts(reg)
        assert "TODO" not in rendered
        assert "py_compile" not in rendered

    def test_dod_missing_shows_fallback(self, lint_mod):
        item = _item("pkg-no-dod", "ready")
        item["dod_commands"] = []
        reg = _reg(waves=[_wave("w", "wip", ["pkg-no-dod"])], items=[item])
        rendered = lint_mod._render_active_contracts(reg)
        assert "backlog_registry.yaml" in rendered


# ===========================================================================
# 4. backlog_registry_lint._upsert_contracts_in_now
# ===========================================================================


class TestUpsertContractsInNow:
    def _now_section(self, contract_block: str = "") -> str:
        return _TASKLIST_TEMPLATE.replace("### Wave queue", contract_block + "\n### Wave queue")

    def test_inserts_new_contract_before_wave_queue(self, lint_mod):
        contracts = "### my-pkg Contract\n\nsome content\n"
        result = lint_mod._upsert_contracts_in_now(_TASKLIST_TEMPLATE, contracts)
        assert "### my-pkg Contract" in result
        # Must appear before Wave queue
        idx_contract = result.index("### my-pkg Contract")
        idx_wave = result.index("### Wave queue")
        assert idx_contract < idx_wave

    def test_replaces_existing_contract(self, lint_mod):
        old_contract = "### my-pkg Contract\n\nold content\n"
        tasklist = _TASKLIST_TEMPLATE.replace(
            "### Wave queue", old_contract + "\n### Wave queue"
        )
        new_contracts = "### my-pkg Contract\n\nnew content\n"
        result = lint_mod._upsert_contracts_in_now(tasklist, new_contracts)
        assert "new content" in result
        assert "old content" not in result

    def test_no_now_section_returns_unchanged(self, lint_mod):
        text = "# No Now section here\n\nfoo bar\n"
        contracts = "### pkg Contract\n\ncontent\n"
        result = lint_mod._upsert_contracts_in_now(text, contracts)
        assert result == text

    def test_multiple_contracts_all_inserted(self, lint_mod):
        contracts = "### pkg-a Contract\n\ncontent-a\n\n### pkg-b Contract\n\ncontent-b\n"
        result = lint_mod._upsert_contracts_in_now(_TASKLIST_TEMPLATE, contracts)
        assert "### pkg-a Contract" in result
        assert "### pkg-b Contract" in result


# ===========================================================================
# 5. backlog_registry_lint — dod_commands lint rule
# ===========================================================================


class TestDodCommandsLintRule:
    _EXPECTED_MSG = "must have dod_commands (non-empty list)"

    def test_ready_without_dod_commands_fails(self, lint_mod):
        item = _item("pkg-ready-no-dod", "ready")
        item["dod_commands"] = []
        data = {"schema_version": 2, "items": [item], "waves": []}
        errors, _ = lint_mod.lint(data)
        assert any(self._EXPECTED_MSG in e for e in errors), (
            f"Expected error containing {self._EXPECTED_MSG!r}; got: {errors}"
        )

    def test_wip_without_dod_commands_fails(self, lint_mod):
        item = _item("pkg-wip-no-dod", "wip")
        item["dod_commands"] = []
        data = {"schema_version": 2, "items": [item], "waves": []}
        errors, _ = lint_mod.lint(data)
        assert any(self._EXPECTED_MSG in e for e in errors), (
            f"Expected error containing {self._EXPECTED_MSG!r}; got: {errors}"
        )

    def test_proposed_without_dod_commands_passes(self, lint_mod):
        item = _item("pkg-proposed", "proposed")
        item["dod_commands"] = []
        data = {"schema_version": 2, "items": [item], "waves": []}
        errors, _ = lint_mod.lint(data)
        dod_errors = [e for e in errors if self._EXPECTED_MSG in e]
        assert dod_errors == []

    def test_ready_with_dod_commands_no_dod_error(self, lint_mod):
        item = _item("pkg-ready-ok", "ready")
        item["dod_commands"] = ["pytest tests/t.py"]
        data = {"schema_version": 2, "items": [item], "waves": []}
        errors, _ = lint_mod.lint(data)
        dod_errors = [e for e in errors if self._EXPECTED_MSG in e]
        assert dod_errors == []


# ===========================================================================
# 6. auto_promote_next_wave_package — registry-only readers
# ===========================================================================


def _write_registry(path: Path, reg: dict) -> None:
    import yaml
    path.write_text(yaml.dump(reg, allow_unicode=True), encoding="utf-8")


class TestGetActiveWaveFromRegistry:
    def test_returns_wip_wave(self, tmp_path, monkeypatch, promote_mod):
        reg = _reg(
            waves=[_wave("wave-done", "completed"), _wave("wave-wip", "wip")],
            items=[],
        )
        reg_file = tmp_path / "registry.yaml"
        _write_registry(reg_file, reg)
        monkeypatch.setattr(promote_mod, "BACKLOG_REGISTRY", reg_file)
        assert promote_mod._get_active_wave_from_registry() == "wave-wip"

    def test_returns_ready_when_no_wip(self, tmp_path, monkeypatch, promote_mod):
        reg = _reg(waves=[_wave("wave-r", "ready"), _wave("wave-p", "proposed")], items=[])
        reg_file = tmp_path / "registry.yaml"
        _write_registry(reg_file, reg)
        monkeypatch.setattr(promote_mod, "BACKLOG_REGISTRY", reg_file)
        assert promote_mod._get_active_wave_from_registry() == "wave-r"

    def test_returns_none_all_completed(self, tmp_path, monkeypatch, promote_mod):
        reg = _reg(waves=[_wave("wave-a", "completed")], items=[])
        reg_file = tmp_path / "registry.yaml"
        _write_registry(reg_file, reg)
        monkeypatch.setattr(promote_mod, "BACKLOG_REGISTRY", reg_file)
        assert promote_mod._get_active_wave_from_registry() is None


class TestGetNowPackageIdsFromRegistry:
    def test_returns_wip_and_ready_ids(self, tmp_path, monkeypatch, promote_mod):
        reg = _reg(
            waves=[],
            items=[
                _item("epoch-pkg-a", "wip"),
                _item("pkg-b", "ready"),
                _item("pkg-c", "closed"),
                _item("pkg-d", "proposed"),
            ],
        )
        reg_file = tmp_path / "registry.yaml"
        _write_registry(reg_file, reg)
        monkeypatch.setattr(promote_mod, "BACKLOG_REGISTRY", reg_file)
        result = promote_mod._get_now_package_ids_from_registry()
        # Both full and short ids
        assert "epoch-pkg-a" in result
        assert "pkg-a" in result
        assert "pkg-b" in result
        assert "pkg-c" not in result
        assert "pkg-d" not in result

    def test_empty_when_no_active(self, tmp_path, monkeypatch, promote_mod):
        reg = _reg(waves=[], items=[_item("p", "proposed")])
        reg_file = tmp_path / "registry.yaml"
        _write_registry(reg_file, reg)
        monkeypatch.setattr(promote_mod, "BACKLOG_REGISTRY", reg_file)
        assert promote_mod._get_now_package_ids_from_registry() == []


# ===========================================================================
# 7. auto_promote_next_wave_package.find_next_candidate
# ===========================================================================


def _write_story_index(path: Path, us_ids: list[str], status: str = "open") -> None:
    items = [
        {
            "us_id": uid,
            "title": f"Story {uid}",
            "status": status,
            "covered_by": None,
            "cjm_stage": "#1",
            "priority": "P1",
            "path": f"doc/user_stories/{uid.lower()}.md",
        }
        for uid in us_ids
    ]
    path.write_text(json.dumps({"items": items}), encoding="utf-8")


class TestFindNextCandidate:
    def test_returns_none_when_all_proposed_in_now(self, tmp_path, monkeypatch, promote_mod):
        """If the only proposed package is already active in registry (wip/ready), return None."""
        reg = _reg(
            waves=[_wave("wave-a", "wip", ["epoch-pkg-1"])],
            items=[_item("epoch-pkg-1", "ready", us=["US-1.1"])],
        )
        reg_file = tmp_path / "registry.yaml"
        _write_registry(reg_file, reg)
        idx_file = tmp_path / "index.json"
        _write_story_index(idx_file, ["US-1.1"])
        monkeypatch.setattr(promote_mod, "BACKLOG_REGISTRY", reg_file)
        monkeypatch.setattr(promote_mod, "USER_STORIES_INDEX", idx_file)

        result = promote_mod.find_next_candidate(verbose=True)
        assert result is None

    def test_returns_proposed_candidate(self, tmp_path, monkeypatch, promote_mod):
        reg = _reg(
            waves=[_wave("wave-a", "wip", ["epoch-pkg-1", "epoch-pkg-2"])],
            items=[
                _item("epoch-pkg-1", "closed", us=["US-1.1"]),
                _item("epoch-pkg-2", "proposed", us=["US-2.1"]),
            ],
        )
        reg_file = tmp_path / "registry.yaml"
        _write_registry(reg_file, reg)
        idx_file = tmp_path / "index.json"
        _write_story_index(idx_file, ["US-1.1", "US-2.1"])
        monkeypatch.setattr(promote_mod, "BACKLOG_REGISTRY", reg_file)
        monkeypatch.setattr(promote_mod, "USER_STORIES_INDEX", idx_file)

        result = promote_mod.find_next_candidate()
        assert result is not None
        assert result.id == "epoch-pkg-2"

    def test_open_story_with_covered_by_open_sentinel_is_promotable(
        self, tmp_path, monkeypatch, promote_mod
    ) -> None:
        """Индекс помечает непокрытую открытую историю как covered_by: \"open\"."""
        reg = _reg(
            waves=[_wave("wave-a", "wip", ["epoch-pkg-cov-open"])],
            items=[_item("epoch-pkg-cov-open", "proposed", us=["US-12.8"])],
        )
        reg_file = tmp_path / "registry.yaml"
        _write_registry(reg_file, reg)
        idx_file = tmp_path / "index.json"
        idx_file.write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "us_id": "US-12.8",
                            "title": "Story US-12.8",
                            "status": "open",
                            "covered_by": "open",
                            "cjm_stage": "#1",
                            "priority": "P1",
                            "path": "doc/user_stories/us-12.8.md",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(promote_mod, "BACKLOG_REGISTRY", reg_file)
        monkeypatch.setattr(promote_mod, "USER_STORIES_INDEX", idx_file)

        result = promote_mod.find_next_candidate()
        assert result is not None
        assert result.id == "epoch-pkg-cov-open"

    def test_skips_package_with_covered_user_story(self, tmp_path, monkeypatch, promote_mod):
        reg = _reg(
            waves=[_wave("wave-a", "wip", ["epoch-pkg-1"])],
            items=[_item("epoch-pkg-1", "proposed", us=["US-3.1"])],
        )
        reg_file = tmp_path / "registry.yaml"
        _write_registry(reg_file, reg)
        idx_file = tmp_path / "index.json"
        # US-3.1 is covered — should be skipped
        _write_story_index(idx_file, ["US-3.1"], status="closed")
        monkeypatch.setattr(promote_mod, "BACKLOG_REGISTRY", reg_file)
        monkeypatch.setattr(promote_mod, "USER_STORIES_INDEX", idx_file)

        result = promote_mod.find_next_candidate(verbose=True)
        assert result is None

    def test_skips_package_with_unsatisfied_dependency(self, tmp_path, monkeypatch, promote_mod):
        reg = _reg(
            waves=[_wave("wave-a", "wip", ["epoch-pkg-1"])],
            items=[
                {
                    **_item("epoch-pkg-1", "proposed", us=["US-4.1"]),
                    "depends_on": ["epoch-pkg-prereq"],
                }
            ],
        )
        reg_file = tmp_path / "registry.yaml"
        _write_registry(reg_file, reg)
        idx_file = tmp_path / "index.json"
        _write_story_index(idx_file, ["US-4.1"])
        monkeypatch.setattr(promote_mod, "BACKLOG_REGISTRY", reg_file)
        monkeypatch.setattr(promote_mod, "USER_STORIES_INDEX", idx_file)

        result = promote_mod.find_next_candidate(verbose=True)
        assert result is None

    def test_fallback_to_other_wave_when_active_exhausted(self, tmp_path, monkeypatch, promote_mod):
        reg = _reg(
            waves=[
                _wave("wave-active", "wip", ["epoch-pkg-done"]),
                _wave("wave-other", "proposed", ["epoch-pkg-next"]),
            ],
            items=[
                _item("epoch-pkg-done", "closed", us=["US-1.1"]),
                _item("epoch-pkg-next", "proposed", us=["US-2.1"], wave_id="wave-other"),
            ],
        )
        reg_file = tmp_path / "registry.yaml"
        _write_registry(reg_file, reg)
        idx_file = tmp_path / "index.json"
        _write_story_index(idx_file, ["US-1.1", "US-2.1"])
        monkeypatch.setattr(promote_mod, "BACKLOG_REGISTRY", reg_file)
        monkeypatch.setattr(promote_mod, "USER_STORIES_INDEX", idx_file)

        result = promote_mod.find_next_candidate()
        assert result is not None
        assert result.id == "epoch-pkg-next"

    def test_does_not_read_tasklist_argument(self, tmp_path, monkeypatch, promote_mod):
        """Решение только по registry; параметр tasklist_text у find_next_candidate не используется."""
        reg = _reg(waves=[], items=[])
        reg_file = tmp_path / "registry.yaml"
        _write_registry(reg_file, reg)
        idx_file = tmp_path / "index.json"
        idx_file.write_text('{"items":[]}', encoding="utf-8")
        monkeypatch.setattr(promote_mod, "BACKLOG_REGISTRY", reg_file)
        monkeypatch.setattr(promote_mod, "USER_STORIES_INDEX", idx_file)

        result = promote_mod.find_next_candidate()
        assert result is None


# ===========================================================================
# 8. auto_promote_next_wave_package._build_contract_block
# ===========================================================================


class TestBuildContractBlock:
    def _make_pkg(self, dod_commands: list[str], promote_mod) -> object:
        return promote_mod.WavePackage(
            id="epoch-e99-z1-test",
            wave_id="wave-test",
            wave_position=1,
            status="ready",
            user_stories=["US-9.1"],
            cjm_moments=["#1 Discover"],
            blocks="Test outcome block",
            depends_on=[],
            write_set_max=4,
            read_set_hint=["app/foo.py"],
            exit_artifact="app/foo.py",
            notes="",
            cost_estimate="S",
            dod_commands=dod_commands,
        )

    def test_uses_real_dod_commands(self, promote_mod):
        pkg = self._make_pkg(["pytest tests/test_foo.py -v", "pytest tests/test_bar.py"], promote_mod)
        block = promote_mod._build_contract_block(pkg)
        assert "pytest tests/test_foo.py -v" in block
        assert "pytest tests/test_bar.py" in block

    def test_no_todo_placeholder_when_dod_provided(self, promote_mod):
        pkg = self._make_pkg(["pytest tests/real.py"], promote_mod)
        block = promote_mod._build_contract_block(pkg)
        assert "TODO" not in block
        assert "py_compile" not in block

    def test_fallback_message_when_no_dod(self, promote_mod):
        pkg = self._make_pkg([], promote_mod)
        block = promote_mod._build_contract_block(pkg)
        assert "backlog_registry.yaml" in block

    def test_block_has_generated_comment(self, promote_mod):
        pkg = self._make_pkg(["pytest"], promote_mod)
        block = promote_mod._build_contract_block(pkg)
        assert "GENERATED from backlog_registry.yaml" in block

    def test_contract_id_uses_full_id(self, promote_mod):
        """Contract block uses full id with epoch- prefix to match lint rendering."""
        pkg = self._make_pkg(["pytest"], promote_mod)
        block = promote_mod._build_contract_block(pkg)
        assert "### epoch-e99-z1-test Contract" in block


# ===========================================================================
# 9. backlog_registry_lint._strip_registry_generated_contracts
# ===========================================================================


class TestStripRegistryGeneratedContracts:
    def test_removes_marked_contract_blocks(self, lint_mod):
        now_body = textwrap.dedent(
            """\
            preamble

            ### epoch-a Contract

            <!-- GENERATED from backlog_registry.yaml — do not edit manually -->

            - line

            ### epoch-b Contract

            <!-- GENERATED from backlog_registry.yaml — do not edit manually -->

            - other

            ### Wave queue
            """
        )
        out = lint_mod._strip_registry_generated_contracts(now_body)
        assert "epoch-a Contract" not in out
        assert "epoch-b Contract" not in out
        assert "preamble" in out
        assert "### Wave queue" in out

    def test_keeps_manual_contract_without_marker(self, lint_mod):
        now_body = textwrap.dedent(
            """\
            ### Manual epoch-x Contract

            - hand-edited

            ### epoch-g Contract

            <!-- GENERATED from backlog_registry.yaml — do not edit manually -->

            - gen
            """
        )
        out = lint_mod._strip_registry_generated_contracts(now_body)
        assert "Manual epoch-x Contract" in out
        assert "hand-edited" in out
        assert "epoch-g Contract" not in out

    def test_reconcile_clears_stale_then_inserts_new(self, lint_mod):
        stale = _TASKLIST_TEMPLATE.replace(
            "### Wave queue",
            textwrap.dedent(
                """\
                ### epoch-stale Contract

                <!-- GENERATED from backlog_registry.yaml — do not edit manually -->

                - stale

                ### Wave queue"""
            ),
        )
        contracts = textwrap.dedent(
            """\
            ### epoch-new Contract

            <!-- GENERATED from backlog_registry.yaml — do not edit manually -->

            fresh
            """
        )
        out = lint_mod._reconcile_generated_contracts_in_now(stale, contracts)
        assert "epoch-stale" not in out
        assert "epoch-new Contract" in out
        assert "fresh" in out


# ===========================================================================
# 10. generate_next_prompt._init_team_artifacts — execution_contract.md skeleton
# ===========================================================================


class TestInitTeamArtifactsSkeleton:
    def _contract(self) -> dict:
        return {
            "PACKAGE_ID": "epoch-e99-test",
            "PACKAGE_TITLE": "Test package",
            "USER_STORIES": "US-9.1",
            "WRITE_SET_MAX": "4",
            "DOD_COMMANDS": "pytest tests/test_foo.py -v",
            "OUTCOMES": "app/foo.py with bar feature",
        }

    def test_creates_execution_contract_skeleton(self, tmp_path, monkeypatch, gen_mod):
        monkeypatch.setattr(gen_mod, "TEAM_ARTIFACTS_DIR", tmp_path)
        contract = self._contract()
        gen_mod._init_team_artifacts("epoch-e99-test", "prompt text", contract, "2026-01-01")
        exec_file = tmp_path / "epoch-e99-test" / "execution_contract.md"
        assert exec_file.exists()

    def test_skeleton_contains_dod_commands(self, tmp_path, monkeypatch, gen_mod):
        monkeypatch.setattr(gen_mod, "TEAM_ARTIFACTS_DIR", tmp_path)
        contract = self._contract()
        gen_mod._init_team_artifacts("epoch-e99-test", "prompt", contract, "2026-01-01")
        text = (tmp_path / "epoch-e99-test" / "execution_contract.md").read_text()
        assert "pytest tests/test_foo.py -v" in text

    def test_skeleton_has_started_status(self, tmp_path, monkeypatch, gen_mod):
        monkeypatch.setattr(gen_mod, "TEAM_ARTIFACTS_DIR", tmp_path)
        contract = self._contract()
        gen_mod._init_team_artifacts("epoch-e99-test", "prompt", contract, "2026-01-01")
        text = (tmp_path / "epoch-e99-test" / "execution_contract.md").read_text()
        assert "STARTED" in text

    def test_existing_skeleton_not_overwritten(self, tmp_path, monkeypatch, gen_mod):
        monkeypatch.setattr(gen_mod, "TEAM_ARTIFACTS_DIR", tmp_path)
        contract = self._contract()
        pkg_dir = tmp_path / "epoch-e99-test"
        pkg_dir.mkdir(parents=True)
        existing = pkg_dir / "execution_contract.md"
        existing.write_text("# existing content with EVIDENCE", encoding="utf-8")

        gen_mod._init_team_artifacts("epoch-e99-test", "prompt", contract, "2026-01-01")
        assert existing.read_text(encoding="utf-8") == "# existing content with EVIDENCE"

    def test_planning_prompt_always_overwritten(self, tmp_path, monkeypatch, gen_mod):
        monkeypatch.setattr(gen_mod, "TEAM_ARTIFACTS_DIR", tmp_path)
        contract = self._contract()
        gen_mod._init_team_artifacts("epoch-e99-test", "prompt v1", contract, "2026-01-01")
        gen_mod._init_team_artifacts("epoch-e99-test", "prompt v2", contract, "2026-01-02")
        plan_file = tmp_path / "epoch-e99-test" / "planning_prompt.md"
        assert "prompt v2" in plan_file.read_text(encoding="utf-8")


def test_resume_prompt_derives_write_set_from_exit_artifact_when_max_is_numeric(gen_mod, tmp_path):
    pkg = "pkg-resume"
    gen_mod.ROOT = tmp_path
    prompt_file = tmp_path / "archive" / "agent_prompts" / "exec_prompt.md"
    prompt_file.parent.mkdir(parents=True)
    prompt_file.write_text("# prompt\n", encoding="utf-8")
    ws = gen_mod.WorkState(
        gen_mod.WorkState.EXECUTION_READY,
        exec_prompt_file=prompt_file,
    )
    contract = {
        "PACKAGE_ID": pkg,
        "WRITE_SET_MAX": "6",
        "DOD_COMMANDS": "pytest tests/test_answer_parser.py -v",
        "EXIT_ARTIFACT": (
            "`app/answer_parser.py`, `app/tutor_context_parser.py`, "
            "`app/session_analytics_parser.py` and `tests/test_answer_parser.py`"
        ),
    }

    text = gen_mod.generate_resume_prompt(contract, ws, failing_commands=[])

    assert "- `app/answer_parser.py`" in text
    assert "- `app/tutor_context_parser.py`" in text
    assert "- `app/session_analytics_parser.py`" in text
    assert "- `tests/test_answer_parser.py`" in text
    assert "- (see contract)" not in text


def test_generate_next_prompt_ignores_archived_exec_prompt_without_contract(gen_mod, tmp_path, monkeypatch):
    monkeypatch.setattr(gen_mod, "TEAM_ARTIFACTS_DIR", tmp_path / "team_artifacts")
    monkeypatch.setattr(gen_mod, "ARCHIVE_DIR", tmp_path / "agent_prompts")

    package_id = "epoch-router-proof"
    gen_mod.ARCHIVE_DIR.mkdir(parents=True)
    (gen_mod.ARCHIVE_DIR / "epoch_router_proof_exec_prompt_quick_2026-05-08.md").write_text(
        "prompt body",
        encoding="utf-8",
    )

    ws = gen_mod._detect_work_state(package_id)

    assert ws.state == gen_mod.WorkState.FRESH
    assert ws.exec_prompt_file is None


def test_skeleton_has_all_required_sections(gen_mod, tmp_path, monkeypatch):
    """STATE-A guard relies on ## Evidence, ## DoD commands, ## Outcomes delivered."""
    monkeypatch.setattr(gen_mod, "TEAM_ARTIFACTS_DIR", tmp_path)
    contract = {
        "PACKAGE_ID": "epoch-e99-test",
        "PACKAGE_TITLE": "Test package",
        "USER_STORIES": "US-9.1",
        "WRITE_SET_MAX": "4",
        "DOD_COMMANDS": "pytest tests/test_foo.py -v",
        "OUTCOMES": "app/foo.py with bar feature",
    }
    gen_mod._init_team_artifacts("epoch-e99-test", "prompt", contract, "2026-01-01")
    text = (tmp_path / "epoch-e99-test" / "execution_contract.md").read_text(encoding="utf-8")
    assert "## Evidence" in text, "## Evidence section missing from skeleton"
    assert "## DoD commands" in text, "## DoD commands section missing from skeleton"
    assert "## Outcomes delivered" in text, "## Outcomes delivered section missing from skeleton"


# ===========================================================================
# 11. Integration: lint sync round-trip — ACTIVE_WAVE + contract in tasklist
# ===========================================================================


class TestLintSyncRoundTrip:
    """Smoke test: after sync, tasklist.md contains ACTIVE_WAVE marker and contract."""

    def test_active_wave_marker_in_wave_queue(self, lint_mod):
        reg = _reg(
            waves=[_wave("wave-smoke", "wip", ["epoch-pkg-smoke"])],
            items=[_item("epoch-pkg-smoke", "ready", dod=["pytest tests/t.py"])],
        )
        rendered = lint_mod._render_wave_queue(reg)
        assert "<!-- ACTIVE_WAVE: wave-smoke -->" in rendered

    def test_real_dod_in_rendered_contract(self, lint_mod):
        reg = _reg(
            waves=[_wave("wave-x", "wip", ["epoch-e1-real-dod"])],
            items=[
                {
                    **_item("epoch-e1-real-dod", "ready"),
                    "dod_commands": [
                        ".venv/Scripts/python.exe -m pytest tests/test_specific.py -v",
                    ],
                }
            ],
        )
        contracts = lint_mod._render_active_contracts(reg)
        assert "test_specific.py" in contracts
        assert "TODO" not in contracts

    def test_upsert_round_trip_idempotent(self, lint_mod):
        """Running _upsert_contracts_in_now twice with same content is idempotent."""
        contracts = "### my-pkg Contract\n\ncontent here\n"
        result1 = lint_mod._upsert_contracts_in_now(_TASKLIST_TEMPLATE, contracts)
        result2 = lint_mod._upsert_contracts_in_now(result1, contracts)
        # Both runs produce same result (idempotent)
        assert result1.count("### my-pkg Contract") == 1
        assert result2.count("### my-pkg Contract") == 1

    def test_full_sync_idempotent(self, lint_mod):
        """Registry → render contracts → insert → render again → insert again: no drift."""
        reg = _reg(
            waves=[_wave("wave-sync", "wip", ["epoch-sync-pkg"])],
            items=[_item("epoch-sync-pkg", "ready", dod=["pytest tests/test_sync.py -v"])],
        )
        contracts = lint_mod._render_active_contracts(reg)
        t1 = lint_mod._upsert_contracts_in_now(_TASKLIST_TEMPLATE, contracts)
        # Second pass: re-render from same registry, re-insert into already-synced tasklist
        contracts2 = lint_mod._render_active_contracts(reg)
        t2 = lint_mod._upsert_contracts_in_now(t1, contracts2)
        assert t1 == t2, "Double sync produced different output — not idempotent"


# ===========================================================================
# 12. run_autonomous._set_registry_active_wave_id
# ===========================================================================


class TestSetRegistryActiveWaveId:
    @pytest.fixture
    def autonomous_mod(self, monkeypatch):
        import importlib, sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        mod = importlib.import_module("run_autonomous")
        return mod

    def test_writes_field_when_absent(self, autonomous_mod, tmp_path):
        reg_path = tmp_path / "registry.yaml"
        reg_path.write_text(
            "schema_version: 2\nitems: []\nwaves: []\n",
            encoding="utf-8",
        )
        autonomous_mod._set_registry_active_wave_id(reg_path, "wave-foo")
        text = reg_path.read_text(encoding="utf-8")
        assert "active_wave_id: wave-foo" in text

    def test_replaces_existing_field(self, autonomous_mod, tmp_path):
        reg_path = tmp_path / "registry.yaml"
        reg_path.write_text(
            "schema_version: 2\nactive_wave_id: old-wave\nitems: []\n",
            encoding="utf-8",
        )
        autonomous_mod._set_registry_active_wave_id(reg_path, "new-wave")
        text = reg_path.read_text(encoding="utf-8")
        assert "active_wave_id: new-wave" in text
        assert "old-wave" not in text

    def test_handles_null_existing_value(self, autonomous_mod, tmp_path):
        """Default registry has 'active_wave_id: null' — must replace, not duplicate."""
        reg_path = tmp_path / "registry.yaml"
        reg_path.write_text(
            "schema_version: 2\nactive_wave_id: null\nitems: []\n",
            encoding="utf-8",
        )
        autonomous_mod._set_registry_active_wave_id(reg_path, "wave-x")
        text = reg_path.read_text(encoding="utf-8")
        assert text.count("active_wave_id:") == 1
        assert "active_wave_id: wave-x" in text


# ===========================================================================
# 13. run_autonomous._wave_auto_continue (BUG-8 coverage)
# ===========================================================================


class TestWaveAutoContinue:
    @pytest.fixture
    def autonomous_mod(self):
        import importlib, sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        return importlib.import_module("run_autonomous")

    def _make_registry(self, tmp_path, *, items, waves):
        reg = {"schema_version": 2, "active_wave_id": None, "items": items, "waves": waves}
        reg_path = tmp_path / "registry.yaml"
        import yaml
        reg_path.write_text(yaml.safe_dump(reg, sort_keys=False), encoding="utf-8")
        return reg_path

    def test_returns_none_for_unknown_package(self, autonomous_mod, tmp_path, monkeypatch):
        reg_path = self._make_registry(tmp_path, items=[], waves=[])
        (tmp_path / "doc").mkdir(exist_ok=True)
        (tmp_path / "doc" / "backlog_registry.yaml").write_text(
            reg_path.read_text(encoding="utf-8"), encoding="utf-8"
        )
        monkeypatch.setattr(autonomous_mod, "ROOT", tmp_path)
        result = autonomous_mod._wave_auto_continue("unknown-pkg")
        assert result is None

    def test_returns_none_when_package_has_no_wave(self, autonomous_mod, tmp_path, monkeypatch):
        items = [{"id": "loose-pkg", "status": "closed", "wave_id": None}]
        reg_path = self._make_registry(tmp_path, items=items, waves=[])
        (tmp_path / "doc").mkdir(exist_ok=True)
        (tmp_path / "doc" / "backlog_registry.yaml").write_text(
            reg_path.read_text(encoding="utf-8"), encoding="utf-8"
        )
        monkeypatch.setattr(autonomous_mod, "ROOT", tmp_path)
        result = autonomous_mod._wave_auto_continue("loose-pkg")
        assert result is None

    def test_does_not_read_tasklist(self, autonomous_mod, tmp_path, monkeypatch):
        """Critical SSoT invariant: function must work without doc/tasklist.md."""
        items = [
            {"id": "pkg-a", "status": "closed", "wave_id": "w-1"},
            {"id": "pkg-b", "status": "proposed", "wave_id": "w-1"},
        ]
        waves = [{"id": "w-1", "status": "wip", "packages": ["pkg-a", "pkg-b"]}]
        reg_path = self._make_registry(tmp_path, items=items, waves=waves)
        (tmp_path / "doc").mkdir(exist_ok=True)
        (tmp_path / "doc" / "backlog_registry.yaml").write_text(
            reg_path.read_text(encoding="utf-8"), encoding="utf-8"
        )
        # Intentionally do NOT create tasklist.md — function must not read it.
        monkeypatch.setattr(autonomous_mod, "ROOT", tmp_path)
        # Stub subprocess.run so we don't actually invoke lint
        called: list = []
        import subprocess as _sp
        monkeypatch.setattr(_sp, "run", lambda *a, **kw: called.append(a) or _sp.CompletedProcess(args=[], returncode=0))
        result = autonomous_mod._wave_auto_continue("pkg-a")
        assert result == "pkg-b"
        assert called, "subprocess.run (lint sync) must be invoked"

    def test_marks_wave_completed_on_last_package(self, autonomous_mod, tmp_path, monkeypatch):
        """When the closed package is the last in its wave, wave status → completed."""
        import yaml
        items = [{"id": "pkg-only", "status": "closed", "wave_id": "wave-solo"}]
        waves = [{"id": "wave-solo", "status": "wip", "packages": ["pkg-only"], "north_star": "ship it"}]
        reg_path = self._make_registry(tmp_path, items=items, waves=waves)
        (tmp_path / "doc").mkdir(exist_ok=True)
        registry_file = tmp_path / "doc" / "backlog_registry.yaml"
        registry_file.write_text(reg_path.read_text(encoding="utf-8"), encoding="utf-8")
        monkeypatch.setattr(autonomous_mod, "ROOT", tmp_path)

        result = autonomous_mod._wave_auto_continue("pkg-only")

        assert result is None, "Last package in wave must return None"
        updated = yaml.safe_load(registry_file.read_text(encoding="utf-8"))
        wave = next(w for w in updated["waves"] if w["id"] == "wave-solo")
        assert wave["status"] == "completed", "Wave must be marked completed after last package closes"
