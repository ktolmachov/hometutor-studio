from pathlib import Path

import pytest

from app import faq_memory


class _FakeEmbedModel:
    def get_text_embedding(self, text: str):
        return [1.0, 0.0]


@pytest.fixture
def faq_env(tmp_path, monkeypatch):
    """Отдельный chroma_db и jsonl на тест — без пересечения состояния."""
    faq_memory.reset_faq_embed_circuit_for_tests()
    chroma = tmp_path / "chroma_db"
    chroma.mkdir(parents=True)
    monkeypatch.setattr(faq_memory, "CHROMA_DIR", chroma)
    faq_memory.FAQ_MEMORY_PATH = tmp_path / "faq_test.jsonl"
    monkeypatch.setattr(faq_memory, "_get_embed_model", lambda: _FakeEmbedModel())
    monkeypatch.setattr(faq_memory, "_loopback_tcp_reachable", lambda *_a, **_k: True)


def test_save_and_find_similar(faq_env):
    faq_memory.save_interaction("Как настроить индекс?", "Нужно запустить ingest.py", [])

    results = faq_memory.find_similar_questions(
        "Как настроить индекс?",
        top_k=5,
        min_score=0.1,
    )

    assert len(results) == 1
    assert results[0]["question"] == "Как настроить индекс?"
    assert "answer" in results[0]
    assert results[0]["score"] >= 0.1


def test_find_similar_on_empty_file(faq_env):
    faq_memory.FAQ_MEMORY_PATH.write_text("", encoding="utf-8")

    results = faq_memory.find_similar_questions("Любой вопрос")

    assert results == []


def test_dedup_skips_second_save(faq_env):
    faq_memory.save_interaction("Same?", "A1", [])
    faq_memory.save_interaction("Same?", "A2", [])

    results = faq_memory.find_similar_questions("Same?", top_k=5, min_score=0.1)
    assert len(results) == 1
    assert results[0]["answer"] == "A1"


def test_migrate_jsonl_to_chroma(faq_env, tmp_path):
    import json

    legacy = tmp_path / "legacy.jsonl"
    legacy.write_text(
        json.dumps(
            {
                "question": "Q?",
                "answer": "A!",
                "sources": [],
                "embedding": [1.0, 0.0],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    faq_memory.FAQ_MEMORY_PATH = legacy

    out = faq_memory.find_similar_questions("Q?", top_k=3, min_score=0.1)
    assert len(out) == 1
    assert out[0]["answer"] == "A!"
    assert legacy.read_text(encoding="utf-8").strip() == ""


def test_clear_faq_memory_file(faq_env):
    faq_memory.save_interaction("X", "Y", [])
    assert faq_memory.find_similar_questions("X", min_score=0.1)

    faq_memory.clear_faq_memory_file()

    assert faq_memory.find_similar_questions("X", min_score=0.1) == []
    assert faq_memory.FAQ_MEMORY_PATH.read_text(encoding="utf-8") == ""
