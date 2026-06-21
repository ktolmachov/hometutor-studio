"""Контракты app.models: session semantics вынесены выше model cache_key."""

from app.models import Message, QueryClientParams, QueryContext, QueryExecutionPlan, QueryOptions


def test_query_options_cache_key_stays_transport_only_for_session_fields():
    base = QueryOptions(folder="a")
    with_session = QueryOptions(folder="a", session_id="s1", query_mode="tutor")
    assert base.cache_key() == with_session.cache_key()


def test_message_defaults():
    m = Message(role="user", content="hi")
    assert m.role == "user"
    assert m.content == "hi"
    assert m.metadata == {}
    assert len(m.timestamp) >= 10


def test_query_client_params_defaults():
    p = QueryClientParams()
    assert p.session_id is None
    assert p.query_mode is None
    assert p.temperature == 0.7
    assert p.max_sources == 8


def test_query_context_keeps_condensed_question_separate_from_rewritten_query():
    ctx = QueryContext(
        original_question="original question",
        condensed_question="condensed follow-up",
        rewritten_query="rewritten search query",
    )

    assert ctx.condensed_question == "condensed follow-up"
    assert ctx.rewritten_query == "rewritten search query"
    assert ctx.effective_query == "condensed follow-up"
    assert ctx.effective_query_source == "condensed"


def test_query_execution_plan_to_pipeline_params():
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
        doc_top_k=5,
    )

    assert plan.to_pipeline_params() == {
        "profile": "fast",
        "query_type": "qa",
        "prompt_key": "qa",
        "retrieval_mode": "vector_only",
        "enable_reranker": False,
        "similarity_top_k": 4,
        "rerank_top_n": 4,
        "rerank_model": "test-reranker",
        "split_strategy": "sentence_window",
        "window_size": 2,
        "doc_top_k": 5,
        "homework_mode": False,
        "assistance_level": None,
        "query_engine_cache_policy": "shared",
        "faq_cache_eligible": True,
        "faq_cache_skip_reason": None,
    }
