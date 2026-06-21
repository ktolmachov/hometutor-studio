# Kilo Budget Health Check — Daily-Use Prompt

> Вставь этот промпт в начало сессии когда хочешь проверить бюджет
> или перед стартом работы с тяжёлым workflow.

---

## Быстрая проверка (< 3 секунды, всё локально)

```bash
python scripts/kilo_budget_daily.py
```

По умолчанию это read-only проверка по committed fixture.
Если нужен локальный estimate, запускай отдельно:

```bash
python scripts/kilo_budget_daily.py --use-calibrated-estimate
```

**Читай результат так:**

| Строка в выводе | Что делать |
|---|---|
| `STATUS: OK` | Работай спокойно |
| `CAUTION — margin N chars` | Тесный запас до `warn`; сначала подрежь launcher или memory |
| `SOFT_BLOCK / HARD_BLOCK` | Стоп. Запусти attribution и найди причину |
| `REGRESSION DETECTED` | Последний коммит сломал бюджет — откати или исправь |

---

## Стандартный утренний ритуал (2 команды)

```bash
# 1. Read-only baseline check + сохранить отчёт в logs/budget_reports/
python scripts/kilo_budget_daily.py

# 2. При необходимости добавить локальную calibrated estimate
python scripts/kilo_budget_daily.py --use-calibrated-estimate

# 3. Посмотреть тренд за 7 дней
python scripts/kilo_budget_daily.py --trend 7
```

---

## Если что-то не так — глубокая диагностика

**Шаг 1. Какой launcher виноват?**
```bash
python scripts/kilo_budget_gate.py --dry-run
```
→ Смотри колонку `->warn`. Меньше +7k — опасная зона.

**Шаг 2. Что именно съедает бюджет?**
```bash
python scripts/kilo_budget_simulate.py simulate \
  --launcher doc/team_workflow/generate_plan_next_prompt.md \
  --injection fixtures/kilo_injection_baseline.json \
  --attribute --section-attribute
```
→ Message-level + section-level attribution: сначала дорогой message/block, затем дорогая секция launcher.

**Шаг 3. Что занимает место в injection?**
```bash
python scripts/kilo_injection_calibrate.py --dry-run --show-sources
```
→ Самые тяжёлые источники — кандидаты на trim.

---

## Текущие margins (актуально для последнего сохранённого режима расчёта)

| Launcher | Body chars | Gap to warn |
|---|---|---|
| orch | ~55k | ~14k |
| planning | ~62k | ~7k ← тесный |
| resume | ~61k | ~9k |
| execution_auto | ~59k | ~10k |

> `committed_fixture_gate` показывает committed fixture, который использует реальный pre-commit gate.
> `calibrated_estimate` — локальная оценка, а не точный runtime capture.
> `planning` обычно самый тесный. Каждый новый раздел launcher'а стоит дорого.

---

## Когда делать полную перекалибровку

Запускай `kilo_injection_calibrate.py` вручную когда:

- Добавил/удалил memory файл
- Обновил CLAUDE.md существенно (>500 chars)
- Обновился Kilo (новый системный промпт → запусти v1 probe и capture)
- `kilo_budget_daily.py` показывает неожиданный скачок injection

```bash
python scripts/kilo_injection_calibrate.py
```

---

## Экстренный override (если надо commit прямо сейчас)

```bash
KILO_BUDGET_GATE=skip git commit -m "your message"
```

> Логируется. Потом обязательно пройди диагностику.

---

## Быстрый reference команд

```bash
# Ежедневная проверка
python scripts/kilo_budget_daily.py

# Тренд N дней
python scripts/kilo_budget_daily.py --trend 7

# Gate (HEAD vs working tree)
python scripts/kilo_budget_gate.py --dry-run

# Simulate конкретный launcher
python scripts/kilo_budget_simulate.py simulate \
  --launcher <path> --injection fixtures/kilo_injection_baseline.json \
  --fail-on warn

# Attribution (найти корень проблемы)
python scripts/kilo_budget_simulate.py simulate \
  --launcher <path> --injection fixtures/kilo_injection_baseline.json \
  --attribute --section-attribute

# Перекалибровать fixture
python scripts/kilo_injection_calibrate.py

# Захватить captured fixture из relay (после v1 probe)
python scripts/kilo_budget_simulate.py capture \
  --from-jsonl logs/kilo_relay.jsonl \
  -o fixtures/kilo_injection_captured.json

# V1 probe (для получения реального relay лога)
python scripts/kilo_budget_probe.py prepare --port 8791 --guard-mode block
# → запустить probe sessions в Kilo → потом:
python scripts/kilo_budget_probe.py analyze
```
