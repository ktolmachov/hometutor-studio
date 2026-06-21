"""Unit-тесты для app/ui/study_scope.py (без Streamlit runtime)."""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch


def _make_st_mock(state: dict) -> MagicMock:
    """Streamlit mock с изолированным session_state dict."""
    mock_st = MagicMock()
    mock_st.session_state = state
    return mock_st


# ---------------------------------------------------------------------------
# folder_rel_from_paths — чистая функция, не требует Streamlit
# ---------------------------------------------------------------------------

def test_folder_rel_from_paths_basic():
    from app.ui.study_scope import folder_rel_from_paths

    result = folder_rel_from_paths(["ml_course/lec1.pdf", "ml_course/lec2.pdf", "ml_course/lec3.pdf"])
    assert result == "ml_course"


def test_folder_rel_from_paths_majority_wins():
    from app.ui.study_scope import folder_rel_from_paths

    paths = ["course_a/doc1.pdf", "course_a/doc2.pdf", "course_b/doc1.pdf"]
    assert folder_rel_from_paths(paths) == "course_a"


def test_folder_rel_from_paths_empty():
    from app.ui.study_scope import folder_rel_from_paths

    assert folder_rel_from_paths([]) is None


def test_folder_rel_from_paths_no_subdir():
    from app.ui.study_scope import folder_rel_from_paths

    assert folder_rel_from_paths(["flat_file.pdf"]) is None


# ---------------------------------------------------------------------------
# activate_scope / get_active_scope / deactivate_scope — мокируем st.session_state
# ---------------------------------------------------------------------------

def _make_state():
    """Возвращает изолированный dict-like mock для session_state."""
    return {}


def test_activate_and_get_scope():
    from app.ui import study_scope

    state: dict = {"last_synthesis": {"topic": "old"}, "last_learning_plan": {"topic": "old"}}
    mock_st = _make_st_mock(state)
    with patch.dict(sys.modules, {"streamlit": mock_st}):
        scope = study_scope.activate_scope(folder_rel="ml_course", title="Курс ML", source_paths=["ml_course/lec1.pdf"])
        assert scope["folder_rel"] == "ml_course"
        assert scope["title"] == "Курс ML"
        assert scope["active"] is True
        assert len(scope["id"]) == 12
        assert state["last_synthesis"] is None
        assert state["last_learning_plan"] is None
        result = study_scope.get_active_scope()
        assert result == scope


def test_deactivate_scope():
    from app.ui import study_scope

    state: dict = {"last_synthesis": {"topic": "old"}, "last_learning_plan": {"topic": "old"}}
    mock_st = _make_st_mock(state)
    with patch.dict(sys.modules, {"streamlit": mock_st}):
        study_scope.activate_scope(folder_rel="ml_course")
        state["last_synthesis"] = {"topic": "course"}
        state["last_learning_plan"] = {"topic": "course"}
        study_scope.deactivate_scope()
        assert study_scope.get_active_scope() is None
        assert state["last_synthesis"] is None
        assert state["last_learning_plan"] is None


def test_apply_scope_folder_rel_overrides():
    from app.ui import study_scope

    state: dict = {}
    mock_st = _make_st_mock(state)
    with patch.dict(sys.modules, {"streamlit": mock_st}):
        study_scope.activate_scope(folder_rel="physics")
        result = study_scope.apply_scope_folder_rel("chemistry")
        assert result == "physics"


def test_apply_scope_folder_rel_passthrough_when_inactive():
    from app.ui import study_scope

    state: dict = {}
    mock_st = _make_st_mock(state)
    with patch.dict(sys.modules, {"streamlit": mock_st}):
        result = study_scope.apply_scope_folder_rel("chemistry")
        assert result == "chemistry"


def test_get_active_scope_none_when_empty():
    from app.ui import study_scope

    state: dict = {}
    mock_st = _make_st_mock(state)
    with patch.dict(sys.modules, {"streamlit": mock_st}):
        assert study_scope.get_active_scope() is None


# ---------------------------------------------------------------------------
# continuity_bridge copy strings (Package AB)
# ---------------------------------------------------------------------------

def test_course_scope_chip_ru():
    from app.ui.continuity_bridge import course_scope_chip_ru

    chip = course_scope_chip_ru("Курс ML")
    assert "Курс ML" in chip
    assert "🎯" in chip


def test_flashcard_gap_to_tutor_cta_ru():
    from app.ui.continuity_bridge import flashcard_gap_to_tutor_cta_ru

    assert "объясни" in flashcard_gap_to_tutor_cta_ru().lower()


def test_tutor_back_to_flashcards_ru():
    from app.ui.continuity_bridge import tutor_back_to_flashcards_ru

    label = tutor_back_to_flashcards_ru()
    assert "карточк" in label.lower()


# ---------------------------------------------------------------------------
# Cyrillic folder names and scope_id stability
# ---------------------------------------------------------------------------

def test_folder_rel_from_paths_cyrillic_with_spaces():
    from app.ui.study_scope import folder_rel_from_paths

    result = folder_rel_from_paths(["ИИ Агенты/лекция1.md", "ИИ Агенты/лекция2.pdf"])
    assert result == "ИИ Агенты"


def test_scope_id_stable_for_same_folder_rel():
    from app.ui.study_scope import _scope_id

    assert _scope_id("ИИ Агенты") == _scope_id("ИИ Агенты")
    assert _scope_id("ml_course") != _scope_id("ИИ Агенты")


def test_activate_scope_with_cyrillic_clears_derived_state():
    from app.ui import study_scope

    state: dict = {"last_synthesis": {"topic": "old"}, "last_learning_plan": {"topic": "old"}}
    mock_st = _make_st_mock(state)
    with patch.dict(sys.modules, {"streamlit": mock_st}):
        scope = study_scope.activate_scope(
            folder_rel="ИИ Агенты",
            title="Курс: ИИ Агенты",
            source_paths=["ИИ Агенты/лекция1.md", "ИИ Агенты/лекция2.pdf"],
        )
        assert scope["folder_rel"] == "ИИ Агенты"
        assert scope["active"] is True
        assert state["last_synthesis"] is None
        assert state["last_learning_plan"] is None


def test_activate_scope_clears_last_answer_and_quiz_keys():
    from app.ui import study_scope

    state: dict = {
        "last_synthesis": {"topic": "old"},
        "last_learning_plan": {"topic": "old"},
        "last_answer": {"text": "old answer"},
        "topic_scope_quiz_abc123": {"questions": ["q1"]},
        "topic_scope_quiz_xyz": {"questions": ["q2"]},
        "unrelated_key": "keep_me",
    }
    mock_st = _make_st_mock(state)
    with patch.dict(sys.modules, {"streamlit": mock_st}):
        study_scope.activate_scope(folder_rel="ml_course", source_paths=["ml_course/lec1.pdf"])
        assert state["last_answer"] is None
        assert state["topic_scope_quiz_abc123"] == {}
        assert state["topic_scope_quiz_xyz"] == {}
        assert state["unrelated_key"] == "keep_me"


def test_deactivate_scope_clears_last_answer_and_quiz_keys():
    from app.ui import study_scope

    state: dict = {
        "last_synthesis": {"topic": "stale"},
        "last_learning_plan": {"topic": "stale"},
        "last_answer": {"text": "stale"},
        "topic_scope_quiz_t1": {"questions": ["q"]},
    }
    mock_st = _make_st_mock(state)
    with patch.dict(sys.modules, {"streamlit": mock_st}):
        study_scope.activate_scope(folder_rel="physics")
        state["last_answer"] = {"text": "course answer"}
        state["topic_scope_quiz_t1"] = {"questions": ["course q"]}
        study_scope.deactivate_scope()
        assert study_scope.get_active_scope() is None
        assert state["last_answer"] is None
        assert state["topic_scope_quiz_t1"] == {}
