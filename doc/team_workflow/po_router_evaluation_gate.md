# PO Router - Evaluation Contract Gate

Updated: **2026-05-08**

Use this module before planning or implementing any AI-assisted feature in
`hometutor`. The goal is to make evaluation explicit before an ML, LLM, or
hybrid package enters the backlog.

Main router: [`product_owner_router.md`](product_owner_router.md).

---

## When To Use

Use this gate when a proposed idea:

- uses an ML model, LLM call, classifier, reranker, planner, or learned policy;
- changes routing, ranking, explanations, or study recommendations with AI;
- needs a human-eval rubric, offline eval harness, or model-quality target;
- has cost, latency, privacy, or explainability constraints.

If the idea is purely deterministic and already has ordinary acceptance
criteria, use [`product_owner_plan_package_prompt.md`](product_owner_plan_package_prompt.md)
instead.

---

## Required Inputs

```yaml
feature: "<feature title>"
current_behavior: "<deterministic or template baseline>"
baseline_metric: "<current measured value or explicit unknown>"
target_metric: "<desired value>"
constraints:
  latency: "<p95 target>"
  cost: "<token/model/runtime budget>"
  privacy: "<local-only/cloud/anonymized>"
  explainability: "<trace requirements>"
read_set:
  - "<1-3 docs or code signatures used to define the contract>"
```

Rules:

- Do not write implementation tasks until the evaluation contract is complete.
- Prefer measured baselines. If baseline is unknown, the first deliverable is a
  baseline measurement task.
- Every AI decision must have a deterministic fallback or an explicit abort
  policy.
- Keep test data local unless the owner explicitly accepts a different privacy
  mode.

---

## Output Format

```yaml
evaluation_contract:
  feature: "<feature title>"
  owner_decision: "proposed | ready_for_package | blocked"

  metrics:
    primary:
      name: "<metric_name>"
      type: "offline_eval | human_eval | product_metric | latency | cost"
      baseline: "<current value, random baseline, or unknown>"
      target: "<target value>"
      test_set: "<source and size>"
    secondary:
      - name: "<metric_name>"
        target: "<bound>"

  test_harness:
    script: "<path or proposed path>"
    data: "<path or proposed path>"
    rubric: "<path or proposed path, if human_eval>"
    command: ".\\.venv\\Scripts\\python.exe -m pytest <targeted tests>"

  success_criteria:
    - "primary metric hits target"
    - "all secondary metrics stay within bounds"
    - "no regression in deterministic baseline behavior"

  failure_plan:
    - condition: "<what failed>"
      action: "<iterate, fallback, shrink scope, or abort>"

  fallback:
    mode: "rule_based | template_based | previous_model | disabled"
    trigger: "<exception, confidence, latency, or metric threshold>"
    user_visible_trace: "<what the user can inspect>"
```

---

## Review Checklist

- Primary metric reflects the user-facing value, not only model convenience.
- Baseline is measured or the package explicitly includes baseline measurement.
- Test set is local, reproducible, and separated from any training set.
- Latency and cost constraints are explicit.
- Failure plan says what to do after a miss; it is not just "try again".
- Fallback preserves the current deterministic path.
- The contract can be linked from `backlog_registry.yaml` before implementation.

---

## Failure Modes

If an idea fails the eval gate during ideation, do not move straight into
implementation. Pick one explicit outcome:

| Outcome | Use when | Next step |
|---|---|---|
| `park` | Evaluation cost, data need, or human-review effort is larger than the expected product value. | Record the reason in the ideation artifact and leave the idea out of the active backlog. |
| `iterate` | The signal is measurable, but the current target, constraints, or mitigation plan is too ambitious. | Lower or narrow the target, add mitigations, then rerun the eval-contract review once. |
| `reject` | No local, reproducible metric can show whether the AI path improves the learner outcome. | Reject the AI framing and keep or improve the deterministic baseline instead. |

---

## Copy-Paste Prompt

```text
Read doc/team_workflow/po_router_evaluation_gate.md
and create an evaluation contract.

Context:
- Feature: <feature title>
- Current behavior: <baseline behavior>
- Baseline metric: <current value or unknown>
- Target metric: <desired target>
- Constraints: <latency/cost/privacy/explainability>

Output:
1. Evaluation contract (metrics, harness, success criteria)
2. Test data and rubric proposal
3. Failure plan
4. Fallback plan
5. Decision: ready_for_package or blocked
```
