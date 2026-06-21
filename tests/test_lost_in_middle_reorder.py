"""Tests for lost-in-the-middle context reorder."""

from types import SimpleNamespace

from app.config import RetrievalSettings
from app.lost_in_middle_reorder import (
    LostInMiddleReorderPostprocessor,
    append_lost_in_middle_reorder_postprocessor,
    reorder_nodes_lost_in_middle,
)


def _node(label: str, score: float = 0.0):
    return SimpleNamespace(node=SimpleNamespace(text=label), score=score)


def test_reorder_nodes_lost_in_middle_sandwiches_ranked_list():
    nodes = [_node(f"n{i}", score=1.0 - i * 0.1) for i in range(6)]
    ordered = reorder_nodes_lost_in_middle(nodes)
    assert [n.node.text for n in ordered] == ["n0", "n5", "n1", "n4", "n2", "n3"]


def test_reorder_nodes_lost_in_middle_short_lists_unchanged():
    one = [_node("only")]
    two = [_node("a"), _node("b")]
    assert reorder_nodes_lost_in_middle(one) == one
    assert reorder_nodes_lost_in_middle(two) == two


def test_reorder_nodes_lost_in_middle_preserves_members():
    nodes = [_node(f"x{i}") for i in range(4)]
    ordered = reorder_nodes_lost_in_middle(nodes)
    assert len(ordered) == len(nodes)
    assert {n.node.text for n in ordered} == {n.node.text for n in nodes}


def test_lost_in_middle_postprocessor_delegates_to_helper():
    nodes = [_node("a"), _node("b"), _node("c"), _node("d")]
    pp = LostInMiddleReorderPostprocessor()
    out = pp.postprocess_nodes(nodes, query_bundle=None)
    assert [n.node.text for n in out] == ["a", "d", "b", "c"]


def test_append_lost_in_middle_reorder_respects_setting(monkeypatch):
    monkeypatch.setattr(
        "app.config.get_retrieval_settings",
        lambda: RetrievalSettings(enable_lost_in_middle_reorder=True),
    )
    with_pp = append_lost_in_middle_reorder_postprocessor([])
    assert len(with_pp) == 1
    assert isinstance(with_pp[0], LostInMiddleReorderPostprocessor)

    monkeypatch.setattr(
        "app.config.get_retrieval_settings",
        lambda: RetrievalSettings(enable_lost_in_middle_reorder=False),
    )
    without_pp = append_lost_in_middle_reorder_postprocessor([])
    assert without_pp == []


def test_build_query_engine_appends_lost_in_middle_postprocessor(monkeypatch):
    import app.retrieval as retrieval
    from app.models import QueryOptions

    captured: dict[str, list] = {}

    def fake_append_graph(postprocessors, **kwargs):
        captured["graph_called"] = True
        return postprocessors + ["graph_pp"]

    def fake_append_lim(postprocessors):
        captured["lim_input"] = list(postprocessors)
        return postprocessors + [LostInMiddleReorderPostprocessor()]

    monkeypatch.setattr(retrieval, "append_graph_expansion_postprocessor", fake_append_graph)
    monkeypatch.setattr(retrieval, "append_lost_in_middle_reorder_postprocessor", fake_append_lim)
    monkeypatch.setattr(retrieval, "build_postprocessors", lambda params: ["base_pp"])
    monkeypatch.setattr(retrieval, "get_query_engine_cache_result", lambda key: {"engine": None, "cache_latency_ms": 0.0})
    monkeypatch.setattr(
        retrieval,
        "get_base_services",
        lambda: {"index": object(), "llm": object(), "collection": object(), "summary_index": None},
    )
    monkeypatch.setattr(
        retrieval,
        "build_query_engine_for_retrieval_mode",
        lambda **kwargs: captured.setdefault("node_postprocessors", kwargs["postprocessors"]) or object(),
    )
    monkeypatch.setattr(
        retrieval,
        "resolve_query_execution_plan",
        lambda *a, **k: SimpleNamespace(
            to_pipeline_params=lambda: {},
            query_type="qa",
            profile="quality",
            retrieval_mode="vector_only",
            similarity_top_k=4,
            enable_reranker=False,
            rerank_top_n=4,
            rerank_model="test",
            split_strategy="sentence_splitter",
            query_engine_cache_policy="shared",
            prompt_key="qa",
        ),
    )
    monkeypatch.setattr(
        retrieval,
        "get_settings",
        lambda: SimpleNamespace(
            enable_tutor_inline_quiz=False,
            tutor_inline_quiz_separate_llm_call=False,
            enable_tutor_pedagogical_orchestrator=False,
            enable_graph_augmented_retrieval=False,
            graph_augment_max_extra_docs=0,
        ),
    )

    retrieval.build_query_engine("test question", QueryOptions())

    assert captured.get("graph_called") is True
    assert captured["lim_input"] == ["base_pp", "graph_pp"]
    assert isinstance(captured["node_postprocessors"][-1], LostInMiddleReorderPostprocessor)
