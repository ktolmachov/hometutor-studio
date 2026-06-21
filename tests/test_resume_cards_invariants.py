from app.ui import resume_cards as r


def test_public_facade_symbols_preserved():
    expected = [
        "render_resume_cards",
        "render_home_continue_unified",
        "render_due_reviews_card",
        "render_due_flashcards_card",
        "render_smart_study_router_strip_from_session_context",
        "render_smart_study_steering_controls",
        "render_smart_study_router_for_progress_tab",
        "render_ssr_quiet_mode_toggle",
    ]

    assert all(hasattr(r, name) for name in expected)
