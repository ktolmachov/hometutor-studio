from app.tutor_learner_contract import (
    build_orchestration_state_dict,
    next_homework_level,
)


def test_next_homework_level_advances():
    assert next_homework_level("hint", advance=True) == "plan"
    assert next_homework_level("full_solution", advance=True) == "full_solution"


def test_next_homework_level_retreats():
    assert next_homework_level("plan", advance=False) == "hint"


def test_build_orchestration_state_dict():
    td = {
        "focus_topic": "RAG",
        "due_review_count": 1,
        "weak_concepts": ["chunking"],
        "action": {"next_action": "Проверь меня", "next_action_reason": "test"},
    }
    out = build_orchestration_state_dict(tutor_decision=td, session_metadata={"mastery_level": "advanced"})
    assert out["current_concept"] == "RAG"
    assert out["needs_review"] is True
    assert out["prerequisite_gap"] == "chunking"


def test_build_orchestration_state_dict_merges_pipeline_snapshot():
    out = build_orchestration_state_dict(
        tutor_decision={"focus_topic": "z"},
        session_metadata={"mastery_level": "intermediate"},
        tutor_orchestration_pipeline={
            "schema_version": 1,
            "phase": "orchestrate",
            "decision_source": "llm",
            "selected_agent": "ConceptExplainer",
            "should_trigger_microquiz": True,
            "policy_clamped": True,
            "policy_clamp_reasons": ["due_review_forced_microquiz"],
        },
    )
    assert out["tutor_orchestration_pipeline"]["phase"] == "orchestrate"
    assert out["orchestration_phase"] == "orchestrate"
    assert out["orchestration_decision_source"] == "llm"
    assert out["selected_agent"] == "ConceptExplainer"
    assert out["should_trigger_microquiz"] is True
    assert out["policy_clamped"] is True
    assert out["policy_clamp_reasons"] == ["due_review_forced_microquiz"]


def test_personalization_hints():
    from app.tutor_personalization_policy import personalization_hints

    h = personalization_hints(
        learning_goal="exam_prep",
        mastery_level="beginner",
        due_reviews_count=2,
        weak_concepts=["a", "b"],
    )
    assert h["quiz_emphasis"] == "due_review_first"
    assert "explanation_depth" in h
