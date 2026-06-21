# PO Router — Ideation Scope Decision Matrix

Модуль роутера продуктового планирования.  
Основной файл: [`product_owner_router.md`](product_owner_router.md).

Актуализировано: **2026-05-08**

---

## Правило масштаба после ideation

| Идей | Cohesion | Решение | Обоснование |
|------|----------|---------|-------------|
| 1 | N/A | `product_owner_plan_package_prompt.md` | Один package |
| 2 | **High** (same CJM stage) | `product_owner_plan_package_prompt.md` | Объединить в один package |
| 2 | **Low** (разные stages) | Два отдельных packages | Раздельная поставка |
| 3-5 | **High** (shared foundation) | `generate_roadmap_epoch_waves_prompt.md` | Multi-wave horizon |
| 3-5 | **Medium** | Отдельные packages | Не форсировать wave |
| 3-5 | **Low** | Отдельные packages | Независимая поставка |
| 6+ | Any | **Split по темам** → несколько ideation runs | Слишком широко для одной волны |

---

## Cohesion Signals

| Signal | High Cohesion | Low Cohesion |
|--------|---------------|--------------|
| **Write-set overlap** | ≥3 файла пересекаются | <2 файла пересекаются |
| **CJM moments** | Same moment или adjacent (#2→#3) | Разные moments (#2 и #12) |
| **Dependency chain** | Idea B requires idea A | Независимые идеи |
| **User story epic** | Same epic (US-20.x) | Разные epics (US-14.x и US-20.x) |
| **Method source** | Same analog (все из Duolingo) | Разные analogs (Duolingo + Anki + Khan) |
| **Implementation layer** | Same layer (все UI) | Разные layers (UI + backend + infra) |

### Hybrid Intelligence Scope

Use this scope when an idea combines an existing deterministic baseline with an
ML/LLM enhancement.

Signals:

- There is a rule-based or template-based baseline already working.
- ML/LLM improves ranking, personalization, planning, or explanation but does
  not replace the baseline.
- A fallback is required when inference fails, confidence is low, or latency is
  outside bounds.
- Explainability is part of the user value or trust contract.

Package structure:

1. **Phase 1: Baseline Hardening**
   - Document the current deterministic behavior.
   - Add or identify tests that preserve the baseline.
   - Measure baseline metrics before AI work starts.

2. **Phase 2: ML/LLM Layer**
   - Create an evaluation contract with
     [`po_router_evaluation_gate.md`](po_router_evaluation_gate.md).
   - Define data, prompt, or model artifacts.
   - Integrate with a deterministic fallback.

3. **Phase 3: Hybrid Orchestration**
   - Combine rule baseline, AI adjustment, and explanation trace.
   - Monitor quality, latency, cost, and fallback rate.
   - Optionally compare rule-only vs hybrid behavior.

Example: SSR Level 1 Local ML Layer

- Baseline: current rule priority for next study action.
- ML layer: rerank using a local forgetting-curve signal.
- Fallback: if model load or inference fails, use baseline priority.
- Explainability: show rule priority plus the ML adjustment reason.

### Manual Cohesion Assessment

```text
1. Посчитать signals из таблицы Cohesion Signals
2. Если ≥4 signals → High (≥0.7) → consider wave
3. Если 2-3 signals → Medium (0.4-0.7) → separate packages
4. Если ≤1 signal → Low (<0.4) → definitely separate
```

---

## Проверка покрытия CJM (из roadmap.md §7)

Перед ideation проверить, какие моменты истины уже покрыты:

```powershell
# Прочитать таблицу покрытия:
Select-String -Path doc/roadmap.md -Pattern "Follow-up"
```

---

## Баланс типов волн

> ⚠️ Перед созданием новой волны проверить баланс типов (из `roadmap.md` §6.1):
> - Целевой баланс: 70% user-facing, 30% platform
> - Если Platform > 50% → приоритет user-facing волнам

---

## Примеры применения

### Пример 1: 3 идеи, High Cohesion → Wave

```text
# [two-root] Two-repo project: resolve app/** and requirements.txt against CODE_ROOT
# (editable install of `hometutor`: `pip show hometutor` -> "Editable project location");
# resolve doc/**, tests/**, scripts/** against the current cwd (DOCS_ROOT).
# Run git per-root: `git -C <CODE_ROOT> ...` for app code, `git -C <cwd> ...` for docs/tests.
Идеи:
1. Contrastive router explanation (US-20.7)
2. Route confidence ledger (US-20.8)
3. Learning debt queue (US-20.9)

Cohesion signals:
- Write-set: app/ui/smart_router.py, app/study_router_policy.py (overlap: 2+)
- CJM: cross-loop (same moment)
- Dependency: ledger extends explanation
- Epic: US-20.x (same)
- Method source: trust/explainability (cohesive)
- Layer: UI + policy (mixed but coupled)

Assessment: ≥4 signals → High → wave
```

### Пример 2: 4 идеи, Low Cohesion → Separate packages

```text
Идеи:
1. Flashcard deck export (US-15.x)
2. Course graduation overlay (US-17.x)
3. Answer quality eval gate (infra)
4. Home mode intent ordering (US-14.x)

Assessment: ≤1 signal → Low → 4 separate packages
```
