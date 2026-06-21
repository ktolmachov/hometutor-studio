"""Logs из ``app.*`` модулей должны идти через JSON-форматтер setup_logging,
а не падать в logging.lastResort с дефолтным форматтером без полей."""

from __future__ import annotations

import io
import json
import logging

from app.logging_config import log_event, setup_logging


def _detach_handlers_from(name: str) -> list[logging.Handler]:
    lg = logging.getLogger(name)
    saved = list(lg.handlers)
    lg.handlers.clear()
    return saved


def _restore_handlers(name: str, handlers: list[logging.Handler]) -> None:
    lg = logging.getLogger(name)
    lg.handlers.clear()
    for h in handlers:
        lg.addHandler(h)


def test_app_namespace_logger_uses_json_formatter() -> None:
    setup_logging()
    app_logger = logging.getLogger("app")
    assert app_logger.handlers, "expected setup_logging to attach handlers to 'app' logger"
    # Должен быть JSON-форматтер (тот же класс, что у root project logger).
    formatters = {type(h.formatter).__name__ for h in app_logger.handlers if h.formatter}
    assert "StructuredFormatter" in formatters


def test_app_child_logger_emits_json_with_extra_fields() -> None:
    """log_event из app.<module> должен попасть в JSON-handler с полями event/stage/error_type."""
    setup_logging()
    app_logger = logging.getLogger("app")

    buf = io.StringIO()
    capture = logging.StreamHandler(buf)
    capture.setFormatter(app_logger.handlers[0].formatter)
    app_logger.addHandler(capture)
    try:
        module_logger = logging.getLogger("app.provider_openai")  # реальный namespace
        log_event(
            module_logger,
            logging.WARNING,
            "llm_complete_failed",
            stage="ssr_why_now",
            error_type="APIConnectionError",
            message="Connection error.",
        )
    finally:
        app_logger.removeHandler(capture)

    line = buf.getvalue().strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["event"] == "llm_complete_failed"
    assert payload["stage"] == "ssr_why_now"
    assert payload["error_type"] == "APIConnectionError"
    # log_event кладёт переданный ``message`` в extra_fields → перетирает базовый
    # ``record.getMessage()`` в JSON-payload (поведение StructuredFormatter.format).
    assert payload["message"] == "Connection error."
    assert payload["logger"] == "app.provider_openai"


def test_app_logger_does_not_propagate_to_root() -> None:
    """Без propagate=False сообщение из app.* дублируется через root → lastResort."""
    setup_logging()
    app_logger = logging.getLogger("app")
    assert app_logger.propagate is False
