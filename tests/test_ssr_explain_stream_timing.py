"""SSR /ssr/explain stream completion metric (P0 baseline)."""

from __future__ import annotations

import logging
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api import app


def test_ssr_explain_stream_completed_logged() -> None:
    tokens = ["Привет", " мир"]
    client = TestClient(app)
    with patch("app.routers.ssr.stream_explanation_tokens", return_value=iter(tokens)):
        with patch("app.routers.ssr.log_event") as mock_log:
            resp = client.post(
                "/ssr/explain",
                json={
                    "ctx": {},
                    "hint_kind": "resume",
                    "primary_label_ru": "Тьютор",
                    "why_now_ru": "Продолжить",
                    "primary_nav": "tutor",
                },
            )
    assert resp.status_code == 200
    assert b"[DONE]" in resp.content
    completed = [
        c
        for c in mock_log.call_args_list
        if len(c.args) >= 3 and c.args[2] == "ssr_explain_stream_completed"
    ]
    assert len(completed) == 1
    fields = completed[0].kwargs
    assert fields.get("token_count") == 2
    assert isinstance(fields.get("stream_ms"), float)
