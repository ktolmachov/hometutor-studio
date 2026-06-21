"""Tutor prompt templates should format cleanly and include routing hints."""

from app.prompts import format_chat_prompt_text, select_prompt_id
from app.tutor_prompts import (
    ADAPTIVE_PLAN_PROMPT,
    NEXT_ACTION_PROMPT,
    ORCHESTRATOR_DECISION_PROMPT,
    QUIZ_PROMPT,
    TUTOR_RAG_WITH_QUIZ_PROMPT,
    TUTOR_SYSTEM_PROMPT,
    build_tutor_rag_prompt_with_quiz_difficulty,
    get_tutor_prompt,
    select_socratic_followup_type,
)
from app.tutor_orchestrator import normalize_pedagogical_orchestrator_decision


def test_get_tutor_prompt_includes_placeholders_resolved():
    s = get_tutor_prompt("TopicA", "C1", "H1", "Q1")
    assert "TopicA" in s and "C1" in s and "H1" in s and "Q1" in s


def test_tutor_rag_with_quiz_prompt_llamaindex_placeholders():
    s = format_chat_prompt_text(TUTOR_RAG_WITH_QUIZ_PROMPT, context_str="ctx", query_str="q")
    assert "ctx" in s and "q" in s
    assert "=== QUIZ ===" in s


def test_build_tutor_rag_prompt_with_quiz_difficulty():
    tpl = build_tutor_rag_prompt_with_quiz_difficulty("recall", socratic_type="implications")
    s = format_chat_prompt_text(tpl, context_str="ctx", query_str="q")
    assert "recall" in s and "ctx" in s and "=== QUIZ ===" in s
    assert "implications" in s and "socratic_check" in s


def test_build_tutor_rag_prompt_includes_goal_and_depth():
    tpl = build_tutor_rag_prompt_with_quiz_difficulty(
        "recognition",
        learning_goal="exam_prep",
        answer_depth="short",
    )
    s = format_chat_prompt_text(tpl, context_str="ctx", query_str="q")
    assert "экзамен" in s.lower()
    assert "кратко" in s.lower()


def test_build_tutor_rag_prompt_includes_preferred_style():
    tpl = build_tutor_rag_prompt_with_quiz_difficulty(
        "recognition",
        preferred_style="practice",
    )
    s = format_chat_prompt_text(tpl, context_str="ctx", query_str="q")
    assert "практик" in s.lower()


def test_build_tutor_rag_prompt_includes_orchestration_hints():
    tpl = build_tutor_rag_prompt_with_quiz_difficulty(
        "recall",
        graph_hint="Graph cluster: A, B.",
        learner_state_hint="Focus: A.",
        orchestration_hint="Route: due_review.",
    )
    s = format_chat_prompt_text(tpl, context_str="ctx", query_str="q")
    assert "Graph cluster: A, B." in s
    assert "Focus: A." in s
    assert "Route: due_review." in s


def test_select_socratic_followup_type():
    assert select_socratic_followup_type("keyword", 0) == "clarification"
    assert select_socratic_followup_type("qa", 1) == "clarification"
    assert select_socratic_followup_type("qa", 8) == "implications"


def test_orchestrator_decision_prompt_formats():
    s = ORCHESTRATOR_DECISION_PROMPT.format(
        learner_profile='{"mastery_level": "intermediate"}',
        knowledge_graph_subgraph="- A: quiz_mastery_level=recognition",
        session_history="user: hi",
        last_quiz_results="{}",
        current_user_message="Explain X",
    )
    assert "Explain X" in s and "intermediate" in s


def test_normalize_pedagogical_orchestrator_decision_defaults():
    d = normalize_pedagogical_orchestrator_decision({})
    assert d["selected_agent"] == "ConceptExplainer"
    assert len(d["reasoning_steps"]) == 4
    assert isinstance(d["should_trigger_microquiz"], bool)


def test_prompt_templates_format():
    s = QUIZ_PROMPT.format(
        mode_instructions="",
        topic="t",
        user_level="easy",
        learned_concepts="a,b",
        recent_history="hi",
        concept_names="C1,C2",
    )
    assert "easy" in s and "a,b" in s and "hi" in s and "C1" in s
    assert "50" in ADAPTIVE_PLAN_PROMPT.format(
        history_summary="h",
        known_concepts="k",
        progress_percent="50",
    )
    assert "g" in NEXT_ACTION_PROMPT.format(
        current_concept="c",
        learned_concepts="l",
        graph_summary="g",
    )
    assert "ctx" in TUTOR_SYSTEM_PROMPT.format(
        topic="t",
        context_str="ctx",
        history_summary="hs",
        query_str="q",
    )


def test_orchestrator_prompt_contains_quality_constraints():
    from app.tutor_prompts import ORCHESTRATOR_SYSTEM_PROMPT

    low = ORCHESTRATOR_SYSTEM_PROMPT.lower()
    assert "anti-overhelp" in low
    assert "misconception-first" in low
    assert "mastery dashboard prioritization" in low
    assert "что стоит повторить" in low


def test_retrieval_prompt_selector_does_not_replace_tutor_prompt_contract():
    # Tutor flow stays on tutor prompts; retrieval selector falls back to retrieval-safe prompt ids.
    assert select_prompt_id("tutor") == "qa"
    s = format_chat_prompt_text(TUTOR_RAG_WITH_QUIZ_PROMPT, context_str="ctx", query_str="q")
    assert "Socratic Tutor v2" in s
