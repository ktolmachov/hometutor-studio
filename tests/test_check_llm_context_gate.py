from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_check_llm_context_gate_passes_without_incidents(tmp_path) -> None:
    log_dir = tmp_path / "cost_logs"
    log_dir.mkdir()
    payload = {
        "timestamp": "2026-04-23T06:42:00Z",
        "model": "grok-4.1-fast-thinking",
        "input_tokens": 8000,
        "output_tokens": 300,
        "cost_rub": 0.5,
        "status": "OK",
        "prompt_stats": {
            "total_chars": 30000,
            "messages_count": 2,
            "chars_per_token_estimate": 3.75,
            "char_limit_warning": False,
        },
    }
    (log_dir / "cost_logs_2026-04-23.jsonl").write_text(
        json.dumps(payload, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "check_llm_context_gate.py"),
            "--log-dir",
            str(log_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "PASS: LLM context gate passed" in proc.stdout


def test_check_llm_context_gate_fails_and_can_emit_json(tmp_path) -> None:
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
            str(ROOT / "scripts" / "check_llm_context_gate.py"),
            "--log-dir",
            str(log_dir),
            "--json-out",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert proc.returncode == 2, proc.stderr + proc.stdout
    stdout_lines = [line for line in proc.stdout.splitlines() if line.strip()]
    data = json.loads("\n".join(stdout_lines[:-1]))
    assert data["context_length_errors"] == 1
    assert "FAIL: LLM context gate failed" in stdout_lines[-1]
