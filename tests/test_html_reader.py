import tempfile
from pathlib import Path

from llama_index.core import Document

from app.ingestion import (
    HTMLTextReader,
    _add_metadata,
    _apply_contextualized_chunks,
    _expand_structured_documents,
)
from app.ingestion_loader import _build_nodes


def _write_html(tmp_dir: Path, content: str) -> Path:
    path = tmp_dir / "test.html"
    path.write_text(content, encoding="utf-8")
    return path


def test_strips_script_and_style():
    reader = HTMLTextReader()
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_html(
            Path(tmp),
            "<html><head><style>body{color:red}</style></head>"
            "<body><script>alert(1)</script><p>Hello world</p></body></html>",
        )
        docs = reader.load_data(path)

    assert len(docs) == 1
    assert "alert" not in docs[0].text
    assert "color:red" not in docs[0].text
    assert "Hello world" in docs[0].text


def test_strips_nav_header_footer():
    reader = HTMLTextReader()
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_html(
            Path(tmp),
            "<html><body>"
            "<nav>Menu item</nav>"
            "<header>Site header</header>"
            "<main><p>Main content</p></main>"
            "<footer>Copyright</footer>"
            "</body></html>",
        )
        docs = reader.load_data(path)

    text = docs[0].text
    assert "Menu item" not in text
    assert "Site header" not in text
    assert "Copyright" not in text
    assert "Main content" in text


def test_extracts_title():
    reader = HTMLTextReader()
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_html(
            Path(tmp),
            "<html><head><title>Lecture 1</title></head>"
            "<body><p>Content</p></body></html>",
        )
        docs = reader.load_data(path)

    assert docs[0].metadata.get("html_title") == "Lecture 1"


def test_no_title():
    reader = HTMLTextReader()
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_html(
            Path(tmp),
            "<html><body><p>No title here</p></body></html>",
        )
        docs = reader.load_data(path)

    assert "html_title" not in docs[0].metadata
    assert "No title here" in docs[0].text


def test_preserves_extra_info():
    reader = HTMLTextReader()
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_html(Path(tmp), "<html><body><p>Text</p></body></html>")
        docs = reader.load_data(path, extra_info={"source": "test"})

    assert docs[0].metadata["source"] == "test"


def test_html_chunks_contain_no_css_js_nav_garbage(monkeypatch):
    """Проверка качества чанков: после полного пути HTML → ноды в чанках нет CSS, JS, навигации."""
    reader = HTMLTextReader()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        html_path = tmp_path / "lecture.html"
        html_path.write_text(
            "<!DOCTYPE html><html><head>"
            "<title>Lecture 1</title>"
            "<style>body{color:red; font-size:14px;}</style>"
            "<script>function init(){ alert('x'); } var x = 1;</script>"
            "</head><body>"
            "<nav><ul><li>Menu item</li><li>Home</li></ul></nav>"
            "<header>Site header</header>"
            "<main><p>Основной контент лекции. Второе предложение. Третье для чанка.</p></main>"
            "<footer>Copyright 2024</footer>"
            "</body></html>",
            encoding="utf-8",
        )
        docs = reader.load_data(html_path)
        for doc in docs:
            doc.metadata["file_path"] = str(html_path)

        monkeypatch.setattr("app.ingestion.DATA_DIR", tmp_path)
        documents = _add_metadata(docs)
        nodes = _build_nodes(documents)

    garbage_patterns = [
        "alert",
        "color:red",
        "font-size",
        "function init",
        "var x",
        "Menu item",
        "Site header",
        "Copyright 2024",
    ]
    for node in nodes:
        text = node.get_content()
        for pattern in garbage_patterns:
            assert pattern not in text, f"Chunk should not contain '{pattern}': {text[:200]}..."
    assert any("Основной контент лекции" in node.get_content() for node in nodes)


def test_html_reader_extracts_section_metadata():
    reader = HTMLTextReader()
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_html(
            Path(tmp),
            "<html><head><title>Lecture 1</title></head><body>"
            "<h1>Intro</h1><p>First concept.</p>"
            "<h2>Details</h2><p>Second concept.</p>"
            "</body></html>",
        )
        docs = reader.load_data(path)

    assert len(docs) == 2
    assert docs[0].metadata["section_path"] == "Intro"
    assert docs[0].metadata["section_level"] == 1
    assert docs[1].metadata["section_path"] == "Intro > Details"
    assert docs[1].metadata["section_level"] == 2


def test_markdown_documents_expand_into_sections():
    docs = [
        Document(
            text="# Intro\nOverview text.\n## Details\nMore detail here.",
            metadata={"file_path": "data/course/module/lesson.md"},
        )
    ]

    expanded = _expand_structured_documents(docs)

    assert len(expanded) == 2
    assert expanded[0].metadata["section_path"] == "Intro"
    assert expanded[1].metadata["section_path"] == "Intro > Details"
    assert "More detail here." in expanded[1].text


def test_add_metadata_keeps_structure_and_learning_fields(monkeypatch):
    docs = [
        Document(
            text="Section text",
            metadata={
                "file_path": "data/course_a/module_b/lecture_01/topic.md",
                "section_path": "Topic > Basics",
                "section_title": "Basics",
                "section_level": 2,
                "structural_path": "Topic > Basics",
            },
        )
    ]

    monkeypatch.setattr("app.ingestion.DATA_DIR", Path("data"))
    enriched = _add_metadata(docs)
    metadata = enriched[0].metadata

    assert metadata["course"] == "course_a"
    assert metadata["module"] == "module_b"
    assert metadata["lecture"] == "lecture_01"
    assert metadata["doc_kind"] == "lecture"
    assert metadata["section_path"] == "Topic > Basics"


def test_contextualized_chunks_include_structural_header():
    docs = [
        Document(
            text="Dense retrieval compares semantic vectors.",
            metadata={
                "file_name": "lesson.md",
                "title": "Hybrid Retrieval",
                "section_path": "Intro > Dense Retrieval",
                "doc_kind": "lecture",
                "difficulty": "intermediate",
                "topic": "retrieval",
            },
        )
    ]

    contextualized = _apply_contextualized_chunks(docs)
    text = contextualized[0].text

    assert "Document: Hybrid Retrieval" in text
    assert "Section: Intro > Dense Retrieval" in text
    assert "Type: lecture" in text
    assert "Difficulty: intermediate" in text
    assert "Topic: retrieval" in text
    assert "Chunk:\nDense retrieval compares semantic vectors." in text


def test_contextualized_chunks_reach_nodes(monkeypatch):
    docs = [
        Document(
            text="Semantic search retrieves by meaning.",
            metadata={
                "file_path": "data/course/module/lecture_01/lesson.md",
                "title": "Lecture 1",
                "section_path": "Overview",
                "doc_kind": "lecture",
                "difficulty": "beginner",
            },
        )
    ]

    monkeypatch.setattr("app.ingestion.DATA_DIR", Path("data"))
    enriched = _add_metadata(docs)
    contextualized = _apply_contextualized_chunks(enriched)
    nodes = _build_nodes(contextualized)

    contents = [node.get_content() for node in nodes]
    assert any("Document: Lecture 1" in text for text in contents)
    assert any("Section: Overview" in text for text in contents)
    assert any("Semantic search retrieves by meaning." in text for text in contents)
