"""Integration tests for pipeline runner (Iteration 12, расширение 19.2).

``run_pipeline`` — только classify → condense → rewrite (синхронно). Он не
генерирует ответ и не парсит quiz / Socratic: это делается в ``query_service``
после retrieval (см. ``tests/test_query_service.py``, ``tests/test_condense_step.py``).

Покрытие здесь: ``pipeline_steps``, приоритет ``effective_query``, окно condense
для tutor, feature flags condense/rewrite, сохранение ``QueryOptions``.
"""

from unittest.mock import MagicMock

import app.condense_step as condense_mod
import app.pipeline_runner as runner
import app.pipeline_steps as steps
from app.config import RetrievalSettings
from app.metrics import PIPELINE_TRACE_SCHEMA_VERSION
from app.models import Message, PipelineOverrides, QueryContext, QueryExecutionPlan, QueryOptions


# ---------------------------------------------------------------------------
# run_pipeline — full pass with defaults (ENABLE_REWRITE=False, ENABLE_CLASSIFIER=False)
# ---------------------------------------------------------------------------

def test_run_pipeline_defaults_qa(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings())

    ctx = runner.run_pipeline("What is RAG?")

    assert ctx.query_type == "qa"
    assert ctx.classify_method == "heuristic"
    assert ctx.rewritten_query is None
    assert ctx.effective_query == "What is RAG?"
    assert ctx.retrieval_strategy == "default"
    assert ctx.prompt_key == "qa"


def test_run_pipeline_defaults_keyword(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings())

    ctx = runner.run_pipeline("RFC-2024-003")

    assert ctx.query_type == "keyword"
    assert ctx.classify_method == "heuristic"
    assert ctx.retrieval_strategy == "bm25_only"
    assert ctx.prompt_key == "keyword"


def test_resolve_strategy_overview_prefers_doc_then_chunk(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings(enable_classifier=True))

    class _FakeResponse:
        text = '{"type": "overview", "confidence": 0.9}'

    monkeypatch.setattr(
        "app.provider.get_classifier_llm",
        lambda: type("LLM", (), {"complete": staticmethod(lambda prompt: _FakeResponse())})(),
    )

    ctx = runner.run_pipeline("Дай обзор по RAG и retrieval")

    assert ctx.query_type == "overview"
    assert ctx.retrieval_strategy == "doc_then_chunk"


def test_run_pipeline_passes_options(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings())

    options = QueryOptions(folder="lectures")
    ctx = runner.run_pipeline("What is security?", options)

    assert ctx.query_options.folder == "lectures"


# ---------------------------------------------------------------------------
# run_pipeline — graceful degradation
# ---------------------------------------------------------------------------

def test_run_pipeline_classify_failure_falls_back_to_qa(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings())

    def broken_classify(ctx):
        raise RuntimeError("LLM down")

    monkeypatch.setattr(runner, "classify_step", broken_classify)

    ctx = runner.run_pipeline("test question")

    assert ctx.query_type == "qa"
    assert ctx.classify_method == "fallback"
    assert "broken_classify_error" in ctx.trace or "classify_step_error" in ctx.trace


def test_run_pipeline_rewrite_failure_passthrough(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings(enable_rewrite=True))

    def broken_rewrite(ctx):
        raise RuntimeError("LLM timeout")

    monkeypatch.setattr(runner, "rewrite_step", broken_rewrite)

    ctx = runner.run_pipeline("What is RAG?")

    assert ctx.rewritten_query is None
    assert ctx.effective_query == "What is RAG?"


# ---------------------------------------------------------------------------
# resolve_retrieval_strategy — config priority
# ---------------------------------------------------------------------------

def test_resolve_strategy_api_override_highest():
    """API override > QueryContext > config defaults."""
    ctx = QueryContext(original_question="test", retrieval_strategy="bm25_only")
    overrides = PipelineOverrides(retrieval_mode="hybrid")
    settings = RetrievalSettings(retrieval_mode="vector_only")

    result = runner.resolve_retrieval_strategy(ctx, overrides, settings)
    assert result == "hybrid"


def test_resolve_strategy_query_context_over_config():
    """QueryContext > config defaults when no override."""
    ctx = QueryContext(original_question="test", retrieval_strategy="bm25_only")
    settings = RetrievalSettings(retrieval_mode="vector_only")

    result = runner.resolve_retrieval_strategy(ctx, overrides=None, settings=settings)
    assert result == "bm25_only"


def test_resolve_strategy_config_default_when_context_is_default():
    """Config defaults used when QueryContext strategy is 'default'."""
    ctx = QueryContext(original_question="test", retrieval_strategy="default")
    settings = RetrievalSettings(retrieval_mode="hybrid")

    result = runner.resolve_retrieval_strategy(ctx, overrides=None, settings=settings)
    assert result == "hybrid"


def test_resolve_strategy_override_none_means_skip():
    """Override with retrieval_mode=None doesn't override."""
    ctx = QueryContext(original_question="test", retrieval_strategy="bm25_only")
    overrides = PipelineOverrides(retrieval_mode=None)
    settings = RetrievalSettings(retrieval_mode="vector_only")

    result = runner.resolve_retrieval_strategy(ctx, overrides, settings)
    assert result == "bm25_only"


def test_resolve_strategy_all_defaults():
    ctx = QueryContext(original_question="test")
    settings = RetrievalSettings(retrieval_mode="vector_only")

    result = runner.resolve_retrieval_strategy(ctx, overrides=None, settings=settings)
    assert result == "vector_only"


# ---------------------------------------------------------------------------
# Regression: qa type backward compatibility
# ---------------------------------------------------------------------------

def test_run_pipeline_qa_prompt_key_matches_current(monkeypatch):
    """qa type should use 'qa' prompt_key, matching current QA_PROMPT behavior."""
    monkeypatch.setattr(steps, "get_settings", lambda: _settings())

    ctx = runner.run_pipeline("What is prompt injection?")

    assert ctx.query_type == "qa"
    assert ctx.prompt_key == "qa"

    from app.prompts import PROMPTS, QA_PROMPT
    assert PROMPTS["qa"] is QA_PROMPT


def test_run_pipeline_keyword_prompt_key_matches_current(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings())

    ctx = runner.run_pipeline("OWASP")

    assert ctx.query_type == "keyword"
    assert ctx.prompt_key == "keyword"

    from app.prompts import PROMPTS, KEYWORD_PROMPT
    assert PROMPTS["keyword"] is KEYWORD_PROMPT


# ---------------------------------------------------------------------------
# Pipeline trace populated
# ---------------------------------------------------------------------------

def test_run_pipeline_trace_populated(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings())

    ctx = runner.run_pipeline("What is RAG?")

    assert "classify_step_ms" in ctx.trace
    assert "rewrite_step_ms" in ctx.trace
    assert ctx.trace.get("rewrite_enabled") is False
    assert ctx.trace.get("schema_version") == PIPELINE_TRACE_SCHEMA_VERSION
    assert ctx.pipeline_steps == ["classify"]


def test_run_pipeline_pipeline_steps_includes_rewrite_when_enabled(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings(enable_rewrite=True))

    class _FakeResponse:
        text = "optimized query for search"

    monkeypatch.setattr(
        "app.provider.get_rewrite_llm",
        lambda: type("LLM", (), {"complete": staticmethod(lambda prompt: _FakeResponse())})(),
    )

    ctx = runner.run_pipeline("What is RAG?")

    assert ctx.trace.get("rewrite_enabled") is True
    assert ctx.pipeline_steps == ["classify", "rewrite"]


# ---------------------------------------------------------------------------
# Iteration 19.2: condense + rewrite, tutor window, options, flags
# ---------------------------------------------------------------------------


def _history(n: int = 10) -> list[Message]:
    return [
        Message(role="user" if i % 2 == 0 else "assistant", content=f"msg-{i}")
        for i in range(n)
    ]


def _patch_session_and_settings(monkeypatch, **settings_kwargs):
    """Единые настройки для steps и condense_step + подставная история сессии."""
    fake = _settings(**settings_kwargs)

    monkeypatch.setattr(steps, "get_settings", lambda: fake)
    monkeypatch.setattr(condense_mod, "get_settings", lambda: fake)
    monkeypatch.setattr(runner.session_store, "get", lambda _sid: _history(10))


def test_run_pipeline_condense_does_not_overwrite_rewritten_query(monkeypatch):
    """condense пишет ``condensed_question``; rewrite — ``rewritten_query`` (разные поля)."""
    _patch_session_and_settings(monkeypatch, enable_rewrite=True, enable_condense=True)

    class _Condensed:
        text = "This is a condensed summary of the dialog with enough length."

    monkeypatch.setattr(
        "app.condense_step.get_llm",
        lambda: MagicMock(complete=lambda prompt, **kw: _Condensed()),
    )

    class _Rewritten:
        text = "optimized search query distinct from condensed"

    monkeypatch.setattr(
        "app.provider.get_rewrite_llm",
        lambda: MagicMock(complete=lambda prompt, **kw: _Rewritten()),
    )

    ctx = runner.run_pipeline(
        "What is RAG?",
        QueryOptions(session_id="sess-condense-rewrite"),
    )

    assert ctx.condensed_question == _Condensed.text
    assert ctx.rewritten_query == _Rewritten.text
    assert ctx.condensed_question != ctx.rewritten_query
    assert ctx.trace["effective_query"] == _Condensed.text
    assert ctx.trace["effective_query_source"] == "condensed"
    assert ctx.pipeline_steps == ["classify", "condense", "rewrite"]


def test_run_pipeline_effective_query_prefers_condensed_over_rewritten(monkeypatch):
    """Свойство ``effective_query``: condensed_question > rewritten_query > original."""
    _patch_session_and_settings(monkeypatch, enable_rewrite=True, enable_condense=True)

    class _Condensed:
        text = "This is a condensed summary of the dialog with enough length."

    monkeypatch.setattr(
        "app.condense_step.get_llm",
        lambda: MagicMock(complete=lambda prompt, **kw: _Condensed()),
    )

    class _Rewritten:
        text = "different rewrite text"

    monkeypatch.setattr(
        "app.provider.get_rewrite_llm",
        lambda: MagicMock(complete=lambda prompt, **kw: _Rewritten()),
    )

    ctx = runner.run_pipeline("original?", QueryOptions(session_id="s-eff"))
    assert ctx.effective_query == ctx.condensed_question
    assert ctx.effective_query != ctx.rewritten_query


def test_run_pipeline_tutor_uses_condense_history_window_16(monkeypatch):
    """В tutor mode condense_step задаёт окно 16 (см. ``ctx.trace``)."""
    _patch_session_and_settings(monkeypatch, enable_condense=True, enable_rewrite=False)

    class _Condensed:
        text = "This is a condensed summary of the dialog with enough length."

    monkeypatch.setattr(
        "app.condense_step.get_llm",
        lambda: MagicMock(complete=lambda prompt, **kw: _Condensed()),
    )

    ctx = runner.run_pipeline(
        "Explain reranking",
        QueryOptions(session_id="tutor-win", query_mode="tutor"),
    )
    assert ctx.trace.get("condense_history_window") == 16
    assert "condense" in ctx.pipeline_steps


def test_run_pipeline_preserves_homework_and_tutor_query_options(monkeypatch):
    """QueryOptions (homework в tutor-сессии) проходят в контекст без потерь."""
    _patch_session_and_settings(monkeypatch, enable_condense=False)

    opts = QueryOptions(
        session_id="hw1",
        query_mode="tutor",
        homework_mode=True,
        assistance_level="hint",
    )
    ctx = runner.run_pipeline("Подсказка по задаче", opts)

    assert ctx.query_options.query_mode == "tutor"
    assert ctx.query_options.homework_mode is True
    assert ctx.query_options.assistance_level == "hint"


def test_run_pipeline_condense_disabled_skips_condense_step(monkeypatch):
    """При ``enable_condense=False`` шаг condense всё же вызывается, но без LLM."""
    fake = _settings(enable_condense=False, enable_rewrite=False)
    monkeypatch.setattr(steps, "get_settings", lambda: fake)
    monkeypatch.setattr(condense_mod, "get_settings", lambda: fake)
    monkeypatch.setattr(runner.session_store, "get", lambda _sid: _history(10))

    ctx = runner.run_pipeline("test", QueryOptions(session_id="s1"))
    assert ctx.trace.get("condense") == "skipped_disabled"
    assert ctx.condensed_question is None
    # runner считает «condense» выполненным, если не skipped_no_session / too_short
    assert "condense" in ctx.pipeline_steps


def test_run_pipeline_long_history_tutor_still_condenses(monkeypatch):
    """20 сообщений в истории: condense берёт последние ``condense_history_window_tutor``."""
    _patch_session_and_settings(monkeypatch, enable_condense=True, enable_rewrite=False)

    class _Condensed:
        text = "This is a condensed summary of the dialog with enough length."

    monkeypatch.setattr(
        "app.condense_step.get_llm",
        lambda: MagicMock(complete=lambda prompt, **kw: _Condensed()),
    )

    monkeypatch.setattr(runner.session_store, "get", lambda _sid: _history(20))

    ctx = runner.run_pipeline(
        "Next?",
        QueryOptions(session_id="long", query_mode="tutor"),
    )
    assert ctx.trace.get("condense") == "success"
    assert ctx.condensed_question is not None


def test_update_pipeline_post_retrieval_trace_adds_full_stage_sequence():
    ctx = QueryContext(original_question="What is RAG?")
    ctx.trace["rewrite_enabled"] = True
    plan = QueryExecutionPlan(
        query_type="qa",
        prompt_key="qa",
        retrieval_mode="vector_only",
        enable_reranker=False,
        similarity_top_k=4,
        rerank_top_n=4,
        rerank_model="test-reranker",
        split_strategy="sentence_window",
        window_size=2,
        profile="fast",
        homework_mode=False,
        assistance_level=None,
        query_engine_cache_policy="shared",
        faq_cache_eligible=True,
        faq_cache_skip_reason=None,
        doc_top_k=None,
    )

    ctx = runner.update_pipeline_post_retrieval_trace(
        ctx,
        plan,
        cache_hit=False,
        source_count=2,
        generation_model="gpt-5-mini",
        answer_length=120,
    )

    assert ctx.trace["retrieve_stage"]["retrieval_mode"] == "vector_only"
    assert ctx.trace["rerank_stage"]["enabled"] is False
    assert ctx.trace["generate_stage"]["model"] == "gpt-5-mini"
    assert ctx.trace["pipeline_stages"] == [
        "classify",
        "condense",
        "rewrite",
        "retrieve",
        "rerank_skipped",
        "generate",
    ]
    assert ctx.pipeline_steps == ctx.trace["pipeline_stages"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeSettings:
    def __init__(self, **kwargs):
        self.enable_classifier = kwargs.get("enable_classifier", False)
        self.enable_rewrite = kwargs.get("enable_rewrite", False)
        self.enable_self_correction = False
        self.enable_condense = kwargs.get("enable_condense", True)
        self.condense_history_window = kwargs.get("condense_history_window", 8)
        self.condense_history_window_tutor = kwargs.get("condense_history_window_tutor", 16)
        self.llm_model = "gpt-5-mini"
        self.rewrite_model = None
        self.classifier_model = None


def _settings(**kwargs):
    return _FakeSettings(**kwargs)
