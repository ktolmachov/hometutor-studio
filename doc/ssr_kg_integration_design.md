# SSR ↔ Knowledge Graph integration (L4 scaffold design)

Maintainer-facing design for **epoch-ssr-graph-routing-eval-scaffold-v1**. Production SSR and UI are **unchanged** in this package.

## Boundaries

**No learner-visible graph override in this package.** No Streamlit changes, no new `session_state` keys, no feature flags, no `app/**` edits. Scaffold delivers design + offline eval only; runtime hook ships in follow-up `epoch-ssr-graph-routing-v1`.

## Baseline data flow (unchanged in scaffold)

1. **Signal collection (UI)** — `app/ui/mission_control.py`, `app/ui/resume_cards_smart_study.py`, `app/ui/adaptive_plan_hub_layout.py`, tutor surfaces: queues (`flashcard_due_n`, `sm2_due_n`), `quiz_feedback_status`, `has_tutor_resume`, `tutor_topic`, `has_last_answer_qa`, optional recovery ladder step from `smart_study_recovery_ladder`.
2. **Weak concept today** — `first_weak_concept = ctx.weak_concepts[0]` from `get_weak_concepts()` (quiz mastery order via `weak_concepts_for_kg`), **not** KG topological order.
3. **Facade** — `build_smart_study_recommendation` in `app/smart_study_router.py`.
4. **Pipeline** — `_build_smart_study_recommendation_rules` → `_apply_ssr_ml_hybrid_if_enabled` → `apply_source_coverage_route_guard` → `_apply_concept_recovery_ladder_overlay`.
5. **Render** — `app/ui/smart_study_next_step_card.py`; `hint_kind` maps through `HINT_TO_TILE` in `mission_control.py`.

### session_state provenance (read-only citations)

| Key / pattern | Role in SSR |
|---------------|-------------|
| `last_answer` | `has_last_answer_qa` → `answer_ready` |
| `current_topic` | Tutor topic fallback |
| `concept_recovery_ladder_step` (+ `_CONCEPT_RECOVERY_*` in `resume_cards_smart_study.py`) | Recovery ladder on `quiz_failed` |
| `smart_study_steering_preference` (via `user_state`) | Post-render steering in card |

No new keys in scaffold.

## Read-only KG APIs (reference)

From `app/knowledge_graph.py` (read-only in follow-up):

- `JsonKnowledgeGraph`, `get_prerequisites`, `topological_sort`, `find_prerequisite_cycles`, `get_graph_prerequisites_health`, `weak_concepts_for_kg`
- Active graph: `get_active_knowledge_graph()` (prod `data/concept_graph.json` or bundle SQLite)

**NBA / learning-plan path (parallel, not SSR today):** `get_next_best_actions_for_user`, `get_learning_plan_graph_bundle` — prerequisite-respecting plan actions. L4 weak reorder may align with topo on a subset but **must not** imply SSR calls NBA in the current baseline.

## Fallback matrix

| Condition | SSR behavior (scaffold + prod today) |
|-----------|--------------------------------------|
| Graph file missing / unloadable | Rule-based SSR identical to today; no graph adjustment |
| Prerequisite cycle in subgraph | `topological_sort` warns; no graph-based weak reorder in prod |
| Dangling prerequisite edge | Treat as missing edge; rule copy unchanged |
| Weak concept not in graph | `first_weak_concept` still passed; `why_now_ru` without false prereq claims |
| Higher-priority queues (`cards_due`, `sm2_due`, `answer_ready`, …) | Graph reorder (follow-up) applies only within same `hint_kind` tier; never bypasses `_build_smart_study_recommendation_rules` priority |

## Follow-up hook (epoch-ssr-graph-routing-v1)

**Recommended placement:** pure helper `order_weak_concepts_for_ssr(weak_ids, kg) -> str | None` in new `app/ssr_graph_routing.py`, invoked inside `build_smart_study_recommendation` **after** `_build_smart_study_recommendation_rules` and **before** `_apply_ssr_ml_hybrid_if_enabled`, mutating effective `first_weak_concept` only when rule `hint_kind` ∈ `{quiz_failed, mastery_stale}` and no higher-priority queue signals.

**Rejected for scaffold:** reorder at UI call sites — duplicates logic across four surfaces.

**This package:** test-only `_order_weak_by_prerequisites` in `tests/eval/test_ssr_graph_routing.py` scores L4 expectation without prod merge.

## Explainability

Graph influence (follow-up) may extend `why_now_ru` / `ml_audit_ru` only. `SmartStudyRouterHintKind`, `primary_nav`, and `HINT_TO_TILE` mapping stay stable (US-20.1).

## Eval alignment

- Contract: `archive/ml_eval/ssr_level4/contract.yaml`
- Rubric: `doc/eval/ssr_graph_routing_rubric.md`
- Harness: `tests/eval/test_ssr_graph_routing.py`, `tests/eval/ssr_graph_routing_cases.json`
- KG readiness assumption: `doc/kg_completeness_report.md` (graph **ready** for design/fixtures)
