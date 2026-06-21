#!/usr/bin/env python3
"""Summarize LLM cost log JSONL files with prompt/context diagnostics."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COST_LOG_DIR = ROOT / "logs" / "cost_logs"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def load_cost_rows(log_dir: Path, *, limit_files: int | None = None) -> list[dict[str, Any]]:
    files = sorted(log_dir.glob("cost_logs_*.jsonl"))
    if limit_files:
        files = files[-limit_files:]
    rows: list[dict[str, Any]] = []
    for path in files:
        for row in _read_jsonl(path):
            row["_source_file"] = path.name
            rows.append(row)
    return rows


def _fmt_int(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def _top_rows(rows: list[dict[str, Any]], *, key: str, topn: int) -> list[dict[str, Any]]:
    def sort_key(row: dict[str, Any]) -> int:
        if key == "total_chars":
            return int(((row.get("prompt_stats") or {}).get("total_chars")) or 0)
        if key == "input_tokens":
            return int(row.get("input_tokens") or 0)
        return 0

    return sorted(rows, key=sort_key, reverse=True)[:topn]


def _build_summary_payload(rows: list[dict[str, Any]], *, topn: int) -> dict[str, Any]:
    total = len(rows)
    status_counts = Counter(str(row.get("status") or "UNKNOWN") for row in rows)
    model_counts = Counter(str(row.get("model") or "unknown") for row in rows)
    context_errors = [
        row
        for row in rows
        if ((row.get("provider_error") or {}).get("error_kind") == "context_length_exceeded")
    ]
    char_warning_rows = [
        row for row in rows if ((row.get("prompt_stats") or {}).get("char_limit_warning") is True)
    ]
    top_by_chars = _top_rows(rows, key="total_chars", topn=topn)
    top_by_tokens = _top_rows(rows, key="input_tokens", topn=topn)

    return {
        "records": total,
        "status_counts": dict(status_counts),
        "top_models": dict(model_counts.most_common(5)),
        "context_length_errors": len(context_errors),
        "char_limit_warnings": len(char_warning_rows),
        "top_by_chars": top_by_chars,
        "top_by_input_tokens": top_by_tokens,
        "context_length_incidents": context_errors[:topn],
    }


def build_summary(rows: list[dict[str, Any]], *, topn: int) -> str:
    if not rows:
        return "No cost log records found."

    payload = _build_summary_payload(rows, topn=topn)

    lines = [
        "LLM Cost Log Summary",
        f"Records: {payload['records']}",
        f"Statuses: {payload['status_counts']}",
        f"Top models: {payload['top_models']}",
        f"Context-length errors: {payload['context_length_errors']}",
        f"Char-limit warnings: {payload['char_limit_warnings']}",
        "",
        f"Top {topn} prompts by chars:",
    ]

    for row in payload["top_by_chars"]:
        stats = row.get("prompt_stats") or {}
        provider_error = row.get("provider_error") or {}
        lines.append(
            "  - "
            f"{row.get('timestamp')} | {row.get('model')} | status={row.get('status')} | "
            f"chars={_fmt_int(stats.get('total_chars'))} | "
            f"tokens={_fmt_int(row.get('input_tokens'))} | "
            f"messages={_fmt_int(stats.get('messages_count'))} | "
            f"pkg={row.get('package_id') or '-'} | "
            f"prompt={row.get('prompt_type') or '-'} | "
            f"err={provider_error.get('error_kind') or row.get('error_type') or '-'}"
        )

    lines.append("")
    lines.append(f"Top {topn} prompts by input tokens:")
    for row in payload["top_by_input_tokens"]:
        stats = row.get("prompt_stats") or {}
        lines.append(
            "  - "
            f"{row.get('timestamp')} | {row.get('model')} | status={row.get('status')} | "
            f"tokens={_fmt_int(row.get('input_tokens'))} | "
            f"chars={_fmt_int(stats.get('total_chars'))} | "
            f"chars/token={stats.get('chars_per_token_estimate', '-')}"
        )

    if payload["context_length_incidents"]:
        lines.append("")
        lines.append("Context-length incidents:")
        for row in payload["context_length_incidents"]:
            provider_error = row.get("provider_error") or {}
            stats = row.get("prompt_stats") or {}
            lines.append(
                "  - "
                f"{row.get('timestamp')} | actual={_fmt_int(provider_error.get('input_char_actual'))} | "
                f"limit={_fmt_int(provider_error.get('input_char_limit'))} | "
                f"chars={_fmt_int(stats.get('total_chars'))} | "
                f"tokens={_fmt_int(row.get('input_tokens'))} | "
                f"file={row.get('_source_file')}"
            )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_COST_LOG_DIR)
    parser.add_argument("--limit-files", type=int, default=7, help="Read only the last N daily JSONL files")
    parser.add_argument("--top", type=int, default=5, help="How many heavy prompts/incidents to show")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of text")
    parser.add_argument(
        "--fail-on-context-errors",
        action="store_true",
        help="Exit with code 2 if any context_length_exceeded incidents are present",
    )
    args = parser.parse_args()

    rows = load_cost_rows(args.log_dir, limit_files=args.limit_files)
    payload = _build_summary_payload(rows, topn=args.top) if rows else {
        "records": 0,
        "status_counts": {},
        "top_models": {},
        "context_length_errors": 0,
        "char_limit_warnings": 0,
        "top_by_chars": [],
        "top_by_input_tokens": [],
        "context_length_incidents": [],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(build_summary(rows, topn=args.top))

    if args.fail_on_context_errors and payload["context_length_errors"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
