# run_audit_chain_prompt

Updated: **2026-04-30**

Master prompt for running the full closed-packages audit chain:

1. Generate the main closed-package audit prompt.
2. Execute the generated audit prompt.
3. Verify or create audit group files.
4. Generate the standalone DoD coverage prompt.
5. Execute coverage group prompts safely.
6. Ensure reports, `_audit_raw.json`, and `coverage_dod_analysis.md` are in sync.

Use this when the goal is not just to create one prompt, but to drive the whole
audit workflow to a consistent audit state.

---

## How To Use

Paste into the target AI agent:

```text
Read doc/team_workflow/run_audit_chain_prompt.md
and execute the instructions.

TARGET_AGENT: <cursor_ai | codex | claude_code>
PERIOD: <YYYY-MM | YYYY-MM-DD..YYYY-MM-DD>
DEPTH: <dod_replay | index_only, default dod_replay>
SCOPE: <closed | closed,wip, default closed>
COVERAGE_FIX: <true | false, default true>
GROUP_MODE: <generate_only | execute_one | execute_all, default generate_only>
GROUP_ID: <optional group id, for execute_one; example group_01>
```

Recommended safe first pass:

```text
Read doc/team_workflow/run_audit_chain_prompt.md
and execute the instructions.

TARGET_AGENT: cursor_ai
PERIOD: 2026-04
DEPTH: dod_replay
SCOPE: closed
COVERAGE_FIX: true
GROUP_MODE: generate_only
```

Then run one group at a time:

```text
Read doc/team_workflow/run_audit_chain_prompt.md
and execute the instructions.

TARGET_AGENT: cursor_ai
PERIOD: 2026-04
DEPTH: dod_replay
SCOPE: closed
COVERAGE_FIX: true
GROUP_MODE: execute_one
GROUP_ID: group_01
```

---

## Instructions For The AI Agent

````text
Goal: execute the closed-package audit chain for hometutor until the selected
handoff point is genuinely complete.

Inputs:
  TARGET_AGENT
  PERIOD
  DEPTH
  SCOPE
  COVERAGE_FIX
  GROUP_MODE
  GROUP_ID

Defaults:
  DEPTH = dod_replay
  SCOPE = closed
  COVERAGE_FIX = true
  GROUP_MODE = generate_only

Derived paths:
  PERIOD_SLUG = filesystem-safe PERIOD
  AUDIT_PROMPT = doc/team_workflow/audit_prompt_${PERIOD_SLUG}_${TARGET_AGENT}.md
  GROUP_DIR = doc/team_workflow/audit_groups_${PERIOD_SLUG}_${TARGET_AGENT}
  COVERAGE_PROMPT = doc/team_workflow/audit_coverage_prompt_${PERIOD_SLUG}_${TARGET_AGENT}.md
  AUDIT_DIR = archive/team_artifacts/audit_${PERIOD_SLUG}
  RAW_JSON = archive/team_artifacts/audit_${PERIOD_SLUG}/_audit_raw.json
  COVERAGE_ANALYSIS = ${GROUP_DIR}/coverage_dod_analysis.md

Hard rules:
  - Use .\.venv\Scripts\python.exe for Python commands.
  - Do not change product code during coverage completion.
  - Coverage fixes may touch only tests/fixtures/eval data and package
    dod_commands metadata unless the called group prompt says narrower.
  - A markdown-only coverage report is incomplete audit state.
  - A raw JSON update with stale coverage_dod_analysis.md is incomplete audit state.
  - Do not run the full test suite unless explicitly requested.
  - Process coverage groups one at a time unless GROUP_MODE == execute_all.
  - If a new test exposes a product bug, stop for that package, record FAIL,
    and do not fix product code in this audit pass.

Preflight:
  1. Verify these files exist:
     - doc/team_workflow/generate_audit_closed_packages_prompt.md
     - doc/team_workflow/generate_audit_packages_coverage_prompt.md
     - doc/backlog_registry.yaml
     - doc/closed_iterations.md
     - doc/user_stories_index.json
     - doc/cjm.md
  2. If any are missing, report BLOCKERS and stop.

Phase 1 - Generate Main Audit Prompt:
  Read and execute:
    doc/team_workflow/generate_audit_closed_packages_prompt.md

  Use exactly:
    TARGET_AGENT: ${TARGET_AGENT}
    PERIOD: ${PERIOD}
    DEPTH: ${DEPTH}
    SCOPE: ${SCOPE}
    COVERAGE_FIX: ${COVERAGE_FIX}

  Completion criteria:
    - ${AUDIT_PROMPT} exists.
    - The prompt contains the selected period, scope, depth, target agent.
    - The prompt includes Step B DoD coverage/replay rules.

Phase 2 - Execute Main Audit Prompt:
  Execute ${AUDIT_PROMPT} in this same session unless the user explicitly asked
  only to generate prompts.

  Completion criteria:
    - ${AUDIT_DIR}/_audit_raw.json exists.
    - ${GROUP_DIR}/run_next_group_coverage_audit.md exists.
    - ${GROUP_DIR}/coverage_dod_analysis.md exists.
    - At least one ${GROUP_DIR}/group_*.md file exists.
    - Group files contain Coverage Completion Prompt, Raw JSON Update, and
      Coverage Analysis Refresh sections.

  If audit groups are missing:
    - Create them from the audit results by grouping related packages by wave
      and dependency.
    - Merge packages without a wave into one no-wave group.
    - Keep isolated packages as their own group only when not part of a wave,
      dependency component, or no-wave batch.
    - Write ${GROUP_DIR}/run_next_group_coverage_audit.md and ${GROUP_DIR}/group_*.md.
    - In ${GROUP_DIR}/run_next_group_coverage_audit.md, include a `## Next Action` block that points
      directly to the next unresolved group prompt by filename, not back to this
      master prompt. Example:
        Completed coverage groups: `group_01`.
        Recommended next safe run:
          Read ${GROUP_DIR}/group_02_<slug>.md
          and execute the instructions.
    - Update that `Next Action` after each completed group so it advances to
      the next numeric group file from ${GROUP_DIR}/run_next_group_coverage_audit.md.

Phase 3 - Generate Coverage Prompt:
  Read and execute:
    doc/team_workflow/generate_audit_packages_coverage_prompt.md

  Use exactly:
    TARGET_AGENT: ${TARGET_AGENT}
    PERIOD: ${PERIOD}
    SCOPE: ${SCOPE}

  Completion criteria:
    - ${COVERAGE_PROMPT} exists.
    - It references ${GROUP_DIR}/run_next_group_coverage_audit.md.
    - It references ${GROUP_DIR}/coverage_dod_analysis.md.
    - It requires updates to ${RAW_JSON}.
    - It requires refresh of ${COVERAGE_ANALYSIS}.

Phase 4 - Coverage Group Execution:
  If GROUP_MODE == generate_only:
    Stop after Phase 3 and report the exact next group prompt(s) to run.

  If GROUP_MODE == execute_one:
    - Require GROUP_ID.
    - Execute only ${GROUP_DIR}/${GROUP_ID}_*.md or the exact matching group file.
    - Do not process other groups.

  If GROUP_MODE == execute_all:
    - Process groups in numeric order from ${GROUP_DIR}/run_next_group_coverage_audit.md.
    - After each group, verify the report, ${RAW_JSON}, and ${COVERAGE_ANALYSIS}
      before starting the next group.
    - Stop on the first product-code blocker or unresolved FAIL/STALE that
      requires human review.

  Per completed group, verify:
    - ${AUDIT_DIR}/group_<NN>_dod_coverage_report.md exists.
    - ${RAW_JSON} contains coverage_groups["group_<NN>"].
    - summary.coverage_groups_completed and coverage package counters are updated.
    - ${COVERAGE_ANALYSIS} no longer lists PASS packages from that group as open gaps.
    - Only focused test commands were run and recorded.

Phase 5 - Final Consistency Check:
  Run:

  ```powershell
  .\.venv\Scripts\python.exe scripts/backlog_registry_lint.py
  .\.venv\Scripts\python.exe scripts/lint_agent_prompts.py
  .\.venv\Scripts\python.exe scripts/check_audit_chain_state.py --period ${PERIOD} --target-agent ${TARGET_AGENT} --write-next-action --write-summary --write-raw-check --json-out archive/team_artifacts/audit_${PERIOD_SLUG}/audit_chain_state.json
  ```

  Do not run full pytest unless explicitly requested.

Output format:

  AUDIT CHAIN RESULT:
  <PASS | PARTIAL | BLOCKED>

  GENERATED PROMPTS:
  - Main audit prompt: <path + exists?>
  - Coverage prompt: <path + exists?>

  GROUPS:
  - Group dir: <path + exists?>
  - Groups found: <N>
  - Groups completed this run: <ids>
  - Next group to run: <id or none>

  ARTIFACTS:
  - Raw JSON: <path + coverage_groups summary>
  - Coverage analysis: <path + whether refreshed>
  - Reports: <paths>

  COMMANDS RUN:
  <focused commands only>

  BLOCKERS:
  <only if something failed or needs human review>

  NEXT STEP:
  <one concrete next action>
````

---

## Notes

- `GROUP_MODE=generate_only` is the safest master mode for a first pass. It
  prepares all prompts and group files without mutating tests.
  - `GROUP_MODE=execute_one` is the preferred mode for real coverage completion.
- `GROUP_MODE=execute_all` is allowed only when the operator accepts the broader
  write surface across many groups.
- `scripts/check_audit_chain_state.py --write-next-action --write-summary --write-raw-check --json-out ...`
  keeps the group runbook pointed at the next unresolved group, refreshes
  `archive/team_artifacts/audit_${PERIOD_SLUG}/final_coverage_audit_summary.md`,
  writes `archive/team_artifacts/audit_${PERIOD_SLUG}/README.md`, and records
  `last_chain_check` in `_audit_raw.json`.
