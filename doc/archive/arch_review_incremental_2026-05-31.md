# Incremental Architecture Review — 2026-05-31

Archived pointer for `doc/archive/arch_review_baseline.yaml`.

The original review and freshness audit were executed outside the repository:

- `D:\Downloads\plans\goal-periodic-incremental-smooth-pond.md`
- `D:\Downloads\plan_audit.md`

Warnings fixed on 2026-06-01:

- `AR-2026-05-31-001` — recent modules documented in `doc/architecture.md`; guard added.
- `AR-2026-05-31-002` — duplicate `_discover_staging_chunks_collection` removed; `F811` guard added.
- `AR-2026-05-31-003` — `quiz_scoped.py` broad exceptions annotated with `BLE001` rationale; no-new-debt guard added.

Warning fixed after follow-up:

- `AR-2026-05-31-008` — SSR backend-to-UI imports removed by moving exact cache/feedback helpers to `app/ssr_explanation_cache.py` and redirecting SSR pregeneration to backend-safe modules. The remaining `app/quiz_micro_receipt.py` dependency now uses `app/adaptive_plan_progress.py`.

Known residual guard failure:

- `scripts/arch_regression_guards.py` still fails on carried line-count debt: `app/query_service.py` has 845 lines while the guard threshold is 800. This was not in the current write-set.
