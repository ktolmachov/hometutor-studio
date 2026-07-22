"""Tests for scripts/_kilo_prompt_stats.py and content-stats helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _kilo_prompt_stats import (  # noqa: E402
    analyze_chat_payload,
    fragment_char_counts,
    normalize_path_key,
    path_char_contributions,
)
import kilo_proxy_relay as relay  # noqa: E402
import kilo_prompt_content_report as report  # noqa: E402


def test_fragment_char_counts_detects_skills_and_rules():
    text = (
        "<available_skills>ABCDEFGHIJ</available_skills>"
        "<rules>12345</rules>"
        "plain"
    )
    counts = fragment_char_counts(text)
    assert counts["available_skills"] > 10
    assert counts["rules"] > 5


def test_normalize_path_key_agents_and_doc_relative():
    assert normalize_path_key(r"D:\Projects\hometutor-studio\AGENTS.md").lower().endswith("agents.md")
    assert normalize_path_key("doc/conventions.md") == "doc/conventions.md"


def test_analyze_chat_payload_roles_tools_paths():
    payload = {
        "model": "x",
        "messages": [
            {"role": "system", "content": "<user_info>os=win</user_info> hello"},
            {
                "role": "user",
                "content": "<user_query>read AGENTS.md</user_query>\nSee doc/token_safety.md please",
            },
            {"role": "tool", "content": "file D:\\Projects\\hometutor\\CLAUDE.md\n" + ("x" * 500)},
        ],
        "tools": [
            {"type": "function", "function": {"name": "Read", "description": "d" * 200, "parameters": {}}},
            {"type": "function", "function": {"name": "Shell", "description": "s", "parameters": {}}},
        ],
    }
    stats = analyze_chat_payload(payload, top_messages=5, top_paths=10)
    assert stats["messages_count"] == 3
    assert stats["role_chars"]["tool"] >= 500
    assert "user_query" in stats["fragment_chars"] or "user_info" in stats["fragment_chars"]
    assert stats["tools"]["tools_count"] == 2
    assert stats["tools"]["by_name"][0]["name"] in {"Read", "Shell"}
    paths = [r["path"].lower() for r in stats["path_chars"]]
    assert any("agents.md" in p or "claude.md" in p or "token_safety" in p for p in paths)


def test_content_stats_glance_and_sanitize():
    glance = relay._content_stats_glance(
        {
            "original": {
                "kind_chars": {"tool_result": 9000, "user": 100},
                "path_chars": [{"path": "AGENTS.md", "chars": 4000, "hits": 3}],
                "fragment_chars": {"rules": 1200},
            }
        }
    )
    assert "top_kind=tool_result:9000" in glance
    assert "top_path=AGENTS.md:4000" in glance
    assert "top_frag=rules:1200" in glance

    summary = {
        "body_chars": 10,
        "message_stats": [{"index": 0}],
        "body_preview_start": "x",
        "body_preview_end": "y",
    }
    cleaned = relay.sanitize_request_summary_for_log(summary)
    assert "message_stats" not in cleaned
    assert "body_preview_start" not in cleaned


def test_report_aggregates_content_stats():
    rec = {
        "path": "/v1/chat/completions",
        "content_stats": {
            "original": {
                "role_chars": {"tool": 1000, "user": 50},
                "kind_chars": {"tool_result": 1000},
                "fragment_chars": {"rules": 200},
                "ext_chars": {"md": 800},
                "path_chars": [{"path": "AGENTS.md", "chars": 800, "hits": 2}],
                "tools": {"by_name": [{"name": "Read", "chars": 300}]},
            }
        },
        "response": {"usage": {"prompt_tokens": 1234}},
    }
    out = report.build_report([rec, {"path": "/v1/models"}])
    assert out["chat_with_content_stats"] == 1
    assert out["top_kinds"][0]["key"] == "tool_result"
    assert out["top_paths"][0]["path"] == "AGENTS.md"
    assert out["usage_prompt_tokens_sum"] == 1234
    text = report.render_text(out)
    assert "AGENTS.md" in text
    assert "top extensions" in text
    assert "relative rank" in text
    assert out["top_extensions"][0]["key"] == "md"


def test_report_main_refuses_empty_json_out(tmp_path: Path):
    log = tmp_path / "empty.jsonl"
    log.write_text("{}\n", encoding="utf-8")
    out = tmp_path / "report.json"
    out.write_text('{"keep": true}', encoding="utf-8")
    rc = report.main(["--log", str(log), "--last", "10", "--json-out", str(out)])
    assert rc == 2
    assert json.loads(out.read_text(encoding="utf-8")) == {"keep": True}
