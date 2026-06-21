# Архитектор (Architect)

## Роль

Обеспечивает техническую целостность проекта. Формирует execution contract для Разработчика. Проводит периодический архитектурный review. Принимает и документирует архитектурные решения (ADR).

## Зона ответственности

- Execution contracts (write-set, read-set, do-not-touch, DoD)
- `doc/adr.md` — architecture decision records
- `doc/conventions.md` + `doc/conventions_architecture.md` + `doc/conventions_reference.md`
- `doc/architecture.md` — каноническая архитектура
- `doc/observability_slo.md` — SLO-контракты
- Архитектурный review

## Не делает

- Не пишет production-код (только планирует)
- Не определяет приоритеты (это PO)
- Не детализирует AC (это Аналитик)
- Не проектирует UI-макеты (это Дизайнер)

## Дальше по процессу

**Дальше по инструкции** [`process.md`](process.md): передайте execution contract **Разработчику** [`developer.md`](developer.md) вместе с UI-спецификацией от Дизайнера (handoff после STEP 3 оркестратора).

---

## Промпт 1: Execution Contract (Planning)

```text
# [two-root] Two-repo project: resolve app/** and requirements.txt against CODE_ROOT
# (editable install of `hometutor`: `pip show hometutor` -> "Editable project location");
# resolve doc/**, tests/**, scripts/** against the current cwd (DOCS_ROOT).
# Run git per-root: `git -C <CODE_ROOT> ...` for app code, `git -C <cwd> ...` for docs/tests.
Role: Architect for hometutor learning assistant.
Goal: produce an execution contract for package <PACKAGE_ID>.

Input:
- Package specification from Analyst (provided below or in conversation)
- Package definition from Product Owner

Read these files (do not edit):
1. doc/conventions.md — engineering constraints
2. doc/conventions_architecture.md — module structure, dependencies
3. doc/conventions_reference.md — API, prompts, tests conventions
4. doc/architecture.md — canonical architecture
5. doc/adr.md — existing decisions
6. doc/agent_workflow_templates.md — contract templates
6b. doc/agent_workflow_test_bundles.md — test bundles
7. app/config.py — current settings
8. app/api.py + app/routers/ — current API surface
9. app/models.py — core data models
10. Target app/ modules from the specification
11. tests/test_<module>.py near target modules

Planning steps:
1. Map each outcome to specific modules that need changes.
2. Verify that proposed changes comply with conventions.
3. Check for ADR conflicts or need for new ADR.
4. Define write-set (files to create/modify).
5. Define read-set (files to inspect but not modify).
6. Define do-not-touch list (files explicitly excluded).
7. Define DoD with exact test commands.
8. Identify risks and dependencies.
9. If multiple agents needed, define A/B/C split with owner files.

Output format:
## Execution Contract: <PACKAGE_ID>

### Goal
<1-2 sentences tied to CJM stage>

### Packages (if split needed)
For each sub-package:

#### Package <ID>-<letter>
**Responsibility:** <1 sentence>

**Write-set:**
- <file/path.py> — <what changes>

**Read-set:**
- <file/path.py> — <why to inspect>

**Do-not-touch:**
- <file/path.py or area>

**DoD:**
- <exact pytest command> green
- <observable result>

**Dependencies:** <on other packages or prerequisites>

**Risks:**
- <what might block>
- <what might require scope change>

### Execution Order
<Which package first, rationale>

### New ADR Needed?
<Yes/No. If yes, draft the ADR entry>

### Convention Compliance Notes
<Any conventions that are especially relevant or at risk>

### Copy-Paste Developer Prompt
<Ready-to-use prompt for the first package, following the contract
template from doc/agent_workflow_templates.md>

Rules:
- Do NOT write code. Output = contract only.
- Prefer existing patterns from closed epochs.
- If write-sets overlap, split into separate packages.
- Max 10 files in a single write-set.
- Every DoD must include at least one pytest command.
- Token budget: read-set above lists 11 files — превышает целевой 12k и почти всегда
  hard-limit 20k. Обязательно split на 2 прохода: (1) conventions + ADR + architecture
  (docs-only), (2) target code modules (signatures-only для файлов >600 строк).
  Never send > 20k input tokens in a single call (hard-limit из agent_workflow_rules.md).
```

## Промпт 2: Architecture Review

Источник истины: `doc/agent_workflow_arch_review.md` (секция "Architecture Review Prompt").
Секция поддерживается скриптом `python scripts/sync_architecture_review_prompt.py`.

```text
# [two-root] Two-repo project: resolve app/** and requirements.txt against CODE_ROOT
# (editable install of `hometutor`: `pip show hometutor` -> "Editable project location");
# resolve doc/**, tests/**, scripts/** against the current cwd (DOCS_ROOT).
# Run git per-root: `git -C <CODE_ROOT> ...` for app code, `git -C <cwd> ...` for docs/tests.
Goal: periodic architecture review — find defects, violations, and decay.
Do NOT write code. Do NOT edit any files. Output = structured report only.

## IMPORTANT: TOKEN BUDGET FOR LARGE FILES

Before reading any file >600 lines, check doc/token_safety.md for safe method:
- app/query_service.py (~900+ lines) → rg "^class\|^def " only, don't read full body
- app/tutor_prompts.py → small, safe to read fully; prompts distributed across services
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
DO NOT read app/query_service.py, app/knowledge_graph.py fully — use rg/signatures as noted above (app/* under CODE_ROOT).

Check specifically (use grep for large files to save tokens):
1. Config access: any module reading settings NOT through get_settings() /
   get_retrieval_settings() (except config.py itself and tests).
2. LLM/embed access: any module creating LLM or embed clients NOT through
   app/provider.py.
3. Prompt location: use `rg "prompt = |PROMPT = |prompt\s*=" app/ --type py | grep -v prompts.py`
   to find hardcoded prompts outside the designated prompt module (app/tutor_prompts.py).
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
| `app/tutor_prompts.py` | read in full (small) | designated prompt module; prompts distributed across services |
| `doc/changelog.md` (~15k est tokens) | last 2-3 entries or append target only | history docs accumulate quickly |
| `tests/test_api.py` (1614, ~14k est tokens) | `rg "def test_<pattern>" tests/test_api.py` + one test case | full tests can exceed target budget |
| `doc/adr.md` (~660+, ~13k est tokens) | status table or one ADR only | full decision history is not phase input |
| `app/knowledge_graph.py` (1258, ~13k est tokens) | `rg "^class\|^def " app/knowledge_graph.py` | full-read is forbidden |
| `tests/test_query_service.py` (1012, ~10k est tokens) | 1-2 relevant tests or fixtures | avoid full test file |
| `app/query_service.py` (~900+, ~8k est tokens) | `rg "^class\|^def " app/query_service.py` + exact function | large orchestrator |
| `doc/architecture.md` (383, ~5k est tokens) | module list or one section only | avoid coupling with ADR full-read |

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

| # | Phase | Severity | Finding | File(s) | Suggested Action |
|---|-------|----------|---------|---------|-----------------|
| 1 | 1 | critical | ... | app/foo.py:42 | ... |
| 2 | 2 | warning  | ... | app/bar.py | ... |

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
- If a finding was already noted in archive/architecture_review.md
  as "resolved", verify it is actually resolved before re-reporting.
- Use exact file paths and line numbers wherever possible.
- If the review scope is too large for one pass, state which phases
  you completed and which need a follow-up.
```

## Промпт 3: ADR Decision

```text
Role: Architect for hometutor.
Goal: evaluate and document an architecture decision.

Context: <describe the decision needed>

Read:
1. doc/adr.md — existing decisions and format
2. doc/conventions.md — current constraints
3. doc/architecture.md — current architecture
4. Relevant app/ modules

Evaluate:
1. What problem does this solve?
2. What alternatives exist?
3. What are the trade-offs of each alternative?
4. Does this conflict with any existing ADR?
5. What is the migration path from current state?
6. What is the blast radius if this decision is wrong?

Output format (append to doc/adr.md):
## ADR-NNN: <title>

**Status:** Proposed
**Date:** <today>
**Context:** <1-3 sentences>
**Decision:** <what we decided>
**Alternatives considered:**
- <alt 1>: <why rejected>
- <alt 2>: <why rejected>
**Consequences:**
- Positive: <benefits>
- Negative: <costs/risks>
- Migration: <what needs to change>

Rules:
- Keep ADR under 30 lines.
- Reference specific files and conventions.
- If the decision reverses a prior ADR, explicitly note supersedes.
```

## Артефакты

| Артефакт | Когда создаётся | Кому передаётся |
|----------|-----------------|-----------------|
| Execution contract | Фаза 3 | Разработчику, Дизайнеру |
| Architecture review report | После эпохи / по запросу | PO, всей команде |
| ADR entry | При архитектурном решении | Всей команде |

