"""Retrieval-stage embedding cost estimates (heuristic tokens)."""

from app.usage_cost import estimate_retrieval_embedding_usage


def test_retrieval_estimate_empty_queries_returns_none():
    usage, cost = estimate_retrieval_embedding_usage([], embed_model="text-embedding-3-small")
    assert usage is None
    assert cost is None


def test_retrieval_estimate_single_query():
    usage, cost = estimate_retrieval_embedding_usage(
        ["short query"],
        embed_model="text-embedding-3-small",
    )
    assert usage is not None
    assert usage["prompt_tokens"] == max(1, len("short query") // 4)
    assert usage["completion_tokens"] == 0
    assert cost is not None
    assert cost > 0


def test_retrieval_estimate_dedupes_queries():
    usage, cost = estimate_retrieval_embedding_usage(
        ["hello world", "hello world", "other"],
        embed_model="text-embedding-3-small",
    )
    assert usage is not None
    # "hello world" (11 chars) -> max(1, 11//4)=2; "other" (5 chars) -> 1 => 3 prompt tokens
    assert usage["prompt_tokens"] == 3
    assert usage["completion_tokens"] == 0
    assert cost is not None
    assert cost > 0
