#!/usr/bin/env python3
"""
Lightweight docs gate for token-safety artifacts and prompt structure.

Checks:
  1. doc/token_safety_registry.json is valid and contains required entries.
  2. check_readset smoke: known-bad read-set must return BLOCK (exit 2).
  3. (--prompt-file) Structural validation of a planning or execution prompt:
       - planning prompt: Ignore/Fresh context, Read ONLY section, token budget,
         output format, absence of forbidden full-read paths.
       - execution prompt: write-set, DoD run commands, do-not-touch section,
         word count ≤ 500 (warn), absence of forbidden full-read paths.

Usage:
  python scripts/lint_agent_prompts.py
  python scripts/lint_agent_prompts.py --no-readset-check
  python scripts/lint_agent_prompts.py --prompt-file archive/agent_prompts/foo.md
  python scripts/lint_agent_prompts.py --prompt-text "Implement X only. ..."
"""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
from pathlib import Path

def _force_utf8_stdio() -> None:
    """Force UTF-8 output on Windows without breaking pytest imports."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    elif hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    elif hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "doc" / "token_safety_registry.json"

# Word-count targets
EXEC_WORD_WARN = 500    # warn above this (target is 400, allow some buffer)
EXEC_WORD_BLOCK = 800   # hard error above this

# Forbidden full-read patterns: if these appear as plain file paths
# in a prompt (not inside rg/grep commands), it's a violation.
FORBIDDEN_FULL_READ = {
    "app/query_service.py",
    "app/prompts/_impl.py",
    "app/knowledge_graph.py",
    "tests/test_api.py",
    "doc/changelog.md",
    "doc/adr.md",
    "doc/architecture.md",
    "doc/cjm.md",
    "doc/epochs/",
}

WORKFLOW_DOC_PATHS = (
    "doc/agent_workflow.md",
    "doc/agent_workflow_arch_review.md",
    "doc/agent_workflow_templates.md",
    "doc/team_workflow/orchestrator_template.md",
)

EXECUTION_CONTRACT_PROMPT_PATHS = (
    "scripts/run_autonomous.py",
    "scripts/workflow.py",
    "scripts/generate_orchestration_prompt.py",
    "doc/team_workflow",
)


# ---------------------------------------------------------------------------
# Registry lint (existing)
# ---------------------------------------------------------------------------

def lint_registry() -> list[str]:
    errs: list[str] = []
    if not REGISTRY.is_file():
        errs.append(
            f"Missing {REGISTRY.relative_to(ROOT)} — run: "
            "python scripts/measure_token_registry.py --write"
        )
        return errs
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"Invalid JSON in {REGISTRY}: {e}"]
    if "files" not in data or "measured_at" not in data:
        errs.append("token_safety_registry.json: expected keys files, measured_at")
        return errs
    for path in ("app/prompts/_impl.py", "doc/changelog.md"):
        meta = data["files"].get(path)
        if not meta:
            errs.append(f"token_safety_registry.json: missing entry {path}")
            continue
        if meta.get("full_read") != "forbidden":
            errs.append(f"token_safety_registry.json: {path} must be full_read forbidden")
    return errs


def lint_agent_adapters() -> list[str]:
    """Ensure orchestration agent adapter files resolve (guides/ canonical layout)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import prompt_utils as pu  # noqa: WPS433 — local import avoids import-time side effects at module load

    errs: list[str] = []
    for agent_id, path in pu.agent_adapters_map().items():
        if not path.is_file():
            errs.append(f"Missing agent adapter for {agent_id}: {path.relative_to(ROOT)}")
    return errs


def lint_readset_smoke() -> list[str]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "check_readset.py"),
        "app/prompts/_impl.py",
        "tests/test_api.py",
    ]
    proc = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if proc.returncode != 2:
        return [
            "check_readset smoke: expected exit code 2 (BLOCK) for "
            f"app/prompts/_impl.py + tests/test_api.py, got {proc.returncode}:\n"
            f"{proc.stdout}\n{proc.stderr}"
        ]
    return []


def _iter_workflow_docs() -> list[Path]:
    docs = [(ROOT / rel).resolve() for rel in WORKFLOW_DOC_PATHS]
    return [p for p in docs if p.exists()]


def _is_fallback_line(line: str) -> bool:
    lowered = line.lower()
    return "fallback" in lowered or "if .venv" in lowered or "если .venv" in lowered


def lint_workflow_docs() -> list[str]:
    errs: list[str] = []
    docs = _iter_workflow_docs()
    if not docs:
        return ["workflow docs lint: no files matched target globs"]

    stale_budget_patterns = (
        r"Hard-limit\s*>\s*30k",
        r"Soft-limit\s*20k[-–]30k",
        r"target\s*(?:<=|≤)\s*20k",
        r"Token budget:\s*(?:<=|≤)\s*20k",
    )
    py_script_pattern = re.compile(r"\bpython\s+scripts/[^\s`]+", re.IGNORECASE)
    py_pytest_pattern = re.compile(r"\bpython\s+-m\s+pytest\b", re.IGNORECASE)
    md_link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

    for path in docs:
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()

        for idx, line in enumerate(lines, 1):
            for pat in stale_budget_patterns:
                if re.search(pat, line, re.IGNORECASE):
                    errs.append(f"{rel}:{idx}: stale token budget wording: {line.strip()}")

            if py_script_pattern.search(line) and not _is_fallback_line(line):
                if "{{RUN_CMD}}" in line:
                    continue
                errs.append(
                    f"{rel}:{idx}: use .venv-first python command instead of `{line.strip()}`"
                )

            if py_pytest_pattern.search(line) and ".venv\\Scripts\\python.exe" not in line and not _is_fallback_line(line):
                errs.append(
                    f"{rel}:{idx}: pytest command must be .venv-first: `{line.strip()}`"
                )

        for idx, line in enumerate(lines, 1):
            for match in md_link_pattern.finditer(line):
                target = match.group(1).strip()
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                if target.startswith("#"):
                    continue
                link_target = target.split("#", 1)[0]
                if not link_target or link_target.startswith("<"):
                    continue
                candidate = (path.parent / link_target).resolve()
                if not candidate.exists():
                    errs.append(
                        f"{rel}:{idx}: broken local markdown link `{target}`"
                    )
    return errs


def _iter_execution_contract_prompt_paths() -> list[Path]:
    paths: list[Path] = []
    for rel in EXECUTION_CONTRACT_PROMPT_PATHS:
        root = ROOT / rel
        if root.is_file():
            paths.append(root)
        elif root.is_dir():
            paths.extend(root.rglob("*.md"))
    return paths


def lint_execution_contract_encoding_commands() -> list[str]:
    errs: list[str] = []
    out_file_re = re.compile(r"\bOut-File\b.*\bexecution_contract\.md\b", re.IGNORECASE)
    utf8_re = re.compile(r"-Encoding\s+utf-?8", re.IGNORECASE)

    for path in _iter_execution_contract_prompt_paths():
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for idx, line in enumerate(text.splitlines(), 1):
            if out_file_re.search(line) and not utf8_re.search(line):
                errs.append(
                    f"{rel}:{idx}: Out-File writing execution_contract.md must specify UTF-8 "
                    "or use Set-Content -Encoding utf8"
                )
    return errs


# ---------------------------------------------------------------------------
# Prompt structure lint (new)
# ---------------------------------------------------------------------------

def _extract_prompt_text(path: Path) -> str:
    """
    Extract prompt body from an archive .md file.
    Looks for a ```text ... ``` fenced block; falls back to full file text.
    """
    raw = path.read_text(encoding="utf-8")
    m = re.search(r"```text\n(.*?)```", raw, re.DOTALL)
    return m.group(1).strip() if m else raw.strip()


def _detect_prompt_type(text: str, filename: str) -> str:
    """
    Return 'execution', 'planning', or 'unknown'.
    Detection order: filename hint → content markers.
    """
    name = filename.lower()
    if "exec_prompt" in name:
        return "execution"
    if "planning_prompt" in name:
        return "planning"
    # Content-based detection
    if re.search(r"stay strictly in write.set|implement .+ only", text, re.IGNORECASE):
        return "execution"
    if re.search(r"шаблон planning prompt|generate a planning prompt|read only.*max.*files", text, re.IGNORECASE):
        return "planning"
    return "unknown"


def _check_forbidden_full_reads(text: str, label: str) -> list[str]:
    """
    Error if a forbidden file appears as a bare full-read reference.

    A reference is considered SAFE when:
    - The line is a shell command (rg, grep, python …)
    - The line or adjacent lines (±1) contain safe-access qualifiers:
      "only", "fragment", "section", "signatures", "row"
    - The line or adjacent lines contain exclusion context:
      "do not", "forbidden", "avoid", "full broad reads" (negative context)
    """
    errs = []
    safe_qualifiers = re.compile(
        r"\bonly\b|fragment|section|signatures|--signatures|\brow\b|"
        r"do not|do NOT|Don.t|forbidden|avoid|запрещено|не читать|"
        r"full broad reads|primary sources",
        re.IGNORECASE,
    )
    cmd_pattern = re.compile(r"^\s*(rg|grep|python|bash|cat)\s", re.IGNORECASE)

    lines = text.splitlines()
    for forbidden in FORBIDDEN_FULL_READ:
        flagged = False
        for i, line in enumerate(lines):
            if forbidden not in line:
                continue
            if cmd_pattern.match(line):
                continue
            # Build a context window: current line + line before + line after
            window_lines = lines[max(0, i - 1): i + 2]
            window = "\n".join(window_lines)
            if safe_qualifiers.search(window):
                continue
            flagged = True
            break
        if flagged:
            errs.append(
                f"{label}: forbidden full-read reference to `{forbidden}` "
                "(use rg/grep/signatures or a targeted section instead)"
            )
    return errs


def lint_planning_prompt(text: str, label: str = "planning prompt") -> tuple[list[str], list[str]]:
    """
    Structural checks for a planning prompt (step-2 or Final planning prompt).
    Returns (errors, warnings).
    """
    errs: list[str] = []
    warns: list[str] = []

    required = [
        (
            r"ignore prior responses|fresh context only",
            "missing 'Ignore prior responses/tools. Fresh context only.'",
        ),
        (
            r"read only|read ONLY",
            "missing 'Read ONLY' section",
        ),
        (
            r"\boutput\b",
            "missing Output format specification",
        ),
        (
            r"20k|12k|token budget",
            "missing token budget specification",
        ),
    ]
    for pattern, msg in required:
        if not re.search(pattern, text, re.IGNORECASE):
            errs.append(f"{label}: {msg}")

    errs.extend(_check_forbidden_full_reads(text, label))
    return errs, warns


def lint_execution_prompt(text: str, label: str = "execution prompt") -> tuple[list[str], list[str]]:
    """
    Structural checks for a Copy-paste execution prompt (step-4/5 output).
    Returns (errors, warnings).
    """
    errs: list[str] = []
    warns: list[str] = []

    required = [
        (
            r"write.set|stay strictly in write.set|owner files",
            "missing write-set specification",
        ),
        (
            r"python -m pytest|pytest|rg |run:",
            "missing DoD run commands",
        ),
        (
            r"do not touch|do not modify|don.t touch|не трогать|out.of.scope",
            "missing 'do not touch' section",
        ),
        (
            r"return|output:",
            "missing Return/Output specification",
        ),
    ]
    for pattern, msg in required:
        if not re.search(pattern, text, re.IGNORECASE):
            errs.append(f"{label}: {msg}")

    # Word count
    word_count = len(text.split())
    if word_count > EXEC_WORD_BLOCK:
        errs.append(
            f"{label}: {word_count} words — exceeds hard limit {EXEC_WORD_BLOCK} "
            f"(target ≤ 400; compress scope or split into sub-packages)"
        )
    elif word_count > EXEC_WORD_WARN:
        warns.append(
            f"{label}: {word_count} words — above soft target of 400 "
            f"(consider compressing; hard limit is {EXEC_WORD_BLOCK})"
        )

    errs.extend(_check_forbidden_full_reads(text, label))
    return errs, warns


def lint_prompt(text: str, filename: str = "") -> tuple[list[str], list[str]]:
    """Auto-detect type and lint accordingly."""
    ptype = _detect_prompt_type(text, filename)
    label = f"{ptype} prompt" + (f" ({filename})" if filename else "")

    if ptype == "execution":
        return lint_execution_prompt(text, label)
    elif ptype == "planning":
        return lint_planning_prompt(text, label)
    else:
        # Unknown: run both and merge (lenient — only errors that appear in both)
        e1, w1 = lint_execution_prompt(text, label + " [exec?]")
        e2, w2 = lint_planning_prompt(text, label + " [plan?]")
        warns = [f"could not detect prompt type for {filename!r} — ran both checks"] + w1 + w2
        # Report only errors common to both types (avoid false positives)
        common = [e for e in e1 if any(kw in e for kw in ("write-set", "DoD", "do not touch"))]
        return common + [e for e in e2 if "Ignore prior" in e], warns


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    _force_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-readset-check", action="store_true", help="Skip check_readset subprocess smoke")
    parser.add_argument("--no-workflow-docs-check", action="store_true", help="Skip workflow docs contract lint")
    parser.add_argument("--prompt-file", metavar="FILE", help="Lint a prompt archive .md file")
    parser.add_argument("--prompt-text", metavar="TEXT", help="Lint a prompt passed as a string")
    args = parser.parse_args()

    all_errs: list[str] = []
    all_warns: list[str] = []

    # 1. Registry + readset smoke (always, unless --prompt-file/text only mode)
    all_errs.extend(lint_registry())
    if not args.no_readset_check:
        all_errs.extend(lint_readset_smoke())
    if not args.no_workflow_docs_check:
        all_errs.extend(lint_workflow_docs())
        all_errs.extend(lint_execution_contract_encoding_commands())
        all_errs.extend(lint_agent_adapters())

    # 2. Structural prompt lint
    if args.prompt_file:
        path = ROOT / args.prompt_file if not Path(args.prompt_file).is_absolute() else Path(args.prompt_file)
        if not path.exists():
            all_errs.append(f"--prompt-file: file not found: {path}")
        else:
            text = _extract_prompt_text(path)
            errs, warns = lint_prompt(text, path.name)
            all_errs.extend(errs)
            all_warns.extend(warns)

    if args.prompt_text:
        errs, warns = lint_prompt(args.prompt_text, "<inline>")
        all_errs.extend(errs)
        all_warns.extend(warns)

    # Output
    for w in all_warns:
        print(f"  WARN: {w}")

    if all_errs:
        print("lint_agent_prompts: FAILED", file=sys.stderr)
        for e in all_errs:
            print(f"  ERROR: {e}", file=sys.stderr)
        return 1

    status = "OK"
    if all_warns:
        status = "OK (with warnings)"
    print(f"lint_agent_prompts: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
