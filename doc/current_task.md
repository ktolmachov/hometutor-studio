> **ORCHESTRATION STEP TASK — execute ONLY Step 3.5 in this session.**
> Do not execute other steps. Do not call `generate_next_prompt.py --quick`.

# Orchestration Step 3.5 — Ops Impact Gate  [CONDITIONAL, fires if false=true]

Package: `multi-query-expansion-v1`
Target agent: `cursor_ai`
Orchestration file: `archive/team_artifacts/multi-query-expansion-v1/orchestration_cursor_ai.md`

Execute ONLY the following section from `archive/team_artifacts/multi-query-expansion-v1/orchestration_cursor_ai.md`:

## STEP 3.5 — Ops Impact Gate  [CONDITIONAL, fires if false=true]

PURPOSE: Surface RAG / LLM / ML / Course Workspace risks BEFORE Developer writes code.
         Each triggered Ops role produces a structured Impact Report (GREEN / YELLOW / RED).

SKIP CONDITION:
  If false == false:
    Print "[multi-query-expansion-v1] Step 3.5 — Ops Impact Gate: SKIPPED (no triggers in write-set)"
    Save (MANDATORY — workflow detector requires this file):
      archive/team_artifacts/multi-query-expansion-v1/3_5_skipped.md
      Content: one-line note — "STEP 3.5 SKIPPED: no ops triggers in write-set"
    Proceed directly to STEP 4.

TRIGGERS (canonical list — doc/team_workflow/rag_llm_ops_project_document.md §35
          + perf triggers from doc/team_workflow/performance_devops.md):
  app/provider.py                                        → llmops
  app/config.py (новые LLM / embeddings / profile keys)  → llmops
  app/prompts/, app/tutor_prompts.py                     → llmops
  app/query_service.py, app/pipeline_steps.py            → ragops
  app/course_cache.py, app/ui/study_scope.py, data/docs/ → ragops
  app/knowledge_graph.py                                 → mlops + ragops
  embeddings / chunking strategy / index version         → mlops + ragops
  scripts/local_readiness.py, app/ui/llm_local_banner.py → llmops + performance (+ Designer note)
  scripts/local_*.{py,ps1}, .env.example                 → performance
  timeouts / budgets / new runtime dependencies          → performance
  Dockerfile / CI workflows / GitHub Actions             → performance (sole)
  ingest throughput / new ingestion-pipeline step        → performance + ragops

BEFORE STARTING:
  Read: archive/team_artifacts/multi-query-expansion-v1/3_architect_contract.md (write-set + sub-package boundaries)
  Read: archive/team_artifacts/multi-query-expansion-v1/2_analyst_spec.md (data flow)
  Resolve  from write-set vs triggers above.

Открыть Agents Window (View → Agents или Ctrl+Shift+A).
По одному "New Agent" на каждую роль.
Вставить промпт каждого агента в соответствующее окно.
Дождаться Complete в окнах Agents Window.
Затем вернуться в основной Composer window и продолжить.
[one agent per role in ]:

  AGENT R — RAGOps  (only if "ragops" in ):
    Read: doc/team_workflow/ragops_engineer.md → Промпт 1
    Inject: write-set from architect contract; relevant balance-plan §4 subsection
    Cursor сохраняет файлы через IDE: → archive/team_artifacts/multi-query-expansion-v1/3_5_ragops_impact.md

  AGENT L — LLMOps  (only if "llmops" in ):
    Read: doc/team_workflow/llmops_engineer.md → Промпт 1
    Inject: write-set; balance-plan §Phase 1/2/3 if profile/fallback/banner touched
    Cursor сохраняет файлы через IDE: → archive/team_artifacts/multi-query-expansion-v1/3_5_llmops_impact.md

  AGENT M — MLOps  (only if "mlops" in ):
    Read: doc/team_workflow/mlops_engineer.md → Промпт 1
    Inject: write-set; current eval baseline run_id from index_versions registry
    Cursor сохраняет файлы через IDE: → archive/team_artifacts/multi-query-expansion-v1/3_5_mlops_impact.md

  AGENT P — Performance / DevOps  (only if "performance" in ):
    Read: doc/team_workflow/performance_devops.md → Промпт 1
    Inject: write-set; last 5 rows of archive/pipeline_metrics.md (filenames only,
            не читать timing-файлы целиком — это съест бюджет)
    Cursor сохраняет файлы через IDE: → archive/team_artifacts/multi-query-expansion-v1/3_5_performance_impact.md

WAIT for all triggered agents to complete.

VERDICT ROUTING (combine reports):
  ALL GREEN          → print status line, START STEP 4 immediately.
  ANY YELLOW (no RED) → append conditions to archive/team_artifacts/multi-query-expansion-v1/deferred.md AND inject
                        them into Developer prompt (STEP 4) as additional DoD/test
                        requirements. Proceed to STEP 4.
  ANY RED            → STOP. Print combined RED findings.
                       Ask user: "Send back to Architect for write-set/contract revision? (y/n)"
                       If y → re-run STEP 3 with RED findings; then re-run STEP 3.5.
                       Do NOT proceed to STEP 4 until no RED remains.

CHECKPOINT:
  ✓ Each triggered role produced its impact artifact?
  ✓ No RED verdicts unresolved?
  ✗ Missing artifact for a triggered role → STOP, re-run that agent
  ✗ RED unresolved → STOP, escalate to user

NEXT — дальше по инструкции: STEP 4 — Developer sp1 (с условиями из YELLOW reports, если есть).

After completing this step, stop. The workflow loop will schedule the next step on the following iteration.
---

## Mandatory Final Step

If blocked on this step, replace `archive/team_artifacts/multi-query-expansion-v1/execution_contract.md` with a `BLOCKED` proof (last completed step, files touched, exact blocker). Do not leave only `STARTED` unless this is Step 1 and you are still working.

Intermediate steps must NOT write final delivery proof unless blocked — the closure step will update `archive/team_artifacts/multi-query-expansion-v1/execution_contract.md`.

Do not close the package manually. `scripts/workflow.py --loop --watch-contract` is watching progress and will run `run_autonomous.py --post-agent` when proof is substantive.
