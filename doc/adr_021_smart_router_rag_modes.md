# ADR-021: Smart Router RAG modes and bounded GraphRAG analytics

**Статус:** Accepted (architecture decision, not full runtime implementation)
**Дата:** 2026-05-14  
**Принято:** 2026-05-14  
**Источник:** критический разбор внешнего draft ADR `D:\Downloads\ADR-001_ Переход к Smart Router RAG с режимами Fast _ Hybrid _ Graph и отдельным GraphRAG-режимом глобальной аналитики.md`  
**Связанные ADR:** ADR-004, ADR-007, ADR-013, ADR-016, ADR-019, ADR-020  
**Implementation status:** partially implemented. `Accepted` означает, что принята архитектурная граница и направление развития; это не означает, что новые product labels уже являются runtime mode constants или что public API уже расширен.

### Current state (verified 2026-05-15)

| Claim | Truth on master | Anchor |
| --- | --- | --- |
| `KNOWN_RETRIEVAL_MODES = {vector_only, hybrid, bm25_only, doc_then_chunk}` | Implemented | `app/config.py` |
| Default `RetrievalSettings.retrieval_mode = "vector_only"` | Implemented | `app/config.py` |
| `enable_graph_augmented_retrieval`, `graph_augment_max_extra_docs`, `graph_expand_max_hops` | Implemented on root `Settings` (not `RetrievalSettings`) | `app/config.py` |
| `QueryContext.trace["graph_expansion"]` | Implemented (written by `graph_expansion_trace_scope`) | `app/graph_retrieval.py` |
| `QueryContext.trace["retrieval_routing"]` | **Not yet implemented** — proposed as new key by this ADR (§6) | — |
| Bounded graph postprocessor with multi-level fallback | Implemented (disabled / wrong query_type / KG load failure / empty expansion all return baseline nodes) | `app/graph_retrieval.py` |
| `slo_max_p95_latency_ms`, `slo_latency_by_mode` | Implemented, **keyed by `query_mode` (`qa`/`tutor`), not retrieval mode** — see §10 | `app/config.py` |
| `/ask` mode/profile override | **Not yet implemented** in `AskRequest`; internal `PipelineOverrides.retrieval_mode` / `rag_profile` exist but are not API-exposed | `app/api_requests.py`, `app/models.py` |
| `PipelineOverrides.retrieval_mode`, `rag_profile` | Implemented (internal contract) | `app/models.py` |
| `app/knowledge_service.py` facade over JSON + `kg.sqlite` | Implemented; one in-wrapper `sqlite3.connect` in `knowledge_graph_bundle.py` (acceptable, inside the wrapper itself) | `app/knowledge_service.py`, `app/knowledge_graph_bundle.py` |
| Dedicated retrieval-mode router/classifier | **Not yet implemented**. Only `classify_step()` in `pipeline_steps.py` (produces `query_type`, `classify_confidence`, `classify_method`). Unrelated `app/smart_study_router.py` (ADR-020) and `app/orchestrator_router.py` (tutor orchestration) exist and must not be conflated with this router. | `app/pipeline_steps.py` |
| Graph eval scaffolding (baseline, expansion benchmark, gate smoke) | Implemented | `tests/test_graph_*` |
| Fast / hybrid / global-analytics named eval sets per §9 | Not yet present as named datasets | `tests/eval/` |

---

## 1. Контекст

`home-rag_v2` уже вырос из простого Q&A RAG в локального учебного ассистента: FastAPI, Streamlit, CLI и Telegram входят в один learning loop, ответы должны быть связаны с источниками, а retrieval используется не только для ответа, но и для tutor, quiz, spaced repetition, graph expansion и планирования.

В проекте уже приняты важные решения:

- ADR-004 задает общую границу pipeline/factory: новый retrieval path должен встраиваться в существующую сборку, а не создавать второй RAG-стек.
- ADR-007 фиксирует Hybrid Retrieval: BM25 + vector search; hybrid реализован, но не является default `RETRIEVAL_MODE`.
- ADR-013 фиксирует формат knowledge graph: JSON как source of truth, SQLite как производный indexed read layer; поэтому graph-aware retrieval не должен заводить новый primary graph store.
- ADR-016 фиксирует decomposed observability contract; routing/graph decisions должны попадать в существующие trace/metrics поверхности.
- ADR-019 фиксирует границы split для query/graph god-modules; новые graph/query capabilities должны уважать эти ownership boundaries.
- ADR-020 фиксирует Smart Study Router как педагогический next-step router, отдельный от retrieval routing.
- `doc/conventions_architecture.md` уже задает контракт retrieval modes: `vector_only`, `hybrid`, `bm25_only`, `doc_then_chunk` через `app/retrieval_strategies.py`, `KNOWN_RETRIEVAL_MODES`, `QueryContext` и `PipelineOverrides`.
- Graph-augmented retrieval уже существует как опциональное расширение через `app/graph_retrieval.py`, `Settings.enable_graph_augmented_retrieval` и trace `QueryContext.trace["graph_expansion"]`.

Внешний draft ADR правильно называет главный риск: нельзя заменять весь RAG на GraphRAG. Но в исходном виде он предлагает слишком широкий параллельный дизайн: новые `/ask/fast`, `/ask/hybrid`, `/ask/graph` endpoints, отдельное дерево `app/rag/`, отдельное `graph_store.py`, новые feature flags и prompt contracts вне текущих проектных границ. Такая форма противоречит уже принятым конвенциям проекта и создает риск второго RAG-стека рядом с существующим.

Этот ADR принимает основную идею draft ADR, но фиксирует ее в форме, совместимой с текущей архитектурой.

**Boundary clarification (added 2026-05-15).** "Routing" в этом ADR означает решение о retrieval mode / profile / graph-augmentation. Это **не** педагогический next-step router из ADR-020 (`app/smart_study_router.py`) и **не** tutor orchestration router (`app/orchestrator_router.py`). Decision objects, traces и метрики этих трёх роутеров живут под разными ключами и не должны смешиваться. Точно так же prompt-локация `app/prompts/` (см. §4) не означает миграцию `app/tutor_prompts.py` или `app/prompt_smoke_checks.py` — их перенос вне scope этого ADR.

---

## 2. Проблема

Один retrieval pipeline не одинаково хорош для разных пользовательских запросов:

- точечные определения и поиск фрагмента требуют скорости и простоты;
- подробные объяснения, сравнения и инструкции требуют hybrid retrieval, rerank и хорошего context building;
- вопросы о причинах, зависимостях и связях выигрывают от graph-augmented retrieval;
- вопросы по всему корпусу, карты знаний и поиск противоречий требуют отдельного тяжелого global analytics режима.

При этом проект local-first. Нельзя делать каждый запрос дорогим, медленным или зависящим от LLM-extraction всего корпуса. Также нельзя заводить отдельные runtime-пути, которые обходят `get_settings()`, `app/provider.py`, `app/prompts/`, `app/routers/*`, `app/retrieval_strategies.py`, `pipeline_runner.py`, `pipeline_steps.py`, `QueryContext` и observability-контракт.

Ключевая архитектурная ошибка:

```text
Every query -> GraphRAG
```

Правильная целевая линия:

```text
Every query -> bounded routing decision -> cheapest sufficient retrieval path -> answer with evidence and trace
```

---

## 3. Decision drivers

1. **Local-first:** система должна работать как локальный учебный ассистент, без обязательной тяжелой graph-инфраструктуры.
2. **Evidence-first:** каждый режим обязан сохранять citations, provenance и trace.
3. **Incremental adoption:** новые режимы добавляются через существующие strategy/pipeline contracts.
4. **No parallel RAG stack:** нельзя создавать отдельное дерево модулей, которое дублирует `retrieval.py`, `retrieval_strategies.py`, `pipeline_runner.py` и `pipeline_steps.py`.
5. **Cost and latency control:** expensive LLM calls и global analytics включаются только при явной необходимости.
6. **Testability:** routing, retrieval uplift, graph expansion и citations проверяются focused tests/evals.
7. **SSR separation:** Smart Study Router из ADR-020 остается педагогическим next-step router; retrieval mode router не должен смешиваться с SSR decisions.

---

## 4. Решение

Принимаем **Smart Router RAG modes** как целевую архитектурную линию:

```text
user query
  -> input validation / guardrails
  -> QueryContext + QueryOptions + PipelineOverrides
  -> query classification / execution plan
  -> retrieval mode:
       vector_only
       hybrid
       bm25_only
       doc_then_chunk
     plus optional graph expansion where enabled and eligible
     or explicit global analytics operation outside ordinary /ask
  -> context builder / prompt from app/prompts
  -> LLM via app/provider.py + resilience wrapper
  -> answer + citations + trace
```

Архитектурно это не новый framework, а расширение текущего pipeline:

- retrieval modes живут в `app/retrieval_strategies.py`;
- допустимые mode names живут в `KNOWN_RETRIEVAL_MODES` / settings;
- runtime decision проходит через `QueryContext`, `QueryExecutionPlan`, `PipelineOverrides` и `pipeline_runner.py`;
- graph-aware поведение развивается вокруг `app/graph_retrieval.py` как bounded context expansion поверх существующего retrieval mode, а не как отдельный mode name или замена всего retrieval;
- global GraphRAG analytics не является retrieval mode в `KNOWN_RETRIEVAL_MODES`, не является default `/ask` path и не запускается случайно;
- новые prompts добавляются только в `app/prompts/`;
- новые настройки добавляются только в `app/config.py` и читаются через `get_settings()` / `get_retrieval_settings()`.

### 4.1. Product labels vs runtime names

В пользовательской документации допустимы понятные имена, но они не являются SSoT для кода:

| Product label | Resolved profile | Runtime composition |
| --- | --- | --- |
| Fast RAG | `fast` profile | registered retrieval mode (initially `vector_only`) + `graph_augmented=false` + small `top_k` + reranker off |
| Hybrid RAG | `quality` profile | `hybrid` retrieval mode + optional reranker + `graph_augmented=false` |
| Graph RAG / Graph-aware RAG | `graph_aware` profile | registered retrieval mode (typically `hybrid`) + bounded graph expansion via `app/graph_retrieval.py` postprocessor |
| Global GraphRAG Analytics | not a profile | explicit corpus-level analysis job, not ordinary `/ask`; see §4.5 |

Runtime names должны оставаться стабильными и совместимыми с `config.py` и `retrieval_strategies.py`. На дату принятия ADR допустимые retrieval modes: `vector_only`, `hybrid`, `bm25_only`, `doc_then_chunk`. Product labels не становятся вторым набором mode constants; вместо этого они резолвятся через **профили** (см. §4.6 и §8). Профиль композирует `{retrieval_mode, top_k, reranker, graph_augmented}` поверх существующих strategy registries и postprocessor. Prompt variant не хранится в профиле: он выводится отдельным selector contract в §12 Phase 3, чтобы не дублировать состояние между profile registry и prompt package.

"Fast" не является синонимом `vector_only`: это профиль с `graph_augmented=false` и cheap retrieval params; конкретный baseline mode может меняться без изменения product label. Инвариант профиля: `fast.retrieval_mode` должен ссылаться только на зарегистрированный mode, чей измеренный p95 в целевом eval/latency наборе укладывается в fast-бюджет из §10 или в более строгий бюджет, заданный follow-up SLO task.

### 4.2. Fast RAG

Fast RAG нужен для коротких фактологических вопросов, терминов и поиска конкретного фрагмента.

Expected behavior:

- minimum retrieval overhead;
- no graph expansion;
- citations remain mandatory;
- trace фиксирует выбранный режим и retrieval params.

Fast mode не должен становиться отдельным endpoint, если тот же override можно выразить через существующий request contract. Если публичный API меняется, сначала обновляется `app/api_requests.py`, `app/api_models.py`, `doc/api_reference.md` и соответствующие tests.

### 4.3. Hybrid RAG

Hybrid RAG остается production backbone для качественных ответов.

Expected behavior:

- lexical + vector retrieval;
- deterministic merge/fusion where configured;
- optional reranker through existing retrieval settings;
- stable citations and trace;
- no graph expansion unless explicitly enabled by settings/execution plan.

Hybrid является quality path для сценариев, где явно выбран или выбран будущим router-решением. Текущий default `RetrievalSettings.retrieval_mode` остается `vector_only`; изменение default требует отдельной реализации, тестов и doc-sync. При слабом retrieval система должна сохранять existing weak-context behavior и trace.

### 4.4. Graph-aware RAG

Graph-aware RAG нужен для вопросов о зависимостях, причинах, компонентах, prerequisite chains, topic relationships и architecture impact.

Принятое ограничение: на текущем этапе graph-aware RAG является **bounded context expansion** — postprocessor поверх зарегистрированного retrieval mode, владелец `app/graph_retrieval.py`, — а не full GraphRAG replacement, не отдельный `KNOWN_RETRIEVAL_MODES` значение и не knob `RetrievalSettings`. В текущем коде это опциональное расширение через `Settings.enable_graph_augmented_retrieval` (на root `Settings`, не `RetrievalSettings`); его границы задаются `Settings.graph_augment_max_extra_docs` и `Settings.graph_expand_max_hops`.

**Gating contract.** Сегодня expansion gated только по членству `query_type ∈ GRAPH_AUGMENT_QUERY_TYPES` (жёсткое множество в `app/graph_retrieval.py`; на дату проверки это только `synthesis` и `learning_plan`). Этот ADR расширяет gating до композитного правила: expansion включается, когда выполняются **все** условия:

1. `enable_graph_augmented_retrieval=True`;
2. `query_type ∈ GRAPH_AUGMENT_QUERY_TYPES`;
3. `classify_confidence >= graph_augment_min_confidence` (новая настройка, proposed default `0.70`);
4. `(baseline retrieval даёт меньше graph_augment_baseline_thin_k результатов после baseline dedupe / pre-graph expansion **или** профиль явно graph_aware)` (новая настройка, proposed default `3`).

Правило полностью: `enable AND query_type ∈ GRAPH_AUGMENT_QUERY_TYPES AND confidence >= threshold AND (thin_baseline OR explicit_graph_aware_profile)`. Это делает graph-aware "uplift when it pays off" вместо "always on for eligible class", уменьшая latency p95 и шум в trace. Если graph expansion отключается или падает из-за gating/fallback, trace должен записывать оба значения: `selected_profile` (например, `graph_aware`) и `effective_profile` / `effective_graph_augmented` (например, `quality` / `false`) вместе с `fallback_reason`.

Graph-aware path обязан:

- использовать существующий knowledge graph contract из ADR-013;
- требовать evidence links для graph relations;
- добавлять graph evidence к retrieved context, а не заменять source chunks абстрактными graph statements;
- писать `graph_expansion` trace по контракту `doc/conventions_architecture.md`;
- fallback to non-graph retrieval при недоступном graph bundle, низком confidence, missing evidence или пустом graph expansion;
- не открывать ad hoc SQLite connections вне documented store wrappers.

Graph-aware retrieval не должен:

- создавать Neo4j или другой graph DB без отдельного ADR;
- записывать напрямую в `kg.sqlite` в обход JSON source of truth;
- смешиваться с SSR policy из ADR-020;
- обходить `app/knowledge_service.py` / фасады при доступе из routers/UI.

### 4.5. Global GraphRAG Analytics

Global GraphRAG Analytics принимается как отдельное направление, но не как default answer path.

Этот режим предназначен для:

- карты знаний по scope;
- глобального summary;
- поиска противоречий;
- анализа архитектурных рисков;
- topic dependency map;
- learning path generation по корпусу.

Ограничения:

- запускается только explicit user action или route with high-confidence + confirmation/clear mode;
- должен иметь scope limit;
- должен иметь explicit kill switch (`enable_global_analytics=False` by default) and per-job / per-day cost ceilings before public runtime exposure;
- должен иметь отдельные latency/cost/trace events;
- должен сохранять provenance от community/global summary к исходным documents/chunks;
- должен проектироваться как long-running или async-like operation, если выходит за интерактивный latency budget.

`global_graph` не добавляется в обычный `/ask` как случайный fallback и не добавляется в `KNOWN_RETRIEVAL_MODES`. Этот ADR не утверждает конкретный endpoint, request schema или response schema для global analytics. Если такой endpoint позже проектируется, он требует отдельного API/design update, живет в `app/routers/*`, регистрируется через `app/api.py` и документируется в `doc/api_reference.md`.

### 4.6. RAG profiles (user-facing override surface)

Product labels резолвятся в **профили**, а не в raw retrieval mode names. Профиль — это Pydantic model `RagProfile`, который композирует `{retrieval_mode, top_k, reranker, graph_augmented}` поверх существующих strategy registries and `PipelineOverrides` ([app/models.py](app/models.py)). `graph_caps` intentionally is not a separate profile field in this ADR; graph bounds remain the settings-owned caps `graph_augment_max_extra_docs` and `graph_expand_max_hops`.

Initial set of profiles:

| Profile | retrieval_mode | top_k | reranker | graph_augmented | Notes |
| --- | --- | --- | --- | --- | --- |
| `fast` | `vector_only` (initial baseline; can change only if latency invariant holds) | small, setting-owned | off | false | cheap path |
| `quality` | `hybrid` | default retrieval setting | optional (via settings) | false | production backbone |
| `graph_aware` | `hybrid` baseline (configurable) | default retrieval setting + bounded extras | optional | true (gated per §4.4) | bounded postprocessor uplift |

Профили — user-facing override surface (см. §8). Raw `retrieval_mode` остаётся internal override, доступным только через debug/admin paths или config. Routing v1 (§6) выбирает profile name, а не mode напрямую. Because `PipelineOverrides` is currently a frozen dataclass, Phase 1 must either migrate it to Pydantic or keep `rag_profile: Optional[str]` as the transport field and resolve the Pydantic `RagProfile` inside a profile registry/router boundary; the resolved struct must not be stored silently inside a dataclass if that creates serialization drift at the API/FastAPI boundary.

## 5. Draft ADR dispositions

Принято из draft ADR:

- Не заменять весь RAG на GraphRAG.
- Разделить быстрые, качественные, graph-aware и global analytics сценарии.
- Считать Hybrid RAG production backbone.
- Требовать evidence links для graph relations.
- Требовать trace, eval и route observability.
- Отложить Neo4j и тяжелую community-based GraphRAG механику до доказанной необходимости.

Отклонено или изменено:

| Draft proposal | Решение в этом ADR | Причина |
| --- | --- | --- |
| Новое дерево `app/rag/`, `app/retrieval/`, `app/graph/`, `app/indexing/` | Не принимается как immediate architecture | Уже есть `pipeline_runner`, `pipeline_steps`, `retrieval_strategies`, `knowledge_graph_bundle`; параллельное дерево создаст drift |
| `/ask/fast`, `/ask/hybrid`, `/ask/graph` как обязательные endpoints | Не принимается как обязательный API | Mode override должен идти через существующий contract; endpoint surface расширяется только отдельным API ADR/update |
| SQLite/Postgres graph tables как primary MVP graph store | Уточнено через ADR-013: JSON source of truth + SQLite derived read layer | Нельзя сломать storage contract и backup/sync expectations |
| Prompt contracts прямо в ADR | Только как behavioral intent; фактические prompts живут в `app/prompts/` | Проект запрещает hardcoded prompts вне prompt package |
| Массовые feature flags для всего | Только settings with owner, default, tests and doc-sync | Проект избегает лишних flags; runtime toggles допустимы только при clear owner/need |
| Entity extraction for every chunk as near-term must | Принимается только как scoped/batched/index-time capability with cost budget | Иначе local-first и cost-control быстро ломаются |
| `global_graph` как route рядом с обычным answer path | Только explicit/global analytics operation outside `KNOWN_RETRIEVAL_MODES` | Слишком дорогой и долгий режим для случайного auto route |

---

## 6. Routing contract

Routing v1 должен быть deterministic-first:

1. explicit user/API override wins (profile via API → raw `retrieval_mode` via debug only); no-uplift demotion (§9.2) applies only to auto-resolved profiles and must be skipped for explicit user overrides with a `route_demotion_skipped` trace/metric event;
2. existing query type / execution plan signals are considered;
3. rule-based intent signals can choose cheaper sufficient profile;
4. router v1 is deterministic-first and must not make an additional LLM call before retrieval; if a later ADR introduces LLM-assisted routing, that signal must go through `app/provider.py`, `app/prompts/` and resilience wrapper and must not overwrite `classify_*` fields;
5. low-confidence fallback applies only when no explicit non-default user/config override (`profile` or raw debug `retrieval_mode`) is set: route to `quality` profile for default behavior, or to `fast` profile when latency budget signals require it. The current configured default (`RetrievalSettings.retrieval_mode = "vector_only"` today, [app/config.py](app/config.py)) does not by itself count as an explicit user/config override. Changing the global default is out of scope of this ADR and requires a separate change with doc-sync (§4.3).

### 6.1. Relationship to `classify_step`

The retrieval router **consumes** existing classifier output and does **not** re-classify:

- inputs: `QueryContext.query_type`, `QueryContext.classify_confidence`, `QueryContext.classify_method`, `PipelineOverrides`, settings, and deterministic intent signals (for example regex/rule matches over the normalized question);
- outputs: the `RetrievalRoutingDecision` written to `QueryContext.trace["retrieval_routing"]` plus a resolved `RagProfile` propagated into `PipelineOverrides.rag_profile` / `retrieval_mode` for the downstream pipeline.

There is exactly one `classify_step` pass per request. Router v1 does not run an additional LLM classifier; any later LLM-assisted routing extension requires a separate ADR/update and must write a distinct router signal into the decision object, never overwriting `classify_*` fields on `QueryContext`.

### 6.2. Typed routing decision

The trace shape proposed by this ADR is a **new** key (`QueryContext.trace["retrieval_routing"]`) and a **new** Pydantic model `RetrievalRoutingDecision` in `app/models.py`:

```json
{
  "selected_profile": "quality",
  "selected_retrieval_mode": "hybrid",
  "effective_profile": "quality",
  "effective_retrieval_mode": "hybrid",
  "graph_augmented": false,
  "effective_graph_augmented": false,
  "fallback_reason": null,
  "reason": "comparison intent with multi-document likelihood",
  "confidence": 0.76,
  "matched_signals": ["comparison", "detailed_answer"],
  "manual_override": false,
  "classify_query_type_input": "qa",
  "classify_confidence_input": 0.82,
  "profile_resolved_from": "rule"
}
```

For deterministic rule-based routing, `confidence` is a normalized rule score in `[0,1]` derived from matched signals; if no reliable score exists, it is omitted/null and the fallback policy treats it as low-confidence. The model is written into `QueryContext.trace["retrieval_routing"]` as `model_dump()`. A focused schema test (`tests/test_retrieval_routing_trace.py`) is required in the same task that introduces the router. The trace is exposed through existing debug/pipeline trace surfaces and must not create a separate observability store.

### 6.3. Decision caching

Route decisions are cacheable by `(question_hash, profile_request, classify_query_type, settings_signature)`. `settings_signature` must include retrieval/profile settings plus classifier model id, prompt hash where relevant, and active graph/index generation id so model, prompt, settings or KG changes invalidate stale decisions. Implementation reuses the key-namespace conventions of `app/query_faq_cache.py` to avoid a second cache store. Cached decisions still write `trace["retrieval_routing"]` (with `profile_resolved_from = "cache"`) so observability stays uniform.

---

## 7. Data and storage contract

### 7.1. Retrieval result

Every final context item must preserve:

- source text or bounded text preview;
- source path / document id / chunk id where available;
- score or ranking reason;
- retrieval source (`vector`, `bm25`, `rrf`, `reranker`, `graph_expansion`, or `doc_then_chunk` when lineage cannot be represented by the underlying sub-strategy label);
- metadata needed for citation display.

Phase 1 must introduce `RetrievalSource = Literal["vector", "bm25", "rrf", "reranker", "graph_expansion", "doc_then_chunk"]` in `app/models.py` (or an equivalent typed enum) and tag context items at the strategy boundary. This makes per-item provenance auditable instead of only request-level routing.

### 7.2. Graph evidence

Every graph relation used in an answer must be carried as a typed `GraphEvidence` payload (new Pydantic model in `app/models.py`) attached to context items emitted by `GraphExpansionPostprocessor` ([app/graph_retrieval.py](app/graph_retrieval.py)). Required fields:

- source entity;
- target entity;
- relation id (stable hash or UUID for dedupe/citation pinning);
- relation type;
- direction (`forward`, `reverse`, `undirected`) or an explicit statement that `(source_entity, target_entity)` is ordered for that relation type;
- evidence chunk/document id;
- confidence or provenance quality (required float in `[0,1]`);
- generation/index version when available.

No answer may cite a graph relation as fact without source-backed evidence. When `confidence` is below a configured threshold (`graph_evidence_weak_threshold`, new setting, proposed default `0.60`), the answer builder must render an "evidence weak / inferred" badge and the prompt must instruct the model to mark the relation as inferred. Relations with missing evidence are dropped from answer context by default; if a future task chooses to surface them, they must be explicitly marked as inferred and must not be used as citations. Acceptance criterion §13 #5 becomes testable against the typed payload.

### 7.3. Global summaries

Community/global summaries are derived artifacts. They must preserve provenance to source documents/chunks and are not a replacement for citations.

The **concrete schema** of summary artifacts is owned by the global-analytics design ADR scheduled in §12 Phase 4. This ADR pins only the artifact-level contract: every global-analytics run produces a `GlobalAnalyticsJob` record under `data/graph_analytics/jobs/<job_id>/` with a forward provenance link to the graph/index generation id (rather than nesting job lifecycle under the generation tree) and carrying at minimum:

- request scope descriptor;
- generation id;
- started/completed timestamps;
- cost / token totals;
- output artifact path(s);
- provenance index from summary → chunks/documents.

Pinning the artifact shape now keeps re-computation and idempotency rules bindable before the endpoint design lands.

---

## 8. API and UI implications

This ADR does not approve an immediate public API expansion.

State of `/ask` override today: `AskRequest` ([app/api_requests.py](app/api_requests.py)) does **not** carry a `retrieval_mode` or `profile` field. The internal `PipelineOverrides.retrieval_mode` and `PipelineOverrides.rag_profile` ([app/models.py](app/models.py)) exist but are not API-exposed. Surfacing override therefore requires an explicit `AskRequest` schema change (with corresponding updates to `app/api_models_main.py`, `doc/api_reference.md`, and focused tests) — it is not a no-op.

Allowed near-term path:

- expose user-facing override as `profile: Optional[str]` on `AskRequest`, validate it against `KNOWN_PROFILES` / profile registry at request time, and return a 400 with the valid list on invalid input; map valid values to internal `PipelineOverrides.rag_profile`. Raw `retrieval_mode` override stays behind debug/admin-only paths so product labels and runtime mode names cannot drift through the public API;
- expose debug trace through existing metrics/debug surfaces;
- keep Streamlit controls aligned with existing UI helper modules;
- document public API changes before or with implementation.

If new endpoints are later added, preferred shape:

- ordinary answer endpoint remains `/ask`;
- graph inspection endpoints belong under existing knowledge/graph router ownership;
- global analytics endpoint must be explicit, scoped and documented as potentially long-running.

---

## 9. Evaluation contract

Before promoting a route to default behavior, create or update focused eval sets:

| Set | Purpose |
| --- | --- |
| fast questions | Verify latency and citation correctness for simple factual queries |
| hybrid questions | Verify context precision/recall for comparison, instruction and multi-document answers |
| graph questions | Verify graph expansion uplift and evidence-backed relation answers |
| global analytics tasks | Verify scoped corpus-level synthesis, provenance and cost/latency limits |

Minimum metrics:

- router accuracy against manually labeled eval questions (or drop/rename the metric in an implementation task if no ground-truth labels exist);
- retrieval context precision/recall;
- citation correctness;
- faithfulness;
- graph uplift over non-graph baseline;
- latency p50/p95;
- cost or token budget for LLM-backed steps;
- fallback rate.

Graph mode is not considered successful merely because it returns more context. It must improve evidence quality or answer correctness on graph-shaped questions.

### 9.1. Metric ownership

Router and routing-related metrics ship through existing aggregation surfaces ([app/metrics_slo.py](app/metrics_slo.py), [app/metrics_summarizer.py](app/metrics_summarizer.py)), mirroring how `query_mode` metrics already flow. No new metrics store is introduced. Minimum aggregated surfaces:

- route distribution by `selected_profile` and `selected_retrieval_mode`;
- override-vs-auto ratio;
- low-confidence fallback rate;
- graph-augmented uplift over hybrid baseline on the graph eval set;
- per-mode p50/p95 latency and cost (see §10 for namespace rules).

### 9.2. No-uplift demotion rule

If graph-augmented uplift over the hybrid baseline on the graph eval set is below a fixed delta (`graph_uplift_min_delta`, new setting, proposed default `0.05`) for N consecutive offline eval runs (`graph_uplift_consecutive_runs`, new setting, proposed default `3`), the router demotes auto-resolved `graph_aware` to `quality` until a later eval run passes the threshold or an operator explicitly clears the demotion state. Demotion state must be persisted in a documented settings/artifact path or represented by a config commit; runtime-only memory is not sufficient. The demotion event is logged through the metrics surface above, increments `route_demotion_count{from,to,reason}`, and surfaces in `trace["retrieval_routing"].reason`. This is the feedback loop that keeps graph-aware honest as the corpus grows; without it, §9's "must improve" requirement is unenforceable.

---

## 10. Non-functional requirements

Target budgets are aspirational guardrails, not hard API guarantees and not automatically enforced by this ADR.

**Namespace conflict.** Today `slo_latency_by_mode` ([app/config.py](app/config.py)) is keyed by `query_mode` (e.g. `qa`, `tutor`), not by retrieval mode or profile. The table below is keyed by **RAG profile** (§4.6), which is a third namespace. Wiring the two requires an explicit migration: either extend `slo_latency_by_mode` to accept profile-prefixed keys (`profile:fast`, `profile:quality`, `profile:graph_aware`, `query_mode:qa`, …) with a documented resolution rule (most-specific wins), or introduce a dedicated `slo_latency_by_profile` setting and keep `slo_latency_by_mode` for `query_mode`. The decision is deferred to the task that promotes these targets to enforced SLOs and is gated by its own doc-sync.

Until that wiring lands, the table below is **advisory only** and must not be referenced as enforced SLO.

| Profile (§4.6) | p50 target | p95 target | Notes |
| --- | --- | --- | --- |
| `fast` | <= 2s | <= 5s | No graph expansion; small `top_k`; reranker off |
| `quality` | <= 5s | <= 15s | Hybrid + optional reranker; no graph expansion |
| `graph_aware` | <= 8s | <= 25s | Must fallback cleanly when graph unavailable; demoted to `quality` if no-uplift rule fires (§9.2) |
| Global analytics | explicit long task | scope-dependent | Not accidental `/ask` behavior |

Cost-control rules:

- no strong LLM for every chunk by default;
- extraction should be batch/index-time where possible;
- use content hashes and index generation to avoid unnecessary recomputation;
- global summaries are recomputed only for changed scope/generation;
- all expensive steps must be observable.

Enforcement follow-up: when profile SLO wiring lands, each profile gets a hard deadline. For `graph_aware`, the recommended first deadline is `12000 ms`; deadline breach falls back to effective `quality`, records `fallback_reason="profile_deadline_exceeded"`, and increments `route_demotion_count` / fallback metrics. Guardrails must also prevent repeated forced `graph_aware` usage from a noisy or hostile client (for example per-session/IP budget or backpressure through the existing guardrails layer).

---

## 11. Consequences

Positive:

- Project gets a clear path from current hybrid retrieval to graph-aware answers without replacing the existing stack.
- Simple queries remain fast.
- Complex relationship questions can use graph evidence.
- Global analytics becomes possible without making every `/ask` request heavy.
- Reviewers get concrete boundaries for future changes.

Negative:

- Routing adds another decision layer that must be tested.
- Trace payloads become more important and may need UI/debug polishing.
- Graph quality can regress answers if entity normalization and evidence links are weak.
- Global analytics introduces expensive derived artifacts and scope/cost management.

Mitigations:

- deterministic-first routing;
- manual override;
- graph fallback to hybrid/vector path;
- focused eval sets;
- provenance requirements;
- no new storage or endpoint surface without doc-sync and tests.

---

## 12. Suggested implementation sequence

This sequence is advisory and non-authoritative; `doc/backlog_registry.yaml` remains the SSoT for task priority, owner and status.

### Phase 0: Align existing state

- Verify and patch any drift between `doc/conventions_architecture.md` / `doc/api_reference.md` and actual retrieval / graph-expansion behavior (the docs already describe modes — this phase fixes drift, it does not re-document).
- Ensure trace includes selected retrieval mode, graph expansion status and fallback reason.
- Keep mode names aligned between `config.py`, `retrieval_strategies.py` and public docs.

### Phase 1: Router contract hardening

- Introduce `KNOWN_PROFILES` / profile registry in `app/config.py` (or a small config-owned module) and validate profile names at API/debug boundaries.
- Introduce typed `RetrievalRoutingDecision` (`app/models.py`) and `QueryContext.trace["retrieval_routing"]` writer; cover with a schema test.
- Introduce typed `RetrievalSource` provenance labels (§7.1) and tag final context items at strategy boundaries.
- Wire the retrieval router to consume `classify_step` output (§6.1) — no re-classification.
- Surface `profile: Optional[str]` on `AskRequest` (§8) with corresponding `api_models_main.py` / `api_reference.md` / tests updates.
- Add focused tests for rule routing, low-confidence fallback, explicit override, and decision caching (§6.3).
- Add a debug-only route inspection surface (for example `/debug/route`) that returns `RetrievalRoutingDecision` without running retrieval or LLM, if the project still has an appropriate debug/admin router at implementation time.

### Phase 2: Graph-aware uplift

- Improve graph expansion only through `app/graph_retrieval.py` and graph bundle contracts.
- Introduce typed `GraphEvidence` payload (§7.2) and weak-evidence rendering in answer builder.
- Implement composite gating (§4.4): `enable AND query_type ∈ S AND confidence ≥ θ AND (thin baseline OR explicit profile)`.
- Add graph-question eval set and graph uplift report; wire §9.2 demotion rule.
- Persist or document demotion state and recovery policy; expose `route_demotion_count{from,to,reason}` via existing metrics surfaces.

### Phase 3: Prompt selector contract

- Define `PromptSelector(query_type, profile, retrieval_mode, graph_augmented, learner_state) -> PromptId` owned by `app/prompts/`.
- Migrate retrieval-side prompt selection to the selector; `app/tutor_prompts.py` continues to own tutor selection and is out of scope for this phase.
- Cover with focused tests that selection is deterministic for each `(query_type, profile)` pair.

### Phase 4: Global analytics design

- Write a separate implementation ADR or design doc before building full community/global summary pipeline.
- Define artifact ownership, recomputation rules, provenance schema, cost logging and UI/API surface; the `GlobalAnalyticsJob` artifact-level contract (§7.3) is the starting point.

### Phase 5: Product surfacing

- Add user-facing controls only after route behavior is stable.
- Keep SSR next-step routing (ADR-020) and RAG retrieval routing visibly separate in docs and code.

---

## 13. Acceptance criteria for future implementation

1. Runtime retrieval mode names remain exactly the registered values in `KNOWN_RETRIEVAL_MODES`; product labels are mapped at API/UI/docs boundaries only, via `RagProfile` (§4.6).
2. Graph-aware behavior is implemented as optional bounded expansion as a postprocessor over a registered retrieval mode, gated by `enable_graph_augmented_retrieval` **and** `query_type ∈ GRAPH_AUGMENT_QUERY_TYPES` **and** `classify_confidence ≥ graph_augment_min_confidence` **and** (thin baseline OR explicit `graph_aware` profile); bounded by `graph_augment_max_extra_docs` and `graph_expand_max_hops`.
3. Routing writes a typed `RetrievalRoutingDecision` to `QueryContext.trace["retrieval_routing"]` with selected profile and mode, graph expansion decision, reason, confidence/signals where available, manual override status, classify input fields, and `profile_resolved_from`.
4. Global analytics is explicit, scoped and outside ordinary `/ask` fallback behavior; any endpoint/schema requires API docs and focused tests in the same task; the `GlobalAnalyticsJob` artifact contract (§7.3) is honored.
5. Every graph relation used in answer generation is carried as a typed `GraphEvidence` payload with source evidence or is clearly marked as weak/inferred evidence (rendered by the answer builder when `confidence < graph_evidence_weak_threshold`).
6. Focused routing tests cover explicit override, auto route, low-confidence fallback and decision caching.
7. `QueryContext.trace["retrieval_routing"]` schema is covered by a dedicated schema test (`tests/test_retrieval_routing_trace.py`) in the same task that introduces routing.
8. `GraphEvidence` typed payload is covered by a focused test asserting required fields and weak-evidence rendering threshold.
9. The retrieval router does not re-classify: tests assert exactly one `classify_step` pass per request (§6.1).
10. `RetrievalSource` provenance is typed and covered by at least one focused strategy-boundary test.

---

## 14. Final position

Accepted architecture:

```text
Fast RAG for simple factual work.
Hybrid RAG as quality path where selected.
Graph-aware RAG as bounded evidence expansion over registered retrieval modes.
Global GraphRAG Analytics as explicit scoped corpus analysis outside default RAG.
```

The project should evolve toward an adaptive RAG platform only through the existing local-first contracts. GraphRAG is a specialized capability, not a replacement for retrieval, citations, tutor flow or Smart Study Router. When the §9 graph eval set shows `graph_aware` uplift >= `graph_uplift_min_delta` for at least four consecutive weekly runs and `quality` profile SLO violation rate is below 5%, propose ADR-022 to consider adaptive routing as default behavior.

---

## 15. Relationship to ADR-019 ownership lines

ADR-019 (Wave B3) fixed the split boundary between query-side and graph-side modules to break the god-module growth. This ADR's new components honor those lines:

- **Query side** (owner of the retrieval router): `RetrievalRoutingDecision`, the router that consumes `classify_step` output (§6.1), `RagProfile` resolution, route caching (§6.3), and `trace["retrieval_routing"]` writer.
- **Graph side** (owner of evidence and expansion): `GraphEvidence` typed payload, `GraphExpansionPostprocessor` gating changes (§4.4), `trace["graph_expansion"]` writer (unchanged), and the `GlobalAnalyticsJob` artifact (§7.3).

No module crosses the line. The query-side router never opens a graph store, and the graph-side postprocessor never overwrites `QueryContext.query_type` / `classify_*` fields. The prompt selector (§12 Phase 3) lives in `app/prompts/` and reads from both sides through the typed contracts above, not by importing internals from either.
