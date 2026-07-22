"""Tests for scripts/kilo_proxy_relay.py — streaming proxy, client disconnect, headers."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request

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
        "reasoning_content_guard": "warn",
    }


def test_deepseek_config_thinking_and_reasoning_effort_opt_in():
    # thinking=enabled + reasoning_effort=max is the only self-consistent explicit combination
    # (reasoning_effort has no effect once thinking is disabled — see the rejection test below).
    environ = {
        "KILO_RELAY_UPSTREAM_PRESET": "deepseek",
        "DEEPSEEK_API_KEY": "sk-test",
        "DEEPSEEK_THINKING": "enabled",
        "DEEPSEEK_REASONING_EFFORT": "max",
    }
    cfg = relay.deepseek_config_from_env(environ)
    assert cfg["thinking"] == "enabled"
    assert cfg["reasoning_effort"] == "max"


def test_deepseek_config_rejects_reasoning_effort_with_thinking_disabled():
    environ = {
        "KILO_RELAY_UPSTREAM_PRESET": "deepseek",
        "DEEPSEEK_API_KEY": "sk-test",
        "DEEPSEEK_THINKING": "disabled",
        "DEEPSEEK_REASONING_EFFORT": "max",
    }
    try:
        relay.deepseek_config_from_env(environ)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "meaningless" in str(exc)


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


def test_validate_deepseek_api_base_accepts_canonical_https_host():
    relay.validate_deepseek_api_base("https://api.deepseek.com", {})  # must not raise


def test_validate_deepseek_api_base_rejects_http_scheme():
    try:
        relay.validate_deepseek_api_base("http://api.deepseek.com", {})
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "https" in str(exc)


def test_validate_deepseek_api_base_rejects_unexpected_host():
    try:
        relay.validate_deepseek_api_base("https://api-deepseek.example", {})
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "api.deepseek.com" in str(exc)


def test_validate_deepseek_api_base_allows_custom_host_with_explicit_opt_out():
    relay.validate_deepseek_api_base(
        "https://internal-proxy.example", {"DEEPSEEK_ALLOW_CUSTOM_HOST": "1"}
    )  # must not raise


def test_apply_deepseek_compatibility_developer_role_and_null_tool_content():
    payload = {
        "thinking": {"type": "disabled"},
        "messages": [
            {"role": "developer", "content": "sys prompt"},
            {"role": "assistant", "tool_calls": [{"id": "1"}], "content": None},
        ],
    }
    applied = relay.apply_deepseek_compatibility(payload)
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["content"] == ""
    assert "developer_role_to_system" in applied
    assert "null_tool_call_content_to_empty" in applied


def test_apply_deepseek_compatibility_max_completion_tokens_renamed():
    payload = {"thinking": {"type": "disabled"}, "max_completion_tokens": 512}
    applied = relay.apply_deepseek_compatibility(payload)
    assert payload["max_tokens"] == 512
    assert "max_completion_tokens" not in payload
    assert "max_completion_tokens_to_max_tokens" in applied


def test_apply_deepseek_compatibility_max_completion_tokens_dropped_when_both_present():
    payload = {"thinking": {"type": "disabled"}, "max_tokens": 256, "max_completion_tokens": 512}
    applied = relay.apply_deepseek_compatibility(payload)
    assert payload["max_tokens"] == 256
    assert "max_completion_tokens" not in payload
    assert "dropped_redundant_max_completion_tokens" in applied


def test_apply_deepseek_compatibility_strips_tool_choice_when_thinking_effective():
    # payload doesn't declare "thinking" at all -> DeepSeek's own default is enabled -> stripped.
    payload = {"tool_choice": "auto"}
    applied = relay.apply_deepseek_compatibility(payload)
    assert "tool_choice" not in payload
    assert "stripped_tool_choice_thinking_mode" in applied


def test_apply_deepseek_compatibility_keeps_tool_choice_when_thinking_disabled():
    payload = {"thinking": {"type": "disabled"}, "tool_choice": "auto"}
    applied = relay.apply_deepseek_compatibility(payload)
    assert payload["tool_choice"] == "auto"
    assert applied == []


def test_apply_deepseek_compatibility_reads_client_payload_thinking_not_env_cfg():
    """Regression for the confirmed bug: both apply_deepseek_compatibility and
    detect_missing_reasoning_content used to read only an env-derived cfg dict, so a client
    that itself sent thinking.type=disabled (no env override at all) was still treated as
    thinking-enabled (DeepSeek's default) -- wrongly stripping tool_choice. effective_thinking_type
    must read the payload directly, which by _handle_proxy's call order already reflects any env
    override baked in earlier, or the client's own value if there was none."""
    payload = {"thinking": {"type": "disabled"}, "tool_choice": "auto"}
    assert relay.effective_thinking_type(payload) == "disabled"
    applied = relay.apply_deepseek_compatibility(payload)
    assert payload["tool_choice"] == "auto"  # NOT stripped -- client explicitly disabled thinking
    assert applied == []


def test_detect_missing_reasoning_content_warns_when_thinking_effective():
    payload = {
        "messages": [
            {"role": "user", "content": "do it"},
            {"role": "assistant", "tool_calls": [{"id": "1"}], "content": ""},
        ]
    }
    warnings = relay.detect_missing_reasoning_content(payload)  # no "thinking" key -> enabled default
    assert warnings == ["assistant_tool_call_missing_reasoning_content"]


def test_detect_missing_reasoning_content_silent_when_present():
    payload = {
        "thinking": {"type": "enabled"},
        "messages": [
            {"role": "assistant", "tool_calls": [{"id": "1"}], "content": "", "reasoning_content": "thought..."},
        ],
    }
    assert relay.detect_missing_reasoning_content(payload) == []


def test_detect_missing_reasoning_content_silent_when_thinking_disabled():
    payload = {
        "thinking": {"type": "disabled"},
        "messages": [{"role": "assistant", "tool_calls": [{"id": "1"}], "content": ""}],
    }
    assert relay.detect_missing_reasoning_content(payload) == []


def test_detect_missing_reasoning_content_silent_without_tool_calls():
    payload = {"messages": [{"role": "assistant", "content": "just text"}]}
    assert relay.detect_missing_reasoning_content(payload) == []


def test_detect_missing_reasoning_content_reads_client_payload_thinking_not_env_cfg():
    """Same class of regression as apply_deepseek_compatibility above: a client-declared
    thinking.type=disabled (no env override) must silence the warning."""
    payload = {
        "thinking": {"type": "disabled"},
        "messages": [{"role": "assistant", "tool_calls": [{"id": "1"}], "content": ""}],
    }
    assert relay.detect_missing_reasoning_content(payload) == []


def test_prepare_upstream_request_headers_strips_accept_encoding_always():
    headers = {"Accept-Encoding": "gzip", "Content-Type": "application/json", "Host": "x"}
    out = relay._prepare_upstream_request_headers(headers)
    assert "Accept-Encoding" not in out
    assert "Host" not in out
    assert out["Content-Type"] == "application/json"


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


class _FakeRequestHandler:
    """Minimal stand-in for RelayHandler exercising the real _handle_proxy() code path
    end-to-end, not just its helper functions in isolation."""

    def __init__(self, path: str, command: str, body: bytes, headers: dict[str, str]) -> None:
        self.path = path
        self.command = command
        self.headers = headers
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.status_code: int | None = None
        self.sent_headers: list[tuple[str, str]] = []

    def send_response(self, code: int, message: str | None = None) -> None:
        self.status_code = code

    def send_header(self, key: str, value: str) -> None:
        self.sent_headers.append((key, value))

    def end_headers(self) -> None:
        pass


class _FakeUpstreamCtxResp:
    status = 200
    headers = {"Content-Type": "application/json"}

    def read(self) -> bytes:
        return b'{"choices":[{"message":{"content":"ok"}}],"usage":{"prompt_tokens":1,"completion_tokens":1}}'

    def __enter__(self) -> "_FakeUpstreamCtxResp":
        return self

    def __exit__(self, *args: object) -> bool:
        return False


def _run_handle_proxy(path: str, body: bytes, headers: dict[str, str]) -> tuple[Request, dict]:
    """Drive the real RelayHandler._handle_proxy against a fake handler + mocked urlopen.

    Returns (the urllib.request.Request that was actually about to go out over the wire,
    the JSONL record that would have been written to disk) — both captured, not mocked away,
    so tests can assert on outbound request AND on-disk log content in the same run."""
    handler = _FakeRequestHandler(path, "POST", body, headers)
    captured_requests: list[Request] = []
    captured_records: list[dict] = []

    def _fake_urlopen(request: Request, timeout: float | None = None, context: object = None) -> _FakeUpstreamCtxResp:
        captured_requests.append(request)
        return _FakeUpstreamCtxResp()

    with (
        patch.object(relay, "urlopen", _fake_urlopen),
        patch.object(relay, "write_jsonl", captured_records.append),
        patch.object(relay, "RELAY_COMPRESS_ACTIVE", False),
    ):
        relay.RelayHandler._handle_proxy(handler)  # type: ignore[arg-type]

    assert len(captured_requests) == 1
    assert len(captured_records) == 1
    return captured_requests[0], captured_records[0]


def test_handle_proxy_stale_deepseek_preset_does_not_leak_key_to_raw_upstream():
    """Integration regression for the confirmed critical bug: a stale
    KILO_RELAY_UPSTREAM_PRESET=deepseek combined with an explicit raw KILO_RELAY_UPSTREAM must
    resolve DEEPSEEK_CFG to None (see test_deepseek_actually_active_false_when_raw_upstream_also_set)
    AND _handle_proxy must then apply zero DeepSeek overrides — exercised here through the real
    handler code path, not just the helper function in isolation."""
    body = b'{"model":"qwen3-coder-next-q4ks","messages":[{"role":"user","content":"hi"}]}'
    headers = {
        "Content-Length": str(len(body)),
        "Content-Type": "application/json",
        "Authorization": "Bearer local-relay",
    }

    with (
        patch.object(relay, "DEEPSEEK_CFG", None),
        patch.object(relay, "UPSTREAM_BASE", "http://127.0.0.1:8080"),
    ):
        sent, _record = _run_handle_proxy("/v1/chat/completions", body, headers)

    assert sent.full_url == "http://127.0.0.1:8080/v1/chat/completions"
    assert sent.get_header("Authorization") == "Bearer local-relay"  # NOT replaced with a DeepSeek key
    sent_body = json.loads(sent.data)
    assert sent_body["model"] == "qwen3-coder-next-q4ks"  # NOT rewritten to deepseek-v4-pro


def test_handle_proxy_active_deepseek_preset_does_apply_overrides():
    """Positive control for the test above: proves the harness actually detects overrides when
    DeepSeek IS the resolved provider, so the negative test isn't trivially always-green."""
    body = b'{"model":"qwen3-coder-next-q4ks","messages":[{"role":"user","content":"hi"}]}'
    headers = {
        "Content-Length": str(len(body)),
        "Content-Type": "application/json",
        "Authorization": "Bearer local-relay",
    }

    with (
        patch.object(
            relay,
            "DEEPSEEK_CFG",
            {"base": "https://api.deepseek.com", "model": "deepseek-v4-pro", "api_key": "sk-real-secret",
             "thinking": None, "reasoning_effort": None, "reasoning_content_guard": "warn"},
        ),
        patch.object(relay, "UPSTREAM_BASE", "https://api.deepseek.com"),
    ):
        sent, _record = _run_handle_proxy("/v1/chat/completions", body, headers)

    assert sent.full_url == "https://api.deepseek.com/v1/chat/completions"
    assert sent.get_header("Authorization") == "Bearer sk-real-secret"
    sent_body = json.loads(sent.data)
    assert sent_body["model"] == "deepseek-v4-pro"


def test_handle_proxy_deepseek_reasoning_content_warn_mode_still_forwards():
    """Regression for the confirmed bug: the warning used to be computed but never acted on
    before the (possibly paid) upstream call -- only written to JSONL afterward. In "warn" mode
    (default) the request must still be forwarded, but the warning must now be visible via
    deepseek_overrides at the point the decision is made, not just after the call completes."""
    body = (
        b'{"model":"qwen3-coder-next-q4ks","messages":['
        b'{"role":"user","content":"do it"},'
        b'{"role":"assistant","tool_calls":[{"id":"1"}],"content":""}]}'
    )
    headers = {
        "Content-Length": str(len(body)),
        "Content-Type": "application/json",
        "Authorization": "Bearer local-relay",
    }

    with (
        patch.object(
            relay,
            "DEEPSEEK_CFG",
            {"base": "https://api.deepseek.com", "model": "deepseek-v4-pro", "api_key": "sk-real-secret",
             "thinking": None, "reasoning_effort": None, "reasoning_content_guard": "warn"},
        ),
        patch.object(relay, "UPSTREAM_BASE", "https://api.deepseek.com"),
    ):
        sent, record = _run_handle_proxy("/v1/chat/completions", body, headers)

    # warn mode: request still goes out (upstream call happened -- _run_handle_proxy already
    # asserts exactly one captured urlopen call), but the warning is recorded.
    assert sent.full_url == "https://api.deepseek.com/v1/chat/completions"
    assert record["deepseek_overrides"]["warnings"] == ["assistant_tool_call_missing_reasoning_content"]


def test_handle_proxy_deepseek_reasoning_content_block_mode_prevents_upstream_call():
    """The actual fail-fast fix: DEEPSEEK_REASONING_CONTENT_GUARD=block must reject the request
    with a local error WITHOUT ever calling urlopen -- proving the paid API call is genuinely
    saved, not just that a flag gets written to JSONL after the call already happened."""
    body = (
        b'{"model":"qwen3-coder-next-q4ks","messages":['
        b'{"role":"assistant","tool_calls":[{"id":"1"}],"content":""}]}'
    )
    headers = {
        "Content-Length": str(len(body)),
        "Content-Type": "application/json",
        "Authorization": "Bearer local-relay",
    }
    handler = _FakeRequestHandler("/v1/chat/completions", "POST", body, headers)
    urlopen_calls: list[Request] = []

    def _fake_urlopen(request: Request, timeout: float | None = None, context: object = None) -> _FakeUpstreamCtxResp:
        urlopen_calls.append(request)
        return _FakeUpstreamCtxResp()

    with (
        patch.object(
            relay,
            "DEEPSEEK_CFG",
            {"base": "https://api.deepseek.com", "model": "deepseek-v4-pro", "api_key": "sk-real-secret",
             "thinking": None, "reasoning_effort": None, "reasoning_content_guard": "block"},
        ),
        patch.object(relay, "UPSTREAM_BASE", "https://api.deepseek.com"),
        patch.object(relay, "urlopen", _fake_urlopen),
        patch.object(relay, "write_jsonl", lambda record: None),
        patch.object(relay, "RELAY_COMPRESS_ACTIVE", False),
    ):
        relay.RelayHandler._handle_proxy(handler)  # type: ignore[arg-type]

    assert urlopen_calls == []  # the paid call never happened
    assert handler.status_code == 422
    body_sent_to_client = json.loads(handler.wfile.getvalue())
    assert body_sent_to_client["error"]["code"] == "relay_deepseek_reasoning_content_missing"


def test_redact_headers_masks_credential_style_headers():
    headers = {
        "Authorization": "Bearer sk-real-secret",
        "Cookie": "session=abc123",
        "Proxy-Authorization": "Basic xyz",
        "X-Auth-Token": "tok-secret",
        "X-Api-Key": "key-secret",
        "Content-Type": "application/json",
    }
    redacted = relay.redact_headers(headers)
    assert redacted["Authorization"] == "Bearer ***REDACTED***"
    assert redacted["Cookie"] == "***REDACTED***"
    assert redacted["Proxy-Authorization"] == "***REDACTED***"
    assert redacted["X-Auth-Token"] == "***REDACTED***"
    assert redacted["X-Api-Key"] == "***REDACTED***"
    assert redacted["Content-Type"] == "application/json"  # not touched


def test_redact_headers_masks_response_set_cookie():
    """Regression: redact_headers() is also applied to upstream *response* headers
    (response.headers in the JSONL record) -- a real Set-Cookie from a cloud provider is just
    as sensitive as a request-side credential and must not leak to disk."""
    headers = {"Set-Cookie": "session_id=super-secret; Path=/", "Content-Type": "application/json"}
    redacted = relay.redact_headers(headers)
    assert redacted["Set-Cookie"] == "***REDACTED***"
    assert redacted["Content-Type"] == "application/json"


def test_redact_headers_masks_additional_token_variants():
    headers = {
        "X-Session-Token": "s1",
        "X-Refresh-Token": "r1",
        "X-Bearer-Token": "b1",
        "X-Amz-Security-Token": "a1",
        "Authentication-Info": "ai1",
        "Proxy-Authentication-Info": "pai1",
        "Cookie2": "c2",
    }
    redacted = relay.redact_headers(headers)
    assert all(v == "***REDACTED***" for v in redacted.values())


def test_prepare_upstream_request_headers_strips_transfer_encoding_and_proxy_connection():
    headers = {
        "Transfer-Encoding": "chunked",
        "Proxy-Connection": "keep-alive",
        "Content-Type": "application/json",
    }
    out = relay._prepare_upstream_request_headers(headers)
    assert "Transfer-Encoding" not in out
    assert "Proxy-Connection" not in out
    assert out["Content-Type"] == "application/json"


def test_prepare_upstream_request_headers_strips_connection_listed_headers():
    headers = {
        "Connection": "X-Internal, X-Debug-Trace",
        "X-Internal": "secret-internal-value",
        "X-Debug-Trace": "trace-id-1",
        "Content-Type": "application/json",
    }
    out = relay._prepare_upstream_request_headers(headers)
    assert "X-Internal" not in out
    assert "X-Debug-Trace" not in out
    assert out["Content-Type"] == "application/json"


def test_handle_proxy_does_not_write_cookie_or_proxy_auth_to_jsonl_record():
    """Regression for the confirmed bug: request_headers written to the JSONL record were only
    ever passed through redact_headers(), which previously missed Cookie/Proxy-Authorization/
    X-Auth-Token entirely — those leaked to disk in plaintext on every request, unconditionally
    (not gated by KILO_RELAY_FULL_BODY). This drives the real _handle_proxy and inspects the
    actual record that would be written, not just the redact_headers() helper in isolation."""
    body = b'{"model":"qwen3-coder-next-q4ks","messages":[{"role":"user","content":"hi"}]}'
    headers = {
        "Content-Length": str(len(body)),
        "Content-Type": "application/json",
        "Cookie": "session=super-secret-session-id",
        "Proxy-Authorization": "Basic dXNlcjpwYXNz",
        "X-Auth-Token": "tok-super-secret",
    }

    with (
        patch.object(relay, "DEEPSEEK_CFG", None),
        patch.object(relay, "UPSTREAM_BASE", "http://127.0.0.1:8080"),
    ):
        _sent, record = _run_handle_proxy("/v1/chat/completions", body, headers)

    logged_headers = record["request_headers"]
    assert logged_headers["Cookie"] == "***REDACTED***"
    assert logged_headers["Proxy-Authorization"] == "***REDACTED***"
    assert logged_headers["X-Auth-Token"] == "***REDACTED***"
    dumped = json.dumps(record)
    assert "super-secret-session-id" not in dumped
    assert "dXNlcjpwYXNz" not in dumped
    assert "tok-super-secret" not in dumped


def test_handle_proxy_deepseek_strips_cookie_and_proxy_auth_from_outbound_request():
    body = b'{"model":"qwen3-coder-next-q4ks","messages":[{"role":"user","content":"hi"}]}'
    headers = {
        "Content-Length": str(len(body)),
        "Content-Type": "application/json",
        "Authorization": "Bearer local-relay",
        "Cookie": "session=super-secret-session-id",
        "Proxy-Authorization": "Basic dXNlcjpwYXNz",
    }

    with (
        patch.object(
            relay,
            "DEEPSEEK_CFG",
            {"base": "https://api.deepseek.com", "model": "deepseek-v4-pro", "api_key": "sk-real-secret",
             "thinking": None, "reasoning_effort": None, "reasoning_content_guard": "warn"},
        ),
        patch.object(relay, "UPSTREAM_BASE", "https://api.deepseek.com"),
    ):
        sent, _record = _run_handle_proxy("/v1/chat/completions", body, headers)

    assert sent.get_header("Cookie") is None
    assert sent.get_header("Proxy-Authorization") is None
