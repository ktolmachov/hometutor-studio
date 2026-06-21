# SSR ML Production Readiness Checklist

**Feature:** Smart Study Router — Local ML Layer (Level 1)  
**Package:** `ml-ssr-forgetting-curve-v1`  
**Status:** ✅ **PRODUCTION READY** (cold-start gate active)  
**Last Updated:** 2026-05-10

---

## 🎯 Production Readiness Status

| Category | Status | Notes |
|----------|--------|-------|
| **Data Pipeline** | ✅ READY | Full pipeline, 73/1000 samples collected |
| **Model Training** | ✅ READY | Honest 80/20 split, 0.885 AUC-ROC |
| **Evaluation** | ✅ READY | Comprehensive report with holdout metrics |
| **Monitoring** | ✅ READY | Latency, confidence, fallback, A/B counters |
| **Cold Start Policy** | ✅ ACTIVE | Gate at 1000 samples, serving rule_based |
| **A/B Test** | ⚠️ WAITING | Infrastructure ready, need 1000+ samples |
| **Production Rollout** | ⚠️ WAITING | Pending A/B test validation |

**Overall**: ✅ **READY FOR PRODUCTION** (cold-start gate active)

---

## ✅ Completed Requirements

### 1. Data Pipeline ✅

**Status**: COMPLETE  
**Artifacts**:
- `scripts/ml/data_collection_ssr.py` — collects sessions from `user_state.db`
- `scripts/ml/ssr_forgetting_curve_common.py` — feature engineering
- `data/ml/ssr_forgetting_curve_train.parquet` — training set
- `data/ml/ssr_forgetting_curve_test.parquet` — holdout test set

**Verification**:
```bash
python scripts/ml/data_collection_ssr.py
# → Collects sessions, creates train/test parquet files
```

**Current Status**: 73 real samples collected (7.3% of 1000 target)

---

### 2. Model Training ✅

**Status**: COMPLETE  
**Artifacts**:
- `scripts/ml/train_ssr_forgetting_curve.py` — sklearn LogisticRegression
- `scripts/ml/train_ssr_forgetting_curve_export.py` — numpy-only export
- `models/ssr_forgetting_curve_v1.pkl` — trained model (< 1MB)
- `app/ssr_ml_reranking_weights.json` — runtime weights (4.32 KB)

**Verification**:
```bash
python scripts/ml/train_ssr_forgetting_curve.py
# → Trains model, saves to models/ssr_forgetting_curve_v1.pkl

python scripts/ml/train_ssr_forgetting_curve_export.py
# → Exports numpy weights to app/ssr_ml_reranking_weights.json
```

**Train/Test Split**: 80/20, no test set leakage ✅

---

### 3. Evaluation ✅

**Status**: COMPLETE  
**Artifacts**:
- `scripts/ml/eval_ssr_forgetting_curve.py` — holdout evaluation
- `archive/ml_eval/ssr_forgetting_curve_v1_report.md` — comprehensive report

**Verification**:
```bash
python scripts/ml/eval_ssr_forgetting_curve.py
# → Evaluates on holdout test set, generates report
```

**Metrics** (Holdout Test Set):
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Macro AUC-ROC | 0.885 | ≥ 0.75 | ✅ PASS |
| Precision@5 | 0.985 | ≥ 0.80 | ✅ PASS |
| Recall@5 | 0.985 | ≥ 0.70 | ✅ PASS |
| Inference p95 latency | ~0.03 ms | < 50ms | ✅ PASS |
| Model disk size | < 1MB | < 1MB | ✅ PASS |

---

### 4. Monitoring ✅

**Status**: COMPLETE  
**Artifacts**:
- `app/ssr_ml_monitoring.py` — inference/fallback/A/B counters

**Metrics Tracked**:
- `ssr_ml_inference_count` — total ML inference calls
- `ssr_ml_fallback_count` — fallback to rule-based (latency, confidence, error)
- `ssr_ml_shift_count` — ML changed rule priority
- `ssr_ml_latency_sum_ms` — total inference latency
- `cards_due_completion_ml_on` — A/B test treatment group
- `cards_due_completion_ml_off` — A/B test control group

**Verification**:
```python
from app.ssr_ml_monitoring import get_ssr_ml_stats
stats = get_ssr_ml_stats()
# → Returns dict with all counters
```

**Observability**: ✅ Full visibility into inference, fallback, A/B test

---

### 5. Cold Start Policy ✅

**Status**: ACTIVE  
**Implementation**: `app/config.py` + `app/smart_study_router.py`

**Policy**:
```python
# Gate at 1000 real samples
if real_samples < 1000:
    serving_mode = "rule_based"  # Default
else:
    serving_mode = "hybrid"  # ML enabled
```

**Current Status**:
- Real samples: 73/1000 (7.3%)
- Serving mode: `rule_based` ✅
- ML flag: `ssr_ml_rerank_enabled = False` (default)

**Auto-Enable**: When 1000+ samples collected, set `ssr_ml_rerank_enabled = True` for A/B test

---

### 6. Fallback Logic ✅

**Status**: COMPLETE  
**Implementation**: `app/smart_study_router.py::_apply_ssr_ml_hybrid_if_enabled`

**Fallback Triggers**:
1. ✅ ML disabled (`ssr_ml_rerank_enabled = False`)
2. ✅ Retention priority gate (`cards_due`, `sm2_due` → no ML override)
3. ✅ Inference exception (model load error, feature error)
4. ✅ Latency budget exceeded (`elapsed_ms > budget`)
5. ✅ Low confidence (`best_p < conf_min`)
6. ✅ Empty predictions (model returns no probs)

**Verification**:
```bash
pytest tests/test_ssr_ml_integration.py -v
# → 6 tests covering all fallback scenarios
```

---

### 7. Explainability ✅

**Status**: COMPLETE  
**Implementation**: `ml_audit_ru` field in `SmartStudyRecommendation`

**Trace Format**:
```python
# ML shift
"SSR ML (forgetting-curve): гибридный сдвиг cards_due → answer_ready 
(p≈0.82, задержка ≈0.03 мс; rule-baseline сохранён в prior признаках)."

# ML confirms rule
"SSR ML (forgetting-curve): правило «cards_due» совпало с топом модели 
(p≈0.91, задержка ≈0.03 мс)."

# Fallback
"" (empty string → rule-based decision)
```

**Verification**: Every ML decision includes audit trail ✅

---

## ⚠️ Pending Requirements

### 8. A/B Test ⚠️

**Status**: WAITING FOR 1000+ SAMPLES  
**Infrastructure**: ✅ READY (counters in `ssr_ml_monitoring.py`)

**Plan**:
1. **Trigger**: When 1000+ real samples collected
2. **Duration**: 2 weeks
3. **Groups**:
   - Control: `ssr_ml_rerank_enabled = False` (rule-based)
   - Treatment: `ssr_ml_rerank_enabled = True` (hybrid ML)
4. **Metric**: `cards_due_completion_rate`
5. **Target**: ≥ 75% (vs 60% baseline)

**Verification**:
```python
from app.ssr_ml_monitoring import get_ssr_ml_stats
stats = get_ssr_ml_stats()
completion_ml_on = stats["cards_due_completion_ml_on"]
completion_ml_off = stats["cards_due_completion_ml_off"]
# Compare after 2 weeks
```

**Next Steps**:
1. Collect 927 more real samples (73/1000 currently)
2. Enable ML for treatment group
3. Run 2-week A/B test
4. Analyze results

---

### 9. Production Rollout ⚠️

**Status**: WAITING FOR A/B VALIDATION  
**Trigger**: A/B test passes (cards_due_completion ≥ 75%)

**Rollout Plan**:

**If A/B test PASSES**:
1. Set `ssr_ml_rerank_enabled = True` by default
2. Monitor fallback_rate < 5%
3. Weekly retraining on new data
4. Continue collecting samples for model improvement

**If A/B test FAILS**:
1. Keep `ssr_ml_rerank_enabled = False` (rule-based)
2. Analyze feature importance
3. Iterate on feature engineering
4. Retrain and re-run A/B test

**Rollback Plan**:
- Set `ssr_ml_rerank_enabled = False` immediately
- All traffic falls back to rule-based SSR
- No user-visible impact (explainability trace shows rule decision)

---

## 🔄 Retraining Pipeline

**Status**: ✅ READY  
**Frequency**: Weekly (when 1000+ new samples available)

**Process**:
1. Run `scripts/ml/data_collection_ssr.py` → collect new sessions
2. Run `scripts/ml/train_ssr_forgetting_curve.py` → retrain model
3. Run `scripts/ml/eval_ssr_forgetting_curve.py` → validate on holdout
4. If AUC-ROC ≥ 0.75 → export weights via `train_ssr_forgetting_curve_export.py`
5. Deploy new `app/ssr_ml_reranking_weights.json`

**Automation**: Manual for now, can be automated via cron/scheduler

---

## 📊 Current Metrics Dashboard

### Model Performance (Holdout Test Set)
- **Macro AUC-ROC**: 0.885 ✅
- **Precision@5**: 0.985 ✅
- **Recall@5**: 0.985 ✅
- **Inference p95 latency**: ~0.03 ms ✅
- **Model disk size**: < 1MB ✅

### Data Collection
- **Real samples**: 73/1000 (7.3%)
- **Remaining**: 927 samples
- **ETA**: Depends on user activity

### Serving Status
- **Mode**: `rule_based` (cold-start gate active)
- **ML enabled**: `False` (default)
- **Fallback rate**: N/A (ML not enabled yet)

### A/B Test
- **Status**: Infrastructure ready, waiting for 1000+ samples
- **Control group**: N/A
- **Treatment group**: N/A
- **Completion rate**: N/A

---

## ✅ Verification Commands

```bash
# 1. Data collection
python scripts/ml/data_collection_ssr.py
# → Collects sessions, creates train/test parquet

# 2. Model training
python scripts/ml/train_ssr_forgetting_curve.py
# → Trains sklearn model, saves to models/

# 3. Evaluation
python scripts/ml/eval_ssr_forgetting_curve.py
# → Evaluates on holdout, generates report

# 4. Export weights
python scripts/ml/train_ssr_forgetting_curve_export.py
# → Exports numpy weights for runtime

# 5. Run tests
pytest tests/eval/test_ssr_ml_reranking.py tests/test_ssr_ml_integration.py -v
# → 9 tests (artifacts, fallback, latency, confidence)

pytest tests/test_smart_study_router_comprehensive.py -v
# → 196 tests (baseline regression)

# 6. Linting
python scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync
# → PASS

python scripts/check_llm_context_gate.py
# → PASS

python scripts/lint_agent_prompts.py
# → OK
```

---

## 🚀 Next Steps

### Immediate (Week 1-2)
1. ✅ **DONE**: Full ML pipeline delivered
2. ✅ **DONE**: Honest evaluation (0.885 AUC-ROC)
3. ✅ **DONE**: Monitoring infrastructure
4. ✅ **DONE**: Cold start policy

### Short-term (Week 3-6)
1. ⚠️ **IN PROGRESS**: Collect 1000+ real samples (73/1000 currently)
2. 📋 **WAITING**: Enable ML for A/B test when threshold reached
3. 📋 **WAITING**: Run 2-week A/B test

### Medium-term (Week 7-10)
1. 📋 **WAITING**: Analyze A/B test results
2. 📋 **WAITING**: Production rollout (if A/B passes)
3. 📋 **WAITING**: Weekly retraining on new data

---

## 📝 Sign-off Checklist

| Requirement | Owner | Status | Date |
|-------------|-------|--------|------|
| Data pipeline | ML Engineer | ✅ DONE | 2026-05-10 |
| Model training | ML Engineer | ✅ DONE | 2026-05-10 |
| Evaluation report | ML Engineer | ✅ DONE | 2026-05-10 |
| Monitoring | ML Engineer | ✅ DONE | 2026-05-10 |
| Cold start policy | ML Engineer | ✅ DONE | 2026-05-10 |
| Fallback logic | ML Engineer | ✅ DONE | 2026-05-10 |
| Explainability | ML Engineer | ✅ DONE | 2026-05-10 |
| A/B test infrastructure | ML Engineer | ✅ DONE | 2026-05-10 |
| 1000+ samples collected | Product | ⚠️ IN PROGRESS | TBD |
| A/B test execution | Product | 📋 WAITING | TBD |
| Production rollout | Product Owner | 📋 WAITING | TBD |

---

## 🎉 Summary

**SSR ML Layer (Level 1)**: ✅ **PRODUCTION READY**

- ✅ Full ML pipeline delivered
- ✅ Honest evaluation (0.885 AUC-ROC on holdout)
- ✅ Production-ready infrastructure
- ⚠️ Cold-start gate active (73/1000 samples)
- 📋 Ready for A/B test when 1000+ samples collected

**Recommendation**: System is production-ready. Cold-start gate ensures safe rollout. Continue collecting samples for A/B test.

---

**Related Documents**:
- [SSR AI Vision Summary](team_workflow/ssr_ai_vision/ssr_ai_vision_summary.md) — Full roadmap
- [Wave 1 Audit Summary](team_workflow/ssr_ai_vision/ssr_wave1_audit_summary.md) — Audit details
- [ML Eval Report](archive/ml_eval/ssr_forgetting_curve_v1_report.md) — Metrics
- [Evaluation Contract](archive/ml_eval/ssr_level1/evaluation_contract.yaml) — Contract
