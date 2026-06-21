"""US-11.1: inline-цитаты [n] в markdown ответа Q&A."""

from __future__ import annotations

from app.ui.answer_helpers import linkify_qa_inline_citations


def test_linkify_qa_inline_citations_markdown_links() -> None:
    s = "См. определение [1] и детали в [2]."
    out = linkify_qa_inline_citations(s, anchor_prefix="qa-cite")
    assert "[\\[1\\]](#qa-cite-1)" in out
    assert "[\\[2\\]](#qa-cite-2)" in out
    assert "определение" in out
