"""Unit tests for router eval (mocked LLM)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.router_eval import aggregate_router_accuracy, run_single_router_case


def test_aggregate_router_accuracy_per_category():
    rows = [
        {"id": "a", "category": "quiz_quality", "status": "completed", "match": True},
        {"id": "b", "category": "quiz_quality", "status": "completed", "match": False},
        {"id": "c", "category": "socratic_quality", "status": "completed", "match": True},
        {"id": "d", "category": "skipped", "status": "skipped"},
    ]
    agg = aggregate_router_accuracy(rows)
    assert agg["cases_completed"] == 3
    assert agg["cases_correct"] == 2
    assert agg["overall_accuracy"] == pytest.approx(2 / 3, rel=1e-3)
    assert agg["per_category"]["quiz_quality"]["accuracy"] == pytest.approx(0.5)
    assert agg["per_category"]["socratic_quality"]["accuracy"] == pytest.approx(1.0)


def test_run_single_router_case_skips_without_gold():
    out = run_single_router_case({"id": "x", "category": "q", "input": {"question": "hi"}})
    assert out["status"] == "skipped"
    assert out["reason"] == "missing_or_invalid_router_gold"


def test_run_single_router_case_match(monkeypatch):
    from app import router_eval as rv

    def fake_invoke(**kwargs):
        return (
            {
                "selected_agent": "ConceptExplainer",
                "should_trigger_microquiz": False,
                "_fallback": False,
            },
            {"prompt_tokens": 1, "completion_tokens": 2},
        )

    def fake_clamp(decision, _profile):
        return decision, {}

    monkeypatch.setattr(rv, "invoke_pedagogical_orchestrator_llm", fake_invoke)
    monkeypatch.setattr(rv, "apply_orchestrator_policy_clamp", fake_clamp)
    case = {
        "id": "tutor_x",
        "category": "explain_depth",
        "input": {"query_mode": "tutor", "question": "Что такое RAG?"},
        "router_eval": {"gold_selected_agent": "ConceptExplainer"},
    }
    out = run_single_router_case(case)
    assert out["status"] == "completed"
    assert out["match"] is True
    assert out["predicted_agent"] == "ConceptExplainer"
    assert isinstance(out.get("latency_ms"), int)
    assert out.get("llm_model")


def test_per_category_guardrail_skips_low_n_non_us125():
    from scripts import run_router_eval as rre

    baseline = {
        "per_category": {
            "hint_gradation": {"correct": 1, "total": 1, "accuracy": 1.0},
            "quiz_quality": {"correct": 2, "total": 3, "accuracy": 0.6667},
        }
    }
    new_pc = {
        "hint_gradation": {"correct": 0, "total": 1, "accuracy": 0.0},
        "quiz_quality": {"correct": 2, "total": 3, "accuracy": 0.6667},
    }
    viol, low_n = rre._check_per_category_guardrails(new_pc, baseline)
    assert not any("hint_gradation" in v for v in viol)
    assert any("hint_gradation" in n for n in low_n)


def test_run_router_eval_script_import_and_regression_logic():
    from scripts import run_router_eval as rre

    assert rre._regression_overall(0.5, {"overall_accuracy": 0.6}, 5.0)[0] is True
    assert rre._regression_overall(0.56, {"overall_accuracy": 0.6}, 5.0)[0] is False
    assert rre._regression_overall(0.5, {"overall_accuracy": None}, 5.0)[0] is False
    # Строгое сравнение: ровно −5.00 п.п. ещё не регрессия (−5.01 — уже да)
    assert rre._regression_overall(0.60, {"overall_accuracy": 0.65}, 5.0)[0] is False
    assert rre._regression_overall(0.599, {"overall_accuracy": 0.65}, 5.0)[0] is True


def test_tutor_regression_has_router_gold_for_26_cases():
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / "eval_data" / "tutor_regression.json").read_text(encoding="utf-8"))
    cases = data.get("test_cases") or []
    assert len(cases) == 26
    for c in cases:
        rev = c.get("router_eval") or {}
        g = rev.get("gold_selected_agent")
        assert g in {
            "ConceptExplainer",
            "SocraticQuestioner",
            "ErrorDiagnoser",
            "MotivationCoach",
            "MicroQuizGenerator",
        }
        assert str(rev.get("gold_rationale") or "").strip(), (
            f"missing gold_rationale for {c.get('id')} (US-12.5 contract)"
        )


def test_orchestrator_prompt_metadata_exports():
    from app.tutor_prompts import ORCHESTRATOR_PROMPT_FINGERPRINT, ORCHESTRATOR_PROMPT_LEVEL

    assert ORCHESTRATOR_PROMPT_LEVEL == "19.5"
    assert len(ORCHESTRATOR_PROMPT_FINGERPRINT) == 16
    assert int(ORCHESTRATOR_PROMPT_FINGERPRINT, 16) >= 0


def test_critical_category_diagnostics_guardrail():
    from scripts.run_router_eval import _critical_category_diagnostics

    diag = _critical_category_diagnostics(
        {"quiz_quality": {"correct": 1, "total": 3, "accuracy": 0.3333}},
        {"quiz_quality": {"correct": 2, "total": 2, "accuracy": 1.0}},
    )
    q = diag["categories"]["quiz_quality"]
    assert q["guardrail_status"] == "violation"
    assert q["delta_pp_vs_baseline"] is not None


def test_validate_gold_rationale_contract_helper():
    from scripts.run_router_eval import _validate_gold_rationale_contract

    ok = [
        {
            "id": "a",
            "router_eval": {"gold_selected_agent": "ConceptExplainer", "gold_rationale": "because"},
        }
    ]
    _validate_gold_rationale_contract(ok)

    with pytest.raises(SystemExit):
        _validate_gold_rationale_contract(
            [
                {
                    "id": "b",
                    "router_eval": {"gold_selected_agent": "ConceptExplainer", "gold_rationale": ""},
                }
            ]
        )
