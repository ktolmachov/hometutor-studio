# Контрактный промпт: breakthrough по бюджету промпта (content_stats → AGENTS/CLAUDE)

**Дата:** 2026-07-22  
**Пакет:** `kilo_prompt_content_budget_breakthrough`  
**Цель:** на порядок снизить расход токенов Cursor→relay→DeepSeek за счёт evidence-based правок read-set / `token_safety_registry` / `AGENTS.md` / `CLAUDE.md` (оба корня при необходимости).

Скопируй блок **Prompt** в новый чат агента (свежий тред!). Логирование уже в релеe — сначала собери данные, потом правь бюджеты.

---

## Prompt

```text
Goal
Глубоко разобрать, ЧТО именно засоряет proxied chat.completions через kilo_proxy_relay
(Cursor → relay → DeepSeek), по полям content_stats в logs/kilo_relay.jsonl.
На основе цифр (не догадок) актуализировать бюджеты/запреты full_read для файлов,
которые больше всего раздувают контекст, в:
- D:\Projects\hometutor-studio\AGENTS.md
- D:\Projects\hometutor-studio\CLAUDE.md
- D:\Projects\hometutor-studio\doc\token_safety_registry.json
- и при наличии расхождений: D:\Projects\hometutor\AGENTS.md, D:\Projects\hometutor\CLAUDE.md
Добиться измеримого снижения prompt_tokens (порядок: с >100k in на длинной сессии
к устойчивым ≤12k target / ≤20k hard на типичном ходе в НОВОМ чате + дисциплина read-set).

Scope
1) Сбор evidence из JSONL (обязательно), в этом порядке:
   - Перезапустить relay с KILO_RELAY_CONTENT_STATS=1 (дефолт), cloud_budget, DeepSeek.
   - Прогнать 5–15 реальных chat-запросов в НОВОМ Cursor-чате (короткий сценарий + 1–2 tool-heavy).
   - СНАЧАЛА сухой прогон БЕЗ --json-out:
     .\.venv\Scripts\python.exe scripts/kilo_prompt_content_report.py --last 40
     Убедиться, что chat_with_stats > 0 (иначе exit 2 — лог ещё старый).
   - ТОЛЬКО потом писать JSON (иначе перезапишешь пустым отчётом):
     .\.venv\Scripts\python.exe scripts/kilo_prompt_content_report.py --last 40 --json-out logs/kilo_content_report.json
     Скрипт сам откажет --json-out при chat_with_stats=0.
2) Анализ (только по report + выборочно 2–3 JSONL records.content_stats):
   - top_kinds (tool_result vs system vs user_query vs assistant_tool_calls)
   - top_fragments (rules, available_skills, mcp_*, agent_transcripts, …)
   - top_paths / agents_claude_mentions / top_extensions
   - top_tools_schema
   - сравнить content_stats.original vs forwarded (что реально срезает cloud_budget)
   - ВАЖНО: path_chars / est_tok по путям — эвристика окна ±200 симв. вокруг упоминания
     пути, НЕ реальные байты файла. Используй ranking (кто выше — приоритетнее запретить
     full-read), НЕ вписывай эти est_tok как точные лимиты в token_safety_registry.
3) Рекомендации с приоритетом savings×(1/quality_risk):
   A. Без потери качества агента (IDE + registry + AGENTS rules)
   B. Opt-in cloud_budget strip flags
   C. Чего НЕ делать без явного решения (GUARD_MODE=block по умолчанию; SLIM=local на Cursor→DeepSeek). Trim history в relay — **реализован opt-in** (2026-07-23, см. `kilo_relay_history_window_tier_b_2026-07-23.md`).
4) Правки write-set (только после evidence):
   - token_safety_registry.json: full_read/forbidden + safe_hint для топ-засорителей
     (ранжирование по top_paths; без псевдоточных token numbers из path est_tok)
   - AGENTS.md / CLAUDE.md (studio; sync CODE_ROOT copies если они SSoT для агентов там):
     явные лимиты read-set, запрет full-read для топ-файлов, правило «новый чат при msgs/in hard»
5) DoD verification:
   - pytest tests/test_kilo_prompt_stats.py tests/test_kilo_proxy_relay.py -q
   - новый короткий чат: in= из мини-статы ≪ предыдущих 120k+; top_path/top_frag не доминируют AGENTS/CLAUDE full dumps
   - краткий отчёт в doc/next/ (1–2 экрана): before/after таблица

Files to inspect first
- scripts/_kilo_prompt_stats.py
- scripts/kilo_prompt_content_report.py
- scripts/kilo_proxy_relay.py (content_stats / sanitize_request_summary_for_log)
- logs/kilo_relay.jsonl (last records only; NEVER dump full bodies into the LLM context)
- logs/kilo_content_report.json (после генерации)
- doc/token_safety_registry.json (section for top paths only)
- AGENTS.md, CLAUDE.md (studio) — только секции Token Budget / Forbidden full-read / Тесты
- doc/kilo_proxy_relay.md § лог / content_stats

DoD
- [ ] content_stats присутствует в новых JSONL-записях chat completions
- [ ] kilo_prompt_content_report.py выдаёт top_paths / top_fragments / top_kinds / top_extensions
- [ ] Написан ranked list «файл/фрагмент → relative weight → действие» (без точных лимитов из path est_tok)
- [ ] Обновлены registry + AGENTS/CLAUDE под топ-засорители (без оверинжиниринга)
- [ ] Повторный короткий прогон: prompt_tokens заметно ниже (цель: укладываться в 12k/20k на обычном ходе)
- [ ] pytest по затронутым тестам зелёный

Do not touch (на момент исходного контракта; обновлено 2026-07-23)
- ~~Trim messages[] / history внутри relay~~ — **снято пользователем**; реализовано opt-in в `_kilo_relay_compress.py` (`KILO_RELAY_CLOUD_BUDGET_KEEP_LAST_MESSAGES`, `KILO_RELAY_CLOUD_BUDGET_MAX_TOOL_RESULT_CHARS`). См. `doc/next/kilo_relay_history_window_tier_b_2026-07-23.md`.
- Смена GUARD_MODE default на block (по-прежнему не трогать без отдельного решения)
- CODE_ROOT app/* (RAG domain A)
- Внешние Start-KiloRelay*.ps1 вне этого репо
- Полный pytest suite / full-read запрещённых файлов
- --json-out logs/kilo_content_report.json пока chat_with_stats=0 (пустой overwrite)

Output
1. Таблица топ засорителей (kind / fragment / path) с цифрами из report; path est_tok пометить как relative
2. Diff-план правок AGENTS/CLAUDE/registry (bullet list)
3. Фактические правки в write-set
4. Before/after: 2–3 строки мини-статы (in=, top_kind, top_path)
5. Открытые риски (reasoning_content, msgs growth) — коротко
```

---

## Как пользоваться (оператор)

```powershell
# 1) Релей (уже с content_stats)
$env:KILO_RELAY_UPSTREAM_PRESET = "deepseek"
$env:KILO_RELAY_SLIM_MODE = "cloud_budget"
$env:DEEPSEEK_THINKING = "disabled"
.\.venv\Scripts\python.exe scripts/kilo_proxy_relay.py

# 2) Новый чат в Cursor → 5–15 ходов (старый JSONL без content_stats не годится)

# 3) Сначала сухой отчёт; --json-out только если chat_with_stats > 0
.\.venv\Scripts\python.exe scripts/kilo_prompt_content_report.py --last 40
.\.venv\Scripts\python.exe scripts/kilo_prompt_content_report.py --last 40 --json-out logs/kilo_content_report.json

# 4) Вставить Prompt выше в новый агент-чат
```

**Напоминание:** `path_chars` в stats — окно ±200 симв. вокруг упоминания пути (`_kilo_prompt_stats.path_char_contributions`). Для registry это **ранг засорения**, не абсолютный бюджет токенов файла.

## Ожидаемый «прорыв»

| Рычаг | Ожидание |
|---|---|
| Новый чат (срезать msgs≈250) | `in` с ~130k → десятки k на старте |
| cloud_budget (уже) | ~30k chars XML/schema tax |
| thinking=disabled (уже) | меньше output/latency |
| Registry + AGENTS запрет full-read топ-файлов | убрать повторные full dumps AGENTS/CLAUDE/conventions/epochs |
| Дисциплина tool results | сдержать рост msgs |

Порядок снижения достигается **комбинацией** (новый чат + не читать тяжёлые SSoT целиком), а не одним strip в релеe.
