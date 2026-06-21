"""Tests for scripts/roadmap_sync_check.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECK_PATH = ROOT / "scripts" / "roadmap_sync_check.py"


@pytest.fixture(scope="module")
def roadmap_sync_module():
    spec = importlib.util.spec_from_file_location("roadmap_sync_check", CHECK_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_docs(tmp_path: Path) -> dict[str, Path]:
    doc_dir = tmp_path / "doc"
    user_stories_dir = doc_dir / "user_stories"
    user_stories_dir.mkdir(parents=True)

    tasklist = doc_dir / "tasklist.md"
    _write_text(
        tasklist,
        """# План работ

## Now

### Truth View

| Package | Status | CJM | Primary US | Owner | Notes |
|---|---|---|---|---|---|
| `epoch-active` | `ready` | #5 | `US-7.3` | codex | Active package |

### epoch-active Contract

contract body
""",
    )

    registry = doc_dir / "backlog_registry.yaml"
    _write_text(
        registry,
        """schema_version: 1
items:
  - id: epoch-active
    status: ready
    impact: loop-improvement
    user_stories: ["US-7.3"]
    created: 2026-04-21
    last_review: 2026-04-21
  - id: epoch-closed
    status: closed
    impact: loop-improvement
    user_stories: ["US-14.4"]
    created: 2026-04-20
    last_review: 2026-04-21
""",
    )

    closed_iterations = doc_dir / "closed_iterations.md"
    _write_text(
        closed_iterations,
        """# Closed

### epoch-closed — 2026-04-21

- summary
""",
    )

    _write_text(
        user_stories_dir / "us-7.3.md",
        """---
us_id: "US-7.3"
status: "open"
covered_by: null
closed_date: null
---
""",
    )
    _write_text(
        user_stories_dir / "us-14.4.md",
        """---
us_id: "US-14.4"
status: "closed"
covered_by: "epoch-closed"
closed_date: "2026-04-21"
---
""",
    )

    index = doc_dir / "user_stories_index.json"
    index.write_text(
        json.dumps(
            {
                "version": 1,
                "generated": "2026-04-21",
                "items": [
                    {
                        "us_id": "US-7.3",
                        "status": "open",
                        "covered_by": None,
                        "closed_date": None,
                        "path": "doc/user_stories/us-7.3.md",
                    },
                    {
                        "us_id": "US-14.4",
                        "status": "closed",
                        "covered_by": "epoch-closed",
                        "closed_date": "2026-04-21",
                        "path": "doc/user_stories/us-14.4.md",
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "tasklist": tasklist,
        "registry": registry,
        "closed_iterations": closed_iterations,
        "user_stories_dir": user_stories_dir,
        "user_stories_index": index,
    }


def test_repo_seed_passes_roadmap_sync_check(roadmap_sync_module):
    errors = roadmap_sync_module.check_roadmap_sync()
    assert errors == [], f"repo roadmap sync must pass, got: {errors}"


def test_closed_package_contract_left_in_tasklist_fails(roadmap_sync_module, tmp_path: Path):
    paths = _seed_docs(tmp_path)
    tasklist = paths["tasklist"]
    tasklist.write_text(
        tasklist.read_text(encoding="utf-8") + "\n### epoch-closed Contract\n\nlegacy contract\n",
        encoding="utf-8",
    )

    errors = roadmap_sync_module.check_roadmap_sync(
        tasklist_path=paths["tasklist"],
        backlog_registry_path=paths["registry"],
        closed_iterations_path=paths["closed_iterations"],
        user_stories_dir=paths["user_stories_dir"],
        user_stories_index_path=paths["user_stories_index"],
    )
    assert any("must not keep a full Contract section" in error for error in errors)


def test_closed_package_requires_story_closure_fields(roadmap_sync_module, tmp_path: Path):
    paths = _seed_docs(tmp_path)
    _write_text(
        paths["user_stories_dir"] / "us-14.4.md",
        """---
us_id: "US-14.4"
status: "open"
covered_by: null
closed_date: null
---
""",
    )

    errors = roadmap_sync_module.check_roadmap_sync(
        tasklist_path=paths["tasklist"],
        backlog_registry_path=paths["registry"],
        closed_iterations_path=paths["closed_iterations"],
        user_stories_dir=paths["user_stories_dir"],
        user_stories_index_path=paths["user_stories_index"],
    )
    assert any("must be status=closed" in error for error in errors)
    assert any("must set covered_by" in error for error in errors)
    assert any("must set closed_date" in error for error in errors)


def test_active_status_comes_from_registry_not_tasklist_truth_view(roadmap_sync_module, tmp_path: Path):
    paths = _seed_docs(tmp_path)
    paths["tasklist"].write_text(
        paths["tasklist"].read_text(encoding="utf-8").replace("`ready`", "`closed`"),
        encoding="utf-8",
    )

    errors = roadmap_sync_module.check_roadmap_sync(
        tasklist_path=paths["tasklist"],
        backlog_registry_path=paths["registry"],
        closed_iterations_path=paths["closed_iterations"],
        user_stories_dir=paths["user_stories_dir"],
        user_stories_index_path=paths["user_stories_index"],
    )

    assert not any("tasklist Truth View status" in error for error in errors)


def test_active_slot_retries_when_truth_view_row_misses_registry_items(
    roadmap_sync_module, monkeypatch, tmp_path: Path
):
    """Transient empty items[] snapshot + inconsistent Truth View row → reload fixes (max 2 retries)."""
    paths = _seed_docs(tmp_path)
    loads = {"n": 0}
    real_load = roadmap_sync_module.load_backlog_registry
    real_tv = roadmap_sync_module.get_backlog_truth_view
    stub_registry: dict = {"schema_version": 1, "items": []}

    def _load_side_effect(reg_path, **kwargs):
        loads["n"] += 1
        if loads["n"] == 1:
            return stub_registry.copy()
        return real_load(reg_path)

    def _tv_side_effect(*, registry_data=None, registry_path=None):
        if registry_data == stub_registry:
            return {
                "truth_view": [
                    {
                        "package": "epoch-active",
                        "status": "ready",
                        "cjm": "-",
                        "primary_us": "US-7.3",
                        "owner": "x",
                        "notes": "",
                        "wave_id": "",
                    }
                ]
            }
        return real_tv(registry_data=registry_data, registry_path=registry_path)

    monkeypatch.setattr(roadmap_sync_module, "load_backlog_registry", _load_side_effect)
    monkeypatch.setattr(roadmap_sync_module, "get_backlog_truth_view", _tv_side_effect)
    monkeypatch.setattr(roadmap_sync_module.time, "sleep", lambda *_a, **_k: None)

    errors = roadmap_sync_module.check_roadmap_sync(
        tasklist_path=paths["tasklist"],
        backlog_registry_path=paths["registry"],
        closed_iterations_path=paths["closed_iterations"],
        user_stories_dir=paths["user_stories_dir"],
        user_stories_index_path=paths["user_stories_index"],
    )
    assert errors == []
    assert loads["n"] == 2


def test_active_slot_transient_retryable_predicate(roadmap_sync_module):
    """Only missing-id slot errors may trigger reload; data errors (no status) must not."""
    pred = roadmap_sync_module._active_slot_errors_transient_retryable
    mid = "epoch-x: Truth View active package not found under items[].id in backlog_registry.yaml"
    ms = "epoch-x: backlog_registry item is missing `status` field (Truth View slot status='ready')"
    assert pred([]) is False
    assert pred([mid]) is True
    assert pred([ms]) is False
    assert pred(["other"]) is False
    assert pred([mid, ms]) is False
    assert pred([mid, "unrelated"]) is True


def test_active_slot_stops_retrying_after_two_attempts_still_missing_item(
    roadmap_sync_module, monkeypatch, tmp_path: Path
):
    """Initial load + two retries (three reads); persistent missing-id → surface error."""
    paths = _seed_docs(tmp_path)
    loads = {"n": 0}
    stub_registry: dict = {"schema_version": 1, "items": []}
    sleeps: list[float] = []

    def _load_always_stub(_reg_path, **_kwargs):
        loads["n"] += 1
        return stub_registry.copy()

    def _tv_always_injected(*, registry_data=None, registry_path=None):
        return {
            "truth_view": [
                {
                    "package": "epoch-active",
                    "status": "ready",
                    "cjm": "-",
                    "primary_us": "US-7.3",
                    "owner": "x",
                    "notes": "",
                    "wave_id": "",
                }
            ]
        }

    monkeypatch.setattr(roadmap_sync_module, "load_backlog_registry", _load_always_stub)
    monkeypatch.setattr(roadmap_sync_module, "get_backlog_truth_view", _tv_always_injected)
    monkeypatch.setattr(
        roadmap_sync_module.time,
        "sleep",
        lambda s, **_k: sleeps.append(float(s)),
    )

    errors = roadmap_sync_module.check_roadmap_sync(
        tasklist_path=paths["tasklist"],
        backlog_registry_path=paths["registry"],
        closed_iterations_path=paths["closed_iterations"],
        user_stories_dir=paths["user_stories_dir"],
        user_stories_index_path=paths["user_stories_index"],
    )
    assert any("Truth View active package not found under items[].id" in e for e in errors)
    assert loads["n"] == 3
    assert len(sleeps) == 2
    assert sleeps[0] == pytest.approx(0.05)
    assert sleeps[1] == pytest.approx(0.1)


def test_user_stories_index_drift_fails(roadmap_sync_module, tmp_path: Path):
    paths = _seed_docs(tmp_path)
    index_data = json.loads(paths["user_stories_index"].read_text(encoding="utf-8"))
    index_data["items"][1]["covered_by"] = "stale-package"
    paths["user_stories_index"].write_text(
        json.dumps(index_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    errors = roadmap_sync_module.check_roadmap_sync(
        tasklist_path=paths["tasklist"],
        backlog_registry_path=paths["registry"],
        closed_iterations_path=paths["closed_iterations"],
        user_stories_dir=paths["user_stories_dir"],
        user_stories_index_path=paths["user_stories_index"],
    )
    assert any("doc/user_stories_index.json is stale" in error for error in errors)


def test_open_story_coverage_sentinel_matches_null_frontmatter(roadmap_sync_module, tmp_path: Path):
    paths = _seed_docs(tmp_path)
    index_data = json.loads(paths["user_stories_index"].read_text(encoding="utf-8"))
    index_data["items"][0]["covered_by"] = "open"
    paths["user_stories_index"].write_text(
        json.dumps(index_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    errors = roadmap_sync_module.check_roadmap_sync(
        tasklist_path=paths["tasklist"],
        backlog_registry_path=paths["registry"],
        closed_iterations_path=paths["closed_iterations"],
        user_stories_dir=paths["user_stories_dir"],
        user_stories_index_path=paths["user_stories_index"],
    )
    assert not errors


def test_main_runs_autocorrect_before_sync_check(roadmap_sync_module, monkeypatch):
    calls: list[tuple] = []

    def _fake_run(cmd, **kwargs):
        calls.append(tuple(cmd))
        return SimpleNamespace(returncode=0, stdout="PASS", stderr="")

    monkeypatch.setattr(roadmap_sync_module, "check_roadmap_sync", lambda **_: [])
    monkeypatch.setattr(roadmap_sync_module.subprocess, "run", _fake_run)
    monkeypatch.setattr(sys, "argv", ["roadmap_sync_check.py"])

    exit_code = roadmap_sync_module.main()

    assert exit_code == 0
    assert calls, "autocorrect subprocess must be invoked"
    assert any("auto_correct_registry_closed_status.py" in str(part) for part in calls[0])


def test_main_fails_when_autocorrect_fails(roadmap_sync_module, monkeypatch):
    def _fake_run(*_args, **_kwargs):
        return SimpleNamespace(returncode=1, stdout="broken", stderr="error")

    monkeypatch.setattr(roadmap_sync_module.subprocess, "run", _fake_run)
    monkeypatch.setattr(sys, "argv", ["roadmap_sync_check.py"])

    exit_code = roadmap_sync_module.main()

    assert exit_code == 2
