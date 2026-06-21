# 🧭 Руководство по Использованию Промптов (Prompts Usage Guide)

> **Область этого документа:** markdown-промпты **team / agent workflow** (роли, планирование, аудит, оркестрация). Тексты LLM для runtime-приложения (RAG, тьютор, квизы и т.д.) — единственный модуль [`app/prompts.py`](../app/prompts.py); полный перечень сценариев и копипаста — в [Каталоге Промптов](prompts_catalog.md).

Данное руководство основано на [Каталоге Промптов](prompts_catalog.md) и представляет собой **навигатор по сценариям и ролям**. Оно помогает понять, *когда*, *какой промпт* использовать и *какую роль* на себя берет AI-агент в конкретной ситуации.

**Источник истины по задачам:** [backlog_registry.yaml](backlog_registry.yaml). Файл [tasklist.md](tasklist.md) — производный weekly view (`python scripts/backlog_registry_lint.py --sync-from-index --write-sync`), статусы в нём не править вручную.

**Процесс по шагам и роли (чтобы не терять время на поиск следующего шага):** [team_workflow/process.md](team_workflow/process.md) — сводная таблица «кто что делает» и в каком порядке идут handoff PO → Analyst → Architect / Designer → Developer → Tester → закрытие; там же диаграмма пайплайна, правила WIP и эскалации. Сочетайте с блоками **«Дальше по процессу»** в ролевых файлах `doc/team_workflow/<role>.md` и с STEP 1–8 в сгенерированном оркестраторе ([generate_orchestration_prompt.md](team_workflow/generate_orchestration_prompt.md)).

**Что запускать прямо сейчас (дерево решений):** [team_workflow/workflow_decision_tree.md](team_workflow/workflow_decision_tree.md).

**⭐ Единая точка входа (рекомендуется):** `python scripts/workflow.py` — автоматически определяет состояние пайплайна и выдаёт следующий шаг. Флаг `--skip-review` — пропуск паузы на ревью контракта между plan-next и `generate_orchestration_prompt.py` (см. [workflow_router.md](team_workflow/workflow_router.md)).

В `ready_fresh` роутер разделяет два понятия: mechanical complexity (`classify_package_complexity`) и lifecycle routing. Пакеты с `user_stories` или `cjm_moments` считаются accepted learning-product контрактами и идут через orchestration-first даже при low complexity; `execution_auto` остаётся для компактных maintenance/infra задач без US/CJM.

**Handoff при сбоях:** в отчёте исполнителя или верификатора добавляйте строку **`HANDOFF_SIGNAL: …`** — формат в [team_workflow/developer.md](team_workflow/developer.md) и [team_workflow/tester.md](team_workflow/tester.md). Для сохранённых артефактов оркестратора: [`scripts/validate_team_artifact.py`](../scripts/validate_team_artifact.py) (строже — `--strict` или закрытие пакета с `--team-artifacts-strict` / `HOME_RAG_TEAM_ARTIFACTS_STRICT`, см. [.env.example](../.env.example)).

---

## Шесть входов team workflow (кратко)

> **Предпочтительный способ:** `python scripts/workflow.py` — роутер определит нужную строку автоматически.  
> Ручной выбор из таблицы ниже — только если нужен конкретный режим.

| Ситуация | Что запускать |
|----------|---------------|
| Backlog пустой / все пакеты закрыты / нужен новый контракт | [generate_plan_next_prompt.md](team_workflow/generate_plan_next_prompt.md) |
| В `backlog_registry.yaml` есть продуктовый пакет `ready` / `wip` с US/CJM | [generate_orchestration_prompt.md](team_workflow/generate_orchestration_prompt.md) |
| В `backlog_registry.yaml` есть low-complexity maintenance/infra пакет без US/CJM | `python scripts/workflow.py` выберет `execution_auto` / `run_autonomous.py` |
| Работа по `PACKAGE_ID` уже начиналась (`archive/team_artifacts/<ID>/`) | [generate_resume_prompt.md](team_workflow/generate_resume_prompt.md) |
| Вся цепочка аудита end-to-end (audit → coverage) | [run_audit_chain_prompt.md](team_workflow/run_audit_chain_prompt.md) |
| Периодический аудит закрытых / при необходимости `wip` пакетов | [generate_audit_closed_packages_prompt.md](team_workflow/generate_audit_closed_packages_prompt.md) |
| Добивка unit/e2e DoD по уже созданным audit-группам | [generate_audit_packages_coverage_prompt.md](team_workflow/generate_audit_packages_coverage_prompt.md) |

---

## 👥 1. Матрица Ролей: Кто вы в данный момент?

Workflow проекта `hometutor` разделен на строгие роли. Для каждой роли есть свои промпты, которые не пересекаются по зоне ответственности.

### 👑 Product Owner (Владелец Продукта)
**Фокус:** Бизнес-ценность, CJM, беклог, эпохи.

**Когда что запускать (контур):**
- Есть хотя бы одна строка контракта в [backlog_registry.yaml](backlog_registry.yaml), которую хотите превратить в пакет, но её ещё нет в реестре как `ready` / нет набора acceptance — сначала [Product Owner — Планирование пакета](team_workflow/product_owner_plan_package_prompt.md) или диалог по [team_workflow/product_owner.md](team_workflow/product_owner.md).
- В реестре **нет** активных пакетов (`ready` / `wip`), волны в `waves:` уже `completed`, а машинный пул из CJM/US пуст или не даёт ни одного кандидата, удовлетворяющего re-entry — см. **сценарий 5** ниже (`blocker: no eligible plan-next…`).
- Нужно **не выбрать из беклога**, а получить поток **новых** гипотез по стадии CJM / US / pain — [generate_breakthrough_ideation_prompt.md](team_workflow/generate_breakthrough_ideation_prompt.md): генерация набора прорывных идей (≥N по спецификации промпта), опора на методики Duolingo/Anki/JTBD и др., выход — артефакт с черновиками изменений для CJM/US/`backlog_registry`/`epochs`; дальше владелец фильтрует и переносит лучшие в контракт. В том же файле описано, **чем эта дорожка отличается** от машинного [generate_plan_next_prompt.md](team_workflow/generate_plan_next_prompt.md) (plan-next только ранжирует и оформляет уже допустимых кандидатов под правилами реестра).

*   **Сценарий 1: Выбор следующей задачи (plan-next).** Используйте [generate_plan_next_prompt.md](team_workflow/generate_plan_next_prompt.md). **Типично после** того, как закрыли текущий `wip`/последнюю активную волну: в реестре нет `ready`/`wip`, а вы хотете 1–3 ранжированных кандидата с контрактом из уже существующих правил реестра, CJM, отложенных пакетов и roadmap. Агент выполняет `check_backlog_drift.py`, strict-lint реестра, preflight token-check по `read_set_hint` и только **после вашего явного accept** пишет пакет в [backlog_registry.yaml](backlog_registry.yaml); [tasklist.md](tasklist.md) пересобирается sync-скриптом — **не** считайте tasklist источником беклога.
*   **Сценарий 2: Стратегическое планирование и ручная упаковка.** Ролевой промпт [team_workflow/product_owner.md](team_workflow/product_owner.md); для одного пакета — [Product Owner — Планирование пакета](team_workflow/product_owner_plan_package_prompt.md). Используйте, когда идея уже сформулирована человеком или пришла из brainstorm, но ещё не оформлена как элемент реестра с DoD/read-set/write-set.
*   **Сценарий 3: Административный аудит SSoT.** [generate_audit_closed_packages_prompt.md](team_workflow/generate_audit_closed_packages_prompt.md) — сверка реестра, закрытых итераций и user stories. Полная цепочка «аудит + coverage» — [run_audit_chain_prompt.md](team_workflow/run_audit_chain_prompt.md).
*   **Сценарий 4: Генерация новых продуктовых направлений (breakthrough ideation).** [generate_breakthrough_ideation_prompt.md](team_workflow/generate_breakthrough_ideation_prompt.md) — **не** заменяет plan-next: он не выбирает готовый пакет из SSoT, а даёт список идей по заданному **направлению** (pain point из [cjm.md](cjm.md), US, область фич). Имеет смысл после «всё в беклоге уже закрыто», когда нужен новый топливный слой гипотез до возврата к plan-next или к [product_owner_plan_package_prompt.md](team_workflow/product_owner_plan_package_prompt.md).
*   **Сценарий 5: Блокер plan-next (`blocker: no eligible plan-next candidate under current registry/re-entry rules`).** Возникает, когда **одновременно** типично выполняются условия: нет активных пакетов `ready`/`wip`; все волны в `waves:` в статусе `completed`/`frozen` или нет ни одной волны со статусом `proposed`/`ready`; в таблице CJM § 8 все pain points уже `closed:*`; индекс `open_candidates` пуст или отсутствуют истории со статусом `open`; отложенные (`deferred`) пакеты **не** удовлетворяют своему `re_entry_condition`. Plan-next здесь закончен — **писать контракт в реестр агенту нельзя** до появления нового scope. Цепочка без зависания: (1) [product_owner_plan_package_prompt.md](team_workflow/product_owner_plan_package_prompt.md) или [product_owner.md](team_workflow/product_owner.md) — зафиксировать пробел, решить owner/priority; (2) при необходимости сырья идей — [generate_breakthrough_ideation_prompt.md](team_workflow/generate_breakthrough_ideation_prompt.md); (3) новая/обновлённая US + правка индексов при необходимости; (4) снова plan-next или прямое оформление пакета в `backlog_registry.yaml` + `backlog_registry_lint.py --sync-from-index --write-sync`.
*   **Сценарий 6: Ни один промпт не дал actionable результата (анти-тупик).** Проявляется, когда plan-next вернул `blocker`/пустой пул без accept, breakthrough-прогон не дал пригодных идей после фильтра, refine/повтор всё сходит на нет, или все кандидаты отвалились на preflight (**BLOCK** в `check_readset.py`). Что делать по шагам: проверить `scripts/check_backlog_drift.py` и синхронность US/реестра; при **BLOCK read-set** — поправить подсказки в [token_safety](token_safety.md) / реестре метрик, затем сузить scope; повторить plan-next с параметрами `FOCUS_CJM` / меньше `MAX_CANDIDATES` (см. шапку [generate_plan_next_prompt.md](team_workflow/generate_plan_next_prompt.md)); если снова тишина — **сценарий 5**, затем снова ideation или ручное планирование пакета; опционально [generate_audit_closed_packages_prompt.md](team_workflow/generate_audit_closed_packages_prompt.md), чтобы исключить «фантомные» пробелы в SSoT.

### 🕵️‍♂️ Analyst (Аналитик)
**Фокус:** Детализация, критерии приемки, Edge-кейсы.
*   **Сценарий:** Декомпозиция контракта от PO. Используется ролевой промпт [team_workflow/analyst.md](team_workflow/analyst.md). Агент берет бизнес-цель и превращает ее в сценарии BDD (Given-When-Then), находя неучтенные ограничения.

### 🏛️ Architect (Архитектор)
**Фокус:** Технические решения, структура, ревью кода, границы (boundaries).
*   **Сценарий 1: Проектирование фичи.** Ролевой промпт [team_workflow/architect.md](team_workflow/architect.md). Агент определит файлы для записи (write-set), ограничения и паттерны реализации до написания кода.
*   **Сценарий 2: Периодический аудит (Tech Debt).** [Architecture Review Prompt](agent_workflow_arch_review.md#шаблон-architecture-review-prompt) (Phase 1–5). Используйте для сканирования репозитория на архитектурный дрейф, нарушения [conventions.md](conventions.md) или мертвый код. Запускается по одной фазе за раз.

### 💻 Developer / Инженер (Разработчик)
**Фокус:** Написание кода, тестов, следование DoD.
*   **Сценарий 1: Быстрая реализация.** [Execution Contract](agent_workflow_templates.md#контрактный-prompt-для-ударных-пакетов) в [agent_workflow_templates.md](agent_workflow_templates.md). Идеально для изолированных задач, багфиксов и быстрых внедрений.
*   **Сценарий 2: Возобновление работы (Resume).** Если задача зависла или делается в несколько этапов, применяйте [generate_resume_prompt.md](team_workflow/generate_resume_prompt.md). Агент прочитает последние коммиты и восстановит контекст.

### 🧪 Tester / QA (Верификатор)
**Фокус:** Проверка DoD (Definition of Done), регрессия, интеграция.
*   **Сценарий 1: Приемка пакета.** [Verify Prompt](agent_workflow_templates.md#verify-prompt--проверка-выполненного-пакета). Агент не пишет код, а только запускает тесты, проверяет diff и выдает вердикт: PASS, CONDITIONAL PASS или FAIL (формируя промпт для исправления).
*   **Сценарий 2: E2E Smoke-тесты.** Используйте промпт [epoch_demo_post_agent_smoke.md](team_workflow/archive/epoch_demo_post_agent_smoke.md) для локального запуска демо-сценариев и проверки пайплайна автоматизации после вмешательства агентов.
*   **Сценарий 3: DoD-покрытие после аудита.** [generate_audit_packages_coverage_prompt.md](team_workflow/generate_audit_packages_coverage_prompt.md) — закрытие пробелов в тестах и артефактах по audit-группам.

### ⏱️ Performance Engineer / DevOps (Инфраструктура и Производительность)
**Фокус:** Скорость, лимиты, затраты, локальная надёжность, observability.
**Ролевой промпт:** [team_workflow/performance_devops.md](team_workflow/performance_devops.md) — Impact Review (gate в STEP 3.5) + Post-Release Performance Watch.

*   **Сценарий 1: Impact Review нового пакета (gate).** Применяйте `Промпт 1` из [performance_devops.md](team_workflow/performance_devops.md) **до** старта Developer-а, если контракт трогает `scripts/local_*.{py,ps1}`, `app/ui/llm_local_banner.py`, новые таймауты / budgets / зависимости, ingest-pipeline, `.env.example`, Dockerfile или CI workflows. Выход — Performance Impact Report (GREEN / YELLOW / RED) с проекцией p50/p95/cost.
*   **Сценарий 2: Post-release watch.** `Промпт 2` из того же файла — после закрытия пакета сверяет `archive/pipeline_metrics.md`, `archive/team_artifacts/_timing/`, читает honesty readiness и предупреждает о регрессе.
*   **Сценарий 3: Мониторинг бюджета (тактический инструмент).** Используйте `Kilo Budget Health Prompt` ([budget_health_prompt.md](team_workflow/budget_health_prompt.md)), если нужно понять, сколько токенов тратится, и диагностировать перерасход (overflow).
*   **Сценарий 4: Анализ узких мест (тактический инструмент).** Применяйте `Bottleneck Analysis Prompt` ([generate_bottleneck_analysis_prompt.md](team_workflow/generate_bottleneck_analysis_prompt.md)) для анализа JSON-отчётов по автономным прогонам пайплайна (оценка времени на каждый шаг).
*   **Сценарий 5: Local Control Center (balance plan §Phase 7).** При работе над localhost-балансом — owner [`scripts/local_status.py`](../scripts/local_status.py), `app/ui/llm_local_banner.py`, profile-aware KPI (см. [`rag_llm_ops_project_document.md` §32.2](team_workflow/rag_llm_ops_project_document.md#32-profile-aware-ops-policy-local_strict--balanced--cloud_fast)).

### 🔎 RAGOps / LLMOps / MLOps (Условные роли Ops — gate в STEP 3.5)
**Фокус:** Качество retrieval / стабильность LLM-слоя / воспроизводимость моделей. Подключаются **только** если контракт затрагивает соответствующие модули — иначе gate пропускается.

| Роль | Когда подключается | Ролевой промпт |
|---|---|---|
| **RAGOps Engineer** | Контракт трогает `app/query_service.py`, `app/pipeline_steps.py`, `app/course_cache.py`, `app/ui/study_scope.py`, `data/docs/`, citation/trace pipeline | [team_workflow/ragops_engineer.md](team_workflow/ragops_engineer.md) |
| **LLMOps Engineer** | Контракт трогает `app/provider.py`, `app/prompts/`, `app/tutor_prompts.py`, profile / soft-hard timeout / fallback ключи, `app/ui/llm_local_banner.py` | [team_workflow/llmops_engineer.md](team_workflow/llmops_engineer.md) |
| **MLOps Engineer** | Контракт меняет embedding / reranker / router classifier / entity-relation extractor / chunking стратегию / eval dataset / index version | [team_workflow/mlops_engineer.md](team_workflow/mlops_engineer.md) |

**Канонический список триггеров:** [`rag_llm_ops_project_document.md` §35](team_workflow/rag_llm_ops_project_document.md#35-hook-в-team-workflow-процесс). **Verdict routing:** GREEN → продолжаем; YELLOW → условия в `deferred.md` и доп. DoD в STEP 4; RED → возврат на Architect.

*   **Сценарий 1: Импакт-ревью нового пакета.** Применяйте `Промпт 1` соответствующей роли (или нескольких параллельно) сразу после STEP 3 (Architect+Designer) и до STEP 4 (Developer).
*   **Сценарий 2: Сужённая верификация.** `Промпт 2` каждой роли — узкие верифицирующие сценарии (Course Scope Verify для RAGOps, 8-scenario Primary Chat Fallback Verify для LLMOps, Eval Regression Verify для MLOps). Полезно подключать на STEP 5/7 как дополнительный сигнал к основному Tester-у.
*   **Сценарий 3: Course Delight Loop.** RAGOps — owner шагов 4.1–4.10 балансового плана ([`localhost_balance_course_delight_plan.md` §4](next/localhost_balance_course_delight_plan.md)); координируется с LLMOps по prompts/banner и с Performance/DevOps по latency.

---

## 🚀 2. Сценарии Использования (Use Cases)

В зависимости от текущей фазы проекта, выберите нужную связку промптов.

### Сценарий A: Запуск автономного конвейера ("Zero-Click Delivery")
Если нужно, чтобы система сама забрала пакеты из реестра и прогоняла цикл «исполнение → `--post-agent` → закрытие → promote» с минимумом ручных шагов.

1. **Каталог (готовый блок + навигация):** раздел **Run Autonomous Prompt (Zero-Click Delivery)** в [prompts_catalog.md](prompts_catalog.md#run-autonomous-prompt) — там же ссылка на этот сценарий и на углублённый разбор документов.
2. **SSoT текста промпта / стартовая команда:** [run_autonomous_prompt.md](team_workflow/run_autonomous_prompt.md) (PowerShell, `--non-stop`, семантика exit-кодов, без `&&`). Для расшифровки любого exit-кода: `.\.venv\Scripts\python.exe scripts/run_autonomous.py --explain-exit <N>`.
3. **Статус конвейера в любой момент:** `.\.venv\Scripts\python.exe scripts/pipeline_status.py` (как в каталоге). Или `python scripts/workflow.py --status` — высокоуровневый обзор.
4. **Диагностика и карта артефактов:** [zero_click_delivery_analysis.md](../archive/doc_team_workflow/archive/zero_click_delivery_analysis.md) — жизненный цикл, `backlog_registry.yaml` ↔ производные файлы, типичные рассогласования, чеклист скриптов.
5. **Runtime v3 (state / proof / replay):** при необходимости деталей среды выполнения — [run_autonomous_runbook.md](team_workflow/run_autonomous_runbook.md).

**Связка с остальным гайдом (по аналогии с каталогом):**
- **Подготовка / бюджет:** при необходимости сначала [budget_health_prompt.md](team_workflow/budget_health_prompt.md).
- **E2E оболочка PowerShell:** опционально [run_start_workflow_prompt.md](team_workflow/run_start_workflow_prompt.md) — не заменяет п. 2; финальная команда должна соответствовать `run_autonomous_prompt.md`.
- **Оркестрация multi-agent:** для пакетов с UI/ролями по шагам — [generate_orchestration_prompt.md](team_workflow/generate_orchestration_prompt.md); исполнитель всё равно завершает цикл через `current_task.md` и MANDATORY STEP с `--post-agent`.
- **Копируемый промпт:** тот же блок, что в каталоге — см. п. 1–2 выше.

### Сценарий B: Планирование Новой Эпохи (Strategic Ideation)
Вы хотите придумать новые функции, улучшающие опыт пользователя.
1.  **Поиск Идей:** Запустите `Breakthrough Ideation Prompt` ([generate_breakthrough_ideation_prompt.md](team_workflow/generate_breakthrough_ideation_prompt.md)), указав конкретный Pain Point из [cjm.md](cjm.md). Агент сгенерирует 10+ прорывных идей на базе проверенных практик (Anki, Duolingo и др.).
2.  **Утверждение:** Идеи с наивысшим скорингом (Impact / Effort) переходят к роли **Product Owner** ([product_owner.md](team_workflow/product_owner.md)) для упаковки в пакеты в [backlog_registry.yaml](backlog_registry.yaml); производный снимок — [tasklist.md](tasklist.md).
3.  **Если [generate_plan_next_prompt.md](team_workflow/generate_plan_next_prompt.md) остановился на блокере или идея не нашла себя ни в каком промпте** — см. сценарии **5 и 6** в разделе **Product Owner** выше (сначала восстановление scope вручную / PO-пакет, затем повторное plan-next или ideation).

### Сценарий C: Ручное выполнение сложной задачи (Step-by-Step)
Вы не хотите запускать полную автоматизацию, а хотите контролировать агента (например, в Cursor AI или Claude Code) на каждом шаге.
1.  **Plan:** [Planning Prompt](agent_workflow_templates.md#шаблон-planning-prompt-рекомендуемый-по-умолчанию) в [agent_workflow_templates.md](agent_workflow_templates.md). Агент подготовит строгий Execution Contract.
2.  **Execute:** Передайте сгенерированный Contract агенту-разработчику. Ограничьте Read-Set и Write-Set согласно контракту.
3.  **Verify:** [Verify Prompt](agent_workflow_templates.md#verify-prompt--проверка-выполненного-пакета). Если результат FAIL, скормите Fix-промпт обратно разработчику.

### Сценарий D: Поддержание документации в идеальном состоянии (SSoT Sync)
Проект растет, задачи закрываются, документация может отставать.
1.  **Цепочка целиком (предпочтительно при полном прогоне):** [run_audit_chain_prompt.md](team_workflow/run_audit_chain_prompt.md) — мастер-промпт audit → coverage.
2.  **Только аудит закрытых пакетов:** [generate_audit_closed_packages_prompt.md](team_workflow/generate_audit_closed_packages_prompt.md).
3.  **После audit-групп — добить DoD-покрытие:** [generate_audit_packages_coverage_prompt.md](team_workflow/generate_audit_packages_coverage_prompt.md).
4.  Связность артефактов: [backlog_registry.yaml](backlog_registry.yaml) (SSoT) ↔ производный [tasklist.md](tasklist.md) ↔ [user_stories/](user_stories/).
5.  Если закрытые пакеты нужно **переоткрыть** административно (closed window): [reopen_prompt_closed_window_template.md](team_workflow/reopen_prompt_closed_window_template.md).

---

## 🛠️ 3. Адаптация под Инструменты

В зависимости от того, в какой среде выполняется задача, используйте соответствующий **Адаптер** из каталога.

*   **Используете Claude Code?** → [agent_adapter_claude_code.md](team_workflow/guides/agent_adapter_claude_code.md). Агент будет использовать свои tool calls и корректно передавать артефакты между чатами.
*   **Используете Cursor AI?** → [agent_adapter_cursor_ai.md](team_workflow/guides/agent_adapter_cursor_ai.md). Идеально для inline-редактирования, проверки UI "на лету" и работы с Compose.
*   **Автоматизация через API (Kilo)?** → [agent_adapter_kilo.md](team_workflow/guides/agent_adapter_kilo.md). Гарантирует правильный async execution и жесткий контроль токенов.

> 💡 **Главное правило:** Не начинайте писать код без [Planning Prompt](agent_workflow_templates.md#шаблон-planning-prompt-рекомендуемый-по-умолчанию) или [Execution Contract](agent_workflow_templates.md#контрактный-prompt-для-ударных-пакетов). Контракт защищает от галлюцинаций LLM и «дрейфа» архитектуры (когда агент по пути решает отрефакторить соседний модуль).
