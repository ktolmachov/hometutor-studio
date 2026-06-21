from __future__ import annotations

from types import SimpleNamespace

import app.ingestion_index_nodes as index_nodes


class _FakeNode:
    def __init__(self, text: str) -> None:
        self.text = text

    def get_content(self, metadata_mode=None) -> str:
        return self.text


def test_embed_and_store_flushes_in_configured_store_batches(monkeypatch, settings_env, tmp_path):
    settings_env({"INGEST_EMBED_PIPELINE_BATCH_SIZE": "2", "INGEST_STORE_BATCH_SIZE": "3"})
    monkeypatch.setattr(index_nodes.ing, "INGEST_CACHE_PATH", tmp_path / "ingest_embed_cache.json")

    nodes = [_FakeNode(f"node-{idx}") for idx in range(7)]
    add_calls: list[int] = []

    class FakePipeline:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def run(self, nodes, show_progress=True):
            return list(nodes)

    class FakeCache:
        @classmethod
        def from_persist_path(cls, path):
            return cls()

        def persist(self, path):
            return None

    monkeypatch.setattr(index_nodes, "IngestionPipeline", FakePipeline)
    monkeypatch.setattr(index_nodes, "IngestionCache", FakeCache)

    vector_store = SimpleNamespace(add=lambda batch: add_calls.append(len(batch)))

    index_nodes._embed_and_store(nodes, embed_model=object(), vector_store=vector_store, show_progress=False)

    assert add_calls == [3, 3, 1]
