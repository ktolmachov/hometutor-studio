import pytest
from chromadb.errors import NotFoundError

import app.retrieval_cache as retrieval_cache
import app.retrieval_cache_discovery as retrieval_cache_discovery


# ---------------------------------------------------------------------------
# is_base_services_ready
# ---------------------------------------------------------------------------

def test_is_base_services_ready_false_when_cache_cleared():
    """Returns False immediately after cache is cleared (no services initialised)."""
    retrieval_cache.clear_retrieval_cache()
    assert retrieval_cache.is_base_services_ready() is False


def test_is_base_services_ready_true_after_index_set(monkeypatch):
    """Returns True once _cached_index is populated (simulates post-warmup state)."""
    retrieval_cache.clear_retrieval_cache()
    monkeypatch.setattr(retrieval_cache, "_cached_index", object())
    assert retrieval_cache.is_base_services_ready() is True


def test_get_base_services_raises_for_empty_collection(monkeypatch):
    class FakeCollection:
        def count(self):
            return 0

    class FakeClient:
        def get_collection(self, name):
            return FakeCollection()

    monkeypatch.setattr(retrieval_cache, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(
        retrieval_cache,
        "get_active_collection_names",
        lambda: ("home_rag", "home_rag_summaries"),
    )
    class _Bk:
        def get_client(self):
            return FakeClient()

    monkeypatch.setattr(retrieval_cache, "get_default_chroma_backend", lambda _path=None: _Bk())
    retrieval_cache.clear_retrieval_cache()

    with pytest.raises(retrieval_cache.EmptyIndexError, match="Индекс пуст"):
        retrieval_cache.get_base_services()


def test_get_base_services_raises_for_missing_collection(monkeypatch):
    class FakeClient:
        def get_collection(self, name):
            raise NotFoundError(f"Collection [{name}] does not exist")

    class _Bk:
        def get_client(self):
            return FakeClient()

        def list_collections(self, _client):
            return []

    monkeypatch.setattr(retrieval_cache, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(
        retrieval_cache,
        "get_active_collection_names",
        lambda: ("home-rag_v2", "home-rag_v2_summaries"),
    )
    monkeypatch.setattr(retrieval_cache, "get_default_chroma_backend", lambda _path=None: _Bk())
    monkeypatch.setattr(retrieval_cache_discovery, "get_default_chroma_backend", lambda _path=None: _Bk())
    retrieval_cache.clear_retrieval_cache()

    with pytest.raises(retrieval_cache.EmptyIndexError, match="Индекс пуст"):
        retrieval_cache.get_base_services()
    assert retrieval_cache._cached_empty is True


def test_resolve_active_collection_names_discovers_default_when_configured_missing(monkeypatch):
    class FakeCollection:
        def __init__(self, count: int):
            self._count = count

        def count(self):
            return self._count

    class FakeClient:
        def get_collection(self, name):
            if name == "home_rag":
                return FakeCollection(42)
            if name == "home_rag_summaries":
                return FakeCollection(5)
            raise NotFoundError(name)

    class _Bk:
        def list_collections(self, _client):
            return ["home_rag", "home_rag_summaries"]

    adopted: list[tuple[str, str]] = []

    class _Settings:
        enable_document_summaries = True
        faq_memory_collection_name = "home_rag_faq"
        collection_name = "home-rag_v2"
        summary_collection_name = "home-rag_v2_summaries"

    monkeypatch.setattr(retrieval_cache_discovery, "_settings", lambda: _Settings())
    monkeypatch.setattr(retrieval_cache_discovery, "get_default_chroma_backend", lambda _path=None: _Bk())
    monkeypatch.setattr(
        "app.index_registry.adopt_discovered_collections",
        lambda chunks, summaries: adopted.append((chunks, summaries)),
    )

    def _raise_empty(**_kw):
        raise retrieval_cache.EmptyIndexError("empty")

    chunks, summaries = retrieval_cache_discovery._resolve_active_collection_names(
        FakeClient(),
        "home-rag_v2",
        "home-rag_v2_summaries",
        chroma_dir="chroma_db",
        raise_empty_fn=_raise_empty,
    )
    assert chunks == "home_rag"
    assert summaries == "home_rag_summaries"
    assert adopted == [("home_rag", "home_rag_summaries")]


def test_resolve_active_collection_names_recovers_unactivated_staging(monkeypatch):
    class FakeCollection:
        def __init__(self, count: int):
            self._count = count

        def count(self):
            return self._count

    staging_chunks = "home-rag_v2__staging__1779541798900"

    class FakeClient:
        def get_collection(self, name):
            if name == staging_chunks:
                return FakeCollection(2000)
            raise NotFoundError(name)

    class _Bk:
        def list_collections(self, _client):
            return [
                "home_rag_faq",
                "home-rag_v2__staging__1779536856428",
                staging_chunks,
            ]

    adopted: list[tuple[str, str]] = []

    class _Settings:
        enable_document_summaries = True
        faq_memory_collection_name = "home_rag_faq"
        collection_name = "home-rag_v2"
        summary_collection_name = "home_rag_summaries"

    monkeypatch.setattr(retrieval_cache_discovery, "_settings", lambda: _Settings())
    monkeypatch.setattr(retrieval_cache_discovery, "get_default_chroma_backend", lambda _path=None: _Bk())
    monkeypatch.setattr(
        "app.index_registry.adopt_discovered_collections",
        lambda chunks, summaries: adopted.append((chunks, summaries)),
    )

    def _raise_empty(**_kw):
        raise retrieval_cache.EmptyIndexError("empty")

    chunks, summaries = retrieval_cache_discovery._resolve_active_collection_names(
        FakeClient(),
        "home-rag_v2",
        "home_rag_summaries",
        chroma_dir="chroma_db",
        raise_empty_fn=_raise_empty,
    )
    assert chunks == staging_chunks
    assert summaries == "home_rag_summaries"
    assert adopted == [(staging_chunks, "home_rag_summaries")]


def test_discover_chunks_collection_uses_staging_when_active_missing(monkeypatch):
    class FakeCollection:
        def __init__(self, count: int):
            self._count = count

        def count(self):
            return self._count

    class FakeClient:
        def get_collection(self, name):
            if name == "home-rag_v2__staging__1779541798900":
                return FakeCollection(2000)
            raise NotFoundError(name)

    class _Bk:
        def list_collections(self, _client):
            return [
                "home_rag_faq",
                "home-rag_v2__staging__1779536856428",
                "home-rag_v2__staging__1779541798900",
            ]

    class _Settings:
        faq_memory_collection_name = "home_rag_faq"
        collection_name = "home-rag_v2"

    monkeypatch.setattr(retrieval_cache_discovery, "_settings", lambda: _Settings())
    monkeypatch.setattr(retrieval_cache_discovery, "get_default_chroma_backend", lambda _path=None: _Bk())

    picked = retrieval_cache_discovery._discover_chunks_collection(FakeClient(), "home-rag_v2")
    assert picked == "home-rag_v2__staging__1779541798900"
