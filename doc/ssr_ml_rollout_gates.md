# SSR ML serving — go / no-go gates (US-20.1 hybrid)

Операционный чеклист перед тем, как включать **`ssr_ml_rerank_enabled=True`** в окружении, где пользователи видят Smart Study Router.

## Контракт и автоматизация

| Артефакт | Назначение |
|----------|------------|
| `archive/ml_eval/ssr_level1/evaluation_contract.yaml` → `serving_rollout_gates` | Машиночитаемые пороги и ссылки на скрипт проверки |
| `scripts/check_ssr_ml_rollout_gate.py` | Статические проверки + pytest модулей из DoD пакета |

Запуск gate локально или в CI:

```powershell
.\.venv\Scripts\python.exe scripts/check_ssr_ml_rollout_gate.py
```

Опции: `--skip-pytest` (только статические проверки), `--json-out`.

## GO (можно включать ML rerank)

1. **Cold-start данных**: в контракте зафиксировано достаточное количество реальных сессий для политики владельца (см. `evaluation_contract.actual_results.data_collection` и `remaining_gate`).
2. **Офлайн качество**: holdout-метрики в контракте соответствуют success criteria (AUC / precision@k / recall@k по согласованному окну).
3. **Latency**: локальный inference укладывается в **`ssr_ml_rerank_latency_budget_ms`** (дефолт модели `Settings`: 50 ms).
4. **Fallback-поведение**: при ошибке inference, пустых вероятностях, latency budget, низкой confidence или отсутствии весов — SSR остаётся на **rule-baseline** без регресса детерминизма (покрыто `tests/test_ssr_ml_integration.py`).
5. **Артефакт весов**: `app/ssr_ml_reranking_weights.json` присутствует и меньше **1 MiB**.
6. **Дефолты безопасности**: в базовой конфигурации приложения **`ssr_ml_rerank_enabled=False`**, порог confidence не ниже контрактного минимума (согласован с `Settings`).

## NO-GO / немедленный откат

- Рост доли fallback или latency p95 выше бюджета на стабильном окне (см. `app/ssr_ml_monitoring.py`: `summarize_ssr_ml_monitoring`).
- Регресс rule-приоритетов для пользователя (карточки due / retention-приоритет): любое изменение, ломающее интеграционные тесты baseline.
- Расхождение между числами в `evaluation_contract.yaml` (`serving_rollout_gates.thresholds_align_with_settings_defaults`) и фактическими default полями `Settings` для `ssr_ml_rerank_*` без одновременного обновления контракта и документа.

## Примечание по конфигурации

Все пороги задаются только через **`get_settings()`** / поля `Settings` в `app/config.py`, без прямого чтения env в сервисах.
