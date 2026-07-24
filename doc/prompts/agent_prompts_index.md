# Архив Agent Prompts

## Token budget (read-set)

Архивные контракты могут содержать длинные списки «Read first». Перед запуском в Cursor:

- Свести фактический read-set к **3–5 файлам** с явным **режимом** (signatures / секция / `rg` + один тест), см. `doc/agent_workflow_rules.md`, `doc/agent_workflow_templates.md` и `doc/token_optimization_checklist.md`.
- Полные запреты и оценки: `doc/token_safety.md`, реестр `doc/token_safety_registry.json`, проверка `python scripts/check_readset.py …`.
- **Owner / Write-set ≠ read-set** — не открывать все owner-файлы целиком без строки **Read ONLY**.

## Index

> **LEGACY** — The manual index table has been removed to prevent state duplication with
> `doc/backlog_registry.yaml` (SSoT). This folder is an append-only archive of generated
> prompt artifacts. To find recent prompts use file search or `ls -t archive/agent_prompts/`.

The manual table index has been removed to prevent state duplication.
Please use file search or ls -t to find recent prompts.

## Prompts

- [Token Analysis — Cursor AI High Input Token Consumption](token_analysis_cursor_ai_2026-04-19.md) — Анализ причин высокого потребления входных токенов в сессии Cursor AI (2026-04-19)
- [Handoff: kilo_proxy_relay / cloud_budget](kilo_relay_cloud_budget_handoff_2026-07-23.md) — Handoff в New Session: релей ок; повторный bloated после tool-loop (актуализация вечер 2026-07-23)
- [Evolutionary Wave Continuation Template](evolutionary_wave_continuation_template.md) — Шаблон продолжения реализации по эволюционным разборам с обязательным финальным doc-sync двух README

## Как добавить prompt в архив

См. инструкцию: [ARCHIVE_ADD_PROMPT.md](ARCHIVE_ADD_PROMPT.md)
