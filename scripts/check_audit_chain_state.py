"""Check audit-chain artifacts for prompt/report/json coverage consistency."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_GROUP_SECTIONS = (
    "## Coverage Completion Prompt",
    "## Raw JSON Update",
    "## Coverage Analysis Refresh",
)


def period_slug(period: str) -> str:
    return period.replace("..", "__")


def resolve_team_workflow_top_level_audit_md(root: Path, basename: str) -> Path:
    """Find audit/coverage prompt md: ``doc/team_workflow`` first, else ``archive/doc_team_workflow``.

    Top-level prompts may move to archive to keep ``doc/team_workflow/*.md`` count ≤48
    without breaking audit tooling.
    """
    primary = root / "doc" / "team_workflow" / basename
    if primary.is_file():
        return primary
    return root / "archive" / "doc_team_workflow" / basename


def report(status: str, message: str) -> None:
    print(f"{status}: {message}")


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def group_id_from_path(path: Path) -> str | None:
    match = re.match(r"(group_\d+)_", path.name)
    return match.group(1) if match else None


def group_sort_key(path: Path) -> int:
    group_id = group_id_from_path(path)
    if not group_id:
        return 10**9
    return int(group_id.split("_", 1)[1])


def relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def extract_next_action_group_id(text: str) -> str | None:
    match = re.search(r"audit_groups_[^/\s]+/(group_\d+)_[^\s`]+\.md", text)
    return match.group(1) if match else None


def format_group_list(group_ids: list[str]) -> str:
    return ", ".join(f"`{group_id}`" for group_id in group_ids) if group_ids else "none"


def build_next_action_block(
    *,
    completed_group_ids: list[str],
    next_group_file: Path | None,
    root: Path,
    period: str,
    target_agent: str,
) -> str:
    completed = format_group_list(completed_group_ids)
    slug = period_slug(period)
    if next_group_file is None:
        next_text = """All groups completed.

Recommended final run:

```powershell
.\\.venv\\Scripts\\python.exe scripts/check_audit_chain_state.py --period {period} --target-agent {target_agent} --write-next-action --write-summary --write-raw-check --json-out archive/team_artifacts/audit_{slug}/audit_chain_state.json
```""".format(period=period, target_agent=target_agent, slug=slug)
    else:
        next_path = relative_posix(next_group_file, root)
        next_text = f"""Recommended next safe run:

```text
Read {next_path}
and execute the instructions.
```"""

    return f"""## Next Action

Completed coverage groups: {completed}.

{next_text}

After each group, run:

```powershell
.\\.venv\\Scripts\\python.exe scripts/check_audit_chain_state.py --period {period} --target-agent {target_agent} --write-next-action --write-summary --write-raw-check --json-out archive/team_artifacts/audit_{slug}/audit_chain_state.json
```

The next group is safe to start only after the check is PASS or any reported
FAIL is intentionally resolved.
"""


def replace_next_action_block(text: str, new_block: str) -> str:
    pattern = re.compile(r"## Next Action\n.*?(?=\n## |\Z)", re.DOTALL)
    if pattern.search(text):
        return pattern.sub(lambda _match: new_block.rstrip() + "\n", text, count=1)
    return new_block.rstrip() + "\n\n" + text


def write_final_summary(
    *,
    path: Path,
    period: str,
    target_agent: str,
    group_files: list[Path],
    coverage_groups: dict,
    report_files: list[Path],
    coverage_analysis: Path,
    raw_json: Path,
    next_group_file: Path | None,
    warnings: list[str],
    errors: list[str],
    root: Path,
) -> None:
    package_rows: list[tuple[str, str, str, str, str]] = []
    blockers: list[tuple[str, str]] = []
    pass_count = fail_count = stale_count = 0
    commands: list[str] = []

    for group_id, group in sorted(coverage_groups.items()):
        if not isinstance(group, dict):
            continue
        for command in group.get("commands_run", []):
            if command and command not in commands:
                commands.append(command)
        for package in group.get("packages", []):
            for command in package.get("commands_run", []):
                if command and command not in commands:
                    commands.append(command)
            result = package.get("coverage_result", "UNKNOWN")
            if result == "PASS":
                pass_count += 1
            elif result == "FAIL":
                fail_count += 1
            elif result == "STALE":
                stale_count += 1
            package_id = package.get("package_id", "")
            added_tests = ", ".join(package.get("added_tests", [])) or "-"
            dod = ", ".join(package.get("dod_commands", [])) or "-"
            package_rows.append((group_id, package_id, result, added_tests, dod))
            for blocker in package.get("blockers", []):
                blockers.append((package_id, str(blocker)))

    completed_ids = sorted(coverage_groups)
    all_group_ids = [group_id_from_path(path) for path in group_files]
    all_group_ids = [group_id for group_id in all_group_ids if group_id]
    next_group = relative_posix(next_group_file, root) if next_group_file else "none"
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    lines = [
        f"# Final Coverage Audit Summary - {period} / {target_agent}",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "## Summary",
        "",
        f"- Groups total: {len(group_files)}",
        f"- Groups completed: {len(completed_ids)} / {len(group_files)}",
        f"- Next group: `{next_group}`",
        f"- Coverage reports: {len(report_files)}",
        f"- Packages PASS: {pass_count}",
        f"- Packages FAIL: {fail_count}",
        f"- Packages STALE: {stale_count}",
        f"- Raw JSON: `{relative_posix(raw_json, root)}`",
        f"- Coverage analysis: `{relative_posix(coverage_analysis, root)}`",
        "",
        "## Groups",
        "",
        "| Group | Status | Report |",
        "|---|---|---|",
    ]
    report_by_group = {path.name.split("_dod_coverage_report.md", 1)[0]: path for path in report_files}
    for group_id in all_group_ids:
        report_path = report_by_group.get(group_id)
        status = "completed" if group_id in coverage_groups else "pending"
        report_text = f"`{relative_posix(report_path, root)}`" if report_path else "-"
        lines.append(f"| `{group_id}` | {status} | {report_text} |")

    lines.extend(["", "## Package Results", "", "| Group | Package | Result | Added Tests | DoD Commands |", "|---|---|---|---|---|"])
    if package_rows:
        for group_id, package_id, result, added_tests, dod in package_rows:
            lines.append(f"| `{group_id}` | `{package_id}` | {result} | {added_tests} | {dod} |")
    else:
        lines.append("| - | - | - | - | - |")

    lines.extend(["", "## Commands Run", ""])
    if commands:
        lines.extend(f"- `{command}`" for command in commands)
    else:
        lines.append("- none recorded")

    lines.extend(["", "## Blockers", ""])
    if blockers:
        lines.extend(f"- `{package_id}`: {blocker}" for package_id, blocker in blockers)
    else:
        lines.append("- none")

    lines.extend(["", "## Check Warnings", ""])
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- none")

    lines.extend(["", "## Check Errors", ""])
    if errors:
        lines.extend(f"- {error}" for error in errors)
    else:
        lines.append("- none")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_state(
    *,
    period: str,
    target_agent: str,
    group_files: list[Path],
    coverage_groups: dict,
    report_files: list[Path],
    next_group_file: Path | None,
    completed_pass_packages: set[str],
    warnings: list[str],
    errors: list[str],
    stale_next_action: bool,
    root: Path,
    summary_path: Path,
    raw_json: Path,
    coverage_analysis: Path,
) -> dict:
    group_ids = [group_id_from_path(path) for path in group_files]
    group_ids = [group_id for group_id in group_ids if group_id]
    completed_group_ids = sorted(coverage_groups)
    pending_group_ids = [group_id for group_id in group_ids if group_id not in coverage_groups]
    next_group = relative_posix(next_group_file, root) if next_group_file else None

    package_counts = {"PASS": 0, "FAIL": 0, "STALE": 0, "UNKNOWN": 0}
    blockers: list[dict] = []
    for group_id, group in sorted(coverage_groups.items()):
        if not isinstance(group, dict):
            continue
        for package in group.get("packages", []):
            result = package.get("coverage_result", "UNKNOWN")
            package_counts[result if result in package_counts else "UNKNOWN"] += 1
            for blocker in package.get("blockers", []):
                blockers.append(
                    {
                        "group_id": group_id,
                        "package_id": package.get("package_id"),
                        "blocker": str(blocker),
                    }
                )

    return {
        "period": period,
        "target_agent": target_agent,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "FAIL" if errors else "PASS",
        "groups_total": len(group_files),
        "groups_completed": len(completed_group_ids),
        "completed_group_ids": completed_group_ids,
        "pending_group_ids": pending_group_ids,
        "next_group": next_group,
        "next_group_id": group_id_from_path(next_group_file) if next_group_file else None,
        "all_groups_completed": next_group_file is None and bool(group_files),
        "coverage_reports": len(report_files),
        "completed_pass_packages": len(completed_pass_packages),
        "package_counts": package_counts,
        "stale_next_action": stale_next_action,
        "warnings": warnings,
        "errors": errors,
        "blockers": blockers,
        "summary_path": relative_posix(summary_path, root),
        "raw_json": relative_posix(raw_json, root),
        "coverage_analysis": relative_posix(coverage_analysis, root),
    }


def write_archive_readme(
    *,
    path: Path,
    state: dict,
    root: Path,
    runbook_path: Path,
) -> None:
    next_group = state["next_group"] or "all groups completed"
    lines = [
        f"# Audit {state['period']} / {state['target_agent']}",
        "",
        "## Status",
        "",
        f"- Chain status: {state['status']}",
        f"- Groups completed: {state['groups_completed']} / {state['groups_total']}",
        f"- Next group: `{next_group}`",
        f"- Packages PASS: {state['package_counts']['PASS']}",
        f"- Packages FAIL: {state['package_counts']['FAIL']}",
        f"- Packages STALE: {state['package_counts']['STALE']}",
        "",
        "## Files",
        "",
        f"- Runbook: `{relative_posix(runbook_path, root)}`",
        f"- Raw JSON: `{state['raw_json']}`",
        f"- Final summary: `{state['summary_path']}`",
        f"- Coverage analysis: `{state['coverage_analysis']}`",
        "",
        "## Next Command",
        "",
        "```powershell",
        f".\\.venv\\Scripts\\python.exe scripts/check_audit_chain_state.py --period {state['period']} --target-agent {state['target_agent']} --write-next-action --write-summary --write-raw-check --json-out archive/team_artifacts/audit_{period_slug(state['period'])}/audit_chain_state.json",
        "```",
        "",
    ]
    if state["next_group"]:
        lines.extend(
            [
                "## Next Group Prompt",
                "",
                "```text",
                f"Read {state['next_group']}",
                "and execute the instructions.",
                "```",
                "",
            ]
        )
    else:
        lines.extend(["## Next Group Prompt", "", "All groups completed.", ""])

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", required=True)
    parser.add_argument("--target-agent", required=True)
    parser.add_argument("--write-next-action", action="store_true")
    parser.add_argument("--write-summary", action="store_true")
    parser.add_argument("--write-raw-check", action="store_true")
    parser.add_argument("--fail-on-stale-next-action", action="store_true")
    parser.add_argument("--json-out")
    args = parser.parse_args()

    root = Path.cwd()
    slug = period_slug(args.period)
    target = args.target_agent

    ap_name = f"audit_prompt_{slug}_{target}.md"
    cov_name = f"audit_coverage_prompt_{slug}_{target}.md"
    audit_prompt = resolve_team_workflow_top_level_audit_md(root, ap_name)
    coverage_prompt = resolve_team_workflow_top_level_audit_md(root, cov_name)
    group_dir = root / "doc" / "team_workflow" / f"audit_groups_{slug}_{target}"
    group_readme = group_dir / "run_next_group_coverage_audit.md"
    coverage_analysis = group_dir / "coverage_dod_analysis.md"
    audit_dir = root / "archive" / "team_artifacts" / f"audit_{slug}"
    raw_json = audit_dir / "_audit_raw.json"
    summary_path = audit_dir / "final_coverage_audit_summary.md"
    archive_readme = audit_dir / "README.md"

    required_files = [
        audit_prompt,
        coverage_prompt,
        group_readme,
        coverage_analysis,
        raw_json,
    ]

    errors: list[str] = []
    warnings: list[str] = []

    for path in required_files:
        if not path.exists():
            errors.append(f"missing required artifact: {path}")

    group_files = sorted(group_dir.glob("group_*.md"), key=group_sort_key) if group_dir.exists() else []
    if not group_files:
        errors.append(f"no group files found in {group_dir}")

    for group_file in group_files:
        text = group_file.read_text(encoding="utf-8")
        missing = [section for section in REQUIRED_GROUP_SECTIONS if section not in text]
        if missing:
            errors.append(f"{group_file} missing sections: {', '.join(missing)}")

    raw: dict = {}
    coverage_groups: dict = {}
    if raw_json.exists():
        raw = load_json(raw_json)
        coverage_groups = raw.get("coverage_groups", {})
        if not isinstance(coverage_groups, dict):
            errors.append("coverage_groups exists but is not an object")
            coverage_groups = {}
    else:
        warnings.append("cannot inspect coverage_groups because _audit_raw.json is missing")

    report_files = sorted(audit_dir.glob("group_*_dod_coverage_report.md")) if audit_dir.exists() else []
    report_group_ids = {
        match.group(1)
        for path in report_files
        if (match := re.match(r"(group_\d+)_dod_coverage_report\.md$", path.name))
    }

    for group_id in sorted(report_group_ids):
        if group_id not in coverage_groups:
            errors.append(f"{group_id} has markdown report but no coverage_groups entry")

    completed_group_ids = sorted(coverage_groups)
    for group_id in completed_group_ids:
        expected_report = audit_dir / f"{group_id}_dod_coverage_report.md"
        if not expected_report.exists():
            warnings.append(f"{group_id} has coverage_groups entry but missing {expected_report}")

    next_group_file = None
    for group_file in group_files:
        group_id = group_id_from_path(group_file)
        if group_id and group_id not in coverage_groups:
            next_group_file = group_file
            break

    if group_readme.exists():
        runbook_text = group_readme.read_text(encoding="utf-8")
        actual_next_id = extract_next_action_group_id(runbook_text)
        expected_next_id = group_id_from_path(next_group_file) if next_group_file else None
        stale_next_action = actual_next_id != expected_next_id
        if stale_next_action:
            if expected_next_id is None:
                warnings.append(
                    "Next Action is stale: all groups are completed, but runbook still points "
                    f"to {actual_next_id}"
                )
            else:
                warnings.append(
                    "Next Action is stale: "
                    f"points to {actual_next_id}, expected {expected_next_id}"
                )
            if args.fail_on_stale_next_action:
                errors.append("Next Action is stale")

        if args.write_next_action:
            next_block = build_next_action_block(
                completed_group_ids=completed_group_ids,
                next_group_file=next_group_file,
                root=root,
                period=args.period,
                target_agent=target,
            )
            updated_text = replace_next_action_block(runbook_text, next_block)
            if updated_text != runbook_text:
                group_readme.write_text(updated_text, encoding="utf-8")
                report("INFO", f"updated Next Action in {group_readme}")
                stale_next_action = False
    else:
        stale_next_action = False

    completed_pass_packages: set[str] = set()
    for group in coverage_groups.values():
        if not isinstance(group, dict):
            continue
        for package in group.get("packages", []):
            if package.get("coverage_result") == "PASS":
                package_id = package.get("package_id")
                if package_id:
                    completed_pass_packages.add(package_id)

    if coverage_analysis.exists() and completed_pass_packages:
        analysis_text = coverage_analysis.read_text(encoding="utf-8")
        for package_id in sorted(completed_pass_packages):
            line_match = re.search(rf"^\| `{re.escape(package_id)}` \|.+$", analysis_text, re.MULTILINE)
            if line_match and "| PASS |" not in line_match.group(0):
                errors.append(f"{package_id} is PASS in raw json but not PASS in coverage analysis")

    if isinstance(raw, dict):
        if "summary" not in raw or not isinstance(raw["summary"], dict):
            raw["summary"] = {}
        summary = raw["summary"]
    else:
        summary = {}
    expected_total = len(
        [
            package
            for group in coverage_groups.values()
            if isinstance(group, dict)
            for package in group.get("packages", [])
        ]
    )
    if summary.get("coverage_packages_total") not in (None, expected_total):
        if args.write_raw_check:
            summary["coverage_packages_total"] = expected_total
            warnings.append(f"auto-healed summary.coverage_packages_total to {expected_total}")
        else:
            errors.append(
                "summary.coverage_packages_total does not match coverage_groups package count "
                f"({summary.get('coverage_packages_total')} != {expected_total})"
            )

    if args.write_summary:
        if audit_dir.exists():
            write_final_summary(
                path=summary_path,
                period=args.period,
                target_agent=target,
                group_files=group_files,
                coverage_groups=coverage_groups,
                report_files=report_files,
                coverage_analysis=coverage_analysis,
                raw_json=raw_json,
                next_group_file=next_group_file,
                warnings=warnings,
                errors=errors,
                root=root,
            )
            report("INFO", f"wrote final summary to {summary_path}")

    state = build_state(
        period=args.period,
        target_agent=target,
        group_files=group_files,
        coverage_groups=coverage_groups,
        report_files=report_files,
        next_group_file=next_group_file,
        completed_pass_packages=completed_pass_packages,
        warnings=warnings,
        errors=errors,
        stale_next_action=stale_next_action,
        root=root,
        summary_path=summary_path,
        raw_json=raw_json,
        coverage_analysis=coverage_analysis,
    )

    if args.write_summary and audit_dir.exists():
        write_archive_readme(
            path=archive_readme,
            state=state,
            root=root,
            runbook_path=group_readme,
        )
        report("INFO", f"wrote archive README to {archive_readme}")

    if args.write_raw_check and raw_json.exists():
        raw["last_chain_check"] = state
        raw_json.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report("INFO", f"updated last_chain_check in {raw_json}")

    if args.json_out:
        json_out = Path(args.json_out)
        if not json_out.is_absolute():
            json_out = root / json_out
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report("INFO", f"wrote JSON state to {json_out}")

    for warning in warnings:
        report("WARN", warning)
    for error in errors:
        report("FAIL", error)

    if errors:
        return 2

    report("PASS", f"audit chain artifacts look consistent for {args.period}/{target}")
    report("INFO", f"group files: {len(group_files)}")
    report("INFO", f"coverage groups completed: {len(coverage_groups)}")
    report("INFO", f"coverage reports: {len(report_files)}")
    report("INFO", f"completed PASS packages: {len(completed_pass_packages)}")
    if next_group_file:
        report("INFO", f"next group: {relative_posix(next_group_file, root)}")
    else:
        report("INFO", "next group: all groups completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
