"""Unit tests for composable pipeline steps (Iteration 12)."""

import app.pipeline_steps as steps
from app.models import QueryContext, QueryOptions


# ---------------------------------------------------------------------------
# run_step_safe
# ---------------------------------------------------------------------------

def test_run_step_safe_records_timing():
    def ok_step(ctx):
        ctx.query_type = "keyword"
        return ctx

    ctx = QueryContext(original_question="test")
    ctx = steps.run_step_safe(ok_step, ctx)

    assert ctx.query_type == "keyword"
    assert "ok_step_ms" in ctx.trace
    assert ctx.trace["ok_step_ms"] >= 0


def test_run_step_safe_uses_fallback_on_error():
    def bad_step(ctx):
        raise RuntimeError("boom")

    def fallback(ctx):
        ctx.query_type = "qa"
        ctx.classify_method = "fallback"
        return ctx

    ctx = QueryContext(original_question="test")
    ctx = steps.run_step_safe(bad_step, ctx, fallback_fn=fallback)

    assert ctx.query_type == "qa"
    assert ctx.classify_method == "fallback"
    assert "bad_step_error" in ctx.trace
    assert ctx.trace["bad_step_error"] == "boom"
    assert "bad_step_ms" in ctx.trace


def test_run_step_safe_passthrough_without_fallback():
    def bad_step(ctx):
        raise ValueError("oops")

    ctx = QueryContext(original_question="test", query_type="keyword")
    ctx = steps.run_step_safe(bad_step, ctx)

    assert ctx.query_type == "keyword"
    assert "bad_step_error" in ctx.trace


def test_run_step_safe_traces_failed_fallback_without_raising():
    def bad_step(ctx):
        raise RuntimeError("step down")

    def bad_fallback(ctx):
        raise RuntimeError("fallback down")

    ctx = QueryContext(original_question="test", query_type="keyword")
    ctx = steps.run_step_safe(bad_step, ctx, fallback_fn=bad_fallback)

    assert ctx.query_type == "keyword"
    assert ctx.trace["bad_step_error"] == "step down"
    assert ctx.trace["bad_step_fallback_error"] == "fallback down"
    assert ctx.trace["pipeline_step_failures"][-1]["step"] == "bad_step_fallback"


# ---------------------------------------------------------------------------
# classify_step — heuristic mode (ENABLE_CLASSIFIER=False)
# ---------------------------------------------------------------------------

def test_classify_step_keyword_heuristic(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings(enable_classifier=False))

    ctx = QueryContext(original_question="RFC-2024-003")
    ctx = steps.classify_step(ctx)

    assert ctx.query_type == "keyword"
    assert ctx.classify_method == "heuristic"
    assert ctx.classify_confidence == 1.0
    assert ctx.prompt_key == "keyword"
    assert ctx.retrieval_strategy == "bm25_only"


def test_classify_step_qa_heuristic(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings(enable_classifier=False))

    ctx = QueryContext(original_question="What is prompt injection?")
    ctx = steps.classify_step(ctx)

    assert ctx.query_type == "qa"
    assert ctx.classify_method == "heuristic"
    assert ctx.prompt_key == "qa"
    assert ctx.retrieval_strategy == "default"


def test_classify_step_overview_heuristic(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings(enable_classifier=False))

    ctx = QueryContext(original_question="Дай краткий обзор темы машинного обучения")
    ctx = steps.classify_step(ctx)

    assert ctx.query_type == "overview"
    assert ctx.prompt_key == "overview"
    assert ctx.retrieval_strategy == "doc_then_chunk"


# ---------------------------------------------------------------------------
# classify_step — LLM mode (ENABLE_CLASSIFIER=True)
# ---------------------------------------------------------------------------

def test_classify_step_llm_keyword_skips_llm(monkeypatch):
    """Keyword detected by heuristic => no LLM call even when classifier enabled."""
    monkeypatch.setattr(steps, "get_settings", lambda: _settings(enable_classifier=True))

    ctx = QueryContext(original_question="OWASP")
    ctx = steps.classify_step(ctx)

    assert ctx.query_type == "keyword"
    assert ctx.classify_method == "heuristic"


def test_classify_step_llm_returns_overview(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings(enable_classifier=True))

    class _FakeResponse:
        text = '{"type": "overview", "confidence": 0.85}'
        usage = {"prompt_tokens": 120, "completion_tokens": 12, "total_tokens": 132}

    monkeypatch.setattr(
        "app.provider.get_classifier_llm",
        lambda: type("LLM", (), {"complete": staticmethod(lambda prompt: _FakeResponse())})(),
    )

    ctx = QueryContext(original_question="Какие основные подходы к безопасности существуют?")
    ctx = steps.classify_step(ctx)

    assert ctx.query_type == "overview"
    assert ctx.classify_confidence == 0.85
    assert ctx.classify_method == "llm"
    assert ctx.prompt_key == "overview"
    assert ctx.retrieval_strategy == "doc_then_chunk"
    assert ctx.trace["classify_usage"]["total_tokens"] == 132
    assert ctx.trace["classify_estimated_cost_usd"] is not None


def test_classify_step_llm_returns_synthesis_uses_doc_then_chunk(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings(enable_classifier=True))

    class _FakeResponse:
        text = '{"type": "synthesis", "confidence": 0.91}'

    monkeypatch.setattr(
        "app.provider.get_classifier_llm",
        lambda: type("LLM", (), {"complete": staticmethod(lambda prompt: _FakeResponse())})(),
    )

    ctx = QueryContext(original_question="Собери конспект по теме retrieval")
    ctx = steps.classify_step(ctx)

    assert ctx.query_type == "synthesis"
    assert ctx.prompt_key == "synthesis"
    assert ctx.retrieval_strategy == "doc_then_chunk"


def test_classify_step_llm_low_confidence_falls_back_to_qa(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings(enable_classifier=True))

    class _FakeResponse:
        text = '{"type": "synthesis", "confidence": 0.3}'

    monkeypatch.setattr(
        "app.provider.get_classifier_llm",
        lambda: type("LLM", (), {"complete": staticmethod(lambda prompt: _FakeResponse())})(),
    )

    ctx = QueryContext(original_question="Something ambiguous")
    ctx = steps.classify_step(ctx)

    assert ctx.query_type == "qa"
    assert ctx.trace.get("classify_low_confidence_fallback") is True


def test_classify_step_llm_invalid_json_falls_back(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings(enable_classifier=True))

    class _FakeResponse:
        text = "not json at all"

    monkeypatch.setattr(
        "app.provider.get_classifier_llm",
        lambda: type("LLM", (), {"complete": staticmethod(lambda prompt: _FakeResponse())})(),
    )

    ctx = QueryContext(original_question="What is RAG?")
    ctx = steps.classify_step(ctx)

    assert ctx.query_type == "qa"
    assert ctx.classify_confidence < 0.6


# ---------------------------------------------------------------------------
# rewrite_step
# ---------------------------------------------------------------------------

def test_rewrite_step_disabled(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings(enable_rewrite=False))

    ctx = QueryContext(original_question="test question")
    ctx = steps.rewrite_step(ctx)

    assert ctx.rewritten_query is None
    assert ctx.trace["rewrite_enabled"] is False
    assert ctx.effective_query == "test question"


def test_rewrite_step_enabled(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings(enable_rewrite=True))

    class _FakeResponse:
        text = "What are the main principles of prompt injection defense?"
        usage = {"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100}

    monkeypatch.setattr(
        "app.provider.get_rewrite_llm",
        lambda: type("LLM", (), {"complete": staticmethod(lambda prompt: _FakeResponse())})(),
    )

    ctx = QueryContext(original_question="prompt injection defense")
    ctx = steps.rewrite_step(ctx)

    assert ctx.rewritten_query == "What are the main principles of prompt injection defense?"
    assert ctx.trace["rewrite_enabled"] is True
    assert ctx.trace["rewritten_question"] == ctx.rewritten_query
    assert ctx.effective_query == ctx.rewritten_query
    assert ctx.trace["rewrite_usage"]["total_tokens"] == 100
    assert ctx.trace["rewrite_estimated_cost_usd"] is not None


def test_rewrite_step_generates_subquestions_for_overview(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings(enable_rewrite=True))

    class _FakeResponse:
        def __init__(self, text):
            self.text = text

    class _FakeLLM:
        def __init__(self):
            self.calls = 0

        def complete(self, prompt):
            self.calls += 1
            if self.calls == 1:
                return _FakeResponse("overview retrieval question")
            return _FakeResponse('{"subquestions":["Что такое retrieval?","Как работает reranking?","Что такое retrieval?"]}')

    monkeypatch.setattr("app.provider.get_rewrite_llm", lambda: _FakeLLM())

    ctx = QueryContext(original_question="Дай обзор по retrieval", query_type="overview")
    ctx = steps.rewrite_step(ctx)

    assert ctx.rewritten_query == "overview retrieval question"
    assert ctx.subquestions == ["Что такое retrieval?", "Как работает reranking?"]
    assert ctx.trace["subquestions"] == ctx.subquestions


def test_rewrite_step_records_subquestion_error(monkeypatch):
    monkeypatch.setattr(steps, "get_settings", lambda: _settings(enable_rewrite=True))

    class _FakeResponse:
        def __init__(self, text):
            self.text = text

    class _FakeLLM:
        def __init__(self):
            self.calls = 0

        def complete(self, prompt):
            self.calls += 1
            if self.calls == 1:
                return _FakeResponse("overview retrieval question")
            raise RuntimeError("subquestions down")

    monkeypatch.setattr("app.provider.get_rewrite_llm", lambda: _FakeLLM())

    ctx = QueryContext(original_question="Дай обзор по retrieval", query_type="overview")
    ctx = steps.rewrite_step(ctx)

    assert ctx.rewritten_query == "overview retrieval question"
    assert ctx.subquestions == []
    assert ctx.trace["subquestions_error"] == "subquestions down"


def test_rewrite_step_same_text_no_rewrite(monkeypatch):
    """If LLM returns same text, rewritten_query stays None."""
    monkeypatch.setattr(steps, "get_settings", lambda: _settings(enable_rewrite=True))

    class _FakeResponse:
        text = "exact same question"

    monkeypatch.setattr(
        "app.provider.get_rewrite_llm",
        lambda: type("LLM", (), {"complete": staticmethod(lambda prompt: _FakeResponse())})(),
    )

    ctx = QueryContext(original_question="exact same question")
    ctx = steps.rewrite_step(ctx)

    assert ctx.rewritten_query is None
    assert ctx.effective_query == "exact same question"


# ---------------------------------------------------------------------------
# _parse_classifier_response
# ---------------------------------------------------------------------------

def test_parse_classifier_response_valid_json():
    result = steps._parse_classifier_response('{"type": "qa", "confidence": 0.9}')
    assert result == {"type": "qa", "confidence": 0.9}


def test_parse_classifier_response_markdown_fences():
    result = steps._parse_classifier_response('```json\n{"type": "overview", "confidence": 0.7}\n```')
    assert result == {"type": "overview", "confidence": 0.7}


def test_parse_classifier_response_unknown_type():
    result = steps._parse_classifier_response('{"type": "unknown_type", "confidence": 0.8}')
    assert result["type"] == "qa"
    assert result["confidence"] <= 0.5


def test_parse_classifier_response_garbage():
    result = steps._parse_classifier_response("this is not json")
    assert result["type"] == "qa"
    assert result["confidence"] == 0.3


# ---------------------------------------------------------------------------
# QueryContext.effective_query
# ---------------------------------------------------------------------------

def test_effective_query_uses_rewritten():
    ctx = QueryContext(original_question="original", rewritten_query="rewritten")
    assert ctx.effective_query == "rewritten"
    assert ctx.effective_query_source == "rewritten"


def test_effective_query_falls_back_to_original():
    ctx = QueryContext(original_question="original")
    assert ctx.effective_query == "original"
    assert ctx.effective_query_source == "original"


def test_effective_query_prefers_condensed_over_rewritten():
    ctx = QueryContext(
        original_question="original",
        condensed_question="condensed",
        rewritten_query="rewritten",
    )
    assert ctx.effective_query == "condensed"
    assert ctx.effective_query_source == "condensed"


# ---------------------------------------------------------------------------
# Tutor 19.4 — orchestrator / agent / self-correction steps
# ---------------------------------------------------------------------------


def test_orchestrate_pedagogical_skips_when_not_tutor():
    ctx = QueryContext(original_question="Hi", query_options=QueryOptions(query_mode="qa"))
    ctx.metadata["learner_profile"] = {"mastery_level": "intermediate"}
    ctx = steps.orchestrate_pedagogical_action_step(ctx)
    assert ctx.trace["orchestrate_pedagogical_action_step"] == "skipped_not_tutor"
    assert ctx.trace["tutor_pipeline"][0]["step"] == "orchestrate_pedagogical_action_step"


def test_orchestrate_pedagogical_skips_when_disabled(monkeypatch):
    class _S:
        enable_tutor_pedagogical_orchestrator = False

    monkeypatch.setattr(steps, "get_settings", lambda: _S())
    ctx = QueryContext(original_question="Hi", query_options=QueryOptions(query_mode="tutor"))
    ctx.metadata["learner_profile"] = {"mastery_level": "intermediate"}
    ctx.trace["tutor_pipeline"] = []
    ctx = steps.orchestrate_pedagogical_action_step(ctx)
    assert ctx.trace["orchestrate_pedagogical_action_step"] == "skipped_disabled"
    pipe = ctx.metadata.get("tutor_orchestration_pipeline")
    assert pipe.get("decision_source") == "disabled"
    assert ctx.trace["tutor_pipeline"][0]["status"] == "skipped_disabled"


def test_orchestrate_pedagogical_merges_qa_handoff_context(monkeypatch):
    """US-19.2: metadata['qa_handoff_context'] попадает в tutor_orchestration_pipeline."""
    class _S:
        enable_tutor_pedagogical_orchestrator = False

    monkeypatch.setattr(steps, "get_settings", lambda: _S())
    ctx = QueryContext(original_question="Hi", query_options=QueryOptions(query_mode="tutor"))
    ctx.metadata["learner_profile"] = {"mastery_level": "intermediate"}
    ctx.metadata["qa_handoff_context"] = {
        "topic": "RAG",
        "last_question": "Что это?",
        "answer_summary": "Кратко",
        "confidence": {"level": "high", "label": "Высокая"},
        "sources": [{"file_name": "a.md"}],
    }
    ctx.trace["tutor_pipeline"] = []
    ctx = steps.orchestrate_pedagogical_action_step(ctx)
    qh = ctx.metadata["tutor_orchestration_pipeline"].get("qa_handoff_context")
    assert isinstance(qh, dict)
    assert qh.get("topic_head") == "RAG"
    assert qh.get("has_last_question") is True
    assert qh.get("source_count") == 1
    assert qh.get("confidence_level") == "high"


def test_execute_specialized_agent_step_tutor_trace():
    ctx = QueryContext(
        original_question="Q",
        query_options=QueryOptions(query_mode="tutor"),
        metadata={"orchestrator_selected_agent": "ConceptExplainer"},
    )
    ctx.trace["tutor_pipeline"] = []
    ctx = steps.execute_specialized_agent_step(ctx)
    assert ctx.trace["execute_specialized_agent_step"]["mode"] == "embedded_in_tutor_rag_prompt"
    assert ctx.trace["execute_specialized_agent_step"]["selected_agent"] == "ConceptExplainer"
    assert ctx.metadata["tutor_orchestration_pipeline"]["phase"] == "rag_prepare"


def test_tutor_pipeline_trace_three_steps(monkeypatch):
    class _S:
        enable_tutor_pedagogical_orchestrator = False

    monkeypatch.setattr(steps, "get_settings", lambda: _S())
    ctx = QueryContext(original_question="Hi", query_options=QueryOptions(query_mode="tutor"))
    ctx.metadata["learner_profile"] = {"mastery_level": "intermediate"}
    ctx.trace["tutor_pipeline"] = []
    ctx = steps.orchestrate_pedagogical_action_step(ctx)
    ctx = steps.execute_specialized_agent_step(ctx)
    ctx = steps.self_correction_and_compose_step(ctx)
    assert len(ctx.trace["tutor_pipeline"]) == 3, "Tutor trace must keep exactly 3 canonical pipeline steps"
    assert ctx.metadata["tutor_orchestration_pipeline"]["phase"] == "pre_generate"
    assert ctx.metadata["tutor_orchestration_pipeline"]["decision_source"] == "disabled"


def test_orchestrate_pedagogical_step_exception_applies_rule_fallback(monkeypatch):
    class _S:
        enable_tutor_pedagogical_orchestrator = True

    monkeypatch.setattr(steps, "get_settings", lambda: _S())

    def _boom(**_kwargs):
        raise RuntimeError("llm_down")

    monkeypatch.setattr(
        "app.tutor_orchestrator.invoke_pedagogical_orchestrator_llm",
        _boom,
    )

    ctx = QueryContext(original_question="Q", query_options=QueryOptions(query_mode="tutor"))
    ctx.metadata["learner_profile"] = {"mastery_level": "intermediate", "focus_topic": "x"}
    ctx.trace["tutor_pipeline"] = []
    ctx = steps.orchestrate_pedagogical_action_step(ctx)
    assert "error:" in ctx.trace["orchestrate_pedagogical_action_step"]
    assert ctx.metadata["tutor_orchestration_pipeline"]["decision_source"] == "rule_fallback"
    assert ctx.metadata["orchestrator_trigger_microquiz"] is False
    assert ctx.trace["tutor_pipeline"][-1]["status"] == "error_fallback"


def test_orchestrate_pedagogical_kg_lookup_failure_uses_none(monkeypatch):
    class _S:
        enable_tutor_pedagogical_orchestrator = True

    monkeypatch.setattr(steps, "get_settings", lambda: _S())

    def _kg_boom():
        raise RuntimeError("kg unavailable")

    monkeypatch.setattr("app.knowledge_graph.get_active_knowledge_graph", _kg_boom)
    captured = {}

    def _ok(**kwargs):
        captured["kg"] = kwargs.get("kg")
        return (
            {
                "selected_agent": "ConceptExplainer",
                "parameters": {"depth": "intuitive"},
                "should_trigger_microquiz": False,
                "_fallback": False,
            },
            None,
        )

    monkeypatch.setattr(
        "app.tutor_orchestrator.invoke_pedagogical_orchestrator_llm", _ok
    )

    ctx = QueryContext(original_question="Q", query_options=QueryOptions(query_mode="tutor"))
    ctx.metadata["learner_profile"] = {"mastery_level": "intermediate", "focus_topic": "x"}
    ctx.trace["tutor_pipeline"] = []
    ctx = steps.orchestrate_pedagogical_action_step(ctx)

    assert captured["kg"] is None
    assert ctx.metadata["tutor_orchestration_pipeline"]["decision_source"] == "llm"
    assert ctx.trace["tutor_pipeline"][-1]["status"] == "ok"


def test_orchestrate_step_contract_schema_version(monkeypatch):
    """E6.0: после успешного шага в metadata есть schema_version=1, а в trace — запись шага."""
    from app.tutor_pipeline_contract import SCHEMA_VERSION

    def _ok(**_kw):
        return (
            {
                "selected_agent": "ConceptExplainer",
                "parameters": {"depth": "intuitive"},
                "should_trigger_microquiz": False,
                "_fallback": False,
            },
            None,
        )

    monkeypatch.setattr(
        "app.tutor_orchestrator.invoke_pedagogical_orchestrator_llm", _ok
    )

    class _S:
        enable_tutor_pedagogical_orchestrator = True

    monkeypatch.setattr("app.pipeline_steps.get_settings", lambda: _S())

    ctx = QueryContext(
        original_question="Q", query_options=QueryOptions(query_mode="tutor")
    )
    ctx.metadata["learner_profile"] = {"mastery_level": "intermediate", "focus_topic": "x"}
    ctx = steps.orchestrate_pedagogical_action_step(ctx)

    contract = ctx.metadata.get("tutor_orchestration_pipeline")
    assert isinstance(contract, dict)
    assert contract["schema_version"] == SCHEMA_VERSION
    assert contract["decision_source"] == "llm"
    assert contract["selected_agent"] == "ConceptExplainer"

    pipeline_trace = ctx.trace.get("tutor_pipeline")
    assert isinstance(pipeline_trace, list) and pipeline_trace
    assert pipeline_trace[-1]["step"] == "orchestrate_pedagogical_action_step"
    assert pipeline_trace[-1]["status"] == "ok"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeSettings:
    def __init__(self, **kwargs):
        self.enable_classifier = kwargs.get("enable_classifier", False)
        self.enable_rewrite = kwargs.get("enable_rewrite", False)
        self.enable_self_correction = False
        self.llm_model = "gpt-5-mini"
        self.rewrite_model = kwargs.get("rewrite_model", None)
        self.classifier_model = kwargs.get("classifier_model", None)


def _settings(**kwargs):
    return _FakeSettings(**kwargs)
