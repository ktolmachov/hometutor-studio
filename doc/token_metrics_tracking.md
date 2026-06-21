---
name: Token Metrics Tracking
description: Baseline measurements и validation framework для измерения реальной экономии токенов
type: reference
---

# Метрики расхода токенов: Baseline и Валидация

**Дата baseline:** 2026-04-19  
**Источник:** лог из 17 запросов (14 OK, 3 ERR)

## Baseline (ДО оптимизаций)

### Итоговая статистика

| Метрика | Значение | Примечание |
|---|---|---|
| Запросы OK | 14 | grok-4.1-fast-thinking × 13, z-ai/glm-5.1 × 1 |
| Запросы ERR | 3 | openai/gpt-5.3-codex × 3 (повторный вызов без сжатия) |
| **Входных токенов (OK только)** | 265,419 | Среднее 18,958 на запрос |
| **Входных токенов (потрачено на ERR)** | 140,703 | 46,901 × 3 без полезного выхода |
| **Всего потраченных входных токенов** | **406,122** | |
| Полезного выхода (tokens) | 10,329 | только из OK запросов |
| **Ratio полезного выхода** | 3.9% | 10,329 из 265,419 |
| **Стоимость (рубли)** | 26.63 | OK запросы + ERR потери |
| **Стоимость за 1 полезный token** | ~2.58 руб | 26.63 / 10.329 |

### Breakdown по типам запросов

**Нормальные запросы (grok, OK выход):**
- Count: 13
- Input: 17,116–29,434 токенов
- Output: 229–1,607 токенов
- Cost: 1.06–1.89 руб
- **Типичный вызов:** 18,500 in, 750 out, 1.48 руб

**Аномалия #1 (glm-5.1, low output):**
- Row #14: 17,591 in, 61 out (0.35% ratio)
- Cost: 7.12 руб (4.8× дороже нормального)
- **Проблема:** дорогая модель + бесполезный вывод

**Аномалия #2 (openai/gpt-5.3, error loop):**
- Rows #15-17: 46,901 in × 3, -2 out (ошибка)
- Cost: 0 × 3 (но входные токены потрачены)
- **Проблема:** повторный ретрай БЕЗ сжатия контекста

---

## Target (ПОСЛЕ оптимизаций)

На основе новых правил в `doc/agent_workflow.md`:

### Ожидаемые улучшения

| Правило | До | После | Эффект |
|---|---|---|---|
| **Read-set limit ≤ 5 файлов** | 20–25 файлов читали | 3–5 файлов | −40–60% входа |
| **Запрет glm-5.1** | row #14: 7.12 руб | grok: 1.89 руб | −73% стоимости на call |
| **Запрет ERR без сжатия** | 3 повтора × 46k | 1 вызов + fallback | −66% потраченных токенов |
| **Signatures only для >600 строк** | полный query_service (1499 lines, ~5k) | signatures only (~500 tokens) | −90% для модулей |
| **History limit: последние 2–3 шага** | полная история conversation | ~1k токенов | −15–20% в цепочках |

### Projected Metrics

| Метрика | Baseline | Target | Delta |
|---|---|---|---|
| **Среднее входа на запрос** | 18,958 | 10,500 | −45% |
| **Выброс 83k (ArchReview)** | 83,041 | 6,000 (per phase) | −93% (5 фаз вместо 1) |
| **Стоимость за запрос** | 1.48 руб | 0.80 руб | −46% |
| **Стоимость за полезный token** | 2.58 руб | 1.20 руб | −54% |
| **Потеря на ERR-петлю** | 140,703 токенов | 0 | −100% (guard) |

---

## Validation Checklist

Для валидации, что оптимизации работают, проверять:

### ✅ Hard Guards (должны срабатывать)

- [ ] **Guard #1:** Вызов с `model="z-ai/glm-5.1"` → REJECTED перед отправкой
- [ ] **Guard #2:** Вызов с `model="openai/gpt-5.3-codex"` → REJECTED перед отправкой
- [ ] **Guard #3:** Вызов с `input_tokens > 20000` → REJECTED (hard-limit)
- [ ] **Guard #4:** Вызов после ERR без сжатия → REJECTED (no retry)

### ✅ Metrics Collection (должны логироваться)

- [ ] **Per-call log:** timestamp, model, input_tokens, output_tokens, cost_rub
- [ ] **Per-package summary:** total_cost, input_tokens_used, output_tokens, compression_applied
- [ ] **Cost anomaly flag:** cost > 5 руб или ratio > 400% от среднего
- [ ] **ERR tracking:** error_count, error_type (timeout, rate_limit, invalid_model, etc.)

### ✅ Quality Validation (нет регрессии)

- [ ] **Planning output quality:** контракт все ещё читаем, цели ясны, DoD точные
- [ ] **ArchReview output quality:** фазовое разбиение не снижает качество анализа
- [ ] **Micro-* templates:** работают для budget-constrained моделей без потери смысла

### ✅ Baseline Verification (прошлые ошибки не повторяются)

- [ ] Нет повторных запросов к glm-5.1 (row #14 pattern исчез)
- [ ] Нет 3+ ретраев одного вызова без сжатия (row #15-17 pattern исчез)
- [ ] Input tokens за сессию < 250k (было 406k)

---

## Measurement Strategy

### Фаза 1: Инструментация (День 1)

Добавить логирование в LLM-caller:

```json
{
  "timestamp": "2026-04-20T10:15:33Z",
  "session_id": "e14-b-execution",
  "package_id": "E14-B",
  "prompt_type": "planning",
  "model": "grok-4.1-fast-thinking",
  "input_tokens": 10500,
  "output_tokens": 850,
  "cost_rub": 0.89,
  "guards_applied": ["read_set_limit_5", "no_glm51", "fresh_context"],
  "compression_applied": false,
  "status": "OK"
}
```

Сохранять в `logs/cost_logs/` по датам (JSON lines).

### Фаза 2: A/B Сравнение (День 2–3)

Запустить 3 planning-пакета на старом и новом шаблонах:
- **Old template:** без read-set limit, с полными файлами
- **New template:** с read-set limit ≤ 5, с signatures-only
- **Сравнить:** input_tokens, output quality (objective scoring), cost

### Фаза 3: Валидация (День 4–7)

Посмотреть логи за неделю:
- Сработал ли guard #1-4?
- Остались ли дорогие ошибки?
- Есть ли улучшение в baseline?

---

## Отчёт (шаблон)

Сохранять еженедельно в `doc/cost_tracking.md`:

```markdown
# Weekly Token Metrics Report — Week 2026-04-21

## Summary
- Total requests: 42 (all OK, 0 ERR)
- Total input tokens: 384,250 (−5% vs baseline 406k)
- Total cost: 18.50 руб (−30% vs baseline 26.63)
- Average cost/call: 0.44 руб (−70% vs baseline 1.48)
- Guards triggered: 2 (glm-5.1 block #1, >20k limit #1)

## Anomalies
- None

## Top 3 expensive calls
1. ArchReview Phase 1 (conventions): 14,500 tokens, 0.98 руб
2. Planning E14-C: 12,100 tokens, 0.81 руб
3. Planning E14-D: 11,900 tokens, 0.80 руб

## Conclusion
✅ All guards working. Token budget < target. Cost −30% vs baseline.
```

---

## Red Flags (мониторить)

Если видишь это — остановить и отчитаться:

| Flag | Триггер | Действие |
|---|---|---|
| 🚨 **Cost spike** | Вызов > 5 руб | Логировать, анализировать модель/context |
| 🚨 **Guard bypass** | glm-5.1 или openai в логе | Проверить guard-реализацию |
| 🚨 **ERR loop** | 2+ вызова одного пакета | Проверить retry policy |
| 🚨 **Low output ratio** | output < 1% от input | Quality check output, возможно краш |
| 🚨 **High input** | input > 20k в OK запросе | Проверить read-set, может быть лишний файл |

---

## Success Criteria

Оптимизация считается **успешной**, если к концу недели:

- ✅ Среднее входа/запрос < 12k (было 18.9k)
- ✅ Среднее стоимости < 0.90 руб (было 1.48)
- ✅ Нулевых ERR-потерь (было 140k токенов)
- ✅ Нулевых glm-5.1 вызовов (было row #14)
- ✅ Нет регрессии качества (ручная проверка output)
