# Runbook — Epic 20 SSR DoD coverage (codex)

- **Audit directory:** `archive/team_artifacts/audit_epic20-smart-study-router/`
- **Raw JSON:** `archive/team_artifacts/audit_epic20-smart-study-router/_audit_raw.json`
- **Coverage analysis:** `doc/team_workflow/audit_groups_epic20-smart-study-router_codex/coverage_dod_analysis.md`
- **Master coverage prompt:** `doc/team_workflow/archive/audit_coverage_prompt_epic20-smart-study-router_codex.md`

## Next Action

Completed coverage groups: `group_01`, `group_02`, `group_03`, `group_04`.

All groups completed.

Recommended final run:

```powershell
.\.venv\Scripts\python.exe scripts/check_audit_chain_state.py --period epic20-smart-study-router --target-agent codex --write-next-action --write-summary --write-raw-check --json-out archive/team_artifacts/audit_epic20-smart-study-router/audit_chain_state.json
```

After each group, run:

```powershell
.\.venv\Scripts\python.exe scripts/check_audit_chain_state.py --period epic20-smart-study-router --target-agent codex --write-next-action --write-summary --write-raw-check --json-out archive/team_artifacts/audit_epic20-smart-study-router/audit_chain_state.json
```

The next group is safe to start only after the check is PASS or any reported
FAIL is intentionally resolved.
