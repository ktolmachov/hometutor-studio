# Невидимая половина: закрытие ядра петли — Composition Plan

Updated: 2026-07-12

Status: corrective P0 envelope promoted. Это **не** SSoT исполнения (SSoT — `doc/backlog_registry.yaml`).
На 2026-07-12 активный package: `invisible-half-p0-closure-v1` в `wave-invisible-half-p0-closure` (wip).
Пакет создан как процессная фиксация уже начатого runtime diff; дальнейшее расширение scope запрещено — только proof/verification/closure через штатный workflow.

Owner: product / learning loop

Source: эволюционный разбор №8 «Невидимая половина» (метаразбор серии,
`doc/presentations/evolutionary_analyses/08_invisible_half.html`).

## Чем этот план отличается от остальных в doc/next/

Это **композиционный** план: он не вводит новых кандидатов, а собирает сильный ход из
кандидатов уже существующих detail-планов и фиксирует их актуальный статус по коду.
Ключевая находка разбора №8: статусы в detail-планах отстают от кода — часть кандидатов
уже реализована без промоута волн из планов. Перед промоутом любого кандидата — сверка с HEAD.

## Статус-снимок 40 кандидатов (проверен на hometutor @ 35e5db3 «185», 2026-07-12)

| План | Кандидаты | Shipped на HEAD 185 | Живо |
|---|---|---|---|
| `learning_plan_single_source_plan.md` (№7) | 7 | **7/7** (все волны A/B/C; `wave-learning-plan-single-source` closed в registry) | — |
| `infographics_living_map_plan.md` (№6) | 5 | **A1** (download живой карты, `dashboards_graph.py:1090`), **A2** (`section_diagram` в `app/prompts/_impl.py` + workbench; mermaid вендорен `app/ui/assets/mermaid.min.js`, CDN только fallback) | B1, C1, C2 |
| `first_ten_minutes_onboarding_plan.md` (№2) | 7 | **A1** (единый резолвер кандидатов: `course_cache.py:493-523`, `ingestion_support.py:289`) | A2 (hero всё ещё безусловно «готовится», `mission_control_first_session.py:217`), B1, B2, B3, C1, C2 |
| `material_as_product_quality_plan.md` (№3) | 6 | частично: метрики docs_participating в prepare-view (`course_prepare_view.py:414`) | A1 (на Mission Control свежести нет — 0 упоминаний в `mission_control.py`), A2, B1, B2, C1, C2 |
| `knowledge_fate_memory_loop_plan.md` (№1) | 6 | **0** (появился `flashcard_review_log`, `user_state_flashcards.py:416` — журнал, не концептная память) | все 6. Якорь жив: `query_response_postprocessing.py:407` передаёт `{}`, `learner_model_service.py:528` — только cognitive_load −0.05; в `flashcard_service.py` 0 упоминаний apply_sm2/spaced_repetition/provenance |
| `trust_under_load_provider_plan.md` (№5) | 4 | **0** (в `llm_resilience.py` 0 упоминаний circuit; `HOME_RAG_LLM_FALLBACK_ENABLED=false`, `config.env:70`) | все 4 |
| `agent_as_one_button_plan.md` (№4) | 5 | **0** (`app/routers/agent.py` не существует; `query_mode="agent"` нигде в app не устанавливается). Обострение: `AGENT_ENABLED=true` уже в `config.env:82`, комментарий строкой выше устарел («Выключено по умолчанию») | все 5 |

Паттерн: shipped — только «поверхности» (видимое на скриншоте), живо — «провода»
(след, честность, дверь). Полный разбор — в HTML №8.

## P0 — два хода (не больше)

### Ход 1 «След» = promote `wave-memory-loop-closure`

Состав: **A1 + A2 из `knowledge_fate_memory_loop_plan.md`** (evidence перепроверен 2026-07-12):

- A1: `review_flashcard` → концептная память через новый provenance-тип `flashcard_review`
  (той же дверью `apply_quiz_outcome_to_learner_state`, у которой сейчас 4 quiz-only call-site:
  scoped_quiz, quiz_service, quiz_micro, fact_source_binding).
- A2: exposure-след tutor-ответа слоем ниже гейта (mastery не трогает) вместо пустого
  `outcome={}` в `query_response_postprocessing.py:407`.

Эффект: коэффициент следа 1/4 → 3/4 типов учебных действий; «дельта карты за сессию» ≠ 0
для любой сессии. Ни одного нового экрана.

### Ход 2 «Честность» = promote `wave-provider-circuit-honesty`

Состав: **A1 + A2 из `trust_under_load_provider_plan.md`**:

- A1: `record_failure/record_success` в `llm_resilience.complete_with_resilience` /
  `chat_with_resilience` — переносом уже работающего паттерна из
  `adaptive_plan_llm_explanation.py` (единственное место, где CB подключён к реальному трафику).
- A2: быстрый честный отказ ~2-3 с в ветке balanced + CB-open + fallback-выключен
  (вместо полных `HOME_RAG_LLM_LOCAL_HARD_TIMEOUT_SEC=45`). Fallback насильно не включать —
  решение владельца.

Эффект: после 3 сбоев подряд ни один запрос не ждёт дольше нескольких секунд перед честным
сообщением.

### Гигиена вне волн (однострочник, можно в любой write-set рядом)

`config.env:81-82`: комментарий «Выключено по умолчанию» при `AGENT_ENABLED=true` — привести
в честность: либо флаг в `false` до появления двери (№4 A1), либо переписать комментарий.
Требует решения владельца о желаемом дефолте.

## P1 (после ядра)

- Дверь агента: A1 (CTA «Собрать учебную сессию») + A2 (read-роутер `/agent/runs`) из
  `agent_as_one_button_plan.md` — теперь с питанием от полного следа.
- Бейдж источника ответа в Tutor chat: B1 из `trust_under_load_provider_plan.md`.
- Честный hero вместо «готовится»: A2 из `first_ten_minutes_onboarding_plan.md`.
- «Карта отстаёт на N лекций» на Mission Control: A1 из `material_as_product_quality_plan.md`.

## P2 (когда след потечёт)

- Единая очередь «Повторить сегодня» (№1 B2), кнопка «→ в карточку» (№1 B1),
  one-pager лекции + mastery-overlay (№6 B1/C1), учебный журнал прогонов агента (№4 C1).

## Метрики приёмки сильного хода

- Коэффициент следа: ≥3 из 4 типов учебных действий пишут в концептную память.
- Дельта карты за сессию: > 0 после часа занятий без квиза.
- Цена сбоя: p95 времени до честного ответа при упавшей LM Studio ≤ 3 с (сейчас до 45 с/запрос).

## Порядок и процесс

1. `multi-query-expansion-v1` и `lost-in-middle-reorder-v1` в registry закрыты; старая активная волна больше не должна вести новые runtime-правки.
2. Текущий corrective package: `invisible-half-p0-closure-v1` — SSoT envelope для уже начатого P0 diff (memory trace + provider honesty + config hygiene).
3. Выполнить только proof/verification/closure текущего package через `archive/team_artifacts/invisible-half-p0-closure-v1/orchestration_cursor_ai.md` и workflow post-agent.
4. После closure отдельно решать судьбу следующих волн: чистая `wave-memory-loop-closure` follow-up или `wave-provider-circuit-honesty` follow-up, если останется scope за пределами текущего write-set.
5. Перед стартом любого следующего package — повторная сверка evidence с HEAD (строки смещаются).

## Kill switches

- Не переоткрывать закрытые области (№7 целиком; №6 P0; №2 A1).
- Не включать cloud-fallback насильно — только честный быстрый отказ.
- Не строить новые экраны до замыкания следа.

## Связанные документы

- `doc/presentations/evolutionary_analyses/08_invisible_half.html` — разбор №8 (этот план — его слой 2)
- `doc/presentations/evolutionary_analyses/README.md` — индекс серии
- `doc/next/knowledge_fate_memory_loop_plan.md`, `doc/next/trust_under_load_provider_plan.md` —
  источники P0-кандидатов (детальные write-set/DoD там)
