# Trust Under Load — Provider Circuit Honesty Plan

Updated: 2026-07-11

Status: all candidates `proposed`. Это не SSoT исполнения — `backlog_registry.yaml`
этим документом не меняется, промоушен волн/пакетов решает владелец.
Owner: product / platform reliability
Source: эволюционный разбор hometutor «Доверие под нагрузкой» (2026-07-11), формат —
[`../presentations/evolutionary_analysis_guide.md`](../presentations/evolutionary_analysis_guide.md).
Полный читаемый разбор:
[`../presentations/evolutionary_analyses/05_trust_under_load.html`](../presentations/evolutionary_analyses/05_trust_under_load.html)
(тот же контент опубликован как HTML-артефакт сессии).

Related docs:
- `doc/backlog_registry.yaml` — SSoT исполнения; кандидаты попадают туда только решением владельца
- [`first_ten_minutes_onboarding_plan.md`](first_ten_minutes_onboarding_plan.md) — detail-plan
  разбора №2; кандидат B2 того плана (честный LLM-баннер) и кандидат A1 этого плана делят
  один корень — оба про то, что недоступность локального LLM недооценена на пользовательской
  поверхности; этот план чинит первопричину (circuit breaker без runtime-питания), тот —
  формулировку одного статического баннера
- [`material_as_product_quality_plan.md`](material_as_product_quality_plan.md) — detail-plan
  разбора №3; боль-якорь того плана (молчаливый promote-skip графа при `graph_llm_probe_ok()
  == False`) — ещё одно проявление того же семейства сбоев local LLM, что и этот план,
  но для отдельного (graph) LLM-getter'а, не primary chat
- hometutor: `docs/architecture.md`, `docs/conventions_architecture.md`, `CLAUDE.md`

## Как использовать этот документ

Каждый пункт ниже — candidate-package с достаточной детализацией, чтобы владелец мог
промоутить его в wave/package `backlog_registry.yaml` или отклонить/отложить с причиной.
Реализация кода происходит в `hometutor` и подчиняется его runtime-правилам: targeted
tests, doc-sync при изменении поведения, никаких попутных рефакторингов вне
согласованного write-set. Все evidence-ссылки проверены на `hometutor@60b55f3` (`149`).

Статусы: `proposed` → `accepted` → `in_progress` → `done` / `declined` / `superseded`.

## Суть разбора

Доверие под нагрузкой — это не «система никогда не подведёт», а «система никогда не
подведёт молча». Provider-слой уже спроектировал правильную архитектуру: три профиля
маршрутизации, circuit breaker с auto half-open, честный бейдж источника ответа. Аудит
нашёл единственный, но глубокий разрыв: у самого нагруженного пути — primary chat —
предохранитель ни разу не подключён к реальному трафику после старта процесса.

---

## Волна-кандидат A: `wave-provider-circuit-honesty` (P0)

**North star (кандидат):** после трёх сбоев подряд на локальном endpoint ни один
следующий запрос в той же сессии не ждёт дольше нескольких секунд перед честным
сообщением — независимо от того, включён ли cloud-fallback.

**Kill switch (кандидат):** если runtime-запись в circuit breaker (A1) начинает открывать
его от единичных не-сетевых ошибок (например, guardrail-отказов или content-ошибок,
ошибочно классифицированных как connection error), что приводит к ложным открытиям на
здоровом endpoint, сузить набор типов ошибок, засчитываемых в breaker, до подтверждённо
сетевых (`_is_connection_error`, уже существующий в `llm_resilience.py:33-35`) — не
убирать сам runtime-путь записи.

### Кандидат A1 — Runtime `record_failure`/`record_success` для primary chat

**Статус:** `proposed`

**Приоритет:** P0 · **Усилие:** малое (интерфейс и паттерн уже существуют в кодовой базе)

**Проблема.** `llm_local_circuit.is_open()` для primary chat читает состояние, которое
пишется **только один раз** — при старте процесса, в daemon-потоке. Реальные HTTP-вызовы
чата (каждый ответ тьютора и Быстрого ответа) никогда не сообщают circuit breaker об
успехе или неудаче. Если локальный endpoint падает в середине сессии, `is_open()`
продолжает возвращать `False` до перезапуска процесса — предохранитель, задуманный как
«не ждать N×timeout против мёртвого endpoint», в этом случае не срабатывает никогда.

**Evidence:**
- `app/api.py:126-170` (`_startup_probe_local_llm` или аналог) — единственный сегодняшний
  caller `record_failure`/`record_success` для этого circuit; запускается один раз в
  daemon-потоке при старте API-процесса.
- `app/provider.py:217-223` (`local_primary_chat_circuit_open`) и `provider.py:432-433`
  (`is_open(local_base_norm)` внутри `get_llm()`) — единственные читатели состояния для
  primary chat.
- Прямая проверка отсутствия записи на реальном трафике:
  `grep -n "circuit" app/provider_openai.py app/llm_resilience.py` → пустой вывод. Ни
  `OpenAI._chat`/`_achat` (`provider_openai.py`), ни `complete_with_resilience`/
  `chat_with_resilience` (`llm_resilience.py:38-118`) не упоминают circuit breaker.
- `app/llm_resilience.py:33-35` (`_is_connection_error`) — уже существующий классификатор
  типа ошибки (отличает «endpoint недоступен» от «ошибка контента/guardrail»); тот же
  классификатор уже используется для выбора cross-base fallback
  (`llm_resilience.py:92-93`) — переиспользуется, не изобретается заново.
- `app/ui/adaptive_plan_llm_explanation.py:111-217` — образцовый паттерн для копирования:
  `is_open()` перед попыткой → `record_failure(circuit_base, error_type=...)` в except →
  `record_success(circuit_base)` при успехе.

**Proposed change:**
1. В `complete_with_resilience`/`chat_with_resilience` (`app/llm_resilience.py`) добавить
   вызов `llm_local_circuit.record_success(base_url)` после успешного
   `llm.complete(...)`/`llm.chat(...)` и `llm_local_circuit.record_failure(base_url,
   error_type=...)` в `except`-ветке — **только когда `_is_connection_error(e)` истинно**
   (не открывать circuit от guardrail/content-ошибок).
2. `base_url` берётся из уже переданного `llm` (через `llm_source_metadata(llm)` /
   `home_rag_llm_api_base`, `provider.py:206-214`), не заново резолвится по настройкам —
   иначе рассинхронизация с тем, какой endpoint реально вызывался.
3. Не менять сигнатуру `complete_with_resilience`/`chat_with_resilience` для вызывающего
   кода — запись в circuit breaker становится внутренней деталью резилиенс-обёртки, как
   уже есть `log_event`/`record_error`.

**Files:** `app/llm_resilience.py`, targeted tests (расширить существующий тестовый файл
резилиенс-слоя новыми кейсами: успех закрывает открытый circuit, connection error
открывает circuit после порога, non-connection error не трогает circuit).

**DoD:**
- После N подряд идущих реальных connection-failures (`N = settings.llm_local_cb_failures`,
  дефолт 3) на местном endpoint `local_primary_chat_circuit_open()` возвращает `True` без
  перезапуска процесса.
- Успешный ответ после восстановления endpoint закрывает circuit (`record_success`).
- Guardrail/content-ошибки не открывают circuit (regression test на
  `_is_connection_error`-фильтр).

**Doc-sync:** `docs/architecture.md` (если там описан provider/circuit flow — добавить,
что circuit теперь runtime-питается, не только startup-пробой).

**Dependencies:** нет — интерфейс (`record_failure`/`record_success`) уже существует и
стабилен, меняется только вызывающая сторона.

---

### Кандидат A2 — Быстрый честный отказ при `balanced` + открытом CB без fallback

**Статус:** `proposed`

**Приоритет:** P0 · **Усилие:** малое–среднее

**Проблема.** Даже после A1 (circuit корректно открывается на реальных сбоях) поведение
`get_llm()` в дефолтной конфигурации (`HOME_RAG_LOCAL_PROFILE=balanced`,
`HOME_RAG_LLM_FALLBACK_ENABLED=false` — оба tracked-дефолты `config.env:67,70`) не
меняется: код только логирует предупреждение и всё равно строит `OpenAI`-клиент на тот
же локальный `api_base` с полным read-таймаутом. Открытый circuit в этой ветке ни на что
не влияет.

**Evidence:**
- `app/provider.py:443-451` — точная развилка:
  ```
  fallback_ready = primary_chat_fallback_ready(s)
  use_fallback = profile == "balanced" and cb_now and fallback_ready
  if profile == "balanced" and cb_now and not fallback_ready:
      logger.warning("balanced_primary_chat_circuit_open_no_fallback_using_local_attempt", ...)
  ```
  — при `use_fallback == False` управление проваливается к строке 472
  (`llm = OpenAI(..., api_base=local_base_norm, **_llm_client_kwargs_local_primary(s))`) —
  тому же мёртвому endpoint, с обычным полным таймаутом.
- `app/provider.py:120-124` (`_primary_local_read_cap_sec`) — текущий read-cap для этой
  ветки: `min(llm_request_timeout, home_rag_llm_local_hard_timeout_sec)`, где
  `HOME_RAG_LLM_LOCAL_HARD_TIMEOUT_SEC=45` (`config.env:76`) — верхняя граница ожидания
  на КАЖДЫЙ запрос, пока circuit открыт.
  `app/provider.py:133-144` (`_llm_client_kwargs_local_primary`) — уже правильно ставит
  `max_retries=0` (нет 3×-амплификации ожидания повторами) — эту часть трогать не нужно,
  проблема только в самом read-таймауте одной попытки.

**Proposed change:**
1. Новый короткий read-timeout специально для «известно нездорового» повтора — отдельная
   настройка (например `home_rag_llm_local_known_unhealthy_timeout_sec`, дефолт в районе
   2–3 секунд — того же порядка, что `DEFAULT_PROBE_TIMEOUT_SEC=1.5` из
   `llm_local_health.py:27`), применяется **только** в ветке `balanced + cb_now + not
   fallback_ready` — обычный путь с закрытым circuit не меняется.
2. Такой быстрый неудачный повтор при закрытии совпадает с обычной семантикой ошибки:
   `answer_question` уже умеет строить `build_safe_fallback_result` (`query_fallbacks.py`)
   при исключении guardrail-слоя — короткий таймаут просто ускоряет попадание в уже
   существующий путь честного отказа, не создавая новую ветку обработки ошибок.
3. Не включать `HOME_RAG_LLM_FALLBACK_ENABLED` автоматически и не менять его дефолт — это
   осознанное решение владельца про privacy/cost (см. `config.env:65` комментарий
   `# HOME_RAG_LLM_FALLBACK_ENABLED=true`), кандидат сокращает только бесполезное
   молчаливое ожидание.

**Files:** `app/config.py` (новая настройка + `.env.example`/`config.env` doc-sync),
`app/provider.py` (`_llm_client_kwargs_local_primary` получает вариант с укороченным
таймаутом для этой ветки, либо новый `_llm_client_kwargs_local_primary_known_unhealthy`),
targeted tests.

**DoD:** при открытом CB и выключенном fallback единичный запрос к мёртвому local
endpoint завершается ошибкой за секунды, не за `HOME_RAG_LLM_LOCAL_HARD_TIMEOUT_SEC`;
при закрытом CB поведение не меняется (обычный полный read-cap).

**Doc-sync:** `.env.example`, `config.env` (новая переменная), `docs/architecture.md`
(если там задокументированы таймауты primary chat).

**Dependencies:** логически усиливается A1 (без runtime-питания circuit почти никогда не
будет открыт вне окна сразу после старта), но реализуем независимо — код развилки уже
существует и сегодня, просто с полным таймаутом.

---

## Волна-кандидат B: `wave-provider-transparency` (P1)

**North star (кандидат):** студент видит источник и задержку ответа на любой поверхности
диалога, не только в «Быстром ответе».

### Кандидат B1 — Бейдж источника LLM в Tutor chat

**Статус:** `proposed`

**Приоритет:** P1 · **Усилие:** малое

**Проблема.** `llm_source_badge_text`/`llm_source_privacy_notice` — уже готовый, честный,
видимый по умолчанию (не за debug-тиром) индикатор «Источник ответа: … · fallback ·
profile · latency» — подключён только к «Быстрому ответу». Tutor chat, основная
поверхность диалогового обучения (петля памяти, [[knowledge_fate_memory_loop_plan]],
разбор №1), не показывает источник ответа вообще, хотя необходимые данные собираются
единым кодом для любого `query_mode`.

**Evidence:**
- `app/ui/helpers.py:181-258` (`llm_source_summary`, `llm_source_badge_text`,
  `llm_source_privacy_notice`, `llm_source_debug_rows`) — переиспользуемые pure-функции,
  принимают тот же `debug: dict | None`, что и любой ответ `/ask`.
- `app/ui/query_tab_answer_section.py:84-89` и `app/ui/query_tab_sidebar.py:11-24` —
  единственные сегодняшние потребители за пределами `debug_panel.py`; оба — поверхность
  «Быстрый ответ», не Tutor chat.
- `grep -n "llm_source" app/ui/tutor_chat*.py` → пусто — рендер tutor-ответа не читает и
  не показывает эти поля.
- `app/query_service.py:359-375` (`_build_generation_model_and_metadata`) — генерирует
  `generation_source_metadata` (`llm_source`, `llm_model`, `llm_api_base`,
  `fallback_used`, `llm_profile`) в общем RAG-assembly пути, используемом и для tutor-, и
  для query-ответов; поле `debug["fallback_used"]`/`"llm_source"` уже присутствует в
  debug-словаре tutor-ответа — не хватает только UI-рендера.

**Proposed change:**
1. Вызвать `llm_source_badge_text(debug)`/`llm_source_privacy_notice(debug)` в модуле
   рендера tutor-ответа (кандидат места: `app/ui/tutor_chat_response_render.py`, тот же
   слой, что уже показывает confidence/latency-подписи Быстрого ответа) — как
   `st.caption`/`st.info`, не за экспертным `st.expander`.
2. Никаких новых вычислений — те же helper'ы, тот же источник данных
   (`st.session_state["last_debug"]` эквивалент для tutor-сессии).

**Files:** `app/ui/tutor_chat_response_render.py` (или ближайший модуль, реально
рендерящий финальный текст tutor-ответа), targeted tests.

**DoD:** после ответа тьютора студент видит ту же строку источника/задержки/fallback, что
и в «Быстром ответе», без нового визуального языка.

**Doc-sync:** `docs/user_guide.md` (если там описан состав tutor-ответа).

**Dependencies:** независим от волны A — использует уже существующие debug-поля
безотносительно того, чинится ли circuit breaker.

---

## Волна-кандидат C: `wave-provider-observability` (P2)

**North star (кандидат):** владелец видит состояние provider-слоя человеческим языком, не
только через grep по JSONL-логам.

### Кандидат C1 — Человекочитаемая панель состояния circuit breaker

**Статус:** `proposed`

**Приоритет:** P2 · **Усилие:** малое

**Проблема/возможность.** `llm_local_circuit.snapshot()` уже возвращает структурированное
состояние всех отслеживаемых endpoint'ов (открыт/закрыт, число сбоев, последний тип
ошибки), но используется только программно для отладки — нет поверхности, где владелец
мог бы увидеть это без чтения кода/логов.

**Evidence:**
- `app/llm_local_circuit.py:147-...` (`snapshot`) — «Read-only view of current circuit
  state, for debugging/observability» — уже задокументирован как предназначенный для
  этого use case, но потребителя нет.
- `app/ui/debug_panel.py:10-158` — существующая debug-поверхность в UI, уже показывает
  `llm_source_debug_rows` (`helpers.py:243-258`) для последнего ответа; естественное
  соседство для добавления секции per-endpoint circuit state (не per-ответ, а текущее
  состояние всех отслеживаемых баз).

**Proposed change:** секция в `debug_panel.py`, рендерящая `snapshot()` построчно на
каждый отслеживаемый `base_url`: состояние (открыт/закрыт), сколько секунд назад открыт,
число сбоев в окне, тип последней ошибки — человеческим языком («локальный endpoint:
открыт 42 с назад, 3 сбоя подряд, тип ошибки: connection refused»).

**Files:** `app/ui/debug_panel.py`.

**DoD:** владелец видит текущее состояние circuit breaker без обращения к логам/коду.

**Doc-sync:** нет (существующая debug-поверхность, новая секция внутри неё).

**Dependencies:** осмысленнее после A1 (иначе показывает почти всегда «закрыт» из-за
отсутствия runtime-питания), но реализуемо независимо.

---

## Рекомендованный порядок реализации

1. **A1** — runtime-питание circuit breaker; без него все остальные пункты либо чинят
   несуществующий сценарий (A2 не имеет смысла без реально открывающегося CB), либо
   показывают вводящее в заблуждение «всегда закрыто» состояние (C1).
2. **A2** — быстрый честный отказ; логически зависит от A1 по эффекту, но код развилки
   можно писать параллельно.
3. **B1** — бейдж источника в Tutor chat; полностью независим от A1/A2, чистое
   UI-расширение уже существующих данных.
4. **C1** — панель состояния для владельца; ставить последним, чтобы показывать
   осмысленное состояние (после A1), а не всегда «закрыто».

## Связанные документы

- [`../presentations/evolutionary_analysis_guide.md`](../presentations/evolutionary_analysis_guide.md) — формат исходного анализа
- [`../presentations/evolutionary_analyses/README.md`](../presentations/evolutionary_analyses/README.md) — индекс серии разборов
- [`../backlog_registry.yaml`](../backlog_registry.yaml) — SSoT исполнения
- [`knowledge_fate_memory_loop_plan.md`](knowledge_fate_memory_loop_plan.md) — detail-plan разбора №1 (петля памяти)
- [`first_ten_minutes_onboarding_plan.md`](first_ten_minutes_onboarding_plan.md) — detail-plan разбора №2 (онбординг)
- [`material_as_product_quality_plan.md`](material_as_product_quality_plan.md) — detail-plan разбора №3 (качество материала)
- [`agent_as_one_button_plan.md`](agent_as_one_button_plan.md) — detail-plan разбора №4 (Agent Coach → UI)
- hometutor: `docs/architecture.md`, `docs/conventions_architecture.md`, `CLAUDE.md`
