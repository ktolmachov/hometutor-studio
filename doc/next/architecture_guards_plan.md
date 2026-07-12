# Architecture Guards — Law Into The Loop Plan

**Дата:** 2026-07-12 · **База проверки:** hometutor HEAD `f21c1db38` «206»
**Источник:** эволюционный разбор №12 «Дом с образцовыми стенами и выключенной сигнализацией»
(`../presentations/evolutionary_analyses/12_architecture_design.html`,
артефакт https://claude.ai/code/artifact/9f7eb364-7814-4be5-8d3e-bb120e6d4c7e)

Этот план — runtime-handoff для `D:\Projects\hometutor`. Перед кодом сверить
фактический runtime-код: detail-планы серии могут отставать от HEAD.

## Контекст: диагноз разбора №12

Стены каркаса образцовые — греп-аудит на HEAD 206 не нашёл ни одного нарушения
границ (config/provider/user_state/guardrails/ui_client, streamlit вне `app/ui`,
bare except). Но из трёх видов закона (pytest+ruff в CI, стражи `scripts/check_*`,
проза CLAUDE.md/conventions) к ежедневному циклу подключён только первый.
Следствие, проверенное запуском: `python scripts/arch_regression_guards.py`
**падает** — size budget нарушен по всем четырём метрикам (large_files 33>24,
long_functions 153>138, peak_file 1928>1651, peak_function 361>338), дрейф
копился 177 коммитов с 2026-06-25 (`a64afb821` «29») незамеченным, потому что
стражей никто не вызывает: греп по `tests/`, `.github/`, `scripts/*.ps1` — 0.

Порождающая причина болезни серии «одна истина в нескольких копиях»:
**всё, что не выражено живым тестом, стареет молча** — стражи, бюджеты, проза.

**Не входит в план:** большой рефакторинг каркаса, новые механизмы контроля
(pre-commit-инфраструктура, дашборды качества), дробление `app/prompts/_impl.py`
(депо текста — вердикт «не дробить», оформляется waiver'ом).

---

## wave-arch-law-power (P0 — два хода, один коммит или A2 → A1)

### A2. Сверить закон с реальностью (делается ПЕРВЫМ)

- **Problem:** бюджеты стража — снимок 2026-06-25, сам страж хранит копию истины,
  которая устарела. Если подключить его как есть (A1), CI станет вечно-красным —
  и стражей выключат второй раз, теперь осознанно.
- **Evidence:** `scripts/check_size_budget.py:15-18` —
  `MAX_LARGE_FILES=24 / MAX_LONG_FUNCTIONS=138 / MAX_FILE_LINES=1651 /
  MAX_FUNCTION_LINES=338`; факт HEAD 206 — 33 / 153 / 1928 / 361.
  Пики: `app/prompts/_impl.py` (1928 строк, депо текста, 20 def на файл),
  `app/ui/topics_tab_plan_subtab.py:22` `render_topics_plan_subtab` (361),
  `app/user_state_db.py:322` `_ensure_schema` (353, декларативный DDL).
- **Proposed:** (1) обновить константы до факта HEAD 206 с комментарием-датой
  «признанный долг, no-growth»; (2) добавить явный waiver-словарь
  `{путь: причина}` для файлов-исключений из file-line-лимита: `_impl.py`
  (правило «промпт живёт в одном месте» важнее лимита строк) — и, при желании
  владельца, function-waiver для `_ensure_schema` (DDL). Waiver — константа в
  том же скрипте, не новый механизм.
- **Files:** `scripts/check_size_budget.py`.
- **DoD:** `python scripts/arch_regression_guards.py` → exit 0 на HEAD;
  комментарии объясняют, откуда числа и почему waiver.

### A1. Подключить сигнализацию к pytest

- **Problem:** четыре стража написаны и работают, но не подключены ни к чему,
  что бежит ежедневно. Единственный живой закон — `pytest tests/ -q` в CI
  (`.github/workflows/ci.yml:31-32`).
- **Evidence:** `scripts/arch_regression_guards.py:13` — кортеж GUARDS из
  четырёх модулей (`check_config_access`, `check_dead_modules`,
  `check_requirements_imports`, `check_size_budget`), каждый экспортирует
  `main() -> int`; вызывающих — ноль.
- **Proposed:** новый `tests/test_architecture_guards.py`: параметризованный
  тест по четырём модулям — вставить repo root в `sys.path` (как это уже
  делает `arch_regression_guards.py:9-11`), `importlib.import_module(...)`,
  `assert module.main() == 0`. Никакого нового механизма: тест — это провод.
- **Files:** `tests/test_architecture_guards.py` (новый).
- **Tests:** сам файл; локальная проверка «сигнализация кричит»: временно
  внести нарушение (например, `os.getenv` в сервис) → тест красный → откатить.
- **DoD:** `pytest tests/test_architecture_guards.py -q` зелёный на HEAD после
  A2; полный CI зелёный; тест работает и из корня, и из CI (ubuntu) — пути
  через `Path(__file__).resolve().parents[1]`, не cwd.
- **Doc-sync:** `docs/conventions_architecture.md` (§Конфигурация уже ссылается
  на guard — дописать «стражи запускаются в CI через
  tests/test_architecture_guards.py»); CLAUDE.md §Test Selection — добавить
  строку про guard-тест в бандл «Guardrails / pipeline invariants».

## wave-arch-prose-honesty (P1)

- **B1. Числа покидают прозу.** CLAUDE.md §«Known Large Areas» и conventions
  не хранят счётчики (модулей/тестов/бюджетов) — вместо точных чисел порядок
  величины + ссылка на стражей и `docs/architecture.md`. Координация: правка
  текущих цифр уже запущена отдельной сессией 2026-07-12 (задача «Обновить
  устаревшие цифры в CLAUDE.md») — B1 идёт поверх неё и убирает саму привычку.
- **B2. Вендорить шрифты.** `app/ui_theme.css:1-2` — последний CDN-остров
  (fonts.googleapis.com, Manrope/Plex Mono/Material Symbols). НЕ новый кандидат:
  это C2 плана №9 (`color_worlds_theming_plan.md`), образец —
  `_load_d3_source()` / `_load_mermaid_source()` (вендор + честный fallback).
  Здесь только повышение приоритета: разбор №12 показал, что паттерн
  «сеть — всегда fallback» уже изобретён трижды и достоин статуса правила
  каркаса (одна строка в conventions_architecture.md).
- **B3. Правило отщепления панелей.** В conventions: при касании UI-функции
  >300 строк — выделять панель-модуль (образцы: `living_konspekt_*_panel.py`).
  Кампании рефакторинга нет; бюджет (после A1) автоматически следит за
  no-growth. Четыре текущих гиганта: `render_topics_plan_subtab` 361,
  `_render_learning_progress_tab` 314 (`dashboards_progress.py:160`),
  `build_interactive_card_html` 311, `render_query_answer_section` 271.

## wave-arch-living-map (P2)

- **C1. BLE001 с baseline — или честное удаление обещания.** CLAUDE.md требует
  `# noqa: BLE001`, но ruff в CI выбирает только E и F (`pyproject.toml:98`):
  правило-проза без исполняемого двойника. Либо включить `BLE` в select с
  baseline/per-file-ignores для существующего кода, либо убрать обещание из
  CLAUDE.md. Needs discovery: объём существующих broad except.
- **C2. Живая карта в цикле.** `scripts/generate_diagrams.py` уже генерирует
  `docs/diagrams.md` (последний прогон 2026-07-10, вручную). Кандидат: guard
  или CI-шаг, падающий при рассинхроне диаграмм с кодом; плюс fan-in снапшот
  (top-15 несущих модулей) в тот же автоген. Needs discovery: детерминизм
  вывода generate_diagrams (иначе diff-check будет флапать).

---

**Рекомендованный порядок:** A2 → A1 (можно одним коммитом) → B1 → B3 → B2 → C1 → C2.

**Kill switch:** если для P0 понадобился новый механизм (фреймворк, pre-commit,
дашборд, хранилище) — стоп: стражи написаны, весь ход — один провод. Если после
A2 стражи всё ещё красные — сверка сделана неправильно, не поднимать бюджеты
вслепую второй раз.

**North star:** ни одно нарушение каркаса не живёт дольше одного коммита.
Вторичная: медиана файлов на коммит (сейчас 5, n=60) не растёт при росте кода.

Это кандидаты, НЕ записи `backlog_registry.yaml` — промоут решением владельца.
