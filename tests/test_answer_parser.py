from __future__ import annotations

import json

import pytest

from app.answer_parser import AnswerObject, AnswerParseError, format_answer, parse_answer


def test_answer_semantic_round_trip() -> None:
    """Property 1 — semantic round-trip."""
    original = AnswerObject(
        text="Ответ с **markdown**",
        sources=[{"file_name": "a.md", "text": "цитата"}],
        confidence=87.5,
        metadata={"route": "default"},
    )
    wire = format_answer(original)
    again = parse_answer(wire)
    assert again.model_dump() == original.model_dump()


def test_answer_parse_errors_are_descriptive() -> None:
    """Property 2 — понятные ошибки."""
    with pytest.raises(AnswerParseError) as ei:
        parse_answer("{not json")
    assert "not valid JSON" in str(ei.value).lower() or "json" in str(ei.value).lower()

    with pytest.raises(AnswerParseError) as ei2:
        parse_answer("[]")
    assert "object" in str(ei2.value).lower()

    with pytest.raises(AnswerParseError) as ei3:
        parse_answer({"confidence": 150, "text": "x"})
    assert "validation" in str(ei3.value).lower()


def test_answer_formatting_stable_sections() -> None:
    """Property 3 — стабильный вывод (отсортированные ключи JSON)."""
    obj = AnswerObject(text="t", sources=[], metadata={"z": 1, "a": 2})
    a = format_answer(obj)
    b = format_answer(obj)
    assert a == b
    parsed = json.loads(a)
    top_keys = list(parsed.keys())
    assert top_keys == sorted(top_keys)


def test_parse_accepts_dict() -> None:
    got = parse_answer({"text": "hi", "sources": [], "confidence": None})
    assert got.text == "hi"
