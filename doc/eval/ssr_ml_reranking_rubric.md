# SSR ML Reranking — Evaluation Rubric (Level 1)

Офлайн и продуктовая оценка гибридного SSR (rule baseline + локальный ML rerank).
Согласовано с `archive/ml_eval/ssr_level1/evaluation_contract.yaml`.

## 1. Offline ranking / classification

| Gate | Принять | Погранично | Отклонить |
|------|---------|------------|-----------|
| AUC-ROC | ≥ 0.75 | 0.68–0.74 (max 2 итерации улучшения) | < 0.68 |
| Precision@5 | ≥ 0.80 | 0.72–0.79 | < 0.72 |
| Recall@5 | ≥ 0.70 | 0.60–0.69 | < 0.60 |
| Inference p95 | < 50ms | 50–65ms (только с планом оптимизации) | > 65ms |
| Model size | < 1MB | — | ≥ 1MB |

## 2. Product proxy: cards_due completion

| Условие | Интерпретация |
|---------|----------------|
| ≥ 75% | primary metric hit |
| 70–74% | продлить сбор; пересмотреть feature importance |
| < 70% | default rule-only; ML за flag |

Базовая линия контракта: **60%** (до внедрения Level 1).

## 3. Explainability trace (Hard Fail)

Сценарий **провален**, если в trace нельзя восстановить цепочку:

1. Rule priority / hint order до ML.
2. ML adjustment (вклад признаков или агрегированный score).
3. Финальный top hint и признак использования fallback.

Также hard fail при скрытии факта fallback или подмене маршрута без явного журнала.

## 4. Fallback behavior

| Метрика | Target | Действие при miss |
|---------|--------|-------------------|
| fallback_rate | < 5% | см. evaluation_contract.failure_plan |

## 5. Агрегация офлайн harness

На этапе контракта достаточно:

- наличие 100 локальных сценариев с `ground_truth_best_hint_kind` и признаками;
- pytest harness проверяет целостность набора и артефакты;
- после обучения модели — добавить сравнение predictions vs labels в `scripts/ml/eval_ssr_forgetting_curve.py`.
