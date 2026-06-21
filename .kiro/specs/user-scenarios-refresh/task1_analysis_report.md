# Task 1: Analysis Infrastructure and Closed Waves Parsing

## Summary

Successfully parsed `doc/backlog_registry.yaml` and extracted all closed waves with user-visible impact.

## Results

- **Total closed waves found:** 39
- **Infrastructure-only waves filtered out:** Multiple waves with `entry_mot: "infra"` or `"platform"` were excluded unless they had user-visible impact (e.g., waves mentioning "Learner" in north_star were kept)
- **Output file:** `.kiro/specs/user-scenarios-refresh/closed_waves.json`

## Data Model

Created structured `Wave` dataclass with fields:
- `id`: Wave identifier (e.g., "wave-mission-control-home")
- `theme`: Short description of the wave
- `north_star`: Success metric/goal
- `entry_mot`: Entry moment of truth from CJM
- `exit_mot`: Exit moment of truth from CJM
- `packages`: List of package IDs in the wave
- `status`: Wave status (filtered to "completed" only)
- `created`: Creation date
- `last_touched_mot`: Optional last touched MoT
- `kill_switch`: Optional kill switch criteria

## Breakdown by Entry MoT

| Entry MoT | Count |
|-----------|-------|
| cross-loop | 10 waves |
| #2 First Answer | 4 waves |
| #13 Home mode selection | 3 waves |
| Ingest / Discover | 3 waves |
| course-workspace | 3 waves |
| #1 Discover | 2 waves |
| #10 Retrieval trust | 2 waves |
| #7 Progress | 2 waves |
| infra | 2 waves (with user-visible impact) |
| #11 Retain | 1 wave |
| #12 Flashcard review | 1 wave |
| #3 Transition to tutor | 1 wave |
| #4 First micro-quiz | 1 wave |
| #6 Adaptive plan | 1 wave |
| #8 Learning plan | 1 wave |
| #8 Progress | 1 wave |
| Ingest / Trust | 1 wave |

## Key Closed Waves Identified

### High-Priority Waves (from requirements)

1. **wave-mission-control-home** - Mission Control home screen with SSR banner and 7 destination tiles
2. **wave-smart-study-router** + 4 next-level variants - Smart Study Router family (10 waves total in cross-loop)
3. **wave-home-mode-selection-v2** - Improved home mode selection UI
4. **wave-course-retention-resilience** - Course recovery, promise, and repair features
5. **wave-interactive-tour** - Interactive in-app onboarding tour (5 chapters)
6. **ssr-ai-vision-wave-1-foundation** + wave-2-explainability + wave-2b-l2-reliability - AI Vision levels 1-2

### Medium-Priority Waves

7. **wave-course-learning-v2** - Course Cockpit (E30) with graduation overlay
8. **wave-course-homework-playbook** - Homework playbook for courses
9. **wave-flashcard-polish** - Flashcard deck UX improvements
10. **wave-first-answer-ux** - First-answer onboarding with 3 clickable examples
11. **wave-plan-visibility** - Adaptive plan transparency with diff
12. **wave-agentic-tutor-depth** - Mastery-adaptive tutoring

### UX Breakthrough Wave

13. **wave-ux-breakthrough-2026-05** - Perceived quality and wow-moments (skeleton screens, celebration overlays, session analytics)

### Demo Waves (Already Covered in Scenarios)

- **wave-learning-loop-demo** - Answer → tutor → quiz loop
- **wave-retention-demo** - SRS + progress retention engine
- **wave-orchestration-demo** - Personalized learning plan
- **wave-trust-demo** - Trust drill-down with sources

### Infrastructure/Quality Waves (Lower Priority)

- **wave-quality-defense-adversarial-rag** - Adversarial RAG tests
- **wave-non-text-corpus-delivery** - OCR/Docling ingest
- **wave-mot2-perceived-latency** - Wait UX and two-stage answer
- **wave-e5-learner-state-migration** - Learner state migration
- **wave-e8-user-value-delivery** - User value delivery discipline

## Infrastructure Filtering

The following types of waves were filtered out:
- Waves with `entry_mot: "infra"` or `"platform"` that don't mention user-visible impact
- Examples kept: `wave-sync-export` (Learner переносит прогресс), `wave-e5-learner-state-migration` (Learner profile survives)

## Next Steps

Task 2 will:
1. Parse existing 22 scenarios from `doc/user_scenarios.md`
2. Compare closed waves against existing scenario coverage
3. Identify gaps and prioritize them using the scoring algorithm
4. Generate recommendations for creating new scenarios or updating existing ones

## Requirements Validated

✅ **Requirement 1.1:** Identified all waves with `status: completed` (39 waves)
✅ **Requirement 1.2:** Extracted structured data (id, theme, north_star, entry_mot, exit_mot, packages, status)
✅ **Requirement 1.6:** Filtered out infrastructure-only waves unless they have user-visible impact
✅ **Requirement 1.7:** Generated initial list of closed waves for analysis (saved to JSON)

## Script Location

The analysis script is available at: `scripts/analyze_closed_waves.py`

To re-run the analysis:
```bash
.\.venv\Scripts\python.exe scripts/analyze_closed_waves.py
```
