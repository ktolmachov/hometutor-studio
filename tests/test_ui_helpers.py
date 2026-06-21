"""Регрессии для app/ui/helpers.py (без Streamlit runtime)."""
from unittest.mock import MagicMock

from app.ui.helpers import (
    build_tutor_action_items,
    build_tutor_orchestration_summary,
    esc_html,
    format_request_error,
    graph_expansion_skip_reason_label,
    home_mode_best_for_line,
    home_mode_intent_row_orders,
    home_mode_preview_lines,
    learner_rag_profile_label,
    llm_source_badge_text,
    llm_source_debug_rows,
    llm_source_privacy_notice,
    llm_source_summary,
    preview_code_language,
    retrieval_route_debug_rows,
    retrieval_route_demotion_badge,
    retrieval_route_summary,
    retrieval_route_summary_text,
    supports_text_preview,
)


def test_format_request_error_plain_exception():
    assert format_request_error(ValueError("plain")) == "plain"


def test_format_request_error_uses_response_detail():
    err = MagicMock()
    err.response = MagicMock()
    err.response.json.return_value = {"detail": "from api"}
    assert format_request_error(err) == "from api"


def test_esc_html():
    assert esc_html("<x>") == "&lt;x&gt;"
    assert esc_html("") == ""


def test_learner_rag_profile_label_masks_internal_names():
    assert learner_rag_profile_label("fast") == "быстрый ответ"
    assert learner_rag_profile_label("quality") == "точный ответ"
    assert learner_rag_profile_label("graph_aware") == "ответ с учетом связей"


def test_retrieval_route_summary_text_reports_fallback_without_raw_mode():
    text = retrieval_route_summary_text(
        {
            "retrieval_routing": {
                "selected_profile": "fast",
                "effective_profile": "quality",
                "fallback_reason": "low_confidence",
                "manual_override": False,
                "profile_resolved_from": "rule",
            }
        }
    )

    assert text is not None
    assert "быстрый ответ" in text
    assert "точный ответ" in text
    assert "retrieval_mode" not in text
    assert "надежный профиль" in text


def test_retrieval_route_summary_text_reports_manual_choice():
    text = retrieval_route_summary_text(
        {
            "retrieval_routing": {
                "selected_profile": "quality",
                "effective_profile": "quality",
                "manual_override": True,
            }
        }
    )

    assert text == "Почему этот маршрут: используется профиль «точный ответ» по вашему выбору."


def test_retrieval_route_summary_handles_missing_trace():
    assert retrieval_route_summary_text({}) is None
    assert retrieval_route_summary(None)["selected_profile"] is None


def test_retrieval_route_debug_rows_preserve_selected_and_effective_profiles():
    rows = retrieval_route_debug_rows(
        {
            "retrieval_routing": {
                "selected_profile": "fast",
                "effective_profile": "quality",
                "fallback_reason": "low_confidence",
                "profile_resolved_from": "rule",
            }
        }
    )

    assert ("Выбранный профиль", "fast") in rows
    assert ("Эффективный профиль", "quality") in rows
    assert ("Причина маршрута", "система выбрала более надежный профиль") in rows
    assert ("Источник решения", "rule") in rows


def test_retrieval_route_summary_text_reports_demotion_without_raw_reason():
    text = retrieval_route_summary_text(
        {
            "retrieval_routing": {
                "selected_profile": "graph_aware",
                "effective_profile": "quality",
                "fallback_reason": "graph_no_uplift_below_delta",
                "manual_override": False,
            }
        }
    )

    assert text is not None
    assert "ответ с учетом связей" in text
    assert "точный ответ" in text
    assert "graph_no_uplift" not in text
    assert "uplift" in text.lower()


def test_retrieval_route_summary_text_unknown_fallback_uses_raw_string():
    text = retrieval_route_summary_text(
        {
            "retrieval_routing": {
                "selected_profile": "fast",
                "effective_profile": "quality",
                "fallback_reason": "future_unknown_reason_code",
                "manual_override": False,
            }
        }
    )

    assert text is not None
    assert "future unknown reason code" in text


def test_retrieval_route_demotion_badge_for_graph_no_uplift():
    badge = retrieval_route_demotion_badge(
        {
            "retrieval_routing": {
                "selected_profile": "graph_aware",
                "effective_profile": "quality",
                "fallback_reason": "graph_no_uplift_below_delta",
            }
        }
    )

    assert badge == "демotion: нет uplift"


def test_retrieval_route_demotion_badge_absent_when_profiles_match():
    assert retrieval_route_demotion_badge(
        {
            "retrieval_routing": {
                "selected_profile": "graph_aware",
                "effective_profile": "graph_aware",
                "fallback_reason": "graph_no_uplift_below_delta",
            }
        }
    ) is None


def test_graph_expansion_skip_reason_label_maps_query_type():
    assert graph_expansion_skip_reason_label("query_type") == "тип запроса не требует расширения графа"
    assert graph_expansion_skip_reason_label("custom_skip") == "custom skip"


def test_llm_source_summary_prefers_top_level_debug_payload():
    summary = llm_source_summary(
        {
            "llm_source": "local",
            "llm_model": "qwen/qwen3.6-27b",
            "llm_api_base": "http://127.0.0.1:1234/v1",
            "fallback_used": False,
            "llm_profile": "primary",
            "llm_latency_ms": 42.25,
            "pipeline_trace": {
                "generate_stage": {
                    "llm_source": "cloud",
                    "llm_model": "openai/gpt-4o-mini",
                }
            },
        }
    )

    assert summary["source"] == "local"
    assert summary["label"] == "Local"
    assert summary["model"] == "qwen/qwen3.6-27b"
    assert summary["api_base"] == "http://127.0.0.1:1234/v1"
    assert summary["fallback_used"] is False
    assert summary["profile"] == "primary"
    assert summary["latency_ms"] == 42.25


def test_llm_source_badge_falls_back_to_pipeline_generate_stage():
    debug = {
        "pipeline_trace": {
            "generate_stage": {
                "llm_source": "cloud",
                "llm_model": "openai/gpt-4o-mini",
                "fallback_used": True,
                "llm_profile": "primary_fallback",
                "llm_latency_ms": "18.5",
            }
        }
    }

    assert (
        llm_source_badge_text(debug)
        == "Источник ответа: Cloud · openai/gpt-4o-mini · fallback · profile: primary_fallback · 18.5 ms"
    )


def test_llm_source_debug_rows_include_source_contract_fields():
    rows = llm_source_debug_rows(
        {
            "llm_source": "local",
            "llm_model": "qwen/qwen3.6-27b",
            "llm_api_base": "http://127.0.0.1:1234/v1",
            "llm_profile": "primary",
            "llm_latency_ms": 7,
        }
    )

    assert ("Источник LLM", "Local") in rows
    assert ("Модель", "qwen/qwen3.6-27b") in rows
    assert ("API base", "http://127.0.0.1:1234/v1") in rows
    assert ("Профиль", "primary") in rows
    assert ("Latency LLM", "7.0 ms") in rows


def test_llm_source_privacy_notice_is_cloud_only():
    assert llm_source_privacy_notice({"llm_source": "local"}) is None
    assert llm_source_badge_text({}) is None

    notice = llm_source_privacy_notice({"llm_source": "cloud"})

    assert notice is not None
    assert "HOME_RAG_LLM_CLOUD_CONSENT=true" in notice


def test_smart_study_router_contract_flashcard_priority():
    from app.ui.adaptive_plan_card import build_smart_study_recommendation

    rec = build_smart_study_recommendation(surface="home", flashcard_due_n=1, sm2_due_n=5)
    assert rec.hint_kind == "cards_due"


def test_ssr_quiet_mode_styles_target_router_card_fixture():
    from app.ui.resume_cards import _ssr_quiet_stylesheet_markup

    css = _ssr_quiet_stylesheet_markup()
    assert "e2e-smart-study-next-step" in css


def test_home_mode_best_for_lines_cover_primary_cards():
    slots = ("tutor", "qa", "quiz", "flashcards", "topics", "progress")
    seen = set()
    for slot in slots:
        text = home_mode_best_for_line(slot)
        assert text.strip(), slot
        assert len(text) > 12, slot
        seen.add(text)
    assert len(seen) == len(slots)


def test_home_mode_preview_lines_cover_primary_cards():
    slots = ("tutor", "qa", "quiz", "flashcards", "topics", "progress")
    for slot in slots:
        lines = home_mode_preview_lines(slot)
        assert len(lines) >= 2, slot
        blob = " ".join(lines)
        assert "Маршрут:" in blob, slot


def test_home_mode_intent_row_orders_safe_starter_default_tie_break():
    r1, r2 = home_mode_intent_row_orders(
        cta_kind="safe_starter",
        flashcard_due_n=0,
        due_n=0,
        has_tutor_resume=False,
        has_mastery_gap=False,
        has_handoff_topic=False,
        last_primary_slot=None,
    )
    assert r1 == ("tutor", "qa", "quiz")
    assert r2 == ("flashcards", "topics", "progress")


def test_home_mode_intent_row_orders_flashcard_due_pushes_flashcards_first():
    r1, r2 = home_mode_intent_row_orders(
        cta_kind="flashcard_due",
        flashcard_due_n=2,
        due_n=0,
        has_tutor_resume=False,
        has_mastery_gap=False,
        has_handoff_topic=False,
        last_primary_slot=None,
    )
    assert r1 == ("tutor", "qa", "quiz")
    assert r2[0] == "flashcards"


def test_home_mode_intent_row_orders_resume_pushes_tutor_first():
    r1, r2 = home_mode_intent_row_orders(
        cta_kind="resume",
        flashcard_due_n=0,
        due_n=0,
        has_tutor_resume=True,
        has_mastery_gap=False,
        has_handoff_topic=False,
        last_primary_slot=None,
    )
    assert r1[0] == "tutor"
    assert r2 == ("flashcards", "topics", "progress")


def test_home_mode_intent_row_orders_last_slot_boosts_that_mode():
    r1, _r2 = home_mode_intent_row_orders(
        cta_kind="safe_starter",
        flashcard_due_n=0,
        due_n=0,
        has_tutor_resume=False,
        has_mastery_gap=False,
        has_handoff_topic=False,
        last_primary_slot="qa",
    )
    assert r1[0] == "qa"


def test_home_mode_intent_row_orders_mastery_gap_prioritizes_topics():
    _r1, r2 = home_mode_intent_row_orders(
        cta_kind="mastery_gap",
        flashcard_due_n=0,
        due_n=0,
        has_tutor_resume=False,
        has_mastery_gap=True,
        has_handoff_topic=False,
        last_primary_slot=None,
    )
    assert r2[0] == "topics"


def test_flashcard_home_effort_hint_lines_surface_states_for_home_hub():
    from app.flashcard_service import flashcard_home_effort_hint_lines

    assert len(flashcard_home_effort_hint_lines(0)) == 1
    assert len(flashcard_home_effort_hint_lines(10)) == 1
    assert len(flashcard_home_effort_hint_lines(80)) == 2


def test_preview_helpers():
    assert supports_text_preview("x.md") is True
    assert supports_text_preview("x.pdf") is True
    assert supports_text_preview("z.docx") is True
    assert preview_code_language("a.md") == "markdown"
    assert preview_code_language("b.html") == "html"
    assert preview_code_language("c.txt") == "text"
    assert preview_code_language("x.pdf") == "text"
    assert preview_code_language("y.docx") == "text"
    assert preview_code_language("x.bin") is None


def test_build_tutor_action_items_adds_user_facing_labels():
    items = build_tutor_action_items(
        ["Дай пример", "Проверь меня", "Следующий шаг"],
        next_action="Следующий шаг",
    )

    assert items[0] == {"label": "Понял", "prompt": "Следующий шаг"}
    assert {"label": "Нужен пример", "prompt": "Дай пример"} in items
    assert {"label": "Проверь меня", "prompt": "Проверь меня"} in items
    assert {"label": "Следующий шаг", "prompt": "Следующий шаг"} in items


def test_build_tutor_action_items_prioritizes_due_review_button():
    items = build_tutor_action_items(
        ["Проверь меня"],
        next_action="Пора повторить",
        due_reviews_count=2,
    )

    assert items[0] == {"label": "Пора повторить", "prompt": "Пора повторить"}


def test_deepen_with_sources_prompt_requests_source_grounding():
    from app.ui.tutor_chat_actions import build_deepen_with_sources_prompt

    prompt = build_deepen_with_sources_prompt("Не знаю: Что такое RAG?")

    assert "по источникам базы знаний" in prompt
    assert "подтверждено источниками" in prompt
    assert "Что такое RAG" in prompt


def test_build_tutor_orchestration_summary_compacts_typed_state():
    items = build_tutor_orchestration_summary(
        orchestration_state={
            "current_concept": "RAG",
            "mastery_estimate": "advanced",
            "needs_review": True,
            "prerequisite_gap": "chunking",
            "recommended_action": "Проверь меня",
        },
        decision={"route": "due_review", "focus_topic": "ignored"},
        socratic={"question_type": "clarification"},
    )

    assert {"label": "Маршрут", "value": "due review"} in items
    assert {"label": "Фокус", "value": "RAG"} in items
    assert {"label": "Mastery", "value": "advanced"} in items
    assert {"label": "Рекомендация", "value": "Проверь меня"} in items
    assert {"label": "Пробел", "value": "chunking"} in items
    assert {"label": "Повторение", "value": "есть due review"} in items
    assert {"label": "Socratic", "value": "clarification"} in items


def test_build_tutor_orchestration_summary_falls_back_to_decision_focus():
    items = build_tutor_orchestration_summary(
        orchestration_state={},
        decision={"route": "standard", "focus_topic": "Graph"},
        socratic=None,
    )

    assert {"label": "Маршрут", "value": "standard"} in items
    assert {"label": "Фокус", "value": "Graph"} in items


def test_qa_handoff_context_lines_for_preview_includes_confidence_and_sources():
    from app.tutor_pipeline_contract import qa_handoff_context_lines_for_preview

    lines = qa_handoff_context_lines_for_preview(
        {"topic": "RAG", "last_question": "Что?", "answer_summary": "Коротко"},
        last_answer={
            "confidence": {"label": "Высокая", "level": "high"},
            "sources": [{"file_name": "a.md"}, {"file_name": "b.md"}],
        },
    )
    blob = " ".join(lines)
    assert "Тема:" in blob
    assert "Уверенность" in blob
    assert "Источников" in blob


def test_build_tutor_orchestration_summary_includes_pipeline_contract():
    items = build_tutor_orchestration_summary(
        orchestration_state={"current_concept": "x"},
        tutor_orchestration_pipeline={
            "phase": "rag_prepare",
            "decision_source": "llm",
            "policy_clamped": True,
            "policy_clamp_reasons": ["due_review_forced_microquiz"],
        },
    )

    assert {"label": "Фаза пайплайна", "value": "rag prepare"} in items
    assert {"label": "Источник решения", "value": "llm"} in items
    assert {"label": "Policy clamp", "value": "due_review_forced_microquiz"} in items


def test_build_tutor_orchestration_summary_prefers_typed_scalar_overrides():
    items = build_tutor_orchestration_summary(
        orchestration_state=None,
        tutor_orchestration_pipeline={"phase": "ignored", "decision_source": "ignored"},
        orchestration_phase="rag_prepare",
        orchestration_decision_source="llm",
        selected_agent="MicroQuizGenerator",
        should_trigger_microquiz=True,
    )

    assert {"label": "Фаза пайплайна", "value": "rag prepare"} in items
    assert {"label": "Источник решения", "value": "llm"} in items
    assert {"label": "Агент", "value": "MicroQuizGenerator"} in items
    assert {"label": "Micro-quiz", "value": "да"} in items


def test_build_tutor_orchestration_summary_falls_back_to_orchestration_state_scalars():
    items = build_tutor_orchestration_summary(
        orchestration_state={
            "orchestration_phase": "rag_prepare",
            "orchestration_decision_source": "rule_fallback",
            "selected_agent": "ConceptExplainer",
            "should_trigger_microquiz": False,
            "policy_clamped": True,
            "policy_clamp_reasons": ["due_review_forced_microquiz"],
        },
        tutor_orchestration_pipeline=None,
    )
    assert {"label": "Фаза пайплайна", "value": "rag prepare"} in items
    assert {"label": "Источник решения", "value": "rule fallback"} in items
    assert {"label": "Агент", "value": "ConceptExplainer"} in items
    assert {"label": "Micro-quiz", "value": "нет"} in items
    assert {"label": "Policy clamp", "value": "due_review_forced_microquiz"} in items


def test_qa_wait_runway_stable_per_question():
    from app.ui.qa_wait_ux import wait_runway_message_for_question

    a = wait_runway_message_for_question("Что такое RAG?")
    b = wait_runway_message_for_question("Что такое RAG?")
    c = wait_runway_message_for_question("Совсем другой вопрос про индексацию документов")
    assert a == b
    assert a != c


def test_qa_fast_success_reinforcement_rules():
    from app.ui.qa_wait_ux import answer_qualifies_for_fast_success_reinforcement

    assert (
        answer_qualifies_for_fast_success_reinforcement(
            total_answer_ms=1500,
            confidence={"level": "high"},
            sources=[{"file_name": "x.md"}],
        )
        is True
    )
    assert (
        answer_qualifies_for_fast_success_reinforcement(
            total_answer_ms=1500,
            confidence={"level": "low"},
            sources=[{"file_name": "x.md"}],
        )
        is False
    )
    assert (
        answer_qualifies_for_fast_success_reinforcement(
            total_answer_ms=1500,
            confidence={"level": "high"},
            sources=[],
        )
        is False
    )
    assert (
        answer_qualifies_for_fast_success_reinforcement(
            total_answer_ms=2500,
            confidence={"level": "high"},
            sources=[{"file_name": "x.md"}],
        )
        is False
    )


def test_adaptive_plan_trust_summary_counts_route_signals():
    from app.ui.adaptive_daily_plan_layout import adaptive_plan_trust_summary

    summary = adaptive_plan_trust_summary(
        {"seed_topic": "RAG", "new_reviews_balance": "reviews 1/3 · gaps 1/3 · new 1/3"},
        [
            {"type": "review", "concept": "Chunking", "duration_min": 7, "xp_base": 25},
            {"type": "gap", "concept": "Retrieval", "duration_min": 10, "xp_base": 40, "current_mastery": 0.35},
            {"type": "new", "concept": "Reranking", "duration_min": 12, "xp_base": 35},
        ],
    )

    assert summary["counts"] == {"review": 1, "gap": 1, "new": 1}
    assert summary["total_duration"] == 29
    assert summary["total_xp"] == 100
    assert summary["avg_mastery"] == 0.35
    assert "первый шаг: review: Chunking" in summary["signals"]
    assert "seed: RAG" in summary["signals"]


def test_build_redacted_interactive_quiz_generation_debug():
    from app.ui.interactive_quiz import build_redacted_interactive_quiz_generation_debug

    d = build_redacted_interactive_quiz_generation_debug(
        learning_mode_ui="auto",
        effective_learning_mode="exam_prep",
        topic_guess="x" * 60,
        concepts_count=10,
        learned_count=3,
        recent_history_chars=120,
        n_questions=3,
        gen_id="abcdefgh-ijkl",
    )
    assert d["n_questions_requested"] == 3
    assert "…" in d["topic_guess_redacted"]
    assert d["gen_id_prefix"] == "abcdefgh"


def test_format_quiz_question_type_distribution():
    from app.ui.interactive_quiz import format_quiz_question_type_distribution

    assert "50%" in format_quiz_question_type_distribution({"a": 1, "b": 1}, 2)
    assert format_quiz_question_type_distribution({}, 0) == "нет вопросов"


def test_build_adaptive_plan_redacted_debug():
    from app.ui.adaptive_daily_plan_layout import build_adaptive_plan_redacted_debug

    plan = {
        "date": "2026-01-01",
        "seed_topic": "RAG",
        "new_reviews_balance": "1/2",
        "learner_model": "19.5",
        "entry_state": "actionable",
        "primary_block": {"type": "review", "concept": "c"},
        "concept_graduation": {"n1": "g"},
    }
    blocks: list[dict] = [{"type": "review"}, {"type": "gap"}]
    d = build_adaptive_plan_redacted_debug(plan, blocks)
    assert d["block_type_counts"]["review"] == 1
    assert d["concept_graduation_signals"] == 1


def test_compact_plan_history_for_expert_strips_noise():
    from app.ui.adaptive_daily_plan_layout import compact_plan_history_for_expert

    h = [
        {
            "date": "a",
            "archived_at": "t",
            "focus_review_gap_new": [1, 2, 0],
            "main_concepts": ["x", "y", "z"],
            "total_xp_goal": 100,
            "noise": "drop-me",
        }
    ]
    c = compact_plan_history_for_expert(h, limit=3)
    assert len(c) == 1
    assert "noise" not in c[0]
    assert c[0]["main_concepts"] == ["x", "y", "z"]


def test_flashcard_generate_timeout_scales_with_course_documents():
    from app.ui.flashcards_generate_view import _flashcard_generate_timeout_sec

    assert _flashcard_generate_timeout_sec(scope="document") == 180
    assert _flashcard_generate_timeout_sec(scope="course", source_path_count=5) == 420


def test_flashcard_generate_timeout_detection():
    import requests

    from app.ui.flashcards_generate_view import _is_read_timeout_error

    assert _is_read_timeout_error(requests.exceptions.ReadTimeout("boom"))
    assert _is_read_timeout_error(ConnectionError("HTTPConnectionPool read timed out. (read timeout=120)"))
    assert not _is_read_timeout_error(ValueError("bad payload"))


def test_format_duration_sec_for_flashcard_summary():
    from app.ui.flashcards_generate_view import _format_duration_sec

    assert _format_duration_sec(45) == "45 с"
    assert _format_duration_sec(125) == "2:05"


def test_course_card_tags_include_scope_metadata():
    from app.ui.flashcards_generate_view import _course_card_tags

    tags = _course_card_tags(
        base_tags="basics",
        course_id="c1",
        folder_rel="courses/ai",
        source_path="docs/intro.md",
    )
    assert "basics" in tags
    assert "course:c1" in tags
    assert "folder:courses/ai" in tags
    assert "source:docs/intro.md" in tags
