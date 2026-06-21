---
us_id: "US-3.4"
epic: 3
epic_name: "Epic 3: First Answer"
priority: "P0"
cjm_stage: "2"
cjm_moment_name: "First answer / course activation"
status: "closed"
covered_by: "unknown-closed"
closed_date: "2026-04-25"
---

# US-3.4 — Smart-default retrieval на первом вопросе (P0)

## Epic 3: First Answer

[← Back to user stories index](../user_stories.md)

---

### US-3.4 — Smart-default retrieval на первом вопросе (P0)
**As a** Learner, который задаёт самый первый вопрос по новой базе,
**I want** чтобы система автоматически выбирала безопасный retrieval path по типу вопроса,
**so that** я не получал слабый ответ только из-за неудачного default-профиля.

**Acceptance:**
- Given индекс собран и я задаю первый вопрос без ручной настройки профиля,
- When вопрос относится к `keyword`, `overview`, `synthesis` или обычному `qa`,
- Then система выбирает retrieval strategy по типу вопроса без ручного вмешательства.
- And в debug/trust-представлении видно, какой retrieval path был использован.
- And для тривиального вопроса из стартового набора продукт не отвечает пустым «не нашёл информации»,
  если в базе есть релевантные документы.

---

## Epic 4: Switch to Tutor

## Status History

- 2026-04-25 | status: `closed` | covered_by: `unknown-closed` | closed_date: `2026-04-25`
