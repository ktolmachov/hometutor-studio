# Coverage / DoD analysis — Epic 20 Smart Study Router

**Audit period label:** `epic20-smart-study-router`  
**Agent:** `codex`  
**Chain mode:** Epic 20 coverage **PASS** — `group_01`–`group_04` (2026-05-09); дальнейшие шаги — только поддержание DoD / `check_audit_chain_state` при изменениях.  
**Evidence cut:** pytest `tests/test_smart_study_router.py` + `tests/test_ui_helpers.py`; Playwright `npm run test:e2e:smoke -- tests/e2e/smart_study_router.spec.ts`.

---

## User story rollup (acceptance ↔ evidence)

| US | Registry `covered_by` | Status index | Implementation pointers (`smart_study_router.md`) | pytest / policy signals | Playwright SSR spec | Coverage verdict (this pass) |
|:--|:--|:--:|:--|:--:|:--:|:--|
| US-20.1 | `epoch-smart-study-router-surface-parity` | closed | `resume_cards`, `main.py` surfaces | ✅ | ✅ group_02 | **PASS** |
| US-20.2 | `epoch-smart-study-router-card` | closed | `adaptive_plan_card.py` | ✅ | ✅ group_01 | **PASS** |
| US-20.3 | `epoch-smart-study-router-core-policies` | closed | policy ordering / hints | ✅ | ✅ group_01 | **PASS** |
| US-20.4 | `epoch-smart-study-router-core-policies` | closed | weak-concept / recovery routing | ✅ | ✅ group_01 | **PASS** |
| US-20.5 | `epoch-smart-study-router-core-policies` | closed | post-answer runway | ✅ | ✅ group_01 | **PASS** |
| US-20.6 | `epoch-smart-study-router-accessibility-harness` | closed | a11y / entry points preserved | ✅ | ✅ group_01 | **PASS** |
| US-20.7 | `epoch-ssr-next-contrastive-explanations` | closed | contrastive explanation strings | ✅ | ✅ group_03 | **PASS** |
| US-20.8 | `epoch-ssr-next-confidence-ledger` | closed | evidence ledger | ✅ | ✅ group_03 | **PASS** |
| US-20.9 | `epoch-ssr-next-learning-debt-queue` | closed | pedagogical labels / debt framing | ✅ | ✅ group_04 (pedagogy marker e2e) | **PASS** |
| US-20.10 | `epoch-ssr-next-steering-toggles` | closed | `user_state_core` steering | ✅ | ✅ group_04 (steering strip e2e) | **PASS** |
| US-20.11 | `epoch-ssr-next-outcome-receipts` | closed | outcome receipts surface | ✅ | ✅ pytest + smoke spec run | **PASS** |
| US-20.12 | `epoch-ssr-next-quiet-mode` | closed | quiet mode routing | ✅ | ✅ group_04 (quiet smoke) | **PASS** |

Legend: ✅ replayed / strongly covered by cited tests this session; ⚪ listed in registry `dod_commands` but not replayed yet in this audit chain mode.

---

## Audit finding (CJM ↔ US-20)

- **`doc/cjm.md`** — в MoT-таблице **нет** ссылок `us-20.*` / `US-20.*`; возможности SSR описаны в блоке «Smart Study Router opportunities» текстом. **Follow-up (док):** при желании добавить явные ссылки на US-20.x для трассируемости (вне `GROUP_MODE=generate_only` для тестов).

---

## Package-level coverage (SSoT cross-check: строка пакета должна содержать `| PASS |` при закрытии группы)

Только пакеты с `covered_by` для US-20.1…US-20.12 (**10**).  
`epoch-smart-study-router-trust-control` — отдельный closed SSR-пакет, **не** входит в Epic 20 US-rollup.

| Package | Linked US | Unit/UI helper coverage | Playwright `smart_study_router.spec.ts` | Notes | Verdict |
|---|---|:--:|:--:|---|:-:|
| `epoch-smart-study-router-card` | US-20.2 + shared | ✅ | ✅ | group_01 DoD replay | PASS |
| `epoch-smart-study-router-core-policies` | US-20.3–20.5 | ✅ | ✅ | e2e `cards_due` + pytest policies | PASS |
| `epoch-smart-study-router-accessibility-harness` | US-20.6 | ✅ | ✅ | e2e region / reason / contrast / caption | PASS |
| `epoch-smart-study-router-surface-parity` | US-20.1 (table) | ✅ | ✅ | parity hint e2e | PASS |
| `epoch-ssr-next-contrastive-explanations` | US-20.7 | ✅ | ✅ | contrastive e2e + full smoke spec | PASS |
| `epoch-ssr-next-confidence-ledger` | US-20.8 | ✅ | ✅ | evidence ledger e2e + full smoke spec | PASS |
| `epoch-ssr-next-learning-debt-queue` | US-20.9 | ✅ | ✅ | pedagogy `e2e-ssr-route-pedagogy` in cards_due | PASS |
| `epoch-ssr-next-steering-toggles` | US-20.10 | ✅ | ✅ | «Локальный руль» visible when cards_due | PASS |
| `epoch-ssr-next-outcome-receipts` | US-20.11 | ✅ | ✅ | pytest receipt lines; smoke suite replay | PASS |
| `epoch-ssr-next-quiet-mode` | US-20.12 | ✅ | ✅ | quiet mode e2e | PASS |

---

## Sync / closure (documentation)

- **`doc/user_stories.md`** — Epic 20 rows: all `closed` with `covered_by` aligned to table above ✅  
- **`doc/user_stories_index.json`** — US-20.1–US-20.12 `closed` + `closed_date` 2026-05-06 / 2026-05-08 ✅  
- **`doc/backlog_registry.yaml`** — **10** epic-пакетов выше + `trust-control` отдельно (`closed`) ✅  
- **`doc/closed_iterations.md`** — headings for each epic package (2026-05-06 / 2026-05-08) ✅  
- **`doc/smart_study_router.md`** — states full delivery US-20.1–US-20.12; ключевые пути в репо проверены ✅  

**Finding:** цепочка `group_01`–`group_04` завершена; US-20.1–US-20.12 в таблице выше — **PASS** по согласованному DoD (см. `group_04_dod_coverage_report.md` для US-20.11: pytest-first).

---

## Follow-up instruction

При изменениях SSR перезапускать узкий DoD: pytest SSR bundle + `npm run test:e2e:smoke -- tests/e2e/smart_study_router.spec.ts` + `backlog_registry_lint.py --strict --sync-from-index --write-sync`; при закрытии связанных пакетов — `scripts/check_audit_chain_state.py` с флагами записи summary/raw.
