"""Tests for scripts/_kilo_prompt_stats.py and content-stats helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

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


def test_fragment_char_counts_mcp_meta_does_not_double_count():
    known = "<mcp_file_system>ABCDEFGHIJ</mcp_file_system>"
    other = "<mcp_custom_block>XYZ</mcp_custom_block>"
    counts_known = fragment_char_counts(known)
    assert counts_known["mcp_file_system"] == len(known)
    assert "mcp_meta" not in counts_known
    counts_other = fragment_char_counts(other)
    assert counts_other["mcp_meta"] == len(other)
    assert "mcp_file_system" not in counts_other


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


def _chat_row(idx: int, chars: int = 100) -> dict:
    return {
        "path": "/v1/chat/completions",
        "content_stats": {
            "original": {
                "total_message_chars": chars,
                "messages_count": idx,
                "role_chars": {"user": chars},
            }
        },
    }


def test_collect_chat_records_filters_non_chat_rows(tmp_path: Path):
    log = tmp_path / "mixed.jsonl"
    rows = [_chat_row(1), {"path": "/v1/models"}, _chat_row(2), {"path": "/healthz"}]
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    counters, chat = report.collect_chat_records(log, last=None)
    assert counters["dict_records"] == 4
    assert counters["invalid_json"] == 0
    assert counters["non_dict_records"] == 0
    assert counters["chat_with_stats"] == 2
    assert len(chat) == 2
    assert all(r["path"] == "/v1/chat/completions" for r in chat)


def test_collect_chat_records_last_keeps_tail_chat_only(tmp_path: Path):
    """Non-chat rows interspersed in the tail window must not shrink the chat
    sample below N (the exact regression the audit's --last finding covered)."""
    log = tmp_path / "mixed.jsonl"
    rows = []
    for i in range(10):
        rows.append(_chat_row(i))
        rows.append({"path": "/v1/models"})
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    counters, chat = report.collect_chat_records(log, last=3)
    assert counters["lines_total"] == 20
    assert counters["dict_records"] == 20
    assert len(chat) == 3
    assert [r["content_stats"]["original"]["messages_count"] for r in chat] == [7, 8, 9]


def test_collect_chat_records_last_none_and_zero_return_all(tmp_path: Path):
    log = tmp_path / "chat.jsonl"
    rows = [_chat_row(i) for i in range(5)]
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    _, chat_none = report.collect_chat_records(log, last=None)
    _, chat_zero = report.collect_chat_records(log, last=0)
    assert len(chat_none) == 5
    assert len(chat_zero) == 5


def test_collect_chat_records_counts_malformed_and_non_dict_lines_without_hiding_them(tmp_path: Path):
    """A partially corrupted log must not look externally normal: malformed
    JSON and valid-but-non-dict JSON are counted, not silently discarded."""
    log = tmp_path / "dirty.jsonl"
    log.write_text(
        "\n".join(
            [
                json.dumps(_chat_row(1)),
                "",
                "{not valid json",
                "[1, 2, 3]",  # valid JSON but not a dict
                json.dumps(_chat_row(2)),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    counters, chat = report.collect_chat_records(log, last=None)
    assert counters["lines_total"] == 4  # blank line excluded, 4 non-blank lines
    assert counters["dict_records"] == 2
    assert counters["invalid_json"] == 1
    assert counters["non_dict_records"] == 1
    assert counters["chat_with_stats"] == 2
    assert len(chat) == 2


def test_collect_chat_records_missing_file_returns_empty_counters(tmp_path: Path):
    counters, chat = report.collect_chat_records(tmp_path / "does_not_exist.jsonl", last=10)
    assert counters == {
        "lines_total": 0,
        "dict_records": 0,
        "invalid_json": 0,
        "non_dict_records": 0,
        "chat_records_seen": 0,
        "chat_with_stats": 0,
    }
    assert chat == []


def test_collect_chat_records_seen_counts_full_file_not_just_the_slice(tmp_path: Path):
    """chat_with_stats is capped at --last (deque maxlen); chat_records_seen must
    still report how much instrumented traffic exists in the whole file, so a
    reader can't mistake "sample size" for "total instrumented requests"."""
    log = tmp_path / "chat.jsonl"
    rows = [_chat_row(i) for i in range(10)]
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    counters, chat = report.collect_chat_records(log, last=3)
    assert counters["chat_records_seen"] == 10
    assert counters["chat_with_stats"] == 3
    assert len(chat) == 3


def test_report_main_rejects_negative_last(tmp_path: Path):
    log = tmp_path / "empty.jsonl"
    log.write_text("", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        report.main(["--log", str(log), "--last", "-1"])
    assert exc.value.code == 2


def test_report_main_missing_log_file_is_a_distinct_error(tmp_path: Path, capsys):
    """A missing/mistyped --log path must not be reported as 'no content_stats
    yet — restart relay': that message implies the relay is fine and just hasn't
    seen chat traffic, which is misleading for a simple path typo."""
    missing = tmp_path / "does_not_exist.jsonl"
    rc = report.main(["--log", str(missing)])
    assert rc == 3
    err = capsys.readouterr().err
    assert "not found" in err.lower()
    assert str(missing) in err
    assert "restart relay" not in err.lower()


def test_report_main_shows_scan_counters_for_partially_corrupted_log(tmp_path: Path, capsys):
    log = tmp_path / "dirty.jsonl"
    log.write_text(
        "\n".join([json.dumps(_chat_row(1)), "{not valid json", json.dumps(_chat_row(2))]) + "\n",
        encoding="utf-8",
    )
    rc = report.main(["--log", str(log)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "invalid_json=1" in out
    assert "malformed-JSON line" in out


def test_build_report_path_hits_vs_requests_are_distinct():
    """hits sums per-message mentions and can outrun the request count on its
    own (one request naming a path 3x in different messages); requests counts
    distinct chat requests that mentioned the path at least once. A reader
    must not read a high aggregate `hits` as "appeared in that many requests"."""
    one_request_three_mentions = {
        "path": "/v1/chat/completions",
        "content_stats": {
            "original": {
                "path_chars": [{"path": "AGENTS.md", "chars": 900, "hits": 3}],
            }
        },
    }
    two_requests_one_mention_each = [
        {
            "path": "/v1/chat/completions",
            "content_stats": {"original": {"path_chars": [{"path": "CLAUDE.md", "chars": 300, "hits": 1}]}},
        },
        {
            "path": "/v1/chat/completions",
            "content_stats": {"original": {"path_chars": [{"path": "CLAUDE.md", "chars": 300, "hits": 1}]}},
        },
    ]
    out = report.build_report([one_request_three_mentions, *two_requests_one_mention_each])
    by_path = {row["path"]: row for row in out["top_paths"]}
    assert by_path["AGENTS.md"]["hits"] == 3
    assert by_path["AGENTS.md"]["requests"] == 1
    assert by_path["CLAUDE.md"]["hits"] == 2
    assert by_path["CLAUDE.md"]["requests"] == 2


def test_build_report_records_total_vs_chat_with_stats_differ():
    records = [_chat_row(1), {"path": "/v1/models"}, {"path": "/v1/models"}]
    out = report.build_report(records, records_total=len(records))
    assert out["records_total"] == 3
    assert out["chat_with_content_stats"] == 1


def test_per_request_summary_stats_avg_median_min_max():
    records = [_chat_row(1, chars=100), _chat_row(2, chars=200), _chat_row(3, chars=300)]
    out = report.build_report(records)
    pr = out["per_request"]["message_chars"]
    assert pr["n"] == 3
    assert pr["avg"] == 200.0
    assert pr["median"] == 200
    assert pr["min"] == 100
    assert pr["max"] == 300
