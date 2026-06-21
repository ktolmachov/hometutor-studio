#!/usr/bin/env python3
"""
Measure line/byte counts and rough token estimates for token-safety registry.

Usage:
  python scripts/measure_token_registry.py           # print JSON to stdout
  python scripts/measure_token_registry.py --write # write doc/token_safety_registry.json

Estimation: est_tokens = file_size_bytes // chars_per_token (default 4).

После крупных изменений в «тяжёлых» файлах проекта: выполнить --write,
затем при необходимости синхронизировать числа в тексте doc/token_safety.md
(см. раздел «Поддержка документации» в том файле).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_OUT = ROOT / "doc" / "token_safety_registry.json"
CHARS_PER_TOKEN = 4

# Paths that must never be full-read in LLM context (hints for agents / check_readset).
FORBIDDEN_HINTS: dict[str, str] = {
    "app/ingestion.py": 'rg -n "^class|^def " app/ingestion.py',
    "app/ingestion_loader.py": 'rg -n "^class|^def " app/ingestion_loader.py',
    "app/query_service.py": 'rg -n "^class|^def " app/query_service.py',
    "app/prompts/_impl.py": 'rg -n "^def|^[A-Z_].*=" app/prompts/_impl.py',
    "app/knowledge_graph.py": 'rg -n "^class|^def " app/knowledge_graph.py',
    "tests/test_api.py": 'rg -n "def test_" tests/test_api.py  # then open one test',
    "tests/test_query_service.py": 'rg -n "def test_" tests/test_query_service.py  # one case',
    "doc/changelog.md": "tail / last 2-3 entries or append stub only",
    "doc/adr.md": "## Status table or single ADR section only",
    "doc/architecture.md": "module list or single ## section only",
    "doc/cjm.md": "single journey / pain-point section only",
    "doc/epochs/e4.md": "header + target fragment only (file is very large)",
    "scripts/run_autonomous.py": 'rg -n "^class|^def " scripts/run_autonomous.py',
    "scripts/generate_orchestration_prompt.py": (
        'rg -n "^class|^def " scripts/generate_orchestration_prompt.py'
    ),
}

# All paths we want stats for (union of safety tables + check_readset).
MEASURE_PATHS = sorted(
    set(
        list(FORBIDDEN_HINTS.keys())
        + [
            "app/tutor_orchestrator.py",
            "app/learner_model_service.py",
            "app/learning_plan_service.py",
            "app/retrieval.py",
            "app/retrieval_strategies.py",
            "app/graph_retrieval.py",
            "app/config.py",
            "app/pipeline_steps.py",
            "doc/conventions_architecture.md",
            "doc/conventions_reference.md",
            "doc/observability_slo.md",
            "doc/api_reference.md",
            "doc/user_guide_details.md",
            "doc/tasklist.md",
            "doc/conventions.md",
            "app/api.py",
            "app/models.py",
            "app/tutor_prompts.py",
            "tests/conftest.py",
            "doc/closed_iterations.md",
            "doc/technical_specification.md",
            "doc/user_guide.md",
            "requirements.txt",
            "scripts/check_llm_context_gate.py",
            "scripts/check_backlog_drift.py",
            "scripts/context_cart.py",
            "scripts/generate_orchestration_prompt.py",
            "app/ui/main.py",
            "doc/agent_workflow.md",
            "doc/agent_workflow_rules.md",
            "doc/agent_workflow_cycle.md",
            "doc/agent_workflow_templates.md",
            "doc/agent_workflow_arch_review.md",
            "doc/agent_workflow_test_bundles.md",
        ]
    )
)


def measure(rel: str) -> dict:
    path = ROOT / rel.replace("/", os.sep)
    if not path.is_file():
        return {"lines": 0, "bytes": 0, "est_tokens": 0, "missing": True}
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="ignore")
    lines = len(text.splitlines())
    b = len(raw)
    est = b // CHARS_PER_TOKEN
    meta: dict = {"lines": lines, "bytes": b, "est_tokens": est}
    if rel in FORBIDDEN_HINTS:
        meta["full_read"] = "forbidden"
        meta["safe_hint"] = FORBIDDEN_HINTS[rel]
    return meta


def build_document() -> dict:
    files: dict[str, dict] = {}
    for rel in MEASURE_PATHS:
        files[rel.replace("\\", "/")] = measure(rel)
    return {
        "measured_at": date.today().isoformat(),
        "chars_per_token": CHARS_PER_TOKEN,
        "budgets": {"target_input_tokens": 12_000, "hard_input_tokens": 20_000},
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help=f"Write {REGISTRY_OUT.relative_to(ROOT)}",
    )
    args = parser.parse_args()
    doc = build_document()
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    if args.write:
        REGISTRY_OUT.parent.mkdir(parents=True, exist_ok=True)
        REGISTRY_OUT.write_text(text, encoding="utf-8")
        print(f"Wrote {REGISTRY_OUT}", file=sys.stderr)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
