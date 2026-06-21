# Expert Controls Recommendations

Дата: 2026-05-14
Статус: Recommendation Ready
Источник: product analysis после UX Breakthrough wave

## Executive Summary

После UX-рефакторинга опытным пользователям нужен единый блок
`Расширенное управление (эксперт)` в mission-critical разделах. Сейчас
экспертная прозрачность покрывает глобальный sidebar и Q&A, но SRS, Tutor,
Quiz и Adaptive Plan остаются неравномерными по explainability и управлению.

Рекомендация: оформить follow-up wave `wave-expert-controls-2026-05` с двумя
пакетами:

1. `epoch-expert-controls-phase-1` — P0: Flashcards + Tutor.
2. `epoch-expert-controls-phase-2` — P1/P2: Quiz + Adaptive Plan.

Оба пакета регистрируются как `proposed`: они готовы к PO review, но не
занимают singleton `ready/wip` slot.

## Prioritization

| Section | File | Algorithm complexity | Current transparency | Priority | Estimate |
|---|---|---:|---:|---:|---:|
| Flashcards | `app/ui/flashcards_review_view.py` | High, SM-2 | Low | P0 | 3h |
| Tutor | `app/ui/tutor_chat_footer.py` / `app/ui/tutor_chat_controls.py` | High, policy engine | Medium | P0 | 4h |
| Quiz | `app/ui/interactive_quiz.py` | Medium | High | P1 | 2h |
| Adaptive Plan | `app/ui/adaptive_daily_plan_layout.py` | Medium | High, JSON dump | P2 | 2h |

## Phase 1: Flashcards And Tutor

Package: `epoch-expert-controls-phase-1`
Wave: `wave-expert-controls-2026-05`
Priority: P0
Estimate: 7h

### Flashcards Scope

Goal: make SM-2 review behavior inspectable and controllable without
overwhelming the default review flow.

Recommended UI placement:

- File: `app/ui/flashcards_review_view.py`
- Position: after review progress, before the current card body.
- Expander label: existing `expert_controls_expander_label_ru()`.
- Default state: collapsed.

Recommended sections:

- Current card statistics: interval days, easiness factor, repetitions, due
  status, and short explanation of EF ranges.
- Rating history: last 10 ratings with timestamp, quality, and resulting
  interval.
- Review queue filters: interval range, EF/difficulty band, overdue threshold.
- SM-2 settings: minimum EF, first interval settings, and optional cramming
  mode with clear warning.
- Session debug/export: recent review actions and JSON export for local
  inspection.

Backend recommendations:

- Add a history query in `app/flashcard_service.py` through existing
  persistence boundaries.
- Add queue filtering behind service/helper functions rather than filtering
  ad hoc in UI.
- Persist user SM-2 expert settings through documented user-state helpers, not
  direct SQLite connections from UI or services.
- Keep cramming mode explicit and local to future scheduling decisions.

DoD:

- Expert block renders collapsed in Flashcards review.
- EF, interval, repetitions, due/overdue state, and last rating history are
  visible for the current card.
- Queue filters affect the review queue and survive rerun for the session.
- SM-2 settings persist through existing user-state boundaries.
- Cramming mode has a visible warning and deterministic scheduling behavior.
- Debug log captures session actions without leaking secrets.
- JSON export works.
- Targeted tests: `tests/test_flashcard_service.py` plus a focused UI/helper
  test if a helper module is added.

### Tutor Scope

Goal: explain tutor policy decisions, LLM context shape, and session state to
advanced users while preserving a calm default footer.

Recommended UI placement:

- File: `app/ui/tutor_chat_footer.py` or `app/ui/tutor_chat_controls.py`.
- Position: after existing tutor action controls.
- Expander label: existing `expert_controls_expander_label_ru()`.
- Default state: collapsed.

Recommended sections:

- Session state: session id, turn count, learned concepts, current policy step.
- Policy engine debug: selected action, reason, score/weight if available,
  alternatives, and routing signals.
- LLM context: model, token counts where available, retrieval sources, and a
  redacted prompt preview.
- Session management: Markdown export and reset with confirmation.
- Policy override: optional next-step override for local expert experiments.

Backend recommendations:

- Store policy-decision debug snapshots in session state or a UI-safe debug
  contract at orchestration boundaries.
- Keep prompts in `app/prompts/` and LLM clients in `app/provider.py`; do not
  introduce UI-side prompt/client construction.
- Redact sensitive values before showing prompt/context debug.
- Treat override as an explicit session-scoped control and log it in debug
  state.

DoD:

- Expert block renders collapsed in Tutor.
- Session state, policy choice, alternatives, and routing signals are visible.
- LLM context shows token/model/source metadata when available.
- Markdown export works.
- Reset requires confirmation.
- Policy override affects only the next tutor step and is visible to the user.
- Targeted tests: `tests/test_tutor_orchestrator.py`,
  `tests/test_pipeline_steps.py`, and UI helper tests if helpers are added.

## Phase 2: Quiz And Adaptive Plan

Package: `epoch-expert-controls-phase-2`
Wave: `wave-expert-controls-2026-05`
Priority: P1/P2
Estimate: 4h

### Quiz Scope

Goal: expose generation controls and debug context for users tuning practice
sessions.

Recommended sections:

- Generation parameters: difficulty, question type balance, graph-only concept
  selection if supported by existing contracts.
- Quiz statistics: type distribution, average difficulty, concepts covered.
- Debug: redacted prompt metadata and raw generation diagnostics where safe.

DoD:

- Expert block renders collapsed in Quiz.
- Generation parameters are session-scoped and deterministic.
- Debug data is redacted and does not expose secrets.
- Targeted tests cover generation parameter plumbing and UI helper behavior.

### Adaptive Plan Scope

Goal: make plan construction and personalization inspectable without changing
the default learner-facing plan.

Recommended sections:

- Plan-building logic: weights, order reasons, and selected signals.
- Learner profile snapshot: mastery, due pressure, current course/scope where
  available.
- Plan history: compact last-7-days view if existing persistence supports it.

DoD:

- Expert block renders collapsed in Adaptive Plan.
- Plan reasons and profile snapshot are visible.
- History is shown only through existing persistence contracts.
- Targeted tests cover rendering helpers and avoid direct SQLite access.

## UX Rules

- Use `expert_controls_expander_label_ru()` for the top-level label.
- Use per-section intro strings from `app/ui/continuity_bridge.py` when the
  implementation package adds them.
- Keep top-level expert blocks collapsed by default.
- Recommended order: statistics, controls, debug/export.
- Do not put expert controls inside nested visual cards.
- Do not expose API keys, raw env values, or unredacted provider payloads.
- Keep controls local-first and session-scoped unless persistence is explicitly
  part of package DoD.

Suggested bridge strings for implementation:

```python
def flashcards_expert_controls_intro_ru() -> str:
    return "SM-2 статистика, фильтры очереди и настройки алгоритма"

def tutor_expert_controls_intro_ru() -> str:
    return "Policy engine, контекст LLM и управление сессией"

def quiz_expert_controls_intro_ru() -> str:
    return "Параметры генерации, статистика квиза и debug"

def adaptive_plan_expert_controls_intro_ru() -> str:
    return "Логика построения плана, персонализация и история"
```

## Risks

| Risk | Probability | Impact | Mitigation |
|---|---:|---:|---|
| Cognitive overload | Medium | High | Collapsed by default, progressive disclosure |
| Debug performance cost | Low | Medium | Lazy rendering, bounded logs |
| Sensitive data exposure | Low | High | Redaction gate before display/export |
| UI contract drift | Low | Medium | Focused UI helper tests and existing design conventions |

## Success Metrics

- Adoption: at least 30% of advanced users open an expert block once.
- Engagement: at least 10% use filters, exports, or settings.
- Satisfaction: at least 4.5/5 usefulness score after repeated use.

Metrics should be local-first and privacy-preserving. Avoid adding analytics
that leaves the local environment unless a separate privacy-reviewed package
explicitly approves it.

## PO Checklist

- Review Phase 1 scope and confirm it should be promoted before Phase 2.
- Check active package slot in `doc/backlog_registry.yaml`.
- Promote `epoch-expert-controls-phase-1` from `proposed` to `ready` only when
  the singleton active slot is free.
- Run `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Start execution through `scripts/workflow.py` after promotion.
