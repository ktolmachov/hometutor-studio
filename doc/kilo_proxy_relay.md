# Локальный релей `kilo_proxy_relay.py`

**Назначение:** HTTP-прокси между Cursor (OpenAI-compatible клиент) и локальным провайдером (LM Studio / `llama.cpp` на `127.0.0.1:1234` и т.п.). Сжимает тело `POST /v1/chat/completions`, пишет JSONL-лог, применяет тот же guard, что и `scripts/_kilo_guard.py`.

**Запуск (из корня репозитория):**

```bash
.\.venv\Scripts\python.exe scripts/kilo_proxy_relay.py
```

Полный список переменных окружения `KILO_RELAY_*` и режимов сжатия — в длинном docstring в [`scripts/kilo_proxy_relay.py`](../scripts/kilo_proxy_relay.py).

**Таймаут к upstream:** `KILO_RELAY_UPSTREAM_TIMEOUT` (секунды, по умолчанию `120`) — единый для буферного и потокового прокси.

---

## Cursor и базовый URL

Базовый URL OpenAI-compatible API в настройках Cursor должен указывать **на этот релей** (например `http://127.0.0.1:8787`), а не напрямую на порт LM Studio — иначе сжатие и guard на границе не выполняются.

---

## Стриминг (`stream: true`)

1. По умолчанию релей **проксирует SSE-поток** байт-в-байт как приходит от upstream: ответ к клиенту идёт как **HTTP/1.0**, **`Connection: close`**, без **`Content-Length`** и без **ручного `Transfer-Encoding: chunked`**. Так совместим разбор ответа в Cursor (раньше ручной chunked давал `Error parsing response` / невалидный JSON).
2. Если после обновления клиента снова появятся артефакты со стримом — включите полную буферизацию: **`KILO_RELAY_BUFFER_STREAM=1`** (ждать весь ответ upstream, как в самом раннем варианте релея).

---

## Лог LM Studio / LlamaV4 (как читать)

1. Сообщение **`cache reuse is not supported - ignoring n_cache_reuse`** — ограничение конфигурации/сборки, не обязательно ошибка; полезен в первую очередь **LCP/prompt cache** (`sim_best`, `f_keep`).
2. **`sim_best = 1.000`** и **`prompt eval` ~десятки ms на 1 токен** при **`task.n_tokens` в сотнях** — префикс промпта переиспользуется из KV, пересчитывается только хвост (типичный «хороший» прогон).
3. Смена модели, первого большого system/user-блока или заметного разъезда начала истории снова делает prompt eval дорогим — это ожидаемо.

---

## Лог релея (`logs/kilo_relay.jsonl`)

1. При **`KILO_RELAY_FULL_BODY=yes`** в запись попадают полные тела запроса/ответа — следите за **размером файла** и **PII** (ключи, переписка, пути).
2. Для повседневной работы можно ослабить логирование (см. env в docstring скрипта).

---

## System stub и имя модели

1. В режиме «local» длинный system Cursor заменяется коротким stub’ом (см. `scripts/_kilo_relay_compress.py`, `KILO_RELAY_CURSOR_SYSTEM_STUB`).
2. В stub заложено: при вопросе о модели можно опереться на поле **`model`** в JSON запроса (например `google/gemma-4-e4b`). Ответ вроде «Gemma 4» и строка из API могут расходиться — при необходимости ужесточите формулировку в stub или в project user rules.

---

## Несколько параллельных запросов

Несколько активных чатов/запросов = несколько **слотов** и **task** в логе Studio; суммарно растёт нагрузка на VRAM и может падать **tok/s**. Ориентир — по строкам `slot` / `task` и времени `eval` в логе.

---

## Обновления LM Studio и `llama.cpp`

После крупного обновления сервера имеет смысл прогнать **один короткий запрос** через релей: иногда меняются детали заголовков или формата SSE. При регрессии временно включите **`KILO_RELAY_BUFFER_STREAM=1`** и сверьте версии.

---

## Системный промпт Cursor и релей (alignment с аудитом)

Платформенный system в Cursor — склейка **идентичности**, **коротких политик** и **операционной документации** (citing tutorial, MCP/browser handbook, terminal manual и т.д.). Облачные большие модели это переваривают; **локальная 8B** несёт фиксированный налог на каждый запрос.

### Три класса контента

| Класс | Примеры в Cursor | Нужен локалке? | Типичная стратегия |
|--------|------------------|----------------|---------------------|
| Core identity | «You are a coding assistant…», `<user_query>` | да | Короткий stub / сжатая формулировка |
| Behavioral rules | tone, tool_calling, часть editing | частично | Оставить суть в stub + user rules без дубляжа |
| Operational docs | `<citing_code>` tutorial, `<mcp_file_system>`, browser playbook, terminal how-to | нет (как статический префикс) | Убрать или не пускать до модели |

### Что делает режим `KILO_RELAY_SLIM_MODE=cloud_budget`

Между **local** и **off**: **`role: system`** от Cursor **не заменяется** (citing / tool orchestration остаются); из текста сообщений вырезается «вторичный» XML (skills, MCP book, terminal manual и т.д., как в local); **список tools не сужается** (если не задан `KILO_RELAY_TOOLS_ALLOWLIST`); по умолчанию **ужимаются** descriptions в схеме tools и **очищаются** описания внутри `parameters` (см. env `KILO_RELAY_CLOUD_BUDGET_*`).

### Что делает режим `KILO_RELAY_SLIM_MODE=local` (дефолт)

При **`KILO_RELAY_LOCAL_KEEP_CURSOR_SYSTEM` не включён** весь длинный **`role: system`** от Cursor **заменяется stub’ом** — вместе с ним из запроса **исчезает целиком** блок типа `<citing_code>…`, `<tool_calling>…`, `<mcp_file_system>…` (всё, что жило в этом system). Это главный **«de-enterprise»** выигрыш релея относительно сырого Cursor.

Остаётся токен-нагрузка во **втором и последующих сообщениях**: `<rules>`, user_info, skills — их режет отдельный набор strip-флагов (см. ниже).

### Карта: фрагмент платформенного промпта → рычаг

| Фрагмент (концептуально) | Релей / Cursor |
|--------------------------|----------------|
| Экономия в облаке **без** замены platform system | **`KILO_RELAY_SLIM_MODE=cloud_budget`**: strip XML в сообщениях + ужимание схемы tools; см. `KILO_RELAY_CLOUD_BUDGET_*` |
| Весь тяжёлый Cursor `system` | **`replace_cursor_system_content`** (local): `KILO_RELAY_CURSOR_SYSTEM_STUB`, отмена: `KILO_RELAY_LOCAL_KEEP_CURSOR_SYSTEM=1` |
| `<mcp_file_system>` + server instructions | **strip** MCP XML в **local** и **cloud_budget**; дополнительно выключите MCP в Cursor |
| `<terminal_files_information>` | **`KILO_RELAY_STRIP_TERMINAL_FILES_INFORMATION_XML`** (в local уже on) |
| `<task_management>` / `todo_write` | **`KILO_RELAY_STRIP_TASK_MANAGEMENT_XML`** (в local уже on); согласуйте с allowlist tools |
| `<available_skills>` | **`KILO_RELAY_STRIP_AVAILABLE_SKILLS_XML`** (в local уже on) |
| Блок `<rules>…</rules>` в user | Опция **`KILO_RELAY_LOCAL_STRIP_CURSOR_RULES=1`** |
| Схемы tools (длинные descriptions) | В local: **`use_local_tool_summaries`**, **`purge_parameter_descriptions`**, allowlist **`KILO_RELAY_TOOLS_ALLOWLIST`** |

Детали имён полей конфига см. `relay_compress_config_from_env` в [`scripts/_kilo_relay_compress.py`](../scripts/_kilo_relay_compress.py).

### Чеклист после аудита

1. **Базовый URL** в Cursor — на релей, не на LM Studio напрямую.
2. **Режим сжатия:** **`SLIM_MODE=local`** для LM Studio; **`SLIM_MODE=cloud_budget`** если релей смотрит в облако и нужна экономия без stub system; не включать `KEEP_CURSOR_SYSTEM` без нужды в local.
3. **Дубли:** не копировать в project user rules длинные tutorial-блоки (citing/MCP), если они уже вырезаны релеем — иначе токены возвращаются.
4. **MCP:** неиспользуемые серверы выключить в Cursor; релей при local всё равно вырезает MCP XML из текста, но меньше сюрпризов на стороне IDE.
5. **Правила репозитория:** если нужен ещё минус к префиксу — `KILO_RELAY_LOCAL_STRIP_CURSOR_RULES=1` (осознанно: теряется часть pinned policy из Cursor rules).
6. **Сверка факта:** в логе старта релея смотреть блок `compress.*` и заголовки `X-Kilo-Relay-*` на ответе.

### Три профиля: полное облако, экономия в облаке, локалка

Один набор **global user rules** редко подходит всем трём; лучше явно переключать режим (профили Cursor, разные окна или хотя бы осознанный выбор перед сессией).

#### A. Облако — полный контекст (качество)

| | |
|---|---|
| **Endpoint** | Провайдер Cursor / OpenAI-совместимый **напрямую**, без `kilo_proxy_relay` |
| **Модель** | Sonnet / GPT-class и т.д. |
| **Rules / MCP** | Можно шире: длинные правила, больше MCP, длиннее история, если бюджет позволяет |
| **Когда** | Сложная архитектура, большие рефакторы, когда важнее качество, чем счёт |

#### B. Облако — экономия бюджета (компромисс)

Та же **класс моделей** (Sonnet / GPT-class), но сознательно **урезаем всё, что раздувает вход**, не отключая облако:

| Рычаг | Действие |
|--------|----------|
| **Релей** | Base URL Cursor → релей. **`KILO_RELAY_UPSTREAM`** можно **не задавать**: при `cloud_budget` релей сам направит на **`https://api.vsegpt.ru`** (или значение `KILO_RELAY_CLOUD_DEFAULT_UPSTREAM`) |
| **Режим сжатия** | **`KILO_RELAY_SLIM_MODE=cloud_budget`** (алиас `budget_cloud`): вырезание MCP/skills/terminal XML из текста сообщений, **без** замены платформенного `system` и **без** обрезки списка tools по умолчанию; опционально ужать descriptions tools (`KILO_RELAY_CLOUD_BUDGET_TOOL_DESC_MAX`, purge schema) |
| **User / project rules** | Короткие; только **дельта** к платформе (язык, стек репо, запреты). **Не** копировать citing/MCP/tool prose — это уже в system Cursor |
| **MCP** | Оставить только то, что реально нужно в этой сессии; лишнее отключить |
| **История чата** | Новый чат на новый пакет работ; не таскать десятки сообщений без нужды |
| **Контекст** | Узкий `@` и read-set (см. `doc/token_safety.md`, `AGENTS.md`); без «закинуть полпроекта» |
| **Модель внутри облака** | Если в Cursor есть более дешёвая/быстрая опция для механических задач — использовать по смыслу задачи |

**Когда:** повседневная работа в облаке при ограниченном бюджете; релей с `cloud_budget` уменьшает объём **сообщений и tools JSON**, не отключая полный платформенный system.

Подробные env для `cloud_budget` — в docstring [`scripts/kilo_proxy_relay.py`](../scripts/kilo_proxy_relay.py) и в [`scripts/_kilo_relay_compress.py`](../scripts/_kilo_relay_compress.py).

#### C. Локалка через релей

| | |
|---|---|
| **Endpoint** | Base URL → **`kilo_proxy_relay`**, upstream → LM Studio / локальный сервер |
| **Модель** | Локальная малая модель |
| **Rules** | Отдельный **короткий** набор (см. прежний раздел); не смешивать с длинными правилами профиля A |

**Почему три, а не два:** профиль **B** даёт экономию **без** смены инфраструктуры на LM Studio и **без** агрессивного stub’а system — за счёт дисциплины правил, MCP и истории.

---

## Связанные документы

| Документ | Содержание |
|---|---|
| [kilo_budget_system.md](kilo_budget_system.md) | Архитектура Kilo budget, guard Tier 1/2 |
| [kilo_budget_gate.md](kilo_budget_gate.md) | CI gate, те же пороги guard |
| [kilo_budget_capture_runbook.md](kilo_budget_capture_runbook.md) | Runbook, в т.ч. запуск релея |
| [`tests/test_kilo_proxy_relay.py`](../tests/test_kilo_proxy_relay.py) | Юнит-тесты: стрим без chunked, обрыв клиента, заголовки |
