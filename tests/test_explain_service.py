import pytest

import app.explain_service as explain_service
from app.path_safety import validate_data_relative_path


def test_get_file_content_reads_text_file(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    file_path = data_dir / "note.txt"
    # Длина ≥ SHORT_EXTRACT_THRESHOLD (100), иначе _read_file уходит в LLM-fallback.
    content = "hello world\n" * 10
    file_path.write_text(content, encoding="utf-8")

    monkeypatch.setattr(explain_service, "DATA_DIR", data_dir)

    result = explain_service.get_file_content("note.txt")

    assert result["content"] == content


def test_get_file_content_blocks_path_traversal(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    outside_file = tmp_path / "secret.txt"
    outside_file.write_text("secret", encoding="utf-8")

    monkeypatch.setattr(explain_service, "DATA_DIR", data_dir)

    with pytest.raises(ValueError):
        explain_service.get_file_content("../secret.txt")


def test_validate_data_relative_path_normalizes_safe_path(tmp_path):
    data_dir = tmp_path / "data"
    nested = data_dir / "course"
    nested.mkdir(parents=True)
    (nested / "note.md").write_text("hello", encoding="utf-8")

    assert validate_data_relative_path("course/../course/note.md", data_dir=data_dir) == "course/note.md"


def test_validate_data_relative_path_rejects_absolute_escape(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    outside = tmp_path / "secret.md"
    outside.write_text("secret", encoding="utf-8")

    with pytest.raises(ValueError):
        validate_data_relative_path(str(outside), data_dir=data_dir)


def test_get_file_content_rejects_non_text_files(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    file_path = data_dir / "archive.zip"
    file_path.write_bytes(b"PK\x03\x04")

    monkeypatch.setattr(explain_service, "DATA_DIR", data_dir)

    with pytest.raises(ValueError):
        explain_service.get_file_content("archive.zip")


def test_get_file_content_reads_html_as_text(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    file_path = data_dir / "page.html"
    body = "Hello " * 25
    html = f"<html><body><p>{body}</p></body></html>"
    file_path.write_text(html, encoding="utf-8")

    monkeypatch.setattr(explain_service, "DATA_DIR", data_dir)

    result = explain_service.get_file_content("page.html")

    assert "Hello" in result["content"]


def test_get_file_content_reads_pdf_via_extractor(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    file_path = data_dir / "manual.pdf"
    file_path.write_bytes(b"%PDF-1.4")

    # Длина ≥ SHORT_EXTRACT_THRESHOLD (100), иначе _read_file уходит в LLM-fallback и тянет реальный LLM.
    long_pdf = "pdf content\n" * 15

    monkeypatch.setattr(explain_service, "DATA_DIR", data_dir)
    monkeypatch.setattr(
        explain_service,
        "_extract_pdf_text",
        lambda path, max_chars: long_pdf[:max_chars],
    )

    result = explain_service.get_file_content("manual.pdf")

    assert result["content"] == long_pdf


def test_get_file_content_reads_docx(tmp_path, monkeypatch):
    pytest.importorskip("docx")
    from docx import Document as DocxDocument

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    file_path = data_dir / "notes.docx"
    doc = DocxDocument()
    for i in range(10):
        doc.add_paragraph(f"Hello from docx paragraph {i}")
    doc.save(str(file_path))

    monkeypatch.setattr(explain_service, "DATA_DIR", data_dir)

    result = explain_service.get_file_content("notes.docx")

    assert "Hello from docx" in result["content"]


def test_short_extract_triggers_llm_fallback(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    file_path = data_dir / "thin.pdf"
    file_path.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(explain_service, "DATA_DIR", data_dir)
    monkeypatch.setattr(explain_service, "_extract_pdf_text", lambda path, max_chars: "x" * 50)
    monkeypatch.setattr(
        explain_service,
        "_gather_extended_source_for_fallback",
        lambda path, suffix: "extended pdf text " * 20,
    )
    monkeypatch.setattr(
        explain_service,
        "_llm_fallback_plaintext",
        lambda extended, rel: "Recovered meaningful text for preview.",
    )

    result = explain_service.get_file_content("thin.pdf")

    assert "Recovered meaningful" in result["content"]


def test_short_extract_skips_llm_when_no_api_key(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    file_path = data_dir / "thin.txt"
    file_path.write_text("short", encoding="utf-8")

    monkeypatch.setattr(explain_service, "DATA_DIR", data_dir)
    monkeypatch.setattr(explain_service, "_gather_extended_source_for_fallback", lambda path, suffix: "more text")
    monkeypatch.setattr(
        "app.provider.get_ingestion_llm",
        lambda: (_ for _ in ()).throw(ValueError("no key")),
    )

    result = explain_service.get_file_content("thin.txt", max_chars=8000)

    assert result["content"] == "short"
