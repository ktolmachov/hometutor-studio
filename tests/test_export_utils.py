"""Tests for app/export_utils.py (Anki + interactive quiz export)."""

import pytest

from app.export_utils import (
    anki_field_safe,
    anki_apkg_from_pairs,
    format_interactive_quiz_correct_for_export,
    interactive_quiz_apkg_bytes,
    interactive_quiz_back_text,
    interactive_quiz_csv_bytes,
)


def test_format_interactive_quiz_correct_for_export_scalar() -> None:
    assert format_interactive_quiz_correct_for_export({"correct": "A"}) == "A"


def test_format_interactive_quiz_correct_for_export_list() -> None:
    s = format_interactive_quiz_correct_for_export({"correct": ["x", "y"]})
    assert "[" in s and "x" in s


def test_interactive_quiz_back_text_csv_vs_apkg_separator() -> None:
    q = {
        "explanation": "Пояснение",
        "type": "multiple_choice",
        "correct": "A",
        "concept": "C1",
    }
    csv_back = interactive_quiz_back_text(q, for_apkg=False)
    apkg_back = interactive_quiz_back_text(q, for_apkg=True)
    assert csv_back.startswith("Пояснение\nТип:")
    assert apkg_back.startswith("Пояснение\n\nТип:")
    assert "Концепт: C1" in csv_back
    assert "Концепт: C1" in apkg_back


def test_interactive_quiz_csv_bytes_bom_and_columns() -> None:
    quiz = {
        "questions": [
            {
                "q": "Вопрос 1",
                "type": "true_false",
                "explanation": "потому что",
                "correct": "True",
                "concept": "",
            },
        ]
    }
    raw = interactive_quiz_csv_bytes(quiz)
    assert raw[:3] == b"\xef\xbb\xbf"
    text = raw.decode("utf-8-sig")
    assert "Front" in text and "Back" in text
    assert "Вопрос 1" in text
    assert "Тип: true_false" in text


def test_interactive_quiz_apkg_bytes_smoke() -> None:
    pytest.importorskip("genanki")
    quiz = {
        "quiz_title": "Мини-квиз",
        "questions": [
            {
                "q": "Q?",
                "type": "fill_blank",
                "explanation": "exp",
                "correct": "ok",
            },
        ],
    }
    data, err = interactive_quiz_apkg_bytes(quiz)
    assert err is None
    assert data is not None and len(data) > 50


def test_anki_apkg_from_pairs_default_flattens_newlines() -> None:
    pytest.importorskip("genanki")
    data, err = anki_apkg_from_pairs("D", [("f", "a\nb")])
    assert err is None
    assert data is not None


def test_anki_field_safe_preserve_newlines() -> None:
    assert "\n" in anki_field_safe("line1\nline2", preserve_newlines=True)
    assert "\n" not in anki_field_safe("line1\nline2", preserve_newlines=False)
