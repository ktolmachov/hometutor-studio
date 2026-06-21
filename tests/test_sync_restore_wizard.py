"""US-10.2: restore wizard preview/success contract helpers."""

from app.ui.sidebar import _restore_preview_entity_rows, _restore_result_summary


def test_restore_preview_entity_rows_maps_key_entities() -> None:
    preview = {
        "table_row_counts": {
            "learner_profile_snapshots": 2,
            "learner_profile_migration_log": 1,
            "flashcard_decks": 3,
            "flashcards": 11,
            "spaced_repetition": 7,
        }
    }

    counts = _restore_preview_entity_rows(preview)

    assert counts == {"profiles": 3, "decks": 3, "cards": 11, "reviews": 7}


def test_restore_result_summary_shows_inserted_rows_and_version() -> None:
    message = _restore_result_summary({"rows_inserted": 42, "sync_version": 1})
    assert "42" in message
    assert "sync_version=1" in message
