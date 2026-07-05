import app.ingestion_metadata as ingestion_metadata


def test_enrich_document_metadata_with_cost_returns_usage(monkeypatch):
    class _FakeResponse:
        text = '{"topic": "Retrieval", "key_concepts": ["BM25", "RAG"], "doc_type": "lecture", "difficulty": "beginner"}'
        usage = {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150}

    class _FakeLLM:
        model = "gpt-5-mini"

        @staticmethod
        def complete(prompt):
            return _FakeResponse()

    monkeypatch.setattr(ingestion_metadata, "get_ingestion_llm", lambda **kwargs: _FakeLLM())

    enrichment, cost = ingestion_metadata.enrich_document_metadata_with_cost("Test document")

    assert enrichment is not None
    assert enrichment.topic == "Retrieval"
    assert cost is not None
    assert cost.token_usage["total_tokens"] == 150
    assert cost.estimated_cost_usd is not None


def test_build_document_summary_with_cost_returns_usage(monkeypatch):
    class _FakeResponse:
        text = "Short summary"
        usage = {"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100}

    class _FakeLLM:
        model = "gpt-5-mini"

        @staticmethod
        def complete(prompt):
            return _FakeResponse()

    monkeypatch.setattr(ingestion_metadata, "get_ingestion_llm", lambda **kwargs: _FakeLLM())

    summary, cost = ingestion_metadata.build_document_summary_with_cost("Test document")

    assert summary == "Short summary"
    assert cost is not None
    assert cost.token_usage["total_tokens"] == 100
    assert cost.estimated_cost_usd is not None
