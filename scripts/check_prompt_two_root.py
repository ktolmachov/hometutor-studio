#!/usr/bin/env python3
"""Lint (and optionally fix) copy-paste prompts for two-root / editable-install awareness.

Context
-------
This project is split across TWO independent git working trees:
  * CODE_ROOT  — editable install of the `hometutor` package (app/, requirements.txt).
                 Derive at runtime: ``pip show hometutor`` -> "Editable project location".
  * DOCS_ROOT  — this `*-studio` workspace (doc/, tests/, scripts/, baseline yaml).

Any prompt that instructs an agent to operate on code from the current working
directory (``git diff``, ``rg ... app/...``, reading ``app/<mod>.py``) silently
breaks under the split: ``app/`` does not exist in DOCS_ROOT, only in CODE_ROOT.

What this script does
---------------------
* CHECK (default): scan prompt-bearing markdown for fenced *instruction* prompt
  blocks that contain a code-scope operation but no two-root marker, and report
  them with file:line + matched signal. Exits non-zero if any are unguarded.
* FIX (``--fix``): insert a standardized, idempotent two-root preamble at the top
  of each qualifying block. Re-running is a no-op (guarded by a ``[two-root]``
  sentinel). Only instruction prompts that actually touch ``app/`` are edited.
* Always prints a "manual review" section for nuanced stale references that are
  NOT auto-rewritten (``last_review.sha``, singular ``report_file``,
  phantom ``app/prompts.py``) — fix those by hand like in prompts_catalog.md.

Usage
-----
    python scripts/check_prompt_two_root.py            # check, report, exit 1 if dirty
    python scripts/check_prompt_two_root.py --fix      # apply preamble inserts
    python scripts/check_prompt_two_root.py --all      # widen scope (incl. examples/snapshots)
    python scripts/check_prompt_two_root.py --json     # machine-readable report

Exit codes: 0 = clean (or --fix applied), 1 = unguarded blocks found (check mode), 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# --- Sentinel that marks an already-applied preamble (idempotency) --------------
SENTINEL = "[two-root]"

PREAMBLE = [
    "# [two-root] Two-repo project: resolve app/** and requirements.txt against CODE_ROOT",
    '# (editable install of `hometutor`: `pip show hometutor` -> "Editable project location");',
    "# resolve doc/**, tests/**, scripts/** against the current cwd (DOCS_ROOT).",
    "# Run git per-root: `git -C <CODE_ROOT> ...` for app code, `git -C <cwd> ...` for docs/tests.",
]

# Fenced-block info strings we treat as copy-paste prompts (preamble may be inserted).
PROMPT_INFO = {"", "text", "prompt"}
# Info strings we still scan for signals (report only), never auto-edit.
SCANNED_INFO = PROMPT_INFO | {"bash", "sh", "powershell", "ps1", "console"}

# Code-scope operations that break under the repo split (need CODE_ROOT).
CODE_SCOPE_SIGNALS = [
    ("git-diff", re.compile(r"\bgit\s+diff\b")),
    ("git-rev", re.compile(r"\bgit\s+(rev-parse|cat-file|log)\b")),
    ("rg-app", re.compile(r"\brg\s+[^\n]*\bapp/")),
    ("read-app-py", re.compile(r"\bapp/[\w/]+\.py\b")),
    ("shell-read-app", re.compile(r"\b(Get-Content|wc\s+-l|cat)\b[^\n]*\bapp/")),
    ("pip-editable", re.compile(r"\bpip\s+install\s+-e\b")),
    ("scan-app-dir", re.compile(r"--type\s+py[^\n]*\bapp/|\bapp/\s*--type\s+py")),
]

# Markers that identify a block as an *agent instruction* (vs example output / data).
INSTRUCTION_MARKERS = re.compile(
    r"(Goal:|Ignore prior responses|Read ONLY|Read-Set|Write-set|Write-Set|"
    r"\bDoD\b|You are|Role:|MANDATORY|PRE-SCAN|Phase\s+\d|Фаза|Scope\b)",
    re.IGNORECASE,
)

# Already two-root aware?
TWO_ROOT_MARKER = re.compile(r"CODE_ROOT|DOCS_ROOT|\[two-root\]|Editable project location")

# Nuanced stale references — reported for MANUAL fix, never auto-rewritten.
MANUAL_SIGNALS = [
    ("last_review.sha (single-repo; use code_sha/docs_sha)", re.compile(r"last_review\.sha|<last_review\.sha>")),
    ("singular report_file (schema is report_files: list)", re.compile(r"\breport_file\b(?!s)")),
    ("phantom app/prompts.py (does not exist; use app/tutor_prompts.py)", re.compile(r"\bapp/prompts\.py\b")),
]

# Default prompt-bearing scope (active prompts). --all widens it.
DEFAULT_GLOBS = [
    "doc/prompts_catalog.md",
    "doc/agent_workflow_arch_review.md",
    "doc/agent_workflow_templates.md",
    "doc/team_workflow/*.md",
    "doc/team_workflow/guides/*.md",
    "doc/prompts/*.md",
]
ALL_GLOBS = ["doc/**/*.md"]

# Historical/snapshot/example files: scanned only with --all, never default-fixed.
EXCLUDE_SUBSTR = (
    "/examples/",
    "/audit_groups_",
    "/ssr_ai_vision/",
)
EXCLUDE_NAME_RE = re.compile(r"(audit_report|readiness_gate|_summary|_20\d\d-\d\d|retrospectiv)", re.IGNORECASE)


@dataclass
class Block:
    start: int          # 0-based line index of opening fence
    end: int            # 0-based line index of closing fence
    info: str
    signals: list[str] = field(default_factory=list)
    is_instruction: bool = False
    has_marker: bool = False

    @property
    def actionable(self) -> bool:
        """Qualifies for auto-preamble: instruction prompt, touches app/, no marker."""
        return (
            self.info in PROMPT_INFO
            and self.is_instruction
            and bool(self.signals)
            and not self.has_marker
        )


@dataclass
class FileReport:
    path: Path
    blocks: list[Block] = field(default_factory=list)
    manual: list[tuple[int, str]] = field(default_factory=list)  # (1-based line, label)

    @property
    def actionable_blocks(self) -> list[Block]:
        return [b for b in self.blocks if b.actionable]


_FENCE_RE = re.compile(r"^(\s*)```(\S*)\s*$")


def parse_blocks(lines: list[str]) -> list[Block]:
    blocks: list[Block] = []
    i = 0
    n = len(lines)
    while i < n:
        m = _FENCE_RE.match(lines[i])
        if not m:
            i += 1
            continue
        info = m.group(2).lower()
        start = i
        j = i + 1
        while j < n and not _FENCE_RE.match(lines[j]):
            j += 1
        # j is closing fence (or EOF)
        body = "\n".join(lines[start + 1 : j])
        if info in SCANNED_INFO:
            blk = Block(start=start, end=j, info=info)
            blk.signals = [name for name, rx in CODE_SCOPE_SIGNALS if rx.search(body)]
            blk.is_instruction = bool(INSTRUCTION_MARKERS.search(body))
            blk.has_marker = bool(TWO_ROOT_MARKER.search(body))
            blocks.append(blk)
        i = j + 1
    return blocks


def scan_manual(lines: list[str]) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for idx, line in enumerate(lines, start=1):
        for label, rx in MANUAL_SIGNALS:
            if rx.search(line):
                hits.append((idx, label))
    return hits


def collect_files(use_all: bool, explicit: list[str]) -> list[Path]:
    if explicit:
        return [Path(p) if Path(p).is_absolute() else REPO_ROOT / p for p in explicit]
    globs = ALL_GLOBS if use_all else DEFAULT_GLOBS
    seen: dict[Path, None] = {}
    for g in globs:
        for p in REPO_ROOT.glob(g):
            if not p.is_file():
                continue
            posix = p.as_posix()
            if not use_all and (
                any(s in posix for s in EXCLUDE_SUBSTR) or EXCLUDE_NAME_RE.search(p.name)
            ):
                continue
            seen[p] = None
    return sorted(seen)


def build_report(path: Path) -> FileReport:
    lines = path.read_text(encoding="utf-8").splitlines()
    rep = FileReport(path=path)
    rep.blocks = parse_blocks(lines)
    rep.manual = scan_manual(lines)
    return rep


def apply_fix(path: Path) -> int:
    """Insert preamble into actionable blocks. Returns count inserted."""
    lines = path.read_text(encoding="utf-8").splitlines()
    blocks = parse_blocks(lines)
    inserts = {b.start: b for b in blocks if b.actionable}
    if not inserts:
        return 0
    out: list[str] = []
    for idx, line in enumerate(lines):
        out.append(line)
        if idx in inserts:
            out.extend(PREAMBLE)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return len(inserts)


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fix", action="store_true", help="insert two-root preamble into actionable blocks")
    ap.add_argument("--all", action="store_true", help="widen scope to all doc/**/*.md (incl. snapshots/examples)")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON report")
    ap.add_argument("files", nargs="*", help="explicit files to scan (overrides default globs)")
    args = ap.parse_args(argv)

    files = collect_files(args.all, args.files)
    reports = [build_report(p) for p in files]

    if args.json:
        payload = {
            "files": [
                {
                    "path": rel(r.path),
                    "actionable_blocks": [
                        {"line": b.start + 1, "info": b.info, "signals": b.signals}
                        for b in r.actionable_blocks
                    ],
                    "manual": [{"line": ln, "label": lbl} for ln, lbl in r.manual],
                }
                for r in reports
            ]
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        total = sum(len(r.actionable_blocks) for r in reports)
        return 0 if (args.fix or total == 0) else 1

    total_actionable = 0
    total_fixed = 0
    total_manual = 0

    for r in reports:
        actionable = r.actionable_blocks
        if not actionable and not r.manual:
            continue
        print(f"\n{rel(r.path)}")
        for b in actionable:
            total_actionable += 1
            print(f"  L{b.start + 1:<5} prompt block ({b.info or 'plain'}) - code-scope, no two-root marker"
                  f"  [signals: {', '.join(b.signals)}]")
        if args.fix and actionable:
            inserted = apply_fix(r.path)
            total_fixed += inserted
            print(f"  -> inserted two-root preamble into {inserted} block(s)")
        for ln, lbl in r.manual:
            total_manual += 1
            print(f"  L{ln:<5} MANUAL: {lbl}")

    print("\n" + "=" * 60)
    if args.fix:
        print(f"FIX: inserted preamble into {total_fixed} block(s) across "
              f"{sum(1 for r in reports if r.actionable_blocks)} file(s).")
    else:
        print(f"CHECK: {total_actionable} actionable block(s) need two-root preamble "
              f"(run with --fix to apply).")
    print(f"MANUAL: {total_manual} nuanced stale reference(s) - fix by hand "
          f"(last_review.sha -> code_sha/docs_sha, report_file -> report_files, app/prompts.py -> app/tutor_prompts.py).")
    print("=" * 60)

    if args.fix:
        return 0
    return 1 if total_actionable else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        raise SystemExit(130)
