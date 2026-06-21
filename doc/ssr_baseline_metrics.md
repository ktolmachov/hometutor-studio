# SSR rule baseline (pre–ML reranking)

Фиксированная **лестница приоритета** в `build_smart_study_recommendation` (`app/ui/adaptive_plan_card.py`):

1. `flashcard_due_n > 0` → `cards_due` / `flashcards_review`
2. иначе `sm2_due_n > 0` → `sm2_due` / `sm2_tutor`
3. иначе провал мини-quiz (`fail`, `failed`, `incorrect`, `wrong`, `bad`, `partial`) → `quiz_failed` / `quiz_recovery_tutor`
4. иначе поверхность `adaptive_plan` с блоком плана и без очередей fc/sm2 → `adaptive_plan` / `plan_block_tutor`
5. иначе tutor resume с непустой темой → `tutor_resume` / `tutor_resume`
6. иначе `has_last_answer_qa` → `answer_ready` / `qa_continue`
7. иначе weak concept или reading resume → `mastery_stale` / `tutor_weak_gap`
8. иначе → `safe_default` / `safe_tutor_5min`

**Инварианты secondaries:** 2–4 действия; при `cards_due` на `flashcards_hub` нет `fc_create`.

## Regression harness

| Suite | Назначение |
|-------|------------|
| `tests/test_smart_study_router.py` | Функциональные и UX-контракты SSR (существующие кейсы) |
| `tests/test_smart_study_router_comprehensive.py` | Массовая параметризация приоритетов и поверхностей (baseline перед hybrid) |

Подсчёт тестов в comprehensive-модуле: `pytest tests/test_smart_study_router_comprehensive.py --collect-only -q` (ожидается **≥100** тестов).

## Baseline для ML reranking

Hybrid-слой не должен нарушать: при отключенном reranking или fallback результаты должны совпадать с rule-приоритетом выше; отклонения только при явном включении модели и контракте merge (вне этого пакета).
