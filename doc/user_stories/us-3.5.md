---
us_id: "US-3.5"
epic: 3
epic_name: "Epic 3: First Answer"
priority: "P1"
cjm_stage: "2"
cjm_moment_name: "MoT №2 First Answer / perceived latency"
title: "US-3.5 — Управляемое ожидание первого ответа (latency UX)"
status: "closed"
covered_by: "epoch-mot2-wait-ux-engagement"
closed_date: "2026-05-02"
---

# US-3.5 — Управляемое ожидание первого ответа (latency UX) (P1)

## Epic 3: First Answer

[← Back to user stories index](../user_stories.md)

---

### US-3.5 — Управляемое ожидание первого ответа (latency UX) (P1)

**As a** Learner в Quick Answer,
**I want** пока система готовит первый ответ, видеть понятный, не отвлекающий фидбек и при быстром удачном ответе — лёгкое подкрепление,
**so that** пауза не ощущается как зависание, а успех закрепляется без обмана насчёт качества ответа.

**Источник идей:** breakthrough ideation 2026-05-02 (`archive/ideation/mot2_first_answer_latency_eval_2026-05-02.md`) — E-01, P-01, E-02.

**Acceptance:**

- Given я отправляю вопрос в Quick Answer,
- When запрос обрабатывается,
- Then показывается не менее одной фазы ожидания с педагогически выверенной копи (ротация вариантов, без техно-жаргона по умолчанию).
- And переменный микро-фидбек не перекрывает вопрос (ограниченная частота смены; нет бесконечных отвлекающих анимаций).
- And при ответе, уложившемся в согласованный порог latency и прошедшем trust-гейты, показывается ненавязчивое позитивное подкрепление (copy или лёгкий UI).
- And контракт micro-quiz / существующий формат вопросов в tutor loop **не** меняется; регрессионные тесты по quiz зелёные.
- And в `doc/user_guide.md` или `user_guide_details.md` зафиксировано, что подкрепление относится к UX ожидания, а не к гарантии истинности ответа.

---

## Status History

- 2026-05-02 | status: `open` | принято из breakthrough ideation; пакет `epoch-mot2-wait-ux-engagement`
