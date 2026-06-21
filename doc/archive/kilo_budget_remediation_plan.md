# Kilo Budget Stack — Remediation Plan (Wave 4)

**Status:** ready-for-execution
**Target model:** Sonnet 4.6 (standalone session, no access to parent conversation)
**Created:** 2026-04-24
**Author:** Opus 4.7 audit of Waves 1–3 delivery

---

## 0. Context for a fresh agent

В репозитории `home-rag_v2` уже есть три слоя защиты бюджета Kilo-сессий:

1. **`scripts/_kilo_guard.py`** — pure core. `GuardThresholds`, `evaluate_guard()`, `summarize_body()`. Единственный источник истины для verdict-логики.
2. **`scripts/kilo_proxy_relay.py`** — runtime relay (Tier 2). Уже использует `evaluate_guard()`.
3. **`scripts/kilo_budget_simulate.py`** — static simulator (Tier 1). Subcommands: `simulate`, `capture`, `replay`. Использует `evaluate_guard()` и `build_payload()`.
4. **`scripts/kilo_budget_gate.py`** — pre-commit gate. Сравнивает HEAD vs staged index (в `--dry-run` — worktree).
5. **`scripts/kilo_injection_calibrate.py`** — билдер calibrated estimate из project files.
6. **`scripts/kilo_budget_daily.py`** — daily health check.
7. **`fixtures/kilo_injection_baseline.json`** — единственный fixture (в текущем состоянии — `fixture_kind: calibrated_estimate`).
8. **`.pre-commit-config.yaml`** — hook с broad `files:` regex.
9. Docs: `doc/kilo_budget_gate.md`, `doc/kilo_budget_system.md`, `doc/team_workflow/budget_health_prompt.md`.

Три waves исправлений уже сделаны предыдущим агентом. Этот план закрывает **остатки**, которые либо не выполнены, либо привели к регрессии.

**Обязательное чтение перед началом работы:**

- `CLAUDE.md` — проектные правила (token safety, read-set rules, NEVER read forbidden files)
- `scripts/_kilo_guard.py` (241 строка — целиком можно читать)
- `scripts/kilo_budget_gate.py` (360 строк — целиком можно читать)
- `scripts/kilo_budget_daily.py` (312 строк — целиком можно читать)
- `scripts/kilo_budget_simulate.py` (442 строки — целиком можно читать)
- `fixtures/kilo_injection_baseline.json` (222 строки)

Совокупный read-set ~8–10k tokens — в рамках лимита 12k.

**Общий принцип работы:**

- Каждый шаг — отдельный commit с понятным сообщением.
- Перед каждым commit: `python scripts/kilo_budget_gate.py --dry-run` чтобы убедиться, что изменения в самом стеке не ломают gate.
- После каждого шага: запустить соответствующие тесты (указаны в каждом шаге).
- Язык commit-сообщений — английский, тело — 1–3 строки.
- **НИКОГДА не используй `git commit --no-verify` или `KILO_BUDGET_GATE=skip`** без явного запроса пользователя.
- Документировать каждое реальное отклонение от плана в `doc/changelog.md` (append, не переписывать).

---

## 1. Критичные баги (P0 — ломают систему сегодня)

### P0-1. `kilo_budget_daily.py` падает с TypeError при любом запуске

**Симптом:**

```
$ python scripts/kilo_budget_daily.py --no-save
TypeError: evaluate_launcher() missing 1 required keyword-only argument: 'dry_run'
```

**Причина:** в Wave 2 сигнатура `evaluate_launcher()` в [scripts/kilo_budget_gate.py:185](../scripts/kilo_budget_gate.py) получила keyword-only параметр `dry_run`, но [scripts/kilo_budget_daily.py:75](../scripts/kilo_budget_daily.py) вызывает её без этого аргумента:

```python
# scripts/kilo_budget_daily.py:75 (текущее, сломанное)
gate_rows = [evaluate_launcher(l["name"], l["path"], fixture_data, thresholds) for l in LAUNCHERS]
```

**Fix (минимальный):** передать `dry_run=True` явно — daily всегда работает по worktree-like снимку (он ведь не pre-commit, а обзор).

```python
gate_rows = [
    evaluate_launcher(l["name"], l["path"], fixture_data, thresholds, dry_run=True)
    for l in LAUNCHERS
]
```

**Почему `dry_run=True`, а не `False`:** daily запускается вне контекста commit'а и не должен зависеть от staged index (который может быть пуст). Он показывает "текущее состояние worktree", что совпадает с semantics `--dry-run` в gate.

**Verification:**

```bash
python scripts/kilo_budget_daily.py --no-save                          # must exit 0 or 2, not crash
python scripts/kilo_budget_daily.py --no-save --json                   # must produce valid JSON
python scripts/kilo_budget_daily.py --no-save --use-calibrated-estimate # must compute both analyses
pytest tests/test_kilo_budget_daily.py -q                              # создать тесты — см. P0-2
```

### P0-2. Нет теста, который ловит запуск `daily.py`

Тесты на daily отсутствуют полностью (`ls tests/test_kilo*` подтверждает). Именно это позволило регрессии P0-1 просочиться.

**Fix:** создать `tests/test_kilo_budget_daily.py` со следующими минимальными тестами:

```python
# tests/test_kilo_budget_daily.py
"""Smoke + contract tests для scripts/kilo_budget_daily.py.

Главная цель — сделать невозможным регрессию типа "сломан вызов
evaluate_launcher()" незамеченной. Плюс — проверяет, что дефолтный запуск
НЕ модифицирует committed fixture (read-only invariant).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import kilo_budget_daily as daily  # noqa: E402


def test_run_check_does_not_crash_without_calibrated_estimate():
    thresholds = daily.GuardThresholds()
    report = daily.run_check(
        thresholds,
        include_calibrated_estimate=False,
        write_fixture=False,
    )
    assert report["overall_status"] in daily.STATUS_ORDER
    assert "baseline_gate" in report["analyses"]
    assert "calibrated_estimate" not in report["analyses"]


def test_run_check_with_calibrated_estimate_produces_both_analyses():
    thresholds = daily.GuardThresholds()
    report = daily.run_check(
        thresholds,
        include_calibrated_estimate=True,
        write_fixture=False,
    )
    assert "baseline_gate" in report["analyses"]
    assert "calibrated_estimate" in report["analyses"]


def test_default_run_is_read_only_for_committed_fixture(tmp_path, monkeypatch):
    """Fixture на диске не должен меняться при обычном запуске."""
    fixture_path = ROOT / "fixtures" / "kilo_injection_baseline.json"
    before_bytes = fixture_path.read_bytes()
    daily.run_check(
        daily.GuardThresholds(),
        include_calibrated_estimate=False,
        write_fixture=False,
    )
    after_bytes = fixture_path.read_bytes()
    assert before_bytes == after_bytes


def test_main_no_save_returns_non_crashing_exit_code(capsys):
    rc = daily.main(["--no-save"])
    assert rc in (0, 2)  # 0 = ok/caution/warn, 2 = soft/hard_block


def test_main_json_output_contains_overall_status(capsys):
    rc = daily.main(["--no-save", "--json"])
    captured = capsys.readouterr().out
    payload = json.loads(captured.splitlines()[0] if captured.startswith("{\n") else captured)
    # JSON печатается через json.dumps(..., indent=2) → ищем в raw
    payload = json.loads(captured[: captured.rfind("}") + 1])
    assert "overall_status" in payload
    assert payload["overall_status"] in daily.STATUS_ORDER
```

Обрати внимание: `test_main_json_output_contains_overall_status` может потребовать лёгкой коррекции парсинга — daily печатает JSON и иногда дополнительный `Report saved:` line (когда `--no-save` — не печатает). Проверь вручную `python scripts/kilo_budget_daily.py --no-save --json | head -5`, чтобы подобрать точный slice.

**Verification:**

```bash
pytest tests/test_kilo_budget_daily.py -q
pytest tests/test_kilo_guard.py tests/test_kilo_budget_simulate.py tests/test_kilo_budget_gate.py tests/test_kilo_budget_daily.py -q
```

### P0-3. UTC даты в `_today()` приводят к off-by-one day

**Симптом:** при работе в МСК после 21:00 отчёт за сегодня сохраняется под именем "завтра"; при работе до 03:00 — под именем "вчера". Пользователь уже жаловался.

**Причина:** [scripts/kilo_budget_daily.py:40–41](../scripts/kilo_budget_daily.py)

```python
def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
```

**Fix:** использовать локальную дату:

```python
def _today() -> str:
    # Local date — reports are human-facing artefacts; UTC off-by-one confuses users.
    return datetime.now().strftime("%Y-%m-%d")
```

И **ts** тоже — но для ts сохранить UTC с явным суффиксом (`isoformat()` с tzinfo). Т.е. `date` — локально, `ts` — UTC:

```python
# в run_check():
"date": _today(),  # local
"ts": datetime.now(timezone.utc).isoformat(),  # UTC, unambiguous
```

**Verification:** ручная — `python scripts/kilo_budget_daily.py --no-save | head -2` должен показать текущую московскую дату в заголовке `=== Kilo Budget Health [YYYY-MM-DD] ===`.

---

## 2. Семантические дыры, подрывающие гарантию системы (P1)

### P1-1. "baseline_gate" считается по calibrated fixture — лейбл обманывает

**Текущее состояние:** [fixtures/kilo_injection_baseline.json:4](../fixtures/kilo_injection_baseline.json)

```json
"fixture_kind": "calibrated_estimate"
```

При этом в `daily.py`, `gate.py` и docs этот же файл называется "baseline" и противопоставляется "calibrated_estimate". Это структурная ложь: pre-commit gate фактически считает по оценке, а docs обещают authoritative baseline.

**Fix (two-part):**

**Part A. Переименовать in-code: baseline_gate → committed_fixture_gate.**

Changes:
- [scripts/kilo_budget_daily.py](../scripts/kilo_budget_daily.py): везде `"baseline_gate"` → `"committed_fixture_gate"`. Не лейтмотив "реальность", а "то, что в репо".
- [doc/kilo_budget_system.md](../doc/kilo_budget_system.md), [doc/team_workflow/budget_health_prompt.md](../doc/team_workflow/budget_health_prompt.md), [doc/kilo_budget_gate.md](../doc/kilo_budget_gate.md): последовательно заменить "baseline" → "committed fixture" там, где речь идёт об источнике, а не о снимке для сравнения. Слово "baseline" оставить только когда имеется в виду "HEAD-снимок для diff".

**Part B. Честно промаркировать сам fixture.**

Изменить [fixtures/kilo_injection_baseline.json](../fixtures/kilo_injection_baseline.json) `_meta`:

```json
"_meta": {
  "purpose": "Committed injection fixture used by the pre-commit gate.",
  "fixture_kind": "calibrated_estimate",
  "authority": "offline_approximation",
  "source_note": "This fixture is currently a calibrated estimate built from project files; it is NOT a real relay capture. Replace with captured_relay_fixture via `scripts/kilo_budget_simulate.py capture` when a real Kilo capture becomes available. Until then, gate verdicts are indicative, not authoritative.",
  "refresh": "python scripts/kilo_budget_simulate.py capture --from-jsonl logs/kilo_relay.jsonl --probe <marker> -o fixtures/kilo_injection_baseline.json",
  ...
}
```

**Verification:**

```bash
grep -rn "baseline_gate\|baseline fixture" scripts/ doc/ | wc -l   # должно резко упасть
python scripts/kilo_budget_daily.py --no-save | grep -i committed  # новый лейбл виден
```

### P1-2. Нет физического split'а captured vs calibrated fixture

**Текущее:** один файл `fixtures/kilo_injection_baseline.json`. В `kilo_injection_calibrate.py` прописана отдельная константа `CALIBRATED_FIXTURE_PATH = fixtures/kilo_injection_calibrated.json`, но этот файл **не существует** и никем не используется.

**Предложенное решение (минимально инвазивное):**

1. Создать `fixtures/kilo_injection_calibrated.json` как output по умолчанию для `kilo_injection_calibrate.py`. Калибратор уже туда пишет — проверь [scripts/kilo_injection_calibrate.py:326](../scripts/kilo_injection_calibrate.py). Если ещё не пишет в этот путь по умолчанию — правь default.
2. Оставить `fixtures/kilo_injection_baseline.json` как "committed gate fixture" (независимо от происхождения).
3. Добавить новый символический слот: `fixtures/kilo_injection_captured.json` — **пока не создавать**, но упомянуть в docs как целевое состояние и добавить в `.gitignore`-исключения (если captured когда-нибудь появится, его **нужно** коммитить). Фактически: добавить в `doc/kilo_budget_system.md` § Injection Anatomy таблицу:

   | File | Purpose | Status |
   |---|---|---|
   | `fixtures/kilo_injection_baseline.json` | fixture used by pre-commit gate | present (calibrated_estimate) |
   | `fixtures/kilo_injection_calibrated.json` | latest calibrator output | regenerated by calibrate script |
   | `fixtures/kilo_injection_captured.json` | authoritative runtime capture | **not yet created** — target state |

4. В `scripts/kilo_budget_simulate.py capture` subcommand: если `-o` не указан, default → `fixtures/kilo_injection_captured.json`. Это создаёт четкое место для authoritative fixture без изменения baseline.
5. В `scripts/kilo_budget_gate.py`: если `fixtures/kilo_injection_captured.json` **существует**, использовать его как источник для `INJECTION_FIXTURE`; иначе fallback на `kilo_injection_baseline.json`. Логировать выбор:

```python
CAPTURED_FIXTURE = ROOT / "fixtures" / "kilo_injection_captured.json"
LEGACY_BASELINE  = ROOT / "fixtures" / "kilo_injection_baseline.json"

def _choose_fixture() -> tuple[Path, str]:
    if CAPTURED_FIXTURE.exists():
        return CAPTURED_FIXTURE, "captured_relay_fixture"
    return LEGACY_BASELINE, "legacy_calibrated_baseline"

INJECTION_FIXTURE, INJECTION_FIXTURE_AUTHORITY = _choose_fixture()
```

В `--json` output gate добавить поле `"fixture_authority": INJECTION_FIXTURE_AUTHORITY`. Это создаёт **механизм будущего автоматического апгрейда** без миграции кода — как только появится captured fixture, gate сам на него переключится.

**Verification:**

```bash
python scripts/kilo_injection_calibrate.py --dry-run  # пишет в calibrated path
python scripts/kilo_budget_gate.py --dry-run          # использует baseline (captured не существует)
touch fixtures/kilo_injection_captured.json && echo '{"messages":[],"tools":[]}' > fixtures/kilo_injection_captured.json
python scripts/kilo_budget_gate.py --dry-run | grep -i fixture  # теперь authority=captured_relay_fixture
rm fixtures/kilo_injection_captured.json                         # откат — это был smoke
```

### P1-3. Dependency-aware launcher selection обещан, но не реализован

**Обещано в плане:** gate должен помечать, триггернулся launcher потому что **он сам** изменился, или потому что изменился **fixture/guard** (dependency).

**Текущее:** все 4 launcher'а обрабатываются одинаково, никакой attribution на staged-источник нет.

**Fix:** в `evaluate_launcher()` и в output добавить поле `trigger_reason`:

```python
def evaluate_launcher(
    name: str, path: str, fixture: dict, thresholds: GuardThresholds,
    *, dry_run: bool, staged_files: list[str] | None = None,
) -> dict:
    ...
    # trigger reason
    launcher_is_staged = staged_files is not None and path.replace("\\", "/") in staged_files
    dependency_changed = staged_files is not None and any(
        f in staged_files for f in (
            "fixtures/kilo_injection_baseline.json",
            "fixtures/kilo_injection_captured.json",
            "scripts/_kilo_guard.py",
            "scripts/kilo_budget_gate.py",
            "scripts/kilo_budget_simulate.py",
        )
    )
    if launcher_is_staged and dependency_changed:
        trigger = "launcher+dependency"
    elif launcher_is_staged:
        trigger = "launcher_self"
    elif dependency_changed:
        trigger = "dependency_only"
    else:
        trigger = "none"  # dry-run или launcher не задет

    return {..., "trigger_reason": trigger, ...}
```

И в `format_launcher_row()` добавить суффикс `[dep]` / `[self]` / `[self+dep]` к строке. В JSON output — как есть, новое поле.

**Verification:**

```bash
# artificial staged dep-only change:
git stash
echo ' ' >> scripts/_kilo_guard.py && git add scripts/_kilo_guard.py
python scripts/kilo_budget_gate.py --json | grep trigger_reason   # должно показать dependency_only для всех 4 launcher'ов
git reset HEAD scripts/_kilo_guard.py && git checkout scripts/_kilo_guard.py
git stash pop
```

---

## 3. Доводка до уровня "predict → prevent" (P2)

### P2-1. Section-level attribution вместо message-level (killer feature из исходного плана)

**Статус:** предыдущий агент честно признал, что не сделал, оставил message-level.

**Значение:** сейчас `--attribute` в simulator показывает "удаление launcher как целого message спасёт от warn→ok". Полезность ограничена — launcher всегда останется одним message. Нужна attribution **внутри** launcher по секциям (`##`, `###`, fenced блоки).

**Контракт новой фичи:**

```bash
python scripts/kilo_budget_simulate.py simulate \
    --launcher doc/team_workflow/generate_plan_next_prompt.md \
    --injection fixtures/kilo_injection_baseline.json \
    --attribute --section-attribute
```

Новый флаг `--section-attribute` запускает дополнительную attribution **внутри launcher-файла**:

1. Парсер режет launcher по heading-уровню (settable: `--section-level 2` = `##`, `--section-level 3` = `###`; default 2).
2. Для каждой секции: leave-one-out — пересоздать launcher_text без этой секции, пересчитать verdict, посчитать `contrib_body_chars` и `would_downgrade`.
3. Сортировать top-10 по вкладу, показать "which section in launcher is driving the budget".

**Реализация (псевдокод):**

```python
# в kilo_budget_simulate.py
import re

_H2_RE = re.compile(r"^(##+)\s+(.+)$", re.MULTILINE)

def split_launcher_by_sections(text: str, level: int = 2) -> list[tuple[str, str]]:
    """Return [(heading, section_text), ...]. Section includes its heading line."""
    anchors = [(m.start(), m.group(1), m.group(2)) for m in _H2_RE.finditer(text)
               if len(m.group(1)) == level]
    if not anchors:
        return [("(whole launcher)", text)]
    sections = []
    # preamble before first heading
    if anchors[0][0] > 0:
        sections.append(("(preamble)", text[:anchors[0][0]]))
    for i, (pos, hashes, title) in enumerate(anchors):
        end = anchors[i + 1][0] if i + 1 < len(anchors) else len(text)
        sections.append((title.strip(), text[pos:end]))
    return sections


def attribute_sections(
    fixture: dict, launcher_text: str, user_turn: str | None,
    *, thresholds: GuardThresholds, mode: str, level: int,
) -> list[dict]:
    sections = split_launcher_by_sections(launcher_text, level=level)
    base_payload, _ = build_payload(fixture, launcher_text=launcher_text, user_turn=user_turn)
    base = simulate_payload(base_payload, thresholds=thresholds, mode=mode)
    base_order = LEVEL_ORDER[base["verdict"]["level"]]
    base_body = base["summary"]["body_chars"]
    rows = []
    for title, section_text in sections:
        trimmed_launcher = launcher_text.replace(section_text, "", 1)
        alt_payload, _ = build_payload(fixture, launcher_text=trimmed_launcher, user_turn=user_turn)
        alt = simulate_payload(alt_payload, thresholds=thresholds, mode=mode)
        rows.append({
            "section": title,
            "chars": len(section_text),
            "contrib_body_chars": base_body - alt["summary"]["body_chars"],
            "if_removed_level": alt["verdict"]["level"],
            "would_downgrade": LEVEL_ORDER[alt["verdict"]["level"]] < base_order,
        })
    rows.sort(key=lambda r: r["contrib_body_chars"], reverse=True)
    return rows
```

Подключение к `cmd_simulate`:

```python
section_rows = None
if args.section_attribute and launcher_text:
    section_rows = attribute_sections(
        fixture, launcher_text, args.user_turn,
        thresholds=thresholds, mode=args.mode, level=args.section_level,
    )
# В format_report: отдельная таблица "Section-level attribution (inside launcher)".
```

**Тесты:** `tests/test_kilo_budget_simulate.py` — добавить `test_section_attribute_splits_by_h2`, `test_section_attribute_orders_by_contribution`, `test_section_attribute_whole_launcher_when_no_headings`.

**Docs sync:**
- `doc/kilo_budget_gate.md` § "When gate fails — how to investigate": добавить `--section-attribute` пример.
- `doc/kilo_budget_system.md`: в разделе о simulator пометить message-level и section-level как два режима.

**Verification:**

```bash
pytest tests/test_kilo_budget_simulate.py -q
python scripts/kilo_budget_simulate.py simulate \
  --launcher doc/team_workflow/generate_plan_next_prompt.md \
  --injection fixtures/kilo_injection_baseline.json \
  --attribute --section-attribute
```

В output должна появиться секция `Section-level attribution (inside launcher)` с top-10 разделов по вкладу в body_chars.

### P2-2. Parity test simulator ↔ relay (интеграционный sanity)

Исходный план требовал: "взять одну существующую запись из `logs/kilo_relay.jsonl`, реконструировать payload, прогнать через simulator — verdict должен совпасть с `guard.level` из записи".

**Статус:** subcommand `replay` существует ([scripts/kilo_budget_simulate.py:362](../scripts/kilo_budget_simulate.py)), но на него **нет теста**. Это значит: regression в payload-reconstruction может остаться незамеченной.

**Fix:** в `tests/test_kilo_budget_simulate.py` добавить synthetic parity test:

```python
def test_replay_parity_with_synthesized_record(tmp_path):
    """Build a synthetic JSONL record, feed to replay — verdict must match recorded level."""
    from _kilo_guard import GuardThresholds, evaluate_guard, summarize_body
    import kilo_budget_simulate as sim

    body = json.dumps({
        "model": "openai/gpt-4o-mini",
        "messages": [{"role": "user", "content": "hi"}],
        "tools": [],
    }, ensure_ascii=False)
    summary = summarize_body(body)
    verdict = evaluate_guard(sim.CHAT_PATH, body, summary, thresholds=GuardThresholds(), mode="warn")

    record = {
        "path": sim.CHAT_PATH,
        "request_id": "test-1",
        "ts": "2026-04-24T00:00:00Z",
        "request": {"body_raw": body, "body_chars": len(body)},
        "guard": {"level": verdict.level},
    }
    jsonl_path = tmp_path / "synth.jsonl"
    jsonl_path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    rc = sim.main(["replay", "--from-jsonl", str(jsonl_path)])
    assert rc == 0  # 0 mismatches
```

### P2-3. Thresholds drift: проверить, что везде `max_messages=15`

Ручная грепка:

```bash
grep -rn "max_messages\|MAX_MESSAGES\|messages_count" scripts/ doc/ | grep -iE "=\s*8|:\s*8" || echo "clean"
```

Если найдутся упоминания `8` — обновить на `15`. Отдельно проверить:
- `scripts/kilo_proxy_relay.py` — любые inline константы и comments
- `doc/kilo_budget_gate.md:109`, `doc/kilo_budget_system.md`, `doc/team_workflow/budget_health_prompt.md`

---

## 4. Docs & integration cleanup (P3)

### P3-1. Ослабить overclaim в `doc/kilo_budget_system.md`

Текущее (строка ~32–34):

> ### Single source of truth
> Вся guard-логика живёт в `scripts/_kilo_guard.py`.
> Relay, simulator, gate и daily check вызывают одну функцию `evaluate_guard()`.
> Для identical payload drift между static verdict и runtime verdict структурно невозможен.

Добавить второй параграф с оговоркой:

> **Важная оговорка.** Single-source-of-truth гарантирует верdict-равенство **только для identical payload**. Injection (system prompt, memory blocks, tool schemas, `<available_skills>`) у нас сейчас представлен `calibrated_estimate`, а не captured runtime snapshot. Поэтому static verdict — это индикатор, а не substitute for runtime probe. Для получения authoritative baseline запусти `kilo_budget_probe.py` и закоммить результат в `fixtures/kilo_injection_captured.json` (см. § P1-2).

### P3-2. `doc/team_workflow/budget_health_prompt.md` — убрать "всегда актуально"

Найти все формулировки вида "margins всегда актуальны" / "реальное состояние системы" / "гарантированно отражает" и заменить на точные: "оценочная margin на момент запуска", "приближение по committed fixture", "требует periodic refresh через Tier-2 probe".

### P3-3. README / `doc/agent_workflow.md` — навигация

Убедиться, что `doc/agent_workflow.md` содержит ссылку на `doc/kilo_budget_system.md` и `doc/kilo_budget_remediation_plan.md` (этот файл). Если нет — добавить 1–2 строки в навигационный индекс.

---

## 5. Порядок исполнения и чек-лист

Исполнять строго в этом порядке. Каждый шаг — свой commit.

- [ ] **Step 1 (P0-1 + P0-2):** fix TypeError в daily.py + добавить `tests/test_kilo_budget_daily.py`. Commit: `fix(kilo-budget): pass dry_run to evaluate_launcher in daily; add regression tests`.
- [ ] **Step 2 (P0-3):** локальная дата в `_today()`, UTC в `ts`. Commit: `fix(kilo-budget): use local date for daily report filename`.
- [ ] **Step 3 (P1-1):** переименовать `baseline_gate` → `committed_fixture_gate` в коде и docs; обновить `_meta` в fixture. Commit: `refactor(kilo-budget): honest labels — committed_fixture_gate, not baseline_gate`.
- [ ] **Step 4 (P1-2):** ввести three-file схему (baseline / calibrated / captured) + автоматический upgrade в gate. Commit: `feat(kilo-budget): prefer captured fixture over calibrated baseline when available`.
- [ ] **Step 5 (P1-3):** `trigger_reason` в `evaluate_launcher()`. Commit: `feat(kilo-budget-gate): label launcher triggers (launcher_self / dependency_only / both)`.
- [ ] **Step 6 (P2-1):** `--section-attribute` в simulator + тесты + docs. Commit: `feat(kilo-budget-simulate): add section-level attribution inside launcher`.
- [ ] **Step 7 (P2-2):** parity test для `replay`. Commit: `test(kilo-budget-simulate): synthetic replay parity test`.
- [ ] **Step 8 (P2-3 + P3-*):** threshold audit + ослабить overclaim в docs. Commit: `docs(kilo-budget): reduce overclaim, sync thresholds everywhere`.

**Финальная верификация (запустить перед последним commit):**

```bash
# 1. Весь kilo-стек тестов
pytest tests/test_kilo_guard.py \
       tests/test_kilo_budget_simulate.py \
       tests/test_kilo_budget_gate.py \
       tests/test_kilo_budget_daily.py -q

# 2. Smoke всех CLI
python scripts/kilo_budget_daily.py --no-save
python scripts/kilo_budget_daily.py --no-save --use-calibrated-estimate
python scripts/kilo_budget_daily.py --no-save --json
python scripts/kilo_budget_gate.py --dry-run
python scripts/kilo_budget_gate.py --json
python scripts/kilo_budget_simulate.py simulate \
    --launcher doc/team_workflow/generate_plan_next_prompt.md \
    --injection fixtures/kilo_injection_baseline.json \
    --attribute --section-attribute
python scripts/kilo_injection_calibrate.py --dry-run

# 3. Grep на drift
grep -rn "baseline_gate" scripts/ doc/ | grep -v remediation_plan   # должно быть пусто
grep -rn "max_messages=\s*8\|MAX_MESSAGES=\s*8" scripts/ doc/ || echo "clean"
```

Все три блока должны проходить без ошибок и с consistent verdict'ами.

---

## 6. Что НЕ делать в этой сессии

- **Не трогать** `scripts/_kilo_guard.py` API — это stable core. Только добавление новых полей в `GuardVerdict`/`GuardThresholds` допустимо, и только если строго необходимо (в этом плане не нужно).
- **Не запускать** реальный `kilo_budget_probe.py` через Kilo GUI — это Tier-2, требует человека.
- **Не создавать** `fixtures/kilo_injection_captured.json` с synthetic содержимым. Этот файл должен появиться только из реального capture. В плане описано только как gate должен себя вести *когда он появится*.
- **Не переписывать** simulator/gate "для красоты" — scope строго по P0–P3.
- **Не добавлять** новые threshold'ы, новые risk patterns, новые level'ы — scope только исправления и section-level attribution.

---

## 7. Контакт и эскалация

Если в процессе обнаружится что-то, что противоречит этому плану (например, `evaluate_launcher()` окажется уже fixed, или появится captured fixture), — **не делай silent override**. Пауза, report в chat: "обнаружил X — план Y более не применим, предлагаю Z". Пользователь подтвердит или скорректирует.

Если какой-то шаг упрётся в token budget (>12k input): разбивай на подшаги, делай по одному файлу за call, используй `grep --signatures` вместо full-read для модулей >600 строк.

Успеха. Цель Wave 4: от "частично реализовано" к "действительно predict-and-prevent на уровне репозитория".

---

## 8. Дополнительные риски и слепые зоны (P2–P3, при наличии бюджета)

Пункты ниже не блокируют breakthrough, но без них система остаётся "локально надёжной, глобально дырявой". Реализовывать в порядке убывания риска.

### 8.1 Нет CI enforcement — только opt-in local hook

**Риск:** `.pre-commit-config.yaml` активен только если разработчик вручную сделал `pre-commit install`. У коллеги/CI этого нет — gate молча пропускает регрессии в shared branches. Это **принципиальная дыра** в "repository-level invariant".

**Fix:** добавить GitHub Actions workflow (или аналог) `.github/workflows/kilo_budget_gate.yml`:

```yaml
name: kilo-budget-gate
on:
  pull_request:
    paths:
      - 'doc/team_workflow/**'
      - 'fixtures/kilo_injection_*.json'
      - 'scripts/_kilo_guard.py'
      - 'scripts/kilo_budget_*.py'
      - 'scripts/kilo_injection_calibrate.py'
      - 'CLAUDE.md'
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 2 }  # need HEAD + PR tip
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: python scripts/kilo_budget_gate.py --dry-run --json > gate_report.json
      - run: python scripts/kilo_budget_simulate.py simulate --launcher doc/team_workflow/generate_orchestration_prompt.md --injection fixtures/kilo_injection_baseline.json --fail-on soft_block
      - uses: actions/upload-artifact@v4
        with: { name: budget-gate-report, path: gate_report.json }
```

Перед созданием проверить `ls .github/workflows/` — если CI уже есть, встроить хук в существующий job.

### 8.2 Privacy risk: `discover_sources()` коммитит содержимое memory в fixture

`scripts/kilo_injection_calibrate.py` читает `C:\Users\<user>\.claude\projects\.../memory/*.md` и **вшивает текст** в `kilo_injection_calibrated.json`. Если calibrated fixture коммитится в git, персональные memory пользователя утекают в репо.

**Fix (выбрать один):**

- **Вариант A (безопасный default):** заменить реальный текст memory на hash + char count в calibrated fixture. Payload shape сохраняется, приватность — тоже.
- **Вариант B (явный opt-in):** добавить `--embed-memory-content` флаг, по умолчанию вшивать placeholder `<memory redacted, {chars} chars>`. Настоящий текст попадает в fixture только с явным флагом.
- **Вариант C (минимум):** в `.gitignore` добавить `fixtures/kilo_injection_calibrated.json` — калибровать локально, не коммитить. Тогда baseline остаётся единственным коммитимым fixture.

**Рекомендация:** C как immediate fix + A как долгосрочное.

### 8.3 Performance section-attribute на больших launcher'ах

Если launcher имеет 25+ секций и `body_chars~80k`, leave-one-out = 25 payload rebuilds × JSON serialize 80k × regex risk-scan. На слабой машине — 3–6 сек. Это медленнее pre-commit target'а (<500ms).

**Fix:** в `cmd_simulate` установить soft limit: если `len(sections) > 15`, печатать warning и ограничивать top-15 секций по размеру до attribution. В pre-commit gate `--section-attribute` не вызывается (это только для `simulate` subcommand), так что на сам gate это не влияет — но пользователь, следующий совету из gate error message, может удивиться.

### 8.4 Daily reports: отсутствует schema version + fragile trend parsing

`scripts/kilo_budget_daily.py::format_trend` читает старые JSON-файлы и ожидает `analyses.baseline_gate.launchers[*].body_chars`. Как только Step 3 переименует `baseline_gate` → `committed_fixture_gate`, старые отчёты станут невидимы для trend — тихо.

**Fix:**

1. В `run_check()` добавить `"schema_version": 2` в root отчёта.
2. В `_previous_reports()` — graceful fallback: если `schema_version < 2` или отсутствует, пробовать старые ключи (`baseline_gate`); иначе новые.
3. Опционально: миграционный скрипт `scripts/migrate_budget_reports.py`, разовый, переименовывает ключи в старых JSON-файлах.

### 8.5 Нет operational runbook для обновления captured fixture

Нигде end-to-end не описано: как человек реально обновляет `fixtures/kilo_injection_captured.json`. Docs упоминают probe + capture по частям, но процесс рассыпан. Новый член команды не поймёт, что именно делать.

**Fix:** добавить `doc/kilo_budget_capture_runbook.md` (~50 строк):

```markdown
# Capturing a real Kilo injection fixture

Step-by-step to refresh `fixtures/kilo_injection_captured.json` from a live Kilo session.

1. Start relay: `python scripts/kilo_proxy_relay.py`
2. Point Kilo at the relay endpoint (see relay README)
3. Open a **fresh Kilo session** (no prior context)
4. Send probe marker: `orch_launcher_capture_probe_YYYYMMDD`
5. Stop relay (Ctrl+C). JSONL is at `logs/kilo_relay.jsonl`
6. Capture: `python scripts/kilo_budget_simulate.py capture --from-jsonl logs/kilo_relay.jsonl --probe orch_launcher_capture_probe_YYYYMMDD -o fixtures/kilo_injection_captured.json`
7. Diff vs previous capture: `git diff fixtures/kilo_injection_captured.json`
8. Verify gate: `python scripts/kilo_budget_gate.py --dry-run` — fixture_source должен показать captured
9. Commit: `git add fixtures/kilo_injection_captured.json && git commit -m "chore: refresh captured injection fixture"`

## How often

- After any change in `CLAUDE.md`, `memory/*`, or Kilo settings
- Monthly as routine sanity check
- When `kilo_budget_daily.py` shows persistent divergence between committed_fixture_gate and calibrated_estimate
```

### 8.6 Override без audit trail

`KILO_BUDGET_GATE=skip` логируется только в stdout текущего commit'а. Никакого journal нет. Если кто-то commit'ит с override и регрессией — через неделю никто не вспомнит.

**Fix (минимальный):** при срабатывании override писать строку в `logs/budget_gate_overrides.log`:

```python
# в main(), перед return 0 в skip-branch:
if override:
    log_path = ROOT / "logs" / "budget_gate_overrides.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        user = subprocess.check_output(["git", "config", "user.email"], text=True).strip()
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()[:10]
        f.write(f"{datetime.now(timezone.utc).isoformat()}\t{user}\t{head}\tKILO_BUDGET_GATE=skip\n")
```

`logs/` уже должен быть в `.gitignore` (проверить). Если нет — либо добавить, либо коммитить журнал (team decision).

### 8.7 Нет теста на fixture self-trigger в `.pre-commit-config.yaml`

`files:` regex в hook'е — простая строка. Если кто-то переименует `kilo_budget_daily.py` → `kilo_health.py`, pattern не обновится, и регрессия в переименованном файле пройдёт мимо.

**Fix:** `tests/test_pre_commit_config.py` — parser + invariant checks:

```python
import re
from pathlib import Path
import yaml  # may need to add to dev deps; fallback to manual parse

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES_IN_TRIGGER = [
    "scripts/_kilo_guard.py",
    "scripts/kilo_budget_gate.py",
    "scripts/kilo_budget_simulate.py",
    "scripts/kilo_proxy_relay.py",
    "scripts/kilo_budget_daily.py",
    "scripts/kilo_injection_calibrate.py",
    "fixtures/kilo_injection_baseline.json",
    "CLAUDE.md",
]


def test_pre_commit_hook_covers_all_budget_sensitive_files():
    cfg_text = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    cfg = yaml.safe_load(cfg_text)
    hook = next(h for r in cfg["repos"] for h in r["hooks"] if h["id"] == "kilo-budget-gate")
    pattern = re.compile(hook["files"])
    for path in REQUIRED_FILES_IN_TRIGGER:
        assert pattern.search(path), f"Hook regex does not cover {path}"
```

Тест ломается сразу как только кто-то переименует файл или забудет обновить pattern.

### 8.8 Bonus: healthcheck команда для onboarding

Новый член команды запускает репо и хочет одной командой понять "всё ли в порядке с budget-системой". Сейчас такой команды нет.

**Nice-to-have:** `python scripts/kilo_budget_daily.py --selftest` — запускает:
1. `preflight()` из gate
2. smoke всех трёх CLI
3. pytest subset `tests/test_kilo_*` с `--timeout 30`
4. печатает финальную зелёную/красную сводку

Не обязательно в Wave 4, но мощно для DX.

---

## 9. Итоговый executive summary для handoff

Если следующий агент/человек прочитает только один абзац:

> Kilo budget stack работает на 70%. Критический рантайм-баг в `kilo_budget_daily.py` (строка 75) ломает всю ежедневную проверку — fix в одной строке. Semantic debt: committed fixture называется "baseline", но фактически calibrated estimate; attribution обещан section-level, а реализован message-level; CI enforcement отсутствует (только локальный opt-in hook). Wave 4 закрывает 8 commit'ов в фиксированном порядке (см. § 5). Breakthrough считается достигнутым, когда: (1) pytest зелёный весь kilo-стек, (2) три CLI-smoke не падают, (3) grep не находит drift'а terminology, (4) есть хоть один captured fixture в репо ИЛИ в docs явно документировано "captured недоступен, система — indicative". Без этих четырёх — система остаётся "диагностической", не "preventive".
