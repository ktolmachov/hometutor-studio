# E2E Test Guide

## Profiles

- `smoke`: быстрые офлайн-сценарии для PR и локальной проверки.
- `nightly`: более дорогие сценарии, зависящие от live tutor/Q&A.
- `nightly-strict`: строгий nightly без auto-skip инфраструктурных оговорок (для полностью подготовленного стенда); есть fail-fast preflight на `OPENAI_API_KEY`.
- `demo`: снимает PNG-кадры для документации. Читает YAML-манифесты из `doc/scenarios/`, пишет кадры в `doc/screenshots/<RUN>/<scenario_id>/`, фиксирует `meta.json`. Не влияет на smoke/nightly.

## Commands

```bash
npm run test:e2e:smoke
```

```bash
npm run test:e2e:nightly
```

```bash
npm run test:e2e:nightly:strict
```

```bash
npm run test:e2e
```

```bash
npm run test:e2e:demo            # прогнать только demo-сценарии
npm run demo:build               # демо + сборка doc/quickstart_demo.md одной командой
npm run demo:clean               # final/, quickstart_demo.md, dist (не удаляет doc/screenshots/<RUN>/)
```

## Demo screenshots pipeline

Архитектура в двух словах:

```
doc/scenarios/*.yaml  ──►  tests/e2e/demos/*.spec.ts  ──►  doc/screenshots/<id>/
                                       │
                                       └──►  scripts/generate_demo_doc.py
                                                      │
                                                      └──►  doc/quickstart_demo.md
```

- **Источник правды** — YAML-манифест сценария. В нём shots (slug+caption+narration), persona, wow-момент, takeaway. Структуру см. в [doc/scenarios/README.md](../../doc/scenarios/README.md).
- **Тест** использует фикстуру `createDemoRecorder(page, 'scenario_XX')` из [fixtures/demo_recorder.ts](fixtures/demo_recorder.ts). Кадры пишутся в `doc/screenshots/<RUN>/<scenario_id>/`, где `RUN` по умолчанию — `YYYY-MM-DD` (локальная дата); переопределение: `DEMO_SHOT_RUN` в том же формате. Каждый `demo.shot(slug, { caption, narration })` кладёт PNG и дописывает `meta.json`.
- **Генератор документа** — `python scripts/generate_demo_doc.py` — собирает YAML + screenshots в красивый markdown.
- **Offline-first.** Все существующие demo-тесты работают без `OPENAI_API_KEY` (используют `HOME_RAG_E2E_OFFLINE=1`, который уже выставляется `scripts/e2e_run_stack.mjs`). Кадры с реальным ответом LLM помечены условием и пропускаются при отсутствии ключа.

## Ports

When Playwright starts the stack itself, the default ports are:

- FastAPI: `127.0.0.1:18000`
- Streamlit: `127.0.0.1:18501`

Override with `E2E_API_PORT` / `E2E_STREAMLIT_PORT` when a local run needs specific ports. Manual app defaults can still use `8000` / `8501`; smoke avoids those so an already-running dev server does not mask harness failures.

The stack also exports `UI_API_BASE_URL` and augments `CORS_ORIGINS` for those ports so Streamlit and browser-side `fetch()` calls target the same isolated FastAPI instance.

## E2E Query Hooks

- `e2e_restore_preview=1` preloads a valid empty sync bundle preview so backup/restore UI gating can be tested without relying on browser file-upload plumbing.

## Course Workspace smoke

Новые course-scope сценарии помечены `@smoke`, поэтому автоматически входят в `npm run test:e2e:smoke`:

- `course_scope_activation.spec.ts` — API принимает валидный `scope=course` payload.
- `course_scope_query_filter.spec.ts` — generated cards содержат `folder:<folder_rel>` tag.
- `course_scope_deactivation.spec.ts` — без `folder_rel` folder-tag не добавляется.
- `flashcards_course_generation.spec.ts` — generate(scope=course) → save deck → due filter.

## Epoch: learning-route-continuity (2026-04-17)

Добавлены **9 e2e-тестов** для покрытия всех 13 моментов истины CJM и **6 переходов** (CJM §6):

### @nightly (5 тестов, 7 кейсов)

| Файл | Момент | Что проверяет |
|---|---|---|
| `learning_route_continuity.spec.ts` | #2–4, §6 | North Star: answer→trust(sources)→tutor(context)→quiz→progress(Δmastery) |
| `tutor_context_preservation.spec.ts` | #3 | Concepts/sources из Q&A reально в tutor UI |
| `quiz_error_recovery.spec.ts` | #4 | Неверный ответ → hint/next_step, не dead end |
| `resume_next_day.spec.ts` | #5 | Snapshot сохранён; reload → resume card + контекст |
| `concept_graduation.spec.ts` | #9 | Graduated концепты исключены из gap-блока |

### @smoke (9 тестов, 10+ кейсов)

| Файл | Момент | Что проверяет |
|---|---|---|
| `reindex_profile_preservation.spec.ts` | #6 | POST /reindex → mastery XP/vector не обнулены |
| `srs_soft_recovery.spec.ts` | #7 | Overdue queue ≤ keep_limit; идемпотентность |
| `flashcard_session_summary.spec.ts` | #12 | End-of-session summary со stats + next_review |
| `progress_next_action.spec.ts` | #8 | Progress tab: CTA следующего шага (не просто метрики) |
| `course_scope_activation.spec.ts` | Course Workspace | `scope=course` валидируется и принимает `source_paths` |
| `course_scope_query_filter.spec.ts` | Course Workspace | Карточки курса получают `folder:<folder_rel>` tag |
| `course_scope_deactivation.spec.ts` | Course Workspace | При отсутствии `folder_rel` folder-tag не проставляется |
| `flashcards_course_generation.spec.ts` | Course Workspace | Полный API поток: generate → save deck → due filter |
| `course_progress_panel.spec.ts` | Course Workspace | Active course deck → Progress tab course panel with `course_workspace` metrics label |
| `unified_context_block.spec.ts` | #3, #8 | QA→Tutor→Home→Progress: виден блок «Текущий учебный контекст» + строки «Почему сейчас»/«Следующий шаг» |

**DoD:** все 12 кейсов зелёные; тест #1 — сквозной acceptance-тест маршрута.

## Epoch: KG 3D Memory Run (2026-07-17)

Новые e2e-сценарии после реализации разборов №15/#17/#18:

| Файл | Профиль | Что проверяет |
|---|---|---|
| `kg_3d_memory_run_smoke.spec.ts` | `@smoke` | Embedded 3D-зал рендерит Memory Run UI: route-first кадр, topbar/sidebar, canvas не пустой, есть CTA |
| `kg_3d_actions_flow.spec.ts` | `@smoke` | G0/G1: `collect` обновляет инвентарь/конспект, `start` ведёт в учебную поверхность |
| `kg_3d_memory_overlay.spec.ts` | `@smoke` | G2: quiz-progress виден как dated memory trace; ✓ не затирает номер остановки |
| `kg_3d_export_inert.spec.ts` | `@smoke` | 3D export self-contained/read-only: без live action bridge и без `obsidian://` |
| `tutor_answer_save_to_flashcard.spec.ts` | `@smoke` | Ответ тьютора можно сохранить в колоду «Из ответов тьютора» |
| `agent_one_button_gate.spec.ts` | `@smoke` | `query_mode:"agent"` не роняет API; Agent tile скрыт gate-ом или открывает surface |
| `appearance_theme_persistence.spec.ts` | `@smoke` | Мир оформления сохраняется после reload |
| `audio_podcast_playlist.spec.ts` | `@smoke` | При наличии локальных audio-артефактов виден плейлист/скачивание |
| `due_badge_sum.spec.ts` | `@smoke` | Home due badge показывает «К повторению: N» без обещания единой очереди |

Demo-витрина дополнена:

| ID | Что покрывает |
|---|---|
| `scenario_39` | Memory Run: 3D-зал маршрута дня |
| `scenario_40` | 3D-зал → Живой конспект: collect/action bridge |
| `scenario_41` | 3D-зал: вчерашний след quiz-прогресса |

## Current Rules

- `@smoke` должен оставаться стабильным без live LLM.
- `@nightly` допускает зависимость от `OPENAI_API_KEY`.
- Если сценарий не воспроизводим в текущем e2e harness, его нужно помечать `fixme` с явной причиной.
- **New:** тесты переходов (learning_route_continuity и др.) фокусируются на **качестве маршрута**, не на отдельных поверхностях.

## OPENAI_API_KEY

Для live-сценариев нужен `OPENAI_API_KEY`.

Сейчас от ключа зависят:

- `qa_to_tutor_loop.spec.ts`
- `unified_context_block.spec.ts`
- `tutor_microquiz_flow.spec.ts`
- `long_learning_continuity.spec.ts` (existing North Star)
- **Новое (epoch-learning-route-continuity):**
  - `learning_route_continuity.spec.ts` — CJM §6 маршрут (answer→trust→tutor→quiz→progress delta)
  - `tutor_context_preservation.spec.ts` — перенос концептов из Q&A в tutor
  - `quiz_error_recovery.spec.ts` — неверный ответ → hint/next step
  - `resume_next_day.spec.ts` — сохранение snapshot и resume card на reload
  - `concept_graduation.spec.ts` — graduated концепты исключены из gap

Без ключа эти тесты корректно `skip`, а не падают.

Для `nightly-strict` это правило не действует: прогон завершится до старта тестов с явной ошибкой preflight, если `OPENAI_API_KEY` не задан.

## `HOME_RAG_E2E_OFFLINE`

Скрипт `scripts/e2e_run_stack.mjs` (webServer в Playwright) выставляет **`HOME_RAG_E2E_OFFLINE=1`** для изолированного PR-smoke.

Эффект:

- **`POST /flashcards/generate`** в `app/flashcard_service.py` не вызывает LLM: возвращаются детерминированные карточки из текста загрузки (достаточно для `flashcards_review_flow.spec.ts` без ключа).
- Обычный запуск приложения этой переменной не трогает — только если задать вручную (см. `.env.example`).

Юнит-покрытие: `tests/test_flashcard_service.py::test_generate_flashcards_e2e_offline_stub_skips_llm`.

## Flashcards smoke (селекторы и query)

- Файл для загрузки в колоды: **не** первый `input[type=file]` на странице — в сайдбаре есть JSON uploader для backup. Используйте dropzone по подписи «Загрузи файл (PDF, TXT, MD, DOCX)» и `input` внутри неё, либо кнопки/`stMain` как в `flashcards_review_flow.spec.ts`.
- В URL **не закрепляйте** `e2e_fc_section=create` на весь сценарий с сохранением колоды: в `app/ui/main.py` при каждом rerun query снова выставляет секцию из `e2e_fc_section` и отменит переход на «Колоды» после `st.rerun()`. Для сценария «создать → сохранить» достаточно `e2e_view=flashcards` + при необходимости `e2e_fc_source=upload` и переход кнопкой «Создать».

## CJM Moments of Truth Coverage

Все 13 критических моментов (doc/cjm.md §5) имеют покрытие:

1. Первый запуск Streamlit — ✅ onboarding во всех
2. Первый ответ (relevant + sources < 5s) — ✅ learning_route_continuity
3. Переход в tutor (контекст) — ✅ tutor_context_preservation
4. Первый micro-quiz — ✅ learning_route_continuity
5. Возврат на день 2 (resume card) — ✅ resume_next_day
6. После reindex (профиль) — ✅ reindex_profile_preservation
7. Spaced repetition due — ✅ srs_soft_recovery (API) + existing guided_start (UI)
8. Progress check — ✅ progress_next_action
9. Concept graduation — ✅ concept_graduation
10. Guided start — ✅ existing guided_start.spec.ts
11. Flashcard generation (preview) — ✅ existing flashcards_review_flow.spec.ts
12. Flashcard session summary — ✅ flashcard_session_summary
13. Mission Control home — ✅ existing mission_control.spec.ts

## Current Fixme Cases

- `onboarding_persistence.spec.ts`
  - Полный first-run onboarding сейчас не воспроизводится, потому что `scripts/e2e_run_stack.mjs` заранее проставляет `onboarding_v1_done=1`.

## Recommended Policy

- В `smoke` держать только сценарии, которые проходят без внешних ключей и ручной подготовки.
- В `nightly` выносить tutor/Q&A и другие live user flows.
- `nightly-strict` использовать как жёсткий gate только когда окружение стабильно: корректный `OPENAI_API_KEY`, согласованная размерность embeddings и готовый индекс.
- В `demo` добавлять сценарии только после того, как они закрыты YAML-манифестом и протестированы локально. Если сценарий требует LLM — оформить условный блок, чтобы offline-прогон не падал.
- При починке harness сначала снимать `fixme`, потом переводить сценарий в обязательный прогон.

## Demo scenarios currently shipped

| ID | Файл | Offline-ok | Манифест | Что покрывает |
|---|---|:---:|---|---|
| `scenario_01` | [demos/scenario_01_first_answer.spec.ts](demos/scenario_01_first_answer.spec.ts) | частично (live LLM для кадров 03–05) | [scenario_01_first_answer.yaml](../../doc/scenarios/scenario_01_first_answer.yaml) | — |
| `scenario_02` | [demos/scenario_02_home_navigation.spec.ts](demos/scenario_02_home_navigation.spec.ts) | ✅ | [scenario_02_home_navigation.yaml](../../doc/scenarios/scenario_02_home_navigation.yaml) | — |
| `scenario_05` | [demos/scenario_05_flashcards_create.spec.ts](demos/scenario_05_flashcards_create.spec.ts) | ✅ (HOME_RAG_E2E_OFFLINE=1) | [scenario_05_flashcards_create.yaml](../../doc/scenarios/scenario_05_flashcards_create.yaml) | — |
| `scenario_10` | [demos/scenario_10_day2_resume.spec.ts](demos/scenario_10_day2_resume.spec.ts) | ✅ | [scenario_10_day2_resume.yaml](../../doc/scenarios/scenario_10_day2_resume.yaml) | — |
| `scenario_11` | [demos/scenario_11_anki_export.spec.ts](demos/scenario_11_anki_export.spec.ts) | ✅ | [scenario_11_anki_export.yaml](../../doc/scenarios/scenario_11_anki_export.yaml) | — |
| `scenario_12` | [demos/scenario_12_quiz_to_deck.spec.ts](demos/scenario_12_quiz_to_deck.spec.ts) | ✅ | [scenario_12_quiz_to_deck.yaml](../../doc/scenarios/scenario_12_quiz_to_deck.yaml) | — |
| `scenario_13` | [demos/scenario_13_course_workspace.spec.ts](demos/scenario_13_course_workspace.spec.ts) | ✅ | [scenario_13_course_workspace.yaml](../../doc/scenarios/scenario_13_course_workspace.yaml) | — |
| `scenario_14` | [demos/scenario_14_full_sync.spec.ts](demos/scenario_14_full_sync.spec.ts) | ✅ | [scenario_14_full_sync.yaml](../../doc/scenarios/scenario_14_full_sync.yaml) | — |
| `scenario_16` | [demos/scenario_16_interactive_tour.spec.ts](demos/scenario_16_interactive_tour.spec.ts) | ✅ | [scenario_16_interactive_tour.yaml](../../doc/scenarios/scenario_16_interactive_tour.yaml) | **Тур:** глава 1 (шаги) → глава 2 → reload и resume прогресса тура |
| `scenario_17` | [demos/scenario_17_plan_diff.spec.ts](demos/scenario_17_plan_diff.spec.ts) | ✅ | [scenario_17_plan_diff.yaml](../../doc/scenarios/scenario_17_plan_diff.yaml) | **Diff плана:** детерминированный KV → раскрытие «Что изменилось в плане» (добавлено/убрано) |
| `scenario_18` | [demos/scenario_18_home_retention_hub.spec.ts](demos/scenario_18_home_retention_hub.spec.ts) | ✅ | [scenario_18_home_retention_hub.yaml](../../doc/scenarios/scenario_18_home_retention_hub.yaml) | **Home hub:** 6 режимов → Flashcards → Progress → возврат на Home |
| `scenario_19` | [demos/scenario_19_env_validation.spec.ts](demos/scenario_19_env_validation.spec.ts) | ✅ | [scenario_19_env_validation.yaml](../../doc/scenarios/scenario_19_env_validation.yaml) | **Env / сайдбар:** основной UI + сайдбар (контекст ключей и провайдера) |
| `scenario_39` | [demos/scenario_39_memory_run_3d.spec.ts](demos/scenario_39_memory_run_3d.spec.ts) | ✅ | [scenario_39_memory_run_3d.yaml](../../doc/scenarios/scenario_39_memory_run_3d.yaml) | **Memory Run:** embedded 3D-зал маршрута дня |
| `scenario_40` | [demos/scenario_40_kg3d_collect_to_konspekt.spec.ts](demos/scenario_40_kg3d_collect_to_konspekt.spec.ts) | ✅ | [scenario_40_kg3d_collect_to_konspekt.yaml](../../doc/scenarios/scenario_40_kg3d_collect_to_konspekt.yaml) | **3D → конспект:** collect/action bridge |
| `scenario_41` | [demos/scenario_41_kg3d_yesterday_trace.spec.ts](demos/scenario_41_kg3d_yesterday_trace.spec.ts) | ✅ | [scenario_41_kg3d_yesterday_trace.yaml](../../doc/scenarios/scenario_41_kg3d_yesterday_trace.yaml) | **3D память:** quiz trace + дата снимка |

Быстрый прогон сценариев 10–14:

```bash
# PowerShell
powershell -NoProfile -Command "$env:DEMO_SHOT_RUN=(Get-Date -Format 'yyyy-MM-dd'); npm run test:e2e:demo -- --grep '@demo Scenario (10|11|12|13|14)'"
```

Добавление нового сценария: [doc/scenarios/README.md § Добавление нового сценария](../../doc/scenarios/README.md#добавление-нового-сценария).
