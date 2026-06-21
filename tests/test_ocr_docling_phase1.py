"""US-2.3 phase1: Docling/OCR path for non-text corpus (opt-in via settings)."""

from __future__ import annotations

from pathlib import Path

import pytest
from llama_index.core import Document

import app.ingestion as ing


def test_get_doc_supported_exts_includes_raster_when_docling_enabled(settings_env):
    settings_env({"INGEST_DOCLING_ENABLED": "false"})
    assert ".png" not in ing.get_doc_supported_exts()
    settings_env({"INGEST_DOCLING_ENABLED": "true"})
    assert ".png" in ing.get_doc_supported_exts()
    assert ".pdf" in ing.get_doc_supported_exts()


def test_image_load_routes_through_docling(monkeypatch, settings_env, tmp_path):
    settings_env({"INGEST_DOCLING_ENABLED": "true"})
    img = tmp_path / "page.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n\x00")

    def fake_docling(path: Path) -> list[Document]:
        assert path.resolve() == img.resolve()
        return [
            Document(
                text="ocr line",
                metadata={"file_path": str(path.resolve()), "source_extraction": "docling_ocr"},
            )
        ]

    monkeypatch.setattr(ing, "_load_via_docling", fake_docling)
    out = ing._load_one_file(img)
    assert len(out) == 1
    assert out[0].text == "ocr line"
    assert out[0].metadata.get("source_extraction") == "docling_ocr"


def test_pdf_low_native_text_falls_back_to_docling(monkeypatch, settings_env, tmp_path):
    settings_env({"INGEST_DOCLING_ENABLED": "true", "INGEST_DOCLING_MIN_NATIVE_TEXT_CHARS": "100"})
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    class FakeReader:
        def __init__(self, **kwargs: object) -> None:
            pass

        def load_data(self) -> list[Document]:
            return [Document(text="tiny", metadata={"file_path": str(pdf.resolve())})]

    monkeypatch.setattr(ing, "SimpleDirectoryReader", FakeReader)

    def fake_docling(path: Path) -> list[Document]:
        return [
            Document(
                text="from docling",
                metadata={"file_path": str(path.resolve()), "source_extraction": "docling_ocr"},
            )
        ]

    monkeypatch.setattr(ing, "_load_via_docling", fake_docling)
    out = ing._load_one_file(pdf)
    assert out[0].text == "from docling"
    assert out[0].metadata.get("source_extraction") == "docling_ocr"


def test_pdf_sufficient_native_text_stamps_native_and_skips_docling(monkeypatch, settings_env, tmp_path):
    settings_env({"INGEST_DOCLING_ENABLED": "true", "INGEST_DOCLING_MIN_NATIVE_TEXT_CHARS": "10"})
    pdf = tmp_path / "texty.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    class FakeReader:
        def __init__(self, **kwargs: object) -> None:
            pass

        def load_data(self) -> list[Document]:
            return [Document(text="x" * 80, metadata={"file_path": str(pdf.resolve())})]

    monkeypatch.setattr(ing, "SimpleDirectoryReader", FakeReader)

    def boom(_path: Path) -> list[Document]:
        raise AssertionError("docling must not run when native pdf text is sufficient")

    monkeypatch.setattr(ing, "_load_via_docling", boom)
    out = ing._load_one_file(pdf)
    assert out[0].metadata.get("source_extraction") == "native_text"
