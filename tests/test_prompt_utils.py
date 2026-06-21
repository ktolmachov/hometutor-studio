"""
tests/test_prompt_utils.py — Unit tests for scripts/prompt_utils.py

Tests cover:
 - Tasklist parsing (Truth View, package contracts)
 - DoD command extraction (with quote-aware splitting)
 - Work-state detection
 - Pipeline metrics parsing
 - String helpers
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prompt_utils as pu


def _patch_git_commit(
    monkeypatch,
    returncode: int = 0,
    path_returncode: int = 0,
    changed_paths: str = "app/flashcards.py\n",
):
    def _fake_run(args, **kwargs):
        if args[:3] == ["git", "rev-parse", "--verify"]:
            return SimpleNamespace(stdout="", stderr="", returncode=returncode)
        if args[:3] == ["git", "cat-file", "-e"]:
            return SimpleNamespace(stdout="", stderr="", returncode=path_returncode)
        if args[:3] == ["git", "diff-tree", "--no-commit-id"]:
            return SimpleNamespace(stdout=changed_paths, stderr="", returncode=0)
        return SimpleNamespace(stdout="", stderr="", returncode=0)

    monkeypatch.setattr(pu.subprocess, "run", _fake_run)


def test_verification_only_evidence_requires_existing_paths(tmp_path, monkeypatch):
    _patch_git_commit(monkeypatch, returncode=0)
    delivered = tmp_path / "app" / "flashcards.py"
    delivered.parent.mkdir(parents=True)
    delivered.write_text("# delivered\n", encoding="utf-8")

    ok, reason = pu.validate_verification_only_evidence(
        "Pre-existing delivery evidence:\n"
        "- commit: abc1234\n"
        "- files: app/flashcards.py\n",
        root=tmp_path,
    )

    assert ok is True
    assert reason is None

    ok, reason = pu.validate_verification_only_evidence(
        "Pre-existing delivery evidence:\n"
        "- commit: abc1234\n"
        "- files: app/missing_panel.py\n",
        root=tmp_path,
    )

    assert ok is False
    assert "missing file" in (reason or "")


def test_verification_only_evidence_rejects_unknown_commit(tmp_path, monkeypatch):
    _patch_git_commit(monkeypatch, returncode=1)
    delivered = tmp_path / "app" / "flashcards.py"
    delivered.parent.mkdir(parents=True)
    delivered.write_text("# delivered\n", encoding="utf-8")

    ok, reason = pu.validate_verification_only_evidence(
        "Pre-existing delivery evidence:\n"
        "- commit: abc1234\n"
        "- files: app/flashcards.py\n",
        root=tmp_path,
    )

    assert ok is False
    assert "does not resolve" in (reason or "")


def test_verification_only_evidence_rejects_commit_without_referenced_path(tmp_path, monkeypatch):
    _patch_git_commit(monkeypatch, returncode=0, path_returncode=1)
    delivered = tmp_path / "app" / "flashcards.py"
    delivered.parent.mkdir(parents=True)
    delivered.write_text("# delivered\n", encoding="utf-8")

    ok, reason = pu.validate_verification_only_evidence(
        "Pre-existing delivery evidence:\n"
        "- commit: abc1234\n"
        "- files: app/flashcards.py\n",
        root=tmp_path,
    )

    assert ok is False
    assert "does not contain" in (reason or "")


def test_verification_only_evidence_rejects_commit_that_only_contains_path(tmp_path, monkeypatch):
    _patch_git_commit(monkeypatch, returncode=0, path_returncode=0, changed_paths="doc/changelog.md\n")
    delivered = tmp_path / "app" / "flashcards.py"
    delivered.parent.mkdir(parents=True)
    delivered.write_text("# delivered\n", encoding="utf-8")

    ok, reason = pu.validate_verification_only_evidence(
        "Pre-existing delivery evidence:\n"
        "- commit: abc1234\n"
        "- files: app/flashcards.py\n",
        root=tmp_path,
    )

    assert ok is False
    assert "does not change" in (reason or "")


def test_verification_only_evidence_requires_marker_when_git_change_proof_inconclusive(tmp_path, monkeypatch):
    _patch_git_commit(monkeypatch, returncode=0, path_returncode=0, changed_paths="")
    delivered = tmp_path / "app" / "flashcards.py"
    delivered.parent.mkdir(parents=True)
    delivered.write_text("# delivered\n", encoding="utf-8")

    ok, reason = pu.validate_verification_only_evidence(
        "Pre-existing delivery evidence:\n"
        "- commit: abc1234\n"
        "- files: app/flashcards.py\n",
        root=tmp_path,
    )

    assert ok is False
    assert "evidence_inconclusive_allowed" in (reason or "")

    ok, reason = pu.validate_verification_only_evidence(
        "Pre-existing delivery evidence:\n"
        "- commit: abc1234\n"
        "- files: app/flashcards.py\n"
        "- note: evidence_inconclusive_allowed\n",
        root=tmp_path,
    )

    assert ok is True
    assert reason is None


def test_verification_only_evidence_accepts_git_show_fallback_without_marker(tmp_path, monkeypatch):
    def _fake_run(args, **kwargs):
        if args[:3] == ["git", "rev-parse", "--verify"]:
            return SimpleNamespace(stdout="", stderr="", returncode=0)
        if args[:3] == ["git", "cat-file", "-e"]:
            return SimpleNamespace(stdout="", stderr="", returncode=0)
        if args[:3] == ["git", "diff-tree", "--no-commit-id"]:
            return SimpleNamespace(stdout="", stderr="", returncode=0)
        if args[:4] == ["git", "show", "--pretty=format:", "--name-only"]:
            return SimpleNamespace(stdout="app/flashcards.py\n", stderr="", returncode=0)
        return SimpleNamespace(stdout="", stderr="", returncode=0)

    monkeypatch.setattr(pu.subprocess, "run", _fake_run)
    delivered = tmp_path / "app" / "flashcards.py"
    delivered.parent.mkdir(parents=True)
    delivered.write_text("# delivered\n", encoding="utf-8")

    ok, reason = pu.validate_verification_only_evidence(
        "Pre-existing delivery evidence:\n"
        "- commit: abc1234\n"
        "- files: app/flashcards.py\n",
        root=tmp_path,
    )

    assert ok is True
    assert reason is None


def test_verification_evidence_changed_files_returns_only_changed_evidence_paths(tmp_path, monkeypatch):
    import prompt_utils as pu

    (tmp_path / "app").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "app" / "x.py").write_text("# x\n", encoding="utf-8")
    (tmp_path / "tests" / "test_x.py").write_text("# test\n", encoding="utf-8")

    def _fake_run(args, **kwargs):
        if args[:3] == ["git", "diff-tree", "--no-commit-id"]:
            return SimpleNamespace(stdout="app/x.py\n", returncode=0)
        return SimpleNamespace(stdout="", returncode=0)

    monkeypatch.setattr(pu.subprocess, "run", _fake_run)

    changed = pu.verification_evidence_changed_files(
        "Pre-existing delivery evidence:\n"
        "- commit: abc1234\n"
        "- files: app/x.py, tests/test_x.py\n",
        tmp_path,
    )

    assert changed == {"app/x.py"}


def test_verification_only_evidence_ignores_paths_after_evidence_section(tmp_path, monkeypatch):
    _patch_git_commit(monkeypatch, returncode=0, path_returncode=0, changed_paths="app/flashcards.py\n")
    delivered = tmp_path / "app" / "flashcards.py"
    delivered.parent.mkdir(parents=True)
    delivered.write_text("# delivered\n", encoding="utf-8")

    ok, reason = pu.validate_verification_only_evidence(
        "Pre-existing delivery evidence:\n"
        "- commit: abc1234\n"
        "- files:\n"
        "  - app/flashcards.py\n"
        "---\n"
        "Verification commands:\n"
        "- python -m pytest tests/test_flashcards.py -v\n",
        root=tmp_path,
    )

    assert ok is True
    assert reason is None


def test_verification_only_evidence_rejects_vague_commit():
    ok, reason = pu.validate_verification_only_evidence(
        "Pre-existing delivery evidence:\n"
        "- commit: pre-existing in current branch history\n"
        "- files: app/flashcards.py\n"
    )

    assert ok is False
    assert "commit SHA" in (reason or "")


def test_ensure_utf8_stdio_uses_reconfigure_when_available(monkeypatch):
    class _Fake:
        def __init__(self):
            self.called: list[tuple[str, str]] = []

        def reconfigure(self, *, encoding: str, errors: str):  # noqa: A003
            self.called.append((encoding, errors))

    fake_out = _Fake()
    fake_err = _Fake()
    monkeypatch.setattr(pu.sys, "stdout", fake_out)
    monkeypatch.setattr(pu.sys, "stderr", fake_err)

    pu.ensure_utf8_stdio()

    assert fake_out.called == [("utf-8", "replace")]
    assert fake_err.called == [("utf-8", "replace")]


# ---------------------------------------------------------------------------
# Fixtures — synthetic tasklist content
# ---------------------------------------------------------------------------

TASKLIST_SIMPLE = """\
# tasklist

## Now

| Package | Status |
|---------|--------|
| epoch-foo | WIP |
| epoch-bar | ready |
| epoch-baz | proposed |

### epoch-foo Contract

| Field | Value |
|-------|-------|
| PACKAGE_ID | epoch-foo |
| PACKAGE_TITLE | Foo feature |
| CJM_STAGE | `#3` — Learn |
| USER_STORIES | US-3.1, US-3.2 |
| DOD_COMMANDS | pytest tests/test_foo.py -v; python scripts/check.py |
| WRITE_SET_MAX | 4 |
| OUTCOMES | 1. Learner sees foo. 2. Foo persists across sessions. |
"""

TASKLIST_WITH_OPEN = """\
## Now

| Package | Status |
|---------|--------|
| epoch-alpha | open |
| epoch-beta  | WIP  |
"""

TASKLIST_PYTHON_ONELINER = """\
## Now

| Package | Status |
|---------|--------|
| epoch-py | WIP |

### epoch-py Contract

| Field | Value |
|-------|-------|
| PACKAGE_ID | epoch-py |
| DOD_COMMANDS | python -c "import json; json.load(open('f.json'))"; pytest tests/ |
"""


# ---------------------------------------------------------------------------
# parse_truth_view
# ---------------------------------------------------------------------------

class TestParseTruthView:
    def test_finds_wip_and_ready(self):
        rows = pu.parse_truth_view(TASKLIST_SIMPLE)
        assert len(rows) == 3
        assert rows[0]["package"] == "epoch-foo"
        assert rows[0]["status"] == "WIP"

    def test_returns_empty_when_no_now_section(self):
        rows = pu.parse_truth_view("# tasklist\n\n## Someday\n\nnothing")
        assert rows == []

    def test_parses_all_rows(self):
        rows = pu.parse_truth_view(TASKLIST_SIMPLE)
        packages = [r["package"] for r in rows]
        assert "epoch-foo" in packages
        assert "epoch-bar" in packages
        assert "epoch-baz" in packages

    def test_open_status_recognized(self):
        rows = pu.parse_truth_view(TASKLIST_WITH_OPEN)
        assert any(r["status"] == "open" for r in rows)


class TestBacklogTruthView:
    def test_registry_view_exposes_now_truth_and_wave_queue(self, tmp_path):
        registry = tmp_path / "backlog_registry.yaml"
        registry.write_text(
            """schema_version: 2
active_wave_id: wave-a
waves:
  - id: wave-a
    status: ready
    packages:
      - epoch-active
      - epoch-next
    north_star: learner wins
    kill_switch: stop on red
  - id: wave-b
    status: proposed
    packages:
      - epoch-later
items:
  - id: epoch-active
    status: ready
    cjm_moments: ["#2 First Answer"]
    user_stories: ["US-2.1"]
    notes: Active package
  - id: epoch-plan
    status: proposed
    user_stories: ["US-3.1"]
""",
            encoding="utf-8",
        )

        view = pu.get_backlog_truth_view(registry)

        assert view["truth_view"][0]["package"] == "epoch-active"
        assert view["truth_view"][0]["cjm_moments"] == ["#2 First Answer"]
        assert view["truth_view"][0]["user_stories"] == ["US-2.1"]
        assert view["resolved_active_package"] == "epoch-active"
        assert view["now"][0]["package"] == "epoch-active"
        assert any(row["package"] == "epoch-plan" for row in view["now"])
        wave_queue = view["wave_queue"]
        assert wave_queue["active_wave"] == "wave-a"
        assert wave_queue["queued_same_wave"] == ["epoch-active", "epoch-next"]
        assert wave_queue["queued_other_waves"][0]["id"] == "wave-b"

    def test_active_ready_package_from_registry_ignores_proposed(self, tmp_path):
        registry = tmp_path / "backlog_registry.yaml"
        registry.write_text(
            """schema_version: 2
items:
  - id: epoch-proposed
    status: proposed
  - id: epoch-ready
    status: ready
""",
            encoding="utf-8",
        )

        assert pu.active_ready_package_from_registry(registry) == "epoch-ready"


# ---------------------------------------------------------------------------
# select_package
# ---------------------------------------------------------------------------

class TestSelectPackage:
    def setup_method(self):
        self.rows = pu.parse_truth_view(TASKLIST_SIMPLE)

    def test_explicit_selection(self):
        row = pu.select_package(self.rows, "epoch-bar")
        assert row is not None
        assert row["package"] == "epoch-bar"

    def test_explicit_missing_returns_none(self):
        row = pu.select_package(self.rows, "epoch-nonexistent")
        assert row is None

    def test_priority_picks_wip_over_ready(self):
        row = pu.select_package(self.rows, None)
        assert row is not None
        assert row["package"] == "epoch-foo"  # WIP before ready

    def test_open_status_selected_when_no_wip(self):
        rows = pu.parse_truth_view(TASKLIST_WITH_OPEN)
        row = pu.select_package(rows, None)
        assert row is not None
        # WIP is present and takes priority over open
        assert row["status"].lower() in {"wip", "open"}

    def test_empty_rows_returns_none(self):
        assert pu.select_package([], None) is None


# ---------------------------------------------------------------------------
# parse_contract
# ---------------------------------------------------------------------------

class TestParseContract:
    def test_parses_package_id(self):
        contract = pu.parse_contract(TASKLIST_SIMPLE, "epoch-foo")
        assert contract.get("PACKAGE_ID") == "epoch-foo"

    def test_parses_title(self):
        contract = pu.parse_contract(TASKLIST_SIMPLE, "epoch-foo")
        assert contract.get("PACKAGE_TITLE") == "Foo feature"

    def test_missing_package_returns_empty(self):
        contract = pu.parse_contract(TASKLIST_SIMPLE, "epoch-nonexistent")
        assert contract == {}

    def test_parses_user_stories(self):
        contract = pu.parse_contract(TASKLIST_SIMPLE, "epoch-foo")
        assert "US-3.1" in contract.get("USER_STORIES", "")

    def test_parses_dod_commands(self):
        contract = pu.parse_contract(TASKLIST_SIMPLE, "epoch-foo")
        assert "pytest" in contract.get("DOD_COMMANDS", "")


# ---------------------------------------------------------------------------
# extract_dod_commands
# ---------------------------------------------------------------------------

class TestExtractDodCommands:
    def test_simple_split(self):
        cmds = pu.extract_dod_commands("pytest tests/ -v; python check.py")
        assert cmds == ["pytest tests/ -v", "python check.py"]

    def test_python_oneliner_not_split(self):
        raw = 'python -c "import json; json.load(open(\'f.json\'))"; pytest tests/'
        cmds = pu.extract_dod_commands(raw)
        assert len(cmds) == 2
        assert cmds[0].startswith("python -c")
        assert "import json; json.load" in cmds[0]
        assert cmds[1] == "pytest tests/"

    def test_single_command_no_semicolon(self):
        cmds = pu.extract_dod_commands("pytest tests/test_foo.py -v")
        assert cmds == ["pytest tests/test_foo.py -v"]

    def test_empty_string(self):
        assert pu.extract_dod_commands("") == []

    def test_strips_backticks(self):
        cmds = pu.extract_dod_commands("`pytest tests/`")
        assert cmds == ["pytest tests/"]

    def test_single_quotes_respected(self):
        raw = "python -c 'import sys; sys.exit(0)'; echo done"
        cmds = pu.extract_dod_commands(raw)
        assert len(cmds) == 2
        assert "sys.exit(0)" in cmds[0]

    def test_three_commands(self):
        raw = "pytest a.py; pytest b.py; python check.py"
        cmds = pu.extract_dod_commands(raw)
        assert len(cmds) == 3

    def test_realworld_contract(self):
        raw = pu.parse_contract(TASKLIST_PYTHON_ONELINER, "epoch-py").get("DOD_COMMANDS", "")
        cmds = pu.extract_dod_commands(raw)
        assert len(cmds) == 2
        assert "json.load" in cmds[0]
        assert cmds[1] == "pytest tests/"


# ---------------------------------------------------------------------------
# extract_us_ids
# ---------------------------------------------------------------------------

class TestExtractUsIds:
    def test_finds_multiple(self):
        ids = pu.extract_us_ids("US-3.1, US-3.2 and US-15.4")
        assert ids == ["US-3.1", "US-3.2", "US-15.4"]

    def test_case_insensitive(self):
        ids = pu.extract_us_ids("us-1.2")
        assert len(ids) == 1
        assert ids[0] == "us-1.2"

    def test_empty_returns_empty(self):
        assert pu.extract_us_ids("n/a (infra package)") == []

    def test_no_false_positives(self):
        assert pu.extract_us_ids("This is a normal sentence.") == []

    def test_deduplicates_case_insensitively(self):
        # Same story mentioned twice must collapse to a single entry,
        # preserving the casing and order of the first occurrence.
        ids = pu.extract_us_ids("US-3.1 is blocked by US-3.1 and us-3.1")
        assert ids == ["US-3.1"]

    def test_dedup_preserves_order_across_stories(self):
        ids = pu.extract_us_ids("US-7.3, US-5.1, US-7.3, US-8.2")
        assert ids == ["US-7.3", "US-5.1", "US-8.2"]


class TestExtractListItems:
    def test_parses_bullets(self):
        items = pu.extract_list_items("- alpha\n- beta")
        assert items == ["alpha", "beta"]

    def test_parses_commas(self):
        items = pu.extract_list_items("`a`, `b`, c")
        assert items == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# slug
# ---------------------------------------------------------------------------

class TestSlug:
    def test_hyphen_to_underscore(self):
        assert pu.slug("epoch-foo-bar") == "epoch_foo_bar"

    def test_special_chars(self):
        assert pu.slug("epoch-us7-3") == "epoch_us7_3"

    def test_already_clean(self):
        assert pu.slug("epochfoo") == "epochfoo"


class TestDetectWorkState:
    def test_archived_exec_prompt_without_contract_is_fresh(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pu, "TEAM_ARTIFACTS", tmp_path / "team_artifacts")
        monkeypatch.setattr(pu, "AGENT_PROMPTS", tmp_path / "agent_prompts")

        package_id = "epoch-router-proof"
        pu.AGENT_PROMPTS.mkdir(parents=True)
        (pu.AGENT_PROMPTS / "epoch_router_proof_exec_prompt_quick_2026-05-08.md").write_text(
            "prompt body",
            encoding="utf-8",
        )

        assert pu.detect_work_state(package_id) == pu.WORK_STATE_FRESH

    def test_started_only_contract_is_not_execution_ready(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pu, "TEAM_ARTIFACTS", tmp_path / "team_artifacts")

        package_id = "epoch-router-proof"
        pkg_dir = pu.TEAM_ARTIFACTS / package_id
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "execution_contract.md").write_text("STARTED", encoding="utf-8")

        assert pu.detect_work_state(package_id) == pu.WORK_STATE_FRESH

    def test_substantive_execution_contract_marks_execution_ready(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pu, "TEAM_ARTIFACTS", tmp_path / "team_artifacts")

        package_id = "epoch-router-proof"
        pkg_dir = pu.TEAM_ARTIFACTS / package_id
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "execution_contract.md").write_text(
            "Delivered: recovery ladder",
            encoding="utf-8",
        )

        assert pu.detect_work_state(package_id) == pu.WORK_STATE_EXECUTION_READY


# ---------------------------------------------------------------------------
# String helpers
# ---------------------------------------------------------------------------

class TestStringHelpers:
    def test_strip_cell(self):
        assert pu.strip_cell("  `epoch-foo`  ") == "epoch-foo"
        assert pu.strip_cell(" hello ") == "hello"

    def test_clean(self):
        assert pu.clean("`value`") == "value"

    def test_clean_inline_removes_backtick_markup(self):
        assert pu.clean_inline("`infra` — description") == "infra — description"
        assert pu.clean_inline("`#5` — CJM stage") == "#5 — CJM stage"

    def test_clean_inline_multiple(self):
        assert pu.clean_inline("`foo` and `bar`") == "foo and bar"


class TestClassifyPackageComplexity:
    def test_override_wins(self):
        result = pu.classify_package_complexity({"COMPLEXITY": "high"})
        assert result["label"] == "high"
        assert result["route"] == "orchestration"

    def test_medium_override_routes_to_orchestration(self):
        result = pu.classify_package_complexity({"COMPLEXITY": "medium"})
        assert result["label"] == "medium"
        assert result["route"] == "orchestration"

    def test_low_override_routes_to_execution_auto(self):
        result = pu.classify_package_complexity({"COMPLEXITY": "low"})
        assert result["label"] == "low"
        assert result["route"] == "execution_auto"

    def test_compact_contract_routes_to_execution_auto(self):
        contract = {
            "WRITE_SET_MAX": "- app/foo.py\n- tests/test_foo.py",
            "USER_STORIES": "US-1.1",
            "OUTCOMES": "- learner sees foo\n- foo persists",
            "DOD_COMMANDS": "pytest tests/test_foo.py -v",
        }
        result = pu.classify_package_complexity(contract)
        assert result["label"] == "low"
        assert result["route"] == "execution_auto"

    def test_broad_contract_routes_to_orchestration(self):
        contract = {
            "WRITE_SET_MAX": "- app/a.py\n- app/b.py\n- app/c.py\n- tests/test_a.py\n- tests/test_b.py",
            "USER_STORIES": "US-1.1, US-1.2",
            "OUTCOMES": "- one\n- two\n- three\n- four",
            "READ_SET_HINT": "- app/a.py\n- app/b.py\n- app/c.py\n- tests/test_a.py\n- tests/test_b.py",
            "DOD_COMMANDS": "pytest tests/test_a.py -v; pytest tests/test_b.py -v; python scripts/check.py",
        }
        result = pu.classify_package_complexity(contract)
        assert result["label"] == "high"
        assert result["route"] == "orchestration"

    # --- breakthrough model invariants ---

    def test_returns_drivers_and_confidence(self):
        """New continuous model exposes per-signal drivers and margin-based confidence."""
        contract = {
            "WRITE_SET_MAX": "- app/a.py\n- app/b.py",
            "USER_STORIES": "US-1.1",
            "OUTCOMES": "- one\n- two",
            "DOD_COMMANDS": "pytest tests/test_a.py -v",
        }
        result = pu.classify_package_complexity(contract)
        assert "drivers" in result
        assert isinstance(result["drivers"], list)
        assert "confidence" in result
        assert result["confidence"] in {"low", "medium", "high"}
        assert "computed_label" in result
        # Score is now a float, not an int
        assert isinstance(result["score"], float)

    def test_override_preserves_computed_audit_trail(self):
        """Operator override must not erase the heuristic label and score.

        This is what allows later calibration of the heuristic against
        operator judgement.
        """
        contract = {
            "COMPLEXITY": "high",
            "WRITE_SET_MAX": "- app/foo.py",
            "DOD_COMMANDS": "pytest foo.py",
        }
        result = pu.classify_package_complexity(contract)
        assert result["label"] == "high"          # override wins routing
        assert result["computed_label"] == "low"  # heuristic still computed
        assert result["confidence"] == "override"
        # Score must reflect the heuristic, not be zero'd out
        assert isinstance(result["score"], float)

    def test_log_scale_separates_large_from_huge(self):
        """A package touching 20 files must score higher than one with 5."""
        def _score(n: int) -> float:
            write_set = "\n".join(f"- app/f{i}.py" for i in range(n))
            return pu.classify_package_complexity(
                {"WRITE_SET_MAX": write_set}
            )["score"]
        assert _score(20) > _score(5) > _score(2)

    def test_dir_entropy_penalises_scattered_writes(self):
        """5 files all in app/ score lower than 5 files across 5 subsystems."""
        concentrated = {
            "WRITE_SET_MAX": "- app/a.py\n- app/b.py\n- app/c.py\n- app/d.py\n- app/e.py",
        }
        scattered = {
            "WRITE_SET_MAX": "- app/a.py\n- tests/b.py\n- doc/c.md\n- scripts/d.py\n- archive/e.md",
        }
        s1 = pu.classify_package_complexity(concentrated)["score"]
        s2 = pu.classify_package_complexity(scattered)["score"]
        assert s2 > s1

    def test_hot_path_raises_complexity(self):
        """Writing to schema/migration/auth paths must raise the score."""
        benign = {"WRITE_SET_MAX": "- app/widget.py\n- tests/test_widget.py"}
        hot    = {"WRITE_SET_MAX": "- app/schema.py\n- migrations/0001.py"}
        s_benign = pu.classify_package_complexity(benign)["score"]
        s_hot    = pu.classify_package_complexity(hot)["score"]
        assert s_hot > s_benign

    def test_risk_keywords_detected(self):
        """Risk language in outcomes must contribute to the score."""
        safe = {
            "WRITE_SET_MAX": "- app/a.py",
            "OUTCOMES": "- user sees new widget",
        }
        risky = {
            "WRITE_SET_MAX": "- app/a.py",
            "OUTCOMES": "- breaking schema change requires rollback plan",
        }
        assert (
            pu.classify_package_complexity(risky)["score"]
            > pu.classify_package_complexity(safe)["score"]
        )

    def test_dod_chained_operations_atomized(self):
        """`pytest X && mypy && ruff` counts as 3 operations, not 1."""
        chained = {
            "DOD_COMMANDS": "pytest app/ && mypy app/ && ruff check app/",
        }
        result = pu.classify_package_complexity(chained)
        assert result["signals"]["dod_ops"] == 3
        assert result["signals"]["dod_cmds"] == 1

    def test_duplicate_user_stories_dont_inflate_score(self):
        """Same US mentioned twice must count once (regression for extract_us_ids)."""
        dup = {"USER_STORIES": "US-1.1, US-1.1, US-1.1, US-1.1"}
        result = pu.classify_package_complexity(dup)
        assert result["signals"]["user_stories"] == 1

    def test_constraint_density_not_binary(self):
        """Multiple EXEC_CONSTRAINTS must contribute more than a single one."""
        one = {"EXEC_CONSTRAINTS": "Stay in write-set."}
        many = {
            "EXEC_CONSTRAINTS":
                "Stay in write-set.\n"
                "No new routes.\n"
                "No schema changes.\n"
                "No new dependencies.",
        }
        s_one  = pu.classify_package_complexity(one)["score"]
        s_many = pu.classify_package_complexity(many)["score"]
        assert s_many > s_one

    def test_signals_snapshot_includes_new_metrics(self):
        """Signals must expose dir_entropy, hot_paths, risk_keywords, dod_ops."""
        contract = {"WRITE_SET_MAX": "- app/schema.py"}
        signals = pu.classify_package_complexity(contract)["signals"]
        for key in ("dod_ops", "unique_dirs", "dir_entropy",
                    "hot_paths", "risk_keywords"):
            assert key in signals, f"missing signal: {key}"


# ---------------------------------------------------------------------------
# Pipeline metrics parsing
# ---------------------------------------------------------------------------

METRICS_TEXT = """\
# Pipeline Metrics

| Package | Date | sp1_verdict | sp2_verdict | retries | escalations | deferred |
|---------|------|:-----------:|:-----------:|:-------:|:-----------:|:--------:|
| _пример_ | 2026-04-18 | PASS | CPASS | 0 | 0 | 1 |
| epoch-foo | 2026-04-20 | PASS | PASS | 0 | 1 | 0 |
| epoch-bar | 2026-04-20 | CPASS | PASS | 1 | 0 | 1 |
| epoch-baz | 2026-04-21 | TBD | TBD | 0 | 0 | 0 |  ← orchestration started
"""


# ---------------------------------------------------------------------------
# parse_contract — bullet-list format (current tasklist style)
# ---------------------------------------------------------------------------

TASKLIST_BULLET = """\
## Now

| Package | Status |
|---------|--------|
| epoch-adaptive | ready |

### epoch-adaptive Contract

- **Title:** Adaptive Plan feature
- **CJM:** `6 — Adaptive plan`
- **User story:** `US-6.1`
- **Pain point:** learner loses track after session.
- **Outcomes:**
  - Home shows AdaptiveDailyPlan.
  - Plan has review/gap/new blocks.
- **DoD:**
  - `python -m pytest tests/test_adaptive.py -v`
  - `python -m pytest tests/test_service.py -v`
- **DOD_COMMANDS:** `python -m pytest tests/test_adaptive.py tests/test_service.py -v`
- **Write-set max:**
  - `app/adaptive_plan.py`
  - `app/ui/home_hub.py`
- **EXEC_CONSTRAINTS:** Stay in write-set. No new routes.
"""


class TestParseContractBullet:
    def test_package_id_injected(self):
        c = pu.parse_contract(TASKLIST_BULLET, "epoch-adaptive")
        assert c.get("PACKAGE_ID") == "epoch-adaptive"

    def test_title(self):
        c = pu.parse_contract(TASKLIST_BULLET, "epoch-adaptive")
        assert "Adaptive Plan feature" in c.get("PACKAGE_TITLE", "")

    def test_cjm_stage(self):
        c = pu.parse_contract(TASKLIST_BULLET, "epoch-adaptive")
        assert "6" in c.get("CJM_STAGE", "")

    def test_user_stories(self):
        c = pu.parse_contract(TASKLIST_BULLET, "epoch-adaptive")
        assert "US-6.1" in c.get("USER_STORIES", "")

    def test_outcomes_multiline(self):
        c = pu.parse_contract(TASKLIST_BULLET, "epoch-adaptive")
        assert "AdaptiveDailyPlan" in c.get("OUTCOMES", "")
        assert "review" in c.get("OUTCOMES", "")

    def test_exec_constraints(self):
        c = pu.parse_contract(TASKLIST_BULLET, "epoch-adaptive")
        assert "Stay in write-set" in c.get("EXEC_CONSTRAINTS", "")

    def test_missing_contract_returns_empty(self):
        c = pu.parse_contract(TASKLIST_BULLET, "epoch-nonexistent")
        assert c == {}

    def test_table_format_still_works(self):
        """Ensure old table format isn't broken by the new code."""
        c = pu.parse_contract(TASKLIST_SIMPLE, "epoch-foo")
        assert c.get("PACKAGE_ID") == "epoch-foo"
        assert c.get("PACKAGE_TITLE") == "Foo feature"

    def test_backtick_key_format_from_tasklist(self):
        raw = """\
## Now

| Package | Status |
|---------|--------|
| epoch-real | ready |

### epoch-real Contract

- `PACKAGE_TITLE`: Real contract title
- `CJM_STAGE`: `7 - Due`
- `USER_STORIES`: `US-7.1`
- `OUTCOMES`:
  - first outcome
  - second outcome
- `DOD_COMMANDS`:
  - `python -m pytest tests/test_real.py -v`
- `WRITE_SET_MAX`:
  - `app/real.py`
"""
        c = pu.parse_contract(raw, "epoch-real")
        assert c.get("PACKAGE_TITLE") == "Real contract title"
        assert "US-7.1" in c.get("USER_STORIES", "")
        assert "first outcome" in c.get("OUTCOMES", "")
        assert "tests/test_real.py" in c.get("DOD_COMMANDS", "")

    def test_same_level_bullets_under_backtick_key(self):
        raw = """\
## Now

| Package | Status |
|---------|--------|
| epoch-real | ready |

### epoch-real Contract

- `OUTCOMES`:
- first outcome
- second outcome
- `WRITE_SET_MAX`:
- `app/a.py`
- `tests/test_a.py`
"""
        c = pu.parse_contract(raw, "epoch-real")
        assert "first outcome" in c.get("OUTCOMES", "")
        assert "second outcome" in c.get("OUTCOMES", "")
        assert "app/a.py" in c.get("WRITE_SET_MAX", "")


class TestExtractDodCommandsNewline:
    def test_newline_separated(self):
        raw = "python -m pytest foo.py -v\npython -m pytest bar.py -v"
        cmds = pu.extract_dod_commands(raw)
        assert len(cmds) == 2
        assert cmds[0] == "python -m pytest foo.py -v"
        assert cmds[1] == "python -m pytest bar.py -v"

    def test_three_newline_commands(self):
        raw = (
            "python -m pytest tests/test_a.py -v\n"
            "python -m pytest tests/test_b.py -v\n"
            "python scripts/check.py"
        )
        cmds = pu.extract_dod_commands(raw)
        assert len(cmds) == 3

    def test_single_command_no_separator(self):
        raw = "python -m pytest tests/test_foo.py -v"
        cmds = pu.extract_dod_commands(raw)
        assert cmds == ["python -m pytest tests/test_foo.py -v"]

    def test_semicolon_still_works(self):
        raw = "pytest foo.py; pytest bar.py"
        cmds = pu.extract_dod_commands(raw)
        assert len(cmds) == 2

    def test_ignores_non_command_prose_lines(self):
        raw = (
            "python -m pytest tests/test_a.py -v\n"
            "python -m pytest tests/test_b.py -v\n"
            "Home/resume surface shows top-N and overflow"
        )
        cmds = pu.extract_dod_commands(raw)
        assert cmds == [
            "python -m pytest tests/test_a.py -v",
            "python -m pytest tests/test_b.py -v",
        ]

    def test_triple_backtick_block_format(self):
        """Regression: must handle triple-backtick DoD block generated by backlog_registry_lint.

        Lint renders DoD commands as:
          ```
          pytest tests/test_foo.py -v
          python scripts/check.py
          ```
        and this raw string (after parse_contract extraction) must yield clean commands.
        """
        raw = "  ```\n  pytest tests/test_foo.py -v\n  python scripts/check.py\n  ```"
        cmds = pu.extract_dod_commands(raw)
        assert cmds == ["pytest tests/test_foo.py -v", "python scripts/check.py"]

    def test_triple_backtick_via_parse_contract_full_pipeline(self):
        """Full pipeline: lint-rendered contract block → parse_contract → extract_dod_commands."""
        contract_block = textwrap.dedent("""\
            ### epoch-e1-dod Contract

            - **Title:** Some feature
            - **CJM:** #1 Discover
            - **User story:** US-1.1
            - **DoD commands:**
              ```
              pytest tests/test_foo.py -v
              python scripts/check.py
              ```
            - **Outcomes:**
              - Outcome A
        """)
        contract = pu.parse_contract(contract_block, "epoch-e1-dod")
        dod_raw = contract.get("DOD_COMMANDS", "")
        cmds = pu.extract_dod_commands(dod_raw)
        assert "pytest tests/test_foo.py -v" in cmds
        assert "python scripts/check.py" in cmds
        assert len(cmds) == 2


class TestReadPipelineMetrics:
    def test_skips_example_row(self, tmp_path, monkeypatch):
        metrics_path = tmp_path / "pipeline_metrics.md"
        metrics_path.write_text(METRICS_TEXT, encoding="utf-8")
        monkeypatch.setattr(pu, "PIPELINE_METRICS", metrics_path)
        rows = pu.read_pipeline_metrics()
        assert all(r["package"] != "_пример_" for r in rows)

    def test_parses_all_real_rows(self, tmp_path, monkeypatch):
        metrics_path = tmp_path / "pipeline_metrics.md"
        metrics_path.write_text(METRICS_TEXT, encoding="utf-8")
        monkeypatch.setattr(pu, "PIPELINE_METRICS", metrics_path)
        rows = pu.read_pipeline_metrics()
        packages = [r["package"] for r in rows]
        assert "epoch-foo" in packages
        assert "epoch-bar" in packages
        assert "epoch-baz" in packages

    def test_strips_comment_from_deferred(self, tmp_path, monkeypatch):
        metrics_path = tmp_path / "pipeline_metrics.md"
        metrics_path.write_text(METRICS_TEXT, encoding="utf-8")
        monkeypatch.setattr(pu, "PIPELINE_METRICS", metrics_path)
        rows = pu.read_pipeline_metrics()
        baz = next(r for r in rows if r["package"] == "epoch-baz")
        assert "orchestration" not in baz["deferred"]

    def test_returns_empty_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pu, "PIPELINE_METRICS", tmp_path / "nonexistent.md")
        assert pu.read_pipeline_metrics() == []


# ---------------------------------------------------------------------------
# append_pipeline_metrics — deduplication
# ---------------------------------------------------------------------------

class TestAppendPipelineMetrics:
    def test_creates_file_if_missing(self, tmp_path, monkeypatch):
        p = tmp_path / "metrics.md"
        monkeypatch.setattr(pu, "PIPELINE_METRICS", p)
        pu.append_pipeline_metrics("epoch-test", "2026-04-21", "test note")
        assert p.exists()
        assert "epoch-test" in p.read_text(encoding="utf-8")

    def test_no_duplicate_on_second_call(self, tmp_path, monkeypatch):
        p = tmp_path / "metrics.md"
        monkeypatch.setattr(pu, "PIPELINE_METRICS", p)
        pu.append_pipeline_metrics("epoch-dup", "2026-04-21")
        pu.append_pipeline_metrics("epoch-dup", "2026-04-21")  # second call
        text = p.read_text(encoding="utf-8")
        # Count data rows (not header rows)
        data_rows = [l for l in text.splitlines()
                     if l.startswith("| epoch-dup |")]
        assert len(data_rows) == 1

    def test_different_packages_both_written(self, tmp_path, monkeypatch):
        p = tmp_path / "metrics.md"
        monkeypatch.setattr(pu, "PIPELINE_METRICS", p)
        pu.append_pipeline_metrics("epoch-a", "2026-04-21")
        pu.append_pipeline_metrics("epoch-b", "2026-04-21")
        text = p.read_text(encoding="utf-8")
        assert "epoch-a" in text
        assert "epoch-b" in text


# ---------------------------------------------------------------------------
# write_task_file_for_cursor — chat message size guard
# ---------------------------------------------------------------------------

class TestWriteTaskFileForCursor:
    def test_budget_profile_defaults_to_strict(self):
        strict = pu.get_budget_profile()
        relaxed = pu.get_budget_profile("relaxed")
        assert strict["name"] == "strict"
        assert strict["inject_chars"] == pu.MAX_INJECT_CHARS
        assert strict["cursor_task_char_limit"] == pu.CURSOR_TASK_CHAR_LIMIT
        assert strict["cursor_task_line_limit"] == 250
        assert relaxed["inject_chars"] > strict["inject_chars"]
        assert relaxed["cursor_task_char_limit"] > strict["cursor_task_char_limit"]

    def test_inline_when_under_limit(self, tmp_path, monkeypatch):
        task = tmp_path / "current_task.md"
        payload = tmp_path / "current_task.payload.md"
        banner = "> x\n\n"
        body = "task\n"
        foot = "---\nfooter\n"
        used = pu.write_task_file_for_cursor(
            no_pause_banner=banner,
            body=body,
            footer=foot,
            task_path=task,
            payload_path=payload,
            char_limit=pu.CURSOR_TASK_CHAR_LIMIT,
        )
        assert used is False
        assert task.read_text(encoding="utf-8") == banner + body + foot
        assert not payload.exists()

    def test_spills_payload_when_over_limit(self, tmp_path):
        task = tmp_path / "current_task.md"
        payload = tmp_path / "current_task.payload.md"
        banner = "B\n"
        body = "## Write-Set\n- scripts/example.py\n\n" + ("x" * 500)
        foot = "## MANDATORY FINAL\n"
        used = pu.write_task_file_for_cursor(
            no_pause_banner=banner,
            body=body,
            footer=foot,
            task_path=task,
            payload_path=payload,
            char_limit=400,
        )
        assert used is True
        assert payload.read_text(encoding="utf-8") == banner + body.rstrip() + "\n"
        text = task.read_text(encoding="utf-8")
        assert "Context Pack" in text
        assert "## Write-Set" in text
        assert "scripts/example.py" in text
        assert foot in text

    def test_force_payload_spills_even_when_under_limit(self, tmp_path):
        task = tmp_path / "current_task.md"
        payload = tmp_path / "current_task.payload.md"
        banner = "> compact\n\n"
        body = "small body\n"
        foot = "## MANDATORY FINAL\n"
        used = pu.write_task_file_for_cursor(
            no_pause_banner=banner,
            body=body,
            footer=foot,
            task_path=task,
            payload_path=payload,
            force_payload=True,
        )
        assert used is True
        assert payload.read_text(encoding="utf-8") == banner + body.rstrip() + "\n"
        text = task.read_text(encoding="utf-8")
        assert "Context Pack" in text
        assert foot in text

    def test_spills_payload_when_over_line_limit(self, tmp_path):
        task = tmp_path / "current_task.md"
        payload = tmp_path / "context_pack.md"
        banner = "> compact\n\n"
        body = "## Write-Set\n- scripts/example.py\n\n## Plan\n" + "\n".join(
            f"- step {idx}" for idx in range(20)
        )
        foot = "## MANDATORY FINAL\n"
        used = pu.write_task_file_for_cursor(
            no_pause_banner=banner,
            body=body,
            footer=foot,
            task_path=task,
            payload_path=payload,
            char_limit=100_000,
            line_limit=10,
        )

        task_text = task.read_text(encoding="utf-8")
        assert used is True
        assert payload.exists()
        assert len(task_text.splitlines()) <= 10
        assert "context_pack.md" in task_text
        assert "## Write-Set" in task_text
        assert "scripts/example.py" in task_text
        assert "- step 19" not in task_text

    def test_default_spill_writes_context_pack_file(self, tmp_path, monkeypatch):
        root = tmp_path
        monkeypatch.setattr(pu, "ROOT", root)
        (root / "doc").mkdir()
        task = root / "doc" / "current_task.md"
        used = pu.write_task_file_for_cursor(
            no_pause_banner="B\n",
            body="## Write-Set\n- scripts/example.py\n\nbody\n",
            footer="## MANDATORY FINAL\n",
            task_path=task,
            char_limit=10,
        )

        assert used is True
        assert (root / "doc" / "context_pack.md").exists()
        assert "## Write-Set" in task.read_text(encoding="utf-8")

    def test_relaxed_profile_uses_larger_default_limit(self, tmp_path):
        task = tmp_path / "current_task.md"
        payload = tmp_path / "current_task.payload.md"
        banner = "B\n"
        foot = "## MANDATORY FINAL\n"
        body = "x" * 95_000
        used = pu.write_task_file_for_cursor(
            no_pause_banner=banner,
            body=body,
            footer=foot,
            task_path=task,
            payload_path=payload,
            budget_profile="relaxed",
        )
        assert used is False
        assert task.read_text(encoding="utf-8") == banner + body.rstrip() + "\n" + foot
        assert not payload.exists()


def test_all_canonical_agent_adapters_resolve_under_guides() -> None:
    adapters = pu.agent_adapters_map()
    assert set(adapters) == set(pu.AGENT_ADAPTER_FILES)
    for agent_id, path in adapters.items():
        assert path.is_file(), f"{agent_id}: {path}"
        assert path.parent.name == "guides", f"{agent_id} should live under guides/: {path}"
