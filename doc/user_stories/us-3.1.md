---
us_id: "US-3.1"
epic: 3
epic_name: "Epic 3: First Answer"
priority: "P0"
cjm_stage: "2"
cjm_moment_name: "First answer / course activation"
status: "closed"
covered_by: "strong-move-first-session-cold-open-v1"
closed_date: "2026-05-24"
---

# US-3.1 — Получить первый ответ за < 5 секунд (P0)

## Epic 3: First Answer

[← Back to user stories index](../user_stories.md)

---

### US-3.1 — Получить первый ответ за < 5 секунд (P0)
**As a** Learner после индексации,
**I want** получить релевантный ответ с источниками за < 5 секунд,
**so that** у меня сложилось «wow»-впечатление.

**Acceptance:**
- Given индекс собран и я открыл Streamlit,
- When я задаю любой вопрос из `doc/user_scenarios.md` § 2,
- Then ответ с минимум одним источником появляется за < 5 секунд (p95 на typical hardware).

## Status History

- 2026-04-25 | status: `closed` | covered_by: `epoch-demo-scenario-03-tutor` | closed_date: `2026-04-25`
