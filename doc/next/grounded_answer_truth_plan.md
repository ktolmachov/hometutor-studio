# «Ответ под присягой» — Semantic Groundedness: Plan

**Разбор №25 · hometutor · runtime HEAD 1c9c56961 · 2026-07-19**

---

## Статус

| Параметр | Значение |
|---|---|
| E1 (код/конфиг) | ✅ верифицировано |
| E2 (живой семпл) | 🔴 0/15 валидных ответов — API и индекс доступны; LM Studio вернул `503 Loading model`, повтор остановлен retry-guard |
| SGAR baseline | не измерен |
| P0 выбран | нет — до E2 остаются два проверяемых кандидата |

---

## North Star

**SGAR** = Semantic Grounded Answer Rate

```
SGAR = count(ответов, где каждый существенный claim entailed из источника
             AND OOC обработан корректно)
     / count(оценённых ответов)
```

Целевой процент не назначается до первого живого E2 baseline.

---

## Пользовательский контракт

> «Каждое существенное утверждение ответа либо доказуемо следует из конкретного фрагмента учебного материала, который можно открыть и проверить, либо явно маркируется как недостаточно подкреплённое; если данных в корпусе нет — система говорит это прямо.»

---

## Ключевые E1-факты

### Центральный разрыв: citation binding не проверяет semantic entailment

```python
# app/grounded_answer.py::_build_facts_from_text
# Для каждого блока валидируются [N] и существование source.
# Смысл claim не сравнивается с source["text"].
```

`app/query_response_postprocessing.py` уже включает в каждый API source поле
`text` (до 500 символов), а ledger содержит `fact_text` и `cite_index`.
Следовательно, offline-eval может соединить их по `cite_index` без расширения
публичного API и без дублирования полного chunk в debug.

### Cache-hit bypass

```python
# app/grounded_answer.py:461
if not settings.grounded_answer_contract_enabled or cache_hit:
    return GroundedValidationResult(answer_text=answer_text, skipped=True)
```

Все cache-hit ответы возвращаются без повторной grounding-проверки. Это не
доказывает изменение смысла кэшированного ответа, но не позволяет доказать, что
cache entry был получен при той же ревизии grounded-контракта и source payload.

Дополнительные bypass (тот же файл):
- `answer_path_mode == "two_stage_early"` → строка 471
- `not sources` → строка 464  
- Guardrail violation (empty/pii/suspicious) → строки 476-482

### home_rag_gate не в CI

`.github/workflows/ci.yml` запускает: ruff, pytest, arch_regression_guards.  
`scripts/home_rag_integration_gate_v1.py` — не упоминается.

Gate запускается с `GROUNDED_ANSWER_STRICT_QA=0` (строка 184 скрипта) — намеренно relaxed.  
15 eval-кейсов проверяют: keyword presence, cite bounds, OOC no-citation.  
Semantic entailment, numeric fidelity — не проверяются.

### Что НЕ делает `_build_facts_from_text`

```python
# app/grounded_answer.py:183-215
# Для каждого блока текста:
#   1. Парсит [N] маркеры
#   2. Проверяет cite_index в source_lookup (структурно)
#   3. Строит CitationProvenance{cite_index, relative_path}
# НЕ делает: загрузку текста чанка, сравнение claim с chunk
```

### Метрика citation_coverage существует, но не видна студенту

```python
# app/grounded_answer.py:247-251
def _citation_coverage(facts):
    cited = sum(1 for fact in facts if fact.provenance)
    return round(cited / len(facts), 4)
# → кладётся в debug.citation_coverage, не в UI
```

---

## P0 — два кандидата, не выбранные до E2

### Candidate P0-A: course-specific SGAR evidence packet

**Боль:** ручной `home_rag_gate` использует фиксированный корпус и не создаёт
воспроизводимый evidence packet по активному пользовательскому курсу.

**Предварительный write-set:** новый operator/eval script в `scripts/` + версия
кейсов/результата в `eval_data/`; runtime API не менять.

**Изменение:** runner сохраняет question, raw answer, runtime snapshot,
`sources`, provenance ledger, cache state и ручную/независимую разметку R1–R8.
Пара claim→source строится offline по уже существующему `cite_index`.

**Acceptance criteria:**
- 15 валидных ответов = 5 категорий × 3 повтора;
- raw outputs не теряются;
- SGAR считается только после независимой semantic-разметки;
- structural checks и semantic verdict хранятся раздельно.

**Тест:** fixture с answer + sources проверяет join по `cite_index`, отсутствие
потерянных outputs и запрет вычислять SGAR без semantic verdict.

**Observability:** versioned JSON/Markdown report; без нового DB.

**Effort:** 0.5–1 день после успешного E2 preflight.

**Kill switch:** если для runner требуется менять публичный API или добавлять DB — стоп; использовать существующий response payload.

---

### Candidate P0-B: grounded contract revision parity для cache

**Боль:** cache-hit возвращает `skipped=True`; простая метка причины показывает
обход, но не доказывает, что entry валидировался текущей ревизией контракта.

**Предварительный write-set:** request-cache contract +
`app/grounded_answer.py::apply_grounded_validation`; уточнить после E2 и аудита cache key/payload.

**Изменение:**

```python
# Candidate contract:
# cache entry несёт grounded_contract_revision + validation outcome.
# При отсутствии/устаревании revision: deterministic revalidation либо cache miss.
```

**Acceptance criteria:**
- cache-hit не считается grounded только по факту cache-hit;
- stale/legacy entry не обходит текущий deterministic contract;
- debug различает validated-current / revalidated / stale-miss.

**Тест:**
```python
# acceptance должен покрывать current, stale и legacy cache entries
```

**Observability:** cache validation status + contract revision в debug/log.

**Effort:** определить после read-only аудита cache contract; не заявлять «1 строка».

**Kill switch:** если требуется новая схема/DB или ломается cache latency budget — не включать в P0; оставить parity кейсом offline gate.

---

## P1 — Следующий уровень (после E1+E2)

### P1-A: Deterministic evidence checks — не SGAR proxy

**Файл:** `scripts/evidence_binding_check.py` [NEW]

Проверяет только разрешимость citation, наличие evidence text, точное сохранение
чисел/единиц и полноту цитирования. Token overlap может быть диагностикой, но
не является entailment и не входит в числитель SGAR.

**Dependency:** evidence packet из Candidate P0-A.

**Effort:** ~4ч

---

### P1-B: Operator protocol — home_rag_gate

Добавить в `docs/conventions_reference.md` или создать `docs/operator_runbook.md`:

```
# Обязательный preflight перед реиндексом или сменой модели/промпта:
.\.venv\Scripts\python.exe scripts/home_rag_integration_gate_v1.py --preflight-only
```

15 кейсов gate покрывают structural regression. Для полного прогона (с LLM):
```
.\.venv\Scripts\python.exe scripts/home_rag_integration_gate_v1.py \
    --llm-base-url http://127.0.0.1:8080/v1 \
    --llm-model <model_id>
```

**Effort:** ~1ч

---

## P2 — Offline LLM-judge (после E2)

**Файл:** `eval_data/sgar_baseline_v1.json` [NEW]

Запустить E2 семпл (15 ответов × 5 категорий по рубрике §4 разбора).  
LLM-judge оценивает R3 (entailment) и R5 (synthesis).  
Первый числовой SGAR baseline.  
Judge той же модели — только proxy, явно помечен.

**Dependency:** P0-A + P1-A + живой endpoint

**Effort:** ~1 рабочий день

---

## E2: Методология (зафиксирована, выполнение pending)

**Условия прогона (фиксируются до генерации):**
- Модель: `qwopus3.6-35b-a3b-v1-mtp` (runtime config на момент preflight)
- Provider: локальный LM Studio; валидная генерация не получена (`503 Loading model`)
- Prompt revision: фиксировать symbol/hash непосредственно перед новым прогоном; не приписывать непроверенную версию
- Retrieval snapshot: фиксировать фактический trace каждого ответа, а не заранее объявленный top_k
- Корпус preflight: индексированный scope `ИИ Агенты` из `D:\AI\app\data`
- Cache: LLM_REQUEST_CACHE_PERSIST=true
- HEAD preflight: 1c9c56961
- GROUNDED_ANSWER_STRICT_QA: true (live, не gate)

**Категории (5 × 3 = 15):**
1. Прямой факт из одного источника
2. Синтез из нескольких источников
3. Конфликтующие / неоднозначные источники
4. Вопрос вне корпуса (OOC)
5. Числовой / citation / cache-hit trap

**Рубрика (R1–R8, предзафиксирована):**
- R1: Выделены существенные claims
- R2: Citation target существует (deterministic)
- R3: Entailment: claim ← chunk text (offline LLM proxy)
- R4: Числа, единицы, отрицания сохранены (regex + human)
- R5: Multi-source synthesis корректен (offline LLM proxy)
- R6: Citation completeness — все claims покрыты (deterministic)
- R7: Abstention correctness для OOC (deterministic)
- R8: Answer usefulness (human only)

---

## Kill Switch

Остановить или вынести из P0, если ход:
- Требует нового DB/schema/хранилища → **стоп для обоих кандидатов**
- Добавляет runtime LLM-judge → **нет** (LLM только в P2 offline)
- Считает наличие cite_index доказательством истинности → **нет**
- Отключает существующий grounded guard → **нет**
- Требует полной переработки retrieval → **нет**
- Назначает baseline без живого измерения → **нет** (SGAR target не назначается)
- Скрывает cache-hit/cache-miss → **стоп**

---

## Связи с предыдущими разборами

| Разбор | Тема | Отличие от №25 |
|---|---|---|
| №5 | Устойчивость доставки ответа | Не проверял истинность утверждений |
| №10 | Видимость trace | Observability, не groundedness |
| №11 | Сценарии использования | Покрытие use-cases, не semantic binding |
| №24 | Качество квизов и честность mastery | Mastery, не provenance пары (утверждение, источник) |

---

*Актуализировано: 2026-07-19 · runtime HEAD 1c9c56961 · E1 verified · E2 0/15 valid · P0 not selected*
