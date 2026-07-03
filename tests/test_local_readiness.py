from __future__ import annotations

import socket
from pathlib import Path

import pytest

from scripts import local_readiness


def _minimal_repo(root: Path) -> None:
    (root / "app" / "ui").mkdir(parents=True)
    (root / "app" / "api.py").write_text("", encoding="utf-8")
    (root / "app" / "ui" / "main.py").write_text("", encoding="utf-8")
    (root / "ingest.py").write_text("", encoding="utf-8")
    (root / "requirements.txt").write_text("", encoding="utf-8")
    (root / ".venv" / "Scripts").mkdir(parents=True)
    (root / ".venv" / "Scripts" / "python.exe").write_text("", encoding="utf-8")
    (root / "data").mkdir()
    (root / "chroma_db").mkdir()
    (root / "logs").mkdir()


def test_read_dotenv_strips_inline_comments_and_quotes(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "OPENAI_API_KEY='local' # accepted placeholder for local providers",
                'LLM_MODEL="qwen2.5:7b-instruct"',
                "EMPTY_VALUE=",
                "COMMENTED_HASH='value # kept'",
            ]
        ),
        encoding="utf-8",
    )

    values = local_readiness.read_dotenv(env_path)

    assert values["OPENAI_API_KEY"] == "local"
    assert values["LLM_MODEL"] == "qwen2.5:7b-instruct"
    assert values["EMPTY_VALUE"] == ""
    assert values["COMMENTED_HASH"] == "value # kept"


def test_read_runtime_env_uses_config_defaults_then_dotenv_overrides(tmp_path: Path) -> None:
    (tmp_path / "config.env").write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=from-config",
                "LLM_MODEL=qwen/qwen3.6-27b",
                "EMBED_API_BASE=https://openrouter.ai/api/v1",
                "SSR_LLM_API_BASE=http://127.0.0.1:1234/v1",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text("OPENAI_API_KEY=local\n", encoding="utf-8")

    values = local_readiness.read_runtime_env(tmp_path)

    assert values["OPENAI_API_KEY"] == "local"
    assert values["LLM_MODEL"] == "qwen/qwen3.6-27b"
    assert values["EMBED_API_BASE"] == "https://openrouter.ai/api/v1"
    assert values["SSR_LLM_API_BASE"] == "http://127.0.0.1:1234/v1"


def test_check_env_rejects_default_placeholder(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("OPENAI_API_KEY=your-key-here\n", encoding="utf-8")

    results = local_readiness.check_env(
        tmp_path,
        {"OPENAI_API_KEY": "your-key-here"},
    )

    assert results[0].status == "fail"
    assert "placeholder" in results[0].message


def test_demo_mode_allows_missing_data_dirs_when_demo_data_exists(tmp_path: Path) -> None:
    (tmp_path / "demo_data").mkdir()

    results = local_readiness.check_dirs(tmp_path, mode="demo")
    by_name = {item.name: item for item in results}

    assert by_name["data/"].status == "warn"
    assert by_name["chroma_db/"].status == "warn"
    assert by_name["logs/"].status == "warn"


def test_main_returns_zero_for_minimal_ready_repo(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _minimal_repo(tmp_path)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=local\n", encoding="utf-8")
    monkeypatch.setattr(local_readiness, "_port_available", lambda _host, _port: True)

    code = local_readiness.main(["--root", str(tmp_path), "--json"])

    captured = capsys.readouterr()
    assert code == 0
    assert '"ok": true' in captured.out


def test_occupied_port_is_blocker_unless_allowed() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen()
    try:
        port = sock.getsockname()[1]
        assert local_readiness._port_available("127.0.0.1", port) is False
    finally:
        sock.close()
