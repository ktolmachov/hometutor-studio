from unittest.mock import MagicMock

from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters

from app.retrieval import DocThenChunkRetriever, _merge_filters


def _node(text: str, metadata: dict | None = None) -> NodeWithScore:
    return NodeWithScore(
        node=TextNode(text=text, metadata=metadata or {}),
        score=1.0,
    )


def test_merge_filters_appends_extra_filters():
    base = MetadataFilters(filters=[MetadataFilter(key="topic", value="security")])
    extra = [MetadataFilter(key="folder", value="lectures/security")]

    merged = _merge_filters(base, extra)

    assert merged is not None
    assert len(merged.filters) == 2
    assert merged.filters[0].key == "topic"
    assert merged.filters[1].key == "folder"


def test_merge_filters_creates_new_when_base_is_none():
    merged = _merge_filters(None, [MetadataFilter(key="file", value="a.md")])

    assert merged is not None
    assert len(merged.filters) == 1
    assert merged.filters[0].key == "file"


def test_doc_then_chunk_retriever_returns_only_chunks_from_matched_docs():
    # Summary index: два документа с разными doc_id
    summary_index = MagicMock()
    summary_retriever = MagicMock()
    summary_index.as_retriever.return_value = summary_retriever
    summary_retriever.retrieve.return_value = [
        _node("summary-1", {"doc_id": "doc-1"}),
        _node("summary-2", {"doc_id": "doc-2"}),
    ]

    # Base index: вернём разные чанки в зависимости от doc_id в фильтре
    base_index = MagicMock()

    def _as_retriever(similarity_top_k: int, filters: MetadataFilters | None = None):
        assert similarity_top_k == 3
        assert filters is not None
        # Находим doc_id в фильтрах
        doc_filter = next(f for f in filters.filters if f.key == "doc_id")
        if doc_filter.value == "doc-1":
            return MagicMock(
                retrieve=lambda q: [
                    _node("chunk-1a", {"doc_id": "doc-1"}),
                    _node("chunk-1b", {"doc_id": "doc-1"}),
                ]
            )
        if doc_filter.value == "doc-2":
            return MagicMock(
                retrieve=lambda q: [
                    _node("chunk-2a", {"doc_id": "doc-2"}),
                ]
            )
        return MagicMock(retrieve=lambda q: [])

    base_index.as_retriever.side_effect = _as_retriever

    retriever = DocThenChunkRetriever(
        summary_index=summary_index,
        base_index=base_index,
        similarity_top_k=3,
        doc_top_k=2,
        base_filters=None,
    )

    result = retriever.retrieve(QueryBundle("test question"))

    texts = [item.node.text for item in result]
    assert texts == ["chunk-1a", "chunk-1b", "chunk-2a"]
    # Все чанки должны иметь doc_id из множества выбранных документов
    assert {item.node.metadata.get("doc_id") for item in result} == {"doc-1", "doc-2"}


def test_doc_then_chunk_retriever_returns_empty_when_no_doc_ids():
    summary_index = MagicMock()
    summary_retriever = MagicMock()
    summary_index.as_retriever.return_value = summary_retriever
    # Нет doc_id в метаданных summary
    summary_retriever.retrieve.return_value = [
        _node("summary-without-id", {}),
    ]

    base_index = MagicMock()

    retriever = DocThenChunkRetriever(
        summary_index=summary_index,
        base_index=base_index,
        similarity_top_k=3,
        doc_top_k=1,
        base_filters=None,
    )

    result = retriever.retrieve(QueryBundle("test question"))

    assert result == []


def test_doc_then_chunk_retriever_falls_back_to_relative_path_when_doc_id_filter_returns_no_chunks():
    summary_index = MagicMock()
    summary_retriever = MagicMock()
    summary_index.as_retriever.return_value = summary_retriever
    summary_retriever.retrieve.return_value = [
        _node(
            "summary-1",
            {
                "doc_id": "doc-1",
                "relative_path": "docs/ai_agents/lecture_1.html",
            },
        ),
    ]

    base_index = MagicMock()

    def _as_retriever(similarity_top_k: int, filters: MetadataFilters | None = None):
        assert similarity_top_k == 3
        assert filters is not None
        doc_filter = next((f for f in filters.filters if f.key == "doc_id"), None)
        path_filter = next((f for f in filters.filters if f.key == "relative_path"), None)

        if doc_filter and doc_filter.value == "doc-1":
            return MagicMock(retrieve=lambda q: [])
        if path_filter and path_filter.value == "docs/ai_agents/lecture_1.html":
            return MagicMock(
                retrieve=lambda q: [
                    _node(
                        "chunk-from-path",
                        {
                            "doc_id": "doc-1",
                            "relative_path": "docs/ai_agents/lecture_1.html",
                        },
                    ),
                ]
            )
        return MagicMock(retrieve=lambda q: [])

    base_index.as_retriever.side_effect = _as_retriever

    retriever = DocThenChunkRetriever(
        summary_index=summary_index,
        base_index=base_index,
        similarity_top_k=3,
        doc_top_k=1,
        base_filters=None,
    )

    result = retriever.retrieve(QueryBundle("test question"))

    assert [item.node.text for item in result] == ["chunk-from-path"]

