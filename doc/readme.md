# Документация `doc/`

Актуализировано по коду и roadmap на **2026-06-05**.

## Как читать папку

В `doc/` лежат документы с разным статусом:

- `Live` — текущий снимок работающей системы; на них можно опираться как на описание runtime.
- `Reference` — точечные справочники по отдельным подсистемам.
- `Roadmap` — планы и backlog; это не обещание, что функция уже есть в коде.
- `ADR` — архитектурные решения и их обоснование.
- `Historical` — исторические design/implementation документы.
- `Archive` — старые аналитические материалы в `archive/`.

## Порядок доверия

Если документы расходятся между собой, порядок такой:

1. код
2. `Live`-документы
3. `Reference`
4. `ADR`
5. `Roadmap` / `Historical` / `Archive`

## Что читать в первую очередь

Для текущей системы:

1. `architecture.md`
2. `technical_specification.md`
3. `api_reference.md`
4. `user_guide.md` (старт) → при необходимости `user_guide_details.md`

Для продукта и UX:

1. `vision.md`
2. `user_scenarios.md`
3. `user_stories.md` → `user_stories/`
4. `product_idea.md`

Для сопровождения:

1. `conventions.md` (TL;DR) → `conventions_architecture.md` / `conventions_reference.md`
2. `observability_slo.md`
3. `personalized_learner_model.md`

Для **плана работ и эпох**:

1. `backlog_registry.yaml` — SSoT по пакетам и статусам; `tasklist.md` — производный weekly view (регенерация `scripts/backlog_registry_lint.py --sync-from-index --write-sync`). Формальные exit criteria и журнал This Week — `archive/tasklist_historical.md`.
2. `next/localhost_balance_course_delight_breakthrough.md` — текущий breakthrough brief: Smoke v7, ADR-024, Wave 2 next step.
3. `roadmap.md` — сводная human-readable карта эпох, волн и ссылок на реестр/CJM/US.
4. `roadmap_governance.md` — правила roadmap, merge-gate discipline, tail-policy, doc-sync.
5. `future_roadmap.md` — стратегический индекс E4–E13 и правила re-entry после foundation.
6. `closed_iterations.md` — исторические детали и закрытые итерации.

## Карта файлов

| Файл | Статус | Назначение |
|---|---|---|
| [readme.md](readme.md) | Live | Главная карта папки `doc/` |
| [index.md](index.md) | Live | Быстрый навигатор по ролям и сценариям чтения |
| [architecture.md](architecture.md) | Live | Реальная архитектура и потоки данных |
| [index_lifecycle.md](index_lifecycle.md) | Live | Резервное копирование индекса, `reindex`/`reset`, кэш и производные файлы |
| [technical_specification.md](technical_specification.md) | Live | Технический снимок системы и ограничений |
| [api_reference.md](api_reference.md) | Live | Карта HTTP API и основных контрактов |
| [user_guide.md](user_guide.md) | Live | Быстрый старт |
| [user_guide_details.md](user_guide_details.md) | Live | Индексация, API/CLI/UI, env, smoke, troubleshooting |
| [user_scenarios.md](user_scenarios.md) | Live | Сквозные пользовательские сценарии |
| [user_stories.md](user_stories.md) | Roadmap | Короткий индекс US-*, shortlists и связи |
| [user_stories/](user_stories/) | Roadmap | Полные INVEST / Given-When-Then acceptance criteria: один файл на US-* |
| [user_stories_details.md](user_stories_details.md) | Roadmap | Лёгкий compatibility-индекс на `user_stories/` |
| [vision.md](vision.md) | Live | Текущая продуктовая рамка и границы решения |
| [conventions.md](conventions.md) | Live | TL;DR и навигация по соглашениям |
| [conventions_architecture.md](conventions_architecture.md) | Live | Архитектурные соглашения и дерево `app/` |
| [conventions_reference.md](conventions_reference.md) | Live | Промпты, HTTP, ошибки, тесты, doc-sync, агенты |
| [archive/tasklist_historical.md](archive/tasklist_historical.md) | Historical | Exit criteria закрытых срезов, архив This Week |
| [observability_slo.md](observability_slo.md) | Reference | Метрики, SLO, alerts и OTEL |
| [personalized_learner_model.md](personalized_learner_model.md) | Reference | Learner model и adaptive daily plan |
| [changelog.md](changelog.md) | Live | Последние изменения документации |
| [backlog_registry.yaml](backlog_registry.yaml) | Roadmap | SSoT: пакеты, статусы, владельцы |
| [tasklist.md](tasklist.md) | Roadmap | Производный weekly execution backlog (из реестра) |
| [roadmap_governance.md](roadmap_governance.md) | Roadmap | Правила roadmap, merge-gate'ы и tail governance |
| [roadmap.md](roadmap.md) | Roadmap | Сводная карта эпох, волн, US/CJM и ссылок на SSoT |
| [next/localhost_balance_course_delight_breakthrough.md](next/localhost_balance_course_delight_breakthrough.md) | Roadmap | Текущий breakthrough brief: `qwen/qwen3.6-27b` accepted, Smoke v7 PASS, Wave 2 ready |
| [future_roadmap.md](future_roadmap.md) | Roadmap | Стратегический индекс E4–E13 + правила re-entry |
| [closed_iterations.md](closed_iterations.md) | Historical | Закрытые итерации и исторические детали |
| [product_idea.md](product_idea.md) | Roadmap | Продуктовая идея и направления развития |
| [adr.md](adr.md) | ADR | Индекс архитектурных решений |
| [archive/adr_rag_architecture.md](archive/adr_rag_architecture.md) | ADR | Расширенные ADR по RAG-архитектуре |
| [archive/blue_green_reindex_*](archive/) | Historical | История проектирования blue-green reindex |
| [archive/architectural_refactoring.md](archive/architectural_refactoring.md) | Historical | Исторический refactoring plan |
| [archive/](archive/) | Archive | Старые аналитические материалы |
| [archive/agent_prompts/README.md](archive/) | Archive | Индекс заархивированных контрактных prompts для агентов |
