# Процесс работы команды над проектом

Актуализировано: **2026-05-03**

## Зачем этот документ

Проект `home-rag_v2` достиг зрелости: 14+ закрытых эпох, стабильная архитектура, развитая документация. Дальнейшее развитие требует чёткого разделения ролей и формализованного процесса, где каждая роль работает через AI-агента с заточенным промптом.

Этот документ описывает **кто**, **когда** и **с каким промптом** работает над проектом.

Навигация по промптам и сценариям: [`doc/prompts_usage_guide.md`](../prompts_usage_guide.md).

Быстрый выбор входа без перебора таблиц: [`workflow_decision_tree.md`](workflow_decision_tree.md) — там же матрица **лёгкий путь / полный конвейер**.

Перед закрытием пакета (`scripts/close_package.py`), если в `archive/team_artifacts/<PACKAGE_ID>/` есть канонические файлы пайплайна (`1_po_package.md`, …), автоматически запускается тот же контроль, что даёт `validate_team_artifact.py`. Обход: `--skip-team-artifacts-check`; строже: `--team-artifacts-strict`.

```bash
python scripts/validate_team_artifact.py --artifacts-dir archive/team_artifacts/<PACKAGE_ID>
```

## Процесс по шагам (сводная таблица)

> **Единая точка входа:** `python scripts/workflow.py` — автоматически определяет состояние и выдаёт следующую команду **только по `doc/backlog_registry.yaml`** (`doc/tasklist.md` роутер не читает). Детали: [`workflow_router.md`](workflow_router.md). Непрерывный handoff plan-next → оркестрация: `workflow.py --skip-review` (см. флаг в том файле). Ready-пакеты с `user_stories` или `cjm_moments` идут через orchestration-first даже при low mechanical complexity; прямой `execution_auto` предназначен для компактных maintenance/infra задач без US/CJM.

| Этап | Роль | Кратко что делает | Дальше по процессу |
|------|------|-------------------|---------------------|
| **Старт** | Человек | Запустить `python scripts/workflow.py` → получить следующий шаг | Зависит от состояния (см. ниже) |
| **Вход: plan-next** | Product Owner / plan-next | Нет активного пакета: ранжировать кандидатов, оформить контракт в `backlog_registry.yaml`, sync `tasklist.md`. Промпт: [`generate_plan_next_prompt.md`](generate_plan_next_prompt.md). | [`generate_orchestration_prompt.md`](generate_orchestration_prompt.md) или ручной старт фазы 1 |
| **Вход: оркестратор** | Человек + оркестратор | Есть `ready`/`wip`: сгенерировать промпт STEP 1–8 под агента. Промпт: [`generate_orchestration_prompt.md`](generate_orchestration_prompt.md). | Выполнить STEP 1 из `archive/team_artifacts/<ID>/orchestration_*.md` |
| **Вход: resume** | Человек + resume | Работа по пакету уже началась: восстановить контекст. Промпт: [`generate_resume_prompt.md`](generate_resume_prompt.md). | Продолжить с помеченного шага пайплайна |
| **1. Постановка** | Product Owner | Боль CJM, outcomes, привязка к US, пакет в реестре. [`product_owner.md`](product_owner.md) | Аналитик |
| **2. Требования** | Analyst | Given/When/Then, data flow, edge cases. [`analyst.md`](analyst.md) | Архитектор и Дизайнер (часто параллельно) |
| **3a. Контракт** | Architect | write-set, read-set, DoD, риски. [`architect.md`](architect.md) | Разработчик (вместе со спекой дизайнера) |
| **3b. Интерфейс** | Designer | UI/UX: layout, состояния, CJM. [`designer.md`](designer.md) | Разработчик |
| **3.5. Ops Impact Gate** _(условно)_ | RAGOps / LLMOps / MLOps | Параллельный обзор затронутых ops-слоёв. Выход: Impact Report (GREEN/YELLOW/RED). Триггеры — см. ниже «Ops Impact Gate (STEP 3.5)». [`ragops_engineer.md`](ragops_engineer.md) · [`llmops_engineer.md`](llmops_engineer.md) · [`mlops_engineer.md`](mlops_engineer.md) | Разработчик (с условиями из YELLOW reports) или Architect (если RED) |
| **4. Код** | Developer | Реализация и тесты по контракту. [`developer.md`](developer.md) | Тестировщик |
| **5. Приёмка** | Tester | Scope, DoD, регресс, вердикт PASS / CONDITIONAL / FAIL. [`tester.md`](tester.md) | PASS → закрытие; FAIL → возврат Разработчику |
| **6. Закрытие** | Product Owner | `closed_iterations.md`, `changelog.md`, статусы US/реестра | Вход: plan-next или новый пакет |
| **Вне цикла: архревью** | Architect | Architecture Review здоровья кодовой базы — не блокирует основной пайплайн | По триггерам в разделе ниже |

В шаблоне оркестратора один пакет может делиться на **sub-package** backend (sp1) и UI (sp2): STEP 4–5 → коммит → STEP 6–7 → STEP 8 closure — см. [`orchestrator_template.md`](orchestrator_template.md).

## Роли

### Базовые роли (всегда участвуют)

| # | Роль | Ответственность | Ключевой артефакт |
|---|------|----------------|-------------------|
| 1 | **Владелец продукта** (Product Owner) | Приоритеты, CJM, user stories, acceptance criteria | Обновлённый `backlog_registry.yaml` (SSoT), regenerated `tasklist.md`, user stories |
| 2 | **Архитектор** (Architect) | Техническая целостность, ADR, conventions, архитектурный review | Architecture review report, ADR |
| 3 | **Аналитик** (Analyst) | Детализация требований, acceptance criteria, data flow, edge cases | Детальные спецификации и acceptance criteria |
| 4 | **Дизайнер** (Designer) | UX-решения, UI-контракты, Streamlit layouts, CJM-соответствие | UI-спецификации, wireframes, UX-решения |
| 5 | **Разработчик** (Developer) | Реализация кода по контракту | Код, тесты, changed files |
| 6 | **Тестировщик** (Tester) | Верификация, регрессия, quality gates | Verify report, regression report |

### Ops-роли (подключаются по триггеру — STEP 3.5 Ops Impact Gate)

| # | Роль | Когда подключается | Ключевой артефакт |
|---|------|-------------------|-------------------|
| 7 | **RAGOps Engineer** ([`ragops_engineer.md`](ragops_engineer.md)) | Контракт трогает retrieval / chunks / indexes / citation / course corpus / `app/course_cache.py` / `data/docs/` | RAGOps Impact Report (GREEN / YELLOW / RED) |
| 8 | **LLMOps Engineer** ([`llmops_engineer.md`](llmops_engineer.md)) | Контракт трогает `app/provider.py`, prompt registry, `app/tutor_prompts.py`, profile-fallback, soft/hard timeout, banner | LLMOps Impact Report; разделение primary chat vs secondary channels |
| 9 | **MLOps Engineer** ([`mlops_engineer.md`](mlops_engineer.md)) | Контракт меняет embedding / reranker / router classifier / entity-relation extractor / chunking стратегию / eval dataset | MLOps Impact Report + rollback plan |
| 10 | **Performance Engineer / DevOps** ([`performance_devops.md`](performance_devops.md)) | Контракт трогает latency / cost / readiness / `scripts/local_*`, `.env.example`, ingest throughput, CI workflows, observability | Performance Impact Report + post-release watch |

Полное описание Ops-ролей, их KPI, RACI и mapping на реальные модули `home-rag_v2` — в [`rag_llm_ops_project_document.md`](rag_llm_ops_project_document.md) (§5, §6, §7, §10–§12, §31–§35); тактические инструменты Performance/DevOps — [`budget_health_prompt.md`](budget_health_prompt.md), [`generate_bottleneck_analysis_prompt.md`](generate_bottleneck_analysis_prompt.md).

> **Принцип подключения Ops:** Ops-роль это **не отдельный шаг конвейера, а gate-обзор**, который вставляется после Architect+Designer (STEP 3) и **до** Developer (STEP 4). Если триггер не сработал — gate пропускается без вреда для скорости.

## Последовательность работы (Pipeline)

Каждая эпоха / пакет проходит через конвейер ролей:

```
┌─────────────┐     ┌────────────┐     ┌───────────┐
│   Product    │────>│  Analyst   │────>│ Architect │
│   Owner      │     │            │     │           │
└─────────────┘     └────────────┘     └─────┬─────┘
                                             │
                                             v
┌─────────────┐     ┌────────────┐     ┌───────────┐
│   Tester    │<────│  Developer │<────│ Designer  │
│             │     │            │     │           │
└──────┬──────┘     └────────────┘     └───────────┘
       │
       v
  [PASS] ──> Закрытие пакета
  [FAIL] ──> Возврат Разработчику
```

### Фаза 1: Постановка (Product Owner)

**Вход:** потребность пользователя, CJM-боль, feedback, метрики.
**Выход:** приоритизированный пакет в `backlog_registry.yaml` с привязкой к CJM и user story.

Промпт-файл: [`product_owner.md`](product_owner.md)

Что делает:
- Анализирует текущий `doc/backlog_registry.yaml`, `cjm.md`, `future_roadmap.md`; `tasklist.md` только как generated display
- Выбирает top-pain point
- Определяет пакет фичей (max 5)
- Формирует высокоуровневые Acceptance Criteria (через US)
- Обновляет реестр `backlog_registry.yaml` и синхронизирует `tasklist.md`

### Фаза 2: Детализация (Analyst)

**Вход:** пакет от PO с CJM-привязкой и верхнеуровневыми AC.
**Выход:** детальная спецификация с acceptance criteria, data flow, edge cases.

Промпт-файл: [`analyst.md`](analyst.md)

Что делает:
- Читает user stories целевого пакета
- Детализирует acceptance criteria до Given/When/Then
- Описывает data flow через существующие модули
- Выявляет edge cases и зависимости
- Готовит спецификацию для Архитектора и Дизайнера

### Фаза 3: Архитектурное решение (Architect)

**Вход:** спецификация от Аналитика.
**Выход:** execution contract (write-set, read-set, do-not-touch, DoD, risks).

Промпт-файл: [`architect.md`](architect.md)

Что делает:
- Проверяет соответствие conventions и ADR
- Определяет write-set и границы изменений
- Выявляет архитектурные риски
- Формирует execution contract для Разработчика
- При необходимости создаёт новый ADR

### Фаза 4: UX-решение (Designer)

**Вход:** спецификация от Аналитика + execution contract от Архитектора.
**Выход:** UI-спецификация с layout, компонентами, состояниями.

Промпт-файл: [`designer.md`](designer.md)

Что делает:
- Проверяет CJM-соответствие
- Определяет UI-компоненты и их состояния
- Описывает layout и navigation flow
- Проверяет консистентность с существующим UI
- Формирует UI-контракт для Разработчика

### Фаза 5: Реализация (Developer)

**Вход:** execution contract от Архитектора + UI-спецификация от Дизайнера.
**Выход:** код + тесты + changed files.

Промпт-файл: [`developer.md`](developer.md)

Что делает:
- Выполняет scan → plan → edit → verify → sync docs
- Работает строго в рамках write-set
- Пишет целевые тесты
- Не выходит за scope контракта

### Фаза 6: Верификация (Tester)

**Вход:** результат Разработчика + execution contract + acceptance criteria.
**Выход:** verify report (PASS / CONDITIONAL PASS / FAIL).

Промпт-файл: [`tester.md`](tester.md)

Что делает:
- Scope check: только файлы из write-set
- DoD checklist: каждый критерий проверен
- Spot check качества кода
- Regression check
- Вердикт с обоснованием

## Правила взаимодействия

### WIP = 1
В каждый момент времени активен только один пакет. Следующий пакет не начинается, пока текущий не получил PASS от Тестировщика.

### Handoff-контракт
Каждая роль передаёт следующей структурированный артефакт (не свободный текст). Формат артефакта определён в промпте роли.

### Эскалация
Если роль обнаруживает проблему за пределами своей компетенции:
- Designer -> Architect: если UX-решение требует архитектурных изменений
- Developer -> Architect: если write-set недостаточен
- Tester -> Product Owner: если acceptance criteria неполны или противоречивы
- Analyst -> Product Owner: если user story не покрывает сценарий

### Источники истины

| Что | Где |
|-----|-----|
| Backlog и статусы | `doc/backlog_registry.yaml` (SSoT) -> `doc/tasklist.md` |
| CJM и боли | `doc/cjm.md` |
| User stories | `doc/user_stories/` |
| Conventions | `doc/conventions.md` + architecture/reference |
| ADR | `doc/adr.md` |
| Закрытые эпохи | `doc/closed_iterations.md` |
| Код | `app/`, `tests/`, `scripts/` |

### Документация конфликтует с кодом?
Верить коду и `doc/backlog_registry.yaml`, потом синхронизировать производный markdown.

## Жизненный цикл пакета

```
1. PO: формирует пакет          → backlog_registry.yaml updated
2. Analyst: детализирует         → spec + AC ready
3. Architect: планирует          → execution contract ready
4. Designer: проектирует UI      → UI spec ready (если есть UI)
5. Developer: реализует          → code + tests ready
6. Tester: верифицирует          → PASS / FAIL
7. PO: закрывает пакет           → closed_iterations.md + changelog.md
```

Шаги 3 и 4 могут идти параллельно, если write-set'ы не пересекаются.

### Триггер: Ops Impact Gate (STEP 3.5)

Подключается между Architect+Designer (STEP 3) и Developer (STEP 4) для пакетов, затрагивающих RAG / LLM / ML слой. Канонический список триггеров — [`rag_llm_ops_project_document.md` §35](rag_llm_ops_project_document.md#35-hook-в-team-workflow-процесс):

| Файл / область write-set | Срабатывает Ops-роль |
|---|---|
| `app/provider.py` | LLMOps |
| `app/config.py` (новые LLM / embeddings / profile ключи) | LLMOps |
| `app/prompts/` или `app/tutor_prompts.py` | LLMOps |
| `app/query_service.py`, `app/pipeline_steps.py` | RAGOps |
| `app/course_cache.py`, `app/ui/study_scope.py`, `data/docs/<...>/` | RAGOps |
| `app/knowledge_graph.py` | MLOps + RAGOps |
| Индексы / chunks / embeddings (включая `INGESTION_MODEL`, chunking strategy) | MLOps + RAGOps |
| `scripts/local_readiness.py`, `app/ui/llm_local_banner.py` | LLMOps + Designer + Performance |
| `scripts/local_*.{py,ps1}`, `.env.example`, новые таймауты / budgets / зависимости | Performance |
| Ingest throughput, новые ingestion-pipeline шаги | Performance + RAGOps |
| Dockerfile / CI workflows / GitHub Actions | Performance (sole) |

**Verdict routing:**

- **GREEN** во всех сработавших gate → Developer проходит без условий.
- **YELLOW** → Developer добавляет условия в `{{ARTIFACTS_DIR}}/deferred.md` или в DoD как доп. тесты.
- **RED** в любом gate → Architect ревизирует контракт; gate перезапускается. Без RED-resolution Developer не стартует.

Если ни один файл из триггер-списка не затронут — gate **пропускается** без вреда для скорости.

### Триггер: Architecture Review (вне основного pipeline)

Architecture Review (Architect Prompt 2) запускается отдельно — не как шаг pipeline,
а как периодическая операция здоровья кодовой базы:

- **Автоматический триггер:** после каждого 3-го закрытого пакета.
- **Ручной триггер:** если write-set любого пакета затронул > 8 файлов.
- **Выход:** структурированный отчёт (findings + metrics snapshot), сохраняется в
  `archive/architecture_review_<YYYY-MM-DD>.md`.
- Не блокирует текущий pipeline — выполняется между эпохами.

## Файлы промптов

| Роль | Файл |
|------|------|
| Product Owner | [`product_owner.md`](product_owner.md) |
| Architect | [`architect.md`](architect.md) |
| Analyst | [`analyst.md`](analyst.md) |
| Designer | [`designer.md`](designer.md) |
| Developer | [`developer.md`](developer.md) |
| Tester | [`tester.md`](tester.md) |
| RAGOps Engineer _(условно, STEP 3.5)_ | [`ragops_engineer.md`](ragops_engineer.md) |
| LLMOps Engineer _(условно, STEP 3.5)_ | [`llmops_engineer.md`](llmops_engineer.md) |
| MLOps Engineer _(условно, STEP 3.5)_ | [`mlops_engineer.md`](mlops_engineer.md) |
| Performance Engineer / DevOps _(условно, STEP 3.5)_ | [`performance_devops.md`](performance_devops.md) |

## Генераторы промптов

| Сценарий | Файл |
|----------|------|
| **Единая точка входа (рекомендуется)** | [`workflow_router.md`](workflow_router.md) → `python scripts/workflow.py` |
| Backlog пустой / нужно выбрать следующий пакет | [`generate_plan_next_prompt.md`](generate_plan_next_prompt.md) |
| Есть принятый активный продуктовый контракт с US/CJM | [`generate_orchestration_prompt.md`](generate_orchestration_prompt.md) |
| Есть low-complexity maintenance/infra контракт без US/CJM | `python scripts/workflow.py` → `execution_auto` |
| Работа по пакету уже начиналась | [`generate_resume_prompt.md`](generate_resume_prompt.md) |
| Вся цепочка аудита закрытых пакетов end-to-end | [`run_audit_chain_prompt.md`](run_audit_chain_prompt.md) |
| Аудит закрытых пакетов за период и проверка SSoT/DoD replay | [`generate_audit_closed_packages_prompt.md`](generate_audit_closed_packages_prompt.md) |
| Добивка unit/e2e DoD-покрытия по audit-группам | [`generate_audit_packages_coverage_prompt.md`](generate_audit_packages_coverage_prompt.md) |

Цепочка аудита закрытых пакетов:

0. [`run_audit_chain_prompt.md`](run_audit_chain_prompt.md) — мастер-вход, который проводит шаги ниже до выбранной handoff-точки.
1. [`generate_audit_closed_packages_prompt.md`](generate_audit_closed_packages_prompt.md) создаёт `audit_prompt_${PERIOD_SLUG}_${TARGET_AGENT}.md`.
2. Выполнение audit prompt создаёт/использует `audit_groups_${PERIOD_SLUG}_${TARGET_AGENT}/group_*.md`, `run_next_group_coverage_audit.md`, `coverage_dod_analysis.md`.
3. [`generate_audit_packages_coverage_prompt.md`](generate_audit_packages_coverage_prompt.md) создаёт `audit_coverage_prompt_${PERIOD_SLUG}_${TARGET_AGENT}.md`.
4. Выполнение coverage prompt добавляет недостающие тесты/DoD-команды, пишет group coverage reports, обновляет `_audit_raw.json` и refresh `coverage_dod_analysis.md`.

Описание автоматизации процесса: [`automation.md`](automation.md)
