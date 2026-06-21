#!/usr/bin/env python3
"""
Context Cart: assemble a token-budget-safe context read-set for LLM agents.

Uses doc/token_safety_registry.json for file sizes; sorts by token cost.
Outputs a "cart" — the files to read and the reading strategy for each.

Usage:
    python scripts/context_cart.py --mode plan app/config.py doc/tasklist.md
    python scripts/context_cart.py --mode verify tests/test_api.py app/api.py
    python scripts/context_cart.py --mode orchestrate --emit-agent-prompt app/query_service.py
    python scripts/context_cart.py --json --mode plan app/config.py

Modes and token budgets (overhead ~3k reserved):
    plan         12 000 tokens  exploratory analysis, multiple context files
    orchestrate   8 000 tokens  focused execution, task + 2-3 impl files
    verify        6 000 tokens  correctness check, minimal context

Exit codes:
    0 = cart assembled; all requested files fit within budget
    1 = partial cart: some files excluded due to budget or forbidden status
    2 = error (bad args, missing registry)
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "doc" / "token_safety_registry.json"

CHARS_PER_TOKEN = 4
OVERHEAD_TOKENS = 3_000  # system prompt + history

MODE_BUDGETS: dict[str, int] = {
    "plan": 12_000,
    "orchestrate": 8_000,
    "verify": 6_000,
}

CART_SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Registry loading
# ---------------------------------------------------------------------------


def _load_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.is_file():
        return {}
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _file_meta(rel_path: str, registry: dict[str, Any]) -> dict[str, Any]:
    """Return per-file metadata from registry, with fallback."""
    files = registry.get("files") or {}
    key = rel_path.replace("\\", "/")
    return dict(files.get(key) or {})


def _estimate_tokens(rel_path: str, registry: dict[str, Any]) -> int:
    """Estimate token count for a file from registry or filesystem fallback."""
    meta = _file_meta(rel_path, registry)
    if meta.get("est_tokens"):
        return int(meta["est_tokens"])
    # Filesystem fallback
    full = ROOT / rel_path
    if full.is_file():
        try:
            size = full.stat().st_size
            return max(1, size // CHARS_PER_TOKEN)
        except OSError:
            pass
    return 500  # conservative unknown


def _strategy(rel_path: str, registry: dict[str, Any]) -> tuple[str, str | None]:
    """
    Determine reading strategy for a file.
    Returns (strategy, hint_or_none):
      'forbidden'  — must not be included; hint = why / what to do instead
      'signatures' — rg ^class|^def only
      'hint'       — specific hint from registry
      'full'       — safe to read fully
    """
    meta = _file_meta(rel_path, registry)
    if meta.get("full_read") == "forbidden":
        return "forbidden", meta.get("safe_hint")
    safe_hint = meta.get("safe_hint")
    if safe_hint:
        return "hint", safe_hint
    # Heuristic: large files get 'signatures' suggestion
    tokens = _estimate_tokens(rel_path, registry)
    if tokens > 5_000:
        return "signatures", f"rg -n \"^class|^def \" {rel_path}"
    return "full", None


# ---------------------------------------------------------------------------
# Cart assembly
# ---------------------------------------------------------------------------


def build_cart(
    files: list[str],
    *,
    budget: int,
    registry: dict[str, Any],
) -> dict[str, Any]:
    """
    Greedily assemble files into a context cart within `budget` tokens.

    Files are processed in the order given (caller controls priority).
    Forbidden files are always excluded.
    Large files are included only with their reduced-strategy token estimate.

    Returns:
        {
            "schema_version": 1,
            "budget": int,
            "tokens_used": int,
            "included": [{"path", "tokens", "strategy", "hint"}],
            "excluded": [{"path", "tokens", "strategy", "hint", "reason"}],
        }
    """
    available = budget - OVERHEAD_TOKENS
    used = 0
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for rel in files:
        norm = rel.replace("\\", "/")
        strat, hint = _strategy(norm, registry)
        tokens = _estimate_tokens(norm, registry)

        if strat == "forbidden":
            excluded.append({
                "path": norm,
                "tokens": tokens,
                "strategy": strat,
                "hint": hint,
                "reason": "forbidden_full_read",
            })
            continue

        # For signatures/hint strategies, use reduced token estimate (rg output ~ 10% of file)
        if strat in ("signatures", "hint"):
            tokens_charged = max(50, tokens // 10)
        else:
            tokens_charged = tokens

        if used + tokens_charged > available:
            excluded.append({
                "path": norm,
                "tokens": tokens,
                "tokens_charged": tokens_charged,
                "strategy": strat,
                "hint": hint,
                "reason": "budget_exceeded",
            })
            continue

        used += tokens_charged
        included.append({
            "path": norm,
            "tokens": tokens,
            "tokens_charged": tokens_charged,
            "strategy": strat,
            **({"hint": hint} if hint else {}),
        })

    return {
        "schema_version": CART_SCHEMA_VERSION,
        "budget": budget,
        "overhead_reserved": OVERHEAD_TOKENS,
        "available": available,
        "tokens_used": used,
        "included": included,
        "excluded": excluded,
    }


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------


def _format_agent_prompt(cart: dict[str, Any], mode: str) -> str:
    """Emit a read-set instruction suitable for pasting into an agent prompt."""
    included = cart["included"]
    budget = cart["budget"]
    used = cart["tokens_used"]
    lines = [
        f"Read ONLY (mode={mode}, budget={budget}k, used≈{used // 1000}k tokens):",
    ]
    for i, item in enumerate(included, 1):
        path = item["path"]
        strat = item["strategy"]
        hint = item.get("hint")
        if strat == "full":
            lines.append(f"  {i}. {path}  — full read")
        elif strat == "signatures":
            lines.append(f"  {i}. {path}  — signatures only: {hint}")
        elif strat == "hint":
            lines.append(f"  {i}. {path}  — {hint}")

    excluded = cart["excluded"]
    if excluded:
        lines.append("")
        lines.append("Excluded (budget or forbidden):")
        for item in excluded:
            reason = item.get("reason", "")
            hint = item.get("hint") or ""
            lines.append(f"  - {item['path']}  [{reason}]" + (f"  → {hint}" if hint else ""))

    return "\n".join(lines)


def _format_text_summary(cart: dict[str, Any], mode: str) -> str:
    included = cart["included"]
    excluded = cart["excluded"]
    budget = cart["budget"]
    used = cart["tokens_used"]
    avail = cart["available"]

    lines = [
        f"Context Cart [{mode}]  budget={budget} overhead={cart['overhead_reserved']} "
        f"available={avail} used={used}",
        "",
    ]
    if included:
        lines.append("Included:")
        for item in included:
            charged = item.get("tokens_charged", item["tokens"])
            hint = item.get("hint") or ""
            lines.append(
                f"  ✅ {item['path']}  [{item['strategy']}]  ~{charged}t"
                + (f"  ({hint})" if hint else "")
            )
    if excluded:
        lines.append("")
        lines.append("Excluded:")
        for item in excluded:
            reason = item.get("reason", "")
            hint = item.get("hint") or ""
            lines.append(
                f"  ❌ {item['path']}  [{reason}]"
                + (f"  → {hint}" if hint else "")
            )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--mode",
        choices=list(MODE_BUDGETS),
        default="plan",
        help="Token budget mode (default: plan)",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=None,
        help="Override token budget (default: mode-specific)",
    )
    parser.add_argument(
        "--emit-agent-prompt",
        action="store_true",
        help="Output as agent-ready read-set instruction",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Output full cart as JSON",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Files to include in cart (relative to repo root)",
    )
    args = parser.parse_args(argv)

    budget = args.budget if args.budget is not None else MODE_BUDGETS[args.mode]
    registry = _load_registry()

    cart = build_cart(args.files, budget=budget, registry=registry)

    if args.json_output:
        print(json.dumps(cart, ensure_ascii=False, indent=2))
    elif args.emit_agent_prompt:
        print(_format_agent_prompt(cart, args.mode))
    else:
        print(_format_text_summary(cart, args.mode))

    # Exit 1 if anything was excluded
    if cart["excluded"]:
        return 1
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "buffer") and sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer") and sys.stderr.encoding != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
