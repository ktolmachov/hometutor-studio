# Execution Contract — `ragas-retrieval-metrics-v1`

**Wave:** `wave-ragas-eval-harness` (proposed) · **Position:** 1/2 · **Status:** proposed
**Created:** 2026-06-05 · **Owner:** TBD · **Cost:** M · **Priority:** P1 · **Impact:** eval
**Registry entry (SSoT):** [`doc/backlog_registry.yaml`](../backlog_registry.yaml) → `items[].id == ragas-retrieval-metrics-v1`
**Source idea:** [`ai_driven_design_waves_proposal.md` § I4](ai_driven_design_waves_proposal.md)

> This is the human-readable expansion of the structured registry item. The registry remains SSoT
> for status/scope; this doc carries the rationale, precise gap analysis, and DoD detail.

---

## 1. Context & precise gap

The lecture ([`summary_01-ai-driven-design.md`](../../../../exchange/summary_01-ai-driven-design.md)) calls for an
evaluation loop with datasets and runs (Langfuse). hometutor already evaluates RAG quality:

| Already present | Where | Metric class |
|---|---|---|
| `faithfulness`, `answer_relevancy`, context-relevancy | `app/eval_service.py`, `app/compare_eval.py`, `app/async_quality_judge.py` (LlamaIndex evaluators) | generation quality |
| `recall@k`, `MRR`, `hit_rate` | `app/eval_retrieval_comparison.py` (`calculate_recall_at_k`, `calculate_mrr`, `calculate_hit_rate`, `RetrievalComparisonEngine`) | retrieval quality |
| labeled ground truth | `eval_data/retrieval_regression.json` (`expected_sources`) | dataset |

**So the honest gap is narrow and sharp.** RAGAS-style coverage that is *missing*:

1. **`context_precision` (rank-aware precision@k)** — recall@k answers "did we find the relevant docs?";
   precision@k answers "of what we returned, how much is relevant, and is it ranked first?" Not present.
2. **`answer_correctness` vs reference** — current faithfulness checks the answer is grounded in *retrieved*
   context; it does **not** compare the answer to a *reference/ground-truth answer*. Different signal.

**Out of scope (already covered — do not re-implement):** recall@k, MRR, hit_rate, faithfulness, answer_relevancy.

**Design stance:** add the two missing metrics in the **native pure-Python style** of `eval_retrieval_comparison.py`
(no new hard dependency). The actual `ragas` library is wired only as an **optional cross-check backend**
behind `ENABLE_RAGAS_METRICS` (default `False`) — keeps the harness local-first and dependency-light.

---

## 2. Scope

**In scope**
- `calculate_precision_at_k()` + rank-aware `context_precision()` in `app/eval_retrieval_comparison.py`.
- `answer_correctness` (semantic similarity to `reference`) in the answer-eval path, skipped when no reference.
- Surface both in the comparison report (`app/compare_eval.py`).
- Labeled fixtures: ≥10 `retrieval_regression.json` cases with non-empty `expected_sources`; `reference` on a
  subset of `eval_questions.json`.
- `ENABLE_RAGAS_METRICS` flag (`app/config.py`) + graceful import guard for the optional `ragas` backend.

**Out of scope**
- Langfuse dataset integration → that is `ragas-langfuse-dataset-v1` (package 2/2, gated on `wave-langfuse-eval-loop`).
- Changing retrieval defaults, provider routing, or any runtime answer path. **Eval-only change.**

---

## 3. Read-set (token-safe)

| File | How to read |
|---|---|
| `app/eval_retrieval_comparison.py` | `calculate_recall_at_k` / `RetrievalModeResult` / `RetrievalComparisonEngine` only |
| `app/eval_service.py` | `_run_single_eval_case` / `build_evaluators` / metrics dict only |
| `app/compare_eval.py` | evaluators dict + report assembly only |
| `eval_data/retrieval_regression.json` | `expected_sources` shape (first/labeled cases) |
| `tests/test_eval_retrieval_comparison.py` | 1 recall@k test as the pattern to mirror |

## 4. Write-set (max 6)

`app/eval_retrieval_comparison.py` · `app/eval_service.py` · `app/compare_eval.py` ·
`app/config.py` · `eval_data/retrieval_regression.json` · `eval_data/eval_questions.json`
(+ targeted test files — tests do not count against runtime write-set).

---

## 5. Definition of Done

```powershell
# 1. Targeted eval suite green
.\.venv\Scripts\python.exe -m pytest tests/test_eval_retrieval_comparison.py tests/test_eval_service.py tests/test_compare_eval.py -q

# 2. precision@k is correct (½ for 1 relevant of 2 returned)
.\.venv\Scripts\python.exe -c "from app.eval_retrieval_comparison import calculate_precision_at_k; assert abs(calculate_precision_at_k({'a'}, ['a','b'], 2) - 0.5) < 1e-9"

# 3. read-set budget sane
.\.venv\Scripts\python.exe scripts\check_readset.py app/eval_retrieval_comparison.py app/eval_service.py
```

**Acceptance criteria**
- `context_precision@k` computed alongside `recall@k`; both deterministic on the labeled fixture.
- `answer_correctness` returns a score where `reference` exists, `None` otherwise (never a penalty for missing reference).
- `faithfulness` / `answer_relevancy` / `recall@k` / `MRR` outputs unchanged (regression check).
- With `ENABLE_RAGAS_METRICS=False` (default) the optional `ragas` import is never executed; absence of the
  package does not break any test.

## 6. Constraints & kill-switch

- Do **not** alter the semantics of `recall@k` / `MRR` / `hit_rate`.
- `answer_correctness` **complements**, never replaces, `faithfulness` / `answer_relevancy`.
- `ragas` must stay an optional backend (no hard dependency); flag default off.
- No LLM call inside precision/recall (pure set metrics).
- **Kill-switch:** precision/recall diverge on one fixture without explanation; RAGAS backend loads while the
  flag is off; eval cost doubles; CI eval-gate red on the labeled subset.

## 7. Sequencing

1. Native `precision@k` + `context_precision` (no deps) — lands value immediately.
2. `answer_correctness` + reference fixtures.
3. `ENABLE_RAGAS_METRICS` optional backend + import guard.
4. Hand off to `ragas-langfuse-dataset-v1` once `wave-langfuse-eval-loop` (I1) ships datasets.

---

**Promotion:** `proposed → ready` via [`generate_plan_next_prompt.md`](../team_workflow/generate_plan_next_prompt.md)
(ranking + preflight `check_readset.py` + tasklist regen). Truth View invariant: only one `ready`/`wip` at a time —
currently held by `golden-e2e-graduation-v1`, so this stays `proposed` until that slot frees.
