"""E9.6 Observable loop & ingest feedback — узкие unit-тесты без live LLM."""
from __future__ import annotations

from app.ingestion import build_ingest_run_summary
from app.ui.adaptive_plan_card import adaptive_plan_progress_teaser_caption
from app.ui.answer_helpers import answer_latency_bucket_label_ru, slow_answer_scope_hint_ru
from app.ui.debug_panel import graph_expansion_trust_caption_ru
from app.ui.tutor_mastery_forecast_panel import tutor_orchestration_decision_one_liner


def test_build_ingest_run_summary_partial_line():
    s = build_ingest_run_summary(
        run_kind="partial",
        unique_documents=10,
        source_fragments=12,
        nodes_count=400,
        partial_rebuilt_docs=2,
        partial_unchanged_docs=8,
    )
    assert s["run_kind"] == "partial"
    line = str(s["summary_line"])
    assert line.startswith("INGEST_SUMMARY run_kind=partial")
    assert "rebuilt_docs=2" in line
    assert "unchanged_docs=8" in line
    assert "Частичная переиндексация" in str(s["human_ru"])


def test_build_ingest_run_summary_full_line():
    s = build_ingest_run_summary(
        run_kind="full",
        unique_documents=5,
        source_fragments=7,
        nodes_count=120,
    )
    assert "INGEST_SUMMARY run_kind=full" in str(s["summary_line"])
    assert "Полная переиндексация" in str(s["human_ru"])


def test_build_ingest_run_summary_noop_line():
    s = build_ingest_run_summary(
        run_kind="noop",
        unique_documents=5,
        source_fragments=7,
        nodes_count=120,
    )
    assert s["run_kind"] == "noop"
    assert "INGEST_SUMMARY run_kind=noop" in str(s["summary_line"])
    assert "Индекс уже актуален" in str(s["human_ru"])


def test_slow_answer_bucket_and_hint():
    assert answer_latency_bucket_label_ru(100.0) == "быстро"
    assert answer_latency_bucket_label_ru(5000.0) == "нормально"
    assert answer_latency_bucket_label_ru(9000.0) == "долго"
    assert "сузьте область" in slow_answer_scope_hint_ru().lower()


def test_tutor_orchestration_decision_one_liner():
    snap = {
        "tutor_orchestration_pipeline": {
            "phase": "pedagogical_route",
            "decision_source": "rule_fallback",
            "policy_clamped": True,
            "policy_clamp_reasons": ["due_review_forced_microquiz"],
        }
    }
    line = tutor_orchestration_decision_one_liner(snap)
    assert line
    assert "Фаза:" in line
    assert "Решение:" in line
    assert "Политика:" in line
    assert "педагогический маршрут" in line
    assert "запасное правило" in line
    assert "интервальное повторение" in line
    assert "due_review" not in line


def test_graph_expansion_trust_caption_when_applied():
    dbg = {
        "pipeline_trace": {
            "graph_expansion": {"ok": True, "extra_chunk_count": 3, "hops_applied": 2},
        }
    }
    cap = graph_expansion_trust_caption_ru(dbg)
    assert cap
    assert "граф" in cap.lower()
    assert "+3" in cap


def test_graph_expansion_trust_caption_when_skipped():
    dbg = {"pipeline_trace": {"graph_expansion": {"skipped": True, "reason": "query_type"}}}
    assert graph_expansion_trust_caption_ru(dbg) is None


def test_adaptive_plan_progress_teaser_with_override():
    plan = {
        "blocks": [
            {"type": "review", "concept": "Линейная алгебра"},
        ]
    }
    cap = adaptive_plan_progress_teaser_caption(plan_override=plan)
    assert cap
    assert cap.startswith("Adaptive plan:")
    assert "Повторение" in cap
    assert "Линейная" in cap
