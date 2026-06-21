"""US-3.3: hero examples for first answer screen."""

from app.ui.query_tab import _first_answer_examples


def test_first_answer_examples_returns_three_unique_items_when_index_exists() -> None:
    examples = _first_answer_examples(
        [
            "Пример 1",
            "Пример 2",
            "Пример 2",
            "Пример 3",
            "Пример 4",
        ],
        has_index_content=True,
    )
    assert examples == ["Пример 1", "Пример 2", "Пример 3"]


def test_first_answer_examples_returns_empty_when_index_is_empty() -> None:
    assert _first_answer_examples(["A", "B", "C"], has_index_content=False) == []
