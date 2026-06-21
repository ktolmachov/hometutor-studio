"""Offline misroute policy learner — unit tests (sp1, no router hook)."""
from __future__ import annotations

import importlib
import inspect
import time
from datetime import datetime, timedelta, timezone

import pytest

from app.config import reset_settings_cache
from app.ssr_feedback_collection import weak_concept_sha256
from app.ssr_misroute_policy import (
    MisroutePolicyAdjustment,
    bucket_passes_misroute_gate,
    build_misroute_policy_audit_ru,
    compute_offline_misroute_adjustments,
    misroute_bucket_key,
    refresh_misroute_policy_weights_from_buckets,
    reject_decay_weight,
)
from app.user_state_ssr_feedback import aggregate_ssr_misroute_feedback_buckets, record_ssr_recommendation_feedback
import app.user_state as user_state


@pytest.fixture(autouse=True)
def _isolated_policy_weights(tmp_path, monkeypatch):
    path = tmp_path / "ssr_misroute_policy_weights.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("app.ssr_misroute_policy._WEIGHTS_PATH", path)


@pytest.fixture()
def iso_db(tmp_path, monkeypatch):
    db = tmp_path / "learn.db"
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
    created_at: str | None = None,
) -> int:
    ts = created_at or _iso(days_ago)
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


def test_misroute_bucket_key_format():
    wc = weak_concept_sha256("x")
    key = misroute_bucket_key(hint_kind="safe_default", primary_nav="safe_tutor_5min", weak_concept_sha256=wc)
    assert key == f"safe_default|safe_tutor_5min|{wc}"


def test_reject_decay_weight_linear():
    assert reject_decay_weight(age_days=0.0, decay_days=7) == 1.0
    assert reject_decay_weight(age_days=3.5, decay_days=7) == pytest.approx(0.5)
    assert reject_decay_weight(age_days=8.0, decay_days=7) == 0.0


def test_three_rejects_with_retention_yields_adjustment(iso_db):
    wc = weak_concept_sha256("topic-a")
    for _ in range(3):
        _seed_row(action="reject", weak="topic-a", days_ago=0.01)
    _seed_row(action="reject", weak="topic-a", explanation_outcome="helpful", days_ago=0.005)

    since = _iso(days_ago=10)
    buckets = aggregate_ssr_misroute_feedback_buckets(since_iso=since)
    weights, adj = compute_offline_misroute_adjustments(
        hint_kind="mastery_stale",
        primary_nav="tutor_weak_gap",
        weak_concept_sha256=wc,
        buckets=buckets,
        decay_days=7,
    )
    assert isinstance(adj, MisroutePolicyAdjustment)
    assert adj.adjusted_primary_nav == "qa_continue"
    assert adj.original_primary_nav == "tutor_weak_gap"
    assert weights


def test_two_rejects_no_adjustment(iso_db):
    wc = weak_concept_sha256("topic-b")
    _seed_row(action="reject", weak="topic-b", days_ago=0.01)
    _seed_row(action="reject", weak="topic-b", explanation_outcome="helpful", days_ago=0.005)

    buckets = aggregate_ssr_misroute_feedback_buckets(since_iso=_iso(days_ago=10))
    _, adj = compute_offline_misroute_adjustments(
        hint_kind="mastery_stale",
        primary_nav="tutor_weak_gap",
        weak_concept_sha256=wc,
        buckets=buckets,
    )
    assert adj is None


def test_contradictory_accept_blocks_adjustment(iso_db):
    wc = weak_concept_sha256("topic-c")
    for _ in range(4):
        _seed_row(action="reject", weak="topic-c", days_ago=0.0)
    _seed_row(action="accept", weak="topic-c", explanation_outcome="helpful", days_ago=0.0)

    buckets = aggregate_ssr_misroute_feedback_buckets(since_iso=_iso(days_ago=10))
    reject_bucket = next(b for b in buckets if b["primary_nav"] == "tutor_weak_gap")
    passes, _, reason = bucket_passes_misroute_gate(
        bucket=reject_bucket,
        all_rows=reject_bucket["rows"],
        decay_days=7,
    )
    assert passes is False
    assert reason == "contradictory_accept"
    _, adj = compute_offline_misroute_adjustments(
        hint_kind="mastery_stale",
        primary_nav="tutor_weak_gap",
        weak_concept_sha256=wc,
        buckets=buckets,
    )
    assert adj is None


def test_rejects_without_retention_blocked(iso_db):
    for _ in range(4):
        _seed_row(action="reject", weak="topic-e", days_ago=0.0)

    buckets = aggregate_ssr_misroute_feedback_buckets(since_iso=_iso(days_ago=10))
    passes, _, reason = bucket_passes_misroute_gate(
        bucket=buckets[0],
        all_rows=buckets[0]["rows"],
        decay_days=7,
    )
    assert passes is False
    assert reason == "no_retention"


def test_alternate_accept_within_48h_counts_as_retention(iso_db):
    base = datetime.now(timezone.utc) - timedelta(seconds=30)
    for i in range(4):
        _seed_row(
            action="reject",
            weak="topic-d",
            created_at=(base + timedelta(seconds=i)).isoformat(),
        )
    _seed_row(
        action="accept",
        weak="topic-d",
        primary_nav="qa_continue",
        created_at=(base + timedelta(minutes=10)).isoformat(),
    )

    buckets = aggregate_ssr_misroute_feedback_buckets(since_iso=_iso(days_ago=10))
    reject_bucket = next(b for b in buckets if b["primary_nav"] == "tutor_weak_gap")
    all_rows = [r for b in buckets for r in b["rows"]]
    passes, _, reason = bucket_passes_misroute_gate(
        bucket=reject_bucket,
        all_rows=all_rows,
        decay_days=7,
    )
    assert passes is True, reason


def test_empty_db_no_buckets(iso_db):
    buckets = aggregate_ssr_misroute_feedback_buckets(since_iso=_iso(days_ago=1))
    assert buckets == []
    _, adj = compute_offline_misroute_adjustments(
        hint_kind="safe_default",
        primary_nav="safe_tutor_5min",
        buckets=buckets,
    )
    assert adj is None


def test_defer_only_no_weight_change(iso_db):
    _seed_row(action="defer", days_ago=0.1)
    _seed_row(action="defer", days_ago=0.2)
    buckets = aggregate_ssr_misroute_feedback_buckets(since_iso=_iso(days_ago=10))
    weights = refresh_misroute_policy_weights_from_buckets(buckets=buckets)
    assert weights == {}
    passes, _, reason = bucket_passes_misroute_gate(
        bucket=buckets[0],
        all_rows=buckets[0]["rows"],
        decay_days=7,
    )
    assert passes is False
    assert reason == "defer_only"


def test_stale_rejects_decay_below_gate(iso_db):
    for i in range(3):
        _seed_row(action="reject", explanation_outcome="helpful", days_ago=6.5 + i * 0.01)

    buckets = aggregate_ssr_misroute_feedback_buckets(since_iso=_iso(days_ago=10))
    passes, _, reason = bucket_passes_misroute_gate(
        bucket=buckets[0],
        all_rows=buckets[0]["rows"],
        decay_days=7,
    )
    assert passes is False
    assert reason == "sparse_rejects"


def test_build_misroute_policy_audit_ru_applied():
    line = build_misroute_policy_audit_ru(
        status="applied",
        reason="gated",
        decay=0.8,
        bucket="mastery_stale|tutor_weak_gap|",
    )
    assert "Коррекция" in line
    assert "misroute_policy=applied" in line


def test_feedback_collection_write_path_has_no_policy_import():
    mod = importlib.import_module("app.ssr_feedback_collection")
    src = inspect.getsource(mod)
    assert "ssr_misroute_policy" not in src


def test_record_ssr_recommendation_feedback_stays_fast(iso_db):
    t0 = time.perf_counter()
    record_ssr_recommendation_feedback(
        action="reject",
        hint_kind="mastery_stale",
        primary_nav="tutor_weak_gap",
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 250.0


def test_aggregate_sanitizes_invalid_enums(iso_db):
    record_ssr_recommendation_feedback(
        action="reject",
        hint_kind="not_a_hint",
        primary_nav="tutor_weak_gap",
    )
    buckets = aggregate_ssr_misroute_feedback_buckets(since_iso=_iso(days_ago=1))
    assert buckets == []
