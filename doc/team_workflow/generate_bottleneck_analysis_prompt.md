# Bottleneck Analysis — LLM Prompt Template

Use this prompt to get actionable optimization recommendations from an LLM
after running `analyze_bottlenecks.py`.

## Quick Start

```bash
# Generate JSON report + inline LLM prompt
python scripts/analyze_bottlenecks.py --last 20 --format md --emit-prompt

# Or: pipe JSON directly into this prompt manually
python scripts/analyze_bottlenecks.py --last 20 --format json
```

Then copy the **"Скопируй в LLM"** block (appended by `--emit-prompt`) into a
fresh agent session.

---

## Prompt Template (manual use)

Paste this block into the LLM, replacing `<JSON_REPORT>` with the output of
`analyze_bottlenecks.py --format json`.

```text
Role: Ты Performance Engineer для Python CLI пайплайна hometutor.

Context: hometutor — локальный учебный ассистент. Pipeline запускается через
`scripts/run_autonomous.py`. Единая точка входа: `python scripts/workflow.py` ([workflow_router.md](./workflow_router.md)).
Тяжёлые sub-скрипты: `generate_orchestration_prompt.py`,
`close_package.py`, `backlog_registry_lint.py`, `auto_promote_next_wave_package.py`.
Архитектурные границы: `doc/conventions_architecture.md`.

Task: Проанализируй данные о производительности (JSON ниже) и предложи
actionable рекомендации по устранению узких мест.

Input signatures (grep-only, no full reads):
- app/query_service.py → `grep "^class|^def " app/query_service.py`
- scripts/run_autonomous.py → `grep "^def " scripts/run_autonomous.py`

Output schema (строго соблюдать):

1. Executive summary — 3 строки:
   - Общее wall time последнего run
   - Топ-3 фазы по impact (phase_name: mean=Xs, p95=Ys)
   - Одна строка вывода: "Главный узел: ..."

2. Critical bottlenecks (сортировать P0 → P1 → P2):
   Для каждого:
   - **Приоритет**: P0/P1/P2
   - **Phase**: `script::phase_name`
   - **Current cost**: mean=Xs, p95=Ys, max=Zs
   - **Root cause hypothesis**: (1–2 предложения)
   - **Proposed fix**: file:line ссылки, конкретные изменения
   - **Estimated win**: -Xs / -X%
   - **Risk**: low/medium/high + обоснование

3. Stability issues — фазы с stddev/mean > 0.5:
   - Phase, CV, possible causes

4. Regressions — растущие фазы (slope > 0.1 s/run):
   - Phase, slope, when it started growing

5. Action checklist — упорядоченный список:
   - [ ] PACKAGE_ID: описание (file, estimated gain)

Constraints:
- Не предлагай unsafe параллельность (race-prone subprocess, shared state).
- Не предлагай кэширование без анализа invalidation сложности.
- Уважай write-set политику (изменять только файлы из явного scope).
- Ссылайся на конкретные file:line, не абстрактные "оптимизируй X".
- Бюджет контекста ≤ 12k токенов: для code refs используй grep, не full reads.

Performance data (JSON):
<JSON_REPORT>
```

---

## Expected Output Structure

```
# Executive Summary
- Total wall time: ~35–40s (estimated, 24 runs sampled)
- Top-3: close_package::dod_run (mean=11.5s, p95=14.1s),
         run_autonomous::dod_total (mean=10.2s, p95=10.6s),
         run_autonomous::dod_cmd_0 (mean=8.5s, p95=9.1s)
- Главный узел: DoD-фаза (pytest / lint run) — ~65% суммарного wall-time

# Critical Bottlenecks

## P0: close_package::dod_run + run_autonomous::dod_total
- Current cost: mean≈11s, p95=14.1s, max=14.4s
- Root cause: полный pytest-прогон (dod_cmd_0) запускается каждый раз
  при закрытии пакета; нет разделения smoke vs full suite
- Fix: добавить --smoke flag в close_package.py, запускать только
  тесты затронутых модулей (pytest -k <marker>)
- Estimated win: -5–8s / -40–55%
- Risk: medium (нужна маркировка тестов)

## P1: run_autonomous::roadmap_sync_check + close_package::roadmap_sync_check
- Current cost: mean=5.0s / 4.7s, p95=5.5s
- Root cause: синхронный IO-check roadmap при каждом запуске;
  возможно полное чтение большого файла вместо grep/diff
- Fix: заменить полное чтение на `git diff --name-only HEAD~1` +
  проверку только изменённых секций (scripts/close_package.py)
- Estimated win: -3–4s / -60%
- Risk: low

## P2: backlog_registry_lint::validate_schema (high variance)
- CV=1.12, stddev=0.296 при mean=0.264s
- Root cause: нестабильное время валидации — вероятно зависит от
  размера registry; нет кэширования результата parse_yaml
- Fix: кэшировать результат parse_yaml в памяти внутри одного run
- Estimated win: стабилизация, -0.1–0.2s
- Risk: low

# Stability Issues
- backlog_registry_lint::validate_schema — CV=1.12 (high)
- __main__::lint_tasklist — CV=1.41 (высокий разброс, n=3)
- backlog_registry_lint::parse_yaml — CV=0.65

# Regressions
- Не обнаружено (regressions=[])

# Action Checklist
- [ ] PERF-dod-smoke: Добавить --smoke режим в close_package.py (scripts/close_package.py)
- [ ] PERF-roadmap-io: Заменить roadmap_sync_check на git-diff-based check
- [ ] PERF-lint-cache: Кэшировать parse_yaml внутри backlog_registry_lint.py
```

---

## Last Sample Run (2026-05-23, --last 20, 24 runs)

| Phase | mean (s) | p95 (s) | Category | Status |
|---|---|---|---|---|
| close_package::dod_run | 11.47 | 14.13 | dod | 🔴 P0 outlier |
| run_autonomous::dod_total | 10.19 | 10.64 | dod | 🔴 P0 outlier |
| run_autonomous::close_package | 9.98 | 10.94 | subprocess | 🔴 P0 outlier |
| run_autonomous::dod_cmd_0 | 8.48 | 9.07 | dod | 🔴 P0 outlier |
| run_autonomous::roadmap_sync_check | 5.04 | 5.52 | io | 🟠 P1 outlier |
| close_package::roadmap_sync_check | 4.71 | 4.71 | io | 🟠 P1 mean_slow |
| backlog_registry_lint::validate_schema | 0.26 | 1.02 | subscript | 🟡 high variance |
| backlog_registry_lint::parse_yaml | 0.38 | 0.71 | io | 🟡 high variance |

Regressions: **none**

---

## Tips for Low Token Budget

If context budget is tight (approaching 12k), use these grep commands instead
of reading full files:

```bash
# Sub-script function signatures only
grep "^def " scripts/generate_orchestration_prompt.py | head -30
grep "^def " scripts/close_package.py | head -30
grep "^def " scripts/backlog_registry_lint.py | head -30

# Find specific bottleneck function
grep -n "_extract_cjm_moment\|extract_recent_closed" scripts/generate_orchestration_prompt.py
```

Pass grep output as context instead of full file contents.
