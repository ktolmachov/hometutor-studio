---
us_id: "US-4.2"
epic: 4
epic_name: "Epic 4: Switch to Tutor"
priority: "P1"
cjm_stage: "3"
cjm_moment_name: "Switch to Tutor"
status: "closed"
covered_by: "epoch-expert-controls-phase-1"
closed_date: "2026-05-15"
---

# US-4.2 — Понять, что сейчас делает тьютор и почему (P1)

## Epic 4: Switch to Tutor

[← Back to user stories index](../user_stories.md)

---

### US-4.2 — Понять, что сейчас делает тьютор и почему (P1)
**As a** Learner в tutor mode,
**I want** видеть короткую плашку "сейчас объясняю, потому что mastery=recognition",
**so that** действия router'а не выглядят рандомными.

**Acceptance:**
- Given Pedagogical Router выбрал действие explain/quiz/review,
- When я открыл tutor surface,
- Then у блока есть строка с reason из `policy_clamp_reasons`/`tutor_decision`.

---

## Epic 5: Micro-quiz

## Status History

- 2026-04-22 | status: `closed` | covered_by: `epoch-tutor-transparency` | closed_date: `2026-04-22`
- 2026-04-26 | status: `closed` | covered_by: `epoch-tour-persistence-ch2-5` | closed_date: `2026-04-26`
