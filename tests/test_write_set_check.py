from __future__ import annotations

from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from write_set_check import check_current_task, parse_write_set


def test_parse_write_set_section() -> None:
    text = """# Task

## Write-Set
- `scripts/pipeline_events.py`
- tests/test_pipeline_events.py

## Other
- ignored.md
"""
    assert parse_write_set(text) == [
        "scripts/pipeline_events.py",
        "tests/test_pipeline_events.py",
    ]


def test_check_current_task_flags_out_of_scope(tmp_path: Path) -> None:
    task = tmp_path / "current_task.md"
    task.write_text("## Write-Set\n- scripts/\n", encoding="utf-8")

    result = check_current_task(
        task,
        root=tmp_path,
        changed_paths=["scripts/a.py", "app/other.py"],
    )

    assert result.out_of_scope == ("app/other.py",)
    assert result.missing_write_set is False


def test_check_current_task_missing_writeset_is_violation(tmp_path: Path) -> None:
    task = tmp_path / "current_task.md"
    task.write_text("# Task\n", encoding="utf-8")

    result = check_current_task(task, root=tmp_path, changed_paths=["app/a.py"])

    assert result.missing_write_set is True
    assert result.out_of_scope == ("app/a.py",)


def test_generated_prompt_bullet_write_set_lines_parse_as_paths() -> None:
    import importlib.util

    path = ROOT / "scripts" / "generate_next_prompt.py"
    text = path.read_text(encoding="utf-8")
    assert "## Write-Set" in text
    assert "write_set_bullets" in text
