"""Тесты политики персонализации и clamp оркестратора (E6.1)."""

from __future__ import annotations

from app.tutor_personalization_policy import (
    apply_orchestrator_policy_clamp,
    attach_personalization_policy_to_learner_profile,
    personalization_hints,
)


def test_attach_personalization_policy_idempotent():
    lp = {"mastery_level": "intermediate", "learning_goal": "exam_prep"}
    a = attach_personalization_policy_to_learner_profile(lp)
    b = attach_personalization_policy_to_learner_profile(a)
    assert a["personalization_policy"]["contract_version"] == 1
    assert a == b


def test_personalization_hints_due_review_emphasis():
    h = personalization_hints(
        learning_goal="understand_topic",
        mastery_level="intermediate",
        due_reviews_count=2,
        weak_concepts=[],
    )
    assert h["quiz_emphasis"] == "due_review_first"


def test_policy_clamp_forces_microquiz_when_due_review_priority():
    lp = {
        "mastery_level": "intermediate",
        "learning_goal": "understand_topic",
        "due_review_count": 2,
        "due_review_preview": ["a"],
        "weak_concepts": [],
        "route": "due_review",
        "personalization_policy": personalization_hints(
            learning_goal="understand_topic",
            mastery_level="intermediate",
            due_reviews_count=2,
            weak_concepts=[],
        ),
    }
    decision = {
        "selected_agent": "ConceptExplainer",
        "should_trigger_microquiz": False,
        "parameters": {"focus_concepts": [], "question_type": "probing", "depth": "intermediate", "motivation_link": ""},
        "reasoning_steps": ["1", "2", "3", "4"],
        "rationale": "x",
        "next_best_action": "",
        "confidence_score": 0.8,
    }
    out, meta = apply_orchestrator_policy_clamp(decision, lp)
    assert out["should_trigger_microquiz"] is True
    assert meta["policy_clamped"] is True
    assert "due_review_forced_microquiz" in meta["clamp_reasons"]


def test_policy_clamp_swaps_motivation_under_due_route():
    lp = {
        "mastery_level": "intermediate",
        "learning_goal": "understand_topic",
        "due_review_count": 1,
        "due_review_preview": ["topic_x"],
        "weak_concepts": [],
        "route": "due_review",
        "focus_topic": "topic_x",
        "personalization_policy": personalization_hints(
            learning_goal="understand_topic",
            mastery_level="intermediate",
            due_reviews_count=1,
            weak_concepts=[],
        ),
    }
    decision = {
        "selected_agent": "MotivationCoach",
        "should_trigger_microquiz": True,
        "parameters": {"focus_concepts": [], "question_type": "probing", "depth": "intermediate", "motivation_link": ""},
        "reasoning_steps": ["1", "2", "3", "4"],
        "rationale": "x",
        "next_best_action": "",
        "confidence_score": 0.8,
    }
    out, meta = apply_orchestrator_policy_clamp(decision, lp)
    assert out["selected_agent"] == "MicroQuizGenerator"
    assert "topic_x" in (out["parameters"].get("focus_concepts") or [])
    assert "due_review_overrides_motivation_agent" in meta["clamp_reasons"]


def test_policy_clamp_skips_fallback_decisions():
    lp = {"due_review_count": 5, "route": "due_review", "weak_concepts": []}
    d, meta = apply_orchestrator_policy_clamp(
        {"_fallback": True, "selected_agent": "MotivationCoach"},
        lp,
    )
    assert d["_fallback"] is True
    assert meta["policy_clamped"] is False


def test_policy_clamp_prefers_socratic_for_homework():
    lp = {
        "mastery_level": "intermediate",
        "learning_goal": "solve_homework",
        "due_review_count": 0,
        "weak_concepts": ["retrieval"],
        "route": "standard",
        "personalization_policy": personalization_hints(
            learning_goal="solve_homework",
            mastery_level="intermediate",
            due_reviews_count=0,
            weak_concepts=["retrieval"],
        ),
    }
    decision = {
        "selected_agent": "ConceptExplainer",
        "should_trigger_microquiz": False,
        "parameters": {"focus_concepts": [], "question_type": "probing", "depth": "intermediate", "motivation_link": ""},
        "reasoning_steps": ["1", "2", "3", "4"],
        "rationale": "x",
        "next_best_action": "",
        "confidence_score": 0.8,
    }
    out, meta = apply_orchestrator_policy_clamp(decision, lp)
    assert out["selected_agent"] == "SocraticQuestioner"
    assert out["parameters"]["question_type"] == "clarification"
    assert "homework_prefers_socratic_scaffold" in meta["clamp_reasons"]


def test_e11r_intent_clamp_sm2_repeat_command():
    lp = {
        "mastery_level": "intermediate",
        "learning_goal": "exam_prep",
        "orchestrator_clamp_user_message": "Повтори Prompt Injection",
    }
    decision = {
        "selected_agent": "ConceptExplainer",
        "should_trigger_microquiz": False,
        "parameters": {"focus_concepts": [], "question_type": "probing", "depth": "intermediate", "motivation_link": ""},
        "reasoning_steps": ["1", "2", "3", "4"],
        "rationale": "x",
        "next_best_action": "",
        "confidence_score": 0.8,
    }
    out, meta = apply_orchestrator_policy_clamp(decision, lp)
    assert out["selected_agent"] == "MicroQuizGenerator"
    assert "intent_sm2_repeat_topic_command" in meta["clamp_reasons"]


def test_e11r_intent_clamp_anti_overhelp():
    lp = {
        "mastery_level": "intermediate",
        "learning_goal": "understand_topic",
        "orchestrator_clamp_user_message": "Реши за меня задачу целиком: оптимизация reranker",
    }
    decision = {
        "selected_agent": "ConceptExplainer",
        "should_trigger_microquiz": False,
        "parameters": {"focus_concepts": [], "question_type": "probing", "depth": "intermediate", "motivation_link": ""},
        "reasoning_steps": ["1", "2", "3", "4"],
        "rationale": "x",
        "next_best_action": "",
        "confidence_score": 0.8,
    }
    out, meta = apply_orchestrator_policy_clamp(decision, lp)
    assert out["selected_agent"] == "SocraticQuestioner"
    assert "intent_anti_overhelp_solve_for_me" in meta["clamp_reasons"]


def test_e11r_intent_clamp_skips_when_no_message():
    lp = {"mastery_level": "intermediate", "learning_goal": "understand_topic"}
    decision = {
        "selected_agent": "ConceptExplainer",
        "should_trigger_microquiz": False,
        "parameters": {"focus_concepts": [], "question_type": "probing", "depth": "intermediate", "motivation_link": ""},
        "reasoning_steps": ["1", "2", "3", "4"],
        "rationale": "x",
        "next_best_action": "",
        "confidence_score": 0.8,
    }
    out, meta = apply_orchestrator_policy_clamp(decision, lp)
    assert out["selected_agent"] == "ConceptExplainer"
    assert not any("intent_" in r for r in meta["clamp_reasons"])


def test_policy_clamp_prefers_error_diagnoser_for_weak_concepts():
    lp = {
        "mastery_level": "intermediate",
        "learning_goal": "understand_topic",
        "due_review_count": 0,
        "weak_concepts": ["retrieval", "rerank"],
        "route": "targeted_reinforcement",
        "personalization_policy": personalization_hints(
            learning_goal="understand_topic",
            mastery_level="intermediate",
            due_reviews_count=0,
            weak_concepts=["retrieval", "rerank"],
        ),
    }
    decision = {
        "selected_agent": "ConceptExplainer",
        "should_trigger_microquiz": True,
        "parameters": {"focus_concepts": [], "question_type": "probing", "depth": "intermediate", "motivation_link": ""},
        "reasoning_steps": ["1", "2", "3", "4"],
        "rationale": "x",
        "next_best_action": "",
        "confidence_score": 0.8,
    }
    out, meta = apply_orchestrator_policy_clamp(decision, lp)
    assert out["selected_agent"] == "ErrorDiagnoser"
    assert "weak_concepts_require_diagnosis" in meta["clamp_reasons"]
