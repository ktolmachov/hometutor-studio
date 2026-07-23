#!/usr/bin/env python3
"""Aggregate kilo_relay.jsonl content_stats → pollution report (paths / fragments / kinds).

Usage::

  .\\.venv\\Scripts\\python.exe scripts/kilo_prompt_content_report.py
  .\\.venv\\Scripts\\python.exe scripts/kilo_prompt_content_report.py --log logs/kilo_relay.jsonl --last 50
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _is_chat_record(obj: Any) -> bool:
    return (
        isinstance(obj, dict)
        and str(obj.get("path") or "").startswith("/v1/chat/completions")
        and isinstance(obj.get("content_stats"), dict)
    )


def _scan_jsonl_lines(path: Path) -> Any:
    """Yield ``(obj, kind)`` for every non-blank line, ``kind`` one of
    ``"dict"`` / ``"invalid_json"`` / ``"non_dict"``. ``obj`` is ``None`` for
    ``"invalid_json"``. No full-file materialization."""
    if not path.is_file():
        return
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                yield None, "invalid_json"
                continue
            yield obj, ("dict" if isinstance(obj, dict) else "non_dict")


def collect_chat_records(path: Path, last: int | None = None) -> tuple[dict[str, int], list[dict[str, Any]]]:
    """Stream the JSONL and keep only the last N *chat* records.

    Uses a bounded ``deque(maxlen=last)`` so a large/growing log is never fully
    held in memory, and ``last`` slices the chat sample (not raw rows): non-chat
    routes in the tail window can no longer shrink the sample below N.

    A partially corrupted log must not silently look like a clean, smaller one:
    every non-blank line is classified, so malformed JSON and non-dict JSON
    (valid but not an object) are counted rather than vanishing without a
    trace. Returns ``(counters, chat_records)`` where ``counters`` has:
    ``lines_total`` (all non-blank lines), ``dict_records`` (valid JSON objects,
    the historical "records_total" meaning), ``invalid_json``, ``non_dict_records``,
    ``chat_records_seen`` (every chat-completions row with ``content_stats``,
    scanned across the *whole* file, before the tail slice), ``chat_with_stats``
    (len of the returned chat sample — always <= ``last`` when ``last`` is set,
    so on its own it tells you the sample size, not how much instrumented
    traffic actually exists).
    """
    counters = {
        "lines_total": 0,
        "dict_records": 0,
        "invalid_json": 0,
        "non_dict_records": 0,
        "chat_records_seen": 0,
    }
    chat: deque[dict[str, Any]] = deque(maxlen=last) if last and last > 0 else deque()
    for obj, kind in _scan_jsonl_lines(path):
        counters["lines_total"] += 1
        if kind == "invalid_json":
            counters["invalid_json"] += 1
            continue
        if kind == "non_dict":
            counters["non_dict_records"] += 1
            continue
        counters["dict_records"] += 1
        if _is_chat_record(obj):
            counters["chat_records_seen"] += 1
            chat.append(obj)
    counters["chat_with_stats"] = len(chat)
    return counters, list(chat)


def _merge_int_maps(dst: dict[str, int], src: Any) -> None:
    if not isinstance(src, dict):
        return
    for k, v in src.items():
        try:
            dst[str(k)] += int(v)
        except (TypeError, ValueError):
            continue


def _merge_path_rows(dst: dict[str, dict[str, int]], rows: Any) -> None:
    """Merge one request's ``path_chars`` rows into the aggregate.

    ``hits`` sums per-*message* mentions (one request can rack up several hits
    on its own if a path is named in multiple messages), so a high aggregate
    ``hits`` does not imply the path appeared in that many distinct requests.
    Callers that need "how many requests mentioned this path at least once"
    must count separately (see ``requests_with_path`` in ``build_report``).
    """
    if not isinstance(rows, list):
        return
    for row in rows:
        if not isinstance(row, dict) or not row.get("path"):
            continue
        key = str(row["path"])
        slot = dst.setdefault(key, {"chars": 0, "hits": 0})
        try:
            slot["chars"] += int(row.get("chars") or 0)
            slot["hits"] += int(row.get("hits") or 0)
        except (TypeError, ValueError):
            continue


def _summary_stats(values: list[int | float]) -> dict[str, Any]:
    """avg / median / min / max / n for a per-request metric."""
    nums = [v for v in values if isinstance(v, (int, float))]
    if not nums:
        return {"n": 0, "avg": None, "median": None, "min": None, "max": None}
    ordered = sorted(nums)
    mid = len(ordered) // 2
    median = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
    return {
        "n": len(nums),
        "avg": round(sum(nums) / len(nums), 1),
        "median": round(median, 1),
        "min": min(nums),
        "max": max(nums),
    }


def build_report(
    records: list[dict[str, Any]],
    last: int | None = None,
    records_total: int | None = None,
) -> dict[str, Any]:
    chat = [r for r in records if _is_chat_record(r)]
    if last is not None and last > 0:
        chat = chat[-last:]
    role: dict[str, int] = defaultdict(int)
    kind: dict[str, int] = defaultdict(int)
    frag: dict[str, int] = defaultdict(int)
    ext: dict[str, int] = defaultdict(int)
    paths: dict[str, dict[str, int]] = {}
    requests_with_path: dict[str, int] = defaultdict(int)
    tools_chars: dict[str, int] = defaultdict(int)
    usage_in = 0
    usage_n = 0
    req_msg_chars: list[int] = []
    req_msg_counts: list[int] = []
    req_prompt_tokens: list[int] = []

    for rec in chat:
        cs = rec.get("content_stats") or {}
        src = cs.get("original") or cs.get("forwarded") or {}
        if not isinstance(src, dict):
            continue
        total_chars = src.get("total_message_chars")
        if not isinstance(total_chars, (int, float)):
            total_chars = sum(int(v) for v in (src.get("role_chars") or {}).values() if isinstance(v, (int, float)))
        req_msg_chars.append(int(total_chars))
        if isinstance(src.get("messages_count"), (int, float)):
            req_msg_counts.append(int(src["messages_count"]))
        _merge_int_maps(role, src.get("role_chars"))
        _merge_int_maps(kind, src.get("kind_chars"))
        _merge_int_maps(frag, src.get("fragment_chars"))
        _merge_int_maps(ext, src.get("ext_chars"))
        _merge_path_rows(paths, src.get("path_chars"))
        # "One request" here means one element of `chat` (one instrumented
        # JSONL row that passed `_is_chat_record`) — a row count, not a dedup
        # by `request_id`. Two rows sharing the same `request_id` (e.g. a
        # client-side retry logged twice) each still count toward
        # `requests_with_path` / `chat_with_content_stats`; nothing in this
        # module reads `request_id`. Verified against the live
        # logs/kilo_relay.jsonl (2026-07-23): 248/248 chat rows have a
        # present, unique `request_id` and both `content_stats.original` and
        # `.forwarded` populated — that is a property of the current relay's
        # logging, not an invariant this code enforces or checks.
        #
        # `seen_this_record` guards against a single record's own
        # `path_chars` list naming the same path twice (defensive against a
        # hand-edited or replayed --json-out file; `analyze_chat_payload`'s
        # own output cannot produce this since it builds `path_chars` from a
        # dict keyed by path) — without it, a duplicated row would inflate
        # `requests_with_path` past the actual number of distinct records.
        path_rows_this_record = src.get("path_chars")
        if isinstance(path_rows_this_record, list):
            seen_this_record: set[str] = set()
            for row in path_rows_this_record:
                if isinstance(row, dict) and row.get("path"):
                    key = str(row["path"])
                    if key not in seen_this_record:
                        seen_this_record.add(key)
                        requests_with_path[key] += 1
        tools = src.get("tools") if isinstance(src.get("tools"), dict) else {}
        for row in tools.get("by_name") or []:
            if isinstance(row, dict) and row.get("name"):
                try:
                    tools_chars[str(row["name"])] += int(row.get("chars") or 0)
                except (TypeError, ValueError):
                    pass
        usage = (rec.get("response") or {}).get("usage") if isinstance(rec.get("response"), dict) else None
        if isinstance(usage, dict) and usage.get("prompt_tokens") is not None:
            try:
                pt = int(usage["prompt_tokens"])
                usage_in += pt
                usage_n += 1
                req_prompt_tokens.append(pt)
            except (TypeError, ValueError):
                pass

    def top_map(m: dict[str, int], n: int = 25) -> list[dict[str, Any]]:
        items = sorted(m.items(), key=lambda kv: kv[1], reverse=True)[:n]
        return [{"key": k, "chars": v, "est_tok": v // 4} for k, v in items]

    path_rows = [
        {
            "path": p,
            "chars": v["chars"],
            "hits": v["hits"],
            "requests": requests_with_path.get(p, 0),
            "est_tok": v["chars"] // 4,
        }
        for p, v in paths.items()
    ]
    path_rows.sort(key=lambda r: int(r["chars"]), reverse=True)

    agents_hits = [r for r in path_rows if "agents.md" in str(r["path"]).lower() or "claude.md" in str(r["path"]).lower()]

    return {
        "records_total": records_total if records_total is not None else len(records),
        "chat_with_content_stats": len(chat),
        "note": "top_* values are AGGREGATE sums across all chat requests in the "
        "sample, NOT the cost of a single prompt; divide by per_request.*.n or "
        "read per_request for a one-prompt view.",
        "per_request": {
            "message_chars": _summary_stats(req_msg_chars),
            "messages_count": _summary_stats(req_msg_counts),
            "prompt_tokens": _summary_stats(req_prompt_tokens),
        },
        "usage_prompt_tokens_sum": usage_in,
        "usage_prompt_requests": usage_n,
        "usage_prompt_tokens_avg": round(usage_in / usage_n, 1) if usage_n else None,
        "top_roles": top_map(role),
        "top_kinds": top_map(kind),
        "top_fragments": top_map(frag),
        "top_extensions": top_map(ext),
        "top_paths": path_rows[:40],
        "top_tools_schema": top_map(tools_chars),
        "agents_claude_mentions": agents_hits[:20],
    }


def render_text(report: dict[str, Any]) -> str:
    pr = report.get("per_request", {})

    def _fmt(stats: dict[str, Any], unit: str) -> str:
        if not stats or not stats.get("n"):
            return "n=0"
        return (
            f"n={stats['n']} avg={stats['avg']}{unit} median={stats['median']}{unit} "
            f"min={stats['min']}{unit} max={stats['max']}{unit}"
        )

    scan = report.get("scan")
    lines = [
        "=== kilo_prompt_content_report ===",
        f"records={report['records_total']} chat_with_stats={report['chat_with_content_stats']}",
        f"usage_in_sum={report['usage_prompt_tokens_sum']} avg={report['usage_prompt_tokens_avg']} "
        f"(n={report['usage_prompt_requests']})",
    ]
    if scan:
        lines.append(
            "-- log scan (lines that vanished are counted, not hidden) --"
        )
        lines.append(
            f"  lines_total={scan['lines_total']} dict_records={scan['dict_records']} "
            f"invalid_json={scan['invalid_json']} non_dict_records={scan['non_dict_records']} "
            f"chat_records_seen={scan.get('chat_records_seen', '?')}"
        )
        if scan.get("chat_records_seen", 0) > report["chat_with_content_stats"]:
            lines.append(
                f"  NOTE: {scan['chat_records_seen']} instrumented chat requests exist in the "
                f"full file; this sample is only the last {report['chat_with_content_stats']} "
                "of those (--last), not every instrumented request."
            )
        if scan["invalid_json"] or scan["non_dict_records"]:
            lines.append(
                f"  NOTE: {scan['invalid_json']} malformed-JSON line(s) and "
                f"{scan['non_dict_records']} non-object JSON line(s) were skipped — "
                "this report may undercount a partially corrupted log."
            )
    lines += [
        "",
        "-- per request (one-prompt view) --",
        f"  prompt_tokens : {_fmt(pr.get('prompt_tokens', {}), '')}",
        f"  message_chars : {_fmt(pr.get('message_chars', {}), '')}",
        f"  messages_count: {_fmt(pr.get('messages_count', {}), '')}",
        "",
        "NOTE: top_* below are AGGREGATE sums across ALL chat requests in the sample,",
        "      not the cost of one prompt. Use per-request block above for a single turn.",
        "",
        "-- top kinds (aggregate sums) --",
    ]
    for row in report["top_kinds"][:15]:
        lines.append(f"  {row['chars']:>10} (~{row['est_tok']} tok)  {row['key']}")
    lines.append("-- top fragments --")
    for row in report["top_fragments"][:15]:
        lines.append(f"  {row['chars']:>10} (~{row['est_tok']} tok)  {row['key']}")
    lines.append(
        "-- top paths (window heuristic +/-200 chars; relative rank, not file bytes; "
        "hits=message-level mentions, can exceed request count; reqs=distinct requests "
        "containing >=1 mention) --"
    )
    for row in report["top_paths"][:25]:
        lines.append(
            f"  {row['chars']:>10} (~{row['est_tok']} tok) hits={row['hits']:<4} "
            f"reqs={row.get('requests', '?'):<4}  {row['path']}"
        )
    lines.append("-- top extensions --")
    for row in report["top_extensions"][:15]:
        lines.append(f"  {row['chars']:>10} (~{row['est_tok']} tok)  {row['key']}")
    lines.append("-- AGENTS/CLAUDE path hits (reqs=distinct requests, not message-level hits) --")
    for row in report["agents_claude_mentions"][:15]:
        lines.append(
            f"  {row['chars']:>10} hits={row['hits']:<4} reqs={row.get('requests', '?'):<4}  {row['path']}"
        )
    lines.append("-- top tool schemas --")
    for row in report["top_tools_schema"][:15]:
        lines.append(f"  {row['chars']:>10} (~{row['est_tok']} tok)  {row['key']}")
    lines.append("=== end ===")
    return "\n".join(lines)


def _non_negative_int(raw: str) -> int:
    value = int(raw)
    if value < 0:
        raise argparse.ArgumentTypeError(f"--last must be >= 0, got {value}")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, default=ROOT / "logs" / "kilo_relay.jsonl")
    parser.add_argument(
        "--last",
        type=_non_negative_int,
        default=80,
        help="Use the last N instrumented chat-completion records, i.e. rows with "
        "content_stats (0 = all). Non-chat rows (e.g. /v1/models) are not counted "
        "toward N.",
    )
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)
    if not args.log.is_file():
        print(
            f"ERROR: log file not found: {args.log} — check --log / the relay's "
            "configured log path (this is NOT the same as 'no chat requests yet').",
            file=sys.stderr,
        )
        return 3
    last = None if args.last == 0 else args.last
    counters, chat_records = collect_chat_records(args.log, last)
    # chat_records is already sliced to the last N chat rows by the deque; pass
    # last=None so build_report does not slice a second time.
    report = build_report(chat_records, last=None, records_total=counters["dict_records"])
    report["scan"] = counters
    text = render_text(report)
    print(text)
    if report["chat_with_content_stats"] == 0:
        print(
            "NOTE: no content_stats yet — restart relay (KILO_RELAY_CONTENT_STATS=1 default) "
            "and send a few chat requests. Refusing --json-out so an empty report cannot "
            "overwrite a previous good logs/kilo_content_report.json.",
            file=sys.stderr,
        )
        return 2
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {args.json_out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
