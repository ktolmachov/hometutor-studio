# Design Document: User Scenarios Refresh

## Overview

This design document describes the technical approach for actualizing `doc/user_scenarios.md` based on closed waves from `doc/backlog_registry.yaml`. The project has completed 146+ packages across 13 CJM moments of truth, but the user scenarios document contains only 22 scenarios and doesn't reflect many important UX improvements and features from closed waves.

**Core Challenge:** Bridge the gap between delivered functionality (closed waves in backlog_registry.yaml) and documented user experience (scenarios in user_scenarios.md).

**Solution Approach:** Systematic analysis of closed waves → gap identification → targeted scenario creation/updates → consistency verification.

## Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 1: Analysis                             │
│  Parse backlog_registry.yaml → Extract closed waves →            │
│  Compare with existing scenarios → Identify gaps                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 2: Gap Prioritization                   │
│  Score gaps by: MoT impact, UX breakthrough, cross-loop value    │
│  Filter out: infrastructure-only, already covered                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 3: Scenario Generation                  │
│  For each prioritized gap:                                       │
│    - Create new scenario (if new functionality)                  │
│    - Update existing scenario (if UI/flow changed)               │
│    - Link to YAML artifacts and e2e tests                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 4: Consistency & Verification           │
│  Update navigation table → Verify links → Run check_scenario_ids│
│  Verify document length → Check terminology consistency          │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
backlog_registry.yaml (SSoT for waves)
         │
         ├─→ Extract: wave_id, theme, north_star, entry_mot, exit_mot, status
         │
         ▼
   Closed Waves List
         │
         ├─→ Filter: status == "completed"
         ├─→ Exclude: entry_mot == "infra" OR "platform" (unless user-visible)
         │
         ▼
   Gap Analysis Matrix
         │
         ├─→ Compare: wave themes vs existing 22 scenarios
         ├─→ Score: MoT priority, UX impact, cross-loop value
         │
         ▼
   Prioritized Gaps
         │
         ├─→ High Priority: MoT #1-#14, UX breakthrough, SSR, Mission Control
         ├─→ Medium Priority: Course features, flashcard polish, plan visibility
         ├─→ Low Priority: Quality defense, eval infrastructure
         │
         ▼
   Scenario Updates
         │
         ├─→ New scenarios: gaps not covered by existing scenarios
         ├─→ Updated scenarios: existing scenarios with outdated UI/flow
         │
         ▼
   user_scenarios.md (updated)
```

## Components and Interfaces

### 1. Wave Parser

**Purpose:** Extract structured data from backlog_registry.yaml

**Input:**
- File path: `doc/backlog_registry.yaml`

**Output:**
```python
@dataclass
class Wave:
    id: str
    theme: str
    north_star: str
    entry_mot: str
    exit_mot: str
    packages: List[str]
    status: str
    created: str
    last_touched_mot: Optional[str]
```

**Logic:**
- Parse YAML structure
- Extract all waves with `status: completed`
- Validate required fields present
- Return list of Wave objects

### 2. Gap Analyzer

**Purpose:** Identify functionality in closed waves not covered by existing scenarios

**Input:**
- List of closed waves (from Wave Parser)
- Existing scenarios (from user_scenarios.md)

**Output:**
```python
@dataclass
class Gap:
    wave_id: str
    theme: str
    north_star: str
    entry_mot: str
    exit_mot: str
    priority: str  # "high", "medium", "low"
    gap_type: str  # "new_feature", "ui_update", "flow_change"
    affected_scenarios: List[int]  # existing scenario numbers affected
    recommended_action: str  # "create_new", "update_existing", "merge_with"
```

**Logic:**

1. **Extract existing scenario coverage:**
   - Parse user_scenarios.md
   - Build map: scenario_number → covered_features
   - Example: Scenario 21-22 cover Smart Study Router basics

2. **Compare waves against scenarios:**
   - For each closed wave:
     - Check if theme/north_star mentioned in any scenario
     - Check if entry_mot/exit_mot covered
     - Identify partial vs complete coverage

3. **Classify gaps:**
   - **New feature:** Wave functionality not mentioned in any scenario
   - **UI update:** Wave changed UI elements referenced in existing scenario
   - **Flow change:** Wave modified user flow described in existing scenario

4. **Score priority:**
   ```python
   def calculate_priority(wave: Wave) -> str:
       score = 0
       
       # MoT impact (highest weight)
       if wave.entry_mot in ["#1 Discover", "#2 First Answer", "#3 Transition to tutor"]:
           score += 10
       elif wave.entry_mot.startswith("#") and int(wave.entry_mot.split()[0][1:]) <= 14:
           score += 7
       
       # UX breakthrough keywords
       if any(keyword in wave.theme.lower() for keyword in 
              ["ux breakthrough", "wow", "mission control", "smart study router"]):
           score += 8
       
       # Cross-loop value
       if wave.entry_mot == "cross-loop" or wave.exit_mot == "cross-loop":
           score += 6
       
       # Infrastructure (negative weight unless user-visible)
       if wave.entry_mot in ["infra", "platform"]:
           if "learner" not in wave.north_star.lower():
               score -= 20  # Exclude
       
       if score >= 15:
           return "high"
       elif score >= 8:
           return "medium"
       else:
           return "low"
   ```

### 3. Scenario Template Generator

**Purpose:** Generate new scenario content following existing template structure

**Input:**
- Gap object
- Wave details
- Target level ("Первые шаги", "Учебный ритм", "Мастерство", "Power user")

**Output:**
- Formatted scenario markdown text

**Template Structure:**
```markdown
## Сценарий {N} — {Title}

> *«{User quote expressing need/goal}»*

### Контекст

{Narrative context: who, what, why this matters}

**Для кого:** {Persona}, {situation}
**Время:** {estimated time}
**Главный вопрос:** «{Core question this scenario answers}»

### Шаги

1. **{Action 1}**
   _Почему:_ {rationale}

2. **{Action 2}**
   {Details}

[... more steps ...]

### Под капотом

- {Technical explanation 1}
- {Technical explanation 2}
- {Architecture/implementation details}

### Сигнал успеха

{Observable outcome that indicates success}

### Если что-то пошло не так

| Симптом | Решение |
|---|---|
| {Problem 1} | {Solution 1} |
| {Problem 2} | {Solution 2} |

### Power user tip

{Optional advanced usage tip}

### Следующий шаг

→ [Сценарий {M}](#сценарий-{m}--{title}): {transition description}
```

**Logic:**

1. **Determine scenario level:**
   - entry_mot "#1-#3" → "Первые шаги"
   - entry_mot "#4-#7" → "Учебный ритм"
   - entry_mot "#8-#11" → "Мастерство"
   - entry_mot "#12-#14" or "cross-loop" → "Мастерство"
   - Other → "Power user"

2. **Generate user quote:**
   - Extract key user need from wave.north_star
   - Convert to first-person quote
   - Example: north_star "Learner sees one next action" → quote "Хочу, чтобы система сказала мне, что делать дальше"

3. **Create context narrative:**
   - Explain the problem this wave solves
   - Reference existing user pain points
   - Connect to CJM moment

4. **Generate steps:**
   - Extract user-facing actions from wave packages
   - Order logically (setup → action → verification)
   - Add "Почему" rationale for non-obvious steps

5. **Write "Под капотом":**
   - Reference implementation modules (if known)
   - Explain key technical decisions
   - Link to architecture patterns

6. **Define success signal:**
   - Observable UI change
   - Measurable outcome
   - User feeling/perception

### 4. Scenario Updater

**Purpose:** Update existing scenarios with new UI/flow details from closed waves

**Input:**
- Scenario number to update
- Gap object with update details
- Wave information

**Output:**
- Updated scenario markdown text
- Change summary

**Logic:**

1. **Identify update scope:**
   ```python
   def determine_update_scope(gap: Gap) -> UpdateScope:
       if "UI" in gap.theme or "UX" in gap.theme:
           return UpdateScope.UI_ELEMENTS
       elif "flow" in gap.theme.lower():
           return UpdateScope.USER_FLOW
       elif "mode" in gap.theme.lower():
           return UpdateScope.NAVIGATION
       else:
           return UpdateScope.TECHNICAL_DETAILS
   ```

2. **Preserve core narrative:**
   - Keep scenario number and title unchanged
   - Maintain persona and main question
   - Preserve narrative voice and style

3. **Update specific sections:**
   - **UI_ELEMENTS:** Update step descriptions, UI element names, screenshots references
   - **USER_FLOW:** Reorder steps, add/remove steps, update transitions
   - **NAVIGATION:** Update mode names, entry points, navigation paths
   - **TECHNICAL_DETAILS:** Update "Под капотом" section with new implementation

4. **Add update note:**
   ```markdown
   > **Обновлено после {wave_id}:** {brief description of changes}
   ```

5. **Verify consistency:**
   - Check all internal links still valid
   - Verify UI element names match current implementation
   - Ensure terminology consistent with glossary

### 5. Priority Wave Handler

**Purpose:** Create special wow-moment scenarios for key waves

**Priority Waves (from requirements):**
1. wave-mission-control-home
2. wave-smart-study-router (+ surface-parity + next-level-*)
3. wave-home-mode-selection-v2
4. wave-course-retention-resilience
5. wave-interactive-tour
6. ssr-ai-vision-wave-1-foundation + wave-2-explainability + wave-2b-l2-reliability

**Special Handling:**

1. **Comparative narrative:**
   ```markdown
   ### До и После
   
   **До {wave_id}:**
   {Old behavior/UI}
   
   **После {wave_id}:**
   {New behavior/UI}
   
   **Wow-момент:**
   {What makes this special}
   ```

2. **Highlight innovation:**
   - Emphasize what's unique/breakthrough
   - Use visual language ("skeleton screens появляются мгновенно")
   - Connect to user emotion ("момент, когда система понимает тебя")

3. **Link to demos:**
   - Reference YAML artifacts in `doc/scenarios/`
   - Link to e2e tests in `tests/e2e/demos/`
   - Provide validation commands

4. **Prominent placement:**
   - Early in level section
   - Or dedicated "Wow-моменты" subsection
   - Clear labels in navigation table

### 6. Consistency Checker

**Purpose:** Ensure updated document maintains quality and consistency

**Checks:**

1. **Navigation table completeness:**
   - All scenarios have entry in navigation table
   - All links use correct format: `[Сценарий N — Title](#сценарий-n--title)`
   - No broken internal links

2. **Scenario numbering:**
   - Sequential numbering (1, 2, 3, ..., 22, 23, ...)
   - No gaps or duplicates
   - Consistent format: "Сценарий N — Title"

3. **Level distribution:**
   - Update "Карта уровней" table with new scenario counts
   - Verify scenarios assigned to appropriate levels
   - Check level balance (not too many in one level)

4. **Terminology consistency:**
   - All terms match glossary in requirements.md
   - Consistent Russian grammar and style
   - No English terms where Russian equivalents exist

5. **Document length:**
   - Target: 1500-2000 lines
   - Current: 1262 lines
   - Budget for new scenarios: ~300-700 lines

6. **Template compliance:**
   - All scenarios follow template structure
   - Required sections present (Context, Steps, Under the Hood, Success Signal)
   - Optional sections used appropriately (Power user tip, If something went wrong)

### 7. Artifact Linker

**Purpose:** Link scenarios to YAML artifacts and e2e tests

**Logic:**

1. **Find matching YAML:**
   ```python
   def find_yaml_artifact(scenario_number: int) -> Optional[str]:
       pattern = f"doc/scenarios/scenario_{scenario_number:02d}_*.yaml"
       matches = glob.glob(pattern)
       return matches[0] if matches else None
   ```

2. **Find matching e2e test:**
   ```python
   def find_e2e_test(scenario_number: int) -> Optional[str]:
       pattern = f"tests/e2e/demos/*scenario_{scenario_number:02d}*.spec.ts"
       matches = glob.glob(pattern)
       return matches[0] if matches else None
   ```

3. **Add artifact section:**
   ```markdown
   ### Связанные артефакты
   
   - **YAML:** `doc/scenarios/scenario_{N}_{name}.yaml`
   - **E2E тест:** `tests/e2e/demos/scenario_{N}.spec.ts`
   - **Проверка:** `.\.venv\Scripts\python.exe scripts/check_scenario_ids.py`
   ```

4. **Track coverage gaps:**
   - Maintain list of scenarios without YAML
   - Maintain list of scenarios without e2e tests
   - Add to separate tracking section at end of document

## Data Models

### Wave Data Structure

```yaml
# From backlog_registry.yaml
wave:
  id: wave-mission-control-home
  theme: "Mission Control home screen"
  north_star: "Learner sees SSR banner and 7 destination tiles"
  entry_mot: "#13 Home mode selection"
  exit_mot: "#13 Home mode selection"
  packages:
    - epoch-mission-control-scaffold
    - epoch-mission-control-ssr-integration
  status: completed
  created: 2026-05-01
  last_touched_mot: "#13 Home mode selection"
```

### Gap Analysis Output

```python
gaps = [
    Gap(
        wave_id="wave-mission-control-home",
        theme="Mission Control home screen",
        north_star="Learner sees SSR banner and 7 destination tiles",
        entry_mot="#13 Home mode selection",
        exit_mot="#13 Home mode selection",
        priority="high",
        gap_type="new_feature",
        affected_scenarios=[18],  # Scenario 18 covers home screen
        recommended_action="update_existing"
    ),
    Gap(
        wave_id="wave-smart-study-router",
        theme="Smart Study Router: explainable next study action",
        north_star="Learner sees one local-first next study action with why",
        entry_mot="cross-loop",
        exit_mot="cross-loop",
        priority="high",
        gap_type="new_feature",
        affected_scenarios=[21, 22],  # Scenarios 21-22 cover SSR basics
        recommended_action="create_new"  # Expand coverage
    )
]
```

### Scenario Metadata

```python
@dataclass
class ScenarioMetadata:
    number: int
    title: str
    level: str  # "Первые шаги", "Учебный ритм", "Мастерство", "Power user"
    persona: str  # "Аня", "Марк", "Сергей", "Елена", "Максим"
    time_estimate: str  # "5 минут", "7-10 минут"
    main_question: str
    covered_waves: List[str]  # wave_ids covered by this scenario
    yaml_artifact: Optional[str]
    e2e_test: Optional[str]
    last_updated: Optional[str]  # wave_id that last updated this scenario
```

## Error Handling

### Validation Errors

1. **Missing required wave fields:**
   - **Error:** Wave missing `theme`, `north_star`, or `entry_mot`
   - **Handling:** Skip wave, log warning, continue with other waves
   - **Recovery:** Manual review of backlog_registry.yaml

2. **Broken internal links:**
   - **Error:** Scenario references non-existent scenario number
   - **Handling:** Report all broken links at end
   - **Recovery:** Fix links before finalizing document

3. **Duplicate scenario numbers:**
   - **Error:** Two scenarios with same number
   - **Handling:** Fail fast, report conflict
   - **Recovery:** Renumber scenarios sequentially

4. **Document length exceeded:**
   - **Error:** Updated document > 2000 lines
   - **Handling:** Report warning, suggest consolidation
   - **Recovery:** Merge similar scenarios or move details to separate docs

### Content Quality Issues

1. **Inconsistent terminology:**
   - **Detection:** Compare terms against glossary
   - **Handling:** Report mismatches
   - **Recovery:** Replace with glossary terms

2. **Missing template sections:**
   - **Detection:** Check each scenario for required sections
   - **Handling:** Report incomplete scenarios
   - **Recovery:** Generate missing sections from wave data

3. **Outdated UI references:**
   - **Detection:** Compare UI element names with current implementation
   - **Handling:** Flag for manual review
   - **Recovery:** Update based on latest UI code

## Testing Strategy

**Property-Based Testing Assessment:**

Property-based testing (PBT) is **NOT appropriate** for this feature because:

1. **Not a pure function:** This is a documentation generation and editorial task, not algorithmic code with clear input/output behavior
2. **No universal properties:** Success depends on subjective quality criteria (clarity, narrative flow, style consistency) rather than universal properties that hold across all inputs
3. **Content generation:** The output is human-readable documentation requiring editorial judgment, not data transformations with verifiable invariants
4. **Manual review required:** Quality assessment requires human review of narrative coherence, terminology consistency, and user experience storytelling

**Therefore, the Correctness Properties section is omitted** as recommended by the workflow guidelines for features where PBT does not apply (documentation, content generation, editorial tasks).

**Alternative Testing Approach:**

Instead of PBT, this feature uses:
- **Validation checks** for structural correctness (YAML parsing, markdown format, link integrity)
- **Example-based tests** for specific scenarios (e.g., "wave X should generate scenario Y")
- **Manual review** for content quality, narrative flow, and style consistency
- **Integration tests** for end-to-end document generation workflow

### Unit Tests

**Not applicable** - This is a documentation generation task, not code implementation. However, we can define validation checks:

1. **YAML parsing validation:**
   - Verify backlog_registry.yaml parses correctly
   - Check all required fields present
   - Validate wave status values

2. **Markdown structure validation:**
   - Verify all scenarios follow template
   - Check heading hierarchy correct
   - Validate internal link format

3. **Scenario numbering validation:**
   - Check sequential numbering
   - No gaps or duplicates
   - Consistent format

### Integration Tests

1. **End-to-end document generation:**
   - Input: backlog_registry.yaml + user_scenarios.md
   - Process: Full analysis → gap identification → scenario generation
   - Output: Updated user_scenarios.md
   - Validation: Run `scripts/check_scenario_ids.py`

2. **Link validation:**
   - Parse all internal links
   - Verify targets exist
   - Check navigation table completeness

3. **Artifact linking:**
   - Verify YAML files exist for referenced scenarios
   - Check e2e test files exist
   - Validate file paths correct

### Manual Verification

1. **Content quality review:**
   - Read generated scenarios for clarity
   - Check narrative flow and voice
   - Verify technical accuracy

2. **Consistency check:**
   - Compare terminology with glossary
   - Check Russian grammar and style
   - Verify persona usage consistent

3. **Coverage verification:**
   - Confirm all priority waves covered
   - Check no important gaps missed
   - Verify level distribution balanced

### Validation Commands

```bash
# Check scenario ID consistency
.\.venv\Scripts\python.exe scripts/check_scenario_ids.py

# Verify document length
wc -l doc/user_scenarios.md

# Check for broken links (manual or with markdown linter)
# markdownlint doc/user_scenarios.md

# Verify YAML artifacts exist
ls doc/scenarios/scenario_*.yaml

# Check e2e tests exist
ls tests/e2e/demos/scenario_*.spec.ts
```

## Implementation Phases

### Phase 1: Analysis and Gap Identification

**Input:** backlog_registry.yaml, user_scenarios.md

**Steps:**
1. Parse backlog_registry.yaml
2. Extract all waves with `status: completed`
3. Filter out infrastructure-only waves
4. Compare against existing 22 scenarios
5. Generate gap analysis matrix
6. Prioritize gaps (high/medium/low)

**Output:** Prioritized list of gaps with recommended actions

**Validation:**
- All closed waves processed
- Priority waves identified
- Infrastructure waves correctly filtered

### Phase 2: Priority Wave Scenarios

**Input:** High-priority gaps

**Steps:**
1. wave-mission-control-home → Update Scenario 18 or create new
2. wave-smart-study-router (all variants) → Expand Scenarios 21-22
3. wave-home-mode-selection-v2 → Update Scenario 18
4. wave-course-retention-resilience → Update Scenario 8
5. wave-interactive-tour → Verify Scenario 16 coverage
6. ssr-ai-vision-* → Expand Scenario 22

**Output:** 3-5 new/updated scenarios for priority waves

**Validation:**
- Each priority wave has dedicated coverage
- Wow-moments highlighted
- Comparative narratives included

### Phase 3: Medium-Priority Scenarios

**Input:** Medium-priority gaps

**Steps:**
1. wave-course-learning-v2 (Course Cockpit) → Update Scenario 8
2. wave-flashcard-polish → Update Scenario 5
3. wave-first-answer-ux → Update Scenario 2
4. wave-plan-visibility → Verify Scenario 17 coverage
5. wave-agentic-tutor-depth → Update Scenario 20

**Output:** 3-5 updated scenarios

**Validation:**
- Existing scenarios enhanced
- No duplicate content
- Consistent with priority scenarios

### Phase 4: Consistency and Polish

**Input:** Updated user_scenarios.md draft

**Steps:**
1. Update navigation table with all new scenarios
2. Update "Карта уровней" table
3. Verify all internal links work
4. Check terminology consistency
5. Verify document length within target
6. Add artifact links where available
7. Run `scripts/check_scenario_ids.py`

**Output:** Final user_scenarios.md

**Validation:**
- All checks pass
- No broken links
- Document length 1500-2000 lines
- Consistent style and terminology

## Specific Wave Mappings

### High-Priority Waves

| Wave ID | Theme | Recommended Action | Target Scenario |
|---------|-------|-------------------|-----------------|
| wave-mission-control-home | Mission Control home screen | Update existing | Scenario 18 |
| wave-smart-study-router | SSR core | Expand existing | Scenarios 21-22 |
| wave-smart-study-router-surface-parity | SSR surfaces | Expand existing | Scenarios 21-22 |
| wave-smart-study-router-next-level-trust | SSR trust | Create new | Scenario 23 |
| wave-smart-study-router-next-level-pedagogy | SSR pedagogy | Create new | Scenario 24 |
| wave-smart-study-router-next-level-retention-accessibility | SSR retention | Expand existing | Scenario 22 |
| wave-home-mode-selection-v2 | Home mode selection | Update existing | Scenario 18 |
| wave-course-retention-resilience | Course recovery | Update existing | Scenario 8 |
| wave-interactive-tour | Interactive tour | Verify coverage | Scenario 16 |
| ssr-ai-vision-wave-1-foundation | AI Vision L1 | Expand existing | Scenario 22 |
| ssr-ai-vision-wave-2-explainability | AI Vision L2 | Expand existing | Scenario 22 |
| ssr-ai-vision-wave-2b-l2-reliability | AI Vision L2 reliability | Expand existing | Scenario 22 |

### Medium-Priority Waves

| Wave ID | Theme | Recommended Action | Target Scenario |
|---------|-------|-------------------|-----------------|
| wave-course-learning-v2 | Course Cockpit (E30) | Update existing | Scenario 8 |
| wave-flashcard-polish | Flashcard UX | Update existing | Scenario 5 |
| wave-first-answer-ux | First answer examples | Update existing | Scenario 2 |
| wave-plan-visibility | Plan diff | Verify coverage | Scenario 17 |
| wave-agentic-tutor-depth | Mastery-adaptive tutoring | Update existing | Scenario 20 |
| wave-ux-breakthrough-2026-05 | UX breakthrough | Verify coverage | Scenario 15 |

### Low-Priority Waves (Optional)

| Wave ID | Theme | Recommended Action | Notes |
|---------|-------|-------------------|-------|
| wave-quality-defense-* | Eval baseline, adversarial tests | Create power user scenario | For advanced users |
| wave-non-text-corpus-delivery | OCR/Docling ingest | Create power user scenario | Advanced use case |
| wave-mot2-perceived-latency | Wait UX, two-stage answer | Covered by UX breakthrough | Part of Scenario 15 |

## Out of Scope

The following are explicitly **not** part of this design:

1. **Creating new YAML artifacts** in `doc/scenarios/` - This is a separate task
2. **Writing new e2e tests** for scenarios - This is a separate task
3. **Translating the document** to other languages
4. **Adding scenarios for proposed/deferred waves** - Only closed waves
5. **Changing document structure** (philosophy, navigation, levels)
6. **Creating video demonstrations or screenshots**
7. **Implementing any code changes** - This is documentation only

## Success Criteria

The design is successful if:

1. **Coverage:** All high-priority closed waves have dedicated scenario coverage
2. **Consistency:** Document maintains unified style, structure, and terminology
3. **Validation:** `scripts/check_scenario_ids.py` passes without errors
4. **Length:** Document stays within 1500-2000 lines
5. **Quality:** Scenarios follow template, tell coherent stories, use correct personas
6. **Links:** All internal links work, navigation table complete
7. **Artifacts:** Scenarios reference YAML and e2e tests where available
8. **Freshness:** Updated scenarios reflect current UI implementation

## Appendix: Closed Wave Summary

Based on analysis of backlog_registry.yaml, here are the key closed waves:

**UX & User-Facing (High Priority):**
- wave-mission-control-home
- wave-smart-study-router (+ 3 next-level waves)
- wave-home-mode-selection-v2
- wave-course-retention-resilience
- wave-interactive-tour
- wave-ux-breakthrough-2026-05
- ssr-ai-vision-wave-1-foundation
- ssr-ai-vision-wave-2-explainability
- ssr-ai-vision-wave-2b-l2-reliability

**Learning Features (Medium Priority):**
- wave-course-learning-v2 (Course Cockpit E30)
- wave-flashcard-polish
- wave-first-answer-ux
- wave-plan-visibility
- wave-agentic-tutor-depth

**Infrastructure (Low Priority / Exclude):**
- wave-autonomous-control-plane-v1
- wave-autonomous-control-plane-v2
- wave-production-health
- wave-token-safety-ingestion
- wave-arch-review-remediation-2026-05
- wave-workflow-dx

**Quality & Eval (Low Priority):**
- wave-quality-defense-eval-baseline
- wave-quality-defense-observability
- wave-quality-defense-adversarial-rag

**Demo Scenarios (Already Covered):**
- wave-learning-loop-demo → Scenarios 3-4
- wave-retention-demo → Scenarios 6-7
- wave-orchestration-demo → Scenario 9
- wave-trust-demo → Scenario 11

Total closed waves analyzed: ~40+
High-priority gaps identified: ~12
Medium-priority gaps identified: ~6
Infrastructure waves excluded: ~10
