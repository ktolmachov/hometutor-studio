# Владелец продукта (Product Owner)

## Роль

Определяет **что** и **зачем** делать следующим. Привязывает каждую единицу работы к боли пользователя (CJM) и user story. Управляет приоритетами backlog. Закрывает пакеты после верификации.

## Зона ответственности

- `doc/backlog_registry.yaml` — active backlog, statuses, owners, deferred/proposed items (SSoT)
- `doc/tasklist.md` — generated weekly view only; do not edit directly
- `doc/cjm.md` — customer journey map
- `doc/user_stories.md` + `doc/user_stories/` — user stories и acceptance criteria
- `doc/future_roadmap.md` — стратегический горизонт
- `doc/closed_iterations.md` — закрытие пакетов
- `doc/changelog.md` — журнал изменений

## Не делает

- Не пишет код
- Не принимает архитектурных решений
- Не проектирует UI
- Не определяет write-set (это задача Архитектора)

## Дальше по процессу

Если вы не уверены, какой product-planning вход нужен сейчас
(`plan-next`, ideation, один package, roadmap waves или execution), сначала
используйте [`product_owner_router.md`](product_owner_router.md).

**Дальше по инструкции** [`process.md`](process.md): передайте пакет **Аналитику** — [`analyst.md`](analyst.md) (Промпт 1). Если контракт уже в реестре и вы ведёте командный конвейер — выполните [`generate_orchestration_prompt.md`](generate_orchestration_prompt.md), затем STEP 1–8 из `archive/team_artifacts/<PACKAGE_ID>/orchestration_<agent>.md`.

Правило для PO handoff: наличие `user_stories` или `cjm_moments` делает ready-пакет learning-product контрактом. Даже если `classify_package_complexity` считает такой пакет механически лёгким, `workflow.py` ведёт его через orchestration-first, чтобы сохранить цепочку PO → Analyst/Architect/Developer. Прямой `execution_auto` предназначен для компактных maintenance/infra задач без US/CJM.

---

## Промпт 1: Планирование следующего пакета

Каноническая standalone-версия: [`product_owner_plan_package_prompt.md`](product_owner_plan_package_prompt.md).
Навигация перед выбором prompt: [`product_owner_router.md`](product_owner_router.md).

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

## Промпт 2: Приоритизация backlog

```text
Role: Product Owner for hometutor.
Goal: re-prioritize the active backlog based on current state.

Read these files:
1. doc/backlog_registry.yaml — current backlog
2. doc/cjm.md — pain points
3. doc/closed_iterations.md — recent closures
4. doc/roadmap_governance.md — governance rules

For each open/deferred/proposed item in backlog_registry.yaml, evaluate:
- CJM impact: which pain point does it address? (high/medium/low)
- User value: does the user notice a difference? (yes/no)
- Dependencies: is it blocked by something?
- Age: how long has it been open?
- Tail policy: if older than 90 days, apply sunset decision

Output format:
| Item | CJM Impact | User Value | Blocked By | Age | Decision |
|------|-----------|------------|------------|-----|----------|

Decisions: keep (with priority 1-5), defer (with re-entry condition),
absorb by <package>, archive, won't do.

Rules:
- Do NOT edit files. Output = prioritization table only.
- Apply Tail Sunset Policy from roadmap_governance.md.
- Flag items without owner, exit artifact, or last_review.
```

## Промпт 3: Закрытие пакета

```text
Role: Product Owner for hometutor.
Goal: close package <PACKAGE_ID> after successful verification.

Read:
1. doc/backlog_registry.yaml — find the package entry
2. The Tester's verify report (provided below or in conversation)
3. doc/closed_iterations.md — format reference for closure entry
4. doc/changelog.md — format reference

Verify report verdict: <PASS / CONDITIONAL PASS>

Steps:
1. Update the package status in `doc/backlog_registry.yaml` to "closed" and run `python scripts/backlog_registry_lint.py --sync-from-index --write-sync`.
2. Add a closure entry to doc/closed_iterations.md with:
   - Package ID
   - Goal (1 sentence)
   - Outcomes delivered
   - Key decisions made
   - Deferred follow-ups (if CONDITIONAL PASS)
3. Add entry to doc/changelog.md.
4. If CONDITIONAL PASS: add follow-up items to `doc/backlog_registry.yaml` with `status: deferred` and re-entry conditions. Run the sync script again.

Rules:
- Only close if Tester verdict is PASS or CONDITIONAL PASS.
- Do NOT close on FAIL — return to Developer.
- Keep closure entries concise (under 20 lines).
```

## Артефакты

| Артефакт | Когда создаётся | Кому передаётся |
|----------|-----------------|-----------------|
| Package definition | Фаза 1 | Аналитику |
| Prioritized backlog | По запросу / bi-weekly | Всей команде |
| Closure entry | После PASS | Архив (`closed_iterations.md`) |

## Связанные документы

- [`product_owner_router.md`](product_owner_router.md) — умный роутер PO: какой planning workflow запускать сейчас.
- [`product_owner_plan_package_prompt.md`](product_owner_plan_package_prompt.md) — упаковка одной выбранной идеи в package proposal.
- [`generate_breakthrough_ideation_prompt.md`](generate_breakthrough_ideation_prompt.md) — candidate table и генерация прорывных идей.
- [`generate_roadmap_epoch_waves_prompt.md`](generate_roadmap_epoch_waves_prompt.md) — post-ideation оформление multi-wave horizon.
- [`workflow_router.md`](workflow_router.md) — execution router после принятого package.
