"""Tests for scripts/backlog_registry_lint.py (PoC schema v1)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LINT_PATH = ROOT / "scripts" / "backlog_registry_lint.py"


@pytest.fixture(scope="module")
def lint_module():
    spec = importlib.util.spec_from_file_location("backlog_registry_lint", LINT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _base_item() -> dict:
    return {
        "id": "test-item",
        "status": "ready",
        "impact": "infra",
        "created": "2026-04-20",
        "last_review": "2026-04-20",
    }


def test_seed_registry_passes_lint(lint_module):
    import yaml

    data = yaml.safe_load((ROOT / "doc" / "backlog_registry.yaml").read_text(encoding="utf-8"))
    errors, _ = lint_module.lint(data)
    assert errors == [], f"seed registry must lint clean, got: {errors}"


def test_missing_required_key_fails(lint_module):
    item = _base_item()
    item.pop("status")
    data = {"schema_version": 1, "items": [item]}
    errors, _ = lint_module.lint(data)
    assert any("missing required keys" in e for e in errors)


def test_duplicate_id_fails(lint_module):
    data = {"schema_version": 1, "items": [_base_item(), _base_item()]}
    errors, _ = lint_module.lint(data)
    assert any("duplicate id" in e for e in errors)


def test_bad_status_fails(lint_module):
    item = _base_item()
    item["status"] = "in-progress"
    data = {"schema_version": 1, "items": [item]}
    errors, _ = lint_module.lint(data)
    assert any("status" in e and "not in" in e for e in errors)


def test_deferred_requires_re_entry_condition(lint_module):
    item = _base_item()
    item["status"] = "deferred"
    data = {"schema_version": 1, "items": [item]}
    errors, _ = lint_module.lint(data)
    assert any("re_entry_condition" in e for e in errors)


def test_two_wip_items_fails(lint_module):
    a, b = _base_item(), _base_item()
    a["id"], a["status"] = "a", "wip"
    b["id"], b["status"] = "b", "wip"
    data = {"schema_version": 1, "items": [a, b]}
    errors, _ = lint_module.lint(data)
    assert any("Truth View invariant" in e for e in errors)


def test_two_ready_items_fails(lint_module):
    dod = [".\\.venv\\Scripts\\python.exe -m pytest tests/test_api.py"]
    a, b = _base_item(), _base_item()
    a["id"], b["id"] = "era", "erb"
    a["dod_commands"], b["dod_commands"] = dod, dod
    data = {"schema_version": 1, "items": [a, b]}
    errors, _ = lint_module.lint(data)
    assert any("Truth View invariant" in e for e in errors)


def test_active_package_id_mismatch_fails(lint_module):
    item = _base_item()
    item["id"] = "epoch-only"
    item["dod_commands"] = [".\\.venv\\Scripts\\python.exe -m pytest tests/test_api.py"]
    data = {"schema_version": 1, "items": [item], "active_package_id": "epoch-other"}
    errors, _ = lint_module.lint(data)
    assert any("active_package_id" in e for e in errors)


def test_active_package_id_without_ready_fails(lint_module):
    item = _base_item()
    item["status"] = "proposed"
    data = {"schema_version": 1, "items": [item], "active_package_id": "epoch-only"}
    errors, _ = lint_module.lint(data)
    assert any("no package has status ready or wip" in e for e in errors)


def test_self_dependency_fails(lint_module):
    item = _base_item()
    item["depends_on"] = [item["id"]]
    data = {"schema_version": 1, "items": [item]}
    errors, _ = lint_module.lint(data)
    assert any("includes self" in e for e in errors)


def test_unknown_schema_version_fails(lint_module):
    data = {"schema_version": 999, "items": []}
    errors, _ = lint_module.lint(data)
    assert any("schema_version" in e for e in errors)


def test_bad_date_fails(lint_module):
    item = _base_item()
    item["created"] = "not-a-date"
    data = {"schema_version": 1, "items": [item]}
    errors, _ = lint_module.lint(data)
    assert any("ISO date" in e for e in errors)


def test_last_review_before_created_fails(lint_module):
    item = _base_item()
    item["created"] = "2026-04-20"
    item["last_review"] = "2026-04-10"
    data = {"schema_version": 1, "items": [item]}
    errors, _ = lint_module.lint(data)
    assert any("precedes created" in e for e in errors)


def test_active_wave_determinism_explicit_completed_falls_through(lint_module) -> None:
    """explicit active_wave_id ignored when wave is terminal; scans lower bands."""
    waves = [
        {"id": "w-done", "status": "completed"},
        {"id": "w-proposed", "status": "proposed"},
    ]
    data: dict = {"waves": waves, "active_wave_id": "w-done"}
    assert lint_module.get_active_wave(data) == "w-proposed"


def test_active_wave_determinism_explicit_ready(lint_module) -> None:
    waves = [
        {"id": "w-completed", "status": "completed"},
        {"id": "w-ready", "status": "ready"},
    ]
    data: dict = {"waves": waves, "active_wave_id": "w-ready"}
    assert lint_module.get_active_wave(data) == "w-ready"


def test_active_wave_determinism_wip_over_ready(lint_module) -> None:
    waves = [
        {"id": "w-ready", "status": "ready"},
        {"id": "w-wip", "status": "wip"},
    ]
    data: dict = {"waves": waves}
    assert lint_module.get_active_wave(data) == "w-wip"


def test_active_wave_determinism_ready_over_proposed(lint_module) -> None:
    waves = [
        {"id": "w-proposed", "status": "proposed"},
        {"id": "w-ready", "status": "ready"},
    ]
    data: dict = {"waves": waves}
    assert lint_module.get_active_wave(data) == "w-ready"


def test_active_wave_determinism_completed_only_none(lint_module) -> None:
    waves = [{"id": "w1", "status": "completed"}]
    data: dict = {"waves": waves}
    assert lint_module.get_active_wave(data) is None


def test_active_wave_determinism_frozen_explicit_skipped(lint_module) -> None:
    waves = [
        {"id": "w-frozen", "status": "frozen"},
        {"id": "w-ready", "status": "ready"},
    ]
    data: dict = {"waves": waves, "active_wave_id": "w-frozen"}
    assert lint_module.get_active_wave(data) == "w-ready"


def test_active_wave_determinism_case_insensitive_status(lint_module) -> None:
    waves = [{"id": "w-upper", "status": "READY"}]
    data: dict = {"waves": waves}
    assert lint_module.get_active_wave(data) == "w-upper"
