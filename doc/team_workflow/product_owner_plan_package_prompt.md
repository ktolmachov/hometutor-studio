# Product Owner — Планирование пакета

Актуализировано: **2026-05-02**

Канонический standalone-промпт для роли Product Owner, когда нужно
сформировать следующий delivery package на уровне бизнес-ценности, CJM и user
stories. Используйте его для ручного стратегического планирования пакета или
как fallback после `generate_plan_next_prompt.md`, если автоматический plan-next
не нашел eligible candidate по текущим registry / re-entry rules.

```text
Role: Product Owner for hometutor learning assistant.
Goal: define the next delivery package.

Read these files (do not edit yet):
1. doc/backlog_registry.yaml — current active backlog, open/deferred/proposed items
2. doc/cjm.md — customer journey map, pain points by stage
3. doc/future_roadmap.md — strategic horizon (E15+)
4. doc/closed_iterations.md — last 2-3 closed epochs (patterns, size)
5. doc/user_stories.md — index of user stories
6. doc/vision.md — product boundaries and value proposition

Analysis steps:
1. Identify the top CJM pain point that is NOT yet addressed by closed epochs.
2. Find user stories (US-*) that map to this pain point.
3. Check if any deferred items in backlog_registry.yaml should be absorbed.
4. Verify that the proposed work fits within WIP=1 and max 5 outcomes.

Output format:
## Proposed Package: <epoch-package-id>

### CJM Stage
<Which CJM stage and pain point this addresses>

### Goal
<1-2 sentences: what the user gains>

### Outcomes (max 5)
For each outcome:
- Outcome: <what changes for the user>
- User Story: <US-X.Y reference>
- Acceptance Criteria (high-level): <1-3 bullet points>
- CJM Stage: <stage name>

### Dependencies
<What must be true before this package starts>

### Risks
<What might block or change scope>

### Deferred items absorbed
<Items from backlog_registry.yaml with status deferred that this package closes, if any>

Rules:
- Do NOT write code or propose technical solutions.
- Do NOT exceed 5 outcomes per package.
- Every outcome MUST map to a CJM stage and user story.
- If a user story lacks acceptance criteria, flag it for the Analyst.
- Prefer closing existing pain points over opening new horizons.
- Token budget: <= 20k input tokens per call; read only the target registry entry + one US file; no retry with unchanged payload.
```

## Когда использовать

- Ручное планирование одного следующего пакета, когда нужен Product Owner
  judgement, а не автоматическая запись в `backlog_registry.yaml`.
- Fallback после `generate_plan_next_prompt.md`, если агент остановился с
  `blocker: no eligible plan-next candidate under current registry/re-entry rules`.
- Упаковка идеи из ideation / roadmap review в понятный package proposal перед
  передачей Аналитику.

Если вы не уверены, нужен ли сейчас ideation, один package, roadmap waves или
execution, сначала откройте [`product_owner_router.md`](product_owner_router.md).

## Связанные промпты (идея → таблица → упаковка)

- **Product Owner Router** — [`product_owner_router.md`](./product_owner_router.md): единая точка входа для выбора правильного product-planning шага.
- **`generate_plan_next`** — [`generate_plan_next_prompt.md`](./generate_plan_next_prompt.md): автоматический выбор следующего пакета; если остановился на `blocker: no eligible…`, возвращаетесь к ручному PO-промпту *или* к ideation ниже.
- **Таблица направлений без генерации N идей** — [`generate_breakthrough_ideation_prompt.md`](./generate_breakthrough_ideation_prompt.md), режим **`MODE=CANDIDATE_TABLE`** (§ «Как использовать» в том файле): одна таблица CJM / US / pain / feature area по `cjm.md`, `user_stories.md`, `future_roadmap.md` (+ при необходимости `grep` по реестру) — чтобы выбрать будущий `TARGET`.
- **Прорывные идеи по выбранному направлению** — тот же [`generate_breakthrough_ideation_prompt.md`](./generate_breakthrough_ideation_prompt.md) в основном режиме (`TARGET` + `N_IDEAS`, артефакт в `archive/ideation/…`).
- После фильтра идей — снова **этот файл** для финального текста одного package proposal; затем правка [`backlog_registry.yaml`](../backlog_registry.yaml) и **sync после YAML** по [`doc/team_workflow/_common_rules.md`](_common_rules.md) (раздел Sync).

Навигация для роли PO целиком: [`doc/prompts_usage_guide.md`](../prompts_usage_guide.md) § Product Owner.

## Когда не использовать

- Если в `doc/backlog_registry.yaml` уже есть `ready` или `wip` пакет:
  запусти `python scripts/workflow.py` — он сам выберет следующий шаг (или вручную: `generate_orchestration_prompt.md`).
- Если работа по `PACKAGE_ID` уже начиналась:
  используйте `generate_resume_prompt.md`.
- Если нужно автоматически записать контракт в registry и пересобрать
  `tasklist.md`: сначала используйте `generate_plan_next_prompt.md`.
