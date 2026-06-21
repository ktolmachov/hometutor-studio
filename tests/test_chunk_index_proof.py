"""US-2.3 chunk/index proof: лёгкий non-text (PDF с native text) → чанки в общем индексе.

Граница: полный OCR/Docling и расширенные форматы — в ``tests/test_ocr_docling_phase1.py``
и последующих пакетах; здесь фиксируем контракт «searchable chunks + трассируемый источник»
без внешних API эмбеддингов.
"""

from __future__ import annotations

from pathlib import Path

from llama_index.core import Document
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

import app.ingestion as ing
from app import ingestion_loader


class _FixedDimEmbedding(BaseEmbedding):
    """Фиксированная размерность, без сети — для записи в Chroma в unit-тесте."""

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._get_query_embedding(query)

    def _get_query_embedding(self, query: str) -> list[float]:
        return [0.05] * 8

    def _get_text_embedding(self, text: str) -> list[float]:
        return [0.07] * 8


def _stub_pdf(tmp_path: Path) -> Path:
    pdf = tmp_path / "lecture.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    return pdf


def test_native_pdf_yields_chunk_nodes_with_traceable_metadata(monkeypatch, settings_env, tmp_path):
    settings_env({"INGEST_DOCLING_ENABLED": "true", "INGEST_DOCLING_MIN_NATIVE_TEXT_CHARS": "10"})
    pdf = _stub_pdf(tmp_path)
    anchor = "chunk_index_proof_anchor_token "

    class FakeReader:
        def __init__(self, **kwargs: object) -> None:
            pass

        def load_data(self) -> list[Document]:
            rel = str(pdf.resolve()).replace("\\", "/")
            return [Document(text=anchor * 6, metadata={"file_path": rel})]

    monkeypatch.setattr(ing, "SimpleDirectoryReader", FakeReader)
    docs = ing._load_one_file(pdf)
    assert len(docs) == 1
    assert docs[0].metadata.get("source_extraction") == "native_text"

    enriched = ing._add_metadata(docs)
    assert enriched[0].metadata.get("doc_id"), "doc_id needed for retrieval/source trace"

    nodes = ingestion_loader._build_nodes(enriched)
    assert nodes
    blob = " ".join(n.get_content() for n in nodes)
    assert "chunk_index_proof_anchor_token" in blob


def test_embed_pipeline_persists_pdf_chunks_to_chroma(monkeypatch, settings_env, tmp_path):
    import chromadb

    settings_env({"INGEST_DOCLING_ENABLED": "true", "INGEST_DOCLING_MIN_NATIVE_TEXT_CHARS": "10"})
    monkeypatch.setattr(ing, "INGEST_CACHE_PATH", tmp_path / "ingest_embed_cache.json")

    pdf = _stub_pdf(tmp_path)
    anchor = "chunk_index_proof_anchor_token "

    class FakeReader:
        def __init__(self, **kwargs: object) -> None:
            pass

        def load_data(self) -> list[Document]:
            rel = str(pdf.resolve()).replace("\\", "/")
            return [Document(text=anchor * 6, metadata={"file_path": rel})]

    monkeypatch.setattr(ing, "SimpleDirectoryReader", FakeReader)

    docs = ing._add_metadata(ing._load_one_file(pdf))
    nodes = ingestion_loader._build_nodes(docs)

    chroma_dir = tmp_path / "chroma"
    chroma_dir.mkdir(parents=True)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    collection = client.get_or_create_collection("chunk_index_proof")
    vector_store = ChromaVectorStore(chroma_collection=collection)

    ingestion_loader._embed_and_store(nodes, _FixedDimEmbedding(), vector_store, show_progress=False)

    assert collection.count() > 0
    payload = collection.get(include=["metadatas", "documents"])
    doc_texts = " ".join(payload.get("documents") or [])
    assert "chunk_index_proof_anchor_token" in doc_texts

    metas = payload.get("metadatas") or []
    assert any(_meta_traceable(m) for m in metas), (
        "ожидались метаданные с doc_id или native_text для связки ответа с источником"
    )


def _meta_traceable(meta: object) -> bool:
    if not isinstance(meta, dict):
        return False
    doc_id = meta.get("doc_id")
    extraction = meta.get("source_extraction")
    return bool(doc_id) or extraction == "native_text"
