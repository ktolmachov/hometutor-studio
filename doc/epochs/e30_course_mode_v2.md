# Epoch E30: Course Learning Mode v2 — Immersive Fast Track

**Status:** planning  
**Created:** 2026-04-25  
**Wave:** `wave-course-learning-v2`  
**CJM:** Stage #7 v2 (see `archive/analysis/cjm_stage7_course_mode_v2.md`)  
**Epic:** 17 — Course Learning Mode v2  
**Feature flag:** `RAG_COURSE_COCKPIT_V2` (env var)

---

## Цель эпохи

Превратить Course Learning Mode из набора разрозненных табов в цельный immersive продукт — "кабина пилота" (Course Cockpit) с адаптивным планом, interleaved practice, ритуалом освоения и Knowledge Vault на выходе.

Базовая инфраструктура готова (Epic 16): `study_scope`, `course_cache`, `course_metrics`, `course_prepare_view`, `continuity_bridge`. E30 строит UX-надстройку поверх неё.

---

## Пользовательские истории

| US     | Сценарий | Priority | Phase | Описание                              |
| ------ | -------- | -------- | ----- | ------------------------------------- |
| US-17.2 | S7.2    | P0       | A     | Course Cockpit (single-pane layout)   |
| US-17.4 | S7.4    | P0       | A     | Interleaved Practice auto-rotation    |
| US-17.5 | S7.5    | P1       | B     | Concept Graduation Ceremony           |
| US-17.6 | S7.6    | P1       | B     | Daily Briefing & Debriefing           |
| US-17.1 | S7.1    | P0       | C     | Pre-Flight Diagnostic                 |
| US-17.3 | S7.3    | P1       | C     | Adaptive Pace Engine                  |
| US-17.8 | S7.8    | P0       | D     | Smart Resume + Warm-Up                |
| US-17.7 | S7.7    | P2       | D     | Focus Mode (Pomodoro + lock)          |
| US-17.9 | S7.9    | P1       | E     | Course Graduation + Knowledge Vault   |
| US-17.10 | S7.10  | P2       | C+    | Daily Course Runway + streak chip     |
| US-17.11 | S7.11  | P2       | C+    | Interleaved retrieval gates           |

---

## Пять фаз реализации

### Phase A — Cockpit Skeleton + Interleaving (Entry point)
**Packages:**
- `e30-a1-cockpit-scaffold` — `app/ui/course_cockpit.py`: 3-column layout, feature flag, header, exit. No logic yet, только структура.
- `e30-a2-cockpit-rotator` — `app/ui/cockpit_rotator.py`: rotation scheduler, transition overlays, smart triggers (3 errors → forced tutor, 3× Easy → graduation gate).

**Pre-req:** feature flag `RAG_COURSE_COCKPIT_V2` не ломает текущий tab-flow.  
**DoD:** Cockpit открывается, auto-advances через активности, tab-switches = 0.  
**Kill switch:** scenario_07 красный в CI >2 дней.

---

### Phase B — Ceremonies + Habit Loop
**Packages:**
- `e30-b1-graduation-overlay` — `app/ui/graduation_overlay.py`: 3-sec ceremony, Path Map animation, `concept_graduation_event` logging.
- `e30-b2-daily-briefing` — `app/ui/daily_briefing.py`: morning brief overlay, evening debrief overlay, gap-inbox parking.

**Pre-req:** Phase A merged.  
**DoD:** Graduation показывается при transition to mastered; briefs появляются по условию паузы ≥4ч.

---

### Phase C — Intelligence Layer
**Packages:**
- `e30-c1-diagnostic` — `app/diagnostic_service.py`: 10–15 question adaptive quiz, 3-level heuristic routing, `diagnostic.v1` artifact, skip-confirmation UI.
- `e30-c2-pace-engine` — `app/pace_engine.py`: rolling pace calculation, Sprint/Steady/Deep modes, `plan.v2` artifact, manual override в header.

**Pre-req:** Phase A merged.  
**DoD:** Diagnostic запускается при первом activate; pace переключается без перезагрузки; plan перестраивается.

---

### Phase D — Resume + Focus
**Packages:**
- `e30-d1-smart-resume` — `app/warmup_planner.py`: pause-tier logic (4 tiers), soft-recovery overdue distribution, `warmup.v1` artifact.
- `e30-d2-focus-mode` — `app/ui/focus_mode.py`: Pomodoro 25/5, lock-mode UI, 4-cycle deep-work badge, streak shield activation.

**Pre-req:** Phase B merged.  
**DoD:** Warm-up показывается при правильном tier; Pomodoro lock работает; streak shield логируется.

---

### Phase E — Graduation + Vault
**Packages:**
- `e30-e1-course-graduation` — `app/course_graduation.py`: graduation trigger check, ceremony overlay, PDF certificate generator, Knowledge Vault export (summary.md, concepts/, flashcards.apkg, concept_graph.json).

**Pre-req:** Phase C + D merged.  
**DoD:** Course с ≥80% concepts graduated → ceremony → vault export работает → импорт в Anki/Obsidian проверен вручную.

---

### Ideation follow-up (post-contract, 2026-04-26)
**Packages:**
- `e30-idea-1-daily-runway` — runway + streak chip в cockpit, метрики через `record_course_workflow_event`, анти-gaming cap.
- `e30-idea-2-retrieval-gates` — 1–3 retrieval gates между чанками плана с interleaving, интеграция через `pace_engine`.

**Pre-req:** соответствующие базовые фазы (B2/C2) готовы, без дублей existing briefing/diagnostic gates.  
**DoD:** фиксируется рост completion без нарушения session SLO; покрытие целевыми тестами и telemetry events.

---

## Новые модули (write-set)

| Module                          | Phase | Lines est. | Reuses                                      |
| ------------------------------- | ----- | ---------- | ------------------------------------------- |
| `app/ui/course_cockpit.py`      | A     | ~300       | `study_scope`, `continuity_bridge`          |
| `app/ui/cockpit_rotator.py`     | A     | ~150       | `flashcard_service`, `quiz_panel`, `tutor_orchestrator` |
| `app/ui/graduation_overlay.py`  | B     | ~100       | `learner_model_service`, `course_metrics`   |
| `app/ui/daily_briefing.py`      | B     | ~150       | `course_metrics.collect_course_progress`    |
| `app/diagnostic_service.py`     | C     | ~200       | `quiz_panel`, `course_cache`                |
| `app/pace_engine.py`            | C     | ~180       | `course_metrics`, `learner_model_service`   |
| `app/warmup_planner.py`         | D     | ~150       | `resume_cards`, `course_cache`              |
| `app/ui/focus_mode.py`          | D     | ~120       | cockpit layout                              |
| `app/course_graduation.py`      | E     | ~250       | `export_full_sync_bundle`, `flashcard_service` |

**Итого: ~1600 строк нового кода, 9 модулей.**

---

## Новые артефакты course_cache

| Artifact key        | Phase | Content                                          |
| ------------------- | ----- | ------------------------------------------------ |
| `diagnostic.v1`     | C     | `{concepts_skipped, confidence_scores, method}`  |
| `plan.v2`           | C     | `{pace_mode, rotation_policy, deadline}`         |
| `warmup.v1`         | D     | `{tier, warm_cards, due_redistributed}`          |
| `last_session_at`   | D     | ISO timestamp                                    |
| `graduation_event`  | E     | `{date, concepts_count, days, hours, vault_path}`|

---

## KPI таблица

| Metric                                   | Baseline | Target   | Tracked by           |
| ---------------------------------------- | -------- | -------- | -------------------- |
| % activated courses → graduation         | ~15%     | ≥40%     | `course_graduation`  |
| Avg session duration                     | ~9 min   | ≥18 min  | `course_metrics`     |
| Tab-switches per session                 | 4–7      | 0        | `cockpit_rotator`    |
| Long-term retention (7-day retest)       | ~55%     | ≥75%     | `diagnostic_service` |
| Time saved by Pre-Flight diagnostic      | 0        | 20–35%   | `diagnostic_service` |
| Streak ≥14 days share                    | ~5%      | ≥25%     | `daily_briefing`     |
| Knowledge Vault export rate (graduates)  | 0        | ≥80%     | `course_graduation`  |

---

## Архитектурные решения

1. **Feature flag first.** `RAG_COURSE_COCKPIT_V2=1` включает Cockpit; дефолт `0`. Параллельный tab-flow не ломается ни на одном phase.
2. **Cockpit как shell.** `course_cockpit.py` — только layout + routing. Все бизнес-логики — в существующих сервисах. Нет дублирования.
3. **Artifacts в course_cache.** Все новые состояния сохраняются через `save_course_artifact` — не в Streamlit session_state. Persists между сессиями.
4. **Events через course_metrics.** `record_course_workflow_event` — единственный канал телеметрии. Не создавать новых logging path.
5. **No gamification debt.** Никаких очков-валют, никаких leaderboards. Только visible mastery transformation.

---

## Открытые вопросы (для PO-review перед Phase A)

1. TTS в Daily Briefing: Edge-TTS / pyttsx3 или отложить в отдельный пакет?
2. Diagnostic: 3-level heuristic достаточно или нужен облегчённый IRT (2PL)?
3. Streak Shield: auto раз в месяц или earned через X graduated concepts?
4. Onboarding: нужен ли guided 60-sec tour при первом открытии Cockpit?
5. Размер блоков interleaving (7/3/5/4 min) — подтвердить или оставить configurable?

---

## Связанные документы

- `archive/analysis/cjm_stage7_course_mode_v2.md` — полный дизайн Stage #7 v2 (source of truth)
- `doc/backlog_registry.yaml` — волна `wave-course-learning-v2` и 9 пакетов `epoch-e30-a1-…` … `epoch-e30-e1-…` (machine-readable план; контрактные имена в tasklist — `e30-a1-…`, как в таблицах ниже)
- `doc/user_stories/us-17.1.md` — `us-17.9.md` — user stories Epic 17
- `doc/cjm.md` § Stage #7 — исходный flow (основа)
- `app/ui/course_prepare_view.py`, `app/course_metrics.py`, `app/ui/study_scope.py` — существующая инфраструктура

---

**Next action:** PO review → accept Phase A scope → create package contract `e30-a1-cockpit-scaffold` in `tasklist.md § Now`.
