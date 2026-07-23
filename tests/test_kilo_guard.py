"""Unit coverage for the pure guard module.

Before this file existed, guard thresholds and RISK_PATTERNS had zero test
coverage — any silent drift in `scripts/_kilo_guard.py` would only surface
once a real relay run tripped over it. These tests pin the exact boundary
behaviour so runtime and simulator verdicts stay in lockstep.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _kilo_guard import (  # noqa: E402
    GuardThresholds,
    detect_risk_flags,
    evaluate_guard,
    evaluate_session_health,
    summarize_body,
)


CHAT_PATH = "/v1/chat/completions"
OTHER_PATH = "/v1/models"


def _summary(**overrides) -> dict:
    base = {
        "body_chars": 0,
        "messages_count": 0,
        "largest_message_chars": 0,
        "tools_count": 0,
    }
    base.update(overrides)
    return base


def _thresholds(**overrides) -> GuardThresholds:
    defaults = dict(
        warn_body_chars=70000,
        max_body_chars=90000,
        hard_block_body_chars=110000,
        max_messages=15,
        max_largest_message_chars=24000,
        max_tools=13,
    )
    defaults.update(overrides)
    return GuardThresholds(**defaults)


class TestBodyCharThresholds:
    def test_at_warn_boundary_is_ok(self):
        v = evaluate_guard(CHAT_PATH, "", _summary(body_chars=70000), thresholds=_thresholds(), mode="warn")
        assert v.level == "ok"

    def test_one_over_warn_triggers_warn(self):
        v = evaluate_guard(CHAT_PATH, "", _summary(body_chars=70001), thresholds=_thresholds(), mode="warn")
        assert v.level == "warn"
        assert any("body_chars>70000" in r for r in v.reasons)

    def test_at_max_boundary_is_warn(self):
        v = evaluate_guard(CHAT_PATH, "", _summary(body_chars=90000), thresholds=_thresholds(), mode="warn")
        assert v.level == "warn"

    def test_one_over_max_is_soft_block(self):
        v = evaluate_guard(CHAT_PATH, "", _summary(body_chars=90001), thresholds=_thresholds(), mode="warn")
        assert v.level == "soft_block"

    def test_one_over_hard_is_hard_block(self):
        v = evaluate_guard(CHAT_PATH, "", _summary(body_chars=110001), thresholds=_thresholds(), mode="warn")
        assert v.level == "hard_block"

    def test_non_chat_path_ignores_body_thresholds(self):
        v = evaluate_guard(OTHER_PATH, "", _summary(body_chars=200000), thresholds=_thresholds(), mode="warn")
        assert v.level == "ok"


class TestBlockModeSemantics:
    def test_warn_never_blocks_even_in_block_mode(self):
        v = evaluate_guard(CHAT_PATH, "", _summary(body_chars=75000), thresholds=_thresholds(), mode="block")
        assert v.level == "warn"
        assert v.block is False

    def test_soft_block_blocks_only_in_block_mode(self):
        s = _summary(body_chars=95000)
        assert evaluate_guard(CHAT_PATH, "", s, thresholds=_thresholds(), mode="warn").block is False
        assert evaluate_guard(CHAT_PATH, "", s, thresholds=_thresholds(), mode="block").block is True

    def test_hard_block_level_does_not_block_in_warn_mode(self):
        v_warn = evaluate_guard(CHAT_PATH, "", _summary(body_chars=120000), thresholds=_thresholds(), mode="warn")
        v_block = evaluate_guard(CHAT_PATH, "", _summary(body_chars=120000), thresholds=_thresholds(), mode="block")
        assert v_warn.level == "hard_block"
        assert v_warn.block is False  # warn mode only annotates
        assert v_block.block is True


class TestRiskFlags:
    def test_detect_all_nine_patterns(self):
        # backlog_registry pattern expects JSON-escaped Windows path (two backslashes).
        text = (
            r"doc\\backlog_registry.yaml generate_plan_next_prompt.md "
            "generate_orchestration_prompt.md closed_iterations.md current_task.payload.md "
            "Zero-Click Delivery Pipeline <available_skills> \"type\":\"function\" kilo_local_recall"
        )
        flags = detect_risk_flags(text)
        assert len(flags) == 9
        assert "full backlog registry injected" in flags
        assert "session recall tool schema injected" in flags

    def test_no_false_positives_on_empty_body(self):
        assert detect_risk_flags("") == []

    def test_workflow_combo_triggers_soft_block(self):
        # three workflow-combo labels → soft_block even if body is tiny
        text = (
            r"doc\\backlog_registry.yaml generate_plan_next_prompt.md closed_iterations.md"
        )
        v = evaluate_guard(CHAT_PATH, text, _summary(body_chars=100), thresholds=_thresholds(), mode="warn")
        assert v.level == "soft_block"
        assert any("workflow_context_combo>=3" in r for r in v.reasons)

    def test_workflow_combo_requires_three(self):
        text = r"doc\\backlog_registry.yaml generate_plan_next_prompt.md"  # only 2
        v = evaluate_guard(CHAT_PATH, text, _summary(body_chars=100), thresholds=_thresholds(), mode="warn")
        assert v.level == "ok"


class TestMessageAndToolThresholds:
    def test_messages_over_limit_soft_blocks(self):
        v = evaluate_guard(CHAT_PATH, "", _summary(messages_count=16), thresholds=_thresholds(), mode="warn")
        assert v.level == "soft_block"

    def test_largest_message_over_limit_warns(self):
        v = evaluate_guard(
            CHAT_PATH, "", _summary(largest_message_chars=24001),
            thresholds=_thresholds(), mode="warn",
        )
        assert v.level == "warn"

    def test_tools_over_limit_warns(self):
        v = evaluate_guard(CHAT_PATH, "", _summary(tools_count=17), thresholds=_thresholds(), mode="warn")
        assert v.level == "warn"

    def test_hardest_level_wins_when_multiple_triggers(self):
        v = evaluate_guard(
            CHAT_PATH, "",
            _summary(body_chars=120000, messages_count=9, tools_count=14),
            thresholds=_thresholds(), mode="warn",
        )
        assert v.level == "hard_block"


class TestSummarizeBody:
    def test_invalid_json_returns_best_effort_stats(self):
        s = summarize_body("not-json")
        assert s["json_valid"] is False
        assert s["body_chars"] == len("not-json")

    def test_empty_body_is_valid_zero_stats(self):
        s = summarize_body("")
        assert s["json_valid"] is True
        assert s["messages_count"] == 0
        assert s["largest_message_chars"] == 0

    def test_well_formed_chat_payload_counts_roles(self):
        body = json.dumps({
            "model": "x",
            "messages": [
                {"role": "system", "content": "a" * 100},
                {"role": "user", "content": "b" * 50},
            ],
            "tools": [{"type": "function"}],
        })
        s = summarize_body(body)
        assert s["json_valid"] is True
        assert s["messages_count"] == 2
        assert s["tools_count"] == 1
        assert s["role_chars"] == {"system": 100, "user": 50}
        assert s["largest_message_chars"] == 100


class TestCustomThresholds:
    def test_can_lower_thresholds(self):
        t = _thresholds(warn_body_chars=100, max_body_chars=200, hard_block_body_chars=300)
        v = evaluate_guard(CHAT_PATH, "", _summary(body_chars=150), thresholds=t, mode="warn")
        assert v.level == "warn"


@pytest.fixture
def default_thresholds():
    return _thresholds()


def test_from_env_respects_overrides():
    t = GuardThresholds.from_env({
        "KILO_RELAY_WARN_BODY_CHARS": "5",
        "KILO_RELAY_MAX_BODY_CHARS": "10",
        "KILO_RELAY_HARD_BLOCK_BODY_CHARS": "15",
        "KILO_RELAY_MAX_MESSAGES": "2",
        "KILO_RELAY_MAX_LARGEST_MESSAGE_CHARS": "20",
        "KILO_RELAY_MAX_TOOLS": "3",
    })
    assert t.warn_body_chars == 5
    assert t.max_tools == 3


def test_from_env_defaults_match_historical_relay_constants():
    t = GuardThresholds.from_env({})
    assert t.warn_body_chars == 70000
    assert t.max_body_chars == 90000
    assert t.hard_block_body_chars == 110000
    # Raised from 8 to 15: real injection uses 8-9 system messages.
    assert t.max_messages == 15
    assert t.max_largest_message_chars == 24000
    # Raised from 13 to 16: Cursor agent sessions routinely ship ~16 tools.
    assert t.max_tools == 16


class TestSessionHealth:
    def test_ok_when_small(self):
        h = evaluate_session_health(
            {"messages_count": 12, "estimated_tokens": 5000, "body_chars": 20000}
        )
        assert h.level == "ok"
        assert h.recommend_new_chat is False
        assert h.reasons == []

    def test_warns_on_original_token_bloat(self):
        h = evaluate_session_health(
            {"messages_count": 10, "estimated_tokens": 25000, "body_chars": 50000}
        )
        assert h.recommend_new_chat is True
        assert any("original_estimated_tokens>" in r for r in h.reasons)

    def test_warns_on_message_archive(self):
        h = evaluate_session_health(
            {"messages_count": 400, "estimated_tokens": 1000, "body_chars": 5000}
        )
        assert h.recommend_new_chat is True
        assert any("original_messages>" in r for r in h.reasons)

    def test_warns_on_body_past_hard_threshold(self):
        h = evaluate_session_health(
            {"messages_count": 10, "estimated_tokens": 1000, "body_chars": 120000}
        )
        assert h.recommend_new_chat is True
        assert any("original_body_chars>" in r for r in h.reasons)
