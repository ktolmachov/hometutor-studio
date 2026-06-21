import app.pipeline_profiler as pipeline_profiler
from app.models import QueryOptions


def test_run_profiled_query_uses_shared_prompt(monkeypatch):
    captured = {}

    class _FakeRetriever:
        def retrieve(self, query_bundle):
            return []

    class _FakeIndex:
        def as_retriever(self, **kwargs):
            return _FakeRetriever()

    class _FakeSynthesizer:
        def synthesize(self, query, nodes):
            return "ok"

    monkeypatch.setattr(
        pipeline_profiler,
        "get_base_services",
        lambda: {"index": _FakeIndex(), "llm": object(), "quiz_llm": object(), "collection": object()},
    )
    # Зафиксировать режим vector_only, чтобы profiler не пытался строить hybrid-retriever
    monkeypatch.setattr(
        pipeline_profiler,
        "resolve_pipeline_params",
        lambda overrides=None: {
            "profile": "fast",
            "retrieval_mode": "vector_only",
            "similarity_top_k": 4,
            "enable_reranker": False,
            "rerank_top_n": 4,
            "rerank_model": None,
            "split_strategy": "sentence_window",
            "window_size": 2,
        },
    )
    monkeypatch.setattr(pipeline_profiler, "build_postprocessors", lambda resolved: [])

    def fake_get_response_synthesizer(**kwargs):
        captured.update(kwargs)
        return _FakeSynthesizer()

    monkeypatch.setattr(
        pipeline_profiler,
        "get_response_synthesizer",
        fake_get_response_synthesizer,
    )

    result = pipeline_profiler.run_profiled_query("test", QueryOptions())

    assert result["answer"] == "ok"
    assert captured["text_qa_template"] == pipeline_profiler.QA_PROMPT
