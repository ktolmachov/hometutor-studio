"""US-2.5 — контракт source readiness (сводка + HTTP /kb/source-readiness)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import api as api_module
from app.source_readiness import build_source_readiness_summary

_ALLOWED_BUCKETS = frozenset(
    {"text_ready", "needs_ocr", "extraction_failed", "unsupported_format"}
)
_TOP_KEYS = frozenset(
    {
        "criteria",
        "counts",
        "readiness_score",
        "files",
        "primary_next_action",
        "ingest_docling_enabled",
        "us_2_3_note",
        "supported_files_total",
    }
)


def _settings(**kwargs):
    return SimpleNamespace(
        home_rag_e2e_offline=kwargs.get("home_rag_e2e_offline", False),
        ingest_docling_enabled=kwargs.get("ingest_docling_enabled", False),
        ingest_docling_min_native_text_chars=kwargs.get(
            "ingest_docling_min_native_text_chars",
            80,
        ),
    )


def _assert_contract_payload(data: dict) -> None:
    assert set(data.keys()) >= _TOP_KEYS
    crit = data["criteria"]
    for k in (
        "text_ready",
        "needs_ocr",
        "extraction_failed",
        "unsupported_format",
        "problematic",
    ):
        assert k in crit and isinstance(crit[k], str) and crit[k].strip()

    counts = data["counts"]
    for k in (
        "text_ready",
        "needs_ocr",
        "extraction_failed",
        "unsupported_format",
        "problematic",
    ):
        assert k in counts
        assert isinstance(counts[k], int) and counts[k] >= 0
    assert counts["problematic"] == counts["extraction_failed"] + counts["unsupported_format"]

    score = data["readiness_score"]
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0

    files = data["files"]
    assert isinstance(files, list)
    for row in files:
        assert set(row.keys()) >= {"path", "bucket", "reason", "next_action"}
        assert row["bucket"] in _ALLOWED_BUCKETS
        if row["bucket"] == "text_ready":
            assert row["next_action"] == ""
        else:
            assert row["next_action"].strip()


def test_build_summary_matches_stable_contract(tmp_path):
    (tmp_path / "a.txt").write_text("hello world контент", encoding="utf-8")
    summary = build_source_readiness_summary(tmp_path, _settings())
    _assert_contract_payload(summary)
    assert summary["counts"]["text_ready"] == 1
    assert summary["readiness_score"] == 1.0


def test_kb_source_readiness_http_contract():
    client = TestClient(api_module.app)
    response = client.get("/kb/source-readiness")
    assert response.status_code == 200
    _assert_contract_payload(response.json())
