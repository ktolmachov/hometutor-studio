"""Tests for scripts/rebuild_user_stories_index.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "rebuild_user_stories_index.py"


@pytest.fixture(scope="module")
def rebuild_module():
    spec = importlib.util.spec_from_file_location("rebuild_user_stories_index", SCRIPT_PATH)
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


def _make_us_file(us_id: str, priority: str = "P1", status: str = "open",
                  covered_by: str | None = None, closed_date: str | None = None,
                  epic: int = 1, cjm_stage: str = "2") -> str:
    epic_name = f"Epic {epic}: Test"
    covered_by_str = f'"{covered_by}"' if covered_by else "null"
    closed_date_str = f'"{closed_date}"' if closed_date else "null"
    return (
        f"---\n"
        f'us_id: "{us_id}"\n'
        f"epic: {epic}\n"
        f'epic_name: "{epic_name}"\n'
        f'title: "Title for {us_id}"\n'
        f'priority: "{priority}"\n'
        f'cjm_stage: "{cjm_stage}"\n'
        f'cjm_moment_name: "Test moment"\n'
        f'status: "{status}"\n'
        f"covered_by: {covered_by_str}\n"
        f"closed_date: {closed_date_str}\n"
        f"---\n\n# {us_id}\n"
    )


def _make_registry(items: list[dict]) -> str:
    lines = ["schema_version: 1", "user_stories_index: doc/user_stories_index.json", "", "items:"]
    for item in items:
        lines.append(f"  - id: {item['id']}")
        lines.append(f"    status: {item['status']}")
        lines.append("    impact: loop-improvement")
        lines.append(f"    created: {item.get('created', '2026-04-01')}")
        lines.append(f"    last_review: {item.get('last_review', '2026-04-22')}")
        us_list = item.get("user_stories", [])
        if us_list:
            lines.append(f"    user_stories: [{', '.join(repr(u) for u in us_list)}]")
        else:
            lines.append("    user_stories: []")
        if item.get("re_entry_condition"):
            lines.append(f'    re_entry_condition: "{item["re_entry_condition"]}"')
    return "\n".join(lines) + "\n"


def _seed_env(tmp_path: Path, us_files: dict[str, str], registry_text: str,
              existing_index: dict | None = None) -> tuple[Path, Path, Path]:
    us_dir = tmp_path / "doc" / "user_stories"
    us_dir.mkdir(parents=True, exist_ok=True)
    registry_path = tmp_path / "doc" / "backlog_registry.yaml"
    index_path = tmp_path / "doc" / "user_stories_index.json"

    for filename, content in us_files.items():
        _write(us_dir / filename, content)

    _write(registry_path, registry_text)

    if existing_index is not None:
        _write(index_path, json.dumps(existing_index, ensure_ascii=False, indent=2))

    return us_dir, registry_path, index_path


# ---------------------------------------------------------------------------
# Core rebuild logic
# ---------------------------------------------------------------------------

class TestRebuild:
    def test_basic_rebuild_open_us(self, rebuild_module, tmp_path, monkeypatch):
        """Open US stays open when no closed registry package covers it."""
        monkeypatch.setattr(rebuild_module, "BACKLOG_REGISTRY", tmp_path / "doc" / "backlog_registry.yaml")
        monkeypatch.setattr(rebuild_module, "USER_STORIES_DIR", tmp_path / "doc" / "user_stories")
        monkeypatch.setattr(rebuild_module, "US_INDEX", tmp_path / "doc" / "user_stories_index.json")

        us_files = {"us-3.2.md": _make_us_file("US-3.2", priority="P1", status="open")}
        _seed_env(tmp_path, us_files, _make_registry([]))

        new_index, changed = rebuild_module.rebuild(write=False)

        items = {it["us_id"]: it for it in new_index["items"]}
        assert "US-3.2" in items
        assert items["US-3.2"]["status"] == "open"
        assert items["US-3.2"]["covered_by"] == "open"

    def test_registry_truth_overrides_frontmatter_open(self, rebuild_module, tmp_path, monkeypatch):
        """When registry has a closed package covering US-X.Y, status becomes closed even if frontmatter says open."""
        monkeypatch.setattr(rebuild_module, "BACKLOG_REGISTRY", tmp_path / "doc" / "backlog_registry.yaml")
        monkeypatch.setattr(rebuild_module, "USER_STORIES_DIR", tmp_path / "doc" / "user_stories")
        monkeypatch.setattr(rebuild_module, "US_INDEX", tmp_path / "doc" / "user_stories_index.json")

        # Frontmatter says open, registry says closed via epoch-foo
        us_files = {"us-8.1.md": _make_us_file("US-8.1", priority="P0", status="open")}
        registry = _make_registry([{"id": "epoch-foo", "status": "closed", "user_stories": ["US-8.1"]}])
        _seed_env(tmp_path, us_files, registry)

        new_index, changed = rebuild_module.rebuild(write=False)

        items = {it["us_id"]: it for it in new_index["items"]}
        assert items["US-8.1"]["status"] == "closed"
        assert items["US-8.1"]["covered_by"] == "epoch-foo"
        assert changed is True

    def test_idempotent_no_change_on_second_run(self, rebuild_module, tmp_path, monkeypatch):
        """Running rebuild twice with --write produces no further changes."""
        monkeypatch.setattr(rebuild_module, "BACKLOG_REGISTRY", tmp_path / "doc" / "backlog_registry.yaml")
        monkeypatch.setattr(rebuild_module, "USER_STORIES_DIR", tmp_path / "doc" / "user_stories")
        monkeypatch.setattr(rebuild_module, "US_INDEX", tmp_path / "doc" / "user_stories_index.json")

        us_files = {"us-7.2.md": _make_us_file("US-7.2", priority="P1", status="open")}
        registry = _make_registry([])
        _seed_env(tmp_path, us_files, registry)

        # First run: write
        rebuild_module.rebuild(write=True)
        # Second run: should report no change
        _, changed = rebuild_module.rebuild(write=True)
        assert changed is False

    def test_open_candidates_excludes_closed_us(self, rebuild_module, tmp_path, monkeypatch):
        """open_candidates must not contain any US that is closed."""
        monkeypatch.setattr(rebuild_module, "BACKLOG_REGISTRY", tmp_path / "doc" / "backlog_registry.yaml")
        monkeypatch.setattr(rebuild_module, "USER_STORIES_DIR", tmp_path / "doc" / "user_stories")
        monkeypatch.setattr(rebuild_module, "US_INDEX", tmp_path / "doc" / "user_stories_index.json")

        us_files = {
            "us-6.1.md": _make_us_file("US-6.1", priority="P0", status="open"),
            "us-7.1.md": _make_us_file("US-7.1", priority="P0", status="open"),
        }
        registry = _make_registry([
            {"id": "epoch-foo", "status": "closed", "user_stories": ["US-6.1"]},
            {"id": "epoch-bar", "status": "closed", "user_stories": ["US-7.1"]},
        ])
        _seed_env(tmp_path, us_files, registry)

        new_index, _ = rebuild_module.rebuild(write=False)

        candidate_ids = {c["us_id"] for c in new_index["open_candidates"]}
        assert "US-6.1" not in candidate_ids
        assert "US-7.1" not in candidate_ids

    def test_open_candidates_sorted_by_priority(self, rebuild_module, tmp_path, monkeypatch):
        """P0 stories rank before P1, P1 before P2."""
        monkeypatch.setattr(rebuild_module, "BACKLOG_REGISTRY", tmp_path / "doc" / "backlog_registry.yaml")
        monkeypatch.setattr(rebuild_module, "USER_STORIES_DIR", tmp_path / "doc" / "user_stories")
        monkeypatch.setattr(rebuild_module, "US_INDEX", tmp_path / "doc" / "user_stories_index.json")

        us_files = {
            "us-3.3.md": _make_us_file("US-3.3", priority="P2", status="open", cjm_stage="2"),
            "us-2.2.md": _make_us_file("US-2.2", priority="P1", status="open", cjm_stage="2"),
            "us-8.1.md": _make_us_file("US-8.1", priority="P0", status="open", cjm_stage="6"),
        }
        _seed_env(tmp_path, us_files, _make_registry([]))

        new_index, _ = rebuild_module.rebuild(write=False)
        candidates = new_index["open_candidates"]
        assert candidates[0]["us_id"] == "US-8.1"  # P0 first

    def test_write_persists_to_disk(self, rebuild_module, tmp_path, monkeypatch):
        """--write flag writes the file to disk."""
        monkeypatch.setattr(rebuild_module, "BACKLOG_REGISTRY", tmp_path / "doc" / "backlog_registry.yaml")
        monkeypatch.setattr(rebuild_module, "USER_STORIES_DIR", tmp_path / "doc" / "user_stories")
        index_path = tmp_path / "doc" / "user_stories_index.json"
        monkeypatch.setattr(rebuild_module, "US_INDEX", index_path)

        us_files = {"us-3.2.md": _make_us_file("US-3.2", priority="P1", status="open")}
        _seed_env(tmp_path, us_files, _make_registry([]))

        assert not index_path.exists()
        rebuild_module.rebuild(write=True)
        assert index_path.exists()

        data = json.loads(index_path.read_text(encoding="utf-8"))
        assert "items" in data
        assert "open_candidates" in data
        assert any(it["us_id"] == "US-3.2" for it in data["items"])

    def test_preserves_metadata_from_existing_index(self, rebuild_module, tmp_path, monkeypatch):
        """Title, epic_name and other metadata from existing index are preserved."""
        monkeypatch.setattr(rebuild_module, "BACKLOG_REGISTRY", tmp_path / "doc" / "backlog_registry.yaml")
        monkeypatch.setattr(rebuild_module, "USER_STORIES_DIR", tmp_path / "doc" / "user_stories")
        index_path = tmp_path / "doc" / "user_stories_index.json"
        monkeypatch.setattr(rebuild_module, "US_INDEX", index_path)

        existing_index = {
            "version": 1, "generated": "2026-04-01",
            "items": [{"us_id": "US-3.2", "epic": 3, "epic_name": "Epic 3: First Answer",
                       "title": "Видеть, почему фрагмент попал в ответ", "priority": "P1",
                       "cjm_stage": "2", "cjm_moment_name": "First answer", "status": "open",
                       "covered_by": None, "closed_date": None, "path": "doc/user_stories/us-3.2.md"}],
            "open_candidates": []
        }
        us_files = {"us-3.2.md": _make_us_file("US-3.2", priority="P1", status="open")}
        _seed_env(tmp_path, us_files, _make_registry([]), existing_index=existing_index)

        new_index, _ = rebuild_module.rebuild(write=False)

        item = next(it for it in new_index["items"] if it["us_id"] == "US-3.2")
        assert item["title"] == "Видеть, почему фрагмент попал в ответ"
        assert item["epic_name"] == "Epic 3: First Answer"


# ---------------------------------------------------------------------------
# Check mode
# ---------------------------------------------------------------------------

class TestCheckMode:
    def test_check_returns_1_when_stale(self, rebuild_module, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(rebuild_module, "BACKLOG_REGISTRY", tmp_path / "doc" / "backlog_registry.yaml")
        monkeypatch.setattr(rebuild_module, "USER_STORIES_DIR", tmp_path / "doc" / "user_stories")
        index_path = tmp_path / "doc" / "user_stories_index.json"
        monkeypatch.setattr(rebuild_module, "US_INDEX", index_path)

        # Stale index: US-8.1 is open in index, but registry says closed
        stale_index = {
            "version": 1, "generated": "2026-04-01",
            "items": [{"us_id": "US-8.1", "epic": 8, "epic_name": "Epic 8", "title": "T",
                       "priority": "P0", "cjm_stage": "6", "cjm_moment_name": "M",
                       "status": "open", "covered_by": None, "closed_date": None,
                       "path": "doc/user_stories/us-8.1.md"}],
            "open_candidates": [{"rank": 1, "us_id": "US-8.1", "title": "T", "priority": "P0",
                                  "cjm_stage": "6", "status": "open", "coverage": "open", "pain_point": None}]
        }
        us_files = {"us-8.1.md": _make_us_file("US-8.1", priority="P0", status="open")}
        registry = _make_registry([{"id": "epoch-reindex-mastery-guard", "status": "closed", "user_stories": ["US-8.1"]}])
        _seed_env(tmp_path, us_files, registry, existing_index=stale_index)

        rc = rebuild_module.main(argv=["--check"])
        assert rc == 1

    def test_check_returns_0_when_uptodate(self, rebuild_module, tmp_path, monkeypatch):
        monkeypatch.setattr(rebuild_module, "BACKLOG_REGISTRY", tmp_path / "doc" / "backlog_registry.yaml")
        monkeypatch.setattr(rebuild_module, "USER_STORIES_DIR", tmp_path / "doc" / "user_stories")
        index_path = tmp_path / "doc" / "user_stories_index.json"
        monkeypatch.setattr(rebuild_module, "US_INDEX", index_path)

        us_files = {"us-3.2.md": _make_us_file("US-3.2", priority="P1", status="open")}
        _seed_env(tmp_path, us_files, _make_registry([]))
        # Write fresh index first
        rebuild_module.rebuild(write=True)

        rc = rebuild_module.main(argv=["--check"])
        assert rc == 0
