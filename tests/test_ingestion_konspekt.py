"""Tests for flat Markdown / konspekt ingestion (Шаг 1 — Задача 0)."""

from pathlib import Path

import pytest

from app.ingestion_sections import (
    FlatMarkdownReader,
    _parse_md_frontmatter,
)


# ---------------------------------------------------------------------------
# _parse_md_frontmatter
# ---------------------------------------------------------------------------

def test_parse_md_frontmatter_strips_yaml():
    text = "---\ntype: konspekt\ntags: [lecture]\n---\n\n# Body\nSome text."
    meta, body = _parse_md_frontmatter(text)
    assert meta == {"type": "konspekt", "tags": ["lecture"]}
    assert "---" not in body
    assert "# Body" in body


def test_parse_md_frontmatter_no_frontmatter():
    text = "# Just a heading\nNo YAML here."
    meta, body = _parse_md_frontmatter(text)
    assert meta == {}
    assert body == text


def test_parse_md_frontmatter_invalid_yaml_returns_empty_meta():
    text = "---\n: invalid: : yaml\n---\n\nBody text."
    meta, body = _parse_md_frontmatter(text)
    # Should not raise; returns empty meta and body without frontmatter block
    assert isinstance(meta, dict)
    assert "Body text" in body


# ---------------------------------------------------------------------------
# FlatMarkdownReader
# ---------------------------------------------------------------------------

def test_flat_markdown_reader_returns_single_document(tmp_path: Path):
    md = tmp_path / "урок.md"
    md.write_text(
        "---\ntype: konspekt\ntags: [lecture]\n---\n\n# Heading\nContent here.",
        encoding="utf-8",
    )
    docs = FlatMarkdownReader().load_data(md)
    assert len(docs) == 1, "FlatMarkdownReader must return exactly one Document per file"


def test_flat_markdown_reader_strips_frontmatter_from_body(tmp_path: Path):
    md = tmp_path / "урок.md"
    md.write_text(
        "---\ntype: konspekt\nsource: some/path.txt\n---\n\n# Heading\nContent here.",
        encoding="utf-8",
    )
    doc = FlatMarkdownReader().load_data(md)[0]
    # Body should not contain raw YAML markers
    assert "---" not in doc.text
    assert "type: konspekt" not in doc.text
    assert "# Heading" in doc.text


def test_flat_markdown_reader_stores_frontmatter_as_md_prefix(tmp_path: Path):
    md = tmp_path / "урок.md"
    md.write_text(
        "---\ntype: konspekt\ntags: [конспект, lecture, ai-agents]\nsource: path/file.txt\n---\n\nBody.",
        encoding="utf-8",
    )
    doc = FlatMarkdownReader().load_data(md)[0]
    assert doc.metadata.get("md_type") == "konspekt"
    # Tags list is joined as comma-separated string
    assert "lecture" in doc.metadata.get("md_tags", "")
    assert doc.metadata.get("md_source") == "path/file.txt"


def test_flat_markdown_reader_excludes_frontmatter_from_embeddings(tmp_path: Path):
    """CRITICAL: md_* + _md_flat must NOT pollute the embedding/LLM text.

    The whole reason we strip YAML from the body is to keep sha256/tags out of
    embeddings — storing them as metadata without excluding would reintroduce the
    noise on every chunk.
    """
    from llama_index.core.schema import MetadataMode

    md = tmp_path / "урок.md"
    sha = "dd5203e8bc85a45696c9797b6b241308c7343167b92bc276e4ad28c5377afe2e"
    md.write_text(
        f"---\ntype: konspekt\nsource_sha256: {sha}\ntags: [konspekt, lecture]\n---\n\n"
        "# Конспект\nТело лекции.",
        encoding="utf-8",
    )
    doc = FlatMarkdownReader().load_data(md)[0]

    embed_text = doc.get_content(metadata_mode=MetadataMode.EMBED)
    llm_text = doc.get_content(metadata_mode=MetadataMode.LLM)

    # Hash and frontmatter keys must be absent from both retrieval channels
    assert sha not in embed_text
    assert sha not in llm_text
    assert "md_source_sha256" not in embed_text
    assert "_md_flat" not in embed_text
    # But the body content survives
    assert "Тело лекции" in embed_text
    # And metadata is still queryable programmatically (for doc_kind / filters)
    assert doc.metadata.get("md_type") == "konspekt"
    assert "md_source_sha256" in doc.excluded_embed_metadata_keys
    assert "_md_flat" in doc.excluded_embed_metadata_keys


def test_flat_markdown_reader_sets_md_flat_flag(tmp_path: Path):
    md = tmp_path / "урок.md"
    md.write_text("# No frontmatter\nJust text.", encoding="utf-8")
    doc = FlatMarkdownReader().load_data(md)[0]
    assert doc.metadata.get("_md_flat") is True


def test_flat_markdown_reader_no_frontmatter_returns_full_body(tmp_path: Path):
    md = tmp_path / "plain.md"
    md.write_text("# Heading\nParagraph.", encoding="utf-8")
    doc = FlatMarkdownReader().load_data(md)[0]
    assert "# Heading" in doc.text
    assert doc.metadata.get("_md_flat") is True


# ---------------------------------------------------------------------------
# doc_kind override in _add_metadata (integration via ingestion internals)
# ---------------------------------------------------------------------------

def test_doc_kind_from_frontmatter_lecture_tag(tmp_path: Path, monkeypatch):
    """_add_metadata should set doc_kind='lecture' for konspekt with lecture tag."""
    import app.ingestion as ing

    # Patch DATA_DIR so relative_path resolves correctly
    monkeypatch.setattr(ing, "DATA_DIR", tmp_path)

    topic_dir = tmp_path / "ИИ Агенты"
    topic_dir.mkdir()
    md = topic_dir / "урок 1.md"
    md.write_text(
        "---\ntype: konspekt\ntags: [конспект, lecture, ai-agents]\n---\n\nBody text.",
        encoding="utf-8",
    )

    from llama_index.core import Document
    doc = Document(
        text="Body text.",
        metadata={
            "file_path": str(md),
            "md_type": "konspekt",
            "md_tags": "конспект,lecture,ai-agents",
            "_md_flat": True,
        },
    )
    docs = ing._add_metadata([doc])
    assert docs[0].metadata["doc_kind"] == "lecture"


def test_doc_kind_from_frontmatter_defaults_to_lecture_for_konspekt(tmp_path: Path, monkeypatch):
    """konspekt without explicit category tag defaults to 'lecture'."""
    import app.ingestion as ing

    monkeypatch.setattr(ing, "DATA_DIR", tmp_path)

    topic_dir = tmp_path / "Курс"
    topic_dir.mkdir()
    md = topic_dir / "материал.md"
    md.write_text("---\ntype: konspekt\ntags: [конспект]\n---\n\nBody.", encoding="utf-8")

    from llama_index.core import Document
    doc = Document(
        text="Body.",
        metadata={
            "file_path": str(md),
            "md_type": "konspekt",
            "md_tags": "конспект",
            "_md_flat": True,
        },
    )
    docs = ing._add_metadata([doc])
    assert docs[0].metadata["doc_kind"] == "lecture"


def test_doc_kind_not_overridden_for_non_konspekt(tmp_path: Path, monkeypatch):
    """Regular .txt files should not be affected by konspekt doc_kind logic."""
    import app.ingestion as ing

    monkeypatch.setattr(ing, "DATA_DIR", tmp_path)

    topic_dir = tmp_path / "lectures" / "Курс"
    topic_dir.mkdir(parents=True)
    txt = topic_dir / "lecture.txt"
    txt.write_text("Raw transcript text.", encoding="utf-8")

    from llama_index.core import Document
    doc = Document(
        text="Raw transcript text.",
        metadata={"file_path": str(txt)},
    )
    docs = ing._add_metadata([doc])
    # Should infer 'lecture' from path, not konspekt logic
    assert docs[0].metadata["doc_kind"] == "lecture"
    assert "md_type" not in docs[0].metadata
