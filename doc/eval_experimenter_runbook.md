# Runbook: Eval Experimenter

Актуализировано: **2026-05-20**

Этот документ — пошаговая инструкция для человека-экспериментатора. Вы запускаете замеры, собираете данные и передаёте их агенту для анализа узких мест и рекомендаций.

## Зачем это нужно

Система содержит несколько LLM-зависимых путей (qa, tutor, synthesis, learning_plan, keyword, quiz), каждый из которых имеет разное время ответа, разную стоимость и разную точность. Цель эксперимента — найти конкретные bottleneck, а не общую картину «всё ок / не ок».

## Частота

| Режим | Когда | Что даёт |
|---|---|---|
| **Быстрый** (`--profile ci`) | При каждом PR или подозрении на регрессию | Offline-проверка без API ключа, <1 мин |
| **Ночной** (`--profile nightly`) | Раз в день или после изменений в промптах | Полный прогон с реальным LLM, <15 мин |
| **Ручной глубокий** | Раз в неделю или при деградации метрик | Полный прогон + ручные наблюдения + передача агенту |

## Подготовка

1. Убедитесь, что `.env` содержит `OPENAI_API_KEY` (для nightly/full профилей).
2. Убедитесь, что приложение хотя бы раз отвечало на запросы — иначе `logs/metrics_store.jsonl` будет пустым и фазы judge_sweep / latency_by_mode вернут `skipped`.
3. Если хотите получить алерты в Slack/Telegram — убедитесь, что `ALERT_WEBHOOK_URL` задан в `.env`.

## Шаг 1 — Запуск полного прогона

```bash
python scripts/run_eval_loop.py --profile nightly --report-json logs/eval_report.json
```

Ожидаемое время: 5–15 минут (зависит от скорости LLM API).

Exit code:
- `0` — всё зелёное или только warnings
- `2` — есть fail в одной из фаз или SLO breach

## Шаг 2 — Первичный осмотр отчёта

Откройте `logs/eval_report.json` и проверьте ключевые поля:

```
overall_status: "pass" | "warn" | "fail"
```

Если `fail` — посмотрите, какая фаза:

```
phases.prompt_smoke.status
phases.quality_benchmark.status
phases.router_eval.status
phases.judge_sweep.status
phases.latency_by_mode.status
```

Запишите свои наблюдения в свободной форме (шаг 5).

## Шаг 3 — Сбор дополнительных данных (если есть fail или интересные паттерны)

### 3a. Детальный prompt smoke

```bash
python scripts/run_prompt_smoke.py --report-json logs/prompt_smoke_detail.json
```

Что смотреть: `cases[].token_usage_stages` — если classify или rewrite занимают непропорционально много токенов, это overhead.

### 3b. Детальный router eval

```bash
python scripts/run_router_eval.py --report-json logs/router_eval_detail.json
```

Что смотреть: `cases[].match` = false — конкретные кейсы, где orchestrator выбрал не того агента. Поле `cases[].usage` — сколько токенов ушло на orchestration.

### 3c. Детальный quality benchmark

```bash
python scripts/run_quality_benchmark.py --report-json logs/quality_benchmark_detail.json
```

Что смотреть: `cases[].hit_rate` = 0 — retrieval не нашёл ожидаемые источники.

### 3d. SLO alerts с anomalies

```bash
python -c "
from app.metrics import evaluate_slo_alerts
import json
r = evaluate_slo_alerts(limit_events=20000)
print(json.dumps(r, indent=2, ensure_ascii=False))
" > logs/slo_alerts.json
```

### 3e. Latency по user-сессиям (опционально, ручной замер)

Выполните 3–5 запросов каждого типа через UI или curl и запишите время ответа:

| # | query_mode | Вопрос (краткий) | Время ответа (сек) | Источники (да/нет) | Субъективная оценка ответа (1–5) |
|---|---|---|---|---|---|
| 1 | qa | ... | ... | ... | ... |
| 2 | tutor | ... | ... | ... | ... |
| 3 | synthesis | ... | ... | ... | ... |
| 4 | learning_plan | ... | ... | ... | ... |
| 5 | keyword | ... | ... | ... | ... |

## Шаг 4 — Запись наблюдений

Заполните этот шаблон **перед передачей агенту**. Не пропускайте пункты — пустое поле тоже информация.

```
=== EVAL EXPERIMENT REPORT ===
Дата: YYYY-MM-DD
Профиль прогона: ci / nightly / full
LLM модель: (из .env, LLM_MODEL=...)
Embed модель: (из .env, EMBED_MODEL=...)

--- OVERALL ---
overall_status: pass / warn / fail
exit_code: 0 / 2

--- PHASES ---
prompt_smoke:
  status: ...
  p95_latency_sec: ...
  cases_failed: ... из ...
  failed_cases: [...]

quality_benchmark:
  status: ...
  hit_rate: ...
  mrr: ...
  relevancy: ...

router_eval:
  status: ...
  overall_accuracy: ...
  zero_accuracy_categories: [...]

judge_sweep:
  status: ...
  answer_relevancy: ...
  faithfulness: ...
  context_relevancy: ...
  sample_size: ...

latency_by_mode:
  qa: p50=... p95=... slo_status=...
  tutor: p50=... p95=... slo_status=...
  synthesis: p50=... p95=... slo_status=...
  (другие mode, если есть)

--- SLO ALERTS ---
Количество alerts: ...
Количество anomalies: ...
Критические: [перечислить metric + observed vs threshold]

--- COST ---
total_usd: ...
per_request_avg_usd: ...

--- РУЧНЫЕ НАБЛЮДЕНИЯ ---
Субъективная скорость ответа (быстро / приемлемо / медленно / недопустимо):
Какой query_mode самый медленный:
Качество ответов субъективно (хорошо / средне / плохо):
Были ли пустые ответы или ответы без источников:
Что удивило или показалось аномальным:
Изменилось ли что-то по сравнению с прошлым прогоном:

--- ФАЙЛЫ ПРИЛОЖЕНЫ ---
[ ] logs/eval_report.json
[ ] logs/prompt_smoke_detail.json (если собирали)
[ ] logs/router_eval_detail.json (если собирали)
[ ] logs/quality_benchmark_detail.json (если собирали)
[ ] logs/slo_alerts.json (если собирали)
=== END ===
```

## Шаг 5 — Передача агенту

Скопируйте заполненный шаблон из шага 4 и отправьте агенту со следующим промптом:

```
Проанализируй результаты eval эксперимента.
Задача: найти конкретные узкие места (bottleneck), не общие советы.

Данные:
<вставить заполненный шаблон из шага 4>

Контекст проекта:
- Eval pipeline: scripts/run_eval_loop.py (phases: prompt_smoke, quality_benchmark, router_eval, judge_sweep, latency_by_mode)
- Промпты: app/prompts.py (5 query modes), app/tutor_prompts.py (orchestrator + tutor v2)
- LLM provider: app/provider.py (OpenAI-compatible, retry=3, timeout=60s, connect=10s)
- Cost tracking: app/usage_cost.py (MODEL_PRICING_PER_1M_TOKENS)
- SLO config: app/config.py (slo_* fields)
- Metrics: app/metrics.py (evaluate_slo_alerts, 1800+ lines)
- Router gold dataset: eval_data/tutor_regression.json (26 cases)
- Quality dataset: eval_data/quality_benchmark.json (20+ cases)

Формат ответа:
1. ТОП-3 узких места (конкретный файл, функция, метрика) — ранжированы по impact
2. Для каждого: что именно не так + что конкретно изменить (файл, строка, параметр)
3. Quick wins (можно исправить за <30 мин) vs structural changes (>2 часов)
4. Если данных недостаточно — сказать, какие дополнительные замеры нужны
5. Comparison: если есть данные прошлого прогона — показать delta
```

## Шаг 6 — Трекинг прогресса

После получения рекомендаций от агента:

1. Зафиксируйте baseline в файл (первый прогон):
   ```bash
   cp logs/eval_report.json logs/eval_baseline_YYYY-MM-DD.json
   ```

2. После внесения изменений — повторите прогон и сравните:
   ```bash
   python scripts/run_eval_loop.py --profile nightly --report-json logs/eval_report_after.json
   ```

3. Передайте агенту оба файла:
   ```
   Сравни baseline и текущий прогон, покажи delta по каждой метрике:
   
   Baseline: <содержимое eval_baseline.json>
   After: <содержимое eval_report_after.json>
   
   Что улучшилось, что ухудшилось, что не изменилось.
   ```

## Антипаттерны

- **Не запускайте nightly/full без API ключа** — фазы quality_benchmark и router_eval вернут fail, что создаст ложные алерты.
- **Не сравнивайте прогоны на разных LLM моделях** — delta будет бессмысленной. Фиксируйте модель.
- **Не игнорируйте `skipped` фазы** — это значит, что данных нет (metrics_store пуст). Нужно сначала поработать с системой, потом замерять.
- **Не запускайте прогон во время переиндексации** — latency будет искажена.

## Где живут файлы

| Файл | Назначение |
|---|---|
| `scripts/run_eval_loop.py` | Unified eval orchestrator |
| `scripts/run_prompt_smoke.py` | Prompt heuristics + latency |
| `scripts/run_quality_benchmark.py` | Retrieval hit-rate, MRR |
| `scripts/run_router_eval.py` | Orchestrator accuracy vs gold |
| `eval_data/prompt_smoke_cases.json` | 14 smoke test cases |
| `eval_data/quality_benchmark.json` | 20+ quality benchmark cases |
| `eval_data/tutor_regression.json` | 26 router eval gold cases |
| `eval/eval_dataset.json` | 15 вопросов для сравнения retrieval-режимов (defense) |
| `scripts/run_defense_eval.py` | Прогон vector/hybrid/bm25 на `demo_data` → `eval/eval_results_*.json` |
| `scripts/build_demo_chroma.py` | Прединдекс `demo_chroma_db/` для demo/Space |
| `logs/metrics_store.jsonl` | Runtime metrics (auto-populated) |
| `app/config.py` | SLO thresholds (`slo_*` fields) |
