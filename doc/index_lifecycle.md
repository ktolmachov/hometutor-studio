# Индекс: резервное копирование и жизненный цикл артефактов

Статус: `Live`  
Роль: операционная политика после итерации 16 tail (backup/restore, поведение при `reindex` / `reset`).

## Резервное копирование

- **Модуль:** `app/index_backup.py` — сборка ZIP с `manifest.json` и файлами относительно корня проекта (`BASE_DIR`).
- **CLI:** `python scripts/backup_index.py create <path.zip>` / `restore <path.zip>` (из корня репозитория).
- **По умолчанию в архив входят:** дерево `chroma_db/` (без `*.lock`), `index_registry.json`, `index_meta.json` (если есть), опционально `data/concept_graph.json` (legacy), дерево `data/graph_generations/` (SQLite bundle + `property_graph_store.json` по generation), опционально `faq_memory.jsonl` (флаг `--include-faq`).

### Восстановление

1. Остановите процесс API (uvicorn / worker), чтобы не писать в Chroma во время распаковки.
2. Выполните `python scripts/backup_index.py restore <archive.zip>`.
3. Запустите API снова. Кэш query engine в памяти процесса пуст при старте; при необходимости выполните `POST`-сценарий, который сбрасывает кэш (перезапуска обычно достаточно).

Eval-бейзлайны (`eval_data/`), результаты прогонов (`eval_results/`), `logs/metrics_store.jsonl`, `logs/history.jsonl`, `data/user_state.db` **не** входят в минимальный backup индекса: они относятся к истории запросов, метрикам и пользовательскому состоянию; при полном бэкапе машины копируйте их отдельно.

## Поведение при `reindex` (reset=false)

| Артефакт | Поведение |
|----------|-----------|
| Chroma (chunks + summaries) | Новая staging generation; после успешной активации — swap в `index_registry.json`, `index_version++`. |
| `ingestion_content_hashes.json` | Обновляется после успешной активации. |
| `index_meta.json` | Обновляется через слой diff/snapshot (`update_snapshot_after_index`). |
| Query engine + BM25 кэш | `clear_retrieval_cache()` при активации staging. |
| `data/graph_generations/` | Staging: `staging/<slug>/` до swap; после активации — `by_generation/<generation_id>/` (`kg.sqlite` + LlamaIndex `property_graph_store.json`). Чтение активного графа через `get_active_knowledge_graph()` по `generation_id` из registry. Legacy `data/concept_graph.json` используется, пока для активной generation нет bundle. |
| Document summaries в Chroma | Входят в коллекции; при partial reindex копируются/пересобираются вместе с чанками. |
| `faq_memory.jsonl` | Не очищается автоматически; записи могут ссылаться на старые ответы. При необходимости включите `CLEAR_FAQ_ON_INDEX_ACTIVATION=true` в `.env` — после каждой успешной активации индекса файл очищается (`Settings.clear_faq_on_index_activation`). |
| `data/user_state.db` (`spaced_repetition`, `quiz_mastery`) | После каждой успешной активации вызывается `run_learner_state_lineage_sync()` — строки с устаревшим `generation_id` архивируются, совпадающие с активным графом получают актуальные `generation_id` / `index_version` (см. `sync_current_learner_state_lineage` в `app/user_state.py`). |
| `logs/metrics_store.jsonl`, session/history | Не сбрасываются; события остаются для аудита. |

## Поведение при `reset=true`

| Артефакт | Поведение |
|----------|-----------|
| Chroma | Полная пересборка в канонические имена коллекций (`collection_name` / `summary_collection_name`). |
| Registry | `activate_reset_generation`, `index_version++`. |
| Кэш retrieval | `clear_retrieval_cache()` после активации. |
| Концепт-граф (bundle) | После `activate_reset_generation` — запись в `graph_generations/by_generation/<generation_id>/`; learned-состояние берётся из графа до активации. Компилятор: `compile_course_graph` (локальный `GRAPH_MODEL` / `get_graph_llm()`). При ошибке extraction bundle может содержать только `graph_quality_report.json` без `kg.sqlite` — см. § «Пустой Knowledge Graph после ingest». |
| FAQ / metrics / history / user_state | По умолчанию **не** удаляются; см. таблицу выше для опциональной очистки FAQ. |

## Пустой индекс и кэш

- Если активная коллекция Chroma пуста, `get_base_services()` в `retrieval_cache` выбрасывает `EmptyIndexError` с сообщением о необходимости `POST /reindex`.
- После успешной активации новой generation кэш движков запросов и BM25 инвалидируется; первый запрос к `/ask` инициализирует сервисы заново.

## Пустой Knowledge Graph после ingest

**Симптом (UI):** «Нет данных для графа: пустой или отсутствующий `data/concept_graph.json` и нет строк в quiz_mastery».

**Важно:** успешный `ingest.py --reset` **не гарантирует** граф. Chroma может быть заполнен (`GET /index/stats` → `documents_count > 0`), а граф — пуст.

### Как читается активный граф

1. `get_active_knowledge_graph()` берёт `generation_id` из `index_registry.json`.
2. Если есть `data/graph_generations/by_generation/<generation_id>/kg.sqlite` — читается SQLite bundle.
3. Иначе fallback на legacy `data/concept_graph.json` (часто отсутствует после reset).

### Диагностика (2026-06-11, курс «ИИ Агенты»)

| Проверка | Ожидание при успехе | Что было при сбое |
|----------|---------------------|-------------------|
| `chroma_db/`, `/index/stats` | 5 документов | OK |
| `graph_generations/by_generation/<gen>/kg.sqlite` | файл есть | **отсутствовал** |
| `graph_quality_report.json` | `gate_passed: true` или хотя бы записан bundle | `gate_passed: false`, `fail_reasons: ["truncated graph LLM output"]`, `truncated: true` |
| `data/concept_graph.json` | не обязателен при наличии bundle | отсутствовал |
| `ENABLE_METADATA_ENRICHMENT` | `true` даёт концепты в metadata для эвристики | `false` — fallback по metadata тоже пуст |

**Корневая причина:** Course Graph Compiler упал на документе «Урок 3» — локальный LLM (`GRAPH_MODEL=qwen/qwen3.6-27b`, LM Studio) вернул обрезанный JSON (`finish_reason: length`). Вызов шёл без явного `max_tokens`; при truncation compiler возвращает пустой payload и **не** пишет `kg.sqlite`.

**Исправление в коде:** `app/course_graph_compiler.py` — `llm.chat(..., max_tokens=8192)` в `_default_llm_extract`.

### Recovery

1. Удалить `data/llm_request_cache.db` (кэш мог сохранить обрезанные ответы graph extraction).
2. Перезапустить API/Streamlit (сброс singleton `get_active_knowledge_graph()`).
3. Повторить `python ingest.py --reset -y` **или** пересобрать bundle для активной generation (документы из `chroma_db/ingestion_extracted_documents.json` → `write_generation_knowledge_graph_bundle`).
4. Проверить: `kg.sqlite` в каталоге generation; в UI — ненулевое число концептов.

**Примечание:** `gate_passed: false` (quality gate: мало cross-doc relations) **не блокирует** отображение графа, если bundle с концептами записан. Пустой UI — только когда bundle не создан.

### Связанные настройки

- `GRAPH_MODEL`, `GRAPH_LLM_API_BASE` — endpoint graph extraction (локальный LM Studio).
- `graph_llm_probe_ok()` — при `false` ingest использует эвристический `build_graph_payload_from_documents` (нужны `concepts`/`key_concepts` в metadata → `ENABLE_METADATA_ENRICHMENT=true`).

## Связанные модули

- `app/index_registry.py` — registry и блокировки.
- `app/ingestion.py` — `build_index`, partial/full пути.
- `app/index_lifecycle.py` — хуки после активации (очистка FAQ по флагу, eager learner lineage sync).
- `app/faq_memory.py` — `clear_faq_memory_file()`.
