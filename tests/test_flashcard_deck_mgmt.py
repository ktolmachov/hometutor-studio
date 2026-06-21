"""US-15.3 / US-15.6: колоды из квиза, отображение SM-2, API import-quiz."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.api as api
from app import flashcard_service as fc
from app.config import reset_settings_cache
from app.user_state import get_flashcard_deck, reset_schema_cache_for_tests


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "fc_deck_mgmt.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


def _client() -> TestClient:
    return TestClient(api.app)


def test_cards_from_scoped_quiz_items_maps_question_and_answer():
    qs = [
        {
            "question": "Q1?",
            "options": ["A", "B", "C"],
            "correct_index": 1,
            "explanation": "Because B.",
        }
    ]
    cards = fc.cards_from_scoped_quiz_items(qs)
    assert len(cards) == 1
    assert "Q1?" in cards[0]["front"]
    assert "B" in cards[0]["back"]
    assert "Because B" in cards[0]["back"]
    assert "source:scoped-quiz" in (cards[0].get("tags") or "")


def test_import_quiz_endpoint_persists_quiz_source_type(isolated_user_db):
    c = _client()
    r = c.post(
        "/flashcards/decks/import-quiz",
        json={
            "name": "T-quiz",
            "source_identifier": "doc/quiz-1",
            "cards": [
                {"front": "F1", "back": "B1", "tags": None},
                {"front": "F2", "back": "B2", "tags": None},
            ],
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    did = int(data["deck_id"])
    assert did >= 1
    deck = get_flashcard_deck(did)
    assert deck is not None
    assert str(deck.get("source_type") or "") == "quiz"
    assert str(deck.get("source_id") or "") == "doc/quiz-1"
    assert len(deck.get("cards") or []) == 2


def test_deck_card_row_has_sm2_columns(isolated_user_db):
    c = _client()
    c.post(
        "/flashcards/decks/import-quiz",
        json={
            "name": "T-sm2",
            "source_identifier": None,
            "cards": [{"front": "x", "back": "y", "tags": None}],
        },
    )
    r = c.get("/flashcards/decks")
    assert r.status_code == 200
    decks = (r.json() or {}).get("decks") or []
    assert any(d.get("name") == "T-sm2" for d in decks)
    did = next(d["id"] for d in decks if d.get("name") == "T-sm2")
    d2 = c.get(f"/flashcards/decks/{did}")
    assert d2.status_code == 200
    body = d2.json()
    cards = body.get("cards") or []
    assert len(cards) >= 1
    c0 = cards[0]
    assert "easiness" in c0
    assert "interval_days" in c0
    assert "repetitions" in c0
    assert "next_review" in c0
