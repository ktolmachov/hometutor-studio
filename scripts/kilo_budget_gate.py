#!/usr/bin/env python3
"""Pre-commit budget gate — predict-and-prevent guard for workflow regressions.

Compares HEAD vs the **index snapshot** (what is actually about to be
committed). Dry-run mode uses the current worktree for convenience.

Key behaviours:
- If NO budget-sensitive files are staged → exits 0 silently (not a
  budget-relevant commit; gate does not slow down unrelated work).
- If budget-sensitive files ARE staged → compares HEAD vs the index snapshot
  (not worktree) so the verdict reflects exactly what the commit will contain.
- Self-guards: verifies deps and fixture before running.
- Fails if any launcher's staged version regresses or is already ≥ soft_block.

Override: `KILO_BUDGET_GATE=skip` (logged), or `git commit --no-verify`.

Usage:
    python scripts/kilo_budget_gate.py            # guard the pending commit
    python scripts/kilo_budget_gate.py --dry-run  # report levels, never fail
    python scripts/kilo_budget_gate.py --json     # machine output
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from _kilo_guard import GuardThresholds, evaluate_guard, summarize_body  # noqa: E402
from kilo_budget_simulate import build_payload  # noqa: E402


CHAT_PATH = "/v1/chat/completions"
LEVEL_ORDER = {"ok": 0, "warn": 1, "soft_block": 2, "hard_block": 3}

LAUNCHERS: list[dict[str, str]] = [
    {"name": "orch",           "path": "doc/team_workflow/generate_orchestration_prompt.md"},
    {"name": "planning",       "path": "doc/team_workflow/generate_plan_next_prompt.md"},
    {"name": "resume",         "path": "doc/team_workflow/generate_resume_prompt.md"},
    {"name": "execution_auto", "path": "doc/team_workflow/generate_execution_prompt_auto.md"},
]

# Staged files whose presence should trigger budget gate.
BUDGET_SENSITIVE_PATTERNS: tuple[str, ...] = (
    "doc/team_workflow/",
    "fixtures/kilo_injection_baseline.json",
    "fixtures/kilo_injection_captured.json",
    "fixtures/kilo_injection_calibrated.json",
    "scripts/_kilo_guard.py",
    "scripts/kilo_budget_gate.py",
    "scripts/kilo_budget_simulate.py",
    "scripts/kilo_proxy_relay.py",
    "scripts/kilo_budget_daily.py",
    "scripts/kilo_injection_calibrate.py",
    "CLAUDE.md",
    ".claude/",
)

CAPTURED_FIXTURE = ROOT / "fixtures" / "kilo_injection_captured.json"
LEGACY_BASELINE_FIXTURE = ROOT / "fixtures" / "kilo_injection_baseline.json"
ABSOLUTE_FAIL_LEVEL = "soft_block"


def _choose_fixture() -> tuple[Path, str]:
    if CAPTURED_FIXTURE.exists():
        return CAPTURED_FIXTURE, "captured_relay_fixture"
    return LEGACY_BASELINE_FIXTURE, "legacy_calibrated_baseline"


INJECTION_FIXTURE, INJECTION_FIXTURE_AUTHORITY = _choose_fixture()


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _git_available() -> bool:
    try:
        subprocess.check_output(["git", "--version"], stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _get_staged_files() -> list[str]:
    """Return list of paths staged for the pending commit (forward-slash)."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
            cwd=ROOT, stderr=subprocess.DEVNULL,
        )
        return [l.strip().replace("\\", "/") for l in out.decode("utf-8").splitlines() if l.strip()]
    except subprocess.CalledProcessError:
        return []


def _is_budget_sensitive(path: str) -> bool:
    path = path.replace("\\", "/")
    return any(path.startswith(p) or path == p for p in BUDGET_SENSITIVE_PATTERNS)


def _git_show(ref: str, path: str) -> str | None:
    """Read a file at a specific git ref. `ref` may be 'HEAD' or ':' (index)."""
    try:
        out = subprocess.check_output(
            ["git", "show", f"{ref}:{path}"],
            cwd=ROOT, stderr=subprocess.DEVNULL,
        )
        return out.decode("utf-8", errors="replace")
    except subprocess.CalledProcessError:
        return None


def _read_staged(path: str) -> str | None:
    """Read the staged (index) version of a file — what the commit will contain."""
    return _git_show("", path)  # ':path' == git show :path (index)


def _read_worktree(path: str) -> str | None:
    p = ROOT / path
    return p.read_text(encoding="utf-8") if p.exists() else None


def _read_candidate(path: str, *, dry_run: bool) -> tuple[str | None, str]:
    """Read the candidate snapshot for a file.

    Non-dry-run mode must reflect the pending commit, so it always reads the
    index snapshot. Dry-run uses the worktree to make local exploration easy.
    """
    if dry_run:
        return _read_worktree(path), "worktree"
    return _read_staged(path), "staged"


# ---------------------------------------------------------------------------
# Self-guard pre-flight
# ---------------------------------------------------------------------------


def preflight() -> list[str]:
    """Return list of error strings; empty means all good."""
    errors: list[str] = []
    if not _git_available():
        errors.append("git not found in PATH")
    if not INJECTION_FIXTURE.exists():
        errors.append(
            f"Injection fixture missing: {INJECTION_FIXTURE.relative_to(ROOT)}\n"
            "  Fix: python scripts/kilo_injection_calibrate.py"
        )
    else:
        try:
            raw = json.loads(INJECTION_FIXTURE.read_text(encoding="utf-8"))
            if "messages" not in raw:
                errors.append(f"Fixture malformed (no 'messages'): {INJECTION_FIXTURE.relative_to(ROOT)}")
        except Exception as exc:
            errors.append(f"Fixture unreadable: {exc}")
    try:
        from _kilo_guard import evaluate_guard as _  # noqa: F401
    except ImportError as exc:
        errors.append(f"Cannot import _kilo_guard: {exc}")
    return errors


# ---------------------------------------------------------------------------
# Verdict helpers
# ---------------------------------------------------------------------------


def _verdict_for(
    launcher_text: str | None,
    fixture: dict[str, Any],
    thresholds: GuardThresholds,
) -> dict[str, Any]:
    if launcher_text is None:
        return {"missing": True, "level": "ok", "body_chars": 0, "reasons": [], "risk_flags": []}
    payload, _ = build_payload(fixture, launcher_text=launcher_text, user_turn=None)
    body_text = json.dumps(payload, ensure_ascii=False)
    summary = summarize_body(body_text)
    verdict = evaluate_guard(CHAT_PATH, body_text, summary, thresholds=thresholds, mode="warn")
    return {
        "missing": False,
        "level": verdict.level,
        "body_chars": summary["body_chars"],
        "launcher_chars": len(launcher_text),
        "reasons": verdict.reasons,
        "risk_flags": verdict.risk_flags,
    }


def evaluate_launcher(
    name: str,
    path: str,
    fixture: dict[str, Any],
    thresholds: GuardThresholds,
    *,
    dry_run: bool,
    staged_files: list[str] | None = None,
) -> dict[str, Any]:
    """Compare HEAD vs candidate snapshot (index for commits, worktree for dry-run)."""
    head_text = _git_show("HEAD", path)
    candidate_text, candidate_source = _read_candidate(path, dry_run=dry_run)

    head_v = _verdict_for(head_text, fixture, thresholds)
    cand_v = _verdict_for(candidate_text, fixture, thresholds)

    regression = LEVEL_ORDER[cand_v["level"]] > LEVEL_ORDER[head_v["level"]]
    absolute_fail = LEVEL_ORDER[cand_v["level"]] >= LEVEL_ORDER[ABSOLUTE_FAIL_LEVEL]
    delta_chars = cand_v["body_chars"] - head_v["body_chars"]
    delta_launcher = (cand_v.get("launcher_chars") or 0) - (head_v.get("launcher_chars") or 0)
    staged_set = {f.replace("\\", "/") for f in staged_files or []}
    launcher_is_staged = path.replace("\\", "/") in staged_set
    dependency_changed = any(
        f in staged_set for f in (
            "fixtures/kilo_injection_baseline.json",
            "fixtures/kilo_injection_captured.json",
            "scripts/_kilo_guard.py",
            "scripts/kilo_budget_gate.py",
            "scripts/kilo_budget_simulate.py",
        )
    )
    if launcher_is_staged and dependency_changed:
        trigger_reason = "launcher+dependency"
    elif launcher_is_staged:
        trigger_reason = "launcher_self"
    elif dependency_changed:
        trigger_reason = "dependency_only"
    else:
        trigger_reason = "none"

    return {
        "name": name,
        "path": path,
        "candidate_source": candidate_source,
        "head": head_v,
        "work": cand_v,      # kept as "work" for backwards-compat with callers
        "regression": regression,
        "absolute_fail": absolute_fail,
        "trigger_reason": trigger_reason,
        "delta_body_chars": delta_chars,
        "delta_launcher_chars": delta_launcher,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def format_launcher_row(row: dict[str, Any]) -> str:
    name = row["name"]
    src = row["candidate_source"][0].upper()  # S(taged) or W(orktree)
    head_level = row["head"]["level"]
    work_level = row["work"]["level"]
    transition = f"{head_level} -> {work_level}" if head_level != work_level else head_level
    delta = row["delta_body_chars"]
    delta_txt = f"{delta:+,}" if delta != 0 else "0"
    mark = ""
    if row["regression"]:
        mark = "  !! REGRESSION"
    elif row["absolute_fail"]:
        mark = "  !! ALREADY >= soft_block"
    trigger_tag = {
        "launcher_self": "[self]",
        "dependency_only": "[dep]",
        "launcher+dependency": "[self+dep]",
    }.get(row.get("trigger_reason"), "")
    return (
        f"  [{name:>14}][{src}] {transition:<28} "
        f"body={row['work']['body_chars']:>7,}  delta={delta_txt:>8}"
        f"{mark} {trigger_tag}".rstrip()
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kilo budget pre-commit gate")
    parser.add_argument("--dry-run", action="store_true", help="Report levels, never fail")
    parser.add_argument("--json",    action="store_true", help="Machine output")
    parser.add_argument("--thresholds-from-env", action="store_true")
    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    # --- Skip override ---
    if os.getenv("KILO_BUDGET_GATE", "").strip().lower() == "skip":
        print("[kilo-budget-gate] SKIPPED via KILO_BUDGET_GATE=skip")
        return 0

    # --- Self-guard pre-flight ---
    errors = preflight()
    if errors:
        for e in errors:
            print(f"[kilo-budget-gate] ERROR: {e}", file=sys.stderr)
        return 1

    # --- Staged-file awareness ---
    staged: list[str] = []
    budget_staged: list[str] = []
    if not args.dry_run:
        staged = _get_staged_files()
        budget_staged = [f for f in staged if _is_budget_sensitive(f)]
        if not budget_staged:
            if args.json:
                print(json.dumps({
                    "failed": False,
                    "skipped": True,
                    "reason": "no_budget_sensitive_files_staged",
                    "budget_sensitive_staged": [],
                }, ensure_ascii=False, indent=2))
            else:
                print("[kilo-budget-gate] No budget-sensitive files staged — skipping.")
            return 0
        if not args.json:
            print(f"[kilo-budget-gate] Budget-sensitive staged: {budget_staged}")

    fixture_path = INJECTION_FIXTURE.relative_to(ROOT).as_posix()
    fixture_raw, fixture_source = _read_candidate(fixture_path, dry_run=args.dry_run)
    if fixture_raw is None:
        print(
            f"[kilo-budget-gate] ERROR: candidate fixture missing from {fixture_source}: {fixture_path}",
            file=sys.stderr,
        )
        return 1
    fixture = json.loads(fixture_raw)
    thresholds = GuardThresholds.from_env() if args.thresholds_from_env else GuardThresholds()

    rows = [
        evaluate_launcher(
            l["name"],
            l["path"],
            fixture,
            thresholds,
            dry_run=args.dry_run,
            staged_files=staged if not args.dry_run else None,
        )
        for l in LAUNCHERS
    ]

    any_regression = any(r["regression"] for r in rows)
    any_absolute   = any(r["absolute_fail"] for r in rows)
    gate_failed    = (any_regression or any_absolute) and not args.dry_run

    if args.json:
        print(json.dumps({
            "failed": gate_failed,
            "regression": any_regression,
            "absolute_fail": any_absolute,
            "budget_sensitive_staged": budget_staged,
            "fixture_source": fixture_source,
            "fixture_authority": INJECTION_FIXTURE_AUTHORITY,
            "thresholds": asdict(thresholds),
            "launchers": rows,
        }, ensure_ascii=False, indent=2))
    else:
        src_note = "(comparing HEAD vs staged index)" if not args.dry_run else "(dry-run: worktree)"
        print(f"=== Kilo Budget Gate {src_note} ===")
        print(f"Fixture source: {fixture_source}")
        for row in rows:
            print(format_launcher_row(row))
        if gate_failed:
            print()
            print("COMMIT BLOCKED by kilo_budget_gate.py")
            print("Reason(s):")
            for row in rows:
                if row["regression"]:
                    print(
                        f"  - {row['name']} ({row['path']}): "
                        f"{row['head']['level']} -> {row['work']['level']}"
                        f"  launcher +{row['delta_launcher_chars']:,} chars  [{row['candidate_source']}]"
                    )
                if row["absolute_fail"] and not row["regression"]:
                    print(
                        f"  - {row['name']} ({row['path']}): already {row['work']['level']}"
                        f"  body {row['work']['body_chars']:,} chars  [{row['candidate_source']}]"
                    )
            print()
            print("Investigate message-level attribution:")
            print("  python scripts/kilo_budget_simulate.py simulate \\")
            print("    --launcher <path> --injection fixtures/kilo_injection_baseline.json \\")
            print("    --attribute --section-attribute")
            print()
            print("Override: KILO_BUDGET_GATE=skip git commit ...  (or --no-verify)")
        elif args.dry_run:
            print("\n(dry-run: no exit code change)")
        else:
            print("\nOK: commit is within budget.")

    return 1 if gate_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
