from unittest.mock import MagicMock

from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode

from app.hybrid_retrieval import (
    ParallelHybridRetriever,
    _fuse_with_reciprocal_rank,
    _nodes_from_chroma,
    build_hybrid_retriever,
    get_bm25_retriever,
    invalidate_bm25_cache,
    warm_bm25_cache_if_configured,
)


def _make_fake_collection(texts=None, ids=None, metadatas=None):
    if texts is None:
        texts = ["First document text", "Second document text", "Third document text"]
    if ids is None:
        ids = [f"id_{i}" for i in range(len(texts))]
    if metadatas is None:
        metadatas = [{"file_name": f"doc{i}.txt"} for i in range(len(texts))]

    collection = MagicMock()
    # _nodes_from_chroma calls collection.count() for the size/byte guards; a real int is
    # required (a bare MagicMock breaks the `total > _BM25_MAX_NODES` comparison).
    collection.count.return_value = len(ids)
    collection.get.return_value = {
        "ids": ids,
        "documents": texts,
        "metadatas": metadatas,
    }
    return collection


def _node(node_id: str, score: float = 1.0) -> NodeWithScore:
    return NodeWithScore(node=TextNode(text=f"text-{node_id}", id_=node_id), score=score)


def test_nodes_from_chroma_converts_to_text_nodes():
    collection = _make_fake_collection()
    nodes = _nodes_from_chroma(collection)

    assert len(nodes) == 3
    assert all(isinstance(n, TextNode) for n in nodes)
    assert nodes[0].text == "First document text"
    assert nodes[0].id_ == "id_0"
    assert nodes[0].metadata["file_name"] == "doc0.txt"


def test_nodes_from_chroma_skips_empty_texts():
    collection = _make_fake_collection(
        texts=["Some text", "", "More text"],
        ids=["a", "b", "c"],
        metadatas=[{}, {}, {}],
    )
    nodes = _nodes_from_chroma(collection)

    assert len(nodes) == 2
    assert nodes[0].text == "Some text"
    assert nodes[1].text == "More text"


def test_get_bm25_retriever_caches_instance(monkeypatch):
    # Без патча при наличии bm25 на диске путь загрузки обходит collection.get —
    # тест должен воспроизводиться одинаково в CI и локально.
    monkeypatch.setattr(
        "app.hybrid_retrieval._load_bm25_from_disk",
        lambda _top_k: None,
    )
    invalidate_bm25_cache()
    collection = _make_fake_collection()

    r1 = get_bm25_retriever(collection, similarity_top_k=2)
    r2 = get_bm25_retriever(collection, similarity_top_k=2)

    assert r1 is r2
    collection.get.assert_called_once()


def test_get_bm25_retriever_rebuilds_on_different_top_k():
    invalidate_bm25_cache()
    collection = _make_fake_collection()

    r1 = get_bm25_retriever(collection, similarity_top_k=2)
    r2 = get_bm25_retriever(collection, similarity_top_k=5)

    assert r1 is not r2


def test_invalidate_bm25_cache_forces_rebuild():
    invalidate_bm25_cache()
    collection = _make_fake_collection()

    r1 = get_bm25_retriever(collection, similarity_top_k=2)
    invalidate_bm25_cache()
    r2 = get_bm25_retriever(collection, similarity_top_k=2)

    assert r1 is not r2


def test_fuse_with_reciprocal_rank_merges_and_orders_results():
    fused = _fuse_with_reciprocal_rank(
        [
            [_node("shared"), _node("bm25-only")],
            [_node("vector-only"), _node("shared")],
        ],
        similarity_top_k=3,
    )

    assert [item.node.node_id for item in fused] == ["shared", "vector-only", "bm25-only"]


def test_parallel_hybrid_retriever_runs_both_retrievers_and_fuses():
    bm25_retriever = MagicMock()
    vector_retriever = MagicMock()
    bm25_retriever.retrieve.return_value = [_node("shared"), _node("bm25-only")]
    vector_retriever.retrieve.return_value = [_node("vector-only"), _node("shared")]

    retriever = ParallelHybridRetriever(
        bm25_retriever=bm25_retriever,
        vector_retriever=vector_retriever,
        similarity_top_k=3,
    )

    result = retriever.retrieve(QueryBundle("test"))

    assert [item.node.node_id for item in result] == ["shared", "vector-only", "bm25-only"]
    bm25_retriever.retrieve.assert_called_once()
    vector_retriever.retrieve.assert_called_once()


def test_warm_bm25_cache_skips_vector_only(monkeypatch):
    called: list[bool] = []

    def _fake_get_bm25(*_a, **_k):
        called.append(True)
        return MagicMock()

    monkeypatch.setattr("app.hybrid_retrieval.get_bm25_retriever", _fake_get_bm25)
    warm_bm25_cache_if_configured(MagicMock(), "vector_only", 4)
    assert called == []


def test_warm_bm25_cache_invokes_for_hybrid(monkeypatch):
    calls: list[tuple] = []

    def _fake_get_bm25(collection, top_k, filters=None):
        calls.append((collection, top_k, filters))
        return MagicMock()

    monkeypatch.setattr("app.hybrid_retrieval.get_bm25_retriever", _fake_get_bm25)
    coll = MagicMock()
    warm_bm25_cache_if_configured(coll, "hybrid", 4)
    assert calls == [(coll, 4, None)]


def test_build_hybrid_retriever_returns_parallel_retriever():
    invalidate_bm25_cache()
    collection = _make_fake_collection()

    fake_index = MagicMock()
    fake_vector_retriever = MagicMock()
    fake_index.as_retriever.return_value = fake_vector_retriever

    retriever = build_hybrid_retriever(
        index=fake_index,
        collection=collection,
        similarity_top_k=2,
        filters=None,
    )

    assert isinstance(retriever, ParallelHybridRetriever)
    fake_index.as_retriever.assert_called_once_with(
        similarity_top_k=2, filters=None
    )
