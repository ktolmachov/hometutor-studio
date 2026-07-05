import threading
from types import SimpleNamespace

import app.retrieval_cache as retrieval_cache


class _FakeCollection:
    def __init__(self, name: str, count_value: int = 1):
        self.name = name
        self._count_value = count_value

    def count(self):
        return self._count_value


class _FakeClient:
    def __init__(self, collections):
        self.collections = collections

    def get_collection(self, name):
        if name not in self.collections:
            raise KeyError(name)
        return self.collections[name]


def _patch_base_services_dependencies(monkeypatch):
    settings = SimpleNamespace(
        openai_api_key="sk-test",
        embed_model="text-embedding-3-small",
        enable_document_summaries=True,
        query_engine_cache_size=32,
        query_engine_ttl_sec=1800,
    )
    monkeypatch.setattr(retrieval_cache, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(retrieval_cache, "get_index_embed_model", lambda: None)
    monkeypatch.setattr(retrieval_cache, "get_embed_model", lambda **kwargs: object())
    monkeypatch.setattr(retrieval_cache, "get_llm", lambda: object())
    monkeypatch.setattr(retrieval_cache, "effective_settings", lambda: settings)
    monkeypatch.setattr(
        retrieval_cache,
        "_settings",
        lambda: settings,
    )
    monkeypatch.setattr(retrieval_cache, "ChromaVectorStore", lambda chroma_collection: chroma_collection)
    monkeypatch.setattr(
        retrieval_cache.StorageContext,
        "from_defaults",
        lambda vector_store: {"vector_store": vector_store},
    )
    monkeypatch.setattr(
        retrieval_cache.VectorStoreIndex,
        "from_vector_store",
        lambda **kwargs: {"vector_store": kwargs["vector_store"]},
    )


def test_get_base_services_keeps_serving_active_index_while_reindex_flag_is_set(monkeypatch):
    fake_client = _FakeClient(
        {
            "active_chunks_v1": _FakeCollection("active_chunks_v1", count_value=2),
            "active_summary_v1": _FakeCollection("active_summary_v1", count_value=1),
        }
    )
    _patch_base_services_dependencies(monkeypatch)

    class _Bk:
        def get_client(self):
            return fake_client

    monkeypatch.setattr(retrieval_cache, "get_default_chroma_backend", lambda _path=None: _Bk())
    monkeypatch.setattr(
        retrieval_cache,
        "get_active_collection_names",
        lambda: ("active_chunks_v1", "active_summary_v1"),
    )

    retrieval_cache.clear_retrieval_cache()
    retrieval_cache.reindex_begin()
    try:
        services = retrieval_cache.get_base_services()
    finally:
        retrieval_cache.reindex_end()

    assert services["collection"].name == "active_chunks_v1"
    assert services["summary_collection"].name == "active_summary_v1"
    assert retrieval_cache.is_reindex_in_progress() is False


def test_get_base_services_switches_to_new_active_collection_after_activation(monkeypatch):
    fake_client = _FakeClient(
        {
            "active_chunks_v1": _FakeCollection("active_chunks_v1", count_value=2),
            "active_summary_v1": _FakeCollection("active_summary_v1", count_value=1),
            "active_chunks_v2": _FakeCollection("active_chunks_v2", count_value=3),
            "active_summary_v2": _FakeCollection("active_summary_v2", count_value=1),
        }
    )
    active_names = {"value": ("active_chunks_v1", "active_summary_v1")}

    _patch_base_services_dependencies(monkeypatch)

    class _Bk:
        def get_client(self):
            return fake_client

    monkeypatch.setattr(retrieval_cache, "get_default_chroma_backend", lambda _path=None: _Bk())
    monkeypatch.setattr(
        retrieval_cache,
        "get_active_collection_names",
        lambda: active_names["value"],
    )

    retrieval_cache.clear_retrieval_cache()
    before = retrieval_cache.get_base_services()
    assert before["collection"].name == "active_chunks_v1"

    active_names["value"] = ("active_chunks_v2", "active_summary_v2")
    retrieval_cache.clear_retrieval_cache()
    after = retrieval_cache.get_base_services()

    assert after["collection"].name == "active_chunks_v2"
    assert after["summary_collection"].name == "active_summary_v2"


def test_concurrent_get_base_services_while_reindex_flag_set(monkeypatch):
    fake_client = _FakeClient(
        {
            "active_chunks_v1": _FakeCollection("active_chunks_v1", count_value=2),
            "active_summary_v1": _FakeCollection("active_summary_v1", count_value=1),
        }
    )
    _patch_base_services_dependencies(monkeypatch)

    class _Bk:
        def get_client(self):
            return fake_client

    monkeypatch.setattr(retrieval_cache, "get_default_chroma_backend", lambda _path=None: _Bk())
    monkeypatch.setattr(
        retrieval_cache,
        "get_active_collection_names",
        lambda: ("active_chunks_v1", "active_summary_v1"),
    )

    retrieval_cache.clear_retrieval_cache()
    retrieval_cache.reindex_begin()
    results: list[str] = []

    def reader():
        try:
            svc = retrieval_cache.get_base_services()
            results.append(svc["collection"].name)
        except Exception as exc:
            results.append(type(exc).__name__)

    try:
        threads = [threading.Thread(target=reader) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)
    finally:
        retrieval_cache.reindex_end()

    assert results == ["active_chunks_v1"] * 8
