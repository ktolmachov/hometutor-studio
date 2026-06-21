import json

import app.history_service as history_service


def test_append_history_entry_writes_jsonl(tmp_path, monkeypatch):
    history_path = tmp_path / "history.jsonl"
    monkeypatch.setattr(history_service, "HISTORY_PATH", history_path)
    monkeypatch.setattr(history_service, "_index_version", lambda: "home_rag:2026-03-16T00:00:00+00:00")

    entry = history_service.append_history_entry(
        request_id="req-1",
        question="What is retrieval?",
        result={
            "answer": "Retrieval is search",
            "sources": [{"relative_path": "doc.md"}],
            "confidence": {"level": "medium"},
            "debug": {"query_type": "qa"},
        },
    )

    assert entry["request_id"] == "req-1"
    assert history_path.exists()
    lines = history_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["question"] == "What is retrieval?"
    assert payload["index_version"] == "home_rag:2026-03-16T00:00:00+00:00"


def test_get_history_filters_and_limits(tmp_path, monkeypatch):
    history_path = tmp_path / "history.jsonl"
    monkeypatch.setattr(history_service, "HISTORY_PATH", history_path)
    history_path.write_text(
        "\n".join(
            [
                json.dumps({"timestamp": "2026-03-16T10:00:00+00:00", "question": "hello retrieval", "answer": "a"}),
                json.dumps({"timestamp": "2026-03-16T11:00:00+00:00", "question": "security", "answer": "b"}),
                json.dumps({"timestamp": "2026-03-16T12:00:00+00:00", "question": "hello history", "answer": "c"}),
            ]
        ),
        encoding="utf-8",
    )

    result = history_service.get_history(q="hello", limit=1)

    assert result["total"] == 2
    assert len(result["items"]) == 1
    assert result["items"][0]["question"] == "hello history"


def test_get_history_filters_by_date_range(tmp_path, monkeypatch):
    history_path = tmp_path / "history.jsonl"
    monkeypatch.setattr(history_service, "HISTORY_PATH", history_path)
    history_path.write_text(
        "\n".join(
            [
                json.dumps({"timestamp": "2026-03-15T12:00:00+00:00", "question": "early", "answer": "a"}),
                json.dumps({"timestamp": "2026-03-16T12:00:00+00:00", "question": "mid", "answer": "b"}),
                json.dumps({"timestamp": "2026-03-17T12:00:00+00:00", "question": "late", "answer": "c"}),
            ]
        ),
        encoding="utf-8",
    )

    result = history_service.get_history(since="2026-03-16", until="2026-03-16", limit=10)

    assert result["total"] == 1
    assert result["items"][0]["question"] == "mid"


def test_get_history_filters_by_topic_path(tmp_path, monkeypatch):
    history_path = tmp_path / "history.jsonl"
    monkeypatch.setattr(history_service, "HISTORY_PATH", history_path)
    history_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "timestamp": "2026-03-16T10:00:00+00:00",
                        "question": "q1",
                        "answer": "a",
                        "sources": [{"relative_path": "lectures/foo.md"}],
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-03-16T11:00:00+00:00",
                        "question": "q2",
                        "answer": "b",
                        "sources": [{"relative_path": "other/bar.md"}],
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    result = history_service.get_history(topic="lectures", limit=10)

    assert result["total"] == 1
    assert result["items"][0]["question"] == "q1"


def test_get_pipeline_trace_filters_by_request_id(tmp_path, monkeypatch):
    history_path = tmp_path / "history.jsonl"
    monkeypatch.setattr(history_service, "HISTORY_PATH", history_path)
    history_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "request_id": "r1",
                        "timestamp": "2026-03-16T10:00:00+00:00",
                        "debug": {"query_type": "qa", "pipeline_trace": {"classify_step_ms": 10.0}},
                    }
                ),
                json.dumps(
                    {
                        "request_id": "r2",
                        "timestamp": "2026-03-16T11:00:00+00:00",
                        "debug": {"query_type": "overview", "pipeline_trace": {"rewrite_step_ms": 20.0}},
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    result = history_service.get_pipeline_trace(request_id="r2", limit=5)

    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["request_id"] == "r2"
    assert result["items"][0]["query_type"] == "overview"
    assert result["items"][0]["pipeline_trace"]["rewrite_step_ms"] == 20.0
