"""US-20.x Smart Study Router — детерминированный контракт без Streamlit runtime для UI-кнопок.

Also tests US-20.13 Local Route Simulator (what-if preview).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, get_args

import pytest

from app.ui.adaptive_plan_card import (
    SmartStudyRouterHintKind,
    apply_smart_study_steering_preference,
    build_smart_study_evidence_items,
    build_smart_study_evidence_ledger_lines,
    build_smart_study_recommendation,
    smart_study_contrastive_explanation,
    smart_study_why_not_others_ru,
    SmartStudyRecommendation,
)
from app.ui.adaptive_plan_llm_enrichment import (
    _SSR_LLM_EXPLANATION_CACHE,
    _generate_llm_explanation,
    _ssr_why_now_for_card,
)
from app.ssr_context_builder import build_ssr_llm_learning_context as _build_ssr_llm_learning_context
from app.ui.tutor_chat_render import (
    apply_source_trust_smart_study_overlay,
    apply_smart_study_defer_alternate,
    compact_smart_study_router_trace_lines,
    effective_tutor_trust_signals,
    qa_sources_trust_low,
    resolve_smart_study_defer_for_session,
    tutor_trust_signals_low,
)


@pytest.fixture(autouse=True)
def _mute_ssr_llm_profiling(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.ssr_llm_profiling as ssr_prof

    monkeypatch.setattr(ssr_prof, "record_ssr_llm_profile", lambda **_kw: None)


def test_cards_due_beats_sm2_and_quiz_failed_signals():
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=2,
        sm2_due_n=9,
        quiz_feedback_status="failed",
        has_tutor_resume=True,
        tutor_topic="Topic",
    )
    assert rec.hint_kind == "cards_due"
    assert rec.primary_label_ru == "Повторить"
    assert "2" in rec.why_now_ru and "карточки" in rec.why_now_ru
    assert rec.primary_nav == "flashcards_review"
    assert "долг удержания" in rec.route_pedagogy_ru.lower()
    assert 2 <= len(rec.secondaries) <= 4


def test_sm2_due_when_no_flashcards():
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=3,
        quiz_feedback_status="failed",
    )
    assert rec.hint_kind == "sm2_due"
    assert rec.primary_nav == "sm2_tutor"
    assert "долг удержания" in rec.route_pedagogy_ru.lower()


def test_recovery_ladder_quiz_failed_default_hint_primary():
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        quiz_feedback_status="incorrect",
        has_tutor_resume=True,
        tutor_topic="Alpha",
    )
    assert rec.hint_kind == "quiz_failed"
    assert rec.primary_label_ru == "Короткая подсказка по ошибке"
    assert "лестниц" in rec.why_now_ru.lower()
    assert rec.primary_nav == "qa_continue"
    assert "восстановление слабого понятия" in rec.route_pedagogy_ru.lower()
    assert "recovery_ladder_step=1" in (rec.ml_audit_ru or "")
    ids_set = {s.action_id for s in rec.secondaries}
    assert {"quiz_nav", "qa_sources", "progress_go", "tutor_simpler"} <= ids_set


def test_recovery_ladder_step_progression_keeps_cards_due_priority():
    quiz_rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=5,
        sm2_due_n=0,
        quiz_feedback_status="failed",
        concept_recovery_ladder_step=11,
        tutor_topic="Topic",
        has_tutor_resume=True,
    )
    assert quiz_rec.hint_kind == "cards_due"
    assert quiz_rec.primary_nav == "flashcards_review"

    hint = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        quiz_feedback_status="failed",
        concept_recovery_ladder_step=2,
        tutor_topic="Beta",
        has_tutor_resume=True,
    )
    assert hint.primary_nav == "qa_continue"
    assert "шаг 2" in hint.why_now_ru.lower()
    tutor = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        quiz_feedback_status="failed",
        concept_recovery_ladder_step=3,
        tutor_topic="Gamma",
        has_tutor_resume=True,
    )
    assert tutor.primary_nav == "quiz_recovery_tutor"
    varied = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        quiz_feedback_status="failed",
        concept_recovery_ladder_step=4,
        tutor_topic="Delta",
        has_tutor_resume=True,
    )
    assert varied.primary_nav == "tutor_weak_gap"
    assert "Delta" in varied.why_now_ru


def test_recovery_ladder_disabled_restores_legacy_tutor_jump():
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        quiz_feedback_status="incorrect",
        has_tutor_resume=True,
        tutor_topic="Zeta",
        concept_recovery_ladder_enabled=False,
    )
    assert rec.primary_nav == "quiz_recovery_tutor"
    assert "recovery_ladder_step" not in (rec.ml_audit_ru or "")


def test_recovery_ladder_resume_roundtrip_via_helpers():
    from app.smart_study_router import concept_recovery_resume_v1, ladder_step_from_resume_v1

    blob = concept_recovery_resume_v1(3, concept_anchor="  concept x  ")
    assert ladder_step_from_resume_v1(blob) == 3
    bad = dict(blob)
    bad["v"] = 99
    assert ladder_step_from_resume_v1(bad, default=1) == 1


def test_recovery_ladder_normalize_step_clamps_range():
    from app.smart_study_router import normalize_concept_recovery_ladder_step

    assert normalize_concept_recovery_ladder_step(0, default=1) == 1
    assert normalize_concept_recovery_ladder_step("9", default=2) == 4
    assert normalize_concept_recovery_ladder_step("x", default=2) == 2


def test_recovery_ladder_under_source_coverage_guard_keeps_guard_primary_copy():
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        quiz_feedback_status="incorrect",
        has_tutor_resume=True,
        tutor_topic="Tau",
        retrieval_confidence="low",
        source_evidence_count=1,
        concept_recovery_ladder_step=2,
    )
    assert rec.hint_kind == "quiz_failed"
    assert rec.primary_nav == "qa_continue"
    assert "Свериться" in rec.primary_label_ru
    assert "источников" in rec.why_now_ru.lower()
    assert "recovery_ladder_step=2" in (rec.ml_audit_ru or "")
    assert "recovery_ladder_guard_keeps_primary=1" in (rec.ml_audit_ru or "")
    assert rec.secondaries[0].action_id == "tutor_simpler"
    assert "лестниц" in rec.secondaries[0].label_ru.lower()


def test_recovery_ladder_simulator_includes_matching_secondary_line():
    from app.smart_study_route_simulator import simulate_what_if

    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        quiz_feedback_status="incorrect",
        has_tutor_resume=True,
        tutor_topic="Ups",
        concept_recovery_ladder_step=1,
    )
    qa_sec = next(s for s in rec.secondaries if s.action_id == "qa_sources")
    sim = simulate_what_if(rec, "qa_sources")
    assert qa_sec.label_ru in sim.reason_ru


def test_recovery_ladder_metadata_roundtrip_via_pipeline_helpers():
    from app.pipeline_steps import (
        SSR_CONCEPT_RECOVERY_LADDER_KEY_V1,
        merge_concept_recovery_ladder_into_metadata,
        read_concept_recovery_ladder_resume_v1,
    )
    from app.smart_study_recovery_ladder import concept_recovery_resume_v1, ladder_step_from_resume_v1

    metadata: dict = {"trust_block": {"score": 0.8}}
    blob = concept_recovery_resume_v1(3, concept_anchor="Alpha", scope_id="scope-a")
    merge_concept_recovery_ladder_into_metadata(metadata, ladder_resume=blob)
    assert metadata["trust_block"]["score"] == 0.8
    loaded = read_concept_recovery_ladder_resume_v1(metadata)
    assert loaded is not None
    assert ladder_step_from_resume_v1(loaded) == 3
    assert loaded.get("scope_id") == "scope-a"
    assert metadata[SSR_CONCEPT_RECOVERY_LADDER_KEY_V1]["step"] == 3


def test_recovery_ladder_anchor_mismatch_hard_resets_to_step_one():
    from app.smart_study_recovery_ladder import (
        concept_recovery_resume_v1,
        reconcile_concept_recovery_ladder_anchor,
    )

    blob = concept_recovery_resume_v1(3, concept_anchor="Old Topic")
    step, new_blob = reconcile_concept_recovery_ladder_anchor(
        blob,
        current_anchor="New Topic",
        scope_id="scope-b",
    )
    assert step == 1
    assert new_blob is not None
    assert new_blob["step"] == 1
    assert new_blob["anchor"] == "New Topic"
    assert new_blob.get("scope_id") == "scope-b"


def test_recovery_ladder_scope_invalidation_clears_stale_blob():
    from app.pipeline_steps import clear_concept_recovery_ladder_from_metadata, merge_concept_recovery_ladder_into_metadata
    from app.smart_study_recovery_ladder import (
        concept_recovery_resume_v1,
        invalidate_concept_recovery_ladder_on_scope_change,
    )

    blob = concept_recovery_resume_v1(2, concept_anchor="Topic", scope_id="old-scope")
    assert invalidate_concept_recovery_ladder_on_scope_change(blob, active_scope_id="new-scope") is None
    assert invalidate_concept_recovery_ladder_on_scope_change(blob, active_scope_id="old-scope") == blob

    metadata = {"other": 1}
    merge_concept_recovery_ladder_into_metadata(metadata, ladder_resume=blob)
    merge_concept_recovery_ladder_into_metadata(metadata, ladder_resume=None)
    assert "ssr_concept_recovery_ladder_v1" not in metadata
    assert metadata["other"] == 1
    clear_concept_recovery_ladder_from_metadata(metadata)
    assert metadata == {"other": 1}


def test_recovery_ladder_variant_success_predicate():
    from app.smart_study_recovery_ladder import (
        concept_recovery_resume_v1,
        should_clear_ladder_on_variant_quiz_success,
    )

    blob = concept_recovery_resume_v1(4, concept_anchor="Concept A")
    assert should_clear_ladder_on_variant_quiz_success(
        quiz_feedback_status="correct",
        quiz_concept="Concept A",
        ladder_blob=blob,
    )
    assert not should_clear_ladder_on_variant_quiz_success(
        quiz_feedback_status="correct",
        quiz_concept="Concept B",
        ladder_blob=blob,
    )
    assert not should_clear_ladder_on_variant_quiz_success(
        quiz_feedback_status="incorrect",
        quiz_concept="Concept A",
        ladder_blob=blob,
    )
    early = concept_recovery_resume_v1(2, concept_anchor="Concept A")
    assert not should_clear_ladder_on_variant_quiz_success(
        quiz_feedback_status="ok",
        quiz_concept="Concept A",
        ladder_blob=early,
    )


def test_answer_ready_without_higher_priority_signals():
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        quiz_feedback_status=None,
        has_tutor_resume=False,
        has_last_answer_qa=True,
    )
    assert rec.hint_kind == "answer_ready"
    assert rec.primary_label_ru == "Учить тему"
    assert "быстрый ответ" in rec.why_now_ru.lower()
    assert rec.primary_nav == "qa_continue"
    assert "новое обучение" in rec.route_pedagogy_ru.lower()


def test_mastery_stale_via_weak_concept():
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        has_last_answer_qa=False,
        has_reading_resume=False,
        first_weak_concept="Entropy",
    )
    assert rec.hint_kind == "mastery_stale"
    assert rec.primary_nav == "tutor_weak_gap"
    assert "Entropy" in rec.why_now_ru


def test_adaptive_plan_surface_uses_plan_block_when_clear():
    block = {"type": "gap", "concept": "RAG"}
    rec = build_smart_study_recommendation(
        surface="adaptive_plan",
        flashcard_due_n=0,
        sm2_due_n=0,
        plan_primary_block=block,
        has_tutor_resume=True,
        tutor_topic="Chat",
    )
    assert rec.hint_kind == "adaptive_plan"
    assert rec.primary_nav == "plan_block_tutor"


def test_home_surface_ignores_plan_block_without_queues():
    block = {"type": "new", "concept": "X"}
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        plan_primary_block=block,
        has_last_answer_qa=True,
    )
    assert rec.hint_kind == "answer_ready"


def test_cards_due_singular_ru():
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=1,
        sm2_due_n=0,
    )
    assert rec.hint_kind == "cards_due"
    assert "1" in rec.why_now_ru
    assert "карточка" in rec.why_now_ru


def test_secondaries_always_include_quiz_and_dashboard_slots():
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        has_last_answer_qa=False,
        has_reading_resume=False,
        first_weak_concept=None,
    )
    ids = {s.action_id for s in rec.secondaries}
    assert "quiz_nav" in ids
    assert "progress_go" in ids


def test_qa_sources_trust_low_from_confidence_and_empty_sources():
    assert qa_sources_trust_low({"answer": "x", "confidence": {"level": "low"}, "sources": []})
    assert qa_sources_trust_low({"answer": "body", "confidence": {}, "sources": []})
    assert not qa_sources_trust_low({"answer": "body", "confidence": {"level": "high"}, "sources": [{"file_name": "a.md"}]})


def test_tutor_trust_signals_low():
    assert tutor_trust_signals_low({"confidence": "low", "sources_used": 2})
    assert tutor_trust_signals_low({"confidence": "medium", "sources_used": 0, "coverage_warning": "weak"})
    assert not tutor_trust_signals_low({"confidence": "high", "sources_used": 3})


def test_effective_tutor_trust_signals_prefers_persisted_sources():
    trust = {"confidence": "medium", "sources_used": 0, "coverage_warning": "weak"}
    sources = [{"relative_path": "a.md"}, {"relative_path": "b.md"}]

    effective = effective_tutor_trust_signals(trust, sources)

    assert effective["sources_used"] == 2
    assert effective["confidence"] == "medium"
    assert effective["coverage_warning"] is None
    assert trust["sources_used"] == 0


def test_source_trust_overlay_skips_priority_queues():
    base = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=1,
        sm2_due_n=0,
    )
    low_ans = {"answer": "a", "confidence": {"level": "low"}, "sources": []}
    o, applied = apply_source_trust_smart_study_overlay(base, last_answer=low_ans, tutor_trust=None)
    assert applied is False
    assert o.primary_label_ru == base.primary_label_ru


def test_source_trust_overlay_answer_ready_changes_copy_and_keeps_pedagogy():
    base = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        has_last_answer_qa=True,
    )
    assert base.hint_kind == "answer_ready"
    ped_before = base.route_pedagogy_ru
    low_ans = {"question": "q", "answer": "a", "confidence": {"level": "low"}, "sources": []}
    o, applied = apply_source_trust_smart_study_overlay(base, last_answer=low_ans, tutor_trust=None)
    assert applied
    assert o.primary_nav == "qa_continue"
    assert "источник" in o.primary_label_ru.lower()
    assert o.route_pedagogy_ru == ped_before


def test_defer_alternate_and_trace():
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        has_last_answer_qa=True,
    )
    alt = apply_smart_study_defer_alternate(rec)
    assert alt.primary_nav != rec.primary_nav or alt.primary_label_ru != rec.primary_label_ru
    lines = compact_smart_study_router_trace_lines(
        alt,
        trust_branch_applied=True,
        defer_applied=True,
    )
    assert "policy=source_trust_branch" in lines
    assert "policy=skip_with_memory_alternate" in lines


def test_resolve_defer_pending_matches():
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        has_last_answer_qa=True,
    )
    pending = {"hint_kind": rec.hint_kind, "primary_nav": rec.primary_nav}
    out, ok = resolve_smart_study_defer_for_session(rec, pending)
    assert ok
    assert out.primary_nav != rec.primary_nav or out.why_now_ru != rec.why_now_ru


def test_resolve_defer_pending_stale():
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        has_last_answer_qa=True,
    )
    out, ok = resolve_smart_study_defer_for_session(rec, {"hint_kind": "cards_due", "primary_nav": "flashcards_review"})
    assert not ok
    assert out == rec


def test_us20_7_contrastive_line_primary_paths():
    c1 = smart_study_contrastive_explanation(
        build_smart_study_recommendation(
            surface="home",
            flashcard_due_n=2,
            sm2_due_n=1,
        )
    )
    assert "карточ" in c1.lower() or "очеред" in c1.lower() or "важне" in c1.lower()

    c2 = smart_study_contrastive_explanation(
        build_smart_study_recommendation(
            surface="home",
            flashcard_due_n=0,
            sm2_due_n=2,
        )
    )
    assert "sm-2" in c2.lower() or "концепт" in c2.lower()

    c3 = smart_study_contrastive_explanation(
        build_smart_study_recommendation(surface="home", flashcard_due_n=0, sm2_due_n=0)
    )
    assert "сравнения" in c3.lower() or "сигнал" in c3.lower()


def test_us20_7_contrastive_trust_branch_label():
    base = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        has_last_answer_qa=True,
    )
    assert base.hint_kind == "answer_ready"
    trusted = replace(base, primary_label_ru="Сначала проверить источники в быстром ответе")
    txt = smart_study_contrastive_explanation(trusted)
    assert "quiz" in txt.lower() or "интерактивн" in txt.lower()
    assert len(txt) >= 20


def test_us20_7_contrastive_defer_sm2_to_qa():
    base = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=3,
    )
    assert base.hint_kind == "sm2_due"
    deferred = replace(
        base,
        primary_nav="qa_continue",
        primary_label_ru="Сверить факты в быстром ответе",
        why_now_ru="Отложили повтор концепта — сначала посмотрите выдержки из базы.",
    )
    out = smart_study_contrastive_explanation(deferred)
    assert "слеп" in out.lower() or "свер" in out.lower()


def test_us20_why_not_others_matrix_budget_and_names_four_surfaces():
    """Контрастный текст сознательно именует tutor/quiz/карточки/прогресс для доверия."""
    fixtures: list[tuple[str, SmartStudyRecommendation]] = [
        ("cards_due", build_smart_study_recommendation(surface="home", flashcard_due_n=2)),
        ("sm2_due", build_smart_study_recommendation(surface="home", sm2_due_n=2)),
        ("quiz_failed", build_smart_study_recommendation(surface="home", quiz_feedback_status="failed")),
        (
            "tutor_resume",
            build_smart_study_recommendation(
                surface="home",
                has_tutor_resume=True,
                tutor_topic="Demo",
                has_last_answer_qa=False,
            ),
        ),
        ("answer_ready", build_smart_study_recommendation(surface="home", has_last_answer_qa=True)),
        ("mastery_stale", build_smart_study_recommendation(surface="home", first_weak_concept="Entropy")),
        (
            "adaptive_plan",
            build_smart_study_recommendation(
                surface="adaptive_plan",
                plan_primary_block={"type": "gap", "concept": "RAG"},
            ),
        ),
        ("safe_default", build_smart_study_recommendation(surface="home")),
        (
            "gentle_cards_soften",
            apply_smart_study_steering_preference(
                build_smart_study_recommendation(surface="home", flashcard_due_n=1),
                steering="gentle",
            )[0],
        ),
    ]
    for label, rec in fixtures:
        out = smart_study_why_not_others_ru(rec)
        w = len(out.split())
        assert w <= 85, (label, w, out[:120])
        lo = out.lower()
        assert "quiz" in lo, label
        assert "карточ" in lo, label
        assert "прогресс" in lo, label
        assert ("тьютор" in lo) or ("тютор" in lo), label


def test_us20_8_evidence_ledger_lists_signals_and_marks_unavailable_confidence():
    rows = build_smart_study_evidence_ledger_lines(
        flashcard_due_n=2,
        sm2_due_n=1,
        quiz_feedback_status="failed",
        has_last_answer_qa=True,
        last_answer={"question": "q", "answer": "a"},
        tutor_trust=None,
        defer_applied=True,
        trust_branch_applied=False,
    )
    joined = " ".join(rows)
    assert "2" in joined and "карточ" in joined.lower()
    assert "sm-2" in joined.lower() or "концепт" in joined.lower()
    assert "провал" in joined.lower() or "failed" in joined.lower()
    assert "быстрый ответ" in joined.lower()
    assert "недоступ" in joined.lower() and "confidence" in joined.lower()
    assert "недоступ" in joined.lower() and "тьютор" in joined.lower()
    assert "отлож" in joined.lower() and "актив" in joined.lower()
    assert "source-trust" in joined.lower() and "нет" in joined.lower()
    assert "руль" in joined.lower() and "ssr" in joined.lower()


def test_us20_8_evidence_ledger_shows_qa_confidence_when_present():
    rows = build_smart_study_evidence_ledger_lines(
        flashcard_due_n=0,
        sm2_due_n=0,
        has_last_answer_qa=True,
        last_answer={"answer": "x", "confidence": {"level": "low"}},
    )
    assert any("confidence" in r.lower() and "low" in r.lower() for r in rows)
    assert any("руль" in r.lower() for r in rows)


def test_us20_8_evidence_ledger_can_filter_to_influencing_signals():
    items = build_smart_study_evidence_items(
        flashcard_due_n=0,
        sm2_due_n=2,
        has_last_answer_qa=False,
        trust_branch_applied=False,
    )
    influenced = [item for item in items if item.influenced]
    assert [item.key for item in influenced] == ["sm2_due"]

    rows = build_smart_study_evidence_ledger_lines(
        flashcard_due_n=0,
        sm2_due_n=2,
        has_last_answer_qa=False,
        include_all=False,
    )
    assert rows == ["Очередь концептов SM-2 (локально): 2 к повтору"]


def test_us20_10_steering_new_topic_tradeoff_when_cards_due():
    base = build_smart_study_recommendation(surface="home", flashcard_due_n=1, sm2_due_n=0)
    out, changed = apply_smart_study_steering_preference(base, steering="new_topic")
    assert changed
    assert out.hint_kind == base.hint_kind
    assert out.primary_nav == base.primary_nav
    assert "уступает" in out.why_now_ru.lower() or "новое" in out.why_now_ru.lower()


def test_us20_10_steering_gentle_softens_cards_due_keeps_queue_signal():
    base = build_smart_study_recommendation(surface="home", flashcard_due_n=1)
    out, changed = apply_smart_study_steering_preference(base, steering="gentle")
    assert changed
    assert out.hint_kind == "cards_due"
    assert out.primary_nav == "safe_tutor_5min"
    assert "очередь" in out.why_now_ru.lower()


def test_us20_10_steering_review_first_notes_sm2():
    base = build_smart_study_recommendation(surface="home", flashcard_due_n=0, sm2_due_n=2)
    out, changed = apply_smart_study_steering_preference(base, steering="review_first")
    assert changed
    assert "повтор" in out.why_now_ru.lower()


def test_us20_10_steering_gentle_keeps_quiz_failed_primary():
    base = build_smart_study_recommendation(surface="home", quiz_feedback_status="failed")
    out, changed = apply_smart_study_steering_preference(base, steering="gentle")
    assert changed
    assert out.primary_nav == base.primary_nav
    assert "мягк" in out.why_now_ru.lower()


def test_us20_10_steering_empty_means_baseline():
    base = build_smart_study_recommendation(surface="home", has_last_answer_qa=True)
    out, changed = apply_smart_study_steering_preference(base, steering="")
    assert not changed
    assert out == base


def test_us20_6_router_fixture_harness_covers_all_hint_kinds():
    """Локальная матрица состояний роутера (без Streamlit): подписи и входы в режимы не пустые."""
    all_kinds = set(get_args(SmartStudyRouterHintKind))
    fixtures: list[tuple[str, dict[str, Any]]] = [
        ("cards_due", {"surface": "home", "flashcard_due_n": 1}),
        ("sm2_due", {"surface": "home", "flashcard_due_n": 0, "sm2_due_n": 1}),
        ("quiz_failed", {"surface": "home", "quiz_feedback_status": "failed"}),
        (
            "tutor_resume",
            {
                "surface": "home",
                "has_tutor_resume": True,
                "tutor_topic": "Demo",
                "has_last_answer_qa": False,
                "has_reading_resume": False,
                "first_weak_concept": None,
            },
        ),
        ("answer_ready", {"surface": "home", "has_last_answer_qa": True}),
        ("mastery_stale", {"surface": "home", "first_weak_concept": "Entropy"}),
        (
            "adaptive_plan",
            {
                "surface": "adaptive_plan",
                "plan_primary_block": {"type": "gap", "concept": "RAG"},
            },
        ),
        ("safe_default", {"surface": "home"}),
    ]
    seen: set[str] = set()
    for expected_kind, kw in fixtures:
        rec = build_smart_study_recommendation(**kw)
        assert rec.hint_kind == expected_kind
        seen.add(rec.hint_kind)
        assert rec.primary_label_ru.strip()
        assert rec.why_now_ru.strip()
        assert smart_study_contrastive_explanation(rec).strip()
        why_not_txt = smart_study_why_not_others_ru(rec).strip()
        assert why_not_txt
        assert len(why_not_txt.split()) <= 85
        if rec.hint_kind in ("cards_due", "sm2_due", "quiz_failed", "answer_ready"):
            assert rec.route_pedagogy_ru.strip()
        else:
            assert rec.route_pedagogy_ru == ""
        ids = {s.action_id for s in rec.secondaries}
        assert "quiz_nav" in ids
        assert "progress_go" in ids
        assert {"tutor_simpler", "qa_sources"} & ids
        assert 2 <= len(rec.secondaries) <= 4
        for sec in rec.secondaries:
            assert len(sec.label_ru.strip()) >= 8
    assert seen == all_kinds


def test_ssr_llm_explanation_uses_cache_and_preserves_fallback():
    class _Msg:
        content = (
            "Вчера вы работали с деревьями решений, и сейчас полезно вернуться к карточкам: "
            "локальная очередь уже созрела, а короткий повтор закрепит свежий материал без перегруза."
        )

    class FakeChatResponse:
        message = _Msg()

    class FakeLlm:
        def __init__(self) -> None:
            self.calls = 0

        def chat(self, messages: list, **kwargs: Any) -> FakeChatResponse:
            self.calls += 1
            # System message must carry routing constraints; user message has context.
            all_text = " ".join(m.content for m in messages)
            assert "Не меняй рекомендацию и маршрут" in all_text
            assert kwargs["max_tokens"] <= 220
            return FakeChatResponse()

    _SSR_LLM_EXPLANATION_CACHE.clear()
    rec = build_smart_study_recommendation(surface="home", flashcard_due_n=5)
    llm = FakeLlm()
    context = {
        "last_session_topic": "Деревья решений",
        "last_session_date": "вчера",
        "quiz_score_last_3": "3/5",
        "cards_due_count": 5,
        "weak_concepts_list": ["энтропия"],
    }

    first = _generate_llm_explanation(rec, context, llm=llm, now_monotonic=10.0)
    second = _generate_llm_explanation(rec, context, llm=llm, now_monotonic=20.0)

    assert first == second
    assert "дерев" in first.lower()
    assert llm.calls == 1

    class FailingLlm:
        def chat(self, messages: list, **kwargs: Any) -> str:
            raise RuntimeError("provider down")

    _SSR_LLM_EXPLANATION_CACHE.clear()
    assert _generate_llm_explanation(rec, context, llm=FailingLlm()) == rec.why_now_ru


def test_ssr_llm_explanation_falls_back_when_token_budget_exceeds_hard_limit():
    class _Msg:
        content = "Это объяснение не должно попасть в UI из-за превышения token budget."

    class OverBudgetResponse:
        message = _Msg()
        usage = {"total_tokens": 701}

    class OverBudgetLlm:
        def chat(self, messages: list, **kwargs: Any) -> OverBudgetResponse:
            return OverBudgetResponse()

    _SSR_LLM_EXPLANATION_CACHE.clear()
    rec = build_smart_study_recommendation(surface="home", flashcard_due_n=5)
    context = {
        "last_session_topic": "Деревья решений",
        "last_session_date": "вчера",
        "quiz_score_last_3": "3/5",
        "cards_due_count": 5,
        "weak_concepts_list": ["энтропия"],
    }

    assert _generate_llm_explanation(rec, context, llm=OverBudgetLlm(), now_monotonic=10.0) == rec.why_now_ru
    assert not _SSR_LLM_EXPLANATION_CACHE


def test_ssr_llm_learning_context_parses_ledger_counts():
    ledger = [
        "Очередь flashcards (локально): 4 карточки к повтору",
        "Очередь концептов SM-2 (локально): 2 к повтору",
        "Быстрый ответ (готовность Q&A): да",
    ]
    rec = build_smart_study_recommendation(surface="home", flashcard_due_n=9, sm2_due_n=9)
    ctx = _build_ssr_llm_learning_context(
        rec,
        evidence_ledger=ledger,
        tutor_topic="TopicBeta",
        weak_concept="Entropy",
        primary_topic_hint="AlphaFocus",
    )
    assert ctx["cards_due_count"] == 4
    assert ctx["sm2_due_count"] == 2
    assert ctx["weak_concepts_list"] == "Entropy"
    assert ctx["last_session_topic"] != "нет данных"
    assert "Быстрый ответ" in ctx["local_evidence"]


def test_ssr_why_now_for_card_hits_llm_path():
    messages_seen: list[list] = []

    class _Msg:
        content = "Персонализированное объяснение для SSR."

    class OkResp:
        message = _Msg()

    class OkLlm:
        calls = 0

        def chat(self, messages: list, **kwargs: Any) -> OkResp:
            OkLlm.calls += 1
            messages_seen.append(messages)
            return OkResp()

    _SSR_LLM_EXPLANATION_CACHE.clear()
    llm = OkLlm()
    rec = build_smart_study_recommendation(surface="home", flashcard_due_n=1)
    assert _ssr_why_now_for_card(
        rec,
        evidence_ledger=None,
        tutor_topic=None,
        weak_concept="c1",
        primary_topic_hint=None,
        llm=llm,
        now_monotonic=1.0,
    ).startswith("Персонализированное")
    assert llm.calls == 1
    # System message must contain the routing-immutability constraint
    assert messages_seen
    all_text = " ".join(m.content for m in messages_seen[0])
    assert "Не меняй рекомендацию и маршрут" in all_text


def test_us20_11_outcome_receipt_detects_flashcard_queue_delta():
    from app.ui.resume_cards import compute_ssr_outcome_receipt_lines

    before = {"fc_due": 5, "sm2_due": 1, "weak_top": None, "quiz_fb": None}
    after = {"fc_due": 3, "sm2_due": 1, "weak_top": None, "quiz_fb": None}
    lines, measurable = compute_ssr_outcome_receipt_lines(before, after)
    assert measurable
    assert any("Карточки" in ln for ln in lines)


def test_us20_11_outcome_receipt_empty_when_no_measurable_change():
    from app.ui.resume_cards import compute_ssr_outcome_receipt_lines

    before = {"fc_due": 2, "sm2_due": 2, "weak_top": "A", "quiz_fb": None}
    after = dict(before)
    lines, measurable = compute_ssr_outcome_receipt_lines(before, after)
    assert not measurable
    assert lines == []


def test_confidence_ledger_finalize_prepends_trace_and_weak_gap():
    from app.smart_study_router import finalize_smart_study_confidence_ledger_lines

    base = ["Очередь концептов SM-2 (локально): 2 к повтору"]
    out = finalize_smart_study_confidence_ledger_lines(
        base,
        hint_kind="sm2_due",
        primary_nav="sm2_tutor",
        weak_concept="Entropy",
    )
    assert any("Entropy" in line for line in out)
    assert any("hint_kind=sm2_due" in line and "primary_nav=sm2_tutor" in line for line in out)
    assert any("Очередь концептов SM-2" in line for line in out)


def test_confidence_ledger_finalize_skips_duplicate_trace_or_weak():
    from app.smart_study_router import finalize_smart_study_confidence_ledger_lines

    trace_line = "Детерминированный след маршрута (локально): hint_kind=x; primary_nav=y"
    out = finalize_smart_study_confidence_ledger_lines(
        [trace_line, "Примечание: другая строка"],
        hint_kind="x",
        primary_nav="y",
        weak_concept="Already",
    )
    assert sum(1 for row in out if trace_line == row) == 1
    out_w = finalize_smart_study_confidence_ledger_lines(
        ["Пробел мастерства / тема повторения (локально): Zeta"],
        hint_kind="safe_default",
        primary_nav="safe_tutor_5min",
        weak_concept="Zeta",
    )
    assert sum(1 for row in out_w if row.endswith("Zeta")) == 1


def test_source_coverage_route_guard_quiz_failed_low_confidence_redirects_to_sources():
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        quiz_feedback_status="failed",
        retrieval_confidence="low",
    )
    assert rec.hint_kind == "quiz_failed"
    assert rec.primary_nav == "qa_continue"
    assert "источник" in rec.primary_label_ru.lower() or "свер" in rec.primary_label_ru.lower()
    assert "источник" in rec.why_now_ru.lower() or "индекс" in rec.why_now_ru.lower()
    assert "source_coverage_route_guard=1" in (rec.ml_audit_ru or "")
    ids = {s.action_id for s in rec.secondaries}
    assert "quiz_nav" in ids


def test_source_coverage_route_guard_insufficient_sources_without_low_confidence():
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=3,
        retrieval_confidence="high",
        source_evidence_count=1,
    )
    assert rec.hint_kind == "sm2_due"
    assert rec.primary_nav == "qa_continue"


def test_source_coverage_route_guard_skips_when_trust_signals_ok():
    base = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=2,
        retrieval_confidence="high",
        source_evidence_count=3,
    )
    assert base.primary_nav == "sm2_tutor"


def test_source_coverage_route_guard_keeps_flashcards_primary():
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=2,
        sm2_due_n=3,
        quiz_feedback_status="failed",
        retrieval_confidence="low",
    )
    assert rec.hint_kind == "cards_due"
    assert rec.primary_nav == "flashcards_review"


# ── US-20.13: Local Route Simulator (what-if preview) ──────────────────────


def test_us20_13_simulator_maps_known_secondaries():
    """Each known secondary maps to a different counterfactual label."""
    from app.smart_study_route_simulator import simulate_what_if

    rec = build_smart_study_recommendation(surface="home", flashcard_due_n=2)
    seen: set[str] = set()
    for sec in rec.secondaries:
        result = simulate_what_if(rec, sec.action_id)
        assert result.limitation_reason == ""
        assert result.counterfactual_primary_label_ru.strip()
        assert result.reason_ru.strip()
        seen.add(result.counterfactual_primary_label_ru)
    assert len(seen) >= 2


def test_us20_13_simulator_safe_default_soft_counterfactual():
    """safe_default: известные secondaries дают мягкий counterfactual без «жёсткого» limitation."""
    from app.smart_study_route_simulator import simulate_what_if

    rec = build_smart_study_recommendation(surface="home")
    assert rec.hint_kind == "safe_default"
    result = simulate_what_if(rec, "quiz_nav")
    assert result.limitation_reason == ""
    assert "quiz" in result.counterfactual_primary_label_ru.lower()
    assert "обобщён" in result.reason_ru.lower() or "маршрут" in result.reason_ru.lower()


def test_us20_13_simulator_unknown_secondary():
    """Unknown secondary_action_id returns limitation."""
    from app.smart_study_route_simulator import simulate_what_if

    rec = build_smart_study_recommendation(surface="home", flashcard_due_n=2)
    result = simulate_what_if(rec, "nonexistent_action")
    assert result.limitation_reason
    assert result.counterfactual_primary_label_ru == ""


def test_us20_13_simulator_already_primary():
    """Secondary that maps to current primary shows 'already primary' reason."""
    from app.smart_study_route_simulator import simulate_what_if

    # flashcards_review primary — progress_go maps to flashcards_review
    rec = build_smart_study_recommendation(surface="home", flashcard_due_n=2)
    assert rec.primary_nav == "flashcards_review"
    result = simulate_what_if(rec, "progress_go")
    assert result.counterfactual_primary_label_ru.strip()
    assert "уже" in result.reason_ru.lower() or "основн" in result.reason_ru.lower()


def test_us20_13_simulator_no_mutation():
    """Simulator is a pure function — no side effects, frozen input unchanged."""
    from app.smart_study_route_simulator import simulate_what_if
    from dataclasses import fields as dataclass_fields

    rec = build_smart_study_recommendation(surface="home", flashcard_due_n=2)
    fields_before = {f.name: getattr(rec, f.name) for f in dataclass_fields(rec)}
    result = simulate_what_if(rec, "tutor_simpler")
    fields_after = {f.name: getattr(rec, f.name) for f in dataclass_fields(rec)}
    assert fields_before == fields_after

    # SimulatedRoute is frozen too
    import pytest

    with pytest.raises(AttributeError):
        result.counterfactual_primary_label_ru = "mutated"  # type: ignore[misc]


def test_us20_13_simulator_signals_summary_contains_key_fields():
    """signals_summary includes hint_kind, primary_nav, and why_now_preview."""
    from app.smart_study_route_simulator import simulate_what_if

    rec = build_smart_study_recommendation(surface="home", flashcard_due_n=2)
    result = simulate_what_if(rec, "quiz_nav")
    sig = result.signals_summary
    assert "hint_kind" in sig
    assert "primary_nav" in sig
    assert "why_now_preview" in sig
    assert sig["hint_kind"] == "cards_due"
