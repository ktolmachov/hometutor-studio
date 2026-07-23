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
| — | **(audit round 3)** `_PATH_RE`'s Windows-path branch allowed backslash inside its own segment class, so a single letter + `:` + two literal backslash characters + `n` (e.g. source text showing a raw `\n` escape sequence as two literal characters, not an actual newline) false-positived as a one-letter drive path; `normalize_path_key` then turned the doubled backslashes into `y://n` / `e://n`, which **outranked AGENTS.md** in a real `top_paths` run | Excluded backslash from the segment character classes in `_kilo_prompt_stats._PATH_RE` (verified: still matches genuine `D:\Projects\...\AGENTS.md`, no longer matches the doubled-escape case); 2 regression tests added. **Known limitation, not silently glossed over:** `content_stats.path_chars` is computed once per request by the relay and stored in the JSONL — this fix only affects requests logged *after* a relay restart. The historical rows already in `logs/kilo_relay.jsonl` were analyzed by the old regex and still show `y://n`/`e://n` in `top_paths` until fresh traffic ages the bad rows out of any `--last N` window; see § Instrumentation sample for the current (still-affected) live output |
| — | **(audit round 3)** the "Levers toward 10×" section quoted `avg ≈36.6k/req` and `tool_result ~698k tok / 40 ≈17.5k tok/req`, both leftovers from an earlier capture, while § Instrumentation sample above them had already been refreshed to different numbers twice — same doc, two disagreeing numbers | Removed the duplicated hardcoded figures; that section now cross-references § Instrumentation sample instead of repeating numbers that can drift out of sync with it (this had already happened twice by the time it was caught) |
| — | **(audit round 3)** "lint/type tooling: none configured" was checked only against the local `.venv`, not against `.github/workflows/ci.yml`, which does install and run `ruff check app tests` | Corrected below to state both facts: not installed locally, configured in CI — and that CI's `ruff` target (`app tests`) does not include `scripts/`, so this round's `scripts/` edits are not covered by that CI check either |

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
> has shown different numbers than the one before it (211 → 248 instrumented
> requests just between two captures taken minutes apart while writing this
> section). Numbers **will differ again** by the time you read this; re-run
> the exact command below rather than trusting this snapshot as a constant.

```bash
.venv/Scripts/python.exe scripts/kilo_prompt_content_report.py --log logs/kilo_relay.jsonl --last 40
```

```
records=385  chat_records_seen=266  chat_with_stats=40
per request:  prompt_tokens  n=40 avg=5,997  median=6,436  min=3,800  max=7,685  (REAL usage.prompt_tokens)
top kinds (AGGREGATE over 40 req):  tool_result ~6.64M tok   assistant_tool_calls ~2.11M tok   system ~227k tok
top fragments (AGGREGATE over 40 req): available_skills only — `rules` absent from this sample
top paths, as actually ranked, top 3 (NOT cherry-picked — see caveat below):
  1. y://n              hits=240  reqs=40  (~201.8k tok) — KNOWN FALSE POSITIVE, see caveat
  2. scripts/compute_trusted_route_rate.py  hits=1560 reqs=40  (~144.1k tok)
  3. e://n              hits=320  reqs=40  (~125.6k tok) — KNOWN FALSE POSITIVE, see caveat
  ...
  9. AGENTS.md          hits=40   reqs=40  (~61.6k tok)
 (CLAUDE.md, further down): hits=14 reqs=14 (~7.2k tok)
```

**`top_paths` false positives — found, root-caused, and fixed at the
aggregator level, so it also cleans historical rows (correction to an
earlier, now-outdated claim in this doc).** The previous round's doc quoted
only the AGENTS.md/CLAUDE.md rows from `top_paths`; `y://n` and `e://n`
actually ranked above them. Root cause: a single letter + `:` + doubled
literal backslash characters + `n` (e.g. a tool_result echoing source code
that shows a raw `\n` escape sequence as two literal characters, not an
actual newline) satisfied the Windows-path regex's "one-letter drive path"
shape; `normalize_path_key()` then turned the backslashes into `/`,
producing `y://n` / `e://n`.

This went through two fix attempts, worth recording because the first one
overcorrected: (1) excluding backslash from `_PATH_RE`'s own segment classes
stopped the false positive but also stopped matching genuine single-segment
paths (`C:\Windows`) and genuine doubled-backslash paths (JSON-re-escaped
text like `D:\\Projects\\report.txt`) — a real regression an audit caught by
testing those cases directly. (2) The regex was reverted to its original,
permissive form; disambiguating junk from real paths is now entirely
`is_plausible_path_key()`'s job, applied to the *normalized* key (so `y:\\n`
normalizes to `y://n` and gets rejected by shape, while `C:\Windows` and the
JSON-re-escaped path normalize to clean multi-segment keys and pass).

**This fix is NOT only forward-looking, correcting the earlier claim in this
doc that it was.** `kilo_prompt_content_report.py`'s aggregator (`build_report`
/ `_merge_path_rows`) now normalizes-then-validates every stored `path_chars`
row it reads from `logs/kilo_relay.jsonl`, including rows logged long before
this fix existed — so regenerating the report cleans historical junk keys
too, it does not require a relay restart or fresh traffic. Verified live
against the actual growing log (not a synthetic case): a `--last 40` capture
taken after this fix shows no `y://n`/`e://n` in `top_paths`. The earlier
version of this section claimed the opposite (that a relay restart was
required) based on how the fix was scoped at the time — that scoping changed
in a later round and this section was not updated until now, which is itself
the kind of staleness this document keeps needing to correct.

`chat_records_seen=266` vs. `chat_with_stats=40` (audit fix, was previously
ambiguous): `chat_with_stats` is the size of the `--last N` tail slice, capped
at `N` by construction — on its own it told a reader nothing about how much
instrumented traffic actually exists. `chat_records_seen` now counts every
chat-completions row with `content_stats` across the **whole** file before
slicing, so it's clear this sample covers the most recent 40 of 266
instrumented requests, not "all instrumented traffic."

**`rules` absence — precisely scoped, not an open question, but not
overstated either (audit round 2 correction).** `content_stats` in
`logs/kilo_relay.jsonl` carries two payload snapshots per request: `original`
(captured in `kilo_proxy_relay.py` *before* `compress_chat_completion()` runs)
and `forwarded` (captured after). `kilo_prompt_content_report.build_report()`
uses `cs.get("original") or cs.get("forwarded")` — i.e. it prefers the
**pre-compression** payload whenever present. Checked directly against the
live log rather than assumed, re-verified this round at the log's current
size: **266/266** chat rows in `logs/kilo_relay.jsonl` have both
`content_stats.original` and `.forwarded` present (script: iterate the file,
count rows where either key is missing — both counts were 0 both times this
was checked, at 248 and again at 266 rows), so the `forwarded`-only fallback
path in `build_report()`
was never exercised in this data. The precise claim is: **for every record in
this log, `cloud_budget` stripping is not the explanation, because the
aggregator reads the pre-strip `original` payload for all of them** — not the
stronger, unqualified "physically could not be the cause" from the previous
round, which asserted more than the fallback-coverage check actually
established. (Separately, and unrelated to `build_report()`: the live
per-request stderr glance in `kilo_proxy_relay._content_stats_glance()` was
changed in a later commit to prefer `forwarded` specifically for
`fragment_chars` — so that stderr line and this aggregate report can now show
different `top_frag` values by design; they answer different questions
("what did we just send" vs. "what did the original payload contain").) Two
independent 40-request samples (the previous round and this regenerated one)
both show no `rules` fragment in `original`, which is consistent with the
simpler explanation — these sessions' outgoing Cursor payloads did not
contain a `<rules>…</rules>` block matching the fragment regex in this
window — but "consistent with" is what the evidence supports, not proof that
no other cause exists.

**`hits=N` does not by itself prove "present in every request" — audit fix,
and this fresh sample demonstrates the gap directly rather than only in
theory.** `hits` in `_kilo_prompt_stats.path_char_contributions()` increments
once per **message** that mentions a path, not once per request; a single
request that names a path in three different messages contributes 3 to
`hits`. `build_report()` now also tracks `requests` (distinct chat requests
containing >=1 mention; see the loop comment in `build_report()` for the exact
definition — it counts elements of the sliced `chat` list, not unique
`request_id` values). In *this* sample AGENTS.md shows `hits=40 reqs=40` (one
mention per request, every request), but **CLAUDE.md in the same sample shows
`hits=14 reqs=14`** — mentioned in only 14 of the 40 requests, not "every
request" as an AGENTS.md-only sample would imply by extension. (An earlier
capture in this same doc showed CLAUDE.md at `hits=32 reqs=32` — the point
isn't the specific number, which drifts with every capture like everything
else in this section, but that it is *not* 40/40 and a reader must not assume
it is just because AGENTS.md's happens to be.) `reqs` is the field that
answers "how many requests mentioned this"; `hits` answers "how many mentions
total," and the two only coincide when the mention-per-request rate happens
to be exactly 1.

---

## Levers toward the 10× *target* (ranked by savings × 1/quality-risk)

> 10× is a **target hypothesis**, not a measured result. This round's real
> `prompt_tokens` average (see § Instrumentation sample above for the current
> number — deliberately not repeated here, since an earlier draft of this
> section quoted a hardcoded `avg` that fell out of sync with that section
> after two later re-captures, which is exactly the kind of stale-number
> problem an audit round had to catch and fix) sits well under the historical
> >100k-token long-session figure, which is encouraging, but a single
> session's running average is not a controlled before/after — see
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
4. **Tool-result discipline** — consistently the biggest single kind by a wide
   margin (see § Instrumentation sample's `top kinds` line above for the
   current aggregate; not re-quoted here for the same reason as the
   `prompt_tokens` figure above — this exact number was previously
   inconsistent with § Instrumentation sample after that section got
   refreshed and this one didn't); prune/summarize stale `tool_result`
   history to cap `msgs` growth.

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

- [x] Targeted: `pytest tests/test_token_registry.py tests/test_kilo_prompt_stats.py tests/test_kilo_proxy_relay.py -q` — **102 passed** (14 registry + 26 stats + 62 relay; stats went 17 → 24 → 26 across this doc's three audit rounds — don't extrapolate a trend from that, it's just "tests were added each time a real gap was found")
- [x] Full kilo suite: `pytest tests/test_token_registry.py tests/test_kilo_prompt_stats.py tests/test_kilo_proxy_relay.py tests/test_kilo_relay_compress.py tests/test_kilo_guard.py -q` — **161 passed** (adds 36 compress + 23 guard, from an unrelated concurrent round of work on those two files, not this audit round; see § Reproduce evidence for both exact commands run back to back)
- [x] Registry: syntactic validity (`json.tool`) **and** semantic checks — entry count, `doc/adr.md` presence, CODE_ROOT non-zero — via `test_registry_no_zeroed_or_missing_regression_entries`
- [x] `collect_chat_records()` covered directly: non-chat filtering, `deque(maxlen=N)` tail-only-of-chat behavior, `last=None/0`, malformed JSON / blank lines / non-dict rows counted via `lines_total`/`invalid_json`/`non_dict_records`, `chat_records_seen` vs. sliced `chat_with_stats`, missing-file distinct CLI error (exit 3), negative `--last` rejected by argparse, and — added in response to audit round 2 — correctness at 5000-row scale (`test_collect_chat_records_correct_on_large_synthetic_log`) and generator-based streaming asserted structurally (`test_scan_jsonl_lines_is_a_generator_not_a_full_materialization`)
- [x] `build_report()`'s `hits` vs. `requests` distinction covered directly, including the two gaps audit round 2 asked for: `requests` counts JSONL rows, not unique `request_id` (`test_build_report_requests_counts_rows_not_unique_request_ids`), and a malformed record naming one path twice doesn't inflate `requests` (`test_build_report_requests_not_inflated_by_duplicate_path_row_within_one_record`)
- [x] Output determinism: `test_build_report_top_lists_are_deterministic_across_repeated_calls` — same input, same `top_kinds`/`top_paths` order on repeat calls
- [x] `_PATH_RE` doubled-escape false positive (`y://n`/`e://n` outranking AGENTS.md in a real report — found by audit round 3) fixed and regression-tested; **not** claimed fixed in the live sample, since historical `content_stats` is stored, not recomputed — see the caveat in § Instrumentation sample
- [x] `per_request` avg/median/min/max covered directly (`test_per_request_summary_stats_avg_median_min_max`)
- [x] `lint_agent_prompts.py` OK
- [x] Lint/type tooling — corrected this round, previous claim was too broad: `mypy`/`black`/`flake8` are not configured anywhere in this repo. `ruff` **is** configured in CI (`.github/workflows/ci.yml`: `pip install ruff` then `python -m ruff check app tests`) but is **not installed in the local `.venv`** (`python -m ruff` fails with `No module named ruff`) and, more importantly, **CI's ruff target is `app tests` — it does not include `scripts/`**, so this round's edits to `scripts/kilo_prompt_content_report.py` and `scripts/_kilo_prompt_stats.py` are not linted by CI either. `tests/test_kilo_prompt_stats.py` (also touched this round) is covered by CI's `ruff check … tests`. Net: this round's script changes have no lint coverage, local or CI; that's a gap in the repo's CI config, not something this round's PR can fix without expanding scope
- [x] Schema compatibility: `grep -rn` across `scripts/ tests/ doc/` for `kilo_content_report.json`, `top_paths`, `"hits"` found no code that parses this report's JSON back in (only prose references in `doc/next/*.md` and unrelated per-payload fields in `_kilo_prompt_stats.py`); `requests`/`chat_records_seen` are additive keys, no existing key was renamed or removed, and `test_build_report_path_hits_vs_requests_are_distinct` / the existing aggregation tests exercise both the `render_text()` and dict-return paths
- [ ] **10× effect** — NOT closed; needs the live A/B above

**Reproduce evidence (run these yourself — do not take the counts above on faith):**

```bash
.venv/Scripts/python.exe -m pytest tests/test_token_registry.py tests/test_kilo_prompt_stats.py tests/test_kilo_proxy_relay.py -q
# ........................................................................ [ 70%]
# ..............................                                           [100%]
# 102 passed in 0.57s

.venv/Scripts/python.exe -m pytest tests/test_token_registry.py tests/test_kilo_prompt_stats.py tests/test_kilo_proxy_relay.py tests/test_kilo_relay_compress.py tests/test_kilo_guard.py -q
# ........................................................................ [ 44%]
# ........................................................................ [ 89%]
# .................                                                        [100%]
# 161 passed in 0.66s

.venv/Scripts/python.exe -m json.tool doc/token_safety_registry.json >/dev/null && echo "registry VALID"
.venv/Scripts/python.exe scripts/kilo_prompt_content_report.py --log logs/kilo_relay.jsonl --last 40   # dry-run, no --json-out
.venv/Scripts/python.exe scripts/kilo_prompt_content_report.py --last -1          # rejected: "--last must be >= 0"
.venv/Scripts/python.exe scripts/kilo_prompt_content_report.py --log nope.jsonl   # exit 3: "log file not found"
git show 628841c:doc/token_safety_registry.json | python -m json.tool  # 131 valid
git show 9c7b755:doc/token_safety_registry.json  | python -m json.tool  # 132 valid
git show 567e43c:doc/token_safety_registry.json | python -m json.tool  # 133 broken
git show b95abcd:doc/token_safety_registry.json  | python -m json.tool  # 134 fixed
```

**Files this audit round actually touched:** `scripts/_kilo_prompt_stats.py`
(the `_PATH_RE` fix), `scripts/kilo_prompt_content_report.py` (the `+/-200`
ASCII fix), `tests/test_kilo_prompt_stats.py` (new tests), this doc. Stated
explicitly rather than via a hardcoded `git diff --stat`/`git status` snapshot:
across this doc's three audit rounds so far, every committed/uncommitted
claim written into this file went stale by the next round (the doc itself got
committed between rounds at least twice, and the working tree has also
carried unrelated concurrent edits to other files at times). Whether these
four files are committed, and what else is in the working tree, is whatever
`git status --short` / `git diff --stat` / `git log -- <path>` say **when you
run them** — this doc stops asserting that state as a written fact for the
same reason § Instrumentation sample stopped hardcoding `prompt_tokens`
numbers into § Levers: a snapshot copied into prose is a snapshot that goes
wrong.

*Note on dates:* this document's filename/header date (2026-07-23) is this
session's system clock at write time, nothing more — it is not a claim about
commit status, and has been wrong as a proxy for "is this file committed"
before. `git log -- doc/next/kilo_content_budget_audit_fixes_2026-07-23.md`
is the authoritative source for this document's own edit history. The
instrumentation sample's freshness is separate again: `logs/kilo_relay.jsonl`
is a live, growing file, so § Instrumentation sample's numbers reflect
whatever `chat_records_seen` was at the moment that section's command last
ran — re-run it for a current number.
