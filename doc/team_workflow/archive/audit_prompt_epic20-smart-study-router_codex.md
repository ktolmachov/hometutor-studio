# AUDIT PROMPT — Epic 20 Smart Study Router (narrow scope)

**Period label:** `epic20-smart-study-router` (not calendar — epic-scoped audit)  
**Epic index:** [`doc/smart_study_router.md`](../../smart_study_router.md)  
**Target agent:** OpenAI Codex CLI (see [`agent_adapter_codex.md`](agent_adapter_codex.md))  
**DEPTH:** `dod_replay`  
**SCOPE:** `closed` (only SSR delivery packages listed below)  
**COVERAGE_FIX:** `true` (completion via group prompts + [`audit_coverage_prompt_epic20-smart-study-router_codex.md`](audit_coverage_prompt_epic20-smart-study-router_codex.md))

Run steps A → D in order.

---

## Story + package scope (Epic 20 only)

| US | Primary `covered_by` (US index) | Related delivery epochs |
|---|---|---|
| US-20.1 | `epoch-smart-study-router-surface-parity` | Card, policies, trust, a11y, surface-parity |
| US-20.2 | `epoch-smart-study-router-card` | ↑ |
| US-20.3–US-20.5 | `epoch-smart-study-router-core-policies` | ↑ |
| US-20.6 | `epoch-smart-study-router-accessibility-harness` | ↑ |
| US-20.7 | `epoch-ssr-next-contrastive-explanations` | Next-level trust wave |
| US-20.8 | `epoch-ssr-next-confidence-ledger` | ↑ |
| US-20.9 | `epoch-ssr-next-learning-debt-queue` | Pedagogy wave |
| US-20.10 | `epoch-ssr-next-steering-toggles` | ↑ |
| US-20.11 | `epoch-ssr-next-outcome-receipts` | Retention / accessibility wave |
| US-20.12 | `epoch-ssr-next-quiet-mode` | ↑ |

**Packages to audit (10, all `closed` in registry — только те, что встречаются как `covered_by` для US-20.1…US-20.12):**

1. `epoch-smart-study-router-card`
2. `epoch-smart-study-router-core-policies`
3. `epoch-smart-study-router-accessibility-harness`
4. `epoch-smart-study-router-surface-parity`
5. `epoch-ssr-next-contrastive-explanations`
6. `epoch-ssr-next-confidence-ledger`
7. `epoch-ssr-next-learning-debt-queue`
8. `epoch-ssr-next-steering-toggles`
9. `epoch-ssr-next-outcome-receipts`
10. `epoch-ssr-next-quiet-mode`

**Вне этого аудита (не US-20.x):** `epoch-smart-study-router-trust-control` остаётся отдельным закрытым пакетом SSR foundation, но **не входит** в сверку US-20.1…US-20.12 по `doc/user_stories_index.json`.

Cross-check sources for each US/package:

- `doc/user_stories.md` Epic 20 table
- `doc/user_stories/us-20.1.md` … `us-20.12.md` (frontmatter + acceptance)
- `doc/backlog_registry.yaml` — item `status`, `dod_commands`, `user_stories`, `blocks`
- `doc/closed_iterations.md` — `### <package_id> — YYYY-MM-DD`
- `doc/user_stories_index.json`
- Implementation map: **`doc/smart_study_router.md` § Архитектура / модульная карта**

---

## STEP A — INDEX CONSISTENCY

Per package:

- **Registry:** row exists; `status: closed`.
- **closed_iterations:** heading present with closure date compatible with SSR wave (May 2026 deliveries).
- **US index:** every `user_stories` on the registry row agrees with stories whose `covered_by` equals that package; `status: closed`; `closed_date` present.
- **CJM:** `grep` `US-20.` and package id against `doc/cjm.md`; MoT / narrative alignment (SSR cross-loop moments).

Failures → `INDEX_FAIL`, enter Step C for that package; skip Step B.

---

## STEP B — DoD COVERAGE + REPLAY (`dod_replay`)

**COVERAGE_FIX true:** classify GAP_* vs COVERED_* per package; remediation only via coverage group prompts (`tests/**`, e2e, `dod_commands` metadata) — never `app/**` in audit pass without separate approval.

Minimum intent (SSR):

- **Unit/policy:** deterministic router + card behavior — [`tests/test_smart_study_router.py`](../../tests/test_smart_study_router.py), [`tests/test_ui_helpers.py`](../../tests/test_ui_helpers.py) (plus any paths listed in registry `blocks`/`exit_artifact`).
- **Learner-visible surfaces:** Playwright smoke — registry `dod_commands` typically include  
  `npm run test:e2e:smoke -- tests/e2e/smart_study_router.spec.ts`

**Replay rules:**

1. Run every `dod_commands` entry for the package exactly as written (focused runs; no full `pytest`).
2. Do not assume pass — record stdout tail and exit codes in `archive/team_artifacts/audit_epic20-smart-study-router/_audit_raw.json` / group reports after group execution.

If replay fails → `dod_replay`: `FAIL`; if only coverage gap without replay yet → defer to **`audit_groups_epic20-smart-study-router_codex/group_*.md`**.

---

## STEP C — REVERT PROCEDURE

Only after confirmed INDEX_FAIL or DoD FAIL. Follow [`generate_audit_closed_packages_prompt.md`](generate_audit_closed_packages_prompt.md) § Step C checklist (registry, `closed_iterations.md`, US frontmatter, CJM, changelog, sync hooks). **Never** reopen from this prompt without owner confirmation documented in `_audit_raw.json`.

---

## STEP D — WRITE ARTIFACTS

Update / refresh:

1. `archive/team_artifacts/audit_epic20-smart-study-router/_audit_raw.json`  
   — must include **`story_results`** entries for **US-20.1 … US-20.12** and **`results`** rows for **all 10 packages** above (Epic 20 `covered_by` only).
2. `doc/team_workflow/audit_groups_epic20-smart-study-router_codex/coverage_dod_analysis.md`
3. `doc/team_workflow/audit_groups_epic20-smart-study-router_codex/run_next_group_coverage_audit.md` — **`## Next Action`** must point at the **next numeric `group_*.md` file path**, not this master prompt.

Grouping (dependency-friendly):

- **group_01** — foundation wave (`epoch-smart-study-router-card`, `*-core-policies`, `*-accessibility-harness`)
- **group_02** — surface parity (`epoch-smart-study-router-surface-parity`)
- **group_03** — trust / explainability (`epoch-ssr-next-contrastive-explanations`, `epoch-ssr-next-confidence-ledger`)
- **group_04** — pedagogy + retention (`epoch-ssr-next-learning-debt-queue`, `epoch-ssr-next-steering-toggles`, `epoch-ssr-next-outcome-receipts`, `epoch-ssr-next-quiet-mode`)

Codex tooling: shell read via `grep` / `head` / `sed -n`; write via here-doc per adapter.
