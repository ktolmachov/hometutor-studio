# ADR-021a: Audit architecture lifts — amendment to ADR-021

**Статус:** Accepted (архитектурная позиция; не имплементировано в этом пакете)  
**Дата:** 2026-05-17  
**Связано с:** ADR-021 [`doc/adr_021_smart_router_rag_modes.md`](adr_021_smart_router_rag_modes.md), ADR-020 (SSR), ADR-014 (LLM resilience), ADR-019 (god-module split)  
**Скоуп этого документа:** только текстовые dispositions и границы будущих пакетов. **Не** задаёт изменений `KNOWN_RETRIEVAL_MODES`, defaults, профилей, эндпоинтов или хранилищ до отдельного execution-пакета.

---

## Контекст

Аудит (раздел F) вынес на отдельный горизонт набор улучшений («architecture lifts»), сознательно не включённых в пофазную реализацию ADR-021 Phases 1–5. Без явного ADR-021a возможны два риска: (1) тихое внедрение решений без единого SSoT, (2) смешение **retrieval routing** с **Smart Study Router (SSR)** или с tutor orchestration.

Как и в ADR-021 § boundary clarification: **routing** здесь означает выбор retrieval mode / profile composition / graph augmentation для RAG-пайплайна, а не педагогический SSR (`app/smart_study_router.py`) и не `orchestrator_router.py`.

---

## Решение (объединяющее)

ADR-021 остаётся базовым решением по Fast/Hybrid/Graph-aware profiles и bounded global analytics. **ADR-021a** дополняет его таблицей dispositions ниже и фиксирует anti-goals + измеримый горизонт внедрения.

Любой **Accepted** здесь означает: направление согласовано; реализация идёт отдельным backlog-пакетом с собственным write-set и DoD.  
**Deferred** означает: решение принимаем концептуально, но срок и форма упакованы во follow-up после prerequisite (ADR phase или инфра eval).  
**Rejected** означает: противоречит принятым инвариантам или создаёт двойной RAG-стек без компенсирующей ценности.

---

## Диспозиции audit lifts

| Lift | Disposition | Rationale / package boundary |
|------|:-----------:|------------------------------|
| **A1. Явное разделение retrieval-router ↔ profile resolver** | **Accepted** (impl **Deferred**) | Router решает *когда* и *какой контур* режима/оверрайдов применять; профиль резолвит статическое сопоставление product label→`PipelineOverrides`/параметры. Граница модулей: без новых «god routers» поверх существующих `pipeline_runner`/`pipeline_steps`/`retrieval_strategies`. Реализуется только с обновлением `QueryContext.trace` контрактов согласно ADR-021 (`retrieval_routing` и др., когда они появятся в коде). |
| **A2. Слой decorators вокруг стратегий retrieval** | **Accepted** (impl **Deferred**) | Тонкие декораторы/composition wrappers вокруг зарегистрированных билдеров `STRATEGY_REGISTRY` допустимы для cross-cutting наблюдаемости, тайминга или единых guardrails до/после retrieve **без** дублирования второго пайплайна. Запрещено вводить параллельный registry вне `app/retrieval_strategies.py`. |
| **A3. Профили как YAML/TOML assets под репозиторий** | **Deferred** | Сначала стабильный кодовый/registry контракт `KNOWN_PROFILES` и валидация; внешние файлы — после того, как схема профиля зафиксирована и покрыта тестами синхронизации. Путь данных: версионируемые assets в repo (не user-writable SQLite) + явный loader через `config.py`/settings только в будущем пакете. |
| **A4. Endpoint `/debug/route` (read-only наблюдаемость)** | **Deferred** | Полезно для MoT #10 и US-12.7/12.10, но должно быть **opt-in/admin**, не часть learner UI. Выдаёт решение retrieval routing + effective profile/overrides без побочных эффектов. Реализуется в `app/routers/*`, не в `app/api.py`; требует `doc/api_reference.md` + тест контрактов. |
| **A5. `/ask?dry_run=true` или эквивалент в теле запроса** | **Deferred** | Возвращает план шагов, классификацию, выбранные overrides и фрагмент trace **без** полного генеративного пути или с явным «short-circuit» по контракту — отдельный пакет, чтобы не нарушать guardrails/стоимость LLM по умолчанию. Расширение `AskRequest` в [`app/api_requests.py`](../app/api_requests.py). |
| **A6. Graph-aware shadow-mode (dual-run метрики)** | **Deferred** | Сравнение baseline retrieval vs graph expansion по offline/latency/recall-хелперам **не** должно менять пользовательский ответ по умолчанию в первой итерации. Связано с уже существующими graph eval скаффолдами (`tests/test_graph_*`, см. ADR-021 § current state). |
| **A7. Политика устойчивости retrieval-router (circuit breaker / backoff)** | **Deferred** | Базово опираться на ADR-014 для LLM; отдельный breaker для lite-classifier/rules не вводить до метрик падений маршрутизации. Когда понадобится — явные счётчики в `metrics` + деградация к безопасному default mode с trace reason. |
| **A8. Anti-goals + измеримый «final-position» горизонт** | **Accepted** | Зафиксировано в этом документе (см. следующие секции); не требует кода в данном epoch. |

### Примечания по связке с пользовательскими историями

- **US-12.7** — воспроизводимость eval и snapshot/run id: lifts A4–A6 дают технические крючки наблюдаемости; до реализации остаются design-only заготовки в trace-контракте ADR-021.
- **US-12.10** — adversarial trust: `/debug/route` и dry-run снижают «чёрный ящик» для ревью, но должны сохранять разделение от learner-facing режимов.

---

## Anti-goals (явные запреты)

1. Не смешивать ключи trace/metrics между SSR (ADR-020), tutor orchestrator и retrieval routing — повтор принципа ADR-021 boundary.
2. Не добавлять новые имена retrieval mode для продуктовых ярлыков — только профили поверх существующих `KNOWN_RETRIEVAL_MODES` (как §4.1 ADR-021).
3. Не вводить отдельное дерево `app/rag/*` параллельно существующему pipeline (`ADR-021` problem statement).
4. Не использовать сырой двоичный `kg.sqlite` вне задокументированных KG wrappers (ADR-013).
5. Не включать learner-default UI, экспонирующий raw `retrieval_mode` там, где ADR требует product profile labels (см. существующий контракт в `doc/conventions_architecture.md`).
6. Не использовать dry-run или shadow режим как обход guardrails/input validation.

---

## Measurable adoption horizon / KPI (ожидаемые критерии готовности «позиции»)

На горизонте **до завершения реализации deferred lifts** артефакты качества должны позволять:

1. **Наблюдаемость решения routing:** хотя бы один channel (trace key и/или opt-in `/debug/route`) содержит `selected_profile`, `effective_profile`, `effective_graph_augmented`, fallback reason где применимо.
2. **Eval привязка:** любой режим-сравнительный запуск сохраняет run id + config snapshot + git commit когда доступно (уже принято US-12.7; технические точки усиливает A6).
3. **Regression clarity:** падение режима или профиля даёт actionable message без отключения существующих AQE/router gates (не заменять, а добавлять сигнал).
4. **Latency budget:** любой включённый graph uplift не ухудшает p95 худшего режима более чем на заранее записанный SLO-бюджет в будущей SLO задаче (см. текущее замечание ADR-021 про keying latency по query_mode как technological debt для выравнивания).

Целевые **временные** приоритеты (не календарь, а sequencing):  
`A1` → затем ограниченный `A4`/`A5` для доверия → `A6` параллельно eval-инфраструктуре → `A2`/`A3` для чистый registry и assets → `A7` только при данных деградации.

---

## Compliance

Изменений к runtime в рамках пакета **epoch-adr-021a-architecture-lifts-design** не вносилось. Нарушение этого инварианта — триггер re-open см. `re_entry_condition` в `doc/backlog_registry.yaml`.
