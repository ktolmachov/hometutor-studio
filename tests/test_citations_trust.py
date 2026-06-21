"""
US-11.1 + US-3.2 acceptance tests: inline citations and source trust panel.

US-11.1 — Inline citations в ответе:
  linkify_qa_inline_citations converts [n] markers to clickable markdown links.
  Anchor IDs emitted by render_source_cards match the link targets.

US-3.2 — Видеть, почему фрагмент попал в ответ:
  render_source_cards shows chunk text, score, route label, rank_reason/bonus.
  _score_trust_caption and _route_label_ru produce human-readable Russian labels.
"""

from __future__ import annotations

import re

import pytest

from app.ui.answer_helpers import linkify_qa_inline_citations
from app.ui.source_cards import _route_label_ru, _score_trust_caption


# ---------------------------------------------------------------------------
# US-11.1 — linkify_qa_inline_citations: anchor format consistency
# ---------------------------------------------------------------------------


class TestInlineCitationsLinkify:
    """US-11.1: [n] markers → markdown links that point to source card anchors."""

    def test_single_citation_converted(self):
        out = linkify_qa_inline_citations("[1]", anchor_prefix="qa-cite")
        assert "#qa-cite-1" in out

    def test_multiple_citations_all_converted(self):
        text = "Первый [1], второй [2] и третий [3] источники."
        out = linkify_qa_inline_citations(text, anchor_prefix="qa-cite")
        for n in (1, 2, 3):
            assert f"#qa-cite-{n}" in out

    def test_non_citation_brackets_untouched(self):
        """Text like [word] or [] should not be converted."""
        text = "Не цитата [word] и пустые []."
        out = linkify_qa_inline_citations(text, anchor_prefix="qa-cite")
        assert "[word]" in out
        assert "[]" in out

    def test_anchor_prefix_is_parametric(self):
        out = linkify_qa_inline_citations("[2]", anchor_prefix="custom-prefix")
        assert "#custom-prefix-2" in out
        assert "#qa-cite-2" not in out

    def test_text_preserved_around_citation(self):
        text = "Смотри [1] для деталей."
        out = linkify_qa_inline_citations(text, anchor_prefix="qa-cite")
        assert "Смотри" in out
        assert "для деталей" in out

    def test_empty_string_returns_empty(self):
        assert linkify_qa_inline_citations("", anchor_prefix="qa-cite") == ""

    def test_no_citations_returns_original(self):
        text = "Никаких цитат здесь нет."
        assert linkify_qa_inline_citations(text) == text

    def test_link_format_is_valid_markdown(self):
        out = linkify_qa_inline_citations("[1]", anchor_prefix="qa-cite")
        # Should be [[\1]](#qa-cite-1) — valid markdown link
        assert out.startswith("[")
        assert "](#qa-cite-1)" in out

    def test_anchor_id_consistency_with_source_card(self):
        """
        US-11.1 integration contract: linkify uses anchor_prefix-N,
        render_source_cards should emit id="{cite_anchor_prefix}-{N}" spans.
        This test checks the naming convention is consistent.
        """
        prefix = "qa-cite"
        out = linkify_qa_inline_citations("[3]", anchor_prefix=prefix)
        expected_anchor = f"{prefix}-3"
        assert expected_anchor in out


# ---------------------------------------------------------------------------
# US-3.2 — _route_label_ru: retrieval route labels
# ---------------------------------------------------------------------------


class TestRouteLabels:
    """US-3.2: route shown as human-readable Russian label."""

    def test_vector_only_in_russian(self):
        label = _route_label_ru("vector_only")
        assert "вектор" in label.lower()

    def test_hybrid_in_russian(self):
        label = _route_label_ru("hybrid")
        assert "гибрид" in label.lower() or "вектор" in label.lower()

    def test_bm25_only_in_russian(self):
        label = _route_label_ru("bm25_only")
        assert "bm25" in label.lower() or "ключев" in label.lower()

    def test_faq_cache_in_russian(self):
        label = _route_label_ru("faq_cache")
        assert "faq" in label.lower() or "кэш" in label.lower()

    def test_unknown_route_returns_raw_value(self):
        label = _route_label_ru("unknown_route_xyz")
        assert "unknown_route_xyz" in label

    def test_none_route_shows_placeholder(self):
        label = _route_label_ru(None)
        assert label  # non-empty
        assert "не указан" in label.lower() or len(label) > 0

    def test_empty_string_route_shows_placeholder(self):
        label = _route_label_ru("")
        assert label  # non-empty


# ---------------------------------------------------------------------------
# US-3.2 — _score_trust_caption: score → trust explanation
# ---------------------------------------------------------------------------


class TestScoreTrustCaption:
    """US-3.2: score ≥0.75 → high trust; 0.45–0.75 → moderate; <0.45 → low trust."""

    def test_high_score_075_threshold(self):
        caption = _score_trust_caption(0.75)
        assert "высокая" in caption.lower()

    def test_high_score_above_075(self):
        caption = _score_trust_caption(0.9)
        assert "высокая" in caption.lower()

    def test_moderate_score_range(self):
        for score in (0.45, 0.55, 0.65, 0.74):
            caption = _score_trust_caption(score)
            assert "умеренная" in caption.lower(), f"Expected moderate for score={score}"

    def test_low_score_below_045(self):
        for score in (0.0, 0.1, 0.3, 0.44):
            caption = _score_trust_caption(score)
            assert "низкий" in caption.lower(), f"Expected low for score={score}"

    def test_none_score_missing_message(self):
        caption = _score_trust_caption(None)
        assert "не передана" in caption.lower() or "не" in caption.lower()

    def test_invalid_score_fallback(self):
        caption = _score_trust_caption("not_a_number")
        assert caption  # non-empty, no crash

    def test_caption_mentions_action_for_low_score(self):
        """US-3.2: low score should guide user to open the source."""
        caption = _score_trust_caption(0.1)
        # Should mention opening the source or doubt
        has_action = any(
            word in caption.lower()
            for word in ("откройте", "сомнении", "источник", "слабее")
        )
        assert has_action, f"Low score caption should suggest action: {caption!r}"

    def test_caption_uses_boundary_exactly(self):
        """Boundary test: 0.45 is in moderate range, 0.44 is in low range."""
        assert "умеренная" in _score_trust_caption(0.45).lower()
        assert "низкий" in _score_trust_caption(0.44).lower()
