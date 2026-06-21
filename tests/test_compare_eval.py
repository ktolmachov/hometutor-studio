import app.compare_eval as compare_eval
import app.eval_ragas_backend as eval_ragas_backend
import app.provider as provider


def test_build_evaluators_uses_configured_api_base(monkeypatch):
    """Проверяет, что evaluators собираются через провайдер с api_base из настроек."""
    captured = {}

    class _FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    fake_settings = type("FakeSettings", (), {})()
    fake_settings.openai_api_key = "test-key"
    fake_settings.llm_api_base = "https://llm.example.invalid/v1"
    fake_settings.openai_api_base = "https://example.invalid/v1"
    fake_settings.embed_api_base_resolved = "https://example.invalid/v1"
    fake_settings.llm_model = "qwen/qwen3.6-27b"
    fake_settings.embed_model = "text-embedding-3-small"
    fake_settings.eval_judge_llm = None

    monkeypatch.setattr(provider, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(provider, "OpenAI", _FakeOpenAI)
    monkeypatch.setattr(compare_eval, "AnswerRelevancyEvaluator", lambda llm: ("answer", llm))
    monkeypatch.setattr(compare_eval, "ContextRelevancyEvaluator", lambda llm: ("context", llm))
    monkeypatch.setattr(compare_eval, "FaithfulnessEvaluator", lambda llm: ("faithfulness", llm))

    compare_eval._build_evaluators()

    assert captured.get("api_base") == "https://llm.example.invalid/v1"


def test_compare_two_configs_surfaces_answer_correctness_diff(monkeypatch):
    options = type(
        "Options",
        (),
        {"folder": None, "folder_rel": None, "file_name": None, "relative_path": None},
    )()
    results = iter(
        [
            {
                "answer": "alpha beta",
                "sources": [],
                "profile": {
                    "retrieval_ms": 1.0,
                    "rerank_ms": 1.0,
                    "synthesis_ms": 1.0,
                    "total_ms": 3.0,
                    "retrieved_nodes_count": 1,
                    "postprocessed_nodes_count": 1,
                },
            },
            {
                "answer": "unrelated",
                "sources": [],
                "profile": {
                    "retrieval_ms": 1.0,
                    "rerank_ms": 1.0,
                    "synthesis_ms": 1.0,
                    "total_ms": 3.0,
                    "retrieved_nodes_count": 1,
                    "postprocessed_nodes_count": 1,
                },
            },
        ]
    )
    empty_quality = {
        "metrics": {
            "answer_relevancy": None,
            "context_relevancy": None,
            "faithfulness": None,
        },
        "feedback": {},
    }
    monkeypatch.setattr(compare_eval, "_build_evaluators", lambda: {})
    monkeypatch.setattr(compare_eval, "run_profiled_query", lambda *_args: next(results))
    monkeypatch.setattr(compare_eval, "_evaluate_result", lambda *_args: {**empty_quality, "metrics": dict(empty_quality["metrics"])})

    output = compare_eval.compare_two_configs_with_eval(
        "question", options, object(), object(), reference_answer="alpha beta"
    )

    quality = output["diff"]["quality"]
    assert quality["answer_correctness_diff"] == 1.0
    assert quality["context_precision_diff"] is None


def test_ragas_backend_does_not_import_when_disabled(monkeypatch):
    monkeypatch.setattr(
        eval_ragas_backend,
        "get_settings",
        lambda: type("Settings", (), {"enable_ragas_metrics": False})(),
    )
    monkeypatch.setattr(
        eval_ragas_backend,
        "import_module",
        lambda _name: (_ for _ in ()).throw(AssertionError("unexpected import")),
    )

    assert eval_ragas_backend.run_ragas_cross_check([]) == {
        "status": "disabled",
        "result": None,
    }


def test_ragas_backend_gracefully_handles_missing_package(monkeypatch):
    monkeypatch.setattr(
        eval_ragas_backend,
        "get_settings",
        lambda: type("Settings", (), {"enable_ragas_metrics": True})(),
    )
    monkeypatch.setattr(
        eval_ragas_backend,
        "import_module",
        lambda _name: (_ for _ in ()).throw(ImportError("not installed")),
    )

    assert eval_ragas_backend.run_ragas_cross_check([]) == {
        "status": "unavailable",
        "result": None,
    }
