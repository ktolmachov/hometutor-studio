from typing import Any

import pytest

import app.query_service as query_service
from app.config import reset_settings_cache
from app.metrics import RETRIEVAL_TRACE_SCHEMA_VERSION
from app.models import QueryContext, QueryExecutionPlan, QueryOptions
from app.guardrails import OutputGuardrailError
from conftest import patch_faq_cache_enabled


@pytest.fixture(autouse=True)
def _disable_grounded_contract_in_query_service_tests(monkeypatch):
    """Legacy query_service tests assume pre-contract guardrails; enable explicitly in grounded cases."""
    monkeypatch.setenv("GROUNDED_ANSWER_CONTRACT_ENABLED", "false")
    reset_settings_cache()


class _FakeResponse:
    def __init__(self) -> None:
        self.source_nodes = [
            type(
                "Node",
                (),
                {
                    "metadata": {
                        "file_name": "test.txt",
                        "folder_name": "data",
                        "folder_rel": "data",
                        "relative_path": "data/test.txt",
                        "page_label": "1",
                    },
                    "score": 0.9,
                    "text": "some test content",
                },
            )()
        ]
        self.usage = {"prompt_tokens": 220, "completion_tokens": 80, "total_tokens": 300}

    def __str__(self) -> str:
        return "fake answer"


class _CitedFakeResponse(_FakeResponse):
    def __str__(self) -> str:
        return "fake answer [1]"


class _FakeEngine:
    def query(self, question: str):
        return _FakeResponse()


class _CitedFakeEngine(_FakeEngine):
    def query(self, question: str):
        return _CitedFakeResponse()


def test_prepare_query_context_tutor_initialization_failure_falls_back(monkeypatch):
    def fake_run_pipeline(question, options):
        return QueryContext(
            original_question=question,
            query_options=options,
            query_type="qa",
        )

    def broken_tutor_context(ctx, options):
        raise RuntimeError("tutor state down")

    monkeypatch.setattr(query_service, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(query_service, "_initialize_tutor_context", broken_tutor_context)

    ctx, effective_question, followup_used, pipeline_ms = query_service._prepare_query_context(
        "Explain retrieval",
        QueryOptions(query_mode="tutor", topic="retrieval"),
    )

    assert effective_question == "Explain retrieval"
    assert followup_used is False
    assert pipeline_ms >= 0
    assert ctx.trace["tutor_context"] == "fallback"
    assert ctx.trace["tutor_context_error"] == "tutor state down"
    assert ctx.metadata["quiz_difficulty"] == "recognition"
    assert ctx.metadata["learner_profile"]["focus_topic"] == "retrieval"


def _stable_tutor_session_state(**kwargs):
    """Детерминированный learner_profile без due_review из реальной БД (тесты tutor)."""
    topic = str(kwargs.get("current_topic") or "general").strip() or "общая"
    ml = str(kwargs.get("mastery_level") or "intermediate").strip().lower() or "intermediate"
    ps = str(kwargs.get("preferred_style") or "balanced").strip().lower() or "balanced"
    lg = str(kwargs.get("learning_goal") or "understand_topic").strip().lower() or "understand_topic"
    return {
        "learner_profile": {
            "mastery_level": ml,
            "preferred_style": ps,
            "learning_goal": lg,
            "focus_topic": topic,
            "weak_concepts": [],
            "due_review_count": 0,
            "due_review_preview": [],
            "graph_cluster": [topic],
            "route": "standard",
            "recommended_quiz_topic": topic,
            "recent_topics": [topic],
        },
        "learner_hint": "test",
        "graph_hint": "test",
        "orchestration_hint": "test",
    }


def _fake_build_query_engine(question: str, options: QueryOptions, **kwargs):
    return {
        "engine": _FakeEngine(),
        "cache_hit": False,
        "engine_cache_lookup_ms": 0.1,
        "pipeline_params": {
            "profile": "fast",
            "query_type": "qa",
            "retrieval_mode": "vector_only",
            "similarity_top_k": 4,
            "enable_reranker": False,
            "rerank_top_n": 4,
            "rerank_model": "test-reranker",
            "llm_source": "local",
            "llm_model": "qwen/qwen3.6-27b",
            "llm_api_base": "http://127.0.0.1:1234/v1",
            "fallback_used": False,
            "llm_profile": "balanced",
            "homework_mode": options.homework_mode,
            "assistance_level": options.assistance_level,
            "query_engine_cache_policy": "shared",
        },
    }


def _fake_auto_quiz_payload(ctx):
    return {
        "quiz": {
            "questions": [
                {
                    "question": "Auto question?",
                    "options": ["A) 1", "B) 2", "C) 3", "D) 4"],
                    "correct_option": "B",
                    "type": "recognition",
                }
            ]
        },
        "show_immediately": True,
        "motivational_message": "Auto loop",
        "auto_quiz_id": "auto_test",
        "target_topic": (ctx.metadata.get("current_topic") if ctx else None) or "RAG",
    }


def _disable_condense(monkeypatch):
    from app.config import get_settings
    import app.condense_step as condense_step

    monkeypatch.setattr(
        condense_step,
        "get_settings",
        lambda: get_settings().model_copy(update={"enable_condense": False}),
    )


def test_answer_question_smoke(settings_env, monkeypatch):
    settings_env({"LLM_MODEL": "gpt-4o-mini"})
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine)

    options = QueryOptions()
    result = query_service.answer_question("test question", options)

    assert "answer" in result
    assert isinstance(result["answer"], str)

    assert "sources" in result
    assert isinstance(result["sources"], list)
    assert result["sources"], "sources should not be empty for fake response"

    assert "confidence" in result
    confidence = result["confidence"]
    assert confidence["level"] in ("high", "medium", "low")
    assert isinstance(confidence["label"], str)
    assert confidence["source_count"] == 1
    assert "reasons" in confidence

    assert "debug" in result
    debug = result["debug"]
    assert isinstance(debug.get("cache_hit"), bool)
    assert isinstance(debug.get("engine_acquire_ms"), float)
    assert isinstance(debug.get("query_execute_ms"), float)
    assert isinstance(debug.get("total_answer_ms"), float)
    assert debug.get("profile") == "fast"
    assert debug.get("query_type") == "qa"
    assert debug.get("retrieval_mode") == "vector_only"
    assert debug.get("similarity_top_k") == 4
    assert debug.get("rerank_enabled") is False
    assert debug.get("homework_mode") is False
    assert debug.get("assistance_level") is None
    assert debug["token_usage"]["stages"]["generation"]["total_tokens"] == 300
    # Retrieval: heuristic embed tokens for effective query ("test question" → 3)
    assert debug["token_usage"]["stages"]["retrieval"]["total_tokens"] == 3
    assert debug["token_usage"]["total"]["total_tokens"] == 303
    assert debug["estimated_cost_usd"]["stages"]["generation"] is not None
    assert debug["estimated_cost_usd"]["total"] is not None
    assert debug["retrieval_trace"]["schema_version"] == RETRIEVAL_TRACE_SCHEMA_VERSION
    assert debug["retrieval_trace"]["retrieval_mode"] == "vector_only"
    assert debug["retrieval_trace"]["top_k"]["similarity_top_k"] == 4
    assert debug["retrieval_trace"]["returned_source_count"] == 1
    assert debug["retrieval_trace"]["sources"][0]["relative_path"] == "data/test.txt"
    assert debug["retrieval_trace"]["sources"][0]["route"] == "vector_only"
    assert debug["retrieval_trace"]["sources"][0].get("rank_reason")
    src0 = result["sources"][0]
    assert src0.get("cite_index") == 1
    assert src0.get("route") == "vector_only"
    assert src0.get("rank_reason")
    assert debug.get("guardrails") == {
        "input_validated": True,
        "output_validated": True,
        "fallback_applied": False,
        "pii_redacted": False,
        "code": None,
        "message": None,
    }


def test_two_stage_early_exit_skips_llm_query(settings_env, monkeypatch):
    settings_env({"ENABLE_TWO_STAGE_ANSWER_PATH": "true"})

    class _FakeRetriever:
        def retrieve(self, qb):
            n1 = type("NS", (), {})()
            n1.score = 0.95
            inner1 = type("IN", (), {})()
            inner1.text = "chunk one with substantial text for extractive path"
            n1.node = inner1
            n2 = type("NS", (), {})()
            n2.score = 0.91
            inner2 = type("IN", (), {})()
            inner2.text = "chunk two with substantial text for extractive path"
            n2.node = inner2
            return [n1, n2]

    class _FakeEngineTS:
        def __init__(self):
            self.retriever = _FakeRetriever()
            self.query_calls = 0

        def query(self, q):
            self.query_calls += 1
            return _FakeResponse()

    capture: dict[str, Any] = {}

    def _fake_be(question, options, **kwargs):
        eng = _FakeEngineTS()
        capture["engine"] = eng
        return {
            "engine": eng,
            "cache_hit": False,
            "engine_cache_lookup_ms": 0.1,
            "pipeline_params": {
                "profile": "fast",
                "query_type": "qa",
                "retrieval_mode": "vector_only",
                "similarity_top_k": 4,
                "enable_reranker": False,
                "rerank_top_n": 4,
                "rerank_model": "test-reranker",
                "homework_mode": options.homework_mode,
                "assistance_level": options.assistance_level,
                "query_engine_cache_policy": "shared",
            },
        }

    monkeypatch.setattr(query_service, "build_query_engine", _fake_be)

    result = query_service.answer_question("What is retrieval test?", QueryOptions())

    assert capture["engine"].query_calls == 0
    assert result["debug"]["pipeline_trace"].get("answer_path", {}).get("mode") == "two_stage_early"
    assert "выжимка" in (result.get("answer") or "").lower()
    gen = (result["debug"].get("token_usage") or {}).get("stages", {}).get("generation")
    assert gen is None or gen.get("total_tokens", 0) == 0


class _NoSourcesResponse:
    source_nodes = []

    def __str__(self) -> str:
        return "plain unsupported answer"


class _NoSourcesEngine:
    def query(self, question: str):
        return _NoSourcesResponse()


def _fake_build_query_engine_without_sources(question: str, options: QueryOptions, **kwargs):
    return {
        "engine": _NoSourcesEngine(),
        "cache_hit": False,
        "engine_cache_lookup_ms": 0.1,
        "pipeline_params": {
            "profile": "fast",
            "query_type": "qa",
            "retrieval_mode": "vector_only",
            "similarity_top_k": 4,
            "enable_reranker": False,
            "rerank_top_n": 4,
            "rerank_model": "test-reranker",
            "homework_mode": options.homework_mode,
            "assistance_level": options.assistance_level,
        },
    }


def test_answer_question_debug_includes_homework_mode(monkeypatch):
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine)

    options = QueryOptions(homework_mode=True, assistance_level="hint")
    result = query_service.answer_question("help with homework", options)

    assert result["debug"]["homework_mode"] is True
    assert result["debug"]["assistance_level"] == "hint"


def test_answer_question_debug_includes_study_mode(monkeypatch):
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine)

    options = QueryOptions(study_mode=True, followup_context="Previous answer: RAG retrieves context.")
    result = query_service.answer_question("Explain simpler", options)

    assert result["debug"]["study_mode"] is True
    assert result["debug"]["followup_context_used"] is True


def test_answer_question_applies_safe_fallback_without_sources(monkeypatch):
    monkeypatch.setattr(
        query_service,
        "build_query_engine",
        _fake_build_query_engine_without_sources,
    )

    options = QueryOptions()
    result = query_service.answer_question("test question", options)

    assert result["sources"] == []
    assert result["debug"]["guardrails"]["output_validated"] is False
    assert result["debug"]["guardrails"]["fallback_applied"] is True
    assert result["debug"]["guardrails"]["code"] == "missing_sources"
    assert result["answer"]


def test_answer_question_raises_when_fallback_policy_is_disabled(monkeypatch):
    monkeypatch.setattr(
        query_service,
        "build_query_engine",
        _fake_build_query_engine_without_sources,
    )
    monkeypatch.setattr(query_service, "should_apply_fallback", lambda code: False)

    options = QueryOptions()

    try:
        query_service.answer_question("test question", options)
        assert False, "Expected OutputGuardrailError"
    except OutputGuardrailError as exc:
        assert exc.code == "missing_sources"


class _EmptyAnswerResponse:
    source_nodes = []

    def __str__(self) -> str:
        return "   "


class _EmptyAnswerEngine:
    def query(self, question: str):
        return _EmptyAnswerResponse()


def _fake_build_query_engine_with_empty_answer(question: str, options: QueryOptions, **kwargs):
    return {
        "engine": _EmptyAnswerEngine(),
        "cache_hit": False,
        "engine_cache_lookup_ms": 0.1,
        "pipeline_params": {
            "profile": "fast",
            "query_type": "qa",
            "retrieval_mode": "vector_only",
            "similarity_top_k": 4,
            "enable_reranker": False,
            "rerank_top_n": 4,
            "rerank_model": "test-reranker",
        },
    }


class _PiiResponse:
    source_nodes = [
        type(
            "Node",
            (),
            {
                "metadata": {"relative_path": "data/test.txt", "page_label": "1"},
                "score": 0.8,
                "text": "contact info",
            },
        )()
    ]

    def __str__(self) -> str:
        return "Contact me at test@example.com"


class _PiiEngine:
    def query(self, question: str):
        return _PiiResponse()


def _fake_build_query_engine_with_pii(question: str, options: QueryOptions, **kwargs):
    return {
        "engine": _PiiEngine(),
        "cache_hit": False,
        "engine_cache_lookup_ms": 0.1,
        "pipeline_params": {
            "profile": "fast",
            "query_type": "qa",
            "retrieval_mode": "vector_only",
            "similarity_top_k": 4,
            "enable_reranker": False,
            "rerank_top_n": 4,
            "rerank_model": "test-reranker",
        },
    }


def test_answer_question_applies_safe_fallback_for_empty_answer(monkeypatch):
    monkeypatch.setattr(
        query_service,
        "build_query_engine",
        _fake_build_query_engine_with_empty_answer,
    )

    options = QueryOptions()
    result = query_service.answer_question("test question", options)

    assert result["sources"] == []
    assert result["debug"]["guardrails"]["code"] == "empty_answer"
    assert result["debug"]["guardrails"]["fallback_applied"] is True
    assert result["answer"]


def test_answer_question_redacts_pii_in_answer_instead_of_scary_fallback(monkeypatch):
    monkeypatch.setattr(
        query_service,
        "build_query_engine",
        _fake_build_query_engine_with_pii,
    )

    options = QueryOptions()
    result = query_service.answer_question("test question", options)

    assert len(result["sources"]) == 1
    assert result["debug"]["guardrails"]["code"] is None
    assert result["debug"]["guardrails"]["fallback_applied"] is False
    assert result["debug"]["guardrails"]["pii_redacted"] is True
    assert "test@example.com" not in result["answer"]
    assert "[REDACTED_EMAIL]" in result["answer"]


def test_answer_question_logs_redacted_question_and_answer_preview(monkeypatch):
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine_with_pii)

    records = []

    class _FakeLogger:
        def info(self, message, *args):
            records.append(("info", message % args if args else message))

        def warning(self, message, *args):
            records.append(("warning", message % args if args else message))

        def exception(self, message, *args):
            records.append(("exception", message % args if args else message))

        def error(self, message, *args):
            records.append(("error", message % args if args else message))

    monkeypatch.setattr(query_service, "logger", _FakeLogger())

    options = QueryOptions()
    query_service.answer_question("email test@example.com token: abcdefgh", options)

    joined = "\n".join(entry[1] for entry in records)
    assert "test@example.com" not in joined
    assert "abcdefgh" not in joined
    assert "[REDACTED_EMAIL]" in joined


def test_compute_answer_confidence_penalizes_low_classify_confidence():
    confidence = query_service._compute_answer_confidence(
        sources=[
            {"relative_path": "doc1.md", "score": 0.8},
            {"relative_path": "doc2.md", "score": 0.75},
            {"relative_path": "doc3.md", "score": 0.72},
        ],
        query_type="qa",
        classify_confidence=0.4,
    )

    assert confidence["level"] == "medium"
    assert "low_classify_confidence" in confidence["reasons"]


def test_compute_answer_confidence_penalizes_low_document_coverage_for_synthesis():
    confidence = query_service._compute_answer_confidence(
        sources=[
            {"relative_path": "doc1.md", "score": 0.9},
            {"relative_path": "doc1.md", "score": 0.85},
            {"relative_path": "doc1.md", "score": 0.83},
        ],
        query_type="synthesis",
        classify_confidence=0.95,
    )

    assert confidence["unique_source_files"] == 1
    assert "low_document_coverage" in confidence["reasons"]
    assert confidence["level"] in ("medium", "low")


def test_compute_deterministic_quality_checks_flags_short_answer_and_low_score():
    checks = query_service._compute_deterministic_quality_checks(
        "short answer",
        [{"relative_path": "doc1.md", "score": 0.2}],
        fallback_applied=False,
    )

    assert checks["passed"] is False
    assert checks["checks"]["answer_not_empty"] is True
    assert checks["checks"]["has_sources"] is True
    assert checks["checks"]["answer_length_in_range"] is False
    assert checks["checks"]["min_source_score_ok"] is False
    assert "answer_length_in_range" in checks["failed_checks"]
    assert "min_source_score_ok" in checks["failed_checks"]


def test_answer_question_aggregates_stage_token_usage(monkeypatch):
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine)

    class _FakeContext:
        effective_query = "rewritten test question"
        effective_query_source = "rewritten"
        rewritten_query = "rewritten test question"
        query_type = "qa"
        prompt_key = "qa"
        retrieval_strategy = "default"
        classify_method = "llm"
        classify_confidence = 0.91
        subquestions = []
        metadata = {}
        trace = {
            "rewrite_enabled": True,
            "rewritten_question": "rewritten test question",
            "rewrite_model": "gpt-4o-mini",
            "classify_usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60},
            "rewrite_usage": {"prompt_tokens": 30, "completion_tokens": 15, "total_tokens": 45},
            "classify_estimated_cost_usd": 0.0000135,
            "rewrite_estimated_cost_usd": 0.0000135,
        }

    monkeypatch.setattr(query_service, "run_pipeline", lambda question, options: _FakeContext())

    result = query_service.answer_question("test question", QueryOptions())

    assert result["debug"]["token_usage"]["stages"]["classify"]["total_tokens"] == 60
    assert result["debug"]["token_usage"]["stages"]["rewrite"]["total_tokens"] == 45
    assert result["debug"]["token_usage"]["stages"]["generation"]["total_tokens"] == 300
    # "rewritten test question" → 23//4 = 5 embed tokens (vector_only)
    assert result["debug"]["token_usage"]["stages"]["retrieval"]["total_tokens"] == 5
    assert result["debug"]["token_usage"]["total"]["total_tokens"] == 410
    assert result["debug"]["estimated_cost_usd"]["stages"]["classify"] == 0.0000135


def test_tutor_query_mode_adds_knowledge_graph_debug(monkeypatch):
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine)
    monkeypatch.setattr(
        "app.learner_state_scope.due_reviews_summary_for_kg",
        lambda kg, **kwargs: {"count": 0, "hint": None, "preview_concepts": []},
    )
    monkeypatch.setattr(
        "app.quiz_service.generate_tutor_inline_quiz_questions",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        "app.quiz_service.generate_and_attach_micro_quiz",
        _fake_auto_quiz_payload,
    )
    monkeypatch.setattr(
        "app.user_state.get_learner_state_diagnostics",
        lambda recent_limit=8: {
            "current_lineage": {"generation_id": "gen-7", "index_version": 7},
            "synced_lineage": {
                "generation_id": "gen-7",
                "index_version": 7,
                "migrated_at": "2026-04-07T10:00:00+00:00",
            },
            "archive_counts": {"spaced_repetition": 1, "quiz_mastery": 2, "total": 3},
            "has_archived_state": True,
        },
    )
    opts = QueryOptions(query_mode="tutor", topic="RAG")
    result = query_service.answer_question("What is retrieval?", opts)
    dbg = result["debug"]
    tutor = result.get("tutor") or {}
    tutor_answer = result.get("tutor_answer") or {}
    assert dbg.get("query_mode") == "tutor"
    assert dbg.get("prompt_key") == "tutor"
    assert "tutor_next_best_action" in dbg
    assert "graph_summary" in dbg
    assert "tutor_prerequisites_ok" in dbg
    assert dbg.get("tutor_spaced_repetition_due_count") == 0
    assert dbg.get("tutor_quiz_difficulty") == "recognition"
    assert dbg.get("tutor_socratic_type") == "clarification"
    assert dbg.get("tutor_learner_state_lineage", {}).get("current_lineage", {}).get("generation_id") == "gen-7"
    assert dbg.get("tutor_learner_state_lineage", {}).get("archive_counts", {}).get("total") == 3
    assert dbg.get("tutor_learner_state_lineage", {}).get("has_archived_state") is True
    assert "inline_quiz" not in dbg
    assert "socratic_followup" not in dbg
    assert "tutor_decision" not in dbg
    assert "persisted_learner_profile" not in dbg
    assert "auto_quiz" not in dbg
    assert isinstance(tutor.get("decision"), dict)
    assert isinstance(tutor.get("learner_profile"), dict)
    assert isinstance(tutor.get("auto_quiz"), dict)
    assert isinstance(tutor.get("orchestration_state"), dict)
    assert tutor["orchestration_state"].get("contract_version") == 1
    assert tutor["orchestration_state"].get("current_concept")
    assert isinstance(tutor.get("socratic"), dict)
    assert tutor["socratic"].get("question_type") == "clarification"
    assert tutor_answer.get("answer_kind") == "tutor_teaching_step"
    assert tutor_answer.get("teaching_summary")
    assert tutor_answer.get("next_action")
    assert tutor_answer.get("next_action_reason")
    assert isinstance(tutor_answer.get("suggested_ctas"), list)
    assert tutor["auto_quiz"].get("show_immediately") is True
    assert tutor.get("inline_quiz") == []
    assert tutor.get("socratic_followup") is None


def test_tutor_query_mode_keeps_auto_quiz_when_inline_quiz_exists(monkeypatch):
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine)
    monkeypatch.setattr(
        query_service,
        "run_pipeline",
        lambda question, options: query_service.QueryContext(
            original_question=question,
            query_options=options,
            metadata={"current_topic": "RAG", "mastery_level": "intermediate"},
        ),
    )

    def _fake_parse(_: str):
        return (
            "Tutor answer",
            {"type": "probing", "question": "Why?"},
            [{"type": "short_answer", "question": "Q1", "concept": "RAG", "difficulty": "recall"}],
            None,
        )

    monkeypatch.setattr("app.quiz_service.parse_tutor_rag_response", _fake_parse)
    monkeypatch.setattr(
        "app.quiz_service.generate_and_attach_micro_quiz",
        _fake_auto_quiz_payload,
    )

    result = query_service.answer_question("Explain retrieval", QueryOptions(query_mode="tutor"))

    assert result["answer"] == "Tutor answer"
    assert result["tutor"]["inline_quiz"] != []
    assert result["tutor"]["auto_quiz"]["auto_quiz_id"] == "auto_test"
    assert result["tutor_answer"]["check_question"] == "Why?"


def test_tutor_answer_contract_prefers_teaching_json_fields(monkeypatch):
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine)
    monkeypatch.setattr(
        "app.tutor_orchestrator.build_tutor_session_state", _stable_tutor_session_state
    )
    monkeypatch.setattr(
        query_service,
        "run_pipeline",
        lambda question, options: query_service.QueryContext(
            original_question=question,
            query_options=options,
            metadata={"current_topic": "RAG", "mastery_level": "intermediate"},
        ),
    )

    def _fake_parse(_: str):
        return (
            "Tutor answer",
            {"type": "probing", "question": "Fallback?"},
            [],
            {
                "teaching_summary": "Кратко про retrieval.",
                "understanding_state": {
                    "what_you_understood": "Что retrieval добавляет контекст.",
                    "risk_gaps": "Можно путать retrieval и reranking.",
                    "what_to_do_now": "Сверить на примере.",
                },
                "socratic_check": "Почему retrieval помогает LLM?",
                "next_action": "Дай пример",
                "next_action_reason": "Пример закрепит идею на практике.",
                "suggested_ctas": ["Дай пример", "Проверь меня"],
                "depth_level": "intermediate",
                "trust_signals": {"sources_used": 2, "confidence": "medium", "coverage_warning": None},
            },
        )

    monkeypatch.setattr("app.quiz_service.parse_tutor_rag_response", _fake_parse)
    monkeypatch.setattr(
        "app.quiz_service.generate_tutor_inline_quiz_questions",
        lambda **kwargs: [],
    )
    monkeypatch.setattr("app.quiz_service.generate_and_attach_micro_quiz", lambda ctx: None)

    result = query_service.answer_question("Explain retrieval", QueryOptions(query_mode="tutor"))

    assert result["tutor_answer"] == {
        "contract_version": 1,
        "answer_kind": "tutor_teaching_step",
        "teaching_summary": "Кратко про retrieval.",
        "check_question": "Почему retrieval помогает LLM?",
        "next_action": "Дай пример",
        "next_action_reason": "Пример закрепит идею на практике.",
        "suggested_ctas": ["Дай пример", "Проверь меня"],
        "understanding_state": {
            "what_you_understood": "Что retrieval добавляет контекст.",
            "risk_gaps": "Можно путать retrieval и reranking.",
            "what_to_do_now": "Сверить на примере.",
        },
        "depth_level": "intermediate",
        "trust_signals": {"sources_used": 1, "confidence": "medium", "coverage_warning": None},
        "inline_quiz": [],
        "auto_quiz": result["tutor"]["auto_quiz"],
        "learner_profile": result["tutor"]["learner_profile"],
        "route": result["tutor"]["decision"]["route"],
        "recommended_quiz_topic": result["tutor"]["decision"]["recommended_quiz_topic"],
    }


def test_tutor_answer_contract_uses_mode_aware_recommendation_when_teaching_omits_next_step(monkeypatch):
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine)
    monkeypatch.setattr(
        query_service,
        "run_pipeline",
        lambda question, options: query_service.QueryContext(
            original_question=question,
            query_options=options,
            metadata={
                "current_topic": "RAG",
                "mastery_level": "intermediate",
                "learned_concepts": ["Embedding"],
            },
        ),
    )

    def _fake_parse(_: str):
        return (
            "Tutor answer",
            None,
            [],
            {
                "teaching_summary": "Кратко про retrieval.",
                "understanding_state": {
                    "what_you_understood": "Что retrieval добавляет контекст.",
                    "risk_gaps": "",
                    "what_to_do_now": "",
                },
            },
        )

    monkeypatch.setattr("app.quiz_service.parse_tutor_rag_response", _fake_parse)
    monkeypatch.setattr(
        "app.quiz_service.generate_tutor_inline_quiz_questions",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        "app.quiz_service.generate_and_attach_micro_quiz",
        _fake_auto_quiz_payload,
    )
    # Иначе apply_tutor_self_correction для route=foundation подставит next_action «Объясни проще»
    # и перекроет рекомендацию графа (explicit_action имеет приоритет).
    monkeypatch.setattr(
        "app.tutor_orchestrator.apply_tutor_self_correction",
        lambda teaching, **kwargs: teaching,
    )
    monkeypatch.setattr(
        "app.knowledge_graph.knowledge_graph.recommend_tutor_next_step",
        lambda **kwargs: {
            "next_action": "Следующий шаг",
            "next_action_reason": "Можно переходить к теме MultiTurn.",
            "suggested_ctas": ["Следующий шаг", "Проверь меня"],
            "graph_recommendation": {"concept": "MultiTurn"},
        },
    )

    result = query_service.answer_question("Explain retrieval", QueryOptions(query_mode="tutor"))

    assert result["tutor_answer"]["next_action"] == "Следующий шаг"
    assert result["tutor_answer"]["next_action_reason"] == "Можно переходить к теме MultiTurn."
    assert result["tutor_answer"]["suggested_ctas"] == ["Следующий шаг", "Проверь меня"]
    assert result["tutor_answer"]["understanding_state"]["what_to_do_now"] == "Следующий шаг"


def test_tutor_query_mode_persists_typed_tutor_payload(monkeypatch):
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine)
    monkeypatch.setattr(
        "app.quiz_service.generate_tutor_inline_quiz_questions",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        "app.quiz_service.generate_and_attach_micro_quiz",
        _fake_auto_quiz_payload,
    )
    captured = {}

    def _capture_persist(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(query_service, "_persist_chat_session", _capture_persist)
    result = query_service.answer_question(
        "Explain retrieval",
        QueryOptions(query_mode="tutor", session_id="sess-typed"),
    )

    assert isinstance(result.get("tutor"), dict)
    meta = captured.get("assistant_metadata") or {}
    assert isinstance(meta.get("tutor"), dict)
    assert isinstance(meta.get("tutor_answer"), dict)
    assert isinstance(meta["tutor"].get("decision"), dict)
    assert isinstance(meta["tutor"].get("learner_profile"), dict)
    assert isinstance(meta["tutor"].get("orchestration_state"), dict)
    assert meta["tutor"]["orchestration_state"].get("contract_version") == 1
    assert isinstance(meta["tutor"].get("socratic"), dict)
    assert meta["tutor_answer"].get("answer_kind") == "tutor_teaching_step"
    assert "tutor_v2" not in meta
    assert "tutor_decision" not in meta
    assert "auto_quiz" not in meta
    src = captured.get("sources")
    assert isinstance(src, list) and len(src) >= 1
    assert src[0].get("relative_path") == "data/test.txt"


def test_faq_cache_used_when_enabled_and_no_session(monkeypatch):
    patch_faq_cache_enabled(monkeypatch)
    build_calls: list[int] = []

    def _counting_build(*args, **kwargs):
        build_calls.append(1)
        return _fake_build_query_engine(*args, **kwargs)

    monkeypatch.setattr(query_service, "build_query_engine", _counting_build)
    monkeypatch.setattr(
        "app.faq_memory.find_similar_questions",
        lambda **kw: [
            {
                "answer": "from faq memory",
                "sources": [
                    {
                        "relative_path": "data/doc.txt",
                        "page": "1",
                        "score": 0.91,
                    }
                ],
                "score": 0.95,
            }
        ],
    )

    result = query_service.answer_question("How to index?", QueryOptions())
    assert build_calls == []
    assert result["debug"].get("faq_cache_hit") is True
    assert result["debug"].get("faq_cache_eligible") is True
    assert result["debug"].get("faq_cache_skip_reason") is None
    assert result["debug"]["retrieval_trace"]["schema_version"] == RETRIEVAL_TRACE_SCHEMA_VERSION
    assert result["debug"]["trace_schema"]["retrieval_trace_check"]["ok"] is True
    assert result["answer"] == "from faq memory"
    fs = result["sources"][0]
    assert fs.get("route") == "faq_cache"
    assert fs.get("cite_index") == 1
    assert fs.get("rank_reason")
    assert result["debug"]["retrieval_trace"]["sources"][0]["route"] == "faq_cache"


def test_faq_cache_debug_token_usage_is_present(monkeypatch):
    patch_faq_cache_enabled(monkeypatch)
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine)
    monkeypatch.setattr(
        "app.faq_memory.find_similar_questions",
        lambda **kw: [{"answer": "from faq memory", "sources": [], "score": 0.9}],
    )

    result = query_service.answer_question("How to index?", QueryOptions())
    token_usage = result["debug"]["token_usage"]
    assert "stages" in token_usage
    assert "total" in token_usage
    assert token_usage["total"] is None or isinstance(token_usage["total"], dict)


def test_faq_cache_skipped_when_session_id(monkeypatch):
    faq_calls: list[dict] = []

    def _track_faq(**kwargs):
        faq_calls.append(kwargs)
        return [{"answer": "wrong", "sources": [], "score": 1.0}]

    patch_faq_cache_enabled(monkeypatch)
    _disable_condense(monkeypatch)
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine)
    monkeypatch.setattr("app.faq_memory.find_similar_questions", _track_faq)

    result = query_service.answer_question(
        "test question", QueryOptions(session_id="sess-faq-skip"),
    )
    assert faq_calls == []
    assert result["debug"].get("faq_cache_hit") is False
    assert result["debug"].get("faq_cache_eligible") is False
    assert result["debug"].get("faq_cache_skip_reason") == "session_id"
    assert result["debug"].get("query_engine_cache_policy") == "disabled_for_session"
    assert result["answer"] == "fake answer"


def test_faq_cache_skipped_when_tutor_mode(monkeypatch):
    faq_calls: list[dict] = []

    def _track_faq(**kwargs):
        faq_calls.append(kwargs)
        return [{"answer": "wrong", "sources": [], "score": 1.0}]

    patch_faq_cache_enabled(monkeypatch, enable_tutor_auto_quiz_loop=False)
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine)
    monkeypatch.setattr(
        "app.quiz_service.generate_tutor_inline_quiz_questions",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        "app.quiz_service.generate_and_attach_micro_quiz",
        _fake_auto_quiz_payload,
    )
    monkeypatch.setattr("app.faq_memory.find_similar_questions", _track_faq)

    result = query_service.answer_question("What is RAG?", QueryOptions(query_mode="tutor"))
    assert faq_calls == []
    assert result["debug"].get("faq_cache_hit") is False
    assert result["debug"].get("faq_cache_eligible") is False
    assert result["debug"].get("faq_cache_skip_reason") == "tutor_mode"
    assert result["answer"] == "fake answer"


def test_faq_cache_skipped_when_tutor_mode_has_whitespace_and_mixed_case(monkeypatch):
    faq_calls: list[dict] = []

    def _track_faq(**kwargs):
        faq_calls.append(kwargs)
        return [{"answer": "wrong", "sources": [], "score": 1.0}]

    patch_faq_cache_enabled(monkeypatch, enable_tutor_auto_quiz_loop=False)
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine)
    monkeypatch.setattr(
        "app.quiz_service.generate_tutor_inline_quiz_questions",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        "app.quiz_service.generate_and_attach_micro_quiz",
        _fake_auto_quiz_payload,
    )
    monkeypatch.setattr("app.faq_memory.find_similar_questions", _track_faq)

    result = query_service.answer_question("What is RAG?", QueryOptions(query_mode="  TuToR  "))
    assert faq_calls == []
    assert result["debug"].get("faq_cache_hit") is False
    assert result["debug"].get("faq_cache_eligible") is False
    assert result["debug"].get("faq_cache_skip_reason") == "tutor_mode"
    assert result["answer"] == "fake answer"


def test_session_requests_surface_disabled_query_engine_cache_policy(monkeypatch):
    def _session_build(question: str, options: QueryOptions, **kwargs):
        result = _fake_build_query_engine(question, options, **kwargs)
        result["pipeline_params"]["query_engine_cache_policy"] = "disabled_for_session"
        return result

    patch_faq_cache_enabled(monkeypatch)
    _disable_condense(monkeypatch)
    monkeypatch.setattr(query_service, "build_query_engine", _session_build)
    monkeypatch.setattr(
        "app.faq_memory.find_similar_questions",
        lambda **kwargs: [{"answer": "wrong", "sources": [], "score": 1.0}],
    )

    result = query_service.answer_question(
        "test question",
        QueryOptions(session_id="sess-engine-cache"),
    )

    assert result["debug"].get("faq_cache_skip_reason") == "session_id"
    assert result["debug"].get("query_engine_cache_policy") == "disabled_for_session"


def test_query_service_uses_execution_plan_for_faq_and_engine_cache_policy(monkeypatch):
    planner_calls: list[str] = []

    patch_faq_cache_enabled(monkeypatch)
    _disable_condense(monkeypatch)
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine)
    monkeypatch.setattr(
        query_service,
        "resolve_query_execution_plan",
        lambda question, options, query_context=None: (
            planner_calls.append(question) or QueryExecutionPlan(
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
                query_engine_cache_policy="disabled_for_session",
                faq_cache_eligible=False,
                faq_cache_skip_reason="session_id",
                doc_top_k=None,
            )
        ),
    )
    monkeypatch.setattr(
        "app.faq_memory.find_similar_questions",
        lambda **kwargs: [{"answer": "wrong", "sources": [], "score": 1.0}],
    )

    result = query_service.answer_question(
        "test question",
        QueryOptions(session_id="sess-from-plan"),
    )

    # План строится по effective_query после run_pipeline (condense с session_id может развернуть историю).
    assert len(planner_calls) == 1
    assert "test question" in planner_calls[0]
    assert result["debug"].get("faq_cache_skip_reason") == "session_id"
    assert result["debug"].get("query_engine_cache_policy") == "disabled_for_session"


def test_answer_question_debug_includes_full_pipeline_stage_trace(monkeypatch):
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine)

    class _FakeContext:
        effective_query = "rewritten test question"
        effective_query_source = "rewritten"
        rewritten_query = "rewritten test question"
        query_type = "qa"
        prompt_key = "qa"
        retrieval_strategy = "default"
        classify_method = "llm"
        classify_confidence = 0.91
        subquestions = []
        pipeline_steps = ["classify", "rewrite"]
        trace = {
            "schema_version": 1,
            "effective_query": "rewritten test question",
            "effective_query_source": "rewritten",
            "rewrite_enabled": True,
            "rewritten_question": "rewritten test question",
            "rewrite_model": "gpt-4o-mini",
            "classify_usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60},
            "rewrite_usage": {"prompt_tokens": 30, "completion_tokens": 15, "total_tokens": 45},
            "classify_estimated_cost_usd": 0.0000135,
            "rewrite_estimated_cost_usd": 0.0000135,
        }
        # Не первый turn — без smart-default hybrid (US-3.4), ожидаем vector_only из конфига.
        metadata = {"session_user_turns_before": 1}

    monkeypatch.setattr(query_service, "run_pipeline", lambda question, options: _FakeContext())

    result = query_service.answer_question("test question", QueryOptions(rag_profile="fast"))

    assert result["debug"]["pipeline_trace"]["pipeline_stages"] == [
        "classify",
        "condense",
        "rewrite",
        "retrieve",
        "rerank_skipped",
        "generate",
    ]
    assert result["debug"]["trace_schema"]["pipeline_trace_check"]["ok"] is True
    assert result["debug"]["trace_schema"]["retrieval_trace_check"]["ok"] is True
    assert result["debug"]["pipeline_trace"]["retrieve_stage"]["retrieval_mode"] == "vector_only"
    assert result["debug"]["pipeline_trace"]["generate_stage"]["model"] == "qwen/qwen3.6-27b"
    assert result["debug"]["pipeline_trace"]["generate_stage"]["llm_source"] == "local"
    assert result["debug"]["pipeline_trace"]["generate_stage"]["fallback_used"] is False
    assert result["debug"]["pipeline_trace"]["generate_stage"]["latency_ms"] >= 0
    assert result["debug"]["llm_source"] == "local"
    assert result["debug"]["llm_model"] == "qwen/qwen3.6-27b"
    assert result["debug"]["fallback_used"] is False


def test_build_tutor_payload_includes_orchestration_pipeline_fields():
    p = query_service._build_tutor_payload(
        tutor_teaching=None,
        tutor_decision=None,
        auto_quiz_payload=None,
        inline_quiz=None,
        socratic_followup=None,
        learner_profile=None,
        tutor_orchestration_pipeline={
            "schema_version": 1,
            "phase": "orchestrate",
            "decision_source": "rule",
            "selected_agent": "ConceptExplainer",
            "should_trigger_microquiz": False,
            "policy_clamped": True,
            "policy_clamp_reasons": ["due_review_forced_microquiz"],
        },
        tutor_pipeline=[{"step": "orchestrate_pedagogical_action_step", "status": "ok"}],
    )
    assert p is not None
    assert p["tutor_orchestration_pipeline"]["phase"] == "orchestrate"
    assert p["orchestration_phase"] == "orchestrate"
    assert p["orchestration_decision_source"] == "rule"
    assert p["selected_agent"] == "ConceptExplainer"
    assert p["should_trigger_microquiz"] is False
    assert p["policy_clamped"] is True
    assert p["policy_clamp_reasons"] == ["due_review_forced_microquiz"]
    assert p["tutor_pipeline"][0]["status"] == "ok"


def test_build_tutor_payload_uses_orchestration_state_scalar_fallback():
    p = query_service._build_tutor_payload(
        tutor_teaching=None,
        tutor_decision=None,
        auto_quiz_payload=None,
        inline_quiz=None,
        socratic_followup=None,
        learner_profile=None,
        orchestration_state={
            "contract_version": 1,
            "current_concept": "retrieval",
            "orchestration_phase": "rag_prepare",
            "orchestration_decision_source": "rule_fallback",
            "selected_agent": "ConceptExplainer",
            "should_trigger_microquiz": True,
            "policy_clamped": True,
            "policy_clamp_reasons": ["due_review_forced_microquiz"],
        },
        tutor_orchestration_pipeline=None,
        tutor_pipeline=None,
    )
    assert p is not None
    assert p["orchestration_phase"] == "rag_prepare"
    assert p["orchestration_decision_source"] == "rule_fallback"
    assert p["selected_agent"] == "ConceptExplainer"
    assert p["should_trigger_microquiz"] is True
    assert p["policy_clamped"] is True
    assert p["policy_clamp_reasons"] == ["due_review_forced_microquiz"]


class _BudgetFakeClock:
    def __init__(self, *, elapsed_ms: float = 0.0) -> None:
        self._calls = 0
        self._elapsed_ms = elapsed_ms

    def __call__(self) -> float:
        self._calls += 1
        if self._calls == 1:
            return 0.0
        return self._elapsed_ms / 1000.0


def _patch_budget_clock(monkeypatch, *, elapsed_ms: float, jsonl_path):
    import app.latency_budget as latency_budget

    real_with_budget = latency_budget.with_budget

    def _wrapped(surface, fn, **kwargs):
        return real_with_budget(
            surface,
            fn,
            clock=_BudgetFakeClock(elapsed_ms=elapsed_ms),
            jsonl_path=jsonl_path,
            **kwargs,
        )

    monkeypatch.setattr(query_service, "with_budget", _wrapped)


def test_answer_question_latency_budget_surface_query(settings_env, monkeypatch, tmp_path):
    settings_env({"LLM_MODEL": "gpt-4o-mini"})
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine)
    jsonl = tmp_path / "latency_budget.jsonl"
    _patch_budget_clock(monkeypatch, elapsed_ms=5000.0, jsonl_path=jsonl)

    result = query_service.answer_question("test question", QueryOptions())

    budget = result["debug"]["latency_budget"]
    assert budget["surface"] == "query"
    assert budget["event"] == "surface_breached_soft"
    assert budget["target_ms"] == 2500
    rows = [line for line in jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    assert '"surface": "query"' in rows[0]


def test_answer_question_latency_budget_surface_tutor_turn(monkeypatch, tmp_path):
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine)
    monkeypatch.setattr(
        "app.learner_state_scope.due_reviews_summary_for_kg",
        lambda kg, **kwargs: {"count": 0, "hint": None, "preview_concepts": []},
    )
    monkeypatch.setattr(
        "app.quiz_service.generate_tutor_inline_quiz_questions",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        "app.quiz_service.generate_and_attach_micro_quiz",
        _fake_auto_quiz_payload,
    )
    monkeypatch.setattr(
        "app.user_state.get_learner_state_diagnostics",
        lambda recent_limit=8: {
            "current_lineage": {"generation_id": "gen-1", "index_version": 1},
            "synced_lineage": {"generation_id": "gen-1", "index_version": 1},
            "archive_counts": {"total": 0},
            "has_archived_state": False,
        },
    )
    jsonl = tmp_path / "latency_budget.jsonl"
    _patch_budget_clock(monkeypatch, elapsed_ms=4000.0, jsonl_path=jsonl)

    result = query_service.answer_question(
        "What is retrieval?",
        QueryOptions(query_mode="tutor", topic="RAG"),
    )

    budget = result["debug"]["latency_budget"]
    assert budget["surface"] == "tutor_turn"
    assert budget["surface"] != "query"
    assert budget["event"] == "surface_breached_soft"
    assert budget["target_ms"] == 1500


def test_answer_question_latency_budget_session_tape_on_soft_breach(
    settings_env, monkeypatch, tmp_path
):
    settings_env({"LLM_MODEL": "gpt-4o-mini"})
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine)
    jsonl = tmp_path / "latency_budget.jsonl"
    _patch_budget_clock(monkeypatch, elapsed_ms=5000.0, jsonl_path=jsonl)
    sessions_dir = tmp_path / "sessions"
    monkeypatch.setattr("app.session_tape.SESSIONS_DIR", sessions_dir)

    query_service.answer_question(
        "test question",
        QueryOptions(session_id="sess-budget-1", folder_rel="CourseA"),
    )

    tape_path = sessions_dir / "sess-budget-1.jsonl"
    assert tape_path.is_file()
    lines = [line for line in tape_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1
    import json

    row = json.loads(lines[0])
    assert row["event"] == "surface_breached_soft"
    assert row["surface"] == "query"
    assert row["payload"]["ladder_step"] == 3


def test_answer_question_latency_budget_hard_breach_non_preemptive(settings_env, monkeypatch, tmp_path):
    settings_env({"LLM_MODEL": "gpt-4o-mini"})
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine)
    jsonl = tmp_path / "latency_budget.jsonl"
    _patch_budget_clock(monkeypatch, elapsed_ms=9000.0, jsonl_path=jsonl)

    result = query_service.answer_question("test question", QueryOptions())

    budget = result["debug"]["latency_budget"]
    assert budget["event"] == "surface_breached_hard"
    assert result["answer"]
    assert result["sources"]


def _fake_build_query_engine_cited(question: str, options: QueryOptions, **kwargs):
    return {
        "engine": _CitedFakeEngine(),
        "cache_hit": False,
        "engine_cache_lookup_ms": 0.1,
        "pipeline_params": {
            "profile": "fast",
            "query_type": "qa",
            "retrieval_mode": "vector_only",
            "similarity_top_k": 4,
            "enable_reranker": False,
            "rerank_top_n": 4,
            "rerank_model": "test-reranker",
            "homework_mode": options.homework_mode,
            "assistance_level": options.assistance_level,
        },
    }


def test_answer_question_grounded_status_with_inline_citation(settings_env, monkeypatch):
    settings_env({"LLM_MODEL": "gpt-4o-mini", "GROUNDED_ANSWER_CONTRACT_ENABLED": "true"})
    monkeypatch.setattr(query_service, "build_query_engine", _fake_build_query_engine_cited)

    result = query_service.answer_question("test question", QueryOptions())

    assert result.get("answer_status") == "grounded"
    grounded = result["debug"].get("grounded") or {}
    assert grounded.get("schema_validated") is True
    assert grounded.get("facts_count", 0) >= 1


def test_answer_question_abstain_without_citation(settings_env, monkeypatch):
    class _UncitedResponse(_FakeResponse):
        def __str__(self) -> str:
            return "Confident uncited answer."

    class _UncitedEngine(_FakeEngine):
        def query(self, question: str):
            return _UncitedResponse()

    def _uncited_engine(question: str, options: QueryOptions, **kwargs):
        payload = _fake_build_query_engine(question, options, **kwargs)
        payload["engine"] = _UncitedEngine()
        return payload

    settings_env({"LLM_MODEL": "gpt-4o-mini", "GROUNDED_ANSWER_CONTRACT_ENABLED": "true"})
    monkeypatch.setattr(query_service, "build_query_engine", _uncited_engine)

    result = query_service.answer_question("test question", QueryOptions())

    assert result.get("answer_status") == "abstain"
    grounded = result["debug"].get("grounded") or {}
    assert grounded.get("abstain_reason_code") == "insufficient_provenance"
    assert result["debug"]["guardrails"]["code"] == "grounded_abstain"


def test_answer_question_grounded_contract_disabled(settings_env, monkeypatch):
    class _UncitedResponse(_FakeResponse):
        def __str__(self) -> str:
            return "Legacy uncited answer."

    class _UncitedEngine(_FakeEngine):
        def query(self, question: str):
            return _UncitedResponse()

    def _uncited_engine(question: str, options: QueryOptions, **kwargs):
        payload = _fake_build_query_engine(question, options, **kwargs)
        payload["engine"] = _UncitedEngine()
        return payload

    settings_env(
        {
            "LLM_MODEL": "gpt-4o-mini",
            "GROUNDED_ANSWER_CONTRACT_ENABLED": "false",
        }
    )
    monkeypatch.setattr(query_service, "build_query_engine", _uncited_engine)

    result = query_service.answer_question("test question", QueryOptions())

    assert "answer_status" not in result
    assert "grounded" not in (result.get("debug") or {})
