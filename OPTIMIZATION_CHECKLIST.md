# 🚀 Token Optimization Checklist

**Статус:** Начало P0  
**Время создания:** 2026-04-19  
**Deadline P0:** 2026-04-21 (end of tomorrow)

---

## ✅ P0: Критическое (1–2 дня)

### Задача P0.1: Hard limit на входные токены (2–4 часа)
- [ ] Создать `src/utils/token_counter.py` с функциями для подсчёта
- [ ] Добавить `estimate_tokens()` (использовать tiktoken)
- [ ] Добавить `estimate_messages_tokens()` для arrays
- [ ] В `src/api/client.py` добавить валидацию:
  - [ ] `HARD_LIMIT_INPUT = 50_000` (блокировать)
  - [ ] `SOFT_LIMIT_INPUT = 30_000` (warning)
  - [ ] `TRIM_LIMIT_INPUT = 25_000` (auto-trim)
- [ ] Реализовать `_trim_messages()` метод
- [ ] Написать тесты в `tests/test_token_limits.py`
- [ ] Проверить на логах: 83041 должен быть заблокирован

**Проверка:** `pytest tests/test_token_limits.py -v`

---

### Задача P0.2: Request deduplication (2–4 часа)
- [ ] Создать `src/utils/cache.py` с `RequestCache` class
- [ ] Реализовать `_hash_request()` для дедупликации
- [ ] Реализовать `get()` с TTL (10 секунд)
- [ ] Реализовать `set()` с LRU (max 100 entries)
- [ ] В `src/api/client.py` добавить кэш перед API call:
  - [ ] Проверить `cache.get()` перед вызовом
  - [ ] Логировать "Returning cached response"
  - [ ] Сохранить результат в `cache.set()` после вызова
- [ ] Логировать каждый retry с причиной (timeout, rate_limit, etc.)
- [ ] Написать тесты
- [ ] Проверить на логах: 3 одинаковых ERR (46901) должны стать 1

**Проверка:** `pytest tests/test_cache.py -v`

---

### Задача P0.3: History limit до 15 сообщений (1–2 часа)
- [ ] Найти, где собирается `messages` array (вероятно в chat endpoint)
- [ ] Создать функцию `build_messages_with_history_limit()`:
  - [ ] System prompt (обязательно, одна копия)
  - [ ] History: `chat_history[-15:]` (последние 15, не весь диалог)
  - [ ] Current query (обязательно)
- [ ] Заменить текущий message builder на новый
- [ ] Написать тесты: проверить что история ограничена 15 сообщениями
- [ ] Проверить на примерах: базовый input должен упасть с 18k на 4–6k

**Проверка:** `pytest tests/test_history_limit.py -v`

---

### Задача P0.4: Token breakdown логирование (2–4 часа)
- [ ] Создать `src/utils/token_breakdown.py` с `TokenBreakdown` class
- [ ] Реализовать метод `add(component_name, text)`
- [ ] Реализовать метод `add_messages(messages_array)`
- [ ] Реализовать метод `to_dict()` и `to_json()`
- [ ] В `src/api/client.py` перед каждым LLM call добавить:
  ```python
  breakdown = log_token_breakdown(messages, model, retrieved_context, tools)
  logger.info("Token Breakdown", extra={"token_breakdown": breakdown.to_dict()})
  ```
- [ ] Настроить JSON логирование (если не настроено)
- [ ] Проверить логи: должны быть breakdown по system/history/context/query

**Проверка:** `grep "Token Breakdown" logs/latest.log | head -5`

---

## 📊 P0 Progress Tracking

| Задача | Owner | Status | ETA | Notes |
|---|---|---|---|---|
| P0.1: Hard limit | — | ⏳ Pending | ~2h | /src/utils/token_counter.py |
| P0.2: Deduplication | — | ⏳ Pending | ~2h | /src/utils/cache.py |
| P0.3: History limit | — | ⏳ Pending | ~1h | /src/chat/message_builder.py |
| P0.4: Breakdown logging | — | ⏳ Pending | ~2h | /src/utils/token_breakdown.py |
| **TOTAL P0** | — | **⏳ Pending** | **~7–14h** | Target: 1–2 days |

---

## 🔍 Validation Steps

### Before Merging P0

```bash
# 1. Run all tests
pytest tests/test_token_limits.py tests/test_cache.py tests/test_history_limit.py -v

# 2. Run on sample logs
python scripts/replay_logs.py --input logs/2026-04-19.jsonl

# Expected output:
# - 83041 token call: BLOCKED or TRIMMED
# - 46901 x3 retry calls: DEDUPLICATED to 1
# - 18k baseline: reduced to 6–8k
# - Token breakdown for each call

# 3. Check logging
tail -f logs/latest.log | grep "Token Breakdown"

# 4. No regression tests
pytest tests/ -k "quality or correctness"
```

---

## ✅ P0 Sign-off

- [ ] Все 4 задачи реализованы и протестированы
- [ ] Hard limit блокирует >50k
- [ ] Deduplication срабатывает
- [ ] History ограничена 15 сообщениями
- [ ] Breakdown логируется в JSON
- [ ] Нет регрессии в тестах
- [ ] Code review пройдена
- [ ] Merged в master

**Estimated Time:** 1–2 дня  
**Expected Result:** 40–50% экономии входных токенов

---

## ⚠️ P0 Risks & Mitigations

| Риск | Вероятность | Mitigation |
|---|---|---|
| Hard limit будет блокировать нужные запросы | Низкая | Начать с 50k, потом повысить если нужно |
| Cache будет давать неправильные результаты | Низкая | Unit tests, TTL=10s, logs |
| History trim потеряет важный контекст | Средняя | Мониторить quality metrics, fallback |
| Деградация latency | Низкая | Logging overhead минимален |

---

## 🎯 P0 Success Metrics

| Метрика | До | После | Target |
|---|---|---|---|
| **Avg input tokens** | 22,241 | ??? | < 8,000 |
| **Max input tokens** | 83,041 | ??? | < 50,000 |
| **Baseline (16th percentile)** | ~17,000 | ??? | < 6,000 |
| **Retry duplicates** | 93,000 | 0 | 0 |
| **Quality (A/B test)** | 100% | >98% | >98% |

---

## 📝 P0 Code Structure

```
src/
├── utils/
│   ├── token_counter.py          # ✨ NEW: estimate_tokens()
│   ├── cache.py                   # ✨ NEW: RequestCache
│   └── token_breakdown.py          # ✨ NEW: TokenBreakdown
├── api/
│   └── client.py                  # MODIFY: add limits + dedup + logging
├── chat/
│   └── message_builder.py          # ✨ NEW or MODIFY: history limit
└── ...

tests/
├── test_token_limits.py            # ✨ NEW
├── test_cache.py                   # ✨ NEW
└── test_history_limit.py           # ✨ NEW

scripts/
├── replay_logs.py                  # ✨ NEW: test on real logs
├── analyze_token_usage.py          # ✨ NEW: analytics
└── ...
```

---

## 🔗 References

- **Full Plan:** [doc/token_optimization_plan.md](../doc/token_optimization_plan.md)
- **Analysis Report:** [doc/agent_workflow.md](../doc/agent_workflow.md) (section on token analysis)
- **Logs from 2026-04-19:** Available in monitoring dashboard

---

## 💬 Questions?

If stuck on any P0 task:
1. Check full plan in `doc/token_optimization_plan.md`
2. Review code examples in the plan
3. Run unit tests to validate
4. Check logs for breakdown

---

**Good luck! 🚀 Target: Complete P0 by EOD tomorrow (2026-04-21)**
