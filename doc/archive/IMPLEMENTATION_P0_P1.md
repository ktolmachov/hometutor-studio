# Implementation: P0 Guards + P1 Cost Logging

**Date:** 2026-04-20  
**Status:** ✅ COMPLETE  
**Impact:** Blocks expensive models + tracks costs per call

---

## 📋 What Was Implemented

### P0 — Guards (3 checks)

**File:** `app/llm_guards.py` (NEW)

Three blocking guards prevent expensive/unstable calls:

#### Guard #1: Blocked Models Check
```python
check_model_allowed(model)
# Blocks: z-ai/glm-5.1, openai/gpt-5.3-codex
# Error: BlockedModelError("Blocked model not allowed. Use grok-4.1...")
```
**Fixes row #14 from log:** glm-5.1 call (7.12 руб) → REJECTED before API call

#### Guard #3: Hard Token Limit Check
```python
check_input_tokens(input_tokens)
# Hard limit: 20,000 tokens
# Soft limit: 12,000 tokens (warning only)
# Error: HardLimitExceededError("Input tokens X exceeds hard limit...")
```
**Prevents row #5 from log:** 83,041 tokens → REJECTED before API call

#### Guard #2: Soft Limit Warning (non-blocking)
```python
soft_warn = soft_limit_warning(input_tokens)
# Returns warning string if 12k < tokens < 20k
# Logs as WARNING level (doesn't block, just alerts)
```

### P1 — Cost Logging (per-call tracking)

**File:** `app/provider.py` (MODIFIED)
- Added imports for guard functions (lines 22-28)
- Added guard check in `_chat()` method (line 75)
- Added token limit check (lines 88-95)
- Added cost logging (lines 171-186)

**Cost Log Format:**
```json
{
  "timestamp": "2026-04-20T10:15:33Z",
  "model": "grok-4.1-fast-thinking",
  "input_tokens": 10500,
  "output_tokens": 850,
  "cost_rub": 0.89,
  "package_id": "E14-B",
  "prompt_type": "planning",
  "status": "OK",
  "guards_applied": ["model_check", "hard_limit_check"]
}
```

**Storage:** `doc/cost_logs/cost_logs_YYYY-MM-DD.jsonl`

---

## 🔍 How It Works

### Call Flow

```
chat(messages, model="grok-4.1-fast-thinking")
  ↓
_chat() internal method
  ↓
check_model_allowed("grok-4.1-fast-thinking") ← Guard #1 (FAST)
  ✅ Passes (not in BLOCKED_MODELS)
  ↓
estimate_tokens(message_dicts) → 10,500 tokens
  ↓
check_input_tokens(10500) ← Guard #3 (MEDIUM)
  ✅ Passes (10500 < 20000)
  ↓
soft_limit_warning(10500) ← Warning (INFO)
  ⚠️ No warning (10500 < 12000)
  ↓
call API (openrouter, anthropic, openai, etc.)
  ↓
get response (output_tokens=850)
  ↓
estimate_cost_rub("grok-4.1", 10500, 850) → 0.89 руб
  ↓
log_cost_call(...) → write to cost_logs_2026-04-20.jsonl ← P1 Logging
  ↓
cache response
  ↓
return ChatResponse
```

### Error Cases

**Case 1: Blocked Model**
```python
chat(messages, model="glm-5.1")
# Guard #1 check fails immediately
# Raises: BlockedModelError("Blocked model 'glm-5.1' not allowed...")
# Log: "MODEL_BLOCKED" error level
# Cost: $0 (no API call made)
```

**Case 2: Hard Limit Exceeded**
```python
chat(messages_with_25000_tokens, model="grok-4.1")
# Guard #1 check passes
# Guard #3 check fails
# Raises: HardLimitExceededError("Input tokens 25000 exceeds hard limit 20000...")
# Log: "HARD_LIMIT_EXCEEDED" error level
# Cost: $0 (no API call made)
```

**Case 3: Soft Limit Warning (Non-blocking)**
```python
chat(messages_with_15000_tokens, model="grok-4.1")
# Guard #1 passes
# Guard #3 passes
# Soft limit warning logged (12000 < 15000 < 20000)
# API call proceeds normally
# Cost: ~$0.26 (normal price)
```

---

## 📊 Impact on Log Baseline

| Row | Before | After | Savings |
|---|---|---|---|
| #14 (glm-5.1) | 7.12 руб | BLOCKED | 7.12 руб |
| #15-17 (ERR loop) | 140,703 tokens | BLOCKED | 140,703 tokens |
| Typical (grok) | 18,500 tokens, 1.48 руб | Unchanged | Tracked in logs |

**Expected Weekly Savings** (assuming 20 calls/week):
- Blocked dumb mistakes: ~7–10 руб
- Better visibility: cost/package breakdown
- Faster debugging: know exactly which calls cost what

---

## 🧪 Testing

### Manual Test #1: Block glm-5.1

```python
from app.llm_guards import check_model_allowed, BlockedModelError

try:
    check_model_allowed("glm-5.1")
except BlockedModelError as e:
    print(f"✅ Blocked as expected: {e}")
```

Expected: ✅ BlockedModelError raised

### Manual Test #2: Block openai/gpt-5.3

```python
try:
    check_model_allowed("openai/gpt-5.3-codex")
except BlockedModelError as e:
    print(f"✅ Blocked as expected: {e}")
```

Expected: ✅ BlockedModelError raised

### Manual Test #3: Allow grok-4.1

```python
try:
    check_model_allowed("grok-4.1-fast-thinking")
    print("✅ Allowed as expected")
except BlockedModelError as e:
    print(f"❌ Unexpected error: {e}")
```

Expected: ✅ No error (allowed)

### Manual Test #4: Hard Limit Check

```python
from app.llm_guards import check_input_tokens, HardLimitExceededError

# Should pass
check_input_tokens(10000)
print("✅ 10k tokens passed")

# Should fail
try:
    check_input_tokens(25000)
except HardLimitExceededError as e:
    print(f"✅ 25k tokens blocked: {e}")
```

### Manual Test #5: Cost Logging

```python
from app.llm_guards import log_cost_call
from pathlib import Path

log_cost_call(
    model="grok-4.1-fast-thinking",
    input_tokens=10500,
    output_tokens=850,
    cost_rub=0.89,
    package_id="E14-B",
    prompt_type="planning",
    status="OK",
    guards_applied=["model_check", "hard_limit_check"],
)

# Check file was created and has content
log_file = Path(__file__).parent.parent / "doc" / "cost_logs" / "cost_logs_2026-04-20.jsonl"
assert log_file.exists(), "Cost log file not created"
content = log_file.read_text()
assert "grok-4.1-fast-thinking" in content, "Model not in log"
assert "0.89" in content, "Cost not in log"
print("✅ Cost log file created and contains data")
```

---

## 📈 Monitoring & Next Steps

### Week 1: Validation (P3)

Monitor for:
1. ✅ Guard triggers (glm-5.1 blocks, >20k blocks)
2. ✅ Cost logs being created daily
3. ✅ No calls exceeding soft/hard limits
4. ✅ Cost per call averaging <1.50 руб

### Weekly Report (doc/cost_tracking.md)

Generate weekly summary:
```markdown
## Week 2026-04-21

- Total calls: 42
- Total cost: 18.50 руб (−30% vs baseline 26.63)
- Avg cost/call: 0.44 руб (−70% vs baseline)
- Guards triggered: 2 (glm-5.1 × 1, >20k × 1)
- Anomalies: None
```

---

## 📁 Files Created/Modified

| File | Change | Lines |
|---|---|---|
| `app/llm_guards.py` | NEW | 160 |
| `app/provider.py` | MODIFIED | +15 (imports + checks + logging) |
| `doc/cost_logs/README.md` | NEW | 50 |
| `doc/cost_logs/` | NEW DIRECTORY | — |

---

## ⚠️ Known Limitations

1. **Cost estimation is approximate** — uses hardcoded pricing table, actual costs depend on provider
2. **No async logging** — cost logging happens in _chat(), not async version; achat() not yet instrumented
3. **No retroactive blocking** — only blocks new calls, can't undo already-made expensive calls
4. **Guard #2 (retry prevention) not yet implemented** — will add in next iteration if needed

---

## ✅ Success Criteria Met

- [x] Guard #1: glm-5.1 blocked
- [x] Guard #1: openai/gpt-5.3 blocked
- [x] Guard #3: Hard token limit enforced
- [x] Cost logging per call
- [x] Cost logs saved to JSONL per day
- [x] No syntax errors
- [x] Ready for A/B testing (P2)

---

## Critical Follow-up (2026-04-19)

The initial implementation was hardened after review:

1. **Async path covered** - `_achat()` now applies the same model, token, retry-loop, cache, error, and cost logging behavior as `_chat()`.
2. **Unchanged retry guard implemented** - recent failed payload fingerprints are remembered briefly and identical retries are blocked before another provider call.
3. **Blocked/error visibility improved** - JSONL records now include `BLOCKED`, `ERR`, and `CACHE_HIT` statuses plus `error_type` / `error_message` when applicable.
4. **Guard module cleaned up** - comments/docstrings are ASCII-safe and cost-log failures catch `OSError` only.
5. **Regression tests added** - `tests/test_llm_guards.py` plus provider tests cover blocked models, hard token limits, JSONL logging, and unchanged retry blocking before client creation.

Remaining limitation:

1. **Cost estimation is approximate** - uses a static pricing table; actual costs still depend on provider-side pricing.
