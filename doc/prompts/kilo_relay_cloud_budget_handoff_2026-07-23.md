# Handoff: kilo_proxy_relay / cloud_budget (+ продолжение работы)

| Поле | Значение |
|------|----------|
| Дата фиксации | 2026-07-23 (актуализация вечер) |
| Контекст | После успешного New Session сессия снова раздулась на product/tool-loop (`orig_msgs` ~165→287) |
| Тема | Handoff в новый чат: релей ок и задокументирован; текущий Cursor-тред снова bloated |
| Источник | Live stderr `kilo_proxy_relay` + фиксация в `doc/kilo_proxy_relay.md` § Live evidence |
| Связанные доки | [`doc/kilo_proxy_relay.md`](../kilo_proxy_relay.md), [`doc/next/kilo_relay_history_window_tier_b_2026-07-23.md`](../next/kilo_relay_history_window_tier_b_2026-07-23.md), [`doc/changelog.md`](../changelog.md) 2026-07-23 |
| Live-проверка | New Session `id=23aba908`: `body_orig` 821 КБ→66 КБ, `msgs` 15→2. Позже тот же «новый» чат снова `session=bloated` (~95k→135k orig_tok) при работе над `tests/e2e/test_surface_focus_live.py` |

Текст ниже можно копировать в **New Session** как единый запрос.

---

```text
Handoff: продолжение после bloated Cursor-сессии (релей уже в норме)

## Зачем этот чат
Предыдущий Agent-тред снова раздулся (orig_msgs ~165→287, body_orig ~450→620 КБ, на каждом запросе `session=bloated recommend=new_chat`). Это **New Session + handoff**, не донастройка релея.

## Статус релея (закрыто, не трогать без явной просьбы)
Канон работает и задокументирован:
- `cloud_budget` + DeepSeek + Tier B `KEEP_LAST=14` / `MAX_TOOL_RESULT=1500` + `TRIM_TOOLS=1` → `tools=6`
- `GUARD_MODE=block` (если unset), session-health, path-fix без `y://n`
- Forwarded-бюджет стабилен: `guard=ok`, `in` обычно 2–7k, HTTP 413 нет
- Evidence: `doc/kilo_proxy_relay.md` § Live evidence; changelog 2026-07-23; handoff-файл обновлён

Код релея в hometutor-studio может быть ещё незакоммичен — коммит только по явной просьбе.

## Что делали в раздутом треде (ориентир, не ТЗ)
По логу релея доминировал `tests/e2e/test_surface_focus_live.py` (и ранее смежные UI/e2e пути). Точный статус правок в этом handoff **не зафиксирован** — перед работой сверь `git status` / diff по запросу пользователя.

## Правила этого чата (обязательно)
1. Handoff принят. Работа по compress/релею **закрыта**, пока пользователь явно не попросит иначе.
2. После подтверждения **не** спрашивай «что дальше?». Жди задачу пользователя.
3. Не читай весь репозиторий «для контекста». Read-set: только то, что нужно для следующей явной задачи (2–5 файлов).
4. Если в логе релея снова часто `session=bloated` — предложи короткий handoff + New Session; не ужесточай `keep_last` сам.
5. Коммит / push — только после явной просьбы.

## Контекст запуска релея (если понадобится)
- `.\.venv\Scripts\python.exe scripts/kilo_proxy_relay.py`
- Cursor Base URL: `http://127.0.0.1:8787/v1`
- Env: `SLIM_MODE=cloud_budget`, `UPSTREAM_PRESET=deepseek`, `KEEP_LAST=14`, `MAX_TOOL_RESULT=1500`, `TRIM_TOOLS=1`, stub/strip flags как в баннере

## Формат ответа на этот промпт
2–4 коротких пункта: handoff принят; релей ок / не трогаю; этот чат = fresh; жду задачу.
Запрещено: вопросы «что дальше», планы «улучшить релей», широкий explore.
```
