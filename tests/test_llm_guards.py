"""Tests for local LLM guardrails and accounting."""

import json

import pytest

from app import llm_guards


def _patch_cost_log_dir(monkeypatch, tmp_path):
    settings = llm_guards.get_settings().model_copy(update={"llm_cost_log_dir": tmp_path})
    monkeypatch.setattr(llm_guards, "get_settings", lambda: settings)


def test_check_model_allowed_blocks_expensive_models():
    with pytest.raises(llm_guards.BlockedModelError):
        llm_guards.check_model_allowed("z-ai/glm-5.1")

    with pytest.raises(llm_guards.BlockedModelError):
        llm_guards.check_model_allowed("openai/gpt-5.3-codex")


def test_check_model_allowed_allows_default_grok_model():
    llm_guards.check_model_allowed("grok-4.1-fast-thinking")


def test_check_input_tokens_enforces_hard_limit():
    llm_guards.check_input_tokens(llm_guards.HARD_TOKEN_LIMIT)

    with pytest.raises(llm_guards.HardLimitExceededError):
        llm_guards.check_input_tokens(llm_guards.HARD_TOKEN_LIMIT + 1)


def test_soft_limit_warning_is_non_blocking():
    warning = llm_guards.soft_limit_warning(llm_guards.SOFT_TOKEN_LIMIT + 1)

    assert warning is not None
    assert "soft limit" in warning
    llm_guards.check_input_tokens(llm_guards.SOFT_TOKEN_LIMIT + 1)


def test_log_cost_call_writes_daily_jsonl(tmp_path, monkeypatch):
    _patch_cost_log_dir(monkeypatch, tmp_path)

    llm_guards.log_cost_call(
        model="grok-4.1-fast-thinking",
        input_tokens=10_500,
        output_tokens=850,
        cost_rub=0.89,
        package_id="E14-B",
        prompt_type="planning",
        status="OK",
        guards_applied=["model_check", "hard_limit_check"],
    )

    [log_file] = list(tmp_path.glob("cost_logs_*.jsonl"))
    record = json.loads(log_file.read_text(encoding="utf-8").strip())

    assert record["model"] == "grok-4.1-fast-thinking"
    assert record["input_tokens"] == 10_500
    assert record["output_tokens"] == 850
    assert record["cost_rub"] == 0.89
    assert record["status"] == "OK"


def test_log_cost_call_flags_input_only_estimate_after_error(tmp_path, monkeypatch):
    _patch_cost_log_dir(monkeypatch, tmp_path)

    llm_guards.log_cost_call(
        model="grok-4.1-fast-thinking",
        input_tokens=100,
        output_tokens=0,
        cost_rub=0.012,
        status="ERR",
        guards_applied=["model_check"],
        error_type="RuntimeError",
        error_message="bad",
        cost_estimated_after_error=True,
    )

    [log_file] = list(tmp_path.glob("cost_logs_*.jsonl"))
    record = json.loads(log_file.read_text(encoding="utf-8").strip())

    assert record["cost_estimated_after_error"] is True
    assert record["cost_rub"] == 0.012


def test_log_cost_call_persists_prompt_stats_and_provider_error(tmp_path, monkeypatch):
    _patch_cost_log_dir(monkeypatch, tmp_path)

    llm_guards.log_cost_call(
        model="grok-4.1-fast-thinking",
        input_tokens=1234,
        output_tokens=0,
        cost_rub=0.111,
        status="ERR",
        guards_applied=["model_check"],
        prompt_stats={
            "messages_count": 3,
            "total_chars": 185816,
            "role_counts": {"system": 1, "user": 2},
        },
        provider_error={
            "error_kind": "context_length_exceeded",
            "input_char_limit": 128000,
            "input_char_actual": 185816,
        },
    )

    [log_file] = list(tmp_path.glob("cost_logs_*.jsonl"))
    record = json.loads(log_file.read_text(encoding="utf-8").strip())

    assert record["prompt_stats"]["total_chars"] == 185816
    assert record["provider_error"]["error_kind"] == "context_length_exceeded"
    assert record["provider_error"]["input_char_limit"] == 128000


def test_unchanged_retry_after_error_is_blocked():
    llm_guards.reset_error_fingerprints()
    fingerprint = llm_guards.request_fingerprint(
        "grok-4.1-fast-thinking",
        [{"role": "user", "content": "same payload"}],
        {"prompt_type": "planning"},
    )

    llm_guards.check_no_recent_error(fingerprint)
    llm_guards.record_error_fingerprint(fingerprint)

    with pytest.raises(llm_guards.NoRetryAfterError):
        llm_guards.check_no_recent_error(fingerprint)

    llm_guards.clear_error_fingerprint(fingerprint)
    llm_guards.check_no_recent_error(fingerprint)
