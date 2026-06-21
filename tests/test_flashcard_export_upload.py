"""US-15.4 / US-15.5: Anki .apkg export и генерация по загруженному тексту (API upload)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.api as api
import app.flashcard_service as fc
from app.config import reset_settings_cache
from app.user_state import reset_schema_cache_for_tests


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "fc_export_upload.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


def _client() -> TestClient:
    return TestClient(api.app)


def _import_min_deck(c: TestClient) -> int:
    r = c.post(
        "/flashcards/decks/import-quiz",
        json={
            "name": "export-me",
            "source_identifier": None,
            "cards": [
                {"front": f"F{i}", "back": f"B{i}", "tags": None}
                for i in range(5)
            ],
        },
    )
    assert r.status_code == 201, r.text
    return int(r.json()["deck_id"])


def test_export_deck_to_anki_bytes_smoke(isolated_user_db):
    pytest.importorskip("genanki")
    c = _client()
    did = _import_min_deck(c)
    data, err = fc.export_deck_to_anki(did)
    assert err is None, err
    assert data is not None and len(data) > 100
    assert data[:2] == b"PK"  # zip / .apkg container


def test_export_anki_http_matches_service(isolated_user_db):
    pytest.importorskip("genanki")
    c = _client()
    did = _import_min_deck(c)
    r = c.get(f"/flashcards/decks/{did}/export/anki")
    assert r.status_code == 200, r.text
    assert r.content[:2] == b"PK"
    disp = (r.headers.get("content-disposition") or "").lower()
    assert "apkg" in disp or "attachment" in disp


def test_generate_scope_upload_uses_stubs_offline(isolated_user_db, monkeypatch):
    monkeypatch.setenv("HOME_RAG_E2E_OFFLINE", "1")
    reset_settings_cache()
    c = _client()
    # Достаточно строк для 5+ stub-карточек (минимум num_cards=5)
    text = "\n".join(f"Line {i} about sample topic" for i in range(20))
    r = c.post(
        "/flashcards/generate",
        json={"scope": "upload", "content": text, "num_cards": 6},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("success") in (True, None) or "cards" in body
    cards = body.get("cards") or []
    assert len(cards) >= 5
    assert all("front" in x and "back" in x for x in cards)
