# Future Roadmap

Актуализировано: **2026-06-21**

Этот файл хранит только стратегический горизонт и правила re-entry. Он не является

daily backlog и не должен конкурировать с `doc/backlog_registry.yaml`
(`doc/tasklist.md` — производный weekly view).

## Правило чтения

- Закрытые delivery horizons не разворачивать здесь в package-детали.
- История закрытых эпох хранится в `doc/closed_iterations.md` и `doc/epochs/`.
- Активные waves/packages и owner-статусы проверять только в
  `doc/backlog_registry.yaml`.
- Возврат в закрытую эпоху допустим только как owner-scoped follow-up,
  regression/maintenance exception или явно новый product gap.

## Closed Horizon Index

| Epoch | Status | Archive |
|------|--------|---------|
| **E4** Graph-Augmented Intelligence (`20.0-20.3`) | closed 2026-04-07 | `doc/epochs/e4.md` |
| **E5** Personalization & Long-term Learner (`21.0-21.2`) | closed 2026-04-08 | `doc/epochs/e5.md` |
| **E6** Agentic Tutor | closed 2026-04-09 | `doc/epochs/e6.md` |
| **E7** Production & Ecosystem | closed 2026-04-09 | `doc/epochs/e7.md` |
| **E8** User Value Delivery | closed 2026-04-10 | `doc/epochs/e8.md` |
| **E9** Trust & continuity | closed 2026-04-10 | `doc/epochs/e9.md` |
| **E10** Quality + Learning Loop Completion | closed 2026-04-11 | `doc/epochs/e10.md` |
| **E11** Guided Start + Expert Controls | closed 2026-04-11 | `doc/epochs/e11.md` |
| **E12** Flashcards + Persistent SRS | closed 2026-04-11 | `doc/epochs/e12.md` |
| **E13** Home Mode Selector / UX Tail | closed 2026-04-12 | `doc/epochs/e13.md` |

## Закрытые стратегические инициативы (post-E13)

- **Smart Study Router** — полностью доставлен: baseline (US-20.1–20.12),
  next-level (contrastive, ledger, debt, steering, receipts, quiet mode) и все
  5 бывших parked идей Wave 4–5 (Route Simulator 2026-05-22, Source-Coverage
  Guard 2026-05-22, Concept Recovery Ladder v1/v2 2026-05-23/24, Weekly
  Narrative 2026-05-31, Misroute Feedback → policy learning 2026-05-30).
  Детали: [`smart_study_router.md`](smart_study_router.md).
- **SSR AI Vision L1–L5** — инженерно доставлены все пять уровней
  (L3 weekly planner baseline 2026-05-15, L4 graph routing 2026-05-29,
  L5 misroute policy learning 2026-05-30, L2 latency remediation через
  tiered explanation gate 2026-05-23). Serving-границы сохраняются:
  L1 hybrid serving gated по cold-start (1000 real samples), L4 за feature
  flag, L5 — offline adjustments. Статус:
  [`team_workflow/ssr_ai_vision/ssr_ai_vision_summary.md`](team_workflow/ssr_ai_vision/ssr_ai_vision_summary.md).
- **Localhost Balance + Course Delight** — закрыта целиком:
  модель обновлена до `qwopus3.6-35b-a3b-v1-mtp` (llama.cpp, benchmark
  2026-06-20, rank 99.55, 185 tps); ранее `qwen/qwen3.6-27b` accepted
  (ADR-024, Smoke v7). `folder-to-course-delight-v1` closed 2026-06-05,
  `golden-e2e-graduation-v1` closed 2026-06-10,
  `prompt-role-unification-v1` closed 2026-06-11.
  Brief: [`next/localhost_balance_course_delight_breakthrough.md`](next/localhost_balance_course_delight_breakthrough.md).
- **Course Graph Evidence** — `wave-course-graph-evidence-2026-06` закрыта
  целиком 2026-06-11: compiler + relation UX + uplift gate — все 3 пакета.
- **Flashcard Handoff Fast Path** — `wave-flashcard-handoff-fast-path` закрыта
  2026-06-20: fast RAG, prose prompt, honest latency split, one-shot lifecycle.
- **Grounding / Abstain Contract** — `wave-grounding-abstain-contract` закрыта:
  abstain rate baseline, over-/under-citation tolerance, footer filtering.
- **Local llama.cpp Coding Trigger** — Phase 1 engineering milestone
  2026-06-21: `qwen/qwen3-coder-next` через llama.cpp (`/v1`, AutoFit,
  `ctx=32768`, `parallel=1`, q8 KV, reasoning off) прошёл strict no-op,
  disposable real patch и live `scripts/llamacpp_agent_trigger.ts` smoke.
  Benchmark 2026-06-29 принял `ctx=65536` как recommended coding default
  (`rank_score 94.82`, quality `13.5/13.5`, avg `62.43 tps`); `ctx=32768`
  остаётся fast fallback.
  Trigger injects read-set context, validates fenced diff against `WRITE_SET`,
  applies via `git apply --check/apply`, runs targeted tests and writes
  `execution_contract.md` only from evidence. Scope remains controlled
  low-risk patch tasks until orchestrator auto-selection is separately approved.
- **Advanced RAG (multi-query expansion + lost-in-middle reorder)** —
  `wave-advanced-rag-rewrite-rerank` закрыта 2026-06-21: оба пакета
  (`multi-query-expansion-v1`, `lost-in-middle-reorder-v1`) closed.
  Multi-query expansion расширяет одиночный запрос несколькими
  переформулировками, lost-in-middle reorder борется с деградацией
  качества при длинном контексте. Kill-switch: регрессия latency budget
  или grounded-citation rate.

## Текущий горизонт

- **Активного пакета нет** (снимок 2026-06-21). Все пакеты до 2026-06-21 закрыты.
  `wave-advanced-rag-rewrite-rerank` в статусе `wip` (волна), но оба пакета
  (`multi-query-expansion-v1`, `lost-in-middle-reorder-v1`) — `closed`.
  `wave-ragas-eval-harness` в статусе `wip` (волна), но следующий пакет
  `ragas-langfuse-dataset-v1` — `proposed`.
- Очередь proposed волн:
  `wave-ragas-eval-harness` (`ragas-langfuse-dataset-v1`),
  `wave-smart-notes-killer-feature` (`smart-notes-native-generation-v1`),
  `wave-pii-masking-redaction` (`redaction-sink-coverage-v1`),
  `wave-workflow-skills-platform` (2 пакета).
- Закрыты с 2026-06-11: `wave-course-graph-evidence-2026-06` (целиком),
  `wave-flashcard-handoff-fast-path`, `wave-grounding-abstain-contract`,
  `wave-langfuse-eval-loop`, `wave-advanced-rag-rewrite-rerank` (оба пакета
  closed 2026-06-21).
- Платформенная инициатива (proposed, не блокирует продуктовые волны):
  **Skills + Subagents Workflow Platform** — 2–4 тонких skill-адаптера
  (`/workflow`, `/resume-package`, `/orchestrate`, `/audit-chain`) поверх
  существующих `scripts/workflow.py` и генераторов промптов; промпты ролей
  в skills **не** конвертировать — их будущее в субагентах (отдельный пакет).
  Принцип: «документ — закон, скрипт — движок, skill — руль»; правило тонкого
  адаптера (≤50 строк, без копирования логики) фиксируется в
  `team_workflow/process.md` до первого skill'а. Вход — low-complexity infra
  пакет через `execution_auto`, когда слот WIP свободен.
  Brief: [`next/skills_subagents_workflow_platform.md`](next/skills_subagents_workflow_platform.md).
- Платформенная инициатива (Phase 1 candidate):
  **Local Code Executor via llama.cpp** — первый реальный low-risk пакет после
  smoke должен быть малым tooling/diagnostic change в самом trigger контуре,
  например метрики `context_files_count` и `context_truncated`. До накопления
  успешных прогонов не включать `llamacpp` в orchestrator auto-selection и не
  отдавать ему schema/security/provider/config задачи.
- Если в реестре **нет** пакетов в статусе `ready` / `wip` (слот свободен,
  новых принятых пакетов нет) — следующий шаг задаётся командным workflow: см.
  `doc/team_workflow/generate_plan_next_prompt.md` или
  `doc/team_workflow/product_owner_plan_package_prompt.md` после решения владельца.
- Не поднимать снова E4–E13 в реестр из этого файла без явного остаточного scope.

## Правила возврата (re-entry)

Разрешено:

- регрессия или maintenance-исключение, привязанное к падающему gate;
- остаточный scope, явно зафиксированный в `doc/backlog_registry.yaml`;
- новый gap по CJM/US после решения владельца и с проверяемым DoD;
- **SSR serving promotion**: включение L1 hybrid serving, L4 graph routing
  by-default или L5 online policy — только после прохождения соответствующих
  data/rollout gates (cold-start ≥1000 real samples, eval uplift), не как
  feature re-entry;
- архитектурный / платформенный риск, блокирующий текущую поставку.

Не разрешено:

- переоткрывать закрытую эпоху только ради ещё одной смежной фичи;
- дублировать из `doc/epochs/` таблицы уже закрытых пакетов;
- заводить работу в `ready` / `wip` без владельца, write-set, DoD и exit artifact.

## Что сюда не вкладываем

- детальные Must/Should/Could по уже закрытым горизонтам E4–E13;
- UX-обещания без момента истины в CJM, user story и проверяемого DoD;
- крупные инициативы, которые не снимают текущий блокер;
- исторические таблицы пакетов, уже лежащие в `doc/epochs/`.

## Связанные документы

- [`roadmap.md`](roadmap.md) — сводная таблица волн и ссылок на SSoT (исполнение по `backlog_registry.yaml`).
- [`team_workflow/ssr_ai_vision/ssr_ai_vision_summary.md`](team_workflow/ssr_ai_vision/ssr_ai_vision_summary.md) — статус SSR AI Vision L1–L5 и serving gates.
