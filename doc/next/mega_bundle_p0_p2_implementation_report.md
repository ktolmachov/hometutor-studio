# Отчёт: Mega Bundle P0–P2 (реализация)

**Дата:** 2026-07-18  
**План:** `doc/next/mega_bundle_catalog_plan.md` (v1.2)  
**Runtime-репозиторий:** `hometutor`  
**Статус:** волны P0-1 → P0-2a → P1 → P0-2b → P2 закрыты unit/arch checks  
**Коммиты агентом:** не создавались (работа uncommitted / частично в 312 — сверять `git status`)

---

## Цель

Продолжить план «Один город без адресов» / mega bundle catalog: границы курсов, честные этажи, библиотека области, адреса «курс · урок», расписание и линии курсов в зале.

---

## Итог по волнам

| Волна | Название | Статус |
|--------|-----------|--------|
| **P0-1** | Курс — гражданин графа (compiler floors/boundaries) | ✅ |
| **P0-2a** | Библиотека области (thin) + shared read-model | ✅ |
| **P1** | Пересадки + адреса + `catalog.list` | ✅ |
| **P0-2b** | Расписание области (3 сегмента) | ✅ |
| **P2** | Линии курсов в зале + owner order | ✅ |
| **hotfix** | size budget (`long_functions` 156→155) | ✅ |

Рекомендованный порядок плана выполнен **целиком**.

---

## P0-1 — Compiler: границы курсов и lesson floors

**Проблема:** md+txt = два lesson-id; `precedes` шёл сквозь top-folder; `living-konspekt` попадал в лестницу.

**Решение (source of truth = compiler):**

- группировка `(top_folder, stem без расширения)` → один lesson-node;
- canonical id без `-md`/`-txt`;
- `precedes` только внутри top-folder;
- явный exclude `living-konspekt/` (`NON_CURRICULUM_TOP_FOLDERS`);
- `documents`/`related_documents` содержат оба path; поле `course` на lesson-node.

**Файлы (runtime):**

- `app/course_graph_compiler.py`
- `tests/test_course_graph_compiler_lessons.py`

**Инварианты unit:** 2 курса × dual-format + living-konspekt → число lesson = число уроков; 0 cross-folder `precedes`; living не в ladder.

---

## P0-2a — Thin «Библиотека» + read-model

**Проблема:** нельзя обойти все курсы/конспекты без смены active scope.

**Решение:**

- pure API: `list_library_courses` / `list_library_konspekts` / `list_library_sections`;
- UI «Библиотека»: browse **без** мутации scope;
- «Сделать активным» — только явная кнопка;
- «Спросить» → prefill `folder_rel` + «Быстрый ответ».

**Файлы (runtime):**

- `app/library_catalog_read.py`
- `app/ui/library_catalog.py` (+ wiring: constants, feature_registry, main, fragments)
- `tests/test_library_catalog_read.py`
- `tests/test_navigation_visibility.py` (вид «Библиотека» в study-nav)

---

## P1 — Адреса, badge, агент `catalog.list`

**Проблема:** shared themes невидимы; day_route без «курс · урок»; агент не ходит по FS-каталогу.

**Решение:**

1. `app/concept_address.py` — pure address + badge «в N курсах» (`part_of`→lesson, fallback path);
2. `build_kg_payload` — поля `address`, `courses_badge` на nodes;
3. 2D / 3D / Keeper stops — адрес на карточке и в stop dock; multi-course chips;
4. `catalog.list` — agent tool на том же read-model, что P0-2a;
5. golden-кейс «найди раздел … в Deep».

**Файлы (runtime):**

- `app/concept_address.py`
- `app/agent/tools_catalog.py` (+ registry)
- `app/ui/knowledge_graph_d3.py`, `dashboards_graph.py`, `mnemo_keeper_views.py`, `kg_3d_template.html`
- `app/adaptive_plan_step_text.py` (приоритет `address`)
- `eval_data/agent_scenarios_golden_v1.json`
- `tests/test_concept_address.py`, `tests/agent/test_tools_catalog.py`, registry/golden updates

**Hotfix size budget:** `_catalog_list_handler` разбит на helpers ≤80 строк → `long_functions=155`.

---

## P0-2b — Расписание области

**Проблема:** thin catalog есть, но нет одной поверхности «каталог · пересадки · маршрут».

**Решение:**

- сегменты **Каталог | Пересадки | Маршрут** (radio / keyboard);
- summary «Вся область» (counts из индекса/графа, без хардкода 82/8);
- плитки: quant → адрес → имя → status (текстом) → chips → CTA;
- поиск скрывает неподходящие плитки; empty state в каждом сегменте;
- pin ★; CTA: Спросить / В граф / Активным.

**Файлы (runtime):**

- `app/library_schedule_read.py`
- `app/ui/library_schedule.py`
- `app/ui/library_catalog.py` — entry → schedule shell; body каталога = `render_library_catalog_body`
- `tests/test_library_schedule_read.py`

---

## P2 — Линии курсов + owner order

**Проблема:** курсы слабо различимы в зале; порядок «Deep после base» только в голове владельца.

**Решение (presentation-only):**

- `app/course_lanes.py` — палитра, `course_lane` / `lane_color` / `is_transfer`;
- owner order (`course_owner_order`) меняет **только** lane/recommend, **не** `precedes`;
- 3D local|all: tint узлов по курсу, gold ring на multi-course, tint edges same/cross course;
- Z-bias по lane; Y floors / precedes не трогаются;
- adaptive: `transfer_hint` («пересадка в …») как recommend.

**Файлы (runtime):**

- `app/course_lanes.py`
- `app/ui/knowledge_graph_d3.py` (`course_lanes` в payload, export enrich)
- `app/ui/assets/kg_3d_template.html`
- `app/adaptive_plan_step_text.py`
- `tests/test_course_lanes.py` + design contract asserts

**Kill switches соблюдены:** нет фейкового cross-course `precedes`, нет второго графа/storage, нет LLM для порядка.

---

## Тесты (целевые, по ходу волн)

| Зона | Результат (типичный прогон) |
|------|-----------------------------|
| Compiler lessons + evidence | pass |
| Library catalog read + nav/registry | pass |
| Concept address + catalog.list + golden + tool registry | pass |
| Library schedule | pass |
| Course lanes + 3d design contract | pass |
| Architecture guards / size budget | **155 long_functions**, large_files=33 |

Полный suite не входил в обязательный DoD каждой волны; targeted + arch guards — зелёные.

---

## Изменённые / новые файлы (сводка, runtime)

### Новые модули / тесты

- `app/library_catalog_read.py`
- `app/concept_address.py`
- `app/agent/tools_catalog.py`
- `app/library_schedule_read.py`
- `app/ui/library_schedule.py`
- `app/course_lanes.py`
- `tests/test_course_graph_compiler_lessons.py`
- `tests/test_library_catalog_read.py`
- `tests/test_concept_address.py`
- `tests/agent/test_tools_catalog.py`
- `tests/test_library_schedule_read.py`
- `tests/test_course_lanes.py`

### Ключевые правки

- `app/course_graph_compiler.py`
- `app/ui/library_catalog.py`, `constants.py`, `feature_registry.py`, `fragments.py`, `main.py`
- `app/ui/knowledge_graph_d3.py`, `assets/kg_3d_template.html`, `dashboards_graph.py`, `mnemo_keeper_views.py`
- `app/agent/tool_registry.py`, `eval_data/agent_scenarios_golden_v1.json`
- `app/adaptive_plan_step_text.py`
- `tests/test_navigation_visibility.py`, `tests/agent/test_tool_registry.py`, `tests/test_knowledge_graph_counters.py`

> Часть P0–P1 могла уже попасть в commit `312` (`e77133902` и новее); uncommitted остаток сверять `git status` в `hometutor`.

---

## Что не делали (kill switches плана)

- второй mega-graph / своё storage каталога;
- LLM для порядка курсов/уроков;
- multi-scope OR retrieval;
- «починить только UI floors» без compiler;
- re-open vision W4 как metro map;
- `git commit` / `push` без явного запроса владельца;
- правки `backlog_registry.yaml` (только кандидаты / studio process — вне scope).

---

## Manual DoD (опционально у владельца)

1. **Rebuild графа** на эталоне → ~6 lesson floors, 0 cross-folder `precedes`, без living-konspekt в ladder.
2. **UI «Библиотека»** → сегменты Каталог / Пересадки / Маршрут; оба курса без смены scope.
3. **Export 3D** → ≥2 course tints + ≥1 transfer highlight; адреса stop = «курс · урок».

---

## Рекомендуемые следующие шаги

1. Закоммитить uncommitted в `hometutor` (P0-2b + P2 + size-budget fix), если 312 ещё не покрыл всё.
2. Live rebuild + smoke 3D export на эталоне.
3. Опциональный polish: UI для `course_owner_order` (явный pin порядка курсов в Библиотеке).
4. Промоут backlog в studio — только решением владельца.

---

## Вердикт

Реализован **полный valuable slice** mega-bundle плана: от честного compiler до hall-линий курсов. North star «у каждого шага есть адрес» закрыт на fixture-уровне (address helper + day_route/schedule/export). Рабочее состояние после каждой волны сохранялось targeted-тестами.

**Копия отчёта в runtime:** `hometutor/docs/mega_bundle_p0_p2_implementation_report.md`
