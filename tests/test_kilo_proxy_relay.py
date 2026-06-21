"""Tests for scripts/kilo_proxy_relay.py — streaming proxy, client disconnect, headers."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import kilo_proxy_relay as relay  # noqa: E402


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
