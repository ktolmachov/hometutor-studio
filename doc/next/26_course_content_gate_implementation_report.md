# #26 Course Content Gate + Verified Step: Implementation Report

**Волна: #26 P0-A + P0-B · hometutor runtime · 2026-07-20**

---

## Статус

| Параметр | Значение |
|---|---|
| Plan | `hometutor-studio/doc/next/course_content_gate_compiler_plan.md` |
| E2 (живой семпл) | ✅ выполнен до implementation (2026-07-19) |
| E2 адьюдикация | ✅ `eval_data/content_gate_e2_2026-07-19/semantic_adjudication_2026-07-19.md` |
| **P0-A Gate Packet** | ✅ shipped |
| **P0-B Verified Step Contract** | ✅ shipped |
| Tests | 68/68 PASS |
| Lint | clean (pre-existing issues not touched) |

---

## Write-set

### Новые файлы

| Файл | Строк | Назначение |
|---|---|---|
| `app/course_content_gate.py` | 469 | Pure read-only gate packet builder: role/freshness/noise/practice labels, best-source selection with reason, evidence span collection, lookup API for UI |
| `scripts/run_course_content_gate.py` | 135 | Manual runner: `--bundle-dir`, `--topic`, `--staging` |
| `scripts/compute_trusted_route_rate.py` | 200 | TLRR calculation from DB + gate report: 6-component contract, verified_quiz_question_rate, fallback_rate |
| `tests/test_course_content_gate.py` | 492 | 46 tests: role/freshness/noise/practice/selection/rejection/lookup/persistence |
| `tests/test_quiz_content_contract.py` | 315 | 18 tests: evidence binding, origin, mastery blocking, save/load |
| `tests/test_trusted_route_rate.py` | 131 | 4 tests: TLRR with mocked DB + gate report |

### Изменённые файлы

| Файл | Δ | Назначение |
|---|---|---|
| `app/user_state_db.py` | +10/-6 | Колонки `origin TEXT`, `evidence_bound INTEGER` в `quiz_results` (CREATE TABLE + migration + whitelist) |
| `app/user_state_quiz.py` | +25/-6 | Параметры `origin`, `evidence_bound` в `save_quiz_result()` |
| `app/prompts/_impl.py` | +4/-3 | `QUIZ_SCOPED_PROMPT`: поле `source_quote` + правило дословной цитаты |
| `app/quiz_scoped.py` | +36/-1 | `_normalize_scoped_questions`: поле `source_quote`; NEW `evidence_bound_for_questions()`; вызов после parsing |
| `app/quiz_micro.py` | +21/-2 | `origin="fallback"` + `evidence_bound=False` в fallback; `origin="micro_quiz"` в LLM-пути; передача в `process_micro_quiz_outcome` |
| `app/fact_source_binding.py` | +16/-1 | `apply_quiz_outcome_to_learner_state`: параметр `evidence_bound`; блокирует mastery/SR при `evidence_bound=False` |
| `app/knowledge_graph_bundle.py` | +33/-0 | Non-fatal хвост `_write_content_gate_sidecar_if_viable()` после `write_graph_quality_report_sidecar` |
| `app/ui/living_konspekt_reader.py` | +46/-0 | Expander «Почему этот фрагмент — основной источник» с gate-статусом |
| `app/ui/scoped_quiz.py` | +14/-1 | «Завершить» — передача `origin="scoped_quiz"` и `evidence_bound` |

---

## Что сделано — P0-A (Course Content Gate Packet)

1. **`course_content_gate_report.json`** — sidecar рядом с `graph_quality_report.json` в бандле генерации:
   - Темы с конкурирующими источниками (≥2 документов на концепт)
   - Детерминированные ярлыки: роль (конспект.md / транскрипт.txt / living-konspekt), freshness (mtime + sha256), шумность ASR, practice-сигналы
   - Best-source choice **with reason** + rejected/secondary **with reason** (ничего не удаляется)
   - Приоритет multi-folder topics (≥2 course folders)

2. **Интеграция в reindex хвост** — `_write_content_gate_sidecar_if_viable()` вызывается после `write_graph_quality_report_sidecar` в `write_bundle_via_compiler`. Non-fatal: сбой content gate не блокирует publish графа.

3. **UI-блок** — expander «Почему этот фрагмент» в reader Живого конспекта:
   - Статус `best`: показывает причину выбора
   - Статус `rejected`: показывает причину + путь лучшего источника
   - Нулевое влияние на производительность (lookup — dict search)

4. **`freshness_labeled_step_rate`** — считается для gated-тем (доля тем, где хотя бы один источник имеет свежесть ≠ «неизвестно»)

---

## Что сделано — P0-B (Verified Learning Step Contract)

1. **Quiz evidence binding:**
   - `QUIZ_SCOPED_PROMPT` требует поле `source_quote` — дословную цитату из материала
   - `evidence_bound_for_questions()` — нормализованный exact-match (collapse whitespace, substring) цитаты в generation context
   - Каждый вопрос получает `evidence_bound`: 1 (цитата найдена) или 0 (не найдена)
   - Результат: `evidence_bound_count` / `evidence_total` в ответе генерации

2. **Mastery только от validated:**
   - Аддитивные nullable-колонки `quiz_results.origin TEXT`, `evidence_bound INTEGER`
   - Миграция backward-compatible: старые строки → `NULL` = «не оценено»
   - `apply_quiz_outcome_to_learner_state(evidence_bound=False)` → `evidence_blocked=True`, mastery и SR **не** обновляются
   - `evidence_bound=None` (legacy) → поведение без изменений
   - Аудит-след: невалидированный исход пишет `quiz_results` с `evidence_bound=0`

3. **Fallback gate:**
   - `_fallback_micro_quiz` → `origin="fallback"`, `evidence_bound=False`
   - `process_micro_quiz_outcome` передаёт origin/evidence_bound в `save_quiz_result` и `apply_quiz_outcome_to_learner_state`
   - Fallback-микро-квиз **не** обновляет mastery и SR

4. **North star wiring:**
   - `scripts/compute_trusted_route_rate.py` — считает TLRR из DB + gate report
   - 6 компонент контракта: source address, evidence span, freshness label, grounded explanation (TBD), verified quiz, selection reason
   - `verified_quiz_question_rate` = evidence_bound / total из `quiz_results`
   - `fallback_rate` = count(origin='fallback') / total
   - Replayable из DB без повторной генерации

---

## Что НЕ сделано (kill switch — соблюдён)

- ❌ Новая БД/схема/пайплайн — только аддитивные nullable-колонки
- ❌ Runtime LLM-judge
- ❌ Новые хранилища
- ❌ Изменение `node_worth` / SSR ranking formulas
- ❌ Token-overlap как proof of groundedness
- ❌ Semantic entailment (#25 P2) — остаётся offline

---

## DoD verification

| Gate | Статус |
|---|---|
| 3–5 тем эталонного бандла (guardrails/agentic-loop/rag) | ✅ (synthetic payload в тестах) |
| Audit packet воспроизводим, без новой БД/схемы, без LLM | ✅ (read-only JSON sidecar) |
| Студент видит ≥1 «почему этот фрагмент лучше» с причиной | ✅ (expander в reader) |
| `freshness_labeled_step_rate` считается для gated-тем | ✅ |
| Quiz без evidence не обновляет mastery (тест) | ✅ `test_apply_outcome_evidence_bound_false_blocks_mastery` |
| Fallback не обновляет mastery (тест) | ✅ `test_fallback_micro_quiz_has_origin_and_evidence` |
| `origin`/`evidence_bound` персистентны; старые строки читаются (NULL) | ✅ `test_save_quiz_result_stores_origin_and_evidence` / `test_save_quiz_result_legacy_no_origin` |
| TLRR + `verified_quiz_question_rate` + `fallback_rate` считаются | ✅ `test_tlrr_with_data` |
| Targeted tests зелёные | ✅ 68/68 PASS |
| Связанные тесты не сломаны | ✅ `test_course_graph_compiler_evidence.py` + `test_graph_publish_status.py` — 14/14 PASS |

---

## Post-ship

Replay боль-якоря «уголовное наказание…» из E2:
- Без evidence-статуса **не** должен попасть в mastery — P0-B закрывает отсутствие цитаты/evidence
- Semantic entailment offline — P1/P2 (#25), не P0
- TLRR baseline 0% → первый замер после первого реиндекса с новым кодом

---

*Создано: 2026-07-20 · #26 P0-A + P0-B closed.*
