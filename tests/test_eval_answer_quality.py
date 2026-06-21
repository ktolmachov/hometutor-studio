from __future__ import annotations

import json
import sys
from pathlib import Path

from tests.eval import run_eval as answer_eval


def _write_jsonl(path: Path, cases: list[dict]) -> None:
    payload = "\n".join(json.dumps(case, ensure_ascii=False) for case in cases)
    path.write_text(payload + "\n", encoding="utf-8")


def _write_thresholds(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "thresholds": {
                    "source_precision_at_3": 0.6,
                    "answer_groundedness": 2.0,
                    "latency_p95_sec": 10.0,
                    "tutor_coherence": 1.5,
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_source_keys_match_file_name_and_page():
    source = {
        "file_name": "Alpha.md",
        "relative_path": "docs/Alpha.md",
        "page": "12",
    }

    keys = answer_eval._source_keys(source)

    assert "docs/alpha.md" in keys
    assert "alpha.md" in keys
    assert "docs/alpha.md::12" in keys


def test_run_eval_mock_mode_builds_report(tmp_path):
    dataset = tmp_path / "dataset.jsonl"
    thresholds = tmp_path / "thresholds.json"
    _write_jsonl(
        dataset,
        [
            {
                "id": "eqe001",
                "question": "Что такое RAG?",
                "expected_sources": ["alpha_rag_intro.md"],
                "expected_concepts": ["rag"],
                "difficulty": "easy",
                "tags": ["factual"],
            },
            {
                "id": "eqe002",
                "question": "Какая завтра погода?",
                "expected_sources": [],
                "expected_concepts": ["out-of-corpus"],
                "difficulty": "easy",
                "tags": ["out-of-corpus"],
            },
        ],
    )
    _write_thresholds(thresholds)

    report, rc = answer_eval.run_eval(
        dataset_path=dataset,
        thresholds_path=thresholds,
        mock=True,
        quiet=True,
    )

    assert rc == 0
    assert report["mode"] == "mock"
    assert report["judge_mode"] == "skipped"
    assert report["summary"]["cases_total"] == 2
    assert report["summary"]["source_precision_at_3"] == 1.0
    assert report["summary"]["answer_groundedness"] is None
    assert report["summary"]["out_of_corpus_graceful_rate"] == 1.0
    assert report["cases"][0]["retrieved_sources"] == ["alpha_rag_intro.md", "alpha_rag_intro.md", "alpha_rag_intro.md"]
    assert report["cases"][0]["retrieved_sources_top3"] == report["cases"][0]["retrieved_sources"]


def test_run_eval_sets_tutor_query_mode_from_tags(tmp_path):
    dataset = tmp_path / "dataset.jsonl"
    thresholds = tmp_path / "thresholds.json"
    _write_jsonl(
        dataset,
        [
            {
                "id": "eqe001",
                "question": "Объясни тему как тьютор",
                "expected_sources": ["gamma_hybrid.md"],
                "expected_concepts": ["hybrid"],
                "difficulty": "medium",
                "tags": ["tutor-mode"],
            }
        ],
    )
    _write_thresholds(thresholds)
    seen_bodies: list[dict] = []

    def _transport(body: dict, case: dict) -> tuple[int, dict]:
        seen_bodies.append(body)
        return 200, {
            "answer": "Tutor answer",
            "sources": [
                {"file_name": "gamma_hybrid.md", "relative_path": "gamma_hybrid.md", "text": "ctx 1"},
                {"file_name": "gamma_hybrid.md", "relative_path": "gamma_hybrid.md", "text": "ctx 2"},
                {"file_name": "gamma_hybrid.md", "relative_path": "gamma_hybrid.md", "text": "ctx 3"},
            ],
            "debug": {"total_answer_ms": 120.0, "query_type": "tutor"},
            "tutor": {"teaching": {"summary": "Tutor answer"}},
        }

    report, rc = answer_eval.run_eval(
        dataset_path=dataset,
        thresholds_path=thresholds,
        mock=True,
        quiet=True,
        transport=_transport,
    )

    assert rc == 0
    assert seen_bodies[0]["query_mode"] == "tutor"
    assert report["cases"][0]["query_mode"] == "tutor"


def test_run_eval_live_scales_judge_scores(tmp_path, monkeypatch):
    dataset = tmp_path / "dataset.jsonl"
    thresholds = tmp_path / "thresholds.json"
    _write_jsonl(
        dataset,
        [
            {
                "id": "eqe001",
                "question": "Объясни тему как тьютор",
                "expected_sources": ["gamma_hybrid.md"],
                "expected_concepts": ["hybrid"],
                "difficulty": "medium",
                "tags": ["tutor-mode"],
            }
        ],
    )
    _write_thresholds(thresholds)

    class _Result:
        def __init__(self, score: float):
            self.score = score

    class _Evaluator:
        def __init__(self, score: float):
            self._score = score

        def evaluate(self, **kwargs):
            return _Result(self._score)

    monkeypatch.setattr(
        "app.eval_service.build_evaluators",
        lambda: {
            "faithfulness": _Evaluator(0.8),
            "answer_relevancy": _Evaluator(0.9),
        },
    )

    def _transport(body: dict, case: dict) -> tuple[int, dict]:
        return 200, {
            "answer": "Tutor answer",
            "sources": [
                {"file_name": "gamma_hybrid.md", "relative_path": "gamma_hybrid.md", "text": "ctx 1"},
                {"file_name": "gamma_hybrid.md", "relative_path": "gamma_hybrid.md", "text": "ctx 2"},
                {"file_name": "gamma_hybrid.md", "relative_path": "gamma_hybrid.md", "text": "ctx 3"},
            ],
            "debug": {"total_answer_ms": 100.0, "query_type": "tutor"},
        }

    report, rc = answer_eval.run_eval(
        dataset_path=dataset,
        thresholds_path=thresholds,
        mock=False,
        quiet=True,
        transport=_transport,
    )

    assert rc == 0
    assert report["judge_mode"] == "llamaindex_evaluators"
    assert report["cases"][0]["answer_groundedness"] == 2.4
    assert report["cases"][0]["tutor_coherence"] == 1.8


def test_main_blocks_writing_mock_to_baseline(tmp_path, monkeypatch):
    report_path = tmp_path / "baseline.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_eval.py",
            "--mock",
            "--quiet",
            "--report-json",
            str(report_path),
        ],
    )

    rc = answer_eval.main()

    assert rc == 1
    assert not report_path.exists(), "baseline.json must NOT be written when blocking mock write"
