# SSR AI Vision — Level 2↔Level 3 readiness gate

**Package:** `ssr-ai-vision-level2-level3-readiness-gate`  
**Дата решения:** 2026-05-15  
**Тип:** audit / readiness decision (не rollout нового ML)

Назначение: зафиксировать проверку сигналов L1/L2 «в продуктахом смысле» и базовой телеметрии L3 до открытия трат на оптимизацию роутинга / граф.

Источники: `doc/team_workflow/ssr_ai_vision/ssr_ai_vision_summary.md`,  
`archive/ml_eval/ssr_level1/evaluation_contract.yaml`,  
`archive/ml_eval/ssr_level2/evaluation_contract.yaml`, код `app/ssr_ai/telemetry.py`,  
`app/ssr_weekly_planner.py`, регрессионные тесты из DoD пакета.

---

## 1. L1 — production signals и cold-start

| Проверка | Факт в репозитории | Вердикт |
|----------|-------------------|---------|
| Офлайн-качество модели (AUC, latency inference) | Зафиксировано в `evaluation_contract.yaml` (macro AUC 0.885, inference p95 ~0.03 ms) | **PASS** офлайн |
| Cold-start семплов для serving | `production_status: cold_start_gate_active`, реальные семплы **73** при цели **≥1000** | **NO-GO для hybrid serving по умолчанию**; режим намеренно `rule_based` до порога |
| Телеметрия инференса L1 | Ключ `ssr_ml_monitoring_v1`, rollup `summarize_ml_inference_events` (`app/ssr_ai/telemetry.py`), тесты `tests/test_ssr_ai_shared_infra.py` | **Покрыто тестами** (локальный контракт хранилища) |

**Решение L1:** инженерная часть и отчёты — ок; **продуктовый hybrid rollout остаётся заблокирован cold-start гейтом**. Открывать оптимизацию поверх ML-rerank без плана семплов — не рекомендуется.

---

## 2. L2 — production verification и latency

| Проверка | Факт | Вердикт |
|----------|------|---------|
| Граница продукта | LLM меняет только текст объяснения; маршрут детерминированный (контракт L2 YAML + SSR тесты в репозитории) | **Соблюдено по дизайну** |
| Latency LLM (`llm_latency_p95`) | В отчёте гейта 2026-05-09: **4.11s**, цель **&lt;2s** → **NO-GO** для «зелёного» rollout latency | **Открытый риск** до ремедиации (`ssr-l2-reliability-v1` и т.п.) |
| Локальные сигналы в UI (US-20.8) | Evidence ledger / локальные признаки без имитации облачного профилирования — покрыто существующими SSR UI-путями и закрытыми пакетами | **Зафиксировано как delivered** в US; этот gate не перепроходит UX-ревью |

**Решение L2:** **условный GO для продолжения L3 baseline-compatible работ**: пока **(a)** latency не доведена до &lt;2s **или** явно не принят waiver, любые шаги L3 должны сохранять правило **«LLM не входит в расчёт плана»**.

---

## 3. L3 — baseline telemetry coverage

| Проверка | Факт | Вердикт |
|----------|------|---------|
| Планировщик | `app/ssr_weekly_planner.py` — rule-based, профиль → 7 дней, метки `retention_debt` / `weak_concept_recovery` / `new_learning_or_continuation` (US-20.9) | **PASS** логики |
| Телеметрия L3 | При `emit_telemetry=True` вызывается `record_ssr_ai_auxiliary_event(level="L3", ...)` | **PASS** интеграции |
| Вспомогательная телеметрия уровней | `record_ssr_ai_auxiliary_event` для L2/L3, ключ `ssr_ai_auxiliary_telemetry_v1`; тест `test_auxiliary_round_trip_via_with_db_stub` | **PASS** регрессии |
| Фикстуры планировщика | `tests/test_ssr_weekly_planner.py` — 30 профилей, ветки доминирования сигналов | **PASS** |

**Решение L3:** **GO на baseline telemetry coverage** для текущего объёма кода: телеметрия и сценарии debt/recovery/new learning проверяются тестами DoD.

---

## 4. Сводное решение и условия следующих трат

**Общий вердикт:** **CONDITIONAL GO**.

- **Разрешено:** планирование и инженерные пакеты уровня L3 baseline / объяснимости при условии baseline-compatible режима (п. «Решение L2»).
- **Не разрешено без отдельного решения:** трактовать L2 как полностью «green» по latency; включать LLM в входы weekly planner; открывать graph-routing spending без учёта cold-start L1.

**Открытые пункты (перенести в roadmap / следующие пакеты):**

1. Ремедиация `llm_latency_p95` или формальный waiver с фиксацией UX fallback.
2. Набор прод-семплов до порога cold-start L1 либо явная политика сбора.

---

## 5. Верификация (DoD пакета)

Команды из `doc/backlog_registry.yaml` для этого пакета:

- `pytest tests/test_ssr_ai_shared_infra.py tests/test_ssr_weekly_planner.py`
- `scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync`

Результат фиксируется в `archive/team_artifacts/ssr-ai-vision-level2-level3-readiness-gate/execution_contract.md` при закрытии.
