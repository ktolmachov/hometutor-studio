#!/usr/bin/env python3
"""Build a calibrated injection estimate from readable project sources.

The synthetic `fixtures/kilo_injection_baseline.json` has ~2,243 chars — a
placeholder. Real Kilo sessions inject ~49,000+ chars before any launcher
content: CLAUDE.md, memory files, available_skills block, tool schemas. This
creates a +47k blind spot in the gate: launchers look fine at 12-19k, but
real sessions are within 2k chars of the warn threshold.

This script auto-discovers what Kilo likely injects by reading local project
files and writes a calibrated fixture estimate. It is useful for offline
budget awareness, but it is not a substitute for real relay capture.

Usage:
    python scripts/kilo_injection_calibrate.py            # audit + write
    python scripts/kilo_injection_calibrate.py --dry-run  # audit only
    python scripts/kilo_injection_calibrate.py --show-sources  # verbose breakdown
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASELINE_FIXTURE_PATH = ROOT / "fixtures" / "kilo_injection_baseline.json"
CALIBRATED_FIXTURE_PATH = ROOT / "fixtures" / "kilo_injection_calibrated.json"

sys.path.insert(0, str(ROOT / "scripts"))
from _kilo_guard import GuardThresholds, evaluate_guard, summarize_body  # noqa: E402
from kilo_budget_simulate import build_payload, load_injection_fixture  # noqa: E402


LAUNCHERS = [
    {"name": "orch", "path": "doc/team_workflow/generate_orchestration_prompt.md"},
    {"name": "planning", "path": "doc/team_workflow/generate_plan_next_prompt.md"},
    {"name": "resume", "path": "doc/team_workflow/generate_resume_prompt.md"},
    {"name": "execution_auto", "path": "doc/team_workflow/generate_execution_prompt_auto.md"},
]

CHAT_PATH = "/v1/chat/completions"
EMBED_MEMORY_CONTENT = False


# ---------------------------------------------------------------------------
# Source discovery
# ---------------------------------------------------------------------------


@dataclass
class InjectionSource:
    name: str
    chars: int
    source_type: str  # claude_md | memory | kilo_system | tools | skills | unknown
    path: str | None = None
    note: str | None = None


def _find_memory_dir() -> Path | None:
    """Find the Claude Code memory directory for this project."""
    # Claude Code slug: each path separator and colon becomes "-", underscore → "-".
    # e.g. <repo-root> -> repo-root
    home = Path.home()
    raw = str(ROOT)
    proj_slug = raw.replace(":", "-").replace("\\", "-").replace("/", "-").replace("_", "-").lstrip("-")
    candidate = home / ".claude" / "projects" / proj_slug / "memory"
    if candidate.exists():
        return candidate
    # Fallback: find project dir whose name best matches by scanning
    projects_dir = home / ".claude" / "projects"
    if projects_dir.exists():
        root_name = ROOT.name.replace("_", "-")
        for p in sorted(projects_dir.iterdir()):
            if root_name in p.name and (p / "MEMORY.md").exists():
                return p / "memory"
    return None


def discover_sources() -> list[InjectionSource]:
    sources: list[InjectionSource] = []

    # 1. Kilo built-in system prompt (conservative estimate)
    sources.append(InjectionSource(
        name="kilo_system_prompt",
        chars=1_200,
        source_type="kilo_system",
        note="Kilo's own instructions (estimated — not readable locally)",
    ))

    # 2. CLAUDE.md
    claude_md = ROOT / "CLAUDE.md"
    if claude_md.exists():
        text = claude_md.read_text(encoding="utf-8")
        sources.append(InjectionSource(
            name="CLAUDE.md",
            chars=len(text),
            source_type="claude_md",
            path=str(claude_md.relative_to(ROOT)),
        ))

    # 3. Memory files
    mem_dir = _find_memory_dir()
    if mem_dir:
        for f in sorted(mem_dir.glob("*.md")):
            text = f.read_text(encoding="utf-8")
            if text.strip():
                sources.append(InjectionSource(
                    name=f.name,
                    chars=len(text),
                    source_type="memory",
                    path=str(f),
                ))

    # 4. Tool schemas — 6 built-in Kilo tools (from synthetic fixture as floor)
    old_fixture = BASELINE_FIXTURE_PATH
    if old_fixture.exists():
        try:
            fx = json.loads(old_fixture.read_text(encoding="utf-8"))
            tools_chars = len(json.dumps(fx.get("tools", []), ensure_ascii=False))
            sources.append(InjectionSource(
                name="tool_schemas (baseline fixture)",
                chars=tools_chars,
                source_type="tools",
                path=str(old_fixture.relative_to(ROOT)),
                note="Floor estimate from synthetic fixture; real Kilo may include more",
            ))
        except Exception:
            pass

    # 5. Available skills block — Claude Code injects <available_skills> XML
    # containing all installed skills. Estimate from skills list in settings.
    skills_chars = _estimate_skills_block_chars()
    if skills_chars > 0:
        sources.append(InjectionSource(
            name="<available_skills> block",
            chars=skills_chars,
            source_type="skills",
            note=f"Claude Code skill definitions injected into system context (~{skills_chars:,} chars estimated)",
        ))

    return sources


def _estimate_skills_block_chars() -> int:
    """Estimate <available_skills> XML block size from known skills count."""
    # These are the skills visible in the current Claude Code installation.
    # Each skill has name + description + trigger conditions = ~800-1,200 chars.
    # Use 1,000 as midpoint estimate.
    known_skills = [
        "update-config", "keybindings-help", "simplify", "less-permission-prompts",
        "loop", "schedule", "claude-api", "anthropic-skills:consolidate-memory",
        "anthropic-skills:schedule", "anthropic-skills:setup-cowork",
        "anthropic-skills:pptx", "anthropic-skills:xlsx", "anthropic-skills:pdf",
        "anthropic-skills:docx", "anthropic-skills:skill-creator",
        "init", "review", "security-review",
    ]
    # XML wrapper overhead
    wrapper = len("<available_skills>\n</available_skills>")
    per_skill_avg = 1_000
    return wrapper + len(known_skills) * per_skill_avg


# ---------------------------------------------------------------------------
# Fixture construction
# ---------------------------------------------------------------------------


def build_calibrated_fixture(sources: list[InjectionSource]) -> dict[str, Any]:
    """Build an injection fixture from discovered sources.

    Each source becomes its own message so `largest_message_chars` reflects
    actual Kilo behaviour (separate context blocks), not one giant concat.
    """
    messages: list[dict[str, Any]] = []
    tool_schemas: list[Any] = []

    for src in sources:
        if src.source_type == "kilo_system":
            content = _synthetic_block(src.name, src.chars, src.note or "")
            messages.append({"role": "system", "content": content})
        elif src.source_type == "skills":
            content = _synthetic_block(src.name, src.chars, src.note or "")
            messages.append({"role": "system", "content": content})
        elif src.source_type == "claude_md":
            path = ROOT / src.path if src.path else None
            text = path.read_text(encoding="utf-8") if path and path.exists() else ""
            messages.append({"role": "system", "content": f"<project_rules>\n{text}\n</project_rules>"})
        elif src.source_type == "memory":
            path = Path(src.path) if src.path else None
            if path and path.exists():
                text = path.read_text(encoding="utf-8")
                if not EMBED_MEMORY_CONTENT:
                    text = f"<memory redacted, {len(text)} chars>"
            else:
                text = ""
            messages.append({"role": "system", "content": f"<memory file=\"{src.name}\">\n{text}\n</memory>"})
        elif src.source_type == "tools":
            try:
                old_fx = json.loads(BASELINE_FIXTURE_PATH.read_text(encoding="utf-8"))
                tool_schemas = old_fx.get("tools", [])
            except Exception:
                tool_schemas = _default_tools()

    total_msg_chars = sum(len(str(m.get("content", ""))) for m in messages)
    total_chars = total_msg_chars + len(json.dumps(tool_schemas, ensure_ascii=False))
    return {
        "_meta": {
            "purpose": "Calibrated injection fixture built from real project files.",
            "fixture_kind": "calibrated_estimate",
            "source_note": "Offline approximation built from readable project files plus estimates; not authoritative runtime capture.",
            "refresh": "python scripts/kilo_injection_calibrate.py",
            "memory_content_mode": "embedded" if EMBED_MEMORY_CONTENT else "redacted",
            "total_chars_estimate": total_chars,
            "sources": [
                {"name": s.name, "chars": s.chars, "type": s.source_type}
                for s in sources
            ],
        },
        "model": "openai/gpt-4o-mini",
        "messages": messages,
        "tools": tool_schemas,
    }


def _synthetic_block(name: str, target_chars: int, note: str) -> str:
    """Build a placeholder text of approximately target_chars characters."""
    header = f"# {name}\n# Note: {note}\n# Estimated size: {target_chars} chars\n"
    remaining = max(0, target_chars - len(header))
    # Fill with structured placeholder text (not random bytes — human-readable)
    line = "# [synthetic placeholder content — replace with real capture]\n"
    filler = (line * (remaining // len(line) + 1))[:remaining]
    return header + filler


def _default_tools() -> list[dict[str, Any]]:
    return [
        {"type": "function", "function": {"name": "kilo_local_recall",
            "description": "Recall relevant context from prior sessions.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
        {"type": "function", "function": {"name": "read_file",
            "description": "Read a file.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    ]


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


def analyze_launchers(
    fixture: dict[str, Any],
    thresholds: GuardThresholds,
) -> list[dict[str, Any]]:
    rows = []
    for l in LAUNCHERS:
        p = ROOT / l["path"]
        if not p.exists():
            rows.append({"name": l["name"], "path": l["path"], "missing": True})
            continue
        launcher_text = p.read_text(encoding="utf-8")
        payload, _ = build_payload(fixture, launcher_text=launcher_text, user_turn=None)
        body_text = json.dumps(payload, ensure_ascii=False)
        summary = summarize_body(body_text)
        verdict = evaluate_guard(CHAT_PATH, body_text, summary, thresholds=thresholds, mode="warn")
        rows.append({
            "name": l["name"],
            "path": l["path"],
            "level": verdict.level,
            "body_chars": summary["body_chars"],
            "launcher_chars": len(launcher_text),
            "gap_to_warn": thresholds.warn_body_chars - summary["body_chars"],
            "gap_to_soft_block": thresholds.max_body_chars - summary["body_chars"],
            "risk_flags": verdict.risk_flags,
            "reasons": verdict.reasons,
        })
    return rows


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


LEVEL_EMOJI = {"ok": "OK", "warn": "WARN", "soft_block": "SOFT_BLOCK", "hard_block": "HARD_BLOCK"}


def format_sources_table(sources: list[InjectionSource]) -> str:
    lines = ["Source breakdown:", f"  {'Source':<40} {'Chars':>8}  Type"]
    total = 0
    for s in sources:
        lines.append(f"  {s.name:<40} {s.chars:>8,}  {s.source_type}")
        total += s.chars
    lines.append(f"  {'TOTAL injection estimate':<40} {total:>8,}")
    return "\n".join(lines)


def format_launcher_table(rows: list[dict[str, Any]], thresholds: GuardThresholds) -> str:
    lines = [
        "Launcher budget with calibrated injection:",
        f"  {'Name':<16} {'Level':<10} {'Body':>8}  {'Gap→warn':>9}  {'Gap→soft':>9}",
    ]
    for r in rows:
        if r.get("missing"):
            lines.append(f"  {r['name']:<16} MISSING")
            continue
        level = r["level"]
        mark = " !!" if level != "ok" else ""
        lines.append(
            f"  {r['name']:<16} {level:<10} {r['body_chars']:>8,}  "
            f"{r['gap_to_warn']:>+9,}  {r['gap_to_soft_block']:>+9,}{mark}"
        )
    lines.append("")
    lines.append(f"Thresholds: warn={thresholds.warn_body_chars:,}  "
                 f"soft_block={thresholds.max_body_chars:,}  "
                 f"hard_block={thresholds.hard_block_body_chars:,}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build calibrated Kilo injection estimate from project files")
    parser.add_argument("--dry-run", action="store_true", help="Audit only, do not write fixture")
    parser.add_argument("--show-sources", action="store_true", help="Print per-source breakdown")
    parser.add_argument("--output", default=str(CALIBRATED_FIXTURE_PATH), help="Where to write calibrated fixture")
    parser.add_argument(
        "--embed-memory-content",
        action="store_true",
        help="Embed raw memory text into calibrated fixture (privacy-sensitive)",
    )
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    parser.add_argument("--thresholds-from-env", action="store_true")
    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    global EMBED_MEMORY_CONTENT  # noqa: PLW0603
    EMBED_MEMORY_CONTENT = args.embed_memory_content
    thresholds = GuardThresholds.from_env() if args.thresholds_from_env else GuardThresholds()
    sources = discover_sources()
    fixture = build_calibrated_fixture(sources)
    launcher_rows = analyze_launchers(fixture, thresholds)

    total_injection = sum(s.chars for s in sources)

    if args.json:
        print(json.dumps({
            "total_injection_chars": total_injection,
            "sources": [{"name": s.name, "chars": s.chars, "type": s.source_type} for s in sources],
            "launchers": launcher_rows,
            "wrote_fixture": not args.dry_run,
        }, ensure_ascii=False, indent=2))
    else:
        print("=== Kilo Injection Calibration Estimate ===\n")
        if args.show_sources:
            print(format_sources_table(sources))
            print()
        else:
            print(f"Total injection estimate: {total_injection:,} chars  "
                  f"(vs synthetic fixture: {_synthetic_chars()} chars  "
                  f"delta: +{total_injection - _synthetic_chars():,})")
            print()
        print(format_launcher_table(launcher_rows, thresholds))

        any_close = any(
            r.get("gap_to_warn", 99999) < 10_000 for r in launcher_rows if not r.get("missing")
        )
        any_fail = any(
            r.get("level", "ok") not in {"ok"} for r in launcher_rows if not r.get("missing")
        )
        print()
        if any_fail:
            # Diagnose which threshold fired
            print("WARNING: one or more launchers are at warn or above with calibrated injection estimate!")
            print()
            # Check if messages_count is driving the issue
            injection_msg_count = sum(
                1 for s in sources
                if s.source_type in ("kilo_system", "claude_md", "memory", "skills")
            )
            if injection_msg_count >= thresholds.max_messages:
                print(
                    f"Root cause: injection alone uses {injection_msg_count} system messages. "
                    f"Adding any launcher pushes messages_count to {injection_msg_count + 1} "
                    f"> MAX_MESSAGES ({thresholds.max_messages}) -> soft_block."
                )
                print(
                    f"Recommended fix: raise MAX_MESSAGES to at least {injection_msg_count + 4} "
                    f"(injection + 4 conversation turns) or consolidate memory files into 1 message."
                )
                print(
                    "  Set env: KILO_RELAY_MAX_MESSAGES=15 (relay) and update GuardThresholds default."
                )
            # Body margin analysis regardless
            print()
            print("Body chars margins (independent of message count):")
            for r in launcher_rows:
                if not r.get("missing"):
                    gap_body = thresholds.warn_body_chars - r["body_chars"]
                    status = "OK" if gap_body > 0 else "OVER_WARN"
                    print(f"  {r['name']:>16}: {r['body_chars']:>7,} chars  gap_to_warn: {gap_body:>+7,}  [{status}]")
        elif any_close:
            print("CAUTION: one or more launchers have <10k chars margin to warn.")
            print("Session history accumulation across turns can close this gap quickly.")
        else:
            print("All launchers within budget with calibrated injection estimate.")

        if args.dry_run:
            print("\n(dry-run: fixture not written)")
        else:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\nCalibrated fixture estimate written -> {out}")
            print("Use this for offline analysis; refresh the committed baseline only from real relay capture when possible.")

    return 0


def _synthetic_chars() -> int:
    try:
        raw = BASELINE_FIXTURE_PATH.read_text(encoding="utf-8")
        fx = json.loads(raw)
        if not fx.get("_meta", {}).get("total_chars_estimate"):
            return 2243  # known synthetic size before calibration
        return fx["_meta"]["total_chars_estimate"]
    except Exception:
        return 2243


if __name__ == "__main__":
    raise SystemExit(main())
