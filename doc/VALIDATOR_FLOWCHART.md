# Validator Workflow (Decision Tree)

## 🔄 Before Every LLM Call

```
┌──────────────────────────────────────────────────────────────┐
│  STEP 1: List proposed read-set files                        │
│  (e.g., app/query_service.py, tests/test_api.py)             │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  STEP 2: Run validator                                       │
│  $ python scripts/check_readset.py file1 file2 file3         │
└──────────────────────────────────────────────────────────────┘
                            ↓
                    ┌───────┴───────┐
                    ↓               ↓
            ┌──────────────┐  ┌──────────────┐
            │  Exit 0      │  │  Exit 1      │
            │  ✅ SAFE     │  │  ⚠️ WARN     │
            └──────┬───────┘  └──────┬───────┘
                   │                 │
                   ↓                 ↓
            ┌──────────────┐  ┌──────────────────┐
            │ SEND PROMPT  │  │ FIX & RETRY      │
            │ Confidence:  │  │ Options:         │
            │ HIGH         │  │ 1) Remove file   │
            │              │  │ 2) Use grep/head │
            │ Time: ~5-15s │  │ 3) Read section  │
            │ Cost: cheap  │  │                  │
            └──────────────┘  │ Then re-run:     │
                              │ python scripts/  │
                              │ check_readset.py │
                              └──────┬───────────┘
                                     │
                                     ↓
                              ┌──────────────┐
                              │ Exit 0 ✅?   │
                              └──────┬───────┘
                                     │
                       Yes ──────────┘
                       │
                       ↓
                  SEND PROMPT


                    Exit 2
                    🔴 BLOCK
                        ↓
                ┌────────────────────┐
                │ DO NOT SEND         │
                │ Confidence: NONE    │
                │                     │
                │ Action:             │
                │ 1) Read constraints │
                │ 2) Redesign setup   │
                │ 3) Use FORBIDDEN    │
                │    safe methods     │
                │ 4) Re-validate      │
                │                     │
                │ See: FORBIDDEN      │
                │ table in card       │
                └────────────────────┘
```

---

## Exit Code Legend

```
┌──────┬──────────┬──────────────────────────────────────┐
│ Code │ Status   │ Interpretation                       │
├──────┼──────────┼──────────────────────────────────────┤
│ 0    │ ✅ SAFE  │ Input < soft-limit (12k)             │
│      │          │ All files within budget              │
│      │          │ ACTION: SEND PROMPT                  │
├──────┼──────────┼──────────────────────────────────────┤
│ 1    │ ⚠️ WARN  │ soft-limit < input < hard-limit      │
│      │          │ Some compression recommended         │
│      │          │ ACTION: FIX & RETRY                  │
├──────┼──────────┼──────────────────────────────────────┤
│ 2    │ 🔴 BLOCK │ input > hard-limit (20k) OR          │
│      │          │ forbidden full-reads detected        │
│      │          │ ACTION: DO NOT SEND, REDESIGN        │
└──────┴──────────┴──────────────────────────────────────┘
```

---

## Quick Decisions by Type

### If Exit 0 ✅ SAFE

```
CONFIDENCE: High ✓
ACTION: Send prompt
TIME: ~5–20 seconds until response
QUALITY: Expected (no truncation)
```

### If Exit 1 ⚠️ WARN

```
CONFIDENCE: Medium ~
ACTION: Fix one of:
  1) Remove 1–2 lowest-signal files
  2) Replace full-read with grep/head
  3) Read only section needed
  4) Compress history (old tool results)

Then re-run: python scripts/check_readset.py
Target: Get to Exit 0 ✅
```

### If Exit 2 🔴 BLOCK

```
CONFIDENCE: None ✗
ACTION: DO NOT SEND

Analyze error message:
  - "❌ FORBIDDEN": Use safe-method from table
  - "Estimated Xk > hard-limit": Remove files
  - ">600 lines": Use --signatures to see grep command

Fix all issues, then re-run
Target: Get to Exit 0 ✅ or Exit 1 ⚠️
```

---

## Common Fix Patterns

### Pattern 1: File is Too Large

```
❌ FORBIDDEN  app/query_service.py
   Safe: grep "^class\|^def " app/query_service.py

ACTION:
1) Remove app/query_service.py from read-set
2) If needed, use: grep "^class\|^def " app/query_service.py
3) Paste grep output into prompt instead of full file
4) Re-run validator
```

### Pattern 2: Total Too High

```
🟡 WARN: Estimated 16.8k > soft limit 12.0k

ACTION:
1) Identify largest file from output
2) Either:
   a) Remove it, OR
   b) Use grep/section only
3) Re-run validator
```

### Pattern 3: Forbidden Directory

```
❌ FORBIDDEN  doc/epochs/e15.md
   Safe: Read max 1 epoch file; use headers/status tables

ACTION:
1) Remove doc/epochs/ folder from read-set
2) Use only ONE specific file (e.g., doc/epochs/e14.md)
3) Or use doc/closed_iterations.md summary instead
4) Re-run validator
```

---

## Success Paths (Examples)

### Example 1: Planning Task

```
Attempt 1:
$ python scripts/check_readset.py app/quiz_service.py \
    tests/test_quiz_service.py \
    doc/tasklist.md

❌ Result: BLOCK (app/quiz_service.py forbidden)

Fix:
$ python scripts/check_readset.py \
    --signatures app/quiz_service.py \
    tests/test_quiz_service.py \
    doc/tasklist.md
    
[Output shows: grep "^class\|^def " app/quiz_service.py]

Attempt 2:
$ python scripts/check_readset.py \
    doc/tasklist.md \
    doc/conventions.md

✅ Result: SAFE (3.2k tokens)

ACTION: Send prompt
```

### Example 2: Architecture Review

```
Attempt 1:
$ python scripts/check_readset.py \
    doc/conventions.md \
    doc/conventions_architecture.md \
    doc/conventions_reference.md \
    app/query_service.py \
    app/knowledge_graph.py

🔴 Result: BLOCK (input 35k > 20k hard-limit)

Fix (Phase 1 only):
$ python scripts/check_readset.py \
    doc/conventions.md \
    doc/conventions_architecture.md \
    doc/conventions_reference.md

✅ Result: SAFE (~5.6k tokens)

ACTION: Send Phase 1 prompt (conventions audit)
Then: Plan Phase 2 separately
```

---

## Decision Tree (One Page)

```
                    RUN VALIDATOR
                        ↓
            ┌───────────┬─────────────┐
            ↓           ↓             ↓
         Exit 0       Exit 1        Exit 2
         SAFE         WARN          BLOCK
           ↓           ↓              ↓
        SEND       FIX ONE        REMOVE OR
                  OF THREE:       REDESIGN
        ✅         1) Remove      ❌
                   2) Grep
                   3) Section
                      ↓
                   RE-RUN
                      ↓
                   Exit 0?
                     ↓
                    SEND
                    ✅
```

---

## Common Mistakes (Avoid)

| Mistake | Why Bad | Fix |
|---|---|---|
| Skip validator step | Miss token-limit issues | Always run before send |
| Ignore BLOCK status | Wasted API call | Fix FORBIDDEN files first |
| Multiple retries same payload | Stuck loop | Compress, then retry |
| Mix glm-5.1 + large read-set | 20k tokens, cost spikes | Use grok-4.1 always |
| Include old history | Accumulation, context bloat | Fresh context only |

---

## Integration with Shell / CI

### Bash

```bash
#!/bin/bash
set -e

files=("$@")
python scripts/check_readset.py "${files[@]}" || {
  echo "❌ Token budget exceeded. Fix read-set and retry."
  exit 1
}

echo "✅ SAFE. Ready to send."
# ... send LLM prompt ...
```

### Usage

```bash
./validate_and_send.sh file1.py file2.py
```

---

## Troubleshooting

| Issue | Debug Step |
|---|---|
| Validator crashes | `python scripts/check_readset.py --help` |
| Token estimate seems wrong | Check table in `doc/token_safety.md` |
| File not recognized | Add to project root, or use absolute path |
| Exit code not 0/1/2 | Check stderr, may have I/O error |

---

## Reference

- **Full docs:** `doc/token_safety.md`
- **Quick ref:** `doc/QUICK_READSET_REFERENCE.md`
- **Checklist:** `doc/archive/token_optimization_checklist.md`
- **This file:** `doc/VALIDATOR_FLOWCHART.md`

---

*Last updated: 2026-04-19*

