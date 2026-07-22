# Token-budget audit — fixes & evidence (2026-07-23)

**Scope:** address the 2026-07 audit of `kilo_prompt_content_budget_breakthrough`
(Log 2). Code/data defects fixed in this repo; live A/B is a follow-up (needs
Cursor + relay + DeepSeek running).

> Honest labels (audit fix): the numbers below are a **3-request instrumentation
> sample** from `logs/kilo_relay.jsonl`, **not** a measured before/after A/B.
> They rank pollution; they do not prove the policy edits lowered cost yet.

---

## What was broken → fixed

| # | Audit finding | Fix |
|---|---|---|
| 1 | `token_safety_registry.json` invalid JSON — dropped `doc/adr.md` key merged metadata into `files` (`Extra data: line 303`) | Restored the key; registry parses; **50 entries** |
| 2 | Registry sizes/tokens stale right after edits | Regenerated deterministically; **~30 local files were stale**, not just AGENTS/CLAUDE |
| 3 | No test validated the registry | Added `test_registry_structure_no_dropped_keys` + `test_registry_metadata_fresh_for_local_files` |
| 4 | `CLAUDE.md` contradiction: forbids full-read of `conventions_architecture/reference` but example says "(full)" | Example rewritten to section-only; explicit "this is NOT an exception" note |
| 5 | Report sums 3 requests but reads like one prompt | Added `per_request` avg/median/min/max + "AGGREGATE sums" labels |
| 6 | `--last 40` sliced raw rows, not chat rows | `_load_records` no longer truncates; `build_report(records, last)` filters chat **then** slices |
| 9 | Did new always-on rules inflate every prompt? | Now measurable: `rules` fragment ≈ **1.8k tok/request** (see below) |

**Root cause of #1–#3:** the registry was hand-edited. Now
`scripts/measure_token_registry.py` is **merge-safe** — it re-measures the 33
DOCS_ROOT files and **preserves** the 17 CODE_ROOT `app/*` / `requirements.txt`
entries (which cannot be measured from this tree) instead of zeroing them.
Regenerate with:

```bash
.venv/Scripts/python.exe scripts/measure_token_registry.py --write
```

---

## Instrumentation sample (3 chat requests, `--last 40`)

```
records=121  chat_with_stats=3
per request:  message_chars avg=34,575  median=34,575  (n=3)
              messages_count avg=4       (n=3)
top kinds (AGGREGATE over 3 req):  tool_result 81,180  system 22,164
top fragments (AGGREGATE):          rules 21,960  available_skills 204
```

Per-request (÷3) read: **~8.6k tok/prompt** total; `tool_result` ≈6.8k tok/req
leader; `rules` always-on tax ≈**1.8k tok/req**; `system` ≈1.8k tok/req.
(`prompt_tokens n=0` — these old records predate usage capture.)

---

## Order-of-magnitude levers (ranked by savings × 1/quality-risk)

1. **New chat when `msgs≫15` / `in` hard.** Dominant lever: a long session was
   >100k `in`; a fresh chat drops the message tail (~250 msgs) to tens of k.
   No quality loss. This is where the *order of magnitude* actually comes from.
2. **Never full-read heavy SSoT.** Registry now flags the real giants:
   `backlog_registry.yaml` ~123k tok, `changelog.md` ~67k, `closed_iterations.md`
   ~56k, `epochs/e4.md` ~23k, `adr.md` ~22k. One accidental full-read ≈ a whole
   budget. `check_readset.py` + `full_read:"forbidden"` enforce section/grep reads.
3. **`cloud_budget` strip of operational XML** (`rules`, `available_skills`,
   `mcp_*`): ~1.8k tok/req always-on, recurring every turn.
4. **Tool-result discipline** — biggest single kind; prune/summarize stale
   `tool_result` history to cap `msgs` growth.

The 10× target = **new chat + no full-read of heavy SSoT**, not any single relay
strip.

---

## Not done here (needs live infra) — follow-ups

- Real A/B: fresh chat, identical 5–15 tasks, compare `prompt_tokens` before/after
  policy. Only this can claim "breakthrough."
- Re-run report **with usage capture** so `per_request.prompt_tokens` is populated.
- CODE_ROOT `D:\Projects\hometutor\{AGENTS,CLAUDE}.md`: apply the same full-read
  contradiction fix if those copies are SSoT for agents there (separate repo —
  not edited without sign-off).

## DoD

- [x] `pytest tests/test_token_registry.py tests/test_kilo_prompt_stats.py tests/test_kilo_proxy_relay.py` — **80 passed**
- [x] Registry valid JSON, 50 entries, no zeroed/CODE_ROOT loss
- [x] `lint_agent_prompts.py` OK
