# При внешнем PYTHONHOME/PYTHONPATH на «чужой» Python возможен SRE module mismatch
# (в т.ч. во вложенных subprocess); см. pytest.ini и AGENTS.md § Тесты.
import sys
from pathlib import Path
from typing import Any

# Корень репозитория в sys.path — до любого ``import app.*`` (иначе ModuleNotFoundError).
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

_SCRIPTS_DIR = ROOT_DIR / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import pytest

import app.config as app_config
from _pytest.monkeypatch import MonkeyPatch
from app.config import reset_settings_cache


def pytest_configure():
    """
    Тестовое окружение: всегда отключаем reranker, чтобы не грузить Torch/FlagEmbedding.

    Это предотвращает native-краши Windows при попытке загрузить модель reranker
    в рамках unit/integration-тестов.
    """

    original_get_retrieval_settings = app_config.get_retrieval_settings

    def _test_get_retrieval_settings():
        settings = original_get_retrieval_settings()
        settings.enable_reranker = False
        return settings

    app_config.get_retrieval_settings = _test_get_retrieval_settings


@pytest.fixture(autouse=True)
def _default_fact_source_binding_off(monkeypatch: MonkeyPatch) -> None:
    """Disable fact-source binding in most tests; enable explicitly in contract tests."""
    monkeypatch.setenv("FACT_SOURCE_BINDING_ENABLED", "false")
    reset_settings_cache()


@pytest.fixture(autouse=True)
def _default_micro_quiz_offline(monkeypatch: MonkeyPatch) -> None:
    """Не ходить в quiz LLM из unit/integration тестов (на локальном LM Studio это сильно замедляет suite)."""
    monkeypatch.setenv("HOME_RAG_MICRO_QUIZ_OFFLINE", "1")
    reset_settings_cache()


def patch_retrieval_faq_cache_enabled(monkeypatch: MonkeyPatch, **settings_updates: object) -> None:
    """Только ``app.retrieval.get_settings`` — для тестов ``resolve_query_execution_plan`` без ``query_service``."""
    from app.config import get_settings
    import app.retrieval as retrieval

    def _gs():
        updates = {"enable_faq_cache": True, **settings_updates}
        return get_settings().model_copy(update=updates)

    monkeypatch.setattr(retrieval, "get_settings", _gs)


def patch_retrieval_settings(monkeypatch: MonkeyPatch, **settings_kwargs: object) -> app_config.RetrievalSettings:
    """Подмена ``get_retrieval_settings`` в pipeline_factory и retrieval_router."""
    import app.pipeline_factory as pipeline_factory
    import app.retrieval_router as retrieval_router

    settings = app_config.RetrievalSettings(**settings_kwargs)

    def _getter() -> app_config.RetrievalSettings:
        return settings

    monkeypatch.setattr(pipeline_factory, "get_retrieval_settings", _getter)
    monkeypatch.setattr(retrieval_router, "get_retrieval_settings", _getter)
    return settings


@pytest.fixture
def settings_env(monkeypatch: MonkeyPatch):
    """Переменные окружения для pydantic-settings + сброс кэша синглтонов.

    Использование::

        def test_foo(settings_env):
            s = settings_env({"LLM_MODEL": "gpt-4o-mini"})
            assert s.llm_model == "gpt-4o-mini"
    """
    from app.config import get_settings, reset_settings_cache

    def _apply(env: dict[str, str] | None = None) -> Any:
        for key, value in (env or {}).items():
            monkeypatch.setenv(key, value)
        reset_settings_cache()
        return get_settings()

    yield _apply
    reset_settings_cache()


def patch_faq_cache_enabled(monkeypatch: MonkeyPatch, **settings_updates: object) -> None:
    """Подмена ``get_settings`` в ``query_service`` и ``retrieval`` (``_faq_cache_policy`` в ``resolve_query_execution_plan``)."""
    from app.config import get_settings
    import app.query_service as query_service
    import app.retrieval as retrieval

    def _gs():
        updates = {"enable_faq_cache": True, **settings_updates}
        return get_settings().model_copy(update=updates)

    monkeypatch.setattr(query_service, "get_settings", _gs)
    monkeypatch.setattr(retrieval, "get_settings", _gs)


