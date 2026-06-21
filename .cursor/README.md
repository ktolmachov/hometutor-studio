# Cursor: правила и связь с `doc/`

## Назначение

- **[`rules/conventions.mdc`](rules/conventions.mdc)** — always-on сжатые соглашения по коду и структуре (должны совпадать с репозиторием).
- **[`rules/workflow.mdc`](rules/workflow.mdc)** — always-on процесс итераций, tasklist, коммиты, тесты.

Полные и актуальные тексты — в каталоге **`doc/`** (источник правды для деталей).

## Ключевые документы в `doc/`

| Файл | Содержание |
|------|------------|
| [conventions.md](../doc/conventions.md) | TL;DR и навигация; детали — [conventions_architecture.md](../doc/conventions_architecture.md), [conventions_reference.md](../doc/conventions_reference.md) |
| [vision.md](../doc/vision.md) | Продукт, стек и границы (кратко) |
| [tasklist.md](../doc/tasklist.md) | Активный backlog; архив критериев — [tasklist_historical.md](../doc/tasklist_historical.md) |
| [user_guide.md](../doc/user_guide.md) | Быстрый старт; детали — [user_guide_details.md](../doc/user_guide_details.md) |
| [adr.md](../doc/adr.md), [adr_rag_architecture.md](../doc/adr_rag_architecture.md) | Архитектурные решения |
| [architectural_refactoring.md](../doc/architectural_refactoring.md) | Рефакторинг и приоритеты |
| [product_idea.md](../doc/product_idea.md) | Продукт и roadmap |
| [observability_slo.md](../doc/observability_slo.md) | SLO, алерты, OTel |
| [routing_quality_validation.md](../doc/routing_quality_validation.md) | Маршрутизация overview/synthesis |

## Синхронизация

При изменении **`doc/conventions.md`** или **`doc/vision.md`** (структура модулей, процессы):

1. Обновить **`rules/conventions.mdc`** (дерево, архитектурные буллеты).
2. При изменении процесса итераций — **`rules/workflow.mdc`** и при необходимости [doc/conventions_reference.md](../doc/conventions_reference.md) (§ Документация).

Обратная ссылка: в начале [doc/conventions.md](../doc/conventions.md) указано, что существует краткая копия в `.cursor/rules/`.
