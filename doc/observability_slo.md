# SLO И Наблюдаемость

Статус: `Reference`
Актуализировано по коду на 2026-04-12 (architecture review follow-up).

## Где хранятся метрики

По умолчанию:

- `logs/metrics_store.jsonl` — событийное хранилище метрик
- `logs/metrics_dashboard.db` — SQLite-агрегации dashboard

Эти пути можно переопределить через `get_settings()` / поля `Settings`:

- `metrics_store_path` (env `METRICS_STORE_PATH`)
- `metrics_dashboard_db_path` (env `METRICS_DASHBOARD_DB_PATH`)

Значения задаются в `app/config.py`; `app/metrics.py` берёт пути из `get_settings()` при загрузке модуля (константы `METRICS_STORE_PATH` / `METRICS_DASHBOARD_DB_PATH` в коде — снимок для совместимости и тестов).

## Основные endpoints

- `GET /metrics`
- `GET /metrics/quality`
- `GET /metrics/cost`
- `GET /metrics/dashboard`
- `GET /metrics/learner`
- `GET /metrics/alerts`
- `POST /metrics/knowledge-workflow`
- `GET /metrics/knowledge-workflow`
- `POST /feedback`
- `GET /metrics/feedback`
- `GET /metrics/store`
- `GET /history`
- `GET /pipeline/trace`

## SLO-параметры

Эти переменные задаются через `app/config.py`:

- `SLO_MAX_FALLBACK_RATE`
- `SLO_MIN_SOURCE_COVERAGE`
- `SLO_MAX_P95_LATENCY_MS`
- `SLO_LATENCY_BY_MODE`
- `SLO_MAX_AVG_COST_USD`
- `SLO_MIN_JUDGE_SCORE`
- `SLO_MAX_LEARNER_REHYDRATED_RATE`
- `SLO_ANOMALY_RECENT_WINDOW`
- `SLO_ANOMALY_SIGMA`
- `ALERT_WEBHOOK_URL`

Смысл:

- fallback rate — доля ответов с safe fallback
- source coverage — покрытие ответов источниками
- p95 latency — задержка end-to-end
- avg cost — средняя оценочная стоимость запроса
- judge score — средний async judge score при включенном judge

## Alerts

- `GET /metrics/alerts?limit_events=20000` — расчет SLO и аномалий
- `GET /metrics/alerts?notify=true` — то же, плюс webhook при наличии `ALERT_WEBHOOK_URL`

Ответ содержит:

- `alerts`
- `anomalies`
- `observed`
- `policy`

## OpenTelemetry

Переменные:

- `ENABLE_OTEL_TRACING=true`
- `OTEL_EXPORTER_OTLP_ENDPOINT`
- `OTEL_SERVICE_NAME`

Текущее покрытие:

- span для classify/rewrite pipeline
- span для retrieve/generate

## Что считать источником правды

- структура метрик и alert logic: `app/metrics.py`
- HTTP-контракты: `app/routers/metrics.py`
- runtime config: `app/config.py`

## Graph Expansion Gate Recipes

Готовые CLI-сценарии для graph expansion observability / merge-gate:

- overall local:
  `python scripts/graph_expansion_compare.py --baseline-jsonl logs/off.jsonl --candidate-jsonl logs/on.jsonl --preset overall-local --enforce-gate`
- overall strict:
  `python scripts/graph_expansion_compare.py --baseline-jsonl logs/off.jsonl --candidate-jsonl logs/on.jsonl --preset overall-strict --enforce-gate`
- synthesis strict:
  `python scripts/graph_expansion_compare.py --baseline-jsonl logs/off.jsonl --candidate-jsonl logs/on.jsonl --preset synthesis-strict --enforce-gate`
- learning plan local:
  `python scripts/graph_expansion_compare.py --baseline-jsonl logs/off.jsonl --candidate-jsonl logs/on.jsonl --preset learning-plan-local --enforce-gate`
- dual local:
  `python scripts/graph_expansion_compare.py --baseline-jsonl logs/off.jsonl --candidate-jsonl logs/on.jsonl --preset dual-local --enforce-gate`
- dual strict:
  `python scripts/graph_expansion_compare.py --baseline-jsonl logs/off.jsonl --candidate-jsonl logs/on.jsonl --preset dual-strict --enforce-gate`
- smoke off/on overall:
  `python scripts/smoke_graph_expansion_compare.py --preset overall-local --json-out`
- smoke off/on synthesis strict:
  `python scripts/smoke_graph_expansion_compare.py --preset synthesis-strict --enforce-gate --json-out`
- smoke off/on dual local:
  `python scripts/smoke_graph_expansion_compare.py --preset dual-local --query-types synthesis,learning_plan --enforce-gate --json-out`

Дополнительно:

- `scripts/smoke_graph_expansion_gate.py --query-types synthesis,learning_plan` генерирует multi-query-type smoke traffic.
- `--gate-query-type-profile synthesis=strict` позволяет дать отдельный budget для конкретного `query_type`, даже если общий compare-gate остаётся на `local`.

## Learner Migration Gate Recipes

Готовые CLI-сценарии для learner migration observability / merge-gate:

- local gate:
  `python scripts/check_learner_migration_gate.py --profile local --json-out`
- strict gate:
  `python scripts/check_learner_migration_gate.py --profile strict --json-out`
- smoke healthy (ожидаем pass):
  `python scripts/smoke_learner_migration_gate.py --profile strict --mode healthy --json-out`
- smoke degraded (ожидаем fail):
  `python scripts/smoke_learner_migration_gate.py --profile strict --mode degraded --json-out`

CI workflow:

- `.github/workflows/learner-migration-smoke-gate.yml` запускает strict smoke merge-gate на `pull_request` и `push` в `main/master`.

## Tutor Regression Gate

Текущее состояние tutor regression contour:

- ready gate command: `scripts/check_tutor_regression_gate.py`
- baseline: `eval_data/tutor_regression_baseline.json`
- dataset: `eval_data/tutor_regression.json`
- smoke runner: `scripts/smoke_tutor_regression_gate.py`
- CI workflow: `.github/workflows/tutor-regression-gate.yml`

Ручные сценарии:

- summary only, без baseline:
  `python scripts/check_tutor_regression_gate.py`
- baseline gate:
  `python scripts/check_tutor_regression_gate.py --baseline eval_data/tutor_regression_baseline.json`
- baseline via env (backward-compatible):
  `set EVAL_TUTOR_BASELINE_JSON=eval_data/tutor_regression_baseline.json`
  `python scripts/check_tutor_regression_gate.py`
- smoke healthy (ожидаем pass):
  `python scripts/smoke_tutor_regression_gate.py --mode healthy --json-out`
- smoke degraded (ожидаем fail):
  `python scripts/smoke_tutor_regression_gate.py --mode degraded --json-out`

Диагностика fail-типов (E7.1):

- `check_tutor_regression_gate.py` возвращает:
  - `0` — gate pass;
  - `2` — regression fail (baseline comparison);
  - `3` — infra/provider/dependency failure (`status=infra_fail`, поля `error_kind/error_type/error_message` в JSON-отчёте).
- smoke-path детерминированный: `smoke_tutor_regression_gate.py` генерирует baseline из файла
  `eval_data/tutor_regression_baseline.json` (или `--source-baseline-path`), без live LLM-зависимости.
- smoke JSON теперь содержит `diagnostic_summary`:
  - `result_label=healthy_pass` — healthy smoke прошёл как ожидалось;
  - `result_label=degraded_expected_fail` — degraded smoke корректно подтвердил fail-path;
  - `result_label=unexpected_outcome` — smoke-контур дал неожиданный exit/status и требует разбора.

CI merge-gate:

- `.github/workflows/tutor-regression-gate.yml` запускает оба smoke-сценария:
  - `healthy` как основной merge-gate;
  - `degraded` как контрольный сценарий на ожидаемый fail-path.
- В `GITHUB_STEP_SUMMARY` публикуется короткий отчёт по обоим сценариям:
  - `result_label`
  - `status`
  - `error_kind`
  - `next_action` / `owner_hint` / `rerun_recommended` (из `gate.triage`, E7.3)
  - `expected_rc / actual_rc`
  - `matched`

Практическая интерпретация summary:

- `healthy` должен дать `result_label=healthy_pass` и `matched=true`.
- `degraded` должен дать `result_label=degraded_expected_fail` и `matched=true`.
- `error_kind` у healthy smoke должен оставаться пустым; если там `provider_error` или `infra_transient`, это уже не regression fail, а проблема reliability контура.

### Triage runbook (E7.2)

Цель: разобрать падение tutor gate по CI-артефактам без локального полного репродуса.

Где смотреть в CI:

- artifact bundle: `tutor-regression-gate-artifacts`
- smoke reports: `tutor-smoke-healthy.json`, `tutor-smoke-degraded.json`
- gate extracts: `tutor-gate-healthy.json`, `tutor-gate-degraded.json`
- быстрый вход: `GITHUB_STEP_SUMMARY` (блок `Artifacts` + `Diagnostic`)

Порядок разбора:

1. Проверить `Diagnostic` в summary:
   - `healthy`: ожидаем `result_label=healthy_pass`, `matched=true`;
   - `degraded`: ожидаем `result_label=degraded_expected_fail`, `matched=true`.
2. Если `matched=false` в любом сценарии — открыть соответствующий `tutor-smoke-*.json` и сверить:
   - `expectation.expected_rc` vs `expectation.actual_rc`;
   - `diagnostic_summary.gate_status` и `diagnostic_summary.gate_error_kind`.
3. Для детального разбора открыть `tutor-gate-*.json` и читать в порядке:
   - `status`
   - `exit_code`
   - `error_kind` / `error_type` / `error_message`
   - `baseline_comparison` (если есть)

Ветки triage:

- `status=regression_fail`:
  - это контентная/качественная регрессия относительно baseline;
  - проверить `baseline_comparison.regressions` и `summary` в gate JSON;
  - follow-up: обновить код/эвристики tutor-контура или обоснованно переснять baseline в отдельной итерации.

- `status=infra_fail`:
  - это не quality regression, а внешняя/инфраструктурная проблема;
  - ориентиры по `error_kind`: `dependency_missing`, `provider_error`, `infra_transient`, `runtime_error`;
  - follow-up: чинить окружение/провайдер/зависимости или ретраить CI после устранения причины; baseline не переснимать.

Быстрый чек перед merge:

- `healthy` smoke стабильно `matched=true`;
- `degraded` smoke стабильно `matched=true`;
- нет `infra_fail` в healthy-path;
- артефакты из bundle доступны и читаются.

### Operator quick path (E7.3)

Gate JSON (`check_tutor_regression_gate.py`, поле `triage`) и smoke `diagnostic_summary` дают машиночитаемые подсказки без чтения полного отчёта:

| Условие | `triage.next_action` (типовое) | `owner_hint` | `rerun_recommended` |
|--------|----------------------------------|--------------|---------------------|
| `status=pass` | `noop` | `none` | `false` |
| `status=regression_fail` | `fix_baseline_or_tutor_quality` | `tutor_contour_owner` | `false` |
| `status=infra_fail`, `error_kind=dependency_missing` | `install_missing_dependencies` | `repo_ci_owner` | `false` |
| `status=infra_fail`, `error_kind=provider_error` | `check_provider_keys_quota_policy` | `platform_infra` | `true` |
| `status=infra_fail`, `error_kind=infra_transient` | `retry_ci_job` | `ci_operator` | `true` |
| `status=infra_fail`, иначе | `investigate_gate_runtime` | `tutor_contour_owner` | `false` |

Короткое decision tree:

1. Смотри `triage.next_action` в `tutor-gate-healthy.json` (или в строке CI summary).
2. Если `regression_fail` — это не «починить CI», а разбор качества/baseline (owner tutor contour).
3. Если `infra_fail` и `rerun_recommended=true` — сначала исключить флейк/квоту, затем повтор job; baseline не трогать.
4. Если `dependency_missing` — чинить окружение/requirements, не меняя tutor-код.
