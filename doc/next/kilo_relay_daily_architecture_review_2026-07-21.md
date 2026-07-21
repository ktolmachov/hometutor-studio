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
4. Внести точечные фиксы C3 (fallback на `/props`), H2 (пересчитать `HARD_BLOCK_BODY_CHARS` для 64k под ~3.5 chars/token), H3 (расширить `Clear-RelayCompressionEnvironment`) в PowerShell/Python скрипты.
