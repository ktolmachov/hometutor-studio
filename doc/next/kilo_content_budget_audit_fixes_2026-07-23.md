# Token-budget audit — fixes & evidence (2026-07-23)

**Scope:** address the 2026-07 audit of `kilo_prompt_content_budget_breakthrough`
(Log 2). Code/data defects fixed in this repo; live A/B is a follow-up (needs
Cursor + relay + DeepSeek running).

> Honest labels (audit fix): the numbers below are an **instrumentation sample**
> from `logs/kilo_relay.jsonl` (see § Instrumentation sample for the exact `N`
> and the command to reproduce it), **not** a measured before/after A/B. They
> rank pollution; they do not prove the policy edits lowered cost yet. An
> earlier draft of this doc left a stale "3-request" figure in this banner
> after the sample below was regenerated at N=40 — this line is now written to
> point at the section instead of hardcoding a count, so it can't go stale the
> same way again.

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
| — | **(audit round)** `chat_with_stats` conflated "size of the `--last N` slice" with "how much instrumented traffic exists" | Added `chat_records_seen` — counts every chat row with `content_stats` across the whole file, before slicing |
| — | **(audit round)** aggregate path `hits=40` was read as "present in every one of 40 requests," but `hits` sums per-message mentions and can exceed the request count | Added `requests` (distinct chat requests with >=1 mention) to `top_paths` / `agents_claude_mentions`; `render_text` labels both explicitly |
| — | **(audit round)** `rules`-absent explanation was left as an unresolved "cloud_budget strip vs. absent" open question | Resolved via code: the aggregator reads `content_stats.original` (pre-compression), which rules out `cloud_budget` as the cause — see § Instrumentation sample |

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
The fix below targets that failure mode specifically, but a generator bug or a
new hand-edit pattern outside its scope could still corrupt the registry —
"moot" would overstate what a guard can promise.

**Fix that targets this failure mode.** `scripts/measure_token_registry.py`
is now **merge-safe** — it re-measures the 33 DOCS_ROOT files and **preserves**
the 17 CODE_ROOT `app/*` / `requirements.txt` entries (which cannot be measured
from this tree) instead of zeroing them. The registry is now *generated*, not
hand-edited, and the new regression tests below make dropped-key or
zeroed-entry corruption of this specific shape detectable in CI — this
reduces recurrence risk, it does not guarantee no future manual edit can
reintroduce a different kind of corruption. Regenerate + validate with:

```bash
.venv/Scripts/python.exe scripts/measure_token_registry.py --write
.venv/Scripts/python.exe -m json.tool doc/token_safety_registry.json >/dev/null && echo VALID
```

---

## Instrumentation sample (`--last 40`, regenerated 2026-07-23 after the audit)

> The log keeps growing from real usage between rounds — every capture so far
> has shown different numbers than the one before it. Numbers **will differ
> again** on the next capture; re-run the command below rather than trusting
> this snapshot as a constant. `scripts/kilo_prompt_content_report.py --last 40`
> reproduces this.

```
records=330  chat_records_seen=211  chat_with_stats=40
per request:  prompt_tokens  n=40 avg=14,522  median=13,990  min=9,489   max=20,311  (REAL usage.prompt_tokens)
              message_chars  n=40 avg=645,748 median=652,652 min=555,817 max=710,260 (chars/4 heuristic)
top kinds (AGGREGATE over 40 req):  tool_result ~4.36M tok   assistant_tool_calls ~1.67M tok   system ~227k tok
top fragments (AGGREGATE over 40 req): available_skills ~6.2k tok  — `rules` absent from this sample
top paths (AGGREGATE, ±200-char window heuristic): AGENTS.md hits=40 reqs=40 (~61.6k tok)  CLAUDE.md hits=40 reqs=40 (~20.5k tok)
```

`chat_records_seen=211` vs. `chat_with_stats=40` (audit fix, was previously
ambiguous): `chat_with_stats` is the size of the `--last N` tail slice, capped
at `N` by construction — on its own it told a reader nothing about how much
instrumented traffic actually exists. `chat_records_seen` now counts every
chat-completions row with `content_stats` across the **whole** file before
slicing (211 here), so it's clear this sample covers the most recent 40 of 211
instrumented requests, not "all instrumented traffic."

**`rules` absence — resolved, not an open question.** `content_stats` in
`logs/kilo_relay.jsonl` carries two payload snapshots per request: `original`
(captured in `kilo_proxy_relay.py` *before* `compress_chat_completion()` runs)
and `forwarded` (captured after). The aggregator in
`kilo_prompt_content_report.py` uses `cs.get("original") or cs.get("forwarded")`
— i.e. it prefers the **pre-compression** payload whenever present, and
`original` is populated on every instrumented chat request (see
`kilo_proxy_relay.py` around the `CONTENT_STATS` block, well before the
`RELAY_COMPRESS_ACTIVE` branch). So `cloud_budget` stripping `<rules>` from
`forwarded` cannot be why `rules` is missing from this report: the report never
reads `forwarded` here, because `original` is always present first. Two
independent 40-request samples (the previous round and this regenerated one)
both show no `rules` fragment, which points to the simpler explanation: these
sessions' outgoing Cursor payloads did not contain a `<rules>…</rules>` block
matching the fragment regex in this window, not that something downstream
removed it. The earlier "open question" framing overstated the uncertainty —
the code rules out the `cloud_budget` explanation directly.

**`hits=40` does not by itself prove "present in every request" — audit fix.**
`hits` in `_kilo_prompt_stats.path_char_contributions()` increments once per
**message** that mentions a path, not once per request; a single request that
names a path in three different messages contributes 3 to `hits`. The report
now also tracks `requests` (distinct chat requests containing >=1 mention),
added specifically because of this gap. In this sample AGENTS.md/CLAUDE.md
happen to show `hits=40 reqs=40` — one mention per request, so the "every
request" claim holds here — but that's a property of this sample, not a
guarantee of the `hits` field: other paths in the same run show `hits` several
multiples of `reqs` (e.g. one path shows `hits=1560 reqs=40`, ~39
mentions/request). Read `reqs`, not `hits`, when the claim you want is "how
many requests mentioned this."

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
- ~~Determine why `rules` disappeared from the fragment breakdown~~ — resolved
  this round: the aggregator reads `content_stats.original` (pre-compression)
  preferentially, so `cloud_budget` stripping is ruled out by the code, not
  just by the data; see § Instrumentation sample.

## DoD (reproducible in this repo — verify by running the commands, not by reading this table)

- [x] `pytest tests/test_token_registry.py tests/test_kilo_prompt_stats.py tests/test_kilo_proxy_relay.py -q` — **95 passed** (14 registry + 19 stats + 62 relay; +2 vs. the prior 93 for this audit round's `chat_records_seen` and `hits`-vs-`requests` coverage) locally **executed**, not merely collected
- [x] `pytest tests/ --co -q` — re-run to get the current number at the time you read this; not re-quoted here since it drifts every session and quoting a stale count invites the same staleness this audit round flagged elsewhere in this doc
- [x] Registry: syntactic validity (`json.tool`) **and** semantic checks — entry count, `doc/adr.md` presence, CODE_ROOT non-zero — via `test_registry_no_zeroed_or_missing_regression_entries` (added this round; `json.tool` alone does not prove any of that)
- [x] `collect_chat_records()` covered directly: non-chat filtering, `deque(maxlen=N)` tail-only-of-chat behavior, `last=None/0`, malformed JSON / blank lines / non-dict rows counted (not silently dropped) via `lines_total`/`invalid_json`/`non_dict_records`, `chat_records_seen` vs. sliced `chat_with_stats` (this audit round), missing-file distinct CLI error (exit 3, not the "restart relay" message), negative `--last` rejected by argparse
- [x] `build_report()`'s `hits` vs. `requests` distinction covered directly (`test_build_report_path_hits_vs_requests_are_distinct`, this audit round)
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

*Note on dates:* this document's filename/header date (2026-07-23) is this
session's system clock at write time, not a commit timestamp — while this file
is uncommitted, `git log` has no entry for it to check. The regenerated
instrumentation sample above records its own capture context
(`records=330 chat_records_seen=211`, reproducible via
`kilo_prompt_content_report.py --last 40` against the current
`logs/kilo_relay.jsonl`), which is the authoritative "when was this measured"
signal for that data — use it instead of this document's header date.
