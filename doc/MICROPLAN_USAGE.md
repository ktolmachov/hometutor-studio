# Micro-Plan: Как использовать (Real Usage)

**Версия:** 1.0 | **Дата:** 2026-04-19 | **Статус:** Production Ready

Валидированный шаблон для planning-вызовов с бюджетом **< 10k входных токенов** (вместо 33k baseline).

---

## 🎯 Когда использовать Micro-Plan

✅ **Используй Micro-Plan для:**
- Planning одного пакета из `doc/tasklist.md` (Planned или Deferred)
- Уточнение DoD существующего контракта
- Быстрое опубликование execution prompt
- Стандартные пакеты (CRUD, feature, refactor)

❌ **Используй Full Planning для:**
- Архитектурного review (doc/conventions_architecture.md)
- Многопакетных инициатив (5+ пакетов)
- Новых CJM или major pivots

---

## 📋 Template (Copy-Paste)

```text
Goal: plan <PACKAGE_NAME> ONLY — produce execution contract.

Read ONLY (max 3 files):
1. <relevant-code-file.py> — grep "^class\|^def " only
2. <relevant-test-file.py> — 1 specific test case (name: test_<X>)
3. doc/tasklist.md — ONLY the row for <PACKAGE_NAME>

Ignore prior responses/tools. Fresh context only.

Output format:
- Package goal: 1-2 sentences tied to user pain (reference CJM)
- Write-set: 3–5 files max to create or modify
- Read-set: 2–3 files max to inspect
- Do-not-touch: 3–5 items explicit
- DoD: 1 pytest command + observable result
- Copy-paste execution prompt

Rules:
- Do not write code. Only produce the plan.
- Do NOT read doc/epochs/, doc/cjm.md, doc/closed_iterations.md
- Total output: max 300 words.
```

---

## ✅ Real Example: `epoch-answer-quality-eval`

**Current status:** in progress (use only for updates/clarifications)

**If planning similar deferred package:**

```text
Goal: plan epoch-unified-context-layer ONLY — execution contract.

Read ONLY:
1. app/models.py — grep "^class " (find QueryContext, UI state models)
2. tests/test_ui_helpers.py — 1 test_persistence case
3. doc/tasklist.md — row for epoch-unified-context-layer

Ignore prior responses/tools. Fresh context only.

[same rules & format as above]
```

---

## 🔍 Pre-Plan Validation

**Always run before sending prompt:**

```bash
python scripts/check_readset.py <file1> <file2> doc/tasklist.md --overhead 1500

# Expected: SAFE (< 12k tokens)
# Output: Token estimate, file breakdown, recommendations
```

**Example output:**
```
  🟢  SAFE
       Estimated 3.2k tokens — within budget.
```

---

## 📊 Cost Comparison

| Scenario | Input tokens | Cost | Time |
|----------|---|---|---|
| **Full Planning** (baseline) | 33.4k | ~1.2 руб | 30–60s |
| **Micro-Plan** (optimized) | 3.5k | ~0.1 руб | 5–10s |
| **Savings** | -89.5% | **-90%** | **5–10x faster** |

---

## 🚀 Workflow (Step-by-Step)

1. **Pick package** from `doc/tasklist.md` (Planned or Deferred)

2. **List read-set** (max 3 files):
   ```bash
   # Find relevant code
   grep -l "class\|def" app/*.py | head -3
   ```

3. **Validate budget:**
   ```bash
   python scripts/check_readset.py <file1> <file2> doc/tasklist.md --overhead 1500
   ```

4. **If SAFE:** Copy template above, fill in `<PACKAGE_NAME>`, send

5. **If WARN or BLOCK:** 
   - Remove lowest-signal file, or
   - Use grep instead of full-read, or
   - Read only needed section

6. **Validate again** → send when SAFE

---

## 📌 Gotchas

| Issue | Fix |
|-------|-----|
| "BLOCK — file forbidden" | Use `--signatures` flag; grep instead of full read |
| "WARN — 12k exceeded" | Remove 1 file or compress history |
| "Agent reads extra files" | Re-prompt: "Read ONLY: file1, file2, file3" |
| Output > 400 words | Add: "Max 300 words" |

---

## 🔗 Related

- Full validator: `scripts/check_readset.py`
- Token safety reference: `doc/token_safety.md`
- Full planning template: `doc/agent_workflow_templates.md` (§ Шаблон planning prompt)
- Quick reference: `doc/QUICK_READSET_REFERENCE.md`

---

## ✨ Success Checklist

Before sending Micro-Plan prompt:

- [ ] `python scripts/check_readset.py ... ✅ SAFE`?
- [ ] Read-set ≤ 3 files?
- [ ] Model = grok-4.1 (not glm-5.1)?
- [ ] Added: "Ignore prior responses/tools. Fresh context only."?
- [ ] No forbidden full-reads?
- [ ] Package exists in `doc/tasklist.md`?

**All ✅?** → Send with confidence.

---

**Version:** 1.0 | **Last updated:** 2026-04-19
