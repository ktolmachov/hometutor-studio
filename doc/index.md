# 🧭 Навигатор Документации hometutor

> Единая точка входа во всю документацию проекта.
> Актуализирован: **2026-06-21**.

**hometutor** — Python RAG-приложение для адаптивного обучения: graph-retrieval, learner state, LLM-генерация. Стек: FastAPI + Streamlit + SQLite + Chroma + LangChain + Anthropic.

> 🕸️ **[Интерактивный граф документации](doc_graph.html)** — визуальная карта связей между документами: 244 документа, 778 связей, роли, поиск, фильтры и minimap.
> Регенерация: `.\.venv\Scripts\python.exe scripts\generate_doc_graph.py`. Машинный экспорт: `.\.venv\Scripts\python.exe scripts\generate_doc_graph.py --json`.
> 📋 **[Documentation Onboarding Guide](documentation_onboarding_guide.md)** — короткие reading paths и quick reference для ролей.
> Local-first asset: [assets/d3.v7.min.js](assets/d3.v7.min.js).
> Obsidian Graph View настроен через [.obsidian/graph.json](.obsidian/graph.json).

---

## ⚡ Быстрый Старт По Ролям

Выберите свою роль и откройте 2–3 ключевых документа — этого достаточно, чтобы войти в контекст.

| Роль | Что читать в первую очередь |
|---|---|
| 🆕 **Новичок в проекте** | [readme.md](readme.md) → [quickstart.md](quickstart.md) → [vision.md](vision.md) |
| 👤 **Пользователь продукта** | [user_guide.md](user_guide.md) → [user_scenarios.md](user_scenarios.md) → [quickstart_demo.md](quickstart_demo.md) |
| 📊 **Product Owner / Аналитик** | [vision.md](vision.md) → [cjm.md](cjm.md) → [user_stories.md](user_stories.md) → [backlog_registry.yaml](backlog_registry.yaml) |
| 🏗️ **Архитектор** | [architecture.md](architecture.md) → [adr.md](adr.md) → [conventions_architecture.md](conventions_architecture.md) |
| 💻 **Разработчик** | [conventions.md](conventions.md) → [technical_specification.md](technical_specification.md) → [api_reference.md](api_reference.md) → [agent_workflow.md](agent_workflow.md) |
| 🧪 **Тестировщик / QA** | [user_scenarios.md](user_scenarios.md) → [scenarios/](scenarios/) → [agent_workflow_test_bundles.md](agent_workflow_test_bundles.md) |
| 🤖 **AI-агент / Claude Code** | [../CLAUDE.md](../CLAUDE.md) → [token_safety.md](token_safety.md) → [agent_workflow.md](agent_workflow.md) → [team_workflow/README.md](team_workflow/README.md) |
| 🚀 **DevOps / Observability** | [observability_slo.md](observability_slo.md) → [index_lifecycle.md](index_lifecycle.md) → [kilo_budget_system.md](kilo_budget_system.md) |

---

## 🎯 Где Что Лежит — По Темам

### 🌟 1. Продуктовое Видение

| Документ | О чём |
|---|---|
| [vision.md](vision.md) | Миссия и долгосрочные цели продукта |
| [roadmap.md](roadmap.md) | Сводная карта: эпохи, волны, US/CJM, ссылки на SSoT |
| [product_idea.md](product_idea.md) | Концепция, гипотезы, целевая аудитория |
| [pitch.md](pitch.md) | Короткая презентационная подача |
| [presenter_script.md](presenter_script.md) | Скрипт демо-презентации |
| [cjm.md](cjm.md) | Customer Journey Map: пути пользователя и pain points |
| [smart_study_router.md](smart_study_router.md) | **Killer Feature:** Smart Study Router — архитектура, сигналы, AI Vision |
| [future_roadmap.md](future_roadmap.md) | Закрытый стратегический индекс E4–E13 и правила re-entry |
| [roadmap_governance.md](roadmap_governance.md) | Правила управления roadmap, tail-policy |
| [next/localhost_balance_course_delight_breakthrough.md](next/localhost_balance_course_delight_breakthrough.md) | **🚀 Закрытый прорыв:** Localhost Delight + Course Loop полностью закрыт; qwopus35b (llama.cpp, 185 tps); Golden E2E graduation delivered |
| [next/BREAKTHROUGH_SUMMARY.md](next/BREAKTHROUGH_SUMMARY.md) | 2-минутная сводка: три инновации, метрики, сценарий |
| [next/localhost_balance_course_delight_plan.md](next/localhost_balance_course_delight_plan.md) | Исторический план Localhost Balance + Course Delight Loop |
| [next/BREAKTHROUGH_VISUAL.md](next/BREAKTHROUGH_VISUAL.md) | Диаграммы и визуальные гайды: архитектура, метрики, timeline, wow-moments |
| [next/DEFENSE_TALKING_POINTS.md](next/DEFENSE_TALKING_POINTS.md) | Для защиты проекта: нарратив, ответы на вопросы, демо-сценарии, слайды |
| [next/ai_driven_design_waves_proposal.md](next/ai_driven_design_waves_proposal.md) | **AI-driven design:** 13 волн / 27 пакетов по `summary_01-ai-driven-design.md`, сгруппированы по слоям (arch/UX/infra), состыкованы с SSR. 5 waves promoted (proposed) |
| [next/ragas_retrieval_metrics_v1_contract.md](next/ragas_retrieval_metrics_v1_contract.md) | Полный execution contract `ragas-retrieval-metrics-v1` (context_precision@k + answer_correctness поверх существующего eval-harness) |

### 📚 2. Пользовательский Опыт

| Документ | О чём |
|---|---|
| [user_guide.md](user_guide.md) | Главное руководство пользователя |
| [user_guide_details.md](user_guide_details.md) | Детальное описание UI и поведения |
| [user_scenarios.md](user_scenarios.md) | Сценарии использования сквозь продукт |
| [documentation_onboarding_guide.md](documentation_onboarding_guide.md) | Reading paths и quick reference по документации для разных ролей |
| [scenarios/](scenarios/) | YAML-сценарии 01–14 (E2E demo и регрессия) |
| [quickstart.md](quickstart.md) | Быстрый запуск проекта локально |
| [quickstart_demo.md](quickstart_demo.md) | Демо-прогон для презентаций (со скриншотами) |
| [presentations/defense_deploy_plan.md](presentations/defense_deploy_plan.md) | Онлайн-деплой: HF Spaces, VPS, CI, eval для защиты |
| [../deploy/hf-spaces/README.md](../deploy/hf-spaces/README.md) | Hugging Face Spaces — публичный Streamlit demo |

### 🏛️ 3. Архитектура и Технические Спецификации

| Документ | О чём |
|---|---|
| [architecture.md](architecture.md) | Главный архитектурный обзор системы |
| [technical_specification.md](technical_specification.md) | Технические требования и контракты |
| [api_reference.md](api_reference.md) | HTTP API: эндпоинты, схемы, примеры |
| [adr.md](adr.md) | Architecture Decision Records (актуальные решения) |
| [personalized_learner_model.md](personalized_learner_model.md) | Модель ученика: состояние, прогресс, адаптация |
| [observability_slo.md](observability_slo.md) | Метрики, логи, SLO, алерты |
| [ssr_llm_profiling.md](ssr_llm_profiling.md) | Профили SSR LLM («Почему сейчас»), сводка, OTLP |
| [index_lifecycle.md](index_lifecycle.md) | Жизненный цикл векторного индекса (Chroma) |
| [eval_experimenter_runbook.md](eval_experimenter_runbook.md) | Runbook для оценочных экспериментов |

### 🛠️ 4. Инженерные Конвенции

| Документ | О чём |
|---|---|
| [conventions.md](conventions.md) | Базовые правила (imports, errors, config) |
| [conventions_architecture.md](conventions_architecture.md) | Архитектурные паттерны слоёв |
| [conventions_reference.md](conventions_reference.md) | Справочник по сервисам и контрактам |
| [readme.md](readme.md) | README проекта |

### 📋 5. Бэклог и Текущая Работа

| Документ | О чём |
|---|---|
| [backlog_registry.yaml](backlog_registry.yaml) | **Источник истины** по backlog, статусам, owner'ам и package scope |
| [roadmap.md](roadmap.md) | Сводная карта эпох, волн, MoT/US и ссылок на SSoT |
| [archive/arch_review_baseline.yaml](archive/arch_review_baseline.yaml) | Baseline incremental architecture review + связка с `wave-arch-review-remediation-2026-05` |
| [tasklist.md](tasklist.md) | Производный weekly view: Now / queue / recent closed |
| [current_task.md](current_task.md) | Текущий пакет в работе |
| [current_task.payload.md](current_task.payload.md) | Полный контракт текущего пакета |
| [user_stories.md](user_stories.md) | Главный список user stories (US 1.1 — 16.6) |
| [user_stories/](user_stories/) | Каждая US — отдельный файл с DoD |
| [user_stories_index.json](user_stories_index.json) | JSON-индекс для автоматизации |
| [user_stories_details.md](user_stories_details.md) | Расширенные детали историй |
| [tail_sweep.md](tail_sweep.md) | Стратегия закрытия long-tail backlog |

### 🤖 6. Workflow Команды и AI-Агентов

| Документ | О чём |
|---|---|
| [agent_workflow.md](agent_workflow.md) | Slim-индекс рабочего процесса с агентами |
| [agent_workflow_rules.md](agent_workflow_rules.md) | Token Budget & Retry Safety v1 |
| [agent_workflow_cycle.md](agent_workflow_cycle.md) | Цикл Plan → Execute → Verify, A/B/C split |
| [agent_workflow_templates.md](agent_workflow_templates.md) | Шаблоны Plan/Execute/Verify промптов |
| [agent_workflow_test_bundles.md](agent_workflow_test_bundles.md) | Стандартные test bundles по областям |
| [agent_workflow_arch_review.md](agent_workflow_arch_review.md) | Процесс архитектурного ревью (фазы 1–4) |
| [team_workflow/README.md](team_workflow/README.md) | **Командный конвейер**: PO → Analyst → Architect → Dev → Tester |
| [team_workflow/process.md](team_workflow/process.md) | Полное описание team-процесса |
| [team_workflow/automation.md](team_workflow/automation.md) | Автоматизация и скрипты pipeline |
| [team_workflow/workflow_router.md](team_workflow/workflow_router.md) | Умный роутер (`workflow.py`), `--loop`, якоря, паузы IDE |
| [`scripts/workflow_strings.py`](../scripts/workflow_strings.py) | SSoT строк промпта агента для вывода роутера |

### 🛡️ 7. Token Safety и Budget Control

| Документ | О чём |
|---|---|
| [../CLAUDE.md](../CLAUDE.md) | **Главные правила** работы Claude Code в проекте |
| [token_safety.md](token_safety.md) | Полный референс safe-методов чтения файлов |
| [token_safety_registry.json](token_safety_registry.json) | Машиночитаемый реестр опасных файлов |
| [token_metrics_tracking.md](token_metrics_tracking.md) | Baseline и тренды по токенам приложения |
| [QUICK_READSET_REFERENCE.md](QUICK_READSET_REFERENCE.md) | Шпаргалка по сборке read-set |
| [MICROPLAN_USAGE.md](MICROPLAN_USAGE.md) | Использование `scripts/check_readset.py` |
| [VALIDATOR_FLOWCHART.md](VALIDATOR_FLOWCHART.md) | Поток валидации read-set |
| [TOKEN_OPTIMIZATION_CARD.md](TOKEN_OPTIMIZATION_CARD.md) | Карточка с метриками оптимизации |
| [kilo_budget_system.md](kilo_budget_system.md) | Kilo budget: концепция и механика |
| [kilo_budget_gate.md](kilo_budget_gate.md) | CI/CD gate по бюджету |
| [kilo_budget_capture_runbook.md](kilo_budget_capture_runbook.md) | Runbook сбора замеров |
| [kilo_proxy_relay.md](kilo_proxy_relay.md) | Локальный релей Cursor → LM Studio: стриминг, логи, env |
| [loop_metrics_gate_runbook.md](loop_metrics_gate_runbook.md) | Loop-метрики и их пороги |

### 📜 8. Эволюция и История Решений

| Документ | О чём |
|---|---|
| [changelog.md](changelog.md) | Полный changelog проекта (append-only) |
| [closed_iterations.md](closed_iterations.md) | Закрытые эпохи и итерации |
| [epochs/](epochs/) | Архив эпох e4–e29 (по одной — не больше!) |

### 📚 9. Каталог Промптов

| Документ | О чём |
|---|---|
| [prompts_catalog.md](prompts_catalog.md) | **Полный справочник всех промптов**: агент-промпты, ролевые промпты, генераторы team workflow, master audit/coverage цепочки и примеры исполненных пакетов. Сгруппировано по ролям и сценариям. |
| [team_workflow/reopen_package_step_c_prompt.md](team_workflow/reopen_package_step_c_prompt.md) | Переоткрытие **одного** закрытого пакета (`closed` → `ready`): готовый текст Step C для вставки в агент. |
| [../archive/doc_team_workflow/audit_chain_prompt_2026-04_cursor_ai.md](../archive/doc_team_workflow/audit_chain_prompt_2026-04_cursor_ai.md) | Готовый master prompt для audit/coverage цепочки `2026-04` / `cursor_ai`. |

---

## 🗂️ Архивные и Исторические Материалы

> Эти документы зафиксированы как исторический контекст. Они **не отражают текущее состояние системы** — используйте их только для археологии решений.

| Документ | Почему в архиве |
|---|---|
| [adr_rag_architecture.md](archive/adr_rag_architecture.md) | Старая редакция ADR; актуальное — в [adr.md](adr.md) |
| [architectural_refactoring.md](archive/architectural_refactoring.md) | Завершённый план рефакторинга архитектуры |
| [blue_green_reindex_design.md](archive/blue_green_reindex_design.md) | Реализованный дизайн blue-green reindex |
| [blue_green_reindex_implementation_plan.md](archive/blue_green_reindex_implementation_plan.md) | План внедрения blue-green (выполнен) |
| [tasklist_historical.md](archive/tasklist_historical.md) | Старый weekly backlog, заменён на [tasklist.md](tasklist.md) |
| [IMPLEMENTATION_COMPLETE.md](archive/IMPLEMENTATION_COMPLETE.md) | Отчёт о внедрении token-safety (готово) |
| [IMPLEMENTATION_P0_P1.md](archive/IMPLEMENTATION_P0_P1.md) | Отчёт о P0/P1 token-фазах (готово) |
| [token_optimization_plan.md](archive/token_optimization_plan.md) | Исходный план оптимизации (исполнен) |
| [token_optimization_checklist.md](archive/token_optimization_checklist.md) | Чеклист оптимизации (закрыт) |
| [handoff_next_level.md](archive/handoff_next_level.md) | Историческая хэндовер-записка |
| [architecture_review_2026-04-24.md](archive/architecture_review_2026-04-24.md) | Снимок ревью на дату |
| [arch_review_baseline.yaml](archive/arch_review_baseline.yaml) | Baseline-снимок к ревью |
| [workflow_hardening_plan_2026-04-24.md](archive/workflow_hardening_plan_2026-04-24.md) | Точечный план hardening (применён) |
| [kilo_budget_remediation_plan.md](archive/kilo_budget_remediation_plan.md) | План коррекции kilo-бюджета (исполнен) |
| [archive/](archive/) | Замороженные артефакты, ревью, эксперименты |

---

## 🚦 Политика Использования

- **Источник истины по бэклогу** — [backlog_registry.yaml](backlog_registry.yaml); [tasklist.md](tasklist.md) и [current_task.md](current_task.md) — производные runtime/views.
- **Источник истины по архитектуре** — [architecture.md](architecture.md) + [adr.md](adr.md), не старые design-документы.
- **Перед любым LLM-вызовом** проверьте чеклист в [../CLAUDE.md](../CLAUDE.md) § Critical Checkpoints.
- **При расхождении** актуальный документ всегда побеждает архивный — обновите ссылки и оставьте архив как пометку «как было».

---

## 🔍 Если Не Нашли Документ

```bash
# Поиск по заголовкам
grep -l "ключевое слово" doc/*.md

# Поиск по содержимому (быстрее через ripgrep)
rg "ключевое слово" doc/

# Бюджетная проверка перед чтением больших файлов
python scripts/check_readset.py <file>
```

---

> 💡 **Эта страница — единственная точка входа.** Если вы видите ссылку «смотрите doc/X.md» в другом месте — она должна вести через этот навигатор. Если документ важен и его здесь нет — это баг навигатора, добавьте строку.
