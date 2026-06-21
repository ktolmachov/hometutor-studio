# 📚 Каталог Промптов

> Полный справочник всех ключевых промптов в проекте с текстами, сгруппированные по ролям и сценариям.
> Актуализирован: **2026-05-06**
> 
> **Быстро найти промпт:** используйте Ctrl+F и ищите его имя или роль

---

## 🤖 Промпты Для AI-Агентов

Эти промпты используются для управления workflow'ом разработки через AI-агентов.

### Ядро: Цикл Plan → Execute → Verify

| Промпт | Роль | Где находится | Описание | Текст |
|---|---|---|---|---|
| **Planning Prompt** | Планировщик | [agent_workflow_templates.md](agent_workflow_templates.md#шаблон-planning-prompt-рекомендуемый-по-умолчанию) | Планирование новой итерации / пакета. Производит execution contract с write-set, read-set, DoD. Не пишет код. | [📋 Копировать](#planning-prompt-планирование-пакета) |
| **Execution Contract** | Разработчик | [agent_workflow_templates.md](agent_workflow_templates.md#контрактный-prompt-для-ударных-пакетов) | Быстрый шаблон для выполнения одного пакета: goal, scope, read-set, DoD, do-not-touch. | [📋 Копировать](#execution-contract-контрактный-промпт) |
| **Verify Prompt** | Верификатор | [agent_workflow_templates.md](agent_workflow_templates.md#verify-prompt--проверка-выполненного-пакета) | Проверка выполненного пакета по контракту. Выдаёт PASS / CONDITIONAL PASS / FAIL. | [📋 Копировать](#verify-prompt-верификация-пакета) |
| **Architecture Review Prompt** | Архитектор | [agent_workflow_arch_review.md](agent_workflow_arch_review.md#шаблон-architecture-review-prompt) | Периодический архитектурный аудит (Phase 1–5). Находит нарушения соглашений, мёртвый код, drift документации. | [📋 Копировать](#architecture-review-prompt-архитектурный-аудит) |

### Генерация Контрактов

| Промпт | Роль | Где находится | Описание |
|---|---|---|---|
| **product_owner_router** | PO / Навигация | [team_workflow/product_owner_router.md](team_workflow/product_owner_router.md) | Модульный роутер v2.1 (8 файлов). Единая точка входа для PO: Decision Table, Step 0 Registry Health Check, Flow, Smart Study Router status (US-20.1–20.12 closed). Ссылки на 7 модулей ниже. |
| **po_router_conflicts** | PO / Навигация | [team_workflow/po_router_conflicts.md](team_workflow/po_router_conflicts.md) | Правила разрешения конфликтов: proposed/deferred/parallel ideation runs. |
| **po_router_scope_matrix** | PO / Навигация | [team_workflow/po_router_scope_matrix.md](team_workflow/po_router_scope_matrix.md) | Cohesion assessment: 1 идея → package, 2 → зависит, 3+ cohesive → wave. |
| **po_router_escape_hatches** | PO / Навигация | [team_workflow/po_router_escape_hatches.md](team_workflow/po_router_escape_hatches.md) | 4 escape-сценария: 0 viable, пустой backlog, owner paralysis, scope explosion. |
| **po_router_anti_patterns** | PO / Навигация | [team_workflow/po_router_anti_patterns.md](team_workflow/po_router_anti_patterns.md) | 7 типичных ошибок PO workflow + red flag таблица. |
| **po_router_handoffs** | PO / Навигация | [team_workflow/po_router_handoffs.md](team_workflow/po_router_handoffs.md) | Handoff промпты: PO ↔ Analyst ↔ Architect ↔ Execution. Checkpoint перед handoff. |
| **po_router_parallel_waves** | PO / Навигация | [team_workflow/po_router_parallel_waves.md](team_workflow/po_router_parallel_waves.md) | Write-set isolation, merge gate checklist, когда (не) использовать параллельные волны. |
| **po_router_retrospectives** | PO / Навигация | [team_workflow/po_router_retrospectives.md](team_workflow/po_router_retrospectives.md) | Feedback loop: YAML-схема ретроспективы, health metrics, timing/cadence SLAs. |
| **generate_plan_next_prompt** | PO / Аналитик | [team_workflow/generate_plan_next_prompt.md](team_workflow/generate_plan_next_prompt.md) | Когда backlog пуст/устарел: выбрать 1–3 кандидата из контекста ([backlog_registry.yaml](backlog_registry.yaml) SSoT, CJM и др.), preflight token-check, после accept — контракт в реестр и регенерация [tasklist.md](tasklist.md). При `blocker: no eligible…` — см. ниже **breakthrough / PO plan package**. Resume пакета — отдельно: [generate_resume_prompt](team_workflow/generate_resume_prompt.md). |
| **generate_breakthrough_ideation_prompt** | PO / Стратегия | [team_workflow/generate_breakthrough_ideation_prompt.md](team_workflow/generate_breakthrough_ideation_prompt.md) | Новые гипотезы по `TARGET` (CJM / US / pain / feature): режим **полный** (`TARGET` + `N_IDEAS`, артефакт `archive/ideation/…`); режим **таблица** `MODE=CANDIDATE_TABLE` — обзор строк из CJM + user stories + roadmap перед выбором `TARGET`. После идей — упаковка одного пакета: [product_owner_plan_package_prompt](team_workflow/product_owner_plan_package_prompt.md). Отличия от plan-next — в шапке того файла. |
| **generate_roadmap_epoch_waves_prompt** | PO / Стратегический планировщик | [team_workflow/generate_roadmap_epoch_waves_prompt.md](team_workflow/generate_roadmap_epoch_waves_prompt.md) | Post-ideation перенос owner-approved horizon или `archive/ideation/...` artifact в `backlog_registry.yaml` как proposed waves/packages. Запускать после review, если 3+ связанные идеи требуют multi-wave delivery; не использовать как первый шаг для сырой идеи. |
| **generate_orchestration_prompt** | Оркестратор | [team_workflow/generate_orchestration_prompt.md](team_workflow/generate_orchestration_prompt.md) | Сгенерировать полный prompt для team-workflow: найти пакет, собрать контекст (CJM, user stories), выстроить последовательность шагов по ролям. |
| **generate_execution_prompt_auto** | Инженер | [team_workflow/generate_execution_prompt_auto.md](team_workflow/generate_execution_prompt_auto.md) | Автоматический выбор и генерация execution-prompt на основе текущего состояния backlog. |
| **generate_resume_prompt** | Инженер | [team_workflow/generate_resume_prompt.md](team_workflow/generate_resume_prompt.md) | Resume существующего пакета из архива артефактов. Восстанавливает контекст, проверяет commits, вычисляет delta работы. |
| **run_audit_chain_prompt** | QA / Orchestrator | [team_workflow/run_audit_chain_prompt.md](team_workflow/run_audit_chain_prompt.md) | Мастер-промпт всей audit/coverage цепочки: генерирует и выполняет main audit prompt, проверяет audit-группы, генерирует coverage prompt, выполняет выбранные группы и сверяет reports, `_audit_raw.json`, `coverage_dod_analysis.md`. Текст запуска: [Audit Chain Master Prompt](#audit-chain-master-prompt). |
| **ssot_full_audit_prompt** | QA / Verifier | [../archive/doc_team_workflow/ssot_full_audit_prompt.md](../archive/doc_team_workflow/ssot_full_audit_prompt.md) | Готовый prompt для проверки утверждения по `CJM + user_stories_index + backlog_registry` с full audit chain, coverage и DoD replay. |
| **generate_audit_closed_packages_prompt** | QA / PO | [team_workflow/generate_audit_closed_packages_prompt.md](team_workflow/generate_audit_closed_packages_prompt.md) | Периодический аудит пакетов со статусом closed (и опционально wip): сверка backlog_registry ↔ closed_iterations ↔ user_stories_index, при DEPTH=dod_replay — DoD replay; генератор выдаёт самодостаточный промпт для нового чата. Эталон копипасты: [Closed Packages Audit — снимок](#closed-packages-audit-snapshot-2026-04-20-cursor-ai). |
| **generate_audit_packages_coverage_prompt** | QA / Tester | [team_workflow/generate_audit_packages_coverage_prompt.md](team_workflow/generate_audit_packages_coverage_prompt.md) | Генерирует standalone coverage-completion prompt после audit-групп: проверяет полноту unit/e2e/fixture/eval покрытия по связке package ↔ CJM ↔ US, добавляет недостающие тесты/DoD-команды, обновляет `_audit_raw.json` и refresh `coverage_dod_analysis.md`. Текст запуска: [Audit Coverage Prompt Generator](#audit-coverage-prompt-generator). |
| **reopen_package_step_c_prompt** | PO / QA | [team_workflow/reopen_package_step_c_prompt.md](team_workflow/reopen_package_step_c_prompt.md) | **Один пакет:** готовый текст Step C (`closed` → `ready`) для вставки в новый чат — registry, `closed_iterations`, US-index + frontmatter, CJM, changelog, **[current_task.md](current_task.md)** (runtime), `backlog_registry_lint`, коммит. Префлайт без правок: `scripts/print_reopen_package_workflow.py --package <id>`. Канон подшагов: [generate_audit_closed_packages_prompt § STEP C](team_workflow/generate_audit_closed_packages_prompt.md). |
| **reopen_prompt_closed_window_template** | PO / QA | [team_workflow/reopen_prompt_closed_window_template.md](team_workflow/reopen_prompt_closed_window_template.md) | Батч **административного** переоткрытия пакетов `closed→ready` за окно `PERIOD` через Step C всех индексов (см. [generate_audit_closed_packages_prompt](team_workflow/generate_audit_closed_packages_prompt.md)); параметрический шаблон. Пример «последние 3 дня»: [§](#reopen-batch-closed-window-last3days-example); файл-снимок: [reopen_instance_last3days_2026-04-26__2026-04-28.md](../archive/team_workflow_snapshots/reopen_instance_last3days_2026-04-26__2026-04-28.md). |

### Примеры промптов для вставки в новый чат (копипаст)

Готовые полные тексты — в разделе **«🔤 Тексты промптов (Копируй и Вставляй)»** ниже по странице. Краткая навигация:

| Что это | Основа | Перейти к тексту |
|---------|--------|-------------------|
| **Переоткрыть один закрытый пакет** (Step C, копипаста, без полного audit-промпта) | [reopen_package_step_c_prompt.md](team_workflow/reopen_package_step_c_prompt.md) | [фрагмент с текстом](team_workflow/reopen_package_step_c_prompt.md#reopen-step-c-paste) |
| **Переоткрыть закрытые за последние 3 календарных дня** по [reopen_prompt_closed_window_template.md](team_workflow/reopen_prompt_closed_window_template.md); снимок окна на 2026-04-26..2026-04-28 | [reopen_instance_last3days_2026-04-26__2026-04-28.md](team_workflow/reopen_instance_last3days_2026-04-26__2026-04-28.md) | [📋 переоткрытие последних 3 дней](#reopen-batch-closed-window-last3days-example) |
| Мастер-промпт **всей цепочки аудита** | [run_audit_chain_prompt.md](team_workflow/run_audit_chain_prompt.md) | [📋 audit chain](#audit-chain-master-prompt) |
| Полная проверка **CJM + US-index + backlog SSoT** с audit chain / DoD | [ssot_full_audit_prompt.md](../archive/doc_team_workflow/ssot_full_audit_prompt.md) | [📋 SSoT full audit](../archive/doc_team_workflow/ssot_full_audit_prompt.md) |
| Снимок **цепочки аудита 2026-04 / cursor_ai** | [audit_chain_prompt_2026-04_cursor_ai.md](../archive/doc_team_workflow/audit_chain_prompt_2026-04_cursor_ai.md) | [📋 audit chain](#audit-chain-master-prompt) |
| Снимок **аудита** closed/wip (пример параметров) | [generate_audit_closed_packages_prompt.md](team_workflow/generate_audit_closed_packages_prompt.md); [audit_prompt_2026-04-20__2026-04-28_cursor_ai.md](../archive/team_workflow_snapshots/audit_prompt_2026-04-20__2026-04-28_cursor_ai.md) | [📋 аудит SSoT — снимок](#closed-packages-audit-snapshot-2026-04-20-cursor-ai) |
| Генератор **DoD coverage completion** по audit-группам | [generate_audit_packages_coverage_prompt.md](team_workflow/generate_audit_packages_coverage_prompt.md); [audit_coverage_prompt_2026-04_cursor_ai.md](../archive/doc_team_workflow/audit_coverage_prompt_2026-04_cursor_ai.md) | [📋 coverage generator](#audit-coverage-prompt-generator) |

### Мониторинг и Здоровье

| Промпт | Роль | Где находится | Описание | Текст |
|---|---|---|---|---|
| **Kilo Budget Health Prompt** | DevOps / Monitor | [team_workflow/budget_health_prompt.md](team_workflow/budget_health_prompt.md) | Ежедневная проверка бюджета токенов: margins, consumed, projected. Диагностирует overflow, предлагает override или re-plan. | [📋 Копировать](#kilo-budget-health-check) |
| **Demo Scenarios Prompt Bundle** | Demo Runner | [team_workflow/demo_scenarios_prompt_bundle.md](team_workflow/demo_scenarios_prompt_bundle.md) | Bundle для прогона сценариев demo (E2E автоматизированные тесты). Вводит seeded data, проверяет видимые результаты. | – |
| **Bottleneck Analysis Prompt** | Performance Engineer | [team_workflow/generate_bottleneck_analysis_prompt.md](team_workflow/generate_bottleneck_analysis_prompt.md) | Анализ производительности пайплайна по JSON/MD-отчёту `scripts/analyze_bottlenecks.py`: вход `archive/team_artifacts/_timing/`, output `logs/bottlenecks/`, не `logs/cost_logs/`. | – |

### Локальный smoke: пакет `epoch-demo`

| Промпт | Роль | Где находится | Описание | Текст |
|---|---|---|---|---|
| **Epoch-Demo: package + `run_autonomous` smoke** | Dev / QA | [print_epoch_demo_agent_prompts.py](../scripts/print_epoch_demo_agent_prompts.py) · [print_reopen_package_workflow.py](../scripts/print_reopen_package_workflow.py) | Два эталонных текста: подготовка пакета `epoch-demo` (registry entry, generated tasklist, артефакты, демо-функция в `scripts/prompt_utils.py`, переоткрытие по канону Step C при `closed`) и отдельно — **реальный** smoke CLI `run_autonomous.py --post-agent`. **Печать:** `print_epoch_demo_agent_prompts.py` с аргументами `package`, `smoke` или `all`. **Префлайт статуса:** `print_reopen_package_workflow.py --package epoch-demo`. | [📋 Копировать](#epoch-demo-local-smoke-prompts) |

---

## 👥 Промпты Для Команды (Ролевые)

Эти промпты описывают, как должна работать каждая роль в team-workflow процессе.

| Роль | Промпт-инструкция | Где находится | Суть работы | Текст |
|---|---|---|---|---|
| **Product Owner** | Шаг 1: Контекст задачи | [team_workflow/product_owner.md](team_workflow/product_owner.md) | Связать задачу с CJM и user story. Убедиться, что есть бизнес-обоснование. | [📋 Копировать](#product-owner) |
| **Analyst** | Шаг 2: Сценарии | [team_workflow/analyst.md](team_workflow/analyst.md) | Разобрать сценарии через Given-When-Then. Подготовить acceptance criteria. | [📋 Копировать](#analyst) |
| **Architect** | Шаг 3a: Дизайн решения | [team_workflow/architect.md](team_workflow/architect.md) | Выбрать стратегию реализации, определить write-set файлов, risks, boundaries. | [📋 Копировать](#architect) |
| **Designer** | Шаг 3b: UI/UX контракт | [team_workflow/designer.md](team_workflow/designer.md) | Описать изменения UI (если есть): макеты, flow, состояния, accessibility. | [📋 Копировать](#designer) |
| **Developer** | Шаг 4: Реализация | [team_workflow/developer.md](team_workflow/developer.md) | Писать код строго по контракту Архитектора. Тесты, documentation sync. | [📋 Копировать](#developer) |
| **Tester** | Шаг 5: Верификация | [team_workflow/tester.md](team_workflow/tester.md) | Проверить scope, DoD, качество кода, regression. Выдать PASS/FAIL/CONDITIONAL. | [📋 Копировать](#tester) |
| **RAGOps Engineer** | Шаг 3.5: Ops Impact Gate (RAG) | [team_workflow/ragops_engineer.md](team_workflow/ragops_engineer.md) | Review retrieval / index / citation / course-scope impact. Owner Course Delight Loop ([rag_llm_ops_project_document.md §33](team_workflow/rag_llm_ops_project_document.md#33-course-delight-loop-ownership-matrix)). Выдаёт RAGOps Impact Report (GREEN / YELLOW / RED). | – |
| **LLMOps Engineer** | Шаг 3.5: Ops Impact Gate (LLM) | [team_workflow/llmops_engineer.md](team_workflow/llmops_engineer.md) | Review primary chat fallback, profile-aware policy (`LOCAL_STRICT` / `BALANCED` / `CLOUD_FAST`), prompt registry. Разделяет primary chat vs secondary LLM channels ([rag_llm_ops_project_document.md §31](team_workflow/rag_llm_ops_project_document.md#31-primary-chat-llm-vs-secondary-llm-channels)). | – |
| **MLOps Engineer** | Шаг 3.5: Ops Impact Gate (ML) | [team_workflow/mlops_engineer.md](team_workflow/mlops_engineer.md) | Review embedding / reranker / router / extractor / eval impact; version registry; rollback plan; reproducibility по профилям. | – |
| **Performance Engineer / DevOps** | Шаг 3.5: Ops Impact Gate (Perf / Infra) | [team_workflow/performance_devops.md](team_workflow/performance_devops.md) | Review latency / cost / readiness / deployment / observability. Owner Local Control Center и profile-aware KPI monitoring. Тактические инструменты роли: [budget_health_prompt.md](team_workflow/budget_health_prompt.md), [generate_bottleneck_analysis_prompt.md](team_workflow/generate_bottleneck_analysis_prompt.md). | – |

> **Когда срабатывает 3.5 gate:** см. [orchestrator_template.md § STEP 3.5](team_workflow/orchestrator_template.md) и список триггеров в [rag_llm_ops_project_document.md §35](team_workflow/rag_llm_ops_project_document.md#35-hook-в-team-workflow-процесс). Если ни один файл из списка триггеров не затронут — gate **пропускается** без вреда для скорости. Performance/DevOps добавляет собственные триггеры (latency / cost / readiness / deployment / CI) — полный список в [performance_devops.md](team_workflow/performance_devops.md).

---

## 🛠️ Адаптеры (Для разных инструментов)

Эти файлы описывают, как адаптировать workflow для конкретного AI-инструмента.

| Инструмент | Адаптер | Где находится | Специфика |
|---|---|---|---|
| **Claude Code** | Agent Adapter | [team_workflow/guides/agent_adapter_claude_code.md](team_workflow/guides/agent_adapter_claude_code.md) | Параллельный запуск через Agent tool call, синтаксис передачи артефактов, обработка FAIL. |
| **Cursor AI** | Agent Adapter | [team_workflow/guides/agent_adapter_cursor_ai.md](team_workflow/guides/agent_adapter_cursor_ai.md) | Cursor-специфичные команды, inline edits, UI интеграция. |
| **Codex CLI** | Agent Adapter | [team_workflow/guides/agent_adapter_codex.md](team_workflow/guides/agent_adapter_codex.md) | OpenAI Codex CLI, последовательный запуск, shell-integration. |
| **Kilo** | Agent Adapter | [team_workflow/guides/agent_adapter_kilo.md](team_workflow/guides/agent_adapter_kilo.md) | Managed Agent, async execution, cloud deployment. |

---

## 🧬 Примеры (Исполненные Истории)

Полные примеры выполненных пакетов от start до finish.

| Пакет | Пример | Где находится | Что показывает |
|---|---|---|---|
| **E15A Orchestration (Claude Code)** | Full cycle | [team_workflow/examples/example_e15a_orchestration_level3_in_agent_claude_code.md](team_workflow/examples/example_e15a_orchestration_level3_in_agent_claude_code.md) | Полный пример от planning до verify в Claude Code. |
| **E15A Orchestration (Cursor AI)** | Full cycle | [team_workflow/examples/example_e15a_orchestration_level3_in_agent_cursor_ai.md](team_workflow/examples/example_e15a_orchestration_level3_in_agent_cursor_ai.md) | Полный пример от planning до verify в Cursor AI. |
| **E15A Orchestration (Codex)** | Full cycle | [team_workflow/examples/example_e15a_orchestration_level3_in_agent_codex.md](team_workflow/examples/example_e15a_orchestration_level3_in_agent_codex.md) | Полный пример от planning до verify в OpenAI Codex. |
| **Flashcards + Bugfix** | Mixed scope | [team_workflow/examples/example_flashcards_and_bugfix.md](team_workflow/examples/example_flashcards_and_bugfix.md) | Пример параллельного пакета (feature + bug fix). |

---

## 🚀 Процесс (Высокоуровневые Инструкции)

| Тип | Описание | Где находится | Текст |
|---|---|---|---|
| **⭐ Workflow Router** | **Единая точка входа** — `python scripts/workflow.py` определяет состояние и следующий шаг; `--skip-review` — без паузы на ревью контракта после plan-next | [team_workflow/workflow_router.md](team_workflow/workflow_router.md) | – |
| **Team Workflow Process** | Полное описание 8-шагового процесса | [team_workflow/process.md](team_workflow/process.md) | – |
| **Team Workflow Automation** | Автоматизированные скрипты и hooks | [team_workflow/automation.md](team_workflow/automation.md) | – |
| **Start Workflow** _(legacy)_ | PowerShell-запуск (устарело — см. Workflow Router) | [team_workflow/start_workflow.md](team_workflow/start_workflow.md) | [📋 Копировать](#start-workflow) |
| **Run Start Workflow Prompt** | Промпт для агента для E2E запуска workflow (вызов скриптов PowerShell) | [team_workflow/run_start_workflow_prompt.md](team_workflow/run_start_workflow_prompt.md) | – |
| **Run Autonomous** | Как запустить autonomous режим (без паузы) | [team_workflow/run_autonomous.md](team_workflow/run_autonomous.md) | – |
| **Run Autonomous Runbook** | v3 runtime: state/result/proof/replay/gates/evals/observability | [team_workflow/run_autonomous_runbook.md](team_workflow/run_autonomous_runbook.md) | – |
| **Run Autonomous Prompt** | Готовый prompt для autonomous режима | [team_workflow/run_autonomous_prompt.md](team_workflow/run_autonomous_prompt.md) | [📋 Копировать](#run-autonomous-prompt) |
| **Orchestrator Template** | Шаблон для собственного оркестратора | [team_workflow/orchestrator_template.md](team_workflow/orchestrator_template.md) | [📋 Копировать](#orchestrator-template) |

---

## 📖 Workflow Инструкции (Агенты)

| Документ | Область | Описание |
|---|---|---|
| **agent_workflow.md** | Навигация | Slim-индекс всех agent-workflow документов |
| **agent_workflow_rules.md** | Rules | Token Budget & Retry Safety (7 правил) |
| **agent_workflow_cycle.md** | Процесс | Scan → Plan → Edit → Verify → Sync; параллелизм; A/B/C split |
| **agent_workflow_templates.md** | Шаблоны | Planning / Verify / Contract / Task templates |
| **agent_workflow_test_bundles.md** | Тесты | Стандартные test bundles по областям |
| **agent_workflow_arch_review.md** | Architecture | Периодический arch audit (5 фаз) |

---

## 🎯 Быстрый Старт По Сценариям

### Я хочу запустить новый пакет

1. Читай [team_workflow/README.md](team_workflow/README.md) — обзор процесса
2. Используй [team_workflow/generate_plan_next_prompt.md](team_workflow/generate_plan_next_prompt.md) — выбери пакет и напиши контракт
3. Запусти [team_workflow/generate_orchestration_prompt.md](team_workflow/generate_orchestration_prompt.md) — сгенерируй full workflow

### Я прерывистый разработчик, возвращаюсь к старому пакету

1. Используй [team_workflow/generate_resume_prompt.md](team_workflow/generate_resume_prompt.md) — восстанови контекст
2. Читай artifact из `archive/team_artifacts/<PACKAGE_ID>/` — последний статус
3. Запусти [agent_workflow_templates.md](agent_workflow_templates.md#шаблон-planning-prompt-рекомендуемый-по-умолчанию) Planning Prompt с diff от последнего коммита

### Периодический аудит закрытых пакетов (SSoT)

1. Мастер-вход всей цепочки: [team_workflow/run_audit_chain_prompt.md](team_workflow/run_audit_chain_prompt.md)
2. Готовый prompt для проверки утверждения по `CJM + user_stories_index + backlog_registry` с full audit chain / DoD: [../archive/doc_team_workflow/ssot_full_audit_prompt.md](../archive/doc_team_workflow/ssot_full_audit_prompt.md)
3. Инструкции генератора и параметры `PERIOD` / `SCOPE` / `DEPTH`: [team_workflow/generate_audit_closed_packages_prompt.md](team_workflow/generate_audit_closed_packages_prompt.md)
4. Эталонный самодостаточный промпт после генерации (пример окна 2026-04-20..2026-04-28): [копипаст](#closed-packages-audit-snapshot-2026-04-20-cursor-ai) или файл [team_workflow/audit_prompt_2026-04-20__2026-04-28_cursor_ai.md](team_workflow/audit_prompt_2026-04-20__2026-04-28_cursor_ai.md)
5. После создания audit-групп: [team_workflow/generate_audit_packages_coverage_prompt.md](team_workflow/generate_audit_packages_coverage_prompt.md) создаёт `audit_coverage_prompt_${PERIOD_SLUG}_${TARGET_AGENT}.md` для добивки unit/e2e DoD-покрытия, `_audit_raw.json` и `coverage_dod_analysis.md`.
6. Переоткрытие закрытых по окну административным батчем (Step C): шаблон [reopen_prompt_closed_window_template.md](team_workflow/reopen_prompt_closed_window_template.md), пример последних трёх календарных дней до 2026-04-28: [копипаст](#reopen-batch-closed-window-last3days-example)
7. Переоткрытие **одного** пакета вручную (тот же Step C, одна атомарная операция): [reopen_package_step_c_prompt.md](team_workflow/reopen_package_step_c_prompt.md)

### Я хочу добавить свой prompt

1. Создай файл `doc/team_workflow/my_prompt.md`
2. Используй структуру из [team_workflow/orchestrator_template.md](team_workflow/orchestrator_template.md)
3. Добавь ссылку в этот каталог в соответствующую категорию
4. Ссылайся на него из [doc/index.md](index.md)

### 🚀 Я хочу развивать продукт (актуализация, новые волны, стратегия)

Используй эту таблицу для стратегического планирования, обновления CJM, и определения волн пакетов:

| Сценарий | Документы | Промпты | Цель |
|---|---|---|---|
| **Актуализировать Vision & CJM** | [vision.md](vision.md) · [cjm.md](cjm.md) · [product_idea.md](product_idea.md) | [🔤 Planning Prompt](#planning-prompt-планирование-пакета) | Пересмотреть стратегию, обновить CJM pain points, переопределить критические моменты |
| **Обновить CJM Pain Table** | [cjm.md](cjm.md) · [future_roadmap.md](future_roadmap.md) | [🔤 Planning Prompt](#planning-prompt-планирование-пакета) | Добавить новые pain points, изменить приоритеты, выявить незакрытые проблемы |
| **Выбрать следующий product-planning шаг** | [roadmap.md](roadmap.md) · [user_stories.md](user_stories.md) · [future_roadmap.md](future_roadmap.md) | [product_owner_router](team_workflow/product_owner_router.md) | Решить: plan-next, candidate table, breakthrough ideation, один package, roadmap waves или execution |
| **Спланировать волну пакетов** | [backlog_registry.yaml](backlog_registry.yaml) · [future_roadmap.md](future_roadmap.md) · [closed_iterations.md](closed_iterations.md) | [generate_roadmap_epoch_waves_prompt](team_workflow/generate_roadmap_epoch_waves_prompt.md) · [🎭 Product Owner](#product-owner) | После ideation/owner decision оформить 3+ связанные идеи как proposed waves/packages без дублей |
| **Найти прорывные идеи для Stage / US / pain point** | [cjm.md](cjm.md) · [user_stories/](user_stories/) · [backlog_registry.yaml](backlog_registry.yaml) | [🔤 Breakthrough Ideation](#breakthrough-ideation-prompt) | Сгенерировать ≥N идей с методами из best practices (Duolingo/Anki/Khan), готовые диффы для cjm/us/backlog_registry/epochs |
| **Собрать таблицу направлений (CJM · US · pain · roadmap) перед ideation** | [cjm.md](cjm.md) · [user_stories.md](user_stories.md) · [future_roadmap.md](future_roadmap.md) | [generate_breakthrough_ideation_prompt § CANDIDATE_TABLE](team_workflow/generate_breakthrough_ideation_prompt.md#как-использовать) | Одна Markdown-таблица кандидатов без генерации N идей; выбор строки → затем полный Breakthrough или сразу [Product Owner plan package](team_workflow/product_owner_plan_package_prompt.md) |
| **Обновить User Stories** | [user_stories.md](user_stories.md) · [user_stories/](user_stories/) · [cjm.md](cjm.md) | [🔤 Planning Prompt](#planning-prompt-планирование-пакета) | Добавить/изменить US, синхронизировать с CJM и roadmap |
| **Запланировать стратегический horizon** | [archive/ideation/](../archive/ideation/) · [future_roadmap.md](future_roadmap.md) · [backlog_registry.yaml](backlog_registry.yaml) | [product_owner_router](team_workflow/product_owner_router.md) → [generate_roadmap_epoch_waves_prompt](team_workflow/generate_roadmap_epoch_waves_prompt.md) | После ideation/owner decision перенести выбранный horizon в registry как proposed waves/packages, затем sync/lint |
| **Провести Architecture Review** | [architecture.md](architecture.md) · [adr.md](adr.md) · [conventions.md](conventions.md) | [🔤 Architecture Review Prompt](#architecture-review-prompt-архитектурный-аудит) | Проверить drift архитектуры, найти нарушения соглашений, выявить tech debt |
| **Переоценить Roadmap** | [future_roadmap.md](future_roadmap.md) · [closed_iterations.md](closed_iterations.md) · [roadmap_governance.md](roadmap_governance.md) | [🎭 Product Owner](#product-owner) | Пересмотреть приоритеты, отложить/перенести пакеты, переопределить horizons |
| **Локальный smoke-пакет `epoch-demo`** | [backlog_registry.yaml](backlog_registry.yaml) · generated [tasklist.md](tasklist.md) · [prompt_utils.py](../scripts/prompt_utils.py) · [`archive/team_artifacts/epoch-demo/`](../archive/team_artifacts/epoch-demo/) | [Промпт package](#epoch-demo-prompt-package) · [Промпт post-agent smoke](#epoch-demo-prompt-post-agent-smoke) | Повторяемый сценарий: каркас пакета в registry, демо-функция в `prompt_utils`, sync; затем реальный CLI `run_autonomous --post-agent` |

**Типичный flow актуализации:**
1. Прочитай [cjm.md](cjm.md) и [vision.md](vision.md) — текущее состояние
2. Идентифицируй изменения в pain points или неполученные ценности
3. Используй [Product Owner Prompt](#product-owner) для планирования адаптации
4. Обнови [backlog_registry.yaml](backlog_registry.yaml) и [user_stories.md](user_stories.md), затем регенерируй [tasklist.md](tasklist.md)
5. Запусти новую волну пакетов через [Planning Prompt](#planning-prompt-планирование-пакета) + [Orchestrator Template](#orchestrator-template)

---

## 🔤 Тексты Промптов (Копируй и Вставляй)

<a id="audit-chain-master-prompt"></a>

### Audit Chain Master Prompt — вся цепочка аудита

Используй, когда нужно провести всю цепочку, а не только создать один prompt.

**Канон на диске:** [team_workflow/run_audit_chain_prompt.md](team_workflow/run_audit_chain_prompt.md).
**Готовый снимок:** [../archive/doc_team_workflow/audit_chain_prompt_2026-04_cursor_ai.md](../archive/doc_team_workflow/audit_chain_prompt_2026-04_cursor_ai.md).

```text
Read doc/team_workflow/run_audit_chain_prompt.md
and execute the instructions.

TARGET_AGENT: cursor_ai
PERIOD: 2026-04
DEPTH: dod_replay
SCOPE: closed
COVERAGE_FIX: true
GROUP_MODE: generate_only
```

Для безопасного выполнения одной группы:

```text
Read doc/team_workflow/run_audit_chain_prompt.md
and execute the instructions.

TARGET_AGENT: cursor_ai
PERIOD: 2026-04
DEPTH: dod_replay
SCOPE: closed
COVERAGE_FIX: true
GROUP_MODE: execute_one
GROUP_ID: group_01
```

After each group, refresh the next pointer and summary:

```powershell
.\.venv\Scripts\python.exe scripts/check_audit_chain_state.py --period 2026-04 --target-agent cursor_ai --write-next-action --write-summary --write-raw-check --json-out archive/team_artifacts/audit_2026-04/audit_chain_state.json
```

---

<a id="epoch-demo-local-smoke-prompts"></a>

### Epoch-Demo: локальные промпты (package + post-agent smoke)

**Канонический источник (держи текст синхронно со скриптом):** [scripts/print_epoch_demo_agent_prompts.py](../scripts/print_epoch_demo_agent_prompts.py) — константы `PROMPT_EPOCH_DEMO_PACKAGE` и `PROMPT_POST_AGENT_SMOKE`.

**Печать из репозитория (рекомендуется вместо копипаста):**

```bash
.\.venv\Scripts\python.exe scripts/print_epoch_demo_agent_prompts.py
.\.venv\Scripts\python.exe scripts/print_epoch_demo_agent_prompts.py package
.\.venv\Scripts\python.exe scripts/print_epoch_demo_agent_prompts.py smoke
```

**Префлайт статуса `epoch-demo` в registry (без правок файлов):**

```bash
.\.venv\Scripts\python.exe scripts/print_reopen_package_workflow.py --package epoch-demo
```

Для любого `PACKAGE_ID` перед Step C см. [reopen_package_step_c_prompt.md](team_workflow/reopen_package_step_c_prompt.md).

**Порядок шагов агенту (реальный CLI, не `pytest`):** [team_workflow/archive/epoch_demo_post_agent_smoke.md](team_workflow/archive/epoch_demo_post_agent_smoke.md) — тот же эталон текста, что в `print_epoch_demo_agent_prompts.py` (`smoke`).

| Сценарий | Документы | Промпты | Цель |
|---|---|---|---|
| **Подготовка пакета `epoch-demo`** | [backlog_registry.yaml](backlog_registry.yaml) · generated [tasklist.md](tasklist.md) · [prompt_utils.py](../scripts/prompt_utils.py) · [`archive/team_artifacts/epoch-demo/`](../archive/team_artifacts/epoch-demo/) | [📋 Копировать: package](#epoch-demo-prompt-package) | Создать/переоткрыть пакет в registry, демо-функция в `prompt_utils`, sync для повторного прогона |
| **Реальный smoke `run_autonomous --post-agent`** | [run_autonomous.py](../scripts/run_autonomous.py) · [epoch_demo_post_agent_smoke.md](team_workflow/archive/epoch_demo_post_agent_smoke.md) | [📋 Копировать: post-agent](#epoch-demo-prompt-post-agent-smoke) | Проверить UX блокировок в CLI, не unit-тесты |

---

<a id="planning-prompt-планирование-пакета"></a>

### Planning Prompt (Планирование Пакета)

Используй этот промпт для планирования новой итерации или пакета.

```text
# [two-root] Two-repo project: resolve app/** and requirements.txt against CODE_ROOT
# (editable install of `hometutor`: `pip show hometutor` -> "Editable project location");
# resolve doc/**, tests/**, scripts/** against the current cwd (DOCS_ROOT).
# Run git per-root: `git -C <CODE_ROOT> ...` for app code, `git -C <cwd> ...` for docs/tests.
Goal: plan <epoch-package> ONLY — produce a detailed execution contract.

Cursor token guard:
- Target <=12k input tokens.
- Soft-limit 12k-20k: compress history/read-set before sending.
- Hard stop >20k input tokens: stop before the call and report blocker.
- Owner/write-set files are not read-set.
- Do not attach full files unless listed below as full-read.
- Do not include previous tool logs; fresh context only.

Read ONLY (max 3–5 файлов, не больше):
1. Целевой файл кода (e.g., app/query_service.py) — signatures only, не полное тело
2. Целевой тест (e.g., tests/test_query_service.py) — existing patterns only, not full file
3. doc/backlog_registry.yaml — ONLY the entry for <target-package>, not entire file

Output format:
- Package goal: 1-2 sentences tied to user pain (no CJM preamble)
- Write-set: 3–5 files max to create or modify
- Read-set: 2–3 files max to inspect but not touch
- Do-not-touch list: explicit, 3–5 items
- DoD: exact pytest/command + observable result (1 line each)
- Copy-paste execution prompt (use execution contract template below)

Rules:
- Do not write code. Only produce the plan.
- Owner/write-set files in the generated execution prompt must not imply full-read.
- Do NOT read doc/epochs/, doc/cjm.md, doc/closed_iterations.md, or other doc files beyond the 3 listed.
- If a file >600 lines and you haven't read it before: grep for signatures first, don't read the full body.
- If a US lacks clear acceptance criteria, ask ONE clarifying question only.
- If write-sets overlap, propose a split but do not design both.
- Total output: max 400 words.
- Token budget check: if estimated input is 12k-20k, compress before sending; if it exceeds 20k tokens, stop and report blocker.

Ignore prior responses/tools. Fresh context only.
```

**Где использовать:** [agent_workflow_templates.md § Planning Prompt](agent_workflow_templates.md#шаблон-planning-prompt-рекомендуемый-по-умолчанию)

---

<a id="execution-contract-контрактный-промпт"></a>

### Execution Contract (Контрактный Промпт)

Используй этот короткий шаблон для быстрого выполнения одного пакета.

```text
Goal: close <epoch-package> only.

Context:
<1-2 строки: какую CJM-боль или user-visible outcome закрывает пакет.>

Scope:
<что именно сделать, в 1-3 пунктах.>

Read ONLY / files to inspect first:
- <file/path.py>
- <file/path.py>
- <tests or nearby modules>

DoD:
- <точный критерий готовности>
- <команда проверки>
- <ожидаемый результат>

Do not touch:
- <соседняя эпоха / outcome>
- <нерелевантные файлы или подсистемы>
- <документы, если их нельзя менять>

Working rules:
- Prefer existing patterns.
- Keep changes minimal and scoped to this package.
- Do not refactor unrelated code.
- Owner/write-set files are not read-set; read full files only when explicitly listed under Read ONLY.
- For files >600 lines or known unsafe files, use rg/signatures/one section first.
- If blocked, report the smallest blocker and the exact file/command where it appears.
- Token budget per LLM call: Target <=12k input tokens. Soft-limit 12k-20k: compress before sending. Hard-limit >20k: stop and report blocker.

Output:
- Changed files
- Tests run + result
- What was completed
- Unresolved risk / follow-up, if any
```

**Где использовать:** [agent_workflow_templates.md § Контрактный Prompt](agent_workflow_templates.md#контрактный-prompt-для-ударных-пакетов)

---

<a id="verify-prompt-верификация-пакета"></a>

### Verify Prompt (Верификация Пакета)

Используй этот промпт после завершения пакета разработчиком.

```text
# [two-root] Two-repo project: resolve app/** and requirements.txt against CODE_ROOT
# (editable install of `hometutor`: `pip show hometutor` -> "Editable project location");
# resolve doc/**, tests/**, scripts/** against the current cwd (DOCS_ROOT).
# Run git per-root: `git -C <CODE_ROOT> ...` for app code, `git -C <cwd> ...` for docs/tests.
Goal: verify <epoch-package> execution against contract. Do NOT write code. Output = structured report.

CONTRACT_FILE: <path to contract, e.g. archive/team_artifacts/E14-B/contract.md>
PACKAGE_ID: <e.g., E14-B>
COMMIT_RANGE: <e.g., HEAD~1..HEAD>
PACKAGE_TYPE: <code|doc|mixed>

Read ONLY:
- CONTRACT_FILE (entire)
- git diff COMMIT_RANGE (full diff)
- DoD-related test files or single test case if needed

Verification checklist:
1. Scope check: git diff COMMIT_RANGE --name-only should be subset of write-set
2. DoD check: run each DoD command, verify observable result matches expected
3. Spot check: code follows patterns from conventions, no obvious violations
4. Regression: if PACKAGE_TYPE=code, run test suite and verify no new failures
5. Docs sync: if contract mentions doc updates, verify they happened

Verdict options:
- PASS → mark as closed
- CONDITIONAL PASS → findings are follow-up, not blocking; specify findings
- FAIL → identify ONE specific blocker; generate fix-prompt for developer

Falsifiability rule: Every finding must include evidence (rg command, test command, etc.) and expected output.

Output:
- VERDICT: PASS | CONDITIONAL PASS | FAIL
- Findings (if any): id | severity | description | evidence command | expected output
- Fix-prompt (if FAIL/CONDITIONAL): ready-to-copy prompt for developer in fresh context

Ignore prior responses/tools. Fresh context only.
```

**Где использовать:** [agent_workflow_templates.md § Verify Prompt](agent_workflow_templates.md#verify-prompt--проверка-выполненного-пакета)

---

<a id="architecture-review-prompt-архитектурный-аудит"></a>

### Architecture Review Prompt (Архитектурный Аудит)

Используй для периодического аудита архитектуры (по фазам, не целиком!).

```text
Goal: periodic INCREMENTAL architecture review — find defects, violations, and decay
introduced since last review. Do NOT write code. Do NOT edit any files.
Output = structured report only.

## REPOSITORY ROOTS (two-root project — read first)

This project is split across TWO independent git working trees. Resolve every
path below against the correct root; do NOT assume a single repo.

- CODE_ROOT = editable install location of the `hometutor` package.
  Holds all source: app/, app/routers/, app/ui/, requirements.txt.
  Derive it (do not hardcode):
    PowerShell: $CODE_ROOT = (& .\.venv\Scripts\pip.exe show hometutor |
      Select-String 'Editable project location:').ToString().Split(':',2)[1].Trim()
- DOCS_ROOT = current working directory (this `*-studio` workspace).
  Holds doc/, tests/, scripts/, and doc/archive/arch_review_baseline.yaml.

Path → root mapping:
- app/**, requirements.txt            → CODE_ROOT  (use `git -C $CODE_ROOT`, `rg <CODE_ROOT>/app/...`)
- doc/**, tests/**, scripts/**        → DOCS_ROOT  (current cwd)
- baseline yaml + conventions + ADR   → DOCS_ROOT

The two repos have independent histories. Record the reviewed pair in the report:
`reviewed CODE_ROOT@<code HEAD> + DOCS_ROOT@<docs HEAD>`.

## MANDATORY PRE-SCAN (runs before any phase work)

1. Read doc/archive/arch_review_baseline.yaml (DOCS_ROOT) — extract
   last_review.code_sha, last_review.docs_sha, and findings list.
   If file is absent: this is the first incremental run; state that in the report
   and scan full scope for this phase only (baseline will be created from output).
2. Compute incremental scope from BOTH roots:
   - git -C $CODE_ROOT diff --name-only <code_sha>..HEAD  → changed app/ files
   - git -C $DOCS_ROOT diff --name-only <docs_sha>..HEAD  → changed doc/ + tests/ files
   - union with files from baseline findings whose phase matches current phase
     AND status in {new, persists}
   - this is the ONLY scope allowed for the phase. Unchanged+unreferenced
     modules are out of scope.
   - If a stored sha is missing or dangling in its repo (git: "could not get
     object info"), treat that root as first-run for this phase (full scope)
     and flag the stale sha in the report so the baseline can be repaired.
3. For every baseline finding in this phase: run its evidence_cmd in the
   finding's root (app/* findings against CODE_ROOT).
   - No match → mark resolved (report in output, do not re-analyze).
   - Match → mark persists, update last_seen, keep in output.
4. If estimated read-set after incremental scoping still exceeds 12k tokens,
   compress further (signatures-only) before starting the phase.

## FALSIFIABILITY RULE

Every new finding must include an Evidence command (one-liner rg/pytest/python)
and its expected output. Findings without reproducible evidence are auto-downgraded
to severity=info and excluded from the fix-prompt. No subjective claims
("feels coupled", "probably unused") accepted at warning/critical severity.

## IMPORTANT: TOKEN BUDGET FOR LARGE FILES

Before reading any file >600 lines, check doc/token_safety.md for safe method.
Measure size first — do NOT trust static counts (they drift between epochs):
PowerShell `(Get-Content <file>).Count`, Git Bash `wc -l <file>`. app/* paths are under CODE_ROOT.
- app/query_service.py   → rg "^class\|^def " only, don't read full body
- app/tutor_prompts.py   → small, safe to read fully; prompts are distributed, no monolithic prompts file
- app/knowledge_graph.py → rg "^class\|^def " only
- doc/adr.md             → read ONLY the status table or one ADR
- doc/architecture.md    → if >600 lines, read ONLY the module list, skip detail sections

If you are reading a file and it exceeds 1k tokens, STOP and use grep instead.
Owner files are write-scope, not read-scope. Do not read owner files fully unless they are listed under Read ONLY.

## Phase 1 — Conventions Compliance Audit

Read these files as the authoritative baseline:
- doc/conventions.md (~710 tokens, safe to read fully)
- doc/conventions_architecture.md (~3k tokens, safe to read fully)
- doc/conventions_reference.md (~1.9k tokens, safe to read fully)

Then scan the codebase for violations of each stated convention.
DO NOT read app/query_service.py, app/knowledge_graph.py fully — use rg/signatures as noted above (app/* under CODE_ROOT).

Check specifically (use grep for large files to save tokens):
1. Config access: any module reading settings NOT through get_settings() /
   get_retrieval_settings() (except config.py itself and tests).
2. LLM/embed access: any module creating LLM or embed clients NOT through
   app/provider.py.
3. Prompt location: SSoT = `app/prompts/` package (`_impl.py` — forbidden full-read);
   `app/tutor_prompts.py` is a bridge/helper. Use
   `rg "prompt\s*=\s*f?['\"]" app/ --type py | grep -v "app/prompts/" | grep -v "tutor_prompts.py"`
   to find hardcoded prompts outside the prompt package.
4. Pipeline contract: any step NOT following process(QueryContext) -> QueryContext.
5. Router structure: any HTTP handler NOT in app/routers/; any endpoint not
   registered through include_router in app/api.py.
6. Knowledge encapsulation: any UI or API module duplicating business logic
   that should live in knowledge_service.py, quiz_service.py, flashcard_service.py,
   or learning_plan_service.py.
7. Import hygiene: any circular imports; any module importing from UI layer
   into backend layer; any test importing production secrets or live state.
8. Error handling: any pipeline stage without graceful degradation (except
   generate, which is the only stage without fallback by convention).
9. Path safety: any file access to data/ NOT going through safe path validation.
10. Guardrails: any entry point (API, CLI, Telegram) bypassing
    app/guardrails.py or app/input_validation.py.

For each violation found:
- File path and line number
- Which convention is violated (quote the rule)
- Severity: critical / warning / info
- Suggested fix (1-2 sentences, no code)

## ⚠️ Token Budget Note for Large Modules

To stay within the 12k target / 20k hard-limit, do NOT read these files in full. Instead use rg/signatures/sections.
Verify each file's current size first (`(Get-Content <file>).Count` / `wc -l`); the list below is by role, not by a frozen line count. app/* paths are under CODE_ROOT.

| Module / doc | Read method | Why |
|---|---|---|
| `app/prompts/_impl.py` | `rg "^def\|^[A-Z_].*=" app/prompts/_impl.py` | SSoT промптов (>1500 lines — forbidden full-read) |
| `app/tutor_prompts.py` | read in full (small) | bridge/helper for `app/prompts/` |
| `doc/changelog.md` | last 2-3 entries or append target only | history docs accumulate quickly |
| `tests/test_api.py` | `rg "def test_<pattern>" tests/test_api.py` + one test case | full tests can exceed target budget |
| `doc/adr.md` | status table or one ADR only | full decision history is not phase input |
| `app/knowledge_graph.py` | `rg "^class\|^def " app/knowledge_graph.py` | full-read is forbidden |
| `tests/test_query_service.py` | 1-2 relevant tests or fixtures | avoid full test file |
| `app/query_service.py` | `rg "^class\|^def " app/query_service.py` + exact function | large orchestrator |
| `doc/architecture.md` | module list or one section only | >600 lines — treat as large file |

> ⚠️ Перед review проверить актуальный размер каждого файла через `(Get-Content <file>).Count` (PowerShell) или `wc -l <file>` (Git Bash). Никаких зашитых чисел строк — они устаревают между эпохами.

## Phase 2 — Structural Health

Analyze the codebase for structural problems (using grep where specified above):

2.1 Dead code:
- Functions/classes/constants that are defined but never imported or called
- Config fields in Settings/RetrievalSettings with no consumer in app/
- Routers registered in api.py with endpoints that have no UI or test consumer
- Test files that test modules which no longer exist

2.2 Duplication:
- Identical or near-identical logic in different modules (>10 lines)
- Multiple modules implementing the same concept independently
  (e.g., SM-2 in different places, date formatting helpers, retry loops)
- Copy-pasted SQL schemas or queries across modules

2.3 Coupling and dependency direction:
- Backend modules (app/*.py) importing from UI layer (app/ui/*.py)
- Service modules importing from routers
- Circular dependency chains (A imports B imports C imports A)
- God modules with >15 imports from app/ (excessive fan-in or fan-out)
- Shared mutable state outside designated stores (user_state, session_store,
  metrics)

2.4 Module size and responsibility:
- Any single file >600 lines (candidate for split)
- Any function >80 lines (candidate for extraction)
- Modules with mixed responsibilities (e.g., a service that also does HTTP
  serialization, or a UI module that contains business logic)

2.5 Test health:
- Test files with no assertions (smoke-only without checking anything)
- Tests that patch >5 different targets (sign of excessive coupling)
- Missing test coverage for critical paths: pipeline_runner, query_service,
  tutor_orchestrator, user_state migrations, guardrails
- Broken or skipped tests (pytest.mark.skip without explanation)

## Phase 3 — Architecture Decision Audit

Read ONLY the ADR status table / one relevant ADR and the architecture module list / one relevant section. Do not read `doc/adr.md` or `doc/architecture.md` fully in this phase.

3.1 ADR drift:
- For each ADR with status "Accepted": verify the code still follows
  the stated decision. Flag any module that contradicts an accepted ADR.
- For each ADR with status "Proposed": check if it was silently implemented
  without updating the status to Accepted.
- Missing ADRs: identify any significant architectural choice in the code
  that has no corresponding ADR entry (e.g., choice of SQLite for state,
  choice of aiogram for Telegram, session storage strategy, graph storage
  format).

3.2 Documentation-code drift:
- doc/architecture.md: verify that every module listed still exists, and
  every significant module in app/ is listed. Flag missing or renamed.
- doc/api_reference.md: sample 5-10 endpoints and verify they match the
  actual routes in app/routers/.
- doc/observability_slo.md: verify SLO parameters listed match the code
  in app/config.py and app/metrics.py.
- doc/technical_specification.md: verify entry points, stack, formats
  match reality.

3.3 Implicit decisions (no-ADR patterns):
- Identify patterns that appear in 3+ modules without documented
  rationale (e.g., specific error handling strategy, specific serialization
  format, specific caching approach).
- These are implicit architecture decisions. Flag each one and suggest
  whether it needs an ADR.

## Phase 4 — Implementation Quality

4.1 Anti-patterns:
- Catch-all except blocks (bare except: or except Exception without
  re-raise or specific handling)
- Silent failures: errors caught and logged but not propagated to caller
  when the caller needs to know
- N+1 patterns: loops making individual DB queries or LLM calls where
  batch would work
- Synchronous blocking in async context (or vice versa)
- Hardcoded magic numbers without named constants
- Environment-dependent behavior without clear documentation
  (code that behaves differently based on undocumented env vars)

4.2 Security surface:
- SQL injection vectors: any raw string interpolation in SQL queries
  in user_state.py or other SQLite consumers
- Path traversal: any file operation on user-provided paths without
  validation
- Prompt injection: any user input reaching LLM prompts without going
  through guardrails.py
- Sensitive data in logs: any logging of full API keys, user content
  at DEBUG level that could leak, session tokens
- CORS configuration: verify CORS in api.py is appropriate for
  a local-only service

4.3 Resilience:
- LLM call sites without timeout or retry
- External service calls (Chroma, file system) without error handling
- Missing graceful degradation for optional features (graph, telegram,
  OTEL) when their dependencies are unavailable

## Phase 5 — Dependency and Ecosystem Health

5.1 requirements.txt audit:
- Packages imported in code but missing from requirements.txt
- Packages in requirements.txt but never imported in app/ or tests/
- Known incompatible version combinations (if detectable from pinned
  versions)
- Packages with known security advisories (flag for manual check)

5.2 Internal dependency map:
- Which app/ modules have the most dependents (highest fan-in)?
- Which app/ modules import the most other app/ modules (highest fan-out)?
- Are there clear layer boundaries (entrypoints → services → core)?
- Flag any violation of the expected dependency direction.

## Output format

### Executive Summary (3-5 sentences)
Overall health assessment. Top 3 most impactful findings.

### Findings Table

| # | ID | Phase | Severity | Status | Finding | File(s) | Evidence (cmd → expected) | Suggested Action |
|---|----|-------|----------|--------|---------|---------|---------------------------|------------------|
| 1 | AR-2026-04-21-001 | 1 | critical | new | ... | app/foo.py:42 | `rg "..." app/foo.py` → `match on L42` | ... |
| 2 | AR-2026-04-12-005 | 2 | warning  | persists (since 2026-04-12) | ... | app/bar.py | `pytest -k test_bar_contract --collect-only` → `0 tests` | ... |
| 3 | AR-2026-04-12-003 | 1 | —        | resolved | ... | app/baz.py | `rg "..." app/baz.py` → `no matches` | — |

Status values: `new` | `persists` | `resolved` | `accepted-tech-debt`.
Findings без Evidence (пустая колонка или "see report") — автоматически severity=info, не включаются в fix-prompt.

### Baseline Update

В конце отчёта — готовый патч для `doc/archive/arch_review_baseline.yaml`:
- обновить `last_review.code_sha` / `last_review.docs_sha` / `date` / `report_files` (список);
- добавить все `new` findings с полными полями (id, phase, severity, files, first_seen, last_seen, status, evidence_cmd, expected_evidence, regression_guard, owner=null, target_epoch=null);
- для `persists` — обновить `last_seen`;
- для `resolved` — status=resolved, добавить `resolved_date`;
- `accepted-tech-debt` findings не трогать автоматически.

Severity scale:
- critical: active bug risk, security issue, or convention violation
  that will cause problems in the next epoch
- warning: technical debt or drift that should be addressed within
  1-2 epochs
- info: observation, minor improvement, or documentation gap

### Metrics Snapshot

- Total app/ modules: N
- Total test files: N
- Modules >600 lines: list
- Functions >80 lines: list (sample up to 10)
- Convention violations found: N (critical/warning/info breakdown)
- ADR drift instances: N
- Doc-code drift instances: N
- Dead code candidates: N
- Duplication clusters: N

### Recommended Actions (prioritized)

Top 5-10 actions, ordered by impact. For each:
- What to do (1-2 sentences)
- Why it matters now
- Estimated scope: S (1 file) / M (2-5 files) / L (6+ files)
- Suggested epoch-package name if the fix needs its own slice

### Fix Prompts (ОБЯЗАТЕЛЬНО — один prompt на каждую выполненную фазу)

Для каждой выполненной фазы выдать готовый copy-paste execution prompt,
который можно запустить в отдельной fresh-context сессии для устранения
найденных critical+warning замечаний. Info-находки включать в "optional
follow-up" отдельным списком, не в DoD.

Требования:
- Один prompt = одна фаза. Не смешивать findings из разных фаз в один fix.
- Write-set ≤ 5 файлов. Если правок больше — split на A/B/C с порядком merge.
- DoD — конкретная pytest/rg команда на каждую finding с expected result
  (обычно = `evidence_cmd` finding'а с expected output "no match"/"pass").
- Do not touch — зоны других фаз, чтобы fix не расползался.
- Token header:
  `Token budget:`
  `- Target <=12k input tokens.`
  `- Hard stop >20k input tokens.`
  `- If estimated input is 12k-20k, compress before sending.`
  `- No retry with unchanged payload.`
- Первая строка: `Ignore prior responses/tools. Fresh context only.`
- Не вставлять тело отчёта в fix-prompt — только ссылку на report file
  и перечень findings по ID из baseline.
- **Regression Guard (обязательно на каждый critical+warning finding).** В fix-prompt
  указать как предотвратить повторное появление. Минимум один из:
  - новое правило в `doc/conventions.md` / `conventions_architecture.md` со ссылкой на ID finding;
  - pre-commit hook или CI check (скрипт в `scripts/check_*.py`), агрегируемый в `scripts/arch_regression_guards.py`;
  - инвариант-тест в `tests/test_*_invariants.py` (падает при возврате проблемы);
  - добавление `evidence_cmd` в `scripts/arch_regression_guards.py` (Windows-first агрегатор для pre-merge).
  Fix-prompt без Regression Guard на critical/warning → **не принимается verify**.

Шаблон fix-prompt (для каждой фазы):

```text
Goal: fix Phase <N> findings from <arch-review-report-file>.
Ignore prior responses/tools. Fresh context only.

Baseline: doc/archive/arch_review_baseline.yaml
Report:   <arch-review-report-file>

Findings to fix (critical + warning from Phase <N>, by baseline ID):
- <AR-YYYY-MM-DD-NNN>: <one-line finding> (file:line)
- <AR-YYYY-MM-DD-NNN>: <one-line finding> (file:line)

Write-set (≤ 5 files):
- <file1>
- <file2>

Read ONLY:
- <file> — signatures only if >600 строк
- <related test file> — 1 test case only

Do not touch:
- модули из других фаз arch-review
- <другие зоны>

DoD (one per finding — обычно = evidence_cmd finding'а):
- <AR-...>: <rg/pytest команда> → <expected: no match / pass>

Regression Guard (обязательно, один или несколько на каждый finding):
- <AR-...>: new rule in doc/conventions.md §<section> + CI check scripts/check_<name>.py
- <AR-...>: invariant test tests/test_<module>_invariants.py::test_<name>
- <AR-...>: add evidence_cmd to scripts/arch_regression_guards.py

Post-fix baseline update:
- Mark fixed findings as status=resolved in doc/archive/arch_review_baseline.yaml
  with resolved_date=<today>. Do NOT remove entries — keep history.

Token budget:
- Target <=12k input tokens.
- Hard stop >20k input tokens.
- If estimated input is 12k-20k, compress before sending.
- No retry with unchanged payload.
Output: changed files + tests run + guard(s) added + unresolved risk.

Optional follow-up (info-level, not in DoD):
- <AR-...>: <finding>
```

Если в фазе нет critical/warning — явно написать:
`No fix-prompt required for Phase <N> (no actionable findings above info level).`

### Appendix: Positive Patterns

List 3-5 things the codebase does well that should be preserved and
replicated. This prevents future agents from "improving" what already
works.

Rules:
- Do NOT write code. Do NOT edit any files. Output = report only.
- Do NOT propose wholesale rewrites or migrations. Prefer targeted fixes.
- Do NOT flag style issues (formatting, naming preferences) unless they
  violate a stated convention in doc/conventions.md.
- Focus on problems that will compound if left unaddressed.
- Finding history precedence:
  1) `doc/archive/arch_review_baseline.yaml` — source of truth for status/history.
  2) `last_review.report_files` from baseline — reference reports for previous cycle.
  3) `archive/architecture_review*.md` — historical context only, not a status source.
- If a finding appears in legacy `archive/architecture_review.md` as "resolved",
  verify status only via baseline evidence before any reclassification.
- Use exact file paths and line numbers wherever possible.
- If the review scope is too large for one pass, state which phases
  you completed and which need a follow-up.
```

**Где использовать:** [agent_workflow_arch_review.md § Architecture Review Prompt](agent_workflow_arch_review.md#шаблон-architecture-review-prompt)

---

<a id="breakthrough-ideation-prompt"></a>

### Breakthrough Ideation Prompt (Генерация Прорывных Идей)

Используй для поиска ≥N новых сценариев по конкретному CJM-этапу, User Story, pain point или области фич. **Режим только таблицы:** `MODE=CANDIDATE_TABLE` (копипаста в [§ «Как использовать»](team_workflow/generate_breakthrough_ideation_prompt.md#как-использовать) канонического файла) — сводка направлений из CJM §5/§8 + `user_stories.md` + `future_roadmap.md` без идей и без диффов; дальше человек задаёт `TARGET` и при необходимости запускает полный прогон ниже.

После блокера `generate_plan_next_prompt` см. цепочку в тексте **[generate_plan_next_prompt.md](team_workflow/generate_plan_next_prompt.md)** («Инструкции для AI-агента», Phase 3) и в **[product_owner_plan_package_prompt.md](team_workflow/product_owner_plan_package_prompt.md)**.

```text
Goal: generate ≥N breakthrough scenarios for <TARGET> (CJM stage / US / pain point / feature area).
      Produce ≥N_IDEAS candidates with method sources from proven analogs (Duolingo, Anki, Khan, Notion, etc.).
      Stop after creating diffs in read-only artifact.
      Do NOT apply edits directly to cjm.md / user_stories / backlog_registry / tasklist / epochs.
      Output = archive/ideation/<TARGET_SLUG>_<YYYY-MM-DD>.md with proposed changes.

INPUT (required):
  <TARGET>      — CJM stage ID ("Stage #7: Course Learning Mode"),
                  US ID ("US 14.3"),
                  pain point ("high churn in retention"),
                  or feature area ("quiz retry flow")
  <N_IDEAS>     — minimum viable ideas to generate (default: 10)
  
INPUT (optional):
  <ANGLES>      — comma-separated lenses (UX, Pedagogy, Engagement, Accessibility, Monetization, Retention;
                  default: all)
  <CONSTRAINTS> — semicolon-separated constraints
                  (e.g., "cannot break: existing contract; token budget <1M per call")

Token budget for entire flow: ≤ 12k input tokens.

PHASE 0 — INPUTS & VALIDATION
  1. Parse <TARGET> (stage/US/pain/feature area)
  2. Normalize <ANGLES> (validate against known set)
  3. Parse <CONSTRAINTS> (for ranking lower later)
  4. Token budget estimate for Phase 1 — if > 12k: STOP

PHASE 1 — CONTEXT LOAD (read-set, ≤ 2k tokens)
  Read: relevant section of doc/cjm.md, 1–2 user_stories, backlog_registry entries,
        app/<module>.py signatures only.
  
PHASE 2 — BREAKTHROUGH IDEATION
  For EACH lens:
    - Identify world-class analogs (Duolingo, Anki, Khan, Quizlet, Notion, etc.)
    - Apply proven methods (SM-2, retrieval practice, Hook Model, JTBD, Kano, gamification, etc.)
    - Generate ≥ N_IDEAS/|<ANGLES>| candidates per lens
  
  Each candidate:
    title | user_value | method_source (REQUIRED: must reference real source) |
    effort (S/M/L) | impact (Low/Med/High) | risk | dependencies |
    constraint_check (✅ or 🚫)

PHASE 3 — RANKING & TRIAGE
  Score each candidate: (impact × cjm_criticality) / effort
  Top 5 (or 50%-ile): ✅ accept → Phase 4
  Remainder: 🅿️ parked (note reason)
  If viable ideas < 3: STOP with blocker

PHASE 4 — DRAFT DIFFS (read-only artifact)
  Create: archive/ideation/<TARGET_SLUG>_<YYYY-MM-DD>.md
  Include blocks (do NOT apply directly):
    Block 1: Suggested entries for doc/cjm.md (Opportunity rows)
    Block 2: Suggested new User Stories (YAML + acceptance criteria)
    Block 3: Suggested new Packages for doc/backlog_registry.yaml (not tasklist.md)
    Block 4: (optional) Suggested new Epoch or Phase for doc/epochs/
    (All blocks: copy-paste format for manual or orchestration apply)

PHASE 5 — REVIEW HANDOFF
  Output: artifact path + ranking table + next steps
  User reviews blocks, then applies via:
    Path A — Manual: copy blocks → paste into cjm/us/backlog_registry/epochs, edit, commit
    Path B — Automated: run generate_orchestration_prompt on first accepted idea

RULES
  - Read-set ≤ 5 files, ≤ 12k tokens total
  - Write-set: ONLY archive/ideation/<TARGET_SLUG>_<YYYY-MM-DD>.md
  - Forbidden: direct edits to cjm.md / user_stories / backlog_registry / tasklist / epochs (blocks only)
  - Every idea MUST have method_source (real product/algorithm/framework, not invented)
  - If viable ideas < 3: STOP and report blocker
  - Respect <CONSTRAINTS>: ideas violating → ranked lower, marked 🚫

OUTPUT
  - Artifact path (archive/ideation/...)
  - Ranking table (top-N ideas with scores)
  - Open questions / risks / assumptions
  - Next steps (Path A or Path B)

Ignore prior responses/tools. Fresh context only.
```

**Где использовать:** [team_workflow/generate_breakthrough_ideation_prompt.md](team_workflow/generate_breakthrough_ideation_prompt.md)

---

<a id="kilo-budget-health-check"></a>

### Kilo Budget Health Check

Используй для мониторинга бюджета токенов.

```bash
# Быстрая проверка (< 3 секунды)
python scripts/kilo_budget_daily.py

# С локальным estimate
python scripts/kilo_budget_daily.py --use-calibrated-estimate

# Тренд за 7 дней
python scripts/kilo_budget_daily.py --trend 7

# Глубокая диагностика: какой launcher виноват?
python scripts/kilo_budget_gate.py --dry-run

# Что съедает бюджет?
python scripts/kilo_budget_simulate.py simulate \
  --launcher doc/team_workflow/generate_plan_next_prompt.md \
  --injection fixtures/kilo_injection_baseline.json \
  --attribute --section-attribute
```

**Интерпретация результатов:**
- `STATUS: OK` → работай спокойно
- `CAUTION — margin N chars` → тесный запас; подрежь launcher
- `SOFT_BLOCK / HARD_BLOCK` → стоп; запусти attribution
- `REGRESSION DETECTED` → последний коммит сломал бюджет; откати или исправь

**Где использовать:** [team_workflow/budget_health_prompt.md](team_workflow/budget_health_prompt.md)

---

<a id="start-workflow"></a>

### Start Workflow (Запуск Pipeline)

Используй для автоматического запуска workflow с выбором правильного маршрута.

```powershell
# Стандартный вызов (dry-run для проверки)
powershell -ExecutionPolicy Bypass -File scripts/run_start_workflow_e2e.ps1 -Mode dry-run -TargetAgent codex

# Выполнить workflow
powershell -ExecutionPolicy Bypass -File scripts/run_start_workflow_e2e.ps1 -Mode execute -TargetAgent codex

# Для слабых агентов используй .bat вариант
scripts\run_start_workflow_e2e.bat dry-run codex
scripts\run_start_workflow_e2e.bat execute codex
scripts\run_start_workflow_e2e.bat execute codex <PACKAGE_ID>
```

**Автоматический выбор маршрута:**
1. Если в `doc/backlog_registry.yaml` нет активного пакета (`wip`/`ready`) → маршрут **план-next**
2. Если есть артефакты пакета → маршрут **resume**
3. Если пакет сложный → маршрут **orchestration**
4. Если пакет простой → прямо **execution**

**Важно:** В режиме `execute` агент должен продолжить в той же сессии до создания `archive/team_artifacts/<PACKAGE_ID>/execution_contract.md`.

**Где использовать:** [team_workflow/start_workflow.md](team_workflow/start_workflow.md)

---

<a id="run-autonomous-prompt"></a>

### Run Autonomous Prompt (Zero-Click Delivery)

Используй для автоматического выполнения пакетов без остановок.

```text
SSoT: см. `doc/team_workflow/run_autonomous_prompt.md` (актуальная версия промпта).
```

**Статус конвейера в любой момент:**
```bash
.\.venv\Scripts\python.exe scripts/pipeline_status.py
```

**Где использовать:** [team_workflow/run_autonomous_prompt.md](team_workflow/run_autonomous_prompt.md)

**📖 Детальный анализ:** [../archive/doc_team_workflow/archive/zero_click_delivery_analysis.md](../archive/doc_team_workflow/archive/zero_click_delivery_analysis.md) — как работает промпт, описание всех связанных документов (`backlog_registry.yaml` SSoT, производный `tasklist.md`, closed_iterations, pipeline_metrics и др.), порядок их изменения и методика диагностики проблем рассогласованности данных.

**Сценарий в гайде:** [prompts_usage_guide.md § A — Zero-Click Delivery](prompts_usage_guide.md#сценарий-a-запуск-автономного-конвейера-zero-click-delivery).

---

<a id="orchestrator-template"></a>

### Orchestrator Template (Шаблон Оркестратора)

Используй как основу для создания собственного промпта оркестратора. Заполни плейсхолдеры под свой агент.

```text
╔══════════════════════════════════════════════════════════════════╗
║  TEAM PIPELINE ORCHESTRATOR — {{PACKAGE_ID}}                    ║
╚══════════════════════════════════════════════════════════════════╝

You are a team pipeline orchestrator for hometutor.
Your job: coordinate AI agents through the 6-role team pipeline
to deliver package {{PACKAGE_ID}}: {{PACKAGE_TITLE}}.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PACKAGE CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Package ID:    {{PACKAGE_ID}}
Feature:       {{PACKAGE_TITLE}}
CJM Stage:     {{CJM_STAGE}}
User Stories:  {{USER_STORIES}}
Outcomes:
  {{OUTCOMES}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ENVIRONMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Artifacts dir: {{ARTIFACTS_DIR}}
Role prompts:  doc/team_workflow/<role>.md
Max parallel:  {{MAX_PARALLEL}}
Agent spawn:   {{AGENT_SPAWN}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXECUTION PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## STEP 1 — Product Owner  [SEQUENTIAL]

PURPOSE: Define delivery package, confirm CJM binding, list outcomes.

BEFORE STARTING:
{{READ_FILE}} doc/team_workflow/product_owner.md

ACTION:
{{AGENT_SPAWN}}

---

[Полный шаблон — ещё 7 шагов с паралелизмом и ролями]
```

**Плейсхолдеры для заполнения:**
- `{{PACKAGE_ID}}` — идентификатор пакета (e.g., E15-A)
- `{{PACKAGE_TITLE}}` — название фичи
- `{{CJM_STAGE}}` — стадия CJM (Discover / First Answer / Learn / Retain / Progress)
- `{{USER_STORIES}}` — список US (e.g., US-15.3, US-15.4)
- `{{OUTCOMES}}` — что изменится для пользователя (1–5 строк)
- `{{ARTIFACTS_DIR}}` — путь к артефактам
- `{{MAX_PARALLEL}}` — максимум параллельных агентов
- `{{AGENT_SPAWN}}` — синтаксис запуска подагента
- `{{READ_FILE}}` и `{{RUN_CMD}}` — команды по типу агента

**Адаптеры для популярных агентов:**
- [Claude Code](team_workflow/guides/agent_adapter_claude_code.md)
- [Cursor AI](team_workflow/guides/agent_adapter_cursor_ai.md)
- [Codex CLI](team_workflow/guides/agent_adapter_codex.md)

**Где использовать:** [team_workflow/orchestrator_template.md](team_workflow/orchestrator_template.md)

---

## 🎭 Ролевые Промпты (Team Workflow)

<a id="product-owner"></a>

### Product Owner — Планирование пакета

Используй для определения следующего пакета и привязки к CJM.

Каноническая standalone-версия: [team_workflow/product_owner_plan_package_prompt.md](team_workflow/product_owner_plan_package_prompt.md).

```text
Role: Product Owner for hometutor learning assistant.
Goal: define the next delivery package.

Read these files (do not edit yet):
1. doc/backlog_registry.yaml — current active backlog, open/deferred/proposed items
2. doc/cjm.md — customer journey map, pain points by stage
3. doc/future_roadmap.md — strategic horizon (E15+)
4. doc/closed_iterations.md — last 2-3 closed epochs (patterns, size)
5. doc/user_stories.md — index of user stories
6. doc/vision.md — product boundaries and value proposition

Analysis steps:
1. Identify the top CJM pain point that is NOT yet addressed by closed epochs.
2. Find user stories (US-*) that map to this pain point.
3. Check if any deferred items in backlog_registry.yaml should be absorbed.
4. Verify that the proposed work fits within WIP=1 and max 5 outcomes.

Output format:
## Proposed Package: <epoch-package-id>

### CJM Stage
<Which CJM stage and pain point this addresses>

### Goal
<1-2 sentences: what the user gains>

### Outcomes (max 5)
For each outcome:
- Outcome: <what changes for the user>
- User Story: <US-X.Y reference>
- Acceptance Criteria (high-level): <1-3 bullet points>
- CJM Stage: <stage name>

### Dependencies
<What must be true before this package starts>

### Risks
<What might block or change scope>

### Deferred items absorbed
<Items from backlog_registry.yaml with status deferred that this package closes, if any>

Rules:
- Do NOT write code or propose technical solutions.
- Do NOT exceed 5 outcomes per package.
- Every outcome MUST map to a CJM stage and user story.
- If a user story lacks acceptance criteria, flag it for the Analyst.
- Prefer closing existing pain points over opening new horizons.
- Token budget: <= 20k input tokens per call; read only the target registry entry + one US file; no retry with unchanged payload.
```

**Где использовать:** [team_workflow/product_owner_plan_package_prompt.md](team_workflow/product_owner_plan_package_prompt.md); полный ролевой контекст — [team_workflow/product_owner.md](team_workflow/product_owner.md)

---

<a id="analyst"></a>

### Analyst — Детализация пакета

Используй для разработки спецификации пакета с Given-When-Then сценариями.

```text
# [two-root] Two-repo project: resolve app/** and requirements.txt against CODE_ROOT
# (editable install of `hometutor`: `pip show hometutor` -> "Editable project location");
# resolve doc/**, tests/**, scripts/** against the current cwd (DOCS_ROOT).
# Run git per-root: `git -C <CODE_ROOT> ...` for app code, `git -C <cwd> ...` for docs/tests.
Role: Analyst for hometutor learning assistant.
Goal: produce a detailed specification for package <PACKAGE_ID>.

Input from Product Owner:
<paste package definition here>

Read these files (do not edit):
1. doc/user_stories.md — index, find target US-* references
2. doc/user_stories/<US-X.Y>.md — full acceptance criteria for each target story
3. doc/cjm.md — understand the user pain point context
4. doc/conventions.md — engineering constraints
5. doc/api_reference.md — existing API surface
6. app/models.py — core data models (QueryContext, QueryOptions)
7. app/config.py — current settings model

Analysis steps:
1. For each outcome in the package:
   - Map to specific user story acceptance criteria
   - Write Given-When-Then scenarios
   - Identify edge cases and error paths
2. Create detailed feature spec with:
   - User flows (happy path + error paths)
   - Data models affected
   - API contracts (if applicable)
   - UI changes (if any)
3. Identify blockers or assumptions

Output:
## Package Specification: <PACKAGE_ID>

### Outcomes (detailed)
For each outcome:
- User story reference + acceptance criteria
- 3-5 Given-When-Then scenarios
- Edge cases / error paths
- Dependencies on other outcomes

### Assumptions & Blockers
- What must be true for implementation to proceed
- What risks might change scope

Rules:
- Do NOT propose technical implementation.
- Do NOT write code.
- Every scenario MUST be testable (Given-When-Then).
- Token budget: ≤ 20k per call.
```

**Где использовать:** [team_workflow/analyst.md](team_workflow/analyst.md)

---

<a id="architect"></a>

### Architect — Execution Contract

Используй для создания архитектурного контракта и определения write-set.

```text
# [two-root] Two-repo project: resolve app/** and requirements.txt against CODE_ROOT
# (editable install of `hometutor`: `pip show hometutor` -> "Editable project location");
# resolve doc/**, tests/**, scripts/** against the current cwd (DOCS_ROOT).
# Run git per-root: `git -C <CODE_ROOT> ...` for app code, `git -C <cwd> ...` for docs/tests.
Role: Architect for hometutor learning assistant.
Goal: produce an execution contract for package <PACKAGE_ID>.

Input:
- Package specification from Analyst
- Package definition from Product Owner

Read these files (do not edit):
1. doc/conventions.md — engineering constraints
2. doc/conventions_architecture.md — module structure, dependencies
3. doc/conventions_reference.md — API, prompts, tests conventions
4. doc/architecture.md — canonical architecture
5. doc/adr.md — existing decisions
6. doc/agent_workflow_templates.md — contract templates
7. app/config.py — current settings
8. app/api.py + app/routers/ — current API surface
9. app/models.py — core data models

Output: Execution Contract

## Context
<1-2 sentences: what outcome this closes>

## Write-Set (files to create/modify)
List max 5 files:
- file.py — what changes
- file.py — what changes
- tests/test_*.py — what tests

## Read-Set (files to inspect but not change)
- file.py — why needed
- tests/test_*.py — patterns

## Do-Not-Touch
- Lists of areas that must remain unchanged

## DoD (Definition of Done)
- Exact pytest commands + expected results (1 line each)
- Code review checklist items

## Risks & Dependencies
- What could block implementation
- What other packages this depends on

Rules:
- Max 5 files in write-set.
- Every DoD must be testable (command + output).
- Do NOT write code.
- Token budget: ≤ 20k per call.
```

**Где использовать:** [team_workflow/architect.md](team_workflow/architect.md)

---

<a id="designer"></a>

### Designer — UI Specification

Используй для описания UI/UX изменений пакета.

```text
# [two-root] Two-repo project: resolve app/** and requirements.txt against CODE_ROOT
# (editable install of `hometutor`: `pip show hometutor` -> "Editable project location");
# resolve doc/**, tests/**, scripts/** against the current cwd (DOCS_ROOT).
# Run git per-root: `git -C <CODE_ROOT> ...` for app code, `git -C <cwd> ...` for docs/tests.
Role: UX/UI Designer for hometutor Streamlit learning assistant.
Goal: produce a UI specification for package <PACKAGE_ID>.

Input:
- Package specification from Analyst
- Execution contract from Architect (write-set, constraints)

Read these files (do not edit):
1. doc/cjm.md — which CJM stage and pain point
2. doc/user_guide.md — current user-facing documentation
3. doc/user_scenarios.md — user interaction scenarios
4. app/ui/main.py — current Streamlit app structure, navigation
5. app/ui/home_hub.py — home mode selector
6. app/ui/query_tab.py — Q&A interface (reference for patterns)
7. app/ui/tutor_chat.py — tutor chat (reference for chat UX)
8. app/ui/dashboards.py — progress dashboards (reference)
9. Relevant app/ui/*.py files for this package

Output: UI Specification

## Screen Changes
For each screen affected:
- Current state (screenshot reference or description)
- Proposed changes (what's new / what's modified)
- User flows through the changed screens
- Accessibility notes (keyboard nav, labels, ARIA if needed)

## New Components (if any)
- Component name
- Purpose
- States (default, hover, error, loading)
- Interaction patterns (click, input, validation)

## Constraints from Architect
- Files that can be modified (from write-set)
- Styling framework (Streamlit built-in or custom CSS)
- Performance constraints
- Mobile responsiveness (if applicable)

Rules:
- Use Streamlit patterns and components (st.button, st.text_input, etc.)
- Do NOT write code.
- Do NOT exceed 3 screens per package unless specified.
- Accessibility first.
- Token budget: ≤ 20k per call.
```

**Где использовать:** [team_workflow/designer.md](team_workflow/designer.md)

---

<a id="developer"></a>

### Developer — Implementation

Используй для реализации пакета по контракту.

```text
Role: Developer for hometutor learning assistant.
Goal: close <PACKAGE_ID> only.

Context:
<1-2 строки: какую CJM-боль или user-visible outcome закрывает пакет.>

Scope:
<что именно сделать, в 1-3 пунктах.>

Files to inspect first:
- <file/path.py>
- <file/path.py>
- <tests or nearby modules>

Write-Set (ONLY these files may be created or modified):
- <file/path.py> — <what changes>
- <file/path.py> — <what changes>

DoD (Definition of Done):
- <exact pytest command> → <expected result>
- <exact pytest command> → <expected result>
- <observable change in app behavior>

Do not touch:
- <out-of-scope areas>
- <files from read-set>
- <neighboring packages>

Working rules:
- Prefer existing patterns.
- Keep changes minimal and scoped to this package.
- Do not refactor unrelated code.
- Owner/write-set files are not read-set.
- For files >600 lines, use rg/signatures first.
- If blocked, report smallest blocker with exact file/command.
- Token budget: ≤ 12k input tokens per call.

Output:
- Changed files
- Tests run + result (copy-paste output)
- What was completed
- Unresolved risk / follow-up, if any
```

**Где использовать:** [team_workflow/developer.md](team_workflow/developer.md)

---

<a id="tester"></a>

### Tester — Verification

Используй для верификации завершённого пакета.

```text
# [two-root] Two-repo project: resolve app/** and requirements.txt against CODE_ROOT
# (editable install of `hometutor`: `pip show hometutor` -> "Editable project location");
# resolve doc/**, tests/**, scripts/** against the current cwd (DOCS_ROOT).
# Run git per-root: `git -C <CODE_ROOT> ...` for app code, `git -C <cwd> ...` for docs/tests.
Role: Tester for hometutor learning assistant.
Goal: verify package <PACKAGE_ID>.

Inputs:
- CONTRACT_FILE: <path to execution contract>
- PACKAGE_ID: <package identifier>
- COMMIT_RANGE: <e.g., HEAD~3..HEAD>
- PACKAGE_TYPE: <code / doc / mixed>

Read these files (do not edit):
1. The execution contract (CONTRACT_FILE)
2. The package specification from Analyst (if available)
3. doc/conventions.md — for quality checks
4. doc/agent_workflow_test_bundles.md — test bundles

## Step 1: Scope Check
Run: git diff --name-only <COMMIT_RANGE>
Expected: All changed files must be in write-set from contract.

## Step 2: DoD Verification
For each DoD command in contract:
- Run the exact command
- Verify output matches expected result
- Report PASS or FAIL

## Step 3: Quality Spot Check
- Code follows conventions.md patterns
- No obvious violations (hardcoded configs, unsafe imports, etc.)
- Tests cover the outcomes (not exhaustive, just spot-check)

## Step 4: Regression Check (if PACKAGE_TYPE=code)
Run test suite for affected modules.
Expected: No new test failures vs. baseline.

## Verdict
- **PASS**: Package meets contract. Ready to merge.
- **CONDITIONAL PASS**: Minor findings are follow-up (not blocking).
- **FAIL**: Blocker found. Specify exact finding with evidence command.

Output:
- VERDICT: PASS | CONDITIONAL PASS | FAIL
- Findings (if any):
  - id | severity | description | evidence_cmd | expected_output
- Fix-prompt (if FAIL): ready-to-copy for Developer in fresh context

Rules:
- Every finding must have reproducible evidence (rg cmd, pytest cmd, etc.)
- Do NOT edit code; only verify and report.
- Token budget: ≤ 12k input tokens per call.
```

**Где использовать:** [team_workflow/tester.md](team_workflow/tester.md)

---

<a id="epoch-demo-prompt-package"></a>

### Epoch-Demo — промпт: package (`backlog_registry`, generated `tasklist`, артефакты, `prompt_utils`)

```text
Цель: (1) если пакета `epoch-demo` нет — создать минимальный каркас в `backlog_registry.yaml` и артефактах, затем регенерировать `tasklist.md`; (2) если пакет был закрыт — переоткрыть и подготовить к повторному прогону; (3) при **активной работе** пакета добавить в `scripts/prompt_utils.py` ровно **одну** демо-функцию, возвращающую строку (с однократным `uuid` внутри тела); (4) при **переоткрытии** после закрытия — **удалить эту функцию** из `prompt_utils.py` и сбросить артефакты пакета, чтобы сценарий можно было снова пройти с нуля. Запуск `run_autonomous --post-agent` — **не** в этом промпте.

Контекст:
- Репозиторий: <REPO_ROOT> (подставь корень checkout)
- Python/проверки: .\.venv\Scripts\python.exe
- Разрушительные git-операции (`reset --hard`, `clean -fd`) — **только** с явным подтверждением в чате

---

## A. Детекция состояния

Определи одно из:

- **A1. Нет пакета:** в `doc/backlog_registry.yaml` нет записи `epoch-demo` со статусом `ready`/`wip`, нет synced generated view в `doc/tasklist.md`, нет `archive/team_artifacts/epoch-demo/`.
- **A2. Активен:** пакет в `backlog_registry.yaml` (`wip`/`ready`/`open`), generated view и контракт на месте.
- **A3. Закрыт:** статус `closed` в `doc/backlog_registry.yaml`, есть запись в `doc/closed_iterations.md` / и т.п.

Если **A2** и переоткрытие **не** требуется (только проверка) — можно остановиться с отчётом «уже в работе». Если нужен «чистый старт» при активном пакете — выполни раздел **C** + **D** по согласованию (как форс-ресет).

---

## B. Создание пакета (если A1)

1 **`doc/backlog_registry.yaml`**
   - Запись `epoch-demo` со статусом `ready` или `wip`.
   - Поля контракта:
     - **PACKAGE_ID:** `epoch-demo`
     - **Title:** коротко (smoke / demo)
     - **USER_STORIES:** `n/a (smoke)` — без выдуманных `US-x.y`, если не создаёшь реальные файлы stories
     - **OUTCOMES:** одна строка, достаточная для парсера
     - **TARGET_ARTIFACTS:** минимум `scripts/prompt_utils.py` (см. раздел D)
     - **DOD_COMMANDS:** одна **узкая** команда (не полный `pytest tests/`)
   - Пути в TARGET — только **существующие** в репо на момент правки (кроме явно создаваемого в D).

2 **`archive/team_artifacts/epoch-demo/`**
   - Создай каталог.
   - `execution_contract.md` — короткий placeholder (например `STARTED`), достаточный для жизненного цикла артефакта.

3 **Индексы**
   - `doc/tasklist.md` — **не редактировать вручную**; регенерировать через `backlog_registry_lint.py --sync-from-index --write-sync`.
   - `doc/user_stories/*.md`, `doc/user_stories_index.json` — **только** если в контракте реальные `US-x.y` и нужна связь; для `n/a` — **не трогай**.
   - `doc/changelog.md` — по политике команды (опционально одна строка о появлении пакета).

4 Линт registry (если правил): `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`

---

## B2. Переоткрытие пакета (если A3)

1 **`doc/backlog_registry.yaml`** — `closed` → `ready`/`wip`; восстанови полный контракт из `closed_iterations`, предыдущего коммита или минимально заново, если копии нет.

2 **`doc/tasklist.md`** — только regenerated view после `backlog_registry_lint.py --sync-from-index --write-sync`.

3 **User stories** — только если пакет закрывал реальные US: открой статусы / `covered_by` по правилам репо и пересобери `doc/user_stories_index.json` штатным скриптом. Иначе не трогай.

4 **`doc/closed_iterations.md`** — прошлые записи **не вырезать**; при необходимости одна короткая пометка о переоткрытии (по соглашению).

---

## C. Сброс при переоткрытии (обязательно перед повторным прогоном)

1 **`scripts/prompt_utils.py`**
   - **Удали целиком** демо-функцию из раздела D (точное имя — как при создании; без рефакторинга остального файла).
   - Проверь, что нет «осиротевших» импортов/вызовов только ради неё.

2 **`archive/team_artifacts/epoch-demo/execution_contract.md`**
   - Сбрось к короткому placeholder для нового прогона.

3 Проверка: `.\.venv\Scripts\python.exe -m py_compile scripts/prompt_utils.py`
   Узкий pytest — только если есть релевантный тест и вы договорились (не полный suite).

---

## D. Добавление кода в активной итерации (один раз за прогон пакета)

**Файл:** только `scripts/prompt_utils.py` (минимальный diff).

**Добавь одну функцию** с **фиксированным говорящим именем**, например:
- `epoch_demo_placeholder_text`
(имя должно быть уникальным и легко находимым через `grep`.)

**Смысл контракта:**

- Возвращает `str`.
- **Вариативность:** достаточно **один раз** в теле функции получить значение (например `uuid.uuid4()`) и **сразу** подставить его в возвращаемую строку (без состояния между вызовами, без лишней логики).
- Не тянуть тяжёлые зависимости; стандартная библиотека достаточна (`uuid` уже в stdlib).
- Не менять существующие публичные API; ничего не подключать к прод-пайплайну — только демо для пакета.
- Комментарий у функции: `# epoch-demo: temporary — remove on package reopen`

**Write-set в контракте `epoch-demo`:** укажи `scripts/prompt_utils.py` в **TARGET_ARTIFACTS** / write-set.

**Работа с файлом:** не читать `prompt_utils.py` целиком; правка — маленьким патчем; при сомнениях — `rg "def epoch_demo"` / сигнатуры.

---

## E. Ограничения

- Не запускать `run_autonomous.py` / `--post-agent` в этом промпте.
- Не запускать полный `pytest tests/`.
- Не трогать несвязанные модули кроме согласованного write-set.
- Для отката **всего** пакета по git, если когда-то понадобится шире, чем удаление одной функции — отдельное согласование; **в базовом сценарии переоткрытия** достаточно раздела C.

---

## F. Итоговый отчёт

- Состояние до: A1 | A2 | A3
- Сделано: create | reopen | reset artifacts | add function | remove function
- Имя демо-функции (если применимо)
- Список изменённых файлов
- `py_compile` / `backlog_registry_lint`: OK или FAIL (с причиной)
```

---

<a id="epoch-demo-prompt-post-agent-smoke"></a>

### Epoch-Demo — промпт: smoke `run_autonomous --post-agent`

Полная версия с пояснениями и exit-кодами: [team_workflow/archive/epoch_demo_post_agent_smoke.md](team_workflow/archive/epoch_demo_post_agent_smoke.md). Успех без `--non-stop` → **`exit 0`**; успех **`--non-stop`** (продолжение в той же сессии) → **`exit 10`**; см. также [run_autonomous_prompt.md](team_workflow/run_autonomous_prompt.md). Ниже — эталон как в `PROMPT_POST_AGENT_SMOKE` (подставь `<REPO_ROOT>`).

```text
Цель: выполнить быстрый smoke реального CLI-потока `run_autonomous.py --post-agent` на тестовом пакете `epoch-demo` и вручную проверить UX блокировок (не unit-тесты).

Контекст:
- Репозиторий: <REPO_ROOT> (корень checkout: есть каталоги `app/`, `scripts/`, `doc/`)
- ОС: Windows / PowerShell (или ваш терминал; команды ниже — вид для PowerShell из корня репо)
- Python: .\.venv\Scripts\python.exe из корня репозитория
- Пакет: `epoch-demo` — должен быть в `doc/backlog_registry.yaml`, производный `doc/tasklist.md` синхронизирован, есть `archive/team_artifacts/epoch-demo/execution_contract.md`
- Важно: скрипт `scripts/run_autonomous.py` НЕ переоткрывает пакет автоматически. Если в registry статус `closed`, переоткрытие делает исполнитель этого промпта ДО любого запуска `run_autonomous.py`.

Шаги:

1) Перейди в корень репозитория. Префлайт статуса:
   .\.venv\Scripts\python.exe scripts/print_reopen_package_workflow.py --package epoch-demo

2) Только если префлайт показал `registry status: 'closed'` — сразу выполни **автоматический полный Step C** (до шага 3), одной командой из корня репозитория:
   .\.venv\Scripts\python.exe scripts/reopen_epoch_demo_step_c.py --reason "smoke post-agent: registry closed before --post-agent"
   Скрипт выставляет `ready`, правит индексы/changelog/`doc/current_task.md` по канону для smoke-пакета `epoch-demo` и дважды вызывает `backlog_registry_lint.py --sync-from-index --write-sync` (второй раз с `--strict`). Он **не** делает git commit (C.8) и **не** сбрасывает `prompt_utils` / `execution_contract.md` — при необходимости сбрось артефакты по промпту `package` (`scripts/print_epoch_demo_agent_prompts.py package`) **после** успешного скрипта и до `run_autonomous.py`, если сценарий требует «чистый» прогон.
   Если автоматизация не подходит (другой пакет, спорный REASON, нестандартные US) — вручную полный Step C по `doc/team_workflow/reopen_package_step_c_prompt.md`, затем всё равно lint как в каноне.
   Если статус уже `ready`/`wip`, шаг 2 пропускаешь (скрипт при вызове тоже noop с кодом 0); достаточно актуального tasklist и `execution_contract.md`.

3) Только после выполнения шагов 1–2 запусти один реальный вызов:
   .\.venv\Scripts\python.exe scripts/run_autonomous.py --post-agent --package epoch-demo --budget-profile strict

   Опционально (без кэша DoD для этого прогона): добавь `--no-dod-cache`

4) Зафиксируй: exit code; ключевые строки stderr/stdout; ветку (verification_only / unknown / execution hard gate / DoD / другое).

5) UX: понятная причина блокировки; actionable next steps; согласованные подсказки (`allow_verification_only`, `evidence_inconclusive_allowed` где уместно); нет противоречий между сообщениями.

6) Краткий отчёт в чат: Command — Exit code — Branch — Key messages (3–8 строк) — UX PASS или FAIL — при FAIL: что не так и куда смотреть (файл/область).

Ограничения: не полный `pytest tests/` как замена этому smoke; без force-push; без несанкционированных правок CI.

Критерий готовности: один реальный запуск `--post-agent` выполнен, результат и UX оценены.
```

---

<a id="closed-packages-audit-snapshot-2026-04-20-cursor-ai"></a>

<a id="audit-coverage-prompt-generator"></a>

### Audit Coverage Prompt Generator — шаблон запуска

Используй после того, как `generate_audit_closed_packages_prompt.md` уже создал основной audit prompt и audit-группы:
`doc/team_workflow/audit_groups_${PERIOD_SLUG}_${TARGET_AGENT}/group_*.md`.

**Канон на диске:** [team_workflow/generate_audit_packages_coverage_prompt.md](team_workflow/generate_audit_packages_coverage_prompt.md).  
**Пример сгенерированного prompt:** [../archive/doc_team_workflow/audit_coverage_prompt_2026-04_cursor_ai.md](../archive/doc_team_workflow/audit_coverage_prompt_2026-04_cursor_ai.md).

```text
Прочитай doc/team_workflow/generate_audit_packages_coverage_prompt.md
TARGET_AGENT: cursor_ai
PERIOD: 2026-04
SCOPE: closed
```

Цепочка:

1. `generate_audit_closed_packages_prompt.md` → `audit_prompt_${PERIOD_SLUG}_${TARGET_AGENT}.md`.
2. Выполнение audit prompt → `audit_groups_${PERIOD_SLUG}_${TARGET_AGENT}/run_next_group_coverage_audit.md`, `group_*.md`, `coverage_dod_analysis.md`.
3. `generate_audit_packages_coverage_prompt.md` → `audit_coverage_prompt_${PERIOD_SLUG}_${TARGET_AGENT}.md`.
4. Выполнение coverage prompt → group coverage reports, обновлённый `_audit_raw.json`, обновлённый `coverage_dod_analysis.md`.

---

### Closed Packages Audit — самодостаточный промпт (снимок)

**Параметры снимка:** `PERIOD=2026-04-20..2026-04-28`, `SCOPE=closed,wip`, `DEPTH=index_only`, `TARGET_AGENT=cursor_ai`.  
**Канон на диске (синхронизируйте при регенерации):** [archive/team_workflow_snapshots/audit_prompt_2026-04-20__2026-04-28_cursor_ai.md](../archive/team_workflow_snapshots/audit_prompt_2026-04-20__2026-04-28_cursor_ai.md).  
**Генератор:** [team_workflow/generate_audit_closed_packages_prompt.md](team_workflow/generate_audit_closed_packages_prompt.md).

Текст ниже — для вставки в **новый чат** без повторного запуска генератора.

~~~~

╔══════════════════════════════════════════════════════════════╗
║ CLOSED PACKAGES AUDIT — 2026-04-20..2026-04-28  [2026-04-20 .. 2026-04-28]  [cursor_ai]
║ Depth: index_only | Scope: closed,wip
╚══════════════════════════════════════════════════════════════╝

> **Генератор:** `doc/team_workflow/generate_audit_closed_packages_prompt.md` Phase A3.
> В запросе указаны оба режима dod_replay и index_only; для исполнения Step B принят **index_only** (перезапуск с `DEPTH=dod_replay` включает DoD replay).

This is a self-contained audit prompt. Do not re-read the generator.
Run steps A → D in order. Process one package at a time.

**Tooling (Cursor AI):**
- Читать файлы: `@путь` (напр. `@doc/backlog_registry.yaml`, `@app/foo.py:10-90`)
- Команды: встроенный терминал (pytest, grep, git, python)
- Записывать: правки через агент/IDE («Save to: …»)

────────────────────────────────────────────────────────────────

Pre-Audit Index Sync: `2026-04-20..2026-04-28` (**2026-04-20 .. 2026-04-28**)

| Метрика | Значение |
|---------|----------|
| Пакеты в backlog_registry (SCOPE `closed,wip`) | **72** |
| Уникальных `###` заголовков в closed_iterations за период | **72** |
| Совпадение Registry ↔ CI (по спискам) | **0 orphan CI**, **0 без CI-heading** |
| Пакеты с хотя бы одним US в `user_stories_index` за окно дат | **20** |

Табличный pre-sync по каждому пакету — ниже (колонка **Pre-check**: PASS если CI и US есть; WARN если только US пропускается там, где историй нет для пакета в окне дат).

── PACKAGE LIST (from generator Phase A2) ────────────────────────

| # | Package ID | Title | Registry | CI Entries | US Index | Pre-check |
|---|---|---|:---:|:---:|:---:|:---:|
| 1 | `epoch-17-1-ux-tail` | UX-tail polish: deterministic primary CTA on entry surf... | OK | OK | MISS | WARN |
| 2 | `epoch-5min-loop-polish` | Stabilize the 5-minute learner flow answer -> micro-qui... | OK | OK | MISS | WARN |
| 3 | `epoch-adaptive-plan-today` | Plan for today after the first session, connecting firs... | OK | OK | MISS | WARN |
| 4 | `epoch-answer-quality-baseline` | Eval pipeline + baseline score + CI gate; scripts/run_a... | OK | OK | OK | PASS |
| 5 | `epoch-answer-quality-eval` | CI-visible answer-quality gate for First Answer trust m... | OK | OK | MISS | WARN |
| 6 | `epoch-aqe-corpus-choice` | Выбор и формирование golden set для AQE: synthetic corp... | OK | OK | MISS | WARN |
| 7 | `epoch-architecture-review-baseline` | Query service boundary остается разделенной на knowledg... | OK | OK | MISS | WARN |
| 8 | `epoch-backup-benchmark-close` | tests/test_backup_benchmark_acceptance.py` — US-10.1: `... | OK | OK | OK | PASS |
| 9 | `epoch-citations-trust-close` | tests/test_citations_trust.py` — acceptance-level тесты... | OK | OK | MISS | WARN |
| 10 | `epoch-cjm-us-frontmatter` | Structured pain→moment→status map + US frontmatter inde... | OK | OK | MISS | WARN |
| 11 | `epoch-concept-remediation-step` | Tutor предлагает конкретные шаги исправления по каждому... | OK | OK | OK | PASS |
| 12 | `epoch-context-cart-mvp` | Token-safe context assembly for plan/orchestration/veri... | OK | OK | MISS | WARN |
| 13 | `epoch-control-plane-v3-core` | pipeline_state.json + result.json в logs/autonomous_run... | OK | OK | MISS | WARN |
| 14 | `epoch-course-workspace-ab` | Course Workspace: activate folder as course, focus quer... | OK | OK | MISS | WARN |
| 15 | `epoch-course-workspace-d` | Course Workspace: generate flashcards from document, ge... | OK | OK | MISS | WARN |
| 16 | `epoch-course-workspace-e` | Course Workspace: review due flashcards by SM-2, genera... | OK | OK | MISS | WARN |
| 17 | `epoch-course-workspace-f` | Course Workspace: transition from hard card to tutor, s... | OK | OK | MISS | WARN |
| 18 | `epoch-demo` | smoke package scaffolding for post-agent CLI verification | OK | OK | MISS | WARN |
| 19 | `epoch-demo-pipeline-hardening` | Demo pipeline hardening: narrative ordering, strict val... | OK | OK | MISS | WARN |
| 20 | `epoch-demo-scenario-03-tutor` | Demo показывает переход Answer → Tutor за один клик с с... | OK | OK | MISS | WARN |
| 21 | `epoch-demo-scenario-04-quiz` | Demo показывает formative assessment с немедленной обра... | OK | OK | MISS | WARN |
| 22 | `epoch-demo-scenario-06-srs` | Demo показывает: система знает что студент забывает и н... | OK | OK | OK | PASS |
| 23 | `epoch-demo-scenario-07-progress` | Demo показывает: dashboard не декоративный — каждая циф... | OK | OK | MISS | WARN |
| 24 | `epoch-demo-scenario-08-trust` | Demo доказывает anti-hallucination: каждый тезис → фраг... | OK | OK | OK | PASS |
| 25 | `epoch-demo-scenario-09-learning-plan` | Demo показывает: AI не отвечает — AI ведёт по учебному ... | OK | OK | MISS | WARN |
| 26 | `epoch-e30-a1-cockpit-scaffold` | Phase A: `app/ui/course_cockpit.py` — 3-column layout, ... | OK | OK | MISS | WARN |
| 27 | `epoch-e30-a2-cockpit-rotator` | Phase A: `app/ui/cockpit_rotator.py` — interleaved rota... | OK | OK | MISS | WARN |
| 28 | `epoch-e30-b1-graduation-overlay` | Phase B: `app/ui/graduation_overlay.py` — concept gradu... | OK | OK | MISS | WARN |
| 29 | `epoch-e30-b2-daily-briefing` | Phase B: `app/ui/daily_briefing.py` — morning brief + e... | OK | OK | MISS | WARN |
| 30 | `epoch-e30-c1-diagnostic` | Phase C: `app/diagnostic_service.py` — pre-flight adapt... | OK | OK | MISS | WARN |
| 31 | `epoch-e30-c2-pace-engine` | Phase C: `app/pace_engine.py` — Sprint/Steady/Deep, rol... | OK | OK | OK | PASS |
| 32 | `epoch-e30-d1-smart-resume` | Phase D: `app/warmup_planner.py` — pause tiers, soft-re... | OK | OK | OK | PASS |
| 33 | `epoch-e30-d2-focus-mode` | Phase D: `app/ui/focus_mode.py` — Pomodoro 25/5, distra... | OK | OK | OK | PASS |
| 34 | `epoch-e30-e1-course-graduation` | Phase E: `app/course_graduation.py` — course graduation... | OK | OK | OK | PASS |
| 35 | `epoch-e30-idea-1-daily-runway` | Ideation stage7: дневная микро-цель (N шагов / M минут)... | OK | OK | OK | PASS |
| 36 | `epoch-e30-idea-2-retrieval-gates` | Ideation stage7: 1–3 retrieval-вопроса между K-модулями... | OK | OK | OK | PASS |
| 37 | `epoch-env-required-vars` | UI shows missing-env warning | OK | OK | MISS | WARN |
| 38 | `epoch-first-answer-examples` | Hero-экран показывает 3 кликабельных example questions,... | OK | OK | OK | PASS |
| 39 | `epoch-flashcard-deck-mgmt` | Learner может редактировать/удалять карточки и колоды и... | OK | OK | MISS | WARN |
| 40 | `epoch-flashcard-export-upload` | Экспорт колоды в Anki .apkg; загрузка PDF/text файла из... | OK | OK | MISS | WARN |
| 41 | `epoch-flashcard-export-upload-r2` | Экспорт выбранной колоды в `.apkg` доступен из UI; загр... | OK | OK | MISS | WARN |
| 42 | `epoch-ingest-first-index-progress` | CLI первой индексации выводит стабильный прогресс: proc... | OK | OK | OK | PASS |
| 43 | `epoch-inline-citations-first-answer` | Inline citations in first answer | OK | OK | MISS | WARN |
| 44 | `epoch-latency-slo-gate` | p95 latency CI gate интегрирован в pre-merge workflow; ... | OK | OK | MISS | WARN |
| 45 | `epoch-llm-regression-baseline` | Full LLM regression suite с golden baselines; nightly C... | OK | OK | OK | PASS |
| 46 | `epoch-mastery-after-reindex` | Preserve mastery and show an explicit profile-updated b... | OK | OK | MISS | WARN |
| 47 | `epoch-mastery-gap-routing` | Orchestrator маршрутизирует следующую тему исходя из ре... | OK | OK | OK | PASS |
| 48 | `epoch-micro-quiz-feedback-tail` | Submit feedback tail ships status/explanation/one CTA c... | OK | OK | MISS | WARN |
| 49 | `epoch-plan-diff-ux` | Expander «Что изменилось» в Adaptive Plan card показыва... | OK | OK | MISS | WARN |
| 50 | `epoch-plan-next-candidate-seed` | Планировочный цикл не блокируется drift-ошибками на ста... | OK | OK | MISS | WARN |
| 51 | `epoch-qa-tutor-handoff` | One-click handoff from Quick Answer to Tutor with prese... | OK | OK | MISS | WARN |
| 52 | `epoch-query-service-assembly` | Query flow разбит на knowledge lookup, rag assembly и f... | OK | OK | MISS | WARN |
| 53 | `epoch-query-service-assembly-v2` | Query service assembly path remains stable for knowledg... | OK | OK | MISS | WARN |
| 54 | `epoch-quiz-hint-on-fail` | Hint instead of strict fail in micro-quiz, reducing dro... | OK | OK | MISS | WARN |
| 55 | `epoch-reindex-mastery-guard` | Reindex mastery guard: mastery and profile preserved af... | OK | OK | MISS | WARN |
| 56 | `epoch-reindex-quiz-close` | tests/test_reindex_quiz_acceptance.py` — US-2.2: `plan_... | OK | OK | MISS | WARN |
| 57 | `epoch-router-accuracy-baseline` | Router accuracy baseline воспроизводимо считается на `e... | OK | OK | MISS | WARN |
| 58 | `epoch-srs-plan-close` | tests/test_srs_recovery_plan.py` — US-7.2: `defer_due_f... | OK | OK | MISS | WARN |
| 59 | `epoch-srs-priority-queue` | SRS priority queue: learner sees due reviews with prior... | OK | OK | MISS | WARN |
| 60 | `epoch-srs-priority-reason` | В top-priority due блоке показывается краткая причина п... | OK | OK | MISS | WARN |
| 61 | `epoch-sync-multidevice` | Multi-device parity: экспорт/импорт bundle + merge-конф... | OK | OK | MISS | WARN |
| 62 | `epoch-sync-restore-wizard` | Restore wizard в Settings: загрузка файла, валидация sy... | OK | OK | MISS | WARN |
| 63 | `epoch-tour-demo-doc-refresh` | Quickstart demo обновлён: добавлен вводный раздел про i... | OK | OK | OK | PASS |
| 64 | `epoch-tour-persistence-ch2-5` | Guide-runtime сохраняет/восстанавливает прогресс и пров... | OK | OK | OK | PASS |
| 65 | `epoch-tour-scenarios-10-14` | Добавлены и зелёные в demo pipeline сценарии 10–14: day... | OK | OK | OK | PASS |
| 66 | `epoch-tour-skeleton-ch1` | Skeleton интерактивного тура: state, overlay (CSS-only)... | OK | OK | OK | PASS |
| 67 | `epoch-truth-sync` | scripts/rebuild_user_stories_index.py` пересоздаёт `doc... | OK | OK | OK | PASS |
| 68 | `epoch-tutor-transparency` | Learner-facing explanation of tutor orchestration decis... | OK | OK | MISS | WARN |
| 69 | `epoch-ui-main-split` | app/ui/main.py` becomes a lightweight router entrypoint... | OK | OK | MISS | WARN |
| 70 | `epoch-unified-context-layer` | Persistent topic / mastery% / due / streak strip across... | OK | OK | MISS | WARN |
| 71 | `epoch-us7-3-resume-card` | Day-2 resume card: learner returns to the last useful l... | OK | OK | MISS | WARN |
| 72 | `epoch-wave-contract` | doc/backlog_registry.yaml` schema bumped to v2 с блоком... | OK | OK | MISS | WARN |

────────────────────────────────────────────────────────────────

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP A — INDEX CONSISTENCY CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each package `<id>` in the PACKAGE LIST above:

**A.1 Registry entry:**

Verify `doc/backlog_registry.yaml` contains:

- `status`: `closed` (или `wip` если в scope включён wip и строка есть в этом списке)
- `last_review` или `closed_date` попадают в интервал **[2026-04-20, 2026-04-28]** (см. `scripts/audit_closed_packages_helpers.py`)

→ Registry: OK | MISSING

**A.2 closed_iterations.md entry:**

Expect a closure heading ``### `<id>` — YYYY-MM-DD``` with date within **[2026-04-20, 2026-04-28]**.

Дополнительно:

```powershell
grep -n "<id>" doc/closed_iterations.md
```

→ CI Index: OK | MISSING | ORPHAN

**A.3 User story consistency:**

```powershell
.\.venv\Scripts\python.exe -c "
import json
from pathlib import Path
data = json.load(open('doc/user_stories_index.json', encoding='utf-8'))
stories = data if isinstance(data, list) else (data.get('items') or data.get('stories', []))
pkg = '<id>'
for s in stories:
    if s.get('covered_by') == pkg:
        print(s.get('us_id', s.get('id')), s.get('status'), s.get('closed_date', ''))
"
```

For each US with `covered_by == <id>`: `status` must be `closed` AND `closed_date` (если указана) должна входить в **[2026-04-20, 2026-04-28]**.

→ US Index: OK | MISMATCH

**A.4 CJM consistency:**

```powershell
grep -n "<id>" doc/cjm.md | Select-Object -First 20
```

(Pри необходимости добавить US-id из A.3 в паттерн.)

→ CJM: OK | INCOMPLETE | NOT_FOUND

Record: `A_RESULT[<id>] = {registry, ci_index, us_index, cjm}`

Если MISSING/MISMATCH — `INDEX_FAIL[<id>] = true` → переход к Step C (**без Step B**, т.к. индекс неверен).

Если только US «нет связанных строк в окне» для пакетов без связанных US — зафиксировать как WARN в отчёте, без revert по умолчанию.

Если всё ок → `INDEX_PASS` → для **DEPTH=index_only** **пропуск Step B**, сразу **Step D** по этому пакету.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP B — DoD REPLAY  [skipped — DEPTH = index_only]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Текущий режим генератора: `index_only`** — команды pytest/DoD **не выполняются** в этом прогоне.

Чтобы включить описанную ниже проверку, скопируйте этот промпт в новый чат с **`DEPTH=dod_replay`** (без index_only):

For each `<id>` with `INDEX_PASS[<id>] == true`:

**B.1–B.5:** как в § Generated Prompt аудита в `generate_audit_closed_packages_prompt.md`:
- читать `exit_artifact`, `archive/team_artifacts/<id>/3_architect_contract.md` (DoD через `head`/grep),
- выполнять все команды из DoD, regression bundle из `doc/agent_workflow_test_bundles.md` или `doc/team_workflow/tester.md`.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP C — REVERT PROCEDURE  [only for INDEX_FAIL или FAIL/STALE при dod_replay]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Только если подтверждён сбой Step A или (после `dod_replay`) Step B. Атомарно по одному `<id>`.

См. шаблон C.1–C.8 в `doc/team_workflow/generate_audit_closed_packages_prompt.md` (переменные `$PERIOD_SLUG` = `2026-04-20__2026-04-28`, даты начала/конца = выше).

Commit message: `audit(2026-04-20__2026-04-28): reopen <id> — <reason>`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP D — FINAL AUDIT REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Структурированный отчёт Markdown; сохранить в:

`archive/team_artifacts/audit_2026-04-20__2026-04-28/audit_report.md`

**Summary:** после **index_only** ожидается отчёт по сверке индексов; DoD столбцы — «skipped».

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AUDIT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Не править код и не исправлять баги в этом прогоне (кроме Step C при явном FAIL по правилам).
- Не переоткрывать пакеты при одном только WARN без подтверждённой рассинхронизации регистра/registry.
- Токены: использовать `grep`/`head` для больших файлов; см. `doc/token_safety.md`.

Report save path slug: **`audit_2026-04-20__2026-04-28`** = `audit_2026-04-20__2026-04-28`

Literal bindings for this audit:

| Key | Value |
|-----|-------|
| PERIOD | `2026-04-20..2026-04-28` |
| START_ISO | `2026-04-20` |
| END_ISO | `2026-04-28` |
| DEPTH | `index_only` |
| SCOPE | `closed,wip` |
| TARGET_AGENT | `cursor_ai` |


~~~~

---

<a id="reopen-batch-closed-window-last3days-example"></a>

### Batch reopen (closed → ready) — пример по [reopen_prompt_closed_window_template.md](team_workflow/reopen_prompt_closed_window_template.md)

**Параметры примера:** `PERIOD=2026-04-26..2026-04-28`, `SCOPE=closed`, `TODAY=2026-04-28`, **13** пакетов.  
**Канон — файл-пример:** [archive/team_workflow_snapshots/reopen_instance_last3days_2026-04-26__2026-04-28.md](../archive/team_workflow_snapshots/reopen_instance_last3days_2026-04-26__2026-04-28.md).

Текст ниже — для вставки в **новый чат**; строку `REASON` уточни вручную перед запуском.

~~~~

╔══════════════════════════════════════════════════════════════════╗
║  BATCH REOPEN (closed → ready)
║  Window: [2026-04-26 .. 2026-04-28]   PERIOD_SLUG: 2026-04-26__2026-04-28
║  Template: doc/team_workflow/reopen_prompt_closed_window_template.md
╚══════════════════════════════════════════════════════════════════╝

ROLE: Apply Step C (REVERT PROCEDURE) only, from:
  doc/team_workflow/generate_audit_closed_packages_prompt.md — § STEP C.
  Do NOT change application code except doc/registry files listed in Step C.
  Do NOT skip substeps.

GLOBAL:
  PERIOD_SLUG = 2026-04-26__2026-04-28
  START_ISO   = 2026-04-26
  END_ISO     = 2026-04-28
  REASON      = "admin reopen: batch last-3-days window 2026-04-26..2026-04-28 — <уточни человеком>"
  TODAY       = 2026-04-28

For EACH <id> IN LIST BELOW — sequential order — one complete Step C + one git commit:

  PACKAGE_IDS_ORDERED = (
    epoch-control-plane-v3-core,
    epoch-demo,
    epoch-e30-a1-cockpit-scaffold,
    epoch-e30-a2-cockpit-rotator,
    epoch-e30-b1-graduation-overlay,
    epoch-e30-b2-daily-briefing,
    epoch-e30-c1-diagnostic,
    epoch-e30-c2-pace-engine,
    epoch-e30-d1-smart-resume,
    epoch-e30-d2-focus-mode,
    epoch-e30-e1-course-graduation,
    epoch-e30-idea-1-daily-runway,
    epoch-e30-idea-2-retrieval-gates
  )

STEP C — per `<id>` (полный текст подпунктов C.1 … C.8 см. generate_audit_closed_packages_prompt.md):

  C.1 doc/backlog_registry.yaml
  C.2 doc/closed_iterations.md
  C.3 doc/user_stories_index.json  — US с covered_by == <id> и closed_date в [START_ISO, END_ISO]
  C.4 doc/user_stories/<US>.md      — только frontmatter
  C.5 doc/cjm.md
  C.6 doc/changelog.md             — только append
  C.7 после правок индекса: .\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync
  C.8 git commit на один id: audit(2026-04-26__2026-04-28): reopen <id> — <REASON>

After all IDs: .\.venv\Scripts\python.exe scripts/backlog_registry_lint.py  (exit 0)

Report: таблица | Package | reopened | commit |

~~~~

---

## 📋 Индекс Всех Промптов По Файлам

| Файл | Промпты |
|---|---|
| [agent_workflow_templates.md](agent_workflow_templates.md) | Planning, Verify, Fix, Micro-Plan, Micro-Execute, Micro-Verify |
| [agent_workflow_arch_review.md](agent_workflow_arch_review.md) | Architecture Review (Phase 1–5) |
| [agent_workflow_test_bundles.md](agent_workflow_test_bundles.md) | Test bundles (tutor, query, learner, api, user state) |
| [team_workflow/generate_plan_next_prompt.md](team_workflow/generate_plan_next_prompt.md) | generate_plan_next |
| [team_workflow/product_owner_router.md](team_workflow/product_owner_router.md) | Product Owner Router (выбор: plan-next / ideation / package / waves / execution) |
| [team_workflow/generate_orchestration_prompt.md](team_workflow/generate_orchestration_prompt.md) | generate_orchestration |
| [team_workflow/generate_execution_prompt_auto.md](team_workflow/generate_execution_prompt_auto.md) | generate_execution_auto |
| [team_workflow/generate_resume_prompt.md](team_workflow/generate_resume_prompt.md) | generate_resume |
| [team_workflow/run_audit_chain_prompt.md](team_workflow/run_audit_chain_prompt.md) | run_audit_chain (мастер-промпт всей audit/coverage цепочки; текст запуска: [§](#audit-chain-master-prompt)) |
| [../archive/doc_team_workflow/ssot_full_audit_prompt.md](../archive/doc_team_workflow/ssot_full_audit_prompt.md) | SSoT Full Audit Prompt (`CJM + user_stories_index + backlog_registry` плюс full audit chain / DoD replay) |
| [../archive/doc_team_workflow/audit_chain_prompt_2026-04_cursor_ai.md](../archive/doc_team_workflow/audit_chain_prompt_2026-04_cursor_ai.md) | ready-to-run audit chain snapshot for `PERIOD=2026-04`, `TARGET_AGENT=cursor_ai` |
| [team_workflow/generate_audit_closed_packages_prompt.md](team_workflow/generate_audit_closed_packages_prompt.md) | generate_audit_closed_packages (аудит closed/wip, снимок промпта: [§](#closed-packages-audit-snapshot-2026-04-20-cursor-ai)) |
| [team_workflow/generate_audit_packages_coverage_prompt.md](team_workflow/generate_audit_packages_coverage_prompt.md) | generate_audit_packages_coverage (DoD coverage completion по audit-группам; шаблон запуска: [§](#audit-coverage-prompt-generator)) |
| [../archive/doc_team_workflow/audit_coverage_prompt_2026-04_cursor_ai.md](../archive/doc_team_workflow/audit_coverage_prompt_2026-04_cursor_ai.md) | audit coverage prompt snapshot for `PERIOD=2026-04`, `TARGET_AGENT=cursor_ai` |
| [team_workflow/generate_breakthrough_ideation_prompt.md](team_workflow/generate_breakthrough_ideation_prompt.md) | Breakthrough Ideation Prompt |
| [team_workflow/generate_roadmap_epoch_waves_prompt.md](team_workflow/generate_roadmap_epoch_waves_prompt.md) | Roadmap Epoch/Waves Prompt (post-ideation waves/packages) |
| [team_workflow/workflow_router.md](team_workflow/workflow_router.md) | **Workflow Router** — описание `scripts/workflow.py`, 5 состояний, CLI-флаги (`--exec`, `--skip-review`, …) |
| [team_workflow/generate_bottleneck_analysis_prompt.md](team_workflow/generate_bottleneck_analysis_prompt.md) | Bottleneck Analysis Prompt (`archive/team_artifacts/_timing/` -> `logs/bottlenecks/`) |
| [team_workflow/reopen_prompt_closed_window_template.md](team_workflow/reopen_prompt_closed_window_template.md) | batch reopen (шаблон; [пример](#reopen-batch-closed-window-last3days-example)) |
| [../archive/team_workflow_snapshots/reopen_instance_last3days_2026-04-26__2026-04-28.md](../archive/team_workflow_snapshots/reopen_instance_last3days_2026-04-26__2026-04-28.md) | экземпляр reopen (последние 3 дня, снимок дат; копипаст в каталоге: [§](#reopen-batch-closed-window-last3days-example)) |
| [team_workflow/budget_health_prompt.md](team_workflow/budget_health_prompt.md) | Kilo Budget Health |
| [team_workflow/demo_scenarios_prompt_bundle.md](team_workflow/demo_scenarios_prompt_bundle.md) | Demo Scenarios Bundle |
| [team_workflow/run_start_workflow_prompt.md](team_workflow/run_start_workflow_prompt.md) | run_start_workflow_prompt |
| [team_workflow/run_autonomous_runbook.md](team_workflow/run_autonomous_runbook.md) | run_autonomous v3 runbook |
| [team_workflow/{product_owner,analyst,architect,designer,developer,tester}.md](team_workflow/) | Role prompts (6 шт.) |
| [team_workflow/guides/{agent_adapter_claude_code,cursor_ai,codex,kilo,continue}.md](team_workflow/guides/) | Tool adapters (5 шт.) |
| [team_workflow/archive/epoch_demo_post_agent_smoke.md](team_workflow/archive/epoch_demo_post_agent_smoke.md) | Epoch-Demo smoke CLI |
| [print_epoch_demo_agent_prompts.py](../scripts/print_epoch_demo_agent_prompts.py) | Epoch-Demo: package + `run_autonomous` smoke (2 промпта) |

---

> 💡 **Совет:** Почти все промпты находятся в `doc/agent_workflow_*.md` и `doc/team_workflow/*.md`. Если нужен промпт для новой ситуации — скорее всего он уже есть, просто поищи в одном из этих файлов.
