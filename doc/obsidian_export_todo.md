# Obsidian Export — оставшиеся задачи

**Обновлено:** 2026-06-08 (сессия 3)

**Next-level план:** [`doc/next/smart_notes_killer_feature_plan.md`](next/smart_notes_killer_feature_plan.md) — актуальный путь “умный конспект”: готовый `.md` как документ корпуса в `data/`, локальная SmartKonspekt-генерация как offline/no-cloud fallback, интеграция с learning loop через обычный ingest/RAG.

**Контекст:** `app/obsidian_export.py` — map→reduce→compose конвертация txt-лекций в Obsidian-ready Markdown.  
Vault/output: `data/` (Obsidian vault root: `data/.obsidian/`; конспект индексируется как документ корпуса).  
LLM: `app.provider.get_obsidian_export_llm()` (OBSIDIAN_EXPORT_MODEL → LLM_MODEL / qwen3.6-27b через LM Studio), таймаут 600s, max_tokens compose=4096.  
Targeted tests: `tests/test_obsidian_export.py`, `tests/test_ingestion_konspekt.py`, `tests/test_smart_konspekt.py` — зелёные.

---

## ✅ Сделано

- `app/obsidian_export.py` — полный pipeline map→reduce→compose
- `app/config.py` — все настройки: `obsidian_export_*`, `obsidian_vault_name`, `obsidian_vault_subdir`
- `config.env` — `OBSIDIAN_VAULT_NAME=data`, `OBSIDIAN_VAULT_SUBDIR=data`
- Timeout fix: `timeout=timeout_sec` в конструкторе LlamaIndex `OpenAI()` — иначе дефолт 60s перебивал httpx.Client(600s)
- `obsidian://open?vault=data&file=...` URI работает корректно
- UI: кнопка конвертации, inline-просмотр, статус-бейдж, батч курса, индикатор в KG-графе
- **Проверка от 2026-06-06:** полный прогон `урок 2 Как агент думает и дейс.txt` завершился успешно (836s, 134 строки, 15 KB)
- **Ошибка в UI** — `_render_obsidian_export_button` и `_render_obsidian_batch_button` показывают `❌` с текстом исключения, прогресс-бар сбрасывается в 0

### Реальная статистика конвертации (урок 2, 157 922 байт)

| Фаза | Шагов | Время |
|---|---|---|
| map | 16 | 0–314s (~20s/чанк) |
| merge level 1 | 7 | 314–547s (~33s/merge) |
| merge level 2 | 6 | 547–740s (~32s/merge) |
| compose | 1 | 740–836s (~60s) |
| **Итого** | **30 LLM-вызовов** | **836s (14 мин)** |

Исторический результат: `doc/конспекты/ИИ Агенты/урок 2 Как агент думает и дейс.md` · 134 строки · 15 023 байт. Актуальный output path после Задачи 0: `data/ИИ Агенты/урок 2 Как агент думает и дейс.md`.

---

## 🚀 Стратегический сдвиг (2026-06-08): konspekt-import как киллер-фича

**Открытие:** облачная модель + `doc/prompts/smart_lecture_konspekt_universal.md` + мультимодальные входы (txt + черновик + HTML + **PDF 318 стр**) даёт конспект кардинально выше локального pipeline.

| | Локальный (урок 2) | Облачный (урок 1) |
|---|---|---|
| Объём | 134 строки / 15 KB | 693 строки / ~30 KB |
| Содержимое | линейное summary | карта + 4 Mermaid + 3 таблицы + примеры + антипаттерны + 20 вопросов + ДЗ + шпаргалка |
| Время | 14 мин / 30 LLM | 2.5 мин |

**Вывод:** основной путь — **импорт готового облачного .md**; локальная генерация — оффлайн-fallback. Phase 1 (HTML-парсер) из killer-плана теряет смысл (облако уже поглощает HTML как вход). Partial Resume (✅ сделано) полезен только для fallback-пути.

---

## ✅ Задача 0: Конспект-как-документ в `data/` — СДЕЛАНО 2026-06-08

**Решение (подтверждено 2026-06-08):** конспект НЕ отдельный артефакт, а **сам документ корпуса**. Облачно-сгенерированный `.md` кладётся в `data/` и заменяет сырой txt в индексе. Сырой транскрипт остаётся архивом в `D:\exchange\` (вход для облака, вне `data/`).

```
D:\exchange\ИИ Агенты\…ts.txt              ← АРХИВ сырья (вне data/, не индексируется)
data\ИИ Агенты\Введение в AI-агентов.md    ← ДОКУМЕНТ корпуса = конспект
```

**Почему так (обосновано кодом `app/ingestion.py`):** ингест сканирует только `DATA_DIR` и строит топик через `relative_to(DATA_DIR)`. Конспект в `doc/конспекты/` вне ингеста → нет узла графа/RAG. Конспект в `data/` индексируется автоматически, чистый RAG-текст вместо ASR-шума, один узел на лекцию.

**Связывание:** не нужно — документ и конспект это один файл. Provenance во frontmatter: `source`, `source_sha256`, `presentation` (трассируемость, из чего сделан).

**Изменения в коде:**
1. `app/ingestion.py`:
   - срезать YAML-frontmatter у `.md` с `type: konspekt` (чтобы sha/теги не шли в эмбеддинги);
   - `_infer_doc_kind`: брать `type`/`tags` из frontmatter (иначе «ИИ Агенты» → `document`, а нужно `lecture`).
2. `app/obsidian_export.py`:
   - целевая папка локального fallback-конспекта: `doc/конспекты/` → **`data/` рядом с источником** (единый путь external/local);
   - (опц.) `import_smart_note(md, *, dest_rel)` — хелпер записи .md в `data/` + пере-штамп `source_sha256`.
3. `config.env`: `OBSIDIAN_VAULT_NAME=data`; добавить `data/.obsidian/` (vault для obsidian://). Код URI (`vault_obsidian_root` ищет `.obsidian/` вверх) уже поддержит.
4. **Реиндекс** после переноса конспектов в `data/` (меняется состав корпуса).

**Просмотр в приложении:** «👁 Читать» уже рендерит .md инлайн; после ингеста конспект — кликабельный узел графа знаний. Obsidian — вторичен, через `vault=data`.

**Текущий ручной workflow пользователя (вне приложения):**
1. Сгенерировать .md в облаке по `doc/prompts/smart_lecture_konspekt_universal_cloud_llm.md`.
2. Положить в `data/<курс>/<имя>.md`.
3. Проверить quality gate:
   ```powershell
   .\.venv\Scripts\python.exe scripts\validate_smart_konspekt.py "data\<курс>\<имя>.md" --expect-source-sha --strict
   .\scripts\validate_course_konspekts.ps1 -Course "<курс>"
   ```
4. Если gate падает — файл считается черновиком: исправить ошибки валидатора или сделать точечный repair-pass, не переписывая весь конспект.
5. Реиндекс → конспект в графе и RAG, читается по 👁.

**Реализовано (2026-06-08):**
- `app/ingestion_sections.py`: `_parse_md_frontmatter()`, `FlatMarkdownReader` (один Document, `_md_flat=True`, frontmatter → `md_*`), защита `_expand_structured_documents` от повторного разреза `.md`.
- `app/ingestion.py`: импорт `FlatMarkdownReader`, `.md: FlatMarkdownReader()` в `file_extractor`, `doc_kind` из frontmatter для `md_type == "konspekt"`.
- **Шаг 4/5 (vault = data):** `vault_root()`/`config` → `data/`; `OBSIDIAN_VAULT_NAME=data`, `OBSIDIAN_VAULT_SUBDIR=data`; создан `data/.obsidian/`. Локальный fallback и облачный путь теперь пишут в один корень.
- `tests/test_ingestion_konspekt.py` (12) + `tests/test_obsidian_export.py` (17) — **зелёные**.
- Реиндекс начисто: `fragments=1` (было 39), `nodes=17`, `doc_kind=lecture` ✅.

**🐞 CRITICAL bug найден и исправлен (2026-06-08):** `md_*` + `_md_flat` метаданные попадали в текст эмбеддинга каждого чанка — `md_source_sha256`+`md_presentation_sha256` = 128 символов хеш-шума × 17 чанков. Сводило на нет смысл срезания frontmatter. **Фикс:** `FlatMarkdownReader` ставит `excluded_embed_metadata_keys` / `excluded_llm_metadata_keys` для всех `md_*`+`_md_flat` (метаданные остаются для фильтров/`doc_kind`, но не эмбеддятся). Верифицировано на реальном Chroma: 0/17 загрязнённых чанков. Тест: `test_flat_markdown_reader_excludes_frontmatter_from_embeddings`.

**⚠️ Известный риск (footgun, не баг кода):** с `vault_root=data/` локальный fallback пишет `.md` рядом с исходным `.txt` в `data/`. Если **и** `.txt`, **и** конспект `.md` лежат в `data/` — двойной ингест (две ноды одной лекции). Модель это исключает (сырой `.txt` → `D:\exchange\`, вне `data/`), но в коде нет защиты. Удаление исходников — prohibited action, оставлено на workflow пользователя.

**Тесты:** `test_ingest_strips_konspekt_frontmatter`, `test_doc_kind_from_frontmatter_type`, `test_local_konspekt_written_to_data_dir`.

---

## ✅ Задача 1: Partial Resume — СДЕЛАНО 2026-06-06

**Проблема:** 30 LLM-вызовов × 14 мин — если compose падает, всё начинается сначала.  
Merge-фаза одна занимает 7 минут. Кэш после reduce сохраняет 13 из 14 минут при повторе.

**Совместимость с Phase 2 (SmartNote):** кэш хранит `consolidated` — текст после reduce. Phase 2 подразумевает двухпроходный процесс (structure extraction + editorial rendering), но reduce-кэш остаётся полезным как вход для первого прохода. Retry пропускает map+reduce. Дизайн кэша не меняется.

**Решение:** после reduce-фазы сохранять `consolidated` в `.notes_cache.yaml` рядом с target:

```
data/ИИ Агенты/урок 2 Как агент думает и дейс.notes_cache.yaml
```

Структура файла:
```yaml
source_sha256: <hex>
consolidated: |
  ### Тема 1
  - тезис...
```

**Изменения в `app/obsidian_export.py`:**

1. Добавить `_notes_cache_path(target_abs: Path) -> Path` — возвращает `target_abs.with_suffix(".notes_cache.yaml")`.
2. Добавить `_load_notes_cache(target_abs, source_hash) -> str | None` — читает YAML, проверяет sha256, возвращает `consolidated` или `None`.
3. Добавить `_save_notes_cache(target_abs, source_hash, consolidated)` — пишет YAML.
4. В `to_obsidian_markdown()` перед map-фазой:
   ```python
   consolidated = _load_notes_cache(target_abs, source_hash)
   if consolidated is None:
       # map → reduce как сейчас
       ...
       consolidated = _reduce_notes(llm, notes, progress, compose_limit)
       _save_notes_cache(target_abs, source_hash, consolidated)
   ```
5. После успешной записи target — удалять `.notes_cache.yaml`.

**Тесты:** добавить 2 теста в `tests/test_obsidian_export.py`:
- `test_notes_cache_skips_map_reduce_on_retry` — первый прогон сохраняет кэш; второй прогон с `force=True` читает кэш, пропускает map/merge, вызывает только compose.
- `test_notes_cache_invalidated_on_source_change` — изменённый источник игнорирует кэш.

**Реализовано:** `_notes_cache_path()`, `_load_notes_cache()`, `_save_notes_cache()`, `_delete_notes_cache()`; `to_obsidian_markdown()` сохраняет reduce-кэш перед compose и удаляет его после успешной записи target.

**Проверка:** `.\.venv\Scripts\python.exe -m pytest tests\test_obsidian_export.py -q --tb=short` — 10 passed.

---

## ✅ Задача 2: Ошибка в UI — СДЕЛАНО 2026-06-06

- `_render_obsidian_export_button`: `progress.progress(0.0, text="Ошибка")` + `st.error(❌ ...)` + `st.caption(подсказка про retry)`
- `_render_obsidian_batch_button`: `doc_progress.progress(0.0, text=f"{doc_label}: ❌ {type(exc).__name__}")` для упавшего документа; итоговый отчёт уже показывал список ошибок

---

## Задача 3: Статистика в UI (приоритет: средний)

**Проблема:** пользователь не видит сколько времени заняло, какой размер вышел.

**Решение:** расширить `ObsidianExportResult` полем `stats`:

```python
@dataclass(frozen=True)
class ExportStats:
    duration_sec: float
    chunks: int          # map-фаз
    merges: int          # merge-фаз (суммарно по уровням)
    input_chars: int     # исходный txt
    output_chars: int    # итоговый .md без frontmatter

@dataclass(frozen=True)
class ObsidianExportResult:
    ...
    stats: ExportStats | None = None
```

**Изменения в `app/obsidian_export.py`:**
- Счётчики `_map_count`, `_merge_count` внутри `to_obsidian_markdown()`.
- `time.perf_counter()` в начале/конце.
- `ExportStats` → `ObsidianExportResult`.

**Изменения в `app/ui/topics_tab_right_column.py`:**
```
✅ Готово за 14m · 30 LLM-вызовов · 154 KB → 15 KB
```

---

## ✅ Задача 5: Локальная умная генерация — `app/smart_konspekt.py` — REAL-RUN ПРОВЕДЁН 2026-06-08

**Статус:** реализован + проверен real-run на LM Studio (`qwen3.6-27b`). Вердикт: **локальный pipeline — валидный offline/no-cloud fallback** (6/6 структурных проверок), но для основного потока облако пока выигрывает (~3× глубина). Детальный источник плана: `C:\Users\Kostya\.claude\plans\clever-sprouting-church.md`; краткое изложение — в `doc/next/smart_notes_killer_feature_plan.md` § Phase 2.

### Real-run результаты (урок 1, 2026-06-08)

Прогон: `generate_konspekt.py "ИИ Агенты/урок 1" --force` (LM Studio, `qwen3.6-27b`).

| Фаза | Шагов | Время |
|---|---|---|
| map | 17 | 0–287s (~17s/чанк) |
| merge (3 уровня: 4+2+1) | 7 | 287–551s |
| compose | 1 | 551–693s |
| **Итого** | **25 LLM-вызовов** | **693s (~11.5 мин)** |

`action=generated` · вход 329 425 симв · выход 11 033 симв · cache=no.

**Eval local vs golden (cloud):**

| Метрика | Local | Golden (cloud) | Разрыв |
|---|---|---|---|
| Строк | 189 | 692 | ×3.7 |
| Символов | 11 033 | 34 661 | ×3.1 |
| Заголовков (`##`) | 16 | 41 | ×2.6 |
| Mermaid | 1 | 4 | ×4 |
| Таблиц | 13 | 29 | ×2.2 |
| Термины / вопросы / шпаргалка | ✅/✅/✅ | ✅/✅/✅ | = |

**Verdict:** `local-ok (6/6 structural checks)`.

**🔬 Эксперимент с max_tokens (прогон 2, 2026-06-08) — не является чистым доказательством:** поднято `OBSIDIAN_EXPORT_COMPOSE_MAX_TOKENS=8192`. Результат: **11 165 chars (+132, +1.2%)** — практически ноль разницы. Однако LM Studio logs показали, что merge-вызовы всё ещё резались на `2048` токенах (`finish_reason=length`) до финального compose. Значит этот прогон доказывает только одно: поднять один compose-cap недостаточно, если reduce/merge уже потерял детали.

| | Прогон 1 (compose 4096) | Прогон 2 (compose 8192, merge dirty) | Прогон 3 (merge fixed, clean-run) |
|---|---|---|---|
| chars | 11 033 | 11 165 | 7 086 |
| lines | 189 | 183 | 109 |
| mermaid | 1 | 1 | 0 |
| tables | 13 | 13 | 0 |
| structural checks | 6/6 | 6/6 | 4/6 |
| compose finish | length likely / output cap | inconclusive | `finish_reason=length`, `truncated=1` |

**🔑 Финальный clean-run вывод:** текущий `map→reduce→single universal compose` не является пригодным quality fallback для локальной `qwen/qwen3.6-27b`.

После merge max_tokens fix compose получил более длинный вход, но упёрся в эффективный total context cap LM Studio/модели: `prompt_tokens=14328`, `completion_tokens=2056`, `total_tokens=16384`, `finish_reason=length`, `truncated=1`. Файл оборвался посреди слова (`Эффективно для мощ`), поэтому результат хуже предыдущих прогонов и непригоден как завершённый конспект.

**📌 Решение:** не повторять тот же single-compose прогон. Возвращаться к исходному контракту Phase 2:
- section-level compose: отдельные вызовы для главной мысли, карты, схем, таблиц, терминов, вопросов, ДЗ, шпаргалки;
- каждый вызов должен получать узкий prompt/input, чтобы оставлять место под 2-4k output tokens;
- итоговая сборка должна валидировать обязательные блоки (`Mermaid`, tables, terms, questions, cheatsheet) и не принимать `finish_reason=length`;
- `smart_konspekt` можно оставить только как experimental baseline / partial code, но не закрывать `smart-notes-native-generation-v1` как done.

### Section-level SmartKonspekt design (следующий implementation slice)

**Цель:** заменить непригодный single-compose на pipeline `map→evidence reduce→outline→per-section compose→validate→assemble`.

**Контракт секций:**
- `main_thesis` — главная мысль + 5-8 тезисов
- `lecture_map` — карта лекции / маршрут
- `key_topics` — подробные темы с examples/callouts
- `architecture_flow` — минимум 1 Mermaid diagram
- `comparison_tables` — минимум 3 таблицы по отличиям/паттернам/рискам
- `examples` — конкретные демо/истории/инструменты из лекции
- `risks_antipatterns` — ошибки, stop conditions, mitigations
- `practical_takeaways` — инженерные выводы
- `glossary` — термины
- `control_questions` — вопросы самопроверки
- `homework` — практическое задание
- `cheatsheet` — мини-шпаргалка

**Validation gates (hard blockers):**
- любой принятый LLM-result с `finish_reason=length` или provider `truncated=1` запрещён;
- если section-call упёрся в length — один retry с меньшим evidence slice или split на child-sections; второй length → stop, final `.md` не писать;
- final assemble не вызывает LLM, только склеивает валидные секции;
- final Markdown должен иметь Mermaid, tables, terms, questions, homework, cheatsheet;
- не принимать незакрытые fences, сломанные таблицы, frontmatter внутри section body, незавершённый хвост.

**Implementation notes:**
- текущая `_complete()` возвращает только text; нужна обёртка результата с `text`, `finish_reason`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `truncated`;
- prompts должны остаться в `app/prompts`;
- LLM construction — только `app.provider.get_obsidian_export_llm()`;
- partial resume должен кэшировать evidence/section drafts, чтобы retry не повторял весь 25-call map/reduce.

> ⚠️ **Eval CLI fix (2026-06-08):** `--golden` с расширением `.md` резолвился от `BASE_DIR`, а не `DATA_DIR` → golden не находился по data-относительному пути. Исправлено в `scripts/eval_konspekt.py:_resolve_target` (для relative `.md` сначала пробуем `DATA_DIR`, потом fallback `BASE_DIR`).

**Суть:** staged local pipeline (map→reduce→compose с универсальным промптом) для оффлайн/no-cloud генерации конспекта. Входы из `materials/<курс>/<лекция>/` (txt + md + html + pdf), выход в `data/<курс>/<лекция>.md`.

**Deliverables:**
- ✅ `app/smart_konspekt.py` — `gather_lecture_inputs`, `generate_smart_konspekt`, `SmartKonspektResult`
- ✅ `app/config.py`: `obsidian_export_prompt_path`, `obsidian_export_materials_dir`, бюджетные поля (`smart_konspekt_transcript_budget` и др.)
- ✅ `scripts/generate_konspekt.py` — CLI (аргумент: `<курс>/<лекция>` или путь)
- ✅ `scripts/eval_konspekt.py` — структурный чек-лист + сравнение local vs cloud
- ✅ `tests/test_smart_konspekt.py` — focused tests with mock LLM
- ✅ prompt boundary: universal prompt загружается через `app.prompts.get_smart_lecture_konspekt_universal_prompt`; map/merge/compose prompt constants вынесены в `app/prompts`
- ✅ provider boundary: `app.provider.get_obsidian_export_llm()`
- ✅ real-run quality verdict — **3 прогона проведены** (см. таблицу выше); single-compose подход признан непригодным; нужен section-level compose

**Папка исходников:**
```
materials/<курс>/<лекция>/
   ├── *.txt   → транскрипт (map→reduce)
   ├── *.md    → черновой конспект (в compose как есть)
   ├── *.html  → HTML-конспект (strip тегов → текст)
   └── *.pdf   → презентация (extract текст)
data/<курс>/<лекция>.md   → выход (type: konspekt)
```

**Тесты (DoD):**
```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_smart_konspekt.py tests\test_obsidian_export.py tests\test_ingestion_konspekt.py -q --tb=short
```

**Verification (с LM Studio):**
```powershell
.\.venv\Scripts\python.exe scripts/generate_konspekt.py "ИИ Агенты/урок 1" --force
.\.venv\Scripts\python.exe scripts/eval_konspekt.py "ИИ Агенты/урок 1" --golden "ИИ Агенты/урок 1 Введение в концепцию AI-агентов.md"
.\.venv\Scripts\python.exe scripts/validate_smart_konspekt.py "data\ИИ Агенты\урок 1 Введение в концепцию AI-агентов.md" --expect-source-sha --strict
.\scripts\validate_course_konspekts.ps1 -Course "ИИ Агенты"
```

---

## Задача 4: Wikilinks (приоритет: низкий)

**Цель:** в compose-конспекте расставлять `[[название другой лекции]]` для связей.

**Реализация (только через prompt boundary):**
- Перед compose: `existing = [p.stem for p in vault_root().rglob("*.md") if p.name != "README.md"]`
- Добавить инструкцию в Obsidian compose prompt constant в `app/prompts/_impl.py`, не хардкодить в сервисе:
  ```
  Если упоминаешь тему из списка ниже — оформляй как [[название]]:
  {existing_titles}
  ```
- Если список пуст — не добавлять секцию в промпт.

---

## Порядок реализации (пересмотрен 2026-06-08)

1. ~~**Задача 0 — Импорт внешнего .md конспекта**~~ — ✅ сделано (ingestion: flat reader + doc_kind)
2. ~~**Partial Resume**~~ — ✅ сделано (ценно только для локального fallback)
3. ~~**Ошибка в UI**~~ — ✅ сделано
4. ~~**Задача 5 — Локальная умная генерация (`app/smart_konspekt.py`)**~~ — ✅ первый срез, mock-tested
5. **Real-run eval Задачи 5** — LM Studio + `scripts/eval_konspekt.py`, решить “стоит ли локально”
6. **Статистика UI для legacy Obsidian export** — данные уже есть, нужно только вывести
7. **Wikilinks** — после накопления нескольких конспектов; prompt changes only through `app/prompts`

---

## Быстрая проверка готовности (начало новой сессии)

```bash
# 1. Проверить vault-пути (после Задачи 0: vault = data/)
.\.venv\Scripts\python.exe -c "from app.obsidian_export import vault_root, vault_obsidian_root; print(vault_root()); print(vault_obsidian_root())"
# Ожидаем:
# D:\Projects\hometutor-studio\data
# D:\Projects\hometutor-studio\data

# 2. Тесты
.\.venv\Scripts\python.exe -m pytest tests/test_smart_konspekt.py tests/test_obsidian_export.py tests/test_ingestion_konspekt.py -q
# Ожидаем: 36 passed

# 3. Legacy txt-конвертация из data/ (нужен LM Studio с qwen3.6-27b)
.\.venv\Scripts\python.exe -c "
import time; from app.obsidian_export import to_obsidian_markdown
t0 = time.perf_counter()
def p(s,c,t): print(f'  [{s}] {c}/{t}  t={time.perf_counter()-t0:.0f}s', flush=True)
r = to_obsidian_markdown('ИИ Агенты/урок 2 Как агент думает и дейс.txt', force=True, progress=p)
print(f'action={r.action}  total={time.perf_counter()-t0:.0f}s  size={r.target_abs.stat().st_size} bytes')
"
# Ожидаем: action=converted  total=~836s  size=~15000 bytes
# Файл: data/ИИ Агенты/урок 2 Как агент думает и дейс.md  (не doc/конспекты/)

# 4. SmartKonspekt local pipeline (нужна папка materials/<курс>/<лекция>/)
.\.venv\Scripts\python.exe scripts/generate_konspekt.py "ИИ Агенты/урок 1" --force
.\.venv\Scripts\python.exe scripts/eval_konspekt.py "ИИ Агенты/урок 1" --golden "ИИ Агенты/урок 1 Введение в концепцию AI-агентов.md"
```
