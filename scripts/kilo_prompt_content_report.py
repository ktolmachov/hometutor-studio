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
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _load_records(path: Path, last: int | None = None) -> list[dict[str, Any]]:
    """Load all JSONL dict rows. ``last`` is applied to *chat* records in
    :func:`build_report`, never to raw rows — otherwise non-chat routes
    (/v1/models, health checks) inside the tail window silently shrink the
    chat sample below the requested N."""
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _merge_int_maps(dst: dict[str, int], src: Any) -> None:
    if not isinstance(src, dict):
        return
    for k, v in src.items():
        try:
            dst[str(k)] += int(v)
        except (TypeError, ValueError):
            continue


def _merge_path_rows(dst: dict[str, dict[str, int]], rows: Any) -> None:
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


def build_report(records: list[dict[str, Any]], last: int | None = None) -> dict[str, Any]:
    chat = [
        r
        for r in records
        if str(r.get("path") or "").startswith("/v1/chat/completions") and isinstance(r.get("content_stats"), dict)
    ]
    if last is not None and last > 0:
        chat = chat[-last:]
    role: dict[str, int] = defaultdict(int)
    kind: dict[str, int] = defaultdict(int)
    frag: dict[str, int] = defaultdict(int)
    ext: dict[str, int] = defaultdict(int)
    paths: dict[str, dict[str, int]] = {}
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
        {"path": p, "chars": v["chars"], "hits": v["hits"], "est_tok": v["chars"] // 4}
        for p, v in paths.items()
    ]
    path_rows.sort(key=lambda r: int(r["chars"]), reverse=True)

    agents_hits = [r for r in path_rows if "agents.md" in str(r["path"]).lower() or "claude.md" in str(r["path"]).lower()]

    return {
        "records_total": len(records),
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

    lines = [
        "=== kilo_prompt_content_report ===",
        f"records={report['records_total']} chat_with_stats={report['chat_with_content_stats']}",
        f"usage_in_sum={report['usage_prompt_tokens_sum']} avg={report['usage_prompt_tokens_avg']} "
        f"(n={report['usage_prompt_requests']})",
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
    lines.append("-- top paths (window heuristic ±200 chars; relative rank, not file bytes) --")
    for row in report["top_paths"][:25]:
        lines.append(
            f"  {row['chars']:>10} (~{row['est_tok']} tok) hits={row['hits']:<4}  {row['path']}"
        )
    lines.append("-- top extensions --")
    for row in report["top_extensions"][:15]:
        lines.append(f"  {row['chars']:>10} (~{row['est_tok']} tok)  {row['key']}")
    lines.append("-- AGENTS/CLAUDE path hits --")
    for row in report["agents_claude_mentions"][:15]:
        lines.append(f"  {row['chars']:>10} hits={row['hits']:<4}  {row['path']}")
    lines.append("-- top tool schemas --")
    for row in report["top_tools_schema"][:15]:
        lines.append(f"  {row['chars']:>10} (~{row['est_tok']} tok)  {row['key']}")
    lines.append("=== end ===")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, default=ROOT / "logs" / "kilo_relay.jsonl")
    parser.add_argument("--last", type=int, default=80, help="Only last N JSONL records (0=all)")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)
    last = None if args.last == 0 else args.last
    records = _load_records(args.log)
    report = build_report(records, last)
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
