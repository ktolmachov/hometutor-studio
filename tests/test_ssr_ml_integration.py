"""Интеграция SSR rule-baseline + локальный ML rerank (forgetting-curve hybrid)."""

from __future__ import annotations

from unittest.mock import patch

from scripts.check_ssr_ml_rollout_gate import collect_static_violations

from app.ui.adaptive_plan_card import _build_smart_study_recommendation_rules, build_smart_study_recommendation


def test_ssr_ml_rollout_gate_static_checks_pass() -> None:
    assert collect_static_violations() == []


def test_ssr_ml_disabled_equals_rule_baseline() -> None:
    rec = build_smart_study_recommendation(surface="home", flashcard_due_n=2, sm2_due_n=0)
    rule = _build_smart_study_recommendation_rules(surface="home", flashcard_due_n=2, sm2_due_n=0)
    assert rec.hint_kind == rule.hint_kind == "cards_due"
    assert not (rec.ml_audit_ru or "").strip()


@patch("app.ssr_ml_reranking.predict_hint_probability_map_or_empty", return_value={})
@patch("app.smart_study_ssr_ml.get_settings")
def test_ssr_ml_empty_probs_falls_back(mock_settings, _mock_probs) -> None:
    mock_settings.return_value.ssr_ml_rerank_enabled = True
    mock_settings.return_value.ssr_ml_rerank_confidence_min = 0.01
    mock_settings.return_value.ssr_ml_rerank_latency_budget_ms = 500.0
    rec = build_smart_study_recommendation(surface="home", has_last_answer_qa=True)
    assert rec.hint_kind == "answer_ready"
    assert not (rec.ml_audit_ru or "").strip()


@patch("app.ssr_ml_reranking.predict_hint_probability_map_or_empty")
@patch("app.smart_study_ssr_ml.get_settings")
def test_ssr_ml_soft_tier_can_shift_to_safe_default(mock_settings, mock_probs) -> None:
    mock_settings.return_value.ssr_ml_rerank_enabled = True
    mock_settings.return_value.ssr_ml_rerank_confidence_min = 0.25
    mock_settings.return_value.ssr_ml_rerank_latency_budget_ms = 500.0
    mock_probs.return_value = {"answer_ready": 0.1, "safe_default": 0.9}
    rec = build_smart_study_recommendation(surface="home", has_last_answer_qa=True)
    assert rec.hint_kind == "safe_default"
    audit = (rec.ml_audit_ru or "").lower()
    assert "сдвиг" in audit or "совпало" in audit or "ml" in audit


@patch("app.ssr_ml_reranking.predict_hint_probability_map_or_empty")
@patch("app.smart_study_ssr_ml.get_settings")
def test_ssr_ml_low_confidence_no_shift(mock_settings, mock_probs) -> None:
    mock_settings.return_value.ssr_ml_rerank_enabled = True
    mock_settings.return_value.ssr_ml_rerank_confidence_min = 0.85
    mock_settings.return_value.ssr_ml_rerank_latency_budget_ms = 500.0
    mock_probs.return_value = {"answer_ready": 0.5, "safe_default": 0.5}
    rec = build_smart_study_recommendation(surface="home", has_last_answer_qa=True)
    assert rec.hint_kind == "answer_ready"
    assert not (rec.ml_audit_ru or "").strip()


@patch("app.smart_study_ssr_ml.get_settings")
def test_ssr_ml_retention_priority_gate(mock_settings) -> None:
    mock_settings.return_value.ssr_ml_rerank_enabled = True
    mock_settings.return_value.ssr_ml_rerank_confidence_min = 0.01
    mock_settings.return_value.ssr_ml_rerank_latency_budget_ms = 500.0
    rec = build_smart_study_recommendation(surface="home", flashcard_due_n=2, sm2_due_n=3)
    assert rec.hint_kind == "cards_due"
    assert not (rec.ml_audit_ru or "").strip()


@patch("app.ssr_ml_reranking.predict_hint_probability_map_or_empty", return_value={"answer_ready": 1.0, "safe_default": 0.0})
@patch("app.smart_study_ssr_ml.get_settings")
@patch("app.smart_study_ssr_ml.time.perf_counter", side_effect=[0.0, 0.02])
def test_ssr_ml_latency_budget_falls_back(mock_perf, mock_settings, mock_probs) -> None:
    mock_settings.return_value.ssr_ml_rerank_enabled = True
    mock_settings.return_value.ssr_ml_rerank_confidence_min = 0.01
    mock_settings.return_value.ssr_ml_rerank_latency_budget_ms = 5.0
    rec = build_smart_study_recommendation(surface="home", has_last_answer_qa=True)
    assert rec.hint_kind == "answer_ready"
    assert not (rec.ml_audit_ru or "").strip()


@patch("app.ssr_ml_monitoring.get_ssr_ml_real_sample_count")
@patch("app.ssr_ml_monitoring.get_ssr_ml_ab_assignment")
@patch("app.ssr_ml_reranking.predict_hint_probability_map_or_empty")
@patch("app.smart_study_ssr_ml.get_settings")
def test_ssr_ml_auto_enable_threshold_ab_serving(mock_settings, mock_probs, mock_ab, mock_count) -> None:
    # 1. ssr_ml_rerank_enabled = False, sample count < threshold (1000)
    mock_settings.return_value.ssr_ml_rerank_enabled = False
    mock_settings.return_value.ssr_ml_auto_enable_threshold = 1000
    mock_count.return_value = 500
    mock_ab.return_value = "treatment"
    mock_probs.return_value = {"answer_ready": 0.1, "safe_default": 0.9}
    
    rec = build_smart_study_recommendation(surface="home", has_last_answer_qa=True)
    assert rec.hint_kind == "answer_ready"
    assert not (rec.ml_audit_ru or "").strip()

    # 2. sample count >= threshold, variant = control
    mock_count.return_value = 1050
    mock_ab.return_value = "control"
    rec = build_smart_study_recommendation(surface="home", has_last_answer_qa=True)
    assert rec.hint_kind == "answer_ready"
    assert not (rec.ml_audit_ru or "").strip()

    # 3. sample count >= threshold, variant = treatment
    mock_ab.return_value = "treatment"
    mock_settings.return_value.ssr_ml_rerank_confidence_min = 0.25
    mock_settings.return_value.ssr_ml_rerank_latency_budget_ms = 500.0
    rec = build_smart_study_recommendation(surface="home", has_last_answer_qa=True)
    assert rec.hint_kind == "safe_default"
    assert (rec.ml_audit_ru or "").strip()
