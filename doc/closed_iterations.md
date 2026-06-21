# Закрытые Итерации

Актуализировано по `doc/backlog_registry.yaml` на **2026-06-11**.

Этот файл — индекс закрытых итераций. Полная история организована по эпохам в папке [`doc/epochs/`](epochs/).

Источник правды по backlog, owner'ам и статусам пакетов — `doc/backlog_registry.yaml`.
`doc/tasklist.md` является производным weekly view и не должен использоваться
как мастер-источник при проверке закрытых итераций.

---

## Как использовать для Planning Prompt

Вместо чтения всего этого файла (~16k токенов по `scripts/check_readset.py`), в Planning Prompt используйте только файл целевой эпохи:

```text
Read ONLY (do not read other files):
1. doc/backlog_registry.yaml — запись целевого package/epoch только через grep/section read
2. doc/epochs/<target-epoch>.md — если нужен контекст закрытых итераций той же эпохи
3. doc/user_stories/<US-N>.md — acceptance criteria only
```

Пример: для E15 читайте `doc/epochs/e15.md` (~100 строк, 400 токенов) вместо полного `closed_iterations.md`.

---

## Индекс Эпох

| Эпоха | Дата | Фокус |
|---|---|---|
| [E29](epochs/e29.md) | 2026-04-13 | Quiz service boundary |
| [E28](epochs/e28.md) | 2026-04-13 | Reindex profile badge |
| [E27](epochs/e27.md) | 2026-04-13 | Discoverability |
| [E26](epochs/e26.md) | 2026-04-13 | Flashcards soft-recovery |
| [E24](epochs/e24.md) | 2026-04-13 | Learner goal contract |
| [E16](epochs/e16.md) | 2026-04-12 | Flashcards session summary |
| [E15](epochs/e15.md) | 2026-04-12 | Flashcards progress + filters |
| [E14](epochs/e14.md) | 2026-04-12 | Tutor transparency + arch hardening |
| [E13](epochs/e13.md) | 2026-04-12 | Home mode selector |
| [E12](epochs/e12.md) | 2026-04-11 | Flashcards + SRS |
| [E11](epochs/e11.md) | 2026-04-11 | 5-min loop + router repair |
| [E10](epochs/e10.md) | 2026-04-11 | Adaptive quiz + eval |
| [E9](epochs/e9.md) | 2026-04-10 | Continuity & learning loop |
| [E8](epochs/e8.md) | 2026-04-10 | User value delivery discipline |
| [E7](epochs/e7.md) | 2026-04-09 | Production health gates |
| [E6](epochs/e6.md) | 2026-04-08 | Personalization agent split A/B/C |
| [E5](epochs/e5.md) | 2026-04-08 | Learner state migration |
| [E4](epochs/e4.md) | 2026-04-07 | Graph compare profiles |

## Недавние инженерные задачи (не эпохи)

| Задача | Дата | Тип |
|---|---|---|
| `workflow-dx-p1-quick-wins` | 2026-05-02 | Workflow DX wave |
| `workflow-dx-p2-team-workflow-cleanup` | 2026-05-02 | Workflow DX wave |
| `workflow-dx-p3-smart-router` | 2026-05-02 | Workflow DX wave |
| `workflow-dx-p5-explain-exit` | 2026-05-02 | Workflow DX wave |
| `epoch-arch-review-p1-trivial-fixes` | 2026-05-02 | Arch review remediation P1 |
| epoch-inline-citations-first-answer | 2026-04-22 | First Answer trust |
| epoch-17-1-ux-tail | 2026-04-20 | UX polish + loop closure |
| epoch-unified-context-layer | 2026-04-20 | Continuity UX |
| epoch-qa-tutor-handoff | 2026-04-20 | QA→Tutor continuity |
| epoch-answer-quality-eval | 2026-04-20 | Eval gate |
| epoch-agent-workflow-split | 2026-04-20 | Decomposition (docs) |
| epoch-answer-quality-eval contract prerequisite | 2026-04-19 | Contract test |
| AQE-R remediation | 2026-04-19 | Remediation |
| agent-workflow-token-p3 (P3.0–P3.4) | 2026-04-19 | Token optimization |
| [ingest-acceleration](epochs/ingest_acceleration.md) | 2026-04-19 | Optimization |
| [epoch-local-cors-defaults](epochs/epoch_local_cors_defaults.md) | 2026-04-18 | Hardening |
| [epoch-ui-refactoring](epochs/epoch_ui_refactoring.md) | 2026-04-17 | Refactoring |
| [epoch-metrics-decomposition](epochs/epoch_metrics_decomposition.md) | 2026-04-17 | Decomposition |
| [epoch-learning-route-continuity](epochs/epoch_learning_route_continuity.md) | 2026-04-17 | E2E tests |
| [ops-stability-hybrid-embeddings](epochs/ops_stability_hybrid_embeddings.md) | 2026-04-16 | Stability |
| [epoch-query-service-decomposition](epochs/epoch_query_service_decomposition.md) | 2026-04-16 | Decomposition |
| [epoch-adr-010-acceptance](epochs/epoch_adr_.md) | 2026-04-16 | Documentation |
| [epoch-local-store-contracts](epochs/epoch_local_store_contracts.md) | 2026-04-13 | Documentation |
| [epoch-exception-hygiene](epochs/epoch_exception_hygiene.md) | 2026-04-13 | Audit |

### — Autonomous control-plane Wave 2 — 2026-04-29

- Goal: formalize the merged Wave 2 control-plane continuation from `doc/next/autonomous_delivery_control_plane_final.md`.
- Delivered: `epoch-failure-classifier`, `epoch-quality-gates-matrix`, `epoch-prompt-routing-registry`, `epoch-thin-current-task`, `epoch-skills-jit-router`, `epoch-nonstop-wave-policy`, `epoch-agent-evals-layer`, `epoch-adversarial-eval-harness`, `epoch-hitl-approval-protocol`, `epoch-pipeline-concurrency-locks`, `epoch-autonomous-observability-dashboard`.
- Verification: `.\scripts\run_control_plane_regression.ps1` green; report in `archive/team_artifacts/_regression/`.
- Deferred follow-up: full app-level `npm run test:e2e:smoke` currently has unrelated failures outside the control-plane write-set; run explicitly with `-AppSmokeE2E` when investigating app smoke.

### epoch-answer-quality-eval — 2026-04-20

- Goal: protect the First Answer trust moment with a CI-visible `/ask` answer-quality gate.
- Delivered: 20-case golden dataset contract, mock/live eval runner shape, fixed thresholds/baseline, CI gate, nightly report artifact path, and structured failure fields by component.
- Verification: sp1 PASS, sp2 CONDITIONAL PASS accepted; final DoD commands green.
- Deferred follow-up: none required; procedural sp2 condition recorded in `archive/team_artifacts/epoch-answer-quality-eval/deferred.md`.

### epoch-inline-citations-first-answer — 2026-04-22

- Goal: strengthen CJM #2 trust by adding inline citations directly in the first answer text.
- Delivered: citation markers are rendered inline and stay aligned with source cards without debug-noise exposure.
- Verification: package was closed operationally; source-of-truth details are tracked in `doc/backlog_registry.yaml` and package artifacts.

### epoch-5min-loop-polish — 2026-04-21

- Goal: make the 5-minute learner path feel like one deterministic route `answer → micro-quiz → feedback/explanation → next step`, without dead ends after completion.
- Delivered: deterministic next-step behavior for the short loop plus operational guardrails around the contract (`scripts/check_loop_metrics_gate.py`, local pre-push installer, smoke coverage hardening).
- Verification: targeted loop/continuity pytest bundles green; runtime gate and smoke guard added for ongoing protection.
- Verification commands: `python -m pytest tests/test_e11_learning_loop.py -v`, `python -m pytest tests/test_e9_7_continuity_bridge.py -v`, `npm run test:loop-gate`.
- Archive: planning prompt preserved in `archive/agent_prompts/epoch_5min_loop_polish_planning_prompt_2026-04-21.md`.

### epoch-us7-3-resume-card — 2026-04-21

- Goal: on day-2 return, show a deterministic resume card on the main entry surface so the learner immediately sees where they stopped and can continue in one click.
- Delivered: home hero resume card contract for `topic`, `last_action`, `due_count`, and a single primary CTA, plus guard coverage for stale/empty resume payloads and persistence roundtrip stability.
- Verification: focused UI and persistence DoD commands already green in the resume session; no code changes were needed during closure because the implementation was already complete.
- Verification commands: `python -m pytest tests/test_resume_cards.py -v`, `python -m pytest tests/test_user_state.py -v -k "resume"`.
- Archive: execution artefacts remain in `archive/agent_prompts/epoch_us7_3_resume_card_exec_prompt_2026-04-21.md` and `archive/team_artifacts/epoch-us7-3-resume-card/`.

### epoch-qa-tutor-handoff — 2026-04-20

- Goal: one-click handoff from Quick Answer to Tutor with preserved topic/question context (CJM MoT #3).
- Delivered: single QA primary CTA handoff, continuity payload persistence/consumption for Tutor startup, smoke selection tag for `qa_to_tutor_loop`.
- Verification: `pytest tests/test_e9_7_continuity_bridge.py -v` (13 passed), `pytest tests/test_query_tab_topic_infer.py -v` (4 passed), `npm run test:e2e:smoke -- tests/e2e/qa_to_tutor_loop.spec.ts` (1 skipped, exit 0).
- Deferred follow-up: none.

### epoch-unified-context-layer — 2026-04-20

- Goal: unify learning continuity context across Tutor/Home/Progress after QA handoff.
- Delivered: shared compact context block (`Текущий учебный контекст`) on key UI surfaces and consistent reason/next-step lines via continuity helper.
- Verification: `pytest tests/test_e9_7_continuity_bridge.py -v` (17 passed), `pytest tests/test_query_tab_topic_infer.py -v` (4 passed), `npm run test:e2e:smoke -- tests/e2e/qa_to_tutor_loop.spec.ts` (1 skipped, exit 0).
- Deferred follow-up: none.

### epoch-17-1-ux-tail — 2026-04-20

- Goal: finish UX-tail polish for guided entry and guarantee no dead-end in QA→Tutor 5-minute loop.
- Delivered:
  - sp1: deterministic single primary CTA + beginner-first continuity copy on Home/Progress.
  - sp2: QA-origin loop fallback in Tutor (`Продолжить 1 шаг` / `Готово на сегодня`) when quiz branch is unavailable.
- Verification: `python -m pytest tests/test_e9_7_continuity_bridge.py -q` (17 passed), `npx playwright test tests/e2e/qa_to_tutor_loop.spec.ts tests/e2e/unified_context_block.spec.ts --project=smoke` (2 skipped by env-policy, exit 0).
- Deferred follow-up: none.

### epoch-micro-quiz-feedback-tail — 2026-04-20

- Goal: remove the CJM #4 micro-quiz flow break by returning immediate, clear feedback and one next action after submit.
- Delivered:
  - sp1: stable submit feedback block in quiz UI with normalized status (`correct/partial/incorrect`), short learner-facing explanation, and one deterministic primary CTA.
  - sp2: contract/regression tests for partial branch, feedback normalization/sanitization, and status-to-CTA route mapping.
- Verification: `python -m pytest tests/test_learning_plan_micro_quiz.py tests/test_quiz_unified.py -v` (12 passed).
- Deferred follow-up: one process condition recorded in `archive/team_artifacts/epoch-micro-quiz-feedback-tail/deferred.md` (extra non-package files in shared commit range accepted by user).

### epoch-cjm-us-frontmatter — 2026-04-21

- Goal: Агент-планировщик читает несколько прозовых файлов вместо одного машинночитаемого реестра; US-файлы без статуса и CJM-якоря требуют догадок.
- Delivered: 1) Каждый US-файл имеет YAML frontmatter (`us_id`, `epic`, `priority`, `cjm_stage`, `status`, `covered_by`). 2) `doc/user_stories_index.json` создан и содержит все US. 3) `doc/cjm.md §8` оформлен как таблица `pain point → US → package_status`. 4) `doc/user_stories.md` имеет секцию `Open candidates` 
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -c "import json; json.load(open('doc/user_stories_index.json', encoding='utf-8'))"`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`, `.\.venv\Scripts\python.exe scripts/roadmap_sync_check.py`.
- Archive: `archive/agent_prompts/epoch_cjm_us_frontmatter_planning_prompt_2026-04-21.md`, `archive/team_artifacts/epoch-cjm-us-frontmatter/`.

### epoch-adaptive-plan-today — 2026-04-22

- Goal: после первой сессии learner не видит понятный следующий шаг и не переходит в устойчивый learning loop.
- Delivered: Home entry после хотя бы одного tutor-блока показывает `AdaptiveDailyPlan`; в плане видны блоки `review` / `gap` / `new` и мотивационное сообщение; у плана есть один понятный primary next step без пустых и сломанных состояний.
- Verification: DoD not run during closure.
- Verification commands: `python -m pytest tests/test_adaptive_plan_hub.py -v`, `python -m pytest tests/test_learning_plan_service.py -v`, `python -m pytest tests/test_adaptive_plan_history.py -v`.
- Archive: `archive/team_artifacts/epoch-adaptive-plan-today/`.

### epoch-srs-priority-queue — 2026-04-22

- Goal: список из `50+ overdue` без приоритизации ломает возвратный ритуал
- Delivered: Top-N due list ограничен `<= 7` элементами на home/tutor entry.
У очереди есть явная строка `ещё X отложено`.
Приоритет вычисляется детерминированно как `days_overdue × mastery_gap`.
Пустая или stale due-очередь не ломает resume surface.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_spaced_repetition.py tests/test_spaced_repetition_recovery.py -v
python -m pytest tests/test_resume_cards.py -v
python -m pytest tests/test_tutor_orchestrator.py -v -k "due_reviews"
Home/resume surface показывает top-N и overflow без dead-end`.
- Archive: `archive/agent_prompts/epoch_srs_priority_queue_planning_prompt_2026-04-22.md`, `archive/team_artifacts/epoch-srs-priority-queue/`.

### epoch-course-workspace-ab — 2026-04-20
- Goal: Course Workspace MVP: activate folder as course, focus queries to course scope.
- Delivered: US-16.0 (scope isolation), US-16.1 (focus queries), US-16.2 (course activation in Topics).
- Mode: execution.
- Verification: all DoD commands passed.
- Archive: *(backfilled 2026-04-22 — closed before registry was established)*

### epoch-course-workspace-d — 2026-04-20
- Goal: Course Workspace: generate flashcards from document, get course learning plan.
- Delivered: US-15.1 (flashcards preview), US-16.3 (course learning plan).
- Mode: execution.
- Verification: all DoD commands passed.
- Archive: *(backfilled 2026-04-22 — closed before registry was established)*

### epoch-course-workspace-e — 2026-04-20
- Goal: Course Workspace: review due flashcards by SM-2, generate flashcards for course.
- Delivered: US-15.2 (post-session summary), US-16.4 (course flashcards by SM-2).
- Mode: execution.
- Verification: all DoD commands passed.
- Archive: *(backfilled 2026-04-22 — closed before registry was established)*

### epoch-course-workspace-f — 2026-04-20
- Goal: Course Workspace: transition from hard card to tutor, course progress in dashboard.
- Delivered: US-16.5 (tutor transition), US-16.6 (course progress dashboard).
- Mode: execution.
- Verification: all DoD commands passed.
- Archive: *(backfilled 2026-04-22 — closed before registry was established)*

### epoch-quiz-hint-on-fail — 2026-04-22

- Goal: epoch-quiz-hint-on-fail
- Delivered: epoch-quiz-hint-on-fail
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_learning_plan_micro_quiz.py -v
python -m pytest tests/test_quiz_unified.py -v
python -m pytest tests/test_e11_learning_loop.py -v`.
- Archive: `archive/team_artifacts/epoch-quiz-hint-on-fail/`.

### epoch-reindex-mastery-guard — 2026-04-22

- Goal: epoch-reindex-mastery-guard
- Delivered: epoch-reindex-mastery-guard
- Verification: DoD not run during closure.
- Verification commands: (see contract).
- Archive: `archive/agent_prompts/epoch_reindex_mastery_guard_exec_prompt_quick_2026-04-22.md`, `archive/team_artifacts/epoch-reindex-mastery-guard/`.

### epoch-tutor-transparency — 2026-04-22

- Goal: Tutor surface показывает одну короткую reason-строку для выбранного действия explain/quiz/review.
Reason формируется из `policy_clamp_reasons`/`tutor_decision` и не раскрывает debug/internal поля.
При
- Delivered: Tutor surface показывает одну короткую reason-строку для выбранного действия explain/quiz/review.
Reason формируется из `policy_clamp_reasons`/`tutor_decision` и не раскрывает debug/internal поля.
При отсутствии reason UI не ломается и показывает безопасный fallback без пустых блоков.
Regression: су
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_tutor_orchestrator.py -v`, `python -m pytest tests/test_e9_7_continuity_bridge.py -v -k "tutor"`.
- Archive: `archive/agent_prompts/epoch_tutor_transparency_exec_prompt_quick_2026-04-22.md`.

### epoch-env-required-vars — 2026-04-22

- Goal: Первый запуск `streamlit run app/ui/main.py` не падает при отсутствующих обязательных env.
Пользователь видит offline-баннер с явным списком недостающих переменных и следующим действием.
Сообщение ост
- Delivered: Первый запуск `streamlit run app/ui/main.py` не падает при отсутствующих обязательных env.
Пользователь видит offline-баннер с явным списком недостающих переменных и следующим действием.
Сообщение остаётся user-facing (без traceback/debug шума) и не ломает рендер главного экрана.
Регрессии для offli
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_offline_banner.py -v`, `python -m pytest tests/test_main.py -v -k "env or offline"`.
- Archive: `archive/agent_prompts/epoch_env_required_vars_exec_prompt_quick_2026-04-22.md`, `archive/team_artifacts/epoch-env-required-vars/`.

### epoch-ingest-first-index-progress — 2026-04-22

- Goal: CLI первой индексации выводит стабильный прогресс: processed/total и текущий файл.
Для первой индексации показывается оценка ETA и throughput без отрицательных/пустых значений.
При отсутствии файлов в
- Delivered: CLI первой индексации выводит стабильный прогресс: processed/total и текущий файл.
Для первой индексации показывается оценка ETA и throughput без отрицательных/пустых значений.
При отсутствии файлов в `data/` пользователь получает явное сообщение о причине, без "зависания" процесса.
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_ingestion_progress.py -v`, `python -m pytest tests/test_ingestion_content_state.py -v`.
- Archive: `archive/agent_prompts/epoch_ingest_first_index_progress_exec_prompt_quick_2026-04-22.md`, `archive/team_artifacts/epoch-ingest-first-index-progress/`.

### epoch-truth-sync — 2026-04-22

- Goal: scripts/rebuild_user_stories_index.py` пересоздаёт `doc/user_stories_index.json` из `doc/backlog_registry.yaml` + frontmatter `doc/user_stories/*.md`; idempotent (`--check` режим без записи).
scripts/
- Delivered: scripts/rebuild_user_stories_index.py` пересоздаёт `doc/user_stories_index.json` из `doc/backlog_registry.yaml` + frontmatter `doc/user_stories/*.md`; idempotent (`--check` режим без записи).
scripts/regenerate_cjm_pain_table.py` пересоздаёт `open_candidates` в JSON и таблицу в `doc/cjm.md § 8` и се
- Mode: unknown.
- Verification: all DoD commands passed.
- Verification commands: `python scripts/check_backlog_drift.py`, `python scripts/backlog_registry_lint.py --strict`, `python -m pytest tests/test_backlog_drift.py tests/test_rebuild_us_index.py -v`.
- Audit correction: infra truth-sync did not deliver maintainable UI / split `main.py`; `US-12.2` remains open.
- Archive: `archive/team_artifacts/epoch-truth-sync/`.

### epoch-mastery-after-reindex — 2026-04-22

- Goal: tests/test_mastery_after_reindex.py` покрывает US-8.1: `_rehydrate_mastery_from_profile_history` возвращает непустой mastery_vector когда active_concepts перекрываются с историей; при отсутствии перес
- Delivered: tests/test_mastery_after_reindex.py` покрывает US-8.1: `_rehydrate_mastery_from_profile_history` возвращает непустой mastery_vector когда active_concepts перекрываются с историей; при отсутствии пересечений возвращает пустой dict.
tests/test_mastery_after_reindex.py` покрывает US-8.1 integration: `g
- Mode: unknown.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_mastery_after_reindex.py -v`, `python scripts/check_backlog_drift.py`.
- Archive: see `archive/agent_prompts/` and `archive/team_artifacts/`.

### epoch-context-cart-mvp — 2026-04-22

- Goal: scripts/context_cart.py` с поддержкой `--mode plan|orchestrate|verify`, `--emit-agent-prompt`, `--json` флагами. Выводит cart (список файлов + стратегия чтения) вписывающийся в бюджет режима.
Budget п
- Delivered: scripts/context_cart.py` с поддержкой `--mode plan|orchestrate|verify`, `--emit-agent-prompt`, `--json` флагами. Выводит cart (список файлов + стратегия чтения) вписывающийся в бюджет режима.
Budget по режимам: `plan=12k`, `orchestrate=8k`, `verify=6k` (параметр `--budget` для override).
Читает разм
- Mode: unknown.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_context_cart.py -v`, `python scripts/context_cart.py --mode plan app/config.py doc/tasklist.md`.
- Archive: see `archive/agent_prompts/` and `archive/team_artifacts/`.

### epoch-citations-trust-close — 2026-04-22

- Goal: tests/test_citations_trust.py` — acceptance-level тесты: anchor IDs от `linkify_qa_inline_citations` совпадают с якорями в `render_source_cards`; route/score/rank_reason корректно формируют trust capt
- Delivered: tests/test_citations_trust.py` — acceptance-level тесты: anchor IDs от `linkify_qa_inline_citations` совпадают с якорями в `render_source_cards`; route/score/rank_reason корректно формируют trust caption; edge cases (missing route, non-int cite_index, пустой snippet).
Закрытие US-11.1 и US-3.2 через
- Mode: unknown.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_citations_trust.py -v`, `python scripts/check_backlog_drift.py`.
- Archive: see `archive/agent_prompts/` and `archive/team_artifacts/`.

### epoch-srs-priority-reason — 2026-04-22

- Goal: В top-priority due блоке показывается краткая причина приоритета (`давно не повторял` / `низкий mastery` / `ошибки в quiz`).
Причина формируется детерминированно из уже существующих сигналов приоритиз
- Delivered: В top-priority due блоке показывается краткая причина приоритета (`давно не повторял` / `низкий mastery` / `ошибки в quiz`).
Причина формируется детерминированно из уже существующих сигналов приоритизации и не раскрывает debug/internal поля.
На home/resume/tutor surfaces reason отображается одной ст
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_spaced_repetition.py -v`, `python -m pytest tests/test_resume_cards.py -v -k "due or priority or reason"`, `python -m pytest tests/test_tutor_orchestrator.py -v -k "due_reviews"`.
- Archive: `archive/agent_prompts/epoch_srs_priority_reason_exec_prompt_quick_2026-04-22.md`, `archive/team_artifacts/epoch-srs-priority-reason/`.

### epoch-srs-plan-close — 2026-04-22

- Goal: tests/test_srs_recovery_plan.py` — US-7.2: `defer_due_flashcards_for_recovery` при >20 due оставляет `keep_limit` карточек, распределяет остаток по `stagger_days`; при ≤`keep_limit` due — возвращает 0
- Delivered: tests/test_srs_recovery_plan.py` — US-7.2: `defer_due_flashcards_for_recovery` при >20 due оставляет `keep_limit` карточек, распределяет остаток по `stagger_days`; при ≤`keep_limit` due — возвращает 0; edge cases (deck_id filter, параметры граней).
tests/test_srs_recovery_plan.py` — US-6.3: `plan_sn
- Mode: acceptance_close.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_srs_recovery_plan.py -v`, `python scripts/check_backlog_drift.py`.
- Archive: see `archive/agent_prompts/` and `archive/team_artifacts/`.
- Audit note (2026-04-23): closure evidence confirms acceptance verification only; a fresh product delta for this package was not established in the audit trail.

### epoch-reindex-quiz-close — 2026-04-22

- Goal: tests/test_reindex_quiz_acceptance.py` — US-2.2: `plan_partial_reindex` возвращает `use_partial=True` и только изменённые doc_ids при наличии существующего хэша; `enable_partial_reindex=False` → полна
- Delivered: tests/test_reindex_quiz_acceptance.py` — US-2.2: `plan_partial_reindex` возвращает `use_partial=True` и только изменённые doc_ids при наличии существующего хэша; `enable_partial_reindex=False` → полная переиндексация.
tests/test_reindex_quiz_acceptance.py` — US-13.1: `mastery_label_from_vector_level
- Mode: acceptance_close.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_reindex_quiz_acceptance.py -v`, `python scripts/check_backlog_drift.py`.
- Archive: see `archive/agent_prompts/` and `archive/team_artifacts/`.
- Audit note (2026-04-23): closure evidence confirms acceptance verification only; a fresh product delta for this package was not established in the audit trail.

### epoch-backup-benchmark-close — 2026-04-22

- Goal: tests/test_backup_benchmark_acceptance.py` — US-10.1: `import_full_sync_bundle()` возвращает `rows_inserted >= 1` после `export_full_sync_bundle()` с данными.
tests/test_backup_benchmark_acceptance.py
- Delivered: tests/test_backup_benchmark_acceptance.py` — US-10.1: `import_full_sync_bundle()` возвращает `rows_inserted >= 1` после `export_full_sync_bundle()` с данными.
tests/test_backup_benchmark_acceptance.py` — US-12.1: benchmark verdict logic `pass=True` когда hit_rate/MRR/relevancy >= thresholds; `pass=F
- Mode: acceptance_close.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_backup_benchmark_acceptance.py -v`, `python scripts/check_backlog_drift.py`.
- Archive: see `archive/agent_prompts/` and `archive/team_artifacts/`.
- Audit note (2026-04-23): closure evidence confirms acceptance verification only; a fresh product delta for this package was not established in the audit trail.

### epoch-wave-contract — 2026-04-22

- Goal: doc/backlog_registry.yaml` schema bumped to v2 с блоком `waves:` (4 волны) и опциональными полями `wave_id`, `wave_position` на proposed items.
scripts/backlog_registry_lint.py --strict` валидирует wa
- Delivered: doc/backlog_registry.yaml` schema bumped to v2 с блоком `waves:` (4 волны) и опциональными полями `wave_id`, `wave_position` на proposed items.
scripts/backlog_registry_lint.py --strict` валидирует wave-структуру (инварианты 5–6).
doc/team_workflow/generate_plan_next_prompt.md` обновлён: Phase 0 dri
- Mode: unknown.
- Verification: all DoD commands passed.
- Verification commands: `python scripts/backlog_registry_lint.py --strict`, `python scripts/check_backlog_drift.py`, `python -m pytest tests/test_wave_contract.py tests/test_plan_next_wave_ranking.py -v`.
- Archive: see `archive/agent_prompts/` and `archive/team_artifacts/`.

### epoch-flashcard-deck-mgmt — 2026-04-22

- Goal: Пользователь видит колоды и карточки (front/back + SM-2 поля) и может редактировать/удалять карточку, добавлять вручную, удалить колоду (согласовано с API)
После Interactive Quiz на summary есть CTA с
- Delivered: Пользователь видит колоды и карточки (front/back + SM-2 поля) и может редактировать/удалять карточку, добавлять вручную, удалить колоду (согласовано с API)
После Interactive Quiz на summary есть CTA создания колоды из вопросов; колода с `source_type=quiz` и привязкой к документу квиза; переход в зон
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_flashcard_deck_mgmt.py -v`, `python -m pytest tests/test_flashcard_service.py tests/test_flashcards_ui.py tests/test_flashcards_views.py -v`.
- Archive: `archive/agent_prompts/epoch_flashcard_deck_mgmt_exec_prompt_quick_2026-04-22.md`, `archive/team_artifacts/epoch-flashcard-deck-mgmt/`.

### epoch-flashcard-export-upload — 2026-04-23

- Goal: Экспорт колоды в Anki .apkg; загрузка PDF/text файла из UI для генерации карточек
- Delivered: Экспорт колоды в Anki .apkg; загрузка PDF/text файла из UI для генерации карточек
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/ -v`, `python scripts/check_backlog_drift.py`.
- Archive: `archive/agent_prompts/epoch_flashcard_export_upload_exec_prompt_quick_2026-04-22.md`, `archive/team_artifacts/epoch-flashcard-export-upload/`.
- Audit note (2026-04-23): closure invalidated and package reopened. The recorded execution artifact matched pipeline/prompt changes rather than the claimed flashcard export/upload delivery.

### epoch-plan-diff-ux — 2026-04-23

- Goal: В Adaptive Plan card есть expander "Что изменилось" c отдельными списками `added` и `removed` концептов относительно вчера.
При отсутствии вчерашнего плана expander не ломает UI и показывает детермини
- Delivered: В Adaptive Plan card есть expander "Что изменилось" c отдельными списками `added` и `removed` концептов относительно вчера.
При отсутствии вчерашнего плана expander не ломает UI и показывает детерминированный fallback без пустых ошибок.
Diff отображается только для валидных концептов из текущего пла
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_plan_diff_ux.py -v`, `python -m pytest tests/test_adaptive_plan_hub.py -v -k "diff or changed"`, `python -m pytest tests/test_adaptive_plan_history.py -v`.
- Archive: `archive/agent_prompts/epoch_plan_diff_ux_exec_prompt_quick_2026-04-23.md`, `archive/team_artifacts/epoch-plan-diff-ux/`.

### epoch-sync-restore-wizard — 2026-04-23

- Goal: Settings показывает пошаговый restore wizard с загрузкой backup-файла и явным confirm.
Перед confirm выполняется валидация `sync_version`; при несовместимости пользователь видит блокирующее сообщение.
- Delivered: Settings показывает пошаговый restore wizard с загрузкой backup-файла и явным confirm.
Перед confirm выполняется валидация `sync_version`; при несовместимости пользователь видит блокирующее сообщение.
До применения restore UI показывает preview row counts по основным сущностям (profiles/decks/cards/
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_sync_restore_wizard.py -v`, `python -m pytest tests/test_sync_service.py -v -k "restore or version"`.
- Archive: `archive/agent_prompts/epoch_sync_restore_wizard_exec_prompt_quick_2026-04-23.md`, `archive/team_artifacts/epoch-sync-restore-wizard/`.

### epoch-sync-multidevice — 2026-04-23

- Goal: Multi-device parity: экспорт/импорт bundle + merge-конфликт policy
- Delivered: Multi-device parity: экспорт/импорт bundle + merge-конфликт policy
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_sync_bundle.py tests/test_sync_restore_wizard.py tests/test_sync_service.py -v`, `python scripts/check_backlog_drift.py`.
- Archive: `archive/team_artifacts/epoch-sync-multidevice/`.

### epoch-first-answer-examples — 2026-04-23

- Goal: Hero-экран показывает 3 кликабельных примера при непустом индексе
Примеры берутся из доступного контекста и запускают запрос в один клик
- Delivered: Hero-экран показывает 3 кликабельных примера при непустом индексе
Примеры берутся из доступного контекста и запускают запрос в один клик
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_first_answer_examples.py -v`, `python scripts/check_backlog_drift.py`.
- Archive: `archive/agent_prompts/epoch_first_answer_examples_exec_prompt_quick_2026-04-23.md`, `archive/team_artifacts/epoch-first-answer-examples/`.

### epoch-router-accuracy-baseline — 2026-04-23

- Goal: Router accuracy baseline воспроизводимо считается на `eval_data/tutor_regression.json`.
Регрессии точности детектируются через baseline comparison в eval-скрипте/тестах.
- Delivered: Router accuracy baseline воспроизводимо считается на `eval_data/tutor_regression.json`.
Регрессии точности детектируются через baseline comparison в eval-скрипте/тестах.
- Mode: verification_only.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe scripts/run_router_eval.py --limit 1 --quiet`, `.\.venv\Scripts\python.exe -m pytest tests/test_router_eval.py -v`.
- Archive: `archive/agent_prompts/epoch_router_accuracy_baseline_exec_prompt_quick_2026-04-23.md`, `archive/team_artifacts/epoch-router-accuracy-baseline/`.
- Audit note (2026-04-23): closure evidence shows a verification-only pass over a pre-existing capability; no new product delta was recorded in this closure.

### epoch-flashcard-export-upload — 2026-04-24

- Goal: Кнопка на экране колоды скачивает валидный `.apkg` (импорт в Anki desktop); пары front/back из БД согласованы с `anki_apkg_from_pairs()`.
В UI доступна загрузка PDF/text для генерации карточек в рамка
- Delivered: Кнопка на экране колоды скачивает валидный `.apkg` (импорт в Anki desktop); пары front/back из БД согласованы с `anki_apkg_from_pairs()`.
В UI доступна загрузка PDF/text для генерации карточек в рамках пакета (см. US-15.5).
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_flashcard_export_upload.py -v`, `python -m pytest tests/test_flashcard_deck_mgmt.py tests/test_export_utils.py -v`.
- Archive: `archive/agent_prompts/epoch_flashcard_export_upload_exec_prompt_quick_2026-04-22.md`, `archive/team_artifacts/epoch-flashcard-export-upload/`.

### epoch-query-service-assembly — 2026-04-24

- Goal: Query flow разбит на knowledge lookup, rag assembly и fallback assembly без изменения публичного API.
Fallback path возвращает тот же schema-контракт ответа и не теряет source anchors.
Regression cove
- Delivered: Query flow разбит на knowledge lookup, rag assembly и fallback assembly без изменения публичного API.
Fallback path возвращает тот же schema-контракт ответа и не теряет source anchors.
Regression coverage фиксирует debug-token и routing invariants для first-answer path.
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_query_service.py -v`, `python -m pytest tests/test_query_service_invariants.py -v`.
- Archive: `archive/agent_prompts/epoch_query_service_assembly_exec_prompt_quick_2026-04-24.md`, `archive/team_artifacts/epoch-query-service-assembly/`.

### epoch-architecture-review-baseline — 2026-04-24

- Goal: Query service boundary остается разделенной на knowledge, RAG assembly и fallback assembly без изменений внешнего API.
Router/review surface сохраняет контракт отладки и не ломает first-answer routing
- Delivered: Query service boundary остается разделенной на knowledge, RAG assembly и fallback assembly без изменений внешнего API.
Router/review surface сохраняет контракт отладки и не ломает first-answer routing invariants.
Архитектурные docs синхронизированы с фактической сборкой query pipeline.
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_query_service.py -v`, `python -m pytest tests/test_query_service_invariants.py -v`.
- Archive: `archive/agent_prompts/epoch_architecture_review_baseline_exec_prompt_quick_2026-04-24.md`, `archive/team_artifacts/epoch-architecture-review-baseline/`.

### epoch-query-service-assembly-v2 — 2026-04-24

- Goal: Query service assembly path remains stable for knowledge and fallback branches.
Regression suite for query assembly and invariants is green without API drift.
- Delivered: Query service assembly path remains stable for knowledge and fallback branches.
Regression suite for query assembly and invariants is green without API drift.
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_query_service.py -v`, `python -m pytest tests/test_query_service_invariants.py -v`.
- Archive: `archive/agent_prompts/epoch_query_service_assembly_v2_exec_prompt_quick_2026-04-24.md`, `archive/team_artifacts/epoch-query-service-assembly-v2/`.

### epoch-flashcard-export-upload-r2 — 2026-04-24

- Goal: Экспорт выбранной колоды в `.apkg` доступен из UI и завершает операцию без ошибок.
Загрузка файла (PDF/text) из UI создаёт карточки в целевой колоде с видимым подтверждением результата.
- Delivered: Экспорт выбранной колоды в `.apkg` доступен из UI и завершает операцию без ошибок.
Загрузка файла (PDF/text) из UI создаёт карточки в целевой колоде с видимым подтверждением результата.
- Mode: verification_only.
- Verification: all DoD commands passed.
- Verification commands: `python -m pytest tests/test_flashcard_export_upload.py -v`, `python -m pytest tests/test_flashcards_ui.py -v`.
- Audit correction: r2 is the current closure package for `US-15.4` and `US-15.5`; UI Anki download coverage is now pinned by `tests/test_flashcards_ui.py::test_deck_detail_renders_anki_download_button`.
- Archive: `archive/agent_prompts/epoch_flashcard_export_upload_r2_exec_prompt_quick_2026-04-24.md`, `archive/team_artifacts/epoch-flashcard-export-upload-r2/`.

### epoch-plan-next-candidate-seed — 2026-04-24

- Goal: Планировочный цикл не блокируется drift-ошибками на старте (`check_backlog_drift.py` exit code 0).
Реестр backlog остаётся согласованным для автоподбора следующего пакета (`backlog_registry_lint.py --
- Delivered: Планировочный цикл не блокируется drift-ошибками на старте (`check_backlog_drift.py` exit code 0).
Реестр backlog остаётся согласованным для автоподбора следующего пакета (`backlog_registry_lint.py --strict` PASS).
Оркестрационные промпты валидны для следующего execution-пакета (`lint_agent_prompts.
- Mode: verification_only.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe scripts/check_backlog_drift.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict`, `.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py`.
- Audit correction: this package validates planning/backlog guardrails only; `US-12.2` was reopened because maintainable UI / split `main.py` delivery is outside this verification-only evidence.
- Archive: `archive/agent_prompts/epoch_plan_next_candidate_seed_exec_prompt_quick_2026-04-24.md`, `archive/team_artifacts/epoch-plan-next-candidate-seed/`.

### epoch-ui-main-split — 2026-04-24

- Goal: verify that `app/ui/main.py` is already a lightweight router under 300 lines, with UI tab rendering delegated to dedicated modules.
- Delivered: verification-only closure; no product files changed in this run. Current tree evidence: `app/ui/main.py` is 204 lines and delegates to `app/ui/*` modules.
- Mode: verification_only.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_main.py -v`, `.\.venv\Scripts\python.exe -m pytest tests/test_query_tab_topic_infer.py -v`.
- Audit note: this closure confirms pre-existing implementation only. It must not be counted as a fresh execution delivery; evidence is recorded in `archive/team_artifacts/epoch-ui-main-split/execution_contract.md`.
- Archive: `archive/agent_prompts/epoch_ui_main_split_exec_prompt_quick_2026-04-24.md`, `archive/team_artifacts/epoch-ui-main-split/`.

### epoch-demo-pipeline-hardening — 2026-04-25

- Goal: Demo pipeline hardening: narrative ordering, strict validation commands, auto-chain DoD without full pytest, and blocker notes for scenario waves.
- Delivered: Pipeline hardening for demo scenarios with stricter contract validation and autonomous chain behavior.
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe scripts/check_backlog_drift.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict`, `.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py`.
- Archive: `archive/team_artifacts/epoch-demo-pipeline-hardening/`.

### epoch-demo-scenario-03-tutor — 2026-04-25

- Goal: Demo-сценарий `scenario_03` показывает реальный user-facing переход в Tutor из answer flow
Контекст темы (question/sources/concepts) переносится в Tutor и отображается без регрессий
Артефакты сценария
- Delivered: Demo-сценарий `scenario_03` показывает реальный user-facing переход в Tutor из answer flow
Контекст темы (question/sources/concepts) переносится в Tutor и отображается без регрессий
Артефакты сценария и e2e-покрытие обновлены для последующего `demo:validate
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_tutor_orchestrator.py -v`, `.\.venv\Scripts\python.exe -m pytest tests/test_pipeline_steps.py -v`.
- Archive: `archive/agent_prompts/epoch_demo_scenario_03_tutor_exec_prompt_quick_2026-04-25.md`, `archive/team_artifacts/epoch-demo-scenario-03-tutor/`.

### epoch-demo-scenario-04-quiz — 2026-04-25

- Goal: scenario_04` показывает формативную mini-quiz ветку вместо AI-чата
После ответа learner видит мгновенный feedback и понятный следующий шаг
Артефакты сценария и e2e-покрытие готовы для `demo:validate
- Delivered: scenario_04` показывает формативную mini-quiz ветку вместо AI-чата
После ответа learner видит мгновенный feedback и понятный следующий шаг
Артефакты сценария и e2e-покрытие готовы для `demo:validate
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_quiz_unified.py -v`, `.\.venv\Scripts\python.exe -m pytest tests/test_tutor_orchestrator.py -v`.
- Archive: `archive/agent_prompts/epoch_demo_scenario_04_quiz_exec_prompt_quick_2026-04-25.md`, `archive/team_artifacts/epoch-demo-scenario-04-quiz/`.

### epoch-demo-scenario-06-srs — 2026-04-25

- Goal: Сценарий `scenario_06_spaced_repetition` стабильно демонстрирует очередь карточек к повторению в demo-режиме.
Детерминированный seed для SRS-данных позволяет воспроизводить demo без ручной подготовки 
- Delivered: Сценарий `scenario_06_spaced_repetition` стабильно демонстрирует очередь карточек к повторению в demo-режиме.
Детерминированный seed для SRS-данных позволяет воспроизводить demo без ручной подготовки состояния.
Артефакты сценария и e2e-проверка синхронизированы с текущим API/guardrails контрактом.
- Mode: verification_only.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_user_state.py -v`, `.\.venv\Scripts\python.exe -m pytest tests/test_learner_model_service.py -v`.
- Archive: `archive/agent_prompts/epoch_demo_scenario_06_srs_exec_prompt_quick_2026-04-25.md`, `archive/team_artifacts/epoch-demo-scenario-06-srs/`.

### epoch-demo-scenario-07-progress — 2026-04-25

- Goal: Demo показывает: dashboard не декоративный — каждая цифра превращается в actionable next-step.
- Delivered: Demo показывает: dashboard не декоративный — каждая цифра превращается в actionable next-step.
- Mode: verification_only.
- Verification: all DoD commands passed.
- Verification commands: `npm run demo:validate`, `powershell -NoProfile -Command "$env:DEMO_SHOT_RUN='2026-01-07'; npm run test:e2e:demo -- --grep '@demo Scenario 07'"`, `.\.venv\Scripts\python.exe scripts\validate_demo_contract.py --screenshots-dir doc\screenshots\2026-01-07 --require-screenshots --strict-captures --require-unique-shots`, `.\.venv\Scripts\python.exe scripts\generate_demo_doc.py --screenshots-dir doc\screenshots\2026-01-07 --output doc\quickstart_demo.preview.md --no-final-sync`.
- Archive: `archive/agent_prompts/epoch_demo_scenario_07_progress_exec_prompt_quick_2026-04-25.md`, `archive/team_artifacts/epoch-demo-scenario-07-progress/`.

### epoch-demo-scenario-09-learning-plan — 2026-04-25

- Goal: Demo показывает переход от прогресса к персональному плану без ручных подсказок.
В сценарии 09 каждый plan step привязан к измеримому следующему действию.
- Delivered: Demo показывает переход от прогресса к персональному плану без ручных подсказок.
В сценарии 09 каждый plan step привязан к измеримому следующему действию.
- Mode: verification_only.
- Verification: all DoD commands passed.
- Verification commands: `npm run demo:validate`, `powershell -NoProfile -Command "$env:DEMO_SHOT_RUN='2026-01-09'; npm run test:e2e:demo -- --grep '@demo Scenario 09'"`, `.\.venv\Scripts\python.exe scripts\validate_demo_contract.py --screenshots-dir doc\screenshots\2026-01-09 --require-screenshots --strict-captures --require-unique-shots`, `.\.venv\Scripts\python.exe scripts\generate_demo_doc.py --screenshots-dir doc\screenshots\2026-01-09 --output doc\quickstart_demo.preview.md --no-final-sync`.
- Archive: `archive/agent_prompts/epoch_demo_scenario_09_learning_plan_exec_prompt_quick_2026-04-25.md`, `archive/team_artifacts/epoch-demo-scenario-09-learning-plan/`.

### epoch-e30-a1-cockpit-scaffold — 2026-04-26 ⚠️ REOPENED 2026-04-28

- Goal: app/ui/course_cockpit.py`: трёхколоночный каркас, заголовок, выход; за флагом `RAG_COURSE_COCKPIT_V2` без поломки tab-flow без флага
.env.example` документирует флаг; регрессия course/progress покрыта
- Delivered: app/ui/course_cockpit.py`: трёхколоночный каркас, заголовок, выход; за флагом `RAG_COURSE_COCKPIT_V2` без поломки tab-flow без флага
.env.example` документирует флаг; регрессия course/progress покрыта pytest
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_course_cockpit.py tests/test_ui_helpers.py -v`.
- Archive: `archive/agent_prompts/e30_a1_cockpit_scaffold_exec_prompt_quick_2026-04-26.md`, `archive/team_artifacts/e30-a1-cockpit-scaffold/`.

### epoch-e30-a2-cockpit-rotator — 2026-04-26 ⚠️ REOPENED 2026-04-28

- Goal: app/ui/cockpit_rotator.py`: планировщик слотов активностей (stub), session_state; хуки для последующих триггеров 3×error / 3×Easy
app/ui/course_cockpit.py`: центральная колонка вызывает ротатор (без п
- Delivered: app/ui/cockpit_rotator.py`: планировщик слотов активностей (stub), session_state; хуки для последующих триггеров 3×error / 3×Easy
app/ui/course_cockpit.py`: центральная колонка вызывает ротатор (без полной бизнес-логики квиза/тьютора)
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_cockpit_rotator.py tests/test_course_cockpit.py -v`.
- Archive: `archive/team_artifacts/e30-a2-cockpit-rotator/`.

### epoch-e30-b1-graduation-overlay — 2026-04-26 ⚠️ REOPENED 2026-04-28

- Goal: app/ui/graduation_overlay.py`: заглушка overlay «церемонии» (3s timer stub) + публичный API для последующего wiring
Логирование события в `course_metrics` или заглушка-вызов без поломки существующих т
- Delivered: app/ui/graduation_overlay.py`: заглушка overlay «церемонии» (3s timer stub) + публичный API для последующего wiring
Логирование события в `course_metrics` или заглушка-вызов без поломки существующих тестов
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_graduation_overlay.py tests/test_progress_tab.py -v`.
- Archive: `archive/team_artifacts/e30-b1-graduation-overlay/`.

### epoch-e30-b2-daily-briefing — 2026-04-26 ⚠️ REOPENED 2026-04-28

- Goal: app/ui/daily_briefing.py`: заглушки morning/evening + логирование `daily_briefing_stub` через `course_metrics
- Delivered: app/ui/daily_briefing.py`: заглушки morning/evening + логирование `daily_briefing_stub` через `course_metrics
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_daily_briefing.py tests/test_progress_tab.py -v`.
- Archive: `archive/team_artifacts/e30-b2-daily-briefing/`.

### epoch-demo — 2026-04-26 ⚠️ REOPENED 2026-04-28

- Goal: smoke post-agent для `epoch-demo`; write-set путей `scripts/` в `run_autonomous._parse_write_set`; единая verification-only policy в workflow-скриптах
- Delivered: execution closure, DoD `py_compile` для `scripts/prompt_utils.py` (демо-функция удалена после закрытия)
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m py_compile scripts/prompt_utils.py`
- Archive: `archive/team_artifacts/epoch-demo/`

### epoch-e30-idea-1-daily-runway — 2026-04-26 ⚠️ REOPENED 2026-04-28

- Goal: Видимая дневная микро-цель и streak в контексте курса (ideation)
- Delivered: daily runway и streak chip в `course_cockpit
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_course_cockpit.py -v`.
- Archive: `archive/agent_prompts/e30_idea_1_daily_runway_exec_prompt_quick_2026-04-26.md`, `archive/team_artifacts/e30-idea-1-daily-runway/`.

### epoch-e30-idea-2-retrieval-gates — 2026-04-26 ⚠️ REOPENED 2026-04-28

- Goal: Вопросы между чанками плана; интеграция с pace flow (ideation)
- Delivered: точки вставки retrieval gates между чанками (через pace_engine / план, по спеке эпохи)
- Mode: verification_only.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_course_cockpit.py -v`.
- Archive: `archive/agent_prompts/e30_idea_2_retrieval_gates_exec_prompt_quick_2026-04-26.md`, `archive/team_artifacts/e30-idea-2-retrieval-gates/`.

### epoch-e30-c1-diagnostic — 2026-04-26 ⚠️ REOPENED 2026-04-28

- Goal: Phase C: `app/diagnostic_service.py` — pre-flight adaptive quiz, `diagnostic.v1` artifact, skip-confirmation UI.
- Delivered: Phase C: `app/diagnostic_service.py` — pre-flight adaptive quiz, `diagnostic.v1` artifact, skip-confirmation UI.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m py_compile app/dummy.py`.
- Archive: `archive/agent_prompts/e30_c1_diagnostic_exec_prompt_quick_2026-04-26.md`, `archive/team_artifacts/e30-c1-diagnostic/`.

### epoch-truth-sync — 2026-04-26

- Goal: scripts/rebuild_user_stories_index.py` пересобирает `doc/user_stories_index.json` из registry/frontmatter и остаётся идемпотентным.
scripts/regenerate_cjm_pain_table.py` пересобирает секцию `doc/cjm.m
- Delivered: scripts/rebuild_user_stories_index.py` пересобирает `doc/user_stories_index.json` из registry/frontmatter и остаётся идемпотентным.
scripts/regenerate_cjm_pain_table.py` пересобирает секцию `doc/cjm.md § 8` между GENERATED-маркерами.
scripts/check_backlog_drift.py` покрывает инварианты drift guard и
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts/check_backlog_drift.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict`, `.\.venv\Scripts\python.exe -m pytest tests/test_backlog_drift.py tests/test_rebuild_us_index.py -v`.
- Archive: `archive/team_artifacts/epoch-truth-sync/`.

### epoch-e30-c2-pace-engine — 2026-04-26 ⚠️ REOPENED 2026-04-28

- Goal: В `course` режиме доступен pace engine с режимами Sprint/Steady/Deep.
plan.v2` сохраняет `pace_mode`, а cockpit отображает текущий режим.
- Delivered: В `course` режиме доступен pace engine с режимами Sprint/Steady/Deep.
plan.v2` сохраняет `pace_mode`, а cockpit отображает текущий режим.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_course_cache.py -v`, `.\.venv\Scripts\python.exe -m pytest tests/test_course_cockpit.py -v`.
- Archive: `archive/agent_prompts/epoch_e30_c2_pace_engine_exec_prompt_quick_2026-04-26.md`, `archive/team_artifacts/epoch-e30-c2-pace-engine/`.

### epoch-e30-d1-smart-resume — 2026-04-26 ⚠️ REOPENED 2026-04-28

- Goal: Введён planner warm-up с явными pause tiers: <1 day, 1-3 days, 3-7 days, >7 days.
Добавлен soft-recovery overdue rule: при паузе >2 days и due-pile >20 карточки равномерно разносятся на 3-5 сессий.
По
- Delivered: Введён planner warm-up с явными pause tiers: <1 day, 1-3 days, 3-7 days, >7 days.
Добавлен soft-recovery overdue rule: при паузе >2 days и due-pile >20 карточки равномерно разносятся на 3-5 сессий.
Покрыта тестами базовая логика классификации и формирования warm-up payload.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_warmup_planner.py -v`, `.\.venv\Scripts\python.exe -m pytest tests/test_resume_cards.py -v`.
- Archive: `archive/team_artifacts/epoch-e30-d1-smart-resume/`.

### epoch-e30-d2-focus-mode — 2026-04-26 ⚠️ REOPENED 2026-04-28

- Goal: Добавлен модуль `app/ui/focus_mode.py` со stub-слоем Focus 25 и логикой payload для `pomodoro_session`.
Реализована логика deep-work achievement (4 цикла без прерывания) и streak shield flag.
Добавлен
- Delivered: Добавлен модуль `app/ui/focus_mode.py` со stub-слоем Focus 25 и логикой payload для `pomodoro_session`.
Реализована логика deep-work achievement (4 цикла без прерывания) и streak shield flag.
Добавлены unit-тесты для badge/payload/metrics logging.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_focus_mode.py -v`, `.\.venv\Scripts\python.exe -m pytest tests/test_course_cockpit.py -v`.
- Archive: `archive/team_artifacts/epoch-e30-d2-focus-mode/`.

### epoch-e30-e1-course-graduation — 2026-04-26 ⚠️ REOPENED 2026-04-28

- Goal: Phase E: `app/course_graduation.py` — course graduation ceremony, PDF certificate, Knowledge Vault export (md, apkg, graph json).
- Delivered: Phase E: `app/course_graduation.py` — course graduation ceremony, PDF certificate, Knowledge Vault export (md, apkg, graph json).
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_course_graduation.py -v`, `.\.venv\Scripts\python.exe -m pytest tests/test_course_cache.py tests/test_user_state.py -v`.
- Archive: `archive/agent_prompts/epoch_e30_e1_course_graduation_exec_prompt_quick_2026-04-26.md`, `archive/team_artifacts/epoch-e30-e1-course-graduation/`.

### epoch-demo-scenario-08-trust — 2026-04-26

- Goal: Demo доказывает anti-hallucination: каждый тезис → фрагмент → строка в файле. Local-first.
- Delivered: Demo доказывает anti-hallucination: каждый тезис → фрагмент → строка в файле. Local-first.
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_citations_trust.py -v`, `.\.venv\Scripts\python.exe -m pytest tests/test_ingestion_reindex.py -v`.
- Archive: `archive/team_artifacts/epoch-demo-scenario-08-trust/`.

### epoch-tour-skeleton-ch1 — 2026-04-27

- Goal: Skeleton интерактивного тура: state, overlay (CSS-only), глава 1 «Первый ответ» end-to-end внутри Streamlit.
- Delivered: Skeleton интерактивного тура: state, overlay (CSS-only), глава 1 «Первый ответ» end-to-end внутри Streamlit.
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ui_tutorial.py -v`, `.\.venv\Scripts\python.exe -m pytest tests/test_citations_trust.py -v`.
- Archive: `archive/agent_prompts/epoch_tour_skeleton_ch1_exec_prompt_quick_2026-04-27.md`, `archive/team_artifacts/epoch-tour-skeleton-ch1/`.

### epoch-tour-persistence-ch2-5 — 2026-04-27

- Goal: allow_verification_only; touchpoints: `app/tutorial_service.py`, `app/ui/tutorial_guide.py`, `app/ui/tutorial_chapters.py`, `tests/test_tutorial_service.py`, `tests/test_ui_tutorial.py
Guide-runtime с
- Delivered: allow_verification_only; touchpoints: `app/tutorial_service.py`, `app/ui/tutorial_guide.py`, `app/ui/tutorial_chapters.py`, `tests/test_tutorial_service.py`, `tests/test_ui_tutorial.py
Guide-runtime сохраняет/восстанавливает прогресс и проводит пользователя через главы 2–5 (Tutor, Resume, Flashcards
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_tutorial_service.py -v`, `.\.venv\Scripts\python.exe -m pytest tests/test_ui_tutorial.py -v`.
- Archive: `archive/agent_prompts/epoch_tour_persistence_ch2_5_exec_prompt_quick_2026-04-27.md`, `archive/team_artifacts/epoch-tour-persistence-ch2-5/`.

### epoch-demo — 2026-04-27 ⚠️ REOPENED 2026-04-28, 2026-05-02

- Goal: smoke package scaffolding for post-agent CLI verification
allow_verification_only (smoke scaffold; pre-existing `scripts/prompt_utils.py`)
- Delivered: smoke package scaffolding for post-agent CLI verification
allow_verification_only (smoke scaffold; pre-existing `scripts/prompt_utils.py`)
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m py_compile scripts/prompt_utils.py`.
- Archive: `archive/agent_prompts/epoch_demo_scenario_09_learning_plan_exec_prompt_quick_2026-04-25.md`, `archive/team_artifacts/epoch-demo/`.

### epoch-tour-scenarios-10-14 — 2026-04-27

- Goal: Добавлены и зелёные в demo pipeline сценарии 10–14: day-2 resume, Anki export, quiz→deck, course workspace, full sync.
- Delivered: Добавлены и зелёные в demo pipeline сценарии 10–14: day-2 resume, Anki export, quiz→deck, course workspace, full sync.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts/validate_demo_contract.py --scenario-id scenario_10 --scenario-id scenario_11 --scenario-id scenario_12 --scenario-id scenario_13 --scenario-id scenario_14`, `powershell -NoProfile -Command "$env:DEMO_SHOT_RUN=(Get-Date -Format 'yyyy-MM-dd'); npm run test:e2e:demo -- --grep '@demo Scenario (10|11|12|13|14)'"`.
- Archive: `archive/agent_prompts/epoch_tour_scenarios_10_14_exec_prompt_quick_2026-04-27.md`, `archive/team_artifacts/epoch-tour-scenarios-10-14/`.

### epoch-tour-demo-doc-refresh — 2026-04-27

- Goal: allow_verification_only
Quickstart demo обновлён: добавлен вводный раздел про in-app interactive tour, при этом 9 существующих PR-витрина сценариев сохранены.
- Delivered: allow_verification_only
Quickstart demo обновлён: добавлен вводный раздел про in-app interactive tour, при этом 9 существующих PR-витрина сценариев сохранены.
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts/validate_demo_contract.py --scenario-id scenario_10 --scenario-id scenario_11 --scenario-id scenario_12 --scenario-id scenario_13 --scenario-id scenario_14`, `powershell -NoProfile -Command "$env:DEMO_SHOT_RUN=(Get-Date -Format 'yyyy-MM-dd'); npm run test:e2e:demo -- --grep '@demo Scenario (10|11|12|13|14)'"`.
- Archive: `archive/agent_prompts/epoch_tour_demo_doc_refresh_exec_prompt_quick_2026-04-27.md`, `archive/team_artifacts/epoch-tour-demo-doc-refresh/`.

### epoch-aqe-corpus-choice — 2026-04-27

- Goal: Выбор и формирование golden set для AQE: synthetic corpus или real-data; AQE-R remediation decision.
- Delivered: Выбор и формирование golden set для AQE: synthetic corpus или real-data; AQE-R remediation decision.
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -c "import json, pathlib; json.loads(pathlib.Path('eval_data/tutor_regression.json').read_text(encoding='utf-8-sig'))"`, `.\.venv\Scripts\python.exe -c "import json, pathlib; json.loads(pathlib.Path('tests/eval/thresholds.json').read_text(encoding='utf-8-sig'))"`.
- Archive: `archive/agent_prompts/epoch_aqe_corpus_choice_exec_prompt_quick_2026-04-27.md`, `archive/team_artifacts/epoch-aqe-corpus-choice/`.

### epoch-answer-quality-baseline — 2026-04-27

- Goal: allow_verification_only
Eval pipeline + baseline score + CI gate; scripts/run_aqe.py; результат ≥ 80% green в pre-merge.
- Delivered: allow_verification_only
Eval pipeline + baseline score + CI gate; scripts/run_aqe.py; результат ≥ 80% green в pre-merge.
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -c "import pathlib; assert pathlib.Path('scripts/run_router_eval.py').exists()"`, `.\.venv\Scripts\python.exe -c "import json, pathlib; json.loads(pathlib.Path('tests/eval/thresholds.json').read_text(encoding='utf-8-sig'))"`.
- Archive: `archive/team_artifacts/epoch-answer-quality-baseline/`.

### epoch-mastery-gap-routing — 2026-04-27

- Goal: Orchestrator маршрутизирует следующую тему исходя из реального mastery/gap, не random_next.
- Delivered: Orchestrator маршрутизирует следующую тему исходя из реального mastery/gap, не random_next.
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_tutor_orchestrator.py -v`, `.\.venv\Scripts\python.exe -m pytest tests/test_pipeline_steps.py -v`.
- Archive: `archive/agent_prompts/epoch_mastery_gap_routing_exec_prompt_quick_2026-04-27.md`, `archive/team_artifacts/epoch-mastery-gap-routing/`.

### epoch-concept-remediation-step — 2026-04-27

- Goal: allow_verification_only
Tutor предлагает конкретные шаги исправления по каждому concept gap в плане.
- Delivered: allow_verification_only
Tutor предлагает конкретные шаги исправления по каждому concept gap в плане.
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_tutor_orchestrator.py -v`, `.\.venv\Scripts\python.exe -m pytest tests/test_pipeline_steps.py -v`.
- Archive: `archive/agent_prompts/epoch_concept_remediation_step_exec_prompt_quick_2026-04-27.md`, `archive/team_artifacts/epoch-concept-remediation-step/`.

### epoch-latency-slo-gate — 2026-04-28

- Goal: p95 latency CI gate интегрирован в pre-merge workflow; порог из tests/eval/thresholds.json.
- Delivered: p95 latency CI gate интегрирован в pre-merge workflow; порог из tests/eval/thresholds.json.
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -c "import pathlib; assert pathlib.Path('scripts/eval_ci_gate.py').exists(), 'eval_ci_gate.py missing'"`, `.\.venv\Scripts\python.exe -c "import json, pathlib; t=json.loads(pathlib.Path('tests/eval/thresholds.json').read_text(encoding='utf-8-sig')); assert 'latency_p95_sec' in t.get('thresholds', {}), 'latency_p95_sec missing from thresholds'"`.
- Archive: `archive/agent_prompts/epoch_latency_slo_gate_exec_prompt_quick_2026-04-27.md`, `archive/team_artifacts/epoch-latency-slo-gate/`.

### epoch-llm-regression-baseline — 2026-04-28

- Goal: allow_verification_only
Full LLM regression suite с golden baselines; nightly CI job; нет silent regression на merge.
- Delivered: allow_verification_only
Full LLM regression suite с golden baselines; nightly CI job; нет silent regression на merge.
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -c "import pathlib; assert pathlib.Path('scripts/run_router_eval.py').exists(), 'run_router_eval.py missing'"`, `.\.venv\Scripts\python.exe -c "import json, pathlib; json.loads(pathlib.Path('eval_data/tutor_regression.json').read_text(encoding='utf-8-sig'))"`, `.\.venv\Scripts\python.exe -c "import pathlib; assert pathlib.Path('eval_results/llm_regression_baseline.json').exists(), 'eval_results/llm_regression_baseline.json missing'"`.
- Archive: `archive/agent_prompts/epoch_llm_regression_baseline_exec_prompt_quick_2026-04-28.md`, `archive/team_artifacts/epoch-llm-regression-baseline/`.

### epoch-control-plane-v3-core — 2026-04-28 ⚠️ REOPENED 2026-04-28

- Goal: pipeline_state.json + result.json в logs/autonomous_runs/<run_id>/; get_or_create_run_id() (ms+token, без коллизий); schemas; atomic pipeline_state; orphan log; PID-scoped current/*.json; правки run_a
- Delivered: pipeline_state.json + result.json в logs/autonomous_runs/<run_id>/; get_or_create_run_id() (ms+token, без коллизий); schemas; atomic pipeline_state; orphan log; PID-scoped current/*.json; правки run_autonomous + _perf_timer.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_pipeline_events.py tests/test_run_autonomous_result_json.py -v`.
- Archive: `archive/agent_prompts/epoch_control_plane_v3_core_exec_prompt_quick_2026-04-28.md`, `archive/team_artifacts/epoch-control-plane-v3-core/`.

### epoch-ingestion-loader-extraction — 2026-04-29

- Goal: Выделить orchestration загрузчика из app/ingestion.py в app/ingestion_loader.py; публичные entrypoints и поведение без регрессий; ingestion.py остаётся под лимитом Phase-2 guard. Для чтения app/ingest
- Delivered: Выделить orchestration загрузчика из app/ingestion.py в app/ingestion_loader.py; публичные entrypoints и поведение без регрессий; ingestion.py остаётся под лимитом Phase-2 guard. Для чтения app/ingestion.py — только signatures/секции (token_safety).
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ingestion_reindex.py tests/test_ingestion_progress.py tests/test_ingestion_metadata.py tests/test_ingestion_content_state.py tests/test_ingestion_split_metadata.py -v`.
- Archive: `archive/agent_prompts/epoch_ingestion_loader_extraction_exec_prompt_quick_2026-04-29.md`, `archive/team_artifacts/epoch-ingestion-loader-extraction/`.

### epoch-doc-ingestion-split-arch-sync — 2026-04-29

- Goal: Синхронизировать описание модуля ingestion: doc/architecture.md (разделы с app/ingestion.py) — разделение document pipeline vs app/ingestion_loader.py (orchestration индекса); обновить ручной блок Mai
- Delivered: Синхронизировать описание модуля ingestion: doc/architecture.md (разделы с app/ingestion.py) — разделение document pipeline vs app/ingestion_loader.py (orchestration индекса); обновить ручной блок Maintenance в doc/tasklist.md (убрать устаревший «следующий шаг extraction»).
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`, `.\.venv\Scripts\python.exe -m pytest tests/test_ingestion_reindex.py -v`.
- Archive: `archive/agent_prompts/epoch_doc_ingestion_split_arch_sync_exec_prompt_quick_2026-04-29.md`, `archive/team_artifacts/epoch-doc-ingestion-split-arch-sync/`.

### epoch-ingestion-loader-token-registry — 2026-04-29

- Goal: Добавить app/ingestion_loader.py в doc/token_safety_registry.json: full_read forbidden, est_tokens/lines, safe_hint (grep signatures по правилам token_safety); при необходимости подстроить golden/fixt
- Delivered: Добавить app/ingestion_loader.py в doc/token_safety_registry.json: full_read forbidden, est_tokens/lines, safe_hint (grep signatures по правилам token_safety); при необходимости подстроить golden/fixtures context_cart.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts/check_readset.py doc/token_safety_registry.json scripts/context_cart.py`, `.\.venv\Scripts\python.exe scripts/check_readset.py --signatures app/ingestion_loader.py`, `.\.venv\Scripts\python.exe -m pytest tests/test_token_registry.py tests/test_context_cart.py -v`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`.
- Archive: `archive/agent_prompts/epoch_ingestion_loader_token_registry_exec_prompt_quick_2026-04-29.md`, `archive/team_artifacts/epoch-ingestion-loader-token-registry/`.

### epoch-token-registry-measure-reconcile — 2026-04-30

- Goal: Пересчитать est_tokens/lines в doc/token_safety_registry.json через scripts/measure_token_registry.py --write после landing ingestion_loader; при расхождениях подстроить doc/token_safety.md (только за
- Delivered: Пересчитать est_tokens/lines в doc/token_safety_registry.json через scripts/measure_token_registry.py --write после landing ingestion_loader; при расхождениях подстроить doc/token_safety.md (только затронутые строки).
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts/measure_token_registry.py --write`, `.\.venv\Scripts\python.exe -m pytest tests/test_token_registry.py -v`, `.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`.
- Archive: `archive/agent_prompts/epoch_token_registry_measure_reconcile_exec_prompt_quick_2026-04-30.md`, `archive/team_artifacts/epoch-token-registry-measure-reconcile/`.

### epoch-context-cart-token-metrics — 2026-04-30

- Goal: Добавить scripts/context_cart.py в MEASURE_PATHS scripts/measure_token_registry.py (агентский read-set для context_cart); пересобрать doc/token_safety_registry.json через measure_token_registry.py --w
- Delivered: Добавить scripts/context_cart.py в MEASURE_PATHS scripts/measure_token_registry.py (агентский read-set для context_cart); пересобрать doc/token_safety_registry.json через measure_token_registry.py --write; зелёный контур token_registry + context_cart тестов.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts/measure_token_registry.py --write`, `.\.venv\Scripts\python.exe -m pytest tests/test_token_registry.py tests/test_context_cart.py -v`, `.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`.
- Archive: `archive/agent_prompts/epoch_context_cart_token_metrics_exec_prompt_quick_2026-04-30.md`, `archive/team_artifacts/epoch-context-cart-token-metrics/`.

### epoch-backlog-active-wave-determinism — 2026-05-01

- Goal: Юнит-тесты get_active_wave() в backlog_registry_lint.py: приоритет explicit active_wave_id → wip → ready → proposed; волны completed/frozen не выбираются. Реализацию в scripts/backlog_registry_lint.py
- Delivered: Юнит-тесты get_active_wave() в backlog_registry_lint.py: приоритет explicit active_wave_id → wip → ready → proposed; волны completed/frozen не выбираются. Реализацию в scripts/backlog_registry_lint.py смотреть только через rg "^def \|^class " / узкий фрагмент get_active_wave (token_safety).
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_backlog_registry_lint.py -v -k active_wave_determinism`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`.
- Archive: `archive/agent_prompts/epoch_backlog_active_wave_determinism_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-backlog-active-wave-determinism/`.

### epoch-cjm-progress-next-action — 2026-05-01

- Goal: Progress tab: один primary CTA следующего шага (приоритет US-14.1); единый поток метрик и действия (US-9.1); доступ к плану на сегодня с Progress (US-6.1); согласованность с resume без конфликтующих C
- Delivered: Progress tab: один primary CTA следующего шага (приоритет US-14.1); единый поток метрик и действия (US-9.1); доступ к плану на сегодня с Progress (US-6.1); согласованность с resume без конфликтующих CTA (US-7.3); Playwright smoke progress_next_action без live LLM (US-12.6).
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_progress_tab.py tests/test_mastery_dashboard.py tests/test_learning_plan_service.py tests/test_resume_cards.py -v --tb=short`, `npm run test:e2e:smoke -- tests/e2e/progress_next_action.spec.ts`.
- Archive: `archive/agent_prompts/epoch_cjm_progress_next_action_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-cjm-progress-next-action/`.

### epoch-run-autonomous-token-registry — 2026-05-01

- Goal: Зарегистрировать scripts/run_autonomous.py в doc/token_safety_registry.json (full_read при необходимости forbidden, safe_hint через rg signatures); добавить путь в MEASURE_PATHS scripts/measure_token_
- Delivered: Зарегистрировать scripts/run_autonomous.py в doc/token_safety_registry.json (full_read при необходимости forbidden, safe_hint через rg signatures); добавить путь в MEASURE_PATHS scripts/measure_token_registry.py; пересобрать метрики --write; зелёный контур tests/test_token_registry.py + check_readse
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts/measure_token_registry.py --write`, `.\.venv\Scripts\python.exe -m pytest tests/test_token_registry.py -v`, `.\.venv\Scripts\python.exe scripts/check_readset.py --signatures scripts/run_autonomous.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`, `.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py`.
- Archive: `archive/agent_prompts/epoch_run_autonomous_token_registry_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-run-autonomous-token-registry/`.

### epoch-check-llm-context-gate-token-registry — 2026-05-01

- Goal: Зарегистрировать scripts/check_llm_context_gate.py в doc/token_safety_registry.json (full_read допустим или forbidden + safe_hint); добавить путь в MEASURE_PATHS scripts/measure_token_registry.py; пер
- Delivered: Зарегистрировать scripts/check_llm_context_gate.py в doc/token_safety_registry.json (full_read допустим или forbidden + safe_hint); добавить путь в MEASURE_PATHS scripts/measure_token_registry.py; пересобрать метрики --write; зелёный контур tests/test_token_registry.py + check_readset (read_set_hint
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts/measure_token_registry.py --write`, `.\.venv\Scripts\python.exe -m pytest tests/test_token_registry.py -v`, `.\.venv\Scripts\python.exe scripts/check_readset.py doc/token_safety_registry.json scripts/measure_token_registry.py scripts/check_llm_context_gate.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`, `.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py`.
- Archive: `archive/agent_prompts/epoch_check_llm_context_gate_token_registry_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-check-llm-context-gate-token-registry/`.

### epoch-generate-orchestration-prompt-token-registry — 2026-05-01

- Goal: Зарегистрировать scripts/generate_orchestration_prompt.py в doc/token_safety_registry.json (full_read forbidden + safe_hint через rg signatures); добавить путь в MEASURE_PATHS scripts/measure_token_re
- Delivered: Зарегистрировать scripts/generate_orchestration_prompt.py в doc/token_safety_registry.json (full_read forbidden + safe_hint через rg signatures); добавить путь в MEASURE_PATHS scripts/measure_token_registry.py; пересобрать метрики --write; зелёный контур tests/test_token_registry.py + check_readset 
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts/measure_token_registry.py --write`, `.\.venv\Scripts\python.exe -m pytest tests/test_token_registry.py -v`, `.\.venv\Scripts\python.exe scripts/check_readset.py --signatures scripts/generate_orchestration_prompt.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`, `.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py`.
- Archive: `archive/agent_prompts/epoch_generate_orchestration_prompt_token_registry_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-generate-orchestration-prompt-token-registry/`.

### epoch-answer-trust-to-learning-path — 2026-05-01

- Goal: First Answer becomes a confident learning handoff: learner can see whether source coverage is strong or partial, recover from weak support, and continue into tutor or plan without losing question/sour
- Delivered: First Answer becomes a confident learning handoff: learner can see whether source coverage is strong or partial, recover from weak support, and continue into tutor or plan without losing question/source context.
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_e11_learning_loop.py tests/test_e9_7_continuity_bridge.py -v --tb=short`, `npm run test:e2e:smoke -- tests/e2e/progress_next_action.spec.ts`.
- Archive: `archive/agent_prompts/epoch_answer_trust_to_learning_path_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-answer-trust-to-learning-path/`.

### epoch-course-retention-polish — 2026-05-01

- Goal: Course mode return path becomes more confident: learner sees where they stopped, chooses a small daily runway, and confirms understanding through course-scoped retrieval gates.
- Delivered: Course mode return path becomes more confident: learner sees where they stopped, chooses a small daily runway, and confirms understanding through course-scoped retrieval gates.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_course_cockpit.py -v --tb=short`, `.\.venv\Scripts\python.exe -m pytest tests/test_course_workflow.py -v --tb=short`.
- Archive: `archive/agent_prompts/epoch_course_retention_polish_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-course-retention-polish/`.

### epoch-home-mode-card-labels — 2026-05-01

- Goal: allow_verification_only
Home mode grid becomes intent-readable: each of the 6 primary mode cards exposes concise best-for metadata, a state/time hint when available, and preserves the US-14.1 primary 
- Delivered: allow_verification_only
Home mode grid becomes intent-readable: each of the 6 primary mode cards exposes concise best-for metadata, a state/time hint when available, and preserves the US-14.1 primary CTA priority contract.
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ui_helpers.py -v --tb=short`, `npm run test:e2e:smoke -- tests/e2e/home_mode_selection.spec.ts`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`.
- Archive: `archive/agent_prompts/epoch_home_mode_card_labels_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-home-mode-card-labels/`.

### epoch-home-mode-flashcard-time-badge — 2026-05-01

- Goal: Flashcards card communicates review effort as due count plus simple time-to-clear estimate, including calm recovery copy for large due queues and a clear no-due state that does not override primary CT
- Delivered: Flashcards card communicates review effort as due count plus simple time-to-clear estimate, including calm recovery copy for large due queues and a clear no-due state that does not override primary CTA priority rules.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_flashcard_service.py tests/test_ui_helpers.py -v --tb=short`, `npm run test:e2e:smoke -- tests/e2e/home_mode_selection.spec.ts`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`.
- Archive: `archive/agent_prompts/epoch_home_mode_flashcard_time_badge_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-home-mode-flashcard-time-badge/`.

### epoch-home-mode-preview-drawer — 2026-05-01

- ⚠️ REOPENED 2026-05-02 — исправлены e2e/history (fragment + e2e_view); пакет снова в ready для формального закрытия.
- ⚠️ REOPENED 2026-05-01 — audit DoD FAIL (e2e home_mode_selection / «История вопросов»).
- Goal: Home mode cards expose a keyboard-accessible preview disclosure that explains outcome, current learner state, and destination route while keeping direct one-click entry for returning users.
- Delivered: Home mode cards expose a keyboard-accessible preview disclosure that explains outcome, current learner state, and destination route while keeping direct one-click entry for returning users.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ui_helpers.py -v --tb=short`, `npm run test:e2e:smoke -- tests/e2e/home_mode_selection.spec.ts`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`.
- Archive: `archive/agent_prompts/epoch_home_mode_preview_drawer_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-home-mode-preview-drawer/`.

### epoch-course-confidence-dip-detector — 2026-05-01

- Goal: Detect repeated retrieval misses or low-confidence course signals and route the learner into a bounded remediation mini-loop with an explicit exit back to the main course runway.
- Delivered: Detect repeated retrieval misses or low-confidence course signals and route the learner into a bounded remediation mini-loop with an explicit exit back to the main course runway.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_course_cockpit.py tests/test_course_workflow.py tests/test_learning_plan_service.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`.
- Archive: `archive/agent_prompts/epoch_course_confidence_dip_detector_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-course-confidence-dip-detector/`.

### epoch-course-next-session-promise — 2026-05-01

- Goal: End each course session with a concise next-session promise derived from course state, retrieval outcomes, or runway progress, then surface that promise on the next resume when still valid.
- Delivered: End each course session with a concise next-session promise derived from course state, retrieval outcomes, or runway progress, then surface that promise on the next resume when still valid.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_course_cockpit.py tests/test_course_workflow.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`.
- Archive: `archive/agent_prompts/epoch_course_next_session_promise_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-course-next-session-promise/`.

### epoch-course-recovery-budget-slider — 2026-05-01

- Goal: Add a course recovery budget control so returning learners can choose a realistic catch-up size for today while preserving the system's recommended default and keeping remaining overdue work visible.
- Delivered: Add a course recovery budget control so returning learners can choose a realistic catch-up size for today while preserving the system's recommended default and keeping remaining overdue work visible.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_course_cockpit.py tests/test_course_workflow.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`.
- Archive: `archive/agent_prompts/epoch_course_recovery_budget_slider_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-course-recovery-budget-slider/`.

### epoch-home-mode-intent-ordering — 2026-05-01

- Goal: Reorder the 6 primary home mode cards by learner context (resume, due burden, recent mode) while keeping the complete grid visible and preserving direct navigation + US-14.1 primary CTA rules.
- Delivered: Reorder the 6 primary home mode cards by learner context (resume, due burden, recent mode) while keeping the complete grid visible and preserving direct navigation + US-14.1 primary CTA rules.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ui_helpers.py -v --tb=short`, `npm run test:e2e:smoke -- tests/e2e/home_mode_selection.spec.ts`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`.
- Archive: `archive/agent_prompts/epoch_home_mode_intent_ordering_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-home-mode-intent-ordering/`.

### epoch-e7-1-tutor-gate-reliability — 2026-05-01

- Goal: Tutor regression gate distinguishes pass, regression_fail, and infra_fail with deterministic healthy/degraded smoke paths.
- Delivered: Tutor regression gate status contract and deterministic smoke diagnostics (registry backfill from historical E7.1).
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_check_tutor_regression_gate.py tests/test_smoke_tutor_regression_gate.py -v --tb=short`
- Notes: `doc/backlog_registry.yaml` backfill 2026-05-01; source `doc/epochs/e7.md`.

### epoch-e7-2-eval-artifact-retention — 2026-05-01

- Goal: Tutor regression gate writes stable JSON reports and retains CI artifacts for triage.
- Delivered: Report JSON envelope, CI artifact retention, and triage runbook (registry backfill from historical E7.2).
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_check_tutor_regression_gate.py -v --tb=short`
- Notes: `doc/backlog_registry.yaml` backfill 2026-05-01; source `doc/epochs/e7.md`.

### epoch-e7-3-gate-triage-automation — 2026-05-01

- Goal: Tutor gate report schema_version 2 includes triage next_action, owner_hint, and rerun_recommended.
- Delivered: Automated tutor-gate triage fields in reports, smoke payloads, and CI summary (registry backfill from historical E7.3).
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_check_tutor_regression_gate.py tests/test_smoke_tutor_regression_gate.py -v --tb=short`
- Notes: `doc/backlog_registry.yaml` backfill 2026-05-01; source `doc/epochs/e7.md`.

### epoch-e8-1-cjm-outcome-discipline — 2026-05-01

- Goal: User-value epochs are bounded to small CJM/user-story outcomes with verifiable DoD.
- Delivered: E8 epoch discipline documented and used as planning guardrail (registry backfill from historical E8.1).
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`
- Notes: `doc/backlog_registry.yaml` backfill 2026-05-01; source `doc/epochs/e8.md`.

### epoch-e8-2-active-backlog-cleanup — 2026-05-01

- Goal: Active tasklist is kept compact; closed E8.x details move to archived history instead of weekly backlog.
- Delivered: E8.x historical details archived outside active tasklist (registry backfill from historical E8.2).
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`
- Notes: `doc/backlog_registry.yaml` backfill 2026-05-01; source `doc/changelog.md` roadmap cleanup entry.

### epoch-e5-0-versioned-learner-profile-history — 2026-05-01

- Goal: Versioned learner profile history is persisted in personalized_learner_model_history_json.
- Delivered: Versioned learner profile history is persisted in personalized_learner_model_history_json. (registry backfill; see notes).
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_learner_model_service.py -v --tb=short`
- Notes: Backfill 2026-05-01 from historical package E5.0; source: doc/epochs/e5.md and doc/changelog.md.

### epoch-e5-1-migration-safe-mastery-rehydrate — 2026-05-01

- Goal: Mastery vector rehydrates from learner profile history when current mastery is orphaned after index changes.
- Delivered: Mastery vector rehydrates from learner profile history when current mastery is orphaned after index changes. (registry backfill; see notes).
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_learner_model_service.py -v --tb=short`
- Notes: Backfill 2026-05-01 from historical package E5.1; source: doc/epochs/e5.md and doc/changelog.md.

### epoch-e5-2-learner-profile-history-api — 2026-05-01

- Goal: Expose learner profile history diagnostics through /kb/learner/profile-history.
- Delivered: Expose learner profile history diagnostics through /kb/learner/profile-history. (registry backfill; see notes).
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_api.py::test_learner_profile_history_endpoint -v --tb=short`
- Notes: Backfill 2026-05-01 from historical package E5.2; source: doc/epochs/e5.md and doc/changelog.md.

### epoch-e5-3-learner-migration-metrics — 2026-05-01

- Goal: Expose learner migration rollups through /metrics/learner and get_learner_profile_migration_metrics.
- Delivered: Expose learner migration rollups through /metrics/learner and get_learner_profile_migration_metrics. (registry backfill; see notes).
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_learner_model_service.py tests/test_api.py -k learner -v --tb=short`
- Notes: Backfill 2026-05-01 from historical package E5.3; source: doc/epochs/e5.md and doc/changelog.md.

### epoch-e5-4-learner-migration-slo-alert — 2026-05-01

- Goal: Learner migration SLO alert is evaluated from learner_rehydrated_rate.
- Delivered: Learner migration SLO alert is evaluated from learner_rehydrated_rate. (registry backfill; see notes).
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_metrics.py tests/test_config.py -k learner -v --tb=short`
- Notes: Backfill 2026-05-01 from historical package E5.4; source: doc/epochs/e5.md and doc/changelog.md.

### epoch-e5-5-learner-migration-gate-command — 2026-05-01

- Goal: Ready learner migration quality-gate command exits non-zero on failed migration thresholds.
- Delivered: Ready learner migration quality-gate command exits non-zero on failed migration thresholds. (registry backfill; see notes).
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_check_learner_migration_gate.py -v --tb=short`
- Notes: Backfill 2026-05-01 from historical package E5.5; source: doc/epochs/e5.md and doc/changelog.md.

### epoch-e5-6-learner-migration-smoke-command — 2026-05-01

- Goal: Smoke command generates learner profile history and runs the learner migration gate.
- Delivered: Smoke command generates learner profile history and runs the learner migration gate. (registry backfill; see notes).
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smoke_learner_migration_gate.py -v --tb=short`
- Notes: Backfill 2026-05-01 from historical package E5.6; source: doc/epochs/e5.md and doc/changelog.md.

### epoch-e5-7-learner-migration-ci-gate — 2026-05-01

- Goal: Learner migration smoke gate runs in CI on pull_request and push.
- Delivered: Learner migration smoke gate runs in CI on pull_request and push. (registry backfill; see notes).
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smoke_learner_migration_gate.py tests/test_check_learner_migration_gate.py -v --tb=short`
- Notes: Backfill 2026-05-01 from historical package E5.7; source: doc/epochs/e5.md and doc/changelog.md.

### epoch-e5-8-learner-lineage-sync-on-activation — 2026-05-01

- Goal: Index activation eagerly syncs learner DB lineage through apply_index_activation_hooks.
- Delivered: Index activation eagerly syncs learner DB lineage through apply_index_activation_hooks. (registry backfill; see notes).
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_index_backup.py::test_apply_index_activation_hooks_syncs_learner_lineage -v --tb=short`
- Notes: Backfill 2026-05-01 from historical package E5.8; source: doc/epochs/e5.md and doc/changelog.md.

### epoch-e7-0-production-health-bootstrap — 2026-05-01

- Goal: Bootstrap production-health direction after E6 stabilization.
- Delivered: Bootstrap production-health direction after E6 stabilization. (registry backfill; see notes).
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`
- Notes: Backfill 2026-05-01 from historical package E7.0; source: doc/epochs/e7.md and doc/changelog.md.

### epoch-check-backlog-drift-token-registry — 2026-05-01

- Goal: Зарегистрировать scripts/check_backlog_drift.py в doc/token_safety_registry.json (full_read или forbidden + safe_hint); добавить путь в MEASURE_PATHS scripts/measure_token_registry.py; пересобрать мет
- Delivered: Зарегистрировать scripts/check_backlog_drift.py в doc/token_safety_registry.json (full_read или forbidden + safe_hint); добавить путь в MEASURE_PATHS scripts/measure_token_registry.py; пересобрать метрики --write; зелёный контур tests/test_token_registry.py + check_readset по read_set_hint + lint ре
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts/measure_token_registry.py --write`, `.\.venv\Scripts\python.exe -m pytest tests/test_token_registry.py -v`, `.\.venv\Scripts\python.exe scripts/check_readset.py --profile relaxed doc/token_safety_registry.json scripts/measure_token_registry.py scripts/check_backlog_drift.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`, `.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py`.
- Archive: `archive/agent_prompts/epoch_check_backlog_drift_token_registry_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-check-backlog-drift-token-registry/`.

### epoch-ocr-docling-story-gate — 2026-05-01

- Goal: Product/Analyst gate for deferred ocr-docling: define whether non-text corpus ingest is a real learner pain, create or update one open US with acceptance criteria, and keep OCR/Docling implementation 
- Delivered: Создана открытая **US-2.3** (`doc/user_stories/us-2.3.md`) с acceptance для non-text ingest в KB; граница с US-15.5; `ocr-docling` остаётся deferred. История не закрыта пакетом (implementation — будущие эпохи).
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync --strict`, `.\.venv\Scripts\python.exe scripts/rebuild_user_stories_index.py --write`, `.\.venv\Scripts\python.exe scripts/rebuild_user_stories_index.py --check`.
- Archive: `archive/agent_prompts/epoch_ocr_docling_story_gate_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-ocr-docling-story-gate/`.

### epoch-source-readiness-diagnostic-story — 2026-05-01

- Goal: Product/Analyst story definition for a source-readiness diagnostic: learner can see which files are text-ready, which need OCR/extraction, which are problematic, and the single safest next ingest acti
- Delivered: Product/Analyst story definition for a source-readiness diagnostic: learner can see which files are text-ready, which need OCR/extraction, which are problematic, and the single safest next ingest action before asking the first question.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts/rebuild_user_stories_index.py --write`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync --strict`, `.\.venv\Scripts\python.exe scripts/rebuild_user_stories_index.py --write`, `.\.venv\Scripts\python.exe scripts/rebuild_user_stories_index.py --check`.
- Archive: `archive/agent_prompts/epoch_source_readiness_diagnostic_story_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-source-readiness-diagnostic-story/`.

### epoch-us-2.3-non-text-corpus-contract — 2026-05-01

- Goal: Зафиксировать learner-facing сценарий и контракт индексации для non-text корпуса (сканы PDF, изображения в data/): форматы, ожидаемое поведение относительно текстовых файлов, явное отличие от US-15.5 
- Delivered: Документация в `doc/user_guide.md`, `doc/user_guide_details.md` (якорь `us-2-3-non-text-corpus`); модуль-якорь `scripts/us_2_3_non_text_corpus_contract.py`. **US-2.3** остаётся **open** — acceptance про поискоспособные чанки в общем индексе ждёт реализации OCR/Docling.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync --strict`, `.\.venv\Scripts\python.exe scripts/check_readset.py --profile relaxed doc/user_guide.md doc/user_guide_details.md`.
- Archive: `archive/agent_prompts/epoch_us_2_3_non_text_corpus_contract_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-us-2.3-non-text-corpus-contract/`.

### epoch-ocr-docling-ingest-phase1 — 2026-05-01

- Goal: Первый сквозной ingest non-text (Docling/OCR) в общий индекс с трассируемыми источниками в ответах; граница с US-15.5 задокументирована; deferred ocr-docling снимается или обновляется по итогу.
- Delivered: Первый сквозной ingest non-text (Docling/OCR) в общий индекс с трассируемыми источниками в ответах; граница с US-15.5 задокументирована; deferred ocr-docling снимается или обновляется по итогу.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ingestion_content_state.py tests/test_ocr_docling_phase1.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict`.
- Archive: `archive/agent_prompts/epoch_ocr_docling_ingest_phase1_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-ocr-docling-ingest-phase1/`.

### epoch-us-2-4-source-readiness-mvp — 2026-05-01

- Goal: Learner-facing диагностика готовности файлов в data/: классы text-ready / needs OCR / problematic, один primary next action до первого Q&A; согласовано с US-2.3 (диагностика не заменяет OCR-ingest).
- Delivered: Learner-facing диагностика готовности файлов в data/: классы text-ready / needs OCR / problematic, один primary next action до первого Q&A; согласовано с US-2.3 (диагностика не заменяет OCR-ingest).
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ui_helpers.py -v --tb=short`, `.\.venv\Scripts\python.exe -m pytest tests/test_source_readiness_mvp.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync --strict`.
- Archive: `archive/agent_prompts/epoch_us_2_4_source_readiness_mvp_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-us-2-4-source-readiness-mvp/`.

### epoch-us-2-3-chunk-index-proof — 2026-05-02

- Goal: allow_verification_only
Автотесты доказывают появление searchable чанков в общем индексе для согласованного «лёгкого» non-text сценария (например PDF с текстовым слоем или stub); явная граница что ост
- Delivered: allow_verification_only
Автотесты доказывают появление searchable чанков в общем индексе для согласованного «лёгкого» non-text сценария (например PDF с текстовым слоем или stub); явная граница что остаётся для полного OCR.
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ingestion_content_state.py -v --tb=short`, `.\.venv\Scripts\python.exe -m pytest tests/test_chunk_index_proof.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict`.
- Archive: `archive/agent_prompts/epoch_us_2_3_chunk_index_proof_exec_prompt_quick_2026-05-01.md`, `archive/team_artifacts/epoch-us-2-3-chunk-index-proof/`.

### epoch-mot2-wait-ux-engagement — 2026-05-02

- Goal: Quick Answer: педагогический runway-копи, переменный микро-фидбек ожидания, ненавязчивое подкрепление при быстром успешном ответе; пороги latency согласованы с eval gate; формат micro-quiz не меняется
- Delivered: Quick Answer: педагогический runway-копи, переменный микро-фидбек ожидания, ненавязчивое подкрепление при быстром успешном ответе; пороги latency согласованы с eval gate; формат micro-quiz не меняется.
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ui_helpers.py -v --tb=short`, `.\.venv\Scripts\python.exe -m pytest tests/test_query_service.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync --strict`.
- Archive: `archive/team_artifacts/epoch-mot2-wait-ux-engagement/`.

### workflow-dx-p4-common-rules — 2026-05-03

- Goal: Создать doc/team_workflow/_common_rules.md с повторяющимися блоками: Windows/PowerShell note, SSoT warning, token budget, sync command. Заменить дублирующиеся блоки ссылками в 6+ промпт-файлах.
- Delivered: Создать doc/team_workflow/_common_rules.md с повторяющимися блоками: Windows/PowerShell note, SSoT warning, token budget, sync command. Заменить дублирующиеся блоки ссылками в 6+ промпт-файлах.
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.venv\Scripts\python.exe -m pytest tests/test_workflow_router.py -q`.
- Archive: `archive/team_artifacts/workflow-dx-p4-common-rules/`.

### epoch-arch-review-p2-inline-logging-noqa — 2026-05-03

- Goal: Пакет P2: ко всем except Exception, за которыми следует inline import logging, добавить # noqa: BLE001; regression guard в scripts/arch_regression_guards.py. Finding: AR-2026-05-02-005.
- Delivered: Пакет P2: ко всем except Exception, за которыми следует inline import logging, добавить # noqa: BLE001; regression guard в scripts/arch_regression_guards.py. Finding: AR-2026-05-02-005.
- Mode: verification_only.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ui_helpers.py tests/test_query_service.py -x --tb=short -q`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync --strict`.
- Archive: `archive/team_artifacts/epoch-arch-review-p2-inline-logging-noqa/`.

### epoch-arch-review-p3-orphaned-modules — 2026-05-03

- Goal: Пакет P3: course_graduation.py / diagnostic_service.py — runtime consumers в app/ или удаление по решению owner. Finding: AR-2026-04-29-004 (остаток после warmup_planner).
- Delivered: Пакет P3: course_graduation.py / diagnostic_service.py — runtime consumers в app/ или удаление по решению owner. Finding: AR-2026-04-29-004 (остаток после warmup_planner).
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_course_graduation.py tests/test_diagnostic_service.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync --strict`.
- Archive: `archive/team_artifacts/epoch-arch-review-p3-orphaned-modules/`.

### epoch-arch-review-p4-ingestion-loader-decompose — 2026-05-03

- Goal: Пакет P4: декомпозиция app/ingestion_loader.py и сжатие _build_index_partial до thin orchestrator (≤80L); при необходимости новый модуль фаз. Findings: AR-2026-05-02-001, AR-2026-05-02-002.
- Delivered: Пакет P4: декомпозиция app/ingestion_loader.py и сжатие _build_index_partial до thin orchestrator (≤80L); при необходимости новый модуль фаз. Findings: AR-2026-05-02-001, AR-2026-05-02-002.
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ingestion_content_state.py tests/test_api.py -x --tb=short -q`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync --strict`.
- Archive: `archive/agent_prompts/epoch_arch_review_p4_ingestion_loader_decompose_exec_prompt_quick_2026-05-03.md`, `archive/team_artifacts/epoch-arch-review-p4-ingestion-loader-decompose/`.

### epoch-arch-review-p5e-telegram-handler-tests — 2026-05-03

- Goal: Эпик E (P5 backlog): поведенческие pytest cmd_help/cmd_ask с mock Message (без сети). Finding: AR-2026-04-29-014.
- Delivered: Эпик E (P5 backlog): поведенческие pytest cmd_help/cmd_ask с mock Message (без сети). Finding: AR-2026-04-29-014.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_telegram_parsing.py tests/test_telegram_handlers.py -v --tb=short`.
- Archive: `archive/agent_prompts/epoch_arch_review_p5e_telegram_handler_tests_exec_prompt_quick_2026-05-03.md`, `archive/team_artifacts/epoch-arch-review-p5e-telegram-handler-tests/`.

### epoch-arch-review-p5d-learning-plan-split — 2026-05-03

- Goal: Эпик D: разбиение learning_plan_service.py (generation vs adaptive); файлы ≤600L. Finding: AR-2026-05-02-003.
- Delivered: Эпик D: разбиение learning_plan_service.py (generation vs adaptive); файлы ≤600L. Finding: AR-2026-05-02-003.
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/ -k plan -x --tb=short -q`.
- Archive: `archive/agent_prompts/epoch_arch_review_p5d_learning_plan_split_exec_prompt_quick_2026-05-03.md`, `archive/team_artifacts/epoch-arch-review-p5d-learning-plan-split/`.

### epoch-mot2-two-stage-answer — 2026-05-03

- Goal: Двухступенчатый путь ответа: явные критерии раннего выхода vs полная генерация; расширение/обновление eval и latency gate; лимит контекста на запрос; без смены формата micro-quiz.
- Delivered: Двухступенчатый путь ответа: явные критерии раннего выхода vs полная генерация; расширение/обновление eval и latency gate; лимит контекста на запрос; без смены формата micro-quiz.
- Mode: verification_only.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_query_service.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync --strict`.
- Archive: `archive/agent_prompts/epoch_mot2_two_stage_answer_exec_prompt_quick_2026-05-03.md`, `archive/team_artifacts/epoch-mot2-two-stage-answer/`.

### epoch-arch-review-p5a-knowledge-service-split — 2026-05-03

- Goal: Эпик A: декомпозиция knowledge_service.py — synthesis / catalog / planning + тонкий фасад; закрытие AR-2026-04-29-003. Каждый новый модуль ≤600L.
- Delivered: Эпик A: декомпозиция knowledge_service.py — synthesis / catalog / planning + тонкий фасад; закрытие AR-2026-04-29-003. Каждый новый модуль ≤600L.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_knowledge_service.py tests/test_api.py -k knowledge -x --tb=short -q`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync --strict`.
- Archive: `archive/team_artifacts/epoch-arch-review-p5a-knowledge-service-split/`.

### epoch-arch-review-p5c-ui-tabs-decompose — 2026-05-03

- Goal: Эпик C: декомпозиция render_topics_tab / render_query_tab в app/ui; целевой размер оркестраторов ≤200L (промежуточно). Finding: AR-2026-04-21-006.
- Delivered: Эпик C: декомпозиция render_topics_tab / render_query_tab в app/ui; целевой размер оркестраторов ≤200L (промежуточно). Finding: AR-2026-04-21-006.
- Mode: verification_only.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ui_helpers.py -v --tb=short`.
- Archive: `archive/agent_prompts/epoch_arch_review_p5c_ui_tabs_decompose_exec_prompt_quick_2026-05-03.md`, `archive/team_artifacts/epoch-arch-review-p5c-ui-tabs-decompose/`.

### epoch-arch-review-p5b-god-modules-wave1-ingestion — 2026-05-03

- Goal: Волна B1: снижение размера ingestion.py + ingestion_loader.py (после P4) до правил >600L; пересчёт списка >600L. Finding: AR-2026-04-21-005 (часть).
- Delivered: Волна B1: снижение размера ingestion.py + ingestion_loader.py (после P4) до правил >600L; пересчёт списка >600L. Finding: AR-2026-04-21-005 (часть).
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ingestion_content_state.py tests/test_ingestion_reindex.py -x --tb=short -q`.
- Archive: `archive/agent_prompts/epoch_arch_review_p5b_god_modules_wave1_ingestion_exec_prompt_quick_2026-05-03.md`, `archive/team_artifacts/epoch-arch-review-p5b-god-modules-wave1-ingestion/`.

### epoch-arch-review-p5b-god-modules-wave2-product-services — 2026-05-03

- Goal: Волна B2: quiz_service.py, learner_model_service.py и др. продуктовые сервисы >600L — осмысленные сплиты без смены API. Finding: AR-2026-04-21-005.
- Delivered: Волна B2: quiz_service.py, learner_model_service.py и др. продуктовые сервисы >600L — осмысленные сплиты без смены API. Finding: AR-2026-04-21-005.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_quiz_adaptive.py tests/test_learner_model_service.py -x --tb=short -q`.
- Archive: `archive/agent_prompts/epoch_arch_review_p5b_god_modules_wave2_product_services_exec_prompt_quick_2026-05-03.md`, `archive/team_artifacts/epoch-arch-review-p5b-god-modules-wave2-product-services/`.

### epoch-arch-review-p5b-god-modules-wave3-query-graph — 2026-05-03

- Goal: Волна B3: query_service.py / knowledge_graph.py — только после ADR/epoch согласования; верифицируемый сплит без изменения HTTP/UI контрактов. Finding: AR-2026-04-21-005.
- Delivered: Волна B3: query_service.py / knowledge_graph.py — только после ADR/epoch согласования; верифицируемый сплит без изменения HTTP/UI контрактов. Finding: AR-2026-04-21-005.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_query_service.py tests/test_api.py -x --tb=short -q`.
- Archive: `archive/agent_prompts/epoch_arch_review_p5b_god_modules_wave3_query_graph_exec_prompt_quick_2026-05-03.md`, `archive/team_artifacts/epoch-arch-review-p5b-god-modules-wave3-query-graph/`.

### epoch-arch-review-p5b-god-modules-wave4-infra-config — 2026-05-03

- Goal: Волна B4: provider.py, api_models.py, user_state_core.py, metrics_summarizer.py, prompts.py (пакетная структура prompts/) — снижение >600L без feature creep. Finding: AR-2026-04-21-005.
- Delivered: Волна B4: provider.py, api_models.py, user_state_core.py, metrics_summarizer.py, prompts.py (пакетная структура prompts/) — снижение >600L без feature creep. Finding: AR-2026-04-21-005.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_user_state.py tests/test_api.py -x --tb=short -q`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync --strict`.
- Archive: `archive/agent_prompts/epoch_arch_review_p5b_god_modules_wave4_infra_config_exec_prompt_quick_2026-05-03.md`, `archive/team_artifacts/epoch-arch-review-p5b-god-modules-wave4-infra-config/`.

### workflow-dx-p6-cursor-sdk-trigger — 2026-05-03

- Goal: SDK Trigger — убрать единственный оставшийся ручной шаг в execution_auto и ready_orch (открыть Composer + doc/current_task.md). Создать scripts/cursor_agent_trigger.ts (~50L): читает current_task.md, 
- Delivered: SDK Trigger — убрать единственный оставшийся ручной шаг в execution_auto и ready_orch (открыть Composer + doc/current_task.md). Создать scripts/cursor_agent_trigger.ts (~50L): читает current_task.md, вызывает Agent.prompt через @cursor/sdk, CURSOR_API_KEY только из env. Расширить scripts/workflow.py
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.venv\Scripts\python.exe -m pytest tests/test_workflow_router.py -v`.
- Archive: `archive/agent_prompts/workflow_dx_p6_cursor_sdk_trigger_exec_prompt_quick_2026-05-03.md`, `archive/team_artifacts/workflow-dx-p6-cursor-sdk-trigger/`.

### epoch-cjm-pain-map-ssot-sync — 2026-05-03

- Goal: Сгенерированная таблица Pain → US в doc/cjm.md §7 снова согласована с doc/user_stories_index.json и статусом US-3.6 (closed / epoch-mot2-two-stage-answer); planning/agents не видят ложный «open» gap.
- Delivered: Сгенерированная таблица Pain → US в doc/cjm.md §7 снова согласована с doc/user_stories_index.json и статусом US-3.6 (closed / epoch-mot2-two-stage-answer); planning/agents не видят ложный «open» gap.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts/rebuild_user_stories_index.py --write`, `.\.venv\Scripts\python.exe scripts/rebuild_user_stories_index.py --check`, `.\.venv\Scripts\python.exe scripts/check_backlog_drift.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/agent_prompts/epoch_cjm_pain_map_ssot_sync_exec_prompt_quick_2026-05-03.md`, `archive/team_artifacts/epoch-cjm-pain-map-ssot-sync/`.

### epoch-cursor-sdk-trigger-reliability — 2026-05-04

- Goal: Усилить надёжность Cursor SDK trigger после workflow-dx-p6: предсказуемые коды выхода scripts/cursor_agent_trigger.ts (сетевые/конфиг ошибки, таймауты/повторы по политике KISS), понятные сообщения в s
- Delivered: Усилить надёжность Cursor SDK trigger после workflow-dx-p6: предсказуемые коды выхода scripts/cursor_agent_trigger.ts (сетевые/конфиг ошибки, таймауты/повторы по политике KISS), понятные сообщения в scripts/workflow.py при rc≠0; без изменения контракта plan-next (ручной accept). Обновить релевантную
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_workflow_router.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/agent_prompts/epoch_cursor_sdk_trigger_reliability_exec_prompt_quick_2026-05-04.md`, `archive/team_artifacts/epoch-cursor-sdk-trigger-reliability/`.

### epoch-us19-2-tutor-handoff-ux — 2026-05-05

- Goal: Плавный переход Q&A→Tutor (MoT #3): передача полного контекста (вопрос, тема, источники, confidence), краткое резюме при открытии tutor-режима, переходная анимация 300–500ms и визуальная связь с исход
- Delivered: Плавный переход Q&A→Tutor (MoT #3): передача полного контекста (вопрос, тема, источники, confidence), краткое резюме при открытии tutor-режима, переходная анимация 300–500ms и визуальная связь с исходным ответом; обработка неполного Context_Payload (AC6 US-19.2). Без изменения HTTP-контрактов вне со
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_tutor_orchestrator.py tests/test_pipeline_steps.py -v --tb=short`, `.\.venv\Scripts\python.exe -m pytest tests/test_ui_helpers.py -v --tb=short`.
- Archive: `archive/agent_prompts/epoch_us19_2_tutor_handoff_ux_exec_prompt_quick_2026-05-05.md`, `archive/team_artifacts/epoch-us19-2-tutor-handoff-ux/`.

### ux-foundation-parsers-contracts — 2026-05-05

- Goal: Typed UX data contracts для AnswerObject, ContextObject и SessionStatsObject. Пакет снижает риск хрупкого string parsing перед UI-полировкой и создаёт foundation для wait UX и flashcard analytics; Con
- Delivered: Typed UX data contracts для AnswerObject, ContextObject и SessionStatsObject. Пакет снижает риск хрупкого string parsing перед UI-полировкой и создаёт foundation для wait UX и flashcard analytics; ContextObject remains available as a supporting contract for the already closed tutor handoff slice.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_answer_parser.py tests/test_tutor_context_parser.py tests/test_session_analytics_parser.py -v`.
- Archive: `archive/agent_prompts/ux_foundation_parsers_contracts_exec_prompt_quick_2026-05-05.md`, `archive/team_artifacts/ux-foundation-parsers-contracts/`.

### ux-first-answer-wait-flow — 2026-05-05

- Goal: Perceived-latency улучшение первого ответа: first visible feedback, skeleton/progress state, progressive reveal и clear retry state без изменения LLM provider layer.
- Delivered: Perceived-latency улучшение первого ответа: first visible feedback, skeleton/progress state, progressive reveal и clear retry state без изменения LLM provider layer.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ui_wait_ux.py tests/test_answer_parser.py -v`.
- Archive: `archive/agent_prompts/ux_first_answer_wait_flow_exec_prompt_quick_2026-05-05.md`, `archive/team_artifacts/ux-first-answer-wait-flow/`.

### ux-mastery-celebration-analytics — 2026-05-05

- Goal: Motivational loop after study/review: flashcard session analytics, difficult-topic CTA, skippable graduation surface and badge persistence through existing services.
- Delivered: Motivational loop after study/review: flashcard session analytics, difficult-topic CTA, skippable graduation surface and badge persistence through existing services.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_session_analytics_parser.py tests/test_flashcard_service.py tests/test_ui_graduation_overlay.py -v`.
- Archive: `archive/agent_prompts/ux_mastery_celebration_analytics_exec_prompt_quick_2026-05-05.md`, `archive/team_artifacts/ux-mastery-celebration-analytics/`.

### ux-home-hub-navigation-polish — 2026-05-05

- Goal: Home hub makes the next best action visually obvious through resume priority, due flashcard badge, stable mode layout and restrained hover/focus polish.
- Delivered: Home hub makes the next best action visually obvious through resume priority, due flashcard badge, stable mode layout and restrained hover/focus polish.
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ui_home_hub_enhanced.py tests/test_ui_helpers.py -v`.
- Archive: `archive/agent_prompts/ux_home_hub_navigation_polish_exec_prompt_quick_2026-05-05.md`, `archive/team_artifacts/ux-home-hub-navigation-polish/`.

### epoch-team-workflow-top-level-md-budget-2026-05 — 2026-05-06

- Goal: Сократить число верхнеуровневых *.md в doc/team_workflow/ до ≤48 (north star wave-workflow-dx): часть файлов — в archive/doc_team_workflow/ или слияние в существующие каркасы; README.md обновить так, 
- Delivered: Сократить число верхнеуровневых *.md в doc/team_workflow/ до ≤48 (north star wave-workflow-dx): часть файлов — в archive/doc_team_workflow/ или слияние в существующие каркасы; README.md обновить так, чтобы навигация не ломалась; добавить проверку в scripts/arch_regression_guards.py (count только *.m
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts\arch_regression_guards.py`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/agent_prompts/epoch_team_workflow_top_level_md_budget_2026_05_exec_prompt_quick_2026-05-05.md`, `archive/team_artifacts/epoch-team-workflow-top-level-md-budget-2026-05/`.

### epoch-smart-study-router-card — 2026-05-06

- Goal: Define the first Smart Study Router delivery slice: a local deterministic recommendation contract and shared Explainable Next Step Card that shows one primary next study action, a short "why now" reas
- Delivered: Define the first Smart Study Router delivery slice: a local deterministic recommendation contract and shared Explainable Next Step Card that shows one primary next study action, a short "why now" reason, and 2-4 safe secondary actions without hiding tutor, quiz, flashcards, or dashboard entry points
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py tests/test_ui_helpers.py -v --tb=short`, `npm run test:e2e:smoke -- tests/e2e/smart_study_router.spec.ts`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/team_artifacts/epoch-smart-study-router-card/`.

### epoch-smart-study-router-core-policies — 2026-05-06

- Goal: Add the first Smart Study Router policy set on top of the shared recommendation contract: `cards_due -> Повторить`, `quiz_failed -> Разобрать слабое место`, and `answer_ready -> Учить тему`. Each reco
- Delivered: Add the first Smart Study Router policy set on top of the shared recommendation contract: `cards_due -> Повторить`, `quiz_failed -> Разобрать слабое место`, and `answer_ready -> Учить тему`. Each recommendation must include a short "why now" reason from local learning state and preserve tutor, quiz,
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py tests/test_ui_helpers.py -v --tb=short`, `npm run test:e2e:smoke -- tests/e2e/smart_study_router.spec.ts`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/team_artifacts/epoch-smart-study-router-core-policies/`.

### epoch-smart-study-router-trust-control — 2026-05-06

- Goal: Preserve the ideation ideas that should follow the core policy set: source-trust routing for low-confidence answers, a compact reason trace for explainability, and "skip with memory" so declining a re
- Delivered: Preserve the ideation ideas that should follow the core policy set: source-trust routing for low-confidence answers, a compact reason trace for explainability, and "skip with memory" so declining a recommendation does not become a dead end. All behavior remains local-first and must not hide tutor, q
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py tests/test_ui_helpers.py -v --tb=short`, `npm run test:e2e:smoke -- tests/e2e/smart_study_router.spec.ts`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/team_artifacts/epoch-smart-study-router-trust-control/`.

### epoch-smart-study-router-accessibility-harness — 2026-05-06

- Goal: Preserve the ideation ideas that keep the router honest and usable: accessible no-dead-end behavior, a local preview/fixture harness for router states, and compact preservation of existing tutor, quiz
- Delivered: Preserve the ideation ideas that keep the router honest and usable: accessible no-dead-end behavior, a local preview/fixture harness for router states, and compact preservation of existing tutor, quiz, flashcard, and dashboard entry points beside the recommendation.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py tests/test_ui_helpers.py -v --tb=short`, `npm run test:e2e:smoke -- tests/e2e/smart_study_router.spec.ts`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/team_artifacts/epoch-smart-study-router-accessibility-harness/`.

### epoch-qbi-data-deletion-governance — 2026-05-06

- Goal: Document and implement a confirmation-gated complete data deletion flow for local index, user-state stores, logs, history, feedback, cost logs, and verification checks.
- Delivered: Document and implement a confirmation-gated complete data deletion flow for local index, user-state stores, logs, history, feedback, cost logs, and verification checks.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_data_deletion.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/agent_prompts/epoch_qbi_data_deletion_governance_exec_prompt_quick_2026-05-06.md`, `archive/team_artifacts/epoch-qbi-data-deletion-governance/`.

### epoch-qbi-terminology-limitations-sync — 2026-05-06

- Goal: Migrate user-facing confidence language to retrieval_confidence with backward-compatible API behavior, document limitations, and remove absolute quality/production claims unless tied to eval-run evide
- Delivered: Migrate user-facing confidence language to retrieval_confidence with backward-compatible API behavior, document limitations, and remove absolute quality/production claims unless tied to eval-run evidence.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_api.py::test_query_response_confidence_backward_compatibility tests/test_ui_helpers.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/team_artifacts/epoch-qbi-terminology-limitations-sync/`.

### epoch-qbi-source-readiness-contract-parity — 2026-05-06

- Goal: Close the residual gap between the closed US-2.4 source-readiness MVP and quality-breakthrough Requirement 11: stable `/kb/source-readiness` contract, explicit text_ready / needs_ocr / extraction_fail
- Delivered: Close the residual gap between the closed US-2.4 source-readiness MVP and quality-breakthrough Requirement 11: stable `/kb/source-readiness` contract, explicit text_ready / needs_ocr / extraction_failed / unsupported_format categories, readiness score, and actionable items.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_source_readiness_mvp.py tests/test_source_readiness_contract.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/agent_prompts/epoch_qbi_source_readiness_contract_parity_exec_prompt_quick_2026-05-06.md`, `archive/team_artifacts/epoch-qbi-source-readiness-contract-parity/`.

### epoch-qbi-golden-eval-dataset — 2026-05-06

- Goal: Create a defense-specific golden eval dataset with qa, keyword, overview, synthesis, negative, and injection categories; include schema validation and round-trip serialization coverage before implemen
- Delivered: Create a defense-specific golden eval dataset with qa, keyword, overview, synthesis, negative, and injection categories; include schema validation and round-trip serialization coverage before implementation expands into runners.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_eval_dataset.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/agent_prompts/epoch_qbi_golden_eval_dataset_exec_prompt_quick_2026-05-06.md`, `archive/team_artifacts/epoch-qbi-golden-eval-dataset/`.

### epoch-qbi-retrieval-mode-comparison — 2026-05-06

- Goal: Add a retrieval-mode comparison engine for vector_only, hybrid, bm25_only, and doc_then_chunk with recall@k, MRR, hit-rate, and p50/p95/p99 latency metrics over the defense dataset.
- Delivered: Add a retrieval-mode comparison engine for vector_only, hybrid, bm25_only, and doc_then_chunk with recall@k, MRR, hit-rate, and p50/p95/p99 latency metrics over the defense dataset.
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_eval_retrieval_comparison.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/agent_prompts/epoch_qbi_retrieval_mode_comparison_exec_prompt_quick_2026-05-06.md`, `archive/team_artifacts/epoch-qbi-retrieval-mode-comparison/`.

### epoch-qbi-baseline-regression-gate — 2026-05-06

- Goal: Add baseline report serialization, baseline comparison, promotion workflow, and regression-gate output for defense eval runs while preserving existing AQE/router gate contracts.
- Delivered: Add baseline report serialization, baseline comparison, promotion workflow, and regression-gate output for defense eval runs while preserving existing AQE/router gate contracts.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_baseline_comparator.py tests/test_eval_service.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/team_artifacts/epoch-qbi-baseline-regression-gate/`.

### epoch-qbi-adversarial-corpus-runner — 2026-05-06

- Goal: Add RAG adversarial corpus and runner for prompt injection inside documents, conflicting sources, and no-answer cases with guardrail-effectiveness and grounding metrics.
- Delivered: Add RAG adversarial corpus and runner for prompt injection inside documents, conflicting sources, and no-answer cases with guardrail-effectiveness and grounding metrics.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_adversarial_runner.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/agent_prompts/epoch_qbi_adversarial_corpus_runner_exec_prompt_quick_2026-05-06.md`, `archive/team_artifacts/epoch-qbi-adversarial-corpus-runner/`.

### epoch-qbi-adversarial-regression-gate — 2026-05-06

- Goal: Integrate adversarial RAG metrics into baseline comparison and regression gate thresholds with clear failure messages for injection, grounding, and no-answer regressions.
- Delivered: Integrate adversarial RAG metrics into baseline comparison and regression gate thresholds with clear failure messages for injection, grounding, and no-answer regressions.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_adversarial_runner.py tests/test_baseline_comparator.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/agent_prompts/epoch_qbi_adversarial_regression_gate_exec_prompt_quick_2026-05-06.md`, `archive/team_artifacts/epoch-qbi-adversarial-regression-gate/`.

### epoch-qbi-stage-cost-latency-budgets — 2026-05-06

- Goal: Enhance pipeline profiling with stage-level latency budgets, token/cost accounting, budget-violation reports, and a focused cost/latency CLI report.
- Delivered: Enhance pipeline profiling with stage-level latency budgets, token/cost accounting, budget-violation reports, and a focused cost/latency CLI report.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_pipeline_profiler.py tests/test_metrics_api.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/agent_prompts/epoch_qbi_stage_cost_latency_budgets_exec_prompt_quick_2026-05-06.md`, `archive/team_artifacts/epoch-qbi-stage-cost-latency-budgets/`.

### epoch-qbi-learning-metrics-validation — 2026-05-06

- Goal: Add educational metrics and mastery-validation reporting for quiz correctness, retention after 7+ days, transfer outcomes, SRS stability, mastery correlation, and false-positive graduation checks.
- Delivered: Add educational metrics and mastery-validation reporting for quiz correctness, retention after 7+ days, transfer outcomes, SRS stability, mastery correlation, and false-positive graduation checks.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_educational_metrics.py tests/test_mastery_validation.py tests/test_metrics_api.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/agent_prompts/epoch_qbi_learning_metrics_validation_exec_prompt_quick_2026-05-06.md`, `archive/team_artifacts/epoch-qbi-learning-metrics-validation/`.

### epoch-smart-study-router-surface-parity — 2026-05-06

- Goal: Surface parity for explainable SSR: shared session-context builder in `resume_cards`; Progress mounts SSR from main.py before the progress fragment; smoke e2e validates Flashcards hub and Progress bes
- Delivered: Surface parity for explainable SSR: shared session-context builder in `resume_cards`; Progress mounts SSR from main.py before the progress fragment; smoke e2e validates Flashcards hub and Progress beside home.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py tests/test_ui_helpers.py -v --tb=short`, `npm run test:e2e:smoke -- tests/e2e/smart_study_router.spec.ts`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/agent_prompts/epoch_smart_study_router_surface_parity_exec_prompt_quick_2026-05-06.md`, `archive/team_artifacts/epoch-smart-study-router-surface-parity/`.

### epoch-ssr-next-contrastive-explanations — 2026-05-08

- Goal: Add a compact contrastive explanation to the Smart Study Router card: why the recommended action is better than at least one other visible mode right now, while preserving tutor, quiz, flashcards, and
- Delivered: Add a compact contrastive explanation to the Smart Study Router card: why the recommended action is better than at least one other visible mode right now, while preserving tutor, quiz, flashcards, and dashboard entry points.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py tests/test_ui_helpers.py -v --tb=short`, `npm run test:e2e:smoke -- tests/e2e/smart_study_router.spec.ts`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/epoch-ssr-next-contrastive-explanations/`.

### epoch-ssr-next-confidence-ledger — 2026-05-08

- Goal: Add a compact local evidence ledger for SSR recommendations, listing available signals such as due cards, failed quiz state, answer-ready state, retrieval confidence, and skip memory without implying 
- Delivered: Add a compact local evidence ledger for SSR recommendations, listing available signals such as due cards, failed quiz state, answer-ready state, retrieval confidence, and skip memory without implying cloud-only scoring or invented certainty.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py tests/test_ui_helpers.py -v --tb=short`, `npm run test:e2e:smoke -- tests/e2e/smart_study_router.spec.ts`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/epoch-ssr-next-confidence-ledger/`.

### epoch-ssr-next-learning-debt-queue — 2026-05-08

- Goal: Label SSR route priority as retention debt, weak-concept recovery, or new learning so the learner can see the pedagogical reason for the route.
- Delivered: Label SSR route priority as retention debt, weak-concept recovery, or new learning so the learner can see the pedagogical reason for the route.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py tests/test_ui_helpers.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/agent_prompts/epoch_ssr_next_learning_debt_queue_exec_prompt_quick_2026-05-08.md`, `archive/team_artifacts/epoch-ssr-next-learning-debt-queue/`.

### epoch-ssr-next-steering-toggles — 2026-05-08

- Goal: Let the learner set a local steering preference such as review first, new topic, or gentle mode, while explaining tradeoffs when higher-priority learning signals should still win.
- Delivered: Let the learner set a local steering preference such as review first, new topic, or gentle mode, while explaining tradeoffs when higher-priority learning signals should still win.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py tests/test_user_state.py tests/test_ui_helpers.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/agent_prompts/epoch_ssr_next_steering_toggles_exec_prompt_quick_2026-05-08.md`, `archive/team_artifacts/epoch-ssr-next-steering-toggles/`.

### epoch-ssr-next-outcome-receipts — 2026-05-08

- Goal: Show an honest local before/after receipt after a routed action completes, such as due cards reduced, weak concept practiced, or next step unlocked, without claiming progress when state did not measur
- Delivered: Show an honest local before/after receipt after a routed action completes, such as due cards reduced, weak concept practiced, or next step unlocked, without claiming progress when state did not measurably change.
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py tests/test_ui_helpers.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/agent_prompts/epoch_ssr_next_outcome_receipts_exec_prompt_quick_2026-05-08.md`, `archive/team_artifacts/epoch-ssr-next-outcome-receipts/`.

### epoch-ssr-next-quiet-mode — 2026-05-08

- Goal: Add a quieter SSR display mode with the same primary action, reason, and alternatives, covered by fixture tests for keyboard and screen-reader order.
- Delivered: Add a quieter SSR display mode with the same primary action, reason, and alternatives, covered by fixture tests for keyboard and screen-reader order.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py tests/test_ui_helpers.py -v --tb=short`, `npm run test:e2e:smoke -- tests/e2e/smart_study_router.spec.ts`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/epoch-ssr-next-quiet-mode/`.

### llm-ssr-explanation-eval — 2026-05-09

- Goal: Create the evaluation contract, rubric, and 50-scenario local harness for SSR Level 2 LLM explanations before any rollout decision.
- Delivered: Create the evaluation contract, rubric, and 50-scenario local harness for SSR Level 2 LLM explanations before any rollout decision.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/eval/test_ssr_llm_explanation.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/llm-ssr-explanation-eval/`.

### llm-ssr-prompt-engineering — 2026-05-09

- Goal: Design and iterate the SSR explanation prompt so LLM output personalizes why_now_ru while preserving deterministic routing and factual grounding.
- Delivered: Design and iterate the SSR explanation prompt so LLM output personalizes why_now_ru while preserving deterministic routing and factual grounding.
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/eval/test_ssr_llm_explanation.py tests/test_tutor_prompts.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\eval_ssr_prompts.py --json`.
- Archive: `archive/team_artifacts/llm-ssr-prompt-engineering/`.

### llm-ssr-explanation-integration — 2026-05-09

- Goal: Integrate a guarded LLM explanation helper for SSR with 1-hour caching, template fallback, and monitoring documentation. The LLM may replace only explanation text and must not affect routing decisions
- Delivered: Integrate a guarded LLM explanation helper for SSR with 1-hour caching, template fallback, and monitoring documentation. The LLM may replace only explanation text and must not affect routing decisions.
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py tests/eval/test_ssr_llm_explanation.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/llm-ssr-explanation-integration/`.

### ssr-ai-vision-level1-level2-readiness-gate — 2026-05-09

- Goal: Verify SSR AI Vision Level 1/2 readiness after audit fixes and record explicit Go/No-Go rollout gates before Level 3 planning.
- Delivered: Level 1 eval/harness marked GO while ML serving remains gated; Level 2 integration marked GO while automatic UI-time rollout remains gated by latency/human eval; Level 3 dependency mode constrained to baseline-compatible inputs.
- Mode: audit.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/eval/test_ssr_ml_reranking.py tests/eval/test_ssr_llm_explanation.py tests/test_smart_study_router.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`, `.\.venv\Scripts\python.exe scripts\check_llm_context_gate.py`, `.\.venv\Scripts\python.exe scripts\lint_agent_prompts.py`.
- Archive: `archive/team_artifacts/ssr-ai-vision-level1-level2-readiness-gate/`.

### ml-ssr-baseline-hardening — 2026-05-09

- Goal: Укрепить rule-based SSR: comprehensive tests, edge cases, baseline measurements до включения ML reranking.
- Delivered: Укрепить rule-based SSR: comprehensive tests, edge cases, baseline measurements до включения ML reranking.
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py tests/test_smart_study_router_comprehensive.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/ml-ssr-baseline-hardening/`.

### ml-ssr-eval-harness — 2026-05-10

- Goal: Evaluation infrastructure для ML reranking до интеграции модели: контракт, rubric, 100 офлайн сценариев, pytest harness.
- Delivered: Evaluation infrastructure для ML reranking до интеграции модели: контракт, rubric, 100 офлайн сценариев, pytest harness.
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/eval/test_ssr_ml_reranking.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/ml-ssr-eval-harness/`.

### ml-ssr-forgetting-curve-v1 — 2026-05-10

- Goal: Локальный logistic regression reranking forgetting-curve признаков; hybrid merge с rule SSR; мониторинг latency/fallback.
- Delivered: Локальный logistic regression reranking forgetting-curve признаков; hybrid merge с rule SSR; мониторинг latency/fallback.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/eval/test_ssr_ml_reranking.py tests/test_ssr_ml_integration.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/ml-ssr-forgetting-curve-v1/`.

### epoch-e31-course-homework-playbook-ladder — 2026-05-10

- Goal: Course Mode: домашнее задание привязано к курсу/теме; inline плейбук шагов (панель / mobile stack) без tab-hopping; генерация шагов в формате worked-example ladder — на шаге действие + критерий самопр
- Delivered: Course Mode: домашнее задание привязано к курсу/теме; inline плейбук шагов (панель / mobile stack) без tab-hopping; генерация шагов в формате worked-example ladder — на шаге действие + критерий самопроверки; режим «кратко»; сохранение прогресса шагов между сессиями; опора на материалы курса где умес
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_course_cockpit.py tests/test_ui_helpers.py -v --tb=short`, `npm run test:e2e:smoke -- tests/e2e/course_learning_wave_smoke.spec.ts`.
- Archive: `archive/team_artifacts/epoch-e31-course-homework-playbook-ladder/`.

### ml-ssr-serving-rollout-gate — 2026-05-10

- Goal: Документированные go/no-go ворота и автоматизируемые проверки для включённого ML rerank SSR: latency/fallback, регресс rule-бейзлайна, безопасные дефолты конфигурации.
- Delivered: Документированные go/no-go ворота и автоматизируемые проверки для включённого ML rerank SSR: latency/fallback, регресс rule-бейзлайна, безопасные дефолты конфигурации.
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/eval/test_ssr_ml_reranking.py tests/test_ssr_ml_integration.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/ml-ssr-serving-rollout-gate/`.

### epoch-mission-control-home — 2026-05-13

- Goal: Mission Control home surface: SSR banner, seven destination tiles, recommended highlighting, breadcrumb back; Course/Adaptive Plan entry; secondary tools in sidebar.
- Delivered: Replaced stacked home ribbon with Mission Control; navigation cleanup and compatibility shim for `home_hub.render_mode_selector()`; regression tests in `tests/test_mission_control.py` and home hub updates.
- Mode: execution.
- Verification: targeted pytest per package DoD (`tests/test_mission_control.py`, `tests/test_ui_home_hub_enhanced.py`, `tests/test_course_cockpit.py`).
- Archive: (UI modules in app/ui; no separate `archive/team_artifacts` slice for this closure.)

### ssr-l2-reliability-v1 — 2026-05-14

- Goal: Reduce p95 LLM explanation latency via semantic caching and async pre-generation; surface explanation-quality feedback analytics.
- Delivered: Reduce p95 LLM explanation latency via semantic caching and async pre-generation; surface explanation-quality feedback analytics.
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ssr_pregeneration.py tests/test_ssr_semantic_cache.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/ssr-l2-reliability-v1/`.

### epoch-adr-021-router-contract-phase1 — 2026-05-15

- Goal: Implement ADR-021 Phase 1 only: profile registry / validation, `RagProfile`, `RetrievalRoutingDecision`, `RetrievalSource`, and a typed `QueryContext.trace["retrieval_routing"]` path that consumes exi
- Delivered: Implement ADR-021 Phase 1 only: profile registry / validation, `RagProfile`, `RetrievalRoutingDecision`, `RetrievalSource`, and a typed `QueryContext.trace["retrieval_routing"]` path that consumes existing `classify_step` output without re-classifying or changing the default `RetrievalSettings.retri
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_retrieval_routing_trace.py tests/test_api.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`, `.\.venv\Scripts\python.exe scripts\lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts\check_llm_context_gate.py`.
- Archive: `archive/team_artifacts/epoch-adr-021-router-contract-phase1/`.

### ssr-ai-shared-infra-v1 — 2026-05-15

- Goal: Extract shared SSR AI telemetry, eval-harness, fallback, and dataset utilities so L3-L5 do not duplicate the L1 monitoring/eval scaffolds.
- Delivered: Extract shared SSR AI telemetry, eval-harness, fallback, and dataset utilities so L3-L5 do not duplicate the L1 monitoring/eval scaffolds.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ssr_ai_shared_infra.py tests/eval/test_ssr_ml_reranking.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/ssr-ai-shared-infra-v1/`.

### ssr-weekly-planner-baseline — 2026-05-15

- Goal: Generate a 7-day rule-based study plan from due cards, SM-2 state, weak concepts, and available time before any L3 optimization package exists.
- Delivered: Generate a 7-day rule-based study plan from due cards, SM-2 state, weak concepts, and available time before any L3 optimization package exists.
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ssr_weekly_planner.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\validate_evaluation_contract.py archive/ml_eval/ssr_level3/contract.yaml`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/ssr-weekly-planner-baseline/`.

### ssr-misroute-feedback-collection — 2026-05-15

- Goal: Collect accept/reject/defer feedback on SSR recommendations with local, privacy-safe storage before any L5 policy-learning model is scoped.
- Delivered: Collect accept/reject/defer feedback on SSR recommendations with local, privacy-safe storage before any L5 policy-learning model is scoped.
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ssr_feedback_collection.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\validate_evaluation_contract.py archive/ml_eval/ssr_level5/contract.yaml`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/ssr-misroute-feedback-collection/`.

### epoch-expert-controls-phase-1 — 2026-05-15

- Goal: Phase 1 of Expert Controls: add collapsed advanced-management blocks to Flashcards and Tutor so experienced learners can inspect SM-2 state, review queue filters, session debug, tutor policy decisions
- Delivered: Phase 1 of Expert Controls: add collapsed advanced-management blocks to Flashcards and Tutor so experienced learners can inspect SM-2 state, review queue filters, session debug, tutor policy decisions, LLM context metadata, and safe session export/reset controls. Preserve local-first persistence bou
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_flashcard_service.py tests/test_tutor_orchestrator.py tests/test_pipeline_steps.py tests/test_ui_helpers.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/epoch-expert-controls-phase-1/`.

### epoch-expert-controls-phase-2 — 2026-05-15

- Goal: Phase 2 of Expert Controls: add collapsed advanced-management blocks to Quiz and Adaptive Plan for generation parameters, quiz distribution statistics, redacted generation debug, plan-building weights
- Delivered: Phase 2 of Expert Controls: add collapsed advanced-management blocks to Quiz and Adaptive Plan for generation parameters, quiz distribution statistics, redacted generation debug, plan-building weights, learner profile snapshot, and compact plan history where existing persistence contracts support it
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ui_helpers.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/epoch-expert-controls-phase-2/`.

### ssr-ai-vision-level2-level3-readiness-gate — 2026-05-15

- Goal: Verify L1/L2 production signals and L3 baseline telemetry coverage before opening optimization or graph-routing spending.
- Delivered: Verify L1/L2 production signals and L3 baseline telemetry coverage before opening optimization or graph-routing spending.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ssr_ai_shared_infra.py tests/test_ssr_weekly_planner.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/ssr-ai-vision-level2-level3-readiness-gate/`.

### epoch-adr-021-graph-evidence-gating — 2026-05-15

- Goal: Implement ADR-021 Phase 2 only: typed `GraphEvidence` payloads for graph expansion context, composite graph-aware gating, weak/inferred evidence rendering, graph uplift eval/report scaffolding, and do
- Delivered: Implement ADR-021 Phase 2 only: typed `GraphEvidence` payloads for graph expansion context, composite graph-aware gating, weak/inferred evidence rendering, graph uplift eval/report scaffolding, and documented demotion state / `route_demotion_count` metrics. Preserve GraphExpansionPostprocessor owner
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_graph_retrieval.py tests/test_retrieval_routing_trace.py tests/test_metrics.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`, `.\.venv\Scripts\python.exe scripts\lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts\check_llm_context_gate.py`.
- Archive: `archive/team_artifacts/epoch-adr-021-graph-evidence-gating/`.

### epoch-adr-021-prompt-selector-contract — 2026-05-16

- Goal: Implement ADR-021 Phase 3 only: introduce a deterministic `PromptSelector(query_type, profile, retrieval_mode, graph_augmented, learner_state) -> PromptId` contract owned by `app/prompts/`, migrate re
- Delivered: Implement ADR-021 Phase 3 only: introduce a deterministic `PromptSelector(query_type, profile, retrieval_mode, graph_augmented, learner_state) -> PromptId` contract owned by `app/prompts/`, migrate retrieval-side prompt selection to that selector, and keep tutor prompt selection (`app/tutor_prompts.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_prompt_selector.py tests/test_retrieval_profile.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`, `.\.venv\Scripts\python.exe scripts\lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts\check_llm_context_gate.py`.
- Archive: `archive/team_artifacts/epoch-adr-021-prompt-selector-contract/`.

### epoch-adr-021-profile-surfacing — 2026-05-16

- Goal: Implement ADR-021 Phase 5 only: learner/operator surfacing for stable RAG profiles and routing explanations through existing Streamlit/debug surfaces, including a compact "why this route" badge, safe 
- Delivered: Implement ADR-021 Phase 5 only: learner/operator surfacing for stable RAG profiles and routing explanations through existing Streamlit/debug surfaces, including a compact "why this route" badge, safe profile selector/control copy, and trace visibility for selected/effective profile without exposing 
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ui_helpers.py tests/test_retrieval_routing_trace.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`, `.\.venv\Scripts\python.exe scripts\lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts\check_llm_context_gate.py`.
- Archive: `archive/team_artifacts/epoch-adr-021-profile-surfacing/`.

### epoch-adr-021-global-analytics-design — 2026-05-17

- Goal: Write the ADR-021 Phase 4 implementation design for global GraphRAG analytics before any runtime implementation: define `GlobalAnalyticsJob`, artifact ownership under `data/graph_analytics/jobs/<job_i
- Delivered: Write the ADR-021 Phase 4 implementation design for global GraphRAG analytics before any runtime implementation: define `GlobalAnalyticsJob`, artifact ownership under `data/graph_analytics/jobs/<job_id>/`, forward links to graph/index generation ids, provenance schema, recomputation rules, cost/toke
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`, `.\.venv\Scripts\python.exe scripts\lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts\check_llm_context_gate.py`.
- Archive: `archive/team_artifacts/epoch-adr-021-global-analytics-design/`.

### kg-completeness-audit — 2026-05-17

- Goal: Audit knowledge-graph readiness before L4 prerequisite-aware routing is scoped, including concept count, prerequisites, cycles, and orphan nodes.
- Delivered: Audit knowledge-graph readiness before L4 prerequisite-aware routing is scoped, including concept count, prerequisites, cycles, and orphan nodes.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts\audit_knowledge_graph.py`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/kg-completeness-audit/`.

### epoch-adr-021a-architecture-lifts-design — 2026-05-17

- Goal: Write ADR-021a as the explicit architecture-lift amendment requested by the audit: decide accepted/deferred/rejected dispositions for splitting router vs profile resolver, introducing a strategy decor
- Delivered: Write ADR-021a as the explicit architecture-lift amendment requested by the audit: decide accepted/deferred/rejected dispositions for splitting router vs profile resolver, introducing a strategy decorator layer, moving profiles to YAML/TOML, adding `/debug/route`, adding `/ask?dry_run=true`, running
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`, `.\.venv\Scripts\python.exe scripts\lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts\check_llm_context_gate.py`.
- Archive: `archive/team_artifacts/epoch-adr-021a-architecture-lifts-design/`.

### epoch-ssr-contrastive-why-not-others — 2026-05-17

- Goal: Контрастное объяснение Smart Study Router («почему не tutor / quiz / карточки / прогресс сейчас» рядом с primary) без изменения правил роутера и без скрытия secondary входов.
- Delivered: `smart_study_why_not_others_ru`; отображение в Mission Control SSR-баннере и в общей SSR-карточке; pytest + e2e smoke smart_study_router.
- Mode: execution.
- Verification: DoD backlog (pytest SSR + ui_helpers + registry lint strict); e2e по команде пакета.
- Archive: `archive/team_artifacts/epoch-ssr-contrastive-why-not-others/`.

### epoch-adr-021a-a1-retrieval-router-profile-split — 2026-05-17

- Goal: Имплементировать ADR‑021a **A1 (Accepted, impl Deferred)**: явное разделение retrieval-router vs profile resolver без второго RAG-пайплайна; обновления `QueryContext.trace` согласно ADR‑021 только в р
- Delivered: Имплементировать ADR‑021a **A1 (Accepted, impl Deferred)**: явное разделение retrieval-router vs profile resolver без второго RAG-пайплайна; обновления `QueryContext.trace` согласно ADR‑021 только в разрешённом scope; invariant: PromptSelector/`app/prompts/`, SSR и tutor orchestration при boundary н
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_retrieval_routing_trace.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`, `.\.venv\Scripts\python.exe scripts\lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts\check_llm_context_gate.py`.
- Archive: `archive/team_artifacts/epoch-adr-021a-a1-retrieval-router-profile-split/`.

### epoch-ssr-route-confidence-ledger-v1 — 2026-05-18

- Goal: Локальный «confidence ledger»: компактные проверяемые сигналы (due/SM-2, weak concept, answer-ready, существующий reason trace), объясняющие уверенность детерминированного SSR без облачного скоринга; 
- Delivered: Локальный «confidence ledger»: компактные проверяемые сигналы (due/SM-2, weak concept, answer-ready, существующий reason trace), объясняющие уверенность детерминированного SSR без облачного скоринга; раскрываемый UI-блок у Explainable Next Step Card; tutor, quiz, flashcards и dashboard остаются види
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py tests/test_ui_helpers.py -v --tb=short`, `npm run test:e2e:smoke -- tests/e2e/smart_study_router.spec.ts`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/epoch-ssr-route-confidence-ledger-v1/`.

### epoch-orchestrator-e2e-test — 2026-05-20

- Goal: COMPLEXITY: low
Create a file archive/team_artifacts/test_e2e_hello.txt with the text hello world.

- `archive/team_artifacts/test_e2e_hello.txt
- Delivered: COMPLEXITY: low
Create a file archive/team_artifacts/test_e2e_hello.txt with the text hello world.

- `archive/team_artifacts/test_e2e_hello.txt
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -c "print('e2e')"`.
- Archive: `archive/agent_prompts/epoch_orchestrator_e2e_test_exec_prompt_quick_2026-05-20.md`, `archive/team_artifacts/epoch-orchestrator-e2e-test/`.

### epoch-orchestrator-e2e-test-2 — 2026-05-20

- Goal: COMPLEXITY: low
Create a file archive/team_artifacts/test_e2e_hello_2.txt with the text hello world.

- `archive/team_artifacts/test_e2e_hello_2.txt
- Delivered: COMPLEXITY: low
Create a file archive/team_artifacts/test_e2e_hello_2.txt with the text hello world.

- `archive/team_artifacts/test_e2e_hello_2.txt
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `echo e2e2`.
- Archive: `archive/agent_prompts/epoch_orchestrator_e2e_test_2_exec_prompt_quick_2026-05-20.md`, `archive/agent_prompts/epoch_orchestrator_e2e_test_2_planning_prompt_2026-05-20.md`, `archive/team_artifacts/epoch-orchestrator-e2e-test-2/`.

### epoch-ssot-drift-20260521 — 2026-05-21

- Goal: Устранить INV4 drift: в doc/closed_iterations.md зафиксированы закрытые epoch-orchestrator-e2e-test и epoch-orchestrator-e2e-test-2 (2026-05-20), но в doc/backlog_registry.yaml нет соответствующих ite
- Delivered: Устранить INV4 drift: в doc/closed_iterations.md зафиксированы закрытые epoch-orchestrator-e2e-test и epoch-orchestrator-e2e-test-2 (2026-05-20), но в doc/backlog_registry.yaml нет соответствующих items — plan-next и drift-guard блокируются exit 2.
- Mode: execution.
- Verification: all DoD commands passed.
- Verification commands: `.\.venv\Scripts\python.exe scripts/check_backlog_drift.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`, `.\.venv\Scripts\python.exe -m pytest tests/test_backlog_drift.py -v --tb=short`.
- Archive: `archive/team_artifacts/epoch-ssot-drift-20260521/`.

### epoch-ssr-source-coverage-route-guard-v1 — 2026-05-22

- Goal: Source-Coverage Route Guard: при низком retrieval_confidence или недостаточном source coverage SSR не предлагает quiz/tutor как primary; reason честно сообщает «источников мало для проверки» и направл
- Delivered: Source-Coverage Route Guard: при низком retrieval_confidence или недостаточном source coverage SSR не предлагает quiz/tutor как primary; reason честно сообщает «источников мало для проверки» и направляет в source review или clarification; tutor, quiz, flashcards и dashboard остаются видимыми seconda
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py -v -k source_ --tb=short`, `npm run test:e2e:smoke -- tests/e2e/smart_study_router.spec.ts`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/epoch-ssr-source-coverage-route-guard-v1/`.

### epoch-ssr-local-route-simulator-v1 — 2026-05-22

- Goal: Local Route Simulator: learner opens a what-if preview for at least one visible SSR alternative and sees counterfactual primary + honest local reason; maintainer runs documented offline fixture cases 
- Delivered: Local Route Simulator: learner opens a what-if preview for at least one visible SSR alternative and sees counterfactual primary + honest local reason; maintainer runs documented offline fixture cases (due debt, weak concept, answer-ready, thin sources) with stable route/reason output; runtime SSR de
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py -v -k "simulator or what_if" --tb=short`, `.\.venv\Scripts\python.exe scripts/run_ssr_route_simulator.py --fixtures tests/eval/ssr_route_simulator_fixtures.json`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/epoch-ssr-local-route-simulator-v1/`.

### ssr-l2-tiered-explanation-gate-v1 — 2026-05-23

- Goal: Tiered Explanation Gate: template-first «why now» for simple SSR evidence; LLM enrichment only for complex cases (contrastive, ≥3 ledger signals, debt+steering conflict); blended eval p95 explanation 
- Delivered: Tiered Explanation Gate: template-first «why now» for simple SSR evidence; LLM enrichment only for complex cases (contrastive, ≥3 ledger signals, debt+steering conflict); blended eval p95 explanation latency <2s with helpful-rate ≥ L2 baseline; tier decision visible in profiling/trace; zero routing 
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ssr_explanation_tier_gate.py tests/eval/test_ssr_llm_explanation.py -v --tb=short`, `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py -v -k "not simulator and not what_if" --tb=short`, `.\.venv\Scripts\python.exe scripts/validate_evaluation_contract.py archive/ml_eval/ssr_level2/evaluation_contract.yaml`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/ssr-l2-tiered-explanation-gate-v1/`.

### localhost-balance-course-delight-v1 — 2026-05-23

- Goal: Localhost Balance Mode: 3 LLM profiles (LOCAL_STRICT / BALANCED / CLOUD_FAST) + data_mode axis (real/demo); graceful fallback с soft/hard timeout для primary chat LLM (complement к существующему LLM_L
- Delivered: Localhost Balance Mode: 3 LLM profiles (LOCAL_STRICT / BALANCED / CLOUD_FAST) + data_mode axis (real/demo); graceful fallback с soft/hard timeout для primary chat LLM (complement к существующему LLM_LOCAL_CB_*); честный AI+embeddings status в UI; course activation → first mission; persistent course 
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_provider.py tests/test_llm_local_health.py tests/test_llm_local_banner.py -q`, `.\.venv\Scripts\python.exe -m pytest tests/test_study_scope.py tests/test_course_cockpit.py tests/test_course_graduation.py tests/test_course_upload.py tests/test_resume_cards_tutor.py -q`, `npm run test:e2e:smoke:course-scope`, `npm run local:course-loop`, `.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts/check_llm_context_gate.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/localhost-balance-course-delight-v1/`.

### epoch-ssr-concept-recovery-ladder-v1 — 2026-05-23

- Goal: Concept Recovery Ladder: SSR quiz_failed предлагает step 1 (hint) вместо прямого tutor jump; steps 2–4 (worked example → tutor → variant quiz → flashcard) доступны как secondary с объяснением; ladder 
- Delivered: Concept Recovery Ladder: SSR quiz_failed предлагает step 1 (hint) вместо прямого tutor jump; steps 2–4 (worked example → tutor → variant quiz → flashcard) доступны как secondary с объяснением; ladder state persists локально между сессиями и сбрасывается после успешного variant quiz; 0 regression в c
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py -v -k "recovery_ladder" --tb=short`, `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py -v -k "not recovery_ladder" --tb=short`, `npm run test:e2e:smoke -- tests/e2e/smart_study_router.spec.ts`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/epoch-ssr-concept-recovery-ladder-v1/`.

### epoch-ssr-concept-recovery-ladder-v2 — 2026-05-24

- Goal: Завершить Concept Recovery Ladder после sp1a: вынести контракт resume в smart_study_recovery_ladder.py, провести merge/read через learner metadata (pipeline_steps + learner_model_service), прокинуть s
- Delivered: Завершить Concept Recovery Ladder после sp1a: вынести контракт resume в smart_study_recovery_ladder.py, провести merge/read через learner metadata (pipeline_steps + learner_model_service), прокинуть step/resume во все call sites build_smart_study_recommendation (SSR card, tutor quiz/response, adapti
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py -v -k "recovery_ladder or concept_recovery" --tb=short`, `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py -v -k "not recovery_ladder and not concept_recovery" --tb=short`, `npm run test:e2e:smoke -- tests/e2e/smart_study_router.spec.ts --grep recovery`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/epoch-ssr-concept-recovery-ladder-v2/`.

### strong-move-first-session-precompute-v1 — 2026-05-24

- Goal: Precompute First Session Artifact at ingest tail for each course candidate: outline_blocks, seed_questions с pre-retrieved citations, baseline_mission, candidate_flashcards. Cached under data/cache/fi
- Delivered: Precompute First Session Artifact at ingest tail for each course candidate: outline_blocks, seed_questions с pre-retrieved citations, baseline_mission, candidate_flashcards. Cached under data/cache/first_session/<course_id>.json, invalidated by scope hash (same mechanism as course_cache promise). Mi
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_first_session_builder.py tests/test_course_cache.py -q`, `npm run local:course-loop`, `.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts/check_llm_context_gate.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/strong-move-first-session-precompute-v1/`.

### perf-retrieval-init-fix-v1 — 2026-05-24

- Goal: Fix retrieval service re-initialization on every request; Chroma empty-index short-circuit; bootstrap/SSR warmup non-blocking.
- Delivered: `app/api.py` lifespan warmups moved outside `get_base_services()` try block; `app/retrieval_cache.py` `_cached_empty` O(1) short-circuit; `scripts/check_env.py` OS env override warnings.
- Mode: execution.
- Verification: `pytest tests/test_retrieval_cache.py tests/test_api.py -q` (81+4 passed at close).
- Archive: registry notes + `app/retrieval_cache.py`, `app/api.py`.

### perf-flashcards-decks-latency-v1 — 2026-05-24

- Goal: Investigate /flashcards/decks 3343ms latency spike.
- Delivered: Root cause stale OS `LLM_MODEL=google/gemma-4-e4b` triggering real API during metadata init; fixed via env cleanup (`unset_stale_env.ps1`); `/flashcards/decks` 14ms — no code change required.
- Mode: verification_only.
- Verification: log confirmation post env cleanup.
- Archive: registry notes only.

### strong-move-first-session-cold-open-v1 — 2026-05-24

- Goal: sp2 UI: Mission Control First Session Hero + Course Cockpit «Активность» read-path через load_first_session_artifact_for_scope; cold open без primary chat LLM call; Empty/Error fallback при missing/st
- Delivered: sp2 UI: Mission Control First Session Hero + Course Cockpit «Активность» read-path через load_first_session_artifact_for_scope; cold open без primary chat LLM call; Empty/Error fallback при missing/stale artifact; E2E first-session block visible + provider primary-chat stub counter = 0.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_first_session_builder.py tests/test_course_cache.py -q`, `npm run local:course-loop`, `.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts/check_llm_context_gate.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/strong-move-first-session-cold-open-v1/`.

### strong-move-latency-budget-contracts-v1 — 2026-05-24

- Goal: Latency-budgeted surface contracts: per-call-site budget annotations (target/soft/hard ms), four-step degradation ladder (best-path → degraded → soft-breach banner → hard fallback/strict-error), obser
- Delivered: Latency-budgeted surface contracts: per-call-site budget annotations (target/soft/hard ms), four-step degradation ladder (best-path → degraded → soft-breach banner → hard fallback/strict-error), observability into Package E stream (surface, target_ms, actual_ms, degraded, degrade_reason). ADR AR-202
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_latency_budget.py tests/test_provider.py -q`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/strong-move-latency-budget-contracts-v1/`.

### strong-move-session-tape-v1 — 2026-05-24

- Goal: Session tape: append-only JSONL per session under data/sessions/<session_id>.jsonl. MVP events: session_started, mission_loaded, question_asked, retrieval_completed, answer_surfaced, quiz_attempt, car
- Delivered: Session tape: append-only JSONL per session under data/sessions/<session_id>.jsonl. MVP events: session_started, mission_loaded, question_asked, retrieval_completed, answer_surfaced, quiz_attempt, card_created, dwell_ms, surface_breached_soft, surface_breached_hard, session_ended. Additive — existin
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_session_tape.py -q`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/strong-move-session-tape-v1/`.

### epoch-ssr-graph-routing-eval-scaffold-v1 — 2026-05-27

- Goal: SSR L4 scaffold: integration design + offline eval harness for prerequisite-aware routing; KG audit classified graph ready — no learner-visible graph override in this package (follow-up epoch-ssr-grap
- Delivered: SSR L4 scaffold: integration design + offline eval harness for prerequisite-aware routing; KG audit classified graph ready — no learner-visible graph override in this package (follow-up epoch-ssr-graph-routing-v1 after harness gate).
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/eval/test_ssr_graph_routing.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts/validate_evaluation_contract.py archive/ml_eval/ssr_level4/contract.yaml`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/epoch-ssr-graph-routing-eval-scaffold-v1/`.

### epoch-ssr-graph-routing-v1 — 2026-05-29

- Goal: Runtime prerequisite-aware weak-concept reorder in SSR: pure helper order_weak_concepts_for_ssr in app/ssr_graph_routing.py, hook inside build_smart_study_recommendation after rules and before ML hybr
- Delivered: Runtime prerequisite-aware weak-concept reorder in SSR: pure helper order_weak_concepts_for_ssr in app/ssr_graph_routing.py, hook inside build_smart_study_recommendation after rules and before ML hybrid for hint_kind in {quiz_failed, mastery_stale}; settings/feature flag gate; rule-based fallback wh
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/eval/test_ssr_graph_routing.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts\validate_evaluation_contract.py archive/ml_eval/ssr_level4/contract.yaml`, `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py -q --tb=short -k "cards_due or quiz_failed or mastery_stale or recovery_ladder or us20_6_router_fixture"`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/epoch-ssr-graph-routing-v1/`.

### epoch-ssr-misroute-policy-learning-v1 — 2026-05-30

- Goal: SSR L5 misroute policy learning: after closed feedback collection, apply offline weight adjustments with decay when ≥3 consistent rejects align with downstream retention signals; expose adjustment in 
- Delivered: SSR L5 misroute policy learning: after closed feedback collection, apply offline weight adjustments with decay when ≥3 consistent rejects align with downstream retention signals; expose adjustment in evidence ledger; rule-based fallback when feedback sparse; 0 hint_kind/primary_nav regression on can
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ssr_misroute_policy.py -v --tb=short`, `.\.venv\Scripts\python.exe scripts/validate_evaluation_contract.py archive/ml_eval/ssr_level5/policy_learning_contract.yaml`, `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py -q --tb=short -k "cards_due or quiz_failed or us20_6_router_fixture"`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/epoch-ssr-misroute-policy-learning-v1/`.

### epoch-ssr-weekly-study-narrative-v1 — 2026-05-31

- Goal: Weekly Study Narrative (ideation #11): collapsible «Неделя в обучении» on Progress with 3–5 template bullets from local signals (due trend, weak concepts, primary SSR routes); ≤120 words; no LLM by de
- Delivered: Weekly Study Narrative (ideation #11): collapsible «Неделя в обучении» on Progress with 3–5 template bullets from local signals (due trend, weak concepts, primary SSR routes); ≤120 words; no LLM by default; honest empty state when <3 events in 7d; does not hide tutor/quiz/flashcards/dashboard entry 
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_ssr_weekly_narrative.py -v --tb=short`, `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py -q --tb=short -k "cards_due or sm2_due"`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/epoch-ssr-weekly-study-narrative-v1/`.

### epoch-latency-budget-surface-rollout-v1 — 2026-05-31

- Goal: Расширить latency budget beyond mission_load: обернуть primary query answer path и tutor turn в with_budget (target/soft/hard ms); soft breach → banner + surface_breached_soft в session tape; hard bre
- Delivered: Расширить latency budget beyond mission_load: обернуть primary query answer path и tutor turn в with_budget (target/soft/hard ms); soft breach → banner + surface_breached_soft в session tape; hard breach → существующий Phase 2 fallback; не трогать quiz/SSR/ingestion LLM channels.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_latency_budget.py tests/test_provider.py -q`, `.\.venv\Scripts\python.exe -m pytest tests/test_query_service.py -q -k "budget or latency" --tb=short`, `.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts/check_llm_context_gate.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/epoch-latency-budget-surface-rollout-v1/`.

### epoch-latency-budget-quiz-surface-v1 — 2026-05-31

- Goal: Расширить latency budget на micro-quiz surface: обернуть scoped micro-quiz submit/generation в with_budget (target/soft/hard ms); soft breach → banner + surface_breached_soft в session tape; hard brea
- Delivered: Расширить latency budget на micro-quiz surface: обернуть scoped micro-quiz submit/generation в with_budget (target/soft/hard ms); soft breach → banner + surface_breached_soft в session tape; hard breach → существующий Phase 2 fallback; не менять hint_kind/SSR routing; контракт micro-quiz feedback (U
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_latency_budget.py tests/test_provider.py -q`, `.\.venv\Scripts\python.exe -m pytest tests/test_quiz_scoped.py -q -k "budget or latency" --tb=short`, `.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts/check_llm_context_gate.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/epoch-latency-budget-quiz-surface-v1/`.

### epoch-ssot-drift-20260531 — 2026-05-31

- Goal: Устранить INV1/INV4 drift: closed_iterations и user_stories_index помечают localhost-balance-course-delight-v1 closed, а registry держал status proposed; plan-next блокировался check_backlog_drift exi
- Delivered: Устранить INV1/INV4 drift: closed_iterations и user_stories_index помечают localhost-balance-course-delight-v1 closed, а registry держал status proposed; plan-next блокировался check_backlog_drift exit 2.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts/rebuild_user_stories_index.py --write`, `.\.venv\Scripts\python.exe scripts/check_backlog_drift.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`, `.\.venv\Scripts\python.exe -m pytest tests/test_backlog_drift.py -v --tb=short`.
- Archive: see `archive/agent_prompts/` and `archive/team_artifacts/`.

### epoch-srs-overdue-soft-recovery-v1 — 2026-05-31

- Goal: При >50 due в spaced repetition tutor/resume показывает top-N (≤7) приоритетных повторений с формулой days_overdue × mastery_gap и явным «ещё X отложено»; SSR cards_due primary routing не меняется.
- Delivered: При >50 due в spaced repetition tutor/resume показывает top-N (≤7) приоритетных повторений с формулой days_overdue × mastery_gap и явным «ещё X отложено»; SSR cards_due primary routing не меняется.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_user_state.py -q -k "overdue or due_queue" --tb=short`, `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py -q -k cards_due --tb=short`, `.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/epoch-srs-overdue-soft-recovery-v1/`.

### epoch-flashcard-review-progress-bridge-v1 — 2026-05-31

- Goal: После flashcard review session learner видит локальный «receipt»: due уменьшился, streak/weekly goal затронуты, дата следующего повторения — и один CTA «Посмотреть в Progress» без tab-hopping; session
- Delivered: После flashcard review session learner видит локальный «receipt»: due уменьшился, streak/weekly goal затронуты, дата следующего повторения — и один CTA «Посмотреть в Progress» без tab-hopping; session summary не overclaim'ит прогресс.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_flashcards_ui.py tests/test_progress_tab.py -v --tb=short`, `npm run test:e2e:smoke -- tests/e2e/micro_quiz_submit.spec.ts --grep health`, `.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/epoch-flashcard-review-progress-bridge-v1/`.

### epoch-micro-quiz-progress-bridge-v1 — 2026-05-31

- Goal: После submit micro-quiz learner видит локальный receipt: результат попытки + честные локальные изменения (weak concept / plan hint / due — без overclaim) и один CTA «Посмотреть в Progress» без tab-hop
- Delivered: После submit micro-quiz learner видит локальный receipt: результат попытки + честные локальные изменения (weak concept / plan hint / due — без overclaim) и один CTA «Посмотреть в Progress» без tab-hopping; US-5.1 feedback <2s и explanation path не регрессируют.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_quiz_scoped.py tests/test_progress_tab.py -v --tb=short`, `.\.venv\Scripts\python.exe -m pytest tests/test_smart_study_router.py -q -k cards_due --tb=short`, `.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/epoch-micro-quiz-progress-bridge-v1/`.

### doc-navigation-graph-onboarding-v1 — 2026-06-01

- Goal: Documentation entry points include a generated interactive graph, a stable role-based onboarding guide, and Obsidian color grouping so humans and agents can orient in the doc corpus without full-tree reads.
- Delivered: `doc/doc_graph.html` regenerates from real doc links; `doc/index.md` links graph, guide, local D3 asset, and Obsidian config; `doc/documentation_onboarding_guide.md` provides role-based onboarding paths.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe scripts\generate_doc_graph.py --dry-run`, `.\.venv\Scripts\python.exe scripts\generate_doc_graph.py --json`, `.\.venv\Scripts\python.exe scripts\lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts\check_llm_context_gate.py`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --sync-from-index --write-sync`.
- Archive: see deliverables in `doc/backlog_registry.yaml`.

### folder-to-course-delight-v1 — 2026-06-05

- Goal: Пользователь кладёт 3+ документа в data/docs/<course>/, нажимает «Активировать курс» — и через ≤30 секунд видит indexed course с graph DNA (concept extraction via GRAPH_MODEL=qwen/qwen3.6-27b), список
- Delivered: Пользователь кладёт 3+ документа в data/docs/<course>/, нажимает «Активировать курс» — и через ≤30 секунд видит indexed course с graph DNA (concept extraction via GRAPH_MODEL=qwen/qwen3.6-27b), список prerequisite-концептов и статус графа в UI. Если graph model недоступна — курс активируется как ind
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_folder_to_course.py -q --tb=short`, `.\.venv\Scripts\python.exe scripts\run_prompt_smoke.py --strict`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/team_artifacts/folder-to-course-delight-v1/`.

### golden-e2e-graduation-v1 — 2026-06-10

- Goal: Guided delight loop: за одну сессию learner проходит Q&A → Tutor → Quiz → Card → Review → Graduation на qwen/qwen3.6-27b local-first; Mission Control показывает progress rail по шагам; session tape фи
- Delivered: Guided delight loop: за одну сессию learner проходит Q&A → Tutor → Quiz → Card → Review → Graduation на qwen/qwen3.6-27b local-first; Mission Control показывает progress rail по шагам; session tape фиксирует e2e_graduation с llm_model/llm_source/fallback_used; UI не делает тихий cloud switch (assert
- Mode: execution.
- Verification: final DoD completed after closure audit — 44 focused Python tests passed;
  `npm run local:course-loop` passed 6/6 including the Golden browser path; strict smoke-fast
  passed 18/18; session tape recorded local Qwen with `fallback_used=false`.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_course_graduation.py tests/test_session_tape.py tests/test_golden_e2e_graduation_flow.py -q --tb=short`, `npm run local:course-loop`, `.\.venv\Scripts\python.exe scripts\run_prompt_smoke.py --strict --smoke-fast`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync`.
- Archive: `archive/agent_prompts/golden_e2e_graduation_v1_planning_prompt_2026-06-05.md`, `archive/team_artifacts/golden-e2e-graduation-v1/`.
- Final wiring: Mission Control renders the delight progress rail; the offline-only browser
  completion hook invokes the real `e2e_graduation` session-tape writer.

### ragas-retrieval-metrics-v1 — 2026-06-10

- Goal: Expanded from doc/next/ai_driven_design_waves_proposal.md § I4 per owner request 2026-06-05. Sharp scope: recall@k already exists (app/eval_retrieval_comparison.py:21) — contract adds rank-aware preci
- Delivered: Expanded from doc/next/ai_driven_design_waves_proposal.md § I4 per owner request 2026-06-05. Sharp scope: recall@k already exists (app/eval_retrieval_comparison.py:21) — contract adds rank-aware precision + correctness-vs-reference only. Full human-readable contract: doc/next/ragas_retrieval_metrics
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_eval_retrieval_comparison.py tests/test_eval_service.py tests/test_compare_eval.py -q`, `.\.venv\Scripts\python.exe -c "assert round(__import__('app.eval_retrieval_comparison', fromlist=['calculate_precision_at_k']).calculate_precision_at_k({'a'}, ['a','b'], 2), 9) == 0.5"`, `.\.venv\Scripts\python.exe scripts\check_readset.py app/eval_retrieval_comparison.py app/eval_service.py`.
- Archive: `archive/team_artifacts/ragas-retrieval-metrics-v1/`.

### smart-notes-konspekt-surfacing-v1 — 2026-06-10

- Goal: Surface existing `type: konspekt` Markdown notes in the topics UI with exact source matching, download access, and course-level coverage awareness.
- Delivered: `app/konspekt_discovery.py` frontmatter discovery and coverage summary; per-document ready badge/download action; smart Obsidian batch behavior that skips covered documents by default while preserving explicit override.
- Mode: execution.
- Verification: `16 passed` in `tests/test_konspekt_discovery.py` at delivery.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_konspekt_discovery.py -q --tb=short`, `.\.venv\Scripts\python.exe scripts\check_readset.py app/konspekt_discovery.py app/ui/topics_tab_right_column.py app/ui/topics_tab.py tests/test_konspekt_discovery.py`, `.\.venv\Scripts\python.exe scripts\lint_agent_prompts.py`.
- Archive: delivery details in `doc/changelog.md` and `doc/backlog_registry.yaml`.

### prompt-role-unification-v1 — 2026-06-11

- Goal: Follow-up к qwen/qwen3.6-27b validation: основной RAG уже подтверждён как system+user и reasoning_tokens=0 по LM Studio логам; остаточный риск — отдельные tutor/quiz/minicheck calls с messages=[user].
- Delivered: Follow-up к qwen/qwen3.6-27b validation: основной RAG уже подтверждён как system+user и reasoning_tokens=0 по LM Studio логам; остаточный риск — отдельные tutor/quiz/minicheck calls с messages=[user]. Пакет должен превратить это из ручного наблюдения в machine-readable smoke contract. Accepted via g
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_prompt_smoke_checks.py tests/test_usage_cost_generation_tokens.py tests/test_tutor_prompts.py -q`, `.\.venv\Scripts\python.exe scripts\run_prompt_smoke.py --strict --report-json logs/smoke_qwen3_6_27b_role_unification.json`, `.\.venv\Scripts\python.exe scripts\lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts\check_llm_context_gate.py`.
- Archive: `archive/team_artifacts/prompt-role-unification-v1/`.

### course-graph-compiler-v1 — 2026-06-11

- Goal: Audit 2026-06-10 for course `ИИ Агенты`: latest matching generation had 5 nodes, 0 relations, 0 triplets; node ids were lesson filenames with heuristic confidence 0.72. data/concept_graph.json was abs
- Delivered: Audit 2026-06-10 for course `ИИ Агенты`: latest matching generation had 5 nodes, 0 relations, 0 triplets; node ids were lesson filenames with heuristic confidence 0.72. data/concept_graph.json was absent; metadata enrichment, summaries, and graph-augmented retrieval were disabled. Targeted current-c
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_knowledge_graph.py tests/test_knowledge_graph_bundle_persist.py tests/test_folder_to_course.py -q --tb=short`, `.\.venv\Scripts\python.exe scripts\audit_knowledge_graph.py --graph data/concept_graph.json`, `.\.venv\Scripts\python.exe scripts\lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts\check_llm_context_gate.py`.
- Archive: `archive/team_artifacts/course-graph-compiler-v1/`.

### course-graph-relation-ux-v1 — 2026-06-11

- Goal: Auto-promoted to ready after course-graph-compiler-v1 closed 2026-06-11 (post-close wave sync). Depends on compiler gate + binding fields. US-16.0 is a closed baseline story. This package extends its 
- Delivered: Auto-promoted to ready after course-graph-compiler-v1 closed 2026-06-11 (post-close wave sync). Depends on compiler gate + binding fields. US-16.0 is a closed baseline story. This package extends its graph UX without reopening or replacing the delivered activation-course contract.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_knowledge_graph_d3.py tests/test_knowledge_graph_viz.py tests/test_ui_helpers.py -q --tb=short`.
- Archive: `archive/team_artifacts/course-graph-relation-ux-v1/`.

### course-graph-aware-uplift-gate-v1 — 2026-06-11

- Goal: Auto-promoted to ready after course-graph-relation-ux-v1 closed 2026-06-11 (manual backfill: user_stories US-12.7/US-12.10 for eval uplift gate contract). Depends on compiler + relation UX delivery; g
- Delivered: Auto-promoted to ready after course-graph-relation-ux-v1 closed 2026-06-11 (manual backfill: user_stories US-12.7/US-12.10 for eval uplift gate contract). Depends on compiler + relation UX delivery; graph-aware enablement requires measured uplift.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_graph_shaped_eval_dataset.py tests/test_graph_uplift_gate.py tests/test_graph_expansion_benchmark.py tests/test_retrieval_profile.py tests/test_retrieval_routing_trace.py tests/test_check_graph_expansion_gate.py tests/test_ui_helpers.py tests/test_debug_panel.py -q --tb=short`, `.\.venv\Scripts\python.exe scripts\check_graph_expansion_gate.py --help`.
- Archive: `archive/team_artifacts/course-graph-aware-uplift-gate-v1/`.

### grounded-answer-contract-v1 — 2026-06-11

- Goal: Proposed package from doc/next/ai_driven_design_waves_proposal.md § A4. Accepted via generate_plan_next 2026-06-11 (candidate #1, wave-grounding-abstain-contract). Preflight WARN — compress read-set (
- Delivered: Proposed package from doc/next/ai_driven_design_waves_proposal.md § A4. Accepted via generate_plan_next 2026-06-11 (candidate #1, wave-grounding-abstain-contract). Preflight WARN — compress read-set (signatures/rg-only для query_service) before orchestration. US-3.1 is a closed baseline story; this 
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_grounded_answer_contract.py tests/test_answer_parser.py tests/test_guardrails.py -q --tb=short`, `.\.venv\Scripts\python.exe -m pytest tests/test_query_service.py -q -k "citation or abstain or grounded" --tb=short`, `.\.venv\Scripts\python.exe scripts\lint_agent_prompts.py`, `.\.venv\Scripts\python.exe scripts\check_llm_context_gate.py`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/team_artifacts/grounded-answer-contract-v1/`.

### fact-source-binding-v1 — 2026-06-19

- Goal: Second package of wave-grounding-abstain-contract; pairs with SSR evidence ledger.
- Delivered: Second package of wave-grounding-abstain-contract; pairs with SSR evidence ledger.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_fact_source_binding.py tests/test_quiz_adaptive.py tests/test_spaced_repetition.py -q --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/team_artifacts/fact-source-binding-v1/`.

### langfuse-trace-export-v1 — 2026-06-19

- Goal: Proposed package from doc/next/ai_driven_design_waves_proposal.md § I1. Requires wave-pii-masking-redaction for safe PII export; v1 applies guardrails redact on span attributes as interim sink coverag
- Delivered: Proposed package from doc/next/ai_driven_design_waves_proposal.md § I1. Requires wave-pii-masking-redaction for safe PII export; v1 applies guardrails redact on span attributes as interim sink coverage.
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_langfuse_trace_export.py tests/test_otel_tracing.py -q --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/agent_prompts/langfuse_trace_export_v1_exec_prompt_quick_2026-06-19.md`, `archive/team_artifacts/langfuse-trace-export-v1/`.

### trace-to-eval-dataset-v1 — 2026-06-19

- Goal: Second package of wave-langfuse-eval-loop; consumed by ragas-langfuse-dataset-v1. 2026-06-10 offline-first slice delivered: app/langfuse_dataset.py and scripts/build_langfuse_eval_dataset.py convert J
- Delivered: Second package of wave-langfuse-eval-loop; consumed by ragas-langfuse-dataset-v1. 2026-06-10 offline-first slice delivered: app/langfuse_dataset.py and scripts/build_langfuse_eval_dataset.py convert JSON/JSONL exports into a redacted, deduplicated eval_data dataset. Live import/export remains gated 
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_langfuse_dataset.py -q --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/agent_prompts/trace_to_eval_dataset_v1_exec_prompt_quick_2026-06-19.md`, `archive/team_artifacts/trace-to-eval-dataset-v1/`.

### log-masking-policy-v1 — 2026-06-19

- Goal: Second package of wave-pii-masking-redaction; gates Langfuse export safety (I1).

- `app/log_masking_policy.py`
- `tests/test_log_masking_policy.py
- Delivered: Second package of wave-pii-masking-redaction; gates Langfuse export safety (I1).

- `app/log_masking_policy.py`
- `tests/test_log_masking_policy.py
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_log_masking_policy.py tests/test_guardrails.py -q --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/agent_prompts/log_masking_policy_v1_exec_prompt_quick_2026-06-19.md`, `archive/team_artifacts/log-masking-policy-v1/`.

### lost-in-middle-reorder-v1 — 2026-06-19

- Goal: Second package of wave-advanced-rag-rewrite-rerank; reranker already exists.

- `app/lost_in_middle_reorder.py`
- `app/retrieval.py`
- `app/config.py`
- `tests/test_lost_in_middle_reorder.py
- Delivered: Second package of wave-advanced-rag-rewrite-rerank; reranker already exists.

- `app/lost_in_middle_reorder.py`
- `app/retrieval.py`
- `app/config.py`
- `tests/test_lost_in_middle_reorder.py
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_lost_in_middle_reorder.py -q --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict`.
- Archive: `archive/agent_prompts/lost_in_middle_reorder_v1_exec_prompt_quick_2026-06-19.md`, `archive/team_artifacts/lost-in-middle-reorder-v1/`.

### flashcard-handoff-fast-path-v1 — 2026-06-20

- Goal: Contract: archive/team_artifacts/flashcard-handoff-fast-path-v1/execution_contract.md. P0 (baseline instrumentation) in progress this session.

- `app/flashcard_handoff_timing.py`
- `app/ui/flashcards
- Delivered: Contract: archive/team_artifacts/flashcard-handoff-fast-path-v1/execution_contract.md. P0 (baseline instrumentation) in progress this session.

- `app/flashcard_handoff_timing.py`
- `app/ui/flashcards_review_view.py`
- `app/ui/tutor_chat_session.py`
- `app/query_service.py`
- `app/query_rag_executio
- Mode: execution.
- Verification: DoD not run during closure.
- Verification commands: `.\.venv\Scripts\python.exe -m pytest tests/test_flashcard_handoff_timing.py tests/test_ssr_explain_stream_timing.py tests/test_query_service.py tests/test_retrieval_profile.py tests/test_ui_helpers.py -q --tb=short`, `.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --sync-from-index --write-sync --strict`.
- Archive: `archive/team_artifacts/flashcard-handoff-fast-path-v1/`.
