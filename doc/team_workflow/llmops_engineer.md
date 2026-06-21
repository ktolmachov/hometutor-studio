# LLMOps Engineer

> Часть Ops-конвейера, описанного в [`rag_llm_ops_project_document.md`](rag_llm_ops_project_document.md) §6, §11, §31, §32, §34.
> Текущий приоритетный план: [`doc/next/localhost_balance_course_delight_plan.md`](../next/localhost_balance_course_delight_plan.md).

## Роль

Отвечает за стабильную, контролируемую и безопасную работу LLM-слоя. Главный вопрос:

> «Почему LLM дала именно такой ответ, каким prompt/model/context это было вызвано, и можно ли это повторить?»

В `hometutor` LLMOps — owner Profile-aware Fallback (`LOCAL_STRICT` / `BALANCED` / `CLOUD_FAST`) и разделения **primary chat LLM** vs **secondary LLM channels** (см. §31, §32).

## Зона ответственности

- Prompt registry (`app/prompts/`, `app/tutor_prompts.py`); prompt versioning; prompt regression tests.
- Primary chat LLM client (`app/provider.py`); fallback logic; soft/hard timeout.
- Profile policy: `HOME_RAG_LOCAL_PROFILE`, `HOME_RAG_LLM_FALLBACK_*`, `HOME_RAG_LLM_LOCAL_SOFT/HARD_TIMEOUT_SEC`.
- Secondary LLM channels guardrails: не ломать circuit breaker (`LLM_LOCAL_CB_*`); не включать их в profile-fallback без отдельного пакета.
- Token budget manager; context compression; structured outputs; JSON validation.
- LLM call trace и латентность p50/p95; fallback success rate.
- AI status banner copy (`app/ui/llm_local_banner.py`) — совместно с Designer.

## Не делает

- Не управляет retrieval / chunks / indexes (это RAGOps).
- Не управляет embedding моделями (это MLOps).
- Не пишет UI макеты (это Designer).
- Не закрывает пакеты в backlog (это PO).
- Не расширяет fallback на secondary каналы без отдельного пакета + ADR.

## Дальше по процессу

**Дальше по инструкции** [`process.md`](process.md): LLMOps gate срабатывает на STEP 3.5 после Architect+Designer, если контракт затрагивает `app/provider.py`, `app/config.py` (LLM/profile keys), `app/prompts/`, `app/tutor_prompts.py`, soft/hard timeout, fallback. На STEP 5/7 (Tester) — Reviewer для primary chat fallback тестов и quiz/SSR regression smoke.

---

## Промпт 1: LLMOps Impact Review (gate в STEP 3.5)

```text
# [two-root] Two-repo project: resolve app/** and requirements.txt against CODE_ROOT
# (editable install of `hometutor`: `pip show hometutor` -> "Editable project location");
# resolve doc/**, tests/**, scripts/** against the current cwd (DOCS_ROOT).
# Run git per-root: `git -C <CODE_ROOT> ...` for app code, `git -C <cwd> ...` for docs/tests.
Role: LLMOps Engineer for hometutor.
Goal: review proposed package for LLM-layer impact.
       Do NOT write code. Output = structured LLMOps Impact Report.

Input:
- {{ARTIFACTS_DIR}}/3_architect_contract.md
- {{ARTIFACTS_DIR}}/2_analyst_spec.md

Read ONLY:
- doc/team_workflow/rag_llm_ops_project_document.md  (§6, §11, §31, §32 — grep sections)
- doc/next/localhost_balance_course_delight_plan.md  (§0, §3.1, §3.2, §Phase 1, §Phase 2, §Phase 3 — grep)
- app/provider.py        (signatures only via grep)
- app/config.py          (Settings fields only)
- app/prompts/           (list filenames)
- app/tutor_prompts.py   (full read, ~87 lines)

Checklist:
1. Channel classification: does this change touch primary chat OR a secondary channel? Both? Flag clearly.
2. Profile awareness:
   - LOCAL_STRICT: no cloud leak? friendly error on CB-open?
   - BALANCED: soft/hard timeout не дублирует CB?
   - CLOUD_FAST: latency budget? UI fallback if key missing?
3. Prompt changes: stored in app/prompts/ or app/tutor_prompts.py? versioned? no hardcoding in routers/UI?
4. Token budget: new context-builder? respects model_context_window?
5. Secondary channel regression risk: quiz/SSR/ingestion smoke needed in DoD?
6. Banner copy: honest about where the request goes? respects embeddings axis separately?
7. Privacy note: retrieved context may go to cloud in BALANCED/CLOUD_FAST — is this documented?

Output format:
## LLMOps Impact Report — {{PACKAGE_ID}}

### Affected channels
- Primary chat: yes/no — <surface>
- Secondary: <list channels touched or "none">

### Profile policy diff
| Profile | Behavior before | Behavior after |
|---|---|---|
| LOCAL_STRICT | … | … |
| BALANCED    | … | … |
| CLOUD_FAST  | … | … |

### Prompt diff
<list new/changed prompts + versions>

### Required tests in DoD
- tests/test_provider.py -k <pattern>
- tests/test_llm_local_banner.py (if banner changed)
- regression smoke for quiz/SSR if app/provider.py changed

### Verdict
- GREEN | YELLOW (conditions) | RED (block — needs Architect revision)

Token budget: <= 8k input.
```

---

## Промпт 2: Primary Chat Fallback Verify (для Tester gate)

```text
Role: LLMOps Verifier for hometutor primary chat fallback.
Goal: confirm fallback policy works across 8 scenarios from balance plan Phase 2.

Scenarios (each must be covered by an existing test):
1. local-ok
2. local-down-balanced  (fallback fires)
3. local-down-strict    (friendly error)
4. local-slow-soft-timeout  (banner switches)
5. local-slow-hard-timeout  (request cancelled, fallback fires in BALANCED)
6. fallback-misconfigured   (friendly error, no hang)
7. CB-open-balanced         (immediate fallback, no timeout check)
8. CB-open-strict           (friendly error, no cloud touch)

Steps:
1. Run: pytest tests/test_provider.py tests/test_llm_local_health.py -q
2. For each scenario, grep test file for matching test name; verify it exists and passes.
3. Smoke regression: pytest tests/test_quiz*.py tests/test_ssr*.py -q (secondary channels untouched).

Output:
- VERDICT: PASS | CONDITIONAL PASS | FAIL
- For each missing scenario: name + suggested test stub (no code, just intent)
- Regression result: green/red
```
