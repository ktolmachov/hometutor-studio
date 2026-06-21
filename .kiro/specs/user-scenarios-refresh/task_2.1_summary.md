# Task 2.1 Summary: Parse Existing 22 Scenarios

**Status:** ✅ COMPLETED

**Date:** 2025-01-XX

**Requirements Validated:** 1.3

---

## Overview

Successfully parsed all 22 existing scenarios from `doc/user_scenarios.md` and built comprehensive coverage maps. The analysis extracted scenario numbers, titles, covered features, personas, MoT moments, and artifact references.

---

## Key Findings

### Total Scenarios: 22

**Distribution by Level:**
- **Первые шаги (First Steps):** 6 scenarios - [1, 2, 3, 15, 16, 19]
- **Учебный ритм (Learning Rhythm):** 4 scenarios - [4, 5, 6, 7]
- **Мастерство (Mastery):** 9 scenarios - [8, 9, 10, 11, 17, 18, 20, 21, 22]
- **Power user:** 3 scenarios - [12, 13, 14]

---

## Coverage Map: Scenario → Features

### Top Features by Coverage

| Feature | Scenarios Count | Scenario Numbers |
|---------|----------------|------------------|
| **Tutor** | 19 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 20, 21, 22 |
| **Flashcards** | 14 | 4, 5, 6, 7, 8, 9, 12, 13, 14, 15, 16, 18, 21, 22 |
| **Trust Panel** | 13 | 1, 2, 3, 5, 9, 11, 12, 14, 15, 16, 17, 21, 22 |
| **Mastery Tracking** | 12 | 3, 4, 7, 8, 9, 10, 12, 13, 14, 15, 20, 22 |
| **Spaced Repetition** | 9 | 5, 6, 7, 8, 9, 15, 18, 21, 22 |
| **Course Workspace** | 8 | 1, 5, 7, 8, 9, 16, 20, 22 |
| **Adaptive Plan** | 8 | 4, 9, 10, 13, 14, 17, 20, 21 |
| **Environment Validation** | 5 | 1, 14, 15, 19, 22 |
| **Quick Answer** | 4 | 1, 2, 3, 11 |
| **Plan Diff** | 4 | 4, 9, 13, 17 |
| **Pedagogical Router** | 3 | 3, 4, 20 |
| **Reindexing** | 2 | 7, 13 |
| **Backup & Offline** | 2 | 12, 14 |
| **Smart Study Router** | 2 | 21, 22 |
| **Telegram Bot** | 1 | 12 |
| **Interactive Tour** | 1 | 16 |
| **Home Hub** | 1 | 18 |
| **AI Vision** | 1 | 22 |
| **UX Breakthrough** | 1 | 15 |

---

## MoT (Moment of Truth) Coverage

**Critical Finding:** No explicit MoT moment references were found in the existing scenarios.

**Implication:** This is a significant gap. The scenarios describe features and workflows but don't explicitly map to the 13 CJM moments of truth. This should be addressed in the gap analysis (task 2.2).

**Expected MoT Moments (from requirements):**
- #1 Discover
- #2 First Answer
- #3 Transition to tutor
- #4-#14 (other moments)

**Recommendation:** During scenario updates, explicitly add MoT references to connect scenarios to the customer journey map.

---

## Wave Coverage

**Critical Finding:** No explicit wave references were found in existing scenarios.

**Implication:** The scenarios were written before the wave-based development model was established. This is the primary gap that this spec aims to address.

**Expected Priority Waves (from requirements):**
- wave-mission-control-home
- wave-smart-study-router (+ variants)
- wave-home-mode-selection-v2
- wave-course-retention-resilience
- wave-interactive-tour
- ssr-ai-vision-wave-1-foundation (+ L2 variants)

**Recommendation:** Task 2.2 will compare closed waves from backlog_registry.yaml against this baseline to identify gaps.

---

## Artifact Coverage

### YAML Artifacts
**Scenarios with YAML:** 7 out of 22 (31.8%)
- Scenario 15: scenario_15_ux_breakthrough.yaml
- Scenario 16: scenario_16_interactive_tour.yaml
- Scenario 17: scenario_17_plan_diff.yaml
- Scenario 18: scenario_18_home_retention_hub.yaml
- Scenario 19: scenario_19_env_validation.yaml
- Scenario 21: scenario_21_smart_study_router.yaml
- Scenario 22: scenario_22_ai_router_vision.yaml

**Scenarios without YAML:** 15 (68.2%)
- Scenarios 1-14, 20

### E2E Tests
**Scenarios with e2e tests:** 6 out of 22 (27.3%)
- Scenario 16: scenario_16_interactive_tour.spec.ts
- Scenario 17: scenario_17_plan_diff.spec.ts
- Scenario 18: scenario_18_home_retention_hub.spec.ts
- Scenario 19: scenario_19_env_validation.spec.ts
- Scenario 21: scenario_21_smart_study_router.spec.ts
- Scenario 22: scenario_22_ai_router_vision.spec.ts

**Scenarios without e2e tests:** 16 (72.7%)
- Scenarios 1-15, 20

**Note:** Scenarios 15-22 are more recent and have better artifact coverage. This suggests a shift toward better documentation and testing practices in later development phases.

---

## Persona Distribution

### Primary Personas Used

| Persona | Scenarios | Context |
|---------|-----------|---------|
| **Аня** | 1, 3, 5, 7, 10, 16, 20, 21 | Student, learning-focused, first-time user |
| **Марк** | 4, 6, 9, 13, 17 | Developer, preparing for interview, returning user |
| **Сергей** | 8, 12 | Course learner, power user |
| **Максим** | 2, 19 | Developer, quick answer user, setup scenarios |
| **Елена** | 14 | Privacy-focused, offline user |
| **Generic** | 11, 15, 18, 22 | "любой пользователь", "скептически настроенный", "защита проекта" |

**Observation:** Personas are used consistently across scenarios, with Аня and Марк being the most common. This provides good continuity for the learner journey narrative.

---

## Scenario Details by Level

### Первые шаги (First Steps) - 6 scenarios

| # | Title | Persona | Time | Main Question |
|---|-------|---------|------|---------------|
| 1 | Первый запуск | Аня | 5 минут | Оно вообще работает? |
| 2 | Быстрый ответ | Максим | 30–60 секунд | Можно ли получить ответ, не проходя урок? |
| 3 | Мост «ответ → тьютор» | Аня | 3 минуты | Сохранится ли контекст при переключении режима? |
| 15 | UX Breakthrough | любой пользователь | сразу | Чувствуется ли система быстрой, плавной и мотивирующей? |
| 16 | Интерактивный тур: 5 глав | Аня | ~20 минут | - |
| 19 | Проверка окружения и сайдбар | Максим | - | - |

**Coverage:** First-time user experience, quick answer, tutor transition, UX quality, onboarding tour, environment setup.

### Учебный ритм (Learning Rhythm) - 4 scenarios

| # | Title | Persona | Time | Main Question |
|---|-------|---------|------|---------------|
| 4 | Учебная сессия | Марк | 7–10 минут | Это диалог или бесконечная лекция? |
| 5 | Flashcards: генерация | Аня | 4–6 минут | Смогу ли я проверить карточки до сохранения? |
| 6 | SM-2 повторение | Марк | 5–8 минут | Это Anki или что-то лучше? |
| 7 | Возврат на следующий день | Аня | 2 минуты | Придётся ли снова объяснять системе, кто я и что изучаю? |

**Coverage:** Learning sessions, flashcard generation, spaced repetition, retention and resume.

### Мастерство (Mastery) - 9 scenarios

| # | Title | Persona | Time | Main Question |
|---|-------|---------|------|---------------|
| 8 | Course Workspace | Сергей | 10–15 минут | Может ли папка с файлами стать курсом? |
| 9 | Adaptive Daily Plan | Марк | 5 минут | Кто-нибудь скажет мне, что делать сегодня? |
| 10 | Mastery и Graduation | Аня | 5 минут | Есть ли разница между "прочитал" и "освоил"? |
| 11 | Trust-панель | скептик | 3 минуты | Откуда взялся этот ответ? |
| 17 | Что изменилось в плане (diff) | Марк | - | - |
| 18 | Главная как карта возврата | returning learner | - | - |
| 20 | Адаптивный маршрут тьютора | Аня | - | - |
| 21 | Умный Маршрутизатор | Аня | 1 минута | Что мне делать прямо сейчас? |
| 22 | Умный Маршрутизатор с ИИ | защита проекта | 2 минуты | Почему это не просто кнопка, а будущий персональный учебный проводник? |

**Coverage:** Course mode, adaptive planning, mastery tracking, trust/transparency, plan diff, home hub, pedagogical routing, smart study router (basic + AI vision).

### Power user - 3 scenarios

| # | Title | Persona | Time | Main Question |
|---|-------|---------|------|---------------|
| 12 | Telegram | Сергей | 5 минут setup | - |
| 13 | Переиндексация | Марк | 4 минуты | - |
| 14 | Backup и офлайн | Елена | 5 минут | - |

**Coverage:** Mobile access, reindexing, backup/offline, data control.

---

## Gap Analysis Preview

Based on this parsing, the following gaps are evident:

### 1. **No MoT Mapping**
- Scenarios don't explicitly reference CJM moments of truth
- Need to add MoT references during updates

### 2. **No Wave References**
- Scenarios predate wave-based development model
- Need to map scenarios to closed waves in task 2.2

### 3. **Low Artifact Coverage**
- Only 31.8% have YAML artifacts
- Only 27.3% have e2e tests
- Older scenarios (1-14) lack artifacts

### 4. **Missing Recent Waves**
From requirements, these priority waves are likely not covered:
- wave-mission-control-home (may partially overlap with scenario 18)
- wave-smart-study-router variants (scenarios 21-22 cover basics, but not all variants)
- wave-home-mode-selection-v2 (may need scenario 18 update)
- wave-course-retention-resilience (may need scenario 8 update)
- wave-course-learning-v2 (Course Cockpit E30 - not explicitly covered)
- wave-flashcard-polish (may need scenario 5 update)
- wave-first-answer-ux (may need scenario 2 update)

### 5. **Feature Gaps**
Features mentioned in requirements but not strongly represented:
- Mission Control home screen (only scenario 18, may be outdated)
- SSR surface parity and next-level variants (only basic SSR in 21-22)
- Course Cockpit E30 with graduation overlay (scenario 8 may be outdated)
- Homework playbook (not covered)
- AI Vision levels 1-2 (scenario 22 is roadmap/vision, not implementation)

---

## Deliverables

### 1. **Parse Script**
- Location: `.kiro/specs/user-scenarios-refresh/parse_scenarios.py`
- Functionality: Extracts all scenario metadata from user_scenarios.md
- Output: JSON file with structured data

### 2. **Coverage Map JSON**
- Location: `.kiro/specs/user-scenarios-refresh/scenario_analysis.json`
- Contents:
  - Full scenario list with metadata
  - Coverage map (scenario → features/waves/MoT)
  - MoT coverage analysis
  - Summary statistics

### 3. **Summary Report**
- This document
- Comprehensive analysis of existing scenarios
- Gap analysis preview for task 2.2

---

## Next Steps (Task 2.2)

1. **Parse backlog_registry.yaml** to extract all closed waves
2. **Compare closed waves** against this scenario baseline
3. **Identify gaps:**
   - New features not covered by any scenario
   - UI updates that make scenarios outdated
   - Flow changes that require scenario updates
4. **Classify gaps** as: new_feature, ui_update, flow_change
5. **Prioritize gaps** using scoring algorithm (MoT impact, UX breakthrough, cross-loop value)
6. **Generate gap list** with recommended actions (create_new, update_existing, merge_with)

---

## Validation

✅ All 22 scenarios successfully parsed
✅ Coverage map built: scenario_number → features/waves/MoT
✅ MoT coverage identified (currently empty - gap confirmed)
✅ Wave coverage identified (currently empty - gap confirmed)
✅ Artifact coverage analyzed (31.8% YAML, 27.3% e2e)
✅ Persona distribution analyzed
✅ Level distribution confirmed matches "Карта уровней" table
✅ Results saved to JSON for next tasks

**Requirements 1.3 validated:** ✅
- Extracted scenario numbers: 1-22
- Extracted titles: all 22 titles captured
- Extracted covered features: 19 unique features identified
- Built coverage map: scenario_number → covered_features
- Identified MoT coverage: none found (gap confirmed)

---

## Files Generated

1. `parse_scenarios.py` - Parsing script
2. `scenario_analysis.json` - Structured coverage data
3. `task_2.1_summary.md` - This summary document

---

**Task 2.1 Status:** ✅ COMPLETED

**Ready for Task 2.2:** ✅ YES

**Blockers:** None

**Notes:** The parsing revealed that existing scenarios lack explicit MoT and wave references, confirming the need for this refresh spec. The coverage map provides a solid baseline for gap analysis in task 2.2.
