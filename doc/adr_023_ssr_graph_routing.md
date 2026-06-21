# ADR-023: SSR Graph Routing — Prerequisite-Aware Weak-Concept Ordering

**Status:** Accepted
**Date:** 2026-05-29
**Scope:** Smart Study Router graph-routing subsystem (4 modules)

---

## Context

The Smart Study Router (SSR) produces next-step recommendations from a learner's weak concepts. As the knowledge graph grew, ordering recommendations purely by mastery delta ignored prerequisite structure: learners were directed to advanced concepts before foundational gaps were closed, reducing completion rates and increasing re-attempt loops.

Four new modules were added across two epochs to address this:

- `app/ssr_graph_routing.py` — prerequisite-aware ordering of weak concepts using knowledge graph edges.
- `app/smart_study_route_simulator.py` — what-if preview of alternative SSR routes (pure, no side effects).
- `app/smart_study_recovery_ladder.py` — Concept Recovery Ladder contract (US-20.1): overlay, resume blob, persistence helpers.
- `app/ssr_explanation_tier_gate.py` — gate deciding whether SSR "why now" explanation requires LLM enrichment or can use a static template.

No dedicated ADR was written at implementation time. This ADR records the rationale retroactively.

---

## Decision

### Graph Routing (`ssr_graph_routing.py`)

- Order weak-concept recommendations by prerequisite depth: concepts with no unmastered prerequisites are promoted; concepts that depend on unmastered prerequisites are deferred.
- Pure helper module: takes a list of candidate concepts and the learner's mastery snapshot; returns a re-ordered list with `prerequisite_gap` annotations.
- No DB writes, no LLM calls, no global state.

### Route Simulator (`smart_study_route_simulator.py`)

- Given the current `SmartStudyRecommendation` and a secondary `action_id`, produce a `SimulatedRoute` with counterfactual primary label, reason, or limitation.
- Used exclusively by UI and eval code for "what if" preview rendering; never called on the hot path.
- Pure deterministic; regression-safe to run without network.

### Recovery Ladder (`smart_study_recovery_ladder.py`)

- Implements the Concept Recovery Ladder per US-20.1: a prioritized remediation sequence when a learner fails a concept multiple times.
- Contracts: overlay payload, resume blob schema, SQLite persistence helpers.
- Consumes `user_state_ssr_feedback` for historical failure counts.

### Explanation Tier Gate (`ssr_explanation_tier_gate.py`)

- Decides at card-render time whether the "why now" explanation should be:
  - `template_only` — static string from recommendation, no LLM cost.
  - `llm_enriched` — triggers `adaptive_plan_llm_enrichment` enrichment path.
- Criteria: learner mastery confidence, recommendation action type, and feature flag `ssr_explanation_llm_enrichment_enabled`.

---

## Consequences

- **Ordering stability:** prerequisite ordering is deterministic given the same graph snapshot. Tests can assert ordering without mocking.
- **Simulator isolation:** route simulator has no production side effects; can be safely called from eval harness and UI preview widgets.
- **LLM cost control:** tier gate prevents LLM enrichment for low-value explanations; default threshold keeps >70% of cards template-only.
- **Recovery ladder persistence:** recovery state survives app restarts via SQLite; requires migration on schema changes.

---

## Related

- ADR-020: Smart Study Router and SSR ML Hybrid Contract
- ADR-021: Smart Router RAG modes and bounded GraphRAG analytics (`adr_021_smart_router_rag_modes.md`)
- ADR-022: SSR-AI eval harness and local artifact contract (`adr_022_ssr_ai_eval_harness.md`)
- `doc/architecture.md` Module Reference § Services (domain/application)
