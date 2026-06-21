# Runbook — next coverage group

Period slug: `2026-05-04__2026-05-10`  
Target agent: `cursor_ai`

## Completed coverage groups

`group_01`, `group_02`

## Next Action

Completed coverage groups: `group_01`, `group_02`.

All groups completed.

Recommended final run:

```powershell
.\.venv\Scripts\python.exe scripts/check_audit_chain_state.py --period 2026-05-04..2026-05-10 --target-agent cursor_ai --write-next-action --write-summary --write-raw-check --json-out archive/team_artifacts/audit_2026-05-04__2026-05-10/audit_chain_state.json
```

After each group, run:

```powershell
.\.venv\Scripts\python.exe scripts/check_audit_chain_state.py --period 2026-05-04..2026-05-10 --target-agent cursor_ai --write-next-action --write-summary --write-raw-check --json-out archive/team_artifacts/audit_2026-05-04__2026-05-10/audit_chain_state.json
```

The next group is safe to start only after the check is PASS or any reported
FAIL is intentionally resolved.

## References

- Main audit prompt: `archive/doc_team_workflow/audit_prompt_2026-05-04__2026-05-10_cursor_ai.md`
- Coverage master prompt: `archive/doc_team_workflow/audit_coverage_prompt_2026-05-04__2026-05-10_cursor_ai.md`
- Raw JSON: `archive/team_artifacts/audit_2026-05-04__2026-05-10/_audit_raw.json`
