# Testing the Performance Fixes

**Date:** 2026-05-13  
**Fixes to Test:**
1. ✅ BM25 cache warmup (aligned to profile)
2. ✅ Multi-variant BM25 cache (dict-based)
3. ✅ Token reduction (top_k=2 for fast profile)
4. ✅ Local Gemma 4B LLM (5-10s latency)
5. ✅ Mastery dashboard caching

---

## 🚀 Setup & Start

### 1. Start LM Studio (Required for Gemma 4B)
```bash
# Windows: Open LM Studio, Load "Gemma 4B" model
# Ensure running at http://127.0.0.1:1234
# Check it's ready with: curl http://127.0.0.1:1234/api/v1/models
```

### 2. Start the API Server
```bash
cd C:\Users\Dragon\Exchange\home-rag_v2
python main.py
# OR with uvicorn directly:
# uvicorn app.api:app --host 0.0.0.0 --port 8000
```

### 3. Watch Startup Logs
Look for these messages in order (should complete in <10 seconds):
```
✓ "Retrieval base services warmed up at startup." (line 152)
✓ "BM25 cache warmed up at startup | profile=fast | top_k=2" (line 45, new)
✓ "Topics catalog warmed up at startup."
✓ "Source readiness warmed up at startup."
✓ "Index stats warmed up at startup."
✓ "llm_local_warmup_ok" (Gemma 4B check)
```

**✅ Success:** All warmup messages appear in <10 seconds  
**❌ Failure:** Missing "BM25 cache warmed up" or Gemma latency > 5s

---

## 📊 Test 1: Verify BM25 Cache Working

### Test Query (Simple Factual)
```
Question: "What files are in the app directory?"
Expected: Answer mentions app/api.py, app/config.py, etc.
```

### Check Logs for Cache Hit
After the first query, look for:
- **First query (cold):** `BM25Retriever built and cached | nodes=... | top_k=2 | total_cached=1`
- **Second query (hit):** `BM25Retriever cache hit | top_k=2 | cached_variants=1`

**✅ Success:** See "cache hit" log on 2nd+ queries  
**❌ Failure:** See "BM25Retriever built" on every query (cache miss)

### Latency Check
- **First query:** 25-35 seconds (includes BM25 build)
- **Second query:** 20-30 seconds (faster, no BM25 build)

**✅ Success:** 2nd query is 5-10 seconds faster  
**❌ Failure:** Both queries same speed (~30s)

---

## 📊 Test 2: Verify Token Reduction

### Check .env Configuration
```bash
cat .env | grep -E "^(RAG_PROFILE|SIMILARITY_TOP_K|LLM_MODEL)="
```

**Expected output:**
```
RAG_PROFILE=fast
SIMILARITY_TOP_K=10
LLM_MODEL=qwen2.5-coder-7b-instruct
```

### Test Query with Token Counting
```
Question: "Explain the query service architecture"
Expected: Answer ~2000-3000 tokens
```

**✅ Success:** Answer is coherent but concise (~30-40 seconds response time)  
**❌ Failure:** Answer cuts off or takes >45 seconds

---

## 📊 Test 3: Verify Gemma 4B Quality

### Test 3a: Coherence Test
```
Question: "How do I run the quality benchmark?"
Expected: Step-by-step instructions with file paths
Success Criteria:
  ☐ Answer is grammatically correct
  ☐ Steps are in logical order
  ☐ File paths are real (e.g., scripts/run_quality_benchmark.py)
  ☐ No cut-off sentences
```

### Test 3b: Accuracy Test
```
Question: "What is the default RAG profile?"
Expected: "fast" (from config.py or .env)
Success Criteria:
  ☐ Answer mentions "fast" as default
  ☐ No hallucinated alternatives
  ☐ Sources reference config files
```

### Test 3c: Source Relevance Test
```
Question: "How does BM25 retrieval work?"
Expected: Sources from hybrid_retrieval.py and related files
Success Criteria:
  ☐ Retrieved sources mention BM25, hybrid, or retrieval
  ☐ No sources about unrelated topics (e.g., UI, Streamlit)
  ☐ Top 2-3 sources are most relevant
```

**Overall Quality Score:**
- 3/3 tests pass → ✅ Quality acceptable
- 2/3 tests pass → ⚠️ Quality borderline
- <2 tests pass → ❌ Quality degraded, escalate

---

## 📊 Test 4: Verify Mastery Dashboard Caching

### Setup
1. Open the Streamlit UI
2. Navigate to the "Dashboard" or "Mastery" section
3. Open browser DevTools → Network tab
4. Filter for API calls to `/dashboard/mastery`

### Test
1. Click "Refresh" button multiple times (< 5 seconds apart)
2. Watch network tab for API calls

**✅ Success:**
- First click triggers API call
- Subsequent clicks (within 30 seconds) do NOT trigger new API calls
- After 30 seconds of inactivity, next click triggers fresh call

**❌ Failure:**
- Every click triggers a new API call
- Network tab shows 5+ calls to `/dashboard/mastery` in quick succession

---

## 📊 Test 5: Verify Bootstrap Performance

### Measure Bootstrap Time
```bash
# In browser console (DevTools):
# Capture the Network tab and measure time from page load to "DOMContentLoaded"
# OR measure time from click to "Home" page fully interactive
```

**Expected timings:**
- Old: 4934ms (4.9 seconds)
- New: 247ms (0.25 seconds) - but with Gemma warmup overhead
- Realistic: 500-1500ms depending on hardware

**✅ Success:** Page fully interactive in <2 seconds  
**❌ Failure:** Page takes >3-4 seconds to load

---

## 🔍 Log Analysis Checklist

### Startup Logs (First 30 seconds)
```
grep -E "warmed up|warmup|Initializing|BM25" <log-file>
```

**✅ Expected to see (in order):**
- [ ] "Retrieval base services warmed up at startup"
- [ ] "BM25 cache warmed up at startup | profile=fast | top_k=2"
- [ ] "Topics catalog warmed up at startup"
- [ ] "llm_local_warmup_ok" (Gemma 4B check)

**❌ Should NOT see:**
- [ ] "Initializing retrieval base services" during first query (this was the bug!)
- [ ] "BM25Retriever built" at query time (cache should hit)

### Query Logs (During test queries)
```
grep -E "cache hit|cache miss|BM25Retriever built|answer_generation_latency" <log-file>
```

**✅ Expected patterns:**
- First query: `BM25Retriever built ... top_k=2`
- Second query: `BM25Retriever cache hit | top_k=2`
- Later queries: `cache hit` messages

### Latency Tracking
```
grep -i "latency_ms\|generation_time\|inference" <log-file>
```

**✅ Expected:**
- Inference latency: 5-10 seconds (Gemma local)
- Retrieval latency: 2-4 seconds
- Total: 7-14 seconds per query (with RRF fusion)

---

## 📋 Test Summary Template

Copy this after testing:

```
Date: ____-____-____
Environment: [Windows/Linux/Mac], Python ___

STARTUP LOGS:
☐ All warmup threads completed
☐ No errors in BM25 warmup
☐ Gemma 4B health check passed
Status: [PASS / FAIL]

TEST 1: BM25 Cache
- First query latency: ___ seconds
- Second query latency: ___ seconds
- Cache hit logs: [YES / NO]
Status: [PASS / FAIL]

TEST 2: Token Reduction
- RAG_PROFILE: [fast / quality / other]
- Answer token count: ___
- Response time: ___ seconds
Status: [PASS / FAIL]

TEST 3: Gemma 4B Quality
- Coherence: [PASS / WARN / FAIL]
- Accuracy: [PASS / WARN / FAIL]
- Source relevance: [PASS / WARN / FAIL]
Overall: [PASS / BORDERLINE / FAIL]

TEST 4: Mastery Dashboard
- First API call: [TRIGGERED / SKIPPED]
- Subsequent calls (5 sec): [CACHED / API CALLED]
Status: [PASS / FAIL]

TEST 5: Bootstrap
- Page interactive time: ___ ms
- Improvement: [20x faster / OK / SLOW]
Status: [PASS / FAIL]

OVERALL RESULT: [ALL PASS / MOSTLY PASS / ISSUES FOUND]
Issues: _________________
Recommendations: _________________
```

---

## 🚨 If Tests Fail

### Gemma 4B Quality Issues
**Symptom:** Answers are short, incoherent, or hallucinating facts  
**Fix:** Switch to larger model:
```bash
# Edit .env
LLM_MODEL=google/gemma-3-12b  # Larger model (slower)
# OR revert to cloud API
OPENAI_API_BASE=https://openrouter.ai/api/v1
LLM_MODEL=gpt-5-mini
```

### BM25 Cache Not Hitting
**Symptom:** "BM25Retriever built" appears on every query  
**Check:**
- Are logs showing `BM25 cache warmed up at startup`?
- Is RAG_PROFILE set to "fast"?
- Run: `grep "BM25Retriever" <logfile>` to see pattern

### Mastery Dashboard Still Over-Polling
**Symptom:** Network tab shows 30+ calls to `/dashboard/mastery`  
**Check:**
- Did app restart with new code?
- Check `app/ui/home_hub.py` line ~75 for `@st.cache_data(ttl=30)`
- Restart Streamlit: `pkill streamlit` then re-run

### Latency Still High (>30s)
**Check:**
1. Is Gemma 4B actually running? `curl http://127.0.0.1:1234/api/v1/models`
2. Is top_k=2 in use? Check logs for "top_k=2" in BM25 cache
3. Latency breakdown: Add `print(time.time())` in logs at each step

---

## ✅ Success Criteria

All 5 tests pass:
1. ✅ BM25 cache hits on subsequent queries
2. ✅ Bootstrap time <2 seconds
3. ✅ Token count reduced (9-10k tokens)
4. ✅ Gemma 4B quality acceptable (coherent answers, no hallucinations)
5. ✅ Mastery dashboard debounced (cached)

If all pass → Production ready ✅  
If 4/5 pass → Acceptable with monitoring 🟡  
If <4 pass → Investigate failures before deploying 🔴

---

**Ready to test?** Start with Step 1 and work through the checklist!
