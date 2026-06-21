"""Интеграционные тесты: реальный mini-index + retrieval + QA (US-12.3)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from openai import PermissionDeniedError, RateLimitError

from tests.integration_paths import apply_integration_fs_layout

pytestmark = pytest.mark.integration

KB_SRC = Path(__file__).resolve().parents[1] / "eval_data" / "quality_benchmark_kb"


@pytest.fixture(scope="session")
def rag_mini_index_session(tmp_path_factory: pytest.TempPathFactory):
    if not (os.getenv("OPENAI_API_KEY") or "").strip():
        pytest.fail(
            "OPENAI_API_KEY обязателен для integration: mini-index + embed/LLM",
            pytrace=False,
        )

    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    root = tmp_path_factory.mktemp("rag_integration")
    data_dir, chroma_dir = apply_integration_fs_layout(mp, root)
    shutil.copytree(KB_SRC, data_dir, dirs_exist_ok=True)

    # Очистка кэшей после применения monkeypatch, чтобы настройки вступили в силу
    from app.config import reset_settings_cache
    reset_settings_cache()

    # До дорогого build_index: проверяем и chat, и embeddings.
    # Иначе при недоступных эмбеддингах падение произойдёт внутри VectorStoreIndex.
    from llama_index.core.base.llms.types import ChatMessage, MessageRole
    from llama_index.core.base.embeddings.base import BaseEmbedding

    from app.provider import get_embed_model
    from app.provider import get_healthcheck_llm

    try:
        get_healthcheck_llm(timeout_sec=25.0).chat(
            [ChatMessage(role=MessageRole.USER, content="ping")]
        )
    except (PermissionDeniedError, RateLimitError) as exc:
        mp.undo()
        pytest.skip(f"LLM API: квота или rate limit — integration пропущен: {exc}")
    except RuntimeError as exc:
        mp.undo()
        pytest.fail(
            f"LLM chat недоступен (проверьте ключ, модель, billing): {exc}",
            pytrace=False,
        )

    try:
        embed_model: BaseEmbedding = get_embed_model()
        embed_model.get_text_embedding("ping")
    except (PermissionDeniedError, RateLimitError) as exc:
        mp.undo()
        pytest.skip(f"Embeddings API: квота или rate limit — integration пропущен: {exc}")
    except Exception as exc:  # noqa: BLE001 — провайдер эмбеддингов может кидать разные ошибки.
        mp.undo()
        pytest.fail(
            f"Embeddings недоступны (проверьте EMBED_MODEL/провайдера/billing): {exc}",
            pytrace=False,
        )

    from app.index_diff import update_snapshot_after_index
    from app.ingestion import build_index
    from app.retrieval_cache import clear_retrieval_cache

    clear_retrieval_cache()
    build_index(reset=True)
    update_snapshot_after_index()
    clear_retrieval_cache()

    try:
        yield {"root": root, "data_dir": data_dir, "chroma_dir": chroma_dir}
    finally:
        mp.undo()


def test_index_not_empty(rag_mini_index_session):
    from app.retrieval_cache import get_base_services

    col = get_base_services()["collection"]
    assert col.count() > 0


def test_answer_returns_sources_and_nonempty_answer(rag_mini_index_session):
    from app.models import QueryOptions
    from app.query_service import answer_question

    r = answer_question("Что такое RAG пайплайн?", QueryOptions())
    assert isinstance(r.get("answer"), str) and r["answer"].strip()
    assert isinstance(r.get("sources"), list) and r["sources"]


def test_source_hit_alpha_anchor(rag_mini_index_session):
    from app.models import QueryOptions
    from app.query_service import answer_question

    r = answer_question("Где упоминается RAG_ALPHA_UNIQUE_7741?", QueryOptions())
    blob = " ".join(
        f'{s.get("file_name","")} {s.get("relative_path","")}'.lower() for s in (r.get("sources") or [])
    )
    assert "alpha_rag_intro" in blob


def test_file_filter_limits_to_beta(rag_mini_index_session):
    from app.models import QueryOptions
    from app.query_service import answer_question

    r = answer_question(
        "Расскажи про Chroma",
        QueryOptions(file_name="beta_vector_db.md"),
    )
    for s in r.get("sources") or []:
        name = f'{s.get("file_name") or ""} {s.get("relative_path") or ""}'.lower()
        assert "beta_vector" in name


def test_retrieval_debug_trace_present(rag_mini_index_session):
    from app.models import QueryOptions
    from app.query_service import answer_question

    r = answer_question("Что такое SM-2 интервалы?", QueryOptions())
    dbg = r.get("debug") or {}
    rt = dbg.get("retrieval_trace") or {}
    assert rt.get("schema_version") is not None
    assert rt.get("returned_source_count", 0) >= 1


def test_hybrid_topic_retrieves_gamma(rag_mini_index_session):
    from app.models import QueryOptions
    from app.query_service import answer_question

    r = answer_question("Reciprocal Rank Fusion в гибридном поиске", QueryOptions())
    blob = " ".join(
        f'{s.get("file_name","")} {s.get("relative_path","")}'.lower() for s in (r.get("sources") or [])
    )
    assert "gamma_hybrid" in blob


def test_guardrails_epsilon_in_sources(rag_mini_index_session):
    from app.models import QueryOptions
    from app.query_service import answer_question

    r = answer_question("GUARD_EPSILON_UNIQUE_9917 политики вывода", QueryOptions())
    blob = " ".join(
        f'{s.get("file_name","")} {s.get("relative_path","")}'.lower() for s in (r.get("sources") or [])
    )
    assert "epsilon_guardrails" in blob
