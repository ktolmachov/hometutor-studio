from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_summarize_cost_logs_reports_context_incidents(tmp_path) -> None:
    log_dir = tmp_path / "cost_logs"
    log_dir.mkdir()
    payload = [
        {
            "timestamp": "2026-04-23T06:41:04Z",
            "model": "grok-4.1-fast-thinking",
            "input_tokens": 15000,
            "output_tokens": 0,
            "cost_rub": 0.9,
            "package_id": "epoch-a",
            "prompt_type": "planning",
            "status": "ERR",
            "prompt_stats": {
                "total_chars": 185816,
                "messages_count": 3,
                "chars_per_token_estimate": 12.387,
                "char_limit_warning": True,
            },
            "provider_error": {
                "error_kind": "context_length_exceeded",
                "input_char_limit": 128000,
                "input_char_actual": 185816,
            },
        },
        {
            "timestamp": "2026-04-23T06:42:00Z",
            "model": "grok-4.1-fast-thinking",
            "input_tokens": 8000,
            "output_tokens": 300,
            "cost_rub": 0.5,
            "package_id": "epoch-b",
            "prompt_type": "rewrite",
            "status": "OK",
            "prompt_stats": {
                "total_chars": 30000,
                "messages_count": 2,
                "chars_per_token_estimate": 3.75,
                "char_limit_warning": False,
            },
        },
    ]
    (log_dir / "cost_logs_2026-04-23.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in payload) + "\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "summarize_cost_logs.py"),
            "--log-dir",
            str(log_dir),
            "--limit-files",
            "1",
            "--top",
            "3",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "Context-length errors: 1" in proc.stdout
    assert "185,816" in proc.stdout
    assert "actual=185,816" in proc.stdout


def test_summarize_cost_logs_can_emit_json_and_fail_on_context_errors(tmp_path) -> None:
    log_dir = tmp_path / "cost_logs"
    log_dir.mkdir()
    payload = {
        "timestamp": "2026-04-23T06:41:04Z",
        "model": "grok-4.1-fast-thinking",
        "input_tokens": 15000,
        "output_tokens": 0,
        "cost_rub": 0.9,
        "status": "ERR",
        "prompt_stats": {
            "total_chars": 185816,
            "messages_count": 3,
            "chars_per_token_estimate": 12.387,
            "char_limit_warning": True,
        },
        "provider_error": {
            "error_kind": "context_length_exceeded",
            "input_char_limit": 128000,
            "input_char_actual": 185816,
        },
    }
    (log_dir / "cost_logs_2026-04-23.jsonl").write_text(
        json.dumps(payload, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "summarize_cost_logs.py"),
            "--log-dir",
            str(log_dir),
            "--json",
            "--fail-on-context-errors",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert proc.returncode == 2, proc.stderr + proc.stdout
    data = json.loads(proc.stdout)
    assert data["context_length_errors"] == 1
    assert data["top_by_chars"][0]["prompt_stats"]["total_chars"] == 185816
