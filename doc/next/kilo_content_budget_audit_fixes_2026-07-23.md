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
| 6 | `--last 40` sliced raw rows, not chat rows | `collect_chat_records()` streams the JSONL, filters to chat rows with `content_stats`, and keeps only the last N of *those* via `deque(maxlen=N)`; `main()` calls it then `build_report(chat_records, last=None, records_total=...)` |
| 9 | Did new always-on rules inflate every prompt? | Now measurable: `rules` fragment ≈ **1.8k tok/request** (see below) |
| — | (this round) old `_load_records(path, last)` was dead code with a broken contract — declared `last` but ignored it | Removed; nothing called it |
| — | (this round) `test_check_readset_merges_registry` had an operator-precedence bug: `A and B or C` picked any existing file, not only forbidden ones | Fixed to `A and (B or C)` |
| — | (this round) negative `--last` silently meant "all" | `argparse` now rejects `--last < 0` with a usage error (exit 2) |

**Provenance of #1 (git-verified in THIS repo — reproduce yourself, don't take
my word).** The dropped-key corruption entered in **commit 133 (`567e43c`)**;
`131 (628841c)` and `132 (9c7b755)` both parse valid, `134 (b95abcd)` is the fix:

```bash
git show 567e43c:doc/token_safety_registry.json | python -m json.tool  # -> "Extra data: line 303"
git show b95abcd:doc/token_safety_registry.json  | python -m json.tool  # -> parses clean
git show --stat 567e43c   # touched AGENTS.md, CLAUDE.md, doc/token_safety_registry.json (+43/-?), two doc/next reports
git show --stat b95abcd   # touched CLAUDE.md, doc/token_safety_registry.json, both scripts (the actual fix)
```

This is one commit dropping the `doc/adr.md` key — consistent with an in-place
hand-edit, though the exact mechanism (manual edit vs. a bad tool run) isn't
provable from history alone. Either way the guard below makes the cause moot.

**Fix that removes the whole class of bug.** `scripts/measure_token_registry.py`
is now **merge-safe** — it re-measures the 33 DOCS_ROOT files and **preserves**
the 17 CODE_ROOT `app/*` / `requirements.txt` entries (which cannot be measured
from this tree) instead of zeroing them. The registry is now *generated*, not
hand-edited; regenerate + validate with:

```bash
.venv/Scripts/python.exe scripts/measure_token_registry.py --write
.venv/Scripts/python.exe -m json.tool doc/token_safety_registry.json >/dev/null && echo VALID
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

## Levers toward the 10× *target* (ranked by savings × 1/quality-risk)

> 10× is a **target hypothesis**, not a measured result. It is plausible from the
> gap between a >100k-token long session and an ~8.6k-token fresh turn, but those
> are different tasks/lengths/configs — see "Not yet proven" below.

1. **New chat when `msgs≫15` / `in` hard — *with a compact handoff*.** Dominant
   lever: a long session was >100k `in`; a fresh chat drops the message tail
   (~250 msgs) to tens of k. **Not free:** a fresh chat loses decision history,
   prior tool results, task constraints and any open tool-loop. Quality holds
   **only if** a short handoff-summary (goal, constraints, done-so-far, next step)
   is carried over. This is where the *order of magnitude* comes from.
2. **Never full-read heavy SSoT.** Registry now flags the real giants:
   `backlog_registry.yaml` ~123k tok, `changelog.md` ~67k, `closed_iterations.md`
   ~56k, `epochs/e4.md` ~23k, `adr.md` ~22k. One accidental full-read ≈ a whole
   budget. `check_readset.py` + `full_read:"forbidden"` enforce section/grep reads.
3. **Operational-XML tax vs. actual saving — do not conflate.** Measured:
   `rules` ≈**1.8k tok/req** constant tax. But current `cloud_budget` only saves
   ≈**10 tok/req** — it does *not* strip `rules`. Removing `rules` needs a
   **separate opt-in strip flag**, and that carries a policy-loss risk, so it is
   **not** a zero-risk lever. Three distinct numbers:
   - measured tax: `rules` ≈1.8k tok/req
   - current `cloud_budget` saving: ≈10 tok/req
   - potential saving *if* `rules` strip is enabled: ≈1.8k tok/req (policy risk)
4. **Tool-result discipline** — biggest single kind; prune/summarize stale
   `tool_result` history to cap `msgs` growth.

The target = **new chat (+handoff) + no full-read of heavy SSoT**, not any single
relay strip.

---

## Not yet proven — follow-ups (needs live infra)

- **10× is unproven.** Real A/B required: fresh chat, identical 5–15 tasks, same
  config, compare real `prompt_tokens` before/after. The 3-request sample uses
  `chars/4` heuristics and has `prompt_tokens n=0`; it ranks pollution, it does
  not measure the effect of the policy edits.
- Re-run report **with usage capture** so `per_request.prompt_tokens` is populated.
- CODE_ROOT `D:\Projects\hometutor\{AGENTS,CLAUDE}.md`: apply the same full-read
  contradiction fix if those copies are SSoT for agents there (separate repo —
  not edited without sign-off).

## DoD (reproducible in this repo)

- [x] `pytest tests/test_token_registry.py tests/test_kilo_prompt_stats.py tests/test_kilo_proxy_relay.py` — **88 passed** (13 registry + 14 stats + 61 relay)
- [x] Registry valid JSON, 50 entries, `doc/adr.md` present, no zeroed/CODE_ROOT loss — `python -m json.tool doc/token_safety_registry.json`
- [x] `collect_chat_records()` covered directly: non-chat filtering, `deque(maxlen=N)` tail-only-of-chat behavior, `last=None/0`, malformed JSON / blank lines / non-dict rows, missing file, negative `--last` rejected by argparse
- [x] `per_request` avg/median/min/max covered directly (`test_per_request_summary_stats_avg_median_min_max`)
- [x] Freshness/structure caught by `pytest tests/ -q` — that is exactly what [`.github/workflows/test.yml`](../../.github/workflows/test.yml) runs, so a future dropped key or stale size fails that workflow, not "CI" in the abstract
- [x] `lint_agent_prompts.py` OK
- [ ] **10× effect** — NOT closed; needs the live A/B above

**Reproduce evidence:**

```bash
.venv/Scripts/python.exe -m pytest tests/test_token_registry.py tests/test_kilo_prompt_stats.py tests/test_kilo_proxy_relay.py -q
.venv/Scripts/python.exe -m json.tool doc/token_safety_registry.json >/dev/null && echo "registry VALID"
.venv/Scripts/python.exe scripts/kilo_prompt_content_report.py --last 40   # dry-run, no --json-out
.venv/Scripts/python.exe scripts/kilo_prompt_content_report.py --last -1  # rejected: "--last must be >= 0"
git show 567e43c:doc/token_safety_registry.json | python -m json.tool     # broken (commit 133)
git show b95abcd:doc/token_safety_registry.json  | python -m json.tool    # fixed   (commit 134)
```
