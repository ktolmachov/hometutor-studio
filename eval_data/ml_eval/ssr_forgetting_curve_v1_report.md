# SSR forgetting-curve v1 eval report

Generated: 2026-05-09T22:15:18.893145+00:00

## Gate summary

- Serving mode: `rule_based`
- Serving reason: real_samples 73 < 1000
- Real samples: 73
- Synthetic samples: 500
- AUC-ROC target: >= 0.75

## Holdout metrics

- Rows: 135
- Macro AUC-ROC: 0.885 (PASS)
- Retention AUC-ROC: 0.732
- Accuracy: 0.511
- Precision@5: 0.985
- Recall@5: 0.985
- Inference latency p95: 0.021 ms

## Contract harness metrics

- Rows: 100
- Macro AUC-ROC: 0.695
- Retention AUC-ROC: 0.619
- Accuracy: 0.500
- Precision@5: 0.960
- Recall@5: 0.960
- Inference latency p95: 0.040 ms

## Holdout confusion matrix

| expected \ predicted | adaptive_plan | answer_ready | cards_due | mastery_stale | quiz_failed | safe_default | sm2_due | tutor_resume |
|---|---|---|---|---|---|---|---|---|
| adaptive_plan | 3 | 7 | 2 | 0 | 0 | 0 | 0 | 0 |
| answer_ready | 3 | 7 | 7 | 0 | 0 | 0 | 0 | 0 |
| cards_due | 0 | 4 | 23 | 1 | 0 | 0 | 2 | 1 |
| mastery_stale | 0 | 3 | 5 | 4 | 1 | 2 | 2 | 0 |
| quiz_failed | 0 | 0 | 0 | 1 | 8 | 0 | 4 | 0 |
| safe_default | 0 | 0 | 5 | 0 | 0 | 1 | 7 | 0 |
| sm2_due | 0 | 0 | 4 | 0 | 0 | 5 | 10 | 0 |
| tutor_resume | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 |

## Production readiness note

The model remains rule-only for serving until the cold-start gate has at least 1000 real samples and AUC-ROC >= 0.70.
Synthetic bootstrap rows are allowed for pipeline validation, not for enabling production ML by default.
