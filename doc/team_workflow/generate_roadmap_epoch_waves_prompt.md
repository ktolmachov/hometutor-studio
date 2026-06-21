# generate_roadmap_epoch_waves_prompt

Актуализировано: **2026-05-06**

Промпт для безопасного переноса **уже выбранного стратегического горизонта**
в `doc/backlog_registry.yaml` как waves и package items.

Использовать, когда нужно превратить owner-approved roadmap horizon или
post-ideation artifact в backlog registry SSoT без дублирования уже закрытых
или уже представленных эпох.

> Важно: это **не** первый шаг для новой продуктовой идеи. Для Smart Study Router
> и похожих направлений сначала используйте
> [`generate_breakthrough_ideation_prompt.md`](generate_breakthrough_ideation_prompt.md)
> с конкретным `TARGET` (например `US-20.1`), затем после review/owner decision
> упаковывайте выбранную концепцию через
> [`product_owner_plan_package_prompt.md`](product_owner_plan_package_prompt.md).
> Этот prompt нужен позже, если принято решение оформить результат как
> multi-wave horizon.

## Когда запускать

Запускать **после** breakthrough ideation, если:

- artifact в `archive/ideation/` содержит ≥3 cohesive accepted ideas;
- владелец продукта хочет оформить их как волну/несколько волн, а не один пакет;
- есть понятные `user_stories`, CJM/MoT, DoD и owner decision;
- нужно записать proposed waves/items в `backlog_registry.yaml`.

Не запускать перед ideation, если:

- есть только сырая идея без набора вариантов;
- нужно понять, какие сценарии вообще возможны;
- нет owner decision на multi-wave delivery;
- `future_roadmap.md` не содержит явного нового horizon/detail section.

Для текущего состояния проекта `doc/future_roadmap.md` хранит Closed Horizon Index
и re-entry rules, а не исторический `## Epoch Map`. Поэтому source для новых
идей обычно: `archive/ideation/...` + `doc/roadmap.md` §8 + конкретные US.

---

## Copy-Paste Prompt

```text
Прочитай и выполни задачу в корне проекта.

Goal: аккуратно перенести owner-approved horizon / post-ideation artifact
в `doc/backlog_registry.yaml` как `waves` и связанные `items` packages,
а также синхронизировать нужные связанные индексы/документы так, чтобы SSoT
был консистентен и без дублей.

Inputs:
- SOURCE: `archive/ideation/<artifact>.md` или `doc/future_roadmap.md`
- SOURCE_SECTION: accepted ideas / owner-approved horizon detail
- MIN_WAVES: 1
- OUTPUT_SSOT: `doc/backlog_registry.yaml`
- DERIVED_SYNC: `doc/tasklist.md`
- DATE: `<YYYY-MM-DD>` (set to the current date at execution time)

Hard Project Rules:
- SSoT / derived views / синхронизация / путь Python / PowerShell — см. [`_common_rules.md`](_common_rules.md).
- `doc/backlog_registry.yaml` holds waves/packages; `tasklist.md` — только после lint-sync из канона.
- Do not duplicate closed or already represented waves/packages.
- If an epoch from `future_roadmap.md` is fully closed or already represented
  in `doc/backlog_registry.yaml` / `doc/closed_iterations.md`, do not import it
  again. Either skip it or create a follow-up wave only when there is explicit
  residual scope, tail scope, regression/maintenance exception, or owner
  decision.
- Do not add `user_stories` references to package entries unless the referenced
  `doc/user_stories/us-*.md` file and `doc/user_stories_index.json` entry already
  exist.
- If new user story files are created, update `doc/user_stories_index.json` and
  run the sync command.
Read-Set Budget:
- Read only targeted fragments. Do not full-read large docs without need.
- Allowed read-set:
  1. `archive/ideation/<artifact>.md`: accepted ideas, proposed diffs, epoch proposal only.
     If no artifact exists, STOP and ask for breakthrough ideation first unless the
     owner supplied an explicit horizon detail elsewhere.
  2. `doc/future_roadmap.md`: Current Horizon, Re-entry Rules, and selected
     horizon/detail blocks only.
  3. `doc/backlog_registry.yaml`: grep selected epoch/wave/package ids plus
     targeted existing wave/item sections.
  4. `doc/closed_iterations.md`: grep selected epoch/wave ids only.
  5. `doc/user_stories_index.json`: targeted lookup for candidate US ids.
  6. `doc/cjm.md`: only relevant CJM rows/MoT if creating user stories or
     setting `cjm_moments`.

Phase 1 - Inventory
1. Extract accepted ideas / proposed waves from SOURCE.
2. For each candidate wave/package, classify status:
   - `closed`: explicitly closed in roadmap/current horizon, registry, or
     closed_iterations.
   - `represented`: already has a wave/package in `doc/backlog_registry.yaml`.
   - `candidate`: not represented, or has explicit residual/follow-up scope.
3. Produce an internal inventory table:
   `Candidate | Focus | Entry condition | status | existing registry refs | duplicate risk | candidate note`.

Phase 2 - Weighting
Select highest-weight safe candidates, but do not force duplicates.

Weight formula:
- +5: epoch is not represented in registry as a wave/package.
- +4: explicit owner-approved accepted idea / follow-up scope exists.
- +3: high learner value / CJM impact.
- +3: foundational platform or risk-reduction value.
- +2: clear entry condition.
- +2: can be split into 1-4 small packages.
- -5: fully closed with no residual scope.
- -4: completed wave/package already covers the same scope.
- -3: requires large-scope initiative without owner decision.
- -2: no verifiable DoD.

If no safe candidate remains after dedupe:
- STOP.
- Do not edit registry.
- Report a blocker:
  - which candidates were closed/duplicates;
  - which owner decisions or residual scopes are needed.

Phase 3 - Wave Design
For each selected candidate, create one wave:
- `id`: `wave-<epoch-slug>`
- `theme`: short focus title.
- `north_star`: one measurable outcome.
- `entry_mot`: relevant CJM moment, `"infra"`, or `"platform"`.
- `exit_mot`: relevant CJM moment, `"infra"`, or `"platform"`.
- `packages`: 1-4 package ids.
- `kill_switch`: concrete failure condition.
- `status`: `proposed`, unless an explicit owner decision supports `ready`.
- `created`: `<DATE>`
- `last_touched_mot`: relevant MoT or `null`.

For every package item:
- `id`: `epoch-<clear-slug>`
- `wave_id`
- `wave_position`
- `status`: usually `proposed`
- `cjm_moments`
- `user_stories`: existing US ids only; otherwise `[]` and explain expected US
  in `notes`
- `impact`: one of `loop-improvement`, `loop-blocker`, `infra`, `eval`
- `blocks`: concrete package scope in 1-3 lines
- `depends_on`: only real existing package ids
- `cost_estimate`: `S`, `M`, or `L`
- `write_set_max`: realistic integer
- `dod_commands`: targeted commands only
- `read_set_hint`: 2-5 token-safe paths
- `exit_artifact`
- `re_entry_condition`
- `created`: `<DATE>`
- `last_review`: `<DATE>`
- `notes`: include SOURCE path/section and dedupe rationale. If SOURCE is an
  ideation artifact, include accepted idea IDs.

Phase 4 - Related Docs
Update only what is needed for consistency:
1. `doc/backlog_registry.yaml`: SSoT waves/items.
2. `doc/tasklist.md`: generated only through sync command.
3. If creating new user stories:
   - create `doc/user_stories/us-*.md`;
   - update `doc/user_stories_index.json`;
   - run sync.
4. If roadmap truth changes:
   - add a minimal note to `doc/future_roadmap.md`;
   - do not rewrite historical closed sections.
5. Do not touch product code.

Phase 5 - Validation
Run:

```powershell
.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py
.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict
.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --sync-from-index --write-sync
.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict
```

If user stories were created or edited, also verify generated docs/index drift
according to the repo workflow.

Phase 6 - Final Report
Return a concise report with:
- selected epochs and why they were selected;
- added waves and package ids;
- skipped epochs and why (closed, duplicate, missing owner decision, too large);
- files changed;
- validation command results;
- whether `user_stories` were linked to existing US ids or intentionally left
  empty until product-doc review;
- any residual manual review needed before promoting a wave from `proposed` to
  `ready`.
```

---

## Notes

- This prompt is intentionally conservative. It should prefer no-op/blocker over
  duplicating historical epochs.
- `future_roadmap.md` is strategic context, not the active backlog. The active
  plan must land in `doc/backlog_registry.yaml`.
- Use `proposed` for new waves unless the source includes a clear owner decision.
