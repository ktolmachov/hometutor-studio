---
us_id: "US-1.1"
epic: 1
epic_name: "Epic 1: Discover & Install"
priority: "P1"
cjm_stage: "1"
cjm_moment_name: "Discover / first launch"
status: "closed"
covered_by: "workflow-dx-p4-common-rules"
closed_date: "2026-05-03"
---

# US-1.1 — Понять, для чего нужен hometutor (P1)

## Epic 1: Discover & Install

[← Back to user stories index](../user_stories.md)

---

### US-1.1 — Понять, для чего нужен hometutor (P1)
**As a** новый пользователь, который наткнулся на репозиторий,
**I want** за 60 секунд понять, чем hometutor отличается от ChatGPT и Obsidian,
**so that** я мог решить, стоит ли его ставить.

**Acceptance:**
- Given я открыл `README.md`,
- When я прочитал верхний экран (до первого `##`),
- Then я вижу: 1-предложение позиционирование, visual demo path главного flow, ссылку
  на `doc/product_idea.md` и явный список «для кого / не для кого».
- And если готового GIF/screencast asset нет, допустим статичный markdown fallback без новой генерации медиа.

## Status History

- 2026-04-20 | status: `closed` | covered_by: `E10.4-C` | closed_date: `2026-04-20`
