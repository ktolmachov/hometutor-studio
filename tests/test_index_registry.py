"""Tests for index_registry.json (blue-green generation pointer)."""

import json
from pathlib import Path

import pytest

import app.index_registry as ir


@pytest.fixture
def isolated_registry(monkeypatch, tmp_path):
    reg = tmp_path / "index_registry.json"
    lock = tmp_path / "index_registry.json.lock"
    monkeypatch.setattr(ir, "REGISTRY_PATH", reg)
    monkeypatch.setattr(ir, "REGISTRY_LOCK_PATH", lock)
    yield reg, lock


def test_migrate_from_legacy_active_index_writes_registry(isolated_registry, monkeypatch, tmp_path):
    reg_path, _ = isolated_registry
    legacy = tmp_path / "legacy_active.json"
    legacy.write_text(
        json.dumps(
            {
                "collection_name": "chunks_staging_1",
                "summary_collection_name": "sum_staging_1",
                "version_marker": "chunks_staging_1:act",
                "activated_at": "2020-01-01T00:00:00+00:00",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(ir, "LEGACY_ACTIVE_INDEX_PATH", legacy)
    assert not reg_path.exists()
    data = ir.load_registry()
    assert reg_path.exists()
    assert data["active_generation"]["chunks_collection"] == "chunks_staging_1"
    assert data["active_generation"]["summaries_collection"] == "sum_staging_1"
    assert data["index_version"] == 1


def test_activate_staging_generation_bumps_index_version(isolated_registry, monkeypatch):
    _, _ = isolated_registry
    monkeypatch.setattr(ir, "LEGACY_ACTIVE_INDEX_PATH", Path("/nonexistent/legacy.json"))
    ir.activate_staging_generation(
        chunks_collection="a__staging__1",
        summaries_collection="b__staging__1",
        nodes_count=5,
    )
    reg = ir.load_registry()
    assert reg["index_version"] == 1
    assert reg["active_generation"]["chunks_collection"] == "a__staging__1"
    assert reg["active_generation"]["nodes_count"] == 5


def test_mark_activation_failed_does_not_change_active(isolated_registry, monkeypatch):
    _, _ = isolated_registry
    monkeypatch.setattr(ir, "LEGACY_ACTIVE_INDEX_PATH", Path("/nonexistent/legacy.json"))
    ir.activate_staging_generation(chunks_collection="keep_c", summaries_collection="keep_s")
    before = ir.get_active_collection_names()
    ir.mark_activation_failed(chunks_collection="bad", summaries_collection="bad2", error="empty")
    after = ir.get_active_collection_names()
    assert before == after
    reg = ir.load_registry()
    assert reg["last_failed_generation"]["error"] == "empty"
