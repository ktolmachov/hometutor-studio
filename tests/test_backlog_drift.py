"""Tests for scripts/check_backlog_drift.py — all 6 invariants."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "check_backlog_drift.py"


@pytest.fixture(scope="module")
def drift_module():
    spec = importlib.util.spec_from_file_location("check_backlog_drift", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_registry(items: list[dict], waves: list[dict] | None = None, schema_version: int = 1) -> str:
    lines = [f"schema_version: {schema_version}", "user_stories_index: doc/user_stories_index.json", ""]
    if waves is not None:
        lines.append("waves:")
        for w in waves:
            pkg_list = "\n".join(f"      - {p}" for p in w.get("packages", []))
            lines.append(f"  - id: {w['id']}")
            lines.append(f"    status: {w.get('status', 'proposed')}")
            if w.get("packages"):
                lines.append("    packages:")
                for p in w["packages"]:
                    lines.append(f"      - {p}")
        lines.append("")
    lines.append("items:")
    for item in items:
        lines.append(f"  - id: {item['id']}")
        lines.append(f"    status: {item['status']}")
        lines.append(f"    impact: loop-improvement")
        lines.append(f"    created: {item.get('created', '2026-04-01')}")
        lines.append(f"    last_review: {item.get('last_review', '2026-04-01')}")
        us_list = item.get("user_stories", [])
        if us_list:
            lines.append(f"    user_stories: [{', '.join(repr(u) for u in us_list)}]")
        else:
            lines.append("    user_stories: []")
        if item.get("wave_id"):
            lines.append(f"    wave_id: {item['wave_id']}")
            lines.append(f"    wave_position: {item.get('wave_position', 1)}")
        if item.get("re_entry_condition"):
            lines.append(f'    re_entry_condition: "{item["re_entry_condition"]}"')
    return "\n".join(lines) + "\n"


def _make_us_index(items: list[dict], candidates: list[dict] | None = None) -> str:
    if candidates is None:
        # auto-compute
        open_items = [it for it in items if it.get("status") == "open"]
        candidates = [
            {"rank": i + 1, "us_id": it["us_id"], "title": it.get("title", ""), "priority": it.get("priority", "P1"),
             "cjm_stage": it.get("cjm_stage", "2"), "status": "open", "coverage": "open", "pain_point": None}
            for i, it in enumerate(open_items[:8])
        ]
    return json.dumps({"version": 1, "generated": "2026-04-22", "items": items, "open_candidates": candidates}, ensure_ascii=False, indent=2)


def _make_cjm_pain_table(rows: list[dict]) -> str:
    """Returns a minimal cjm.md with § 8 section."""
    table_lines = [
        "| Pain point | US | package_status |",
        "|---|---|---|",
    ]
    for r in rows:
        table_lines.append(f"| {r['pain']} | `{r['us_id']}` | `{r['pkg_status']}` |")
    table = "\n".join(table_lines)
    return f"""# CJM

## 7. Something

---

## 8. CJM pain table для planning automation (`infra`)

<!-- GENERATED: user_stories_index.items + pain map (do not edit manually) -->

{table}

---

## 9. Other
"""


def _make_tasklist_with_closed(closed_ids: list[str]) -> str:
    refs = "\n".join(f"- `{pkg}` закрыт 2026-04-22; перенесено в `doc/closed_iterations.md`." for pkg in closed_ids)
    return f"""# План работ

## Now

### Truth View

| Package | Status | CJM | Primary US | Owner | Notes |
|---|---|---|---|---|---|

### Recent closed references
{refs}
"""


def _make_closed_iterations_with_closed(closed_ids: list[str]) -> str:
    blocks = []
    for pkg in closed_ids:
        blocks.append(
            f"### {pkg} — 2026-04-22\n\n"
            f"- **Roadmap closure:** `{pkg}` moved to closed.\n"
        )
    return "\n".join(blocks) if blocks else "# Closed iterations\n"


# ---------------------------------------------------------------------------
# INV1 tests
# ---------------------------------------------------------------------------

class TestInv1:
    def test_pass_closed_us_has_closed_package(self, drift_module, tmp_path, monkeypatch):
        monkeypatch.setattr(drift_module, "BACKLOG_REGISTRY", tmp_path / "backlog_registry.yaml")
        monkeypatch.setattr(drift_module, "US_INDEX", tmp_path / "us_index.json")
        monkeypatch.setattr(drift_module, "TASKLIST", tmp_path / "tasklist.md")
        monkeypatch.setattr(drift_module, "CJM_MD", tmp_path / "cjm.md")

        registry = _make_registry([{"id": "epoch-foo", "status": "closed", "user_stories": ["US-1.1"]}])
        index = _make_us_index([{"us_id": "US-1.1", "status": "closed", "covered_by": "epoch-foo", "priority": "P0", "cjm_stage": "1", "title": "T"}])

        _write(tmp_path / "backlog_registry.yaml", registry)
        _write(tmp_path / "us_index.json", index)
        _write(tmp_path / "tasklist.md", _make_tasklist_with_closed([]))
        _write(tmp_path / "cjm.md", _make_cjm_pain_table([]))

        violations, _ = drift_module.run_checks()
        inv1 = [v for v in violations if v[0] == "INV1"]
        assert inv1 == []

    def test_fail_closed_us_no_package_in_registry(self, drift_module, tmp_path, monkeypatch):
        monkeypatch.setattr(drift_module, "BACKLOG_REGISTRY", tmp_path / "backlog_registry.yaml")
        monkeypatch.setattr(drift_module, "US_INDEX", tmp_path / "us_index.json")
        monkeypatch.setattr(drift_module, "TASKLIST", tmp_path / "tasklist.md")
        monkeypatch.setattr(drift_module, "CJM_MD", tmp_path / "cjm.md")

        registry = _make_registry([])  # empty items
        index = _make_us_index([{"us_id": "US-1.1", "status": "closed", "covered_by": "epoch-missing", "priority": "P0", "cjm_stage": "1", "title": "T"}])

        _write(tmp_path / "backlog_registry.yaml", registry)
        _write(tmp_path / "us_index.json", index)
        _write(tmp_path / "tasklist.md", _make_tasklist_with_closed([]))
        _write(tmp_path / "cjm.md", _make_cjm_pain_table([]))

        violations, _ = drift_module.run_checks()
        inv1 = [v for v in violations if v[0] == "INV1"]
        assert len(inv1) == 1
        assert "US-1.1" in inv1[0][1]

    def test_pass_legacy_covered_by_unknown_closed(self, drift_module, tmp_path, monkeypatch):
        """Legacy IDs like 'unknown-closed' or 'E10.4-A' should not trigger INV1."""
        monkeypatch.setattr(drift_module, "BACKLOG_REGISTRY", tmp_path / "backlog_registry.yaml")
        monkeypatch.setattr(drift_module, "US_INDEX", tmp_path / "us_index.json")
        monkeypatch.setattr(drift_module, "TASKLIST", tmp_path / "tasklist.md")
        monkeypatch.setattr(drift_module, "CJM_MD", tmp_path / "cjm.md")

        registry = _make_registry([])
        index = _make_us_index([
            {"us_id": "US-3.1", "status": "closed", "covered_by": "unknown-closed", "priority": "P0", "cjm_stage": "2", "title": "T"},
            {"us_id": "US-3.4", "status": "closed", "covered_by": "E10.4-A", "priority": "P0", "cjm_stage": "2", "title": "T"},
        ])

        _write(tmp_path / "backlog_registry.yaml", registry)
        _write(tmp_path / "us_index.json", index)
        _write(tmp_path / "tasklist.md", _make_tasklist_with_closed([]))
        _write(tmp_path / "cjm.md", _make_cjm_pain_table([]))

        violations, _ = drift_module.run_checks()
        inv1 = [v for v in violations if v[0] == "INV1"]
        assert inv1 == []


# ---------------------------------------------------------------------------
# INV2 tests
# ---------------------------------------------------------------------------

class TestInv2:
    def test_fail_open_candidates_contains_closed_us(self, drift_module, tmp_path, monkeypatch):
        monkeypatch.setattr(drift_module, "BACKLOG_REGISTRY", tmp_path / "backlog_registry.yaml")
        monkeypatch.setattr(drift_module, "US_INDEX", tmp_path / "us_index.json")
        monkeypatch.setattr(drift_module, "TASKLIST", tmp_path / "tasklist.md")
        monkeypatch.setattr(drift_module, "CJM_MD", tmp_path / "cjm.md")

        registry = _make_registry([{"id": "epoch-foo", "status": "closed", "user_stories": ["US-2.1"]}])
        # US-2.1 is closed in items, but still appears in open_candidates (drift)
        stale_candidates = [{"rank": 1, "us_id": "US-2.1", "title": "T", "priority": "P0",
                              "cjm_stage": "1", "status": "open", "coverage": "open", "pain_point": None}]
        index = _make_us_index(
            [{"us_id": "US-2.1", "status": "closed", "covered_by": "epoch-foo", "priority": "P0", "cjm_stage": "1", "title": "T"}],
            candidates=stale_candidates,
        )

        _write(tmp_path / "backlog_registry.yaml", registry)
        _write(tmp_path / "us_index.json", index)
        _write(tmp_path / "tasklist.md", _make_tasklist_with_closed([]))
        _write(tmp_path / "cjm.md", _make_cjm_pain_table([]))

        violations, _ = drift_module.run_checks()
        inv2 = [v for v in violations if v[0] == "INV2"]
        assert len(inv2) == 1
        assert "US-2.1" in inv2[0][1]

    def test_pass_open_candidates_only_open_us(self, drift_module, tmp_path, monkeypatch):
        monkeypatch.setattr(drift_module, "BACKLOG_REGISTRY", tmp_path / "backlog_registry.yaml")
        monkeypatch.setattr(drift_module, "US_INDEX", tmp_path / "us_index.json")
        monkeypatch.setattr(drift_module, "TASKLIST", tmp_path / "tasklist.md")
        monkeypatch.setattr(drift_module, "CJM_MD", tmp_path / "cjm.md")

        registry = _make_registry([])
        index = _make_us_index([
            {"us_id": "US-3.2", "status": "open", "covered_by": None, "priority": "P1", "cjm_stage": "2", "title": "T"},
        ])

        _write(tmp_path / "backlog_registry.yaml", registry)
        _write(tmp_path / "us_index.json", index)
        _write(tmp_path / "tasklist.md", _make_tasklist_with_closed([]))
        _write(tmp_path / "cjm.md", _make_cjm_pain_table([]))

        violations, _ = drift_module.run_checks()
        inv2 = [v for v in violations if v[0] == "INV2"]
        assert inv2 == []


# ---------------------------------------------------------------------------
# INV3 tests
# ---------------------------------------------------------------------------

class TestInv3:
    def test_fail_cjm_table_shows_open_for_closed_us(self, drift_module, tmp_path, monkeypatch):
        monkeypatch.setattr(drift_module, "BACKLOG_REGISTRY", tmp_path / "backlog_registry.yaml")
        monkeypatch.setattr(drift_module, "US_INDEX", tmp_path / "us_index.json")
        monkeypatch.setattr(drift_module, "TASKLIST", tmp_path / "tasklist.md")
        monkeypatch.setattr(drift_module, "CJM_MD", tmp_path / "cjm.md")

        registry = _make_registry([{"id": "epoch-foo", "status": "closed", "user_stories": ["US-4.2"]}])
        index = _make_us_index([{"us_id": "US-4.2", "status": "closed", "covered_by": "epoch-foo", "priority": "P1", "cjm_stage": "3", "title": "T"}])
        # cjm table still shows "open" for US-4.2 (stale)
        cjm = _make_cjm_pain_table([{"pain": "Learner не понимает тьютора", "us_id": "US-4.2", "pkg_status": "open"}])

        _write(tmp_path / "backlog_registry.yaml", registry)
        _write(tmp_path / "us_index.json", index)
        _write(tmp_path / "tasklist.md", _make_tasklist_with_closed([]))
        _write(tmp_path / "cjm.md", cjm)

        violations, _ = drift_module.run_checks()
        inv3 = [v for v in violations if v[0] == "INV3"]
        assert len(inv3) >= 1
        assert "US-4.2" in inv3[0][1]

    def test_pass_cjm_table_matches_closed_status(self, drift_module, tmp_path, monkeypatch):
        monkeypatch.setattr(drift_module, "BACKLOG_REGISTRY", tmp_path / "backlog_registry.yaml")
        monkeypatch.setattr(drift_module, "US_INDEX", tmp_path / "us_index.json")
        monkeypatch.setattr(drift_module, "TASKLIST", tmp_path / "tasklist.md")
        monkeypatch.setattr(drift_module, "CJM_MD", tmp_path / "cjm.md")

        registry = _make_registry([{"id": "epoch-foo", "status": "closed", "user_stories": ["US-4.2"]}])
        index = _make_us_index([{"us_id": "US-4.2", "status": "closed", "covered_by": "epoch-foo", "priority": "P1", "cjm_stage": "3", "title": "T"}])
        cjm = _make_cjm_pain_table([{"pain": "Learner не понимает тьютора", "us_id": "US-4.2", "pkg_status": "closed:epoch-foo"}])

        _write(tmp_path / "backlog_registry.yaml", registry)
        _write(tmp_path / "us_index.json", index)
        _write(tmp_path / "tasklist.md", _make_tasklist_with_closed([]))
        _write(tmp_path / "cjm.md", cjm)

        violations, _ = drift_module.run_checks()
        inv3 = [v for v in violations if v[0] == "INV3"]
        assert inv3 == []


# ---------------------------------------------------------------------------
# INV4 tests
# ---------------------------------------------------------------------------

class TestInv4:
    def test_fail_tasklist_closed_not_in_registry(self, drift_module, tmp_path, monkeypatch):
        monkeypatch.setattr(drift_module, "BACKLOG_REGISTRY", tmp_path / "backlog_registry.yaml")
        monkeypatch.setattr(drift_module, "US_INDEX", tmp_path / "us_index.json")
        monkeypatch.setattr(drift_module, "TASKLIST", tmp_path / "tasklist.md")
        monkeypatch.setattr(drift_module, "CJM_MD", tmp_path / "cjm.md")

        registry = _make_registry([])  # registry empty
        index = _make_us_index([])
        tasklist = _make_tasklist_with_closed(["epoch-missing"])
        closed_iterations = _make_closed_iterations_with_closed(["epoch-missing"])

        _write(tmp_path / "backlog_registry.yaml", registry)
        _write(tmp_path / "us_index.json", index)
        _write(tmp_path / "tasklist.md", tasklist)
        _write(tmp_path / "closed_iterations.md", closed_iterations)
        _write(tmp_path / "cjm.md", _make_cjm_pain_table([]))

        violations, _ = drift_module.run_checks()
        inv4 = [v for v in violations if v[0] == "INV4"]
        assert len(inv4) == 1
        assert "epoch-missing" in inv4[0][1]

    def test_pass_tasklist_closed_in_registry(self, drift_module, tmp_path, monkeypatch):
        monkeypatch.setattr(drift_module, "BACKLOG_REGISTRY", tmp_path / "backlog_registry.yaml")
        monkeypatch.setattr(drift_module, "US_INDEX", tmp_path / "us_index.json")
        monkeypatch.setattr(drift_module, "TASKLIST", tmp_path / "tasklist.md")
        monkeypatch.setattr(drift_module, "CJM_MD", tmp_path / "cjm.md")

        registry = _make_registry([{"id": "epoch-foo", "status": "closed", "user_stories": []}])
        index = _make_us_index([])
        tasklist = _make_tasklist_with_closed(["epoch-foo"])
        closed_iterations = _make_closed_iterations_with_closed(["epoch-foo"])

        _write(tmp_path / "backlog_registry.yaml", registry)
        _write(tmp_path / "us_index.json", index)
        _write(tmp_path / "tasklist.md", tasklist)
        _write(tmp_path / "closed_iterations.md", closed_iterations)
        _write(tmp_path / "cjm.md", _make_cjm_pain_table([]))

        violations, _ = drift_module.run_checks()
        inv4 = [v for v in violations if v[0] == "INV4"]
        assert inv4 == []


# ---------------------------------------------------------------------------
# INV5+INV6 tests (schema_version >= 2)
# ---------------------------------------------------------------------------

class TestInv5Inv6:
    def test_skip_when_schema_v1(self, drift_module, tmp_path, monkeypatch):
        monkeypatch.setattr(drift_module, "BACKLOG_REGISTRY", tmp_path / "backlog_registry.yaml")
        monkeypatch.setattr(drift_module, "US_INDEX", tmp_path / "us_index.json")
        monkeypatch.setattr(drift_module, "TASKLIST", tmp_path / "tasklist.md")
        monkeypatch.setattr(drift_module, "CJM_MD", tmp_path / "cjm.md")

        # schema_version 1: wave checks are skipped
        registry = _make_registry([{"id": "epoch-foo", "status": "closed", "user_stories": []}], schema_version=1)
        _write(tmp_path / "backlog_registry.yaml", registry)
        _write(tmp_path / "us_index.json", _make_us_index([]))
        _write(tmp_path / "tasklist.md", _make_tasklist_with_closed(["epoch-foo"]))
        _write(tmp_path / "cjm.md", _make_cjm_pain_table([]))

        violations, _ = drift_module.run_checks()
        wave_violations = [v for v in violations if v[0] in ("INV5", "INV6")]
        assert wave_violations == []

    def test_fail_inv5_unknown_wave_id(self, drift_module, tmp_path, monkeypatch):
        monkeypatch.setattr(drift_module, "BACKLOG_REGISTRY", tmp_path / "backlog_registry.yaml")
        monkeypatch.setattr(drift_module, "US_INDEX", tmp_path / "us_index.json")
        monkeypatch.setattr(drift_module, "TASKLIST", tmp_path / "tasklist.md")
        monkeypatch.setattr(drift_module, "CJM_MD", tmp_path / "cjm.md")

        waves = [{"id": "wave-alpha", "status": "proposed", "packages": ["epoch-foo"]}]
        items = [{"id": "epoch-foo", "status": "proposed", "user_stories": [],
                  "wave_id": "wave-NONEXISTENT", "wave_position": 1}]
        registry = _make_registry(items, waves=waves, schema_version=2)

        _write(tmp_path / "backlog_registry.yaml", registry)
        _write(tmp_path / "us_index.json", _make_us_index([]))
        _write(tmp_path / "tasklist.md", _make_tasklist_with_closed([]))
        _write(tmp_path / "cjm.md", _make_cjm_pain_table([]))

        violations, _ = drift_module.run_checks()
        inv5 = [v for v in violations if v[0] == "INV5"]
        assert len(inv5) >= 1

    def test_fail_inv6_wave_package_not_backlinked(self, drift_module, tmp_path, monkeypatch):
        monkeypatch.setattr(drift_module, "BACKLOG_REGISTRY", tmp_path / "backlog_registry.yaml")
        monkeypatch.setattr(drift_module, "US_INDEX", tmp_path / "us_index.json")
        monkeypatch.setattr(drift_module, "TASKLIST", tmp_path / "tasklist.md")
        monkeypatch.setattr(drift_module, "CJM_MD", tmp_path / "cjm.md")

        waves = [{"id": "wave-alpha", "status": "proposed", "packages": ["epoch-foo"]}]
        # epoch-foo has wrong wave_id back-link
        items = [{"id": "epoch-foo", "status": "proposed", "user_stories": [],
                  "wave_id": "wave-beta", "wave_position": 1}]
        registry = _make_registry(items, waves=waves, schema_version=2)

        _write(tmp_path / "backlog_registry.yaml", registry)
        _write(tmp_path / "us_index.json", _make_us_index([]))
        _write(tmp_path / "tasklist.md", _make_tasklist_with_closed([]))
        _write(tmp_path / "cjm.md", _make_cjm_pain_table([]))

        violations, _ = drift_module.run_checks()
        inv6 = [v for v in violations if v[0] == "INV6"]
        assert len(inv6) >= 1

    def test_pass_wave_cross_refs_correct(self, drift_module, tmp_path, monkeypatch):
        monkeypatch.setattr(drift_module, "BACKLOG_REGISTRY", tmp_path / "backlog_registry.yaml")
        monkeypatch.setattr(drift_module, "US_INDEX", tmp_path / "us_index.json")
        monkeypatch.setattr(drift_module, "TASKLIST", tmp_path / "tasklist.md")
        monkeypatch.setattr(drift_module, "CJM_MD", tmp_path / "cjm.md")

        waves = [{"id": "wave-alpha", "status": "proposed", "packages": ["epoch-pkg1", "epoch-pkg2"]}]
        items = [
            {"id": "epoch-pkg1", "status": "proposed", "user_stories": [], "wave_id": "wave-alpha", "wave_position": 1},
            {"id": "epoch-pkg2", "status": "proposed", "user_stories": [], "wave_id": "wave-alpha", "wave_position": 2},
        ]
        registry = _make_registry(items, waves=waves, schema_version=2)

        _write(tmp_path / "backlog_registry.yaml", registry)
        _write(tmp_path / "us_index.json", _make_us_index([]))
        _write(tmp_path / "tasklist.md", _make_tasklist_with_closed([]))
        _write(tmp_path / "cjm.md", _make_cjm_pain_table([]))

        violations, _ = drift_module.run_checks()
        wave_violations = [v for v in violations if v[0] in ("INV5", "INV6")]
        assert wave_violations == []


# ---------------------------------------------------------------------------
# Integration: full clean state (no violations)
# ---------------------------------------------------------------------------

class TestFullCleanState:
    def test_no_violations_when_all_in_sync(self, drift_module, tmp_path, monkeypatch):
        monkeypatch.setattr(drift_module, "BACKLOG_REGISTRY", tmp_path / "backlog_registry.yaml")
        monkeypatch.setattr(drift_module, "US_INDEX", tmp_path / "us_index.json")
        monkeypatch.setattr(drift_module, "TASKLIST", tmp_path / "tasklist.md")
        monkeypatch.setattr(drift_module, "CJM_MD", tmp_path / "cjm.md")

        registry = _make_registry([
            {"id": "epoch-foo", "status": "closed", "user_stories": ["US-4.2"]},
        ])
        index = _make_us_index([
            {"us_id": "US-4.2", "status": "closed", "covered_by": "epoch-foo", "priority": "P1", "cjm_stage": "3", "title": "T"},
            {"us_id": "US-3.2", "status": "open", "covered_by": None, "priority": "P1", "cjm_stage": "2", "title": "T2"},
        ])
        cjm = _make_cjm_pain_table([
            {"pain": "Learner не понимает тьютора", "us_id": "US-4.2", "pkg_status": "closed:epoch-foo"},
        ])
        tasklist = _make_tasklist_with_closed(["epoch-foo"])
        closed_iterations = _make_closed_iterations_with_closed(["epoch-foo"])

        _write(tmp_path / "backlog_registry.yaml", registry)
        _write(tmp_path / "us_index.json", index)
        _write(tmp_path / "tasklist.md", tasklist)
        _write(tmp_path / "closed_iterations.md", closed_iterations)
        _write(tmp_path / "cjm.md", cjm)

        violations, _ = drift_module.run_checks()
        assert violations == []


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

class TestMain:
    def test_main_exit_0_clean(self, drift_module, tmp_path, monkeypatch):
        monkeypatch.setattr(drift_module, "BACKLOG_REGISTRY", tmp_path / "backlog_registry.yaml")
        monkeypatch.setattr(drift_module, "US_INDEX", tmp_path / "us_index.json")
        monkeypatch.setattr(drift_module, "TASKLIST", tmp_path / "tasklist.md")
        monkeypatch.setattr(drift_module, "CJM_MD", tmp_path / "cjm.md")

        _write(tmp_path / "backlog_registry.yaml", _make_registry([]))
        _write(tmp_path / "us_index.json", _make_us_index([]))
        _write(tmp_path / "tasklist.md", _make_tasklist_with_closed([]))
        _write(tmp_path / "cjm.md", _make_cjm_pain_table([]))

        rc = drift_module.main(argv=[])
        assert rc == 0

    def test_main_exit_2_with_violations(self, drift_module, tmp_path, monkeypatch):
        monkeypatch.setattr(drift_module, "BACKLOG_REGISTRY", tmp_path / "backlog_registry.yaml")
        monkeypatch.setattr(drift_module, "US_INDEX", tmp_path / "us_index.json")
        monkeypatch.setattr(drift_module, "TASKLIST", tmp_path / "tasklist.md")
        monkeypatch.setattr(drift_module, "CJM_MD", tmp_path / "cjm.md")

        # INV2 violation: open_candidates has a closed US
        stale_candidates = [{"rank": 1, "us_id": "US-2.1", "title": "T", "priority": "P0",
                              "cjm_stage": "1", "status": "open", "coverage": "open", "pain_point": None}]
        index = _make_us_index(
            [{"us_id": "US-2.1", "status": "closed", "covered_by": "epoch-foo", "priority": "P0", "cjm_stage": "1", "title": "T"}],
            candidates=stale_candidates,
        )
        _write(tmp_path / "backlog_registry.yaml", _make_registry([{"id": "epoch-foo", "status": "closed", "user_stories": ["US-2.1"]}]))
        _write(tmp_path / "us_index.json", index)
        _write(tmp_path / "tasklist.md", _make_tasklist_with_closed(["epoch-foo"]))
        _write(tmp_path / "cjm.md", _make_cjm_pain_table([]))

        rc = drift_module.main(argv=[])
        assert rc == 2
