# Implementation Plan: User Scenarios Refresh

## Overview

This plan implements the actualization of `doc/user_scenarios.md` based on closed waves from `doc/backlog_registry.yaml`. The project has completed 146+ packages across 13 CJM moments of truth, but the user scenarios document contains only 22 scenarios and doesn't reflect many important UX improvements and features from closed waves.

**Approach:** Systematic analysis of closed waves → gap identification → targeted scenario creation/updates → consistency verification.

**Key Deliverable:** Updated `doc/user_scenarios.md` with new scenarios for priority closed waves and updated existing scenarios reflecting current UI implementation.

## Tasks

- [x] 1. Set up analysis infrastructure and parse closed waves
  - Parse `doc/backlog_registry.yaml` to extract all waves with `status: completed`
  - Create structured data model for waves (id, theme, north_star, entry_mot, exit_mot, packages, status)
  - Filter out infrastructure-only waves (entry_mot == "infra" or "platform") unless they have user-visible impact
  - Generate initial list of closed waves for analysis
  - _Requirements: 1.1, 1.2, 1.6_

- [x] 2. Analyze existing scenarios and identify gaps
  - [x] 2.1 Parse existing 22 scenarios from `doc/user_scenarios.md`
    - Extract scenario numbers, titles, covered features, and personas
    - Build coverage map: scenario_number → covered_features/waves
    - Identify which MoT moments are covered by existing scenarios
    - _Requirements: 1.3_
  
  - [x] 2.2 Compare closed waves against existing scenario coverage
    - For each closed wave, check if theme/north_star is mentioned in any scenario
    - Classify gaps: new_feature (not covered), ui_update (UI changed), flow_change (flow modified)
    - Identify partial vs complete coverage for each wave
    - _Requirements: 1.4_
  
  - [x] 2.3 Prioritize gaps using scoring algorithm
    - Implement priority scoring: MoT impact (weight 10), UX breakthrough keywords (weight 8), cross-loop value (weight 6)
    - Score all identified gaps and classify as high/medium/low priority
    - Generate prioritized gap list with recommended actions (create_new, update_existing, merge_with)
    - _Requirements: 1.5, 1.7_

- [x] 3. Checkpoint - Review gap analysis results
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Create scenarios for high-priority waves
  - [x] 4.1 Create/update scenario for wave-mission-control-home
    - Update Scenario 18 or create new scenario covering Mission Control home screen with SSR banner and 7 destination tiles
    - Include comparative narrative: "До/После/Wow-момент" structure
    - Add steps describing SSR banner interaction and destination tile navigation
    - _Requirements: 2.1, 2.2, 4.1_
  
  - [x] 4.2 Expand scenarios for wave-smart-study-router family
    - Expand Scenarios 21-22 to cover smart-study-router, surface-parity, and next-level variants
    - Create new Scenario 23 for SSR trust level (wave-smart-study-router-next-level-trust)
    - Create new Scenario 24 for SSR pedagogy level (wave-smart-study-router-next-level-pedagogy)
    - Highlight wow-moment: "система понимает тебя и показывает один лучший следующий шаг"
    - _Requirements: 2.1, 2.2, 4.1, 4.2_
  
  - [x] 4.3 Update scenario for wave-home-mode-selection-v2
    - Update Scenario 18 with improved mode selection UI
    - Replace deprecated UI element names with current equivalents
    - Add "Обновлено после wave-home-mode-selection-v2" note
    - _Requirements: 3.1, 3.2, 3.4, 3.6_
  
  - [x] 4.4 Update scenario for wave-course-retention-resilience
    - Update Scenario 8 to include recovery, promise, and repair features for courses
    - Add steps describing course recovery flow and resilience mechanisms
    - Update "Под капотом" section with retention resilience implementation details
    - _Requirements: 3.1, 3.2, 3.7_
  
  - [x] 4.5 Verify and expand scenario for wave-interactive-tour
    - Verify Scenario 16 adequately covers interactive tour functionality
    - If gaps exist, expand Scenario 16 with missing tour chapters or interactions
    - Ensure tour flow matches current implementation in `app/ui/`
    - _Requirements: 3.1, 3.7_
  
  - [x] 4.6 Expand scenario for ssr-ai-vision waves (L1-L2)
    - Expand Scenario 22 to cover AI Vision levels 1-2 (foundation, explainability, L2-reliability)
    - Add steps describing AI-powered SSR recommendations and explainability features
    - Highlight 5-level AI Vision roadmap and current implementation status
    - _Requirements: 2.1, 2.2, 4.1_

- [x] 5. Checkpoint - Review high-priority scenarios
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Create scenarios for medium-priority waves
  - [x] 6.1 Update scenario for wave-course-learning-v2 (Course Cockpit E30)
    - Update Scenario 8 with Course Cockpit features: graduation overlay, daily briefing
    - Add steps describing E30 cockpit navigation and graduation ceremony
    - Update success signals to include graduation overlay visibility
    - _Requirements: 3.1, 3.2_
  
  - [x] 6.2 Update scenario for wave-flashcard-polish
    - Update Scenario 5 with improved flashcard deck UX
    - Update steps to reflect deck management, editing, and export features
    - Ensure UI element names match current implementation
    - _Requirements: 3.1, 3.2, 3.4_
  
  - [x] 6.3 Update scenario for wave-first-answer-ux
    - Update Scenario 2 with first-answer onboarding improvements
    - Add steps describing 3 clickable examples on first screen
    - Update "Сигнал успеха" to include example visibility
    - _Requirements: 3.1, 3.2_
  
  - [x] 6.4 Verify scenario for wave-plan-visibility
    - Verify Scenario 17 adequately covers plan diff functionality
    - If gaps exist, update Scenario 17 with plan change transparency features
    - Ensure diff visualization matches current implementation
    - _Requirements: 3.1, 3.7_
  
  - [x] 6.5 Update scenario for wave-agentic-tutor-depth
    - Update Scenario 20 with mastery-adaptive tutoring features
    - Add steps describing adaptive tutor routing logic (explain/quiz/review)
    - Update "Под капотом" with agentic tutor depth implementation
    - _Requirements: 3.1, 3.2_

- [x] 7. Checkpoint - Review medium-priority scenarios
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Update document structure and navigation
  - [x] 8.1 Assign unique scenario numbers to new scenarios
    - Number new scenarios sequentially (23, 24, 25, ...)
    - Ensure no gaps or duplicates in scenario numbering
    - Verify consistent format: "Сценарий N — Title"
    - _Requirements: 2.4, 5.1_
  
  - [x] 8.2 Insert new scenarios in appropriate level sections
    - Place scenarios in correct sections: "Первые шаги", "Учебный ритм", "Мастерство", "Power user"
    - Determine level based on entry_mot: #1-#3 → Первые шаги, #4-#7 → Учебный ритм, #8-#14 → Мастерство
    - Maintain narrative flow within each level section
    - _Requirements: 2.3_
  
  - [x] 8.3 Update navigation table with new scenario links
    - Add entries for all new scenarios in "Навигация по сценариям" table
    - Use correct link format: `[Сценарий N — Title](#сценарий-n--title)`
    - Ensure all links are properly formatted and will work correctly
    - _Requirements: 2.5, 5.5_
  
  - [x] 8.4 Update "Карта уровней" table with new scenario counts
    - Recalculate scenario counts for each level (Первые шаги, Учебный ритм, Мастерство, Power user)
    - Update table with new scenario number ranges
    - Verify level distribution is balanced
    - _Requirements: 2.6, 5.4_

- [x] 9. Link scenarios to YAML artifacts and e2e tests
  - [x] 9.1 Find and link YAML artifacts for scenarios
    - For each scenario, search for matching YAML in `doc/scenarios/scenario_NN_*.yaml`
    - Add "Связанные артефакты" section to scenarios with YAML files
    - Note scenarios lacking YAML coverage: "Автотесты: сценарий пока не покрыт..."
    - _Requirements: 6.1, 6.3, 6.4_
  
  - [x] 9.2 Find and link e2e tests for scenarios
    - For each scenario, search for matching e2e test in `tests/e2e/demos/*scenario_NN*.spec.ts`
    - Add e2e test references to "Связанные артефакты" sections
    - Maintain SSoT contract: scenario numbers match YAML filenames
    - _Requirements: 6.2, 6.5_
  
  - [x] 9.3 Create tracking section for coverage gaps
    - Document scenarios without YAML artifacts in separate tracking section
    - Document scenarios without e2e tests in tracking section
    - Provide guidance for future artifact creation
    - _Requirements: 6.7_

- [x] 10. Perform consistency and quality checks
  - [x] 10.1 Verify all scenarios follow template structure
    - Check each scenario has required sections: Context, Persona, Time, Main Question, Steps, Under the Hood, Success Signal
    - Ensure optional sections (Power user tip, If something went wrong) used appropriately
    - Verify consistent tone: живой, практичный, без маркетинговых клише
    - _Requirements: 5.1, 5.2_
  
  - [x] 10.2 Check terminology consistency across document
    - Compare all terms against glossary in requirements.md
    - Replace inconsistent terms with glossary equivalents
    - Verify consistent Russian grammar and style throughout
    - _Requirements: 5.3, 5.7_
  
  - [x] 10.3 Verify document structure and length
    - Ensure section structure preserved: Философия → Навигация → Карта уровней → Сценарии по уровням
    - Check document length is within target: 1500-2000 lines (current 1262 lines)
    - Verify all sections present and properly ordered
    - _Requirements: 5.4, 5.7_
  
  - [x] 10.4 Validate all internal links
    - Parse all internal links in navigation table and scenario cross-references
    - Verify all link targets exist and are correctly formatted
    - Test that links will work correctly in rendered markdown
    - _Requirements: 5.6_

- [x] 11. Run validation scripts and final verification
  - [x] 11.1 Run scenario ID consistency check
    - Execute: `.\.venv\Scripts\python.exe scripts/check_scenario_ids.py`
    - Fix any reported inconsistencies between scenario numbers and YAML filenames
    - Verify all scenario IDs are unique and sequential
    - _Requirements: 6.6_
  
  - [x] 11.2 Verify updated scenarios match current implementation
    - For each updated scenario, cross-reference UI element names with `app/ui/` code
    - Ensure flow descriptions match current implementation
    - Verify technical details in "Под капотом" sections are accurate
    - _Requirements: 3.7_
  
  - [x] 11.3 Perform final document quality review
    - Read through updated document for narrative coherence
    - Check that scenarios tell coherent story of learner's journey
    - Verify personas (Аня, Марк, Сергей, Елена, Максим) used consistently
    - Ensure no duplicate content across scenarios
    - _Requirements: 5.2, 5.3_

- [x] 12. Final checkpoint - Document complete and validated
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- This is a **documentation generation task**, not code implementation - focus on content quality, narrative flow, and consistency
- All new scenarios must follow the existing template structure for consistency
- Priority waves (Mission Control, SSR family, AI Vision) should have prominent placement and wow-moment highlights
- Use comparative language for priority scenarios: "До: [old]. После: [new]. Результат: [wow-moment]"
- Preserve existing scenario numbers and titles unless explicitly required by major changes
- Target document length: 1500-2000 lines (current 1262 lines, budget ~300-700 lines for new content)
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation and user feedback opportunities
- Manual review required for content quality - no automated testing for narrative coherence
- Run `.\.venv\Scripts\python.exe scripts/check_scenario_ids.py` after all updates to verify consistency

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["2.2"] },
    { "id": 3, "tasks": ["2.3"] },
    { "id": 4, "tasks": ["4.1", "4.2", "4.3", "4.4", "4.5", "4.6"] },
    { "id": 5, "tasks": ["6.1", "6.2", "6.3", "6.4", "6.5"] },
    { "id": 6, "tasks": ["8.1"] },
    { "id": 7, "tasks": ["8.2", "8.3", "8.4"] },
    { "id": 8, "tasks": ["9.1", "9.2"] },
    { "id": 9, "tasks": ["9.3", "10.1", "10.2", "10.3"] },
    { "id": 10, "tasks": ["10.4", "11.1", "11.2"] },
    { "id": 11, "tasks": ["11.3"] }
  ]
}
```
