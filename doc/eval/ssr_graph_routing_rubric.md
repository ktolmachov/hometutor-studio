# SSR Level 4 graph routing — evaluation rubric

Mirrors `archive/ml_eval/ssr_level4/contract.yaml`. Canonical metric names match the contract (not `prerequisite_violation_rate` from vision drafts).

## Primary: `prerequisite_ordering_accuracy`

**Baseline:** rule router without graph prerequisite audit (`first_weak_concept` = mastery list head).

**Target:** ≥ 0.85 aggregate on cases tagged `weak_ordering` (contract target).

**Scope:** only cases with `metric_tags` containing `weak_ordering` and `skip_ordering_metric` not true. Cases with `expected_weak_order: null` are excluded (pass-with-skip).

**Algorithm (pairwise compliance):**

- Let `actual_order` be `[first_weak_concept]` when a single weak focus, or `_order_weak_by_prerequisites(weak_concepts, fixture_kg)` for multi-weak cases (harness field `weak_concepts`, optional).
- Let `S` be the concept set from `expected_weak_order`.
- Denominator: all unordered pairs `(u, v)` with `u != v` in `S` — `n(n-1)/2`.
- Numerator: pairs `(u, v)` where `index(u) < index(v)` in `actual_order` **and** `v` is **not** a prerequisite of `u` in the fixture graph (no prerequisite inversion).
- Score per case: `numerator / denominator`; empty denominator → skip case.
- Aggregate: mean of per-case scores on included cases; harness asserts ≥ 0.85.

## Baseline regression policy

**Zero `hint_kind` / `primary_nav` regression** on scaffold fixtures:

- Cases tagged `baseline_regression` assert golden `expected_hint_kind` + `expected_primary_nav` against `build_smart_study_recommendation` (rule path, ML hybrid disabled in harness).
- Plus existing policy suite: `tests/test_smart_study_router.py` with `-k` filter from contract DoD.

Partial golden only — no full `SmartStudyRecommendation` snapshot in scaffold.

## Secondary metrics

| Metric | Scaffold |
|--------|----------|
| `orphan_concept_rate` | Measured on fixture graphs via `get_graph_prerequisites_health` patterns / inline orphan nodes in cases |
| `cycle_count` | `find_prerequisite_cycles` on fixture subgraph; expect 0 blocking cycles on “ready” cases |
| `routing_latency_p95` | **N/A** — deferred to `epoch-ssr-graph-routing-v1`; contract retains field for forward compatibility |

## Fallback (contract-aligned)

`mode: rule_based` when: missing prerequisites data, cycle detected, graph unavailable, or eval regression on baseline goldens. User-visible trace: baseline SSR reason, no graph-based adjustment in scaffold.

## Harness commands

```text
.\.venv\Scripts\python.exe scripts\validate_evaluation_contract.py archive/ml_eval/ssr_level4/contract.yaml
.\.venv\Scripts\python.exe -m pytest tests/eval/test_ssr_graph_routing.py -v --tb=short
```
