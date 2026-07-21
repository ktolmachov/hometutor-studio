# Обзор архитектуры Kilo → kilo_proxy_relay → llama.cpp

**Дата:** 2026-07-21
**Статус:** Review / готово к правкам
**Источники (прочитаны полностью):**
- `C:\Users\Kostya\Downloads\kilo_relay_daily_architecture\kilo_relay_daily_runbook.md`
- `C:\Users\Kostya\Downloads\kilo_relay_daily_architecture\Start-KiloRelayDaily.ps1`
- `C:\Users\Kostya\Downloads\kilo_relay_daily_architecture\Stop-KiloRelayDaily.ps1`
- `C:\Users\Kostya\Downloads\kilo_relay_daily_architecture\Test-KiloRelayDaily.ps1`
- `scripts/kilo_proxy_relay.py`, `scripts/_kilo_guard.py`, `scripts/_kilo_relay_compress.py` (DOCS_ROOT)
- `doc/local_llm_gateway_relay_litellm_report_2026-07-21.md`
- `app/config.py`, `app/llm_guards.py`, `app/token_utils.py`, `app/mnemo_keeper_budget.py` (CODE_ROOT, `D:\Projects\hometutor`)

---

## 0. Главная нестыковка: два несвязанных домена токенов

Запрос «слишком много токенов при запросах к ИИ моделям» может означать два **разных** бюджета. Приоритетная Kilo-архитектура чинит только один из них.

| Домен | Кто тратит | Где лимит | Влияет ли relay-архитектура? |
|---|---|---|---|
| **A. Runtime RAG приложения** | `app/provider_openai.py` → облачные модели (grok/claude/gpt) | `HARD_TOKEN_LIMIT=20 000` в `app/llm_guards.py` | ❌ Нет |
| **B. Kilo coding-ассистент** | Kilo IDE → llama.cpp qwen3-coder | relay char-guard 150k–240k | ✅ Да |

**Вывод:** relay снижает расход только на coding-ассистенте (домен B). Он не убирает ни одного токена из runtime-стоимости RAG-приложения (домен A). Если боль — в проде (запросы пользователей к RAG), это надо решать через §3 «Домен A», а не через Kilo-relay. Нужно явно зафиксировать, какой домен болит, иначе «прорыв» будет измерять не тот счётчик.

---

## 1. Карта токен-бюджетов приложения (домен A)

Источник истины: `app/llm_guards.py` + `app/config.py`.

- **Вход:** `HARD_TOKEN_LIMIT = 20 000` (→ `HardLimitExceededError`), `SOFT_TOKEN_LIMIT = 12 000` (только warning), `RAG_CONTEXT_PROMPT_RESERVE_TOKENS = 5 500`.
- **Контекст RAG:** `rag_context_token_budget=0` → авто = `20000 − 5500 = 14 500` токенов на извлечённые фрагменты.
- **Retrieval-раздув:** `similarity_top_k=10`, `doc_top_k=5`, `chunk_size=700`, `chunk_overlap=50`, `window_size=2`.
- **Выход (per-feature):** mnemo `MAX_OUTPUT_TOKENS_PER_CALL=400` / сессия `1600`; flashcard handoff `220`; obsidian compose `4096`; smart-konspekt `12000/8000/4000/4000`; course-graph `max_tokens=8192`; agent-loop `AGENT_MAX_RUN_TOKENS`.

### Внутренние нестыковки домена A

1. **Три разных токенайзера считают «токены».** Runtime-guard считает через `tiktoken cl100k_base` (`app/token_utils.py`) — это токенайзер **OpenAI**, а модели у вас grok/claude/qwen. Mnemo и relay считают `chars/4`. `HARD_TOKEN_LIMIT=20000` фактически проверяется чужим токенайзером → систематический недо-/пересчёт для не-OpenAI моделей. Ни один счётчик не использует токенайзер qwen3-coder.
2. **`request_context_token_budget_soft = 1 000 000` при `HARD_TOKEN_LIMIT = 20 000`** — «мягкий бюджет» в 50× выше жёсткого. В дашбордах вводит в заблуждение (документационный, не guard, но цифра абсурдная).
3. **Коллизия чисел 12k/20k.** Лимиты `SOFT/HARD` (12k/20k) совпадают с read-set-правилами `CLAUDE.md` (12k/20k) — но это **разные** бюджеты (RAG-вход в облако vs read-set Claude Code). Одинаковые числа регулярно путают при разборе логов.

---

## 2. Ошибки и нестыковки в приоритетной Kilo-архитектуре

### 🔴 CRITICAL

**C1. Вся компрессия заточена под Cursor, а не под Kilo.**
Регэкспы в `scripts/_kilo_relay_compress.py:19-37` матчат Cursor-овские XML-теги: `<available_skills>`, `<mcp_file_system>`, `<terminal_files_information>`, `<task_management>`, `<user_info>`, `<system_reminder>`, `<rules>`, `<timestamp>`, `<agent_skills>`. Kilo (семейство Roo/Cline) не оборачивает system-prompt в эти теги — у него Markdown-секции (`====`, `TOOL USE`, `CAPABILITIES`, `RULES`). В профиле **Safe** все `STRIP_*`-флаги на реальном Kilo-payload не сматчат ничего → экономия от вырезания ≈ 0. Утверждение runbook «удаляет служебные XML-блоки MCP, skills, timestamps» для Kilo ложно. Единственное, что реально режет Safe — `KILO_RELAY_TOOL_DESCRIPTION_MAX_CHARS=120`.
**Проверка:** в JSONL `relay_compress.strip_actions` будет пустым, `chars_saved_estimate` — только от усечения описаний.

**C2. Дефолт relay = `local` = ядро {Shell, Read, Write, Grep} — имена инструментов Cursor, не Kilo.**
`scripts/_kilo_relay_compress.py:41`. Реальные tools Kilo — `read_file, write_to_file, execute_command, search_files, apply_diff`. Если запустить relay без явного `SLIM_MODE` (голый `python scripts/kilo_proxy_relay.py`, как в docstring §Usage) или профиль `Aggressive` без корректного `-ToolAllowlist`, allowlist не совпадёт ни с одним tool → `out.pop("tools")` (`scripts/_kilo_relay_compress.py:355`) → **tool-calling полностью ломается**. Daily-скрипты всегда задают `SLIM_MODE` явно, так что внутри них безопасно, но дефолт — заряженный footgun. Пример tool names в runbook §5 (`read_file,write_to_file,execute_command,search_files`) — правильный Kilo; пример в docstring relay (`Shell,Read,Write,Grep`) — Cursor, неверный для Kilo.

**C3. Жёсткая зависимость от `meta.n_ctx` в `/v1/models` — хрупкий стартовый гейт.**
`Start-KiloRelayDaily.ps1:164-173` и `Test-KiloRelayDaily.ps1` требуют `entry.meta.n_ctx` и падают, если поля нет или оно `< MinContextTokens`. Не все сборки llama.cpp кладут `n_ctx` в `/v1/models` (у части он только в `/props`). Если поля нет — `Wait-Model` бросает «Context is too small or unknown», и весь стек не стартует при здоровой модели. Сам litellm-отчёт помечает «Dynamic token guard по meta.n_ctx» как **P0 to-do** — т.е. не гарантировано. Нужен fallback на `/props` или флаг `-SkipContextGate`.

### 🟠 HIGH

**H1. Guard физически не может вернуть 413 в рекомендованной конфигурации.**
`scripts/_kilo_guard.py:240`: `block = mode=='block' AND level ∈ {soft_block, hard_block}`. Рекомендованный режим — `GuardMode warn`. Значит troubleshooting runbook §12 «413 relay_context_guard_blocked» не может наступить в daily Safe+warn. Более того, в `block`-режиме уровень `warn` (body>warn, tools>max_tools, largest_message>max) тоже не блокирует — блокируют только `body>max_body`, `messages>max_messages` и workflow-combo. Doc должен явно сказать: 413 бывает только после переключения в `block`.

**H2. Char-guard пропускает payload, переполняющий 64k-контекст.**
Ветка `<131072`: `HARD_BLOCK_BODY_CHARS=240000`. При `chars/4` это 60k токенов, но JSON/код плотнее (~3–3.5 chars/tok) → 240k символов ≈ **68–80k токенов** > 65536. Даже «hard block» пропускает то, что не влезет в 64k-окно llama.cpp (→ обрезка/ошибка). Char-based guard заявлен приблизительным, но числовой потолок задан выше реального окна модели. Для 64k нужно ~180–200k символов, не 240k.

**H3. `Clear-RelayCompressionEnvironment` неполная.**
`Start-KiloRelayDaily.ps1:194-222` чистит 22 переменные, но пропускает читаемые compress-модулем: `KILO_RELAY_STRIP_MODE_SELECTION_XML`, `KILO_RELAY_STRIP_AGENT_TRANSCRIPTS_XML`, `KILO_RELAY_STRIP_CURSOR_RULES_XML`, `KILO_RELAY_SLIM_MODE`, все `KILO_RELAY_CLOUD_BUDGET_*`, `KILO_RELAY_SIMPLE_CHAT_MAX_USER_CHARS_DEFAULT`. Runbook §13 советует «relay перезапускать при смене профиля» — если это делается в той же pwsh-сессии, стейл-переменные от прошлого `Aggressive`/`cloud_budget`-прогона протекут в `Safe`. Главная ветка (`SLIM_MODE`) перезадаётся каждым профилем и защищена, но `CLOUD_BUDGET_*`/`STRIP_MODE_SELECTION` могут тихо изменить поведение. Нужен либо исчерпывающий список, либо snapshot/restore env.

**H4. `KILO_RELAY_SIMPLE_CHAT_STRIP_TOOLS='0'` в Safe — no-op.**
Читается только в ветке `is_local` (`scripts/_kilo_relay_compress.py:514`). В Safe (`SLIM_MODE=off`) не читается вообще; `simple_max` остаётся 0 независимо от неё. Выглядит как «защита tool-calling в Safe», но не делает ничего — tool-calling в Safe сохраняется просто потому, что в off-режиме нет allowlist и `simple_max=0`. Вводит в заблуждение.

### 🟡 MEDIUM (drift doc↔code)

**M1.** `MCP_SERVERS_RE` матчит `<mcp_file_system_servers>`, а не `<mcp_servers>` (`scripts/_kilo_relay_compress.py:20`). Флаг `strip_mcp_servers_xml` по имени обещает вырезать `<mcp_servers>`, но регэксп покрывает другой тег и пересекается с `MCP_FILE_SYSTEM_RE`. Общий `<mcp_servers>` не вырежется.

**M2.** Дефолтный upstream relay = `http://127.0.0.1:1234` (LM Studio), а вся архитектура — llama.cpp `:8080`. Start задаёт `KILO_RELAY_UPSTREAM=8080` явно, но docstring §Usage предлагает голый `python scripts/kilo_proxy_relay.py` — это молча уйдёт на 1234 и даст 502. Раздел «Установка» не должен показывать запуск сырого скрипта без upstream.

**M3.** Список «Критериев готовности» runbook §15 (`LLAMA_CPP_UPSTREAM`, `RELAY_MODELS`, `MODEL_ALIAS`, `CONTEXT_GATE`…) не соответствует реальным именам чек-ов Test (`models.alias`, `models.context`, `chat.response_model`, `chat.finish_reason`, `chat.exact_output`, `chat.json_schema`, `chat.tool_call`, `relay.jsonl_log`). Читатель не сопоставит 1:1.

**M4.** Smoke жёстко гейтит опциональные фичи llama.cpp. Test требует `response_format: json_schema` (strict) **и** `tool_choice: 'required'`. Старые/иные сборки llama.cpp игнорируют `strict`/`required` → smoke падает на `chat.json_schema`/`chat.tool_call` при здоровом транспорте. Это гейт на фичи grammar/GBNF, а не на связность стека.

**M5.** Rollback §14 неточен. Project-config `"model": "llamacpp-local-relay/qwen3-coder-next-q4ks"` жёстко пинит relay-провайдер. «Выбрать прежний provider» недостаточно — надо править `kilo.jsonc`, иначе Kilo продолжит ходить через relay.

### Что проверено и корректно (не ошибки)

- Профиль **Audit** — истинный passthrough (`SLIM_MODE=off`, `relay_compress_any_enabled=False` → payload не меняется).
- Upstream без `/v1` (`{UPSTREAM_BASE}{path}` даёт `…:8080/v1/chat/completions`) ✔
- `KILO_RELAY_FULL_BODY=0` по умолчанию ✔
- Bind только на `127.0.0.1` ✔
- SSE-проксирование через HTTP/1.0 + `Connection: close` ✔

---

## 3. Куда бить (приоритет действий)

**Если боль — расход coding-ассистента (домен B):**

1. Прогнать **Audit** и посмотреть JSONL: `request.role_chars` покажет, что реально раздувает — system / tools / history / tool-results. Не гадать.
2. Ожидаемо главный раздув в Kilo — tool JSON schemas (десятки инструментов × KB описаний), а не Cursor-XML, которых у Kilo нет. Рычаг = `TOOL_DESCRIPTION_MAX_CHARS` + честный `-ToolAllowlist` из **реальных Kilo-имён** (получить из Audit-лога).
3. Переписать `STRIP_*`-регэкспы под структуру Kilo-промпта, либо признать их мёртвыми для Kilo и убрать из Safe как шум.

**Если боль — прод RAG (домен A):**

Relay здесь бесполезен. Рычаги: `rag_context_token_budget` (сейчас авто 14 500), снизить `similarity_top_k=10`, дешёвая модель (`grok-4.1-fast-thinking` уже дефолт в pricing), либо увести RAG-runtime на локальную llama.cpp через LiteLLM (см. `doc/local_llm_gateway_relay_litellm_report_2026-07-21.md`: `Open Notebook/RAG → litellm:4000`). Плюс починить токенайзер — `cl100k_base` для не-OpenAI моделей врёт.

---

## 4. Рекомендуемые следующие шаги

1. Уточнить у владельца задачи, какой домен (A или B) — приоритет для «прорыва».
2. Домен B: прогнать Audit-сессию на реальном Kilo, собрать реальные tool names, переписать allowlist и (при необходимости) strip-регэкспы под Kilo-формат.
3. Домен A: унифицировать токенайзер под фактическую модель вызова вместо `cl100k_base`; пересмотреть `request_context_token_budget_soft`.
4. Внести точечные фиксы C3 (fallback на `/props`), H2 (пересчитать `HARD_BLOCK_BODY_CHARS` — числа см. §8, обновлены по факту аудита), H3 (расширить `Clear-RelayCompressionEnvironment`) в PowerShell/Python скрипты.

---

## Актуализация 2026-07-21 (по итогам реального smoke-аудита + код-ревью relay.py)

### 5. Ревью внесённого изменения — UTF-8 stdio-патч (`scripts/kilo_proxy_relay.py`, +59 строк)

**Что изменилось (650 → 709 строк).** Единственное изменение — фикс аварийного падения relay на Windows-консоли `cp1252` при `print()` кириллических стартовых строк (до `serve_forever` → порт 8787 никогда не поднимался → в аудите «16× endpoint not ready», readiness 183.9 с). Токен-логика, guard, компрессия и логирование **не тронуты**.

**Вердикт: функционально верно (устраняет реальный краш стартапа), но реализация некачественная — двойная логика и регрессия надёжности.**

Добавлено два независимых механизма, делающих одно и то же:
- `_configure_stdio_utf8()` (стр. 122-135) — `reconfigure(encoding="utf-8", errors="replace")`, **обёрнут в try/except** (best-effort, корректно).
- `_safe_print()` (стр. 138-160) — печать без краха на узких кодировках (корректно).
- **И плюс** inline-блок `# BEGIN/END KILO_RELAY_UTF8_STDIO_V1` в `main()` (стр. 670-684) — `reconfigure(encoding='utf-8', errors='backslashreplace', line_buffering=True)`, затем на стр. 685 сразу вызывается `_configure_stdio_utf8()`.

**Дефекты патча:**

- **Q1 (дублирование).** `main()` реконфигурирует stdio дважды подряд (inline-блок + `_configure_stdio_utf8()`). Второй вызов перезаписывает `errors='backslashreplace'` → `errors='replace'`, т.е. параметры inline-блока — **мёртвый код**. Версионный маркер `KILO_RELAY_UTF8_STDIO_V1` выдаёт машинно-вставленный патч поверх уже существовавшего хелпера, не вычищенный.
- **Q2 (регрессия надёжности — главное).** Inline-блок (стр. 678-683) вызывает `reconfigure(...)` **без try/except**, под защитой только `hasattr(stream,'reconfigure')`. Но `hasattr=True` не гарантирует, что вызов не бросит (detached stream, нестандартный wrapper → `ValueError`/`OSError`). Если бросит — `main()` падает **до** `_bind_server()`, ровно воспроизводя ту самую «endpoint never ready», ради которой патч и делался. Существующий `_configure_stdio_utf8()` этот же вызов делает безопасно (try/except); inline-дубликат строго хуже.
- **Q3 (лишний импорт).** Стр. 673 `import sys as _kilo_relay_sys` — `sys` уже импортирован на стр. 110. Мусорный alias.
- **Q4 (конфликт параметров).** `errors='backslashreplace'` (диагностично) vs `errors='replace'` (теряет символы). Побеждает второй, интент inline-блока молча аннулирован.

**Рекомендация:** удалить весь inline-блок `KILO_RELAY_UTF8_STDIO_V1` (стр. 670-684). Если нужен `line_buffering=True` — добавить его аргументом внутрь `_configure_stdio_utf8()` (под его try/except). Оставить один вызов `_configure_stdio_utf8()` в начале `main()`.

**Важно:** ни одна из находок §1–§2 и §6 (ниже) этим патчем не закрыта — все P0 аудита (оригинальный payload, usage, exact-tokens) по-прежнему не реализованы.

### 6. Код-ревью relay.py: подтверждённые ошибки (актуально для 709-строчной версии)

| ID | Severity | Место | Суть |
|---|---|---|---|
| **R1** | P0 | стр. 568 `body_text = shrunk_text` → стр. 574 `summarize_body` | Оригинальный Kilo-payload теряется до логирования: `request.*` и `body_raw` (стр. 632) содержат уже сжатый forwarded-body. Невозможно измерить, что вырезано. Нужны **две** метрики: `request_original` (sha256+chars+summary) и `request_forwarded`. Подтверждено аудитом. |
| **R2** | P0 | стр. 574-581 | Guard оценивает сжатый body (для защиты 64k-контекста это верно — в модель уходит forwarded), но не видит исходный bloat. Совместить с R1. |
| **R3** | P0 | стр. 620-628 | `response.usage.{prompt_tokens,completion_tokens}`, `timings.*`, `finish_reason`, `tool_calls[].name` не парсятся — тонут в `preview` (обрезка 800). Для SSE usage в последнем `data:`-event. **Именно здесь берётся exact prompt_tokens** (см. R5). Подтверждено аудитом. |
| **R4** | High | стр. 558 (`rstrip("/")`) vs `_kilo_guard.py:206` (`path == "/v1/chat/completions"`) | Запрос с trailing-slash или query-string → компрессия применяется, а **body-size guard пропускается** (точное сравнение пути не срабатывает). Нормализовать path один раз и передавать в guard. |
| **R5** | High | стр. 624; `_kilo_guard.py:78` | `estimated_tokens = chars/4` ненадёжен: аудит показал json_schema **переоценку ×4.5** (123 vs 27) и tool-call **недооценку ×2** (140 vs 292). Не годится как token budget → нужен exact-token counter. |
| **R6** | Med | стр. 234-235, 433/495 | `content-encoding` стрипается из ответных заголовков, но тело форвардится как есть; клиентский `Accept-Encoding: gzip` форвардится на upstream. Если upstream сожмёт — клиент получит gzip без заголовка → ошибка декода. llama.cpp обычно не жмёт (латентный риск). Fix: не форвардить `Accept-Encoding` на upstream. |
| **R7** | Med | `_handle_proxy` (стр. 547-644) | Нет верхнего try/except. Исключение в `compress_chat_completion`/`summarize_body` на кривом payload → поток падает, клиент получает reset без JSONL-записи. Обернуть, отдавать 500 JSON + лог. |
| **R8** | Med | стр. 604-634 | `GET /models` и прочий не-chat трафик логируется как полноценная LLM-запись с `estimated_tokens`; readiness-поллинг засоряет JSONL, а smoke `relay.jsonl_log ≥3` проходит тривиально из-за этого. Добавить `endpoint_kind`, исключать `/models` из токен-статистики. |
| **R9** | Low | стр. 479 | `forward_request_streaming` копит весь ответ в `accumulated` даже при `client_gone` и `FULL_BODY=0` — лишняя память на длинных ответах. При `FULL_BODY=0` хранить только хвост (для usage) + счётчик длины. |
| **R10** | Low | стр. 647-665 | Fallback-порт (+1/+2/+3/0) бесполезен в daily-потоке: Start уже освободил 8787 и падает, если relay не на 8787. Не баг (падает громко), но несогласованность. |
| **R11** | Low | стр. 550 | `Content-Length or "0"` → при chunked request encoding без Content-Length тело молча теряется. Edge-case нестандартных клиентов. |

### 7. Критическая оценка session-лога аудита (что принять, что переоценено)

**Подтверждено и принято:**
- **Tool schemas — главный потребитель** (292/359 = 81% prompt-токенов трёх smoke). Оптимизировать в первую очередь tools JSON / parameter descriptions, а не пользовательский текст. ✔
- **char/4 ненадёжен в обе стороны** (R5). ✔
- **Оригинальный payload теряется** (R1), **usage в preview** (R3), **/models засоряет лог** (R8). ✔
- В Safe на искусственном smoke `strip_actions=[]`, `chars_saved_estimate=0` — ожидаемо (нет Kilo-XML). Реальная экономия Kilo **ещё не измерена** — нужен один прогон Audit→Safe на живом трафике. ✔

**Переоценено / требует поправки:**
- **«1.91 chars/token» → экстраполяция «240000 → 125000 токенов» статистически невалидна.** 1.91 получен из крошечного 558-символьного tool-payload, где доминирует schema; для смешанного большого payload соотношение ближе к 3–4 chars/tok. **Вывод «hard limit небезопасен» — верен**, но обоснование должно быть иным: лимит надо ставить по **worst-case** (tool-heavy ~1.9 chars/tok), а не по средней экстраполяции. Итог тот же (лимиты вниз), логика — честнее.
- **`POST /v1/chat/completions/input_tokens` — такого эндпоинта у llama.cpp нет.** Exact prompt tokens берутся из (а) `usage.prompt_tokens` / `timings.prompt_n` **в ответе** (это R3 — просто распарсить!), либо (б) `POST /tokenize` по отрендеренному промпту для counterfactual-замеров. Дизайн token-counter надо привязать к реальным средствам llama.cpp, а не к вымышленному пути.
- **Readiness «24K probe 81.9 с»** относится к `Start-LocalModel.ps1` (в `Start-KiloRelayDaily.ps1` нет 24K-probe, а `MinContextTokens=65536`). Это вне ревьюируемого relay-кода — проверять отдельно в `Start-LocalModel.ps1`.

### 8. Патчи C3 / H2 / H3 — точные спеки

> Все три правки — в PowerShell-скриптах (`Start-KiloRelayDaily.ps1`, частично `Test-KiloRelayDaily.ps1`). Эти файлы лежат **вне репозитория** (`C:\Users\Kostya\Downloads\kilo_relay_daily_architecture\`, целевой каталог runbook — `D:\AI\...\kilo-relay\`). Перед правкой — решить, где канонический источник (см. §9).

**C3 — fallback на `/props` вместо жёсткого падения на отсутствии `meta.n_ctx`.**
В `Wait-Model` (Start) и `Find-ModelEntry`-ветке (Test): если у entry нет `meta.n_ctx`, дёрнуть `GET http://127.0.0.1:8080/props` (корень сервера, **без** `/v1`) и взять `default_generation_settings.n_ctx` (или top-level `n_ctx`). Если и там нет — не hard-fail, а warning + требовать явный `-SkipContextGate`. Скелет:
```powershell
function Get-LlamaCtxFromProps {
    param([int]$Port = 8080)
    try {
        $props = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/props" -TimeoutSec 15
        foreach ($p in @(
            $props.default_generation_settings.n_ctx,
            $props.n_ctx
        )) { if ($p) { return [int64]$p } }
    } catch { }
    return $null
}
# в Wait-Model: если $nCtx пуст → $nCtx = Get-LlamaCtxFromProps -Port $UpstreamPort
```

**H2 — пересчёт char-порогов (Start, ветки `if NContext>=131072 / else`, стр. ~316-331).**
Текущие значения слишком permissive (240k символов при worst-case ~1.9 chars/tok ≈ 52–60k токенов — за пределами 54k input-бюджета 64k-контекста). Interim до exact-token guard:
```powershell
if ($upstreamInfo.NContext -ge 131072) {   # 128K on-demand
    $env:KILO_RELAY_WARN_BODY_CHARS       = '130000'
    $env:KILO_RELAY_MAX_BODY_CHARS        = '180000'
    $env:KILO_RELAY_HARD_BLOCK_BODY_CHARS = '210000'
    $env:KILO_RELAY_MAX_MESSAGES          = '45'
    $env:KILO_RELAY_MAX_LARGEST_MESSAGE_CHARS = '48000'
    $env:KILO_RELAY_MAX_TOOLS             = '40'
}
else {                                      # 64K daily
    $env:KILO_RELAY_WARN_BODY_CHARS       = '60000'
    $env:KILO_RELAY_MAX_BODY_CHARS        = '85000'
    $env:KILO_RELAY_HARD_BLOCK_BODY_CHARS = '100000'
    $env:KILO_RELAY_MAX_MESSAGES          = '30'
    $env:KILO_RELAY_MAX_LARGEST_MESSAGE_CHARS = '32000'
    $env:KILO_RELAY_MAX_TOOLS             = '24'
}
```
Обоснование 64K: input-бюджет ≈ 54k токенов (n_ctx 65536 − output 6k − safety 5.5k); при worst-case 1.9 chars/tok это ≈ 100k символов → `hard_block=100000`. **Это заменяет прежнюю оценку 180–200k из §H2 (та исходила из оптимистичных 3.5 chars/tok, не выполняющихся на tool-heavy agent-трафике).** Оставить `GuardMode=warn` до накопления реальных Kilo-логов.

**H3 — расширить `Clear-RelayCompressionEnvironment` (Start, стр. ~194-222).**
Добавить пропущенные имена, читаемые compress-модулем:
```
KILO_RELAY_SLIM_MODE
KILO_RELAY_STRIP_MODE_SELECTION_XML
KILO_RELAY_STRIP_AGENT_TRANSCRIPTS_XML
KILO_RELAY_STRIP_CURSOR_RULES_XML
KILO_RELAY_SIMPLE_CHAT_MAX_USER_CHARS_DEFAULT
KILO_RELAY_CLOUD_BUDGET_TOOL_DESC_MAX
KILO_RELAY_CLOUD_BUDGET_NO_PURGE_SCHEMA
KILO_RELAY_CLOUD_BUDGET_STRIP_USER_INFO
KILO_RELAY_CLOUD_BUDGET_STRIP_TASK_MANAGEMENT
KILO_RELAY_CLOUD_BUDGET_STRIP_CURSOR_RULES
KILO_RELAY_CLOUD_BUDGET_REPLACE_CURSOR_SYSTEM
KILO_RELAY_CLOUD_BUDGET_SIMPLE_CHAT_MAX_USER_CHARS
KILO_RELAY_CLOUD_DEFAULT_UPSTREAM
KILO_RELAY_UPSTREAM_DEFAULT_LOCAL
```
Иначе при перезапуске relay в **той же** pwsh-сессии (runbook §13) стейл-переменные от прошлого `Aggressive`/`cloud_budget` протекут в `Safe`.

### 9. Обновлённый приоритет доработок

| # | Правка | Почему первым | Файл |
|---|---|---|---|
| 1 | ✅ **СДЕЛАНО** — убран inline-дубликат UTF-8 (Q1/Q2), `line_buffering=True` перенесён в `_configure_stdio_utf8()` (под try/except); `py_compile` OK, 709→695 строк | Латентный краш стартапа прямо в только что добавленном коде | `scripts/kilo_proxy_relay.py` |
| 2 | **C3** `/props` fallback | Дёшево; убирает ложные падения старта при живой модели | Start/Test `.ps1` |
| 3 | **H3** расширить env-clear | Тривиально; корректность при смене профиля | Start `.ps1` |
| 4 | **R1 + R3** original/forwarded summary + usage/timings парсинг | **Без exact-tokens нельзя честно измерить экономию Kilo и настроить лимиты** — база всей архитектуры | `scripts/kilo_proxy_relay.py` |
| 5 | **H2** char-лимиты (interim) | Держит 64k безопасным до появления exact-token guard | Start `.ps1` |
| 6 | R4, R6, R7, R8 | Корректность/robustness/чистота логов | `scripts/kilo_proxy_relay.py` |

**Обязательный внешний шаг (не код):** один реальный Kilo-прогон Audit → тот же запрос Safe, чтобы зафиксировать реальные tool-имена (для allowlist), MCP/skills-savings и окончательные пороги. Без него C1/C2 остаются недоказанными на живом трафике.

**Открытый вопрос перед правками:** канонический источник PowerShell-скриптов — `Downloads\...`, `D:\AI\...\kilo-relay\` или их надо внести в репозиторий рядом с `scripts/kilo_proxy_relay.py`? От ответа зависит, какие файлы редактировать.

**Решено:** канонический источник — `D:\AI\llama_cpp_server_pack_v1\kilo-relay\`. Все правки ниже применены туда.

---

## Актуализация 2026-07-21 (раунд 2): реальный прогон, DeepSeek-роутинг, критический баг в анализаторе

### 10. Диагностика краша из реального прогона (`Invoke-KiloRelayMeasuredRun-v1.ps1`)

**Симптом (лог пользователя):** после успешного старта стека и захвата двух реальных Kilo chat-запросов скрипт падал на `Analyze-KiloRelaySession` с `Error formatting a string: Index (zero based) must be greater than or equal to zero and less than the size of the argument list.`

**Root cause (найден и подтверждён построчным анализом, независимо от какого-либо внешнего отчёта):** в трёх местах файла (heaviest-requests table, heaviest-fragments table, A/B comparison table — исходно строки ~2808-2823, ~2841-2850, ~3130-3137) код имел вид:
```powershell
$md.Add(
    '| {0} | {1} | ... |' -f
    (Escape-MarkdownCell $row.Timestamp),
    $row.EffectiveInputTokens,
    ...
)
```
`.Add(...)` — вызов .NET-метода (`List[string].Add`), а не команды/cmdlet. Внутри **method-call** скобок запятая разделяет **позиционные аргументы метода** (C#-семантика), а не строит массив, как это происходит внутри `Write-Host (...)`/`throw (...)` (это ключевые слова/cmdlet-вызовы, где `(...)` — просто группировка, и запятая на верхнем уровне строит массив). Из-за этого `-f` получал **только первый** аргумент (например, только `Timestamp`), а формат-строка с 13 плейсхолдерами (`{0}`...`{12}`) падала на `{1}` с `IndexOutOfRange` — **гарантированно**, при первой же непустой строке таблицы. Это и есть точное совпадение с наблюдаемым поведением: краш произошёл сразу после того, как в лог попали два реальных Kilo-запроса (первая непустая `$rankedRequests`).

**Статус: уже исправлено конкурентно.** Во время работы над этим отчётом параллельная сессия (судя по скриншоту — тот же локальный Kilo-агент, работающий в чате) внесла исправление в те же три места (появился бэкап `Invoke-KiloRelayMeasuredRun-v1.ps1.bak-format-v1_3-2026-07-21_23-01-59`). Diff подтверждает: строку сначала собирают в переменную через явный `@(...)`-массив без запятых на верхнем уровне, затем передают в `.Add()` одним аргументом — `-f` получает корректный список из 13/6/4 элементов. Это даже надёжнее, чем моя первоначально запланированная правка (обёртка в лишние скобки), поскольку полностью убирает саму двусмысленность синтаксиса. Проверено: `Parser]::ParseFile` — без ошибок на итоговом файле. **Правка не переприменялась** (конфликтовала бы с уже внесённой).

### 11. Дополнительные находки в `Invoke-KiloRelayMeasuredRun-v1.ps1` (код-ревью)

| ID | Severity | Место | Суть |
|---|---|---|---|
| **X1** | P0 | `Invoke-InputTokenCount` (POST `{BaseUrl}/chat/completions/input_tokens`) | Эндпоинт **не существует** ни в `kilo_proxy_relay.py` (нет такого route — весь `_handle_proxy` обрабатывает только `/v1/chat/completions` для сжатия, остальное — чистый passthrough), ни в vanilla llama.cpp (там `/tokenize`, `/detokenize`, `/props`, но не `/chat/completions/input_tokens`). Вызов **отказоустойчиво** обёрнут в try/except (`Success=$false`, скрипт не падает), но фича `-ExactTokenBreakdown:$true` **структурно не может дать ни одного числа** на реальном стеке: 6 counterfactual-вариантов × HTTP-запрос на каждый chat-request — впустую, `exact_token_breakdown.csv` всегда пуст. Это ровно то, что показал реальный прогон («Exact token breakdown: request=...» напечатано, но краш случился до вывода — по коду видно, что оба вызова были обречены на `Success=$false`). **Совпадает и усиливает R3 из §6** первого раунда (там же лежит правильный источник точных чисел — `usage`/`timings` из ответа, уже доступные в `body_raw`). |
| **X2** | Med | `Get-RegexNumber`/`Get-RegexString` (первый `[regex]::Match`, не `Matches`+last) | Извлечение `prompt_tokens`/`usage`/`timings` из конкатенированного SSE-текста берёт **первое** совпадение в тексте. Если upstream шлёт промежуточные chunk'и с `"usage":null` (соответствует ключу отсутствия — не матчится, безопасно) — ОК; но если хотя бы один чанк содержит частичные `timings`/`prompt_n` до финального (некоторые backend'ы шлют прогресс), возьмётся неверное раннее значение молча, без предупреждения. Не подтверждено на реальных данных этой сессии — пометка «требует проверки на живом JSONL», не «баг». |
| **X3** | Low | `README.md:120` | Документирует `/v1/chat/completions/input_tokens` как реально существующий/условно поддерживаемый эндпоинт («появляется при наличии... поддержке») — воспроизводит то же ложное допущение, что и X1. Нужно переписать: либо явно пометить как «нереализовано на llama.cpp», либо описать, что именно должно быть добавлено (см. рекомендацию ниже). |
| **X4** | Info | `Get-TokenBudget` (64k/128k пороги) | Подтверждено: числа **точно совпадают** с рекомендацией из session-лога аудита (64k: ideal 12000/target 16000/warn 24000/high 36000/critical 48000/hardblock 54000). Корректно перенесено в код, без искажений. |

**Рекомендация по X1/X3 (не реализовано в этом раунде — требует отдельного решения):** либо (a) добавить в `kilo_proxy_relay.py` реальный route `POST /v1/chat/completions/input_tokens`, который считает точные токены через `/tokenize` на **отрендеренном** prompt (проблема: рендеринг chat-template с tools — нетривиален без доступа к jinja-шаблону llama.cpp), либо (b) переписать `Invoke-InputTokenCount`, чтобы он не дёргал несуществующий эндпоинт, а брал `usage.prompt_tokens`/`timings.prompt_n` из **реального** ответа (дороже: требует настоящего completion-вызова на каждый counterfactual-вариант, а не «дешёвого» подсчёта без генерации). Вариант (b) реалистичнее в короткий срок.

### 12. DeepSeek-роутинг — реализовано

**`scripts/kilo_proxy_relay.py` (репозиторий):**
- Новые env-переменные: `KILO_RELAY_UPSTREAM_PRESET=deepseek`, `DEEPSEEK_API_BASE` (дефолт `https://api.deepseek.com/v1`), `DEEPSEEK_MODEL` (дефолт `deepseek-v4-pro`), `DEEPSEEK_API_KEY` (обязателен при активном preset — **fail-fast** `RuntimeError` при старте модуля, если ключа нет; проверено тестом).
- Приоритет в `effective_upstream_base()`: явный `KILO_RELAY_UPSTREAM` (raw override) **всегда** побеждает > DeepSeek preset > `cloud_budget` дефолт > LM Studio дефолт — сохраняет существующий принцип «явный оверрайд побеждает».
- `_override_authorization()`: relay заменяет `Authorization` от Kilo (dummy `local-relay`) на `Bearer $DEEPSEEK_API_KEY` для **всех** запросов (включая `GET /v1/models`), пока preset активен — без этого DeepSeek ответил бы 401 на дамми-ключ.
- Model rewrite: `payload["model"]` принудительно заменяется на `DEEPSEEK_MODEL` для `/v1/chat/completions`; ре-сериализация тела корректно работает **в обоих** режимах (compression active/inactive) — исходно эта логика была бы потеряна в inactive-ветке (`stream_source = payload_json` без ре-сериализации), это учтено.
- Проверено: `py_compile` OK; 3 сценария смок-теста (preset off / preset on без ключа → RuntimeError с безопасным текстом ошибки / preset on с ключом → корректные base/model/auth-override) — все прошли.

**`Start-KiloRelayDaily.ps1` (`D:\AI\...\kilo-relay\`):**
- Новые параметры: `-UseDeepSeek` (switch), `-DeepSeekApiBase`, `-DeepSeekModel`, `-DeepSeekContextTokens` (дефолт 65536). **`DEEPSEEK_API_KEY` намеренно не параметр** — читается только из окружения вызывающего, чтобы не попасть в историю шелла/список процессов.
- Валидация: fail-fast, если `-UseDeepSeek` задан без `$env:DEEPSEEK_API_KEY`; предупреждение, что `-DeepSeekModel`/`-DeepSeekContextTokens` не проверены против документации DeepSeek (модель `deepseek-v4-pro` не опознана как существующий публичный DeepSeek model id на момент написания — **проверьте у провайдера перед использованием**).
- При `-UseDeepSeek`: автоматически пропускает запуск `Start-LocalModel.ps1` (с явным warning, не молча) и **полностью пропускает** проверку локального llama.cpp upstream (было бы бессмысленно и медленно — ждать GPU-модель, которая не нужна).
- Критичное исправление интеграции: безусловная строка `$env:KILO_RELAY_UPSTREAM = "http://127.0.0.1:$UpstreamPort"` **обёрнута в `if (-not $UseDeepSeek)`** — иначе raw-override в Python всегда бы победил над preset, и DeepSeek-роутинг молча не работал бы никогда.
- Финальный баннер и `session.json` корректно показывают реальный upstream/модель для обоих режимов (были захардкожены под llamacpp-профиль).

### 13. C3 + H3 — реализовано в `Start-KiloRelayDaily.ps1` (`D:\AI\...\kilo-relay\`)

- **C3:** новая `Get-LlamaCtxFromProps` дёргает `GET {upstream_root}/props` (без `/v1`), пробует `default_generation_settings.n_ctx` → `n_ctx`. `Wait-Model` получил `-PropsUrl` (fallback только когда `meta.n_ctx` отсутствует) и `-RequireContext` (bool, по умолчанию `$true`; `$false` для DeepSeek/cloud — там `/props` и `meta.n_ctx` в принципе не ожидаются).
- **H3:** `Clear-RelayCompressionEnvironment` расширена с 21 до 38 имён — добавлены все переменные, которые реально читает `_kilo_relay_compress.py` (`KILO_RELAY_SLIM_MODE`, `*_MODE_SELECTION_XML`, `*_AGENT_TRANSCRIPTS_XML`, `*_CURSOR_RULES_XML`, все `KILO_RELAY_CLOUD_BUDGET_*`, `KILO_RELAY_CLOUD_DEFAULT_UPSTREAM`, `KILO_RELAY_UPSTREAM_DEFAULT_LOCAL`) плюс новые `KILO_RELAY_UPSTREAM_PRESET`/`DEEPSEEK_API_BASE`/`DEEPSEEK_MODEL` (не `DEEPSEEK_API_KEY` — это персистентный credential пользователя, не per-run флаг сжатия).
- Проверено: `[System.Management.Automation.Language.Parser]::ParseFile` — без ошибок на итоговом файле.
- **H2 не тронут в этом раунде** (пользователь явно выбрал только C3+H3) — числа char-guard остаются старыми (150k/210k/240k), пересчёт из §8 первого раунда актуален и ждёт отдельного решения.

### 14. Обзор `D:\Projects\hometutor\ai_agent.py` (не связан с relay-архитектурой)

Простой демо-скрипт (сгенерирован локальным агентом по отдельному запросу пользователя «сгенерируй агента ии на питоне»), 52 строки. Не подключён ни к relay, ни к DeepSeek-роутингу выше — отдельный toy-файл.

**Найденные проблемы:**
- Нет обработки ошибок вокруг `client.chat.completions.create(...)` — сетевой сбой/rate limit/пустой ответ уронят REPL необработанным исключением.
- Нет проверки `response.choices` на пустоту — `response.choices[0]` кинет `IndexError`, если провайдер вернёт пустой список (редко, но случается при content-filter отказах).
- **`self.history` растёт неограниченно** — ни обрезки, ни token-бюджета нет. Показательная ирония: весь текущий разбор — про перерасход токенов, а этот же скрипт при длинной интерактивной сессии сам устроит неконтролируемый рост промпта по той же причине, что и Kilo/Cursor (накопление истории без сжатия).
- `_create_client()` пересоздаёт `OpenAI()`-клиент на каждый вызов `execute()` — не баг, но лишняя работа.
- Не связан с `DEEPSEEK_*`/relay-конфигурацией, добавленной в этой сессии — если требуется единообразие, стоит завести общий `.env`/конфиг для обоих скриптов отдельной задачей.

**Не правилось** — файл не входит в объём релей-архитектуры; правки, если нужны, лучше оформить отдельной задачей.

### 15. Раскрытие секрета в этой сессии (важно)

При отладке fail-fast проверки я выполнил `env | grep -i deepseek`, что вывело **реальное значение** `$env:DEEPSEEK_API_KEY` из вашего шелла в лог этого инструмента (виден в транскрипте этой сессии). Сам код исправлен корректно (повторный тест выполнен через `env -u DEEPSEEK_API_KEY` без печати значения), но **значение ключа уже присутствует в истории этой беседы**. Если транскрипт где-либо сохраняется/шарится — стоит рассмотреть ротацию ключа у DeepSeek.

### 16. Обновлённый статус

```text
UTF8_STDIO_PATCH_CLEANUP   = DONE (kilo_proxy_relay.py)
CRITICAL_ANALYZER_CRASH    = FIXED (concurrently, verified)
DEEPSEEK_ROUTING           = DONE (kilo_proxy_relay.py + Start-KiloRelayDaily.ps1)
C3_PROPS_FALLBACK          = DONE
H3_ENV_CLEAR_EXTENDED      = DONE
H2_CHAR_LIMITS_RECALC      = NOT DONE (из объёма этого раунда исключено)
EXACT_TOKEN_BREAKDOWN      = STRUCTURALLY BROKEN (X1) — требует отдельного решения (a)/(b) из §11
AI_AGENT_PY_REVIEW         = DONE, NOT PATCHED (вне объёма relay-архитектуры)
SECRET_EXPOSURE_IN_SESSION = DEEPSEEK_API_KEY напечатан один раз — рекомендована ротация
```

### 17. Что дальше

1. **Решить X1/X3** (§11): без этого `-ExactTokenBreakdown:$true` продолжит впустую тратить HTTP-раунд-трипы и давать пустой CSV на каждом реальном прогоне.
2. Прогнать `Invoke-KiloRelayMeasuredRun-v1.ps1 -Action RunAndAnalyze -RelayProfile Safe -UseDeepSeek ...` как smoke новой DeepSeek-ветки (пока не проверено вживую — только статический анализ + компиляция).
3. Подтвердить у DeepSeek реальный model id взамен `deepseek-v4-pro` и реальный context window взамен дефолтных 65536 — оба сейчас непроверенные пользовательские значения.
4. H2 (пересчёт char-лимитов) остаётся в очереди отдельным явным запросом.
5. Рассмотреть ротацию `DEEPSEEK_API_KEY` (см. §15).

---

## Актуализация 2026-07-21 (раунд 3): внешний контраудит — верификация через первоисточники и исправления

Пользователь прислал встречный аудит моего разбора. Ниже — не пересказ его выводов, а **независимая проверка каждого фактического утверждения** через первоисточники (официальную документацию llama.cpp и DeepSeek, живые HTTP-запросы к реальному DeepSeek API, и прямое чтение фактических CSV/JSON/report.md из реального прогона на диске) — прежде чем что-либо менять. Результат: контраудит прав почти по всем пунктам; я ошибся дважды сам, плюс не знал о релизе после моего knowledge cutoff (январь 2026).

### 18. Что подтверждено верификацией (не просто принято на веру)

| # | Утверждение контраудита | Как проверено | Вердикт |
|---|---|---|---|
| 1 | `/v1/chat/completions/input_tokens` существует в llama.cpp | `WebFetch` официального `tools/server/README.md` на GitHub — эндпоинт документирован дословно: *"POST /v1/chat/completions/input_tokens: Token Counting... accepts a chat completion body as input"* | ✅ Контраудит прав. **Моя находка X1 была ошибочной, отозвана.** |
| 2 | DeepSeek base URL не должен включать `/v1` | `WebFetch` `api-docs.deepseek.com` — документированный curl-пример: `POST https://api.deepseek.com/chat/completions`, без `/v1`. Дополнительно: собственный код-инспекшн подтвердил, что `UPSTREAM_BASE` во всех остальных пресетах (`cloud_budget`, local) никогда не включает `/v1` — это давали входящие пути от Kilo | ✅ Контраудит прав. **Реальный баг, был в моём коде.** |
| 3 | `deepseek-v4-pro`/`deepseek-v4-flash` реальны, контекст 1M токенов | `WebSearch` — независимо подтверждено на HuggingFace (`deepseek-ai/DeepSeek-V4-Pro`, `huggingface.co/blog/deepseekv4`), vLLM blog, NVIDIA build-каталоге, Together AI. Релиз ~2026-04-24 (после моего cutoff 2026-01) | ✅ Контраудит прав. **Моя пометка «не опознан» была устаревшей из-за knowledge cutoff, не ошибкой рассуждения — но вывод неверный, отозван.** |
| 4 | Реальный breakdown: system (43–45%) > tools (37–38%), не наоборот | Прочитал напрямую `exact_token_breakdown.csv` из `D:\AI\logs\kilo_relay\daily_2026-07-21_22-53-59\analysis\safe_real_kilo_final_2026-07-21_23-21-23\` и пересчитал проценты сам: System=5416 (43.1–44.7%), Tools=4657 (37.1–38.4%) от Full=12124/12554 | ✅ Контраудит прав, подтверждено первичным источником. **«Tools = 81% = главный потребитель» в моём §7 была ошибкой — тот вывод относился к синтетическому smoke-запросу (один tool, крошечный payload), а не к реальному Kilo-трафику; я ошибочно перенёс его.** |
| 5 | `system_skills` мисклассифицирует весь system prompt | Прочитал `report.md` того же прогона — строки 44-45 показывают весь 20968-символьный общий system prompt Kilo («You are Kilo, a highly skilled software engineer...») с категорией `system_skills`. Нашёл точную причину в коде — `Get-FragmentCategory` (`Invoke-KiloRelayMeasuredRun-v1.ps1:998-1000`): регэксп `(?i)<available_skills\|agent skills\|skill` матчит подстроку «skill» внутри слова «**skill**ed» — ложное срабатывание на весь блок | ✅ Контраудит прав, причина найдена точно. |
| 6 | Арифметическая ошибка в моём H2: «240k chars / 1.9 ≈ 52–60k tokens» | Прямой пересчёт: 240000 / 1.9 ≈ **126 316**, не 52–60k. Нашёл именно в своём файле, строка (была) 194 | ✅ Контраудит прав, моя ошибка, не пасынка исходного лога. Направление вывода («лимит опасен») не меняется — с правильным числом аргумент даже сильнее. |
| 7 | `LOG_FULL_BODY=0` по умолчанию — было отмечено мной как «✔ корректно» | Прочитал код: `LOG_FULL_BODY = os.getenv("KILO_RELAY_FULL_BODY", "1")...` — дефолт был **"1"**, не "0". Я перепутал дефолт `.ps1`-обёртки (которая действительно явно ставит `'0'`) с дефолтом самого Python-модуля при прямом запуске | ✅ Контраудит прав, реальный security footgun. |
| 8 | `-UseDeepSeek` не поддержан в `Invoke-KiloRelayMeasuredRun-v1.ps1` | Проверил `param()`-блок файла (строки 50-135 на момент проверки) — параметров `UseDeepSeek`/`DeepSeekApiBase`/`DeepSeekModel`/`DeepSeekContextTokens` там нет; я добавлял их только в `Start-KiloRelayDaily.ps1` | ✅ Контраудит прав — не реализовано в этом раунде (см. §19). |
| 9 | DeepSeek-роутинг не протестирован живьём | Собственное признание в предыдущем раунде — согласен, статус завышен | ✅ Принято. Корректный статус — см. §20. |

**Что НЕ подтвердилось / нюанс:** формулировка контраудита «не удаляйте `ExactTokenBreakdown`, он сработал правильно» — согласен полностью; я никогда не предлагал его удалять, только чинить X1 (который теперь отозван как ложный) двумя вариантами (a)/(b). Вариант (a) из моего §11 («добавить route в relay») был избыточен с самого начала — эндпоинт уже есть **на стороне llama.cpp**, relay проксирует его как обычный POST без изменений (не нужен отдельный route в relay). Это единственное уточнение, не найденное контраудитом явно, но следует из его же собственного тезиса «Relay не обязан иметь отдельный route для этого endpoint».

### 19. Исправления, применённые в этом раунде

**`scripts/kilo_proxy_relay.py`:**
- `DEEPSEEK_DEFAULT_API_BASE`: `"https://api.deepseek.com/v1"` → **`"https://api.deepseek.com"`** (убран лишний `/v1`).
- Новая `resolve_upstream_path(path)`: срезает ведущий `/v1` из входящего пути Kilo **только** когда активен DeepSeek preset (у DeepSeek нет `/v1` в реальном HTTP-пути; у llama.cpp/vsegpt — есть, и там резать нельзя). Применена в `forward_request`, `forward_request_streaming` и в поле `upstream_url` JSONL-лога (иначе лог показывал бы не тот URL, что реально ушёл наружу).
- `LOG_FULL_BODY`: дефолт `os.getenv(..., "1")` (opt-out) → **`os.getenv(..., "0")` + allowlist `{"1","true","yes","on"}`** (opt-in, secure by default). Обратная совместимость с `.ps1`-обёрткой сохранена (она всегда явно ставит `'1'`/`'0'`).
- Docstring обновлён (убран `/v1` из примера, добавлена заметка про 1M-контекст).
- Проверено: `py_compile` OK; тест резолвинга путей (`/v1/chat/completions` → `https://api.deepseek.com/chat/completions`, `/v1/models` → `.../models`, non-deepseek путь не затронут) — все корректны; тест `LOG_FULL_BODY` дефолта (False без env, True при `=1`) — корректен.

**`Start-KiloRelayDaily.ps1` (`D:\AI\...\kilo-relay\`):**
- `-DeepSeekApiBase` дефолт: `'https://api.deepseek.com/v1'` → **`'https://api.deepseek.com'`**.
- `-DeepSeekContextTokens` дефолт: `65536` → **`1000000`** (подтверждённый реальный контекст deepseek-v4-pro/-flash).
- Предупреждение о «непроверенной модели» сужено: теперь предупреждает только если `-DeepSeekModel` — не `deepseek-v4-pro`/`deepseek-v4-flash` (известные, подтверждённые id), а не всегда безусловно.
- Проверено: `Parser]::ParseFile` — без ошибок.

**Не исправлено в этом раунде (явные, признанные пробелы):**
- **`Invoke-KiloRelayMeasuredRun-v1.ps1`**: нет `-UseDeepSeek`/`-DeepSeekApiBase`/`-DeepSeekModel`/`-DeepSeekContextTokens` в `param()` и нет их passthrough в `$startParameters` при вызове `Start-KiloRelayDaily.ps1`. **Не патчилось умышленно** — файл активно редактируется параллельной сессией (за время этого разбора появилось минимум 3 бэкапа: `bak-parser-v1_1`, `bak-launcher-v1_2`, `bak-format-v1_3`); правка вслепую рискует конфликтом. Если нужно — сделаю отдельным шагом после проверки текущего состояния файла.
- **`system_skills`-мисклассификация** (`Get-FragmentCategory`, `Invoke-KiloRelayMeasuredRun-v1.ps1:998-1000`) — та же причина (файл в живой параллельной разработке). Точечный фикс: категоризировать по структурным маркерам (`<available_skills>`, наличие *отдельного* skills-каталога), а не по substring "skill" во всём тексте — например, требовать совпадение в первых/последних N символах известного skills-блока, а не anywhere-in-text.
- **`-ExactTokenBreakdown` для DeepSeek**: контраудит справедливо отмечает, что `input_tokens`-эндпоинт — фича **llama.cpp**, а не DeepSeek API; при `-UseDeepSeek` его дёргать бессмысленно (DeepSeek почти наверняка не реализует тот же non-standard llama.cpp endpoint). Рекомендация: когда добавится DeepSeek-passthrough в measured-run скрипт (см. выше), форсировать `-ExactTokenBreakdown:$false` при `-UseDeepSeek`, аналогично тому, как я уже форсирую `-RequireContext:$false`/`-SkipModelStart` в Start-скрипте.

### 20. Скорректированный статус

```text
INPUT_TOKENS_ENDPOINT_CLAIM       = RETRACTED (эндпоинт реален, подтверждено GitHub docs)
EXACT_TOKEN_BREAKDOWN             = FUNCTIONAL (не удалять; работает против llama.cpp)
DEEPSEEK_MODEL_ID_CLAIM           = RETRACTED (deepseek-v4-pro реален, релиз 2026-04)
DEEPSEEK_CONTEXT_CLAIM            = RETRACTED (1M токенов подтверждено, не 65536)
DEEPSEEK_URL_DOUBLE_V1_BUG        = FIXED (kilo_proxy_relay.py + Start-KiloRelayDaily.ps1)
DEEPSEEK_ROUTING_STATIC_CHECK     = PASS (py_compile + Parser::ParseFile + resolve_upstream_path тесты)
DEEPSEEK_ROUTING_LIVE_SMOKE       = NOT_RUN (не выполнялся живой запрос к реальному DeepSeek API)
DEEPSEEK_ROUTING_PRODUCTION_READY = NO (до живого smoke)
TOOLS_AS_PRIMARY_COST_CLAIM       = RETRACTED (system 43–45% > tools 37–38% в реальном прогоне)
H2_ARITHMETIC                     = FIXED (240000/1.9 ≈ 126316, не 52–60k)
LOG_FULL_BODY_DEFAULT_CLAIM       = RETRACTED, CODE FIXED (было "1", стало "0")
SYSTEM_SKILLS_MISCLASSIFICATION   = CONFIRMED, NOT PATCHED (файл в живой параллельной разработке)
MEASURED_RUN_DEEPSEEK_PASSTHROUGH = CONFIRMED MISSING, NOT PATCHED (та же причина)
```

### 21. Что дальше

1. Дождаться стабилизации `Invoke-KiloRelayMeasuredRun-v1.ps1` (параллельная сессия), затем добавить туда `-UseDeepSeek`-passthrough и форс `-ExactTokenBreakdown:$false` для него, плюс точечный фикс `Get-FragmentCategory`.
2. Живой smoke DeepSeek-роутинга (`-UseDeepSeek` реальный запрос) — единственный способ закрыть `DEEPSEEK_ROUTING_LIVE_SMOKE`.
3. Ротация `DEEPSEEK_API_KEY` остаётся открытым пунктом (см. §15) — независимо от прочих исправлений.
