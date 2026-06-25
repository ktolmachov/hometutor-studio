"""Integration tests for SSR L5 misroute policy learning (sp3)."""
from __future__ import annotations

import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from app.config import reset_settings_cache
from app.smart_study_recommendation import SmartStudyRecommendation, SmartStudySecondaryAction
from app.ssr_feedback_collection import weak_concept_sha256
from app.ssr_misroute_policy import apply_ssr_misroute_policy_if_enabled
from app.user_state_ssr_feedback import record_ssr_recommendation_feedback
import app.user_state as user_state


@pytest.fixture(autouse=True)
def _isolated_policy_weights(tmp_path, monkeypatch):
    path = tmp_path / "ssr_misroute_policy_weights.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("app.ssr_misroute_policy._WEIGHTS_PATH", path)


@pytest.fixture()
def iso_db(tmp_path, monkeypatch):
    db = tmp_path / "policy.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()
    yield db


def _iso(days_ago: float = 0.0) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.isoformat()


def _seed_row(
    *,
    action: str,
    hint_kind: str = "mastery_stale",
    primary_nav: str = "tutor_weak_gap",
    weak: str | None = "algebra",
    explanation_outcome: str | None = None,
    days_ago: float = 0.0,
) -> int:
    ts = _iso(days_ago)
    wc = weak_concept_sha256(weak)

    def _work(conn):
        cur = conn.execute(
            """
            INSERT INTO ssr_recommendation_feedback (
                action, hint_kind, primary_nav, weak_concept_sha256,
                why_now_len, explanation_outcome, latency_ms, session_key_prefix, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (action, hint_kind, primary_nav, wc, 0, explanation_outcome, None, None, ts),
        )
        conn.commit()
        return int(cur.lastrowid or 0)

    return user_state._with_db(_work, write=True)


def _rule(
    *,
    hint_kind: str = "mastery_stale",
    primary_nav: str = "tutor_weak_gap",
) -> SmartStudyRecommendation:
    return SmartStudyRecommendation(
        hint_kind=hint_kind,  # type: ignore[arg-type]
        primary_label_ru="Разобрать слабое место",
        why_now_ru="Тест",
        primary_nav=primary_nav,  # type: ignore[arg-type]
        secondaries=(
            SmartStudySecondaryAction(action_id="sources", label_ru="Источники"),
        ),
    )


def _enable_learning(monkeypatch) -> None:
    monkeypatch.setenv("SSR_MISROUTE_POLICY_LEARNING_ENABLED", "true")
    monkeypatch.setenv("SSR_MISROUTE_POLICY_DECAY_DAYS", "7")
    reset_settings_cache()


def test_prod_import_path_sp1_sp2():
    from app.smart_study_router import build_smart_study_recommendation  # noqa: F401
    from app.ssr_misroute_policy import compute_offline_misroute_adjustments  # noqa: F401

    assert callable(build_smart_study_recommendation)
    assert callable(apply_ssr_misroute_policy_if_enabled)
    assert callable(compute_offline_misroute_adjustments)


def test_hook_flag_off_preserves_rule(iso_db, monkeypatch):
    monkeypatch.setenv("SSR_MISROUTE_POLICY_LEARNING_ENABLED", "false")
    reset_settings_cache()
    for _ in range(3):
        _seed_row(action="reject", days_ago=0.01)
    rule = _rule()
    out = apply_ssr_misroute_policy_if_enabled(rule, weak_concept_sha256=weak_concept_sha256("algebra"))
    assert out == rule
    assert not out.ml_audit_ru


def test_hook_hard_queue_never_overrides(monkeypatch):
    _enable_learning(monkeypatch)
    rule = _rule(hint_kind="cards_due", primary_nav="flashcards_review")
    out = apply_ssr_misroute_policy_if_enabled(rule)
    assert out.primary_nav == "flashcards_review"
    assert out.hint_kind == "cards_due"
    assert "Политика обучения" in out.ml_audit_ru
    assert "quiz" in out.ml_audit_ru.lower()


def test_hook_gated_bucket_adjusts_primary_nav(iso_db, monkeypatch):
    _enable_learning(monkeypatch)
    wc = weak_concept_sha256("topic-int")
    for _ in range(3):
        _seed_row(action="reject", weak="topic-int", days_ago=0.01)
    _seed_row(action="reject", weak="topic-int", explanation_outcome="helpful", days_ago=0.005)

    rule = _rule(primary_nav="tutor_weak_gap")
    out = apply_ssr_misroute_policy_if_enabled(rule, weak_concept_sha256=wc)
    assert out.hint_kind == "mastery_stale"
    assert out.primary_nav == "qa_continue"
    assert "applied" in out.ml_audit_ru


def test_hook_sparse_feedback_skips_with_audit(iso_db, monkeypatch):
    _enable_learning(monkeypatch)
    _seed_row(action="reject", days_ago=0.01)
    rule = _rule()
    wc = weak_concept_sha256("sparse")
    out = apply_ssr_misroute_policy_if_enabled(rule, weak_concept_sha256=wc)
    assert out.primary_nav == "tutor_weak_gap"
    assert "rule-only" in out.ml_audit_ru or "недостаточно" in out.ml_audit_ru


def test_policy_adaptation_accuracy_on_labeled_fixtures(iso_db, monkeypatch):
    """Contract primary metric: >= 0.75 on labeled gate outcomes."""
    _enable_learning(monkeypatch)
    cases: list[tuple[str, bool]] = []

    # Case 1: gated — expect adjustment
    wc1 = weak_concept_sha256("acc-a")
    for _ in range(3):
        _seed_row(action="reject", weak="acc-a", days_ago=0.02)
    _seed_row(action="reject", weak="acc-a", explanation_outcome="helpful", days_ago=0.01)
    out1 = apply_ssr_misroute_policy_if_enabled(_rule(), weak_concept_sha256=wc1)
    cases.append(("gated", out1.primary_nav == "qa_continue"))

    # Case 2: sparse — no adjustment
    wc2 = weak_concept_sha256("acc-b")
    _seed_row(action="reject", weak="acc-b", days_ago=0.01)
    out2 = apply_ssr_misroute_policy_if_enabled(_rule(), weak_concept_sha256=wc2)
    cases.append(("sparse", out2.primary_nav == "tutor_weak_gap"))

    # Case 3: contradictory accept — no adjustment
    wc3 = weak_concept_sha256("acc-c")
    for _ in range(4):
        _seed_row(action="reject", weak="acc-c", days_ago=0.01)
    _seed_row(action="accept", weak="acc-c", explanation_outcome="helpful", days_ago=0.0)
    out3 = apply_ssr_misroute_policy_if_enabled(_rule(), weak_concept_sha256=wc3)
    cases.append(("contradictory", out3.primary_nav == "tutor_weak_gap"))

    # Case 4: hard queue — never adjust
    out4 = apply_ssr_misroute_policy_if_enabled(
        _rule(hint_kind="quiz_failed", primary_nav="quiz_recovery_tutor"),
    )
    cases.append(("hard_queue", out4.primary_nav == "quiz_recovery_tutor"))

    correct = sum(1 for _, ok in cases if ok)
    accuracy = correct / len(cases)
    assert accuracy >= 0.75, f"cases={cases} accuracy={accuracy}"


def test_paired_acceptance_uplift_proxy(iso_db, monkeypatch):
    """Secondary metric proxy: learning-on improves nav shift rate vs flag-off on gated bucket."""
    wc = weak_concept_sha256("uplift")
    for _ in range(3):
        _seed_row(action="reject", weak="uplift", days_ago=0.01)
    _seed_row(action="reject", weak="uplift", explanation_outcome="retained", days_ago=0.005)

    monkeypatch.setenv("SSR_MISROUTE_POLICY_LEARNING_ENABLED", "false")
    reset_settings_cache()
    baseline = apply_ssr_misroute_policy_if_enabled(_rule(), weak_concept_sha256=wc)

    _enable_learning(monkeypatch)
    learned = apply_ssr_misroute_policy_if_enabled(_rule(), weak_concept_sha256=wc)

    assert baseline.primary_nav == "tutor_weak_gap"
    assert learned.primary_nav == "qa_continue"


def test_feedback_collection_write_latency_subset(iso_db):
    t0 = time.perf_counter()
    record_ssr_recommendation_feedback(
        action="reject",
        hint_kind="mastery_stale",
        primary_nav="tutor_weak_gap",
        weak_concept_sha256=weak_concept_sha256("lat"),
        why_now_len=10,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 250.0
