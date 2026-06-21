from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from command_guard import check


def _policy() -> dict:
    return {
        "blocked_commands": [
            {"prefix": ["git", "reset", "--hard"], "reason": "no reset"},
            {"prefix": ["git", "push"], "reason": "no push"},
        ],
        "blocked_arg_fragments": [".env", "secrets/"],
        "blocked_shell_tokens": ["&&", ";"],
    }


def test_blocks_destructive_git_reset() -> None:
    decision, reason = check(["git", "reset", "--hard"], _policy())
    assert decision == "BLOCK"
    assert "reset" in reason


def test_blocks_sensitive_path_fragment() -> None:
    decision, reason = check(["python", "tool.py", "--out", "secrets/key.txt"], _policy())
    assert decision == "BLOCK"
    assert "sensitive" in reason


def test_blocks_shell_control_tokens() -> None:
    decision, reason = check(["pytest", "tests/test_a.py", "&&", "git", "push"], _policy())
    assert decision == "BLOCK"
    assert "shell" in reason


def test_allows_targeted_pytest_command() -> None:
    decision, reason = check(
        [r".\.venv\Scripts\python.exe", "-m", "pytest", "tests/test_pipeline_events.py", "-v"],
        _policy(),
    )
    assert (decision, reason) == ("ALLOW", "allowed")
