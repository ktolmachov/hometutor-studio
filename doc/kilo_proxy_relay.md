# Локальный релей `kilo_proxy_relay.py`

**Назначение:** HTTP-прокси между OpenAI-compatible клиентом (**Cursor** или **Kilo IDE**) и upstream (LM Studio / `llama.cpp` / облако). Сжимает тело `POST /v1/chat/completions`, пишет JSONL-лог, применяет guard из `scripts/_kilo_guard.py`.

**Актуализация:** 2026-07-21 (DeepSeek-preset, UTF-8 stdio, выводы [architecture review](next/kilo_relay_daily_architecture_review_2026-07-21.md)).

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

# DeepSeek cloud (preset; ключ только из env, не из argv)
$env:KILO_RELAY_UPSTREAM_PRESET = "deepseek"
$env:DEEPSEEK_API_KEY = "..."      # обязателен; иначе RuntimeError при импорте модуля
# опционально: DEEPSEEK_API_BASE, DEEPSEEK_MODEL
.\.venv\Scripts\python.exe scripts/kilo_proxy_relay.py
```

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
| `DEEPSEEK_API_BASE` | Дефолт `https://api.deepseek.com` (подтверждено официальными доками; `.../v1/chat/completions` тоже работает — WorkBuddy-интеграция DeepSeek использует именно этот путь, path rewriting не нужен) |
| `DEEPSEEK_MODEL` | Дефолт `deepseek-v4-pro` — подтверждённая реальная модель (релиз 2026-04, есть также `deepseek-v4-flash`), контекст **1M токенов** |
| `DEEPSEEK_THINKING` | Опционально `enabled`/`disabled`. **DeepSeek V4 по умолчанию `thinking.type=enabled` + `reasoning_effort=high`** — может незаметно раздувать output tokens/задержку/счёт. Не задано = релей не трогает поле |
| `DEEPSEEK_REASONING_EFFORT` | Опционально `low`/`medium`/`high` (значимо только при `thinking=enabled`) |

Пока preset **реально активен** (т.е. `KILO_RELAY_UPSTREAM` не задан явно — см. пункт 1 выше):

- для **всех** запросов (включая `GET /v1/models`) `Authorization` клиента заменяется на `Bearer $DEEPSEEK_API_KEY` (дамми-ключ Kilo/`local-relay` на DeepSeek не уходит);
- в `POST /v1/chat/completions` поле `model` принудительно переписывается на `DEEPSEEK_MODEL`, `thinking`/`reasoning_effort` — если заданы явно (и при активной, и при выключенной компрессии);
- фактически применённые оверрайды пишутся в JSONL под ключом `deepseek_overrides` каждого запроса.

В `Start-KiloRelayDaily.ps1 -UseDeepSeek` локальный `Start-LocalModel.ps1` и проверка llama.cpp **пропускаются**; `KILO_RELAY_UPSTREAM` на `:8080` **не** выставляется (иначе raw override перебил бы preset). `DEEPSEEK_API_KEY` в параметры скрипта не передаётся — только из окружения вызывающего. Параметры `-DeepSeekThinking`/`-DeepSeekReasoningEffort` пробрасывают одноимённые env-переменные и попадают в `session.json`.

---

## Клиент: Cursor / Kilo

Базовый URL OpenAI-compatible API должен указывать **на релей** (`http://127.0.0.1:8787`), а не напрямую на LM Studio / llama.cpp — иначе сжатие и guard на границе не выполняются.

### Kilo vs Cursor (важно)

Сжатие и дефолтный allowlist заточены под **Cursor** (XML-теги `<available_skills>`, `<mcp_file_system>`, …; tools `Shell,Read,Write,Grep`). У Kilo (Roo/Cline) другой формат промпта (Markdown-секции) и другие имена tools (`read_file`, `write_to_file`, `execute_command`, `search_files`, `apply_diff`).

| Режим | Для Kilo |
|---|---|
| **`SLIM_MODE=off`** (Audit / Safe daily) | Passthrough: payload не меняется; tool-calling сохраняется |
| **`SLIM_MODE=local`** (дефолт скрипта) | Allowlist Cursor-имён → на Kilo tools могут **исчезнуть** (`tools` выкидывается) |
| Strip-флаги Safe | На живом Kilo-payload часто `strip_actions=[]` — экономия ≈ 0, кроме усечения descriptions при явном `TOOL_DESCRIPTION_MAX_CHARS` |

Для Kilo daily: задавать `SLIM_MODE` явно и брать `-ToolAllowlist` из **реальных** имён (Audit-лог / measured run), не из Cursor-ядра.

Главный потребитель токенов в Kilo — **JSON schemas tools**, не Cursor-XML. Рычаг: `KILO_RELAY_TOOL_DESCRIPTION_MAX_CHARS` + честный allowlist.

---

## Guard

| Режим | Поведение |
|---|---|
| **`KILO_RELAY_GUARD_MODE=warn`** (рекомендуемый / daily Safe) | Только предупреждения в JSONL; **HTTP 413 не бывает** |
| **`block`** | 413 `relay_context_guard_blocked` при `soft_block` / `hard_block` (тело > max / hard, messages, workflow-combo) |

Оценка размера — **char-based** (`chars/4` ≈ токены). На tool-heavy payload соотношение может быть ~1.9 chars/tok → текущие «мягкие» потолки могут пропускать тело шире реального окна модели. Точные `usage.prompt_tokens` / `timings.prompt_n` из ответа upstream в JSONL **пока не парсятся** (лежат в `preview` / `body_raw`).

⚠ **Уточнение 2026-07-22:** эндпоинт `POST /v1/chat/completions/input_tokens` **реально существует** в llama.cpp server (подтверждено официальным `tools/server/README.md`) — точный подсчёт входных токенов через него работает; не отключать/не считать несуществующим (ранняя версия этого разбора ошибочно утверждала обратное). Не работает он для DeepSeek/облачных провайдеров — это фича конкретно llama.cpp.

Guard смотрит уже **forwarded** (после compress) body — для защиты окна модели это верно; исходный bloat в `request.*` / `body_raw` при активной компрессии **не сохраняется** отдельной метрикой (известное ограничение: нет пары `request_original` / `request_forwarded`).

---

## Стриминг (`stream: true`)

1. По умолчанию релей **проксирует SSE** байт-в-байт: ответ клиенту — **HTTP/1.0**, **`Connection: close`**, без **`Content-Length`** и без ручного `Transfer-Encoding: chunked` (chunked ломал разбор в Cursor).
2. Откат к полной буферизации: **`KILO_RELAY_BUFFER_STREAM=1`**.

---

## Лог релея (`logs/kilo_relay.jsonl`)

1. При **`KILO_RELAY_FULL_BODY=yes`** (дефолт скрипта — полный body) в запись попадают тела запроса/ответа — следите за **размером файла** и **PII**. Для повседневного daily обычно выставляют `KILO_RELAY_FULL_BODY=0`.
2. `GET /models` и прочий не-chat трафик пишутся тем же форматом (засоряют статистику токенов) — учитывать при разборе.
3. Стартовый баннер: блок `=== kilo_proxy_relay: режим текущего запуска ===` (`compress.*`, guard thresholds, effective upstream).

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

Между **local** и **off**: `role: system` **не** заменяется; из текста вырезается вторичный XML; список tools не сужается (если нет allowlist); по умолчанию ужимаются descriptions tools и чистятся descriptions в `parameters` (`KILO_RELAY_CLOUD_BUDGET_*`).

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
| **Релей** | Base URL → релей. При `cloud_budget` и пустом `KILO_RELAY_UPSTREAM` → vsegpt (или `CLOUD_DEFAULT_UPSTREAM`). Альтернатива: **DeepSeek preset** |
| **Сжатие** | **`SLIM_MODE=cloud_budget`**: strip XML, без stub system; опционально ужать tools |
| **Rules / MCP / история** | Короткие; только нужные MCP; новый чат на пакет работ |

#### C. Локалка через релей

| | |
|---|---|
| **Endpoint** | Релей → LM Studio `:1234` или llama.cpp `:8080` (`KILO_RELAY_UPSTREAM`) |
| **Rules** | Короткий набор; для Kilo — не полагаться на Cursor-strip |

---

## Известные ограничения (на 2026-07-21)

| ID | Суть | Статус |
|---|---|---|
| C1 / C2 | Strip/allowlist под Cursor; на Kilo без явного `SLIM_MODE`/allowlist — риск сломать tools | Документировано; фикс regex/allowlist — отдельная задача |
| R1 / R3 | Нет `request_original` vs forwarded; usage/timings не парсятся в JSONL | Открыто |
| R5 | `chars/4` неточен в обе стороны | Открыто |
| H2 | Char-пороги daily могут быть слишком permissive для 64k | Пересчёт в Start — в очереди |
| X1 | `/v1/chat/completions/input_tokens` не существует | Не реализовывать как «есть у llama.cpp»; брать usage из ответа или `/tokenize` |
| UTF-8 stdio | Краш стартапа на cp1252 | ✅ Исправлено в `kilo_proxy_relay.py` |
| DeepSeek routing | Preset + auth/model rewrite | ✅ В `kilo_proxy_relay.py` + Start `-UseDeepSeek` |
| C3 / H3 | `/props` fallback; расширенный clear env при смене профиля | ✅ В `Start-KiloRelayDaily.ps1` |

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
