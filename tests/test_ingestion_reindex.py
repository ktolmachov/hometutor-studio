from types import SimpleNamespace

from llama_index.core import Document

from app import ingestion
from app import ingestion_index_full
from app import ingestion_index_partial
from app import ingestion_loader
from app.config import BASE_DIR, get_retrieval_settings
from app.ingestion_content_state import compute_retrieval_fingerprint


class _FakeReader:
    def __init__(self, *args, **kwargs):
        pass

    def load_data(self):
        return [Document(text="hello", metadata={"file_path": "data/example.md", "doc_id": "example.md"})]


class _FakeCollection:
    def __init__(self, name):
        self.name = name

    def count(self):
        return 1


class _FakeClient:
    def __init__(self):
        self.deleted = []
        self.created = []
        self._cols: dict[str, _FakeCollection] = {}

    def delete_collection(self, name):
        self.deleted.append(name)
        self._cols.pop(name, None)

    def get_or_create_collection(self, name):
        self.created.append(name)
        col = _FakeCollection(name)
        self._cols[name] = col
        return col

    def get_collection(self, name):
        return self._cols[name]


class _FakeVectorStoreIndex:
    calls = []
    from_documents_calls = []

    def __init__(self, *args, **kwargs):
        self.__class__.calls.append({"args": args, "kwargs": kwargs})

    @classmethod
    def from_documents(cls, *args, **kwargs):
        cls.from_documents_calls.append({"args": args, "kwargs": kwargs})
        return cls(*args, **kwargs)


def _zero_usage():
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def _patch_common(monkeypatch, fake_client):
    graph_calls = []
    settings = SimpleNamespace(
        openai_api_key="test-key",
        collection_name="home_rag",
        summary_collection_name="home_rag_summaries",
        enable_document_summaries=True,
        enable_metadata_enrichment=False,
        enable_partial_reindex=True,
        embed_model="text-embedding-3-small",
        doc_load_num_workers=4,
    )
    _fake_doc = Document(text="hello", metadata={"file_path": "data/example.md", "doc_id": "example.md"})
    monkeypatch.setattr(ingestion_loader, "get_settings", lambda: settings)
    monkeypatch.setattr(
        ingestion_loader,
        "build_file_manifest",
        lambda _data_dir, _exts: {
            "schema_version": 1,
            "files": {"example.md": {"size": 5, "mtime_ns": 1, "ext": ".md"}},
        },
    )
    monkeypatch.setattr(ingestion_loader, "load_content_hash_state", lambda _chroma_dir: None)
    monkeypatch.setattr(ingestion, "DATA_DIR", BASE_DIR)
    monkeypatch.setattr(ingestion, "_load_documents_parallel", lambda _data_dir: [_fake_doc])
    monkeypatch.setattr(
        ingestion,
        "_load_documents_with_extraction_cache",
        lambda **_kwargs: [_fake_doc],
    )
    monkeypatch.setattr(ingestion_index_full, "_embed_and_store", lambda *a, **kw: None)
    monkeypatch.setattr(ingestion_index_partial, "_embed_and_store", lambda *a, **kw: None)
    monkeypatch.setattr(ingestion, "_expand_structured_documents", lambda docs: docs)
    monkeypatch.setattr(ingestion, "_add_metadata", lambda docs: docs)
    def _fake_enrich_documents(docs, *, ingest_t0=None, **kwargs):
        return (
            docs,
            [],
            {
                "unique_doc_ids": 1,
                "metadata_enrichment_calls": 0,
                "summary_calls": 0,
                "metadata_enrichment_successes": 0,
                "summary_successes": 0,
                "estimated_cost_usd": {"metadata_enrichment": 0.0, "summary_generation": 0.0, "total": 0.0},
                "token_usage": {
                    "metadata_enrichment": _zero_usage(),
                    "summary_generation": _zero_usage(),
                    "total": _zero_usage(),
                },
            },
        )

    monkeypatch.setattr(ingestion, "_enrich_documents", _fake_enrich_documents)
    monkeypatch.setattr(ingestion, "_apply_contextualized_chunks", lambda docs: docs)
    monkeypatch.setattr(ingestion, "_configure_document_for_metadata_aware_split", lambda doc: None)
    monkeypatch.setattr(ingestion_loader, "_build_nodes", lambda docs: ["node-1"])
    monkeypatch.setattr(ingestion_loader, "get_embed_model", lambda: object())

    class _FakeChromaBackend:
        def __init__(self, fc: _FakeClient):
            self._fc = fc

        def get_client(self):
            return self._fc

        def delete_collection(self, client, name):
            self._fc.delete_collection(name)

        def get_or_create_collection(self, client, name):
            return self._fc.get_or_create_collection(name)

        def get_collection(self, client, name):
            return self._fc.get_collection(name)

    monkeypatch.setattr(
        ingestion_loader,
        "get_default_chroma_backend",
        lambda _path=None: _FakeChromaBackend(fake_client),
    )
    monkeypatch.setattr(ingestion_index_full, "activate_reset_generation", lambda **kwargs: None)
    monkeypatch.setattr(ingestion_index_full, "clear_retrieval_cache", lambda: None)
    monkeypatch.setattr(
        ingestion_index_full,
        "ChromaVectorStore",
        lambda chroma_collection: {"collection": chroma_collection},
    )
    monkeypatch.setattr(
        ingestion_index_full.StorageContext,
        "from_defaults",
        lambda vector_store: {"vector_store": vector_store},
    )
    monkeypatch.setattr(ingestion_index_full, "VectorStoreIndex", _FakeVectorStoreIndex)
    monkeypatch.setattr(ingestion_index_full, "record_ingestion_run", lambda **kwargs: None)
    monkeypatch.setattr(
        ingestion_index_full,
        "write_staging_knowledge_graph_bundle",
        lambda docs, _staging, **kwargs: (
            graph_calls.append(len(docs))
            or {"documents": 1, "concepts": 2, "relations": 1, "path": "tmp/staging"}
        ),
    )
    monkeypatch.setattr(
        ingestion_index_full,
        "write_generation_knowledge_graph_bundle",
        lambda docs, _gid, **kw: (
            graph_calls.append(len(docs))
            or {"documents": 1, "concepts": 2, "relations": 1, "path": "tmp/gen"}
        ),
    )
    monkeypatch.setattr(
        ingestion_index_full,
        "get_active_knowledge_graph",
        lambda: SimpleNamespace(get_concepts=lambda: {}),
    )
    monkeypatch.setattr(
        ingestion_index_full,
        "get_active_collection_names",
        lambda: ("home_rag", "home_rag_summaries"),
    )
    monkeypatch.setattr(
        ingestion_index_full,
        "activate_staging_index",
        lambda collection_name, summary_collection_name: {
            "collection_name": collection_name,
            "summary_collection_name": summary_collection_name,
            "version_marker": f"{collection_name}:activated",
        },
    )
    monkeypatch.setattr(ingestion_loader.time, "time", lambda: 1234.567)
    monkeypatch.setattr(ingestion_loader.time, "perf_counter", lambda: 10.0)
    return graph_calls


def test_build_index_reindex_uses_staging_collections_without_touching_active(monkeypatch):
    fake_client = _FakeClient()
    snapshot_calls = []

    _FakeVectorStoreIndex.calls.clear()
    _FakeVectorStoreIndex.from_documents_calls.clear()
    graph_calls = _patch_common(monkeypatch, fake_client)
    monkeypatch.setattr(
        ingestion_index_full,
        "update_snapshot_after_index",
        lambda: snapshot_calls.append("called"),
    )

    ingestion.build_index(reset=False)

    assert fake_client.deleted == [
        "home_rag__staging__1234567",
        "home_rag_summaries__staging__1234567",
    ]
    assert fake_client.created == [
        "home_rag__staging__1234567",
        "home_rag_summaries__staging__1234567",
    ]
    assert "home_rag" not in fake_client.deleted
    assert "home_rag_summaries" not in fake_client.deleted
    assert snapshot_calls == ["called"]
    assert graph_calls == [1]
    assert ingestion.get_ingestion_status()["cost"]["activation_pending"] is False
    assert ingestion.get_ingestion_status()["cost"]["activated_index_state"]["version_marker"] == (
        "home_rag__staging__1234567:activated"
    )
    assert ingestion.get_ingestion_status()["cost"]["knowledge_graph_refresh"] == {
        "ok": True,
        "documents": 1,
        "concepts": 2,
        "relations": 1,
        "path": "tmp/staging",
    }


def test_build_index_skips_when_file_manifest_and_index_are_current(monkeypatch):
    fake_client = _FakeClient()
    fake_client._cols["home_rag"] = _FakeCollection("home_rag")
    snapshot_calls = []

    _patch_common(monkeypatch, fake_client)
    manifest = {
        "schema_version": 1,
        "files": {"example.md": {"size": 5, "mtime_ns": 1, "ext": ".md"}},
    }
    rs = get_retrieval_settings()
    retrieval_fp = compute_retrieval_fingerprint(
        rs.split_strategy,
        rs.chunk_size,
        rs.chunk_overlap,
        rs.window_size,
    )
    monkeypatch.setattr(
        ingestion_loader,
        "load_content_hash_state",
        lambda _chroma_dir: {
            "schema_version": 1,
            "embed_model": "text-embedding-3-small",
            "retrieval_fingerprint": retrieval_fp,
            "hashes": {"example.md": "hash"},
            "file_manifest": manifest,
            "source_fragments": 1,
            "nodes_count": 1,
        },
    )
    monkeypatch.setattr(
        ingestion_loader,
        "get_embed_model",
        lambda: (_ for _ in ()).throw(AssertionError("preflight skipped")),
    )
    monkeypatch.setattr(
        ingestion_index_full,
        "update_snapshot_after_index",
        lambda: snapshot_calls.append("called"),
    )

    ingestion.build_index(reset=False)

    assert fake_client.deleted == []
    assert fake_client.created == []
    assert snapshot_calls == []
    status = ingestion.get_ingestion_status()
    assert status["ingest_run_summary"]["run_kind"] == "noop"
    assert status["cost"]["run_type"] == "noop_reindex"


def test_build_index_reset_rebuilds_active_collections(monkeypatch):
    fake_client = _FakeClient()
    snapshot_calls = []

    _FakeVectorStoreIndex.calls.clear()
    _FakeVectorStoreIndex.from_documents_calls.clear()
    graph_calls = _patch_common(monkeypatch, fake_client)
    monkeypatch.setattr(
        ingestion_index_full,
        "update_snapshot_after_index",
        lambda: snapshot_calls.append("called"),
    )

    ingestion.build_index(reset=True)

    assert fake_client.deleted == ["home_rag", "home_rag_summaries"]
    assert fake_client.created == ["home_rag", "home_rag_summaries"]
    assert snapshot_calls == ["called"]
    assert graph_calls == [1]
    assert ingestion.get_ingestion_status()["cost"]["activation_pending"] is False
    assert ingestion.get_ingestion_status()["cost"]["activated_index_state"] is None
    assert ingestion.get_ingestion_status()["cost"]["knowledge_graph_refresh"]["ok"] is True
