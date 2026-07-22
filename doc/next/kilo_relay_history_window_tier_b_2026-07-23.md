# Tier B: history window + tool_result cap in the relay (2026-07-23)

**Context:** a live-session diagnosis (`kilo_content_budget_breakthrough`) found
per-turn cost growing linearly and unbounded (~337 tok/message, no ceiling)
because the relay forwarded the entire Cursor message history on every call.
Its proposed fix ("Tier B") — trim history and cap `tool_result` size **inside
the relay** — was previously blocked by this workstream's own contract
(`doc/next/prompt_kilo_content_budget_breakthrough.md` § Do not touch: *"Trim
messages\[\] / history внутри relay"*). The user explicitly lifted that
constraint this round. This document covers what was implemented.

## Diagnosis verification (before implementing)

Checked the diagnosis against the actual code and the live session log before
acting on it:

- **Confirmed real:** percentage breakdown matched raw log numbers exactly
  (`top_kind=tool_result:163571` / `body_orig=337225` ≈ 48.5%, table said 49%).
  Linear growth (~337 tok/message) confirmed across the visible session.
  Confirmed via `grep` that `_kilo_relay_compress.py` had **no** history-window
  or tool_result-cap logic before this change — the diagnosis's core claim
  ("relay doesn't own history") was accurate.
- **One bug found and NOT propagated:** the diagnosis's suggested
  `KILO_RELAY_REPLACE_CURSOR_SYSTEM=1` is silently overridden to disabled in
  `cloud_budget` mode by a *different* env var
  (`KILO_RELAY_CLOUD_BUDGET_REPLACE_CURSOR_SYSTEM`) — confirmed at
  `_kilo_relay_compress.py:593` vs `:617`. Tier B vars use the same override at
  `:594-595` vs `:627-628`. Corrected in the usage instructions below; regression
  tests lock in the (intentional) no-fallback behavior. (Line numbers as of the
  case-insensitive allowlist fix below — they drift by one line per edit above
  this point in the file; treat as approximate, not a pinned reference.)

## What changed

`scripts/_kilo_relay_compress.py`:

- `_history_window_bounds()` / `_apply_history_window()` — keeps leading
  `system` message(s) unconditionally, plus the last `keep_last_messages` of
  the rest. If that cut would open on an orphaned `tool`-role message (whose
  triggering `assistant` `tool_calls` got dropped — the case that breaks the
  upstream request), the boundary walks backward until it lands on that
  assistant message instead, extending the window just enough to stay valid.
  Verified with an exhaustive test over every window size against a payload
  containing a parallel (2-call) `tool_calls` turn — no dangling tool result
  in any case.
- `_cap_tool_result_chars()` / `_cap_message_content()` — caps `role=="tool"`
  message content to `max_tool_result_chars`, keeping the head (same
  keep-head convention as the existing `_truncate_desc`) and appending
  `…[truncated by relay: N more chars]`. Handles both string and
  list-of-parts content shapes. Only `tool`-role messages are touched.
- `RelayCompressConfig` gained `keep_last_messages: int = 0` and
  `max_tool_result_chars: int = 0` (both default **off**).
- `CompressResult` gained `messages_before` / `messages_after` /
  `messages_dropped_history` / `tool_results_capped`, surfaced in
  `to_log_dict()` and now visible directly on the relay's per-request stdout
  line as `hist_cut=N` / `tr_capped=N` (only printed when non-zero).
- `relay_compress_any_enabled()` now also turns compression on if only these
  two knobs are set (needed so the generic vars work even with
  `KILO_RELAY_SLIM_MODE=off`).
- Env wiring follows the **existing** two-tier pattern exactly (generic var,
  then a `CLOUD_BUDGET_`-prefixed override that **replaces**, not falls back
  to, the generic value when `KILO_RELAY_SLIM_MODE=cloud_budget`):

| Mode | Env var |
|---|---|
| any (`off`/`local`) | `KILO_RELAY_KEEP_LAST_MESSAGES`, `KILO_RELAY_MAX_TOOL_RESULT_CHARS` |
| `cloud_budget` only | `KILO_RELAY_CLOUD_BUDGET_KEEP_LAST_MESSAGES`, `KILO_RELAY_CLOUD_BUDGET_MAX_TOOL_RESULT_CHARS` |

`scripts/kilo_proxy_relay.py`: per-request stdout line now prints `hist_cut=`
and `tr_capped=` when the new steps did something; the startup banner already
dumps every `RelayCompressConfig` field generically via `asdict()`, so the two
new fields appear there with no extra code.

## Usage (corrected from the diagnosis)

```powershell
$env:KILO_RELAY_SLIM_MODE = "cloud_budget"
$env:KILO_RELAY_CLOUD_BUDGET_STRIP_CURSOR_RULES = "1"
$env:KILO_RELAY_CLOUD_BUDGET_STRIP_USER_INFO = "1"
$env:KILO_RELAY_CLOUD_BUDGET_REPLACE_CURSOR_SYSTEM = "1"   # NOT plain REPLACE_CURSOR_SYSTEM in this mode
# Optional: narrow tools (~2k tok). Match is case-insensitive.
# Use real Cursor tool ids; avoid Edit (usually StrReplace/edit) — unknown names drop silently.
# $env:KILO_RELAY_TOOLS_ALLOWLIST = "Shell,Read,Grep,Write,StrReplace"
$env:KILO_RELAY_CLOUD_BUDGET_KEEP_LAST_MESSAGES = "14"     # tightened 2026-07-23 (was 24)
$env:KILO_RELAY_CLOUD_BUDGET_MAX_TOOL_RESULT_CHARS = "2000" # tightened (was 4000)
.\.venv\Scripts\python.exe scripts/kilo_proxy_relay.py
```

Daily launcher equivalent (sets the same CLOUD_BUDGET_* env, no allowlist):

```powershell
pwsh -File D:\AI\llama_cpp_server_pack_v1\kilo-relay\Start-KiloRelayDaily.ps1 `
  -UseDeepSeek -RelayProfile CloudBudget -StopExistingRelay `
  -DeepSeekThinking disabled
```

## Evidence

**Synthetic worst-case check** (241 messages, shaped like the live session's
growth pattern — 80 turns × system/user/assistant-tool_call/tool_result, each
tool_result 6000 chars):

```
messages_before: 241 -> messages_after: 25
messages_dropped_history: 216
tool_results_capped: 8
chars_saved_estimate: 462986  (~116k tokens on this synthetic payload)
```

This is a synthetic reproduction of the session's *shape*, not a replay of the
real `kilo_relay.jsonl` — directionally consistent with the diagnosis's ×10
estimate, not a claim that the real session saves exactly this much.

**Tests:** `pytest tests/test_kilo_relay_compress.py` — **35 passed** (22
pre-existing + 13 new: no-op below limit, disabled by default, keeps leading
system message(s), never leaves a dangling tool result (exhaustive over every
window size), tool_result cap touches only `tool` role, list-of-parts content
shape, `to_log_dict()` counters, generic-var-in-off-mode, and the
cloud_budget-override-doesn't-fall-back behavior explicitly locked in,
allowlist case-insensitive match for Cursor lowercase tool names).
Broader regression: `pytest tests/test_kilo_relay_compress.py
tests/test_kilo_proxy_relay.py tests/test_kilo_prompt_stats.py
tests/test_kilo_guard.py` — **137 passed**.

## Still true from the original diagnosis (unaffected by this change)

- Env flags only affect **future** turns in a **new** relay process / new
  chat; they don't retroactively shrink an already-bloated in-flight
  conversation on the Cursor side (Cursor still resends full history each
  turn — the relay can only trim what it forwards).
- `GUARD_MODE=block` (Tier C) is a separate, still-untouched decision — this
  round only lifted the "no history trim in relay" constraint, not the guard
  default.

## Live budget honesty (2026-07-23, same JSONL, longer sample)

Verified against `logs/kilo_relay.jsonl` (not a short post-restart sample):

| Claim | Verdict |
|---|---|
| Two sessions in one log (`msgs` 25→**2**, `tools` 16→**6**, `allowlist=None`) | **Confirmed**. Split starts at `82b04c53` (in=1279); `0e1c1e4f` is the *second* turn of the new chat. `top_kind` on split is **`user`**, not `system`. |
| Old session in= 5530…12453; new 1279…19000 (incl. peak **26257**) | **Exact sequences found** in the log |
| vs baseline ~83519: always better | **Confirmed** |
| On that 20-request window: 11/20 >12k (55%), 5/20 >20k (25%) | **Confirmed** |
| `hist_cut` / `tr_capped` grow; window is **message-count**, not char-budget | **Confirmed** — after hist_cut active, `in` still climbs (18k→26k) because ~24×~4000-char tool_results alone ≈24k tok |

**Correction to earlier “×15 / goal met” verdict:** that was based on 2 early turns right after restart. Longer tool-heavy traffic shows **24/4000 does not hold ≤12k/≤20k**.

**Default tightened (launcher + docs):** `KEEP_LAST_MESSAGES=14`, `MAX_TOOL_RESULT_CHARS=2000`. Still not a hard char-budget guarantee — start a new chat when `in` climbs past soft/hard rather than waiting for soft_block.