# E32: Workflow SDK trigger (Cursor Agent из терминала)

**Статус:** план зафиксирован в `doc/backlog_registry.yaml` → пакет `workflow-dx-p6-cursor-sdk-trigger` (волна `wave-workflow-dx`).  
**Дата плана:** 2026-05-03  

## Цель

Убрать ручной шаг «открыть Composer и выполнить `doc/current_task.md`» в ветках `execution_auto` и `ready_orch`. После реализации цикл от принятого контракта до `closed` идёт без участия человека в IDE; единственный ручной шаг остаётся — **принятие контракта** (plan-next Phase 7).

## Архитектура (кратко)

1. `run_autonomous.py` / роутер формирует `doc/current_task.md` (и при необходимости `task_started.md`).
2. При `--loop --watch-contract --trigger-cmd "…"` вызывается `_invoke_trigger_cmd(cmd, path_to_current_task)`.
3. Триггер по умолчанию: `npx tsx scripts/cursor_agent_trigger.ts` → содержимое файла в `Agent.prompt()` (`@cursor/sdk`), ключ **`CURSOR_API_KEY`** только из env.
4. Агент пишет `execution_contract.md` в `archive/team_artifacts/<package>/`; далее существующий `_wait_for_file` и `--post-agent` / close.

## Write-set (исполнение)

| Файл | Действие |
|------|----------|
| `scripts/cursor_agent_trigger.ts` | создать |
| `scripts/workflow.py` | `--trigger-cmd`, `_invoke_trigger_cmd`, ветки ready_fresh / ready_orch |
| `.env.example` | `CURSOR_API_KEY=` |
| `doc/team_workflow/workflow_router.md` | флаг, ручные шаги, таймлайн |
| `tests/test_workflow_router.py` | 3–4 теста |
| `package.json` или `scripts/package.json` | `@cursor/sdk`, `tsx` (dev) |

## DoD

- `.\.venv\Scripts\python.exe -m pytest tests/test_workflow_router.py -v` — зелёный.
- Документирован пример:  
  `workflow.py --loop --skip-review --watch-contract --trigger-cmd "npx tsx scripts/cursor_agent_trigger.ts"`.
- Без `--trigger-cmd` поведение PAUSE не регрессирует.
- Защита от повторного триггера при рестарте роутера согласована с логикой `task_started` / наличия контракта.

## Риски

| Риск | Митигация |
|------|-----------|
| Нестабильный API `@cursor/sdk` | сообщение + fallback на PAUSE с подсказкой |
| Зависание агента | `--watch-timeout`, exit 1 |
| Утечка ключа в логи | только env, не CLI-аргументы |

## Ссылка на реестр

Полный контракт полей (`blocks`, `exit_artifact`, `dod_commands`) — в записи **`workflow-dx-p6-cursor-sdk-trigger`** в `doc/backlog_registry.yaml`.
