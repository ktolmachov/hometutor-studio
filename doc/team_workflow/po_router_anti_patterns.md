# PO Router — Anti-Patterns and Pitfalls

Модуль роутера продуктового планирования.  
Основной файл: [`product_owner_router.md`](product_owner_router.md).

Актуализировано: **2026-05-08**

---

## ❌ Anti-Pattern 1: "Ideation без TARGET"

Запустить `generate_breakthrough_ideation_prompt.md` без конкретного TARGET.

**Почему плохо:** Идеи разнородны, constraints не работают, owner перегружен.

**Правильно:** Сначала `MODE=CANDIDATE_TABLE`, затем выбрать строку как TARGET.

---

## ❌ Anti-Pattern 2: "Package без US"

Создать package напрямую из ideation без user story.

**Почему плохо:** Нет acceptance criteria, нет связи с CJM, DoD неполный.

**Правильно:** Если US нет → сначала создать через Analyst role.

---

## ❌ Anti-Pattern 3: "Multi-wave для 2 идей"

Запустить `generate_roadmap_epoch_waves_prompt.md` для 2 идей.

**Почему плохо:** Overhead wave management, нет synergy, медленнее отдельных packages.

**Правильно:** 2 идеи → проверить cohesion → High = один package, Low = два packages. Wave только для 3+.

---

## ❌ Anti-Pattern 4: "Игнорирование deferred items"

Запустить ideation, когда есть `deferred` с met `re_entry_condition`.

**Почему плохо:** Дублирование, потеря контекста, нарушение re-entry contract.

**Правильно:**
```powershell
# Перед ideation:
Select-String -Path doc/backlog_registry.yaml -Pattern "status: deferred"
# Проверить re_entry_condition для каждого
```

---

## ❌ Anti-Pattern 5: "Execution до sync"

Запустить `workflow.py` до `backlog_registry_lint.py --sync-from-index --write-sync`.

**Почему плохо:** Stale tasklist, unfound packages, lint errors.

**Правильно:**
```powershell
# Всегда после правки backlog_registry.yaml:
.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --sync-from-index --write-sync
.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict
# Только после зелёного lint:
.\.venv\Scripts\python.exe scripts\workflow.py
```

---

## ❌ Anti-Pattern 6: "Constraints без обоснования"

Добавить constraints вроде "must be fast; must be beautiful; must be perfect".

**Почему плохо:** Субъективные критерии, нет measurable threshold, блокируют все идеи.

**Правильно:**
```text
CONSTRAINTS="
  p95 latency ≤ 500ms (measurable);
  must preserve local-first (architectural invariant);
  cannot break existing tutor/quiz entry points (UX contract);
  must work offline (product boundary)
"
```

---

## ❌ Anti-Pattern 7: "Premature waves"

Создать wave до того, как первый package доказал value.

**Почему плохо:** Commitment без validation, если первый package failed → wave wasted.

**Правильно:**
1. Создать один package из ideation
2. Deliver и measure impact
3. Если success → создать wave для follow-up
4. Если failure → pivot без wave overhead

---

## ❌ Anti-Pattern 8: "AI без baseline measurement"

Предложить ML/LLM-фичу без текущей rule-based метрики и без eval contract.

**Почему плохо:** модель может выглядеть умнее в демо, но ухудшить latency, стоимость или обучающий результат.

**Правильно:**
1. Row 13 → `po_router_evaluation_gate.md`
2. Зафиксировать primary metric, baseline, fallback и failure plan
3. Только потом Row 15 → Hybrid Intelligence package

---

## ❌ Anti-Pattern 9: "Eval harness never converges"

Бесконечно менять prompt/model/data, когда eval дважды не достигает target.

**Почему плохо:** roadmap тратит capacity на недоказанный сигнал, а deterministic baseline не улучшается.

**Правильно:** после одного bounded iteration выбрать `park`, `iterate` с меньшим scope или `reject` по Failure Modes.

---

## ❌ Anti-Pattern 10: "Model-first вместо data-first"

Начать training/policy-learning до сбора локальных событий и privacy-safe датасета.

**Почему плохо:** модель учится на синтетике или случайном шуме, а продукт получает ложную уверенность.

**Правильно:** сначала collection/UI/telemetry package, затем минимум 4 недели данных или явный waiver в registry.

---

## 🚨 Red Flags (когда роутер не работает)

| Pattern | Threshold | Действие |
|---------|-----------|----------|
| **Ping-pong** — переключение между промптами | >3 раз | Review decision tree |
| **Abandoned Ideation** — artifact не используется | >7 дней | Escape Hatch #3 |
| **Duplicate Work** — новый package дублирует closed | write-set overlap >50% | Добавить "Related Closed" check |
| **Scope Creep** — package вырос 2x+ от estimate | 2x growth | Split или re-estimate |
