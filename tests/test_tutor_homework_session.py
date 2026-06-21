"""ДЗ внутри tutor-сессии: homework_level API + эвристика сообщения."""

from __future__ import annotations

from app.input_validation import prepare_ask_request
from app.tutor_prompts import infer_homework_level_from_message


def test_prepare_ask_homework_level_sets_mode_and_assistance():
    r = prepare_ask_request(
        type(
            "R",
            (),
            {
                "question": "x",
                "query_mode": "tutor",
                "homework_level": "plan",
            },
        )()
    )
    assert r.options.homework_mode is True
    assert r.options.assistance_level == "plan"
    assert r.options.query_mode == "tutor"


def test_infer_homework_level_from_message():
    assert infer_homework_level_from_message("Дай план решения") == "plan"
    assert infer_homework_level_from_message("подсказка по задаче 3") == "hint"
    assert infer_homework_level_from_message("разбери мою ошибку в коде") == "error_review"
    assert infer_homework_level_from_message("полное решение пожалуйста") == "full_solution"
    assert infer_homework_level_from_message("что такое RAG?") is None
