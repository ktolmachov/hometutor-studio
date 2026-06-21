"""Канонические строки подсказок для `workflow.py` (SSoT для промптов агента).

Документ для людей: `doc/team_workflow/workflow_router.md` — не дублировать длинные
цитаты вручную; при смене формулировок править здесь и прогонять `test_workflow_router.py`.
"""
from __future__ import annotations

from pathlib import Path

WORKFLOW_ROUTER_DOC_REL = "doc/team_workflow/workflow_router.md"

PROMPT_BLOCK_HEADER = "Промпт для агента (вставить в чат):\n"

SHORT_EXECUTE_CURRENT_TASK_PROMPT_LINE = '  «Выполни doc/current_task.md»'


def format_long_execute_current_task_line(rel_contract_posix: str) -> str:
    return (
        f'  «Выполни задачу из doc/current_task.md целиком, включая обязательный '
        f"финальный шаг: создай файл {rel_contract_posix}.»"
    )


def format_prompt_execute_current_task_footer(rel_contract_posix: str) -> str:
    """Блок промпта для агента: длинная строка + краткая (как в консоли роутера)."""
    return (
        f"{PROMPT_BLOCK_HEADER}"
        f"{format_long_execute_current_task_line(rel_contract_posix)}\n"
        "Краткий вариант (если в current_task.md уже расписан финальный шаг):\n"
        f"{SHORT_EXECUTE_CURRENT_TASK_PROMPT_LINE}"
    )


def format_workflow_router_doc_footer(repo_root: Path) -> str:
    """Путь к workflow_router.md + file:// URI + якоря для IDE/браузера."""
    md_path = repo_root / "doc" / "team_workflow" / "workflow_router.md"
    try:
        uri = md_path.as_uri()
    except ValueError:
        uri = WORKFLOW_ROUTER_DOC_REL
    return (
        f"Документация: {WORKFLOW_ROUTER_DOC_REL}\n"
        f"  Открыть файл: {uri}\n"
        "  Якоря: #manual-ready-executing · #canonical-agent-prompt · "
        "#router-graph · #router-loop-steps\n"
        "  Разделы: «Шесть состояний пайплайна»; «Граф переходов авто-цикла»; "
        "«Авто-цикл (--loop) — полная цепочка»."
    )
