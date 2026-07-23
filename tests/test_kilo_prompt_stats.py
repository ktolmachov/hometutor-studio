"""Tests for scripts/_kilo_prompt_stats.py and content-stats helpers."""

from __future__ import annotations

import inspect
import io
import json
import re
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


def test_path_char_contributions_ignores_doubled_escape_sequences():
    """Regression for the 'y://n' / 'e://n' false positives an audit found
    outranking AGENTS.md in a real report: a single letter + ':' + two literal
    backslash characters + 'n' (source code showing a raw `\\n` escape as text,
    not an actual newline) used to satisfy the Windows-path branch and got
    normalized (backslash -> '/') into junk keys that polluted top_paths."""
    bs = chr(92)
    text = "some code shows y:" + bs + bs + "n and e:" + bs + bs + "n as literal escapes, not paths"
    contrib = path_char_contributions(text)
    assert not any(k.lower() in {"y://n", "e://n", "y:/n", "e:/n", "n://n", "n:/n"} for k in contrib)


def test_path_char_contributions_ignores_single_backslash_escape_stubs():
    """``y:\\n`` (one backslash) must not rank as a Windows path either."""
    bs = chr(92)
    text = "escape stubs y:" + bs + "n e:" + bs + "t n:" + bs + "n in source"
    contrib = path_char_contributions(text)
    assert not any(re.match(r"^[a-z]:/{1,2}[ntr]$", k, re.I) for k in contrib)


def test_path_char_contributions_still_finds_real_windows_paths_with_single_backslashes():
    """Uses a generic module filename, not AGENTS.md: AGENTS.md/CLAUDE.md/etc.
    also match via a separate basename-only alternative in _PATH_RE, so a test
    that only checks for those names could pass even if the Windows-abs
    branch itself were completely broken. module.py has no such shortcut."""
    bs = chr(92)
    text = "read " + "D:" + bs + "Projects" + bs + "hometutor-studio" + bs + "module.py" + " please"
    contrib = path_char_contributions(text)
    assert list(contrib.keys()) == ["D:/Projects/hometutor-studio/module.py"]


def test_path_char_contributions_finds_single_segment_drive_root_path():
    """Regression: an earlier version of _PATH_RE required >=2 directory
    segments or a file extension (to reject 'y:\\n'-style escape stubs),
    which also rejected genuine single-segment drive-root paths like
    C:\\Windows. Rejecting junk is now is_plausible_path_key()'s job, not the
    regex's, so single-segment real paths are found again."""
    bs = chr(92)
    text = "look in " + "C:" + bs + "Windows" + " for files"
    contrib = path_char_contributions(text)
    assert list(contrib.keys()) == ["C:/Windows"]


def test_path_char_contributions_finds_json_re_escaped_windows_path():
    """A path shown as JSON-re-escaped text (each backslash doubled, as when a
    JSON blob containing a Windows path is itself embedded as a string and
    re-serialized) must still be found and normalized to a clean single-slash
    key, not rejected the way pure escape-stub doubling ('y:\\n' -> 'y://n')
    is rejected. normalize_path_key's multi-slash collapse turns the doubled
    separators into single '/' the same as for any other match."""
    bs = chr(92)
    text = "path is " + "D:" + bs + bs + "Projects" + bs + bs + "report.txt" + " ok"
    contrib = path_char_contributions(text)
    assert list(contrib.keys()) == ["D:/Projects/report.txt"]


def test_normalize_path_key_collapses_multi_slash():
    assert normalize_path_key("scripts////compute_trusted_route_rate.py/") == (
        "scripts/compute_trusted_route_rate.py"
    )


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

    # When forwarded is present, fragments come from it (post-strip); empty
    # forwarded fragments must not fall back to original skills/rules noise.
    glance_fwd = relay._content_stats_glance(
        {
            "original": {
                "kind_chars": {"tool_result": 9000},
                "fragment_chars": {"available_skills": 622},
            },
            "forwarded": {
                "kind_chars": {"tool_result": 100},
                "fragment_chars": {},
            },
        }
    )
    assert "top_kind=tool_result:9000" in glance_fwd
    assert not any(p.startswith("top_frag=") for p in glance_fwd)

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


def test_session_health_rate_not_diluted_by_records_missing_the_field():
    """session_health was added after some historical rows were already
    logged; those rows have no `session_health` key at all. The rate must be
    computed over records that actually carry the field, not over every
    chat record in the sample — otherwise mixing pre-/post-upgrade rows in
    one --last window silently pulls the rate toward 0 with no indication."""
    with_health_bloated = {
        "path": "/v1/chat/completions",
        "content_stats": {"original": {"role_chars": {"user": 10}}},
        "session_health": {"recommend_new_chat": True},
    }
    with_health_ok = {
        "path": "/v1/chat/completions",
        "content_stats": {"original": {"role_chars": {"user": 10}}},
        "session_health": {"recommend_new_chat": False},
    }
    pre_upgrade_no_health_field = {
        "path": "/v1/chat/completions",
        "content_stats": {"original": {"role_chars": {"user": 10}}},
    }
    out = report.build_report([with_health_bloated, with_health_ok, pre_upgrade_no_health_field])
    sh = out["session_health"]
    assert sh["records_with_session_health"] == 2
    assert sh["recommend_new_chat_count"] == 1
    assert sh["recommend_new_chat_rate"] == 0.5  # not 1/3


def test_session_health_rate_not_diluted_by_unknown_level_records():
    """session_health with level="unknown" (KILO_RELAY_CONTENT_STATS was off,
    or a non-chat route) has the *field* present but recommend_new_chat is
    always False by construction — must be excluded from the denominator the
    same way a missing field is, not counted as "measured and healthy"."""
    measured_bloated = {
        "path": "/v1/chat/completions",
        "content_stats": {"original": {"role_chars": {"user": 10}}},
        "session_health": {"level": "warn", "recommend_new_chat": True},
    }
    not_measured = {
        "path": "/v1/chat/completions",
        "content_stats": {"original": {"role_chars": {"user": 10}}},
        "session_health": {"level": "unknown", "recommend_new_chat": False},
    }
    out = report.build_report([measured_bloated, not_measured])
    sh = out["session_health"]
    assert sh["records_with_session_health"] == 1
    assert sh["recommend_new_chat_count"] == 1
    assert sh["recommend_new_chat_rate"] == 1.0  # not 0.5


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


class _NarrowEncodingStdout:
    """Stands in for a real Windows console on a narrow codepage (cp1252):
    writing a character outside that codepage's repertoire raises
    UnicodeEncodeError, same as the real crash this test guards against."""

    def __init__(self):
        self.encoding = "cp1252"
        self.buffer = io.BytesIO()

    def write(self, s: str) -> int:
        encoded = s.encode(self.encoding)  # raises UnicodeEncodeError, matching a real cp1252 stream
        self.buffer.write(encoded)  # mirrors a real text stream's underlying byte buffer
        return len(s)

    def flush(self) -> None:
        pass


def test_print_safe_does_not_crash_on_narrow_console_encoding(monkeypatch):
    """Regression for the 2026-07-23 P0: a printed report containing a
    character outside cp1252's repertoire (e.g. U+226B '>>' math symbol, or
    any non-ASCII byte surfacing from real log/path content) must degrade
    gracefully on a narrow-encoding console, not raise UnicodeEncodeError and
    kill the whole CLI run."""
    fake_stdout = _NarrowEncodingStdout()
    monkeypatch.setattr(sys, "stdout", fake_stdout)
    text_with_unencodable_char = "top paths: original ≫ threshold"  # U+226B, not in cp1252
    report._print_safe(text_with_unencodable_char)  # must not raise
    written = fake_stdout.buffer.getvalue().decode("cp1252", errors="replace")
    assert "top paths" in written
    assert "threshold" in written


def test_report_main_runs_end_to_end_on_narrow_console_encoding(tmp_path: Path, monkeypatch):
    """End-to-end: main() over a real chat log, with stdout forced to the
    same narrow encoding that crashed the CLI in production, must complete
    and return the normal exit code — not just the isolated _print_safe unit."""
    log = tmp_path / "chat.jsonl"
    log.write_text(
        "\n".join(json.dumps(_chat_row(i)) for i in range(3)) + "\n",
        encoding="utf-8",
    )
    fake_stdout = _NarrowEncodingStdout()
    monkeypatch.setattr(sys, "stdout", fake_stdout)
    rc = report.main(["--log", str(log)])
    assert rc == 0
    written = fake_stdout.buffer.getvalue().decode("cp1252", errors="replace")
    assert "kilo_prompt_content_report" in written


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


def test_build_report_requests_counts_rows_not_unique_request_ids():
    """`requests` in build_report counts elements of the chat list (JSONL
    rows), not distinct `request_id` values — this module never reads
    `request_id`. Two rows sharing one request_id (e.g. a logged retry) must
    still count as 2 toward `requests`, matching the documented semantics in
    build_report()'s loop comment rather than silently deduping by ID."""
    row = {
        "path": "/v1/chat/completions",
        "request_id": "same-id",
        "content_stats": {"original": {"path_chars": [{"path": "AGENTS.md", "chars": 100, "hits": 1}]}},
    }
    out = report.build_report([dict(row), dict(row)])
    by_path = {r["path"]: r for r in out["top_paths"]}
    assert by_path["AGENTS.md"]["requests"] == 2


def test_build_report_requests_not_inflated_by_duplicate_path_row_within_one_record():
    """A single record's own path_chars listing the same path twice (malformed
    / hand-edited input — analyze_chat_payload's own output cannot do this,
    since it builds path_chars from a dict keyed by path) must count as one
    request for that path, not two."""
    rec = {
        "path": "/v1/chat/completions",
        "content_stats": {
            "original": {
                "path_chars": [
                    {"path": "AGENTS.md", "chars": 100, "hits": 1},
                    {"path": "AGENTS.md", "chars": 50, "hits": 1},
                ]
            }
        },
    }
    out = report.build_report([rec])
    by_path = {r["path"]: r for r in out["top_paths"]}
    assert by_path["AGENTS.md"]["requests"] == 1


def test_build_report_normalizes_historical_path_keys_before_validating():
    """Regression: an old record logged before normalize_path_key() collapsed
    repeated slashes can store "path" as e.g. "D:////Projects////hometutor"
    (backslash -> "/" replacement with no multi-slash collapse, from an older
    _kilo_prompt_stats.py). That raw string contains a literal "://"
    substring purely as slash-doubling noise, which is_plausible_path_key()
    would reject as drive+doubled-slash junk if checked before normalizing.
    build_report() must normalize first so this legitimate historical path
    survives — under its clean normalized key, not the raw one."""
    historical_unnormalized_record = {
        "path": "/v1/chat/completions",
        "content_stats": {
            "original": {
                "path_chars": [{"path": "D:////Projects////hometutor", "chars": 400, "hits": 2}],
            }
        },
    }
    duplicate_but_already_normalized = {
        "path": "/v1/chat/completions",
        "content_stats": {
            "original": {
                "path_chars": [{"path": "D:/Projects/hometutor", "chars": 100, "hits": 1}],
            }
        },
    }
    out = report.build_report([historical_unnormalized_record, duplicate_but_already_normalized])
    by_path = {r["path"]: r for r in out["top_paths"]}
    assert "D:////Projects////hometutor" not in by_path
    assert by_path["D:/Projects/hometutor"]["chars"] == 500  # merged, not two separate rows
    assert by_path["D:/Projects/hometutor"]["requests"] == 2


def test_scan_jsonl_lines_is_a_generator_not_a_full_materialization():
    """Guards the streaming design: _scan_jsonl_lines must stay a generator
    so collect_chat_records() never holds the full file in memory, however
    large logs/kilo_relay.jsonl grows."""
    assert inspect.isgeneratorfunction(report._scan_jsonl_lines)


def test_collect_chat_records_correct_on_large_synthetic_log(tmp_path: Path):
    """Correctness at a scale well past any real capture (5000 chat rows,
    tail-sliced to 50) — the deque(maxlen=N) design should hold regardless of
    file size, not just on the handful of rows the other tests use."""
    log = tmp_path / "big.jsonl"
    rows = [_chat_row(i) for i in range(5000)]
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    counters, chat = report.collect_chat_records(log, last=50)
    assert counters["lines_total"] == 5000
    assert counters["chat_records_seen"] == 5000
    assert counters["chat_with_stats"] == 50
    assert len(chat) == 50
    assert [r["content_stats"]["original"]["messages_count"] for r in chat] == list(range(4950, 5000))


def test_build_report_top_lists_are_deterministic_across_repeated_calls():
    """Same input must yield the same ordering every time (no hash-order
    flakiness in top_paths/top_kinds/top_fragments), so a re-run of the report
    for evidence purposes is reproducible, not just "usually the same"."""
    records = [
        _chat_row(1),
        {
            "path": "/v1/chat/completions",
            "content_stats": {
                "original": {
                    "kind_chars": {"tool_result": 500, "system": 500},
                    "path_chars": [
                        {"path": "AGENTS.md", "chars": 500, "hits": 1},
                        {"path": "CLAUDE.md", "chars": 500, "hits": 1},
                    ],
                }
            },
        },
    ]
    first = report.build_report(list(records))
    second = report.build_report(list(records))
    assert first["top_kinds"] == second["top_kinds"]
    assert first["top_paths"] == second["top_paths"]


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
