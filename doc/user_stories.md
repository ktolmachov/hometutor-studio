# User Stories — Learner (home-rag)

Актуализировано на **2026-05-23** (детали вынесены по одной US в `doc/user_stories/`).

> **Статус:** ✅ Все 87 User Stories закрыты. `open_candidates` пуст. Полное покрытие 13 моментов истины CJM.

Производные от `doc/cjm.md`, `doc/user_scenarios.md`, `doc/product_idea.md` и
`doc/personalized_learner_model.md`. Этот файл — короткий индекс и навигация;
полные INVEST + acceptance criteria (Given / When / Then) лежат по одной US в
`doc/user_stories/`. Persona по умолчанию — **Learner** (самообучающийся
пользователь с локальной базой документов). Группировка по стадиям CJM.

Приоритеты: **P0** — блокирует CJM moment of truth; **P1** — устраняет известный pain;
**P2** — улучшение / nice-to-have.

Критерии качества для этого документа:
- story описывает пользовательскую ценность, а не внутреннюю реализацию;
- acceptance можно проверить вручную или автоматизацией;
- story привязана к стадии CJM и pain/opportunity, а не «висит в воздухе»;
- P0 stories закрывают нижние точки эмоциональной кривой: **Install** и **Micro-quiz**,
  а также moments of truth №1–7 из `doc/cjm.md`.

## Базовый shortlist из CJM

Это не полный backlog, а минимальный набор stories, которые сильнее всего влияют на
activation, trust и day-2 retention. Часть этих stories уже закрыта в E9/E10 и остаётся здесь как CJM-baseline:

| Rank | Story | Почему сейчас |
|---|---|---|
| 1 | `US-1.2` — one-command install | Самая низкая точка CJM: пользователь теряется до первого value moment |
| 2 | `US-3.1` — первый ответ < 5 сек с источниками | Главный wow-moment продукта |
| 3 | `US-3.4` — smart-default retrieval на первом вопросе | Снижает риск раннего недоверия из-за слабого retrieval |
| 4 | `US-4.1` — мост из Q&A в Tutor | Переводит разовый value в обучающий loop |
| 5 | `US-4.2` — прозрачность тьютора | Снимает ощущение «router выбрал это случайно» |
| 6 | `US-5.1` — мгновенный feedback после micro-quiz | Удерживает пользователя в моменте напряжения |
| 7 | `US-7.3` — resume card на следующий день | Ключевой day-2 retention hook |
| 8 | `US-8.1` — сохранить mastery после reindex | Критический момент доверия после смены индекса |

## Closed shortlist для E10.4

Этот список оставлен как закрытый execution snapshot. Источник package-level scope: `doc/backlog_registry.yaml`; `doc/tasklist.md` — производный weekly view.

| Package | Story | Почему сейчас | Gate |
|---|---|---|---|
| **E10.4-A** | `US-9.2` — Concept graduation | Следующий качественный скачок: learner видит завершение, а план перестаёт возвращать освоенное в gap | `pytest tests/test_concept_graduation.py` |
| **E10.4-B** | `US-9.1` — Progress tab completion | Собирает mastery, weekly goals, daily streak и KG snapshot в одном месте без нового тяжёлого dashboard | `pytest tests/test_progress_tab.py tests/test_mastery_dashboard.py` |
| **E10.4-C** | `US-1.1` — README demo path | Ускоряет Discover после закрытия install path; static fallback first, GIF/screencast только если asset уже есть | markdown review |

---

## Closed shortlist для E11

E11 стартовал после закрытия E10.4 и закрыт полностью. Цель — убрать прокрастинацию новичка через один следующий шаг, не отнимая у опытного пользователя control/debug/graph/eval возможности. E11-R закрыт как intent-repair tail по full router eval.

| Package | Story | Почему сейчас | Gate |
|---|---|---|---|
| **E11-A** | `closed` — `US-14.1` guided next-best-action | Новичок не выбирает из 10 равных входов, а видит один безопасный следующий шаг | `pytest tests/test_e11_guided_start.py tests/test_e9_7_continuity_bridge.py` |
| **E11-B** | `closed` — `US-14.2` beginner copy pass | Первый экран должен говорить действиями, а не router/retrieval/eval терминами | `pytest tests/test_e11_beginner_copy.py tests/test_e9_7_continuity_bridge.py` |
| **E11-C** | `closed` — `US-14.3` expert controls drawer | Опытный пользователь сохраняет скорость и контроль, но advanced слой не давит на новичка | `pytest tests/test_e11_expert_controls.py tests/test_e11_beginner_copy.py` |
| **E11-D** | `closed` — `US-14.4` 5-minute learning loop | Снижает прокрастинацию через короткий сценарий answer → quiz → feedback → progress | `pytest tests/test_e11_learning_loop.py` + focused tutor/micro-quiz contour |
| **E11-Q** | `closed` — `US-12.5` prompt quality harness | Дешёвый контроль prompt/model regressions перед router repair; не заменяет user-visible E11 пакеты | `pytest tests/test_router_eval.py`; per-category metadata/gold rationale |
| **E11-P** | `closed` — `US-12.6` Playwright E2E metrics | Проверяет E11 в настоящем браузере: CTA, Progress, expert controls, 5-minute loop | `npx playwright test` + CI artifacts |
| **E11-R** | `closed` — `US-12.5` router intent repair | Оркестратор не default’ит в explanation там, где gold — quiz/Socratic/SRS/error-diagnosis | `python scripts/run_router_eval.py`; exit artifact `eval_results/router_eval_e11_r.json` |

---

## Closed shortlist для E13

E13 не создаёт новую user story: это закрытый deferred `17.1 UX tail`, который связывает уже существующие US в один home-surface package.

| Package | Story | Почему сейчас | Gate |
|---|---|---|---|
| **E13-A** | `closed` — `US-14.1` + `US-7.3` + `US-15.2` + `US-9.1` home mode selector | Главный экран перестаёт конкурировать сам с собой: 6 основных режимов видны сразу, Flashcards показывает due badge, вторичные инструменты свернуты | Streamlit smoke: карточки меняют `current_view` + `st.rerun()`; `/flashcards/due/count`; responsive 900px/640px; no router/eval/tutor-runtime changes |

---

## Open candidates

<!-- GENERATED: user_stories_index.open_candidates (do not edit manually) -->

Machine-readable shortlist for planning. Full status/coverage lives in `doc/user_stories_index.json`.

| Rank | Story | CJM | Coverage | Why now |
|---|---|---|---|---|

## Coverage-aware index view

<!-- GENERATED: user_stories_index.items (do not edit manually) -->

Полные INVEST-формулировки и acceptance criteria вынесены по одной US в `doc/user_stories/`.
`Coverage` — это package id из `covered_by`; для незакрытых US используется `open`.

| Epic | Story | Priority | Status | Coverage | Details |
|---|---|---|---|---|---|
| Epic 1: Discover & Install | `US-1.1` - Понять, для чего нужен home-rag | `P1` | `closed` | `workflow-dx-p4-common-rules` | [`details`](user_stories/us-1.1.md) |
| Epic 1: Discover & Install | `US-1.2` - Поднять локально без чтения 5 документов | `P0` | `closed` | `strong-move-first-session-cold-open-v1` | [`details`](user_stories/us-1.2.md) |
| Epic 1: Discover & Install | `US-1.3` - Понять, какие env-переменные обязательны | `P1` | `closed` | `epoch-tour-skeleton-ch1` | [`details`](user_stories/us-1.3.md) |
| Epic 2: Ingest | `US-2.1` - Видеть прогресс первой индексации | `P0` | `closed` | `epoch-ingest-first-index-progress` | [`details`](user_stories/us-2.1.md) |
| Epic 2: Ingest | `US-2.2` - Инкрементальная переиндексация по умолчанию | `P1` | `closed` | `epoch-demo-scenario-08-trust` | [`details`](user_stories/us-2.2.md) |
| Epic 2: Ingest | `US-2.3` - Индексировать сканы и изображения в постоянную базу знаний | `P2` | `closed` | `epoch-ocr-docling-ingest-phase1` | [`details`](user_stories/us-2.3.md) |
| Epic 2: Ingest | `US-2.4` - Диагностика готовности файлов перед первым вопросом | `P2` | `closed` | `epoch-us-2-4-source-readiness-mvp` | [`details`](user_stories/us-2.4.md) |
| Epic 2: Ingest | `US-2.5` - Source readiness API contract parity | `P2` | `closed` | `epoch-qbi-source-readiness-contract-parity` | [`details`](user_stories/us-2.5.md) |
| Epic 3: First Answer | `US-3.1` - Получить первый ответ за < 5 секунд | `P0` | `closed` | `strong-move-first-session-cold-open-v1` | [`details`](user_stories/us-3.1.md) |
| Epic 3: First Answer | `US-3.2` - Видеть, почему фрагмент попал в ответ | `P1` | `closed` | `epoch-answer-trust-to-learning-path` | [`details`](user_stories/us-3.2.md) |
| Epic 3: First Answer | `US-3.3` - "Try these examples" на пустом экране | `P2` | `closed` | `epoch-first-answer-examples` | [`details`](user_stories/us-3.3.md) |
| Epic 3: First Answer | `US-3.4` - Smart-default retrieval на первом вопросе | `P0` | `closed` | `unknown-closed` | [`details`](user_stories/us-3.4.md) |
| Epic 3: First Answer | `US-3.5` - US-3.5 — Управляемое ожидание первого ответа (latency UX) | `P1` | `closed` | `epoch-mot2-wait-ux-engagement` | [`details`](user_stories/us-3.5.md) |
| Epic 3: First Answer | `US-3.6` - US-3.6 — Двухступенчатый ответ: покрытие до полной генерации | `P1` | `closed` | `epoch-cjm-pain-map-ssot-sync` | [`details`](user_stories/us-3.6.md) |
| Epic 4: Switch to Tutor | `US-4.1` - Перейти из Q&A в обучение одним кликом | `P0` | `closed` | `epoch-answer-trust-to-learning-path` | [`details`](user_stories/us-4.1.md) |
| Epic 4: Switch to Tutor | `US-4.2` - Понять, что сейчас делает тьютор и почему | `P1` | `closed` | `epoch-expert-controls-phase-1` | [`details`](user_stories/us-4.2.md) |
| Epic 5: Micro-quiz | `US-5.1` - Получить мгновенный feedback после ответа | `P0` | `closed` | `epoch-expert-controls-phase-2` | [`details`](user_stories/us-5.1.md) |
| Epic 5: Micro-quiz | `US-5.2` - Получить hint вместо строгого fail | `P1` | `closed` | `epoch-tour-persistence-ch2-5` | [`details`](user_stories/us-5.2.md) |
| Epic 6: Adaptive Plan & Personalization | `US-6.1` - Видеть план на сегодня после первой сессии | `P0` | `closed` | `epoch-arch-review-p5d-learning-plan-split` | [`details`](user_stories/us-6.1.md) |
| Epic 6: Adaptive Plan & Personalization | `US-6.2` - Видеть, что изменилось в плане | `P2` | `closed` | `epoch-expert-controls-phase-2` | [`details`](user_stories/us-6.2.md) |
| Epic 6: Adaptive Plan & Personalization | `US-6.3` - Видеть историю перестроения плана | `P1` | `closed` | `epoch-tour-persistence-ch2-5` | [`details`](user_stories/us-6.3.md) |
| Epic 7: Spaced Repetition & Retain | `US-7.1` - Видеть очередь повторений с приоритетами | `P0` | `closed` | `epoch-tour-persistence-ch2-5` | [`details`](user_stories/us-7.1.md) |
| Epic 7: Spaced Repetition & Retain | `US-7.2` - Soft-recovery после пропуска нескольких дней | `P1` | `closed` | `epoch-tour-scenarios-10-14` | [`details`](user_stories/us-7.2.md) |
| Epic 7: Spaced Repetition & Retain | `US-7.3` - Видеть «где остановился» сразу при входе | `P0` | `closed` | `localhost-balance-course-delight-v1` | [`details`](user_stories/us-7.3.md) |
| Epic 7: Spaced Repetition & Retain | `US-7.4` - Понимать, почему именно это нужно повторить | `P1` | `closed` | `epoch-tour-persistence-ch2-5` | [`details`](user_stories/us-7.4.md) |
| Epic 8: Reindex Resilience | `US-8.1` - Сохранить mastery после reindex | `P0` | `closed` | `epoch-mastery-gap-routing` | [`details`](user_stories/us-8.1.md) |
| Epic 8: Reindex Resilience | `US-8.2` - Видеть badge "профиль обновлён после reindex" | `P1` | `closed` | `epoch-mastery-gap-routing` | [`details`](user_stories/us-8.2.md) |
| Epic 9: Progress & Motivation | `US-9.1` - Один экран прогресса | `P1` | `closed` | `epoch-cjm-progress-next-action` | [`details`](user_stories/us-9.1.md) |
| Epic 9: Progress & Motivation | `US-9.2` - Concept "graduation" | `P2` | `closed` | `epoch-concept-remediation-step` | [`details`](user_stories/us-9.2.md) |
| Epic 10: Export / Sync / Multi-device | `US-10.1` - One-click backup всего обучения | `P1` | `closed` | `epoch-tour-scenarios-10-14` | [`details`](user_stories/us-10.1.md) |
| Epic 10: Export / Sync / Multi-device | `US-10.2` - Restore wizard на новой машине | `P2` | `closed` | `epoch-tour-scenarios-10-14` | [`details`](user_stories/us-10.2.md) |
| Epic 10: Export / Sync / Multi-device | `US-10.3` - Telegram parity badge | `P2` | `closed` | `epoch-tour-scenarios-10-14` | [`details`](user_stories/us-10.3.md) |
| Epic 11: Trust & Provenance | `US-11.1` - Inline citations в ответе | `P1` | `closed` | `epoch-demo-scenario-06-srs` | [`details`](user_stories/us-11.1.md) |
| Epic 11: Trust & Provenance | `US-11.2` - Retrieval confidence is explained honestly | `P1` | `closed` | `epoch-ssr-source-coverage-route-guard-v1` | [`details`](user_stories/us-11.2.md) |
| Epic 12: Quality Infrastructure (E10.1 / E10.3) | `US-12.1` - Benchmark качества retrieval с gate | `P1` | `closed` | `epoch-backup-benchmark-close` | [`details`](user_stories/us-12.1.md) |
| Epic 12: Quality Infrastructure (E10.1 / E10.3) | `US-12.10` - RAG adversarial corpus and regression gate | `P1` | `closed` | `epoch-adr-021a-a1-retrieval-router-profile-split` | [`details`](user_stories/us-12.10.md) |
| Epic 12: Quality Infrastructure (E10.1 / E10.3) | `US-12.11` - Local-first data governance and deletion | `P2` | `closed` | `epoch-qbi-terminology-limitations-sync` | [`details`](user_stories/us-12.11.md) |
| Epic 12: Quality Infrastructure (E10.1 / E10.3) | `US-12.2` - Поддерживаемый UI (split main.py) | `P1` | `closed` | `epoch-ssot-drift-20260521` | [`details`](user_stories/us-12.2.md) |
| Epic 12: Quality Infrastructure (E10.1 / E10.3) | `US-12.3` - Интеграционные тесты валидируют реальный retrieval | `P1` | `closed` | `epoch-backup-benchmark-close` | [`details`](user_stories/us-12.3.md) |
| Epic 12: Quality Infrastructure (E10.1 / E10.3) | `US-12.4` - Baseline точности router | `P2` | `closed` | `epoch-llm-regression-baseline` | [`details`](user_stories/us-12.4.md) |
| Epic 12: Quality Infrastructure (E10.1 / E10.3) | `US-12.5` - Prompt/model quality harness для tutor routing | `P1` | `closed` | `epoch-generate-orchestration-prompt-token-registry` | [`details`](user_stories/us-12.5.md) |
| Epic 12: Quality Infrastructure (E10.1 / E10.3) | `US-12.6` - Playwright E2E metrics для browser-level качества | `P1` | `closed` | `epoch-cjm-progress-next-action` | [`details`](user_stories/us-12.6.md) |
| Epic 12: Quality Infrastructure (E10.1 / E10.3) | `US-12.7` - Defense-grade reproducible eval baseline | `P1` | `closed` | `epoch-adr-021a-a1-retrieval-router-profile-split` | [`details`](user_stories/us-12.7.md) |
| Epic 12: Quality Infrastructure (E10.1 / E10.3) | `US-12.8` - Stage-level cost and latency transparency | `P1` | `closed` | `epoch-qbi-stage-cost-latency-budgets` | [`details`](user_stories/us-12.8.md) |
| Epic 12: Quality Infrastructure (E10.1 / E10.3) | `US-12.9` - Learning outcome metrics validate mastery | `P1` | `closed` | `epoch-qbi-learning-metrics-validation` | [`details`](user_stories/us-12.9.md) |
| Epic 13: Adaptive Quiz (E10.2) | `US-13.1` - Quiz адаптируется к моему уровню знаний | `P1` | `closed` | `epoch-tour-persistence-ch2-5` | [`details`](user_stories/us-13.1.md) |
| Epic 14: Guided Start + Expert Controls (E11) | `US-14.1` - Видеть один лучший следующий шаг | `P0` | `closed` | `epoch-cjm-progress-next-action` | [`details`](user_stories/us-14.1.md) |
| Epic 14: Guided Start + Expert Controls (E11) | `US-14.2` - Получить новичковый первый экран без технического шума | `P1` | `closed` | `epoch-home-mode-preview-drawer` | [`details`](user_stories/us-14.2.md) |
| Epic 14: Guided Start + Expert Controls (E11) | `US-14.3` - Быстро открыть expert controls без потери beginner path | `P1` | `closed` | `epoch-tour-persistence-ch2-5` | [`details`](user_stories/us-14.3.md) |
| Epic 14: Guided Start + Expert Controls (E11) | `US-14.4` - Пройти 5-minute learning loop | `P0` | `closed` | `epoch-concept-remediation-step` | [`details`](user_stories/us-14.4.md) |
| Epic 15: Flashcards & Persistent Spaced Repetition (E12) | `US-15.1` - Сгенерировать flashcards из документа базы знаний | `P1` | `closed` | `epoch-tour-persistence-ch2-5` | [`details`](user_stories/us-15.1.md) |
| Epic 15: Flashcards & Persistent Spaced Repetition (E12) | `US-15.2` - Повторить due flashcards по SM-2 расписанию | `P1` | `closed` | `epoch-expert-controls-phase-1` | [`details`](user_stories/us-15.2.md) |
| Epic 15: Flashcards & Persistent Spaced Repetition (E12) | `US-15.3` - Управлять колодами и отдельными карточками | `P2` | `closed` | `epoch-tour-persistence-ch2-5` | [`details`](user_stories/us-15.3.md) |
| Epic 15: Flashcards & Persistent Spaced Repetition (E12) | `US-15.4` - Экспортировать колоду в Anki .apkg | `P2` | `closed` | `epoch-tour-scenarios-10-14` | [`details`](user_stories/us-15.4.md) |
| Epic 15: Flashcards & Persistent Spaced Repetition (E12) | `US-15.5` - Загрузить файл из UI для генерации карточек | `P2` | `closed` | `epoch-tour-persistence-ch2-5` | [`details`](user_stories/us-15.5.md) |
| Epic 15: Flashcards & Persistent Spaced Repetition (E12) | `US-15.6` - Конвертировать quiz-результат в flashcard-колоду | `P2` | `closed` | `epoch-tour-scenarios-10-14` | [`details`](user_stories/us-15.6.md) |
| Epic 16: Course Workspace - Fast Learning Mode | `US-16.0` - Активировать папку как курс | `P1` | `closed` | `localhost-balance-course-delight-v1` | [`details`](user_stories/us-16.0.md) |
| Epic 16: Course Workspace — Fast Learning Mode | `US-16.1` - Активировать курс в Topics | `P0` | `closed` | `epoch-tour-scenarios-10-14` | [`details`](user_stories/us-16.1.md) |
| Epic 16: Course Workspace — Fast Learning Mode | `US-16.2` - Запросы автоматически фокусируются на курсе | `P0` | `closed` | `epoch-tour-scenarios-10-14` | [`details`](user_stories/us-16.2.md) |
| Epic 16: Course Workspace — Fast Learning Mode | `US-16.3` - Получить план изучения курса | `P0` | `closed` | `epoch-tour-scenarios-10-14` | [`details`](user_stories/us-16.3.md) |
| Epic 16: Course Workspace — Fast Learning Mode | `US-16.4` - Сгенерировать flashcards для курса | `P0` | `closed` | `epoch-tour-scenarios-10-14` | [`details`](user_stories/us-16.4.md) |
| Epic 16: Course Workspace — Fast Learning Mode | `US-16.5` - Перейти от сложной карточки к тьютору | `P1` | `closed` | `epoch-tour-scenarios-10-14` | [`details`](user_stories/us-16.5.md) |
| Epic 16: Course Workspace — Fast Learning Mode | `US-16.6` - Видеть прогресс по курсу в Dashboard | `P1` | `closed` | `epoch-tour-scenarios-10-14` | [`details`](user_stories/us-16.6.md) |
| Epic 16: Course Workspace — Fast Learning Mode | `US-16.7` - Добавить домашнее задание к теме/курсу и сгенерировать пошаговую инструкцию (LLM) | `P1` | `closed` | `epoch-e31-course-homework-playbook-ladder` | [`details`](user_stories/us-16.7.md) |
| Epic 17: Course Learning Mode v2 — Immersive Fast Track | `US-17.1` - US-17.1 | `P0` | `closed` | `epoch-e30-c1-diagnostic` | [`details`](user_stories/us-17.1.md) |
| Epic 17: Course Learning Mode v2 — Immersive Fast Track | `US-17.10` - US-17.10 | `P2` | `closed` | `epoch-course-retention-polish` | [`details`](user_stories/us-17.10.md) |
| Epic 17: Course Learning Mode v2 — Immersive Fast Track | `US-17.11` - US-17.11 | `P2` | `closed` | `epoch-course-confidence-dip-detector` | [`details`](user_stories/us-17.11.md) |
| Epic 17: Course Learning Mode v2 — Immersive Fast Track | `US-17.13` - US-17.13 | `P2` | `closed` | `epoch-course-next-session-promise` | [`details`](user_stories/us-17.13.md) |
| Epic 17: Course Learning Mode v2 — Immersive Fast Track | `US-17.2` - US-17.2 | `P0` | `closed` | `epoch-e30-a1-cockpit-scaffold` | [`details`](user_stories/us-17.2.md) |
| Epic 17: Course Learning Mode v2 — Immersive Fast Track | `US-17.3` - US-17.3 | `P1` | `closed` | `epoch-e30-c2-pace-engine` | [`details`](user_stories/us-17.3.md) |
| Epic 17: Course Learning Mode v2 — Immersive Fast Track | `US-17.4` - US-17.4 | `P0` | `closed` | `epoch-e30-a2-cockpit-rotator` | [`details`](user_stories/us-17.4.md) |
| Epic 17: Course Learning Mode v2 — Immersive Fast Track | `US-17.5` - US-17.5 | `P1` | `closed` | `epoch-e30-b1-graduation-overlay` | [`details`](user_stories/us-17.5.md) |
| Epic 17: Course Learning Mode v2 — Immersive Fast Track | `US-17.6` - US-17.6 | `P1` | `closed` | `epoch-e30-b2-daily-briefing` | [`details`](user_stories/us-17.6.md) |
| Epic 17: Course Learning Mode v2 — Immersive Fast Track | `US-17.7` - US-17.7 | `P2` | `closed` | `epoch-e30-d2-focus-mode` | [`details`](user_stories/us-17.7.md) |
| Epic 17: Course Learning Mode v2 — Immersive Fast Track | `US-17.8` - US-17.8 | `P0` | `closed` | `epoch-course-retention-polish` | [`details`](user_stories/us-17.8.md) |
| Epic 17: Course Learning Mode v2 — Immersive Fast Track | `US-17.9` - US-17.9 | `P1` | `closed` | `epoch-e30-e1-course-graduation` | [`details`](user_stories/us-17.9.md) |
| Epic 18: Home mode selection — adaptive grid | `US-18.4` - Intent-aware порядок карточек режимов | `P2` | `closed` | `epoch-home-mode-intent-ordering` | [`details`](user_stories/us-18.4.md) |
| Epic 19: UX Breakthrough Wave | `US-19.1` - Wait UX Improvements | `P1` | `closed` | `ux-first-answer-wait-flow` | [`details`](user_stories/us-19.1.md) |
| Epic 19: UX Breakthrough Wave | `US-19.2` - Seamless Tutor Handoff | `P0` | `closed` | `epoch-us19-2-tutor-handoff-ux` | [`details`](user_stories/us-19.2.md) |
| Epic 19: UX Breakthrough Wave | `US-19.3` - Celebration UX | `P1` | `closed` | `ux-mastery-celebration-analytics` | [`details`](user_stories/us-19.3.md) |
| Epic 19: UX Breakthrough Wave | `US-19.4` - Flashcard Session Analytics | `P1` | `closed` | `ux-mastery-celebration-analytics` | [`details`](user_stories/us-19.4.md) |
| Epic 19: UX Breakthrough Wave | `US-19.5` - Home Hub Visual Hierarchy | `P2` | `closed` | `ux-home-hub-navigation-polish` | [`details`](user_stories/us-19.5.md) |
| Epic 20: Smart Study Router | `US-20.1` - Получить объяснимую подсказку следующего учебного шага | `P0` | `closed` | `epoch-ssr-concept-recovery-ladder-v2` | [`details`](user_stories/us-20.1.md) |
| Epic 20: Smart Study Router | `US-20.10` - Learner Steering Toggles | `P1` | `closed` | `ssr-misroute-feedback-collection` | [`details`](user_stories/us-20.10.md) |
| Epic 20: Smart Study Router | `US-20.11` - Micro-Outcome Receipt | `P1` | `closed` | `kg-completeness-audit` | [`details`](user_stories/us-20.11.md) |
| Epic 20: Smart Study Router | `US-20.12` - Quiet Mode Route | `P1` | `closed` | `epoch-ssr-next-quiet-mode` | [`details`](user_stories/us-20.12.md) |
| Epic 20: Smart Study Router | `US-20.13` - Local Route Simulator (what-if preview) | `P1` | `closed` | `epoch-ssr-local-route-simulator-v1` | [`details`](user_stories/us-20.13.md) |
| Epic 20: Smart Study Router | `US-20.17` - Tiered Explanation Gate | `P0` | `closed` | `ssr-l2-tiered-explanation-gate-v1` | [`details`](user_stories/us-20.17.md) |
| Epic 20: Smart Study Router | `US-20.2` - Explainable Next Step Card | `P0` | `closed` | `ssr-l2-tiered-explanation-gate-v1` | [`details`](user_stories/us-20.2.md) |
| Epic 20: Smart Study Router | `US-20.3` - Due-review priority | `P0` | `closed` | `epoch-smart-study-router-core-policies` | [`details`](user_stories/us-20.3.md) |
| Epic 20: Smart Study Router | `US-20.4` - Weak-concept recovery route | `P0` | `closed` | `epoch-smart-study-router-core-policies` | [`details`](user_stories/us-20.4.md) |
| Epic 20: Smart Study Router | `US-20.5` - Post-answer learning runway | `P0` | `closed` | `epoch-smart-study-router-core-policies` | [`details`](user_stories/us-20.5.md) |
| Epic 20: Smart Study Router | `US-20.6` - Accessible router and preserved entry points | `P1` | `closed` | `epoch-smart-study-router-accessibility-harness` | [`details`](user_stories/us-20.6.md) |
| Epic 20: Smart Study Router | `US-20.7` - Contrastive Router Explanation | `P0` | `closed` | `ssr-l2-reliability-v1` | [`details`](user_stories/us-20.7.md) |
| Epic 20: Smart Study Router | `US-20.8` - Local Route Confidence Ledger | `P0` | `closed` | `ssr-ai-vision-level2-level3-readiness-gate` | [`details`](user_stories/us-20.8.md) |
| Epic 20: Smart Study Router | `US-20.9` - Learning Debt Queue | `P0` | `closed` | `ssr-ai-vision-level2-level3-readiness-gate` | [`details`](user_stories/us-20.9.md) |

## Связи

| Epic | CJM stage | Owning modules |
|---|---|---|
| 1 Discover & Install | Discover, Onboard | `README.md`, `doc/`, `.env.example`, `app/ui/offline_banner.py` |
| 2 Ingest | Onboard | `ingest.py`, `app/ingestion.py`, `app/index_lifecycle.py` |
| 3 First Answer | First Answer | `app/query_service.py`, `app/retrieval.py`, `app/routers/query.py`, `app/ui/query_tab.py` |
| 4 Switch to Tutor | Learn | `app/ui/main.py`, `app/tutor_orchestrator.py`, `app/pipeline_steps.py` |
| 5 Micro-quiz | Learn | `app/quiz_service.py`, `app/ui/quiz_panel.py`, `app/ui/scoped_quiz.py` |
| 6 Adaptive Plan | Learn | `app/adaptive_plan.py`, `app/learner_model_service.py`, `app/ui/adaptive_plan_card.py` |
| 7 Spaced Repetition | Retain | `app/spaced_repetition.py`, `app/user_state.py`, `app/ui/resume_cards.py` |
| 8 Reindex Resilience | Retain | `app/learner_model_service.py`, `app/index_lifecycle.py`, `app/user_state.py` |
| 9 Progress | Master | `app/ui/dashboards.py`, `app/ui/progress_visuals.py`, `app/user_state.py`, `app/gamification_service.py`, `app/adaptive_plan.py`, `app/knowledge_graph.py` |
| 10 Export / Sync | Master | `app/user_state.py`, `app/routers/sync.py` |
| 11 Trust | First Answer / Trust | `app/graph_retrieval.py`, `app/ui/source_cards.py`, `app/ui/debug_panel.py` |
| 12 Quality Infrastructure | Cross-cutting | `app/eval_service.py`, `scripts/run_quality_benchmark.py`, `scripts/run_router_eval.py`, `app/router_eval.py`, `eval_data/tutor_regression.json`, `tests/test_integration_retrieval.py`, `tests/test_router_eval.py`, `tests/e2e/`, `playwright.config.ts` |
| 13 Adaptive Quiz | Learn / Micro-quiz | `app/quiz_adaptive.py`, `app/quiz_service.py` |
| 14 Guided Start + Expert Controls | First Answer / Resume / Progress / Trust | `app/ui/resume_cards.py`, `app/ui/sidebar.py`, `app/ui/query_tab.py`, `app/ui/debug_panel.py`, `app/learning_plan_service.py`, `app/ui/dashboards.py` |
| 15 Flashcards + Persistent SRS | Flashcards Gen / Flashcards Review / Retain / Master | `app/ui/flashcards_ui.py`, `app/flashcard_service.py`, `app/routers/flashcards.py`, `app/user_state.py`, `app/spaced_repetition.py`, `app/ui/resume_cards.py`, `app/ui/interactive_quiz.py` |
| 16 Course Workspace - Fast Learning Mode | Course Workspace | `app/ui/course_workspace.py`, `app/study_scope.py`, `app/course_store.py`, `app/ui/flashcards_ui.py` |
| E13 Home Mode Selector / UX Tail | Discover / First Answer / Learn / Retain / Progress | `app/ui/home_hub.py`, `app/ui/main.py`, `app/ui_theme.css`, `app/ui/resume_cards.py`, `app/ui/interactive_quiz.py`, `app/ui/dashboards.py`, `app/ui/flashcards_ui.py` |
| 20 [Smart Study Router](smart_study_router.md) | Learn / Retain / Cross-loop | `app/ui/adaptive_plan_card.py`, `app/ui/tutor_chat_render.py`, `app/ui/resume_cards.py`, `app/user_state_core.py`, `app/orchestrator_router.py` |

---

_Производный документ от `doc/cjm.md`. Полные Given/When/Then acceptance criteria лежат по одной US в `doc/user_stories/`. Обновлять синхронно при изменении CJM или добавлении нового surface'а. Формулировки P0/P1/P2 — рабочая приоритизация, не обязательство по горизонтам._
