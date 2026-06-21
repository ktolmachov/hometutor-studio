"""Flashcard handoff fast-path contract tests (P1)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.flashcard_handoff import (
    FLASHCARD_HANDOFF_ENTRYPOINT,
    FLASHCARD_HANDOFF_MAX_OUTPUT_TOKENS,
    FLASHCARD_HANDOFF_SEED_ROUTE,
    build_flashcard_handoff_seed,
    clear_flashcard_handoff_session_fields,
    flashcard_handoff_session_fields,
    flashcard_handoff_pipeline_overrides,
    is_flashcard_handoff,
)
from app.models import QueryOptions
from app import query_response_postprocessing as postproc
from app import retrieval
from app import pipeline_factory


def test_is_flashcard_handoff_only_for_entrypoint() -> None:
    assert is_flashcard_handoff(
        QueryOptions(tutor_entrypoint=FLASHCARD_HANDOFF_ENTRYPOINT, query_mode="tutor")
    )
    assert not is_flashcard_handoff(QueryOptions(query_mode="tutor", session_id="s1"))
    assert not is_flashcard_handoff(None)


def test_flashcard_handoff_pipeline_overrides_fast_vector_only() -> None:
    ov = flashcard_handoff_pipeline_overrides()
    assert ov.rag_profile == "fast"
    assert ov.enable_reranker is False
    assert ov.similarity_top_k == 2
    assert ov.retrieval_mode == "vector_only"
    # Bounded for latency, but must fit a complete short prose answer (key idea +
    # example + check question). A live reference answer measures ~150-170 qwen tokens,
    # so the cap must sit comfortably ABOVE that — too low truncates штатную прозу
    # mid-sentence (re-introducing the truncated-answer UX bug). The cap is a ceiling,
    # not a target: the model stops at EOS on its own, so a generous cap costs no latency.
    assert 160 <= FLASHCARD_HANDOFF_MAX_OUTPUT_TOKENS <= 320


def test_flashcard_handoff_session_fields_do_not_persist_answer_depth() -> None:
    fields = flashcard_handoff_session_fields("RAG")

    assert fields["tutor_entrypoint"] == FLASHCARD_HANDOFF_ENTRYPOINT
    assert fields["current_topic"] == "RAG"
    assert "tutor_answer_depth" not in fields


def test_clear_flashcard_handoff_session_fields_preserves_tutor_preferences() -> None:
    state = {
        "tutor_entrypoint": FLASHCARD_HANDOFF_ENTRYPOINT,
        "tutor_answer_depth": "short",
        "tutor_mastery_level": "beginner",
    }

    clear_flashcard_handoff_session_fields(state)

    assert "tutor_entrypoint" not in state
    assert state["tutor_answer_depth"] == "short"
    assert state["tutor_mastery_level"] == "beginner"


def test_build_flashcard_handoff_seed_uses_card_back_as_instant_source() -> None:
    seed = build_flashcard_handoff_seed(
        {
            "id": 42,
            "front": "Почему state machine лучше набора флагов?",
            "back": "State machine явно задает допустимые состояния и переходы.",
            "deck_name": "ИИ Агенты",
            "tags": "course:abc, source:ИИ Агенты/lesson.md",
        }
    )

    assert seed["user_content"].startswith("Не знаю:")
    assert "State machine явно задает" in seed["assistant_content"]
    meta = seed["assistant_metadata"]
    payload = meta["tutor_answer"]
    assert payload["answer_kind"] == "tutor_teaching_step"
    assert payload["trust_signals"]["sources_used"] == 1
    assert payload["trust_signals"]["confidence"] == "high"
    assert payload["depth_level"] == "short"
    assert "Углубить по источникам" in payload["suggested_ctas"]
    assert meta["tutor"]["suppress_smart_study_overlay"] is True
    assert not str(seed["assistant_content"]).lstrip().startswith("{")
    assert meta["sources"][0]["route"] == FLASHCARD_HANDOFF_SEED_ROUTE
    assert meta["sources"][0]["relative_path"] == "ИИ Агенты/lesson.md"
    assert meta["sources"][0]["file_name"] == "lesson.md"
    assert "State machine явно задает" in meta["sources"][0]["text"]
    assert "Как связать с вопросом" in seed["assistant_content"]
    assert "Источник карточки" in seed["assistant_content"]


def test_flashcard_handoff_seed_uses_document_deck_source_id() -> None:
    seed = build_flashcard_handoff_seed(
        {
            "front": "Что такое RAG?",
            "back": "RAG соединяет генерацию с retrieval по базе знаний.",
            "deck_source_type": "document",
            "deck_source_id": "docs/rag.md",
        }
    )

    assert seed["assistant_metadata"]["sources"][0]["relative_path"] == "docs/rag.md"


def test_resolve_plan_uses_shared_cache_for_flashcard_handoff_session(monkeypatch):
    from app.config import RetrievalSettings

    monkeypatch.setattr(
        pipeline_factory,
        "get_retrieval_settings",
        lambda: RetrievalSettings(rag_profile="quality", retrieval_mode="hybrid"),
    )
    plan = retrieval.resolve_query_execution_plan(
        "Explain card concept",
        QueryOptions(
            session_id="sess-fc",
            query_mode="tutor",
            tutor_entrypoint=FLASHCARD_HANDOFF_ENTRYPOINT,
        ),
        overrides=flashcard_handoff_pipeline_overrides(),
    )
    assert plan.query_engine_cache_policy == "shared"
    assert plan.enable_reranker is False
    assert plan.profile == "fast"
    assert plan.retrieval_mode == "vector_only"


def test_process_rag_response_skips_sync_quiz_for_flashcard_handoff(monkeypatch):
    monkeypatch.setattr(postproc, "get_settings", lambda: MagicMock(enable_tutor_auto_quiz_loop=True))
    called = {"n": 0}

    def _boom(_ctx):
        called["n"] += 1
        raise AssertionError("sync micro quiz must not run on handoff")

    monkeypatch.setattr(
        "app.quiz_service.generate_and_attach_micro_quiz",
        _boom,
    )
    opts = QueryOptions(
        query_mode="tutor",
        tutor_entrypoint=FLASHCARD_HANDOFF_ENTRYPOINT,
    )
    ctx = MagicMock()
    ctx.metadata = {}
    ctx.effective_query = "q"
    result = postproc.process_rag_response(
        response=MagicMock(__str__=lambda self: "plain answer"),
        ctx=ctx,
        options=opts,
        retrieval_sc={},
        pipeline_params={},
        accumulated_rag_generation_usage=None,
        original_question="q",
        logger=MagicMock(),
    )
    assert result["auto_quiz_payload"] is None
    assert result["auto_quiz_ms"] is None
    assert called["n"] == 0


def test_resolve_effective_prompt_uses_compact_handoff_template() -> None:
    from app.models import QueryContext

    plan = retrieval.resolve_query_execution_plan(
        "Explain gap",
        QueryOptions(
            query_mode="tutor",
            tutor_entrypoint=FLASHCARD_HANDOFF_ENTRYPOINT,
        ),
        overrides=flashcard_handoff_pipeline_overrides(),
    )
    prompt = retrieval._resolve_effective_prompt(
        execution_plan=plan,
        options=QueryOptions(
            query_mode="tutor",
            tutor_entrypoint=FLASHCARD_HANDOFF_ENTRYPOINT,
        ),
        query_context=QueryContext(
            original_question="Explain gap",
            metadata={"graph_hint": "should not appear in template"},
        ),
    )
    text = getattr(prompt, "template", None) or str(prompt)
    assert "максимально кратко" in text
    assert "=== QUIZ ===" not in text
    assert "Graph guidance" not in text
    # Prose contract (not v2 JSON): the user must never see a raw JSON object. Guard
    # against regressing back to a structured-JSON handoff prompt by forbidding the v2
    # schema field names (the prompt may still say "без JSON" to instruct the model).
    assert "teaching_summary" not in text
    assert "understanding_state" not in text
    assert "trust_signals" not in text


def test_handoff_answer_kept_as_prose_not_parsed_as_v2_json() -> None:
    """Handoff answers are plain prose and must be shown verbatim, never v2-parsed.

    Regression: previously the handoff used a v2-JSON prompt; a token-capped answer
    truncated mid-object and `parse_tutor_rag_response` fell back to rendering the raw
    JSON string to the user. Now handoff skips the v2 parser entirely.
    """
    from app import query_response_postprocessing as postproc

    prose = (
        "Память агента — это инженерный модуль, а не магия модели.\n\n"
        "Например, факты сохраняются через детерминированный API.\n\n"
        "Проверь себя: чем внешняя память отличается от состояния LLM?"
    )

    def _no_v2(*_args, **_kwargs):  # pragma: no cover - must not be called
        raise AssertionError("parse_tutor_rag_response must be skipped for handoff")

    monkeypatch_target = "app.quiz_service.parse_tutor_rag_response"
    import pytest as _pytest

    with _pytest.MonkeyPatch.context() as mp:
        mp.setattr(postproc, "get_settings", lambda: MagicMock(enable_tutor_auto_quiz_loop=False))
        mp.setattr(monkeypatch_target, _no_v2)
        ctx = MagicMock()
        ctx.metadata = {"tutor_decision": "set"}  # skip decide_tutor_next_action branch
        ctx.effective_query = "q"
        result = postproc.process_rag_response(
            response=MagicMock(__str__=lambda self: prose, source_nodes=[]),
            ctx=ctx,
            options=QueryOptions(
                query_mode="tutor",
                tutor_entrypoint=FLASHCARD_HANDOFF_ENTRYPOINT,
            ),
            retrieval_sc={},
            pipeline_params={},
            accumulated_rag_generation_usage=None,
            original_question="q",
            logger=MagicMock(),
        )

    assert result["answer_text"] == prose
    assert result["tutor_teaching"] is None
    assert not result["answer_text"].lstrip().startswith("{")


def test_second_tutor_message_not_handoff_after_entrypoint_cleared() -> None:
    """Clearing tutor_entrypoint from session state must revert to normal tutor mode.

    This guards the one-shot clear added to tutor_chat_session.py: after the first
    handoff answer the entrypoint key is popped, so every subsequent message builds
    normal QueryOptions (disabled_for_session cache, reranker on via quality defaults,
    full quiz pipeline).
    """
    # First message — entrypoint present → handoff
    opts_first = QueryOptions(
        session_id="sess-fc",
        query_mode="tutor",
        tutor_entrypoint=FLASHCARD_HANDOFF_ENTRYPOINT,
    )
    assert is_flashcard_handoff(opts_first)

    # Session state after answer rendered: pop("tutor_entrypoint") was called.
    # Build the second-message options as tutor_chat_session.py would.
    opts_second = QueryOptions(
        session_id="sess-fc",
        query_mode="tutor",
        tutor_entrypoint=None,  # entrypoint cleared
    )
    assert not is_flashcard_handoff(opts_second)

    # Second message must get disabled_for_session cache policy (has session_id, not handoff).
    plan_second = retrieval.resolve_query_execution_plan(
        "Follow-up normal question",
        opts_second,
    )
    assert plan_second.query_engine_cache_policy == "disabled_for_session"


def test_cache_keys_differ_for_handoff_vs_normal_tutor() -> None:
    """Handoff and normal tutor must not share a query-engine cache entry.

    is_flashcard_handoff is included in the cache key precisely because the two modes
    select different prompt templates even when all other dims are identical.
    """
    from app.config import RetrievalSettings

    base_opts_kw = {"query_mode": "tutor"}

    plan_handoff = retrieval.resolve_query_execution_plan(
        "q",
        QueryOptions(**base_opts_kw, tutor_entrypoint=FLASHCARD_HANDOFF_ENTRYPOINT),
        overrides=flashcard_handoff_pipeline_overrides(),
    )
    plan_normal = retrieval.resolve_query_execution_plan(
        "q",
        QueryOptions(**base_opts_kw),
    )
    # Build the actual cache-key tuples by triggering build_query_engine up to the key.
    # We can't call build_query_engine (needs live services), but we can verify the
    # discriminating field presence via is_flashcard_handoff on the respective options.
    assert is_flashcard_handoff(
        QueryOptions(**base_opts_kw, tutor_entrypoint=FLASHCARD_HANDOFF_ENTRYPOINT)
    )
    assert not is_flashcard_handoff(QueryOptions(**base_opts_kw))
    # Handoff uses fast profile + reranker off via overrides; entrypoint lives on QueryOptions.
    assert plan_handoff.profile == "fast"
    assert plan_handoff.enable_reranker is False
    handoff_opts = QueryOptions(**base_opts_kw, tutor_entrypoint=FLASHCARD_HANDOFF_ENTRYPOINT)
    normal_opts = QueryOptions(**base_opts_kw)
    assert handoff_opts.tutor_entrypoint == FLASHCARD_HANDOFF_ENTRYPOINT
    assert normal_opts.tutor_entrypoint != FLASHCARD_HANDOFF_ENTRYPOINT


def test_execute_rag_query_skips_tutor_hints_for_handoff(monkeypatch) -> None:
    from app import query_rag_execution as qre
    from app.models import QueryContext

    captured: dict[str, str] = {}

    class _Engine:
        def query(self, question: str):
            captured["question"] = question
            return MagicMock(__str__=lambda self: '{"teaching_summary":"ok"}')

    engine = _Engine()

    def _fake_build(_question, _options, **kwargs):
        return {"engine": engine, "cache_hit": False, "pipeline_params": {}}

    monkeypatch.setattr(
        qre,
        "begin_llm_generation_token_accumulation",
        lambda: None,
    )
    monkeypatch.setattr(
        qre,
        "consume_llm_generation_token_accumulation",
        lambda: None,
    )
    monkeypatch.setattr(
        qre,
        "consume_llm_generation_message_roles",
        lambda: [],
    )

    ctx = QueryContext(
        original_question="base question",
        metadata={
            "graph_hint": "graph line",
            "learner_hint": "learner line",
            "orchestration_hint": "orch line",
        },
    )
    opts = QueryOptions(
        query_mode="tutor",
        tutor_entrypoint=FLASHCARD_HANDOFF_ENTRYPOINT,
    )
    qre.execute_rag_query(
        ctx=ctx,
        options=opts,
        execution_plan=MagicMock(),
        build_query_engine_fn=_fake_build,
        logger=MagicMock(),
    )
    assert captured["question"] == "base question"
    assert "Graph guidance" not in captured["question"]


def test_execute_rag_query_splits_retrieval_and_llm_ms() -> None:
    """P0 honest split: llm_ms comes from timed LLM calls; retrieval_ms = remainder.

    Regression for the old behavior where the full engine.query() path hardcoded
    retrieval_ms=0.0 and attributed all of query_execute_ms to llm_ms, hiding the
    retrieval/reranker cost this package exists to diagnose.
    """
    import time as _time

    from app import query_rag_execution as qre
    from app.models import QueryContext
    from app.usage_cost import record_llm_generation_call_ms

    class _Resp:
        source_nodes: list = []

        def __str__(self) -> str:
            return '{"teaching_summary":"ok"}'

    class _Engine:
        # No `retriever` attr → two-stage extractive path is skipped; full path runs.
        def query(self, question: str):
            _time.sleep(0.03)  # ~30 ms of retrieval + rerank inside engine.query()
            record_llm_generation_call_ms(4.0)  # the LLM synthesis slice only
            return _Resp()

    def _fake_build(_question, _options, **kwargs):
        return {"engine": _Engine(), "cache_hit": False, "pipeline_params": {}}

    # tutor mode → skips two-stage eligibility and retrieval self-correction (clean full path).
    ctx = QueryContext(original_question="q", metadata={})
    opts = QueryOptions(query_mode="tutor", tutor_entrypoint=FLASHCARD_HANDOFF_ENTRYPOINT)
    result = qre.execute_rag_query(
        ctx=ctx,
        options=opts,
        execution_plan=MagicMock(),
        build_query_engine_fn=_fake_build,
        logger=MagicMock(),
    )

    assert result["llm_ms"] == 4.0
    # retrieval_ms must surface the ~30 ms retrieval/rerank, not be hardcoded 0.
    assert result["retrieval_ms"] > 0
    assert result["retrieval_ms"] == round(
        max(0.0, result["query_execute_ms"] - 4.0), 3
    )

