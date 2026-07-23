"""Unit coverage for Cursor→LM relay payload compression helpers."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _kilo_relay_compress import (  # noqa: E402
    DEFAULT_CURSOR_SYSTEM_STUB,
    DEFAULT_LOCAL_TOOLS,
    RelayCompressConfig,
    compress_chat_completion,
    parse_tools_allowlist,
    relay_compress_any_enabled,
    relay_compress_config_from_env,
)


def _sample_tool(name: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": "X" * 200,
            "parameters": {"type": "object", "properties": {"arg": {"type": "string", "description": "Y" * 120}}},
        },
    }


@pytest.fixture
def dense_payload() -> dict:
    return {
        "model": "qwen3",
        "messages": [
            {
                "role": "system",
                "content": "<available_skills><agent_skill>X</available_skills> tail",
            }
        ],
        "tools": [
            _sample_tool("Read"),
            _sample_tool("Task"),
            _sample_tool("CallMcpTool"),
        ],
    }


def test_parse_allowlist_missing_is_none():
    assert parse_tools_allowlist("") is None
    assert parse_tools_allowlist("  ") is None


def test_parse_allowlist_strips_spaces():
    assert parse_tools_allowlist(" Read , Grep ") == frozenset({"Read", "Grep"})


def test_allowlist_drops_removed_tool_names_and_non_function_tools(dense_payload):
    cfg = RelayCompressConfig(tools_allowlist=frozenset({"Read"}))
    out = compress_chat_completion(dense_payload, cfg)
    names = []
    for t in out.payload.get("tools") or []:
        if isinstance(t.get("function"), dict):
            names.append(t["function"].get("name"))
    assert names == ["Read"]
    assert "Task" in out.tool_names_removed
    assert "CallMcpTool" in out.tool_names_removed


def test_allowlist_matches_tool_names_case_insensitively():
    payload = {
        "tools": [
            _sample_tool("read"),
            _sample_tool("Grep"),
            _sample_tool("agent_manager"),
        ]
    }
    cfg = RelayCompressConfig(tools_allowlist=frozenset({"Read", "GREP"}))
    out = compress_chat_completion(payload, cfg)
    names = [t["function"]["name"] for t in out.payload.get("tools") or []]
    assert names == ["read", "Grep"]
    assert out.tool_names_removed == ["agent_manager"]


def test_allowlist_when_empty_raises_no_tools_and_records_removals():
    cfg = RelayCompressConfig(tools_allowlist=frozenset())
    payload = {"tools": [_sample_tool("Read")]}
    out = compress_chat_completion(payload, cfg)
    assert "tools" not in out.payload
    assert out.tools_after == 0
    assert "Read" in out.tool_names_removed


def test_shrink_caps_description_fields(dense_payload):
    cfg = RelayCompressConfig(tool_description_max_chars=12)
    out = compress_chat_completion(dense_payload, cfg)
    read_fn = None
    for t in out.payload["tools"]:
        if t["function"]["name"] == "Read":
            read_fn = t["function"]
            break
    assert read_fn is not None
    assert len(read_fn["description"]) <= 12
    nested = read_fn["parameters"]["properties"]["arg"]["description"]
    assert len(nested) <= 12


def test_strip_timestamp_xml():
    cfg = RelayCompressConfig(strip_timestamp_xml=True)
    payload = {"messages": [{"role": "user", "content": "<timestamp>Monday</timestamp> tail"}]}
    out = compress_chat_completion(payload, cfg)
    assert "<timestamp>" not in out.payload["messages"][0]["content"].lower()
    assert "strip_timestamp" in out.strip_actions


def test_strip_system_reminder_xml():
    cfg = RelayCompressConfig(strip_system_reminder_xml=True)
    txt = "<system_reminder>Ask mode</system_reminder>Hi"
    payload = {"messages": [{"role": "user", "content": [{"type": "text", "text": txt}]}]}
    out = compress_chat_completion(payload, cfg)
    assert "strip_system_reminder_underscore" in out.strip_actions
    assert "<system_reminder>" not in out.payload["messages"][0]["content"][0]["text"]


def test_relay_default_env_enables_local_slim():
    cfg = relay_compress_config_from_env({})
    assert cfg.slim_mode_label
    assert cfg.tools_allowlist == DEFAULT_LOCAL_TOOLS
    assert relay_compress_any_enabled(cfg)


def test_cloud_budget_env_preserves_platform_system_and_all_tools():
    cfg = relay_compress_config_from_env({"KILO_RELAY_SLIM_MODE": "cloud_budget"})
    assert cfg.slim_mode_label == "cloud_budget"
    assert not cfg.replace_cursor_system_content
    assert cfg.tools_allowlist is None
    assert cfg.strip_mcp_file_system_xml
    assert not cfg.strip_task_management_xml
    assert not cfg.strip_user_info_xml
    assert not cfg.use_local_tool_summaries
    assert cfg.purge_parameter_descriptions
    assert cfg.tool_description_max_chars == 120
    assert relay_compress_any_enabled(cfg)


def test_budget_cloud_alias_matches_cloud_budget():
    a = relay_compress_config_from_env({"KILO_RELAY_SLIM_MODE": "cloud_budget"})
    b = relay_compress_config_from_env({"KILO_RELAY_SLIM_MODE": "budget_cloud"})
    assert a.replace_cursor_system_content == b.replace_cursor_system_content
    assert a.strip_mcp_servers_xml == b.strip_mcp_servers_xml
    assert a.tool_description_max_chars == b.tool_description_max_chars


def test_cloud_budget_compress_keeps_all_tool_names_and_no_stub(dense_payload):
    cfg = relay_compress_config_from_env({"KILO_RELAY_SLIM_MODE": "cloud_budget"})
    out = compress_chat_completion(dense_payload, cfg)
    assert not out.cursor_system_stubbed
    names = sorted(t["function"]["name"] for t in out.payload["tools"])
    assert names == ["CallMcpTool", "Read", "Task"]
    assert "<available_skills>" not in out.payload["messages"][0]["content"]


def test_cloud_budget_tool_desc_max_zero_disables_cap():
    cfg = relay_compress_config_from_env(
        {"KILO_RELAY_SLIM_MODE": "cloud_budget", "KILO_RELAY_CLOUD_BUDGET_TOOL_DESC_MAX": "0"}
    )
    assert cfg.tool_description_max_chars == 0


def test_local_include_glob_via_env():
    cfg = relay_compress_config_from_env(
        {"KILO_RELAY_SLIM_MODE": "local", "KILO_RELAY_LOCAL_INCLUDE_GLOB": "1"}
    )
    assert "Glob" in cfg.tools_allowlist


def test_slim_mode_env_minimal_tools_and_purge():
    cfg = relay_compress_config_from_env(
        {
            "KILO_RELAY_SLIM_MODE": "local",
            "KILO_RELAY_SIMPLE_CHAT_STRIP_TOOLS": "0",
        }
    )
    assert cfg.tools_allowlist == DEFAULT_LOCAL_TOOLS
    assert cfg.use_local_tool_summaries
    assert cfg.purge_parameter_descriptions
    assert cfg.strip_timestamp_xml
    assert relay_compress_any_enabled(cfg)

    payload = {
        "messages": [{"role": "user", "content": "refactor large file"}],
        "tools": [
            _sample_tool("Read"),
            _sample_tool("Task"),
            _sample_tool("CallMcpTool"),
        ],
    }
    out = compress_chat_completion(payload, cfg)
    names = [t["function"]["name"] for t in out.payload.get("tools") or []]
    assert names == ["Read"]
    props = out.payload["tools"][0]["function"]["parameters"]["properties"]["arg"]
    assert "description" not in props
    summ = out.payload["tools"][0]["function"]["description"]
    assert len(summ) < 40


def test_simple_chat_drops_tools():
    cfg = RelayCompressConfig(
        tools_allowlist=frozenset({"Read"}),
        simple_chat_strip_tools_max_user_chars=200,
        strip_available_skills_xml=False,
    )
    payload = {
        "messages": [{"role": "user", "content": "Hello"}],
        "tools": [_sample_tool("Read")],
    }
    out = compress_chat_completion(payload, cfg)
    assert "tools" not in out.payload
    assert out.tool_choice_forced_none
    assert out.simple_chat_tools_dropped


def test_cursor_system_stub_applies_to_all_system_messages():
    stub = "[short system stub]"
    cfg = RelayCompressConfig(
        replace_cursor_system_content=True,
        cursor_system_stub_text=stub,
    )
    payload = {
        "messages": [
            {"role": "system", "content": "very long Cursor system preamble"},
            {"role": "user", "content": "Hi"},
            {"role": "system", "content": "second system message"},
        ]
    }
    out = compress_chat_completion(payload, cfg)
    assert out.cursor_system_stubbed
    msgs = out.payload["messages"]
    assert msgs[0]["content"] == stub
    assert msgs[1]["content"] == "Hi"
    assert msgs[2]["content"] == stub


def test_env_local_replaces_cursor_system_by_default():
    cfg = relay_compress_config_from_env({})
    assert cfg.replace_cursor_system_content


def test_env_local_keep_cursor_system_turns_off_replace():
    cfg = relay_compress_config_from_env({"KILO_RELAY_LOCAL_KEEP_CURSOR_SYSTEM": "1"})
    assert not cfg.replace_cursor_system_content


def test_strip_skills_inside_messages(dense_payload):
    cfg = RelayCompressConfig(strip_available_skills_xml=True)
    out = compress_chat_completion(dense_payload, cfg)
    assert "<available_skills>" not in out.payload["messages"][0]["content"]
    assert "strip_available_skills" in out.strip_actions


def test_relay_compress_config_from_env_shrink_toggle():
    env = {
        "KILO_RELAY_SLIM_MODE": "off",
        "KILO_RELAY_SHRINK_TOOL_DESCRIPTIONS": "true",
    }
    cfg = relay_compress_config_from_env(env)
    assert cfg.tool_description_max_chars == 80
    assert relay_compress_any_enabled(cfg)


def test_relay_compress_disabled_when_explicit_off():
    cfg = relay_compress_config_from_env({"KILO_RELAY_SLIM_MODE": "off"})
    assert cfg.slim_mode_label == ""
    assert cfg.tools_allowlist is None
    assert not relay_compress_any_enabled(cfg)


def test_default_cursor_stub_covers_model_identity_hint():
    """Stub used when replacing Cursor platform system (doc/kilo_proxy_relay § audit)."""
    assert "model" in DEFAULT_CURSOR_SYSTEM_STUB.lower()
    assert "json" in DEFAULT_CURSOR_SYSTEM_STUB.lower()


# --- Tier B: history window + tool_result capping -------------------------
# Added after the diagnosis "kilo_content_budget_breakthrough" flagged
# unbounded per-turn growth (tool_result + assistant_tool_calls history never
# trimmed by the relay). Lifting the earlier "do not touch messages[] history"
# constraint was an explicit, deliberate decision — not an oversight.


def _msg(role: str, content: Any = "x", tool_call_id: str | None = None, tool_calls: list | None = None) -> dict:
    m: dict[str, Any] = {"role": role, "content": content}
    if tool_call_id is not None:
        m["tool_call_id"] = tool_call_id
    if tool_calls is not None:
        m["tool_calls"] = tool_calls
    return m


def _parallel_tool_calls_payload() -> dict:
    """system, then a chain including one single tool_call turn and one
    *parallel* (2-call) tool_call turn — the case that would orphan a
    tool-result message if the window cut naively by raw message count."""
    return {
        "model": "x",
        "messages": [
            _msg("system", "platform prompt"),
            _msg("user", "u1"),
            _msg("assistant", None, tool_calls=[{"id": "c1", "type": "function", "function": {"name": "Read"}}]),
            _msg("tool", "r1", tool_call_id="c1"),
            _msg("assistant", "a1"),
            _msg("user", "u2"),
            _msg(
                "assistant",
                None,
                tool_calls=[
                    {"id": "c2a", "type": "function", "function": {"name": "Read"}},
                    {"id": "c2b", "type": "function", "function": {"name": "Grep"}},
                ],
            ),
            _msg("tool", "r2a", tool_call_id="c2a"),
            _msg("tool", "r2b", tool_call_id="c2b"),
            _msg("assistant", "a2"),
            _msg("user", "u3"),
        ],
    }


def _assert_no_dangling_tool_messages(messages: list) -> None:
    produced_ids: set[str] = set()
    for m in messages:
        if m.get("role") == "assistant" and isinstance(m.get("tool_calls"), list):
            for tc in m["tool_calls"]:
                if isinstance(tc, dict) and tc.get("id"):
                    produced_ids.add(tc["id"])
    for m in messages:
        if m.get("role") == "tool":
            assert m.get("tool_call_id") in produced_ids, f"dangling tool result: {m}"


def test_history_window_noop_when_under_limit():
    cfg = RelayCompressConfig(keep_last_messages=100)
    payload = _parallel_tool_calls_payload()
    out = compress_chat_completion(payload, cfg)
    assert out.messages_dropped_history == 0
    assert out.messages_after == out.messages_before
    assert out.payload["messages"] == payload["messages"]


def test_history_window_disabled_by_default():
    cfg = RelayCompressConfig()  # keep_last_messages defaults to 0
    payload = _parallel_tool_calls_payload()
    out = compress_chat_completion(payload, cfg)
    assert out.messages_dropped_history == 0
    assert len(out.payload["messages"]) == len(payload["messages"])


def test_history_window_keeps_leading_system_and_trims_tail():
    cfg = RelayCompressConfig(keep_last_messages=3)
    payload = _parallel_tool_calls_payload()
    out = compress_chat_completion(payload, cfg)
    kept = out.payload["messages"]
    assert kept[0] == payload["messages"][0]  # system always kept
    assert kept[0]["role"] == "system"
    assert out.messages_dropped_history > 0
    assert len(kept) < len(payload["messages"])
    assert kept[-1] == payload["messages"][-1]  # tail end never dropped


def test_history_window_never_leaves_dangling_tool_result():
    """The core correctness requirement: cutting mid-way through a parallel
    tool_calls/tool_result chain must not send an invalid message list
    upstream. Try every window size to hit both the single-call and the
    parallel-call boundary cases."""
    payload = _parallel_tool_calls_payload()
    for n in range(1, len(payload["messages"]) + 2):
        cfg = RelayCompressConfig(keep_last_messages=n)
        out = compress_chat_completion(payload, cfg)
        _assert_no_dangling_tool_messages(out.payload["messages"])


def test_history_window_skips_oversized_tool_group_to_honor_keep_last():
    """Tool-safe expand used to blow past keep_last (e.g. 14 → 19) when a
    large parallel tool_calls batch sat on the cut boundary, tripping
    soft_block on messages_count. Prefer dropping the older group."""
    tools = [_msg("tool", f"r{i}", tool_call_id=f"c{i}") for i in range(6)]
    payload = {
        "messages": [
            _msg("system", "s"),
            _msg("user", "old"),
            _msg(
                "assistant",
                None,
                tool_calls=[
                    {"id": f"c{i}", "type": "function", "function": {"name": "Read"}}
                    for i in range(6)
                ],
            ),
            *tools,
            _msg("user", "u_recent"),
            _msg("assistant", "a_recent"),
            _msg("user", "u_latest"),
        ]
    }
    # keep_last=4 lands cut_at on the last tool of the parallel batch → old
    # expand-only path would keep assistant+6 tools+3 tail = 10 non-system.
    cfg = RelayCompressConfig(keep_last_messages=4)
    out = compress_chat_completion(payload, cfg)
    kept = out.payload["messages"]
    _assert_no_dangling_tool_messages(kept)
    non_system = [m for m in kept if m.get("role") != "system"]
    assert len(non_system) <= 4
    assert kept[0]["role"] == "system"
    assert kept[-1]["content"] == "u_latest"
    assert all(m.get("role") != "tool" for m in kept), "oversized older tool group should be skipped"


def test_history_window_keeps_multiple_leading_system_messages():
    payload = {
        "messages": [
            _msg("system", "s1"),
            _msg("system", "s2"),
            *[_msg("user", f"u{i}") for i in range(10)],
        ]
    }
    cfg = RelayCompressConfig(keep_last_messages=2)
    out = compress_chat_completion(payload, cfg)
    kept = out.payload["messages"]
    assert kept[0]["content"] == "s1"
    assert kept[1]["content"] == "s2"
    assert len(kept) == 4  # 2 system + last 2 user


def test_cap_tool_result_chars_truncates_only_tool_role():
    cfg = RelayCompressConfig(max_tool_result_chars=10)
    payload = {
        "messages": [
            _msg("system", "s" * 50),
            _msg("assistant", "a" * 50),
            _msg("tool", "t" * 50, tool_call_id="c1"),
        ]
    }
    out = compress_chat_completion(payload, cfg)
    assert out.tool_results_capped == 1
    kept = out.payload["messages"]
    assert kept[0]["content"] == "s" * 50  # system untouched
    assert kept[1]["content"] == "a" * 50  # assistant untouched
    assert len(kept[2]["content"]) < 50
    assert kept[2]["content"].startswith("t" * 10)
    assert "truncated by relay" in kept[2]["content"]


def test_cap_tool_result_chars_leaves_short_results_untouched():
    cfg = RelayCompressConfig(max_tool_result_chars=100)
    payload = {"messages": [_msg("tool", "short", tool_call_id="c1")]}
    out = compress_chat_completion(payload, cfg)
    assert out.tool_results_capped == 0
    assert out.payload["messages"][0]["content"] == "short"


def test_cap_tool_result_chars_disabled_by_default():
    cfg = RelayCompressConfig()
    payload = {"messages": [_msg("tool", "t" * 5000, tool_call_id="c1")]}
    out = compress_chat_completion(payload, cfg)
    assert out.tool_results_capped == 0
    assert out.payload["messages"][0]["content"] == "t" * 5000


def test_cap_tool_result_chars_handles_list_of_parts_content():
    cfg = RelayCompressConfig(max_tool_result_chars=5)
    payload = {
        "messages": [
            {
                "role": "tool",
                "tool_call_id": "c1",
                "content": [{"type": "text", "text": "x" * 20}],
            }
        ]
    }
    out = compress_chat_completion(payload, cfg)
    assert out.tool_results_capped == 1
    text = out.payload["messages"][0]["content"][0]["text"]
    assert text.startswith("x" * 5)
    assert "truncated by relay" in text


def test_compress_result_to_log_dict_reports_history_and_cap_counters():
    cfg = RelayCompressConfig(keep_last_messages=3, max_tool_result_chars=5)
    payload = _parallel_tool_calls_payload()
    out = compress_chat_completion(payload, cfg)
    log = out.to_log_dict()
    assert log["messages_before"] == len(payload["messages"])
    assert log["messages_after"] == len(out.payload["messages"])
    assert log["messages_dropped_history"] == out.messages_dropped_history
    assert log["tool_results_capped"] == out.tool_results_capped


def test_env_keep_last_messages_generic_var_applies_off_mode():
    cfg = relay_compress_config_from_env(
        {"KILO_RELAY_SLIM_MODE": "off", "KILO_RELAY_KEEP_LAST_MESSAGES": "5"}
    )
    assert cfg.keep_last_messages == 5
    assert relay_compress_any_enabled(cfg)  # turns compression on even though slim_mode is off


def test_env_cloud_budget_keep_last_messages_requires_its_own_var():
    """The generic KILO_RELAY_KEEP_LAST_MESSAGES is NOT a fallback in
    cloud_budget mode — mirrors every other KILO_RELAY_CLOUD_BUDGET_* override
    (e.g. strip_cursor_rules_xml), so this is intentional, not a bug."""
    cfg = relay_compress_config_from_env(
        {"KILO_RELAY_SLIM_MODE": "cloud_budget", "KILO_RELAY_KEEP_LAST_MESSAGES": "5"}
    )
    assert cfg.keep_last_messages == 0

    cfg2 = relay_compress_config_from_env(
        {
            "KILO_RELAY_SLIM_MODE": "cloud_budget",
            "KILO_RELAY_CLOUD_BUDGET_KEEP_LAST_MESSAGES": "8",
            "KILO_RELAY_CLOUD_BUDGET_MAX_TOOL_RESULT_CHARS": "500",
        }
    )
    assert cfg2.keep_last_messages == 8
    assert cfg2.max_tool_result_chars == 500
    assert relay_compress_any_enabled(cfg2)
