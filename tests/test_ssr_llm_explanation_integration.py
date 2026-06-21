"""Интеграция: _generate_llm_explanation → JSONL-профиль (без мока записи)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import app.config as config
from app.smart_study_router import build_smart_study_recommendation
from app.ui.adaptive_plan_llm_enrichment import _SSR_LLM_EXPLANATION_CACHE, _generate_llm_explanation


@pytest.fixture
def ssr_profile_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SSR_LLM_PROFILE_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("ENABLE_SSR_LLM_PROFILING", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-integration")
    monkeypatch.setenv("LLM_MODEL", "gpt-integration-dummy")
    config.reset_settings_cache()
    _SSR_LLM_EXPLANATION_CACHE.clear()
    yield tmp_path
    _SSR_LLM_EXPLANATION_CACHE.clear()
    config.reset_settings_cache()


def _last_jsonl_row(log_dir: Path) -> dict[str, Any]:
    files = sorted(log_dir.glob("ssr_llm_profile_*.jsonl"))
    assert len(files) == 1, files
    lines = [ln for ln in files[0].read_text(encoding="utf-8").splitlines() if ln.strip()]
    return json.loads(lines[-1])


def test_generate_llm_explanation_integration_writes_llm_success_profile(ssr_profile_env: Path) -> None:
    class _Msg:
        content = "Короткое персональное объяснение для проверки профиля."

    class OkResp:
        message = _Msg()

    class OkLlm:
        model = "fake-ssr-model"

        def chat(self, messages: list, **kwargs: Any) -> OkResp:
            all_text = " ".join(m.content for m in messages)
            assert "Почему сейчас" in all_text or "почему" in all_text.lower()
            return OkResp()

    rec = build_smart_study_recommendation(surface="home", flashcard_due_n=1)
    ctx = {
        "last_session_topic": "тема",
        "last_session_date": "вчера",
        "quiz_score_last_3": "нет данных",
        "cards_due_count": 1,
        "sm2_due_count": 0,
        "weak_concepts_list": "тест",
        "local_evidence": "нет",
    }
    text = _generate_llm_explanation(rec, ctx, llm=OkLlm())
    assert "персональн" in text.lower() or "объяснен" in text.lower()

    row = _last_jsonl_row(ssr_profile_env)
    assert row["outcome"] == "llm_success"
    assert row["kind"] == "ssr_llm_explanation"
    assert row["event_id"] and len(row["event_id"]) >= 32
    assert row["effective_model"] == "fake-ssr-model"
    assert row["main_llm_model"] == "gpt-integration-dummy"
    assert row["latency_ms"] is not None
    assert float(row["latency_ms"]) >= 0


def test_generate_llm_explanation_integration_writes_fallback_empty_profile(ssr_profile_env: Path) -> None:
    class _EmptyMsg:
        content = ""

    class EmptyResp:
        message = _EmptyMsg()

    class EmptyLlm:
        model = "fake-empty"

        def chat(self, messages: list, **kwargs: Any) -> EmptyResp:
            return EmptyResp()

    rec = build_smart_study_recommendation(surface="home", flashcard_due_n=1)
    ctx = {
        "last_session_topic": "тема",
        "last_session_date": "вчера",
        "quiz_score_last_3": "нет данных",
        "cards_due_count": 1,
        "sm2_due_count": 0,
        "weak_concepts_list": "тест",
        "local_evidence": "нет",
    }
    out = _generate_llm_explanation(rec, ctx, llm=EmptyLlm())
    assert out == rec.why_now_ru

    row = _last_jsonl_row(ssr_profile_env)
    assert row["outcome"] == "template_fallback_empty"
    assert row["effective_model"] == "fake-empty"


def test_generate_llm_explanation_integration_cache_hit_writes_profile(ssr_profile_env: Path) -> None:
    """Второй вызов с тем же контекстом пишет outcome=cache_hit без повторного chat()."""

    class _Msg:
        content = "Кэшируемое объяснение для интеграции."

    class OkResp:
        message = _Msg()

    class OkLlm:
        model = "fake-cache-model"

        def chat(self, messages: list, **kwargs: Any) -> OkResp:
            return OkResp()

    class ExplodingLlm:
        model = "must-not-call"

        def chat(self, messages: list, **kwargs: Any) -> OkResp:
            raise AssertionError("LLM.chat не должен вызываться при cache_hit")

    rec = build_smart_study_recommendation(surface="home", flashcard_due_n=1)
    ctx = {
        "last_session_topic": "тема",
        "last_session_date": "вчера",
        "quiz_score_last_3": "нет данных",
        "cards_due_count": 1,
        "sm2_due_count": 0,
        "weak_concepts_list": "тест",
        "local_evidence": "нет",
    }
    t0 = 10_000.0
    t1 = 10_005.0
    out1 = _generate_llm_explanation(rec, ctx, llm=OkLlm(), now_monotonic=t0)
    out2 = _generate_llm_explanation(rec, ctx, llm=ExplodingLlm(), now_monotonic=t1)
    assert out1 == out2
    assert "кэшируем" in out1.lower()

    files = sorted(ssr_profile_env.glob("ssr_llm_profile_*.jsonl"))
    assert len(files) == 1
    lines = [ln for ln in files[0].read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    row0 = json.loads(lines[0])
    row1 = json.loads(lines[1])
    assert row0["outcome"] == "llm_success"
    assert row1["outcome"] == "cache_hit"
    assert row1["event_id"] and row1["event_id"] != row0["event_id"]
    assert row1["latency_ms"] == 0.0
