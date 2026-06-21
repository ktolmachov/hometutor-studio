# PO Router — Retrospective Feedback Loop

Модуль роутера продуктового планирования.  
Основной файл: [`product_owner_router.md`](product_owner_router.md).

Актуализировано: **2026-05-08**

---

## Сбор данных после каждой волны

Создать `archive/retrospectives/wave-<id>_retro.yaml`:

```yaml
wave_id: wave-<id>
closed_date: <YYYY-MM-DD>
ideation_artifact: archive/ideation/<artifact>.md
ideas_generated: <N>
ideas_accepted: <N>
ideas_delivered: <N>
ideas_deferred: <N>

success_factors:
  - "<factor 1>"
  - "<factor 2>"

failure_factors:
  - "<factor 1>"

method_source_effectiveness:
  Duolingo:
    ideas_generated: <N>
    ideas_delivered: <N>
    delivery_rate: <N%>
  Anki:
    ideas_generated: <N>
    ideas_delivered: <N>
    delivery_rate: <N%>

constraints_review:
  - constraint: "<constraint text>"
    verdict: "✅ Правильно / ⚠️ Слишком жёстко / ❌ Не работает"
    reason: "<why>"

angles_effectiveness:
  UX: "<High/Medium/Low> (<N>/<M> delivered)"
  Pedagogy: "<High/Medium/Low>"

recommendations_for_next:
  - "<recommendation 1>"
  - "<recommendation 2>"
```

> ⚠️ Скрипты ретроспектив (`create_retrospective.py`, `retrospective_insights.py`) не реализованы. Используйте manual YAML creation.

---

## Использование insights

При следующем `MODE=CANDIDATE_TABLE` добавить insights вручную в промпт:

```text
RETROSPECTIVE_INSIGHTS="
Из последних волн:
  - Duolingo patterns: <N%> delivery rate (recommend for UX)
  - Constraint '<name>': blocked <N%> viable ideas (consider relaxing)
  - Cohesion score ≥0.7 → wave: <N%> correct predictions
"
```

---

## Router Health Metrics

| Метрика | Target | Red Flag |
|---------|--------|----------|
| **Time to Decision** | ≤ 5 мин | >15 мин |
| **Decision Accuracy** | ≥ 90% | <70% |
| **Ideation → Delivery Rate** | ≥ 60% | <40% |
| **Blocker Resolution Time** | ≤ 1 день | >3 дня |
| **Router Invocations per Package** | ≤ 3 | >5 |
| **Escape Hatch Usage** | ≤ 10% | >25% |

> ⚠️ Автоматические метрики (`router_metrics.py`) не реализованы. Используйте manual tracking в `archive/router_decisions/`.

---

## Timing and Cadence (Solo Developer)

```text
Неделя 1:
  Пн: CANDIDATE_TABLE (1ч)
  Вт: Breakthrough Ideation (3ч)
  Ср: Owner decision (self-review, 1ч)
  Чт: Package planning (1ч)
  Пт: Execution start

Неделя 2:
  Пн-Чт: Execution (implementation + tests)
  Пт: Close package, start next cycle
```

### Time Budgets (SLAs)

| Шаг | Target | Max | Escalation |
|-----|--------|-----|------------|
| Plan-next blocker → CANDIDATE_TABLE | 1 час | 4 часа | Skip ideation, взять deferred |
| CANDIDATE_TABLE → TARGET выбран | 1 день | 3 дня | Default к highest Актуальность |
| Ideation → Artifact готов | 4 часа | 1 день | Reduce N_IDEAS |
| Artifact → Owner decision | 2 дня | 5 дней | Apply default heuristic |
| Owner decision → Package в registry | 2 часа | 1 день | Escalate к PO |
| Registry → Execution start | 15 мин | 1 час | Check sync/lint errors |
