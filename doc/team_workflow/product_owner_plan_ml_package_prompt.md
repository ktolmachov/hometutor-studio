# Product Owner - ML Package Planning Prompt

Updated: **2026-05-08**

Use this prompt after [`po_router_evaluation_gate.md`](po_router_evaluation_gate.md)
has produced a ready evaluation contract for an AI, ML, LLM, or hybrid package.

This is a product-planning prompt, not an implementation prompt. It defines the
package contract that can later be reviewed and added to
[`../backlog_registry.yaml`](../backlog_registry.yaml).

---

## When To Use

Use this prompt for packages where delivery depends on:

- data collection, labeling, or feature extraction;
- model training, model selection, prompt iteration, or learned policy tuning;
- offline or human evaluation before integration;
- a fallback from AI behavior to deterministic behavior;
- monitoring of accuracy, latency, cost, confidence, or drift.

For deterministic feature packages, use
[`product_owner_plan_package_prompt.md`](product_owner_plan_package_prompt.md).

---

## Required Inputs

```yaml
idea:
  title: "<idea title>"
  type: "ml_package | llm_package | hybrid_intelligence"
  user_value: "<what improves for the learner>"

evaluation_contract:
  primary_metric: "<metric>"
  baseline: "<baseline>"
  target: "<target>"
  test_set: "<source>"

constraints:
  local_first: true
  model_size: "<limit>"
  latency_p95: "<limit>"
  token_budget: "<limit, if LLM is used>"
  explainability: "<required trace>"

fallback:
  current_baseline: "<rule/template behavior>"
  trigger: "<when fallback activates>"
```

---

## Output Format

```yaml
package_id: "<ml-or-llm-package-id>"
type: "ml_package | llm_package | hybrid_intelligence"
status: "proposed"

goal: "<1-2 sentences of learner-facing value>"
user_stories:
  - "<US id or explicit gap>"

data_phase:
  goal: "<what data must exist before model/prompt work>"
  sources:
    - "<local source>"
  labeling:
    method: "<automatic | heuristic | human | none>"
    validation: "<how labels are checked>"
  deliverables:
    - "<data artifact or fixture path>"

model_phase:
  approach: "<sklearn/logistic regression/LLM prompt/reranker/etc>"
  features:
    - "<feature or prompt input>"
  target: "<prediction or generation target>"
  training_or_iteration:
    script: "<path or proposed path>"
    output: "<model/prompt artifact>"
    size_limit: "<limit>"

eval_phase:
  primary_metric: "<metric>"
  baseline: "<baseline>"
  target: "<target>"
  test_set: "<source>"
  script: "<path or proposed path>"
  report: "<report path>"

integration_phase:
  modules:
    - "<intended integration module>"
  behavior: "<how AI output is consumed>"
  fallback: "<rule/template behavior if AI path fails>"
  monitoring:
    - "<latency/cost/quality bound>"

ab_test_phase:
  required: false
  control: "<current behavior>"
  treatment: "<new behavior>"
  metric: "<product metric>"
  duration: "<timebox or not applicable>"

risks:
  - "<data quality/model degradation/privacy/cost risk>"

rollback:
  mode: "<disable model, switch prompt, use previous model, rule-only>"
  trigger: "<metric or incident threshold>"

registry_entry:
  backlog_status: "proposed"
  dependencies:
    - "<evaluation contract id/path>"
  docs_to_update:
    - "doc/changelog.md"
    - "doc/backlog_registry.yaml"
```

---

## Planning Rules

- The evaluation contract comes before implementation tasks.
- Keep WIP small: one model/prompt behavior per package unless the package is an
  explicit wave scaffold.
- Prefer local, lightweight models for runtime decisions.
- LLM calls may explain decisions, but routing decisions must remain traceable.
- Every package needs a rollback plan that restores deterministic behavior.
- Do not edit `doc/backlog_registry.yaml` until the owner accepts the package
  text.

---

## Copy-Paste Prompt

```text
Read doc/team_workflow/product_owner_plan_ml_package_prompt.md
and create an ML/LLM package contract.

Context:
- Idea: <idea title>
- Type: <ml_package | llm_package | hybrid_intelligence>
- Evaluation contract: <primary metric, baseline, target, test set>
- Constraints: <local-first, latency, model size, token budget, explainability>
- Fallback: <current deterministic behavior>

Output:
1. 5-phase package contract (data -> model -> eval -> integration -> A/B)
2. Evaluation contract reference
3. Rollback/fallback plan
4. Proposed backlog_registry.yaml entry with status proposed
```

