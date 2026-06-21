"""Tests for the SSR explanation tier gate (template-only vs LLM enrichment).

Covers all decision rules:
  - Simple evidence (≤2 signals, no contrastive, no debt+steering conflict) → template_only
  - Complex evidence (≥3 signals OR contrastive OR debt+steering conflict) → llm_enriched
  - Edge cases: empty ledger, all non-influencing signals, boundary at 3 signals
"""

from __future__ import annotations

from app.ssr_explanation_tier_gate import (
    TierDecision,
    decide_explanation_tier,
)

# ── Helpers ──────────────────────────────────────────────────────────────────


def _ledger(*lines: str) -> list[str]:
    """Build an evidence ledger from signal lines."""
    return list(lines)


_INFLUENCING = [
    "Очередь flashcards (локально): 5 карточек к повтору",
    "Очередь концептов SM-2 (локально): 2 к повтору",
    "Мини-quiz (tutor, локально): сигнал провала (failed)",
    "Быстрый ответ (готовность Q&A): да",
    "Слабое понятие (локально): энтропия",
]

_NON_INFLUENCING = [
    "Очередь flashcards (локально): нет срочных (0)",
    "Очередь концептов SM-2 (локально): нет срочных (0)",
    "Мини-quiz (tutor, локально): нет сохранённого статуса",
    "Быстрый ответ (готовность Q&A): нет",
    "confidence.score: 0.85 — не влияет на маршрут",
]


# ── Simple evidence → template_only ──────────────────────────────────────────


class TestSimpleEvidence:
    """≤2 influencing signals, no contrastive, no debt+steering conflict."""

    def test_zero_signals_returns_template_only(self) -> None:
        """No evidence at all → simple."""
        decision = decide_explanation_tier([])
        assert decision.tier == "template_only"
        assert decision.signal_count == 0

    def test_none_evidence_returns_template_only(self) -> None:
        """None evidence → simple."""
        decision = decide_explanation_tier(None)
        assert decision.tier == "template_only"
        assert decision.signal_count == 0

    def test_one_signal_returns_template_only(self) -> None:
        decision = decide_explanation_tier(_ledger(_INFLUENCING[0]))
        assert decision.tier == "template_only"
        assert decision.signal_count == 1

    def test_two_signals_returns_template_only(self) -> None:
        decision = decide_explanation_tier(_ledger(_INFLUENCING[0], _INFLUENCING[1]))
        assert decision.tier == "template_only"
        assert decision.signal_count == 2

    def test_only_non_influencing_signals_returns_template_only(self) -> None:
        """All signals are non-influencing → count = 0 → simple."""
        decision = decide_explanation_tier(_ledger(*_NON_INFLUENCING[:3]))
        assert decision.tier == "template_only"
        assert decision.signal_count == 0

    def test_mixed_signals_under_threshold_returns_template_only(self) -> None:
        """1 influencing + 2 non-influencing → count = 1 → simple."""
        lines = [_INFLUENCING[0]] + _NON_INFLUENCING[:2]
        decision = decide_explanation_tier(_ledger(*lines))
        assert decision.tier == "template_only"
        assert decision.signal_count == 1

    def test_has_contrastive_flag_false_returns_template_only(self) -> None:
        decision = decide_explanation_tier(
            _ledger(_INFLUENCING[0]),
            has_contrastive=False,
        )
        assert decision.tier == "template_only"

    def test_has_debt_but_no_steering_conflict_returns_template_only(self) -> None:
        """Debt label alone (without steering conflict) → simple."""
        decision = decide_explanation_tier(
            _ledger(_INFLUENCING[0]),
            has_debt_label=True,
            has_steering_conflict=False,
        )
        assert decision.tier == "template_only"

    def test_steering_conflict_but_no_debt_returns_template_only(self) -> None:
        """Steering conflict alone (without debt label) → simple."""
        decision = decide_explanation_tier(
            _ledger(_INFLUENCING[0]),
            has_debt_label=False,
            has_steering_conflict=True,
        )
        assert decision.tier == "template_only"


# ── Complex evidence → llm_enriched ──────────────────────────────────────────


class TestComplexEvidence:
    """≥3 signals OR contrastive OR debt+steering conflict."""

    def test_three_signals_returns_llm_enriched(self) -> None:
        decision = decide_explanation_tier(_ledger(*_INFLUENCING[:3]))
        assert decision.tier == "llm_enriched"
        assert decision.signal_count == 3

    def test_four_signals_returns_llm_enriched(self) -> None:
        decision = decide_explanation_tier(_ledger(*_INFLUENCING[:4]))
        assert decision.tier == "llm_enriched"
        assert decision.signal_count == 4

    def test_five_signals_returns_llm_enriched(self) -> None:
        decision = decide_explanation_tier(_ledger(*_INFLUENCING))
        assert decision.tier == "llm_enriched"
        assert decision.signal_count == 5

    def test_has_contrastive_returns_llm_enriched_even_with_few_signals(self) -> None:
        """Contrastive triggers LLM even with only 1 signal."""
        decision = decide_explanation_tier(
            _ledger(_INFLUENCING[0]),
            has_contrastive=True,
        )
        assert decision.tier == "llm_enriched"
        assert decision.signal_count == 1

    def test_debt_plus_steering_conflict_returns_llm_enriched(self) -> None:
        """Debt label + steering conflict → LLM even with 1 signal."""
        decision = decide_explanation_tier(
            _ledger(_INFLUENCING[0]),
            has_debt_label=True,
            has_steering_conflict=True,
        )
        assert decision.tier == "llm_enriched"
        assert decision.signal_count == 1

    def test_contrastive_trumps_all_returns_llm_enriched(self) -> None:
        decision = decide_explanation_tier(
            _ledger(_INFLUENCING[0]),
            has_contrastive=True,
            has_debt_label=True,
            has_steering_conflict=True,
        )
        assert decision.tier == "llm_enriched"

    def test_non_influencing_signals_dont_count_toward_threshold(self) -> None:
        """2 influencing + many non-influencing → count = 2 → still simple."""
        # This tests that non-influencing lines are excluded
        lines = _INFLUENCING[:2] + _NON_INFLUENCING
        decision = decide_explanation_tier(_ledger(*lines))
        assert decision.tier == "template_only"  # only 2 influencing signals
        assert decision.signal_count == 2


# ── TierDecision dataclass ───────────────────────────────────────────────────


class TestTierDecision:
    def test_reason_is_not_empty(self) -> None:
        decision = decide_explanation_tier(None)
        assert len(decision.reason) > 10

    def test_signal_count_is_always_int(self) -> None:
        decision = decide_explanation_tier(_ledger(_INFLUENCING[0]))
        assert isinstance(decision.signal_count, int)
        assert decision.signal_count >= 0

    def test_dataclass_is_frozen(self) -> None:
        decision = TierDecision(tier="template_only", reason="test", signal_count=0)
        try:
            decision.tier = "llm_enriched"  # type: ignore[misc]
            assert False, "should be frozen"
        except (AttributeError, TypeError):
            pass

    def test_repr_is_readable(self) -> None:
        decision = decide_explanation_tier(None)
        r = repr(decision)
        assert "TierDecision" in r
        assert "template_only" in r or "llm_enriched" in r


# ── Integration: hint_kind / primary_nav passthrough ─────────────────────────


class TestParamPassthrough:
    """hint_kind and primary_nav are currently used only for debug logging.

    This test ensures the function accepts them without error so they are
    ready for future use in profiling or traces.
    """

    def test_hint_kind_passthrough(self) -> None:
        decision = decide_explanation_tier(
            _ledger(_INFLUENCING[0]),
            hint_kind="cards_due",
            primary_nav="flashcards_review",
        )
        assert decision.tier == "template_only"

    def test_all_optional_params_accepted(self) -> None:
        decision = decide_explanation_tier(
            _ledger(*_INFLUENCING[:3]),
            hint_kind="quiz_failed",
            primary_nav="quiz_recovery_tutor",
            has_contrastive=False,
            has_steering_conflict=True,
            has_debt_label=True,
        )
        assert decision.tier == "llm_enriched"


# ── Realistic scenario tests ─────────────────────────────────────────────────


class TestRealisticScenarios:
    """Approximate real SSR card scenarios with evidence ledger lines."""

    def test_cards_due_simple(self) -> None:
        """Cards due with no other signals → template only."""
        lines = ["Очередь flashcards (локально): 5 карточек к повтору"]
        decision = decide_explanation_tier(
            _ledger(*lines),
            hint_kind="cards_due",
            has_contrastive=False,
            has_debt_label=False,
        )
        assert decision.tier == "template_only"

    def test_quiz_failed_with_debt_and_signals(self) -> None:
        """Quiz failed with multiple signals → LLM enriched."""
        lines = [
            "Очередь flashcards (локально): 3 карточек к повтору",
            "Очередь концептов SM-2 (локально): 1 к повтору",
            "Мини-quiz (tutor, локально): сигнал провала (failed)",
            "Слабое понятие (локально): энтропия",
        ]
        decision = decide_explanation_tier(
            _ledger(*lines),
            hint_kind="quiz_failed",
            has_debt_label=True,
        )
        # 4 signals (all influencing) → llm_enriched
        assert decision.tier == "llm_enriched"
        assert decision.signal_count == 4

    def test_answer_ready_simple(self) -> None:
        """Answer ready with only Q&A signal → template only."""
        lines = [
            "Быстрый ответ (готовность Q&A): да",
            "Очередь flashcards (локально): нет срочных (0)",
            "Очередь концептов SM-2 (локально): нет срочных (0)",
        ]
        decision = decide_explanation_tier(
            _ledger(*lines),
            hint_kind="answer_ready",
            has_contrastive=False,
        )
        # Only Q&A is influencing (flashcards and SM-2 are non-influencing) → 1 signal → template
        assert decision.tier == "template_only"
        assert decision.signal_count == 1

    def test_complex_mastery_stale_with_contrastive(self) -> None:
        """Mastery stale + contrastive plus multiple signals → LLM."""
        lines = [
            "Слабое понятие (локально): энтропия",
            "Быстрый ответ (готовность Q&A): да",
            "confidence.score: 0.55 — уровень low, не влияет на маршрут",
        ]
        decision = decide_explanation_tier(
            _ledger(*lines),
            hint_kind="mastery_stale",
            has_contrastive=True,
            has_debt_label=True,
        )
        # 2 influencing + has_contrastive → llm_enriched
        assert decision.tier == "llm_enriched"
        assert decision.signal_count == 2

    def test_safe_default_empty_ledger(self) -> None:
        """Safe default with no signals → template only."""
        decision = decide_explanation_tier(
            None,
            hint_kind="safe_default",
            has_contrastive=False,
        )
        assert decision.tier == "template_only"
        assert decision.signal_count == 0
