"""US-3.3: стартовые вопросы hero из KB overview (без Streamlit)."""
from __future__ import annotations

from app.ui.hero import suggest_example_questions


def test_suggest_empty_when_no_documents():
    assert (
        suggest_example_questions(
            documents_count=0,
            top_concepts=[{"name": "X"}],
            topic_sizes=[],
        )
        == []
    )


def test_suggest_from_concepts_and_topics():
    qs = suggest_example_questions(
        documents_count=3,
        top_concepts=[{"name": "RAG"}, {"name": "Graph"}],
        topic_sizes=[{"topic_name": "Security"}],
    )
    assert len(qs) == 3
    assert any("RAG" in q for q in qs)
    assert any("Graph" in q for q in qs)
    assert any("Security" in q for q in qs)


def test_suggest_falls_back_to_templates():
    qs = suggest_example_questions(documents_count=1, top_concepts=[], topic_sizes=[])
    assert len(qs) == 3
    assert all(len(x) > 10 for x in qs)
