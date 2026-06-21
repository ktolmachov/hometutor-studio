---
us_id: "US-3.6"
epic: 3
epic_name: "Epic 3: First Answer"
priority: "P1"
cjm_stage: "2"
cjm_moment_name: "MoT №2 First Answer / two-stage path"
title: "US-3.6 — Двухступенчатый ответ: покрытие до полной генерации"
status: "closed"
covered_by: "epoch-cjm-pain-map-ssot-sync"
closed_date: "2026-05-03"
---

# US-3.6 — Двухступенчатый ответ: покрытие до полной генерации (P1)

## Epic 3: First Answer

[← Back to user stories index](../user_stories.md)

---

### US-3.6 — Двухступенчатый ответ: покрытие до полной генерации (P1)

**As a** Learner,
**I want** для запросов с высокой уверенностью retrieval-«покрытия» получать ответ по более короткому и дешёвому по контексту пути, а для сложных случаев — полный путь,
**so that** первый ответ быстрее и предсказуемее по стоимости, без деградации на тривиальных вопросах.

**Источник идей:** breakthrough ideation 2026-05-02 — P-02; связка с deferred `performance-tail-18-1` (latency SLO / eval gate).

**Acceptance:**

- Given задан вопрос с известным индексом,
- When обрабатывается запрос,
- Then явно задокументированы критерии «раннего выхода» vs полного LLM-пути (конфиг или код + docs).
- And eval / latency gate обновлены или расширены так, чтобы не было роста доли «не нашёл» на тривиальных вопросах из CJM §8.
- And суммарный контекст на один пользовательский запрос остаётся в рамках согласованного лимита (напр. &lt; 1M токенов при текущей политике продукта).
- And формат micro-quiz и контракты вопросов **не** меняются.
- And зелёные целевые `pytest` по затронутому контуру (указать в `backlog_registry.yaml` при исполнении).

---

## Status History

- 2026-05-02 | status: `open` | принято из breakthrough ideation; пакет `epoch-mot2-two-stage-answer`
