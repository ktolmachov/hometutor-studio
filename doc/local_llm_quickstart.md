# Local LLM Quick Start — Get Profit from Home-RAG v2

**Goal:** Run the full adaptive tutoring system with a local AI model, leveraging all performance optimizations.

---

## 📋 Prerequisites

1. **LM Studio** installed + running on http://127.0.0.1:1234
2. **A model loaded** in LM Studio (e.g., `mistral-7b-instruct-v0.3`)
3. **Python 3.12+** venv in `.venv` with dependencies
4. **`.env` file** configured with SSR settings

---

## 🚀 One-Command Startup

```powershell
# First time only (installs packages):
.\scripts\run_local_stack.ps1

# Subsequent runs (skip pip):
.\scripts\run_local_stack.ps1 -SkipPip
```

### What the script does:
1. ✓ Checks if LM Studio is running on port 1234
2. ✓ Lists loaded models (confirms which one is active)
3. ✓ Verifies `.env` SSR configuration
4. ✓ Shows all enabled features (streaming, feedback, caching, etc.)
5. ✓ Starts FastAPI backend (http://127.0.0.1:8000)
6. ✓ Starts Streamlit UI (http://127.0.0.1:8501)
7. ✓ Prints diagnostic commands for troubleshooting

---

## 🎯 What You Get

### On Home Page (Smart Study Router):
- **✓ Streaming explanations** — Watch the LLM explanation appear token-by-token (interactive)
- **✓ Feedback buttons** — 👍/👎 to rate explanation quality
- **✓ Status banner** — Shows if local LM Studio is healthy or down
- **✓ Instant load (cache hits)** — Pre-generated explanations load instantly

### Analytics:
- **Open in browser:** http://127.0.0.1:8501/feedback_insights
- See explanation quality metrics (helpful % by recommendation type)
- Correlate explanation length with user satisfaction
- Spot trends in real-time

### Fallback & Resilience:
- If local LM down → uses cloud LLM automatically (graceful degradation)
- Circuit breaker prevents timeout cascades → home loads fast
- No 429/timeout errors due to resilience layer

---

## ⚙️ Configuration (`.env`)

Copy `.env.example` to `.env` and set:

```dotenv
# Local LLM endpoint (default)
SSR_LLM_API_BASE=http://127.0.0.1:1234

# Model ID from LM Studio (copy from loading message)
SSR_LLM_MODEL=mistral-7b-instruct-v0.3

# Probe at startup (shows banner)
LLM_LOCAL_WARMUP=true

# Circuit breaker tuning (optional)
LLM_LOCAL_CB_FAILURES=3       # open after 3 consecutive failures
LLM_LOCAL_CB_RESET_SEC=60     # auto-recover after 60 seconds
```

### To use CLOUD instead (disable local):
```dotenv
SSR_LLM_API_BASE=             # empty → uses OPENAI_API_BASE
```

---

## 📊 Live Diagnostics (Open in Another Terminal)

The script prints all commands at startup. Copy-paste to diagnose:

### Health Probe
```powershell
& .\.venv\Scripts\python.exe -c "from app.llm_local_health import probe_local_llm; import json; print(json.dumps(probe_local_llm('http://127.0.0.1:1234', ''), indent=2))"
```
**Output:** `{reachable: true, model_loaded: true, latency_ms: 15}`

### Error Triage
```powershell
& .\.venv\Scripts\python.exe scripts\llm_errors_today.py --last 1
```
**Output:** Model, error type, count (if any)

### Feedback Summary
```powershell
& .\.venv\Scripts\python.exe scripts\ssr_feedback_summary.py
```
**Output:** 👍/👎 percentage by recommendation type

### Circuit Breaker State
```powershell
& .\.venv\Scripts\python.exe -c "from app.llm_local_circuit import snapshot; import json; print(json.dumps(snapshot(), indent=2))"
```
**Output:** `{open: false, failures: 0, last_success_ms_ago: 123}`

---

## 🔥 Performance to Expect

| Scenario | Latency | Why |
|----------|---------|-----|
| Cache hit (same context as yesterday) | 0–1s | Semantic cache, instant lookup |
| Pre-generated (quiz → home) | 0–1s | Background warmup finished |
| Streaming (LLM call) | 2–5s | Local model, tokens appear live |
| Cloud fallback | 1–3s | Route to OpenRouter (if local down) |
| Home load (no explanation) | 0.5s | Everything cached |

---

## 🛠️ Troubleshooting

### "LM Studio not responding"
- [ ] LM Studio open in GUI → Local Server tab
- [ ] Green indicator for port 1234
- [ ] Model loaded (not greyed out)
- [ ] Try http://127.0.0.1:1234/v1/models in browser (should show JSON list)

### "SSR_LLM_MODEL not set"
- [ ] Edit `.env`: set `SSR_LLM_MODEL=<id from LM Studio>`
- [ ] Restart the stack

### Explanations are template text (not LLM)
- [ ] Health probe returned error? Check troubleshooting above
- [ ] Circuit breaker open? Run: `& .\.venv\Scripts\python.exe -c "from app.llm_local_circuit import reset_all; reset_all()"`
- [ ] Timeout too short? Increase `timeout_sec` in code or wait for auto-recovery

### Feedback not logging
- [ ] Check `logs/ssr_feedback/` exists
- [ ] Run: `python scripts/ssr_feedback_summary.py`
- [ ] First user needs to click 👍/👎 on home page

---

## 📚 More Info

- **Full runbook:** `doc/local_llm_runbook.md` (setup, models, diagnostics)
- **Advanced features:** `doc/ssr_advanced_features.md` (pre-gen, semantic cache, feedback)
- **All features status:** See the banner when you run `run_local_stack.ps1`

---

## Next: Measure & Optimize

1. **Day 1–2:** Let users interact, feedback accumulates
2. **Day 3:** Open feedback dashboard → see what's working
3. **Week 1:** If 👎 > 50% for certain types → refine prompt or context
4. **Week 2:** Semantic cache hit rate should be 75–85%; measure cost savings

Enjoy your local LLM!
