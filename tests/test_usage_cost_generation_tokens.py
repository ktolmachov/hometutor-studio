"""Токены генерации: extract_token_usage + accumulation window."""

from __future__ import annotations

from types import SimpleNamespace

from app.usage_cost import (
    begin_llm_generation_token_accumulation,
    consume_llm_generation_call_ms,
    consume_llm_generation_token_accumulation,
    estimate_cost_usd,
    extract_token_usage,
    record_accumulated_llm_usage_from_llm_response,
    record_llm_generation_call_ms,
)


def test_extract_token_usage_coerces_nested_usage_object():
    class _U:
        def model_dump(self):
            return {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

    class _Raw:
        def model_dump(self):
            return {"usage": _U()}

    r = SimpleNamespace(raw=_Raw(), additional_kwargs={})
    u = extract_token_usage(r)
    assert u is not None
    assert u["prompt_tokens"] == 100
    assert u["completion_tokens"] == 50


def test_extract_token_usage_preserves_reasoning_tokens_from_completion_details():
    payload = {
        "usage": {
            "prompt_tokens": 536,
            "completion_tokens": 137,
            "total_tokens": 673,
            "completion_tokens_details": {"reasoning_tokens": 0},
        }
    }

    u = extract_token_usage(payload)

    assert u is not None
    assert u["prompt_tokens"] == 536
    assert u["completion_tokens"] == 137
    assert u["total_tokens"] == 673
    assert u["reasoning_tokens"] == 0


def test_extract_token_usage_prefers_raw_reasoning_tokens_over_clipped_counts():
    response = SimpleNamespace(
        additional_kwargs={
            "prompt_tokens": 536,
            "completion_tokens": 137,
            "total_tokens": 673,
        },
        raw={
            "usage": {
                "prompt_tokens": 536,
                "completion_tokens": 137,
                "total_tokens": 673,
                "completion_tokens_details": {"reasoning_tokens": 0},
            }
        },
    )

    u = extract_token_usage(response)

    assert u is not None
    assert u["prompt_tokens"] == 536
    assert u["completion_tokens"] == 137
    assert u["total_tokens"] == 673
    assert u["reasoning_tokens"] == 0


def test_estimate_cost_gpt5_nano_in_pricing_table():
    usage = {"prompt_tokens": 1_000_000, "completion_tokens": 0, "total_tokens": 1_000_000}
    cost = estimate_cost_usd("gpt-5-nano", usage)
    assert cost is not None
    assert cost == 0.05


def test_accumulation_window_merge():
    begin_llm_generation_token_accumulation()
    record_accumulated_llm_usage_from_llm_response(
        {"usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "reasoning_tokens": 0}}
    )
    record_accumulated_llm_usage_from_llm_response(
        {"usage": {"prompt_tokens": 20, "completion_tokens": 8, "total_tokens": 28, "reasoning_tokens": 0}}
    )
    out = consume_llm_generation_token_accumulation()
    assert out is not None
    assert out["prompt_tokens"] == 30
    assert out["completion_tokens"] == 13
    assert out["reasoning_tokens"] == 0
    assert consume_llm_generation_token_accumulation() is None


def test_generation_call_ms_window_sums_calls():
    """llm_ms split: sum of timed LLM calls within an open window."""
    begin_llm_generation_token_accumulation()
    record_llm_generation_call_ms(120.0)
    record_llm_generation_call_ms(80.5)
    out = consume_llm_generation_call_ms()
    assert out == 200.5
    # Window closed → subsequent consume returns None (treated as llm_ms=0 by caller).
    assert consume_llm_generation_call_ms() is None


def test_generation_call_ms_none_when_no_llm_call():
    """Extractive early-exit path: no LLM call recorded → None (caller maps to 0)."""
    begin_llm_generation_token_accumulation()
    assert consume_llm_generation_call_ms() is None


def test_generation_call_ms_ignored_outside_window():
    """Recording with no open window must not raise and must not leak into next window."""
    record_llm_generation_call_ms(999.0)  # no window open
    begin_llm_generation_token_accumulation()
    record_llm_generation_call_ms(42.0)
    assert consume_llm_generation_call_ms() == 42.0
