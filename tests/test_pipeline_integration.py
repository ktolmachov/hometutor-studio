"""
Совместимость имён (E10.1): прежний manual integration-тест удалён.

Актуальные сценарии: ``tests/test_integration_retrieval.py`` (маркер ``integration``),
общая раскладка путей: ``tests/integration_paths.py``.

Запуск::

    pytest -m integration tests/test_integration_retrieval.py
"""

import pytest

pytestmark = pytest.mark.skip(
    reason="Superseded by test_integration_retrieval.py (pytest -m integration)"
)


def test_superseded_placeholder() -> None:
    """Оставлено только чтобы старые команды с этим путём не падали с 'file not found'."""
    pass  # pragma: no cover
