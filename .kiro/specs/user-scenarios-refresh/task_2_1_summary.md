# Task 2.1 Summary: Parse Existing 22 Scenarios

## Task Completion

✅ **Task 2.1 completed successfully**

Extracted scenario numbers, titles, covered features, and personas from `doc/user_scenarios.md`. Built comprehensive coverage map identifying which MoT moments are covered by existing scenarios.

## Key Findings

### Scenario Statistics

- **Total scenarios:** 22
- **Scenarios with YAML artifacts:** 7/22 (32%)
- **Scenarios with e2e tests:** 6/22 (27%)
- **MoT moments covered:** 14 (#1-#14)
- **Unique features covered:** 19
- **Wave references found:** 0 (no explicit wave-* references in existing scenarios)

### Scenarios by Level

| Level | Count | Scenario Numbers |
|-------|-------|------------------|
| **Первые шаги** (First Steps) | 6 | 1, 2, 3, 15, 16, 19 |
| **Учебный ритм** (Learning Rhythm) | 4 | 4, 5, 6, 7 |
| **Мастерство** (Mastery) | 9 | 8, 9, 10, 11, 17, 18, 20, 21, 22 |
| **Power user** | 3 | 12, 13, 14 |

### MoT Coverage Analysis

All 14 MoT moments from the CJM are covered by existing scenarios:

| MoT | Description | Covered by Scenarios |
|-----|-------------|---------------------|
| #1 | Discover / First Launch | 1, 22 |
| #2 | First Answer | 3, 16, 22 |
| #3 | Transition to Tutor | 1, 2, 3, 7, 16, 18, 19, 21, 22 |
| #4 | Learning Session | 4, 22 |
| #5 | Flashcard Generation | 5 |
| #6 | Spaced Repetition (SM-2) | 5, 6, 7, 8, 9, 15, 18, 21, 22 |
| #7 | Return Next Day | 3, 6, 7, 16, 18, 20, 21 |
| #8 | Course Workspace | 1, 5, 7, 8, 9, 16, 20, 22 |
| #9 | Adaptive Plan | 4, 10, 13, 14, 17 |
| #10 | Mastery & Graduation | 3, 4, 7, 8, 9, 10, 12, 13, 14, 15, 20, 22 |
| #11 | Trust Panel | 2, 10, 11, 16, 17, 21, 22 |
| #12 | Telegram | 12 |
| #13 | Home Mode Selection | 1, 2, 3, 4, 8, 12, 15, 16, 18, 19, 20, 21 |
| #14 | Backup & Offline | 12, 14 |

**Key Insight:** MoT #3 (Transition to Tutor) and #13 (Home Mode Selection) have the broadest coverage, appearing in 9 and 12 scenarios respectively. MoT #5 (Flashcard Generation) and #12 (Telegram) have the narrowest coverage with only 1-2 scenarios each.

### Feature Coverage Analysis

Top 10 most covered features:

1. **Tutor** - 19 scenarios (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 20, 21, 22)
2. **Home Hub** - 17 scenarios (1, 2, 3, 4, 7, 8, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 21)
3. **Trust Panel** - 15 scenarios (1, 2, 3, 5, 9, 10, 11, 12, 14, 15, 16, 17, 21, 22)
4. **Flashcards** - 14 scenarios (4, 5, 6, 7, 8, 9, 12, 13, 14, 15, 16, 18, 21, 22)
5. **Mastery** - 12 scenarios (3, 4, 7, 8, 9, 10, 12, 13, 14, 15, 20, 22)
6. **SM-2** - 10 scenarios (5, 6, 7, 8, 9, 15, 18, 21, 22)
7. **Course Workspace** - 9 scenarios (1, 5, 7, 8, 9, 16, 20, 22)
8. **Adaptive Plan** - 6 scenarios (4, 9, 10, 13, 14, 17)
9. **Reindex** - 5 scenarios (1, 7, 13, 14, 22)
10. **Quick Answer** - 4 scenarios (1, 2, 3, 11)

**Specialized features with limited coverage:**
- **Smart Study Router** - 2 scenarios (21, 22)
- **AI Vision** - 22 scenarios (appears in all scenarios as a cross-cutting theme)
- **Interactive Tour** - 1 scenario (16)
- **Telegram** - 1 scenario (12)
- **UX Breakthrough** - 1 scenario (15)
- **Plan Diff** - 2 scenarios (9, 17)
- **Pedagogical Router** - 3 scenarios (3, 4, 20)

### Personas Distribution

| Persona | Scenarios | Description |
|---------|-----------|-------------|
| **Аня** | 1, 3, 5, 7, 10, 16, 20, 21 | Student, 3rd year, preparing for exams |
| **Марк** | 4, 6, 9, 13, 17 | Developer, preparing for technical interviews |
| **Максим** | 2, 19 | Developer, needs quick answers |
| **Сергей** | 8, 12 | Taking ML course, active user |
| **Елена** | 14 | Works with confidential materials |
| **Generic** | 11, 15, 18, 22 | Any user, skeptical user, returning learner, project defense |

**Key Insight:** Аня (student persona) is the most represented with 8 scenarios, reflecting the primary target audience. Марк (developer preparing for interviews) appears in 5 scenarios, showing the secondary use case.

### YAML Artifacts Coverage

Scenarios with YAML artifacts (7/22):
- Scenario 15: `scenario_15_ux_breakthrough.yaml`
- Scenario 16: `scenario_16_interactive_tour.yaml`
- Scenario 17: `scenario_17_plan_diff.yaml`
- Scenario 18: `scenario_18_home_retention_hub.yaml`
- Scenario 19: `scenario_19_env_validation.yaml`
- Scenario 21: `scenario_21_smart_study_router.yaml`
- Scenario 22: `scenario_22_ai_router_vision.yaml`

**Gap:** 15 scenarios (1-14, 20) lack YAML artifacts. These are primarily foundational scenarios covering core features.

### E2E Test Coverage

Scenarios with e2e tests (6/22):
- Scenario 16: `scenario_16_interactive_tour.spec.ts`
- Scenario 17: `scenario_17_plan_diff.spec.ts` + smoke test
- Scenario 18: `scenario_18_home_retention_hub.spec.ts`
- Scenario 19: `scenario_19_env_validation.spec.ts` + smoke test
- Scenario 21: `scenario_21_smart_study_router.spec.ts` + smoke test
- Scenario 22: `scenario_22_ai_router_vision.spec.ts`

**Gap:** 16 scenarios lack e2e test coverage.

### Wave References

**Critical Finding:** No explicit wave-* references were found in the existing scenarios.

This confirms the requirements document's assertion that the scenarios document is outdated and doesn't reflect the 146+ closed packages and recent waves like:
- `wave-mission-control-home`
- `wave-smart-study-router` family
- `wave-home-mode-selection-v2`
- `wave-course-retention-resilience`
- `wave-interactive-tour`
- `ssr-ai-vision-wave-*` family

**Implication:** The gap analysis in Task 2.2 will need to identify which closed waves are not adequately covered by existing scenarios.

## Coverage Map Structure

The coverage map has been built with the following structure for each scenario:

```python
{
    scenario_number: {
        'title': str,
        'level': str,  # "Первые шаги", "Учебный ритм", "Мастерство", "Power user"
        'persona': str,
        'features': List[str],
        'waves': List[str],  # Currently empty - no wave references found
        'mot_moments': List[str],  # e.g., ["#1", "#3", "#13"]
        'yaml_artifact': Optional[str],
        'e2e_test': Optional[str]
    }
}
```

## Deliverables

1. ✅ **scenario_parser.py** - Python script to parse scenarios and build coverage map
2. ✅ **scenario_coverage_report.txt** - Comprehensive 1640-line report with:
   - Summary statistics
   - Detailed scenario breakdown (all 22 scenarios)
   - MoT coverage matrix
   - Feature coverage matrix
3. ✅ **task_2_1_summary.md** - This summary document

## Next Steps

**Task 2.2** should use this coverage map to:
1. Compare closed waves from `backlog_registry.yaml` against existing scenario coverage
2. Identify gaps where important waves are not covered
3. Classify gaps as: new_feature, ui_update, or flow_change
4. Determine which scenarios need updates vs. which need new scenarios

**Key Questions for Task 2.2:**
- Which priority waves (Mission Control, SSR family, AI Vision) are adequately covered?
- Which scenarios need updates to reflect UI changes (e.g., Scenario 18 for Mission Control)?
- Which waves require entirely new scenarios?

## Requirements Validation

✅ **Requirement 1.3** - Extracted scenario numbers, titles, covered features, and personas
✅ **Coverage map built** - scenario_number → covered_features/waves/MoT moments
✅ **MoT coverage identified** - All 14 MoT moments mapped to scenarios

## Files Created

- `.kiro/specs/user-scenarios-refresh/scenario_parser.py`
- `.kiro/specs/user-scenarios-refresh/scenario_coverage_report.txt`
- `.kiro/specs/user-scenarios-refresh/task_2_1_summary.md`

---

**Task 2.1 Status:** ✅ **COMPLETE**
