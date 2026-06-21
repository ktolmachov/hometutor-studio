"""Tests for document-level RAG adversarial runner (corpus + guardrail metrics)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.adversarial_test_runner import (
    ADVERSARIAL_MANIFEST,
    DEFENSE_DATASET,
    EVAL_ROOT,
    run_adversarial_rag_suite,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_adversarial_suite_report_schema():
    report = run_adversarial_rag_suite()
    assert report["summary"]["cases_total"] >= 1
    assert "guardrail_effectiveness" in report
    g = report["guardrail_effectiveness"]
    for key in ("injection", "no_answer_grounding", "conflicting_sources"):
        assert key in g
        assert g[key]["total"] >= 1
        assert g[key]["passed"] == g[key]["total"]
    assert report["summary"]["all_passed"] is True
    for case in report["cases"]:
        assert "id" in case and "type" in case and "passed" in case and "trace" in case
        assert isinstance(case["trace"], dict)


def test_each_case_includes_security_trace_on_structure():
    report = run_adversarial_rag_suite()
    for case in report["cases"]:
        assert len(case["trace"]) >= 1


def test_manifest_and_dataset_paths_exist():
    assert DEFENSE_DATASET.is_file()
    assert ADVERSARIAL_MANIFEST.is_file()
    data = json.loads(DEFENSE_DATASET.read_text(encoding="utf-8"))
    for item in data["categories"]["injection"]:
        p = EVAL_ROOT / str(item["injected_document"])
        assert p.is_file(), f"missing injection fixture {p}"


def test_conflict_corpus_files_exist():
    manifest = json.loads(ADVERSARIAL_MANIFEST.read_text(encoding="utf-8-sig"))
    for block in manifest["conflicts"]:
        for rel in block["source_paths"]:
            assert (EVAL_ROOT / rel).is_file(), f"missing conflict doc {rel}"


def test_runner_round_trip_json_report():
    report = run_adversarial_rag_suite()
    blob = json.dumps(report, ensure_ascii=False, sort_keys=True)
    again = json.loads(blob)
    assert again == report
