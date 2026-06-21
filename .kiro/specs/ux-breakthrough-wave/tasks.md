# Implementation Plan — UX Breakthrough Wave

## Overview

This plan intentionally replaces the earlier one-package implementation with five smaller packages. The goal is to keep each agent run reviewable, testable and compatible with project write-set/read-set rules.

## Phase 0: Review Gate

- [ ] 0.1 Confirm the wave remains `proposed` until the package split is reviewed.
- [ ] 0.2 Run registry validation before implementation starts:
  - `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict`
- [ ] 0.3 Treat `doc/backlog_registry.yaml` as SSoT for package order.

## Package 1: `ux-foundation-parsers-contracts`

- [ ] 1.1 Implement `app/answer_parser.py`
  - Add `AnswerObject`.
  - Add `parse_answer()` and `format_answer()`.
  - Add descriptive `AnswerParseError`.
  - Preserve semantic round-trip.
  - _Requirements: 1.1, 1.4, 1.5_

- [ ] 1.2 Implement `app/tutor_context_parser.py`
  - Add `ContextObject`.
  - Add `serialize_context()`, `deserialize_context()`, `validate_context()`.
  - Return missing fields explicitly for incomplete handoff payloads.
  - _Requirements: 1.2, 1.4, 1.5, 3.1, 3.2_

- [ ] 1.3 Implement `app/session_analytics_parser.py`
  - Add `GradesDistribution`, `RetentionPrediction`, `SessionStatsObject`.
  - Add velocity, percentages, insufficient-data flag and 7-day schedule helpers.
  - Keep persistence representation JSON-serializable.
  - _Requirements: 1.3, 1.4, 5.2, 5.3, 5.5_

- [ ] 1.4 Add parser tests
  - `tests/test_answer_parser.py`
  - `tests/test_tutor_context_parser.py`
  - `tests/test_session_analytics_parser.py`
  - Include property-style tests for the 11 properties listed in `design.md`.
  - _Requirements: 1.4, 1.5_

- [ ] 1.5 Checkpoint
  - Run `.\.venv\Scripts\python.exe -m pytest tests/test_answer_parser.py tests/test_tutor_context_parser.py tests/test_session_analytics_parser.py -v`
  - Run `.\.venv\Scripts\python.exe scripts/check_llm_context_gate.py`

## Package 2: `ux-first-answer-wait-flow`

- [ ] 2.1 Enhance `app/ui/qa_wait_ux.py`
  - Add skeleton/progress rendering helpers.
  - Keep layout stable between loading and final answer.
  - Add instant-render fallback.
  - _Requirements: 2.1, 2.2, 2.5, 2.6_

- [ ] 2.2 Integrate wait state in `app/ui/query_tab.py`
  - Show first visible feedback before the blocking ask call.
  - Preserve existing guardrails and query flow.
  - Use `AnswerObject` for final display when available.
  - _Requirements: 2.1, 2.3, 2.4, 2.7_

- [ ] 2.3 Add tests
  - Add `tests/test_ui_wait_ux.py`.
  - Cover stage labels, fallback rendering and timing helpers.
  - _Requirements: 2.1, 2.2, 2.7_

- [ ] 2.4 Checkpoint
  - Run `.\.venv\Scripts\python.exe -m pytest tests/test_ui_wait_ux.py tests/test_answer_parser.py -v`

## Package 3: `epoch-us19-2-tutor-handoff-ux`

- [ ] 3.1 Update answer-to-tutor handoff in `app/ui/query_tab.py`
  - Build `ContextObject` from the answer, sources, topic/concepts and confidence.
  - Store the payload in Streamlit session state.
  - Avoid blank intermediate states.
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 3.2 Update `app/ui/tutor_chat.py`
  - Decode and validate handoff payload.
  - Show compact context summary.
  - Connect first tutor step to the original question/topic.
  - Handle incomplete context transparently.
  - _Requirements: 3.4, 3.5, 3.6, 3.7_

- [ ] 3.3 Add tests
  - Extend `tests/test_tutor_context_parser.py`.
  - Add/extend UI helper tests for session-state payload handling.
  - _Requirements: 3.1, 3.2, 3.6_

- [ ] 3.4 Checkpoint
  - Run `.\.venv\Scripts\python.exe -m pytest tests/test_tutor_context_parser.py tests/test_ui_helpers.py -v`

## Package 4: `ux-mastery-celebration-analytics`

- [ ] 4.1 Integrate session analytics in `app/flashcard_service.py`
  - Use `SessionStatsObject` for completed review sessions.
  - Persist analytics history through existing user-state APIs.
  - _Requirements: 5.1, 5.7, Cross-cutting 5_

- [ ] 4.2 Enhance `app/ui/flashcards_review_view.py`
  - Show grade distribution, velocity and 7-day timeline.
  - Show insufficient-data state for small sessions.
  - Offer "Разобрать сложные темы" when Again count ≥3.
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [ ] 4.3 Enhance `app/ui/graduation_overlay.py`
  - Render skippable graduation surface for mastery ≥80%.
  - Show badge, topic, mastery and available learning metrics.
  - Provide next-step CTA.
  - _Requirements: 4.1, 4.2, 4.4, 4.5, 4.6_

- [ ] 4.4 Integrate badge persistence in `app/gamification_service.py`
  - Persist/retrieve achievement badges through existing boundaries.
  - Add regression tests for badge lifecycle.
  - _Requirements: 4.3_

- [ ] 4.5 Add tests
  - Extend `tests/test_session_analytics_parser.py`.
  - Extend `tests/test_flashcard_service.py`.
  - Add `tests/test_ui_graduation_overlay.py`.
  - _Requirements: 4.1-4.6, 5.1-5.7_

- [ ] 4.6 Checkpoint
  - Run `.\.venv\Scripts\python.exe -m pytest tests/test_session_analytics_parser.py tests/test_flashcard_service.py tests/test_ui_graduation_overlay.py -v`

## Package 5: `ux-home-hub-navigation-polish`

- [ ] 5.1 Enhance `app/ui/home_hub.py`
  - Render stable, scan-friendly mode selection.
  - Prioritize resume card when meaningful unfinished session exists.
  - Highlight flashcards when due count >0.
  - _Requirements: 6.1, 6.2, 6.3_

- [ ] 5.2 Update `app/ui_theme.css`
  - Add restrained hover/focus states.
  - Avoid nested card-in-card styling.
  - Ensure text fits inside cards/buttons.
  - _Requirements: 6.4, 6.5, 6.6_

- [ ] 5.3 Add tests
  - Add `tests/test_ui_home_hub_enhanced.py`.
  - Cover resume priority, due badge and mode metadata.
  - _Requirements: 6.1, 6.2, 6.3_

- [ ] 5.4 Checkpoint
  - Run `.\.venv\Scripts\python.exe -m pytest tests/test_ui_home_hub_enhanced.py tests/test_ui_helpers.py -v`

## Final Documentation and Closure

- [ ] 6.1 Update user docs after implementation:
  - `doc/user_guide.md`
  - `doc/user_guide_details.md`
  - `doc/api_reference.md` if parser APIs are documented as public/internal contracts.

- [ ] 6.2 Update lifecycle docs when closing packages:
  - `doc/backlog_registry.yaml`
  - `doc/changelog.md`
  - linked `doc/user_stories/us-19.*.md`
  - generated indexes via project scripts.

- [ ] 6.3 Final checks for the wave:
  - targeted pytest bundles from each package,
  - `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict`,
  - `.\.venv\Scripts\python.exe scripts/check_llm_context_gate.py`.

## Notes

- Tests are not optional in this wave. The previous `*` optional marker is removed because parser contracts and UI state regressions are the primary risk.
- Do not implement all five packages in one agent run unless the user explicitly asks for that scope.
- Full test suite is intentionally not part of the default DoD; use targeted tests unless explicitly requested.
