# Architecture Review — 2026-04-24 (Incremental)

**Baseline SHA:** `da967b17f9965e89827d01157d7cfeba67e12a10` (2026-04-21)
**HEAD:** `d40622003c8bf70d66dddf747d89beca6495eedf`
**Scope:** 136 commits, 25 changed app modules, 40+ changed test files, requirements.txt.
**Phases completed:** 1–5 (parallel, fresh context per phase).
**Previous report:** `archive/architecture_review_2026-04-21.md`.

---

## Executive Summary

Codebase remains structurally sound through a dense 136-commit delta (flashcards, SRS, sync-restore, llm_resilience, llm_guards, autonomous agent runner, context_cart gates).
**Highest-impact findings:**
1. **Router-level encapsulation breach** — `app/routers/review.py` imports `app.knowledge_graph` directly, recreating the pattern fixed in AR-2026-04-21-013 one layer up (routers instead of UI).
2. **Ingestion module and RAG assembly bloat** — `app/ingestion.py` grew to 1941 lines (+864 vs baseline); `app/query_service.py` has 6 functions >80 lines, 164-line `_try_faq_cache` is the worst offender.
3. **ADR coverage gap for major new subsystems** — LLM resilience (11 consumers), llm_guards, autonomous agent runner, context-cart gates all merged without ADRs.

Two Phase-5 "unused package" alarms (uvicorn, python-dotenv, OTel, bs4, SpeechRecognition) were **false positives** after verification — they are runtime/CLI entrypoints or used via `import` in non-obvious places. Real unused set is 3 packages.

---

## Findings Table

| # | ID | Phase | Severity | Status | Finding | File(s) | Evidence (cmd → expected) | Suggested Action |
|---|----|-------|----------|--------|---------|---------|---------------------------|------------------|
| 1 | AR-2026-04-24-001 | 1 | warning | new | Router imports `knowledge_graph` directly, bypassing service layer (same pattern as AR-2026-04-21-013, one layer up) | app/routers/review.py:7 | `rg "from app.knowledge_graph" app/routers/` → `review.py:7:from app.knowledge_graph import get_active_knowledge_graph` | Add wrapper in `knowledge_service.py` (e.g., `get_active_graph_for_review()`); change router import. |
| 2 | AR-2026-04-24-002 | 2 | warning | new | `app/ingestion.py` = 1941 lines (+864 vs baseline); 46 top-level defs; mixed orchestration + helpers + progress + metadata | app/ingestion.py | `wc -l app/ingestion.py` → `1941` | Split orchestration layer (`build_index`, progress, diff application) from pure helpers; draft package in `app/ingestion/`. |
| 3 | AR-2026-04-24-003 | 2 | warning | new | 6 functions >80 lines in `app/query_service.py`; `_try_faq_cache` (164L), `_rag_assembly_tutor_payloads` (139L), `answer_question` (109L), `_rag_assembly_response_dict` (104L) | app/query_service.py | `python -c "import ast; t=ast.parse(open('app/query_service.py','rb').read()); [print(n.end_lineno-n.lineno,n.name) for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and (n.end_lineno-n.lineno)>80]"` → 6 entries, max 164 | Extract response/payload composition into `app/query_rag_assembly.py`; cap any single function at ≤100 lines. |
| 4 | AR-2026-04-24-004 | 3 | warning | new | LLM resilience wrapper used by 11 modules (enforced by AR-2026-04-21-011 fix) without any ADR documenting the contract | app/llm_resilience.py + 11 consumers | `rg -l "from app.llm_resilience" app/ --type py \| wc -l` → `11` | Draft **ADR-014: LLM Resilience Wrapper Contract** (inputs, retry policy, fallback model, metrics emission). |
| 5 | AR-2026-04-24-005 | 3 | warning | new | Tutor orchestration subsystem (7 modules: tutor_*, orchestrator_router) still has no ADR — persists AR-2026-04-21-009 and promotes to warning since subsystem grew | app/tutor_*.py, app/orchestrator_router.py | `ls app/tutor_*.py app/orchestrator_router.py \| wc -l` → `7` | Draft **ADR-015: Tutor Orchestration Pattern** (decision loop, contract-driven pipeline). |
| 6 | AR-2026-04-24-006 | 3 | info | new | 8 modules absent from `doc/architecture.md` Module Reference | app/api_helpers.py, app/api_services.py, app/eval_service.py, app/prompts.py, app/query_metrics.py, app/query_tutor_context.py, app/ui_events.py, app/__init__.py | `comm -23 <(ls app/*.py app/routers/*.py \| xargs -n1 basename \| sort -u) <(grep -oE "[a-z_]+\.py" doc/architecture.md \| sort -u)` → 8 entries (`__init__.py` excluded) | Append short entries to architecture.md Module Reference (1-line purpose each). |
| 7 | AR-2026-04-24-007 | 3 | info | new | Autonomous agent runner subsystem (10 files: scripts/run_autonomous*, tests/test_run_autonomous*) undocumented | scripts/run_autonomous.py, scripts/run_autonomous.bat, scripts/run_autonomous.ps1, tests/test_run_autonomous_*.py | `ls scripts/run_autonomous* tests/test_run_autonomous_*` → `6+` | Add section to architecture.md §Scripts OR draft lightweight ADR-016. |
| 8 | AR-2026-04-24-008 | 5 | warning | new | 3 packages in `requirements.txt` have no imports: `transformers`, `tokenizers`, `python-docx` | requirements.txt | `for p in transformers tokenizers docx; do rg "^import $p\|^from $p" app/ scripts/ tests/ --type py \| wc -l; done` → `0 0 0` | Remove all three lines; they are legacy from prior pipelines. Keep watchdog (Streamlit dev-watcher, commented as such). |
| 9 | AR-2026-04-24-009 | 5 | info | new | `app/ui/tutor_chat.py` fan-out reduced 23→12 (AR-014 baseline improved) | app/ui/tutor_chat.py | `python -c "import ast; f='app/ui/tutor_chat.py'; t=ast.parse(open(f,'rb').read()); print(len({n.module for n in ast.walk(t) if isinstance(n,ast.ImportFrom) and n.module and n.module.startswith('app.')}))"` → `12` | No action — improvement noted. AR-2026-04-21-014 can be marked resolved. |
| 10 | AR-2026-04-21-002 | 1 | — | resolved | UI variable `prompt` renamed; violation cleared | app/ui/query_tab.py | `rg "prompt\s*=" app/ui/query_tab.py` → no matches | — |
| 11 | AR-2026-04-21-014 | 5 | — | resolved | `tutor_chat.py` fan-out 23 → 12 after refactor | app/ui/tutor_chat.py | see AR-2026-04-24-009 | — |
| 12 | AR-2026-04-21-005 | 2 | info | persists (last_seen 2026-04-24) | 13 modules >600 lines (improved from 15) | app/*.py | `wc -l app/*.py \| sort -rn \| awk '$1>600 && $2!="total"' \| wc -l` → `13` | Monitor; no fix action this cycle. |
| 13 | AR-2026-04-21-006 | 2 | info | persists | UI render fns still large (`render_topics_tab`≈786L file, `render_query_tab`≈600L file) | app/ui/topics_tab.py, app/ui/query_tab.py | file sizes | Monitor. |
| 14 | AR-2026-04-21-009 | 3 | info | **promoted to AR-2026-04-24-005** | see row 5 | — | — | Replaced by new ID at warning severity. |
| 15 | AR-2026-04-21-010 | 3 | info | persists | 7 metrics modules without ADR explaining split | app/metrics*.py | `ls app/metrics*.py \| wc -l` → `7` | Consider consolidated ADR with AR-014/015. |
| 16 | AR-2026-04-21-015 | 5 | info | persists | `watchdog` in requirements.txt has no direct import (Streamlit dev-watcher per comment) | requirements.txt:30 | `rg "watchdog" app/ scripts/ tests/ --type py` → no matches | Keep; commented intent. Re-verify on next Streamlit upgrade. |

**Status legend:** `new` | `persists` | `resolved` | `accepted-tech-debt`.

**False-positive audit (for transparency):**
- Phase 5 initially flagged uvicorn, python-dotenv, opentelemetry-*, beautifulsoup4, SpeechRecognition as unused. Manual verification found: `uvicorn` is CLI entrypoint (`scripts/e2e_run_stack.mjs`), `python-dotenv` used in `scripts/check_env.py`, OTel in 5 app modules, `bs4` in `explain_service.py` / `ingestion.py`, `speech_recognition` in `voice_service.py`. Downgraded to 3 truly unused packages.
- Phase 3 initially reported 110 undocumented modules; correct count is **8** (different diff methodology).

---

## Metrics Snapshot

- Total app/ modules: **124** (+32 vs baseline)
- app/*.py > 600 lines: **13** (down from 15 — 2 files split or shrunk)
- Functions > 80 lines (query_service.py alone): **6**
- Convention violations: **1 warning, 0 critical** (Phase 1)
- ADR drift instances: **2 missing ADRs (warning), 2 info** (Phase 3)
- Doc-code drift: **8 modules missing from architecture.md** (info)
- Dead deps: **3 packages** (warning)
- Layer violations (backend→UI, UI→core bypass): **0** (verified — past breaches all cleaned)
- Resolved from previous cycle: **2** (AR-002, AR-014)

---

## Recommended Actions (prioritized)

1. **AR-2026-04-24-001 — Router knowledge_graph breach** (S, warning). Mirror the fix pattern from AR-2026-04-21-013. Wrapper in `knowledge_service.py`, update `review.py`, add guard.
2. **AR-2026-04-24-004 + AR-2026-04-24-005 — Missing ADRs** (S, warning). Two short ADRs; unblock future architectural drift evaluation.
3. **AR-2026-04-24-008 — Dead deps** (S, warning). Remove 3 lines from requirements.txt.
4. **AR-2026-04-24-002 — Ingestion split** (M, warning). Package-sized refactor — schedule as its own epoch; do NOT bundle with fix prompts.
5. **AR-2026-04-24-003 — query_service function decomposition** (M, warning). Extract RAG assembly module.
6. **AR-2026-04-24-006 + 007 — Doc coverage** (S, info). 15-minute editorial pass.

---

## Fix Prompts

### Fix-prompt — Phase 1

```text
Ignore prior responses/tools. Fresh context only.

Goal: fix Phase 1 findings from doc/architecture_review_2026-04-24.md.
Baseline: doc/arch_review_baseline.yaml
Report:   doc/architecture_review_2026-04-24.md

Findings to fix (warning):
- AR-2026-04-24-001: app/routers/review.py:7 imports app.knowledge_graph directly.

Write-set (≤ 3 files):
- app/routers/review.py
- app/knowledge_service.py
- doc/conventions_architecture.md

Read ONLY:
- app/routers/review.py (full, small)
- app/knowledge_service.py — signatures only (`rg "^class|^def " app/knowledge_service.py`)
- doc/conventions_architecture.md § Knowledge Encapsulation

Do not touch:
- app/knowledge_graph.py, any other router, any UI module.

DoD:
- AR-2026-04-24-001: `rg "from app.knowledge_graph" app/routers/` → no matches.

Regression Guard (required):
- New convention rule in doc/conventions_architecture.md § Knowledge Encapsulation:
  "Routers (app/routers/*.py) MUST NOT import app.knowledge_graph or app.user_state_core
   directly; go through *_service.py wrappers."
- Add to scripts/arch_regression_guards.sh:
    rg "from app\.knowledge_graph" app/routers/ --type py && echo "FAIL: router→knowledge_graph" || echo "OK"

Post-fix baseline update:
- Mark AR-2026-04-24-001 status=resolved, resolved_date=<today> in doc/arch_review_baseline.yaml.

Token budget:
- Target <=12k input tokens.
- Hard stop >20k input tokens.
- If estimated input is 12k-20k, compress before sending.
- No retry with unchanged payload.

Output: changed files + tests run + guard added + unresolved risk.
```

### Fix-prompt — Phase 2

```text
Ignore prior responses/tools. Fresh context only.

Goal: fix Phase 2 findings from doc/architecture_review_2026-04-24.md.
Baseline: doc/arch_review_baseline.yaml
Report:   doc/architecture_review_2026-04-24.md

Findings to fix (warning):
- AR-2026-04-24-003: app/query_service.py has 6 functions >80 lines; extract RAG assembly.

Note on AR-2026-04-24-002 (ingestion split): M-size refactor, do NOT bundle here — schedule
its own epoch. This fix-prompt covers only query_service assembly extraction.

Write-set (≤ 3 files):
- app/query_service.py
- app/query_rag_assembly.py (NEW)
- tests/test_query_service.py (1-2 new cases only, not full rewrite)

Read ONLY:
- app/query_service.py — signatures first (`rg "^class|^def " app/query_service.py`),
  then read only the 4 target functions:
  `_try_faq_cache`, `_rag_assembly_tutor_payloads`, `_rag_assembly_response_dict`, `_assemble_rag_result`
- app/models.py — signatures only
- 1 existing test case from tests/test_query_service.py (do NOT read whole file)

Do not touch:
- app/ingestion.py, app/knowledge_graph.py, any UI module, any router.

DoD:
- AR-2026-04-24-003:
    python -c "import ast; t=ast.parse(open('app/query_service.py','rb').read()); bad=[(n.end_lineno-n.lineno,n.name) for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and (n.end_lineno-n.lineno)>100]; import sys; sys.exit(1 if bad else 0)"
  → exit 0 (no function >100 lines after refactor).
- pytest tests/test_query_service.py -x → pass.

Regression Guard (required):
- Invariant test tests/test_query_service_invariants.py::test_no_function_over_100_lines
  that parses app/query_service.py and fails if any function body >100 lines.
- Add to scripts/arch_regression_guards.sh:
    python -c "import ast,sys; t=ast.parse(open('app/query_service.py','rb').read()); bad=[n for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and (n.end_lineno-n.lineno)>100]; sys.exit(1 if bad else 0)" && echo "OK" || echo "FAIL: query_service fn >100L"

Post-fix baseline update:
- Mark AR-2026-04-24-003 status=resolved.
- Keep AR-2026-04-24-002 open (follow-up epoch).

Token budget:
- Target <=12k. Hard stop >20k. No retry with unchanged payload.
Output: changed files + tests run + guard(s) + unresolved risk.

Optional follow-up (not in DoD):
- AR-2026-04-24-002: ingestion.py 1941L split — schedule as its own package.
```

### Fix-prompt — Phase 3

```text
Ignore prior responses/tools. Fresh context only.

Goal: fix Phase 3 findings from doc/architecture_review_2026-04-24.md.
Baseline: doc/arch_review_baseline.yaml
Report:   doc/architecture_review_2026-04-24.md

Findings to fix (warning):
- AR-2026-04-24-004: draft ADR for LLM resilience wrapper.
- AR-2026-04-24-005: draft ADR for tutor orchestration subsystem (replaces AR-2026-04-21-009).

Write-set (≤ 4 files):
- doc/adr.md (append 2 ADRs + 2 registry rows)
- doc/architecture.md (cross-link from affected module sections)
- scripts/arch_regression_guards.sh (ADR coverage check)
- doc/conventions_architecture.md (guard rule)

Read ONLY:
- doc/adr.md — status table only (`grep -A 40 "^| Status" doc/adr.md | head -45`) + last 2 ADR headers
- app/llm_resilience.py (full, small)
- app/tutor_pipeline_contract.py (full, small)
- app/tutor_orchestrator.py — signatures only (`rg "^class|^def " app/tutor_orchestrator.py`)

Do not touch:
- any code under app/ (design docs only).

DoD:
- AR-2026-04-24-004: `grep -c "## ADR-.*LLM Resilience" doc/adr.md` → ≥1.
- AR-2026-04-24-005: `grep -c "## ADR-.*Tutor Orchestration" doc/adr.md` → ≥1.
- ADR registry table and body counts match (regression guard from AR-2026-04-21-007 must still pass):
    actual=$(grep -c "^## ADR-" doc/adr.md); registry=$(grep -c "^| \[0" doc/adr.md); [ "$actual" -eq "$registry" ] && echo OK || echo FAIL

Regression Guard (required):
- Add to scripts/arch_regression_guards.sh:
    # Subsystems must have an ADR. Map: subsystem-pattern → required ADR keyword.
    has_tutor=$(grep -c "Tutor Orchestration" doc/adr.md)
    has_resilience=$(grep -c "LLM Resilience" doc/adr.md)
    [ "$has_tutor" -ge 1 ] && [ "$has_resilience" -ge 1 ] && echo "OK: required ADRs present" || echo "FAIL: missing subsystem ADR"

Post-fix baseline update:
- Mark AR-2026-04-24-004, AR-2026-04-24-005 status=resolved.
- Mark AR-2026-04-21-009 status=superseded-by:AR-2026-04-24-005.

Token budget:
- Target <=12k. Hard stop >20k. No retry with unchanged payload.
Output: changed files + ADRs drafted + guard added + unresolved risk.

Optional follow-up (info, not in DoD):
- AR-2026-04-24-006: add 8 missing modules to architecture.md Module Reference.
- AR-2026-04-24-007: document autonomous agent runner subsystem.
- AR-2026-04-21-010: consolidated ADR for metrics split.
```

### Fix-prompt — Phase 4

```text
No fix-prompt required for Phase 4 (no actionable findings above info level).

Quality, SQLi mitigation, LLM resilience compliance, and prompt-injection guardrails all
verified PASS against the changed scope. See report §Phase 4 for evidence.
```

### Fix-prompt — Phase 5

```text
Ignore prior responses/tools. Fresh context only.

Goal: fix Phase 5 findings from doc/architecture_review_2026-04-24.md.
Baseline: doc/arch_review_baseline.yaml
Report:   doc/architecture_review_2026-04-24.md

Findings to fix (warning):
- AR-2026-04-24-008: remove 3 unused packages (transformers, tokenizers, python-docx) from requirements.txt.

Write-set (≤ 2 files):
- requirements.txt
- scripts/arch_regression_guards.sh

Read ONLY:
- requirements.txt (full, small)
- scripts/arch_regression_guards.sh

Do not touch:
- watchdog line (commented as Streamlit dev-watcher — retain).
- any uvicorn / python-dotenv / opentelemetry / bs4 / SpeechRecognition entries (verified USED).
- any app/ code.

DoD:
- AR-2026-04-24-008:
    grep -E "^(transformers|tokenizers|python-docx)" requirements.txt | wc -l → 0
- pip install -r requirements.txt completes without error.

Regression Guard (required):
- Add to scripts/arch_regression_guards.sh:
    # Fail if any listed-as-removed package reappears without a corresponding import.
    for pkg in transformers tokenizers docx; do
      if grep -qE "^${pkg}([<>=]|$)" requirements.txt; then
        uses=$(rg "^import ${pkg}|^from ${pkg}" app/ scripts/ tests/ --type py 2>/dev/null | wc -l)
        [ "$uses" -eq 0 ] && { echo "FAIL: ${pkg} in requirements.txt but no imports"; exit 1; }
      fi
    done
    echo "OK: no re-added dead deps"

Post-fix baseline update:
- Mark AR-2026-04-24-008 status=resolved, resolved_date=<today>.

Token budget:
- Target <=12k. Hard stop >20k. No retry with unchanged payload.
Output: changed files + pip install check + guard added.

Optional follow-up (not in DoD):
- AR-2026-04-21-015: re-verify watchdog on next Streamlit upgrade.
```

---

## Baseline Update (patch for `doc/arch_review_baseline.yaml`)

1. **`last_review`** block → set `sha: d40622003c8bf70d66dddf747d89beca6495eedf`, `date: "2026-04-24"`, `report_file: doc/architecture_review_2026-04-24.md`, `phases_completed: [1,2,3,4,5]`, `phases_pending: []`.
2. **Status transitions on existing findings:**
   - `AR-2026-04-21-002`: already resolved, keep.
   - `AR-2026-04-21-005`: status persists, `last_seen: "2026-04-24"`.
   - `AR-2026-04-21-006`: status persists, `last_seen: "2026-04-24"`.
   - `AR-2026-04-21-009`: `status: superseded-by: AR-2026-04-24-005`, `last_seen: "2026-04-24"`.
   - `AR-2026-04-21-010`: status persists, `last_seen: "2026-04-24"`.
   - `AR-2026-04-21-014`: `status: resolved`, `resolved_date: "2026-04-24"`.
   - `AR-2026-04-21-015`: status persists, `last_seen: "2026-04-24"`.
3. **Append new findings:** AR-2026-04-24-001 through AR-2026-04-24-009 (see Findings Table above for fields).

Exact YAML patch committed as part of this review — see `doc/arch_review_baseline.yaml`.

---

## Appendix — Positive Patterns (preserve, replicate)

1. **Service-layer encapsulation holds**: after AR-2026-04-21-013 fix, NO UI module imports `app.knowledge_graph` anymore. Pattern is working — the one regression (AR-2026-04-24-001) is a routers-layer slip, not UI.
2. **Resilience wrapper adoption**: `chat_with_resilience` usage now covers all `.chat()` call sites in changed files; AR-2026-04-21-011 fix held through 136 commits.
3. **Input-validation discipline on LLM endpoints**: `app/routers/flashcards.py` validates every user field (identifier, content, source_paths, course_id, course_title, folder_rel) via `validate_llm_input_text` / `validate_llm_input_list` before invoking generators. Copy this pattern for any new LLM-facing router.
4. **Tutor-chat UI decomposition**: fan-out dropped 23 → 12 by delegating to UI submodules — clean intra-layer refactor, reference example for future UI bloat.
5. **Falsifiable baseline YAML**: every persists/resolved decision in this cycle was decidable from an `evidence_cmd` — zero subjective calls. Keep this rigor.

---

## Rules observed in this review

- No code written or edited (except this report + baseline YAML).
- Every finding has an `evidence_cmd` and expected output; subjective observations downgraded to info.
- Two Phase-agent claims (Phase 3 "110 missing modules", Phase 5 "10 unused packages") were verified against the repo and corrected before inclusion — see False-positive audit above.
- Fix-prompts scoped to ≤5 files each; every critical/warning finding has a Regression Guard.
- Ingestion refactor (AR-2026-04-24-002) deliberately NOT bundled into a fix-prompt — its size exceeds the single-prompt budget and warrants its own planning cycle.
