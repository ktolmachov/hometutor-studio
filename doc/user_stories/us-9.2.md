---
us_id: "US-9.2"
epic: 9
epic_name: "Epic 9: Progress & Motivation"
priority: "P2"
cjm_stage: "9"
cjm_moment_name: "Concept graduation"
status: "closed"
covered_by: "epoch-concept-remediation-step"
closed_date: "2026-04-27"
---

# US-9.2 — Concept "graduation" (P2)

## Epic 9: Progress & Motivation

[← Back to user stories index](../user_stories.md)

---

### US-9.2 — Concept "graduation" (P2)
**As a** Learner,
**I want** явный момент "ты освоил концепт X",
**so that** у меня есть ощущение завершения.

**Acceptance:**
- Given концепт достиг mastery=transfer и есть подтверждённая дата достижения/удержания transfer старше 7 дней,
- When система рассчитывает план,
- Then концепт получает badge "graduated", удаляется из gap-блоков, отмечается в KG.
- And если дата отсутствует или младше 7 дней, концепт не получает graduation и остаётся в fallback-состоянии "not graduated yet".

---

## Epic 10: Export / Sync / Multi-device

## Status History

- 2026-04-20 | status: `closed` | covered_by: `E10.4-A` | closed_date: `2026-04-20`
- 2026-04-26 | status: `closed` | covered_by: `epoch-tour-persistence-ch2-5` | closed_date: `2026-04-26`
