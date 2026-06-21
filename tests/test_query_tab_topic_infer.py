"""US-4.1: тема для CTA «Учить эту тему» из последнего ответа Q&A."""
from __future__ import annotations

from app.ui.query_tab import _infer_topic_label_from_last_answer, _summarize_answer_for_handoff


def test_infer_topic_from_source_metadata():
    last = {
        "question": "что?",
        "sources": [{"metadata": {"topic": "Hybrid retrieval"}}],
    }
    assert _infer_topic_label_from_last_answer(last) == "Hybrid retrieval"


def test_infer_topic_from_file_stem():
    last = {"question": "x", "sources": [{"file_name": "docs/my-topic_note.md"}]}
    assert "my topic note" in _infer_topic_label_from_last_answer(last).lower()


def test_infer_topic_falls_back_to_question():
    last = {"question": "Объясни квантовую запутанность простыми словами", "sources": []}
    out = _infer_topic_label_from_last_answer(last)
    assert len(out) >= 8


def test_handoff_summary_compacts_long_answer():
    last = {"answer": "x" * 400}
    out = _summarize_answer_for_handoff(last)
    assert len(out) <= 280
    assert out.endswith("…")
