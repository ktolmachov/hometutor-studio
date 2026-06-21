import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from starlette.background import BackgroundTasks

import app.metrics as metrics
from app import async_quality_judge


def test_schedule_skips_when_disabled(monkeypatch):
    monkeypatch.setattr(
        async_quality_judge,
        "get_settings",
        lambda: SimpleNamespace(
            enable_async_quality_judge=False,
            async_quality_judge_sample_rate=1.0,
            openai_api_key="x",
        ),
    )
    bt = BackgroundTasks()
    async_quality_judge.schedule_async_quality_judge_if_sampled(
        background_tasks=bt,
        request_id="r1",
        question="q",
        answer="a",
        sources=[{"text": "c"}],
        query_type="qa",
    )
    assert bt.tasks == []


def test_schedule_skips_without_context(monkeypatch):
    monkeypatch.setattr(
        async_quality_judge,
        "get_settings",
        lambda: SimpleNamespace(
            enable_async_quality_judge=True,
            async_quality_judge_sample_rate=1.0,
            openai_api_key="x",
        ),
    )
    monkeypatch.setattr(async_quality_judge.random, "random", lambda: 0.0)
    bt = BackgroundTasks()
    async_quality_judge.schedule_async_quality_judge_if_sampled(
        background_tasks=bt,
        request_id="r1",
        question="q",
        answer="a",
        sources=[{"text": ""}],
        query_type="qa",
    )
    assert bt.tasks == []


def test_schedule_adds_background_task_when_sampled(monkeypatch):
    monkeypatch.setattr(
        async_quality_judge,
        "get_settings",
        lambda: SimpleNamespace(
            enable_async_quality_judge=True,
            async_quality_judge_sample_rate=1.0,
            openai_api_key="x",
        ),
    )
    monkeypatch.setattr(async_quality_judge.random, "random", lambda: 0.0)
    bt = BackgroundTasks()
    async_quality_judge.schedule_async_quality_judge_if_sampled(
        background_tasks=bt,
        request_id="r1",
        question="q",
        answer="a",
        sources=[{"text": "context body"}],
        query_type="qa",
    )
    assert len(bt.tasks) == 1


def test_run_task_records_scores(tmp_path, monkeypatch):
    monkeypatch.setattr(metrics, "METRICS_STORE_PATH", tmp_path / "m.jsonl")

    def _fake_eval(**kwargs):
        m = MagicMock()
        m.score = 0.88
        m.feedback = None
        return m

    ev = MagicMock()
    ev.evaluate = _fake_eval

    monkeypatch.setattr(
        async_quality_judge,
        "build_evaluators",
        lambda: {
            "answer_relevancy": ev,
            "context_relevancy": ev,
            "faithfulness": ev,
        },
    )
    monkeypatch.setattr(
        async_quality_judge,
        "get_settings",
        lambda: SimpleNamespace(eval_judge_llm="judge-m", llm_model="gpt-4o-mini"),
    )

    async_quality_judge.run_async_quality_judge_task(
        "r99",
        "question?",
        "answer text",
        [{"text": "supporting passage"}],
        "qa",
    )

    lines = (tmp_path / "m.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["event_type"] == "quality_judge"
    assert row["request_id"] == "r99"
    assert row["query_type"] == "qa"
    assert row["model"] == "judge-m"
    assert row["scores"]["faithfulness"] == 0.88
    assert row.get("error") is None
