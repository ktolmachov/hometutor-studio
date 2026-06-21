"""SSR misroute feedback — SQLite persistence and HTTP surface."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.config import reset_settings_cache
from app.smart_study_router import build_smart_study_recommendation
import app.user_state as user_state
from app.ssr_feedback_collection import (
    record_ssr_misroute_feedback,
    record_ssr_misroute_feedback_api,
    weak_concept_sha256,
)


@pytest.fixture()
def iso_db(tmp_path, monkeypatch):
    db = tmp_path / "fb.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()
    yield db


@pytest.fixture()
def rec():
    return build_smart_study_recommendation(surface="home", flashcard_due_n=1)


def test_weak_concept_sha256_none_for_empty():
    assert weak_concept_sha256(None) is None
    assert weak_concept_sha256("  ") is None


def test_weak_concept_sha256_hex_length():
    d = weak_concept_sha256("algebra")
    assert d is not None
    assert len(d) == 64


def test_record_three_actions_persist(rec, iso_db):
    rid_a = record_ssr_misroute_feedback(
        action="accept", rec=rec, weak_concept="c1", why_now_text="hidden text", session_key="home_x"
    )
    rid_r = record_ssr_misroute_feedback(
        action="reject", rec=rec, weak_concept="c1", why_now_text="also hidden", session_key="home_x"
    )
    rid_d = record_ssr_misroute_feedback(action="defer", rec=rec, session_key="hub")
    assert rid_a > 0 and rid_r > rid_a and rid_d > rid_r

    rows = user_state.list_ssr_recommendation_feedback_recent(limit=10)
    assert len(rows) == 3
    assert rows[0]["action"] == "defer"
    # No PII columns: explanation text must not appear
    for row in rows:
        assert "hidden" not in str(row.values())
        assert "also" not in str(row.values())
        assert row["why_now_len"] >= 0


def test_api_post_valid(rec, iso_db):
    client = TestClient(app)
    body = {
        "action": "accept",
        "hint_kind": str(rec.hint_kind),
        "primary_nav": str(rec.primary_nav),
        "weak_concept_sha256": weak_concept_sha256("topic-x"),
        "why_now_len": 12,
    }
    r = client.post("/ssr/recommendation-feedback", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert int(data["id"]) > 0


def test_api_post_invalid_hint(iso_db):
    client = TestClient(app)
    r = client.post(
        "/ssr/recommendation-feedback",
        json={
            "action": "accept",
            "hint_kind": "not_a_real_hint",
            "primary_nav": "qa_continue",
        },
    )
    assert r.status_code == 422


def test_api_post_bad_digest_length(iso_db):
    client = TestClient(app)
    r = client.post(
        "/ssr/recommendation-feedback",
        json={
            "action": "defer",
            "hint_kind": "safe_default",
            "primary_nav": "safe_tutor_5min",
            "weak_concept_sha256": "ab",
        },
    )
    assert r.status_code == 422


def test_record_ssr_misroute_feedback_api_validates_nav(iso_db):
    with pytest.raises(ValueError, match="primary_nav"):
        record_ssr_misroute_feedback_api(
            action="accept",
            hint_kind="cards_due",
            primary_nav="invalid_nav_xyz",
        )
