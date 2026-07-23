# Handoff: kilo_proxy_relay / cloud_budget

| Поле | Значение |
|------|----------|
| Дата фиксации | 2026-07-23 |
| Контекст | Live-прогон cloud_budget после session-health / TRIM_TOOLS / path-fix; original-сессия ~600+ msgs |
| Тема | Короткий handoff в новый чат: релей ок, чат надо перезапустить |
| Источник | Рабочая сессия Cursor по аудиту и доработке `scripts/kilo_proxy_relay*` |
| Связанные доки | [`doc/kilo_proxy_relay.md`](../kilo_proxy_relay.md) § Live evidence, [`doc/next/kilo_relay_history_window_tier_b_2026-07-23.md`](../next/kilo_relay_history_window_tier_b_2026-07-23.md) |
| Live-проверка | **Подтверждено вечером 2026-07-23:** New Session дал сброс `body_orig` 821 КБ→66 КБ, `msgs` 15→2 (`id=23aba908`); дальше forwarded `in` 3–7k при `tools=6` / `guard=ok` |

Текст ниже можно копировать в новый чат агента как единый запрос.

---

```text
Handoff: kilo_proxy_relay / cloud_budget (продолжить с чистого чата)

## Цель
Держать Cursor→DeepSeek через локальный релей в бюджете (~≤12k prompt tok), не маскируя раздутую сессию: original vs forwarded раздельно, при bloated original — новый чат + handoff.

## Уже сделано (код в hometutor-studio, не закоммичено без явной просьбы)
1. History window: после tool-safe expand не раздувать keep_last (skip старых assistant+tool групп).
2. Guard: max_tools 13→16; для cloud_budget если GUARD_MODE unset → block.
3. Session health: при original >20k tok / >40 msgs / >110k body → stderr/JSONL `session=bloated … recommend=new_chat` (без HTTP-блока).
4. Opt-in TRIM_TOOLS + allowlist coding-core; канон MAX_TOOL_RESULT_CHARS=1500; keep_last=14 не ужесточали.
5. Path heuristic: убраны ложные top_path `y://n` и т.п.; report фильтрует junk.
6. Glance: top_frag из forwarded; docs `doc/kilo_proxy_relay.md` обновлены.
7. Тесты зоны kilo: ~157 passed (guard/compress/stats/relay).

## Live-проверка (последний прогон)
- Конфиг ок: block + TRIM_TOOLS → tools=6, guard=ok, in часто 3–5k, без soft_block.
- Но orig_msgs ~600→695, на каждом запросе recommend=new_chat → сессию надо было перезапустить (этот чат и есть перезапуск).

## Правила этого чата (обязательно)
1. Этот чат = уже выполненный перезапуск после bloated-сессии. Handoff принят — работа по релею/compress **закрыта**, пока пользователь явно не попросит иначе.
2. После подтверждения **не** спрашивай «что дальше?» / «что нужно делать?». Просто жди следующую задачу пользователя.
3. Пункты ниже — **не** очередь на автозапуск. Делай их только если пользователь прямо скажет.
4. При снова `session=bloated` в логе релея — сразу предложи короткий handoff + новый чат (не ужесточай compress сам).
5. Коммит — только после явной просьбы. Не читай весь репозиторий «для контекста».

## Опционально (только по явной просьбе пользователя)
- Включить TRIM в launcher CloudBudget / сверить Start-KiloRelayDaily с 14/1500 и без `GUARD_MODE=warn`.
- Задача по коду продукта → нужен PACKAGE_ID из backlog_registry.

## Контекст запуска
- Релей: `.\.venv\Scripts\python.exe scripts/kilo_proxy_relay.py`
- Base URL Cursor: `http://127.0.0.1:8787/v1`
- Типичный env: SLIM_MODE=cloud_budget, UPSTREAM_PRESET=deepseek, KEEP_LAST=14, MAX_TOOL_RESULT=1500, TRIM_TOOLS=1, REPLACE_CURSOR_SYSTEM=1, strip rules/user_info=1

## Формат ответа на этот промпт
Ровно 2–4 коротких пункта: handoff принят; релей/бюджет ок; этот чат = fresh; жду задачу.
Запрещено: вопросы «что дальше», планы на опциональные пункты, широкий explore репо.
```
