# Architecture Review — Phase 1 (Conventions)
**Date:** 2026-04-29  
**Reviewer:** Antigravity (Claude Sonnet 4.6 Thinking)  
**Scope:** Conventions — AGENTS.md hard rules, env-reads, LLM client discipline, prompt discipline, router discipline, pipeline contract, DB access discipline  

---

## Phase: 1

## Baseline
`last_review.sha: d40622003c8bf70d66dddf747d89beca6495eedf`  
Previous review date: 2026-04-24

## Incremental Scope
**Changed app/ + scripts/ files since baseline (relevant subset):**
- `app/config.py`, `app/ingestion.py`, `app/knowledge_service.py`, `app/course_graduation.py`,  
  `app/course_cache.py`, `app/course_metrics.py`, `app/diagnostic_service.py`, `app/pace_engine.py`,  
  `app/query_rag_assembly.py`, `app/query_response_postprocessing.py`, `app/query_service.py`,  
  `app/tutorial_service.py`, `app/warmup_planner.py`, `app/dummy.py`  
- `app/routers/dashboard.py`, `app/routers/flashcards.py`, `app/routers/knowledge.py`,  
  `app/routers/query.py`, `app/routers/quiz.py`, `app/routers/review.py`  
- `app/ui/main.py`, `app/ui/tutor_chat.py`, `app/ui/tutor_chat_header.py`, and 10+ other ui/ files  
- `scripts/run_autonomous.py`, `scripts/close_package.py`, `scripts/pipeline_guard_logic.py`,  
  `scripts/prompt_utils.py`, `scripts/_perf_timer.py`, and ~30 other scripts  

**Baseline Phase 1 findings carried forward for re-check:**  
`AR-2026-04-21-001`, `AR-2026-04-21-002`, `AR-2026-04-24-001`

## Read-set Used
| File / Command | Access mode |
|---|---|
| `doc/archive/arch_review_baseline.yaml` | Section (Phase 1 findings only) |
| `git diff --name-only <sha>..HEAD` | rg-equivalent (list only) |
| `Get-ChildItem -Recurse app,scripts | Select-String` | Signatures / grep-only |
| `app/ingestion.py` | Lines 125–166 (context section only) |
| `git cat-file -e <sha>:app/<file>` | existence check only |

No full file reads. Token budget: SAFE (well under 12k input).

---

## Findings

### AR-2026-04-21-001 — `os.environ` reads outside `config.py` in `app/`

- **id:** AR-2026-04-21-001  
- **phase:** 1  
- **severity:** warning  
- **title:** `app/ingestion.py` reads `os.environ` directly — convention violation (diagnostic utility but still outside `config.py`)  
- **files:** `["app/ingestion.py:154"]`  
- **status:** persists (new violating hit in changed file; prior violations remain in `scripts/` with longstanding acceptance)  
- **last_seen:** 2026-04-29  

**Detail:**  
`app/ingestion.py` line 154 inside `_embed_env_sources()`:
```python
process_values = {name: os.environ[name] for name in names if name in os.environ}
```
The function docstring explicitly states this is "not used for runtime configuration … used for CI/shell diagnostic display." However, the AGENTS.md rule is absolute: _"Cannot read env variables directly anywhere except `config.py`."_ The diagnostic intent does not grant an exemption.

Previously this finding was scored against `scripts/` (which had numerous hits); `app/ingestion.py` is a **new** violating file in the incremental scope.

- **evidence_cmd:**
  ```powershell
  Select-String -Path "app/ingestion.py" -Pattern "os\.environ" | Select-Object LineNumber,Line
  ```
- **expected_evidence:** Line 154 — `process_values = {name: os.environ[name] …}`

**Recommended fix:** Extract the diagnostic logic to a helper in `app/config.py` or `scripts/` (not `app/`), or gate it behind an explicit call from `config.py` only.

---

### AR-2026-04-21-002 — LLM clients / prompts outside `provider.py` / `prompts.py`

- **id:** AR-2026-04-21-002  
- **phase:** 1  
- **severity:** info (downgraded from warning: no new violations found in incremental scope)  
- **title:** No direct `openai.OpenAI()` / `AsyncOpenAI()` construction found outside `provider.py` in changed modules; no hardcoded system prompts found in changed service modules  
- **files:** []  
- **status:** resolved (for this incremental window — no regressions in changed files)  
- **last_seen:** 2026-04-29  

**Detail:**  
Scanned all changed `app/` service modules (`diagnostic_service.py`, `knowledge_service.py`, `tutorial_service.py`, `pace_engine.py`, `query_rag_assembly.py`, `query_response_postprocessing.py`, `query_service.py`, etc.) for:
- Direct `openai.OpenAI()`/`AsyncOpenAI()` construction → **0 matches**
- Hardcoded `You are a` / `system_prompt =` strings → **0 matches**

- **evidence_cmd:**
  ```powershell
  Get-ChildItem -Recurse -Path app -Filter "*.py" | Select-String -Pattern "openai\.OpenAI|AsyncOpenAI|anthropic\.Anthropic" | Where-Object { $_.Path -notmatch "provider\.py" }
  ```
- **expected_evidence:** No output (0 matches)

---

### AR-2026-04-24-001 — Router imports `knowledge_graph` directly

- **id:** AR-2026-04-24-001  
- **phase:** 1  
- **severity:** resolved  
- **title:** `app/routers/review.py` no longer imports `app.knowledge_graph` directly  
- **files:** []  
- **status:** resolved  
- **resolved_date:** 2026-04-29 (confirmed clean)  

**Detail:**  
Evidence command returns **0 matches** — the regression guard holds.

- **evidence_cmd:**
  ```powershell
  Get-ChildItem -Recurse -Path "app/routers" -Filter "*.py" | Select-String -Pattern "from app\.knowledge_graph"
  ```
- **expected_evidence:** No output (0 matches — confirmed)

---

### AR-2026-04-29-001 — `app/` modules open SQLite directly, bypassing `_with_db()` — **NEW**

- **id:** AR-2026-04-29-001  
- **phase:** 1  
- **severity:** warning  
- **title:** 4 `app/` modules open `sqlite3.connect()` directly outside `user_state.py` — violates DB/persistence convention  
- **files:**  
  `["app/event_tracking.py:29", "app/knowledge_graph.py:908", "app/knowledge_graph.py:933", "app/knowledge_graph_bundle.py:95", "app/metrics_db.py:202", "app/metrics_db.py:236", "app/metrics_db.py:273", "app/quiz_adaptive.py:66"]`
- **status:** new  
- **first_seen:** 2026-04-29  

**Detail:**  
AGENTS.md rule: _"DB / persistence: only through `_with_db()` from `app/user_state.py`. Cannot open SQLite connections directly in services."_

Found 8+ direct `sqlite3.connect(…)` calls across 4 app modules (`event_tracking.py`, `knowledge_graph.py`, `knowledge_graph_bundle.py`, `metrics_db.py`, `quiz_adaptive.py`). These modules each manage their own SQLite databases (metrics, knowledge graph, event log), which suggests **architectural fragmentation** — multiple separate persistence channels exist alongside `user_state.py`'s `_with_db()` pattern.

Note: `event_tracking.py`, `metrics_db.py`, and `knowledge_graph_bundle.py` all existed at baseline SHA (confirmed via `git cat-file`), but this finding was never captured in prior reviews — it is being raised now as part of the changed scope (`app/ingestion.py` → `app/query_rag_assembly.py` → transitively exposed this pattern).

- **evidence_cmd:**
  ```powershell
  Get-ChildItem -Recurse -Path app -Filter "*.py" | Select-String -Pattern "sqlite3\.connect" | Where-Object { $_.Path -notmatch "user_state\.py" } | Select-Object Path,LineNumber
  ```
- **expected_evidence:**
  ```
  app\event_tracking.py       :29
  app\knowledge_graph.py      :908, :933
  app\knowledge_graph_bundle.py :95
  app\metrics_db.py           :202, :236, :273
  app\quiz_adaptive.py        :66
  ```

**Severity rationale:** These are structural violations of the hard rule but represent well-established sub-systems (metrics DB, KG persistence) likely predating the rule. Recommend either:
1. Formally accept as tech debt with `# noqa: DB001` annotation convention and note in `doc/adr.md`, or  
2. Extract per-module `_with_db()` wrappers to contain the pattern.

---

### AR-2026-04-29-002 — `scripts/` has 6+ direct `os.environ` reads — convention scope clarification needed — **NEW**

- **id:** AR-2026-04-29-002  
- **phase:** 1  
- **severity:** info  
- **title:** `scripts/` has 6+ direct `os.environ` reads — AGENTS.md rule applies to `app/` only; scripts scope ambiguous  
- **files:**  
  `["scripts/close_package.py:822", "scripts/close_package.py:1034", "scripts/pipeline_guard_logic.py:110", "scripts/prompt_utils.py:1307", "scripts/run_autonomous.py:1026", "scripts/_perf_timer.py:162", "scripts/_perf_timer.py:198"]`
- **status:** new  
- **first_seen:** 2026-04-29  

**Detail:**  
AGENTS.md states: _"Cannot read env variables directly anywhere except `config.py`."_ The word "anywhere" is absolute, but `scripts/` modules are autonomous runners/tools that cannot import `app.config` without pulling in the full app stack (circular dependency risk, startup cost). The prior baseline (2026-04-21) acknowledged this as existing-but-tolerated. This finding formalizes the ambiguity: **the rule needs an explicit carve-out for `scripts/`**, or scripts must be re-scoped to import a lightweight env-reader from a non-`app/` utility.

Downgraded to `info` because the hits are all in `scripts/` (tooling layer), but the `app/ingestion.py` violation at AR-2026-04-29-001 confirms the boundary is blurring.

- **evidence_cmd:**
  ```powershell
  Get-ChildItem -Recurse -Path scripts -Filter "*.py" | Select-String -Pattern "os\.environ\[|os\.environ\.get" | Where-Object { $_.Path -notmatch "arch_regression_guards|check_env" } | Select-Object Path,LineNumber
  ```
- **expected_evidence:** 7+ matches across `close_package.py`, `pipeline_guard_logic.py`, `prompt_utils.py`, `run_autonomous.py`, `_perf_timer.py`

---

## Accepted Tech Debt Summary

No tech debt items were formally marked `accepted` in the baseline for Phase 1. The `watchdog` finding (`AR-*-info`) in Phase 5 is unrelated.

---

## Summary

1. **AR-2026-04-24-001 is fully resolved** — no router now imports `knowledge_graph` directly; regression guard is clean.
2. **AR-2026-04-21-001 persists** — `app/ingestion.py` (newly changed in this window) introduces a direct `os.environ` read in `_embed_env_sources()`. Despite the diagnostic intent, it violates the hard convention. Needs either relocation to `config.py` or `scripts/`.
3. **AR-2026-04-29-001 is a new warning** — 4+ `app/` modules bypass `_with_db()` and open SQLite directly. This is a rule violation that has apparently existed since at least baseline SHA but was never surfaced. Formal tech-debt acceptance or containment wrappers are the recommended path.
4. **AR-2026-04-29-002 is a new info** — clarification needed on whether `scripts/` is exempt from the `os.environ` ban; 7+ hits in changed script files.
5. **No new LLM client or prompt hardcoding violations** were found in the 11 changed service modules — convention discipline in that area is holding well.
