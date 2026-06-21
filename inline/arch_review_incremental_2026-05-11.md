# Incremental Architecture Review — 2026-05-11

- Previous review SHA: `defad09ca01b0c22afb107bf0e23767958379bf1` (2026-05-08)
- HEAD at this review: `4548da07192b694d69e53e31778980a30ea02fe8`
- Commits in window: 70 (most touch docs/archive; app/ scope below)
- App/test files changed: 16 app modules + 16 tests + 0 routers + 0 requirements.txt

## Executive Summary

The 3-day window introduced a new **Smart Study Router** subsystem
(`smart_study_router.py` 1094L, four `ssr_*` modules, `adaptive_plan_step_text.py`,
plus heavy growth in `ui/adaptive_plan_card.py` to 1298L) without an ADR or
Module Reference entry. The subsystem ships with `numpy` as a direct
dependency that is **not declared in `requirements.txt`** (transitively
satisfied today, risky in headless deploys). The persisting BLE001 / inline
`import logging` pattern bled into the new UI code (10+ unannotated
`except Exception` blocks in `adaptive_plan_card.py` and central
`llm_resilience.py`). On the positive side, three persisting Phase-2 findings
were **resolved** by the wave: `knowledge_service.py` collapsed to a 44-line
facade, `topics_tab.py`/`query_tab.py` were factored to sub-100L wrappers, and
`docling` is now exact-pinned with optional annotation.

Top 3 actions: (1) declare `numpy` in `requirements.txt`; (2) draft ADR-020
for SSR + add subsystem entries to `doc/architecture.md`; (3) split
`smart_study_router.py` (1094L) and add BLE001 annotations to
`llm_resilience.py` + `ui/adaptive_plan_card.py`.

## Findings Table

| # | ID | Phase | Severity | Status | Finding | File(s) | Evidence (cmd → expected) | Suggested Action |
|---|----|-------|----------|--------|---------|---------|---------------------------|------------------|
| 1 | AR-2026-05-11-001 | 1 | warning | new | `logging_config._env_truthy` reads `HOME_RAG_NO_LOG_ROTATE` / `HOME_RAG_LOG_ROTATE` / `HOME_RAG_E2E_NO_LOG_ROTATE` via `os.environ.get` instead of `Settings` (pre-existing pattern expanded in 569b603). | `app/logging_config.py:20,32,35` | `rg "os\.environ" app/logging_config.py` → 1 match at L20 (and 2 string refs in docstring at L28-33) | Add `home_rag_no_log_rotate`/`home_rag_log_rotate`/`home_rag_e2e_no_log_rotate` fields to `Settings` and read via `get_settings()`. Acceptable to keep the helper but route through `Settings`. |
| 2 | AR-2026-05-11-002 | 2 | warning | new | New module `app/smart_study_router.py` lands at **1094L** with 6 functions >80L (top: 167L `apply_smart_study_steering_preference`). | `app/smart_study_router.py` | `python -c "import ast; t=ast.parse(open('app/smart_study_router.py','rb').read()); print(len(open('app/smart_study_router.py').readlines()), sum(1 for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and (n.end_lineno-n.lineno+1)>80))"` → `1094 6` | Split into `smart_study_recommendation.py` (rule engine), `smart_study_ssr_ml.py` (ML hybrid), `smart_study_evidence.py` (ledger builders). |
| 3 | AR-2026-05-11-003 | 2 | warning | new | `app/ui/adaptive_plan_card.py` grew to 1298L with 5 fns >80L (top: 203L `render_adaptive_plan_hub`); plan rendering + SSR card + LLM enrichment all in one UI module. | `app/ui/adaptive_plan_card.py` | `python -c "import ast; t=ast.parse(open('app/ui/adaptive_plan_card.py','rb').read()); print(len(open('app/ui/adaptive_plan_card.py').readlines()), sum(1 for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and (n.end_lineno-n.lineno+1)>80))"` → `1298 5` | Extract `adaptive_plan_llm_enrichment.py` (the `_generate_llm_explanation` 137L block) and `adaptive_plan_hub_layout.py` (the 203L hub renderer). |
| 4 | AR-2026-05-11-004 | 2 | info | new | `app/ui/home_hub.py` grew past the 600L threshold to 647L. | `app/ui/home_hub.py` | `wc -l app/ui/home_hub.py` → `647` | Watch — split if it crosses ~800L. |
| 5 | AR-2026-05-11-005 | 3 | warning | new | Smart Study Router / SSR subsystem (`smart_study_router.py`, `ssr_llm_profile_summary.py`, `ssr_llm_profiling.py`, `ssr_ml_monitoring.py`, `ssr_ml_reranking.py`, `adaptive_plan_step_text.py`, `ui/adaptive_plan_card.py`) has no ADR explaining rule-vs-ML hybrid, weight artifact, or LLM profile contract. | `doc/adr.md` | `rg "smart_study\|ssr_\|adaptive_plan_step" doc/adr.md` → no matches | Draft **ADR-020: Smart Study Router & SSR ML hybrid contract** covering: hint/primary_nav enums, rule→ML fallback semantics, weight file lifecycle, JSONL profile log contract. |
| 6 | AR-2026-05-11-006 | 3 | warning | new | 8 new/grown app modules absent from `doc/architecture.md` Module Reference. | `doc/architecture.md` | `for m in smart_study_router ssr_llm_profile_summary ssr_llm_profiling ssr_ml_monitoring ssr_ml_reranking adaptive_plan_step_text adaptive_plan_card course_cockpit; do rg -c "$m" doc/architecture.md; done` → `0 0 0 0 0 0 0 0` | Add the 8 modules under appropriate sections (`Services` for backend SSR family, `UI` for `adaptive_plan_card.py` / `course_cockpit.py`). |
| 7 | AR-2026-05-11-007 | 4 | warning | new | `app/llm_resilience.py:35,76` — both `except Exception` in the central LLM resilience wrapper lack `# noqa: BLE001` annotation, despite project convention. | `app/llm_resilience.py:35,76` | `rg -n "except Exception" app/llm_resilience.py` → 2 matches, neither carries `noqa: BLE001` | Add `# noqa: BLE001 — provider failures are caught here on purpose, re-raised after record_error` to both lines. |
| 8 | AR-2026-05-11-008 | 4 | warning | new | `app/ui/adaptive_plan_card.py` has **6** `except Exception` blocks without `noqa: BLE001` (917, 1028, 1032, 1131, 1184, 1236). | `app/ui/adaptive_plan_card.py:917,1028,1032,1131,1184,1236` | `rg -n "except Exception" app/ui/adaptive_plan_card.py \| rg -v "noqa.*BLE001"` → 6 matches | Annotate or narrow exception classes (Streamlit error-render fallbacks). |
| 9 | AR-2026-05-11-009 | 4 | warning | new | `app/ui/home_hub.py:292,315` and `app/ui/course_cockpit.py:270` swallow request errors via bare `except Exception` without `noqa: BLE001`. | `app/ui/home_hub.py:292,315`, `app/ui/course_cockpit.py:270` | `rg -n "except Exception" app/ui/home_hub.py app/ui/course_cockpit.py \| rg -v "noqa.*BLE001"` → 3 matches | Annotate; narrow to `requests.RequestException` / `HTTPError` where applicable. |
| 10 | AR-2026-05-11-010 | 4 | info | new | `app/otel_tracing.py:65` — `except Exception` without `noqa: BLE001`. | `app/otel_tracing.py:65` | `rg -n "except Exception" app/otel_tracing.py` → `65:    except Exception as e:` (no noqa); L116 is annotated | Annotate; OTel shutdown swallow is intentional. |
| 11 | AR-2026-05-11-011 | 5 | critical | new | `numpy` imported in `app/ssr_ml_reranking.py:13` is **not declared** in `requirements.txt`. Currently satisfied transitively via FlagEmbedding/pandas — a headless deployment omitting either breaks SSR ML reranking. | `requirements.txt`, `app/ssr_ml_reranking.py:13` | `rg -i "numpy" requirements.txt` → no match;  `rg "^import numpy" app/ssr_ml_reranking.py` → `13:import numpy as np` | Add `numpy==<pinned>` to `requirements.txt`. |
| 12 | AR-2026-04-21-005 | 2 | info | persists | 13→10 modules >600L (improving). Top: `ui/resume_cards.py` 1402, `ui/adaptive_plan_card.py` 1298, `prompts/_impl.py` 1236, `smart_study_router.py` 1094. | `app/**.py` | `find app -name "*.py" -exec wc -l {} \; \| sort -rn \| awk '$1>600' \| wc -l` → `10` | Continue split focus on top-4 (see AR-2026-05-11-002, -003). |
| 13 | AR-2026-04-21-006 | 2 | — | resolved (2026-05-11) | `topics_tab.py`/`query_tab.py` collapsed to thin facades (88L and 53L). | `app/ui/topics_tab.py`, `app/ui/query_tab.py` | `wc -l app/ui/topics_tab.py app/ui/query_tab.py` → `88 / 53` | — |
| 14 | AR-2026-04-29-003 | 2 | — | resolved (2026-05-11) | `knowledge_service.py` collapsed to a 44L facade re-exporting from `knowledge_catalog`/`knowledge_graph`/`knowledge_insights`/`knowledge_planning`/`knowledge_synthesis`. | `app/knowledge_service.py` | `wc -l app/knowledge_service.py` → `44` | — |
| 15 | AR-2026-04-29-013 | 5 | — | resolved (2026-05-11) | `docling` now exact-pinned `==2.31.0` with explicit `# optional` annotation. | `requirements.txt:31` | `rg "docling" requirements.txt` → `docling==2.31.0  # optional ...` | — |
| 16 | AR-2026-04-29-014 | 5 | info | persists | Telegram/aiogram tests remain at 2 (structural only). | `tests/test_telegram_parsing.py` | `rg -c "def test_.*telegram\|def test_.*aiogram" tests/` → `2 (in 1 file)` | Add handler integration tests when aiogram surface grows. |
| 17 | AR-2026-05-02-005 | 4 | warning | persists | Inline `import logging` inside `except` blocks: now **110** repo-wide unannotated occurrences (was 106 at 2026-05-08); 4 new in `ui/home_hub.py` (94, 185, 538, 549). | `app/ui/home_hub.py:94,185,538,549`, plus 100+ pre-existing | `rg -nE "^\s+import logging" app/ \| rg -v "noqa" \| wc -l` → `110` | Decide: either codify pattern in conventions (allow inline diagnostic logger) or remove and use module-level logger universally. |

> No critical/warning finding was downgraded for missing evidence — every row above carries a runnable command.

## Metrics Snapshot

- Total app/ modules (incl. `routers/`, `ui/`): 175 (`find app -name "*.py" -not -path "*/__pycache__/*" | wc -l` → 175)
- Total test files: ~360 (out of scope to count fully)
- Modules >600 lines (10): `ui/resume_cards.py` 1402, `ui/adaptive_plan_card.py` 1298, `prompts/_impl.py` 1236, `smart_study_router.py` 1094, `knowledge_graph.py` 1067, `eval_service.py` 915, `query_service.py` 720, `tutor_orchestrator.py` 651, `ui/home_hub.py` 647, `ui/dashboards.py` 644
- Functions >80 lines (in changed scope, sample): `apply_smart_study_steering_preference` 167L, `render_adaptive_plan_hub` 203L, `_render_quiz_hero_card` 162L, `render_homework_playbook_panel` 183L, `render_adaptive_daily_plan` 157L
- Convention violations found: 4 (1 warning Phase 1, 3 warning Phase 4 BLE001) + 1 info (Phase 4 otel_tracing)
- ADR drift instances: 2 (subsystem absent from ADR registry; 8 modules absent from architecture.md)
- Doc-code drift instances: 1 (8-module gap in `doc/architecture.md`)
- Dead code candidates: 0 inside incremental scope (SSR family wired into `ui/adaptive_plan_card.py` and `scripts/summarize_ssr_llm_profiles.py`)
- Duplication clusters: 0 detected in scope (separate `ssr_*` modules each have a single responsibility)
- Persisting resolutions: 3 (knowledge_service split, topics_tab/query_tab split, docling pin)

## Recommended Actions (prioritized)

1. **Declare `numpy` in `requirements.txt`** (AR-2026-05-11-011). Why now: silent transitive dep risk; headless deployments shipping without FlagEmbedding/pandas will hit ImportError on SSR ML path. Scope: **S** (1 file).
2. **Draft ADR-020 for Smart Study Router & SSR ML** (AR-2026-05-11-005). Why: new subsystem of ~3400L without architectural record; precedent for AR-2026-04-21-007/-008 / AR-2026-04-29-007 says ADR is mandatory. Scope: **S** (`doc/adr.md` only).
3. **Update `doc/architecture.md` Module Reference** with 8 missing modules (AR-2026-05-11-006). Why: docs source-of-truth drift; pairs with action 2. Scope: **S** (1 file, ~20 lines).
4. **Annotate `except Exception` in `llm_resilience.py`** (AR-2026-05-11-007). Why: central LLM wrapper used by 11+ modules; convention drift in critical path. Scope: **S** (1 file, 2 lines).
5. **Annotate BLE001 in 3 changed UI files** (AR-2026-05-11-008, -009, -010). Why: closes Phase-4 backlog before it accumulates further. Scope: **S** (3 files, ~10 lines total).
6. **Split `smart_study_router.py`** (AR-2026-05-11-002). Why: brand-new module above 600L threshold from day one with 6 fns >80L; cheap to split now before more code lands. Scope: **M** (3–4 files).
7. **Split `ui/adaptive_plan_card.py`** (AR-2026-05-11-003). Why: 1298L UI module mixes plan render + LLM call + SSR card; clean split target. Scope: **M** (extract 2 helpers).
8. **Move `HOME_RAG_*` log toggles into `Settings`** (AR-2026-05-11-001). Why: keeps single-source-of-truth for env vars; trivial. Scope: **S** (2 files).
9. **Decide policy for inline `import logging` pattern** (AR-2026-05-02-005 persists). Why: 110 occurrences indicates intentional pattern; either codify in conventions or write a one-time refactor. Scope: **L** (110 lines repo-wide), OR **S** (codify and move on).
10. **Plan handler-level Telegram tests** (AR-2026-04-29-014 persists, low priority). Scope: **M**, deferred until aiogram surface grows.

## Baseline Update

Apply this patch to `doc/archive/arch_review_baseline.yaml`:

```yaml
# 1. Update last_review block
last_review:
  sha: 4548da07192b694d69e53e31778980a30ea02fe8
  date: "2026-05-11"
  backlog_wave_id: wave-arch-review-remediation-2026-05-11
  report_files:
    - inline/arch_review_incremental_2026-05-11.md
  phases_completed: [1, 2, 3, 4, 5]
  phases_pending: []
  previous_sha: defad09ca01b0c22afb107bf0e23767958379bf1
  previous_report: inline/arch_review_incremental_2026-05-08.md

# 2. For findings already in baseline — update last_seen / status / resolved_date:
#    AR-2026-04-21-005  → last_seen: "2026-05-11"  (10 modules >600L, was 13)
#    AR-2026-04-21-006  → status: resolved,  resolved_date: "2026-05-11"
#    AR-2026-04-29-003  → status: resolved,  resolved_date: "2026-05-11"
#    AR-2026-04-29-013  → status: resolved,  resolved_date: "2026-05-11"
#    AR-2026-04-29-014  → last_seen: "2026-05-11"  (still 2 structural tests)
#    AR-2026-05-02-005  → last_seen: "2026-05-11"  (110 instances repo-wide; +4 new in home_hub.py)

# 3. Append new findings:

  - id: AR-2026-05-11-001
    phase: 1
    severity: warning
    title: "logging_config._env_truthy reads HOME_RAG_*_LOG_ROTATE env vars via os.environ.get instead of Settings"
    files: ["app/logging_config.py:20", "app/logging_config.py:32", "app/logging_config.py:35"]
    first_seen: "2026-05-11"
    last_seen: "2026-05-11"
    status: new
    owner: null
    target_epoch: null
    evidence_cmd: |
      Select-String -Path app/logging_config.py -Pattern "os\.environ"
    expected_evidence: |
      L20: return os.environ.get(key, "").strip().lower() in _ENV_TRUTHY
    regression_guard: |
      Add to scripts/arch_regression_guards.py:
        rg "os\.environ" app/logging_config.py && echo FAIL || echo OK
      Add new rule to doc/conventions_architecture.md § Контракт доступа к конфигурации:
        "Even infrastructure toggles (log rotation, OTel) must be declared in Settings."

  - id: AR-2026-05-11-002
    phase: 2
    severity: warning
    title: "New module smart_study_router.py is 1094L with 6 functions >80L (top 167L apply_smart_study_steering_preference)"
    files: ["app/smart_study_router.py"]
    first_seen: "2026-05-11"
    last_seen: "2026-05-11"
    status: new
    owner: null
    target_epoch: null
    evidence_cmd: |
      .\.venv\Scripts\python.exe -c "import ast; t=ast.parse(open('app/smart_study_router.py','rb').read()); print(len(open('app/smart_study_router.py').readlines()), sum(1 for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and (n.end_lineno-n.lineno+1)>80))"
    expected_evidence: |
      1094 6
    regression_guard: |
      Add to scripts/arch_regression_guards.py:
        lines=len(open('app/smart_study_router.py').readlines()); assert lines<=1200, f"FAIL: smart_study_router.py {lines}L > 1200L limit"

  - id: AR-2026-05-11-003
    phase: 2
    severity: warning
    title: "ui/adaptive_plan_card.py grew to 1298L with 5 functions >80L (top 203L render_adaptive_plan_hub)"
    files: ["app/ui/adaptive_plan_card.py"]
    first_seen: "2026-05-11"
    last_seen: "2026-05-11"
    status: new
    owner: null
    target_epoch: null
    evidence_cmd: |
      .\.venv\Scripts\python.exe -c "import ast; t=ast.parse(open('app/ui/adaptive_plan_card.py','rb').read()); print(len(open('app/ui/adaptive_plan_card.py').readlines()), sum(1 for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and (n.end_lineno-n.lineno+1)>80))"
    expected_evidence: |
      1298 5
    regression_guard: |
      Invariant test tests/test_adaptive_plan_card_invariants.py + scripts/arch_regression_guards.py:
        assert max fn length <= 220L; total <= 1400L

  - id: AR-2026-05-11-004
    phase: 2
    severity: info
    title: "ui/home_hub.py crossed 600L threshold (now 647L)"
    files: ["app/ui/home_hub.py"]
    first_seen: "2026-05-11"
    last_seen: "2026-05-11"
    status: new
    owner: null
    target_epoch: null
    evidence_cmd: |
      .\.venv\Scripts\python.exe -c "print(len(open('app/ui/home_hub.py').readlines()))"
    expected_evidence: |
      647
    regression_guard: null

  - id: AR-2026-05-11-005
    phase: 3
    severity: warning
    title: "Smart Study Router / SSR subsystem (7 modules, ~3400L) has no ADR"
    files:
      - "app/smart_study_router.py"
      - "app/ssr_llm_profile_summary.py"
      - "app/ssr_llm_profiling.py"
      - "app/ssr_ml_monitoring.py"
      - "app/ssr_ml_reranking.py"
      - "app/adaptive_plan_step_text.py"
      - "app/ui/adaptive_plan_card.py"
    first_seen: "2026-05-11"
    last_seen: "2026-05-11"
    status: new
    owner: null
    target_epoch: null
    evidence_cmd: |
      Select-String -Path doc/adr.md -Pattern "smart_study|ssr_|adaptive_plan_step" | Measure-Object | Select-Object -ExpandProperty Count
    expected_evidence: |
      0
    regression_guard: |
      Draft ADR-020: Smart Study Router & SSR ML hybrid.
      Add to scripts/arch_regression_guards.py:
        grep -q "Smart Study Router" doc/adr.md && echo OK || echo "FAIL: ADR-020 missing"

  - id: AR-2026-05-11-006
    phase: 3
    severity: warning
    title: "8 new app modules absent from doc/architecture.md Module Reference"
    files: ["doc/architecture.md"]
    first_seen: "2026-05-11"
    last_seen: "2026-05-11"
    status: new
    owner: null
    target_epoch: null
    evidence_cmd: |
      foreach ($m in @('smart_study_router','ssr_llm_profile_summary','ssr_llm_profiling','ssr_ml_monitoring','ssr_ml_reranking','adaptive_plan_step_text','adaptive_plan_card','course_cockpit')) { "$m $((Select-String -Path doc/architecture.md -Pattern $m | Measure-Object).Count)" }
    expected_evidence: |
      smart_study_router 0
      ssr_llm_profile_summary 0
      ssr_llm_profiling 0
      ssr_ml_monitoring 0
      ssr_ml_reranking 0
      adaptive_plan_step_text 0
      adaptive_plan_card 0
      course_cockpit 0
    regression_guard: |
      Add to scripts/arch_regression_guards.py module-listing check.

  - id: AR-2026-05-11-007
    phase: 4
    severity: warning
    title: "llm_resilience.py:35,76 — both except Exception blocks in central LLM wrapper lack noqa: BLE001"
    files: ["app/llm_resilience.py:35", "app/llm_resilience.py:76"]
    first_seen: "2026-05-11"
    last_seen: "2026-05-11"
    status: new
    owner: null
    target_epoch: null
    evidence_cmd: |
      Select-String -Path app/llm_resilience.py -Pattern "except Exception" | Where-Object { $_.Line -notmatch "noqa.*BLE001" } | Select-Object LineNumber
    expected_evidence: |
      35, 76
    regression_guard: |
      Add to scripts/arch_regression_guards.py:
        rg "except Exception" app/llm_resilience.py | rg -v "noqa.*BLE001" && echo FAIL || echo OK

  - id: AR-2026-05-11-008
    phase: 4
    severity: warning
    title: "ui/adaptive_plan_card.py has 6 except Exception without noqa: BLE001 (917, 1028, 1032, 1131, 1184, 1236)"
    files:
      - "app/ui/adaptive_plan_card.py:917"
      - "app/ui/adaptive_plan_card.py:1028"
      - "app/ui/adaptive_plan_card.py:1032"
      - "app/ui/adaptive_plan_card.py:1131"
      - "app/ui/adaptive_plan_card.py:1184"
      - "app/ui/adaptive_plan_card.py:1236"
    first_seen: "2026-05-11"
    last_seen: "2026-05-11"
    status: new
    owner: null
    target_epoch: null
    evidence_cmd: |
      Select-String -Path app/ui/adaptive_plan_card.py -Pattern "except Exception" | Where-Object { $_.Line -notmatch "noqa.*BLE001" } | Select-Object LineNumber
    expected_evidence: |
      917, 1028, 1032, 1131, 1184, 1236
    regression_guard: null

  - id: AR-2026-05-11-009
    phase: 4
    severity: warning
    title: "home_hub.py:292,315 and course_cockpit.py:270 — except Exception without noqa: BLE001"
    files:
      - "app/ui/home_hub.py:292"
      - "app/ui/home_hub.py:315"
      - "app/ui/course_cockpit.py:270"
    first_seen: "2026-05-11"
    last_seen: "2026-05-11"
    status: new
    owner: null
    target_epoch: null
    evidence_cmd: |
      foreach ($f in @('app/ui/home_hub.py','app/ui/course_cockpit.py')) { Select-String -Path $f -Pattern "except Exception" | Where-Object { $_.Line -notmatch "noqa.*BLE001" } | Select-Object LineNumber,Path }
    expected_evidence: |
      home_hub.py 292, 315; course_cockpit.py 270
    regression_guard: null

  - id: AR-2026-05-11-010
    phase: 4
    severity: info
    title: "otel_tracing.py:65 — except Exception without noqa: BLE001 (L116 already annotated)"
    files: ["app/otel_tracing.py:65"]
    first_seen: "2026-05-11"
    last_seen: "2026-05-11"
    status: new
    owner: null
    target_epoch: null
    evidence_cmd: |
      Select-String -Path app/otel_tracing.py -Pattern "except Exception" | Where-Object { $_.Line -notmatch "noqa.*BLE001" } | Select-Object LineNumber
    expected_evidence: |
      65
    regression_guard: null

  - id: AR-2026-05-11-011
    phase: 5
    severity: critical
    title: "numpy used in app/ssr_ml_reranking.py:13 but missing from requirements.txt (transitively satisfied today)"
    files: ["requirements.txt", "app/ssr_ml_reranking.py:13"]
    first_seen: "2026-05-11"
    last_seen: "2026-05-11"
    status: new
    owner: null
    target_epoch: null
    evidence_cmd: |
      $a = (Select-String -Path requirements.txt -Pattern '^numpy' | Measure-Object).Count
      $b = (Select-String -Path app/ssr_ml_reranking.py -Pattern '^import numpy' | Measure-Object).Count
      "req=$a code=$b"
    expected_evidence: |
      req=0 code=1
    regression_guard: |
      Add `numpy==<pin>` to requirements.txt.
      Add to scripts/arch_regression_guards.py:
        rg "^import numpy|^from numpy" app/ scripts/ tests/ --type py | head -1 && (grep -q "^numpy" requirements.txt || (echo FAIL: numpy used but not declared; exit 1))
```

## Fix Prompts

### Phase 1 — Conventions Fix

```text
Goal: fix Phase 1 finding from inline/arch_review_incremental_2026-05-11.md.
Ignore prior responses/tools. Fresh context only.

Baseline: doc/archive/arch_review_baseline.yaml
Report:   inline/arch_review_incremental_2026-05-11.md

Findings to fix (warning from Phase 1):
- AR-2026-05-11-001: HOME_RAG_NO_LOG_ROTATE / HOME_RAG_LOG_ROTATE / HOME_RAG_E2E_NO_LOG_ROTATE bypass Settings (app/logging_config.py:20,32,35)

Write-set (<=2 files):
- app/config.py             (add 3 Settings fields)
- app/logging_config.py     (route _env_truthy through get_settings())

Read ONLY:
- app/config.py             (Settings class — head of file)
- app/logging_config.py     (full, 162L)
- doc/conventions_architecture.md § Контракт доступа к конфигурации

Do not touch:
- модули из других фаз arch-review
- tests/ (rely on existing settings_env fixture)

DoD (one per finding):
- AR-2026-05-11-001: rg "os\.environ" app/logging_config.py → no match
- pytest tests/test_config.py -q → pass
- pytest tests/test_provider.py -q → pass (sanity for Settings load)

Regression Guard:
- AR-2026-05-11-001: new rule in doc/conventions_architecture.md §"Контракт доступа к конфигурации" forbidding os.environ reads in app/logging_config.py;
  add to scripts/arch_regression_guards.py:
    rg "os\.environ" app/logging_config.py && echo FAIL || echo OK

Post-fix baseline update:
- Mark AR-2026-05-11-001 as status=resolved with resolved_date=2026-05-11 (or actual date)
  in doc/archive/arch_review_baseline.yaml. Do NOT remove entries — keep history.

Token budget:
- Target <=12k input tokens.
- Hard stop >20k input tokens.
- If estimated input is 12k-20k, compress before sending.
- No retry with unchanged payload.
Output: changed files + tests run + guard(s) added + unresolved risk.
```

### Phase 2 — Structural Health Fix

```text
Goal: fix Phase 2 findings from inline/arch_review_incremental_2026-05-11.md.
Ignore prior responses/tools. Fresh context only.

Baseline: doc/archive/arch_review_baseline.yaml
Report:   inline/arch_review_incremental_2026-05-11.md

Findings to fix (warning from Phase 2):
- AR-2026-05-11-002: smart_study_router.py 1094L, 6 fns >80L
- AR-2026-05-11-003: ui/adaptive_plan_card.py 1298L, 5 fns >80L

Write-set (<=5 files):
- app/smart_study_router.py                    (slim entry-point)
- app/smart_study_recommendation.py            (NEW: rules + recommendation builder)
- app/smart_study_ssr_ml.py                    (NEW: ML hybrid + reranking glue)
- app/ui/adaptive_plan_card.py                 (slim renderer)
- app/ui/adaptive_plan_llm_enrichment.py       (NEW: extract _generate_llm_explanation 137L)

Read ONLY:
- app/smart_study_router.py — signatures only (`grep "^def\|^class " app/smart_study_router.py`)
- app/ui/adaptive_plan_card.py — signatures only
- app/adaptive_plan_step_text.py — full (83L)
- app/ssr_ml_reranking.py — full (96L) for `predict_hint_probability_map_or_empty` integration

Do not touch:
- модули из других фаз arch-review
- app/ui/resume_cards.py / app/prompts/_impl.py / app/knowledge_graph.py (out of scope)
- routers/*

DoD (one per finding):
- AR-2026-05-11-002: python -c "import ast; t=ast.parse(open('app/smart_study_router.py','rb').read()); print(len(open('app/smart_study_router.py').readlines()), max((n.end_lineno-n.lineno+1) for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))))" → lines <= 600 AND max fn <= 100
- AR-2026-05-11-003: same probe on app/ui/adaptive_plan_card.py → lines <= 1000 AND max fn <= 120
- pytest tests/test_smart_study_router.py tests/test_smart_study_router_comprehensive.py -q → pass
- pytest tests/test_course_cockpit.py -q → pass (adjacent UI module)
- streamlit smoke: `python -c "import app.ui.adaptive_plan_card; import app.smart_study_router"` → no ImportError

Regression Guard:
- AR-2026-05-11-002: add to scripts/arch_regression_guards.py:
    .\.venv\Scripts\python.exe -c "lines=len(open('app/smart_study_router.py').readlines()); assert lines<=700, f'FAIL: smart_study_router.py {lines}L > 700L'"
- AR-2026-05-11-003: tests/test_adaptive_plan_card_invariants.py with module-line-count and max-fn-length asserts.

Post-fix baseline update:
- Mark AR-2026-05-11-002 / -003 as status=resolved with resolved_date=<today>.
  Do NOT remove entries — keep history.

Token budget:
- Target <=12k input tokens.
- Hard stop >20k input tokens.
- If estimated input is 12k-20k, compress before sending.
- No retry with unchanged payload.
Output: changed files + tests run + guard(s) added + unresolved risk.

Optional follow-up (info-level, not in DoD):
- AR-2026-05-11-004: watch ui/home_hub.py size; split if >800L.
```

### Phase 3 — ADR + Doc-Code Drift Fix

```text
Goal: fix Phase 3 findings from inline/arch_review_incremental_2026-05-11.md.
Ignore prior responses/tools. Fresh context only.

Baseline: doc/archive/arch_review_baseline.yaml
Report:   inline/arch_review_incremental_2026-05-11.md

Findings to fix (warning from Phase 3):
- AR-2026-05-11-005: Smart Study Router / SSR subsystem has no ADR
- AR-2026-05-11-006: 8 app modules absent from doc/architecture.md Module Reference

Write-set (<=2 files):
- doc/adr.md                  (append ADR-020 + add table row)
- doc/architecture.md         (add 8 module reference entries)

Read ONLY:
- doc/adr.md — status table (first ~50 lines) + ADR-014/-015 as templates
- doc/architecture.md — module reference section (L630-720)
- app/smart_study_router.py — signatures only
- app/ssr_*.py — signatures only

Do not touch:
- code modules
- tests
- модули из других фаз arch-review

DoD (one per finding):
- AR-2026-05-11-005: rg "Smart Study Router|ADR-020" doc/adr.md → ≥2 matches; ADR registry row count == 20
- AR-2026-05-11-006: for each of (smart_study_router, ssr_llm_profile_summary, ssr_llm_profiling, ssr_ml_monitoring, ssr_ml_reranking, adaptive_plan_step_text, adaptive_plan_card, course_cockpit) `rg -c "$m" doc/architecture.md` → ≥1

Regression Guard:
- AR-2026-05-11-005: add to scripts/arch_regression_guards.py:
    grep -q "ADR-020" doc/adr.md && echo OK || echo "FAIL: ADR-020 missing"
- AR-2026-05-11-006: add module-presence loop check in arch_regression_guards.py.

Post-fix baseline update:
- Mark AR-2026-05-11-005 / -006 as status=resolved with resolved_date=<today>.

Token budget:
- Target <=12k input tokens.
- Hard stop >20k input tokens.
- If estimated input is 12k-20k, compress before sending.
- No retry with unchanged payload.
Output: changed files + guard(s) added + unresolved risk.
```

### Phase 4 — Implementation Quality Fix

```text
Goal: fix Phase 4 findings from inline/arch_review_incremental_2026-05-11.md.
Ignore prior responses/tools. Fresh context only.

Baseline: doc/archive/arch_review_baseline.yaml
Report:   inline/arch_review_incremental_2026-05-11.md

Findings to fix (warning from Phase 4):
- AR-2026-05-11-007: llm_resilience.py:35,76 — except Exception without noqa: BLE001
- AR-2026-05-11-008: ui/adaptive_plan_card.py 6 except Exception (917, 1028, 1032, 1131, 1184, 1236) without noqa: BLE001
- AR-2026-05-11-009: ui/home_hub.py:292,315 + ui/course_cockpit.py:270 — except Exception without noqa: BLE001

Write-set (<=4 files):
- app/llm_resilience.py
- app/ui/adaptive_plan_card.py
- app/ui/home_hub.py
- app/ui/course_cockpit.py

Read ONLY:
- doc/conventions_reference.md § Обработка ошибок (for noqa rationale)
- the 4 files in write-set — only the lines around each finding (no full reads of >800L files)

Do not touch:
- модули из других фаз arch-review
- otel_tracing.py:65 (info-level — optional follow-up)
- the 110 repo-wide inline `import logging` instances (AR-2026-05-02-005, separate decision)

DoD (one per finding):
- AR-2026-05-11-007: rg "except Exception" app/llm_resilience.py | rg -v "noqa.*BLE001" → 0 lines
- AR-2026-05-11-008: rg "except Exception" app/ui/adaptive_plan_card.py | rg -v "noqa.*BLE001" → 0 lines
- AR-2026-05-11-009: rg "except Exception" app/ui/home_hub.py app/ui/course_cockpit.py | rg -v "noqa.*BLE001" → 0 lines
- pytest tests/test_llm_resilience.py -q → pass
- pytest tests/test_course_cockpit.py -q → pass

Regression Guard:
- AR-2026-05-11-007: add to scripts/arch_regression_guards.py:
    rg "except Exception" app/llm_resilience.py | rg -v "noqa.*BLE001" && echo FAIL || echo OK
- AR-2026-05-11-008/-009: extend existing repo-wide BLE001 guard (already present per AR-2026-05-02-005 regression_guard) to assert 0 for these specific files.

Post-fix baseline update:
- Mark AR-2026-05-11-007 / -008 / -009 as status=resolved with resolved_date=<today>.

Token budget:
- Target <=12k input tokens.
- Hard stop >20k input tokens.
- If estimated input is 12k-20k, compress before sending.
- No retry with unchanged payload.
Output: changed files + tests run + guard(s) added + unresolved risk.

Optional follow-up (info-level, not in DoD):
- AR-2026-05-11-010: app/otel_tracing.py:65 — annotate or narrow exception.
- AR-2026-05-02-005: decide repo-wide policy for inline `import logging`.
```

### Phase 5 — Dependency Fix

```text
Goal: fix Phase 5 finding from inline/arch_review_incremental_2026-05-11.md.
Ignore prior responses/tools. Fresh context only.

Baseline: doc/archive/arch_review_baseline.yaml
Report:   inline/arch_review_incremental_2026-05-11.md

Findings to fix (critical from Phase 5):
- AR-2026-05-11-011: numpy used in app/ssr_ml_reranking.py but missing from requirements.txt

Write-set (<=1 file):
- requirements.txt

Read ONLY:
- requirements.txt (full, tiny)
- app/ssr_ml_reranking.py — full (96L) for confirmation
- scripts/ml/ssr_forgetting_curve_common.py — confirm same numpy use

Do not touch:
- app/ code
- tests/
- модули из других фаз arch-review

DoD (one per finding):
- AR-2026-05-11-011: rg "^numpy" requirements.txt → 1 match with explicit pin (e.g., `numpy==2.1.3`)
- python -c "import numpy" → no ImportError in clean venv (manual check)
- pytest tests/eval/test_ssr_ml_reranking.py -q → pass

Regression Guard:
- AR-2026-05-11-011: add to scripts/arch_regression_guards.py:
    used=$(rg "^import numpy|^from numpy" app/ scripts/ tests/ --type py | head -1)
    declared=$(grep -q "^numpy" requirements.txt && echo 1 || echo 0)
    [ -n "$used" ] && [ "$declared" -eq 0 ] && echo "FAIL: numpy used but not declared" || echo OK

Post-fix baseline update:
- Mark AR-2026-05-11-011 as status=resolved with resolved_date=<today>.

Token budget:
- Target <=12k input tokens.
- Hard stop >20k input tokens.
- If estimated input is 12k-20k, compress before sending.
- No retry with unchanged payload.
Output: changed files + tests run + guard(s) added + unresolved risk.

Optional follow-up (info-level, not in DoD):
- AR-2026-04-29-014: handler-level aiogram integration tests (deferred until aiogram surface grows).
```
