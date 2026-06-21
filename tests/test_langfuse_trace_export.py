"""Tests for Langfuse OTLP trace export helpers."""

from __future__ import annotations

import base64

import pytest

from app.config import reset_settings_cache
from app.langfuse_trace_export import (
    apply_langfuse_query_span_attributes,
    build_langfuse_basic_auth_header,
    merge_langfuse_otlp_headers,
    normalize_langfuse_otlp_endpoint,
    resolve_langfuse_otlp_export,
    sanitize_otel_attribute_value,
)


def test_normalize_langfuse_otlp_endpoint_from_host() -> None:
    assert (
        normalize_langfuse_otlp_endpoint("http://localhost:3000")
        == "http://localhost:3000/api/public/otel/v1/traces"
    )


def test_normalize_langfuse_otlp_endpoint_passthrough() -> None:
    endpoint = "https://cloud.langfuse.com/api/public/otel/v1/traces"
    assert normalize_langfuse_otlp_endpoint(endpoint) == endpoint


def test_build_langfuse_basic_auth_header() -> None:
    header = build_langfuse_basic_auth_header("pk-lf-test", "sk-lf-test")
    assert header is not None
    assert header.startswith("Basic ")
    decoded = base64.b64decode(header.removeprefix("Basic ").encode("ascii")).decode("utf-8")
    assert decoded == "pk-lf-test:sk-lf-test"


def test_merge_langfuse_otlp_headers_adds_ingestion_version() -> None:
    headers = merge_langfuse_otlp_headers({}, public_key="pk", secret_key="sk")
    assert headers["x-langfuse-ingestion-version"] == "4"
    assert headers["Authorization"].startswith("Basic ")


def test_sanitize_otel_attribute_value_redacts_email() -> None:
    raw = "contact me at user@example.com please"
    sanitized = sanitize_otel_attribute_value(raw)
    assert "user@example.com" not in sanitized


class _SpanStub:
    def __init__(self) -> None:
        self.attrs: dict[str, object] = {}

    def set_attribute(self, key: str, value: object) -> None:
        self.attrs[key] = value


def test_apply_langfuse_query_span_attributes() -> None:
    span = _SpanStub()
    apply_langfuse_query_span_attributes(
        span,
        session_id="sess-1",
        query_mode="qa",
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        model="gpt-test",
        estimated_cost_usd=0.001,
        tool_name="retrieval",
    )
    assert span.attrs["langfuse.session.id"] == "sess-1"
    assert span.attrs["gen_ai.usage.total_tokens"] == 15
    assert span.attrs["gen_ai.tool.name"] == "retrieval"


def test_resolve_langfuse_otlp_export_uses_langfuse_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_OTEL_TRACING", "true")
    monkeypatch.setenv("LANGFUSE_TRACE_EXPORT_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_HOST", "http://127.0.0.1:3000")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    reset_settings_cache()
    endpoint, headers = resolve_langfuse_otlp_export()
    assert endpoint.endswith("/api/public/otel/v1/traces")
    assert headers["x-langfuse-ingestion-version"] == "4"
    assert headers["Authorization"].startswith("Basic ")
