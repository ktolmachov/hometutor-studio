"""US-2.4 source readiness MVP — классификация файлов в data/."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.source_readiness import build_source_readiness_summary


def _settings(**kwargs):
    return SimpleNamespace(
        home_rag_e2e_offline=kwargs.get("home_rag_e2e_offline", False),
        ingest_docling_enabled=kwargs.get("ingest_docling_enabled", False),
        ingest_docling_min_native_text_chars=kwargs.get(
            "ingest_docling_min_native_text_chars",
            80,
        ),
    )


def test_empty_data_directory(tmp_path):
    summary = build_source_readiness_summary(tmp_path, _settings())
    assert summary["counts"] == {
        "text_ready": 0,
        "needs_ocr": 0,
        "extraction_failed": 0,
        "unsupported_format": 0,
        "problematic": 0,
    }
    assert summary["supported_files_total"] == 0
    assert summary["readiness_score"] == 0.0
    assert "Добавьте поддерживаемые" in summary["primary_next_action"]


def test_text_file_text_ready(tmp_path):
    (tmp_path / "note.txt").write_text(
        "Достаточно длинного текста для индекса.",
        encoding="utf-8",
    )
    summary = build_source_readiness_summary(tmp_path, _settings())
    assert summary["counts"]["text_ready"] == 1
    assert summary["counts"]["problematic"] == 0
    assert summary["readiness_score"] == 1.0
    assert summary["files"][0]["bucket"] == "text_ready"
    assert summary["files"][0]["next_action"] == ""


def test_empty_file_extraction_failed(tmp_path):
    (tmp_path / "empty.md").write_bytes(b"")
    summary = build_source_readiness_summary(tmp_path, _settings())
    assert summary["counts"]["extraction_failed"] == 1
    assert summary["counts"]["problematic"] == 1
    assert summary["files"][0]["next_action"]


def test_image_needs_ocr_even_when_docling_off(tmp_path):
    (tmp_path / "scan.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
    summary = build_source_readiness_summary(
        tmp_path,
        _settings(ingest_docling_enabled=False),
    )
    assert summary["counts"]["needs_ocr"] == 1
    assert "OCR" in summary["files"][0]["reason"]


def test_blank_pdf_needs_ocr(tmp_path):
    pytest.importorskip("pypdf")
    from pypdf import PdfWriter

    pdf_path = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with open(pdf_path, "wb") as fh:
        writer.write(fh)

    summary = build_source_readiness_summary(tmp_path, _settings())
    assert summary["counts"]["needs_ocr"] == 1
    assert summary["files"][0]["path"] == "blank.pdf"


def test_offline_stub():
    summary = build_source_readiness_summary(Path("."), _settings(home_rag_e2e_offline=True))
    assert summary["counts"]["text_ready"] == 1
    assert "E2E" in summary["primary_next_action"]


def test_criteria_keys_and_us_note(tmp_path):
    (tmp_path / "x.txt").write_text("hello world контент", encoding="utf-8")
    summary = build_source_readiness_summary(tmp_path, _settings())
    for key in (
        "text_ready",
        "needs_ocr",
        "extraction_failed",
        "unsupported_format",
        "problematic",
    ):
        assert key in summary["criteria"]
        assert summary["criteria"][key]
    assert "US-2.3" in summary["us_2_3_note"]


def test_primary_action_docling_off_with_needs_ocr(tmp_path):
    (tmp_path / "scan.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    summary = build_source_readiness_summary(
        tmp_path,
        _settings(ingest_docling_enabled=False),
    )
    assert "Включите Docling" in summary["primary_next_action"]


def test_primary_action_docling_on_with_needs_ocr(tmp_path):
    (tmp_path / "scan.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    summary = build_source_readiness_summary(
        tmp_path,
        _settings(ingest_docling_enabled=True),
    )
    assert "переиндексацию" in summary["primary_next_action"].lower()
