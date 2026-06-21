# Рекомендации по развитию дорожной карты — 2026-06-11

> **Источник:** аудит и актуализация roadmap-документов 2026-06-11
> (`roadmap.md`, `future_roadmap.md`, `ssr_ai_vision_summary.md`,
> `localhost_balance_course_delight_breakthrough.md` v5).
> **Назначение:** трекинг решений владельца по рекомендациям. Это **не** SSoT
> исполнения — принятые рекомендации превращаются в волны/пакеты в
> `doc/backlog_registry.yaml`; здесь отмечается только судьба самой рекомендации.

## Как вести статус

| Статус | Значение |
|---|---|
| `proposed` | Рекомендация зафиксирована, решение владельца не принято |
| `accepted` | Принята; указать package/wave id в колонке «Привязка к SSoT» |
| `in_progress` | Соответствующий пакет в `ready`/`wip` |
| `done` | Соответствующие пакеты закрыты (проверять по `backlog_registry.yaml`) |
| `declined` | Отклонена; кратко указать причину в «Заметки» |
| `superseded` | Поглощена другой рекомендацией/волной; указать какой |

При изменении статуса обновлять колонку «Обновлено» (дата) и «Заметки».

---

## Реестр рекомендаций

| # | Рекомендация | Приоритет | Статус | Привязка к SSoT | Обновлено | Заметки |
|---|---|---|---|---|---|---|
| R1 | **Дожать активную волну Graph Evidence до uplift gate**, не включая graph-aware retrieval без измеренного uplift; закрепить uplift-gate паттерн как стандарт для всех будущих retrieval-изменений | P1 | in_progress | `wave-course-graph-evidence-2026-06`: `course-graph-relation-ux-v1` (ready) → `course-graph-aware-uplift-gate-v1` | 2026-06-11 | Волна уже активна; рекомендация — про дисциплину завершения и перенос паттерна в conventions |
| R2 | **Закрыть две полуоткрытые волны прежде, чем открывать новые**: хвосты `ragas-langfuse-dataset-v1` и `smart-notes-native-generation-v1` | P1 | proposed | `wave-ragas-eval-harness` (ready, 1/2 closed), `wave-smart-notes-killer-feature` (1/2 closed) | 2026-06-11 | Полузакрытые волны — главный источник SSoT-drift (чинился пакетами `epoch-ssot-drift-*` дважды) |
| R3 | **«Usage sprint» — накопление реальных данных для SSR serving promotion**: регулярные реальные учебные сессии на курсе «ИИ Агенты»; цель — снять cold-start (73/1000 real samples для L1) и набрать 4+ недель planner/feedback telemetry для L3/L5 | P0 | proposed | Разблокирует: L1 hybrid serving gate, `ml-ssr-plan-optimization`, L5 online policy | 2026-06-11 | Главный блокер теперь данные, а не код; session tape + receipts уже собирают всё нужное |
| R4 | **Measurement loop как следующая волна после Graph Evidence**: `wave-pii-masking-redaction` → `wave-langfuse-eval-loop` (порядок обязателен — PII masking прописан в kill switch Langfuse-волны) | P1 | proposed | `wave-pii-masking-redaction`, `wave-langfuse-eval-loop` (обе proposed) | 2026-06-11 | Цикл «трейс → датасет → промпт → прогон» умножает ценность eval-активов (RAGAS, adversarial corpus, latency budgets) |
| R5 | **Grounding/abstain contract — кандидат на следующий продуктовый прорыв**: строгий контракт «нет источника → abstain, не выдумка» как категорийный дифференциатор local-first learning OS | P1 | proposed | `wave-grounding-abstain-contract` (proposed) | 2026-06-11 | Логичное продолжение honest-status философии Graph Evidence; сочетается с RAGAS answer_correctness |
| R6 | **Закрыть остаточный gap закрытой Localhost Delight волны**: user-facing cloud consent control (малый UI-пакет) | P2 | proposed | Пакет не заведён; gap зафиксирован в breakthrough v5 §4 | 2026-06-11 | Единственный незакрытый пункт из v4/v5 brief |
| R7 | **Сместить баланс роадмапа с «новые фичи» на «качество доказательств и дистрибуцию»**: production deployment (VPS/Docker), quickstart «3 команды до локального запуска»; gamification/collaborative оставить P2/L | P2 | proposed | Пакеты не заведены | 2026-06-11 | v1 feature-complete доказан Golden E2E 2026-06-10; не переоткрывать закрытые эпохи ради смежных фич |
| R8 | **Гигиена роадмапа: генерация таблицы волн в `roadmap.md` из `backlog_registry.yaml`** по аналогии с `tasklist.md` — убрать ручное ведение, устаревающее за неделю | P2 | proposed | Кандидат: расширение `scripts/backlog_registry_lint.py` или отдельный скрипт | 2026-06-11 | Объём ручных правок 2026-06-11 — прямое следствие отсутствия генерации |

---

## Рекомендованный порядок (на 2026-06-11)

1. R1 — завершить активную волну (relation UX → uplift gate).
2. R3 — запустить usage sprint параллельно с любой инженерной работой (не конкурирует за execution slot).
3. R2 — закрыть хвосты ragas / smart-notes.
4. R4 — measurement loop (PII masking → Langfuse).
5. R5 — grounding/abstain contract.
6. R6–R8 — по мере освобождения слота / решением владельца.

## Связанные документы

- [`../roadmap.md`](../roadmap.md) — карта эволюции и волн
- [`../future_roadmap.md`](../future_roadmap.md) — стратегический горизонт и правила re-entry
- [`../backlog_registry.yaml`](../backlog_registry.yaml) — SSoT исполнения
- [`../team_workflow/ssr_ai_vision/ssr_ai_vision_summary.md`](../team_workflow/ssr_ai_vision/ssr_ai_vision_summary.md) — serving gates для R3
- [`localhost_balance_course_delight_breakthrough.md`](localhost_balance_course_delight_breakthrough.md) — closure brief, источник R6
