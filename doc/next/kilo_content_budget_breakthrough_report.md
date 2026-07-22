# Отчёт: kilo_prompt_content_budget_breakthrough

**Дата:** 2026-07-22 (addendum Tier B: 2026-07-23)  
**Evidence:** `logs/kilo_relay.jsonl` (last 40 + live Tier B session), `logs/kilo_content_report.json` (optional)

## 1. Топ засорители (relative rank)

| Rank | Kind / fragment / path | Chars (report) | est_tok* | Действие |
|------|------------------------|----------------|----------|----------|
| 1 | **kind: tool_result** | 81 180 | ~20 295 | read-set 2–3 файла; не full-read тестов/доков в tool loop |
| 2 | **kind: system** | 22 164 | ~5 541 | `<rules>` уже несёт AGENTS; не дублировать Read |
| 3 | **frag: rules** | 21 960 | ~5 490 | AGENTS/CLAUDE только секции; registry `full_read: forbidden` |
| 4 | **path: backlog_registry.yaml** | 17 298 | ~4 324 | **forbidden** — только `rg` по PACKAGE_ID |
| 5 | **path: doc/tasklist.md** | 7 485 | ~1 871 | derived view; статус из yaml-блока |
| 6 | **ext: .md** | 70 047 | ~17 511 | signatures / section-only |
| 7 | **ext: .py** | 42 345 | ~10 586 | grep `^def test_` / signatures |
| 8 | **ext: .yaml** | 17 298 | ~4 324 | backlog yaml — главный yaml-засоритель |

\* `path_chars` / `est_tok` — эвристика окна ±200 симв. вокруг упоминания пути, **не** размер файла.

### Before (длинная сессия, last 40 chat без content_stats)

| Метрика | Значение |
|---------|----------|
| `prompt_tokens` avg / max | **131 529 / 141 501** |
| `messages_count` avg | **232** |
| `body_chars` avg | **476 062** |
| `role_chars` (sum last 40) | tool **10.0M** (≈91%), system 850k, user 761k, assistant 436k |

### After (короткий сценарий, 3 POST с content_stats; relay cloud_budget)

| Метрика | Значение |
|---------|----------|
| `chat_with_stats` | 3 |
| top_kind | tool_result ~20k tok (relative) |
| top_frag | rules ~5.5k tok |
| top_path | backlog_registry.yaml ~4.3k tok (relative) |
| cloud_budget strip | ~42 chars / ~10 tok на запрос (XML/skills trim); **rules не режутся** |

### After Tier B (2026-07-23, live Cursor→DeepSeek, `cloud_budget` + history window)

Env: `KILO_RELAY_CLOUD_BUDGET_KEEP_LAST_MESSAGES=24`, `MAX_TOOL_RESULT_CHARS=4000`, system stub + strip rules/user_info; **без** `TOOLS_ALLOWLIST` (schemas ~2k tok).

| Метрика | До Tier B (та же сессия) | После Tier B |
|---------|--------------------------|--------------|
| `prompt_tokens` (`in=`) | ~83 500 | **~5 500–5 700** |
| `msgs` forwarded | ~165 | **25** |
| `tools` forwarded | 16 (или 0 при сломанном allowlist) | **16** |
| `guard` | hard_block | **soft_block** |
| stderr | `saved≈32k` | `saved≈430k`, `hist_cut≈240` |

Детали и env: [kilo_relay_history_window_tier_b_2026-07-23.md](kilo_relay_history_window_tier_b_2026-07-23.md), [kilo_proxy_relay.md](../kilo_proxy_relay.md) § Tier B.

## 2. Diff-план (выполнено)

- **token_safety_registry.json:** `full_read: forbidden` + `safe_hint` для `AGENTS.md`, `CLAUDE.md`, `doc/backlog_registry.yaml`, `doc/closed_iterations.md`, `doc/conventions_architecture.md`, `doc/conventions_reference.md`, `doc/agent_workflow_templates.md`.
- **AGENTS.md:** явный запрет full-read топ-SSoT; правило «новый чат» при msgs≫15 / in>20k.
- **CLAUDE.md:** те же файлы в Forbidden Full-Read; правило long session → new chat.

## 3. Не делать (B/C) — обновлено 2026-07-23

| Не трогать | Почему |
|------------|--------|
| Trim `messages[]` **по умолчанию** / без opt-in | ломает tool/reasoning continuity; **Tier B — только явные env** (`KILO_RELAY_CLOUD_BUDGET_KEEP_LAST_MESSAGES`, `KILO_RELAY_CLOUD_BUDGET_MAX_TOOL_RESULT_CHARS`) |
| `SLIM_MODE=local` на Cursor→DeepSeek | stub system + allowlist хуже cloud_budget |
| Opt-in strip `<rules>` в relay | риск потери policy; экономия через registry/агента |
| `KILO_RELAY_TOOLS_ALLOWLIST` с PascalCase без проверки | Cursor tools lowercase → **tools=0**, модель без tool_calls (allowlist теперь case-insensitive, но лучше не задавать без нужды) |

## 4. Открытые риски

- **reasoning_content:** multi-turn DeepSeek tool-loop может требовать `reasoning_content` в history — relay не чинит между запросами.
- **msgs growth:** Tier B срезает хвост истории в relay, но длинный чат всё равно растёт в Cursor; при `in`>20k — новый чат + relay guard soft/hard.
- **Повторная верификация:** для production before/after прогоните 5–15 ходов в **новом** Cursor-чате с перезапущенным relay (`KILO_RELAY_CONTENT_STATS=1`).

## 5. Команды верификации

```powershell
.\.venv\Scripts\python.exe scripts/kilo_prompt_content_report.py --last 40
.\.venv\Scripts\python.exe -m pytest tests/test_kilo_prompt_stats.py tests/test_kilo_proxy_relay.py tests/test_kilo_relay_compress.py -q
```
