from app.ui.tutor_chat_actions import micro_quiz_letter_from_choice, micro_quiz_status_ru
from app.ui.tutor_chat_render import nba_from_tutor_decision


def test_micro_quiz_letter_from_choice_maps_option_order():
    options = ["A one", "B two", "C three", "D four"]
    assert micro_quiz_letter_from_choice("C three", options) == "C"
    assert micro_quiz_letter_from_choice("b", options) == "B"
    assert micro_quiz_letter_from_choice("", options) == ""


def test_micro_quiz_status_ru_humanized_labels():
    assert micro_quiz_status_ru("correct") == "Верно"
    assert micro_quiz_status_ru("incorrect") == "Неверно"
    assert micro_quiz_status_ru("partial") == "Частично"


def test_nba_from_tutor_decision_extracts_fields():
    decision = {
        "focus_topic": "RAG",
        "route": "quiz",
        "action": {"next_action": "Проверь меня", "next_action_reason": "Закрепить"},
    }
    assert nba_from_tutor_decision(decision) == {
        "concept": "RAG",
        "reason": "Закрепить",
        "action": "Проверь меня",
        "route": "quiz",
    }
