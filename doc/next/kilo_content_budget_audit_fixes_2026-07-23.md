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
| 9 | Did new always-on rules inflate every prompt? | Measured (see below) — the fragment responsible for the tax **changed between samples**, called out explicitly rather than papered over |
| — | (this round) old `_load_records(path, last)` was dead code with a broken contract — declared `last` but ignored it | Removed; nothing called it |
| — | (this round) `test_check_readset_merges_registry` had an operator-precedence bug: `A and B or C` picked any existing file, not only forbidden ones | Fixed to `A and (B or C)` |
| — | (this round) negative `--last` silently meant "all" | `argparse` now rejects `--last < 0` with a usage error (exit 2) |
| — | (this round) missing/mistyped `--log` path reported as "no content_stats yet — restart relay" (misleading for a typo) | CLI now checks `--log` existence first and exits 3 with a distinct "log file not found" message |
| — | (this round) malformed JSON / non-dict JSON lines vanished from the report with no trace, so a partially corrupted log could look externally normal | `collect_chat_records()` now returns `lines_total` / `dict_records` / `invalid_json` / `non_dict_records` / `chat_with_stats`; `render_text` prints them and flags a non-zero `invalid_json`/`non_dict_records` |
| — | (this round) `json.tool` only proves syntax validity, not that specific entries/counts survived a regen | Added `test_registry_no_zeroed_or_missing_regression_entries`: asserts `doc/adr.md` present, CODE_ROOT samples non-zero, no unflagged zero-byte entries |

**Provenance of #1 (git-verified in THIS repo — reproduce yourself, don't take
my word).** The dropped-key corruption entered in **commit 133 (`567e43c`)**;
commits 131/132/134 all parse valid:

```bash
git show 628841c:doc/token_safety_registry.json | python -m json.tool  # 131 -> parses clean
git show 9c7b755:doc/token_safety_registry.json  | python -m json.tool  # 132 -> parses clean
git show 567e43c:doc/token_safety_registry.json | python -m json.tool  # 133 -> "Extra data: line 303 column 1"
git show b95abcd:doc/token_safety_registry.json  | python -m json.tool  # 134 -> parses clean (the fix)
git diff --stat 567e43c^ 567e43c -- doc/token_safety_registry.json  # 1 file changed, 33 insertions(+), 10 deletions(-)
git diff --stat b95abcd^ b95abcd -- doc/token_safety_registry.json  # 1 file changed, 93 insertions(+), 92 deletions(-)
```

Commit 133 also touched `AGENTS.md`, `CLAUDE.md`, `doc/kilo_proxy_relay.md`, and
two `doc/next/` reports in the same commit as the registry edit — consistent
with an in-place hand-edit across several docs in one pass, though the exact
mechanism (manual edit vs. a bad tool run) isn't provable from history alone.
Either way the guard below makes the cause moot.

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

## Instrumentation sample (`--last 40`, captured this round)

> The log keeps growing from real usage between rounds — this replaces the
> previous round's 3-request sample with a larger, fresher one. Numbers **will
> differ again** on the next capture; re-run the command below rather than
> trusting this snapshot as a constant.

```
records=170  chat_with_stats=40
per request:  prompt_tokens  n=40 avg=36,602  median=36,029  min=17,602  max=54,705  (REAL usage.prompt_tokens)
              message_chars  n=40 avg=114,625 median=113,788 min=52,104  max=173,774 (chars/4 heuristic)
top kinds (AGGREGATE over 40 req):  tool_result ~698k tok   system ~219k tok   assistant_tool_calls ~168k tok
top fragments (AGGREGATE over 40 req): available_skills ~6.2k tok  — `rules` absent from this sample
top paths (AGGREGATE, ±200-char window heuristic): AGENTS.md hits=40 (~61k tok)  CLAUDE.md hits=40 (~20k tok)
```

**Correction vs. last round:** the earlier 3-request sample showed `rules`
≈1.8k tok/req; this 40-request sample with **real `prompt_tokens`** (not the
`chars/4` heuristic) shows no `rules` fragment at all — only `available_skills`
(≈155 tok/req: 24,880 chars ÷ 40 req ÷ 4). Reporting the earlier number without
this update would have kept a stale, now-contradicted claim in place. Whether
`rules` is absent because `cloud_budget` strips it in this session or because
these particular requests didn't carry it isn't determined by this data alone —
flagged as an open question below, not asserted either way.

AGENTS.md/CLAUDE.md path mentions appear in **every one of the 40 requests**
(`hits=40`) — the most robust finding in this sample, though the char count is
a ±200-char window around each mention, not the file's raw size (see the
report's own caveat).

---

## Levers toward the 10× *target* (ranked by savings × 1/quality-risk)

> 10× is a **target hypothesis**, not a measured result. This round's real
> `prompt_tokens` (avg ≈36.6k/req across 40 requests) sit well under the
> historical >100k-token long-session figure, which is encouraging, but a
> single session's running average is not a controlled before/after — see
> "Not yet proven" below.

1. **New chat when `msgs≫15` / `in` hard — *with a compact handoff*.** Dominant
   lever: a long session was >100k `in`; a fresh chat drops the message tail
   to tens of k. **Not free:** a fresh chat loses decision history, prior tool
   results, task constraints and any open tool-loop. Quality holds **only if**
   a short handoff-summary (goal, constraints, done-so-far, next step) is
   carried over. This is where the *order of magnitude* is expected to come from.
2. **Never full-read heavy SSoT.** Registry now flags the real giants:
   `backlog_registry.yaml` ~123k tok, `changelog.md` ~67k, `closed_iterations.md`
   ~56k, `epochs/e4.md` ~23k, `adr.md` ~22k. One accidental full-read ≈ a whole
   budget. `check_readset.py` + `full_read:"forbidden"` enforce section/grep reads.
3. **Operational-XML tax — reported as an open, moving target, not a fixed
   number.** Last round's small sample (3 req) measured `rules` ≈1.8k tok/req;
   this round's larger sample (40 req) shows `rules` absent and
   `available_skills` ≈155 tok/req instead (see correction above). Whatever the
   current tax is, current `cloud_budget` saves only ≈10 tok/req — it does not
   target these fragments. A dedicated strip needs a **separate opt-in flag**
   and carries a policy-loss risk, so treat it as a candidate to measure per
   session, not a settled ≈1.8k tok/req constant.
4. **Tool-result discipline** — biggest single kind (~698k tok aggregate / 40
   req ≈ 17.5k tok/req average in this sample); prune/summarize stale
   `tool_result` history to cap `msgs` growth.

The target = **new chat (+handoff) + no full-read of heavy SSoT**, not any single
relay strip.

---

## Not yet proven — follow-ups (needs live infra)

- **10× is unproven.** This round's `prompt_tokens` are now real (usage-reported,
  not `chars/4`), which closes the earlier "n=0" gap — but a running average from
  one ongoing session is still not a controlled A/B. Real A/B still required:
  fresh chat, identical 5–15 tasks, same config, compare real `prompt_tokens`
  before/after the policy edits specifically (not before/after in time, which
  conflates the edits with normal task-to-task variance).
- CODE_ROOT `D:\Projects\hometutor\{AGENTS,CLAUDE}.md`: apply the same full-read
  contradiction fix if those copies are SSoT for agents there (separate repo —
  not edited without sign-off).
- Determine why `rules` disappeared from the fragment breakdown between rounds
  (strip in effect vs. absent in these particular requests) before treating
  either the ≈1.8k or the ≈155 tok/req figure as representative.

## DoD (reproducible in this repo — verify by running the commands, not by reading this table)

- [x] `pytest tests/test_token_registry.py tests/test_kilo_prompt_stats.py tests/test_kilo_proxy_relay.py -q` — **93 passed** (14 registry + 17 stats + 62 relay) locally **executed**, not merely collected
- [x] `pytest tests/ --co -q` — 3349 tests **collected** (not run) across the full tree at time of writing; re-run to get the current number — to confirm the target files import and collect cleanly under the same tree `test.yml`'s `pytest tests/ -q` walks
- [x] Registry: syntactic validity (`json.tool`) **and** semantic checks — entry count, `doc/adr.md` presence, CODE_ROOT non-zero — via `test_registry_no_zeroed_or_missing_regression_entries` (added this round; `json.tool` alone does not prove any of that)
- [x] `collect_chat_records()` covered directly: non-chat filtering, `deque(maxlen=N)` tail-only-of-chat behavior, `last=None/0`, malformed JSON / blank lines / non-dict rows counted (not silently dropped) via `lines_total`/`invalid_json`/`non_dict_records`, missing-file distinct CLI error (exit 3, not the "restart relay" message), negative `--last` rejected by argparse
- [x] `per_request` avg/median/min/max covered directly (`test_per_request_summary_stats_avg_median_min_max`)
- [x] `lint_agent_prompts.py` OK
- [ ] **10× effect** — NOT closed; needs the live A/B above

**Reproduce evidence (run these yourself — do not take the counts above on faith):**

```bash
.venv/Scripts/python.exe -m pytest tests/test_token_registry.py tests/test_kilo_prompt_stats.py tests/test_kilo_proxy_relay.py -q
.venv/Scripts/python.exe -m json.tool doc/token_safety_registry.json >/dev/null && echo "registry VALID"
.venv/Scripts/python.exe scripts/kilo_prompt_content_report.py --last 40           # dry-run, no --json-out
.venv/Scripts/python.exe scripts/kilo_prompt_content_report.py --last -1          # rejected: "--last must be >= 0"
.venv/Scripts/python.exe scripts/kilo_prompt_content_report.py --log nope.jsonl   # exit 3: "log file not found"
git show 628841c:doc/token_safety_registry.json | python -m json.tool  # 131 valid
git show 9c7b755:doc/token_safety_registry.json  | python -m json.tool  # 132 valid
git show 567e43c:doc/token_safety_registry.json | python -m json.tool  # 133 broken
git show b95abcd:doc/token_safety_registry.json  | python -m json.tool  # 134 fixed
```

*Note on dates:* this document is timestamped 2026-07-23 to match this
session's system clock; if your environment reports 2026-07-22, that is a
clock/timezone difference between sessions, not a re-edit of this file after
the fact — check `git log` timestamps for the authoritative sequence.
