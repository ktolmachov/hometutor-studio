from __future__ import annotations

from app.tutor_context_parser import (
    ContextObject,
    deserialize_context,
    serialize_context,
    validate_context,
)


def test_context_json_round_trip() -> None:
    """Property 4 — JSON round-trip."""
    ctx = ContextObject(
        question="Что такое X?",
        topic="Тема X",
        sources=[{"file_name": "n.md"}],
        confidence=42.0,
        learner_state={"level": 1},
    )
    wire = serialize_context(ctx)
    loaded = deserialize_context(wire)
    assert loaded.model_dump() == ctx.model_dump()


def test_context_missing_field_detection() -> None:
    """Property 5 — явные пропуски."""
    obj, miss = validate_context({"topic": "t"})
    assert obj is None
    assert "question" in miss

    obj2, miss2 = validate_context({"question": "", "topic": "t"})
    assert obj2 is None
    assert "question" in miss2

    obj3, miss3 = validate_context({"question": "q", "topic": "t"})
    assert obj3 is not None and miss3 == []


def test_context_allows_extra_keys_in_validate() -> None:
    obj, miss = validate_context(
        {"question": "q", "topic": "t", "ui_scratch": {"x": 1}},
    )
    assert obj is not None and miss == []
