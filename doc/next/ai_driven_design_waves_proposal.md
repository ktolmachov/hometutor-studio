# 🚀 AI-Driven Design — Next-Level Waves Proposal

**Дата:** 2026-06-05
**Статус:** Starter cluster из 5 волн promoted в `backlog_registry.yaml` (proposed, 2026-06-05); остальные 8 — кандидаты
**Источник идей:** [`D:\exchange\summary_01-ai-driven-design.md`](../../../../exchange/summary_01-ai-driven-design.md) — конспект «AI-driven проектирование агентской системы» (курс Deep Agents, занятие 1)
**Killer feature, на которую работаем:** [Smart Study Router (SSR)](../smart_study_router.md)
**Roadmap-якорь:** [roadmap.md](../roadmap.md) · [backlog_registry.yaml](../backlog_registry.yaml) (SSoT)

---

## 🎯 Главная мысль

Конспект описывает каноничный стек production-агента: **multi-model routing → context engineering → structured output → advanced RAG → ReAct + MCP-инструменты → память → observability (Langfuse) → security (guardrails) → multimodal → multi-agent**.

hometutor уже закрывает большую часть этого (RAG, graph-retrieval, provider-fallback, OTel, guardrails, local-LLM circuit, eval-harness, SSR local-ML слой). Поэтому **сильный ход — не повторять готовое, а добить реальные пробелы** относительно конспекта и **состыковать каждый пробел с killer feature (SSR)**:

| Пробел из конспекта | Что уже есть | Чего не хватает |
|---|---|---|
| MCP-протокол инструментов | tools разбросаны по сервисам | единого MCP tool-plane нет |
| Несколько моделей под задачу | ~10 per-task моделей в `config.py` (chat/embed/rewrite/classify/graph/quiz/ingestion/eval/ssr) + fallback | единой декларативной tier-политики + **vision/reasoning** tier'ов нет |
| Продвинутый RAG | single-query rewrite (flag), hybrid RRF, cross-encoder rerank (`bge-reranker`, on by default) уже shipped | **multi-query expansion** + явный **lost-in-the-middle reorder** нет |
| «Не выдумывай → верни null» | prompt-level abstain (`guardrails.py`, `prompts/_impl.py`) | **schema-enforced** pydantic-контракта abstain + citations/provenance нет |
| Мультимодальный RAG | OCR/docling ingest (`ingest_docling_enabled`), voice | vision-intake (скриншот/диаграмма) нет |
| Langfuse-цикл | OTel/OTLP traces | Langfuse self-hosted + trace→dataset loop нет |
| RAG-eval (RAGAS) | faithfulness/answer-rel (LlamaIndex) + recall@k/MRR (`eval_retrieval_comparison.py`) | **context_precision@k** (rank-aware) + **answer_correctness** vs reference + Langfuse-датасеты нет |
| Мульти-агент / делегирование (demo 8 субагентов, M08, M10–12) | team-pipeline + `workflow.py` (rule-based); doc-loading уже parallel (`_load_documents_parallel`) | агентного (LLM) router'а + **multi-stage** subagent orchestration (graph/quiz-seed) нет |
| PII masking в логах/трейсах | `redact_sensitive_text` (guardrails.py) для answer/judge | покрытия **logs/OTel-traces/session_tape** + единой policy нет |
| Indirect injection / poisoning | direct injection detect (`detect_prompt_injection`) + HTTP rate-limit (`RateLimitMiddleware`) + adversarial runner | **косвенной (ingested)** injection, poisoning scan, **per-loop** tool-лимитов нет |

**13 волн / 27 пакетов**, сгруппированы по слою наибольшего влияния (5 / 4 / 4). Каждая волна оформлена в схеме `backlog_registry.yaml` (`id / theme / north_star / entry_mot / exit_mot / packages / kill_switch`). Starter cluster (5 волн: I2, A4, A3, I1, I4) **уже promoted как `proposed`** 2026-06-05 — см. § Как промоутить.

---

## 🏛️ Слой 1 — Архитектура (ядро агента, модели, RAG, контракты, мульти-агент)

> Конспект: «Архитектура агента: ReAct», «Инструменты и MCP», «Типы моделей», «Structured Output», «Продвинутый RAG», «Демо: 8 параллельных субагентов».

### Волна A1 — MCP Tool Plane

```yaml
- id: wave-mcp-tool-plane
  theme: "MCP-протокол: единый tool-plane для tutor и SSR"
  north_star: >-
    Все read-инструменты (retrieval, knowledge_graph, learner_state, SRS due-queue)
    доступны агенту через один локальный MCP-сервер; tutor/SSR вызывают их через
    MCP-клиент с rails на число вызовов — без дублирования кода в каждом сервисе.
  entry_mot: "cross-loop"
  exit_mot: "#3 Transition to tutor"
  packages:
    - mcp-tool-server-v1          # локальный MCP-сервер: обёртки над retrieval + learner-state + graph (read-only)
    - mcp-agent-client-v1         # tutor/SSR как ReAct-клиент: tool-call loop + лимит вызовов + tool-result cleanup
  kill_switch: >-
    MCP-слой добавляет >100ms p95 к first-answer, экспонирует write-инструменты без HITL-гейта,
    или e2e tutor/SSR красный >2 дней.
```
- **Конспект → реализация:** «MCP-сервер с набором инструментов; один сервер для разных агентов; rails на количество вызовов».
- **Связь с killer feature:** SSR перестаёт хардкодить доступ к graph/SRS — новые сигналы подключаются как MCP-инструменты.
- **Roadmap:** док-курс M08 (планирование/делегирование), фундамент под мульти-агента.

### Волна A2 — Multi-Model Tier Router

```yaml
- id: wave-multi-model-tier-router
  theme: "Multi-Model Tier Router: единая политика поверх существующих per-task моделей + vision/reasoning"
  north_star: >-
    Существующие ~10 per-task моделей (chat/embed/rewrite/classify/graph/quiz/ingestion/eval/ssr из config.py)
    консолидируются в одну декларативную tier-политику; добавляются недостающие vision и reasoning tier'ы;
    выбор проходит через provider-абстракцию с budget-гейтом и видимым ярлыком модели,
    а per-task cost/latency телеметрия формирует отчёт «кандидаты на спуск в локальную модель».
  entry_mot: "#2 First Answer"
  exit_mot: "cross-loop"
  packages:
    - model-tier-policy-v1        # config-таблица tier'ов + selection в provider.py поверх существующего fallback
    - reasoning-escalation-v1     # эскалация на reasoning-модель только для «трудных» tutor-шагов, под latency_budget
    - model-cost-telemetry-v1     # per-task token/cost/latency → «downshift candidate» отчёт (лайфхак «облако → вниз»)
  kill_switch: >-
    Tier-роутинг ломает balanced-fallback consent, повышает median cost >1.5x,
    меняет hint_kind/SSR routing, или телеметрия добавляет стоимость >1% на запрос.
```
- **Конспект → реализация:** «специализированные модели для embeddings/vision/reasoning»; проект уже разнёс chat/embed/rewrite/graph/quiz/ingestion/eval/ssr по моделям — пробел в **единой политике** и **vision/reasoning** tier'ах; лайфхак «облако → вниз» через cost-телеметрию.
- **Связь с killer feature:** SSR-explanation L2 (LLM-объяснение) идёт на дешёвую модель; tutor-depth — на reasoning. Дополняет «Balanced LLM Fallback» из текущего прорыва.
- **Roadmap:** M01–02 (базовый агент), усиливает [BREAKTHROUGH](BREAKTHROUGH_SUMMARY.md) §1.

### Волна A3 — Advanced RAG: Rewrite + Hybrid + Rerank

```yaml
- id: wave-advanced-rag-rewrite-rerank
  theme: "Advanced RAG: multi-query expansion + lost-in-the-middle reorder (rewrite/hybrid/rerank уже shipped)"
  north_star: >-
    Поверх уже работающих single-query rewrite (enable_rewrite), hybrid RRF и cross-encoder rerank
    (bge-reranker, on by default) основной answer-путь получает multi-query expansion и явный
    lost-in-the-middle reorder контекста; source-coverage растёт без регрессии latency_budget.
  entry_mot: "#2 First Answer"
  exit_mot: "#2 First Answer"
  packages:
    - multi-query-expansion-v1    # multi-query expansion поверх существующего single-query rewrite (enable_rewrite)
    - lost-in-middle-reorder-v1   # явный reorder слитых кандидатов против «lost in the middle» (rerank уже есть)
  kill_switch: >-
    Expansion/reorder добавляют >hard_ms к query-budget >2 дней, снижают grounded-citation rate,
    или ломают retrieval_router / существующий reranker fallback.
```
- **Конспект → реализация:** «переформулирование, гибридный поиск, реранжирование» — гибрид (RRF), rerank (`bge` cross-encoder) и single rewrite уже в `retrieval.py`/`hybrid_retrieval.py`/`condense_step.py`; пробел — **multi-query** и **lost-in-the-middle reorder**.
- **Связь с killer feature:** лучшее покрытие источников питает SSR **source-trust overlay** и scoped-answer качество.
- **Roadmap:** M04 (векторные БД) / M05 (GraphRAG), стыкуется с `retrieval_router.py`/`hybrid_retrieval.py`.

### Волна A4 — Grounding Contract: «Abstain, don't invent»

```yaml
- id: wave-grounding-abstain-contract
  theme: "Structured Output контракт: не выдумывай факт — верни abstain + provenance"
  north_star: >-
    Answer/quiz/plan-генерация возвращают строгую pydantic-схему: каждый факт несёт citation/tool-provenance,
    при отсутствии источника — явный abstain(null), а не выдуманный ответ; факты, меняющие learner_state,
    запрещены без источника.
  entry_mot: "#2 First Answer"
  exit_mot: "#8 Progress check"
  packages:
    - grounded-answer-contract-v1 # pydantic schema: required citations | abstain-path; валидация в pipeline_steps
    - fact-source-binding-v1      # любой state-меняющий факт несёт source/tool provenance, не свободный текст
  kill_switch: >-
    Контракт повышает abstain-rate на valid-запросах >10pp, ломает answer_parser,
    или блокирует tutor-цикл.
```
- **Конспект → реализация:** мантра «не выдумывай — верни null»; prompt-level abstain уже есть (`guardrails.py`, `prompts/_impl.py` «недостаточно информации») — пробел в том, чтобы сделать это **schema-enforced** pydantic-контрактом с citations, а не инструкцией промпта.
- **Связь с killer feature:** SSR **outcome receipts / evidence ledger** получают проверяемый provenance вместо текста.
- **Roadmap:** усиливает «Evidence-based» принцип SSR (§ Принципы развития).

### Волна A5 — Agentic Orchestrator + Parallel Subagents

```yaml
- id: wave-agentic-orchestrator-subagents
  theme: "Мульти-агент: агентный router команды + orchestrator-subagent fan-out"
  north_star: >-
    Детерминированный workflow.py получает LLM-assisted планирование/делегирование (ReAct: предложить
    следующий пакет/шаг с обоснованием, остаётся rule-based fallback); folder→course получает
    multi-stage subagent orchestration (chunk → graph → quiz-seed как отдельные субагенты) —
    document loading уже parallel (_load_documents_parallel), пробел в оркестрации стадий,
    как в demo «8 субагентов → 111 слайдов за 15 мин».
  entry_mot: "cross-loop"
  exit_mot: "#1 Local Setup"
  packages:
    - agentic-workflow-router-v1      # workflow.py: LLM-планировщик next-package/step поверх resolve_state, rule-based fallback
    - parallel-subagent-orchestrator-v1 # multi-stage subagent orchestration (graph/quiz-seed; doc-loading уже parallel)
  kill_switch: >-
    Агентный router меняет статусы в backlog_registry без человеческого review (нарушает Truth View
    invariant), субагенты пишут вне data/docs/<course>/, или fan-out ломает golden-E2E ingest.
```
- **Конспект → реализация:** «Демо: 8 параллельных субагентов» + «ReAct» + M08 + M10–12; document loading уже parallel (`ingestion.py:_load_documents_parallel`) — пробел в **агентном router'е** и **оркестрации стадий** (graph/quiz-seed).
- **Связь с killer feature:** ускоряет **folder→course** (текущий прорыв §2) оркестрацией стадий; опирается на **A1 MCP Tool Plane** как общий tool-plane для субагентов.
- **Roadmap:** M08 / M10–12; стыкуется с `scripts/workflow.py`, `team_workflow/`, `orchestrator_router.py`.
- **⚠️ Governance:** агентный router предлагает, но **не** коммитит статус-переходы в `backlog_registry.yaml` без owner review — Truth View invariant остаётся машинно-защищённым (`roadmap_sync_check.py`).

---

## 📚 Слой 2 — UX (опыт ученика, прозрачность, мультимодальность, agency)

> Конспект: «Контекст и история», «Память агента», «Мультимодальный RAG», «Human-in-the-loop».

### Волна U1 — Multimodal Intake: скриншоты и диаграммы

```yaml
- id: wave-multimodal-vision-intake
  theme: "Мультимодальный вход: ученик кидает скриншот/фото задачи или диаграммы"
  north_star: >-
    Ученик прикладывает скриншот задачи/конспекта/диаграммы → vision-модель извлекает структуру
    → запрос маршрутизируется в Q&A/tutor; подписи/диаграммы индексируются в Chroma с provenance.
  entry_mot: "#2 First Answer"
  exit_mot: "#3 Transition to tutor"
  packages:
    - vision-intake-v1            # image → structured extraction (vision-модель) → query/tutor routing
    - multimodal-rag-index-v1     # caption/figure index в Chroma с source provenance
  kill_switch: >-
    Vision-путь пишет файлы вне data/docs/<course>/, повышает p95 first-answer без явного «обрабатываю…»,
    или vision-цена не помечена в usage_cost.
```
- **Конспект → реализация:** «Принимает мультимодальные входы (текст + скриншоты/файлы)»; модель M06 «Мультимодальный RAG».
- **Связь с killer feature:** новый источник сигналов для SSR («повтори концепт с этой диаграммы»).
- **Roadmap:** M06, расширяет существующий OCR/docling-ingest и `voice_service.py`.

### Волна U2 — Agent Transparency Panel: «что модель реально видела»

```yaml
- id: wave-agent-transparency-panel
  theme: "Прозрачность контекста: показать ученику, что попало в модель"
  north_star: >-
    debug_panel уже показывает routing-источник, llm-source badge, provenance и confidence-reasons,
    а ответ несёт sources; волна добавляет недостающее — read-only «context receipt» с фактами памяти
    и окном истории, чтобы ученик видел расхождение «что в чате vs что в модели».
  entry_mot: "#2 First Answer"
  exit_mot: "#8 Progress check"
  packages:
    - context-inspector-ux-v1     # «context receipt»: memory facts + history window поверх существующих debug_panel/sources
  kill_switch: >-
    Панель раскрывает сырой системный промпт/секреты, блокирует render >200ms p95,
    или дублирует SSR explanation, создавая шум.
```
- **Конспект → реализация:** «то, что видите вы, и что попадает в модель — разные вещи»; `debug_panel.py` + `sources` уже частично это показывают — пробел в **фактах памяти и окне истории**.
- **Связь с killer feature:** доводит **three-level explanation** SSR до основного answer-пути.
- **Roadmap:** усиливает SSR Explainability Engine.

### Волна U3 — Conversation Compaction + Profile Facts

```yaml
- id: wave-conversation-compaction-profile
  theme: "Управление контекстом: компакция диалога + извлечение устойчивых фактов в профиль"
  north_star: >-
    condense_step уже сжимает историю (скользящее окно + LLM-резюме); волна добавляет разрешение
    конфликтов устаревших фактов и извлечение устойчивых фактов об ученике в learner_model
    (дедуплицированы, с source-тегом), чтобы они не «болтались» в истории.
  entry_mot: "#5 Day 2: Resume"
  exit_mot: "cross-loop"
  packages:
    - conversation-compaction-v1  # stale-fact конфликт-резолвер поверх существующего condense_step
    - learner-profile-facts-v1    # extract durable facts → learner_model, dedupe, source-tag
  kill_switch: >-
    Компакция теряет факт, нужный для adaptive-plan; конфликт-резолвер закрепляет устаревший факт;
    извлечение пишет PII в незамаскированном виде.
```
- **Конспект → реализация:** «скользящее окно, резюме, извлечение фактов в профиль» — compaction уже в `condense_step.py`; пробел в **разрешении конфликтов** и **извлечении durable-фактов** в профиль.
- **Связь с killer feature:** даёт SSR стабильную персонализацию и снижает «lost in the middle».
- **Roadmap:** M07 (advanced context engineering); стыкуется с `condense_step.py`, `session_tape.py`, `learner_model_service.py`.

### Волна U4 — Human-in-the-Loop для критических действий

```yaml
- id: wave-hitl-critical-actions
  theme: "Human-in-the-loop: подтверждение перед необратимыми/критичными для state операциями"
  north_star: >-
    Ad-hoc confirm-гейты уже есть (course-deactivate, restore, tutor footer); волна добавляет единую
    confirm-policy для остальных необратимых операций (graduation, wipe progress) и memory-attack guard:
    заявления «я уже всё прошёл» не пишутся в learner_state без provenance события.
  entry_mot: "#9 Course Graduation"
  exit_mot: "#9 Course Graduation"
  packages:
    - critical-action-confirm-v1  # единая confirm-policy поверх ad-hoc гейтов (deactivate/restore уже есть)
    - memory-attack-guard-v1      # отклонять «я уже завершил X» без event-provenance (genuine gap)
  kill_switch: >-
    Гейт срабатывает на не-критичных действиях (friction), или обходится через прямой API
    без подтверждения.
```
- **Конспект → реализация:** «Human-in-the-loop для критических операций»; «Атака на память: ‘я уже оплатил’» — confirm-гейты уже есть ad-hoc (`mission_control`, `sidebar`, `tutor_chat_footer`); пробел — **единая policy** и **memory-attack guard**.
- **Связь с killer feature:** защищает целостность SSR outcome-receipts и graduation.
- **Roadmap:** дополняет `expert-controls` волну и golden-E2E graduation.

---

## 🚀 Слой 3 — Инфраструктура (observability, security, model ops)

> Конспект: «Observability/Langfuse», «Безопасность агента», «Локальный запуск моделей».

### Волна I1 — Langfuse Trace + Dataset Eval Loop

```yaml
- id: wave-langfuse-eval-loop
  theme: "Observability как у конспекта: Langfuse self-hosted + цикл trace→dataset"
  north_star: >-
    Сессии/инструменты/стоимость экспортируются в self-hosted Langfuse; из упавшего трейса — в один шаг
    создаётся eval-датасет; замыкается цикл «увидел ошибку → датасет → меняем промпт → прогон → деплой».
  entry_mot: "infra"
  exit_mot: "cross-loop"
  packages:
    - langfuse-trace-export-v1    # OTLP → Langfuse (sessions, cost, tool spans) поверх otel_tracing.py
    - trace-to-eval-dataset-v1    # «capture failing trace → eval dataset» в eval_service
  kill_switch: >-
    Экспорт шлёт незамаскированный PII (зависимость от I2), добавляет latency в hot-path,
    или дублирует существующие OTel-метрики, создавая двойной учёт.
```
- **Конспект → реализация:** «Langfuse: трейсы, датасеты, онлайн-метрики, маскирование, self-hosted; цикл улучшения агента (5 шагов)».
- **Связь с killer feature:** замыкает quality-loop SSR/tutor на реальных сессиях.
- **Roadmap:** M09 (Evaluation), усиливает `eval_service.py`/`router_eval.py`.

### Волна I2 — Redaction Sink Coverage (расширить существующий redactor)

```yaml
- id: wave-pii-masking-redaction
  theme: "Расширить существующий redact_sensitive_text на logs/traces/session-tape"
  north_star: >-
    redact_sensitive_text (guardrails.py) уже маскирует email/phone/API-keys, но применяется только
    к answer output и judge preview; волна расширяет его на структурные логи, OTel-трейсы и session_tape
    через единую policy с property-тестами против утечки PII в наблюдаемость.
  entry_mot: "infra"
  exit_mot: "infra"
  packages:
    - redaction-sink-coverage-v1  # применить существующий redactor к logs + tape + traces (не строить заново)
    - log-masking-policy-v1       # единая policy + property-тесты на отсутствие утечки
  kill_switch: >-
    Redaction ломает debuggability (маскирует слишком агрессивно нужные поля)
    или добавляет >5ms на лог-запись в hot-path.
```
- **Конспект → реализация:** «Маскирование чувствительных данных в логах»; redactor уже есть (`guardrails.py:redact_sensitive_text`) — пробел в **покрытии всех sink'ов** (logs/traces/tape), не в самом redactor.
- **Связь с killer feature:** делает Langfuse/observability безопасными для публичной защиты демо.
- **Roadmap:** предпосылка для I1; M09/M10 (prompt management & безопасность).

### Волна I3 — Adversarial Guardrails: Indirect Injection & Poisoning (direct injection / rate-limit уже есть)

```yaml
- id: wave-adversarial-guardrails
  theme: "Security-рельсы: косвенная (ingested) injection + отравление RAG-базы + per-loop tool limits"
  north_star: >-
    Поверх уже работающих detect_prompt_injection (direct, EN+RU) и HTTP RateLimitMiddleware:
    загружаемые документы санитизируются по содержимому (скрытый/instruction-like текст, «белый шрифт»),
    ingestion помечает подозрительные паттерны («всегда обещай/игнорируй правила»), а агентский tool-loop
    получает per-call лимиты — без регрессии легитимного контента.
  entry_mot: "infra"
  exit_mot: "#1 Local Setup"
  packages:
    - indirect-injection-guard-v1 # content-санитизация ingest: hidden-text / instruction-injection (direct уже в guardrails.py)
    - ingestion-poisoning-scan-v1 # флаг «always promise / ignore rules» паттернов на этапе индексации
    - agent-loop-tool-limiter-v1  # per-loop лимиты tool-вызовов агента (HTTP RateLimitMiddleware — отдельный слой)
  kill_switch: >-
    Скан даёт >2% false-positive на чистом корпусе, блокирует легитимную загрузку,
    или limiter рвёт golden-E2E.
```
- **Конспект → реализация:** «Prompt Injection (прямая/косвенная), отравление данных; guardrails, rate-limiters» — **прямая** injection (`detect_prompt_injection` + `INJECTION_PATTERNS`) и **HTTP** rate-limit (`RateLimitMiddleware`) уже есть; пробел — **косвенная** injection в ingested-контенте, **poisoning scan** и **per-loop** tool-лимиты.
- **Связь с killer feature:** защищает SSR **source-coverage guard** и source-trust overlay (защитная, авторизованная безопасность).
- **Roadmap:** M09 (Red teaming); стыкуется с `guardrails.py`, `adversarial_test_runner.py`, волной `quality-defense-adversarial-rag`.

### Волна I4 — RAGAS Retrieval-Quality + Correctness Eval

```yaml
- id: wave-ragas-eval-harness
  theme: "RAGAS: context_precision@k + answer_correctness (recall@k/MRR уже есть)"
  north_star: >-
    recall@k/MRR уже есть в eval_retrieval_comparison.py — RAGAS добавляет недостающие
    context_precision@k (rank-aware) и answer_correctness vs reference; прогон идёт на
    Langfuse-датасетах, результат сравним с baseline и блокирует регресс A3.
  entry_mot: "infra"
  exit_mot: "cross-loop"
  packages:
    - ragas-retrieval-metrics-v1  # context_precision/recall@k + answer_correctness в eval_service поверх faithfulness/answer_rel
    - ragas-langfuse-dataset-v1   # прогон RAGAS на Langfuse-датасетах + baseline-сравнение (зависит от I1)
  kill_switch: >-
    RAGAS-judge удваивает eval-стоимость без сигнала, метрики противоречат существующим
    faithfulness/answer_relevancy без объяснения, или прогон рвёт CI-gate.
```
- **Конспект → реализация:** «Langfuse: работа с датасетами и прогонами для оценки качества»; M09 (Evaluation). RAGAS дополняет, **не дублирует**, текущие LlamaIndex-evaluator'ы (`eval_service.py`, `compare_eval.py`, `async_quality_judge.py` уже считают faithfulness + answer_relevancy + context_relevancy).
- **Связь с killer feature:** retrieval-метрики напрямую валидируют **A3 Advanced RAG** и source-coverage, питающие SSR source-trust overlay.
- **Roadmap:** M09; зависит от **I1 Langfuse** (датасеты), усиливает `eval_service.py` / `router_eval.py`.

---

## 🗺️ Матрица: рекомендация конспекта → волна

| Раздел конспекта | Волна(ы) | Слой |
|---|---|---|
| Инструменты и MCP-протокол | A1 MCP Tool Plane | Архитектура |
| Типы моделей / несколько моделей + лайфхак «облако→вниз» | A2 Multi-Model Tier Router (+cost telemetry) | Архитектура |
| Продвинутый RAG (multi-query + reorder; rest shipped) | A3 Advanced RAG | Архитектура |
| Structured Output / Pydantic / «не выдумывай» | A4 Grounding Contract | Архитектура |
| Демо 8 субагентов / ReAct / M08 / M10–12 мультиагент | A5 Agentic Orchestrator + Subagents | Архитектура |
| Мультимодальный RAG (M06) | U1 Vision Intake | UX |
| Контекст: «что видит модель» | U2 Transparency Panel | UX |
| Контекст-стратегии + память/профиль | U3 Compaction + Profile | UX |
| Human-in-the-loop / атака на память | U4 HITL Critical Actions | UX |
| Observability / Langfuse / цикл улучшения | I1 Langfuse Eval Loop | Инфра |
| Маскирование чувствительных данных (расширить redactor) | I2 Redaction Sink Coverage | Инфра |
| Безопасность (косвенная injection / poisoning / per-loop limits) | I3 Adversarial Guardrails | Инфра |
| Evaluation / датасеты-прогоны (RAGAS-метрики) | I4 RAGAS Eval | Инфра |

---

## 📐 Рекомендуемая последовательность (sequencing)

Оптимальный порядок учитывает зависимости и быстрый user-visible эффект:

1. **I2 Redaction Sink Coverage** → расширить существующий `redact_sensitive_text` на logs/traces/tape (быстрая, низкорисковая).
2. **A4 Grounding Contract** → строгий контракт «abstain» повышает доверие к ответам сразу.
3. **A3 Advanced RAG** → multi-query + reorder поверх уже работающих rewrite/hybrid/rerank (инкремент; питает A4 источниками).
4. **I1 Langfuse Eval Loop** → замыкает измеримость, опирается на I2.
5. **I4 RAGAS Eval** → retrieval-метрики (precision/recall) валидируют A3; идёт на Langfuse-датасетах (зависит от I1).
6. **A2 Multi-Model Tier Router (+cost telemetry)** → удешевляет и ускоряет (синергия с Balanced Fallback).
7. **A1 MCP Tool Plane** → рефакторит доступ к инструментам как фундамент под мульти-агента.
8. **A5 Agentic Orchestrator + Subagents** → агентный router + parallel fan-out (зависит от A1; ускоряет folder→course).
9. **U2 Transparency Panel** → UX-доверие на готовом grounding (A4) и контексте.
10. **U3 Compaction + Profile** → стабильная персонализация для SSR.
11. **I3 Adversarial Guardrails** → защита перед публичным демо/деплоем.
12. **U4 HITL Critical Actions** → целостность graduation/receipts.
13. **U1 Vision Intake** → новая мультимодальная ценность (требует A2 vision-tier).

> **Первый «strong move» (1 спринт):** I2 → A4 → A3 — это безопасность логов + честный «не выдумывай» контракт + ощутимый рост качества RAG. Минимум риска, максимум доверия, и сразу видно на демо защиты.

---

## ✅ Как промоутить

Starter cluster (5 волн: `wave-pii-masking-redaction`, `wave-grounding-abstain-contract`, `wave-advanced-rag-rewrite-rerank`, `wave-langfuse-eval-loop`, `wave-ragas-eval-harness`) **уже promoted как `proposed`** 2026-06-05 — Truth View invariant сохранён (ни один не `ready`/`wip`; `active_wave_id`/`active_package_id` не изменены). Остальные 8 волн — кандидаты. Для запуска любой:

1. Owner выбирает 1–3 волны-кандидата (proposed → ready).
2. Запустить planning-вход: [`doc/team_workflow/generate_plan_next_prompt.md`](../team_workflow/generate_plan_next_prompt.md) — он сделает ranking, preflight `check_readset.py`, запишет контракт в `backlog_registry.yaml` как `ready` и регенерирует `tasklist.md`.
3. Orchestration — только после review принятого контракта.

> Это план, не код. Ни один файл рантайма не изменён. В `backlog_registry.yaml` добавлены только `proposed`-записи starter cluster + полный контракт `ragas-retrieval-metrics-v1`.

---

**Авторство:** сгенерировано по запросу «strong move / breakthrough» на основе `summary_01-ai-driven-design.md`.
**Связанные документы:** [smart_study_router.md](../smart_study_router.md) · [BREAKTHROUGH_SUMMARY.md](BREAKTHROUGH_SUMMARY.md) · [roadmap.md](../roadmap.md) · [backlog_registry.yaml](../backlog_registry.yaml)
