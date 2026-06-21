# ADR-021 Appendix A: Global Analytics Design

**Status:** Accepted  
**Date:** 2026-05-16  
**Package:** epoch-adr-021-global-analytics-design  
**CJM Stage:** #10 Retrieval trust, Planning and quality infrastructure

---

## Context

Global GraphRAG analytics (community/global summaries) addresses corpus-level questions — knowledge maps, contradiction detection, corpus-wide synthesis. ADR-021 [§4.3](../doc/adr_021_smart_router_rag_modes.md) mandates that `global_graph` is NOT a retrieval mode and NOT an ordinary `/ask` fallback. [§12 Phase 4](../doc/adr_021_smart_router_rag_modes.md#phase-4-global-analytics-design) requires a separate design document before any implementation.

This document specifies the `GlobalAnalyticsJob`, artifact ownership, provenance, recomputation rules, cost/token/latency ceilings, kill switch, and API/UI boundaries.

**PO Decisions (2026-05-16):**

- Scheduled recomputation: weekly (1x per week)
- On-demand recomputation: supported via API/UI
- Kill switch: `RetrievalSettings.enable_global_analytics` (boolean, from `.env`)
- Mid-job kill: abort immediately, no partial results

---

## 1. GlobalAnalyticsJob

### 1.1 Job Lifecycle

```
trigger → queued → running → done | failed
```

| State | Description |
|-------|-------------|
| `trigger` | Input data received (scope descriptor + generation_id). Pre-flight check passes. |
| `queued` | Job waits for Executor. Queue is sequential — 1 running max. |
| `running` | LLM-based summarization in progress. Runtime ceiling monitoring active. |
| `done` | Result written to artifacts. |
| `failed` | Error, ceiling violation, or kill switch abort. |

### 1.2 Job ID Format

**UUID v4** (36-character string, hex with dashes).

Rationale: unique without coordination, suitable for NTFS/FAT filenames, no collision risk in concurrent environments.

### 1.3 Artifact Ownership

Base path: `data/graph_analytics/jobs/<job_id>/`

Directory contents:

| File | Required | Contents |
|------|----------|----------|
| `metadata.json` | yes | run id, timestamp (ISO 8601), config snapshot, git commit (if available), generation_id, scope_descriptor |
| `result.json` | yes | Serialized community/global summaries (main artifact) |
| `ceiling_violation.json` | only on abort by ceiling | Reason and measured values at violation point |

### 1.4 metadata.json Schema (design-time)

```json
{
  "job_id": "uuid-v4-string",
  "run_id": "uuid-v4-string",
  "created_at": "2026-05-16T12:00:00Z",
  "config_snapshot": {
    "enable_global_analytics": true,
    "max_total_tokens": 100000,
    "model": "claude-sonnet-4-20250514"
  },
  "git_commit": "abc123def...",
  "generation_id": "gen-20260515-001",
  "scope_descriptor": {
    "type": "corpus",
    "scope_id": "full",
    "description": "Full corpus global summary"
  },
  "status": "done"
}
```

`git_commit` is optional — null when unavailable (detached HEAD, CI without clone).

---

## 2. Provenance Schema

### 2.1 Forward Provenance Chain

```
summary_artifact (data/graph_analytics/jobs/<job_id>/metadata.json)
  └─ generation_id
       └─ index_registry.json → active_index
            └─ chunks/documents
```

### 2.2 Rules

- Every artifact contains `generation_id` as a forward link to the graph/index generation.
- Provenance does NOT use nested structure — artifact references generation by id, does not copy generation data.
- Summaries do NOT replace citations. They are additional derived artifacts.
- Provenance chain length: summary → generation_id → chunks → documents (max 3 hops).

### 2.3 Scope Descriptor Schema

```json
{
  "type": "corpus" | "topic" | "document_set",
  "scope_id": "<identifier>",
  "description": "<human-readable description>"
}
```

- `corpus`: full corpus summary
- `topic`: summary scoped to a single topic
- `document_set`: summary of a specific set of documents

---

## 3. Recomputation Rules

### 3.1 Triggers

| Trigger | Type | Behavior |
|---------|------|----------|
| On-demand | Manual (API/UI) | User-initiated job. Generates new artifact. |
| Scheduled | Weekly (1x) | Cron-like trigger at fixed time (e.g., Sunday 03:00). If already current for this generation, skip. If generation changed after last weekly, force run. |
| Generation change | Automatic | When `active_index` in `index_registry.json` changes. Marks all artifacts with old generation_id as stale. |

### 3.2 Invalidation Strategy

- **Cache key:** `(generation_id, scope_descriptor_hash)`
- **Stale marking:** Artifacts with stale generation_id are marked `stale` in metadata. Not deleted (history preserved), but excluded from new queries.
- **Same scope + same generation:** New job overwrites `result.json`.
- **Partial recomputation:** Not supported in first iteration. Always full scope.

### 3.3 Scheduling Detail

- Weekly job: configurable day/time (default Sunday 03:00).
- If weekly job is already current (matching generation_id, no newer generation), skip.
- If weekly job is stale, the scheduler triggers a new job automatically.
- On-demand jobs are independent — they do not reset the weekly timer.

---

## 4. Cost/Token/Latency Ceilings

### 4.1 CeilingConfig (design-time)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_total_tokens` | 100,000 | Max LLM tokens consumed per job |
| `max_llm_calls` | 50 | Max LLM invocations per job |
| `max_latency_seconds` | 600 (10 min) | Max wall-clock time per job |
| `max_cost_usd` | null | Optional (requires pricing model) |

### 4.2 Pre-flight Check

1. Check `enable_global_analytics` — if false, reject job immediately.
2. Estimate expected consumption — if expected > ceiling, reject with message.
3. Validate generation_id exists in `index_registry`.

### 4.3 Runtime Monitoring

- Counter `total_tokens` incremented after each LLM call.
- Counter `total_llm_calls` incremented after each LLM call.
- Timer `elapsed_seconds` measured from job start.
- On any ceiling violation → **abort immediately** (no graceful shutdown).
- Violation details written to `ceiling_violation.json`.

### 4.4 ceiling_violation.json Schema

```json
{
  "violated_ceiling": "max_total_tokens",
  "limit": 100000,
  "actual": 105432,
  "triggered_at": "2026-05-16T12:05:00Z",
  "partial_result_path": null
}
```

No partial results on abort — kill is immediate.

---

## 5. Kill Switch

### 5.1 Mechanism

**Config field:** `enable_global_analytics` in `RetrievalSettings` (boolean, default: `false`).

- Source: `.env` / env vars, via `get_retrieval_settings()`.
- Does NOT affect: ordinary `/ask` endpoint, existing retrieval modes, tutor pipeline.

### 5.2 Behavior

| `enable_global_analytics` | Pre-flight | Mid-job |
|---------------------------|------------|---------|
| `true` | Jobs can start (subject to ceilings) | — |
| `false` | All jobs rejected immediately | Running job aborted immediately (no partial results) |

Mid-job kill switch trigger: abort immediate, no graceful shutdown, no partial results.

---

## 6. API/UI Boundaries

### 6.1 Design-Time Contract (implemented by future packages)

**API:**

| Method | Path | Purpose | Status |
|--------|------|---------|--------|
| POST | `/global-analytics` | Start a global analytics job | Future implementation |
| GET | `/global-analytics/<job_id>` | Get job status + result | Future implementation |
| GET | `/global-analytics` | List all jobs | Future implementation |

`POST /global-analytics` body:

```json
{
  "scope": {
    "type": "corpus" | "topic" | "document_set",
    "scope_id": "optional-identifier"
  },
  "on_demand": true
}
```

**Strict prohibitions:**

- `global_graph` MUST NOT be added to `KNOWN_RETRIEVAL_MODES`
- Ordinary `/ask` MUST NOT fall back to global analytics
- No global analytics prompt added to `app/prompts/` without separate review

**UI:**

- Streamlit: new section "Global Analytics" in debug panel (or separate page)
- Display: job list (id, status, generation_id, created_at)
- Actions: run on-demand, view result
- Hidden: raw retrieval_mode, `global_graph`

### 6.2 Implementation Package Boundaries

The follow-up implementation package will:

1. Create endpoint in `app/routers/` + register in `app/api.py`
2. Create background worker (or async job executor)
3. Create Streamlit UI components
4. Add focused tests
5. Add `enable_global_analytics` to `RetrievalSettings`

The implementation package will NOT:

- Modify ADR-021 routing contract
- Modify existing `retrieval_strategies.py`
- Modify pipeline steps
- Add `global_graph` to `KNOWN_RETRIEVAL_MODES`

---

## 7. Future Test Strategy (design-time)

Focused tests for the implementation package:

- **Job lifecycle test:** trigger → running → done, verify artifact files exist
- **Ceiling abort test:** mock high token count, verify abort + ceiling_violation.json
- **Kill switch test:** `enable_global_analytics=false`, verify job rejection
- **Provenance test:** verify forward link chain summary → generation → chunks
- **Recomputation test:** same scope twice → result.json overwritten; new generation → stale marking

---

## 8. References

- [ADR-021 §4.3](../doc/adr_021_smart_router_rag_modes.md) — global_graph outside KNOWN_RETRIEVAL_MODES
- [ADR-021 §7.3](../doc/adr_021_smart_router_rag_modes.md#73-globalanalyticsjob-and-provenance) — GlobalAnalyticsJob artifact contract
- [ADR-021 §12 Phase 4](../doc/adr_021_smart_router_rag_modes.md#phase-4-global-analytics-design) — global analytics design phase
- [doc/conventions_architecture.md](../doc/conventions_architecture.md) — module boundaries
- [doc/api_reference.md](../doc/api_reference.md) — existing API surface
