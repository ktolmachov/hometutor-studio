"""Quick triage of LLM provider errors recorded in cost logs.

Use: ``python scripts/llm_errors_today.py``
     ``python scripts/llm_errors_today.py --date 2026-05-11``
     ``python scripts/llm_errors_today.py --last 5``
     ``python scripts/llm_errors_today.py --all``    (scan every cost_logs_*.jsonl)

Reads ``logs/cost_logs/cost_logs_YYYY-MM-DD.jsonl`` and groups records with
``status=="ERR"`` by ``(model, error_type)``. Stage is inferred from
``prompt_type`` / ``message_preview`` when present.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_DIR = PROJECT_ROOT / "logs" / "cost_logs"


def _iter_log_files(log_dir: Path, target_date: str | None, scan_all: bool) -> list[Path]:
    if scan_all:
        return sorted(log_dir.glob("cost_logs_*.jsonl"))
    if target_date is None:
        target_date = date.today().isoformat()
    path = log_dir / f"cost_logs_{target_date}.jsonl"
    return [path] if path.exists() else []


def _iter_records(paths: Iterable[Path]) -> Iterable[dict[str, Any]]:
    for path in paths:
        try:
            with path.open("r", encoding="utf-8") as fh:
                for line_no, raw in enumerate(fh, 1):
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        record = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    record["_source_file"] = path.name
                    record["_line_no"] = line_no
                    yield record
        except OSError as e:
            print(f"warn: cannot read {path}: {e}", file=sys.stderr)


def _infer_stage(record: dict[str, Any]) -> str:
    stage = record.get("stage")
    if isinstance(stage, str) and stage:
        return stage
    prompt_type = record.get("prompt_type")
    if isinstance(prompt_type, str) and prompt_type:
        return prompt_type
    preview = (
        ((record.get("prompt_stats") or {}).get("message_preview") or [{}])[0].get("preview")
        or ""
    )
    if "Smart Study Router" in preview or "Почему сейчас" in preview:
        return "ssr_why_now"
    if "квиз" in preview.lower() or "quiz" in preview.lower():
        return "quiz"
    return "unknown"


def _format_ts(ts: str | None) -> str:
    if not ts:
        return "-"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    except ValueError:
        return ts


def summarize(records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    err_records = [r for r in records if r.get("status") == "ERR"]
    groups: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "last_ts": "", "last_message": "", "last_file": "", "last_line": 0}
    )
    for r in err_records:
        key = (r.get("model") or "?", r.get("error_type") or "?", _infer_stage(r))
        slot = groups[key]
        slot["count"] += 1
        ts = r.get("timestamp") or ""
        if ts >= slot["last_ts"]:
            slot["last_ts"] = ts
            slot["last_message"] = (r.get("error_message") or "")[:200]
            slot["last_file"] = r.get("_source_file", "")
            slot["last_line"] = r.get("_line_no", 0)
    grouped = [
        {"model": m, "error_type": et, "stage": st, **slot}
        for (m, et, st), slot in groups.items()
    ]
    grouped.sort(key=lambda x: (-x["count"], x["last_ts"]))
    return grouped, err_records


def print_table(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print("no LLM errors (status=ERR) in scanned files")
        return
    headers = ["count", "model", "error_type", "stage", "last_seen", "last_message"]
    widths = {h: len(h) for h in headers}
    formatted: list[dict[str, str]] = []
    for row in rows:
        f = {
            "count": str(row["count"]),
            "model": str(row["model"]),
            "error_type": str(row["error_type"]),
            "stage": str(row["stage"]),
            "last_seen": _format_ts(row["last_ts"]),
            "last_message": row["last_message"],
        }
        formatted.append(f)
        for h in headers:
            widths[h] = max(widths[h], len(f[h]))
    line = "  ".join(h.ljust(widths[h]) for h in headers)
    print(line)
    print("  ".join("-" * widths[h] for h in headers))
    for f in formatted:
        print("  ".join(f[h].ljust(widths[h]) for h in headers))


def print_last(records: list[dict[str, Any]], n: int) -> None:
    if not records:
        return
    print()
    print(f"--- last {min(n, len(records))} ERR records ---")
    for r in records[-n:]:
        print(
            f"[{_format_ts(r.get('timestamp'))}] "
            f"{r.get('model')} {r.get('error_type')} stage={_infer_stage(r)} "
            f"file={r.get('_source_file')}:{r.get('_line_no')}"
        )
        msg = r.get("error_message") or ""
        if msg:
            print(f"    message: {msg[:300]}")
        provider_error = r.get("provider_error") or {}
        if provider_error:
            print(f"    provider_error: {json.dumps(provider_error, ensure_ascii=False)[:300]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="YYYY-MM-DD; defaults to today (UTC)")
    parser.add_argument("--all", action="store_true", help="scan all cost_logs_*.jsonl files")
    parser.add_argument("--last", type=int, default=0, help="also print N most recent ERR records")
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=DEFAULT_LOG_DIR,
        help=f"override cost logs directory (default: {DEFAULT_LOG_DIR})",
    )
    args = parser.parse_args()

    paths = _iter_log_files(args.log_dir, args.date, args.all)
    if not paths:
        target = args.date or date.today().isoformat()
        print(f"no cost log file for {target} in {args.log_dir}", file=sys.stderr)
        return 1

    print(f"scanning: {', '.join(p.name for p in paths)}")
    grouped, err_records = summarize(_iter_records(paths))
    print_table(grouped)
    if args.last > 0:
        print_last(err_records, args.last)
    return 0


if __name__ == "__main__":
    sys.exit(main())
