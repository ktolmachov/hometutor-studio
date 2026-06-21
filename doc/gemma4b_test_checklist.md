# Gemma 4B Quick Quality Checklist

**Use this after each chat session to spot-check answer quality**

---

## ✅ Quick Tests (5-10 minutes per session)

### Test 1: Simple Factual Question
```
Question: "What is the file structure of the project?"
Expected: Answer lists main directories, references docs, config files

Check:
☐ Answer mentions real files/directories from your knowledge base
☐ Information is accurate (not made up)
☐ Answer is concise but complete
☐ Retrieved sources show up in the answer context
```

### Test 2: How-To / Procedural Question
```
Question: "How do I run the quality benchmark?"
Expected: Step-by-step instructions with relevant file paths

Check:
☐ Steps are in logical order
☐ Command names and file paths are correct (not hallucinated)
☐ Answer includes example usage or code snippets
☐ Sources reference the actual script files
```

### Test 3: Cross-Document Synthesis
```
Question: "What's the difference between the tutor module and quiz module?"
Expected: Comparison of features, use cases, or architecture

Check:
☐ Answer clearly contrasts the two concepts
☐ References are factually grounded (not made up)
☐ Explanation is understandable without deep domain knowledge
☐ Retrieved sources cover both modules
```

---

## 🔴 Red Flags to Watch For

| Red Flag | Example | Action |
|----------|---------|--------|
| **Hallucinated code** | Answer shows syntax that doesn't exist in files | ⚠️ Check if model confused similar code |
| **Made-up file paths** | References `/app/nonexistent_module.py` | 🚫 Indicates retrieval failure or LLM hallucination |
| **Contradictory facts** | Says "FastAPI on port 8000" then "Streamlit on port 8000" | ⚠️ Model confusion or conflicting sources |
| **Incomplete answers** | Sentence cuts off mid-word or thought | 🚫 Token limit reached or inference error |
| **Irrelevant sources** | Retrieved docs don't match the question | 🚫 Retrieval ranking issue (BM25 or vector) |
| **No sources** | Answer given but "sources" list is empty | 🚫 Retrieval failure |

---

## 📊 Success Criteria

**After 3 test queries, assess overall quality:**

| Metric | Expected | Your Result |
|--------|----------|-------------|
| **Coherence** | All 3 answers are grammatically correct | ☐ YES / ☐ NO / ☐ PARTIAL |
| **Accuracy** | No hallucinated facts in any answer | ☐ YES / ☐ NO / ☐ PARTIAL |
| **Relevance** | Sources are clearly related to questions | ☐ YES / ☐ NO / ☐ PARTIAL |
| **Response time** | Answers return in 5-15 seconds | ☐ YES / ☐ NO / ☐ SLOW |

**Result:**
- ✅ 4/4 criteria met → Quality acceptable, continue monitoring
- ⚠️ 2-3 criteria met → Quality borderline, investigate specific issues
- 🚫 <2 criteria met → Quality degraded, escalate to larger model or GPT-5-mini

---

## 🔍 Detailed Quality Assessment (If Needed)

If you want to measure quality more rigorously:

```bash
# Run the quality benchmark on your test KB
python scripts/run_quality_benchmark.py --report-json /tmp/quality_report.json

# Check results:
# - Expected hit_rate >= 0.70 (70%)
# - Expected mrr >= 0.60
# - Expected word_jaccard >= 0.50
```

**Interpret results:**
- Hit rate < 0.70: Check if top_k=2 is filtering out relevant docs
- MRR < 0.60: Retrieved sources not ranked well (BM25/vector hybrid issue)
- Word Jaccard < 0.50: Answer phrasing very different from reference (might be acceptable)

---

## 📋 Session Log Template

Copy this after each testing session:

```
Date: ____
Test Queries: __ / 3 completed

Test 1 - [Topic]: ☐ PASS / ☐ WARN / ☐ FAIL
  Notes: _________________

Test 2 - [Topic]: ☐ PASS / ☐ WARN / ☐ FAIL
  Notes: _________________

Test 3 - [Topic]: ☐ PASS / ☐ WARN / ☐ FAIL
  Notes: _________________

Overall Quality: ☐ ACCEPTABLE / ☐ BORDERLINE / ☐ DEGRADED
Latency: __ sec
Issues Found: _________________
Action Taken: _________________
```

---

## 🎯 What to Do If Quality Degrades

**Step 1: Identify the issue**
- Are all answers wrong? → Model problem (too small/undertrained)
- Are only specific topic answers wrong? → Retrieval problem (top_k=2 too small)
- Are answers cut off? → Token limit (increase context)

**Step 2: Quick fix attempts**
- Clear cache: Restart LM Studio
- Increase top_k: Edit `.env` to `SIMILARITY_TOP_K=4` (slower but more context)
- Test larger model: Swap `LLM_MODEL=google/gemma-3-12b` in `.env`

**Step 3: Escalate if needed**
- If local models still poor: Revert to `OPENAI_API_BASE=https://openrouter.ai/api/v1`
- Accept 20-40s latency for guaranteed quality
- Plan for better local model infrastructure (bigger GPU, more VRAM)

---

**Remember:** Gemma 4B is a tradeoff - smaller but faster. Quality will be good enough for most queries but may not match GPT-5-mini on complex reasoning tasks.
