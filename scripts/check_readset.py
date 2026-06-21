#!/usr/bin/env python3
"""
Token budget validator for LLM read-sets.

Merges forbidden full-read hints from `doc/token_safety_registry.json` (see
`scripts/measure_token_registry.py --write`) with built-in fallbacks.

Usage:
    python scripts/check_readset.py <file1> [file2 ...]
    python scripts/check_readset.py app/query_service.py tests/test_api.py
    python scripts/check_readset.py --budget 8000 app/query_service.py
    python scripts/check_readset.py --signatures app/query_service.py

Exit codes:
    0 = SAFE
    1 = WARN (over soft limit)
    2 = BLOCK (forbidden full-read or over hard limit)
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompt_utils import budget_profile_choices, get_budget_profile  # noqa: E402

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]

# Chars-per-token approximation (conservative)
CHARS_PER_TOKEN = 4

# Default limits (strict profile is the default local operating mode)
DEFAULT_PROFILE = "strict"
_DEFAULT_BUDGET = get_budget_profile(DEFAULT_PROFILE)
SOFT_LIMIT = int(_DEFAULT_BUDGET["soft_token_limit"])
HARD_LIMIT = int(_DEFAULT_BUDGET["hard_token_limit"])
DEFAULT_OVERHEAD = int(_DEFAULT_BUDGET["overhead_tokens"])

# Files that must never be included fully in context.
# Values are suggested safe methods.
FORBIDDEN_FULL = {
    "app/query_service.py": 'grep "^class\\|^def " app/query_service.py',
    "app/prompts/_impl.py": 'grep "^def\\|^[A-Z_].*=" app/prompts/_impl.py',
    "app/knowledge_graph.py": 'grep "^class\\|^def " app/knowledge_graph.py',
    "tests/test_api.py": "Read 1-2 specific test cases only",
    "tests/test_query_service.py": "Read 1 specific test case or fixture only",
    "doc/changelog.md": "Read only last 2-3 rows or append-target section",
    "doc/adr.md": "Read only the Status table at the start",
    "doc/cjm.md": "Read only the specific pain point or state you need",
    "doc/architecture.md": "Read only module list or one ## section",
    "doc/epochs/e4.md": "Read only header / target fragment (very large epoch doc)",
}

REGISTRY_PATH = ROOT / "doc" / "token_safety_registry.json"


def forbidden_hints_merged() -> dict[str, str]:
    """Registry JSON overrides / extends built-in hints (P0-style single source)."""
    merged = dict(FORBIDDEN_FULL)
    if not REGISTRY_PATH.is_file():
        return merged
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return merged
    for rel, meta in data.get("files", {}).items():
        if meta.get("full_read") != "forbidden":
            continue
        key = rel.replace("\\", "/")
        hint = meta.get("safe_hint") or "see doc/token_safety.md"
        merged[key] = hint
    return merged

# Directories whose files must not be included wholesale
FORBIDDEN_DIRS = {
    "doc/epochs": "Read max 1 epoch file; use headers/status tables, not full body",
    "doc/user_stories": "Read only the single US file you need",
}

# Files >600 lines are "large" and need justification
LARGE_FILE_THRESHOLD_LINES = 600


def count_tokens(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return len(text) // CHARS_PER_TOKEN
    except OSError:
        return 0


def count_lines(path: Path) -> int:
    try:
        return path.read_text(encoding="utf-8", errors="ignore").count("\n")
    except OSError:
        return 0


def resolve_path(filepath: str) -> Path:
    p = Path(filepath)
    if not p.is_absolute():
        p = ROOT / p
    return p


def check_forbidden(filepath: str) -> str | None:
    """Return safe-method hint if file is forbidden full-read, else None."""
    norm = filepath.replace("\\", "/").lstrip("./")
    # strip leading project root
    if norm.startswith(str(ROOT).replace("\\", "/")):
        norm = norm[len(str(ROOT).replace("\\", "/")):]
    norm = norm.lstrip("/")
    fb = forbidden_hints_merged()
    if norm in fb:
        return fb[norm]
    for d, hint in FORBIDDEN_DIRS.items():
        if norm.startswith(d + "/") or norm.startswith(d + "\\"):
            return hint
    return None


def format_tokens(n: int) -> str:
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def generate_signatures_command(filepath: str) -> str:
    norm = filepath.replace("\\", "/")
    if norm.endswith(".py"):
        return f'grep "^class\\|^def " {norm}'
    if norm.endswith(".md"):
        return f'grep "^#" {norm}'
    return f"head -50 {norm}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate token budget for a proposed LLM read-set."
    )
    parser.add_argument("files", nargs="*", help="Files to include in read-set")
    parser.add_argument(
        "--profile",
        choices=budget_profile_choices(),
        default=DEFAULT_PROFILE,
        help=f"Budget profile (default: {DEFAULT_PROFILE})",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=None,
        help="Soft token limit override (defaults to the selected profile)",
    )
    parser.add_argument(
        "--hard",
        type=int,
        default=None,
        help="Hard token limit override (defaults to the selected profile)",
    )
    parser.add_argument(
        "--signatures",
        action="store_true",
        help="For each large file, show grep-signatures command instead of full-read",
    )
    parser.add_argument(
        "--overhead",
        type=int,
        default=None,
        help="Estimated system prompt + history overhead override (defaults to the selected profile)",
    )
    args = parser.parse_args()

    if not args.files:
        parser.print_help()
        return 0

    budget_profile = get_budget_profile(args.profile)
    soft_limit = args.budget if args.budget is not None else int(budget_profile["soft_token_limit"])
    hard_limit = args.hard if args.hard is not None else int(budget_profile["hard_token_limit"])
    overhead = args.overhead if args.overhead is not None else int(budget_profile["overhead_tokens"])

    rows = []
    forbidden_found = []
    large_found = []
    total_tokens = overhead

    print(f"\n{'─' * 60}")
    print(f"  TOKEN BUDGET VALIDATOR")
    print(f"{'─' * 60}")
    print(f"  Profile: {budget_profile['name']}")
    print(f"  Soft limit: {format_tokens(soft_limit)} | Hard limit: {format_tokens(hard_limit)}")
    print(f"  Overhead (system+history): ~{format_tokens(overhead)} tokens")
    print(f"{'─' * 60}\n")

    for filepath in args.files:
        rel = filepath.replace("\\", "/").lstrip("./")
        abs_path = resolve_path(filepath)
        tokens = count_tokens(abs_path)
        lines = count_lines(abs_path)
        forbidden_hint = check_forbidden(filepath)

        status = "✅ OK"
        notes = []

        if not abs_path.exists():
            status = "⚠️  NOT FOUND"
            notes.append("file not found — will be 0 tokens")
            tokens = 0
        elif forbidden_hint:
            status = "❌ FORBIDDEN"
            notes.append(f"Full-read forbidden. Safe: {forbidden_hint}")
            if args.signatures:
                notes.append("(signatures mode — safe method only; not a full-read attempt)")
                notes.append(f"→ {generate_signatures_command(filepath)}")
                tokens = 0  # budget assumes signatures-only, not full file
            else:
                forbidden_found.append(filepath)
        elif lines > LARGE_FILE_THRESHOLD_LINES:
            status = "⚠️  LARGE"
            notes.append(f"{lines} lines — consider signatures/sections only")
            large_found.append(filepath)
            if args.signatures:
                notes.append("(signatures mode — safe method only; not a full-read attempt)")
                notes.append(f"→ {generate_signatures_command(filepath)}")
                tokens = 0  # budget assumes signatures-only, same as forbidden + --signatures

        total_tokens += tokens
        rows.append((rel, lines, format_tokens(tokens), status, notes))

    # Print table
    for rel, lines, tok_str, status, notes in rows:
        print(f"  {status}  {rel}")
        print(f"         {lines} lines  ~{tok_str} tokens")
        for note in notes:
            print(f"         💡 {note}")
        print()

    print(f"{'─' * 60}")
    print(f"  Overhead:    ~{format_tokens(overhead)} tokens")
    print(f"  Files total: ~{format_tokens(total_tokens - overhead)} tokens")
    print(f"  ESTIMATED TOTAL: ~{format_tokens(total_tokens)} tokens")
    print(f"{'─' * 60}")

    # Final verdict
    exit_code = 0
    if forbidden_found or total_tokens > hard_limit:
        print(f"\n  🔴  BLOCK")
        if forbidden_found:
            print(f"       {len(forbidden_found)} forbidden full-read file(s).")
            print(f"       Use safe methods shown above before sending.")
        if total_tokens > hard_limit:
            print(f"       Estimated {format_tokens(total_tokens)} tokens > hard limit {format_tokens(hard_limit)}.")
            print(f"       Must compress before sending.")
        exit_code = 2
    elif total_tokens > soft_limit:
        print(f"\n  🟡  WARN")
        print(f"       Estimated {format_tokens(total_tokens)} tokens > soft limit {format_tokens(soft_limit)}.")
        print(f"       Compress history/read-set before sending.")
        if large_found:
            print(f"       Consider using signatures for: {', '.join(large_found)}")
        exit_code = 1
    else:
        print(f"\n  🟢  SAFE")
        print(f"       Estimated {format_tokens(total_tokens)} tokens — within budget.")
        exit_code = 0

    print(f"\n  Tip: re-run with --signatures to see grep commands for large files.")
    print(f"       See doc/token_safety.md for full reference.\n")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
