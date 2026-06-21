# ADR-022: SSR-AI eval harness and local artifact contract

**Status:** Accepted  
**Date:** 2026-05-18  
**Related:** ADR-020 (Smart Study Router), ADR-014 (LLM resilience), ADR-017 (course progression), ADR-021 / ADR-021a (retrieval routing boundaries)  
**Scope:** design and ownership contract for `app/ssr_ai/`. This ADR does not change runtime defaults, UI behavior, public endpoints, model weights, or retrieval modes.

---

## Context

`app/ssr_ai/` was introduced as shared infrastructure for Smart Study Router AI adjuncts:

- `eval_harness.py` owns canonical paths for SSR ML cases, rubric, evaluation contract, model/package artifacts, and train/eval scripts.
- `dataset.py` exposes stable helper functions for local dataset/model/script paths.
- `fallback.py` centralizes ML fallback reasons used by SSR hybrid logic.
- `telemetry.py` records bounded auxiliary SSR-AI events through the documented user-state persistence path.

ADR-020 defines the Smart Study Router decision boundary. It deliberately keeps rules as the source of truth and treats ML/LLM as optional advisors. The eval harness needs its own contract so future SSR-AI work does not quietly become a second router, a remote dependency, or an ad hoc persistence layer.

---

## Decision

`app/ssr_ai/` is accepted as a local-first support package for SSR AI evaluation, datasets, fallbacks, and telemetry.

The package may:

- expose deterministic path constants and helpers for local eval artifacts;
- provide bounded telemetry helpers through existing user-state persistence;
- define stable fallback reason strings for ML/LLM adjuncts;
- support offline tests, offline reports, and explicit scripts under `scripts/ml/`.

The package must not:

- decide `hint_kind`, `primary_nav`, route priority, or learner-facing copy by itself;
- create LLM, embedding, or provider clients directly;
- read environment variables directly;
- open ad hoc SQLite connections outside documented persistence helpers;
- introduce network-required evaluation by default;
- change runtime SSR defaults without an explicit execution package and regression tests.

SSR runtime decision ownership remains in the ADR-020 surface:

- deterministic recommendation: `app/smart_study_router.py` / `app/smart_study_recommendation.py`;
- optional ML adapter: `app/smart_study_ssr_ml.py`;
- evidence ledger: `app/smart_study_evidence.py`;
- local eval and artifact paths: `app/ssr_ai/eval_harness.py` and `app/ssr_ai/dataset.py`;
- auxiliary telemetry: `app/ssr_ai/telemetry.py`.

---

## Artifact Contract

Canonical SSR-AI artifacts stay local and versionable:

- test cases: `tests/eval/ssr_ml_reranking_test_cases.json`;
- rubric: `doc/eval/ssr_ml_reranking_rubric.md`;
- evaluation contract and package metadata: `archive/ml_eval/ssr_level1/`;
- train/test data: `data/ml/`;
- trained local model: `models/`;
- training and evaluation entrypoints: `scripts/ml/`.

Path construction belongs in `app/ssr_ai/eval_harness.py`; callers should import constants or helper functions instead of duplicating paths.

---

## Telemetry Contract

SSR-AI telemetry is auxiliary. It may help explain fallback, latency, or optional planner/cache outcomes, but it must not become the source of truth for learner state. Persistence must continue through documented user-state helpers, and summaries must stay bounded by an explicit `max_events` style parameter.

---

## Consequences

- Architecture reviews can treat `app/ssr_ai/` as a documented owner for SSR-AI eval infrastructure.
- Future packages may extend the harness only with local-first artifacts and targeted tests.
- Any learner-facing behavior change still needs a normal package with API/UI/test/doc updates.
- If a future task introduces remote evaluation or default ML behavior, it must amend this ADR or create a successor ADR.

