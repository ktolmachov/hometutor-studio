import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from app import index_diff
from app.index_diff import get_index_stats, get_index_embed_model


def test_stats_no_chroma_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(index_diff, "CHROMA_DIR", tmp_path / "nonexistent")
    monkeypatch.setattr(index_diff, "COLLECTION_NAME", "test_col")

    stats = get_index_stats()

    assert stats["status"] == "not_initialized"
    assert stats["documents_count"] == 0
    assert stats["nodes_count"] == 0
    assert stats["files"] == []


def test_stats_no_collection(tmp_path, monkeypatch):
    chroma_dir = tmp_path / "chroma"
    chroma_dir.mkdir()
    monkeypatch.setattr(index_diff, "CHROMA_DIR", chroma_dir)
    monkeypatch.setattr(index_diff, "COLLECTION_NAME", "nonexistent_collection_xyz")

    stats = get_index_stats()

    assert stats["status"] == "no_collection"
    assert stats["documents_count"] == 0


def test_stats_with_collection(tmp_path, monkeypatch):
    import chromadb

    chroma_dir = tmp_path / "chroma"
    chroma_dir.mkdir()
    client = chromadb.PersistentClient(path=str(chroma_dir))
    col = client.get_or_create_collection("test_stats")
    col.add(
        ids=["node1", "node2", "node3"],
        documents=["text1", "text2", "text3"],
        metadatas=[
            {"relative_path": "doc1.txt", "file_name": "doc1.txt"},
            {"relative_path": "doc1.txt", "file_name": "doc1.txt"},
            {"relative_path": "doc2.md", "file_name": "doc2.md"},
        ],
    )

    monkeypatch.setattr(index_diff, "CHROMA_DIR", chroma_dir)
    monkeypatch.setattr(index_diff, "COLLECTION_NAME", "test_stats")

    meta_path = tmp_path / "index_meta.json"
    meta_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(index_diff, "INDEX_META_PATH", meta_path)

    stats = get_index_stats()

    assert stats["status"] == "ok"
    assert stats["nodes_count"] == 3
    assert stats["documents_count"] == 2
    assert "doc1.txt" in stats["files"]
    assert "doc2.md" in stats["files"]
    assert stats["last_indexed_at"] is not None
    assert stats["collection_name"] == "test_stats"


def test_stats_last_indexed_at_none_when_no_meta(tmp_path, monkeypatch):
    monkeypatch.setattr(index_diff, "INDEX_META_PATH", tmp_path / "no_such_file.json")
    monkeypatch.setattr(index_diff, "CHROMA_DIR", tmp_path / "nonexistent")

    stats = get_index_stats()
    assert stats["last_indexed_at"] is None


def test_get_index_embed_model_returns_value_when_meta_present(tmp_path, monkeypatch):
    meta_path = tmp_path / "index_meta.json"
    meta_path.write_text(
        json.dumps(
            {
                "__meta__": {
                    "embed_model": "text-embedding-3-small",
                },
                "some/file.txt": {"size": 123, "mtime": 1.0},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(index_diff, "INDEX_META_PATH", meta_path)

    value = get_index_embed_model()
    assert value == "text-embedding-3-small"


def test_get_index_embed_model_returns_none_when_no_meta(tmp_path, monkeypatch):
    meta_path = tmp_path / "index_meta.json"
    meta_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(index_diff, "INDEX_META_PATH", meta_path)

    value = get_index_embed_model()
    assert value is None
