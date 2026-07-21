"""Tests for scripts/kilo_proxy_relay.py — streaming proxy, client disconnect, headers."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import kilo_proxy_relay as relay  # noqa: E402
from _kilo_relay_compress import validate_slim_mode  # noqa: E402


class _MockUpstreamResp:
    """Minimal urllib-like response for forward_request_streaming."""

    def __init__(self, parts: list[bytes]) -> None:
        self.status = 200
        self.headers = {"Content-Type": "text/event-stream; charset=utf-8", "Content-Length": "999"}
        self._parts = list(parts)
        self._i = 0

    def read(self, _amt: int = -1) -> bytes:
        if self._i >= len(self._parts):
            return b""
        chunk = self._parts[self._i]
        self._i += 1
        return chunk

    def close(self) -> None:
        return None


class _RecordingHandler:
    """BaseHTTPRequestHandler subset used by forward_request_streaming."""

    def __init__(self) -> None:
        self.protocol_version = "HTTP/1.1"
        self.close_connection = False
        self.status_code: int | None = None
        self.headers: list[tuple[str, str]] = []
        self.wfile = io.BytesIO()

    def send_response(self, code: int, message: str | None = None) -> None:
        self.status_code = code

    def send_header(self, key: str, value: str) -> None:
        self.headers.append((key, value))

    def end_headers(self) -> None:
        pass


def test_effective_upstream_cloud_budget_defaults_to_vsegpt_host():
    assert relay.effective_upstream_base({"KILO_RELAY_SLIM_MODE": "cloud_budget"}) == relay.CLOUD_BUDGET_DEFAULT_UPSTREAM


def test_effective_upstream_budget_cloud_alias():
    assert relay.effective_upstream_base({"KILO_RELAY_SLIM_MODE": "budget_cloud"}) == relay.CLOUD_BUDGET_DEFAULT_UPSTREAM


def test_effective_upstream_explicit_wins_over_cloud_default():
    assert (
        relay.effective_upstream_base(
            {
                "KILO_RELAY_SLIM_MODE": "cloud_budget",
                "KILO_RELAY_UPSTREAM": "https://example.net",
            }
        )
        == "https://example.net"
    )


def test_effective_upstream_local_defaults_lm_studio():
    assert relay.effective_upstream_base({"KILO_RELAY_SLIM_MODE": "local"}) == "http://127.0.0.1:1234"


def test_effective_upstream_cloud_respects_kilo_cloud_default_upstream():
    assert (
        relay.effective_upstream_base(
            {
                "KILO_RELAY_SLIM_MODE": "cloud_budget",
                "KILO_RELAY_CLOUD_DEFAULT_UPSTREAM": "https://azure.example.com",
            }
        )
        == "https://azure.example.com"
    )


def test_write_wfile_best_effort_swallows_broken_pipe():
    class _BadWfile:
        def write(self, _data: bytes) -> int:
            raise BrokenPipeError()

    relay._write_wfile_best_effort(_BadWfile(), b"x")  # must not raise


def test_write_wfile_best_effort_swallows_connection_aborted_error():
    class _AbortWfile:
        def write(self, _data: bytes) -> int:
            raise ConnectionAbortedError()

    relay._write_wfile_best_effort(_AbortWfile(), b"x")


def test_forward_request_streaming_raw_body_no_transfer_encoding_chunked():
    sse = b'data: {"id":"1"}\n\ndata: [DONE]\n\n'
    mock_resp = _MockUpstreamResp([sse[:10], sse[10:]])
    handler = _RecordingHandler()
    compress = {
        "enabled": True,
        "tools_before": 3,
        "tools_after": 1,
        "chars_saved_estimate": 42,
        "cursor_system_stubbed": True,
    }

    with patch.object(relay, "urlopen", return_value=mock_resp):
        up = relay.forward_request_streaming(
            "POST",
            "/v1/chat/completions",
            {"Host": "127.0.0.1:1234"},
            b'{"model":"x","messages":[],"stream":true}',
            handler,
            compress,
        )

    assert up.error is None
    assert handler.status_code == 200
    assert handler.protocol_version == "HTTP/1.0"
    assert handler.close_connection is True
    assert handler.wfile.getvalue() == sse
    assert up.body == sse

    lower_names = {k.lower(): v for k, v in handler.headers}
    assert lower_names.get("connection") == "close"
    assert "transfer-encoding" not in lower_names
    assert ("X-Kilo-Relay-Via", "1") in handler.headers
    # Upstream hop-by-hop / proxy-skipped headers must not be forwarded
    assert "content-length" not in lower_names


def test_forward_request_streaming_client_abort_still_accumulates_body():
    class _AbortingWfile(io.BytesIO):
        def __init__(self) -> None:
            super().__init__()
            self._n = 0

        def write(self, data: bytes) -> int:
            self._n += 1
            if self._n == 1:
                raise ConnectionAbortedError()
            return super().write(data)

    parts = [b"aa", b"bb", b""]
    mock_resp = _MockUpstreamResp(parts)
    handler = _RecordingHandler()
    handler.wfile = _AbortingWfile()

    with patch.object(relay, "urlopen", return_value=mock_resp):
        up = relay.forward_request_streaming("POST", "/v1/x", {}, b"{}", handler, {"enabled": False})

    assert up.body == b"aabb"
    assert handler.wfile.getvalue() == b""


def test_payload_stream_enabled_accepts_common_truthy_forms():
    assert relay._payload_stream_enabled(True)
    assert relay._payload_stream_enabled(1)
    assert relay._payload_stream_enabled("true")
    assert relay._payload_stream_enabled(" True ")
    assert relay._payload_stream_enabled("yes")
    assert relay._payload_stream_enabled("on")
    assert not relay._payload_stream_enabled(False)
    assert not relay._payload_stream_enabled(None)
    assert not relay._payload_stream_enabled(0)
    assert not relay._payload_stream_enabled("false")
    assert not relay._payload_stream_enabled("")


class _FlakyReadResp(_MockUpstreamResp):
    def __init__(self) -> None:
        super().__init__([])
        self._calls = 0

    def read(self, _amt: int = -1) -> bytes:
        self._calls += 1
        if self._calls == 1:
            return b"aa"
        raise OSError("upstream reset")


def test_forward_request_streaming_survives_upstream_read_error():
    handler = _RecordingHandler()
    flaky = _FlakyReadResp()

    with patch.object(relay, "urlopen", return_value=flaky):
        up = relay.forward_request_streaming("POST", "/v1/x", {}, b"{}", handler, {"enabled": False})

    assert up.body == b"aa"
    assert up.error == "upstream reset"
    assert handler.wfile.getvalue() == b"aa"


def test_deepseek_actually_active_true_when_preset_set_alone():
    environ = {"KILO_RELAY_UPSTREAM_PRESET": "deepseek"}
    assert relay._deepseek_actually_active(environ) is True


def test_deepseek_actually_active_false_when_raw_upstream_also_set():
    # Regression: a stale KILO_RELAY_UPSTREAM_PRESET=deepseek left over from a previous run,
    # combined with an explicit raw KILO_RELAY_UPSTREAM override, must NOT leak the DeepSeek
    # API key / rewrite the model / route to DeepSeek — the raw override fully disables the preset.
    environ = {
        "KILO_RELAY_UPSTREAM": "http://127.0.0.1:8080",
        "KILO_RELAY_UPSTREAM_PRESET": "deepseek",
    }
    assert relay._deepseek_actually_active(environ) is False


def test_deepseek_actually_active_false_when_preset_unset():
    assert relay._deepseek_actually_active({}) is False


def test_deepseek_config_requires_api_key():
    environ = {"KILO_RELAY_UPSTREAM_PRESET": "deepseek"}
    try:
        relay.deepseek_config_from_env(environ)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "DEEPSEEK_API_KEY" in str(exc)


def test_deepseek_config_defaults():
    environ = {"KILO_RELAY_UPSTREAM_PRESET": "deepseek", "DEEPSEEK_API_KEY": "sk-test"}
    cfg = relay.deepseek_config_from_env(environ)
    assert cfg == {
        "base": "https://api.deepseek.com",
        "model": "deepseek-v4-pro",
        "api_key": "sk-test",
        "thinking": None,
        "reasoning_effort": None,
    }


def test_deepseek_config_thinking_and_reasoning_effort_opt_in():
    environ = {
        "KILO_RELAY_UPSTREAM_PRESET": "deepseek",
        "DEEPSEEK_API_KEY": "sk-test",
        "DEEPSEEK_THINKING": "disabled",
        "DEEPSEEK_REASONING_EFFORT": "max",
    }
    cfg = relay.deepseek_config_from_env(environ)
    assert cfg["thinking"] == "disabled"
    assert cfg["reasoning_effort"] == "max"


def test_deepseek_config_rejects_low_medium_reasoning_effort():
    # DeepSeek's only real levels are high/max (it silently maps low/medium up to high) —
    # offering them here would be a fake illusion of finer control the API doesn't provide.
    for bogus in ("low", "medium"):
        environ = {
            "KILO_RELAY_UPSTREAM_PRESET": "deepseek",
            "DEEPSEEK_API_KEY": "sk-test",
            "DEEPSEEK_REASONING_EFFORT": bogus,
        }
        try:
            relay.deepseek_config_from_env(environ)
            raise AssertionError(f"expected RuntimeError for {bogus!r}")
        except RuntimeError as exc:
            assert "DEEPSEEK_REASONING_EFFORT" in str(exc)


def test_deepseek_config_rejects_invalid_thinking_value():
    environ = {
        "KILO_RELAY_UPSTREAM_PRESET": "deepseek",
        "DEEPSEEK_API_KEY": "sk-test",
        "DEEPSEEK_THINKING": "maybe",
    }
    try:
        relay.deepseek_config_from_env(environ)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "DEEPSEEK_THINKING" in str(exc)


def test_effective_upstream_raw_wins_over_deepseek_preset():
    environ = {
        "KILO_RELAY_UPSTREAM": "http://127.0.0.1:8080",
        "KILO_RELAY_UPSTREAM_PRESET": "deepseek",
        "DEEPSEEK_API_KEY": "sk-test",
    }
    assert relay.effective_upstream_base(environ) == "http://127.0.0.1:8080"


def test_normalize_chat_completions_path_variants():
    variants = [
        "/v1/chat/completions",
        "/v1/chat/completions/",
        "/v1/chat/completions?trace=1",
        "/v1/chat/completions/?trace=1",
        "/chat/completions",
    ]
    for path in variants:
        assert relay.normalize_chat_completions_path(path) == "/v1/chat/completions"


def test_normalize_chat_completions_path_leaves_other_paths_alone():
    assert relay.normalize_chat_completions_path("/v1/models") == "/v1/models"
    assert relay.normalize_chat_completions_path("/health") == "/health"


def test_log_full_body_defaults_off_when_unset():
    assert relay.log_full_body_from_env({}) is False


def test_log_full_body_opt_in_values():
    for truthy in ("1", "true", "yes", "on", "TRUE", " 1 "):
        assert relay.log_full_body_from_env({"KILO_RELAY_FULL_BODY": truthy}) is True
    for falsy in ("0", "false", "no", "off", ""):
        assert relay.log_full_body_from_env({"KILO_RELAY_FULL_BODY": falsy}) is False


def test_copy_upstream_response_headers_skips_hop_by_hop():
    handler = _RecordingHandler()
    relay._copy_upstream_response_headers(
        handler,
        {
            "Content-Type": "application/json",
            "Content-Length": "10",
            "Transfer-Encoding": "chunked",
            "Connection": "keep-alive",
        },
    )
    names = {k.lower() for k, _ in handler.headers}
    assert "content-type" in names
    assert "content-length" not in names
    assert "transfer-encoding" not in names
    assert "connection" not in names


def test_format_request_mini_stats_chat_line():
    line = relay.format_request_mini_stats(
        method="POST",
        path="/v1/chat/completions",
        status=200,
        elapsed_ms=1234.5,
        request_summary={
            "json_valid": True,
            "body_chars": 81234,
            "estimated_tokens": 20308,
            "messages_count": 8,
            "tools_count": 4,
            "largest_message_chars": 24000,
            "model": "deepseek-v4-pro",
        },
        guard_level="hard_block",
        guard_mode="warn",
        guard_blocked=False,
        stream=True,
        compress_summary={"enabled": True, "chars_saved_estimate": 15000},
        request_original={
            "json_valid": True,
            "body_chars": 96234,
            "estimated_tokens": 24058,
            "messages_count": 8,
            "tools_count": 4,
        },
        usage={"prompt_tokens": 1000, "completion_tokens": 50, "total_tokens": 1050},
        response_chars=4200,
    )
    assert line.startswith("[relay] POST /v1/chat/completions → 200")
    assert "1234.5ms" in line
    assert "body_orig=96234" in line
    assert "body_fwd=81234 (~20308 tok)" in line
    assert "msgs=8" in line
    assert "tools=4" in line
    assert "max_msg=24000" in line
    assert "model=deepseek-v4-pro" in line
    assert "guard=hard_block mode=warn blocked=no" in line
    assert "stream=yes" in line
    assert "saved=15000" in line
    assert "in=1000 out=50" in line
    assert "resp=4200" in line


def test_format_request_mini_stats_models_line_is_short():
    line = relay.format_request_mini_stats(
        method="GET",
        path="/v1/models",
        status=200,
        elapsed_ms=45.0,
        request_summary={"json_valid": False, "body_chars": 0, "estimated_tokens": 0},
        guard_level="ok",
        guard_mode="warn",
        guard_blocked=False,
        stream=False,
        response_chars=120,
    )
    assert line == (
        "[relay] GET /v1/models → 200 45ms body=0 (~0 tok) "
        "guard=ok mode=warn blocked=no stream=no resp=120"
    )


def test_extract_usage_from_json_response():
    body = json.dumps({"usage": {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13}})
    assert relay.extract_usage_from_response_body(body) == {
        "prompt_tokens": 10,
        "completion_tokens": 3,
        "total_tokens": 13,
    }


def test_extract_usage_from_sse_last_chunk():
    body = (
        'data: {"choices":[{"delta":{"content":"hi"}}]}\n\n'
        'data: {"usage":{"prompt_tokens":7,"completion_tokens":2,"total_tokens":9}}\n\n'
        "data: [DONE]\n\n"
    )
    assert relay.extract_usage_from_response_body(body)["prompt_tokens"] == 7


def test_compact_request_stats_drops_previews():
    compact = relay.compact_request_stats(
        {
            "json_valid": True,
            "body_chars": 10,
            "estimated_tokens": 2,
            "body_preview_start": "xxx",
            "message_stats": [{"index": 0}],
        }
    )
    assert compact == {"json_valid": True, "body_chars": 10, "estimated_tokens": 2}
    assert "body_preview_start" not in compact


def test_startup_budget_warn_deepseek_with_slim_off():
    warns = relay._startup_budget_warnings(
        {
            "KILO_RELAY_UPSTREAM_PRESET": "deepseek",
            "DEEPSEEK_API_KEY": "sk-test",
            "KILO_RELAY_SLIM_MODE": "off",
        }
    )
    assert warns and "cloud_budget" in warns[0]


def test_validate_slim_mode_rejects_unknown():
    try:
        validate_slim_mode("locall")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "Unknown KILO_RELAY_SLIM_MODE" in str(exc)


def test_validate_slim_mode_accepts_known():
    assert validate_slim_mode("cloud_budget") == "cloud_budget"
    assert validate_slim_mode("OFF") == "off"
    assert validate_slim_mode("local") == "local"
