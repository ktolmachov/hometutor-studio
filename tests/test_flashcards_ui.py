from app.ui.flashcards_ui import (
    _build_review_due_params,
    _deck_progress_ratio,
    _fc_receipt_baseline_valid,
    _fc_review_completion_receipt_visible,
    _merge_session_min_next_review,
    _normalize_review_tag_selection,
    _parse_iso_utc,
    _reset_review_session_state,
    _review_progress_ratio,
    _review_scope_signature,
    _review_summary_html,
    _serialize_review_tags,
)
from app.ui.session_state import FLASHCARDS_REVIEW_RECEIPT_BASELINE_KEY
from app.ui.flashcards_decks_view import render_deck_detail
from app.ui.flashcards_review_view import (
    apply_pending_review_scope_reset,
    build_flashcard_tutor_handoff_state,
)


def test_review_tag_selection_normalizes_for_backend_forwarding():
    assert _normalize_review_tag_selection(" Math ; math | Linear  Algebra , ") == [
        "math",
        "linear algebra",
    ]
    assert _serialize_review_tags(["Alpha", " beta ", "alpha"]) == "alpha, beta"


def test_review_due_params_preserve_backend_or_contract():
    params = _build_review_due_params(42, "Alpha; beta", limit=1000)

    assert params == {"limit": 1000, "deck_id": 42, "tags": "alpha, beta"}


def test_review_due_params_omit_empty_filters():
    assert _build_review_due_params(None, "  ") == {"limit": 1000}


def test_review_scope_signature_changes_when_filters_change():
    assert _review_scope_signature(1, "alpha") != _review_scope_signature(1, "beta")
    assert _review_scope_signature(1, "alpha") != _review_scope_signature(2, "alpha")


def test_review_session_reset_clears_stale_queue_state():
    state = {
        "flashcards_review_queue": [{"id": 1}],
        "flashcards_review_index": 3,
        "flashcards_card_flipped": True,
        "flashcards_review_stats": {"good": 2},
        "flashcards_review_session_status": "loaded",
        "flashcards_review_session_error": "boom",
        "flashcards_review_session_loaded_at": "now",
        "flashcards_review_session_next_review_min": "2099-01-01T00:00:00Z",
        FLASHCARDS_REVIEW_RECEIPT_BASELINE_KEY: {"fc_due": 3, "ts": 1.0},
    }

    _reset_review_session_state(state)

    assert state["flashcards_review_queue"] == []
    assert state["flashcards_review_index"] == 0
    assert state["flashcards_card_flipped"] is False
    assert state["flashcards_review_stats"] == {"again": 0, "hard": 0, "good": 0, "easy": 0}
    assert state["flashcards_review_session_status"] == "idle"
    assert state["flashcards_review_session_error"] is None
    assert state["flashcards_review_session_loaded_at"] is None
    assert state["flashcards_review_session_next_review_min"] is None
    assert FLASHCARDS_REVIEW_RECEIPT_BASELINE_KEY not in state


def test_pending_review_scope_reset_runs_before_widget_creation():
    state = {
        "flashcards_review_scope_reset_pending": True,
        "flashcards_review_session_deck_id": 42,
        "flashcards_review_session_tags_text": "algebra",
        "flashcards_review_session_tag_ids": ["algebra"],
        "flashcards_review_queue": [{"id": 1}],
    }

    applied = apply_pending_review_scope_reset(
        state,
        reset_review_session_state=_reset_review_session_state,
        review_scope_signature=_review_scope_signature,
    )

    assert applied is True
    assert "flashcards_review_scope_reset_pending" not in state
    assert state["flashcards_review_session_deck_id"] is None
    assert state["flashcards_review_deck_sync_pending"] is None
    assert state["flashcards_review_session_tags_text"] == ""
    assert state["flashcards_review_session_tag_ids"] == []
    assert state["flashcards_review_session_scope_signature"] == _review_scope_signature(None, None)
    assert state["flashcards_review_queue"] == []


def test_review_summary_html_us152_regression():
    html = _review_summary_html(
        {"again": 1, "hard": 2, "good": 3, "easy": 4},
        10,
        "2026-06-01T12:00:00+00:00",
    )
    assert 'class="fc-review-summary"' in html
    assert "✅ Сессия завершена — 10 карточек" in html
    assert "🔴 Снова:" in html and "<b>1</b>" in html
    assert "🟡 Трудно:" in html and "<b>2</b>" in html
    assert "🟢 Хорошо:" in html and "<b>3</b>" in html
    assert "⭐ Легко:" in html and "<b>4</b>" in html
    assert "Ближайшее повторение среди оценённых" in html


def test_fc_review_completion_receipt_gate():
    assert _fc_review_completion_receipt_visible(idx=0, total=0, stats={}) is False
    assert _fc_review_completion_receipt_visible(idx=2, total=3, stats={"good": 2}) is False
    assert _fc_review_completion_receipt_visible(idx=3, total=3, stats={"good": 0, "again": 0}) is False
    assert _fc_review_completion_receipt_visible(idx=3, total=3, stats={"good": 2, "easy": 1}) is True


def test_fc_receipt_baseline_valid_checks_scope_and_ttl(monkeypatch):
    import time

    scope = "deck=all|tags="
    fresh = {"scope_signature": scope, "ts": time.time(), "fc_due": 5}
    assert _fc_receipt_baseline_valid(fresh, scope) is True
    assert _fc_receipt_baseline_valid(fresh, "deck=1|tags=") is False
    stale = {"scope_signature": scope, "ts": time.time() - 601, "fc_due": 5}
    assert _fc_receipt_baseline_valid(stale, scope) is False
    assert _fc_receipt_baseline_valid(None, scope) is False


def test_parse_iso_utc_accepts_z_suffix():
    dt = _parse_iso_utc("2026-04-20T12:00:00Z")
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 4


def test_merge_session_min_next_review_keeps_earliest():
    state: dict = {}
    _merge_session_min_next_review(state, "2026-04-20T12:00:00Z")
    assert state["flashcards_review_session_next_review_min"] == "2026-04-20T12:00:00Z"
    _merge_session_min_next_review(state, "2026-04-10T08:00:00+00:00")
    assert state["flashcards_review_session_next_review_min"] == "2026-04-10T08:00:00+00:00"
    _merge_session_min_next_review(state, "2026-05-01T00:00:00Z")
    assert state["flashcards_review_session_next_review_min"] == "2026-04-10T08:00:00+00:00"


def test_progress_ratios_are_clamped():
    assert _review_progress_ratio(0, 0) == 0.0
    assert _review_progress_ratio(2, 4) == 0.5
    assert _review_progress_ratio(10, 4) == 1.0
    assert _review_progress_ratio(-1, 4) == 0.0
    assert _deck_progress_ratio({"percent": 50}) == 0.5
    assert _deck_progress_ratio({"percent": 250}) == 1.0
    assert _deck_progress_ratio({"percent": "oops"}) == 0.0


def test_flashcard_tutor_handoff_state_uses_card_front_and_return_marker():
    state = build_flashcard_tutor_handoff_state(
        {
            "front": "Что такое dense retrieval?",
            "back": "Поиск по эмбеддингам",
            "deck_name": "Курс Retrieval",
        }
    )

    assert state["current_topic"] == "Курс Retrieval"
    assert state["tutor_goal_subtopic"] == "Что такое dense retrieval?"
    assert state["tutor_goal_desired_outcome"] == "объяснить вопрос из карточки"
    assert state["tutor_goal_time_budget_min"] == 5
    assert state["flashcard_review_return"] is True
    assert state["tutor_entrypoint"] == "flashcard_handoff"
    assert "tutor_answer_depth" not in state
    assert "current_view" not in state


class _NoopColumn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_deck_detail_renders_anki_download_button(monkeypatch):
    calls: dict[str, object] = {}

    def api_call(method: str, path: str):
        calls.setdefault("api", []).append((method, path))
        if path == "/flashcards/decks/7":
            return {
                "id": 7,
                "name": "Export Deck",
                "updated_at": "2026-04-24T12:00:00Z",
                "cards": [],
            }
        if path == "/flashcards/decks/7/progress":
            return {"mastered": 0, "total": 0, "percent": 0}
        raise AssertionError(path)

    def cached_anki_apkg(deck_id: int, deck_updated: str | None):
        calls["cached_anki"] = (deck_id, deck_updated)
        return b"PK-anki", None

    monkeypatch.setattr(
        "app.ui.flashcards_decks_view.st.columns",
        lambda *args, **kwargs: [_NoopColumn(), _NoopColumn(), _NoopColumn()],
    )
    monkeypatch.setattr("app.ui.flashcards_decks_view.st.markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.ui.flashcards_decks_view.st.divider", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.ui.flashcards_decks_view.st.progress", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.ui.flashcards_decks_view.st.caption", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.ui.flashcards_decks_view.st.info", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.ui.flashcards_decks_view.st.warning", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.ui.flashcards_decks_view.st.error", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.ui.flashcards_decks_view.st.button", lambda *args, **kwargs: False)

    def download_button(label: str, **kwargs):
        calls["download"] = {"label": label, **kwargs}
        return False

    monkeypatch.setattr("app.ui.flashcards_decks_view.st.download_button", download_button)

    render_deck_detail(
        7,
        api_call=api_call,
        go=lambda *args, **kwargs: None,
        seed_review_scope=lambda deck_id: None,
        cached_anki_apkg=cached_anki_apkg,
        deck_progress_ratio=lambda progress: 0.0,
    )

    assert calls["cached_anki"] == (7, "2026-04-24T12:00:00Z")
    download = calls["download"]
    assert "Anki .apkg" in str(download["label"])
    assert download["data"] == b"PK-anki"
    assert download["file_name"] == "Export Deck.apkg"
    assert download["mime"] == "application/octet-stream"
    assert download["width"] == "stretch"
    assert download["key"] == "anki_dl_7"
