#!/usr/bin/env python3
"""Static budget simulator — predict Kilo guard verdict without Kilo or relay.

Turns `scripts/_kilo_guard.evaluate_guard()` into a CLI. Given a launcher
prompt + injection fixture (the messages/tools Kilo auto-adds to a fresh
session) + optional user turn, it builds the same payload the real relay
would see and returns the verdict deterministically in milliseconds.

Subcommands:
  simulate   Build a synthetic payload and print the verdict.
  capture    Extract a captured injection fixture from a real relay JSONL.
  replay     Recompute verdict on an existing relay record (parity check).

Because the guard logic is imported from the same module the relay uses,
simulator and relay verdicts are structurally identical.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _kilo_guard import (  # noqa: E402
    GuardThresholds,
    evaluate_guard,
    summarize_body,
)


ROOT = Path(__file__).resolve().parents[1]
CHAT_PATH = "/v1/chat/completions"
LEVEL_ORDER = {"ok": 0, "warn": 1, "soft_block": 2, "hard_block": 3}
_HEADING_RE = re.compile(r"^(#{2,6})\s+(.+)$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Fixture / payload construction
# ---------------------------------------------------------------------------


def detect_fixture_info(raw: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    """Classify fixture provenance so callers can avoid overclaiming fidelity."""
    meta = raw.get("_meta", {}) if isinstance(raw.get("_meta"), dict) else {}
    source = raw.get("_source", {}) if isinstance(raw.get("_source"), dict) else {}
    if source.get("request_id") or source.get("jsonl"):
        kind = "captured_relay_fixture"
        note = "Captured from real relay JSONL; closest offline proxy to runtime injection."
    elif meta.get("fixture_kind"):
        kind = str(meta["fixture_kind"])
        note = str(meta.get("source_note") or "")
    elif "calibrated" in str(meta.get("purpose", "")).lower():
        kind = "calibrated_estimate"
        note = "Built from readable project files plus estimates; useful offline approximation."
    else:
        kind = "unknown_fixture"
        note = "Fixture provenance not declared."
    return {
        "kind": kind,
        "source_note": note,
        "path": str(path) if path else None,
    }


def load_injection_fixture(path: Path) -> dict[str, Any]:
    """Load an injection fixture. Expected shape: {messages: [...], tools: [...], model?: str}."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if "messages" not in raw or not isinstance(raw["messages"], list):
        raise ValueError(f"Fixture {path} missing 'messages' list")
    raw.setdefault("tools", [])
    raw.setdefault("model", "openai/gpt-4o-mini")
    raw["_fixture"] = detect_fixture_info(raw, path)
    return raw


def build_payload(
    fixture: dict[str, Any],
    *,
    launcher_text: str | None,
    user_turn: str | None,
    launcher_label: str = "launcher",
) -> tuple[dict[str, Any], list[tuple[str, int]]]:
    """Append launcher + user_turn as final user messages. Returns (payload, named_segments)."""
    messages = list(fixture.get("messages", []))
    segments: list[tuple[str, int]] = [
        (f"injection::{m.get('role', 'unknown')}#{i}", _content_chars(m.get("content")))
        for i, m in enumerate(messages)
    ]
    if launcher_text:
        messages.append({"role": "user", "content": launcher_text})
        segments.append((launcher_label, len(launcher_text)))
    if user_turn:
        messages.append({"role": "user", "content": user_turn})
        segments.append(("user_turn", len(user_turn)))
    payload = {
        "model": fixture.get("model", "openai/gpt-4o-mini"),
        "messages": messages,
        "tools": fixture.get("tools", []),
    }
    return payload, segments


def _content_chars(content: Any) -> int:
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return sum(len(json.dumps(p, ensure_ascii=False)) for p in content)
    return len(json.dumps(content, ensure_ascii=False)) if content is not None else 0


# ---------------------------------------------------------------------------
# Simulation + attribution
# ---------------------------------------------------------------------------


def simulate_payload(
    payload: dict[str, Any],
    *,
    thresholds: GuardThresholds,
    mode: str = "warn",
    path: str = CHAT_PATH,
) -> dict[str, Any]:
    body_text = json.dumps(payload, ensure_ascii=False)
    summary = summarize_body(body_text)
    verdict = evaluate_guard(path, body_text, summary, thresholds=thresholds, mode=mode)
    return {
        "verdict": asdict(verdict),
        "summary": {
            "body_chars": summary.get("body_chars"),
            "messages_count": summary.get("messages_count"),
            "tools_count": summary.get("tools_count"),
            "largest_message_chars": summary.get("largest_message_chars"),
            "total_message_chars": summary.get("total_message_chars"),
            "role_chars": summary.get("role_chars"),
            "estimated_tokens": summary.get("estimated_tokens"),
        },
    }


def attribute(
    payload: dict[str, Any],
    segments: list[tuple[str, int]],
    *,
    thresholds: GuardThresholds,
    mode: str,
) -> list[dict[str, Any]]:
    """Leave-one-out: remove each message, recompute level, report downgrade."""
    base = simulate_payload(payload, thresholds=thresholds, mode=mode)
    base_level = base["verdict"]["level"]
    base_order = LEVEL_ORDER[base_level]
    base_body = base["summary"]["body_chars"]
    messages: list[dict[str, Any]] = payload["messages"]
    rows: list[dict[str, Any]] = []
    for idx, msg in enumerate(messages):
        trimmed = {**payload, "messages": [m for i, m in enumerate(messages) if i != idx]}
        alt = simulate_payload(trimmed, thresholds=thresholds, mode=mode)
        alt_level = alt["verdict"]["level"]
        delta_body = base_body - alt["summary"]["body_chars"]
        rows.append(
            {
                "index": idx,
                "label": segments[idx][0] if idx < len(segments) else f"msg#{idx}",
                "role": msg.get("role", "unknown"),
                "chars": segments[idx][1] if idx < len(segments) else _content_chars(msg.get("content")),
                "contrib_body_chars": delta_body,
                "if_removed_level": alt_level,
                "would_downgrade": LEVEL_ORDER[alt_level] < base_order,
            }
        )
    rows.sort(key=lambda r: r["contrib_body_chars"], reverse=True)
    return rows


def split_launcher_by_sections(text: str, level: int = 2) -> list[tuple[str, str]]:
    anchors = [
        (m.start(), m.group(2).strip())
        for m in _HEADING_RE.finditer(text)
        if len(m.group(1)) == level
    ]
    if not anchors:
        return [("(whole launcher)", text)]
    sections: list[tuple[str, str]] = []
    if anchors[0][0] > 0:
        sections.append(("(preamble)", text[:anchors[0][0]]))
    for i, (start, title) in enumerate(anchors):
        end = anchors[i + 1][0] if i + 1 < len(anchors) else len(text)
        sections.append((title, text[start:end]))
    return sections


def attribute_sections(
    fixture: dict[str, Any],
    launcher_text: str,
    user_turn: str | None,
    *,
    thresholds: GuardThresholds,
    mode: str,
    level: int,
) -> list[dict[str, Any]]:
    sections = split_launcher_by_sections(launcher_text, level=level)
    base_payload, _ = build_payload(fixture, launcher_text=launcher_text, user_turn=user_turn)
    base = simulate_payload(base_payload, thresholds=thresholds, mode=mode)
    base_order = LEVEL_ORDER[base["verdict"]["level"]]
    base_body = int(base["summary"]["body_chars"] or 0)

    rows: list[dict[str, Any]] = []
    for title, section_text in sections:
        trimmed_launcher = launcher_text.replace(section_text, "", 1)
        alt_payload, _ = build_payload(fixture, launcher_text=trimmed_launcher, user_turn=user_turn)
        alt = simulate_payload(alt_payload, thresholds=thresholds, mode=mode)
        alt_level = alt["verdict"]["level"]
        rows.append(
            {
                "section": title,
                "chars": len(section_text),
                "contrib_body_chars": base_body - int(alt["summary"]["body_chars"] or 0),
                "if_removed_level": alt_level,
                "would_downgrade": LEVEL_ORDER[alt_level] < base_order,
            }
        )
    rows.sort(key=lambda r: r["contrib_body_chars"], reverse=True)
    return rows


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def format_report(
    sim: dict[str, Any],
    attribution_rows: list[dict[str, Any]] | None = None,
    section_attribution_rows: list[dict[str, Any]] | None = None,
    *,
    source_label: str,
    fixture_info: dict[str, Any] | None = None,
) -> str:
    v = sim["verdict"]
    s = sim["summary"]
    lines = [
        f"=== Kilo Budget Simulation: {source_label} ===",
        f"Level:          {v['level']}  (block={v['block']})",
        f"Body chars:     {s['body_chars']:,}",
        f"Messages:       {s['messages_count']}  | tools: {s['tools_count']}",
        f"Largest msg:    {s['largest_message_chars']:,}",
        f"Est. tokens:    {s['estimated_tokens']:,}",
    ]
    if fixture_info:
        lines.append(f"Fixture kind:   {fixture_info.get('kind')}")
        if fixture_info.get("source_note"):
            lines.append(f"Fixture note:   {fixture_info.get('source_note')}")
    if v["risk_flags"]:
        lines.append("Risk flags:")
        for f in v["risk_flags"]:
            lines.append(f"  - {f}")
    if v["reasons"]:
        lines.append("Reasons:")
        for r in v["reasons"]:
            lines.append(f"  - {r}")
    if attribution_rows:
        lines.append("")
        lines.append("Message-level attribution (top contributors by body chars):")
        for r in attribution_rows[:10]:
            marker = " <-- DOWNGRADES on removal" if r["would_downgrade"] else ""
            lines.append(
                f"  [{r['role']:>9}] {r['label']:<40} {r['chars']:>7,} chars"
                f"  contrib={r['contrib_body_chars']:>7,}  -> if_removed={r['if_removed_level']}{marker}"
            )
    if section_attribution_rows:
        lines.append("")
        lines.append("Section-level attribution (inside launcher):")
        for r in section_attribution_rows[:10]:
            marker = " <-- DOWNGRADES on removal" if r["would_downgrade"] else ""
            lines.append(
                f"  {r['section']:<55} {r['chars']:>7,} chars"
                f"  contrib={r['contrib_body_chars']:>7,}  -> if_removed={r['if_removed_level']}{marker}"
            )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_simulate(args: argparse.Namespace) -> int:
    thresholds = GuardThresholds.from_env() if args.thresholds_from_env else GuardThresholds()

    fixture: dict[str, Any]
    if args.injection:
        fixture = load_injection_fixture(Path(args.injection))
    else:
        fixture = {
            "messages": [],
            "tools": [],
            "model": "openai/gpt-4o-mini",
            "_fixture": {
                "kind": "empty_fixture",
                "source_note": "No injection fixture supplied.",
                "path": None,
            },
        }

    launcher_text = None
    launcher_label = "launcher"
    if args.launcher:
        launcher_path = Path(args.launcher)
        launcher_text = launcher_path.read_text(encoding="utf-8")
        launcher_label = launcher_path.name

    payload, segments = build_payload(
        fixture,
        launcher_text=launcher_text,
        user_turn=args.user_turn,
        launcher_label=launcher_label,
    )
    sim = simulate_payload(payload, thresholds=thresholds, mode=args.mode)
    attr_rows = attribute(payload, segments, thresholds=thresholds, mode=args.mode) if args.attribute else None
    section_attr_rows = None
    if args.section_attribute and launcher_text:
        section_attr_rows = attribute_sections(
            fixture,
            launcher_text,
            args.user_turn,
            thresholds=thresholds,
            mode=args.mode,
            level=args.section_level,
        )

    source = args.launcher or "(no launcher)"
    report = format_report(
        sim,
        attr_rows,
        section_attr_rows,
        source_label=source,
        fixture_info=fixture.get("_fixture"),
    )
    print(report)

    if args.json_out:
        out = {
            "source": {
                "launcher": args.launcher,
                "injection": args.injection,
                "user_turn": args.user_turn,
                "mode": args.mode,
            },
            "fixture": fixture.get("_fixture"),
            "thresholds": asdict(thresholds),
            "verdict": sim["verdict"],
            "summary": sim["summary"],
            "attribution": attr_rows,
            "section_attribution": section_attr_rows,
        }
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON report: {args.json_out}")

    if args.fail_on:
        threshold = LEVEL_ORDER[args.fail_on]
        if LEVEL_ORDER[sim["verdict"]["level"]] >= threshold:
            print(f"\nFAIL: level {sim['verdict']['level']} >= {args.fail_on}")
            return 2
    return 0


def cmd_capture(args: argparse.Namespace) -> int:
    jsonl = Path(args.from_jsonl)
    if not jsonl.exists():
        print(f"ERROR: {jsonl} does not exist", file=sys.stderr)
        return 1

    records: list[dict[str, Any]] = []
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("path") == CHAT_PATH:
            records.append(rec)

    if not records:
        print(f"ERROR: no chat records in {jsonl}", file=sys.stderr)
        return 1

    # Pick the smallest successful record — that's closest to the injection baseline alone.
    if args.probe:
        marker = args.probe
        records = [r for r in records if marker in (r.get("request", {}).get("body_raw") or "")]
        if not records:
            print(f"ERROR: no records matching probe marker {marker!r}", file=sys.stderr)
            return 1

    records.sort(key=lambda r: r.get("request", {}).get("body_chars", 10**9))
    pick = records[0]
    body_raw = pick.get("request", {}).get("body_raw")
    if not body_raw:
        print("ERROR: selected record has no body_raw (enable KILO_RELAY_FULL_BODY=1)", file=sys.stderr)
        return 1

    try:
        payload = json.loads(body_raw)
    except json.JSONDecodeError:
        print("ERROR: body_raw is not valid JSON", file=sys.stderr)
        return 1

    messages: list[Any] = payload.get("messages") or []
    # Drop trailing user turn if it contains the probe marker (simulator re-adds one).
    if args.drop_trailing_user and messages and messages[-1].get("role") == "user":
        messages = messages[:-1]

    fixture = {
        "model": payload.get("model"),
        "messages": messages,
        "tools": payload.get("tools", []),
        "_meta": {
            "fixture_kind": "captured_relay_fixture",
            "source_note": "Captured from real relay JSONL; closest offline proxy to runtime injection.",
        },
        "_source": {
            "jsonl": str(jsonl),
            "request_id": pick.get("request_id"),
            "ts": pick.get("ts"),
            "captured_body_chars": pick.get("request", {}).get("body_chars"),
        },
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Captured relay fixture → {out}")
    print(f"  messages: {len(messages)}  tools: {len(fixture['tools'])}")
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    """Recompute verdict from an existing JSONL record — parity with runtime relay."""
    jsonl = Path(args.from_jsonl)
    thresholds = GuardThresholds.from_env() if args.thresholds_from_env else GuardThresholds()
    mismatches = 0
    total = 0
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("path") != CHAT_PATH:
            continue
        body_raw = rec.get("request", {}).get("body_raw")
        if not body_raw:
            continue
        summary = summarize_body(body_raw)
        verdict = evaluate_guard(CHAT_PATH, body_raw, summary, thresholds=thresholds, mode=args.mode)
        recorded_level = rec.get("guard", {}).get("level")
        total += 1
        if recorded_level != verdict.level:
            mismatches += 1
            print(
                f"MISMATCH request_id={rec.get('request_id')}: recorded={recorded_level} replayed={verdict.level}"
            )
    print(f"Replayed {total} records, mismatches: {mismatches}")
    return 0 if mismatches == 0 else 3


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Kilo budget static simulator")
    sub = parser.add_subparsers(dest="command", required=True)

    sim = sub.add_parser("simulate", help="Predict guard verdict for a launcher + injection")
    sim.add_argument("--launcher", help="Path to launcher markdown file (added as user message)")
    sim.add_argument("--injection", help="Injection fixture JSON (messages Kilo auto-adds)")
    sim.add_argument("--user-turn", default=None, help="Synthetic user turn appended last")
    sim.add_argument("--mode", default="warn", choices=["warn", "block"])
    sim.add_argument("--fail-on", default=None, choices=list(LEVEL_ORDER.keys()))
    sim.add_argument("--json-out", default=None, help="Write structured report JSON")
    sim.add_argument("--attribute", action="store_true", help="Run leave-one-out attribution")
    sim.add_argument(
        "--section-attribute",
        action="store_true",
        help="Run leave-one-out attribution inside launcher sections",
    )
    sim.add_argument(
        "--section-level",
        type=int,
        default=2,
        choices=[2, 3],
        help="Heading level for section attribution (2=##, 3=###)",
    )
    sim.add_argument("--thresholds-from-env", action="store_true")
    sim.set_defaults(func=cmd_simulate)

    cap = sub.add_parser("capture", help="Extract injection fixture from a relay JSONL")
    cap.add_argument("--from-jsonl", required=True)
    cap.add_argument("--probe", default=None, help="Filter records by probe marker substring")
    cap.add_argument("--drop-trailing-user", action="store_true", default=True)
    cap.add_argument("-o", "--output", default="fixtures/kilo_injection_captured.json")
    cap.set_defaults(func=cmd_capture)

    rep = sub.add_parser("replay", help="Recompute verdicts from an existing JSONL (parity check)")
    rep.add_argument("--from-jsonl", required=True)
    rep.add_argument("--mode", default="warn", choices=["warn", "block"])
    rep.add_argument("--thresholds-from-env", action="store_true")
    rep.set_defaults(func=cmd_replay)

    return parser


def main(argv: list[str] | None = None) -> int:
    # Force UTF-8 stdout on Windows (cp1252 otherwise breaks on Unicode punctuation).
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
