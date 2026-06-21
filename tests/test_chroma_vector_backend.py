"""Compatibility smoke tests for ChromaVectorBackend."""

import logging
from pathlib import Path

import pytest

from app.chroma_vector_backend import ChromaVectorBackend


def test_delete_missing_collection_is_silent_at_warning(caplog, tmp_path):
    """Удаление несуществующей коллекции — ожидаемый noop, без warning в логах."""
    caplog.set_level(logging.WARNING)
    backend = ChromaVectorBackend(persist_directory=tmp_path / "chroma")
    client = backend.get_client()
    backend.delete_collection(client, "never_created_collection")
    assert "Chroma collection delete failed" not in caplog.text


def test_backend_list_and_delete_roundtrip(tmp_path):
    backend = ChromaVectorBackend(persist_directory=tmp_path / "chroma")
    client = backend.get_client()
    col = backend.get_or_create_collection(client, "test_col")
    assert col.name == "test_col"
    names = backend.list_collections(client)
    assert "test_col" in names
    backend.delete_collection(client, "test_col")
    names_after = backend.list_collections(client)
    assert "test_col" not in names_after


def test_get_index_stats_empty_chroma_path(monkeypatch, tmp_path):
    """Empty chroma dir yields not_initialized without raising."""
    from app import index_diff

    monkeypatch.setattr(index_diff, "CHROMA_DIR", tmp_path / "missing_chroma")
    monkeypatch.setattr(index_diff, "COLLECTION_NAME", "any")
    stats = index_diff.get_index_stats()
    assert stats["status"] == "not_initialized"
    assert "index_version" in stats
    assert "generation_id" in stats
