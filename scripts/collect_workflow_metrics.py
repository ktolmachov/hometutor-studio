#!/usr/bin/env python3
"""Collect smart-workflow business, system, and model metrics."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from summarize_cost_logs import (
    DEFAULT_COST_LOG_DIR,
    _build_summary_payload,
    load_cost_rows,
)

ROOT = Path(__file__).resolve().parents[1]
TEAM_ARTIFACTS = ROOT / "archive" / "team_artifacts"
TIMING_DIR = TEAM_ARTIFACTS / "_timing"
WORKFLOW_METRICS_DIR = ROOT / "archive" / "workflow_metrics"
PIPELINE_METRICS = ROOT / "archive" / "pipeline_metrics.md"
REGISTRY = ROOT / "doc" / "backlog_registry.yaml"
TRIGGER_METRIC_FILES = {
    "cursor": TEAM_ARTIFACTS / "_metrics" / "cursor_agent_trigger.jsonl",
    "deepseek": TEAM_ARTIFACTS / "_metrics" / "deepseek_agent_trigger.jsonl",
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"status": "parse_error", "raw": line[:500]})
    return rows


def _load_registry() -> dict[str, Any]:
    if not REGISTRY.exists():
        return {}
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8")) or {}


def _registry_items_by_id(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = registry.get("items") or []
    return {
        str(item.get("id") or item.get("package_id")): item
        for item in items
        if isinstance(item, dict) and (item.get("id") or item.get("package_id"))
    }


def _pipeline_rows() -> list[dict[str, str]]:
    if not PIPELINE_METRICS.exists():
        return []
    rows: list[dict[str, str]] = []
    for line in PIPELINE_METRICS.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 8 or cells[0].lower() == "package":
            continue
        rows.append(
            {
                "package": cells[0],
                "date": cells[1],
                "mode": cells[2],
                "sp2": cells[3],
                "retries": cells[4],
                "escalations": cells[5],
                "failures": cells[6],
                "complexity": cells[7],
            }
        )
    return rows


def _latest_timing(script_name: str, *, limit: int = 10) -> list[dict[str, Any]]:
    files = sorted(TIMING_DIR.glob(f"*__{script_name}.json"), key=lambda p: p.stat().st_mtime)
    out: list[dict[str, Any]] = []
    for path in files[-limit:]:
        payload = _read_json(path)
        if not payload:
            continue
        phases = payload.get("phases") or []
        out.append(
            {
                "file": str(path.relative_to(ROOT)),
                "run_id": payload.get("run_id"),
                "script_name": payload.get("script_name"),
                "total_seconds": payload.get("total"),
                "phase_seconds": {
                    str(phase.get("name")): phase.get("seconds")
                    for phase in phases
                    if isinstance(phase, dict)
                },
                "phase_rc": {
                    str(phase.get("name")): phase.get("rc")
                    for phase in phases
                    if isinstance(phase, dict) and phase.get("rc") is not None
                },
            }
        )
    return out


def _extract_changed_paths(contract_text: str) -> list[str]:
    paths = set(
        re.findall(
            r"\b(?:app|tests|scripts|doc|archive)/[A-Za-z0-9_./-]+\.(?:py|ts|tsx|md|yaml|json)",
            contract_text.replace("\\", "/"),
        )
    )
    return sorted(paths)


def _package_artifact_metrics(package_id: str, item: dict[str, Any]) -> dict[str, Any]:
    artifact_dir = TEAM_ARTIFACTS / package_id
    contract = artifact_dir / "execution_contract.md"
    contract_text = contract.read_text(encoding="utf-8", errors="replace") if contract.exists() else ""
    dod_cache = _read_json(artifact_dir / "dod_cache.json")
    orchestration_files = sorted(artifact_dir.glob("orchestration_*.md"))
    return {
        "package_id": package_id,
        "status": item.get("status"),
        "wave": item.get("wave_id") or item.get("wave"),
        "owner": item.get("owner"),
        "user_stories": item.get("user_stories") or [],
        "cjm_moments": item.get("cjm_moments") or [],
        "has_orchestration": bool(orchestration_files),
        "orchestration_files": [str(p.relative_to(ROOT)) for p in orchestration_files],
        "has_execution_contract": contract.exists(),
        "execution_contract_bytes": contract.stat().st_size if contract.exists() else 0,
        "execution_contract_ready": bool(contract_text.strip())
        and contract_text.strip().upper() != "STARTED",
        "changed_paths_from_contract": _extract_changed_paths(contract_text),
        "dod_result": dod_cache.get("result"),
        "dod_command_count": len(dod_cache.get("commands") or []),
        "dod_commands": dod_cache.get("commands") or [],
        "post_closure_audit_task": (artifact_dir / "post_closure_audit_task.md").exists(),
    }


def _business_metrics(packages: list[dict[str, Any]], registry: dict[str, Any]) -> dict[str, Any]:
    waves = registry.get("waves") or []
    return {
        "packages_analyzed": len(packages),
        "packages_closed": sum(1 for p in packages if p.get("status") == "closed"),
        "user_stories_touched": sorted({us for p in packages for us in p.get("user_stories", [])}),
        "cjm_moments_touched": sorted({cjm for p in packages for cjm in p.get("cjm_moments", [])}),
        "waves_completed": [
            w.get("id") for w in waves if isinstance(w, dict) and w.get("status") == "completed"
        ],
        "dod_pass_packages": sum(1 for p in packages if p.get("dod_result") == "pass"),
        "artifact_complete_packages": sum(
            1
            for p in packages
            if p.get("has_orchestration")
            and p.get("execution_contract_ready")
            and p.get("post_closure_audit_task")
        ),
    }


def _system_metrics(
    packages: list[dict[str, Any]], pipeline_rows: list[dict[str, str]]
) -> dict[str, Any]:
    package_ids = {p["package_id"] for p in packages}
    relevant_pipeline = [row for row in pipeline_rows if row.get("package") in package_ids]
    return {
        "pipeline_rows": relevant_pipeline,
        "closure_modes": dict(Counter(row.get("mode") or "unknown" for row in relevant_pipeline)),
        "complexities": dict(Counter(row.get("complexity") or "unknown" for row in relevant_pipeline)),
        "latest_run_autonomous_timing": _latest_timing("run_autonomous", limit=max(2, len(packages) + 2)),
        "latest_orchestration_timing": _latest_timing(
            "generate_orchestration_prompt", limit=max(2, len(packages) + 2)
        ),
        "missing_execution_contracts": [
            p["package_id"] for p in packages if not p.get("execution_contract_ready")
        ],
        "missing_orchestration": [p["package_id"] for p in packages if not p.get("has_orchestration")],
    }


def _model_metrics(limit_cost_files: int, top: int) -> dict[str, Any]:
    cost_rows = load_cost_rows(DEFAULT_COST_LOG_DIR, limit_files=limit_cost_files)
    cost_summary = (
        _build_summary_payload(cost_rows, topn=top)
        if cost_rows
        else {
            "records": 0,
            "status_counts": {},
            "top_models": {},
            "context_length_errors": 0,
            "char_limit_warnings": 0,
            "top_by_chars": [],
            "top_by_input_tokens": [],
            "context_length_incidents": [],
        }
    )
    trigger_rows_by_name = {
        name: _read_jsonl(path) for name, path in TRIGGER_METRIC_FILES.items()
    }
    trigger_rows = [
        {**row, "trigger": name}
        for name, rows in trigger_rows_by_name.items()
        for row in rows
    ]
    trigger_durations = {
        name: [
            int(row.get("duration_ms") or 0)
            for row in rows
            if str(row.get("event") or "").endswith("_agent_prompt")
        ]
        for name, rows in trigger_rows_by_name.items()
    }
    return {
        "llm_cost_logs": cost_summary,
        "trigger_metrics_paths": {
            name: str(path.relative_to(ROOT)) for name, path in TRIGGER_METRIC_FILES.items()
        },
        "trigger_records": len(trigger_rows),
        "trigger_statuses": dict(Counter(str(row.get("status") or "unknown") for row in trigger_rows)),
        "trigger_duration_ms": {
            name: {
                "min": min(durations) if durations else None,
                "max": max(durations) if durations else None,
                "avg": round(sum(durations) / len(durations), 2) if durations else None,
            }
            for name, durations in trigger_durations.items()
        },
        "trigger_latest": trigger_rows[-top:] if trigger_rows else [],
    }


def build_report(package_ids: list[str], *, limit_cost_files: int, top: int) -> dict[str, Any]:
    registry = _load_registry()
    items_by_id = _registry_items_by_id(registry)
    if not package_ids:
        pipeline = _pipeline_rows()
        package_ids = [row["package"] for row in pipeline[-2:]]
    packages = [
        _package_artifact_metrics(package_id, items_by_id.get(package_id, {}))
        for package_id in package_ids
    ]
    return {
        "packages": packages,
        "business": _business_metrics(packages, registry),
        "system": _system_metrics(packages, _pipeline_rows()),
        "model": _model_metrics(limit_cost_files, top),
        "known_metric_gaps": [
            "workflow.py loop-level total time is visible in console but not yet persisted as a single loop-run JSON",
            "historical trigger calls before JSONL metrics support have no trigger records",
            "older pipeline_metrics.md rows may still contain legacy TBD placeholders until their packages are refreshed or audited",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    business = report["business"]
    system = report["system"]
    model = report["model"]
    lines = [
        "# Workflow Metrics Report",
        "",
        "## Business",
        f"- Packages analyzed: {business['packages_analyzed']}",
        f"- Packages closed: {business['packages_closed']}",
        f"- User stories touched: {', '.join(business['user_stories_touched']) or '-'}",
        f"- CJM moments touched: {', '.join(business['cjm_moments_touched']) or '-'}",
        f"- DoD pass packages: {business['dod_pass_packages']}",
        f"- Artifact-complete packages: {business['artifact_complete_packages']}",
        "",
        "## System",
        f"- Closure modes: {system['closure_modes']}",
        f"- Complexities: {system['complexities']}",
        f"- Missing execution contracts: {system['missing_execution_contracts'] or '-'}",
        f"- Missing orchestration: {system['missing_orchestration'] or '-'}",
        "",
        "## Model",
        f"- Cost log records: {model['llm_cost_logs']['records']}",
        f"- Cost log statuses: {model['llm_cost_logs']['status_counts']}",
        f"- Top models: {model['llm_cost_logs']['top_models']}",
        f"- Context-length errors: {model['llm_cost_logs']['context_length_errors']}",
        f"- Trigger records: {model['trigger_records']}",
        f"- Trigger statuses: {model['trigger_statuses']}",
        f"- Trigger duration ms: {model['trigger_duration_ms']}",
        "",
        "## Packages",
    ]
    for package in report["packages"]:
        lines.extend(
            [
                f"### {package['package_id']}",
                f"- Status: {package.get('status') or '-'}",
                f"- Wave: {package.get('wave') or '-'}",
                f"- User stories: {', '.join(package.get('user_stories') or []) or '-'}",
                f"- Orchestration: {package['has_orchestration']}",
                f"- Execution contract ready: {package['execution_contract_ready']} ({package['execution_contract_bytes']} bytes)",
                f"- DoD: {package.get('dod_result') or '-'} ({package['dod_command_count']} commands)",
                f"- Changed paths from contract: {', '.join(package['changed_paths_from_contract']) or '-'}",
                "",
            ]
        )
    lines.extend(["## Known Metric Gaps"])
    lines.extend(f"- {gap}" for gap in report["known_metric_gaps"])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", action="append", dest="packages", default=[])
    parser.add_argument("--limit-cost-files", type=int, default=7)
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    parser.add_argument("--write", action="store_true", help="Write default JSON and Markdown reports")
    args = parser.parse_args()

    report = build_report(args.packages, limit_cost_files=args.limit_cost_files, top=args.top)
    if args.write:
        WORKFLOW_METRICS_DIR.mkdir(parents=True, exist_ok=True)
        args.json_out = args.json_out or (WORKFLOW_METRICS_DIR / "latest.json")
        args.md_out = args.md_out or (WORKFLOW_METRICS_DIR / "latest.md")
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(render_markdown(report), encoding="utf-8")
    if not args.json_out and not args.md_out:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
