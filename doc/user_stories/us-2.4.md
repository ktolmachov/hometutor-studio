---
us_id: "US-2.4"
epic: 2
epic_name: "Epic 2: Ingest"
title: "Диагностика готовности файлов перед первым вопросом"
priority: "P2"
cjm_stage: "2"
cjm_moment_name: "Ingest / First Answer"
status: "closed"
covered_by: "epoch-us-2-4-source-readiness-mvp"
closed_date: "2026-05-01"
---

# US-2.4 — Диагностика готовности файлов перед первым вопросом (P2)

## Epic 2: Ingest

[← Back to user stories index](../user_stories.md)

---

### US-2.4 — Диагностика готовности файлов перед первым вопросом (P2)

**As a** Learner, который добавил в `data/` несколько материалов с разным качеством извлечения текста,
**I want** видеть, какие файлы уже пригодны для обычного индекса, какие потребуют OCR/доработки, и какой один безопасный следующий шаг по ingest,
**so that** я не трачу первое обращение к системе на «пустой» retrieval из-за неготового корпуса.

**Acceptance Criteria:**

- Перед первым meaningful Q&A learner может получить сводку по корпусу в `data/`: минимум три класса — «text-ready», «needs OCR / extraction», «problematic» (с кратким объяснением критерия на уровне продукта, не только внутренний лог).
- Рекомендуется один primary next action (например: переиндексировать готовые, убрать проблемный файл, отложить вопрос до исправления), согласованный с существующими UX-паттернами приложения (не новый параллельный «магазин экранов» без нужды).
- Сценарий явно согласован с **US-2.3** (non-text / OCR-путь): диагностика не заменяет OCR-ингест, а указывает, где он потребуется.
- Пока история открыта, полноценный learner-facing diagnostic UI не обязан быть реализован; пакеты внедрения следуют после принятия этой US.

**Related:** **US-2.1** (прогресс индексации), **US-2.3** (non-text corpus ingest).

## Status History

- 2026-05-01 | status: `open` | создано в `epoch-source-readiness-diagnostic-story` как Product/Analyst story-gate.
