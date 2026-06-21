"""Регрессия: overview/synthesis → doc_then_chunk (итерация 14)."""

from app.pipeline_steps import _STRATEGY_BY_TYPE


def test_overview_synthesis_use_doc_then_chunk():
    assert _STRATEGY_BY_TYPE["overview"] == "doc_then_chunk"
    assert _STRATEGY_BY_TYPE["synthesis"] == "doc_then_chunk"


def test_keyword_uses_bm25_only():
    assert _STRATEGY_BY_TYPE["keyword"] == "bm25_only"
