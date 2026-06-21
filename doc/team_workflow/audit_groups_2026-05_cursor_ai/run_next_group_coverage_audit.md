# Run next group — audit 2026-05 / cursor_ai

## Next Action

Completed coverage groups: `group_01`, `group_02`, `group_03`.

Recommended next safe run:

```text
Read doc/team_workflow/audit_groups_2026-05_cursor_ai/group_04_wave-home-mode-v2.md
and execute the instructions.
```

After each group, run:

```powershell
.\.venv\Scripts\python.exe scripts/check_audit_chain_state.py --period 2026-05 --target-agent cursor_ai --write-next-action --write-summary --write-raw-check --json-out archive/team_artifacts/audit_2026-05/audit_chain_state.json
```

The next group is safe to start only after the check is PASS or any reported
FAIL is intentionally resolved.
