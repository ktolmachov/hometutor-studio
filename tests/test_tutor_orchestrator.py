from app.knowledge_graph import JsonKnowledgeGraph
from app.tutor_orchestrator import (
    apply_pedagogical_orchestrator_to_metadata,
    apply_tutor_self_correction,
    build_redacted_tutor_expert_snapshot,
    build_tutor_session_state,
    decide_tutor_next_action,
    invoke_pedagogical_orchestrator_llm,
    make_rule_fallback_orchestrator_decision,
)


def test_build_tutor_session_state_prioritizes_due_reviews(monkeypatch):
    monkeypatch.setattr(
        "app.tutor_orchestrator.weak_concepts_for_kg",
        lambda kg, threshold=70, limit=6: ["graphs", "rag"],
    )
    monkeypatch.setattr(
        "app.tutor_orchestrator.filter_due_reviews_for_kg",
        lambda kg, limit=3: [{"concept": "photosynthesis"}],
    )
    monkeypatch.setattr("app.tutor_orchestrator.count_due_reviews_for_kg", lambda kg: 2)

    state = build_tutor_session_state(
        current_topic="graphs",
        mastery_level="intermediate",
        preferred_style="examples",
        learning_goal="exam_prep",
        quiz_difficulty="recall",
    )

    profile = state["learner_profile"]
    assert profile["route"] == "due_review"
    assert profile["recommended_quiz_topic"] == "photosynthesis"
    assert "photosynthesis" in profile["due_review_preview"]
    assert profile["due_review_reason"] == "плановое повторение"


def test_apply_tutor_self_correction_marks_prerequisite_cycles_in_trust():
    teaching = {
        "teaching_summary": "x",
        "understanding_state": {"what_you_understood": "x", "risk_gaps": "", "what_to_do_now": ""},
        "next_action": "Следующий шаг",
        "next_action_reason": "y",
        "suggested_ctas": ["Следующий шаг"],
        "trust_signals": {"sources_used": 2, "confidence": "medium"},
    }
    session_state = {"learner_profile": {"route": "standard"}}
    gh = {"has_prerequisite_cycles": True, "cycle_count": 1}

    corrected = apply_tutor_self_correction(
        teaching,
        session_state=session_state,
        source_count=2,
        graph_prerequisites_health=gh,
    )

    assert corrected["trust_signals"]["graph_prerequisite_cycles"] is True
    assert "graph_note" in corrected["trust_signals"]


def test_apply_tutor_self_correction_overrides_next_action_for_due_reviews():
    teaching = {
        "teaching_summary": "Short explanation",
        "understanding_state": {
            "what_you_understood": "x",
            "risk_gaps": "",
            "what_to_do_now": "",
        },
        "socratic_check": None,
        "next_action": "Следующий шаг",
        "next_action_reason": "Move on",
        "suggested_ctas": ["Следующий шаг"],
        "depth_level": "intermediate",
        "trust_signals": {"sources_used": 0, "confidence": "medium", "coverage_warning": None},
    }
    session_state = {
        "learner_profile": {
            "route": "due_review",
            "focus_topic": "graphs",
            "due_review_preview": ["photosynthesis"],
        }
    }

    corrected = apply_tutor_self_correction(
        teaching,
        session_state=session_state,
        source_count=1,
    )

    assert corrected["next_action"] == "Пора повторить"
    assert "photosynthesis" in corrected["next_action_reason"]
    assert "давно не повторял" in corrected["next_action_reason"]
    assert corrected["suggested_ctas"][0] == "Пора повторить"
    assert corrected["trust_signals"]["confidence"] == "low"


def test_apply_tutor_self_correction_uses_diagnosis_for_targeted_reinforcement():
    teaching = {
        "teaching_summary": "Short explanation",
        "understanding_state": {
            "what_you_understood": "x",
            "risk_gaps": "",
            "what_to_do_now": "",
        },
        "socratic_check": None,
        "next_action": "",
        "next_action_reason": "",
        "suggested_ctas": ["Следующий шаг"],
        "depth_level": "intermediate",
        "trust_signals": {"sources_used": 2, "confidence": "medium", "coverage_warning": None},
    }
    session_state = {
        "learner_profile": {
            "route": "targeted_reinforcement",
            "focus_topic": "graphs",
            "weak_concepts": ["retrieval", "rerank"],
        }
    }

    corrected = apply_tutor_self_correction(
        teaching,
        session_state=session_state,
        source_count=2,
    )
    assert corrected["next_action"] == "Проверь меня"
    assert "misconceptions" in corrected["next_action_reason"]
    assert "retrieval" in corrected["understanding_state"]["risk_gaps"]


def test_apply_tutor_self_correction_homework_keeps_scaffold_first():
    teaching = {
        "teaching_summary": "x",
        "understanding_state": {"what_you_understood": "x", "risk_gaps": "", "what_to_do_now": ""},
        "next_action": "",
        "next_action_reason": "",
        "suggested_ctas": ["Дай пример"],
        "trust_signals": {"sources_used": 2, "confidence": "medium"},
    }
    session_state = {
        "learner_profile": {
            "route": "standard",
            "learning_goal": "solve_homework",
        }
    }
    corrected = apply_tutor_self_correction(
        teaching,
        session_state=session_state,
        source_count=2,
    )
    assert corrected["next_action"] == "Следующий шаг"
    assert "scaffold" in corrected["next_action_reason"]


def test_decide_tutor_next_action_returns_explicit_contract(monkeypatch):
    monkeypatch.setattr(
        "app.tutor_orchestrator.weak_concepts_for_kg",
        lambda kg, threshold=70, limit=6: ["graphs"],
    )
    monkeypatch.setattr(
        "app.tutor_orchestrator.filter_due_reviews_for_kg",
        lambda kg, limit=3: [{"concept": "graphs"}],
    )
    monkeypatch.setattr("app.tutor_orchestrator.count_due_reviews_for_kg", lambda kg: 1)

    decision = decide_tutor_next_action(
        current_topic="graphs",
        mastery_level="intermediate",
        preferred_style="examples",
        learning_goal="exam_prep",
        quiz_difficulty="recall",
    )

    assert decision["route"] == "due_review"
    assert decision["recommended_quiz_topic"] == "graphs"
    assert isinstance(decision["action"], dict)
    assert decision["action"]["next_action"] == "Пора повторить"


def test_build_tutor_session_state_ignores_stale_due_reviews(tmp_path):
    p = tmp_path / "tutor_graph.json"
    p.write_text(
        '{"concepts":{"graphs":{"description":"","prerequisites":[]}},"documents":{},"edges":{}}',
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(p)

    state = build_tutor_session_state(
        current_topic="graphs",
        mastery_level="intermediate",
        preferred_style="examples",
        learning_goal="exam_prep",
        quiz_difficulty="recall",
        kg=kg,
        persisted_profile={"recent_topics": ["legacy"]},
    )

    profile = state["learner_profile"]
    assert profile["route"] == "standard"
    assert profile["due_review_count"] == 0
    assert profile["due_review_preview"] == []


def test_make_rule_fallback_orchestrator_decision():
    d = make_rule_fallback_orchestrator_decision(reason="json_parse")
    assert d["_fallback"] is True
    assert d.get("_error") == "json_parse"
    assert d["should_trigger_microquiz"] is False
    assert d["selected_agent"] == "ConceptExplainer"


def test_invoke_pedagogical_orchestrator_uses_graph_llm(monkeypatch):
    called = {"graph": 0}

    class _Msg:
        content = (
            '{"reasoning_steps":["one","two","three","four"],'
            '"selected_agent":"ConceptExplainer",'
            '"rationale":"graph route",'
            '"parameters":{"focus_concepts":["RAG"],"question_type":"probing","depth":"intermediate"},'
            '"should_trigger_microquiz":false,'
            '"next_best_action":"Следующий шаг",'
            '"confidence_score":0.9}'
        )

    class _Resp:
        message = _Msg()

    class _GraphLlm:
        pass

    def _get_graph_llm():
        called["graph"] += 1
        return _GraphLlm()

    def _chat_with_resilience(llm, *_args, **_kwargs):
        assert isinstance(llm, _GraphLlm)
        return _Resp()

    monkeypatch.setattr("app.tutor_orchestrator.get_graph_llm", _get_graph_llm)
    monkeypatch.setattr("app.tutor_orchestrator.chat_with_resilience", _chat_with_resilience)

    decision, usage = invoke_pedagogical_orchestrator_llm(
        learner_profile={"focus_topic": "RAG", "graph_cluster": ["RAG"]},
        current_user_message="Что дальше?",
        conversation_history=[],
        knowledge_graph_subgraph_override="- RAG: quiz_mastery_level=recognition",
    )

    assert called["graph"] == 1
    assert usage is None
    assert decision["_fallback"] is False
    assert decision["selected_agent"] == "ConceptExplainer"
    assert decision["parameters"]["focus_concepts"] == ["RAG"]


def test_apply_pedagogical_orchestrator_sets_pipeline_contract():
    class _Ctx:
        __slots__ = ("metadata",)

        def __init__(self) -> None:
            self.metadata: dict = {"orchestration_hint": ""}

    ctx = _Ctx()
    apply_pedagogical_orchestrator_to_metadata(
        ctx,
        make_rule_fallback_orchestrator_decision(reason="unit"),
    )
    pipe = ctx.metadata.get("tutor_orchestration_pipeline")
    assert isinstance(pipe, dict)
    assert pipe.get("schema_version") == 1
    assert pipe.get("decision_source") == "rule_fallback"
    assert pipe.get("phase") == "orchestrate"
    assert pipe.get("selected_agent") == "ConceptExplainer"
    assert pipe.get("should_trigger_microquiz") is False


def test_build_redacted_tutor_expert_snapshot_preserves_safeScalars():
    snap = build_redacted_tutor_expert_snapshot(
        {
            "orchestration_phase": "gen",
            "policy_clamped": True,
            "policy_clamp_reasons": ["weak_evidence"],
            "decision": {"action": {"next_action": "Дай пример"}, "reason": "учебный план"},
        }
    )
    assert snap.get("orchestration_phase") == "gen"
    assert snap.get("policy_clamped") is True
    assert "decision_excerpt" in snap
