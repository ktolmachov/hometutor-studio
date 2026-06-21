# PO Router — Escape Hatches

Модуль роутера продуктового планирования.  
Основной файл: [`product_owner_router.md`](product_owner_router.md).

Актуализировано: **2026-05-08**

---

## Когда роутер не может продолжить

### Сценарий 1: Ideation вернул 0 viable ideas

**Симптом:** Все идеи нарушают constraints или имеют score < 2.0

**Действия (в порядке приоритета):**

1. **Проверить constraints** — возможно, слишком жёсткие
   ```text
   Пример: "must explain why action chosen" блокировал 8 из 10 идей
   Решение: Ослабить до "should explain" или "explain for P0 actions only"
   ```

2. **Расширить ANGLES** (было: UX, Pedagogy → стало: + Retention, Accessibility)

3. **Изменить TARGET** (выбрать соседний CJM stage или шире)

4. **Снизить N_IDEAS** (было: 15 → стало: 5)

5. **Если всё ещё 0** → **STOP и escalate к Product Owner**

---

### Сценарий 2: Plan-next blocker + пустой backlog

**Симптом:** Нет eligible candidates, нет open US, нет deferred

**Действия:**

1. **Запустить MODE=CANDIDATE_TABLE** для инвентаризации

2. **Если таблица пуста** → проверить `doc/cjm.md` §8 Pain Table
   ```powershell
   Select-String -Path doc/cjm.md -Pattern "pain:" | Select-String -NotMatch "closed:"
   ```

3. **Если все pains closed** → 🎉 **Feature Completeness**
   - Собрать user feedback для новых pain points
   - Retrospective ideation (улучшение существующих фич)
   - Или объявить maintenance mode

4. **Если есть pains без US** → создать US через Analyst role

---

### Сценарий 3: Owner paralysis (не может выбрать > 3 дней)

**Действия:**

1. **Lightweight spike** (1-day proof-of-concept) для top-2 идей
2. **Собрать user feedback** (A/B опрос, 5-10 ответов)
3. **Применить default heuristic** (выбрать идею с highest score)
4. **Если всё ещё блок** → defer wave и взять следующий candidate

---

### Сценарий 4: Ideation scope explosion (20+ идей)

**Действия:**

1. **Stricter ranking** (только score ≥ 7.0)
2. **Split по темам** (3 artifacts, owner выбирает тему)
3. **Reduce N_IDEAS** для следующего run

---

### Сценарий 5: AI eval gate не проходит

**Симптом:** Row 13 выявил, что primary metric, baseline, test set или fallback нельзя описать воспроизводимо.

**Действия:**

1. Выбрать один outcome из `po_router_evaluation_gate.md`: `park`, `iterate`, `reject`.
2. Если выбран `iterate`, разрешён один bounded pass: сузить scope, снизить target или добавить deterministic mitigation.
3. Если после bounded pass контракт всё ещё невалиден — `reject` AI framing и вернуться к rule-based улучшению.

---

### Сценарий 6: Hybrid package требует данных, которых ещё нет

**Симптом:** Row 15 выглядит правильно, но model/policy phase зависит от событий, которых нет в telemetry.

**Действия:**

1. Split package: сначала collection/telemetry/UI feedback без model-serving.
2. Записать re-entry condition: например, "4+ недели событий" или "N локальных samples".
3. Держать model package в `proposed`/`deferred`, пока condition не выполнено или PO явно не оформит waiver.
