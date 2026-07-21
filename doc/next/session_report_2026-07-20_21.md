# Session Report — 2026-07-20/21 (honesty revision 2026-07-21)

> **Not audit-grade source of truth.** Counts re-synced to runtime after
> counter-audits. Prefer code + targeted pytest collect over this ledger.

## Волны

| # | Ход | Репозиторий | Статус (честный) |
|---|---|---|---|
| **26 P0-A** | Course Content Gate Packet | `hometutor` | ✅ **partial ship** — packet/sidecar/UI expander; live bundle numbers open |
| **26 P0-B** | Verified Learning Step Contract | `hometutor` | ✅ **core gate shipped**; full TLRR 6/6 **structural 0** until grounded; KPI = `tlrr_excluding_grounded` |
| **W10-PIXEL** | Pixel/DOM baseline + diff | `hometutor` | ⚠ **partial** — pipeline + DOM surface smoke; **unique per-surface baselines open** (fake 3-hash/27-file clones removed) |
| Size budget | large/long function ceilings | `hometutor` | ✅ green after structural split (not a silent budget bump for #26) |
| W10 honesty gate | unique-baseline policy | `hometutor` | ✅ rejects rebadged clones; `[W10-PIXEL-OPEN]` stays `[~]` until unique matrix |

## Write-set — #26 (runtime)

**New:** `app/course_content_gate.py`, `app/course_content_gate_helpers.py`,
`scripts/run_course_content_gate.py`, `scripts/compute_trusted_route_rate.py`,
`tests/test_course_content_gate.py`, `tests/test_quiz_content_contract.py`,
`tests/test_trusted_route_rate.py`.

**Changed:** `knowledge_graph_bundle.py`, `living_konspekt_reader.py`,
`prompts/_impl.py`, `quiz_scoped.py`, `quiz_micro.py`, `quiz_service.py`,
`fact_source_binding.py`, `scoped_quiz.py`, `user_state_db.py`,
`user_state_quiz.py`, `docs/user_guide.md`.

**Not #26:** `scripts/ssr_route_replay.py` is **#23 C1**, not P0-B.

## Write-set — W10 pixel (runtime)

**New:** `tests/e2e/pixel_baseline.py`, `tests/e2e/test_surface_smoke_live.py`,
`tests/e2e/_baselines/.gitkeep` (surface PNG matrix empty after honesty fix).

**Changed:** `docs/ui_ux_design_review_implementation_plan.md`,
`tests/e2e/README.md`, `tests/test_w10_release_gates.py`.

## Test counts (collect, 2026-07-21)

| Bundle | Collected | Notes |
|---|---:|---|
| `test_course_content_gate.py` | **55** | was miscounted as 46 |
| `test_quiz_content_contract.py` | **20** | was 18 |
| `test_trusted_route_rate.py` | **17** | was 4 |
| #26 subtotal | **92** | unit/integration |
| `test_surface_smoke_live.py` | **27** | e2e mark; **DOM smoke**, pixel opt-in |
| `test_w10_release_gates.py` | **27** | static (+ uniqueness when PNGs present) |
| `test_architecture_guards.py` | pass | size budget 33/156 |

Default full suite does **not** collect `tests/e2e` (opt-in).

## What is NOT done

| Item | Status |
|---|---|
| Full TLRR 6/6 (grounded_explanation) | not implemented — full KPI = 0 by design |
| Live reindex + gate on 3–5 reference topics | open |
| Post-ship replay E2 pain-anchor | open |
| Unique live pixel baselines 9×3 | **open** (close condition for W10-PIXEL) |
| Focus-vs-sticky other surfaces | open |
| Full-app keyboard-only / SR / empty-offline visuals | open |
| #27 P0 local model trust contour | studio, not started |
| #28 «свой материал» | analysis not done |

## Studio artifacts

- `doc/next/26_course_content_gate_implementation_report.md`
- `doc/next/course_content_gate_compiler_plan.md` — Implementation status synced
- `doc/presentations/evolutionary_analyses/README.md` — #26 row (prefer “shipped-unvalidated”)
