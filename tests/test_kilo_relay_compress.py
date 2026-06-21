"""Unit coverage for Cursor→LM relay payload compression helpers."""
from __future__ import annotations

import json
import sys
from pathlib import Path

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
