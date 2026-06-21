"""stream_ssr_explanation: token generator with cache, fallback and circuit-breaker paths."""

from __future__ import annotations

import pytest

from app import llm_local_circuit
from app.smart_study_router import build_smart_study_recommendation
from app.ui.adaptive_plan_llm_enrichment import (
    _SSR_LLM_EXPLANATION_CACHE,
    stream_ssr_explanation,
)


@pytest.fixture(autouse=True)
def _clean_state():
    _SSR_LLM_EXPLANATION_CACHE.clear()
    llm_local_circuit.reset_all()
    yield
    _SSR_LLM_EXPLANATION_CACHE.clear()
    llm_local_circuit.reset_all()


def _rec():
    return build_smart_study_recommendation(surface="home", flashcard_due_n=1)


def _kw(**extra):
    return dict(
        evidence_ledger=None,
        tutor_topic=None,
        weak_concept="chunking",
        primary_topic_hint=None,
        **extra,
    )


# ── cache hit ────────────────────────────────────────────────────────────────

def test_stream_yields_cached_text_immediately(monkeypatch: pytest.MonkeyPatch) -> None:
    import time

    rec = _rec()
    # Seed cache with known text.
    # Replicate the ctx mutation that stream_ssr_explanation applies when
    # evidence_ledger is None (sets cards_due_count/sm2_due_count from hint_kind).
    from app.ui.adaptive_plan_llm_enrichment import _ssr_explanation_cache_key, _build_ssr_llm_learning_context
    ctx = _build_ssr_llm_learning_context(rec, evidence_ledger=None, tutor_topic=None,
                                          weak_concept="chunking", primary_topic_hint=None)
    hk = rec.hint_kind
    ctx["cards_due_count"] = 1 if hk == "cards_due" else 0
    ctx["sm2_due_count"] = 1 if hk == "sm2_due" else 0
    key = _ssr_explanation_cache_key(rec, ctx)
    _SSR_LLM_EXPLANATION_CACHE[key] = (time.monotonic(), "Кэшированный ответ.")

    tokens = list(stream_ssr_explanation(rec, **_kw()))
    assert tokens == ["Кэшированный ответ."]


# ── streaming with mock LLM ──────────────────────────────────────────────────

def test_stream_yields_tokens_and_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Delta:
        def __init__(self, d): self.delta = d

    class StreamLlm:
        model = "stream-model"
        api_base = "http://127.0.0.1:8787"

        def stream_chat(self, messages, **kw):
            for word in ["Это ", "стриминг ", "объяснения."]:
                yield _Delta(word)

    monkeypatch.setattr(
        "app.ui.adaptive_plan_llm_enrichment.get_ssr_llm_resolved",
        lambda: (StreamLlm(), False),
    )
    monkeypatch.setattr(
        "app.ui.adaptive_plan_llm_enrichment.ssr_llm_shares_main_api_base",
        lambda: False,
    )

    rec = _rec()
    tokens = list(stream_ssr_explanation(rec, **_kw()))
    assert tokens == ["Это ", "стриминг ", "объяснения."]
    # Result must be cached after streaming completes.
    assert any("стриминг" in v for _, v in _SSR_LLM_EXPLANATION_CACHE.values())


# ── fallback when stream_chat not supported ──────────────────────────────────

def test_stream_falls_back_when_no_stream_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    class BlockingLlm:
        model = "blocking"
        api_base = "http://127.0.0.1:8787"
        # No stream_chat — stream path delegates to _generate_llm_explanation.

        def chat(self, messages, **kwargs):
            raise RuntimeError("blocking llm unavailable in test")

    monkeypatch.setattr(
        "app.ui.adaptive_plan_llm_enrichment.get_ssr_llm_resolved",
        lambda: (BlockingLlm(), False),
    )
    monkeypatch.setattr(
        "app.ui.adaptive_plan_llm_enrichment.ssr_llm_shares_main_api_base",
        lambda: False,
    )
    # _generate_llm_explanation will also fail (no chat method) → template fallback
    rec = _rec()
    tokens = list(stream_ssr_explanation(rec, **_kw()))
    assert len(tokens) == 1
    assert tokens[0] == rec.why_now_ru


# ── circuit breaker open → immediate fallback ────────────────────────────────

def test_stream_respects_open_circuit(monkeypatch: pytest.MonkeyPatch) -> None:
    base = "http://127.0.0.1:8787"

    class CircuitLlm:
        model = "x"
        api_base = base

    monkeypatch.setattr(
        "app.ui.adaptive_plan_llm_enrichment.get_ssr_llm_resolved",
        lambda: (CircuitLlm(), False),
    )
    monkeypatch.setattr(
        "app.ui.adaptive_plan_llm_enrichment.ssr_llm_shares_main_api_base",
        lambda: False,
    )
    # Open the circuit manually.
    for _ in range(3):
        llm_local_circuit.record_failure(base, error_type="X", failure_threshold=3)

    rec = _rec()
    tokens = list(stream_ssr_explanation(rec, **_kw()))
    assert tokens == [rec.why_now_ru]
