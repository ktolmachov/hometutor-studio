"""Регрессия: SentenceSplitter metadata-aware не должен видеть огромный metadata_str (summary / чанки)."""

from llama_index.core import Document

import app.ingestion as ingestion


def test_enrich_documents_when_enrichment_returns_none(monkeypatch):
    """LLM enrichment может вернуть None — не обращаться к enrichment.key_concepts без проверки."""

    class _Cost:
        token_usage = {"prompt_tokens": 1, "completion_tokens": 0, "total_tokens": 1}
        estimated_cost_usd = 0.0

    monkeypatch.setattr(
        ingestion,
        "enrich_document_metadata_with_cost",
        lambda _text: (None, _Cost()),
    )
    monkeypatch.setattr(
        ingestion,
        "build_document_summary_with_cost",
        lambda _text: (None, None),
    )

    class _Settings:
        enable_metadata_enrichment = True
        enable_document_summaries = False

    monkeypatch.setattr(ingestion, "get_settings", lambda: _Settings())

    docs = [
        Document(
            text="hello world",
            metadata={"doc_id": "data/f.txt", "file_path": "C:/data/f.txt"},
        )
    ]
    enriched, summaries, stats = ingestion._enrich_documents(docs)
    assert len(enriched) == 1
    assert summaries == []
    assert stats["metadata_enrichment_calls"] == 1
    assert stats["metadata_enrichment_successes"] == 0


def test_slim_metadata_for_summary_omits_file_path_and_truncates():
    base = {
        "doc_id": "course/a.md",
        "relative_path": "course/a.md",
        "file_name": "a.md",
        "file_path": "/very/long/abs/path/" * 80,
        "topic": "x" * 600,
        "section_path": "should not appear",
    }
    slim = ingestion._slim_metadata_for_summary(base)
    assert "file_path" not in slim
    assert "section_path" not in slim
    assert slim["node_type"] == "document_summary"
    assert len(slim["topic"]) <= 500
    assert slim["topic"].endswith("...")


def test_normalize_page_range_string_single_and_range():
    assert ingestion.normalize_page_range_string(None) is None
    assert ingestion.normalize_page_range_string("") is None
    assert ingestion.normalize_page_range_string(3) == "3-3"
    assert ingestion.normalize_page_range_string(" 7 ") == "7-7"
    assert ingestion.normalize_page_range_string("10-12") == "10-12"
    assert ingestion.normalize_page_range_string("12-10") == "10-12"


def test_aggregate_page_range_for_doc_group():
    assert ingestion.aggregate_page_range_for_doc_group([1, 2, 3]) == "1-3"
    assert ingestion.aggregate_page_range_for_doc_group([None, "5"]) == "5-5"
    assert ingestion.aggregate_page_range_for_doc_group([]) is None


def test_add_metadata_sets_page_range_from_page_label(tmp_path, monkeypatch):
    monkeypatch.setattr(ingestion, "DATA_DIR", tmp_path)
    p = tmp_path / "a.pdf"
    p.write_bytes(b"x")
    from llama_index.core import Document

    docs = [
        Document(
            text="t",
            metadata={"file_path": str(p), "page_label": "4"},
        )
    ]
    out = ingestion._add_metadata(docs)
    assert out[0].metadata.get("page_range") == "4-4"


def test_configure_document_excludes_original_text_from_metadata_str():
    doc = Document(
        text="hello",
        metadata={"original_text": "x" * 5000, "relative_path": "n/a", "topic": "t"},
    )
    ingestion._configure_document_for_metadata_aware_split(doc)
    assert "original_text" in doc.metadata
    assert "original_text" in doc.excluded_embed_metadata_keys
    assert "window" in doc.excluded_embed_metadata_keys


def test_apply_contextualized_chunks_does_not_store_full_doc_as_original_text():
    """Regression: original_text must NOT be the full source document stored at the
    document level.  Storing it there caused every chunk to inherit ~91 KB, bloating
    ChromaDB _node_content from ~3 KB to ~93 KB per node (21 GB for 2 docs).

    After the fix, _apply_contextualized_chunks must not set original_text at all;
    per-chunk assignment happens later in _build_nodes.
    """
    big_text = "word " * 20_000  # ~100 KB — simulates a real source document
    doc = Document(
        text=big_text,
        metadata={"title": "Big Doc", "file_name": "big.txt", "section_path": "intro"},
    )
    [ctx_doc] = ingestion._apply_contextualized_chunks([doc])

    # The contextualized document must NOT carry original_text in metadata.
    assert "original_text" not in ctx_doc.metadata, (
        "original_text must not be stored at document level — it would be inherited "
        "by every chunk, bloating ChromaDB node content."
    )


def test_sentence_splitter_nodes_have_per_chunk_original_text(monkeypatch):
    """After _build_nodes with sentence_splitter, every node's original_text must be
    bounded to its own chunk size, not the full source document.

    Threshold: original_text length must be < 2× chunk_size (1024 chars).
    """
    from unittest.mock import patch

    from app.ingestion_index_nodes import _build_nodes

    class _FakeRetrieval:
        split_strategy = "sentence_splitter"
        chunk_size = 512
        chunk_overlap = 64
        window_size = 3

    chunk_size_chars = _FakeRetrieval.chunk_size * 4  # generous upper bound (chars, not tokens)

    big_text = " ".join(f"Sentence {i} about topic X is here." for i in range(300))
    doc = Document(
        text=big_text,
        metadata={"title": "Test", "file_name": "t.txt", "section_path": "s"},
    )
    [ctx_doc] = ingestion._apply_contextualized_chunks([doc])
    ingestion._configure_document_for_metadata_aware_split(ctx_doc)

    with patch("app.ingestion_index_nodes.get_retrieval_settings", return_value=_FakeRetrieval()):
        nodes = _build_nodes([ctx_doc])

    assert len(nodes) > 1, "expected document to split into multiple nodes"

    for i, node in enumerate(nodes):
        orig = node.metadata.get("original_text", "")
        assert orig, f"node[{i}] missing original_text"
        assert len(orig) <= chunk_size_chars, (
            f"node[{i}] original_text is {len(orig)} chars — "
            f"exceeds {chunk_size_chars} (2× chunk_size). "
            "Full document is being stored instead of the chunk's own text."
        )


def test_sentence_window_nodes_have_per_sentence_original_text(monkeypatch):
    """Regression: with sentence_window strategy, SentenceWindowNodeParser sets
    node.metadata['original_text'] to each sentence via original_text_metadata_key.
    After removing the document-level original_text assignment, every node must still
    receive its own small original_text (the sentence, not the full document).

    Threshold: original_text must be shorter than the full document text.
    """
    from unittest.mock import patch

    from app.ingestion_index_nodes import _build_nodes

    class _FakeRetrieval:
        split_strategy = "sentence_window"
        window_size = 2
        chunk_size = 512
        chunk_overlap = 64

    big_text = " ".join(f"Sentence {i} about topic X is here." for i in range(200))
    doc = Document(
        text=big_text,
        metadata={"title": "Test", "file_name": "t.txt", "section_path": "s"},
    )
    [ctx_doc] = ingestion._apply_contextualized_chunks([doc])
    ingestion._configure_document_for_metadata_aware_split(ctx_doc)
    full_ctx_len = len(ctx_doc.text)

    with patch("app.ingestion_index_nodes.get_retrieval_settings", return_value=_FakeRetrieval()):
        nodes = _build_nodes([ctx_doc])

    assert len(nodes) > 1, "expected document to split into multiple nodes"

    for i, node in enumerate(nodes):
        orig = node.metadata.get("original_text", "")
        assert orig, f"node[{i}] missing original_text (sentence_window must set it via original_text_metadata_key)"
        assert len(orig) < full_ctx_len, (
            f"node[{i}] original_text length {len(orig)} equals the full contextualized document "
            f"({full_ctx_len} chars). The full document is being stored instead of the sentence."
        )
