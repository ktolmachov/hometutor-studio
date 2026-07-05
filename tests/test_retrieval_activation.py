from types import SimpleNamespace

import app.retrieval_cache as retrieval_cache


class _FakeCollection:
    def __init__(self, count_value=1):
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


def test_activate_staging_index_updates_active_state_and_clears_cache(monkeypatch):
    fake_client = _FakeClient(
        {
            "home_rag__staging__1": _FakeCollection(3),
            "home_rag_summaries__staging__1": _FakeCollection(1),
        }
    )
    cleared = []

    class _Bk:
        def get_client(self):
            return fake_client

    act_calls: list[dict] = []

    def _fake_activate(**kwargs):
        act_calls.append(kwargs)
        return kwargs

    monkeypatch.setattr(retrieval_cache, "get_default_chroma_backend", lambda _path=None: _Bk())
    monkeypatch.setattr(
        retrieval_cache,
        "_settings",
        lambda: SimpleNamespace(enable_document_summaries=True, embed_model="text-embedding-3-small"),
    )
    monkeypatch.setattr(retrieval_cache, "activate_staging_generation", _fake_activate)
    monkeypatch.setattr(
        retrieval_cache,
        "load_active_index_state",
        lambda: {
            "collection_name": "home_rag__staging__1",
            "summary_collection_name": "home_rag_summaries__staging__1",
            "version_marker": "home_rag__staging__1:ts",
            "activated_at": "ts",
            "generation_id": "g_test",
            "index_version": 2,
        },
    )
    monkeypatch.setattr(retrieval_cache, "clear_retrieval_cache", lambda: cleared.append("cleared"))

    state = retrieval_cache.activate_staging_index(
        "home_rag__staging__1",
        "home_rag_summaries__staging__1",
    )

    assert act_calls[0]["chunks_collection"] == "home_rag__staging__1"
    assert act_calls[0]["summaries_collection"] == "home_rag_summaries__staging__1"
    assert act_calls[0]["nodes_count"] == 3
    assert cleared == ["cleared"]
    assert state["collection_name"] == "home_rag__staging__1"


def test_get_base_services_uses_active_collection_marker(monkeypatch):
    fake_client = _FakeClient(
        {
            "active_chunks_v2": _FakeCollection(2),
            "active_summary_v2": _FakeCollection(1),
        }
    )

    monkeypatch.setattr(retrieval_cache, "OPENAI_API_KEY", "sk-test")
    class _Bk:
        def get_client(self):
            return fake_client

    monkeypatch.setattr(retrieval_cache, "get_default_chroma_backend", lambda _path=None: _Bk())
    monkeypatch.setattr(
        retrieval_cache,
        "get_active_collection_names",
        lambda: ("active_chunks_v2", "active_summary_v2"),
    )
    settings = SimpleNamespace(
        openai_api_key="sk-test",
        embed_model="text-embedding-3-small",
        enable_document_summaries=True,
        query_engine_cache_size=32,
        query_engine_ttl_sec=1800,
    )
    monkeypatch.setattr(retrieval_cache, "get_index_embed_model", lambda: None)
    monkeypatch.setattr(retrieval_cache, "get_embed_model", lambda **kwargs: object())
    monkeypatch.setattr(retrieval_cache, "get_llm", lambda: object())
    monkeypatch.setattr(retrieval_cache, "effective_settings", lambda: settings)
    monkeypatch.setattr(
        retrieval_cache,
        "_settings",
        lambda: settings,
    )
    monkeypatch.setattr(retrieval_cache, "ChromaVectorStore", lambda chroma_collection: {"collection": chroma_collection})
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
    retrieval_cache.clear_retrieval_cache()

    services = retrieval_cache.get_base_services()

    assert services["collection"].count() == 2
    assert services["summary_collection"].count() == 1
