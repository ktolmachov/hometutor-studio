from app.due_queue_display import is_soft_recovery_overflow
from app.ui.resume_cards import (
    _due_queue_overflow_text,
    _due_queue_preview_text,
    _due_reason,
    _enrich_resume_recommended_next_with_orchestration,
    due_queue_overflow_caption,
    due_queue_preview_caption,
    is_soft_recovery_overflow as resume_cards_is_soft_recovery_overflow,
    render_tutor_learning_resume_card,
    render_home_continue_unified,
    resolve_tutor_resume_for_home,
    spaced_due_priority_label,
)


def test_due_reason_adds_weak_and_quiz_hints_when_sets_match():
    row = {
        "concept": "Alpha",
        "easiness": 2.5,
        "repetitions": 3,
        "next_review": "2099-01-01T00:00:00+00:00",
    }
    base = _due_reason(row, weak_set=set(), quiz_miss=set())
    assert "плановое повторение" in base
    with_weak = _due_reason(row, weak_set={"Alpha"}, quiz_miss=set())
    assert with_weak == "низкий mastery"
    with_miss = _due_reason(row, weak_set=set(), quiz_miss={"Alpha"})
    assert with_miss == "ошибки в quiz"


def test_due_queue_preview_text_adds_overflow_tail():
    rows = [{"concept": f"Concept {i}"} for i in range(1, 8)]

    text = _due_queue_preview_text(rows, due_count=10)

    assert "Concept 1" in text
    assert "Concept 7" in text
    assert "ещё 3 отложено" in text


def test_due_queue_overflow_text_matches_compact_copy():
    assert _due_queue_overflow_text(due_count=10, shown_count=7) == "ещё 3 отложено"
    assert _due_queue_overflow_text(due_count=7, shown_count=7) == ""


def test_due_queue_preview_text_overflow_120_deferred_caption():
    rows = [{"concept": f"c{i}"} for i in range(7)]
    text = _due_queue_preview_text(rows, due_count=120)
    assert "c0" in text
    assert "ещё 113 отложено" in text


def test_due_queue_overflow_threshold_50_no_soft_recovery_mode():
    assert is_soft_recovery_overflow(50) is False
    assert is_soft_recovery_overflow(51) is True
    assert resume_cards_is_soft_recovery_overflow(120) is True


def test_resume_cards_reexports_due_queue_display_helpers():
    rows = [{"concept": "Alpha"}]
    assert due_queue_preview_caption(rows, 10) == "Alpha · ещё 9 отложено"
    assert due_queue_overflow_caption(120, 7) == "ещё 113 отложено"


def test_tutor_chat_intro_expander_title_includes_overflow(monkeypatch):
    import app.learner_state_scope as learner_scope
    import app.ui.tutor_chat_header as tutor_header

    expander_titles: list[str] = []

    class _Expander:
        def __init__(self, title: str, **_kwargs: object) -> None:
            expander_titles.append(str(title))

        def __enter__(self) -> "_Expander":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

    monkeypatch.setattr(
        "app.knowledge_service.get_active_knowledge_graph",
        lambda: "kg",
    )
    monkeypatch.setattr(
        learner_scope,
        "due_reviews_summary_for_kg",
        lambda _kg, preview_limit=7: {
            "count": 120,
            "overflow_caption": "ещё 113 отложено",
            "hint": "Пора повторить 120 концепций: c0 · ещё 113 отложено",
        },
    )
    monkeypatch.setattr(
        learner_scope,
        "filter_due_reviews_for_kg",
        lambda _kg, limit=7: [{"concept": f"c{i}"} for i in range(limit)],
    )
    monkeypatch.setattr(tutor_header, "_render_panel_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(tutor_header.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(tutor_header.st, "expander", _Expander)
    monkeypatch.setattr(tutor_header.st, "caption", lambda *args, **kwargs: None)

    tutor_header.render_tutor_chat_intro()

    assert expander_titles
    assert "120" in expander_titles[0]
    assert "ещё 113 отложено" in expander_titles[0]


def test_spaced_due_priority_label_uses_priority_score():
    assert spaced_due_priority_label({"priority_score": 8.0}) == "высокий"
    assert spaced_due_priority_label({"priority_score": 3.0}) == "средний"
    assert spaced_due_priority_label({"priority_score": 1.0}) == "спокойный"


def test_enrich_resume_recommended_next_with_orchestration_adds_summary_and_route_focus():
    out = _enrich_resume_recommended_next_with_orchestration(
        {
            "next_action": "Пора повторить",
            "next_action_reason": "Есть due review",
            "suggested_ctas": ["Пора повторить"],
            "new_mastery_estimate": "intermediate",
        },
        {
            "decision": {"route": "due_review", "focus_topic": "Retrieval"},
            "orchestration_state": {
                "current_concept": "RAG",
                "orchestration_phase": "rag_prepare",
                "orchestration_decision_source": "llm",
                "selected_agent": "ConceptExplainer",
                "should_trigger_microquiz": True,
            },
            "policy_clamped": True,
            "policy_clamp_reasons": ["due_review_forced_microquiz"],
        },
    )

    assert out["orchestration_route"] == "due_review"
    assert out["orchestration_focus"] == "RAG"
    assert isinstance(out["orchestration_summary"], list)
    assert {"label": "Фаза пайплайна", "value": "rag prepare"} in out["orchestration_summary"]
    assert {"label": "Micro-quiz", "value": "да"} in out["orchestration_summary"]


def test_resolve_tutor_resume_for_home_positive_branch_keeps_resume_payload():
    snap = {
        "session_id": "sess-1",
        "topic": "RAG",
        "last_action_label": "Получен ответ тьютора",
        "due_reviews_count": 3,
        "index_version": "idx-v1",
    }
    effective, stale = resolve_tutor_resume_for_home(snap, current_index_version="idx-v1")
    assert stale is False
    assert effective is not None
    assert effective["topic"] == "RAG"
    assert effective["last_action_label"] == "Получен ответ тьютора"
    assert effective["due_reviews_count"] == 3


def test_resolve_tutor_resume_for_home_negative_branch_drops_stale_resume():
    # Assumption: stale means only index-version mismatch (existing behavior).
    snap = {
        "session_id": "sess-1",
        "topic": "RAG",
        "last_action_label": "Получен ответ тьютора",
        "due_reviews_count": 3,
        "index_version": "idx-old",
    }
    effective, stale = resolve_tutor_resume_for_home(snap, current_index_version="idx-new")
    assert stale is True
    assert effective is None


def test_resolve_tutor_resume_for_home_none_current_index_keeps_resume():
    snap = {
        "session_id": "sess-1",
        "topic": "RAG",
        "last_action_label": "Получен ответ тьютора",
        "due_reviews_count": 3,
        "index_version": "idx-old",
    }
    effective, stale = resolve_tutor_resume_for_home(snap, current_index_version=None)
    assert stale is False
    assert effective is not None
    assert effective["session_id"] == "sess-1"


def test_render_home_continue_unified_shows_short_due_queue(monkeypatch):
    class _Ctx:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    import app.ui.continuity_bridge as continuity_bridge
    import app.ui.resume_cards as resume_cards

    captions: list[str] = []
    due_rows = [{"concept": f"Concept {i}"} for i in range(1, 8)]

    monkeypatch.setattr(resume_cards, "get_active_knowledge_graph", lambda: "kg")
    monkeypatch.setattr(resume_cards, "count_due_reviews_for_kg", lambda _kg: 10)
    monkeypatch.setattr(
        resume_cards,
        "filter_due_reviews_for_kg",
        lambda _kg, limit=7: due_rows[:limit],
    )
    monkeypatch.setattr(resume_cards.user_state, "get_tutor_learning_resume", lambda: None)
    monkeypatch.setattr(resume_cards.user_state, "get_latest_resume", lambda: None)
    monkeypatch.setattr(resume_cards.user_state, "count_due_flashcards", lambda: 0)
    monkeypatch.setattr(resume_cards, "index_version_label", lambda _stats: "idx-v1")
    monkeypatch.setattr(
        continuity_bridge,
        "guided_primary_home_cta_ru",
        lambda **kwargs: ("ÐŸÐ¾Ñ€Ð° Ð¿Ð¾Ð²Ñ‚Ð¾Ñ€Ð¸Ñ‚ÑŒ", "due_review"),
    )
    monkeypatch.setattr(
        continuity_bridge,
        "home_continue_priority_lines_ru",
        lambda **kwargs: ("Ð“Ð»Ð°Ð²Ð½Ñ‹Ð¹ ÑˆÐ°Ð³", ""),
    )
    monkeypatch.setattr(continuity_bridge, "due_reviews_home_teaser_ru", lambda _n: "")
    monkeypatch.setattr(resume_cards.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(resume_cards.st, "caption", lambda text, *args, **kwargs: captions.append(str(text)))
    monkeypatch.setattr(resume_cards.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(resume_cards.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(resume_cards.st, "rerun", lambda: None)
    monkeypatch.setattr(
        resume_cards.st,
        "columns",
        lambda spec, **_kwargs: tuple(_Ctx() for _ in (spec if isinstance(spec, list) else range(int(spec)))),
    )
    monkeypatch.setattr(resume_cards.st, "button", lambda *args, **kwargs: False)

    render_home_continue_unified(index_stats=None)

    assert any("Короткая очередь:" in text for text in captions)
    assert any("ещё 3 отложено" in text for text in captions)


def test_render_tutor_learning_resume_card_handles_empty_due_preview(monkeypatch):
    class _Ctx:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    import app.ui.resume_cards as resume_cards

    captions: list[str] = []

    monkeypatch.setattr(
        resume_cards.user_state,
        "get_tutor_learning_resume",
        lambda: {
            "session_id": "sess-1",
            "topic": "RAG",
            "last_action_label": "ÐŸÐ¾Ð»ÑƒÑ‡ÐµÐ½ Ð¾Ñ‚Ð²ÐµÑ‚ Ñ‚ÑŒÑŽÑ‚Ð¾Ñ€Ð°",
            "due_reviews_count": 4,
            "index_version": "idx-v1",
        },
    )
    monkeypatch.setattr(resume_cards, "get_active_knowledge_graph", lambda: "kg")
    monkeypatch.setattr(resume_cards, "filter_due_reviews_for_kg", lambda _kg, limit=7: [])
    monkeypatch.setattr(resume_cards, "index_version_label", lambda _stats: "idx-v1")
    monkeypatch.setattr(resume_cards.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(resume_cards.st, "caption", lambda text, *args, **kwargs: captions.append(str(text)))
    monkeypatch.setattr(resume_cards.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(resume_cards.st, "columns", lambda *_args, **_kwargs: (_Ctx(), _Ctx(), _Ctx()))
    monkeypatch.setattr(resume_cards.st, "button", lambda *args, **kwargs: False)

    render_tutor_learning_resume_card(index_stats=None)

    assert any("Очередь повторений скоро обновится" in text for text in captions)


def test_render_home_continue_unified_uses_single_primary_cta(monkeypatch):
    class _Ctx:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    import app.ui.continuity_bridge as continuity_bridge
    import app.ui.resume_cards as resume_cards

    button_calls: list[tuple[str, str]] = []

    monkeypatch.setattr(resume_cards, "get_active_knowledge_graph", lambda: "kg")
    monkeypatch.setattr(resume_cards, "count_due_reviews_for_kg", lambda _kg: 2)
    monkeypatch.setattr(resume_cards, "filter_due_reviews_for_kg", lambda _kg, limit=1: [])
    monkeypatch.setattr(
        resume_cards.user_state,
        "get_tutor_learning_resume",
        lambda: {
            "session_id": "sess-1",
            "topic": "RAG",
            "last_action_label": "Получен ответ тьютора",
            "due_reviews_count": 2,
            "index_version": "idx-v1",
        },
    )
    monkeypatch.setattr(resume_cards.user_state, "get_latest_resume", lambda: None)
    monkeypatch.setattr(resume_cards.user_state, "count_due_flashcards", lambda: 0)
    monkeypatch.setattr(resume_cards, "index_version_label", lambda _stats: "idx-v1")
    monkeypatch.setattr(
        continuity_bridge,
        "guided_primary_home_cta_ru",
        lambda **kwargs: ("Продолжить", "resume"),
    )
    monkeypatch.setattr(
        continuity_bridge,
        "home_continue_priority_lines_ru",
        lambda **kwargs: ("Главный шаг", ""),
    )
    monkeypatch.setattr(continuity_bridge, "due_reviews_home_teaser_ru", lambda _n: "")
    monkeypatch.setattr(resume_cards.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(resume_cards.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(resume_cards.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(resume_cards.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(resume_cards.st, "rerun", lambda: None)
    monkeypatch.setattr(
        resume_cards.st,
        "columns",
        lambda spec, **_kwargs: tuple(_Ctx() for _ in (spec if isinstance(spec, list) else range(int(spec)))),
    )
    monkeypatch.setattr(
        resume_cards.st,
        "button",
        lambda label, **kwargs: button_calls.append((label, str(kwargs.get("key") or ""))) or False,
    )

    render_home_continue_unified(index_stats=None)

    primary = [call for call in button_calls if call[1] == "home_continue_primary"]
    assert len(primary) == 1
    assert primary[0][0] == "Продолжить"
