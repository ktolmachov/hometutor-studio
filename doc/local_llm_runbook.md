# Local LLM Runbook — Smart Study Router («Почему сейчас»)

**Last updated:** 2026-05-12  
**Scope:** LM Studio + SSR `why_now` personalisation on `http://127.0.0.1:1234`  
**Audience:** Developer / Ops — first-line troubleshooting and config

---

## 1. Architecture at a Glance

```
Streamlit UI
  └─ render_smart_study_next_step_card()
       └─ stream_ssr_explanation()          ← streaming tokens
            └─ get_ssr_llm_resolved()       ← picks local or falls back to main LLM
                 ├─ LM Studio (loopback)    ← http://127.0.0.1:1234/v1
                 └─ main LLM_MODEL         ← fallback when loopback unreachable

FastAPI startup
  └─ _llm_local_warmup_background()         ← probes /v1/models, seeds circuit-breaker

Circuit breaker (app/llm_local_circuit.py)
  └─ blocks calls when LM Studio is down → prevents N×timeout per page load
```

**Fallback chain:** LM Studio → main cloud LLM → `why_now_ru` template string.  
The UI always renders; only the quality of the «Почему сейчас» paragraph degrades.

---

## 2. LM Studio — First-Time Setup

### 2.1 Installation

1. Download **LM Studio** ≥ 0.3.5 from https://lmstudio.ai  
2. Install and open it.  
3. Go to **Local Server** tab (left sidebar, server icon).

### 2.2 Start the Local Server

| Setting | Value |
|---------|-------|
| Port | **1234** |
| CORS | enabled (allow all origins for local dev) |
| Verbose logging | optional |

Click **Start Server**. The status indicator turns green.  
Verify: `curl http://127.0.0.1:1234/v1/models` — should return JSON with `"object": "list"`.

### 2.3 Load a Model

Navigate to **Model Browser**, download and load one of the compatible models below.

After loading, re-check `/v1/models` — the model ID must appear in the response.

---

## 3. Compatible Models (tested / recommended)

| Model | VRAM | Context | Quality | Notes |
|-------|------|---------|---------|-------|
| `mistral-7b-instruct-v0.3` | 5–6 GB | 32k | ★★★★☆ | Good instruction follow, Russian OK |
| `qwen2.5-7b-instruct` | 5–6 GB | 128k | ★★★★☆ | Excellent Russian, long context |
| `llama-3.2-3b-instruct` | 2–3 GB | 128k | ★★★☆☆ | Fast, lower VRAM, lightweight |
| `phi-3.5-mini-instruct` | 2–3 GB | 128k | ★★★☆☆ | Very fast, weaker Russian |
| `gemma-2-9b-it` | 7–8 GB | 8k | ★★★★☆ | Strong reasoning, more VRAM |

**Minimum system requirements:** 8 GB RAM + 6 GB VRAM (or CPU-only with 16 GB RAM, slower).

**How to find the model ID** in LM Studio: hover over the loaded model chip — the identifier shown (e.g. `mistral-7b-instruct-v0.3`) is what you put in `SSR_LLM_MODEL`.

---

## 4. Environment Variables

Copy `.env.example` → `.env` and set these for local LLM:

```dotenv
# LM Studio endpoint (default — set explicitly for clarity)
SSR_LLM_API_BASE=http://127.0.0.1:1234

# No key needed for loopback; any non-empty string satisfies validation
SSR_LLM_API_KEY=lm-studio

# Model ID as shown in LM Studio (must match the loaded model exactly)
SSR_LLM_MODEL=mistral-7b-instruct-v0.3

# Startup health probe — keep true to surface problems early
LLM_LOCAL_WARMUP=true

# Circuit-breaker tuning (defaults shown)
LLM_LOCAL_CB_FAILURES=3       # open after N consecutive failures in window
LLM_LOCAL_CB_RESET_SEC=60     # auto-half-open after N seconds
LLM_LOCAL_CB_WINDOW_SEC=30    # failure-counting window
```

**To use the same cloud LLM for SSR** (no local model needed):
```dotenv
SSR_LLM_API_BASE=             # empty → uses OPENAI_API_BASE
SSR_LLM_MODEL=                # empty → uses LLM_MODEL
```

---

## 5. Diagnostic Commands

### 5.1 One-Shot Health Probe

```bash
# Python health probe — same logic as startup warmup
python - <<'EOF'
from app.llm_local_health import probe_local_llm
import json, os

base = os.getenv("SSR_LLM_API_BASE", "http://127.0.0.1:1234")
model = os.getenv("SSR_LLM_MODEL", "")
print(json.dumps(probe_local_llm(base, model), indent=2))
EOF
```

Expected healthy output:
```json
{
  "reachable": true,
  "model_loaded": true,
  "latency_ms": 12.4,
  "error": null,
  "skipped": false
}
```

### 5.2 Circuit-Breaker Snapshot

```bash
python - <<'EOF'
from app.llm_local_circuit import snapshot
import json
print(json.dumps(snapshot(), indent=2))
EOF
```

If `"open": true` — the circuit tripped. Reset with:
```bash
python -c "from app import llm_local_circuit; llm_local_circuit.reset_all(); print('reset OK')"
```
*(Circuit auto-resets after `LLM_LOCAL_CB_RESET_SEC` seconds too.)*

### 5.3 Error Triage from Cost Logs

```bash
# Today's LLM errors grouped by model/stage/type
python scripts/llm_errors_today.py

# Specific date
python scripts/llm_errors_today.py --date 2026-05-11

# Last N days
python scripts/llm_errors_today.py --last 3

# All history
python scripts/llm_errors_today.py --all
```

Sample output:
```
model                    error_type          stage              count
-----------------------  ------------------  -----------------  -----
gpt-5-mini               APIConnectionError  ssr_why_now        3
```

### 5.4 SSR LLM Profile Summary

```bash
python scripts/summarize_ssr_llm_profiles.py
```

Shows outcome distribution (`llm_success`, `template_fallback_*`, `cache_hit`) and p50/p95 latency.  
Raw JSONL logs: `logs/ssr_llm_profiles/ssr_llm_profile_YYYY-MM-DD.jsonl`

### 5.5 Direct curl Tests

```bash
# List models
curl -s http://127.0.0.1:1234/v1/models | python -m json.tool

# Test chat completion
curl -s http://127.0.0.1:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-7b-instruct-v0.3",
    "messages": [{"role": "user", "content": "Ответь одним словом: цвет неба?"}],
    "max_tokens": 10
  }' | python -m json.tool
```

---

## 6. Troubleshooting Checklist

### «Почему сейчас» shows template text (no LLM personalisation)

Work through the checklist in order:

- [ ] **LM Studio server running?** Check the green indicator in LM Studio.
- [ ] **Port matches?** Default is **1234** (LM Studio default). If you changed it, set `SSR_LLM_API_BASE=http://127.0.0.1:<your-port>` in `.env`.
- [ ] **Model loaded?** `/v1/models` must return your model ID.
- [ ] **`SSR_LLM_MODEL` set correctly?** Value must match exactly what `/v1/models` returns.
- [ ] **Circuit open?** Run snapshot (§5.2). If open, restart LM Studio and reset circuit.
- [ ] **App restarted after `.env` change?** `config.reset_settings_cache()` is needed or restart FastAPI + Streamlit.

### Streamlit banner shows «LM Studio unreachable»

The startup warmup probe failed. Causes:
- LM Studio not running
- Wrong port in `SSR_LLM_API_BASE`
- Firewall blocking loopback (rare on Windows; check Windows Defender)

### Streamlit banner shows «model not loaded»

LM Studio server is up but no model is loaded. In LM Studio: **Model Browser → select model → Load**.

### Very slow responses (>10 s)

- Check VRAM usage: if model is swapped to RAM/disk, reduce model size.
- Enable **GPU offloading** in LM Studio (Layers to GPU slider).
- Try a smaller model (3B instead of 7B).
- The prompt budget is ≤400 tokens; if a model is slow at that size, check if it is quantised (Q4/Q5 are fastest).

### `APIConnectionError` in logs

LM Studio process crashed mid-session. Restart it and run the health probe to confirm recovery.

### `model_not_found` / `404` error

Model ID in `SSR_LLM_MODEL` doesn't match what LM Studio has loaded. Use `/v1/models` to get the exact string.

### Repeated `template_fallback_timeout` in profiles

SSR explanation takes longer than the configured timeout. Either:
- Reduce `SSR_LLM_EXPLANATION_TIMEOUT_SEC` if responses arrive but are slow (accept lower quality)
- Load a faster/smaller model
- Increase available GPU layers in LM Studio

---

## 7. Key Code References

| Component | File | Purpose |
|-----------|------|---------|
| Health probe | `app/llm_local_health.py` | `GET /v1/models`, returns `{reachable, model_loaded, latency_ms}` |
| Circuit breaker | `app/llm_local_circuit.py` | Per-endpoint open/close state, configurable threshold/window |
| Startup warmup | `app/api.py` `_llm_local_warmup_background()` | Daemon thread, seeds circuit state at boot |
| Bootstrap field | `app/api_services.py` `get_ui_bootstrap()` | Exposes `llm_local` probe result to UI |
| UI banner | `app/ui/llm_local_banner.py` | `render_llm_local_banner(bootstrap_payload)` |
| LLM resolver | `app/provider.py` `get_ssr_llm_resolved()` | Picks local or falls back to main cloud LLM |
| Streaming | `app/ui/adaptive_plan_llm_enrichment.py` `stream_ssr_explanation()` | Token generator, cache + circuit-aware |
| Blocking call | `app/ui/adaptive_plan_card.py` `_generate_llm_explanation()` | Used when streaming not supported |
| Error triage | `scripts/llm_errors_today.py` | Reads cost_logs JSONL, groups ERR records |
| Profile summary | `scripts/summarize_ssr_llm_profiles.py` | Outcome distribution + latency percentiles |

---

## 8. Turning Off Local LLM (Cloud-Only Mode)

If you don't want to run LM Studio at all, route SSR through the main cloud endpoint:

```dotenv
SSR_LLM_API_BASE=      # empty — uses OPENAI_API_BASE
SSR_LLM_MODEL=         # empty — uses LLM_MODEL
LLM_LOCAL_WARMUP=false # skip startup probe
```

The health probe will return `{"skipped": true}` and no banner will appear.

---

## 9. Resetting Everything

```bash
# Clear circuit-breaker state (in-memory only, resets on restart anyway)
python -c "from app import llm_local_circuit; llm_local_circuit.reset_all()"

# Clear SSR explanation cache (in-memory)
python -c "from app.ui.adaptive_plan_card import _SSR_LLM_EXPLANATION_CACHE; _SSR_LLM_EXPLANATION_CACHE.clear()"

# Rotate profile logs (archive today's file)
python -c "
from datetime import date
from pathlib import Path
src = Path('logs/ssr_llm_profiles') / f'ssr_llm_profile_{date.today()}.jsonl'
if src.exists():
    src.rename(src.with_suffix('.jsonl.bak'))
    print('archived', src)
"
```
