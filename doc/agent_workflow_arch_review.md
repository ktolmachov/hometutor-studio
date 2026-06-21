# Workflow Для Агентов — Architecture Review

Часть split-карты [`doc/agent_workflow.md`](agent_workflow.md).
Этот файл содержит: **периодический arch audit — Architecture Review Prompt, token budget note, Phases 1–5, Output format, Appendix**.

Другие части split-карты:
- [`agent_workflow_rules.md`](agent_workflow_rules.md) — Token Budget & Retry Safety
- [`agent_workflow_cycle.md`](agent_workflow_cycle.md) — базовый цикл, параллелизм, A/B/C split
- [`agent_workflow_templates.md`](agent_workflow_templates.md) — planning/verify/contract/task templates
- [`agent_workflow_test_bundles.md`](agent_workflow_test_bundles.md) — test bundles + low-budget fallback

---

## Architecture Review Prompt — Периодический Архитектурный Надзор

Запускать отдельный review-поток после закрытия каждой эпохи, перед планированием следующей, или по запросу owner'а. Агент **не пишет код и не правит файлы** — только находит проблемы, классифицирует их и выдаёт структурированный отчёт.

> **⚠️ Token budget:** полный review (Phase 1–5) запрещён одним вызовом: он превышает hard-limit 20k. Запускать **только отдельными фазами** (один запрос = одна фаза) и перед отправкой явно считать read-set. Рекомендуемые разбивки:
> - `arch-conventions`: Phase 1 — conventions.md × 3 + grep по ключевым правилам → target ≤8k
> - `arch-structure`: Phase 2 — только модули с рисками (>600 строк или >15 импортов), signatures first → target ≤6k
> - `arch-adr`: Phase 3 — ADR status table + architecture module list, не полные файлы → target ≤4k
> - `arch-quality`: Phase 4 — 3-4 модуля с anti-patterns, точечные sections → target ≤5k
> - `arch-deps`: Phase 5 — requirements.txt + grep по импортам → ~3k

### Зачем

Проект растёт итерациями через coding-агентов. Каждый агент видит только свой write-set и не имеет глобальной картины. Без периодического архитектурного аудита накапливаются:
- нарушения архитектурных соглашений;
- мёртвый и дублированный код;
- скрытые связности между модулями;
- drift между документацией и реальным кодом;
- решения, принятые ситуативно, которые стали системными проблемами.

### Какие файлы читать

| Файл / область | Зачем |
|---|---|
| `doc/conventions.md` + `doc/conventions_architecture.md` + `doc/conventions_reference.md` | Актуальные инженерные соглашения — baseline для проверки |
| `doc/architecture.md` | Каноническая архитектура: слои, потоки, зависимости |
| `doc/adr.md` | Журнал решений: что принято, что proposed, обоснования |
| `doc/observability_slo.md` | SLO-контракты и метрики: проверить, что код им соответствует |
| `doc/technical_specification.md` | Entry points, стек, поддерживаемые форматы |
| `doc/backlog_registry.yaml` | Текущий статус: что закрыто, что open, что deferred (SSoT) |
| `doc/tasklist.md` | Производный weekly view; использовать только как sync cross-check |
| `doc/epochs/` | Только header одного целевого epoch-файла (`Get-Content -TotalCount 30` в PowerShell или `head -30` в Git Bash) или grep по секциям; не читать папку и не читать ни один epoch-файл целиком |
| `app/config.py` | Модель настроек: нет ли мёртвых полей, дублирования, drift с `.env.example` |
| `app/api.py` + `app/routers/` | HTTP surface: маршруты, middleware, lifespan |
| `app/models.py` | `QueryContext`, `QueryOptions`, `PipelineOverrides` — ядро контракта pipeline |
| `app/pipeline_runner.py` + `app/pipeline_steps.py` | Оркестрация pipeline: шаги, fallback, trace |
| `app/retrieval.py` + `app/retrieval_strategies.py` | Retrieval execution plan и реестр стратегий |
| `app/query_service.py` — **signatures only**: `rg -n "^class\|^def " app/query_service.py` | Верхнеуровневая оркестрация ответа; full-read запрещён |
| `app/user_state.py` | SQLite persistence: схема, миграции, состояние |
| `app/prompts.py` — **grep, не Read**: `rg -n "^def\|^[A-Z_].*=" app/prompts.py` | Единый источник промптов; full-read запрещён; для поиска hardcoded вне этого файла используйте `rg "prompt" app/ --type py \| Select-String -NotMatch "prompts.py"` |
| `app/knowledge_graph.py` — **signatures only**: `rg -n "^class\|^def " app/knowledge_graph.py` | Graph-контур; full-read запрещён |
| `app/graph_retrieval.py` | Graph retrieval execution |
| `app/tutor_orchestrator.py` — **signatures only** | Tutor orchestration (641 строк; полное = 3k токенов) |
| `app/tutor_prompts.py` | Compatibility bridge/re-export from `app/prompts.py`; verify it does not become a second prompt source |
| `app/learner_model_service.py` — **signatures only** | Learner model (662 строк; полное = 2.9k токенов) |
| `app/learning_plan_service.py` — **signatures only** | Adaptive plan (592 строк; полное = 2.7k токенов) |
| `app/ui/main.py` + ключевые UI-модули | Streamlit surface: навигация, state management |
| `tests/conftest.py` + выборка `tests/test_*.py` | Тестовая инфраструктура: читать только fixtures или 1-2 test cases; не читать большие test files целиком |
| `requirements.txt` | Зависимости: неиспользуемые, конфликтующие, устаревшие |

### Incremental Review Model (обязательно с 2026-04-21)

Review — **инкрементальный**, не полный пересмотр репо. Источник истины: `doc/archive/arch_review_baseline.yaml`.

**Схема baseline:**

```yaml
last_review:
  sha: <git SHA на котором закрыт предыдущий review>
  date: <YYYY-MM-DD>
  report_file: doc/architecture_review_<date>.md
findings:
  - id: AR-2026-04-12-001            # stable id, не меняется между review
    phase: 1                          # 1..5
    severity: critical                # critical | warning | info
    title: "Hardcoded prompt outside app/prompts.py"
    files: ["app/foo.py:142"]
    first_seen: 2026-04-12
    last_seen: 2026-04-21
    status: persists                  # new | persists | resolved | accepted-tech-debt
    owner: <team-role или agent-id>
    target_epoch: E15                  # когда планируется fix; null если accepted
    evidence_cmd: |
      rg "prompt\\s*=" app/foo.py
    expected_evidence: |
      app/foo.py:142:PROMPT = "..."
    regression_guard: "add rule to doc/conventions.md §Prompts + CI check scripts/check_prompt_location.py"
```

**Правила:**
- Первый запуск после внедрения модели создаёт baseline "с нуля" (все findings = `new`).
- Каждый следующий review **обязан** перед сканом прочитать baseline и для каждой existing finding выполнить `evidence_cmd` → если команда не выдаёт match → статус `resolved`. Если выдаёт → `persists` + обновить `last_seen`.
- Новые findings получают новый id (`AR-<YYYY-MM-DD>-NNN`), `status: new`.
- `accepted-tech-debt` findings **не переклассифицируются** в critical без явного решения owner'а — но повторно сообщаются в executive summary с датой принятия.
- Scope фазы = diff против `last_review.sha` + changed modules из `git diff --name-only <sha>..HEAD` + модули из persists-findings этой фазы. Остальное в фазе **не сканируется**.

### Falsifiable Findings (обязательно)

Каждая finding в отчёте обязана содержать **Evidence** — воспроизводимую команду и её expected output.

- Без Evidence finding → severity понижается до `info` автоматически.
- Evidence должна быть one-liner: `rg ...`, `pytest -k ... --collect-only`, `.\.venv\Scripts\python.exe -c "..."`, `(Get-Content <file>).Count`, или pipe из 2–3 команд.
- Expected output — конкретная строка/число, не "see report".
- Owner запускает Evidence независимо и принимает/отклоняет finding по факту, не по тексту.
- "Ощущение связности", "кажется избыточным", "возможно не используется" без Evidence **не допускаются**.

Пример:

```
Finding: dead config field `settings.graph_debug_probe`
Evidence: rg "graph_debug_probe" app/ tests/ scripts/ | rg -v "config.py"
Expected: no matches
```

### Шаблон architecture review prompt

🚨 **CRITICAL TOKEN WARNING:** Full architecture review (Phase 1–5) exceeds the **20k hard-limit** and is forbidden as one LLM call. Запускайте **только по фазам** (один запрос = одна фаза). Используйте `rg`/sections вместо full-file для больших модулей. См. [doc/token_safety.md](token_safety.md#таблица-безопасного-включения-критические-файлы).

```text
# [two-root] Two-repo project: resolve app/** and requirements.txt against CODE_ROOT
# (editable install of `hometutor`: `pip show hometutor` -> "Editable project location");
# resolve doc/**, tests/**, scripts/** against the current cwd (DOCS_ROOT).
# Run git per-root: `git -C <CODE_ROOT> ...` for app code, `git -C <cwd> ...` for docs/tests.
Goal: periodic INCREMENTAL architecture review — find defects, violations, and decay
introduced since last review. Do NOT write code. Do NOT edit any files.
Output = structured report only.

## MANDATORY PRE-SCAN (runs before any phase work)

1. Read doc/archive/arch_review_baseline.yaml — extract last_review.sha and findings list.
   If file is absent: this is the first incremental run; state that in the report
   and scan full scope for this phase only (baseline will be created from output).
2. Compute incremental scope:
   - git diff --name-only <last_review.sha>..HEAD  → list of changed files
   - union with files from baseline findings whose phase matches current phase
     AND status in {new, persists}
   - this is the ONLY code scope allowed for the phase. Unchanged+unreferenced
     modules are out of scope.
3. For every baseline finding in this phase: run its evidence_cmd.
   - No match → mark resolved (report in output, do not re-analyze).
   - Match → mark persists, update last_seen, keep in output.
4. If estimated read-set after incremental scoping still exceeds 12k tokens,
   compress further (signatures-only) before starting the phase.

## FALSIFIABILITY RULE

Every new finding must include an Evidence command (one-liner rg/pytest/python)
and its expected output. Findings without reproducible evidence are auto-downgraded
to severity=info and excluded from the fix-prompt. No subjective claims
("feels coupled", "probably unused") accepted at warning/critical severity.

## IMPORTANT: TOKEN BUDGET FOR LARGE FILES

Before reading any file >600 lines, check doc/token_safety.md for safe method:
- app/query_service.py (~900+ lines) → rg "^class\|^def " only, don't read full body
- app/prompts.py (1194 lines, ~18k est tokens) → rg "^def\|^[A-Z_].*=" only
- app/knowledge_graph.py (1258 lines, ~13k est tokens) → rg "^class\|^def " only
- doc/adr.md (~660+ lines, ~13k est tokens) → read ONLY the status table or one ADR
- doc/architecture.md (383 lines) → read ONLY the module list, skip detail sections

If you are reading a file and it exceeds 1k tokens, STOP and use grep instead.
Owner files are write-scope, not read-scope. Do not read owner files fully unless they are listed under Read ONLY.

## Phase 1 — Conventions Compliance Audit

Read these files as the authoritative baseline:
- doc/conventions.md (~710 tokens, safe to read fully)
- doc/conventions_architecture.md (~3k tokens, safe to read fully)
- doc/conventions_reference.md (~1.9k tokens, safe to read fully)

Then scan the codebase for violations of each stated convention.
DO NOT read app/query_service.py, app/prompts.py, app/knowledge_graph.py fully — use rg/signatures as noted above.

Check specifically (use grep for large files to save tokens):
1. Config access: any module reading settings NOT through get_settings() /
   get_retrieval_settings() (except config.py itself and tests).
2. LLM/embed access: any module creating LLM or embed clients NOT through
   app/provider.py.
3. Prompt location: use `rg "prompt = |PROMPT = |prompt\s*=" app/ --type py | Select-String -NotMatch "prompts.py"`
   to find hardcoded prompts outside app/prompts.py.
4. Pipeline contract: any step NOT following process(QueryContext) -> QueryContext.
5. Router structure: any HTTP handler NOT in app/routers/; any endpoint not
   registered through include_router in app/api.py.
6. Knowledge encapsulation: any UI or API module duplicating business logic
   that should live in knowledge_service.py, quiz_service.py, flashcard_service.py,
   or learning_plan_service.py.
7. Import hygiene: any circular imports; any module importing from UI layer
   into backend layer; any test importing production secrets or live state.
8. Error handling: any pipeline stage without graceful degradation (except
   generate, which is the only stage without fallback by convention).
9. Path safety: any file access to data/ NOT going through safe path validation.
10. Guardrails: any entry point (API, CLI, Telegram) bypassing
    app/guardrails.py or app/input_validation.py.

For each violation found:
- File path and line number
- Which convention is violated (quote the rule)
- Severity: critical / warning / info
- Suggested fix (1-2 sentences, no code)

## ⚠️ Token Budget Note for Large Modules

To stay within the 12k target / 20k hard-limit, do NOT read these files in full. Instead use rg/signatures/sections:

| Module / doc | Read method | Why |
|---|---|---|
| `app/prompts.py` (1194, ~18k est tokens) | `rg "^def\|^[A-Z_].*=" app/prompts.py` + one section | full-read alone can exceed target budget |
| `doc/changelog.md` (~15k est tokens) | last 2-3 entries or append target only | history docs accumulate quickly |
| `tests/test_api.py` (1614, ~14k est tokens) | `rg "def test_<pattern>" tests/test_api.py` + one test case | full tests can exceed target budget |
| `doc/adr.md` (~660+, ~13k est tokens) | status table or one ADR only | full decision history is not phase input |
| `app/knowledge_graph.py` (1258, ~13k est tokens) | `rg "^class\|^def " app/knowledge_graph.py` | full-read is forbidden |
| `tests/test_query_service.py` (1012, ~10k est tokens) | 1-2 relevant tests or fixtures | avoid full test file |
| `app/query_service.py` (~900+, ~8k est tokens) | `rg "^class\|^def " app/query_service.py` + exact function | large orchestrator |
| `doc/architecture.md` (383, ~5k est tokens) | module list or one section only | avoid coupling with ADR full-read |

> ⚠️ Цифры указаны на 2026-04-21. Перед review проверить актуальный размер через `(Get-Content <file>).Count` в PowerShell (или `wc -l <file>` в Git Bash) — статические значения могут устареть между эпохами.

## Phase 2 — Structural Health

Analyze the codebase for structural problems (using grep where specified above):

2.1 Dead code:
- Functions/classes/constants that are defined but never imported or called
- Config fields in Settings/RetrievalSettings with no consumer in app/
- Routers registered in api.py with endpoints that have no UI or test consumer
- Test files that test modules which no longer exist

2.2 Duplication:
- Identical or near-identical logic in different modules (>10 lines)
- Multiple modules implementing the same concept independently
  (e.g., SM-2 in different places, date formatting helpers, retry loops)
- Copy-pasted SQL schemas or queries across modules

2.3 Coupling and dependency direction:
- Backend modules (app/*.py) importing from UI layer (app/ui/*.py)
- Service modules importing from routers
- Circular dependency chains (A imports B imports C imports A)
- God modules with >15 imports from app/ (excessive fan-in or fan-out)
- Shared mutable state outside designated stores (user_state, session_store,
  metrics)

2.4 Module size and responsibility:
- Any single file >600 lines (candidate for split)
- Any function >80 lines (candidate for extraction)
- Modules with mixed responsibilities (e.g., a service that also does HTTP
  serialization, or a UI module that contains business logic)

2.5 Test health:
- Test files with no assertions (smoke-only without checking anything)
- Tests that patch >5 different targets (sign of excessive coupling)
- Missing test coverage for critical paths: pipeline_runner, query_service,
  tutor_orchestrator, user_state migrations, guardrails
- Broken or skipped tests (pytest.mark.skip without explanation)

## Phase 3 — Architecture Decision Audit

Read ONLY the ADR status table / one relevant ADR and the architecture module list / one relevant section. Do not read `doc/adr.md` or `doc/architecture.md` fully in this phase.

3.1 ADR drift:
- For each ADR with status "Accepted": verify the code still follows
  the stated decision. Flag any module that contradicts an accepted ADR.
- For each ADR with status "Proposed": check if it was silently implemented
  without updating the status to Accepted.
- Missing ADRs: identify any significant architectural choice in the code
  that has no corresponding ADR entry (e.g., choice of SQLite for state,
  choice of aiogram for Telegram, session storage strategy, graph storage
  format).

3.2 Documentation-code drift:
- doc/architecture.md: verify that every module listed still exists, and
  every significant module in app/ is listed. Flag missing or renamed.
- doc/api_reference.md: sample 5-10 endpoints and verify they match the
  actual routes in app/routers/.
- doc/observability_slo.md: verify SLO parameters listed match the code
  in app/config.py and app/metrics.py.
- doc/technical_specification.md: verify entry points, stack, formats
  match reality.

3.3 Implicit decisions (no-ADR patterns):
- Identify patterns that appear in 3+ modules without documented
  rationale (e.g., specific error handling strategy, specific serialization
  format, specific caching approach).
- These are implicit architecture decisions. Flag each one and suggest
  whether it needs an ADR.

## Phase 4 — Implementation Quality

4.1 Anti-patterns:
- Catch-all except blocks (bare except: or except Exception without
  re-raise or specific handling)
- Silent failures: errors caught and logged but not propagated to caller
  when the caller needs to know
- N+1 patterns: loops making individual DB queries or LLM calls where
  batch would work
- Synchronous blocking in async context (or vice versa)
- Hardcoded magic numbers without named constants
- Environment-dependent behavior without clear documentation
  (code that behaves differently based on undocumented env vars)

4.2 Security surface:
- SQL injection vectors: any raw string interpolation in SQL queries
  in user_state.py or other SQLite consumers
- Path traversal: any file operation on user-provided paths without
  validation
- Prompt injection: any user input reaching LLM prompts without going
  through guardrails.py
- Sensitive data in logs: any logging of full API keys, user content
  at DEBUG level that could leak, session tokens
- CORS configuration: verify CORS in api.py is appropriate for
  a local-only service

4.3 Resilience:
- LLM call sites without timeout or retry
- External service calls (Chroma, file system) without error handling
- Missing graceful degradation for optional features (graph, telegram,
  OTEL) when their dependencies are unavailable

## Phase 5 — Dependency and Ecosystem Health

5.1 requirements.txt audit:
- Packages imported in code but missing from requirements.txt
- Packages in requirements.txt but never imported in app/ or tests/
- Known incompatible version combinations (if detectable from pinned
  versions)
- Packages with known security advisories (flag for manual check)

5.2 Internal dependency map:
- Which app/ modules have the most dependents (highest fan-in)?
- Which app/ modules import the most other app/ modules (highest fan-out)?
- Are there clear layer boundaries (entrypoints → services → core)?
- Flag any violation of the expected dependency direction.

## Output format

### Executive Summary (3-5 sentences)
Overall health assessment. Top 3 most impactful findings.

### Findings Table

| # | ID | Phase | Severity | Status | Finding | File(s) | Evidence (cmd → expected) | Suggested Action |
|---|----|-------|----------|--------|---------|---------|---------------------------|------------------|
| 1 | AR-2026-04-21-001 | 1 | critical | new | ... | app/foo.py:42 | `rg "..." app/foo.py` → `match on L42` | ... |
| 2 | AR-2026-04-12-005 | 2 | warning  | persists (since 2026-04-12) | ... | app/bar.py | `pytest -k test_bar_contract --collect-only` → `0 tests` | ... |
| 3 | AR-2026-04-12-003 | 1 | —        | resolved | ... | app/baz.py | `rg "..." app/baz.py` → `no matches` | — |

Status values: `new` | `persists` | `resolved` | `accepted-tech-debt`.
Findings без Evidence (пустая колонка или "see report") — автоматически severity=info, не включаются в fix-prompt.

### Baseline Update

В конце отчёта — готовый патч для `doc/archive/arch_review_baseline.yaml`:
- обновить `last_review.sha` / `date` / `report_file`;
- добавить все `new` findings с полными полями (id, phase, severity, files, first_seen, last_seen, status, evidence_cmd, expected_evidence, regression_guard, owner=null, target_epoch=null);
- для `persists` — обновить `last_seen`;
- для `resolved` — status=resolved, добавить `resolved_date`;
- `accepted-tech-debt` findings не трогать автоматически.

Severity scale:
- critical: active bug risk, security issue, or convention violation
  that will cause problems in the next epoch
- warning: technical debt or drift that should be addressed within
  1-2 epochs
- info: observation, minor improvement, or documentation gap

### Metrics Snapshot

- Total app/ modules: N
- Total test files: N
- Modules >600 lines: list
- Functions >80 lines: list (sample up to 10)
- Convention violations found: N (critical/warning/info breakdown)
- ADR drift instances: N
- Doc-code drift instances: N
- Dead code candidates: N
- Duplication clusters: N

### Recommended Actions (prioritized)

Top 5-10 actions, ordered by impact. For each:
- What to do (1-2 sentences)
- Why it matters now
- Estimated scope: S (1 file) / M (2-5 files) / L (6+ files)
- Suggested epoch-package name if the fix needs its own slice

### Fix Prompts (ОБЯЗАТЕЛЬНО — один prompt на каждую выполненную фазу)

Для каждой выполненной фазы выдать готовый copy-paste execution prompt,
который можно запустить в отдельной fresh-context сессии для устранения
найденных critical+warning замечаний. Info-находки включать в "optional
follow-up" отдельным списком, не в DoD.

Требования:
- Один prompt = одна фаза. Не смешивать findings из разных фаз в один fix.
- Write-set ≤ 5 файлов. Если правок больше — split на A/B/C с порядком merge.
- DoD — конкретная pytest/rg команда на каждую finding с expected result
  (обычно = `evidence_cmd` finding'а с expected output "no match"/"pass").
- Do not touch — зоны других фаз, чтобы fix не расползался.
- Token header:
  `Token budget:`
  `- Target <=12k input tokens.`
  `- Hard stop >20k input tokens.`
  `- If estimated input is 12k-20k, compress before sending.`
  `- No retry with unchanged payload.`
- Первая строка: `Ignore prior responses/tools. Fresh context only.`
- Не вставлять тело отчёта в fix-prompt — только ссылку на report file
  и перечень findings по ID из baseline.
- **Regression Guard (обязательно на каждый critical+warning finding).** В fix-prompt
  указать как предотвратить повторное появление. Минимум один из:
  - новое правило в `doc/conventions.md` / `conventions_architecture.md` со ссылкой на ID finding;
  - pre-commit hook или CI check (скрипт в `scripts/check_*.py`), запускаемый в `scripts/run_checks.sh`;
  - инвариант-тест в `tests/test_*_invariants.py` (падает при возврате проблемы);
  - добавление `evidence_cmd` в `scripts/arch_regression_guards.py` (Windows-first агрегатор для pre-merge).
  Fix-prompt без Regression Guard на critical/warning → **не принимается verify**.

Шаблон fix-prompt (для каждой фазы):

```text
Goal: fix Phase <N> findings from <arch-review-report-file>.
Ignore prior responses/tools. Fresh context only.

Baseline: doc/archive/arch_review_baseline.yaml
Report:   <arch-review-report-file>

Findings to fix (critical + warning from Phase <N>, by baseline ID):
- <AR-YYYY-MM-DD-NNN>: <one-line finding> (file:line)
- <AR-YYYY-MM-DD-NNN>: <one-line finding> (file:line)

Write-set (≤ 5 files):
- <file1>
- <file2>

Read ONLY:
- <file> — signatures only if >600 строк
- <related test file> — 1 test case only

Do not touch:
- модули из других фаз arch-review
- <другие зоны>

DoD (one per finding — обычно = evidence_cmd finding'а):
- <AR-...>: <rg/pytest команда> → <expected: no match / pass>

Regression Guard (обязательно, один или несколько на каждый finding):
- <AR-...>: new rule in doc/conventions.md §<section> + CI check scripts/check_<name>.py
- <AR-...>: invariant test tests/test_<module>_invariants.py::test_<name>
- <AR-...>: add evidence_cmd to scripts/arch_regression_guards.py

Post-fix baseline update:
- Mark fixed findings as status=resolved in doc/archive/arch_review_baseline.yaml
  with resolved_date=<today>. Do NOT remove entries — keep history.

Token budget:
- Target <=12k input tokens.
- Hard stop >20k input tokens.
- If estimated input is 12k-20k, compress before sending.
- No retry with unchanged payload.
Output: changed files + tests run + guard(s) added + unresolved risk.

Optional follow-up (info-level, not in DoD):
- <AR-...>: <finding>
```

Если в фазе нет critical/warning — явно написать:
`No fix-prompt required for Phase <N> (no actionable findings above info level).`

### Appendix: Positive Patterns

List 3-5 things the codebase does well that should be preserved and
replicated. This prevents future agents from "improving" what already
works.

Rules:
- Do NOT write code. Do NOT edit any files. Output = report only.
- Do NOT propose wholesale rewrites or migrations. Prefer targeted fixes.
- Do NOT flag style issues (formatting, naming preferences) unless they
  violate a stated convention in doc/conventions.md.
- Focus on problems that will compound if left unaddressed.
- Finding history precedence:
  1) `doc/archive/arch_review_baseline.yaml` — source of truth for status/history.
  2) `last_review.report_file` from baseline — reference report for previous cycle.
  3) `archive/architecture_review*.md` — historical context only, not a status source.
- If a finding appears in legacy `archive/architecture_review.md` as "resolved",
  verify status only via baseline evidence before any reclassification.
- Use exact file paths and line numbers wherever possible.
- If the review scope is too large for one pass, state which phases
  you completed and which need a follow-up.
```

### Принципы

- **Review ≠ rewrite** — агент находит проблемы, но не правит код и не реструктурирует модули.
- **Conventions как baseline** — каждое замечание привязано к конкретному правилу из `doc/conventions*.md` или к общепринятой практике с обоснованием.
- **Severity обязательна** — без классификации по severity отчёт превращается в wish-list.
- **Positive patterns** — обязательная секция, чтобы зафиксировать работающие решения и не дать следующим агентам их сломать.
- **Инкрементальность через baseline** — `doc/archive/arch_review_baseline.yaml` — source of truth для findings-истории. Scope каждого review = git diff + persists-findings, не полный репо.
- **Falsifiability** — каждое замечание имеет воспроизводимую команду и expected output; без этого severity=info.
- **Regression guard** — fix не считается завершённым без правила/теста/скрипта, который не даст проблеме вернуться.
- **Scope control** — если проект вырос настолько, что полный review не влезает в один проход, разбить на 2-3 прохода по фазам и явно указать, что осталось.

### Первый запуск после внедрения модели (2026-04-21)

1. `doc/archive/arch_review_baseline.yaml` отсутствует → создать с пустым `findings: []` и `last_review.sha: <HEAD на момент старта>`.
2. Прогнать Phase 1 в полном scope (diff ещё невозможен) — собрать findings с Evidence.
3. Записать все findings в baseline как `status: new`, `first_seen=last_seen=<today>`.
4. Для каждого critical/warning назначить `owner` и `target_epoch` при планировании следующего slice.
5. Следующий review уже работает инкрементально.

Аналогично для фаз 2–5 по отдельности.

### Когда запускать

| Триггер | Что запускать |
|---|---|
| Закрытие эпохи (E12, E13 и т.д.) | Полный review (Phase 1-5) |
| Перед планированием следующей эпохи | Phase 1 + Phase 3.2 (conventions + doc drift) |
| После крупного merge (>10 файлов) | Phase 2.3 + Phase 4.1 (coupling + anti-patterns) по затронутым модулям |
| По запросу owner'а | Любой subset фаз |

### Куда сохранять результат

Актуальный отчёт сохраняется как `doc/architecture_review_<date>.md` (например `doc/architecture_review_2026-04-12.md`). При следующем review текущий отчёт перемещается в `archive/` с датой в названии (`archive/architecture_review_<old-date>.md`). Актуальный отчёт — всегда один файл в `doc/`, не массив.

Legacy: файл `archive/architecture_review.md` (без даты в названии) — от предыдущих review до введения конвенции датирования. На него ссылаются правила сверки «resolved»-находок (см. Rules в шаблоне выше); при следующем цикле он будет переименован в формат с датой.
