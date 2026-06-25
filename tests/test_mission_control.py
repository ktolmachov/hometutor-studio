from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.smart_study_recommendation import SmartStudyRecommendation
from app.ui import mission_control as mc
from app.ui.session_state import PENDING_CURRENT_VIEW_KEY


def test_hint_to_tile_covers_all_router_hints() -> None:
    mc.assert_hint_mapping_complete()


def test_tile_definitions_are_locked_seven(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mc, "get_active_scope", lambda: None)
    tiles = mc._tile_definitions(due_count=3)
    assert [tile.tile_id for tile in tiles] == [
        "tutor",
        "quiz",
        "flashcards",
        "quick_question",
        "topics",
        "course",
        "adaptive_plan",
    ]
    assert tiles[5].title == "Активируй курс"


def test_course_tile_uses_active_scope_title(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mc, "get_active_scope", lambda: {"active": True, "title": "ML"})
    tiles = mc._tile_definitions(due_count=0)
    assert tiles[5].title == "ML"
    assert tiles[5].target_view == "Курс"


def test_course_options_include_document_counts_and_paths() -> None:
    options = mc._course_options_from_index_stats(
        {
            "folder_rel_options": ["ml", "math"],
            "files": ["ml/intro.md", "ml/week1.pdf", "math/algebra.md", "other.txt"],
        }
    )
    assert [option.folder_rel for option in options] == ["ml", "math"]
    assert options[0].label == "Курс: ml · 2 док."
    assert options[0].source_paths == ("ml/intro.md", "ml/week1.pdf")


def test_course_options_infer_folders_when_options_absent() -> None:
    options = mc._course_options_from_index_stats(
        {"files": ["course_a/doc.md", "course_b\\lesson.md"]}
    )
    assert [option.folder_rel for option in options] == ["course_a", "course_b"]


def test_recommended_tile_receives_css_class(monkeypatch: pytest.MonkeyPatch) -> None:
    st = MagicMock()
    st.button.return_value = False
    monkeypatch.setattr(mc, "st", st)
    monkeypatch.setattr(mc, "get_active_scope", lambda: None)
    tile = mc.MissionTile(
        tile_id="flashcards",
        title="Flashcards",
        description="К повторению: 2",
        best_for="закрепить",
        icon="style",
        target_view="Flashcards",
        button_label="Повторить",
        slot_hint="flashcards",
    )
    mc._render_tile(tile, recommended_tile="flashcards", due_count=2)
    html = st.markdown.call_args_list[0][0][0]
    assert "smart-recommended" in html
    assert 'data-testid="mission-tile-flashcards"' in html
    assert "material-symbols-outlined" in html
    assert ">style</span>" in html


def test_navigate_to_sets_view_origin_and_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    state: dict[str, object] = {}
    st = SimpleNamespace(session_state=state, rerun=MagicMock())
    monkeypatch.setattr(mc, "st", st)
    mc._navigate_to("Flashcards", slot_hint="flashcards")
    assert state["current_view"] == "Flashcards"
    assert state["home_breadcrumb_origin"] == "Mission Control"
    assert state["home_last_primary_mode_slot"] == "flashcards"
    st.rerun.assert_called_once()


def test_activate_course_callback_sets_state(monkeypatch: pytest.MonkeyPatch) -> None:
    state: dict[str, object] = {}
    st = SimpleNamespace(session_state=state, rerun=MagicMock())
    captured: dict[str, object] = {}
    monkeypatch.setattr(mc, "st", st)
    monkeypatch.setattr(mc, "activate_scope", lambda **kwargs: captured.update(kwargs))

    result = mc._activate_course_and_go_topics(mc.CourseOption("ml", "Курс: ML", ("ml/intro.md",)))

    assert result is True
    assert captured == {"folder_rel": "ml", "title": "Курс: ML", "source_paths": ["ml/intro.md"]}
    assert state["current_view"] == "Темы"
    assert state["home_last_primary_mode_slot"] == "course"
    st.rerun.assert_not_called()


def test_deactivate_course_callback_sets_state(monkeypatch: pytest.MonkeyPatch) -> None:
    state: dict[str, object] = {"current_view": "Курс"}
    st = SimpleNamespace(session_state=state, rerun=MagicMock())
    deactivate = MagicMock()
    clear_cache = MagicMock()
    monkeypatch.setattr(mc, "st", st)
    monkeypatch.setattr(mc, "deactivate_scope", deactivate)
    monkeypatch.setattr(mc, "clear_first_session_session_cache", clear_cache)

    result = mc._deactivate_course_and_go_home()

    assert result is True
    deactivate.assert_called_once()
    clear_cache.assert_called_once()
    assert state["current_view"] == "Mission Control"
    st.rerun.assert_not_called()


def test_course_picker_dialog_reruns_after_button_success(monkeypatch: pytest.MonkeyPatch) -> None:
    state: dict[str, object] = {
        "mission_control_course_options": [
            {"folder_rel": "ml", "title": "Курс: ML", "source_paths": ["ml/intro.md"]}
        ]
    }
    st = MagicMock()
    st.session_state = state
    st.selectbox.return_value = "Курс: ML · 1 док."
    st.button.return_value = True
    monkeypatch.setattr(mc, "st", st)
    monkeypatch.setattr(mc, "_activate_course_and_go_topics", lambda _selected: True)

    mc._render_course_picker_dialog_body()

    st.rerun.assert_called_once()


def test_course_deactivate_dialog_reruns_after_button_success(monkeypatch: pytest.MonkeyPatch) -> None:
    st = MagicMock()
    st.button.return_value = True
    monkeypatch.setattr(mc, "st", st)
    monkeypatch.setattr(mc, "get_active_scope", lambda: {"title": "ML", "folder_rel": "ml"})
    monkeypatch.setattr(mc, "_deactivate_course_and_go_home", lambda: True)

    mc._render_course_deactivate_dialog_body()

    st.rerun.assert_called_once()


def test_ssr_fallback_returns_safe_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.ui.resume_cards.gather_smart_study_router_session_context",
        MagicMock(side_effect=RuntimeError("offline")),
    )
    rec = mc._build_recommendation(index_stats=None)
    assert isinstance(rec, SmartStudyRecommendation)
    assert rec.hint_kind == "safe_default"


def test_due_badge_states(monkeypatch: pytest.MonkeyPatch) -> None:
    st = MagicMock()
    st.button.return_value = False
    monkeypatch.setattr(mc, "st", st)
    monkeypatch.setattr(mc, "get_active_scope", lambda: None)
    tile = mc.MissionTile("flashcards", "Flashcards", "desc", "закрепить", "style", "Flashcards", "Повторить", "flashcards")

    mc._render_tile(tile, recommended_tile="tutor", due_count=None)
    html_none = st.markdown.call_args_list[0][0][0]
    assert "skeleton" in html_none

    st.reset_mock()
    mc._render_tile(tile, recommended_tile="tutor", due_count=0)
    html_zero = st.markdown.call_args_list[0][0][0]
    assert "mode-badge" not in html_zero

    st.reset_mock()
    mc._render_tile(tile, recommended_tile="tutor", due_count=5)
    html_pos = st.markdown.call_args_list[0][0][0]
    assert ">5<" in html_pos
    assert "mode-badge" in html_pos


def test_safe_escapes_html_special_chars() -> None:
    assert mc._safe("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert mc._safe('"quoted"') == "&quot;quoted&quot;"
    assert mc._safe(None) == ""
    assert mc._safe("") == ""


def test_ssr_banner_html_contains_expected_elements(monkeypatch: pytest.MonkeyPatch) -> None:
    st_mock = MagicMock()
    st_mock.button.return_value = False
    monkeypatch.setattr(mc, "st", st_mock)
    monkeypatch.setattr(mc, "build_ssr_evidence_for_banner", lambda _idx: ["сигнал e2e"])
    monkeypatch.setattr(mc, "smart_study_contrastive_explanation", lambda _rec: "причина")
    monkeypatch.setattr(
        mc,
        "smart_study_why_not_others_ru",
        lambda _rec: "Тьютор вторичнее: тест quiz и карточки ждут, прогресс лишь обзор.",
    )

    rec = MagicMock(spec=SmartStudyRecommendation)
    rec.hint_kind = "cards_due"
    rec.primary_label_ru = "Повторить карточки"
    rec.why_now_ru = "Есть просроченные карточки"
    rec.route_pedagogy_ru = ""
    rec.ml_audit_ru = ""
    mc._render_ssr_banner(rec, index_stats=None)

    rendered_html = st_mock.html.call_args_list[0][0][0]
    assert "ssr-banner" in rendered_html
    assert "Подсказка по учебному маршруту" in rendered_html
    assert "Повторить карточки" in rendered_html
    assert "e2e-ssr-why-not-others" in rendered_html
    assert 'data-router-hint="cards_due"' in rendered_html
    assert 'role="region"' in rendered_html
    assert "Почему это подходит:" in rendered_html
    assert "e2e-ssr-contrast" in rendered_html
    assert "e2e-ssr-evidence" in rendered_html
    assert "Локальные сигналы" in rendered_html
    cap = st_mock.caption.call_args[0][0]
    assert "другой режим" in cap.lower() and "quiz" in cap.lower()


def test_course_active_scope_renders_deactivate_button(monkeypatch: pytest.MonkeyPatch) -> None:
    st_mock = MagicMock()
    st_mock.button.return_value = False
    monkeypatch.setattr(mc, "st", st_mock)
    monkeypatch.setattr(mc, "get_active_scope", lambda: {"title": "ML", "folder_rel": "ml"})

    tile = mc.MissionTile("course", "ML", "Кокпит курса", "курс", "map", "Курс", "Открыть", "course")
    mc._render_tile(tile, recommended_tile="tutor", due_count=None)

    button_keys = [call.kwargs.get("key") or (call.args[1] if len(call.args) > 1 else None) for call in st_mock.button.call_args_list]
    assert "mission_tile_course_deactivate" in button_keys


def test_build_recommendation_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_ctx = SimpleNamespace(
        flashcard_due_n=7,
        sm2_due_n=0,
        effective_tutor_snap=None,
        tutor_topic=None,
        has_last_answer_qa=False,
        has_reading=False,
        weak_concepts=[],
        last_answer=None,
    )
    monkeypatch.setattr(
        "app.ui.resume_cards.gather_smart_study_router_session_context",
        MagicMock(return_value=fake_ctx),
    )
    rec = mc._build_recommendation(index_stats=None)
    assert isinstance(rec, SmartStudyRecommendation)
    assert rec.hint_kind in {"cards_due", "sm2_due", "safe_default"}
