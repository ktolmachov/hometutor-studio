# Локальный релей `kilo_proxy_relay.py`

**Назначение:** HTTP-прокси между OpenAI-compatible клиентом (**Cursor** или **Kilo IDE**) и upstream (LM Studio / `llama.cpp` / облако). Сжимает тело `POST /v1/chat/completions`, пишет JSONL-лог, применяет guard из `scripts/_kilo_guard.py`.

**Актуализация:** 2026-07-23 (Tier B: opt-in history window + cap `tool_result` в `cloud_budget`; см. [kilo_relay_history_window_tier_b_2026-07-23.md](next/kilo_relay_history_window_tier_b_2026-07-23.md)). Ранее: 2026-07-22 DeepSeek+cloud_budget, guard/banner, reasoning_content — [architecture review](next/kilo_relay_daily_architecture_review_2026-07-21.md).

---

## Два домена токенов (не путать)

| Домен | Кто тратит | Где лимит | Влияет ли relay? |
|---|---|---|---|
| **A. Runtime RAG** (`hometutor`) | `app/provider_openai.py` → облачные модели | `HARD_TOKEN_LIMIT` в `app/llm_guards.py` | ❌ Нет |
| **B. Coding-ассистент** | Kilo / Cursor → локальная или облачная модель через релей | char-guard `KILO_RELAY_*_BODY_CHARS` | ✅ Да |

Relay снижает расход только в домене **B**. Проблемы прод-RAG решаются в runtime (`rag_context_token_budget`, retrieval, модель), не через этот скрипт.

---

## Запуск

Из корня **hometutor-studio** (DOCS_ROOT). Голый запуск без env уходит на LM Studio `:1234` — для daily-стека `llama.cpp :8080` upstream нужно задать явно.

```powershell
# LM Studio (дефолт upstream)
.\.venv\Scripts\python.exe scripts/kilo_proxy_relay.py

# llama.cpp daily (типично :8080)
$env:KILO_RELAY_UPSTREAM = "http://127.0.0.1:8080"
$env:KILO_RELAY_SLIM_MODE = "off"   # Safe/Audit: без Cursor-allowlist; см. § Kilo vs Cursor
.\.venv\Scripts\python.exe scripts/kilo_proxy_relay.py

# DeepSeek cloud (Cursor: routing + cloud_budget compress)
$env:KILO_RELAY_UPSTREAM_PRESET = "deepseek"
$env:DEEPSEEK_API_KEY = "..."      # обязателен; иначе RuntimeError при импорте модуля
$env:KILO_RELAY_SLIM_MODE = "cloud_budget"   # не local и не off: strip XML без stub system
# опционально: DEEPSEEK_API_BASE, DEEPSEEK_MODEL, DEEPSEEK_THINKING=disabled
.\.venv\Scripts\python.exe scripts/kilo_proxy_relay.py
```

### Cursor → DeepSeek: бюджет без потери качества

Канон для Cursor через релей на DeepSeek:

1. `KILO_RELAY_UPSTREAM_PRESET=deepseek` + `DEEPSEEK_API_KEY` (не задавать raw `KILO_RELAY_UPSTREAM`).
2. **`KILO_RELAY_SLIM_MODE=cloud_budget`** — strip operational XML + ужим схем tools. Список tools не режется (без allowlist). Stub system — **opt-in** через `KILO_RELAY_CLOUD_BUDGET_REPLACE_CURSOR_SYSTEM=1` (профиль launcher `CloudBudget` включает stub). Не использовать `local` и не оставлять unset (дефолт скрипта = `local`).
3. `KILO_RELAY_GUARD_MODE=warn` — уровни `soft_block`/`hard_block` только в JSONL/мини-стате (`blocked=no`); HTTP 413 нет.
4. Опционально `DEEPSEEK_THINKING=disabled` — режет output/latency; для тяжёлого reasoning не включать.
5. **История:** compress default `KEEP_LAST_MESSAGES=0` (не режет). Daily launcher **`CloudBudget`** включает Tier B (`14` / `2000`). Окно режет **число** сообщений, не суммарный размер — при tool-heavy `in=` всё ещё может >12k/20k; тогда новый чат раньше. Ручной env — § Tier B. Неизвестный `SLIM_MODE` → fail-fast при старте.

Канонический daily-оркестратор (Start/Stop/Test/MeasuredRun): `D:\AI\llama_cpp_server_pack_v1\kilo-relay\` (`Start-KiloRelayDaily.ps1`, в т.ч. `-UseDeepSeek`). Python-релей и compress/guard — в этом репозитории: `scripts/kilo_proxy_relay.py`, `_kilo_relay_compress.py`, `_kilo_guard.py`.

Полный список `KILO_RELAY_*` — в docstring [`scripts/kilo_proxy_relay.py`](../scripts/kilo_proxy_relay.py).

**Таймаут к upstream:** `KILO_RELAY_UPSTREAM_TIMEOUT` (секунды, по умолчанию `120`).

**Windows / UTF-8:** при старте вызывается `_configure_stdio_utf8()` (`reconfigure` + `line_buffering=True` под try/except) и `_safe_print()` — без этого кириллица в стартовых строках на `cp1252` роняла процесс до `serve_forever` (порт 8787 не поднимался).

---

## Выбор upstream

Приоритет в `effective_upstream_base()`:

1. Явный **`KILO_RELAY_UPSTREAM`** — всегда побеждает (raw override); при заданном raw override DeepSeek-специфичные подмены (auth/model/thinking) **тоже** отключаются, даже если `KILO_RELAY_UPSTREAM_PRESET=deepseek` остался в окружении (см. `_deepseek_actually_active` — фикс регрессии, найденной живым тестом 2026-07-22).
2. **`KILO_RELAY_UPSTREAM_PRESET=deepseek`** → `DEEPSEEK_API_BASE` (дефолт `https://api.deepseek.com`, без `/v1` — канонический DeepSeek quickstart base_url).
3. **`SLIM_MODE=cloud_budget`** → `KILO_RELAY_CLOUD_DEFAULT_UPSTREAM` (дефолт `https://api.vsegpt.ru`).
4. Иначе LM Studio → `KILO_RELAY_UPSTREAM_DEFAULT_LOCAL` или `http://127.0.0.1:1234`.

Bind по умолчанию: `127.0.0.1:8787` (`KILO_RELAY_HOST` / `KILO_RELAY_PORT`).

### DeepSeek preset

| Env | Смысл |
|---|---|
| `KILO_RELAY_UPSTREAM_PRESET=deepseek` | Включить preset (только если `KILO_RELAY_UPSTREAM` не задан явно) |
| `DEEPSEEK_API_KEY` | Обязателен; fail-fast `RuntimeError`, если нет |
| `DEEPSEEK_API_BASE` | Дефолт `https://api.deepseek.com` (подтверждено официальными доками; конкретно для `.../v1/chat/completions` также подтверждён путь с `/v1` — WorkBuddy-интеграция DeepSeek использует именно этот URL. Это **не** доказывает, что любой другой `/v1/*`-путь — `/v1/models`, нестандартные token-counting endpoints и т.п. — аналогично алиасится; проверялась только chat completions) |
| `DEEPSEEK_MODEL` | Дефолт `deepseek-v4-pro` — подтверждённая реальная модель (релиз 2026-04, есть также `deepseek-v4-flash`), контекст **1M токенов** |
| `DEEPSEEK_THINKING` | Опционально `enabled`/`disabled`. **DeepSeek V4 по умолчанию `thinking.type=enabled` + `reasoning_effort=high`** — может незаметно раздувать output tokens/задержку/счёт. Не задано = релей не трогает поле |
| `DEEPSEEK_REASONING_EFFORT` | Опционально `high`/`max` — это единственные реальные уровни DeepSeek (API молча повышает `low`/`medium` до `high`, `xhigh` до `max`); релей намеренно не предлагает `low`/`medium`, чтобы не создавать иллюзию несуществующей гранулярности |
| `DEEPSEEK_REASONING_CONTENT_GUARD` | `warn` (дефолт) / `block`. `warn` — stderr-предупреждение до upstream-вызова, запрос всё равно уходит; `block` — локальный `HTTP 422` без похода к DeepSeek, если assistant-сообщение с `tool_calls` без `reasoning_content` при включённом thinking |

**Payload compatibility fixes (реализовано, `apply_deepseek_compatibility()`)** — все четыре подтверждены официальным гайдом DeepSeek по agent-интеграциям (oh_my_pi) как несовместимые; гайд явно связывает `HTTP 400` с tool/thinking-полями (`tool_choice`, `content:null`), для `developer`-роли и `max_completion_tokens` там же описана несовместимость без отдельно живьём подтверждённого `400` с нашей стороны:
- `role: "developer"` → переписывается в `role: "system"` (DeepSeek отклоняет `developer`);
- `tool_choice` вырезается, если thinking-режим эффективно включён (в т.ч. дефолт DeepSeek при не заданном `DEEPSEEK_THINKING`) — DeepSeek отклоняет `tool_choice` в thinking-режиме;
- `max_completion_tokens` переименовывается в `max_tokens` (или отбрасывается, если оба заданы);
- `assistant`-сообщение с tool call и `content: null` получает `content: ""` (DeepSeek требует non-null content).

Эти четыре — stateless факты одного запроса, relay может и чинит их сам. Применённые фиксы пишутся в JSONL под `deepseek_overrides.compatibility_fixes`. Эффективный thinking-режим (`effective_thinking_type()`) читается из **самого payload** (`payload["thinking"]["type"]`), а не только из env — так как к этому месту кода env-оверрайд `DEEPSEEK_THINKING` уже применён к payload, если он был задан; это корректно учитывает и явный клиентский `thinking:{"type":"disabled"}` без какого-либо env override (был баг: раньше читался только env, клиентское значение игнорировалось).

⚠ **Частично закрыто — детекция есть, восстановление вне контроля relay:** DeepSeek требует, чтобы `reasoning_content` из ответа с tool call был передан обратно в истории сообщений на **каждом** следующем шаге разговора — иначе API вернёт `HTTP 400`. Relay не может восстановить историю между запросами (это состояние диалога, которым relay не владеет), но **может** проверить текущий payload: `detect_missing_reasoning_content()` находит assistant-сообщение с `tool_calls` без `reasoning_content` при эффективно включённом thinking. Поведение управляется `DEEPSEEK_REASONING_CONTENT_GUARD`:
- `warn` (дефолт) — печатает предупреждение в stderr **до** upstream-вызова и пишет в `deepseek_overrides.warnings`, запрос всё равно уходит;
- `block` — локально отклоняет запрос (`HTTP 422`, без похода к DeepSeek) **до** какого-либо платного вызова.

Совместимость Kilo с конвенцией `reasoning_content` **не подтверждена** (не было ни захваченного multi-turn trace, ни просмотра исходников Kilo-адаптера) — многошаговый agentic tool-loop через DeepSeek preset может сломаться на втором tool round-trip. **Не проверено end-to-end.**

**Защита от утечки ключа на неверный host:** `DEEPSEEK_API_BASE` обязан быть `https://api.deepseek.com`, иначе релей падает при старте с `RuntimeError` (не молча отправляет реальный ключ куда попало). Другой host — только через явный `DEEPSEEK_ALLOW_CUSTOM_HOST=1`. Заголовки `Cookie`/`Proxy-Authorization`/прочие client-side auth убираются перед отправкой на DeepSeek; `Accept-Encoding` убирается перед отправкой на **любой** upstream (релей не умеет распаковывать gzip, а `Content-Encoding` из ответа уже стрипается — иначе клиент получил бы несжимаемые байты без заголовка, объясняющего почему).

Пока preset **реально активен** (т.е. `KILO_RELAY_UPSTREAM` не задан явно — см. пункт 1 выше):

- для **всех** запросов (включая `GET /v1/models`) `Authorization` клиента заменяется на `Bearer $DEEPSEEK_API_KEY` (дамми-ключ Kilo/`local-relay` на DeepSeek не уходит);
- в `POST /v1/chat/completions` поле `model` принудительно переписывается на `DEEPSEEK_MODEL`, `thinking`/`reasoning_effort` — если заданы явно (и при активной, и при выключенной компрессии);
- фактически применённые оверрайды пишутся в JSONL под ключом `deepseek_overrides` каждого запроса.

В `Start-KiloRelayDaily.ps1 -UseDeepSeek` локальный `Start-LocalModel.ps1` и проверка llama.cpp **пропускаются**; `KILO_RELAY_UPSTREAM` на `:8080` **не** выставляется (иначе raw override перебил бы preset). `DEEPSEEK_API_KEY` в параметры скрипта не передаётся — только из окружения вызывающего. Параметры `-DeepSeekThinking`/`-DeepSeekReasoningEffort` пробрасывают одноимённые env-переменные и попадают в `session.json`.

---

## Клиент: Cursor / Kilo

Базовый URL OpenAI-compatible API должен указывать **на релей** (`http://127.0.0.1:8787` или `http://127.0.0.1:8787/v1`), а не напрямую на DeepSeek / LM Studio / llama.cpp — иначе сжатие, guard и JSONL на границе не выполняются.

**Тишина в консоли релея при «живом» чате Cursor** — почти всегда значит, что трафик идёт мимо процесса:

1. В Cursor → Settings → Models у OpenAI-compatible провайдера Base URL = `http://127.0.0.1:8787/v1` (тот же host:port, что в баннере `LISTEN EFFECTIVE`), **не** `https://api.deepseek.com`.
2. В чате выбрана модель именно этого провайдера («Local Coder Relay…»). Бейдж имени модели ≠ гарантия маршрута: Agent может ходить в Cursor Cloud / прямой DeepSeek.
3. Проверка: `Invoke-WebRequest http://127.0.0.1:8787/v1/models` — в консоли релея должна появиться строка `→ GET …`; иначе смотрите другой порт/процесс.
4. Не запускайте второй релей, пока первый держит 8787: на Windows без exclusive-bind два `python scripts/kilo_proxy_relay.py` могли оба показать `:8787`, а мини-стата шла в «чужой» терминал. Сейчас bind exclusive (`SO_EXCLUSIVEADDRUSE`); проверка: `netstat -ano | findstr :8787` — должен быть **один** LISTENING PID.

### Kilo vs Cursor (важно)

Сжатие и дефолтный allowlist заточены под **Cursor** (XML-теги `<available_skills>`, `<mcp_file_system>`, …; tools `Shell,Read,Write,Grep`). У Kilo (Roo/Cline) другой формат промпта (Markdown-секции) и другие имена tools (`read_file`, `write_to_file`, `execute_command`, `search_files`, `apply_diff`).

| Режим | Для Kilo |
|---|---|
| **`SLIM_MODE=off`** (Audit / Safe daily) | Компрессия отключена (skills/MCP/rules XML не режутся, tools не сужаются); **но** provider-specific overrides (DeepSeek preset: `Authorization`, `model`, `thinking`/`reasoning_effort`) применяются независимо от `SLIM_MODE` — «payload не меняется» верно только в отсутствие активного DeepSeek preset |
| **`SLIM_MODE=local`** (дефолт скрипта) | Allowlist Cursor-имён → на Kilo tools могут **исчезнуть** (`tools` выкидывается) |
| Strip-флаги Safe | На живом Kilo-payload часто `strip_actions=[]` — экономия ≈ 0, кроме усечения descriptions при явном `TOOL_DESCRIPTION_MAX_CHARS` |

Для Kilo daily: задавать `SLIM_MODE` явно и брать `-ToolAllowlist` из **реальных** имён (Audit-лог / measured run), не из Cursor-ядра.

⚠ **Уточнение 2026-07-22 (реальный Kilo-прогон, `exact_token_breakdown.csv`):** system prompt Kilo (~43–45% input) больше, чем tool JSON schemas (~37–38%), не наоборот — ранняя оценка «tools = главный потребитель / 81%» основывалась на синтетическом smoke-запросе с одним tool, не на реальном трафике. Tools при этом остаются самым **управляемым** рычагом (system prompt Kilo не меняется), не Cursor-XML. Рычаг: `KILO_RELAY_TOOL_DESCRIPTION_MAX_CHARS` + честный allowlist.

---

## Guard

| Режим | Поведение |
|---|---|
| **`KILO_RELAY_GUARD_MODE=warn`** (рекомендуемый / daily Safe) | Только предупреждения в JSONL; **HTTP 413 не бывает** |
| **`block`** | 413 `relay_context_guard_blocked` при `soft_block` / `hard_block` (тело > max / hard, messages, workflow-combo) |

Оценка размера — **char-based** (`chars/4` ≈ токены в мини-стате). На tool-heavy payload соотношение может быть ~1.9 chars/tok. Exact `usage.prompt_tokens` / `completion_tokens` из ответа upstream пишутся в JSONL `response.usage` и в мини-стату `in=`/`out=` (R3-lite); `timings.*` llama.cpp по-прежнему не парсятся.

⚠ **Уточнение 2026-07-22:** эндпоинт `POST /v1/chat/completions/input_tokens` **реально существует** в llama.cpp server (подтверждено официальным `tools/server/README.md`) — точный подсчёт входных токенов через него работает; не отключать/не считать несуществующим (ранняя версия этого разбора ошибочно утверждала обратное). Не работает он для DeepSeek/облачных провайдеров — это фича конкретно llama.cpp.

Guard смотрит уже **forwarded** (после compress) body. Исходный размер клиента — в JSONL `request_original` (компактный summary без preview); `request` = forwarded (R1-lite). В stderr: `guard=<level> mode=<warn|block> blocked=<yes|no>` — `hard_block` при `mode=warn` **не** означает HTTP-блок.

---

## Стриминг (`stream: true`)

1. По умолчанию релей **проксирует SSE** байт-в-байт: ответ клиенту — **HTTP/1.0**, **`Connection: close`**, без **`Content-Length`** и без ручного `Transfer-Encoding: chunked` (chunked ломал разбор в Cursor).
2. Откат к полной буферизации: **`KILO_RELAY_BUFFER_STREAM=1`**.

---

## Лог релея (`logs/kilo_relay.jsonl`)

1. Единственный источник истины — код: `LOG_FULL_BODY = log_full_body_from_env(dict(os.environ))` (`scripts/kilo_proxy_relay.py`), где `log_full_body_from_env()` читает `KILO_RELAY_FULL_BODY`. **Дефолт — выключено** (opt-in: `"1"`/`"true"`/`"yes"`/`"on"`). Точность формулировки: проверено тестом на саму функцию `log_full_body_from_env({})` (`test_log_full_body_defaults_off_when_unset`), а не тестом полного импорта модуля без env — это разные по силе проверки, вторая не выполнялась отдельно. При **`KILO_RELAY_FULL_BODY=1`** в запись попадают тела запроса/ответа — следите за **размером файла** и **PII**. `Start-KiloRelayDaily.ps1` тоже по умолчанию выставляет `0` (флаг `-FullBodyLogging` включает).
2. **Заголовки в JSONL (`request_headers`) пишутся всегда, независимо от `KILO_RELAY_FULL_BODY`.** До 2026-07-22 (раунд 7) `redact_headers()` маскировал только `Authorization` и имена, содержащие `api-key`/оканчивающиеся на `key` — `Cookie`, `Proxy-Authorization`, `X-Auth-Token` и подобные писались в лог открытым текстом на **каждом** запросе. Исправлено: `redact_headers()` и `_prepare_upstream_request_headers()` (DeepSeek-preset) используют одну функцию `is_sensitive_header_name()`.
3. `GET /models` и прочий не-chat трафик пишутся тем же форматом (засоряют статистику токенов) — учитывать при разборе.
4. Стартовый баннер: bind/upstream/guard/compress/DeepSeek. При `RELAY_COMPRESS_ACTIVE=no` полный dump `compress.*` **не** печатается. При DeepSeek+`off`/`local`/unset — `WARN:` с рекомендацией `cloud_budget`. Аннотация vsegpt только если DeepSeek **не** активен.
5. После каждого запроса в **stderr** — строка `→ METHOD path` в начале и мини-стата в конце: `body_orig`/`body_fwd`, `guard=… mode=… blocked=…`, опционально `saved=` / `hist_cut=` / `tr_capped=` / `in=`/`out=`, плюс glance `top_kind` / `top_path` / `top_frag` из `content_stats` (**original**, до compress). Если после старта тишина — HTTP до этого процесса не доходит (см. § Клиент).
6. **`content_stats`** (дефолт ON, `KILO_RELAY_CONTENT_STATS=1`): в JSONL пара `original`/`forwarded` с `role_chars`, `kind_chars`, `fragment_chars` (Cursor XML), `path_chars` (топ путей; эвристика окна ±200 симв. вокруг упоминания — **относительный ранг**, не байты файла), `ext_chars`, `tools.by_name`, `top_messages` (без тела). Агрегатор: `scripts/kilo_prompt_content_report.py --last 50` (при `chat_with_stats=0` отказывает `--json-out`, чтобы не затереть прежний отчёт).
7. Тяжёлые `message_stats`/preview в `request` по умолчанию **не** пишутся (`KILO_RELAY_MESSAGE_STATS=1` чтобы вернуть).

---

## Лог LM Studio / LlamaV4 (как читать)

1. **`cache reuse is not supported - ignoring n_cache_reuse`** — ограничение конфигурации/сборки; полезен **LCP/prompt cache** (`sim_best`, `f_keep`).
2. **`sim_best = 1.000`** и быстрый **prompt eval** при большом `task.n_tokens` — префикс из KV, пересчитывается хвост.
3. Смена модели / первого system-блока снова делает prompt eval дорогим — ожидаемо.

---

## System stub и имя модели

1. В режиме **`local`** длинный system Cursor заменяется коротким stub’ом (`KILO_RELAY_CURSOR_SYSTEM_STUB`).
2. В stub: при вопросе о модели можно опереться на поле **`model`** в JSON. Ответ модели и строка API могут расходиться.

---

## Несколько параллельных запросов

Несколько чатов = несколько слотов/task в логе Studio; растёт нагрузка на VRAM, может падать tok/s.

---

## Обновления LM Studio и `llama.cpp`

После крупного обновления сервера — один короткий запрос через релей. При регрессии SSE временно **`KILO_RELAY_BUFFER_STREAM=1`**.

Context-gate daily (`meta.n_ctx` в `/v1/models`): при отсутствии поля Start использует fallback **`GET /props`** (`default_generation_settings.n_ctx` / `n_ctx`); иначе warning + `-SkipContextGate`.

---

## System prompt Cursor и релей (alignment)

Платформенный system в Cursor — склейка идентичности, политик и operational docs. Облачные модели это переваривают; локальная малая модель несёт фиксированный налог на каждый запрос.

### Три класса контента

| Класс | Примеры в Cursor | Нужен локалке? | Типичная стратегия |
|--------|------------------|----------------|---------------------|
| Core identity | «You are a coding assistant…», `<user_query>` | да | Короткий stub / сжатая формулировка |
| Behavioral rules | tone, tool_calling, часть editing | частично | Stub + user rules без дубляжа |
| Operational docs | `<citing_code>`, `<mcp_file_system>`, browser/terminal how-to | нет (как статический префикс) | Убрать или не пускать до модели |

### `KILO_RELAY_SLIM_MODE=cloud_budget`

Между **local** и **off**: `role: system` **не** заменяется (пока не включён `KILO_RELAY_CLOUD_BUDGET_REPLACE_CURSOR_SYSTEM=1`); из текста вырезается вторичный XML; список tools не сужается (если нет allowlist); по умолчанию ужимаются descriptions tools и чистятся descriptions в `parameters` (`KILO_RELAY_CLOUD_BUDGET_*`).

**Важно:** в `cloud_budget` generic-переменные `KILO_RELAY_REPLACE_CURSOR_SYSTEM`, `KILO_RELAY_KEEP_LAST_MESSAGES`, `KILO_RELAY_MAX_TOOL_RESULT_CHARS` **не работают** — значения берутся только из одноимённых `KILO_RELAY_CLOUD_BUDGET_*` (override, не fallback; см. `_kilo_relay_compress.py`: `:592-594` generic-чтение, `:616` system stub, `:626-627` Tier B).

### Tier B: history window + cap `tool_result` (opt-in, 2026-07-23)

Cursor шлёт **всю** историю на каждый ход; без Tier B relay только strip XML / ужимает tool schemas (~10% экономии). Tier B режет то, что реально раздувает сессию:

| Env (`cloud_budget`) | Дефолт | Эффект |
|---|---|---|
| `KILO_RELAY_CLOUD_BUDGET_KEEP_LAST_MESSAGES` | `0` (выкл) | Ведущие `system` + последние N остальных сообщений; граница не оставляет «висячий» `tool` без пары `assistant.tool_calls` |
| `KILO_RELAY_CLOUD_BUDGET_MAX_TOOL_RESULT_CHARS` | `0` (выкл) | Head-keep cap для `role=tool`, маркер `…[truncated by relay: N more chars]` |

Рекомендуемый старт для Cursor→DeepSeek (новая сессия + перезапуск relay):

```powershell
# Вариант A — daily launcher (канон):
pwsh -File D:\AI\llama_cpp_server_pack_v1\kilo-relay\Start-KiloRelayDaily.ps1 `
  -UseDeepSeek -RelayProfile CloudBudget -StopExistingRelay `
  -DeepSeekThinking disabled

# Вариант B — ручной env перед scripts/kilo_proxy_relay.py:
$env:KILO_RELAY_UPSTREAM_PRESET = "deepseek"
$env:KILO_RELAY_SLIM_MODE = "cloud_budget"
$env:KILO_RELAY_CLOUD_BUDGET_STRIP_CURSOR_RULES = "1"
$env:KILO_RELAY_CLOUD_BUDGET_STRIP_USER_INFO = "1"
$env:KILO_RELAY_CLOUD_BUDGET_REPLACE_CURSOR_SYSTEM = "1"
# allowlist опционален (~2k tok savings); без него tools=16. Match case-insensitive.
# Имена должны совпадать с Cursor tool ids (часто lowercase: bash/read/grep/…).
# Не используйте Edit — в Cursor это обычно StrReplace/edit; чужое имя silently drop'ает tool.
# $env:KILO_RELAY_TOOLS_ALLOWLIST = "Shell,Read,Grep,Write,StrReplace"
$env:KILO_RELAY_CLOUD_BUDGET_KEEP_LAST_MESSAGES = "14"
$env:KILO_RELAY_CLOUD_BUDGET_MAX_TOOL_RESULT_CHARS = "2000"
```

Параметры launcher: `-CloudBudgetKeepLastMessages` / `-CloudBudgetMaxToolResultChars` (дефолт **14 / 2000**; раньше 24/4000 — live log показал in до 26k при активном tool-loop). Окно = count, не char-budget: даже с hist_cut `in=` может превышать 12k/20k — новый чат раньше soft_block. `-UseDeepSeek` + `-RelayProfile Safe` даёт warning (без Tier B).
В stderr ищите `hist_cut=` / `tr_capped=`; в JSONL — `relay_compress.messages_dropped_history` / `tool_results_capped`. Детали и evidence: [kilo_relay_history_window_tier_b_2026-07-23.md](next/kilo_relay_history_window_tier_b_2026-07-23.md).

### `KILO_RELAY_SLIM_MODE=local` (дефолт скрипта)

При **`KILO_RELAY_LOCAL_KEEP_CURSOR_SYSTEM` не включён** длинный Cursor `system` **заменяется stub’ом**. Остаётся нагрузка во 2+ сообщениях (`<rules>`, user_info, skills) — отдельные strip-флаги.

### Карта: фрагмент → рычаг

| Фрагмент | Релей |
|----------|-------|
| Экономия в облаке без замены platform system | **`SLIM_MODE=cloud_budget`** + `KILO_RELAY_CLOUD_BUDGET_*` |
| Весь тяжёлый Cursor `system` | **`replace_cursor_system_content`** (local); отмена: `KILO_RELAY_LOCAL_KEEP_CURSOR_SYSTEM=1` |
| `<mcp_file_system>` / MCP XML | strip в local и cloud_budget; плюс выключить MCP в IDE |
| `<terminal_files_information>` | **`KILO_RELAY_STRIP_TERMINAL_FILES_INFORMATION_XML`** |
| `<task_management>` | **`KILO_RELAY_STRIP_TASK_MANAGEMENT_XML`** |
| `<available_skills>` | **`KILO_RELAY_STRIP_AVAILABLE_SKILLS_XML`** |
| `<rules>…</rules>` в user | **`KILO_RELAY_LOCAL_STRIP_CURSOR_RULES=1`** |
| Схемы tools | local: summaries / purge / **`KILO_RELAY_TOOLS_ALLOWLIST`** |
| Накопленная история agent-loop | **`KILO_RELAY_CLOUD_BUDGET_KEEP_LAST_MESSAGES`** (Tier B) + новый чат |
| Полные Read/Grep dumps в `tool_result` | **`KILO_RELAY_CLOUD_BUDGET_MAX_TOOL_RESULT_CHARS`** (Tier B) + grep/head вместо full-read |

Имена полей: `relay_compress_config_from_env` в [`scripts/_kilo_relay_compress.py`](../scripts/_kilo_relay_compress.py).

### Чеклист

1. Base URL клиента → релей, не upstream напрямую.
2. Режим: **`local`** для Cursor→LM Studio; **`cloud_budget`** для облака без stub; для **Kilo** — `off` или allowlist из Audit.
3. Не дублировать в user rules tutorial-блоки, уже вырезанные релеем.
4. Неиспользуемые MCP выключить в IDE.
5. Сверка: стартовый баннер `compress.*` и заголовки `X-Kilo-Relay-*`.

### Три профиля

#### A. Облако — полный контекст

| | |
|---|---|
| **Endpoint** | Провайдер напрямую, **без** релея |
| **Когда** | Сложная архитектура; важнее качество, чем счёт |

#### B. Облако — экономия

| Рычаг | Действие |
|--------|----------|
| **Релей** | Base URL → релей. **Cursor→DeepSeek:** `PRESET=deepseek` **и** `SLIM_MODE=cloud_budget` (routing + compress). Без preset при одном `cloud_budget` и пустом upstream → vsegpt |
| **Сжатие** | **`SLIM_MODE=cloud_budget`**: strip XML, без stub system; опционально `CLOUD_BUDGET_*` / allowlist |
| **Rules / MCP / история** | Короткие; только нужные MCP; новый чат на пакет работ (`msgs` compress не режет) |

#### C. Локалка через релей

| | |
|---|---|
| **Endpoint** | Релей → LM Studio `:1234` или llama.cpp `:8080` (`KILO_RELAY_UPSTREAM`) |
| **Rules** | Короткий набор; для Kilo — не полагаться на Cursor-strip |

---

## Известные ограничения (на 2026-07-22)

| ID | Суть | Статус |
|---|---|---|
| C1 / C2 | Strip/allowlist под Cursor; на Kilo без явного `SLIM_MODE`/allowlist — риск сломать tools | Документировано; фикс regex/allowlist — отдельная задача |
| R1 / R3 | `request_original` + `response.usage` в JSONL/мини-стате (lite). Полный sha/hash body и llama.cpp `timings.*` — ещё нет | ✅ lite 2026-07-22; timings open |
| R5 | `chars/4` неточен в обе стороны | Открыто (exact `usage` частично закрывает) |
| H2 | Char-пороги: **SSoT кода** `hard_block_body_chars=110000` (не 100k/150–240k из старых строк review) | Диагностика при `warn`; калибровка `block` — отдельно |
| X1 | ~~`/v1/chat/completions/input_tokens` не существует~~ | ❌ **Отозвано 2026-07-22** — эндпоинт реален в llama.cpp (официальные доки), используется `ExactTokenBreakdown` в measured-run скрипте |
| UTF-8 stdio | Краш стартапа на cp1252 | ✅ Исправлено в `kilo_proxy_relay.py` |
| DeepSeek routing | Preset + auth/model/thinking rewrite | ✅ В `kilo_proxy_relay.py` + Start `-UseDeepSeek`; фикс regressions (raw-override precedence, double-`/v1`) — 2026-07-22 |
| DeepSeek thinking/reasoning | V4 по умолчанию `thinking=enabled`+`reasoning_effort=high` | ✅ Опциональный контроль `DEEPSEEK_THINKING`/`DEEPSEEK_REASONING_EFFORT` |
| C3 / H3 | `/props` fallback; расширенный clear env при смене профиля | ✅ В `Start-KiloRelayDaily.ps1` |
| `system_skills` мисклассификация | `Get-FragmentCategory` матчит substring «skill» внутри «skilled» на весь system prompt | Открыто (файл `Invoke-KiloRelayMeasuredRun-v1.ps1` в параллельной разработке) |
| Measured-run DeepSeek passthrough | `Invoke-KiloRelayMeasuredRun-v1.ps1` не имеет `-UseDeepSeek` | Открыто (та же причина) |
| DeepSeek payload compatibility | `developer`-роль, `tool_choice` в thinking-режиме, `max_completion_tokens`, `content:null` на tool-call — все дают `HTTP 400` (подтверждено oh_my_pi guide) | ✅ `apply_deepseek_compatibility()` — фиксит все 4 (stateless, per-request) |
| DeepSeek API key → произвольный host | `DEEPSEEK_API_BASE` не валидировался (https/hostname) | ✅ `validate_deepseek_api_base()` — fail-fast без `https://api.deepseek.com` или явного `DEEPSEEK_ALLOW_CUSTOM_HOST=1` |
| Header leakage / gzip | Cookie/Proxy-Authorization форвардились на DeepSeek; `Accept-Encoding` форвардился на любой upstream при стрипнутом `Content-Encoding` в ответе | ✅ `_prepare_upstream_request_headers()` — Accept-Encoding убран всегда, доп. заголовки — только для DeepSeek preset |
| `reasoning_content` (multi-turn tool loop) | Требуется передавать обратно на каждом шаге, иначе `HTTP 400` — **stateful**, вне контроля relay | Открыто, не проверено end-to-end; формулировка «Kilo не совместим» смягчена до «совместимость не подтверждена» |
| Regression-тест утечки ключа | Раньше тестировался только helper `_deepseek_actually_active`, не сам `_handle_proxy` | ✅ `test_handle_proxy_stale_deepseek_preset_does_not_leak_key_to_raw_upstream` + позитивный контроль — гоняют реальный код-путь |

Подробный разбор: [kilo_relay_daily_architecture_review_2026-07-21.md](next/kilo_relay_daily_architecture_review_2026-07-21.md). Смежный отчёт по LiteLLM-шлюзу: [local_llm_gateway_relay_litellm_report_2026-07-21.md](local_llm_gateway_relay_litellm_report_2026-07-21.md).

---

## Связанные документы

| Документ | Содержание |
|---|---|
| [kilo_budget_system.md](kilo_budget_system.md) | Архитектура Kilo budget, guard Tier 1/2 |
| [kilo_budget_gate.md](kilo_budget_gate.md) | CI gate, те же пороги guard |
| [kilo_budget_capture_runbook.md](kilo_budget_capture_runbook.md) | Runbook, в т.ч. запуск релея |
| [next/kilo_relay_daily_architecture_review_2026-07-21.md](next/kilo_relay_daily_architecture_review_2026-07-21.md) | Архитектурный review + статус правок |
| [`tests/test_kilo_proxy_relay.py`](../tests/test_kilo_proxy_relay.py) | Юнит-тесты: стрим без chunked, обрыв клиента, заголовки |
