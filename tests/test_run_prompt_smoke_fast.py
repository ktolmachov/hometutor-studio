"""CLI flags for scripts/run_prompt_smoke.py (--smoke-fast)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


@pytest.fixture
def smoke_mod():
    import run_prompt_smoke as mod

    return importlib.reload(mod)


def test_apply_smoke_fast_env_overrides_settings(smoke_mod, monkeypatch):
    monkeypatch.delenv("RAG_PROFILE", raising=False)
    monkeypatch.delenv("RETRIEVAL_MODE", raising=False)
    monkeypatch.delenv("ENABLE_RERANKER", raising=False)
    monkeypatch.delenv("SIMILARITY_TOP_K", raising=False)
    monkeypatch.setenv("TUTOR_INLINE_QUIZ_SEPARATE_LLM_CALL", "true")
    monkeypatch.setenv("ENABLE_TUTOR_AUTO_QUIZ_LOOP", "true")

    from app.config import get_retrieval_settings, get_settings, reset_settings_cache

    reset_settings_cache()
    assert get_settings().tutor_inline_quiz_separate_llm_call is True
    assert get_settings().enable_tutor_auto_quiz_loop is True

    smoke_mod.apply_smoke_fast_env()

    s = get_settings()
    r = get_retrieval_settings()
    assert r.rag_profile == "quality"
    assert r.retrieval_mode == "hybrid"
    assert r.enable_reranker is False
    assert r.similarity_top_k == 4
    assert s.tutor_inline_quiz_separate_llm_call is False
    assert s.enable_tutor_auto_quiz_loop is False


def test_build_options_sets_rag_profile_when_smoke_fast(smoke_mod):
    opts = smoke_mod._build_options({"id": "x", "query_mode": "tutor"}, smoke_fast=True)
    assert opts.rag_profile == "quality"
    opts_default = smoke_mod._build_options({"id": "y", "query_mode": "qa"}, smoke_fast=False)
    assert opts_default.rag_profile is None
