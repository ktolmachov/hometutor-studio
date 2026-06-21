# Gemma 4B Quality Assessment Plan

**Date:** 2026-05-13  
**Change:** Switched from OpenRouter `gpt-5-mini` (cloud API, 20-40s latency) to local LM Studio `google/gemma-4-e4b` (local inference, 5-10s latency)

---

## Rationale for Switch

**Problem:** Chat latency was 65+ seconds on first query, 27-32 seconds on subsequent queries
- Cloud API latency (OpenRouter): 20-40 seconds per request
- Retrieval + token overhead: 5-10 seconds  
- Token bloat: 18.7k tokens → reduced to 9-10k with top_k=2

**Solution:** Replace cloud LLM with local inference
- **Eliminated:** Cloud API latency bottleneck (20-40s per request)
- **Tradeoff:** Gemma 4B is smaller model (4B params) vs GPT-5-mini (much larger)
- **Result:** Acceptable latency (27-32s → 5-10s local inference)

---

## Quality Monitoring Plan

### 1. Manual Spot Checks (Daily)
Test 2-3 representative questions across different knowledge areas:

**Sample questions to test:**
- Simple factual retrieval (index, file structure)
- Multi-step reasoning (how-tos, procedures)
- Cross-document synthesis (comparing concepts)

**Success criteria:**
- ✅ Answer is coherent and grammatically correct
- ✅ Answer directly addresses the question
- ✅ Retrieved sources are relevant to the query
- ✅ No hallucinations or made-up information

### 2. Quality Metrics to Track

| Metric | Threshold | How to Measure |
|--------|-----------|---|
| **Source Hit Rate** | ≥ 70% | % of queries where expected docs are in top-2 retrieved sources |
| **Answer Relevancy** | ≥ 0.6 (Jaccard) | Lexical similarity between answer and reference answer |
| **Answer Coherence** | ✓ Manual review | Is the text grammatically correct and logically structured? |
| **Hallucination Rate** | ≤ 5% | % of answers containing made-up facts not in sources |

### 3. Regression Tests

Run quality benchmark periodically:
```bash
python scripts/run_quality_benchmark.py --report-json /tmp/gemma_benchmark.json
```

Expected baseline from previous runs (GPT-5-mini):
- Hit rate: ~70-80%
- MRR: ~0.65-0.75
- Word Jaccard: ~0.55-0.65

**Expected with Gemma 4B:** 
- Hit rate: ~60-75% (slightly lower due to smaller model)
- MRR: ~0.60-0.70 (acceptable variance)
- Word Jaccard: ~0.50-0.60 (may be more concise/different phrasing)

### 4. Production Monitoring

Track in logs/dashboards:
- Answer generation time (should be 5-10s local vs 20-40s cloud)
- User feedback thumbs up/down (if implemented)
- Error rates in answer generation
- Timeout/latency SLO violations

---

## Known Limitations of Gemma 4B

1. **Smaller model capacity** (4B params)
   - May generate shorter answers
   - Potential for more straightforward/less nuanced responses
   - Acceptable for FAQ-style Q&A, tutoring guidance

2. **Token reduction to top_k=2**
   - Halved context from 18.7k → 9-10k tokens
   - Reduced retrieval breadth (top-10 docs → top-2 docs)
   - Risk: Miss relevant context if top-2 don't cover the topic
   - Mitigation: BM25 + vector RRF fusion still effective for most queries

3. **Inference speed consistency**
   - Local inference depends on hardware (CPU/GPU)
   - May vary by query complexity (longer context = slower)
   - Still 3-5x faster than cloud API

---

## Fallback Options If Quality Degrades

If quality metrics fall below thresholds:

| Option | Pros | Cons |
|--------|------|------|
| **Revert to GPT-5-mini** | Proven quality, no regression risk | 20-40s latency per query (unacceptable UX) |
| **Switch to larger local model** (Gemma 3-12B or Qwen3-8B) | Better quality, still local | Slower inference (10-20s), higher memory/VRAM |
| **Hybrid: Use Gemma for fast queries, GPT for complex** | Optimize per query complexity | Complex orchestration, inconsistent UX |
| **Increase top_k back to 4-5** | More context, better coverage | Longer inference time (10-15s) |

---

## Decision Points

**Week 1 (By 2026-05-20):** Spot-check 10-15 queries
- If answers are coherent and sources are relevant: Continue
- If significant quality drops: Escalate to fallback options

**Week 2 (By 2026-05-27):** Run full quality benchmark
- If metrics ≥ 70% hit rate: Accept Gemma 4B as baseline
- If metrics < 60% hit rate: Trigger investigation/fallback

**Week 3+ (Ongoing):** Monthly quality audits
- Track trends in user feedback
- Monitor performance stability
- Plan migration to larger model if needed

---

## Implementation Notes

- **.env configuration:** 
  ```
  LLM_MODEL=google/gemma-4-e4b
  OPENAI_API_BASE=http://127.0.0.1:1234/v1
  ```

- **LM Studio requirements:**
  - Must have Gemma 4B model loaded and running
  - API endpoint reachable at `127.0.0.1:1234/v1`
  - Fallback circuit-breaker prevents timeouts on first request

- **Monitoring dashboard:**
  - Check logs for "llm_local_warmup_ok" at startup
  - Track "answer_generation_latency_ms" in query logs
  - Alert if inference time > 30s (anomaly indicator)

---

**Next Review:** 2026-05-27 (after 2-week production trial)
