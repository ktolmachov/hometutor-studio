from unittest.mock import MagicMock

from app.otel_tracing import _otlp_endpoint_reachable, _parse_otlp_headers, init_otel_if_enabled


def test_parse_otlp_headers_for_langfuse() -> None:
    headers = _parse_otlp_headers(
        "Authorization=Basic encoded-credentials,x-langfuse-ingestion-version=4"
    )

    assert headers == {
        "Authorization": "Basic encoded-credentials",
        "x-langfuse-ingestion-version": "4",
    }


def test_parse_otlp_headers_ignores_invalid_items() -> None:
    assert _parse_otlp_headers("invalid, =empty,valid=value") == {"valid": "value"}


def test_otlp_endpoint_reachable_open_port() -> None:
    assert _otlp_endpoint_reachable("http://127.0.0.1:1") is False


def test_init_otel_skips_unreachable_collector(monkeypatch) -> None:
    import app.otel_tracing as otel

    otel._provider_initialized = False
    settings = MagicMock(enable_otel_tracing=True, otel_service_name="home-rag")
    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    monkeypatch.setattr(
        "app.langfuse_trace_export.resolve_langfuse_otlp_export",
        lambda: ("http://127.0.0.1:59999/v1/traces", {}),
    )
    monkeypatch.setattr(otel, "_otlp_endpoint_reachable", lambda *_args, **_kwargs: False)

    init_otel_if_enabled()

    assert otel._provider_initialized is False

