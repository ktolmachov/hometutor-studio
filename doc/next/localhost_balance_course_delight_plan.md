# Localhost Balance + Course Delight Loop

> Дата: 2026-05-23 (rev. 2026-05-24 после ревью LLM Provider Router)  
> Статус: product/architecture plan + critical implementation plan для следующего прорыва после очистки backlog  
> Главная цель: превратить локальный запуск из набора продвинутых возможностей в любимый пользовательский ритуал "запусти и учись".

## 0. Glossary and Scope Conventions

- **Primary chat LLM** — LLM, обслуживающий `/ask`, tutor narrative/answer generation и course mission. Все правила fallback и timeout в этом плане относятся **только** к нему. Tutor имеет два слоя: (1) narrative/explanation generation — primary path, подпадает под fallback/timeout политику; (2) quiz, evaluation, scoring внутри tutor — secondary channels (`QUIZ_LLM_*`, `EVALUATE_MODEL`), out-of-scope для Phase 2.
- **Secondary LLM channels** — `QUIZ_LLM_*`, `SSR_LLM_*`, `INGESTION_MODEL`, `LLAMAINDEX_METADATA_FALLBACK_MODEL`, `CLASSIFIER_MODEL`, `REWRITE_MODEL`, `EVALUATE_MODEL`, `EVAL_JUDGE_LLM`. Они **out-of-scope** для Phase 2 fallback; для них действует уже существующий circuit breaker (`LLM_LOCAL_CB_*`).
- **Course folder** — подкаталог `data/docs/<course>/` (например, `data/docs/AI-агенты/`). Не `data/<course>/`. Активный курс ссылается на конкретный путь внутри `data/docs/`.
- **Scope file marker** — каждый файл в "Scope" помечен:
  - *(new)* — создаётся в рамках пакета,
  - *(extend)* — расширяется существующий файл,
  - *(context)* — читается для понимания, не правится.
- **Course candidate heuristic** — подкаталог под `data/docs/`, в котором проиндексировано ≥ 3 файла поддерживаемых форматов. Логика реиспользует существующий учёт документов в `app/course_cache.py` и `app/course_metrics.py`. Эвристику закрепить как чистую функцию `list_course_candidates()` в `app/course_cache.py`.

---

## 1. Контекст

На 2026-05-23 проект дошёл до редкой точки: backlog пустой, основные user stories закрыты, SSR / Mission Control / Course Workspace / Expert Controls уже существуют. Следующий сильный ход — не VPS, не AI Vision L3-L5 и не gamification, а качественный скачок в локальном пользовательском опыте.

Текущий разрыв:

```text
в проекте всё уже есть
→ но пользователь видит набор мощных отдельных возможностей
→ а не один надёжный путь "запустил локально → прошёл учебный цикл → захотел вернуться"
```

Новая продуктовая цель — **баланс**:

- local-first остаётся фундаментом: документы, индекс, learner state, SRS и прогресс лежат локально;
- долгих ожиданий быть не должно: если локальная модель недоступна или слишком медленная, balanced-режим использует быстрый fallback, например `OPENAI_API_BASE=https://openrouter.ai/api/v1`;
- AI должен быть плавно интегрирован: пользователь понимает, какой режим активен, почему ответ быстрый/медленный, и не чувствует технической поломки;
- эталонный локальный цикл должен работать как часы.

---

## 2. Северная Звезда

**Localhost Balance Mode:** пользователь запускает продукт локально, получает честный статус AI-слоя, не ждёт бесконечно локальную модель и проходит полный учебный цикл без ручной сборки сценария.

**Course Delight Loop:** папка с материалами становится локальным курсом, который сам предлагает первый шаг, отвечает с источниками, учит, проверяет, создаёт память и возвращает пользователя завтра ровно туда, где он продолжает двигаться.

Короткая формула:

```text
Папка → курс
Курс → маршрут
Маршрут → сегодняшняя миссия
Миссия → ответ с sources
Ответ → tutor
Tutor → quiz
Quiz → flashcards/SRS
SRS → adaptive next step
Next step → promise на следующую сессию
```

Английская формула для pitch:

```text
Your folder becomes a course.
Your course becomes a plan.
Your plan becomes today's mission.
Your mission becomes quiz + memory.
Your memory becomes tomorrow's next step.
```

---

## 3. Принципы Дизайна

### 3.1 Local-first, not local-pain

Локальность не должна означать ожидание в пустоту. Пользователь выбирает профиль:

Профиль = LLM routing. Источник данных (real vs demo) — это **отдельная** ось `HOME_RAG_DATA_MODE = real | demo`. DEMO_SAFE из первой редакции расщеплён, чтобы не смешивать ортогональные оси.

| Profile | LLM routing | Для кого |
|---|---|---|
| `LOCAL_STRICT` | Только локальные endpoints; cloud fallback запрещён, при недоступности — дружелюбная ошибка | Конфиденциальные материалы, offline |
| `BALANCED` | Primary chat LLM локально, fallback при недоступности/таймауте; secondary LLM channels — по существующему circuit breaker | Основной рекомендуемый режим |
| `CLOUD_FAST` | Primary chat LLM сразу в cloud provider (default: OpenRouter; опционально Yandex AI Studio, DeepSeek direct); индекс, learner state, SRS остаются локально | Демо, слабое железо, нестабильный локальный LLM |

Любой профиль комбинируется с `HOME_RAG_DATA_MODE`:

| Data mode | Эффект |
|---|---|
| `real` | Используется реальный индекс из `data/docs/` |
| `demo` | Подмешивается `demo_data/` для быстрого happy path; флаг безопасен для showcase |

### 3.2 AI объясняет себя без техношума

UI показывает короткий, честный статус. Копи не должно создавать иллюзию, что **контекст** ответа не покидает машину в balanced/cloud — файлы лежат локально, но цитируемые фрагменты передаются LLM.

```text
AI: Local model ready · ответы и контекст локально
AI: Local slow · отвечаю через cloud · файлы и индекс локально · найденные фрагменты отправляются в cloud LLM
AI: Cloud answer mode · файлы и индекс локально · найденные фрагменты отправляются в cloud LLM
AI: Offline strict mode · ничего не уходит в cloud
```

Помимо LLM статуса баннер показывает состояние **embeddings provider** (отдельная ось):

```text
Embeddings: local Ollama ready
Embeddings: cloud OpenRouter · текст индексируемых чанков отправляется провайдеру embeddings
```

Пользователь должен понять:

- куда идёт LLM-запрос (primary chat LLM);
- что **контент** документов передаётся в LLM как retrieved context, даже если файлы лежат локально;
- куда идут embeddings (важно: embeddings отправляют сырой текст чанка провайдеру);
- почему ответ быстрый или медленный;
- что сделать, если локальная модель не запущена.

### 3.3 LLM улучшает опыт, но не держит маршрут в заложниках

Course mission, route selection, due counts, graduation, SRS и adaptive next step должны иметь deterministic/template baseline. LLM делает текст человечнее, но при сбое маршрут остаётся рабочим.

### 3.4 Course is the hero

Курс под ключ должен быть главным вау-маршрутом. LocalRAG не просто отвечает по файлам, а превращает папку курса в управляемую учебную программу.

---

## 4. Target User Journey

### 4.1 First 10 Minutes

```text
1. Пользователь кладёт материалы в data/docs/ML-Course/
2. Запускает .\scripts\local_start.ps1 -SkipPip (флаг -SkipPip — extend существующего скрипта,
   см. Phase 1; при отсутствии флага сейчас pip install выполняется по умолчанию)
3. Readiness gate показывает: stack ready, AI balanced, embeddings ready,
   potential course folders found:
   - data/docs/ML-Course · 18 files · not indexed yet
4. Запускает ingest
5. Ingest summary показывает: course candidates ready:
   - data/docs/ML-Course · 18 files · 421 chunks · ready
6. Открывает Mission Control
7. Видит плитку "Курс": ML-Course · 18 лекций · ready
8. Нажимает "Активировать курс"
9. При необходимости добавляет новый документ в курс прямо из UI
10. Получает today's mission
11. Задаёт первый scoped question
12. Получает answer + sources только из курса
13. Переходит в tutor
14. Проходит quiz по текущему блоку
15. Создаёт карточки
16. Видит adaptive next step и promise на следующую сессию
```

### 4.2 Emotional Outcome

Не "я настроил RAG", а:

> "Моя папка с лекциями стала курсом. Система поняла, с чего начать, дала источники, проверила меня и запомнила следующий шаг."

---

## 4.3 Critical Review: LLM Provider Router Recommendations

Основание ревью: `D:/Downloads/LLM_Provider_Router_home_rag_v2.docx`, текущий `config.env`, `app/config.py`, `app/provider.py`, `tests/test_provider.py`, `.env.example`, а также проверка актуальных model pages OpenRouter/Yandex AI Studio на 2026-05-24.

### Вердикт

Рекомендации из `.docx` полезны как направление, но в текущем виде их нельзя внедрять "одним слоем router поверх всего":

- часть Phase 1/2 уже реализована в коде (`HOME_RAG_LOCAL_PROFILE`, `HOME_RAG_DATA_MODE`, `HOME_RAG_LLM_FALLBACK_*`, CB-aware fallback в `app/provider.py`);
- часть env-переменных из `.docx` дублирует существующие SSoT (`LOCAL_PROVIDER`, `LOCAL_MAIN_MODEL`, `LLM_ROUTER_ENABLED`) и создаёт второй источник истины;
- часть cloud-role переменных в `config.env` сейчас advisory only: Pydantic `Settings` игнорирует лишние ключи, а runtime их не читает;
- Yandex AI Studio реалистичен как OpenAI-compatible provider, но должен быть отдельным optional package после OpenRouter-role registry и cost tracing, а не обязательной зависимостью первого этапа;
- hard timeout в текущем `get_llm()` пока означает read-timeout cap клиента, но не гарантирует автоматический "timeout → fallback retry" на уровне user request. Это главный technical gap.

### Что принять

- Одна локальная daily-driver модель для RTX 4060 Laptop 8GB — правильная стратегия. `qwen2.5-coder-7b-instruct` в LM Studio/Ollama как единая локальная модель хорошо совпадает с ограничением VRAM.
- Ролевое разделение моделей полезно: `fast`, `coding`, `reasoning`, `graph`, `document`, `judge`, `rewrite`, `classifier`.
- Explicit task role лучше auto-router в v1. Автоматическое угадывание intent отложить.
- Observability обязательна: task, provider, model, latency, fallback, usage/cost estimate, validation errors.
- Budget guards нужны до расширения на дорогие cloud-роли.
- Privacy copy должен честно говорить: файлы и индекс локальны, но retrieved chunks уходят в cloud LLM/embeddings, если выбран cloud provider.

### Что отклонить или отложить

- Не добавлять `LOCAL_PROVIDER`, `LOCAL_LLM_API_BASE`, `LOCAL_MAIN_MODEL` как новые runtime SSoT. Уже есть `LLM_API_BASE` / `LMSTUDIO_API_BASE`, `LLM_MODEL`, `QUIZ_LLM_MODEL`, `SSR_LLM_MODEL`.
- Не вводить `LLM_ROUTER_ENABLED=true` без реального router call path. Feature flag создаст иллюзию работающего слоя.
- Не переносить сразу quiz/SSR/ingestion/judge/rewrite/classifier на новый router. Это рискованно для существующих контрактов; сначала primary chat + role registry as data.
- Не коммитить `YANDEX_CLOUD_FOLDER` или конкретные project/folder IDs в tracked `config.env`. Folder ID не секрет в том же смысле, что API key, но это machine/org-specific configuration.
- Не создавать Yandex adapter до отдельного spike: нужен тестовый ключ, проверка streaming/JSON mode, error mapping, rate limits, pricing и модельных URI.
- Не считать справочные цены контрактом. В `config.env` допустимы только комментарии с датой проверки; production должен читать price registry / manual snapshot.

### Фактические несоответствия на 2026-05-24

- `deepseek/deepseek-r1-distill-qwen-32b` на OpenRouter имеет 128K context и 32K max output. Предыдущая правка "32K context" была неверной; `config.env` должен различать context window и output limit.
- `CLOUD_FAST_MODEL`, `CLOUD_CODING_MODEL`, `CLOUD_REASONING_MODEL`, `CLOUD_GRAPH_MODEL`, `CLOUD_DOCUMENT_MODEL` сейчас не влияют на runtime. Они должны быть явно помечены как advisory до появления role registry.
- `cloud_fast` profile в текущем `app/provider.py` использует `LLM_MODEL` на `OPENAI_API_BASE`. Если `LLM_MODEL` остаётся локальным (`qwen2.5-coder-7b-instruct`), `cloud_fast` может отправить неподходящий model id в OpenRouter. Нужен resolver cloud-fast model.
- `primary_chat_fallback_ready()` без explicit `HOME_RAG_LLM_FALLBACK_MODEL` может выбрать `LLM_MODEL`. Поэтому `config.env` должен явно задавать `HOME_RAG_LLM_FALLBACK_MODEL=openai/gpt-4o-mini`.
- `get_llm()` требует `OPENAI_API_KEY` даже для loopback-local primary chat. Для настоящего `LOCAL_STRICT` это нужно исправить: localhost должен принимать dummy key (`lm-studio`) или отдельный `LOCAL_LLM_API_KEY`, как уже сделано для SSR.
- `.env.example` всё ещё содержит `LLM_MODEL=google/gemma-4-e4b`; это нужно исправить на локальный supported id (`qwen2.5-coder-7b-instruct` для LM Studio или `qwen2.5-coder:7b` для Ollama — coder-вариант сохраняет стратегию "одна локальная модель для кода/RAG").
- Soft timeout пока является настройкой/observability intent, а не пользовательским событием в UI. Нужен trace/status path.

### Audit Corrections Status

> **Примечание:** `applied` означает правку в tracked файлах репозитория (`config.env`, `.env.example`, этом плане). Локальный рабочий `config.env` пользователя может содержать другие значения — перед запуском Package A рекомендуется проверить: `LLM_MODEL`, `QUIZ_LLM_MODEL`, `SSR_LLM_MODEL` должны быть `qwen2.5-coder-7b-instruct`; `HOME_RAG_LLM_FALLBACK_MODEL=openai/gpt-4o-mini`; `ENABLE_RERANKER=false` для RTX 4060/8GB.

| Audit item | Status | Where |
|---|---|---|
| DeepSeek context/output distinction: 128K context, 32K max output | applied in repo | `config.env`, this plan |
| `CLOUD_*` variables marked as advisory-only, not runtime | applied in repo | `config.env` |
| `.env.example` default local model changed from `google/gemma-4-e4b` to `qwen2.5-coder-7b-instruct` | applied in repo | `.env.example` |
| `.env.example` three profile blocks: BALANCED (active), LOCAL_STRICT, CLOUD_FAST (commented) | applied in repo | `.env.example` |
| `cloud_fast` resolver prevents local model id on OpenRouter | pending | Package B |
| Timeout-to-fallback retry at primary request boundary | pending | Package C |
| Role registry separates `context_tokens` from `max_output_tokens` | pending | Package D |

### Обновлённая model-policy позиция

| Role | Current recommendation | Status |
|---|---|---|
| local daily-driver | `qwen2.5-coder-7b-instruct` через LM Studio, одна загруженная модель | принять |
| primary fallback / fast utility | `openai/gpt-4o-mini` через OpenRouter | принять, explicit `HOME_RAG_LLM_FALLBACK_MODEL` |
| coding fallback | `qwen/qwen-2.5-coder-32b-instruct` | принять как advisory |
| reasoning | `deepseek/deepseek-r1-distill-qwen-32b` | принять как advisory; 128K context, 32K max output |
| graph / long context | `qwen/qwen3.5-35b-a3b` | принять как advisory |
| document / metadata | `google/gemma-4-31b-it` | принять как advisory |
| Yandex final synthesis / RU fallback | `gpt://<folder>/<model>/latest` via `https://ai.api.cloud.yandex.net/v1` | отложить в отдельный spike |

---

## 5. Implementation Plan

### Phase 1. Balance Profile

**Goal:** сделать режим запуска явным и объяснимым.

**Current status (2026-05-24):** частично реализовано. `app/config.py` уже содержит `HOME_RAG_LOCAL_PROFILE`, `HOME_RAG_DATA_MODE`, `HOME_RAG_LLM_FALLBACK_*`, soft/hard timeout settings и валидаторы. `config.env` теперь явно задаёт balanced fallback на `openai/gpt-4o-mini`. Оставшаяся работа — синхронизировать `.env.example`/docs/readiness и закрыть cloud-fast/local-strict edge cases.

**Scope:**

- `app/config.py` *(extend)* — не добавлять новые дублирующие ключи; проверить тестами текущие валидаторы и добавить только cloud-fast/fallback resolver setting, если он нужен для устранения edge case.
- `config.env` *(extend)* — держать tracked non-secret balanced defaults: `HOME_RAG_LOCAL_PROFILE=balanced`, explicit `HOME_RAG_LLM_FALLBACK_MODEL=openai/gpt-4o-mini`, advisory cloud-role comments с датой проверки.
- `.env.example` *(extend)* — готовые блоки `LOCAL_STRICT`, `BALANCED`, `CLOUD_FAST` + ось `HOME_RAG_DATA_MODE`. Исправить `LLM_MODEL=google/gemma-4-e4b` на локальный supported id (`qwen2.5-coder-7b-instruct` для LM Studio default; `qwen2.5-coder:7b` для Ollama — coder-модель для обоих серверов).
- `scripts/local_readiness.py` *(extend)* — показывать active profile, data mode, fallback readiness, embeddings provider locality.
- `scripts/local_start.ps1` *(extend)* — добавить флаг `-SkipPip`, если он отсутствует; убедиться, что readiness summary печатается даже при skip-pip.
- `README.md`, `doc/quickstart.md`, `doc/user_guide_details.md` *(extend)* — объяснить режимы и явно зафиксировать privacy trade-off (см. §3.2).

**Proposed env (новые ключи помечены NEW; остальные — существующие):**

```env
# NEW — единственный новый axis profile
HOME_RAG_LOCAL_PROFILE=balanced           # local_strict | balanced | cloud_fast
HOME_RAG_DATA_MODE=real                   # real | demo
HOME_RAG_LLM_FALLBACK_ENABLED=true        # выключается профилем local_strict даже если true
HOME_RAG_LLM_FALLBACK_API_BASE=https://openrouter.ai/api/v1
HOME_RAG_LLM_FALLBACK_MODEL=openai/gpt-4o-mini
HOME_RAG_LLM_LOCAL_SOFT_TIMEOUT_SEC=8     # banner переключает копи на "fast fallback active"
HOME_RAG_LLM_LOCAL_HARD_TIMEOUT_SEC=20    # выше — fallback или strict error

# существующие — переиспользуются, новые ключи их НЕ дублируют
LLM_API_BASE=http://127.0.0.1:1234/v1
LLM_MODEL=qwen2.5-coder-7b-instruct
QUIZ_LLM_MODEL=qwen2.5-coder-7b-instruct
SSR_LLM_MODEL=qwen2.5-coder-7b-instruct
LLM_LOCAL_WARMUP=true                     # уже существует
LLM_LOCAL_CB_FAILURES=3                   # уже существует — НЕ переписываем
LLM_LOCAL_CB_RESET_SEC=60                 # уже существует
LLM_LOCAL_CB_WINDOW_SEC=30                # уже существует
```

Все новые ключи единообразно префиксированы `HOME_RAG_` — это снимает разнобой первой редакции. Существующие `LLM_*` остаются неизменными.

**Соотношение с существующим circuit breaker.** Новые soft/hard timeouts работают **поверх** CB, не вместо него:

- CB сейчас открывается после `LLM_LOCAL_CB_FAILURES` подряд за `LLM_LOCAL_CB_WINDOW_SEC` и закрывается через `LLM_LOCAL_CB_RESET_SEC` — это политика **доступности**.
- Soft/hard timeout — это политика **latency** одного запроса: даже при здоровом локальном LLM один долгий запрос не должен заставлять пользователя ждать.
- Если CB открыт → primary chat LLM сразу маршрутизируется на fallback (BALANCED) или возвращает strict-mode error (LOCAL_STRICT). Timeout проверять не нужно.
- Если CB закрыт → запрос идёт локально; soft timeout запускает баннер "fast fallback active", hard timeout прерывает запрос и переключает на fallback.

**Acceptance:**

- readiness output includes profile name, data mode, primary chat LLM target, fallback availability, embeddings provider;
- `LOCAL_STRICT` блокирует cloud fallback и при недоступности возвращает дружелюбную ошибку;
- `LOCAL_STRICT` + non-loopback `EMBED_API_BASE` → readiness выводит blocking error, ingest заблокирован, сообщение объясняет что embeddings отправят raw chunks в cloud; принимается только loopback или `localhost` как `EMBED_API_BASE` в `local_strict`;
- `BALANCED` не падает, если локальная модель недоступна и fallback настроен;
- `CLOUD_FAST` не использует локальный `LLM_MODEL` случайно; resolver выбирает explicit cloud model или падает с понятной конфигурационной ошибкой;
- localhost-local primary chat не требует реального cloud API key в `LOCAL_STRICT`, если endpoint loopback и cloud fallback выключен;
- timeout-логика **не дублирует** CB-логику и описана в `doc/conventions.md` или ADR.

### Phase 2. Provider Fallback Without Pain

**Goal:** убрать бесконечные ожидания **primary chat LLM**.

**Current status (2026-05-24):** частично реализовано. `get_llm()` уже выбирает cloud fallback при CB-open в `BALANCED` и strict error при CB-open в `LOCAL_STRICT`; тесты покрывают эти ветки. Не закрыто: fallback-on-timeout после реального локального read timeout, soft-timeout status event, fallback misconfiguration UX, local strict без обязательного cloud key.

**Explicit scope of fallback policy.** Phase 2 описывает поведение только primary chat LLM (см. §0). Для secondary LLM channels (`QUIZ_LLM_*`, `SSR_LLM_*`, `INGESTION_MODEL`, `LLAMAINDEX_METADATA_FALLBACK_MODEL`, `CLASSIFIER_MODEL`, `REWRITE_MODEL`, `EVALUATE_MODEL`, `EVAL_JUDGE_LLM`) сохраняется текущее поведение и существующий CB. Расширение fallback на эти каналы — отдельный пакет, не входит в этот план.

**Rules:**

- local LLM healthy and fast → use local;
- local LLM unreachable или CB открыт → fallback immediately in `BALANCED`;
- local LLM exceeds soft timeout → UI/status switches to "fast fallback active";
- local LLM exceeds hard timeout → cancel and use fallback (BALANCED) or friendly strict-mode error (LOCAL_STRICT);
- direct cloud LLM clients для **primary chat path** существуют только в `app/provider.py`. Существующие отдельные клиенты для quiz/SSR/ingestion остаются как есть и **не** переписываются в этом пакете.

**Scope:**

- `app/provider.py` *(extend)* — fallback client selection и timeout handling для primary chat LLM.
- `app/llm_resilience.py` или существующий call boundary *(extend, после точного поиска call path)* — если локальный primary chat request падает по timeout в `BALANCED`, выполнить один fallback-call с тем же normalized prompt/messages и записать `fallback_reason=local_timeout`. Не делать это внутри произвольных secondary LLM calls.
- `app/config.py` *(extend)* — fallback settings (см. Phase 1).
- `app/llm_local_health.py` *(extend)* — добавить latency probe; CB остаётся источником истины для доступности.
- `tests/test_provider.py` *(extend)*, `tests/test_llm_local_health.py` *(extend)*.

**Acceptance:**

- provider tests cover: local-ok, local-down-balanced, local-down-strict, local-slow-soft-timeout, local-slow-hard-timeout, fallback-misconfigured, CB-open-balanced, CB-open-strict;
- resilience/call-boundary tests cover: local timeout in balanced retries once on fallback; local timeout in strict returns friendly strict error; fallback timeout/error is surfaced once without loop;
- все новые настройки идут через `get_settings()`;
- API/UI never hang indefinitely on local LLM startup failure или slow generation;
- secondary LLM channels не затронуты регрессионно (smoke по quiz/SSR-тестам).

### Phase 3. AI Status That Users Love

**Goal:** сделать AI-режим видимым, спокойным и понятным.

**Scope:**

- `app/routers/core.py` *(extend)* — handler `/ui/bootstrap` уже здесь ([core.py:46](app/routers/core.py:46)); добавить `ai_mode` и `embeddings_mode` секции.
- `app/api_services.py` *(extend)* — сервисный слой, если bootstrap собирается через сервис.
- `app/ui/llm_local_banner.py` *(extend)* — compact status copy для LLM и embeddings.
- `app/ui/main.py` *(extend)* / Mission Control integration.
- `tests/test_llm_local_banner.py` *(extend)*, `tests/test_bootstrap_parallel.py` *(extend)*.

**Example payload:**

```json
{
  "ai_mode": {
    "profile": "balanced",
    "data_mode": "real",
    "primary": "local",
    "fallback": "openrouter",
    "status": "fallback_ready",
    "privacy_note": "Файлы и индекс лежат локально. Контекст retrieved-chunks передаётся в LLM при ответе — в balanced это локальный LLM или fallback, в cloud_fast — cloud LLM."
  },
  "embeddings_mode": {
    "provider": "local_ollama",
    "status": "ready",
    "privacy_note": "Текст индексируемых файлов отправляется провайдеру embeddings. Сейчас провайдер локальный."
  },
  "llm_roles": {
    "status": "advisory",
    "active_in_runtime": false,
    "note": "Cloud role registry configured for future routing · not active yet",
    "roles": []
  }
}
```

**Acceptance:**

- banner is short and non-alarming;
- strict mode never implies cloud use ни для LLM, ни для embeddings;
- balanced mode честно описывает, что **контекст** уходит к LLM, а файлы остаются локально;
- embeddings-секция отражает реальный target (local Ollama vs cloud);
- **bootstrap latency p95 < 2 s** (measured baseline 2026-05-24: 5046ms — root cause: synchronous LLM health probe blocking response; fix: async/parallel probe with explicit 1s connect timeout, non-blocking response path; `tests/test_bootstrap_parallel.py` asserts p99 < 2s against mock probe). Move 2 устанавливает hard budget 3 s как trigger для fallback/degrade — это операционный ceiling, не acceptance threshold. Phase 3 acceptance остаётся p95 < 2 s;
- bootstrap остаётся parallel и resilient.

### Phase 4. Course Activation Contract

**Goal:** сделать "папка → курс под ключ" главным эталонным локальным циклом.

#### 4.1 Course Discovery

After ingest/readiness, system identifies course candidates по эвристике из §0 (подкаталог `data/docs/` с ≥ 3 проиндексированными файлами поддерживаемых форматов):

```text
Found course candidates (path · files · chunks):
- data/docs/ML-Course · 18 files · 421 chunks · ready
- data/docs/Algebra   ·  6 files ·  88 chunks · ready
```

**Scope:**

- `app/course_cache.py` *(extend)* — добавить чистую функцию `list_course_candidates()` (см. §0); реиспользует существующий cache layer.
- `app/course_metrics.py` *(context)* — переиспользуется без правки.
- `scripts/local_readiness.py` *(extend)* — optional course candidate summary.
- `app/ui/topics_tab_right_column.py` *(extend)* / Course tile — show ready candidates.
- `tests/test_course_cache.py` *(new)* или extend существующих — покрыть эвристику candidate.

**Acceptance:**

- подкаталог под `data/docs/` с ≥ 3 проиндексированными файлами виден как course candidate;
- порог настраиваемый через `HOME_RAG_COURSE_CANDIDATE_MIN_FILES` (default 3);
- пустой индекс даёт чёткий next action: "положите ≥ 3 файла в `data/docs/<имя курса>/` и запустите ingest";
- no LLM call required для discovery.

#### 4.2 One-Click Course Activation

Button copy. Числа должны быть консистентны с §4.1 (одна и та же единица для chunks):

```text
Активировать курс
18 файлов · 421 chunk · ~7 дней плана
```

Если хочется человекочитаемой метрики вместо chunk — выбрать одну из двух (но **не смешивать** в одном UI):

```text
18 файлов · ~7 дней плана · 23 темы (concepts)
```

Решение по метрике зафиксировать в DoD пакета и единообразно тиражировать в discovery, cockpit, mission.

After activation:

- active study scope is set;
- scoped retrieval uses only course documents;
- flashcards get `course:<id>` tags;
- adaptive plan receives course context;
- Mission Control shows active course chip.

**Scope:**

- `app/ui/study_scope.py` *(extend)* — `get_active_scope()` уже есть ([study_scope.py:46](app/ui/study_scope.py:46)); добавить курс-aware activation flow.
- `app/ui/topics_tab_right_column.py` *(extend)*
- `app/ui/course_cockpit.py` *(extend)*
- `tests/test_study_scope.py` *(extend)*
- `tests/e2e/course_scope_activation.spec.ts` *(extend)*
- `tests/e2e/course_scope_query_filter.spec.ts` *(extend)*
- `tests/e2e/course_scope_deactivation.spec.ts` *(extend)*

#### 4.3 Course First Mission

Activation should end with a mission, not a settings screen.

Example:

```text
Сегодня: Лекция 1 — основы градиентного спуска
Почему: это prerequisite для 6 следующих тем
Сделать:
1. Получить краткий ответ с источниками
2. Пройти 1 mini-quiz
3. Создать 5 карточек
```

**Scope:**

- `app/ui/course_cockpit.py` *(extend)*
- `app/ui/course_prepare_view.py` *(extend)*
- `app/adaptive_plan.py` *(extend)*
- `app/smart_study_router.py` *(extend)*
- `app/course_metrics.py` *(extend)*

**Acceptance:**

- mission appears immediately after activation;
- mission has one primary CTA;
- mission has deterministic fallback copy (LLM может улучшить, но не блокирует появление миссии);
- LLM enrichment респектит primary chat fallback из Phase 2.

#### 4.4 Add Documents To Active Course From UI

Course Workspace must be a living workspace, not a static folder snapshot. A learner should be able to add a new lecture, article, homework PDF, markdown note or transcript to the active course without leaving the browser.

UI copy:

```text
Добавить материал в курс
PDF, MD, TXT, DOCX, HTML · сохранится в data/docs/<active-course>/ · после индексации войдёт в ответы, quiz и карточки
```

Happy path:

```text
Upload file in Course Cockpit
→ sanitize filename and resolve target = data/docs/<active-course>/
→ save file
→ run safe partial ingest / mark reindex needed
→ refresh course scope source_paths
→ update course candidate counts
→ update today's mission and next step
```

This is deliberately different from существующий Flashcards upload (`scope="upload"` в [app/flashcard_service.py:142](app/flashcard_service.py:142)): тот извлекает контент для одной колоды и **не** добавляет файл в постоянную базу знаний. Course upload — persistent corpus growth.

**Empty-state UX (no active course).** Загрузка без активного курса — не глухой dead-end:

```text
У вас нет активного курса. Создайте курс из этого файла:
[Создать курс «<filename без расширения>»]  → создаёт data/docs/<sanitized name>/, сохраняет файл и активирует курс
[Активировать существующий курс] → открывает список candidates
```

**Scope:**

- `app/ui/course_cockpit.py` *(extend)* — upload panel внутри active course.
- `app/ui/course_prepare_view.py` *(extend)* — reindex-needed / refreshed artifact state.
- `app/routers/course_upload.py` *(new)* — отдельный router для POST `/course/upload` и POST `/course/create_from_upload`. Регистрируется как и остальные routers через `app/routers/__init__.py`. Защищён `HOME_RAG_API_KEY` так же, как остальные protected endpoints.
- `app/services/course_upload_service.py` *(new)* — sanitize, dedupe suffix, write, trigger partial ingest, course-create-from-file. Изолирует router от ingestion и filesystem.
- `app/ingestion_loader.py` *(context)* — переиспользуется без правки сигнатур.
- `app/course_cache.py` *(extend)* — invalidate course artifact by scope hash after new file; `list_course_candidates()` уже учитывает новый файл после reindex.
- `app/course_metrics.py` *(extend)* — record `course_document_uploaded`, `course_reindex_started`, `course_reindex_ready`, `course_created_from_upload`.
- `tests/test_course_upload.py` *(new)* — filename sanitization, target folder, dedupe suffix, cache invalidation, create-from-upload, API-key guard.
- `tests/e2e/course_document_upload.spec.ts` *(new)* — UI upload → reindex/ready state → scoped answer cites new source.

**Safety and product rules:**

- Supported extensions: `.pdf`, `.md`, `.txt`, `.docx`, `.html`. Прочие — отказ с понятной ошибкой.
- Normalize и sanitize filename: запретить path traversal (`..`, абсолютные пути), скрытые управляющие символы, пустые имена, имена длиннее 200 символов.
- Writes ограничены `data/docs/<course-folder>/`, где `<course-folder>` — это активный курс или вновь созданная директория для `create_from_upload`. `create_from_upload` создаёт директорию первой, затем валидирует запись в неё. Любая попытка записи вне этой директории — отказ. Это закрепляется как unit-инвариант в `tests/test_course_upload.py`.
- Если имя уже существует — детерминированный суффикс `lecture_03 (2).pdf`.
- Endpoint защищён `HOME_RAG_API_KEY` так же, как другие protected REST endpoints; health/bootstrap остаются публичными.
- Upload не блокирует страницу на долгом embedding-run. При медленном индексировании показать:

```text
Материал сохранён. Индексирую в фоне / требуется обновить индекс.
Пока новый файл не войдёт в ответы, но курс уже помнит, что материал добавлен.
```

**Anti-goal carve-out.** §8 anti-goal "No new storage outside documented user-state/cache wrappers" касается **DB / state stores**. Запись пользовательских файлов в `data/docs/<active-course>/` — это product corpus, а не state storage; carve-out зафиксирован в §8.

**Upload/reindex state machine.** Контракт статусов для `/course/upload` и bootstrap polling:

| Status | Meaning |
|---|---|
| `saved_not_indexed` | файл записан на диск, ingest ещё не запускался |
| `indexing_queued` | reindex поставлен в очередь, ещё не начат |
| `indexing_running` | ingest выполняется прямо сейчас |
| `indexing_ready` | файл проиндексирован, вошёл в retrieval scope |
| `indexing_failed` | ingest завершился ошибкой; `failed_files` содержит список |

Bootstrap payload для polling в E2E:

```json
{
  "course_indexing": {
    "course_id": "CourseDelight",
    "status": "indexing_ready",
    "pending_files": [],
    "failed_files": [],
    "last_indexed_at": "2026-05-24T10:00:00Z"
  }
}
```

E2E дожидается `course_indexing.status == "indexing_ready"` с явным таймаутом; не опрашивает произвольные поля.

**Acceptance:**

- user может загрузить supported document в active course из UI;
- user может создать курс из загруженного файла, если активного нет;
- file persists под `data/docs/<active-course>/`, не только для flashcards;
- readiness/course cockpit показывает, проиндексирован ли новый файл;
- course scope refresh включает новый source после reindex;
- scoped answer цитирует загруженный документ после reindex;
- flashcard generation из active course может включать загруженный документ;
- cache invalidation предотвращает stale course plan;
- endpoint требует `HOME_RAG_API_KEY` если переменная задана;
- no ad hoc SQLite или direct env reads.

#### 4.5 Scoped Answer With Sources

First question:

```text
С чего начать этот курс?
```

Answer must:

- use only course files;
- show course sources;
- explain sequence;
- offer CTA "Учить этот блок".

**Acceptance:**

- sources do not leak outside active course;
- low confidence suggests preparing course or narrowing the topic;
- answer → tutor preserves course scope.

#### 4.6 Tutor Inside Course

Tutor framing:

```text
Продолжаем курс ML-Course.
Сейчас блок 1 из 12: "Градиентный спуск".
```

Tutor receives:

- active course id;
- current block;
- last answer summary;
- source references;
- learner weakness if available.

**Scope:**

- `app/api_requests.py` *(extend)*
- `app/tutor_orchestrator.py` *(extend)*
- `app/tutor_cycle.py` *(extend)*
- `app/tutor_pipeline_contract.py` *(extend)*
- `app/prompts/` *(extend)*
- `app/ui/continuity_bridge.py` *(extend)*
- `tests/test_tutor_orchestrator.py` *(extend)*
- `tests/test_tutor_homework_session.py` *(extend)*

**Invariant:** prompts stay in `app/prompts/`; no prompt hardcoding in UI/router.

#### 4.7 Course Quiz

Quiz copy:

```text
Проверить блок: "Градиентный спуск"
5 вопросов · по материалам курса · 3 минуты
```

After completion:

- mastery updates;
- misconceptions affect adaptive plan;
- weak answers can become flashcards.

**Scope:**

- `app/quiz_scoped.py` *(extend)*
- `app/ui/scoped_quiz.py` *(extend)*
- `app/learner_state_scope.py` *(extend)*
- `tests/test_learning_plan_micro_quiz.py` *(extend)*
- `tests/e2e/course_learning_wave_smoke.spec.ts` *(extend)*

#### 4.8 Course Flashcards / SRS

Flashcard CTA:

```text
Создать карточки из текущего блока
5 карточек · tagged course:ml-course · due завтра
```

**Scope:**

- `app/flashcard_service.py` *(extend)*
- `app/course_metrics.py` *(extend)*
- `app/ui/scoped_quiz.py` *(extend)*
- `app/ui/flashcards_generate_view.py` *(extend)*
- `tests/e2e/flashcards_course_generation.spec.ts` *(extend)*

**Acceptance:**

- active course source works from cockpit;
- generated cards are tagged by course;
- due count and progress can be filtered by active course.

#### 4.9 Adaptive Next Step

Route rules:

- overdue cards → review first;
- failed quiz → tutor/gap repair;
- block mastered → next block;
- user returns after absence → recovery soft landing.

**Scope:**

- `app/smart_study_router.py` *(extend)*
- `app/ui/graduation_overlay.py` *(extend)* — текущий дом graduation-логики после AR-2026-04-29-004 (отдельный `app/course_graduation.py` был сознательно удалён, ре-создавать **нельзя**).
- `app/warmup_planner.py` *(extend)*
- `app/adaptive_plan.py` *(extend)*
- `app/ui/course_cockpit.py` *(extend)*
- `tests/test_course_cockpit.py` *(extend)*
- `tests/test_course_graduation.py` *(extend)* — регрессия на `app/ui/graduation_overlay.py`, как зафиксировано в самом тестовом модуле.
- `tests/test_warmup_planner.py` *(extend)*

**ADR reference.** AR-2026-04-29-004 (см. [`doc/adr.md`](../adr.md)) фиксирует, что graduation-логика живёт в `app/ui/graduation_overlay.py`. Любая попытка вынести её обратно в отдельный сервисный модуль требует новой ADR.

**Acceptance:**

- SSR respects active course;
- explanation answers "why now";
- route works without LLM enrichment;
- `app/course_graduation.py` не создаётся; existing UX (overlay + course-modules) расширяется.

#### 4.10 Promise For Next Session

End-of-session promise:

```text
На следующей сессии продолжим:
Лекция 2 — регуляризация
Сначала 4 карточки, потом короткий quiz
```

**Surface ownership (без двойного рендеринга):**

- `app/ui/resume_cards_tutor.py` *(extend)* — **единственный renderer** карточки promise. Логика layout/CTA только здесь.
- `app/ui/mission_control.py` *(extend)* — **observer**: вставляет уже отрендеренный компонент в свой layout, не дублирует разметку.
- `app/course_cache.py` *(extend)* — persistence promise + invalidation по scope hash.

**Scope:**

- `app/course_cache.py` *(extend)*
- `app/ui/resume_cards_tutor.py` *(extend)* — renderer
- `app/ui/mission_control.py` *(extend)* — observer
- `tests/test_course_cockpit.py` *(extend)* — promise persistence assertions
- `tests/test_resume_cards_tutor.py` *(new или extend)* — render contract

**Acceptance:**

- promise persists локально;
- promise invalidates когда course scope hash меняется;
- next launch surfaces promise до generic suggestions;
- единственный визуальный компонент promise — из `resume_cards_tutor.py`; mission_control не реализует свой layout для promise.

### Phase 5. Ingest Without Fog

**Goal:** make ingest feel like progress, not terminal noise.

After ingest:

```text
Indexed 3 files
Reused cache for 2 files
Added 148 chunks
Embeddings: local Ollama · status: ready · last call 142 ms
Course candidates (≥ 3 files in data/docs/*):
- data/docs/ML-Course: ready
Next: open http://127.0.0.1:8501 and activate your course
```

Если embeddings провайдер медленный или недоступен — summary честно об этом скажет (не молчит):

```text
Embeddings: local Ollama · status: slow (> 5 s/чанк) · советуем перейти на cloud embeddings
Embeddings: local Ollama · status: unreachable · ingest прерван
```

**Scope:**

- `ingest.py` *(extend)* — final summary block.
- существующие ingestion summary helpers *(extend, если есть)*.
- focused ingestion tests *(extend)*.

**Constraint:** избегать broad ingestion refactor. Это только summary/clarity + embeddings state.

### Phase 6. First Learning Loop Golden Test

**Goal:** make delight measurable.

New command (add to `package.json`):

```powershell
npm run local:course-loop
```

Suggested test:

```text
tests/e2e/local_course_delight_loop.spec.ts
```

Scenario (един, без "или"-ветвлений):

1. Start isolated e2e stack с пустым learner state.
2. Seed small course: положить **ровно три файла** — `lecture_01.md`, `lecture_02.md`, `syllabus.md` — в `data/docs/CourseDelight/` (из фикстуры). Три файла гарантируют threshold `HOME_RAG_COURSE_CANDIDATE_MIN_FILES=3` и позволяют шагу Activate course пройти до загрузки `lecture_03.md`.
3. Запустить ingest для трёх файлов (или использовать pre-built index, который содержит **только** эти три файла — критично для теста upload).
4. Open UI.
5. Activate course.
6. Проверить course chip / cockpit / daily mission на трёх seed-файлах (две лекции + syllabus).
7. Upload `lecture_03.md` из фикстуры через UI.
8. Дождаться reindex-ready state (polling по статусу в bootstrap; таймаут E2E задаётся явно).
9. Ask scoped question, ответ на который требует именно `lecture_03.md`.
10. Assert: sources только из курса **и** включают `lecture_03.md`.
11. Bridge в tutor.
12. Run scoped quiz по блоку, связанному с `lecture_03.md`.
13. Create flashcards from course.
14. Check course due/progress.
15. Check adaptive next step.
16. Check next-session promise.

**LLM в E2E.** Тест не зависит от cloud LLM:

- primary chat LLM мокается как **echo model over retrieved context**: если retrieved context содержит `lecture_03.md` → stub возвращает ответ с цитатой `lecture_03.md`; если не содержит → stub возвращает `"NO_LECTURE_03_IN_CONTEXT"`. Stub не генерирует цитаты самостоятельно.
- E2E assertion проверяет не только UI-sources, но и retrieval trace: `retrieval.final_context.source_paths` должен содержать `data/docs/CourseDelight/lecture_03.md`; все source paths должны начинаться с `data/docs/CourseDelight/`.
- balanced provider behaviour покрывается unit-тестами Phase 2 отдельно;
- E2E проверяет UX-цепочку и реальный reindex, **не** генеративное качество.

**Acceptance:**

- тест проходит в deterministic offline mode без cloud;
- pre-seeded index содержит только `lecture_01.md` + `lecture_02.md` + `syllabus.md` — это инвариант теста (если seed уже содержит `lecture_03.md`, тест должен падать как мисконфигурация);
- assertion на источник `lecture_03.md` ловит регрессию upload→reindex pipeline;
- balanced provider behavior моделируется отдельно на unit level (см. Phase 2 acceptance).

### Phase 7. Local Control Center

**Goal:** one compact trust snapshot.

Example:

```text
Stack: API OK, UI OK
Data: 4 docs, 892 chunks · data/docs/
AI: local slow, fallback ready (primary chat)
Embeddings: local Ollama ready
Course: ML-Course active (data/docs/ML-Course), mission ready
Learning loop: 3 questions, 1 quiz, 5 cards due
```

Start as CLI:

```powershell
.\.venv\Scripts\python.exe scripts/local_status.py
```

**Scope:**

- `scripts/local_status.py` *(new)* — readonly snapshot, source of truth — `/ui/bootstrap` + readiness helpers.
- `tests/test_local_status.py` *(new)*.

Later it может feed Mission Control как observer ([resume_cards_tutor.py](app/ui/resume_cards_tutor.py)-style: один renderer, mission_control только подключает).

---

## 6. Definition of Done

### Product DoD

- A new user can launch localhost mode and see what to do next.
- Local model slowness does not trap the user in a long wait in balanced mode.
- User sees an honest AI status и embedding status; privacy note явно говорит о retrieved context.
- Course activation immediately produces a mission с детерминированным baseline.
- Active course can receive new persistent documents from UI;
  user без active course может создать курс из загружаемого файла.
- The full course delight loop is documented и протестирован golden E2E.
- The user can stop after a session and return to a meaningful promise (один renderer).

### Engineering DoD

- Config only through `app/config.py`; новые ключи только под префиксом `HOME_RAG_*`.
- **Primary chat LLM** clients только через `app/provider.py`. Secondary LLM channels (quiz/SSR/ingestion/llamaindex/classifier/rewrite/evaluate/judge) остаются на текущей инфраструктуре и **не** мигрируются в этом пакете.
- Prompts only in `app/prompts/`.
- Course state persists через existing state/cache helpers; no ad hoc SQLite.
- Course document upload sanitizes filenames, writes only to `data/docs/<course-folder>/` (active course or newly created sanitized folder from `create_from_upload`), invalidates stale course artifacts; endpoint защищён `HOME_RAG_API_KEY`.
- Soft/hard timeout politiku **не** дублируют существующий `LLM_LOCAL_CB_*`; разделение описано в Phase 1 и зафиксировано в conventions или ADR.
- `app/course_graduation.py` НЕ создаётся (см. AR-2026-04-29-004). Graduation остаётся в `app/ui/graduation_overlay.py`.
- Promise UI рендерится в одном компоненте (`app/ui/resume_cards_tutor.py`); `app/ui/mission_control.py` его только подключает.
- Router logic остаётся deterministic при LLM enrichment failure.
- E2E golden path детерминирован, не зависит от cloud LLM, проверяет реальный upload→reindex→scoped answer pipeline.
- Docs updated: `README.md`, `doc/quickstart.md`, `doc/user_guide.md`, `doc/user_guide_details.md`, `doc/changelog.md`.

### Test Bundles

Focused tests by phase:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_provider.py tests/test_llm_local_banner.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_study_scope.py tests/test_course_cockpit.py tests/test_course_graduation.py -q
npm run test:e2e:smoke:course-scope
npm run local:course-loop
```

Final doc/agent checks:

```powershell
.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py
.\.venv\Scripts\python.exe scripts/check_llm_context_gate.py
```

---

## 7. Recommended Sequencing

1. **Balance profile config** — small, foundational, docs included.
2. **Readiness v2** — expose profile, fallback, embeddings и course candidates.
3. **Provider fallback** — remove long waits для primary chat LLM.
4. **AI status banner** — make behavior lovable (LLM + embeddings).
5. **Course discovery + one-click activation** (4.1, 4.2) — folder becomes a course.
6. **Course first mission** (4.3) — activation becomes a launch moment.
7. **Course document upload** (4.4) — make the course a living workspace.
8. **Scoped answer with sources** (4.5) — prove retrieval scope works.
9. **Tutor inside course** (4.6) — carry course context into explanation.
10. **Course quiz** (4.7) — scoped check per block.
11. **Course flashcards / SRS** (4.8) — memory tagged by course.
12. **Adaptive next step** (4.9) — route respects course state (без воссоздания course_graduation.py).
13. **Promise for next session** (4.10) — close the loop, один renderer.
14. **Ingest summary** (Phase 5) — закрепить строки readiness/ingest до E2E (E2E ассертит против них).
15. **Golden course loop E2E** (Phase 6) — lock the promise end-to-end.
16. **Local control center** (Phase 7) — trust snapshot for repeated use.
17. **Product docs** (README, quickstart, user guide, changelog) — make discovery frictionless.

Изменение порядка vs. первой редакции: Ingest summary (Phase 5) теперь идёт **перед** Golden E2E (Phase 6), потому что E2E делает assertions против текста readiness/ingest и нуждается в стабильных строках.

---

## 8. Detailed Execution Plan For LLM Router Recommendations

Этот план исправляет рекомендации из `.docx` без big-bang router migration. Каждый пакет даёт проверяемый результат и не ломает текущие каналы quiz/SSR/ingestion.

### Package A. Config Truth And Local-Strict Correctness

**Goal:** сделать `config.env` / `.env.example` честными и убрать ложные runtime-сигналы.

**Files:**

- Modify: `config.env`
- Modify: `.env.example`
- Modify: `app/config.py`
- Modify: `app/provider.py`
- Test: `tests/test_config.py`
- Test: `tests/test_provider.py`

**Steps:**

1. Зафиксировать в `.env.example` те же axis, что в `config.env`: `HOME_RAG_LOCAL_PROFILE`, `HOME_RAG_DATA_MODE`, `HOME_RAG_LLM_FALLBACK_*`, soft/hard timeout.
2. Исправить `.env.example` default `LLM_MODEL=google/gemma-4-e4b` на `qwen2.5-coder-7b-instruct`; Ollama example: `qwen2.5-coder:7b` (coder-вариант, не базовый).
3. Добавить/уточнить тест: `Settings` нормализует profile/data mode и принимает explicit fallback model.
4. Исправить `get_llm()` так, чтобы loopback local primary chat мог работать без реального cloud key в `local_strict` при выключенном fallback. Автоматически подставлять dummy key `lm-studio` при loopback endpoint — **не добавлять новый env-ключ** (любой новый ключ должен быть с префиксом `HOME_RAG_*`, но здесь он избыточен).
5. Добавить тесты: local strict + localhost + no `OPENAI_API_KEY` constructs local client; balanced + fallback enabled + no key returns actionable config error only when fallback needed.
6. Исправить `config.env` `LLAMAINDEX_METADATA_FALLBACK_MODEL=google/gemma-4-31b-it` → `gpt-4o-mini` **(applied 2026-05-24)**. Root cause: `google/gemma-4-31b-it` не является валидным OpenAI model id — LlamaIndex пытается валидировать token limits против него и получает ошибку. Значение должно быть известным OpenAI-совместимым id (`gpt-4o-mini`). Это НЕ то же самое что `LLM_MODEL` — это только metadata alias для LlamaIndex internals.
7. Документировать и проверить OS env precedence: `load_dotenv("config.env")` (строка 13 `app/config.py`) **не переопределяет** уже установленные переменные окружения. Log 2026-05-24 показал `configured_model=google/gemma-4-e4b` потому что OS env имел `LLM_MODEL=google/gemma-4-e4b` (leftover от сессии 2026-05-13). `config.env` не может это перезаписать. Добавить в `scripts/check_env.py` предупреждение: если `LLM_MODEL` содержит `google/` или `openai/` (cloud provider prefix) а `HOME_RAG_LOCAL_PROFILE` = `balanced` или `local_strict`, то выводить WARNING: "LLM_MODEL looks like a cloud model id but profile expects local endpoint — OS env may be overriding config.env".
8. Проверить `SSR_LLM_MODEL`: bootstrap log 2026-05-24 показал предупреждение "SSR effective model is empty". Добавить в `.env.example` явный `SSR_LLM_MODEL=qwen2.5-coder-7b-instruct` в BALANCED-блок.
9. Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_config.py tests/test_provider.py -q
```

### Package B. Cloud-Fast And Fallback Model Resolver

**Goal:** исключить отправку локального model id в OpenRouter.

**Files:**

- Modify: `app/config.py`
- Modify: `app/provider.py`
- Test: `tests/test_provider.py`
- Docs: `.env.example`, `doc/user_guide_details.md`

**Steps:**

1. SSoT для cloud-fast primary model — `HOME_RAG_LLM_FALLBACK_MODEL`. Один ключ обслуживает оба сценария: `BALANCED` fallback и `CLOUD_FAST` primary. Отдельный `HOME_RAG_LLM_CLOUD_FAST_MODEL` **не вводить** в этом пакете; если в будущем потребуется разный provider/model для fallback vs direct cloud — это отдельная ADR + следующий package, не Package B.
2. В `cloud_fast` ветке `get_llm()` использовать cloud model resolver, а не `LLM_MODEL`, если `LLM_MODEL` выглядит локальным.
3. Если cloud model не задан и `LLM_MODEL` локальный, вернуть понятную ошибку с remediation: set `HOME_RAG_LLM_FALLBACK_MODEL=openai/gpt-4o-mini` или set `LLM_MODEL` to cloud id.
   Ошибка должна возникать в `get_llm()` / resolver path, а не как global `Settings` startup failure: приложение должно иметь шанс загрузиться, показать config/readiness и дать пользователю исправить профиль.
4. Добавить тест: `HOME_RAG_LOCAL_PROFILE=cloud_fast`, `LLM_MODEL=qwen2.5-coder-7b-instruct`, `HOME_RAG_LLM_FALLBACK_MODEL=openai/gpt-4o-mini` → client model is `openai/gpt-4o-mini`.
5. Добавить тест: cloud_fast без cloud resolver → `ValueError` with config hint only when constructing primary chat LLM; `Settings` creation still succeeds.
6. Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_provider.py -q
```

### Package C. Timeout-To-Fallback At Request Boundary

**Goal:** превратить hard timeout из "клиент упал" в "balanced retry on fallback once".

**Files:**

- Modify: exact LLM call boundary after search (`app/llm_resilience.py`, query service, or pipeline generation step)
- Modify: `app/provider.py` only if resolver helpers need exposing
- Test: `tests/test_query_service.py` or focused existing resilience tests
- Test: `tests/test_provider.py`

**Steps:**

1. Найти единственный boundary, где primary chat LLM вызывается для `/ask` / tutor / course mission; не ловить timeout внутри low-level provider factory.
2. Обернуть только primary chat calls: catch `httpx.TimeoutException` / provider timeout exception, classify `fallback_reason=local_timeout`.
3. Если profile `balanced` и fallback ready → один retry на fallback LLM, без бесконечного цикла и без повторного retrieval.
4. Если profile `local_strict` → friendly strict error; ничего не отправлять в cloud.
5. Записать trace/status: `primary=local`, `fallback_used=true`, `fallback_reason=local_timeout`, latency local/fallback.
6. Добавить тесты на timeout path с fake LLM.
7. Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_query_service.py tests/test_provider.py -q
```

### Package D. Advisory Role Registry, No Router Migration Yet

**Goal:** сделать cloud-role рекомендации машиночитаемыми без переписывания всех LLM вызовов.

**Files:**

- Create: `app/llm_roles.py`
- Test: `tests/test_llm_roles.py`
- Docs: `doc/user_guide_details.md`, `doc/changelog.md`

**Steps:**

1. Создать immutable role registry с ролями `fast`, `coding`, `reasoning`, `graph`, `document`, `judge`, `rewrite`, `classifier`.
2. **CLOUD_* — advisory only, не парсятся Settings.** Значения для registry брать исключительно из hardcoded defaults в `app/llm_roles.py`. Существующие `CLOUD_*` ключи в `config.env` остаются как они есть (живые env-переменные, явно помеченные комментарным блоком "NOT consumed by runtime yet" в `config.env:35-39`); Pydantic Settings их не объявляет и не читает. Не нужно ни комментировать их, ни конвертировать в чистый doc-блок — текущая форма уже совместима с "advisory". Будущий runtime-override через `HOME_RAG_LLM_ROLE_<ROLE>_MODEL` — отдельный Package (не D).
3. Добавить advisory metadata fields: `input_price_per_m`, `output_price_per_m`, `context_tokens`, `max_output_tokens`, `price_checked_at`, `source_url`.
4. Разделение `context_tokens` и `max_output_tokens` обязательно: DeepSeek case (`128K context`, `32K max output`) должен быть unit-test regression.
5. Не подключать registry к production calls кроме status/readiness output.
6. Тесты: defaults only (no env override — CLOUD_* не парсятся Settings); DeepSeek context `128000`, max output `32768`; Gemma/Qwen context metadata; `source_url` present; `CLOUD_*` env variables ignored by registry.
7. Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_llm_roles.py -q
```

### Package E. Router Observability Before Router Behavior

**Goal:** собрать фактическую статистику до миграции ролей.

**Files:**

- Modify or create: existing LLM cost/metrics helper under `app/`
- Logs: `logs/llm_router.jsonl` or reuse existing `logs/cost_logs`
- Test: focused metrics/cost tests

**Steps:**

1. Проверить existing `app/llm_guards.py` / `log_cost_call` и не создавать второй cost logger, если текущий достаточно расширить.
2. Добавить поля: `task`, `provider`, `model`, `latency_ms`, `fallback_used`, `fallback_reason`, `status`, `estimated_cost_usd`.
3. Для unknown tokens писать `null`, не угадывать.
4. Budget limits оставить advisory/report-only до появления stable usage data.
5. Run focused tests for cost/metrics helpers.

### Package F. Yandex AI Studio Spike As Separate ADR

**Goal:** проверить Yandex provider без риска для текущего OpenRouter/local path.

**Files:**

- Create: `doc/adr/...` or update `doc/adr.md`
- Optional experimental module under `scripts/` only, not production provider path
- No tracked secrets/folder IDs

**Steps:**

1. Проверить OpenAI-compatible chat completions на `https://ai.api.cloud.yandex.net/v1` с model URI `gpt://<folder_ID>/<model_ID>/latest`.
2. Проверить Responses API отдельно; не смешивать Chat Completions и Responses adapter в одном интерфейсе без тестов.
3. Зафиксировать auth, model URI, streaming, structured output, error mapping, rate limits, pricing source.
4. Решить ADR: нужен ли Yandex как production fallback или только optional jurisdictional provider.
5. Только после ADR добавлять production adapter.

### Package G. Future Epic: Actual Router Migration (OUT OF CURRENT PACKAGE)

> **Не входит в текущий delivery scope.** Запускается только после того, как Packages A–F приняты (DoD green) и получен отдельный ADR/approval на миграцию secondary channels. До этого вся работа ниже считается заморожённой.

**Goal:** мигрировать роли постепенно, начиная с low-risk service roles.

**Order:**

1. `rewrite`
2. `classifier`
3. `judge`
4. `document/metadata`
5. `coding/reasoning/graph` as explicit tools
6. never migrate `primary chat`, `quiz`, `SSR`, `ingestion` until their current test bundles are green and observability proves the route is stable

**Acceptance:**

- каждый migrated role имеет explicit task enum, route registry entry, tests for primary/fallback/error, cost trace assertion;
- no direct env reads;
- no prompt hardcoding outside `app/prompts/`;
- no new SQLite stores.

## 9. Verification Sources

- OpenRouter model pages checked 2026-05-24:
  - `openai/gpt-4o-mini`: `$0.15/$0.60`, 128K.
  - `qwen/qwen-2.5-coder-32b-instruct`: `$0.66/$1.00`, 128K.
  - `deepseek/deepseek-r1-distill-qwen-32b`: `$0.29/$0.29`, 128K context, 32K max output.
  - `qwen/qwen3.5-35b-a3b`: `$0.139/$1.00`, 262K.
  - `google/gemma-4-31b-it`: `$0.12/$0.37`, 262K.
- Yandex AI Studio docs checked 2026-05-24:
  - OpenAI-compatible base URL: `https://ai.api.cloud.yandex.net/v1`.
  - Model URI format: `gpt://<folder_ID>/<model_ID>/latest`.
  - Responses API exists separately at `/v1/responses`.

### 9.1 Manual Verification Checklist

Run these after Package A/B/C changes in addition to unit tests:

- `HOME_RAG_LOCAL_PROFILE=cloud_fast`, `LLM_MODEL=qwen2.5-coder-7b-instruct`, `HOME_RAG_LLM_FALLBACK_MODEL=openai/gpt-4o-mini` → primary chat client targets OpenRouter with `openai/gpt-4o-mini`, not the local model id.
- `HOME_RAG_LOCAL_PROFILE=cloud_fast`, no resolvable cloud model → app starts, readiness can render, and primary chat construction returns a clear config error when used.
- `HOME_RAG_LOCAL_PROFILE=local_strict`, loopback `LLM_API_BASE`, no `OPENAI_API_KEY` → local primary chat can construct with local/dummy key; no hidden cloud call.
- `HOME_RAG_LOCAL_PROFILE=balanced`, LM Studio stopped, fallback key/model configured → fallback path is used and status/trace marks `fallback_used=true`.
- `HOME_RAG_LOCAL_PROFILE=balanced`, local read timeout forced → exactly one fallback retry; no infinite retry loop and no fallback for secondary LLM channels.
- Secondary-channel regression: with `HOME_RAG_LOCAL_PROFILE=balanced`, run a quiz/SSR/ingestion request path while local LLM is healthy → trace must show secondary call hits local LLM with `fallback_used=false`; the Phase-2 timeout-wrap must not have leaked into quiz/SSR/ingestion call boundaries.
- Readiness/status output explicitly distinguishes LLM provider locality from embeddings provider locality, including privacy copy for retrieved chunks and raw embedding text.

## 10. Anti-Goals

- No VPS/public deployment in this package.
- No AI Vision L3-L5 serving rollout before eval/data gates.
- No gamification layer until the core course loop is frictionless.
- No new **state / DB** storage outside documented user-state/cache wrappers. *(Загрузка пользовательских файлов в `data/docs/<active-course>/` — product corpus, не state storage; carve-out зафиксирован в §4.4.) Future moves may introduce new documented state wrappers (e.g. session tape в Move 3) only via their own ADR — не в текущем пакете.*
- No upload path that writes outside `data/docs/<course-folder>/`, where `<course-folder>` is either the active course folder or a newly created sanitized course folder from `create_from_upload`. `create_from_upload` must create the course folder first, then treat it as the active-course-folder for write validation.
- No hidden cloud use в `LOCAL_STRICT` ни для LLM, ни для embeddings. `LOCAL_STRICT` с non-loopback `EMBED_API_BASE` должен блокировать ingest с явной ошибкой.
- No LLM-dependent route selection для core course mission.
- No воссоздание `app/course_graduation.py` (AR-2026-04-29-004).
- No fallback wiring для secondary LLM channels (quiz/SSR/ingestion/llamaindex/classifier/rewrite/evaluate/judge) в этом пакете.

---

## 11. Strong Moves Beyond Cleanup

> Раздел добавлен 2026-05-24 после ревью. Это **не** список фичей и **не** расширение Phase 1–7. Это три структурных хода, каждый из которых меняет ощущение продукта целиком, и один сознательно отложенный layout-ход. Каждый move ранжирован по leverage и снабжён явным non-goal, чтобы не подтачивать scope текущих пакетов.
>
> Ключевой принцип: **moves композитны со всем планом выше, не конкурируют с ним.** Move 1 ускоряет первое касание, Move 2 делает "balance" инвариантом, Move 3 даёт основу для всех следующих 12 месяцев работы.

### 11.1 Move 1 — Precompute First Session Artifact

**Leverage:** perceived-10x на cold start. Превращает первое открытие Mission Control из "ждём первый LLM-вызов" в disk read.

**Идея.** Хвост ingest (после Phase 5 summary) уже имеет тёплые caches, локальный LLM, embeddings и retrieval. Использовать этот момент, чтобы для каждого course candidate (см. §4.1) собрать и закэшировать **First Session Artifact**:

```json
{
  "course_id": "ML-Course",
  "scope_hash": "<sha из course_cache>",
  "built_at": "2026-05-24T10:00:00Z",
  "outline_blocks": [{ "id": "b1", "title": "...", "source_paths": ["..."] }],
  "seed_questions": [
    {
      "q": "С чего начать этот курс?",
      "retrieval_trace": { "source_paths": ["..."], "chunk_ids": ["..."] },
      "draft_answer": "<optional, only if local LLM healthy при ingest>"
    }
  ],
  "baseline_mission": { "title": "...", "primary_cta": "...", "deterministic": true },
  "candidate_flashcards": [{ "front": "...", "back": "...", "source": "..." }]
}
```

**Scope:**

- `app/services/first_session_builder.py` *(new)* — pure builder, вызывается из ingest tail; respect profile (`LOCAL_STRICT` → no LLM draft, только retrieval + template baseline).
- `ingest.py` *(extend)* — после summary запустить builder для каждого course candidate; ошибка builder'а не блокирует ingest success.
- `app/course_cache.py` *(extend)* — invalidation: артефакт устаревает по тому же scope-hash, что и promise (§4.10), плюс при `course_document_uploaded` (§4.4).
- `app/ui/course_cockpit.py` *(extend)* — first paint читает артефакт; если артефакт устарел/отсутствует → текущий live-path как fallback.
- `tests/test_first_session_builder.py` *(new)* — детерминированный baseline без LLM, scope-hash invalidation, `LOCAL_STRICT` не уходит в cloud.
- `tests/e2e/local_course_delight_loop.spec.ts` *(extend)* — ассерт что первая mission paint после ingest не делает LLM-вызов (отслеживается через provider stub call counter).

**Acceptance:**

- after ingest, opening Mission Control surfaces mission и seed questions **без единого primary chat LLM call**;
- artifact invalidates при изменении course files (через scope hash) и при upload нового документа;
- `LOCAL_STRICT` + ingest без локального LLM → artifact содержит только outline + retrieval-based seed questions + deterministic mission (без `draft_answer`);
- builder failure не валит ingest и не оставляет частичный artifact (atomic write через temp + rename).

**Non-goals:**

- не заменяет live mission generation на втором и последующих заходах;
- не делает scoped answer pre-computed (только seed questions выставлены как "вот с чего можно начать");
- не превращается в "course graduation" pre-build (см. AR-2026-04-29-004; graduation остаётся в `app/ui/graduation_overlay.py`).

**ADR / Spike:** не требуется. Additive cache layer, использует существующий invalidation pattern из `course_cache.py`.

### 11.2 Move 2 — Latency-Budgeted Surface Contracts

**Leverage:** структурная. Превращает "balance" из имени профиля в системный инвариант, измеримый и enforceable. Делает Phase 7 control center осмысленным.

**Идея.** Каждое user-facing место вызова объявляет latency budget. Call planner выбирает путь, который укладывается в бюджет:

| Surface | Measured baseline | Target | Soft (degrade) | Hard (fallback / strict error) |
|---|---|---|---|---|
| `/ui/bootstrap` | **5046ms** (2026-05-24) | 800 ms | 1.5 s | 3 s |
| `mission_load` (cold) | — | 800 ms | 1.5 s | 3 s |
| `mission_load` (warm via Move 1) | — | 200 ms | 600 ms | 1.5 s |
| `scoped_answer` | — | 2.5 s | 4 s | 8 s |
| `quiz_gen` | — | 2 s | 3 s | 6 s |
| `tutor_next_step` | — | 1.5 s | 3 s | 6 s |
| `flashcard_gen` | — | 1.5 s | 3 s | 6 s |
| `/flashcards/decks` | **3343ms** (2026-05-24) | 500 ms | 1 s | 2 s |

> **Note on measured baselines:** `/ui/bootstrap` 5046ms root cause is a synchronous LLM health probe; fix tracked in `perf-retrieval-init-fix-v1` (singleton) + Phase 3 async probe. `/flashcards/decks` 3343ms is secondary-channel scope; tracked in `perf-flashcards-decks-latency-v1`.

Degradation ladder (общая, не per-surface):

1. **Under target** — best path: local LLM + full rerank (если reranker включён и укладывается в budget) + полный context.
2. **Approaching soft** — degraded: template/baseline где есть, меньший k, skip rerank, обрезанный context.
3. **Exceeded soft** — emit "fast fallback active" status (см. Phase 3 banner copy), продолжить запрос.
4. **Exceeded hard** — cancel и применить fallback (BALANCED) или friendly strict-error (LOCAL_STRICT) по правилам Phase 2.

Каждое решение пишется в observability stream Package E с полями `surface`, `target_ms`, `actual_ms`, `degraded`, `degrade_reason`.

**Scope (post-ADR):**

- `app/latency_budget.py` *(new)* — budget registry (single source of truth для всех surface targets), helper `with_budget(surface, fn)`.
- `app/provider.py`, `app/query_service.py`, `app/tutor_orchestrator.py` *(extend)* — оборачивают primary chat call sites через budget helper.
- Phase 7 `scripts/local_status.py` *(extend)* — показывает rolling p50/p95 per surface и breach count.
- Phase 3 banner *(extend)* — копи "fast fallback active" привязан к soft-breach event, не к произвольному эвристике.
- `tests/test_latency_budget.py` *(new)* — budget breach triggers degrade; hard breach triggers fallback path identical to Phase 2.

**Acceptance:**

- любой primary chat call site объявляет surface tag; lint script отказывает в незатегованных call;
- soft breach видим пользователю через banner; hard breach неотличим от Phase 2 fallback;
- Phase 7 snapshot показывает breach budget как первичную gauge;
- secondary LLM channels (quiz/SSR в legacy режиме) **не** оборачиваются в этом пакете — они остаются на existing CB + ad-hoc timeouts.

**Non-goals:**

- не deadline scheduler: бюджет — это политика degrade, не preemption;
- не отменяет in-flight HTTP calls (cancellation сложна и провайдер-специфична; defer до отдельного спайка);
- не применяется к ingest и любому background path (бюджет — только UX-видимые surfaces);
- не вводит per-user budget tuning (single registry, observable, не configurable из UI).

**ADR / Spike required.** Перед кодом нужна ADR `AR-2026-05-XX-latency-budgets`:

- vocabulary бюджетов (target/soft/hard, единицы, default values per surface);
- кто эмитит trace event и в какой стрим;
- degrade rules per surface (что именно отрезается; не магия в каждом call site);
- отношение с Package E observability и Phase 2 timeout-to-fallback (Move 2 — это generalization Phase 2, не дубль).

**Sequencing:** ADR → MVP на одном surface (`mission_load`, lowest risk, highest visibility) → rollout по остальным surfaces по одному, каждый — отдельным мини-пакетом.

### 11.3 Move 3 — Session Tape As The Unit Of State

**Leverage:** compounding foundation. Удешевляет следующие 12 месяцев фич: rich promise, replay debug, "study trace" share, лучший adaptive_plan signal, multi-device sync без сервера.

**Идея.** Сейчас четыре стора (SQLite learner state, Chroma index, course_cache, SRS) хранят агрегаты. Арка сессии теряется. Ввести **append-only JSONL session tape**:

```text
data/sessions/<session_id>.jsonl   # one event per line, schema versioned
```

Event types (MVP): `session_started`, `mission_loaded`, `question_asked`, `retrieval_completed`, `answer_surfaced`, `quiz_attempt`, `card_created`, `dwell_ms`, `surface_breached_soft`, `surface_breached_hard`, `session_ended`.

Каждое событие содержит: `ts`, `event`, `session_id`, `course_id?`, `surface?`, `payload`. Aggregates (`learner_state`, `course_cache`, SRS) остаются на своих местах и продолжают писаться существующими сервисами — tape **additive**, не replacement.

**Scope (post-ADR):**

- `app/session_tape.py` *(new)* — append-only writer, atomic line append, schema versioning.
- Instrumentation hooks в известных точках: `app/api_services.py`, `app/query_service.py`, `app/tutor_orchestrator.py`, `app/quiz_scoped.py`, `app/flashcard_service.py`, `app/ui/course_cockpit.py` *(extend)*. Каждый hook — одна строка вызова writer; не бизнес-логика.
- `app/session_replay.py` *(new, MVP)* — pure reader, отдаёт events as iterator; используется debug UI и (позже) adaptive_plan.
- `app/ui/session_replay_panel.py` *(new, optional UI)* — debug view "что произошло в последней сессии"; за feature flag.
- `tests/test_session_tape.py` *(new)* — append atomicity, schema validation, reader round-trip.

**MVP boundary.** Сначала только write + reader API; **никаких** readers в production code (promise, adaptive_plan остаются как есть). Это даёт месяц на observation real-world schema, прежде чем будут писаться readers, на которых нельзя ломать схему.

**Acceptance MVP:**

- каждая user-facing сессия пишет валидный tape с обязательным `session_started` + `session_ended`;
- tape выживает crash (последняя partial line отбрасывается reader'ом);
- schema validation в tests; новый event type требует bump `schema_version`;
- no PII beyond what уже в learner_state (no raw answer text без явного opt-in — это критично для будущего share-функции).

**Phase 2 readers (отдельные packages, не входят в Move 3):**

- promise (§4.10) читает tape вместо/в дополнение к course_cache, даёт более точный resume;
- adaptive_plan получает per-block dwell + hesitation signal;
- "Share study trace" — выбираем session, экспортируем sanitized JSONL.

**Non-goals MVP:**

- no server-side sync, no cloud upload (multi-device sync — это user copying folder, intentionally);
- no analytics aggregation pipeline (tape — source of truth, не report layer);
- no schema migration tooling (schema_version + reader-side compatibility пока хватает);
- no replacement existing stores (tape additive; удаление дубликатов — отдельный refactor через год observation).

**Move 3 explicitly amends current Anti-Goal.** Anti-Goal §10 запрещает new state/DB storage в текущем пакете. Session tape (`data/sessions/`) — новый documented state wrapper, разрешён только через отдельную ADR `AR-2026-05-XX-session-tape` и не стартует до её принятия.

**ADR / Spike required.** Перед кодом нужна ADR `AR-2026-05-XX-session-tape`:

- полная schema MVP events + versioning policy;
- privacy policy: что **никогда** не пишется в tape (raw secrets, full answer bodies до opt-in);
- ownership: tape принадлежит session lifecycle, не сервису;
- relationship с existing stores: что остаётся source of truth для чего (mastery — SRS, course readiness — course_cache, session arc — tape).

### 11.4 Move I Won't Make Now — Today-Pane Consolidation

Соблазн: схлопнуть Mission Control + Course Cockpit + Continuity Bridge + Resume Cards в одну панель "Today". Когнитивно правильно: пользователю не нужен mode picker, ему нужно видеть следующие 5 минут работы.

**Почему отложить:**

- Phase 4.10 только что зафиксировала ownership: `resume_cards_tutor` — единственный renderer promise, `mission_control` — observer. Today-consolidation требует нового пересмотра этих границ; делать это до Move 1 (который меняет, **что именно** показывает Today) — переделывать дважды.
- После Move 1 у Today будет другой контент по умолчанию (precomputed seed questions, не "сейчас сгенерирую"). Layout должен следовать из новой content modeli, не наоборот.
- Move 3 даёт session tape — на нём будущий Today сможет показать "вы вчера остановились здесь" с реальной точностью.

**Когда вернуться:** после стабилизации Move 1 + минимум 2 недель real session tape data из Move 3 MVP. Это даст evidence для дизайна Today, а не intuition.

### 11.5 Sequencing Across Moves

| Step | Move | Type | Blocked by |
|---|---|---|---|
| 1 | Move 1 ADR | not required | — |
| 2 | Move 1 delivery | code | Phase 5 ingest summary stable |
| 3 | Move 2 ADR | required | Package E observability shape known |
| 4 | Move 2 MVP (`mission_load` only) | code | Move 2 ADR + Move 1 delivered |
| 5 | Move 3 ADR | required | — (parallel to Move 2 ADR) |
| 6 | Move 3 MVP (write-only, no readers) | code | Move 3 ADR |
| 7 | Move 2 rollout to remaining surfaces | code series | Move 2 MVP green |
| 8 | Move 3 readers (promise, adaptive_plan) | per-feature packages | Move 3 MVP collected ≥ 2 weeks data |
| 9 | Today-pane redesign | design + code | Moves 1–3 stable |

**Rule:** ни один Move не входит в delivery scope текущего "Localhost Balance + Course Delight" пакета (Phases 1–7). Они идут **после**, как named follow-ups, и каждый получает собственный backlog entry в `backlog_registry.yaml`.

---

## 12. One-Sentence Pitch

**hometutor turns a local folder of course materials into a private adaptive course: it starts fast, explains its AI mode honestly, teaches from your sources, tests you, creates memory, and brings you back tomorrow with the right next step.**
