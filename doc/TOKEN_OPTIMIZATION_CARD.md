# Token Optimization — Quick Reference Card (Printable)

**Version:** 1.0 | **Date:** 2026-04-19 | **Audience:** Agents, Cursor AI, Developers

---

## 🎯 TL;DR — Три Правила

| # | Правило | Действие |
|---|---|---|
| **1** | Перед вызовом проверить токены | `python scripts/check_readset.py file1 file2` |
| **2** | Если BLOCK → использовать grep | `grep "^class\|^def " file.py` |
| **3** | Всегда добавить | `"Ignore prior responses/tools. Fresh context only."` |

**Если все три сделал → отправляй смело. ✅**

---

## ⚡ Быстрый Старт (30 Секунд)

### Шаг 1: Выбрать Шаблон

```
Planning?       → Micro-Plan (doc/agent_workflow.md)
Execution?      → Micro-Execute
Verify?         → Micro-Verify
Architecture?   → Phase 1–5 (разбить на фазы)
```

### Шаг 2: Выписать Read-Set

```
Max 3–5 файлов, не больше
- file1.py (signatures only если >600 lines)
- file2.py (or 1 specific function)
- doc/file.md (or only section needed)
```

### Шаг 3: Валидировать

```bash
python scripts/check_readset.py file1 file2
# Результат: 🟢 SAFE? → ОК, отправляй
#           🟡 WARN? → сжать и переделать
#           🔴 BLOCK? → redesign read-set
```

---

## ❌ FORBIDDEN (Никогда Целиком)

**Эти файлы ЗАПРЕЩЕНО читать полностью:**

```
app/query_service.py (1499 строк, 14k)
    └─ Safe: grep "^class\|^def " app/query_service.py

app/prompts/_impl.py (>1500 строк, ~15k+)
    └─ Safe: rg "^def\|^[A-Z_].*=" app/prompts/_impl.py
app/tutor_prompts.py (small, safe to read fully)
    └─ Bridge/helper for app/prompts/ package

app/knowledge_graph.py (1258 строк, 13k)
    └─ Safe: grep "^class\|^def " app/knowledge_graph.py

tests/test_api.py (1614 строк, 14.1k)
    └─ Safe: Read 1–2 конкретных test cases only

doc/closed_iterations.md (полный)
    └─ Safe: Use doc/epochs/<target>.md instead (1–2k vs 20k)

doc/cjm.md (полный)
    └─ Safe: Read only target pain point/state

doc/epochs/ (папка целиком)
    └─ Safe: Read ONLY 1 epoch file max
```

**Правило:** Если файл в списке выше → используй safe-метод.

---

## ✅ SAFE (Обычно OK)

```
doc/conventions.md          ✅ OK (~710 токенов)
doc/conventions_architecture.md  ✅ OK (~3k)
doc/conventions_reference.md     ✅ OK (~1.9k)
doc/tasklist.md (1 row)     ✅ OK (~50 токенов вместо 1.5k)
app/models.py               ✅ OK (~1.7k)
app/api.py                  ✅ OK (~1.1k)
tests/conftest.py           ✅ OK (~689 токенов)
requirements.txt            ✅ OK (~164 токенов)
```

---

## 🔍 Token Estimates (Reference)

| Файл | Строк | Токены | Max? |
|---|---:|---:|---|
| app/query_service.py | 1499 | ~14k | ❌ FORBIDDEN |
| app/prompts/_impl.py | >1500 | ~15k+ | ❌ FORBIDDEN |
| app/tutor_prompts.py | small | safe | ✅ read in full |
| app/knowledge_graph.py | 1258 | ~13k | ❌ FORBIDDEN |
| app/tutor_orchestrator.py | 641 | ~6.5k | ⚠️ signatures only |
| app/learner_model_service.py | 662 | ~6.4k | ⚠️ 1 method only |
| app/learning_plan_service.py | 592 | ~5.5k | ⚠️ 1 method only |
| app/pipeline_steps.py | 450 | ~4.3k | ⚠️ 1 step only |
| app/config.py | 340 | ~3.7k | ✅ OK if needed |
| doc/adr.md | 544 | ~7.7k | ⚠️ Status table only |
| doc/architecture.md | 383 | ~4.3k | ⚠️ List only |
| doc/changelog.md | 522 | ~12.8k | ⚠️ Last 2–3 rows |
| doc/closed_iterations.md | full | ~20k | ❌ use epochs/ |
| doc/cjm.md | 241 | ~4.9k | ⚠️ 1 pain point |
| tests/test_api.py | 1614 | ~14.1k | ⚠️ 1–2 cases |
| tests/test_query_service.py | 1012 | ~9.8k | ⚠️ 1 fixture |

---

## 📋 Template Cheatsheet

### Planning (3k–5k)

```text
Goal: plan <package>.

Read ONLY (max 3):
1. <code-file>.py — grep only
2. <test-file>.py — 1 case
3. doc/tasklist.md — 1 row

Ignore prior responses/tools.

Output: goal, write-set, DoD, copy-paste prompt
```

**Exit: ✅ SAFE (~5k)**

### Execution (2k–4k)

```text
Goal: close <package>.

Read ONLY (max 2):
- <code-file>.py
- <test-file>.py

Ignore prior responses/tools.

DoD: <command> green
Output: changed files + test result
```

**Exit: ✅ SAFE (~3k)**

### Verify (1k–2k)

```text
Goal: verify <package>.

DoD: <command> → <result>
Diff: <RANGE>

Ignore prior responses/tools.

Steps: 1) Run, 2) Check scope, 3) Verdict
```

**Exit: ✅ SAFE (~2k)**

---

## 🚨 Red Flags (Stop & Fix)

| Flag | Meaning | Fix |
|---|---|---|
| `❌ FORBIDDEN` on file | File too large, must use safe-method | Use grep/head/section from table |
| Input > 12k | Over soft-limit | Remove 1–2 files |
| Input > 20k | Over hard-limit | Redesign read-set |
| History > 3 steps | Accumulation | Fresh context only |
| glm-5.1 used | Wrong model | Use grok-4.1 |
| 3+ retry with same payload | Stuck loop | Compress, then retry |

**Action: If ANY flag → STOP, fix, re-validate.**

---

## 🔧 Common Commands

```bash
# Basic check
python scripts/check_readset.py file1.py file2.py

# With recommendations (--signatures shows grep commands)
python scripts/check_readset.py file.py --signatures

# Custom budget (e.g., 6k soft limit)
python scripts/check_readset.py --budget 6000 file.py

# Custom hard limit
python scripts/check_readset.py --hard 10000 file.py

# No overhead (if system prompt already counted)
python scripts/check_readset.py --overhead 0 file.py

# Help
python scripts/check_readset.py --help
```

---

## 💰 Cost Comparison

| Scenario | Input | Cost | Time |
|---|---|---|---|
| **Old Planning** (full read-set) | 33k | 1.2 ₽ | 30–60s |
| **New Planning** (Micro-Plan) | 3.5k | 0.1 ₽ | 5–10s |
| **Savings** | -89% | **-90%** | **5–10x faster** |

---

## ✨ Model Selection

```
Planning, Execution, Verify:
  └─ grok-4.1 (default, cheap)

Critical architecture only:
  └─ (explicitly approved, expensive model)

NEVER:
  └─ glm-5.1 (4–5x cost, no quality gain)
```

---

## 📞 When Stuck

| Problem | Solution |
|---|---|
| Token count too high | Remove lowest-signal file from read-set |
| File flagged FORBIDDEN | Use safe-method from FORBIDDEN table above |
| Agent reads wrong files | Re-prompt: "Read ONLY: file1, file2, file3" |
| Output too verbose | Add: "Max 300 words" |
| History too large | "Ignore prior responses/tools. Fresh context only." |

---

## 🎓 Learning Path

1. **5 min:** Read this card (you're doing it!)
2. **10 min:** Read `doc/QUICK_READSET_REFERENCE.md`
3. **15 min:** Try `python scripts/check_readset.py` on 3 files
4. **30 min:** Read `doc/token_safety.md` (optional, full reference)
5. **Ready:** Use templates for first planning call

---

## 📌 Bookmarks (Copy These)

```
Quick Ref:           doc/QUICK_READSET_REFERENCE.md
Full Reference:      doc/token_safety.md
Checklist:           doc/archive/token_optimization_checklist.md
Validator Script:    python scripts/check_readset.py
Templates:           doc/agent_workflow.md (Low-Budget section)
```

---

## ✅ Pre-Submit Checklist

Before sending ANY LLM prompt:

- [ ] `python scripts/check_readset.py ... ✅ SAFE`?
- [ ] Model = grok-4.1 (not glm-5.1)?
- [ ] Added: "Ignore prior responses/tools. Fresh context only."?
- [ ] No forbidden full-reads (check table above)?
- [ ] Read-set ≤ 5 files, ideally ≤ 3?
- [ ] Estimated input ≤ 12k?

**All ✅?** → Send with confidence.

---

## 🎯 Success Metrics

After 1 week of using optimized templates:

- Planning calls: 30k → 5k (average)
- Cost per session: 26 ₽ → 12 ₽ (-54%)
- Model speed: 5–10x faster
- Quality regression: 0% (A/B testing)

---

## 📞 Support

- **Validator issues:** `python scripts/check_readset.py --help`
- **Token estimates wrong:** Check `doc/token_safety.md` table
- **File not in table:** Estimate: lines / 100 ≈ tokens (rough)
- **Integration help:** See `doc/archive/IMPLEMENTATION_COMPLETE.md`

---

**Print this. Bookmark this. Share with your team.** 🚀

---

*Last updated: 2026-04-19 | Version: 1.0 | Status: Production Ready*

