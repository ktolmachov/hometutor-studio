# Обзор архитектуры Kilo → kilo_proxy_relay → llama.cpp

**Создан:** 2026-07-21
**Последняя актуализация:** 2026-07-22 (раунд 5, §22–27; нумерация разделов раунда 4 исправлена с §25–29 на §22–26 — исходный скачок с §21 был артефактом редактирования)
**Статус:** Partially implemented / not production-ready — см. «Текущий статус (актуально)» ниже

---

## Текущий статус (актуально на 2026-07-22) — читать в первую очередь

Этот документ — журнал 4 раундов правок вместе с историей ошибок и их исправлений (не только финальная спецификация). Ниже — сводка того, что верно **сейчас**; секции ниже по документу могут содержать устаревшие/отозванные утверждения, помеченные явно, но не всегда вычищенные из текста.

**Код (`scripts/kilo_proxy_relay.py`, `Start-KiloRelayDaily.ps1` в `D:\AI\...\kilo-relay\`):**
- DeepSeek preset: base URL без `/v1` (`https://api.deepseek.com`), fail-fast без ключа, `Authorization`/`model` rewrite — **только когда DeepSeek реально активен** (raw `KILO_RELAY_UPSTREAM` побеждает preset полностью, включая auth/model — фикс критического бага раунда 4).
- `DEEPSEEK_THINKING` (`enabled`/`disabled`) и `DEEPSEEK_REASONING_EFFORT` (только `high`/`max` — не `low`/`medium`, DeepSeek не даёт настоящей гранулярности ниже) — опциональный контроль, по умолчанию relay не трогает эти поля.
- `LOG_FULL_BODY` — дефолт **выключено** (`os.getenv("KILO_RELAY_FULL_BODY", "0")`), протестировано `test_log_full_body_defaults_off_when_unset`.
- `normalize_chat_completions_path()` — устойчивая детекция chat-эндпоинта (trailing slash / query string / bare `/chat/completions`), используется и для compression, и для guard.
- Тесты: **25** (было 12 до этой сессии), все проходят (`pytest tests/test_kilo_proxy_relay.py -q`).
- ⚠️ **Не закрыто и не в коде:** DeepSeek требует передавать `reasoning_content` обратно на каждом следующем шаге после tool call, иначе `HTTP 400`. Relay это не проверяет и не чинит — это поведение клиента (Kilo), вне контроля relay. **Multi-turn agentic tool-loop через DeepSeek preset не тестировался end-to-end и может сломаться на первом же tool round-trip.**
- ⚠️ `Invoke-KiloRelayMeasuredRun-v1.ps1` и `Test-KiloRelayDaily.ps1` **не обновлены** под DeepSeek (нет `-UseDeepSeek` passthrough; `Test-` не умеет cloud-провайдеров без `meta.n_ctx`) — файлы редактируются параллельной сессией, правка отложена.
- ⚠️ Живой smoke-тест (реальный chat completion Kilo→relay→DeepSeek) **не выполнялся**. Мои «живые HTTP-запросы» к DeepSeek в раунде 3 были probe-запросами к auth-шлюзу (проверка, что `/v1/chat/completions` не 404, без реального содержательного запроса) — это НЕ то же самое, что end-to-end smoke.
- H2 (char-guard пороги) при `GuardMode=warn` (рекомендуемый режим) **не блокирует** ничего — это диагностика, а не защита. Пороги предлагаются как основа для будущего `GuardMode=block` после калибровки на реальных логах, не как готовая защита 64k уже сейчас.

**Документация:** известные внутренние противоречия предыдущих раундов (арифметика в §8, разнобой в счёте тестов между секциями раундов) размечены пометками ниже по мере обнаружения — актуальные числа см. в этой сводке.

**Материал не по этой сессии:** пункты про `execution_contract.md` / `local_model_execution_packet_plan.md` / HTML-презентацию №27 / D2-адаптеры относятся к **другой** задаче (`local_model_trust_contour_refresh`, отдельный execution_contract, статус `DONE`, docs-only), которую вела другая сессия — не разбираются в этом файле.

---

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
Текущие значения слишком permissive (240k символов при worst-case ~1.9 chars/tok ≈ **126k токенов** [^h2-arith-fix] — далеко за пределами 54k input-бюджета 64k-контекста). Interim до exact-token guard:

[^h2-arith-fix]: Исходная версия этой строки содержала арифметическую ошибку («≈ 52–60k»); исправлено в §18/25, число здесь актуализировано на месте, а не оставлено как есть с пометкой — см. пункт 6 второго контраудита (2026-07-22).
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
| 5 | **H2** char-лимиты (interim) | При рекомендуемом `GuardMode=warn` **не блокирует** (только пишет warning в JSONL — HTTP 413 в этом режиме невозможен, см. `_kilo_guard.py`). Даёт диагностические данные для калибровки будущего `GuardMode=block`, не защиту здесь и сейчас | Start `.ps1` |
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

Пользователь прислал встречный аудит моего разбора. Ниже — не пересказ его выводов, а **независимая проверка каждого фактического утверждения** через первоисточники (официальную документацию llama.cpp и DeepSeek; `curl`-probes к реальному DeepSeek API — только проверка HTTP-статуса разных путей без auth, **не** содержательные chat-completion запросы, см. уточнение ниже; и прямое чтение фактических CSV/JSON/report.md из реального прогона на диске) — прежде чем что-либо менять. Результат: контраудит прав почти по всем пунктам; я ошибся дважды сам, плюс не знал о релизе после моего knowledge cutoff (январь 2026).

**Уточнение формулировки (по второму контраудиту):** «живые HTTP-запросы» выше — это `curl`-пробы к auth-шлюзу DeepSeek (`POST` без ключа на разные пути, сравнение кодов ответа), которые все вернули `401 "Authentication Fails (governor)"` — это подтвердило, что DeepSeek проверяет авторизацию **до** маршрутизации (поэтому пробы не могли отличить валидный путь от невалидного), но это **не** реальный content-запрос и **не** end-to-end smoke через relay. Отсюда нет противоречия со статусом `DEEPSEEK_ROUTING_LIVE_SMOKE=NOT_RUN` ниже — это разные вещи, и формулировка должна была разделять их явно с самого начала.

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

---

## Актуализация 2026-07-22 (раунд 4): второй внешний контраудит — критический баг precedence подтверждён и исправлен

Второй встречный аудит (после раунда 3) указал на новый критический баг, введённый именно моим фиксом из раунда 3, плюс несколько документационных и дизайн-пробелов. Как и в раунде 3 — не принимаю на веру, проверяю каждое утверждение первичным источником (живой тест кода, официальная документация DeepSeek/llama.cpp) прежде чем править.

### 22. Что подтверждено верификацией

| # | Утверждение | Как проверено | Вердикт |
|---|---|---|---|
| 1 | **Критично.** `DEEPSEEK_CFG` вычислялся независимо от `UPSTREAM_BASE` — raw override не отключал auth/model rewrite | Живой тест: `KILO_RELAY_UPSTREAM=http://127.0.0.1:8080` + `KILO_RELAY_UPSTREAM_PRESET=deepseek` → `UPSTREAM_BASE` корректно = raw, но `DEEPSEEK_CFG is not None` = **True**; итоговый URL с резкой `/v1` был бы `http://127.0.0.1:8080/chat/completions` (сломан), плюс реальный DeepSeek-ключ ушёл бы в `Authorization` для запроса на raw upstream | ✅ Контраудит прав. **Реальный, воспроизводимый баг**, введённый моим же раунд-3 фиксом. Исправлено. |
| 2 | Категоричность «у DeepSeek нет `/v1`» неточна — WorkBuddy-интеграция DeepSeek использует `/v1/chat/completions` | `WebFetch` `api-docs.deepseek.com/quick_start/agent_integrations/workbuddy/` — подтверждена именно эта строка URL в примерах конфигурации | ✅ Контраудит прав. Формулировка смягчена; **резка `/v1` вообще убрана как избыточная** (оба варианта пути реально работают на DeepSeek, значит base без `/v1` + входящий `/v1/chat/completions` от Kilo дают рабочий URL без какой-либо трансформации). |
| 3 | Детекция chat-эндпоинта (`self.path.rstrip("/") == "/v1/chat/completions"`) не распознаёт query string / bare `/chat/completions` | Прямая проверка кода — точное совпадение, действительно не матчит `?trace=1` и `/chat/completions` без `/v1`. Утверждение «эксплуатационная документация советует Base URL без `/v1`» — **не подтвердилось** (`grep` по всем `.ps1`/runbook показывает только `http://127.0.0.1:8787/v1`, нигде — голый порт) | Частично: сама уязвимость реальна (это же R4 из раунда 1), но конкретная причина («документация советует без /v1») не подтверждена. Исправлено защитно в любом случае — `normalize_chat_completions_path()`. |
| 4 | Документация противоречива: `doc/kilo_proxy_relay.md` содержал старый DeepSeek base с `/v1` и отозванный X1 как факт | Прочитан файл напрямую (`git status` показал: существовал в репозитории до этой сессии, `M` — изменён параллельной сессией во время работы; я его не создавал и не трогал до этого раунда) | ✅ Контраудит прав — файл реально был устаревшим/противоречивым. Исправлено. |
| 5 | Docstring `kilo_proxy_relay.py` всё ещё содержал `KILO_RELAY_FULL_BODY=1` пример и «raw request body» без оговорки про дефолт | Прямой `grep` — подтверждено дословно | ✅ Контраудит прав. Исправлено. |
| 6 | Тесты не покрывали связку routing/auth/model — поэтому баг #1 остался незамеченным в раунде 3 | Факт: у меня не было regression-теста именно на комбинацию raw+stale-preset до этого раунда | ✅ Принято. Тесты добавлены в `tests/test_kilo_proxy_relay.py` в этом и следующем раунде — итоговый актуальный счёт см. §27, здесь не дублируется (была внутренняя нестыковка «8» vs «10» между этой строкой и §23 — исправлено, единственный источник истины теперь §27). |
| 7 | DeepSeek V4 по умолчанию `thinking.type=enabled` + `reasoning_effort=high` — relay это не контролирует | `WebFetch` `api-docs.deepseek.com/api/create-chat-completion` — дословно подтверждено: default `thinking.type=enabled`, default `reasoning_effort=high` | ✅ Контраудит прав, реальный и значимый для архитектуры контроля токенов пробел. Добавлен явный opt-in контроль. |
| 8 | Не показаны актуальные версии всех трёх `.ps1` в этом раунде | Не применимо буквально (у меня прямой доступ к файлам на диске, не к вложениям) — но по существу справедливо: `Test-KiloRelayDaily.ps1` и `Invoke-KiloRelayMeasuredRun-v1.ps1` всё ещё не знают про DeepSeek | Принято частично — см. §27 «Не исправлено». |

### 23. Исправления, применённые в этом раунде

**`scripts/kilo_proxy_relay.py`:**
- **Корневой фикс бага #1:** новая `_deepseek_actually_active(environ)` — DeepSeek считается реально активным только если raw `KILO_RELAY_UPSTREAM` **не** задан И preset=deepseek. `DEEPSEEK_CFG` теперь вычисляется через эту функцию (`None`, если raw override победил), а не независимо от `effective_upstream_base()`. Все нижестоящие проверки (`Authorization`-override, model/thinking/reasoning_effort-rewrite) читают только `DEEPSEEK_CFG` — исправлены одним источником, без патчинга каждого места отдельно.
- **Убрана резка `/v1`** (`resolve_upstream_path` удалена целиком) — не нужна: подтверждено, что `.../v1/chat/completions` тоже рабочий путь на DeepSeek. `forward_request`/`forward_request_streaming`/лог вернулись к простой конкатенации `f"{UPSTREAM_BASE}{path}"`. Это одновременно устраняет саму возможность варианта бага #1 через путь (не только через auth/model).
- **`normalize_chat_completions_path(path)`** — новая функция: распознаёт `/v1/chat/completions` независимо от trailing slash, query string, и трактует голый `/chat/completions` как эквивалент. Используется и для детекции compression-пути, и передаётся в `evaluate_guard()` (вместо `self.path`) — закрывает R4 из раунда 1 и пункт 3 контраудита за один проход.
- **`DEEPSEEK_THINKING` / `DEEPSEEK_REASONING_EFFORT`** — новые опциональные env-переменные (валидация значений, `RuntimeError` на некорректных). Если не заданы явно — relay **не трогает** поля `thinking`/`reasoning_effort` в payload (не делает невидимого поведенческого решения за оператора). Применяются в `_handle_proxy` вместе с model-rewrite, корректно переживают оба пути (compression active/inactive). Эффективные оверрайды пишутся в JSONL под `deepseek_overrides`.
- Docstring: убран стейл-пример `KILO_RELAY_FULL_BODY=1`, добавлена оговорка про дефолт "off"; смягчена формулировка про `/v1` у DeepSeek; задокументированы `DEEPSEEK_THINKING`/`DEEPSEEK_REASONING_EFFORT`.
- Проверено: `py_compile` OK; полный regression-тест бага #1 (`env -u ... KILO_RELAY_UPSTREAM=... KILO_RELAY_UPSTREAM_PRESET=deepseek` → `DEEPSEEK_CFG is None`, URL корректный, без резки `/v1`) — **PASS**; `normalize_chat_completions_path` на 5 вариантах путей — **PASS**; невалидные `DEEPSEEK_THINKING`/`DEEPSEEK_REASONING_EFFORT` корректно отклоняются.

**`tests/test_kilo_proxy_relay.py`:** к концу раунда 4 добавлено 10 тестов (12 → 22, все проходят): `_deepseek_actually_active` (3 сценария, включая прямой regression на баг #1), `deepseek_config_from_env` (дефолты, обязательность ключа, thinking/reasoning_effort opt-in и валидация), `effective_upstream_base` (raw побеждает preset), `normalize_chat_completions_path` (5 вариантов путей + non-chat пути не тронуты). В раунде 5 добавлено ещё 3 (reasoning_effort ограничен `high`/`max`, `log_full_body_from_env` дефолт+opt-in) — **итоговый актуальный счёт: 25 тестов, см. §27**, единственный источник истины — вывод `pytest --collect-only -q`, не текст здесь.

**`Start-KiloRelayDaily.ps1` (`D:\AI\...\kilo-relay\`):**
- `-DeepSeekThinking` / `-DeepSeekReasoningEffort` — новые параметры (`ValidateSet`, дефолт `''` = не трогать поле), пробрасываются в одноимённые env-переменные и в `session.json` (с явной пометкой дефолта DeepSeek API, если не заданы).
- `Clear-RelayCompressionEnvironment` расширена ещё на 2 имени (`DEEPSEEK_THINKING`, `DEEPSEEK_REASONING_EFFORT`) — та же логика H3.
- Комментарий про `/v1` смягчён (убрана категоричность), синхронизирован с Python.
- Проверено: `Parser]::ParseFile` — без ошибок.

**`doc/kilo_proxy_relay.md`** (файл существовал в репозитории до этой сессии; изменялся параллельной сессией конкурентно — не мной создан):
- Исправлен дефолт DeepSeek base (`.../v1` → без `/v1`, с уточнением про WorkBuddy).
- Отозван X1 как факт («не существует» → явно помечено `❌ Отозвано 2026-07-22`, эндпоинт реален).
- Добавлена документация `DEEPSEEK_THINKING`/`DEEPSEEK_REASONING_EFFORT` и предупреждение про дефолт DeepSeek (`thinking=enabled`+`high`).
- Исправлено «tools = главный потребитель» → уточнено по реальным данным (`system 43–45% > tools 37–38%`), с пояснением, что tools остаются самым управляемым рычагом.
- Таблица «Известные ограничения» — X1 помечен отозванным, добавлены строки про `system_skills`-мисклассификацию и отсутствие DeepSeek-passthrough в measured-run скрипте (оба — открыты, не пропущены молча).

### 24. Не исправлено в этом раунде (осознанно)

- **`Invoke-KiloRelayMeasuredRun-v1.ps1`**: по-прежнему нет `-UseDeepSeek`-passthrough и не исправлена `system_skills`-мисклассификация в `Get-FragmentCategory`. Причина та же — файл активно редактируется параллельной сессией; безопаснее дождаться стабилизации, чем вносить конфликтующие правки вслепую.
- **`Test-KiloRelayDaily.ps1`**: не обновлён под DeepSeek (cloud model alias без `meta.n_ctx`, JSON mode/tool calling против DeepSeek, streaming). Не проверялся в этом раунде — отдельная задача.
- **Живой smoke DeepSeek** — по-прежнему не выполнялся (не будет выполняться без явного запроса пользователя, учитывая, что это тратит реальные деньги/ключ).

### 25. Скорректированный статус

```text
DEEPSEEK_RAW_OVERRIDE_PRECEDENCE   = FIXED (единый источник DEEPSEEK_CFG через _deepseek_actually_active; 3 regression-теста)
DEEPSEEK_PATH_HANDLING             = SIMPLIFIED (резка /v1 убрана как ненужная; оба варианта пути подтверждены рабочими на DeepSeek)
CHAT_PATH_NORMALIZATION            = FIXED (normalize_chat_completions_path; trailing slash/query string/bare path)
DEEPSEEK_TOKEN_MODE_CONTROL        = ADDED (DEEPSEEK_THINKING/DEEPSEEK_REASONING_EFFORT, opt-in, не меняет поведение по умолчанию невидимо)
DOCUMENTATION_CONSISTENCY          = IMPROVED (doc/kilo_proxy_relay.md синхронизирован; X1 явно отозван, а не молча забыт)
PYTHON_DOCSTRING_CONSISTENCY       = FIXED
TEST_COVERAGE                      = IMPROVED (12 → 22 теста; добавлен прямой regression-тест на найденный критический баг)
POWERSHELL_STACK_VERIFICATION      = PARTIAL (Start-KiloRelayDaily.ps1 синхронизирован и распарсен; Test-/Invoke- скрипты — не в этом раунде)
LIVE_DEEPSEEK_SMOKE                = NOT_RUN (не изменилось)
API_KEY_ROTATION                   = STILL_REQUIRED (не изменилось, см. §15)
```

### 26. Что дальше

1. Дождаться стабилизации `Invoke-KiloRelayMeasuredRun-v1.ps1` и `Test-KiloRelayDaily.ps1` (параллельная сессия), затем: добавить DeepSeek-passthrough в measured-run, обновить `Test-KiloRelayDaily.ps1` под cloud-провайдеров (без `meta.n_ctx`), исправить `Get-FragmentCategory` (`system_skills`).
2. Живой smoke DeepSeek — единственный оставшийся способ закрыть `LIVE_DEEPSEEK_SMOKE`; требует явного решения пользователя (тратит реальный ключ/деньги).
3. Ротация `DEEPSEEK_API_KEY` (§15) — независимый открытый пункт.
4. H2 (пересчёт char-лимитов) — по-прежнему в очереди, вне объёма текущих раундов.

---

## Раунд 5 (2026-07-22): третий контраудит — reasoning_content, reasoning_effort, чистка отчёта

### 27. Что подтверждено верификацией и исправлено

| # | Утверждение | Проверка | Вердикт / фикс |
|---|---|---|---|
| 1 | **Существенно.** DeepSeek требует передавать `reasoning_content` обратно на каждом следующем шаге после tool call, иначе `HTTP 400` | `WebFetch` `api-docs.deepseek.com/guides/thinking_mode` — дословно: «reasoning_content must... be passed back to the API in all subsequent user interaction turns»; «If your code does not correctly pass back reasoning_content, the API will return a 400 error» | ✅ Контраудит прав. Это **не то же самое**, что «не протестировано» — это конкретный, документированный механизм, который вне контроля relay (relay не переписывает историю сообщений Kilo). Задокументировано явно в docstring `kilo_proxy_relay.py`, `doc/kilo_proxy_relay.md` и в сводке в начале этого файла как открытый блокер для multi-turn tool-loop через DeepSeek. **Не исправлено кодом** — это поведение клиента (Kilo), relay не может это починить. |
| 2 | `DEEPSEEK_REASONING_EFFORT` должен принимать `high`/`max`, не `low`/`medium`/`high` | `WebFetch` `api-docs.deepseek.com/api/create-chat-completion` — дословно: «reasoning_effort: high/max»; low/medium молча повышаются до high, xhigh — до max | ✅ Контраудит прав, реальный функциональный баг (единственное осмысленное значение выше `high` было недостижимо). **Исправлено**: `_DEEPSEEK_VALID_REASONING_EFFORT = {"high", "max"}` в Python, `[ValidateSet('', 'high', 'max')]` в PowerShell. |
| 3 | `KILO_RELAY_FULL_BODY`: `doc/kilo_proxy_relay.md` всё ещё говорил «дефолт скрипта — полный body», противореча коду (`"0"`) | Прямой `grep` — подтверждено дословно | ✅ Контраудит прав. Исправлено в доке; **добавлен regression-тест** `test_log_full_body_defaults_off_when_unset` (`LOG_FULL_BODY` вынесен в тестируемую `log_full_body_from_env()`, по образцу остальных env-функций файла) — раньше такого теста не было, утверждение «дефолт off» ничем не подтверждалось. |
| 4 | `SLIM_MODE=off` неверно назван «payload не меняется» — DeepSeek preset applies поверх независимо от `SLIM_MODE` | Прямая проверка кода: auth/model/thinking rewrite в `_handle_proxy` гейтятся только на `DEEPSEEK_CFG`, не на `SLIM_MODE` | ✅ Контраудит прав. Формулировка исправлена: «компрессия отключена, но provider-specific overrides применяются независимо от SLIM_MODE». |
| 6 | «H2 держит 64k безопасным» — overclaim при `GuardMode=warn` (не блокирует) | Подтверждено собственным же §H1 этого документа (`block = mode=='block' AND level ∈ {...}`) — было known ещё с раунда 1, но формулировка в §9 не была приведена в соответствие | ✅ Исправлено: «диагностика для калибровки будущего block-режима», не «защита». |
| 8 | Разнобой «8 новых тестов» / «10 тестов» между §23-соседними абзацами одного раунда | Точный пересчёт по своим же правкам раунда 4: первая волна — 8, вторая (после добавления thinking/reasoning_effort тестов) — ещё 2, итого 10 за раунд; я не обновил первое упоминание после добавления второй волны | ✅ Контраудит прав, моя ошибка формы. Исправлено — единственный источник истины теперь «см. §27», актуальное число (25) через `pytest --collect-only -q`, не через текст. |
| 9 | Арифметика `240k/1.9 ≈ 52-60k` оставлена в теле §8/§9, хотя признана ошибкой в §18/§22 | Прямой `grep` — строка действительно осталась нетронутой при более раннем исправлении (я исправил только табличную запись со статусом, не исходную формулировку в спеке) | ✅ Контраудит прав — классическая проблема «история и актуальная спецификация не разделены». Число в тексте исправлено на месте (126k) со сноской, поясняющей, что это правка задним числом, а не факт, всегда бывший верным. |
| 11 | «Живые HTTP-запросы к DeepSeek» (раунд 3) звучало как end-to-end проверка, противореча `LIVE_SMOKE=NOT_RUN` | Перечитал свои же curl-команды раунда 3 — это были unauthenticated probe-запросы к разным путям (все вернули одинаковый `401 governor`), не реальные chat completions | ✅ Контраудит прав насчёт двусмысленности формулировки. Добавлено явное уточнение: «probe для проверки HTTP-статуса пути, не content-запрос» — разногласия со статусом NOT_RUN не было по факту, но формулировка вводила в заблуждение. |
| 12 | «Оба варианта пути работают» — WorkBuddy подтверждает только `/v1/chat/completions`, не любой `/v1/*` | Согласен методологически — WorkBuddy-фетч проверял ровно один URL | ✅ Формулировка сужена до «конкретно chat completions», без обобщения на `/v1/models`/token-counting/другие пути. |
| 13 | Bare `/chat/completions` теперь корректно **классифицируется**, но не гарантированно **маршрутизируется** — `forward_request` шлёт путь как получен, локальный llama.cpp может 404 на bare-пути | Подтверждено логикой кода: `normalize_chat_completions_path` используется только для detection/guard, `forward_request`/`forward_request_streaming` пересланы к простой `f"{UPSTREAM_BASE}{path}"` без нормализации пути | ✅ Контраудит прав — это осознанный компромисс (не баг): нормализация нужна ровно для того, чтобы compression/guard не пропускали нестандартные варианты пути, а не для того, чтобы чинить сам запрос к upstream. Уточнено в §22 таблице. |
| 14 | Архитектурный риск: `effective_upstream_base()` / `_deepseek_actually_active()` / `DEEPSEEK_CFG` — три места вместо одного `ResolvedUpstream`-объекта, риск повторного рассинхрона | Согласен по существу — риск реален, хотя сейчас закрыт тестами (`test_effective_upstream_raw_wins_over_deepseek_preset`, `test_deepseek_actually_active_false_when_raw_upstream_also_set`) | Принято как обоснованная architecture debt, не блокирующая. Полный рефакторинг в единый `ResolvedUpstream`-дата­класс — за рамками этой сессии (риск сломать существующие тесты, называющие `effective_upstream_base` напрямую по имени); зафиксировано как рекомендация на будущее в §26/next steps. |

### 28. Про «Лог 2» (execution_contract.md, D2-адаптеры, HTML №27) — отдельная задача, не эта сессия

Проверил происхождение: `doc/next/local_model_execution_packet_plan.md`, `doc/presentations/evolutionary_analyses/27_local_model_trust_contour.html`, `doc/presentations/evolutionary_analyses/README.md` были в статусе `M` (modified) **ещё в самом первом `git status` этой беседы**, до того как я начал что-либо делать. Нашёл соответствующий `archive/team_artifacts/_adhoc/local_model_trust_contour_refresh/execution_contract.md` — это результат **другой** сессии/задачи (`local_model_trust_contour_refresh`, docs-only refresh, статус `DONE`, HEAD `4c5c576`), запущенной через штатный `team_workflow`-оркестратор этого проекта, никак не связанной с моей работой над Kilo relay в этой беседе.

Я не видел транскрипт той сессии («Лог 2») и не могу подтвердить или опровергнуть детали процесса (порядок чтения файлов, формулировки в её собственных внутренних логах). Что я **могу** сказать по первичным источникам, которые прочитал только что:
- Сам `execution_contract.md` этой сессии уже честно фиксирует `P0 остаётся ⬜` (реализация не заявлена) и объясняет `check_readset=BLOCK` как ожидаемый результат для 3 write-set файлов, редактируемых инкрементально, а не как единый read-set одного LLM-вызова — это осмысленная, а не декоративная трактовка gate, при условии что такая трактовка действительно закреплена в конвенции проекта (не проверял `doc/token_safety.md` на этот счёт в рамках этой сессии).
- Остальные 12 пунктов контраудита (доверие к client-классификации, D2a/b/c granularity, версионный drift в заголовках, HTML-валидация вместо рендер-проверки, атрибуция изменений при параллельных сессиях) — по существу разумные методологические требования к любому execution-контракту в этом проекте, но у меня нет основания подтверждать или опровергать их применительно к конкретным файлам без отдельного, целенаправленного ревью — это другая задача. Если нужно — сделаю его отдельно, начав с полного чтения `local_model_execution_packet_plan.md` и HTML №27, а не расширяя дальше этот relay-документ.

### 29. Скорректированный статус (раунд 5)

```text
DEEPSEEK_REASONING_CONTENT_CHAIN  = CONFIRMED GAP, OUT OF RELAY'S CONTROL (Kilo client behavior; not tested end-to-end)
DEEPSEEK_REASONING_EFFORT_VALUES  = FIXED (high/max only, было low/medium/high)
LOG_FULL_BODY_DOC_CONTRADICTION   = FIXED (doc synced with code; regression test added)
SLIM_MODE_OFF_DESCRIPTION         = FIXED (компрессия off ≠ provider overrides off)
H2_WARN_MODE_OVERCLAIM            = FIXED (диагностика, не защита)
STALE_ARITHMETIC_IN_BODY_TEXT     = FIXED (число в тексте, не только в статусной таблице)
TEST_COUNT_INTERNAL_CONTRADICTION = FIXED (единый источник — pytest --collect-only, 25 тестов)
LIVE_HTTP_WORDING_AMBIGUITY       = CLARIFIED (probe ≠ end-to-end smoke)
WORKBUDDY_CLAIM_SCOPE             = NARROWED (только chat completions, не любой /v1/*)
BARE_PATH_ROUTING_VS_DETECTION    = CLARIFIED (нормализация — для detection/guard, не для forwarding)
ROUTING_CONFIG_ARCHITECTURE_DEBT  = ACKNOWLEDGED, NOT REFACTORED (риск закрыт тестами, не структурой)
SECTION_NUMBERING                 = FIXED (§25-29 → §22-26 раунда 4; этот раунд — §27-29)
DOCUMENT_HEADER_DATES_STATUS      = FIXED («Создан»/«Последняя актуализация»/статус разделены)
"ЛОГ_2"_MATERIAL                  = OUT OF SCOPE — другая сессия/задача (local_model_trust_contour_refresh), не разбирается здесь
```

### 30. Что дальше

1. `reasoning_content`-цепочка — единственный способ проверить: живой multi-turn Kilo→relay→DeepSeek прогон с реальным tool call. Без него DeepSeek preset нельзя считать готовым для agentic-сценариев, только для однократных запросов.
2. Если нужно ревью «Лог 2»/`local_model_execution_packet_plan.md`/HTML №27 — отдельная задача с чтением их собственных файлов, не расширение этого документа.
3. Пункты §17 из раунда 3 (measured-run DeepSeek passthrough, `Test-KiloRelayDaily.ps1` под cloud, `system_skills`-классификация) — по-прежнему в очереди, файл `Invoke-KiloRelayMeasuredRun-v1.ps1` под параллельной разработкой.
4. Ротация `DEEPSEEK_API_KEY` — независимый открытый пункт (§15).
