# Дизайн Blue-Green Reindex

Статус: `Historical`
Роль: исторический design doc, подготовленный до внедрения blue-green lifecycle.
Для текущего состояния системы ориентируйтесь на `architecture.md`, `technical_specification.md`, `api_reference.md` и код `app/index_registry.py`.

Дата: 2026-03-21  
Статус: Proposed  
Связанные документы:
- [tasklist.md](/doc/tasklist.md)
- [decision_memo_blockers_2026-03-21.md](/doc/decision_memo_blockers_2026-03-21.md)
- [adr_rag_architecture.md](/doc/adr_rag_architecture.md)

## 1. Проблема в текущем коде

Сейчас `reindex` работает по схеме:

1. `POST /reindex` ставит флаг через `try_reindex_begin()`.
2. `build_index()` удаляет активные коллекции:
   - `settings.collection_name`
   - `settings.summary_collection_name`
3. На их месте строится новый индекс.
4. По завершении вызывается `reindex_end()`.

Критическая проблема: это **delete-and-rebuild**, а не atomic swap.

Текущее состояние видно в коде:
- [app/routers/admin.py](/app/routers/admin.py#L64)
- [app/retrieval_cache.py](/app/retrieval_cache.py#L140)
- [app/retrieval_cache.py](/app/retrieval_cache.py#L254)
- [app/ingestion.py](/app/ingestion.py#L571)

Следствия:
- новые запросы блокируются/получают `503`;
- нет old/new generation boundary;
- `history.index_version` завязан на `collection_name:last_indexed_at`, а не на реальную версию поколения;
- нельзя сделать rollback без повторной сборки;
- нельзя гарантировать consistency в concurrent сценариях.

## 2. Цель

Сделать blue-green reindex с минимальным вмешательством в текущую архитектуру:

- во время `build` пользователи продолжают читать **старый** индекс;
- новый индекс строится в **staging generation**;
- активация происходит атомарно через смену registry pointer;
- in-flight запросы на старом query engine завершаются нормально;
- новые запросы после активации идут в новый generation;
- при ошибке build/validation активный generation не меняется.

## 3. Нецели

- Полноценный partial reindex.
- Миграция Chroma storage layout.
- Полный multi-tenant/workspace manager.
- Удаление старых generations сразу после swap.

Это можно делать позже поверх той же схемы поколений.

## 4. Ключевая идея

Вместо “одна фиксированная коллекция” вводим **индекс-поколения**:

- chunks collection: `home_rag__gen_<generation_id>`
- summaries collection: `home_rag_summaries__gen_<generation_id>`

Активная пара коллекций хранится не в `.env`, а в отдельном registry-файле:

- `index_registry.json`

`settings.collection_name` и `settings.summary_collection_name` становятся **base names**, а не активными physical collection names.

## 5. Новые артефакты

### 5.1. `index_registry.json`

Расположение:
- рядом с `index_meta.json`, в корне проекта.

Предлагаемый формат:

```json
{
  "schema_version": 1,
  "active_generation": {
    "generation_id": "20260321T181500Z_a1b2c3",
    "chunks_collection": "home_rag__gen_20260321T181500Z_a1b2c3",
    "summaries_collection": "home_rag_summaries__gen_20260321T181500Z_a1b2c3",
    "activated_at": "2026-03-21T18:16:10Z",
    "embed_model": "text-embedding-3-small",
    "documents_count": 42,
    "nodes_count": 1834,
    "summary_documents_count": 42
  },
  "staging_generation": null,
  "previous_generation": {
    "generation_id": "20260320T102000Z_d4e5f6",
    "chunks_collection": "home_rag__gen_20260320T102000Z_d4e5f6",
    "summaries_collection": "home_rag_summaries__gen_20260320T102000Z_d4e5f6",
    "activated_at": "2026-03-20T10:21:03Z"
  },
  "last_failed_generation": null
}
```

### 5.2. `index_meta.json`

Оставляем, но меняем смысл:
- `index_meta.json` больше не является источником “какая коллекция активна”;
- он хранит snapshot файлов и embed-модель для diff/compatibility;
- при желании можно добавить туда `active_generation_id`, но canonical source должен быть один: `index_registry.json`.

## 6. Состояния reindex

Вместо одного флага `reindex_in_progress` вводим фазовую модель:

- `idle`
- `building`
- `activating`
- `cleanup`
- `failed`

Важно:
- `building` не должен блокировать `GET /ask`;
- `activating` должен быть очень коротким;
- `cleanup` не должен влиять на активный трафик.

## 7. Новый lifecycle reindex

### Фаза A. Start

`POST /reindex`:

1. Проверяет, что нет другого reindex.
2. Создаёт `staging_generation_id`.
3. Пишет в registry `staging_generation` со статусом `building`.
4. Не трогает активный generation.

### Фаза B. Build staging

`build_index()`:

1. Строит документы и ноды как сейчас.
2. Создаёт staging collections:
   - `home_rag__gen_<id>`
   - `home_rag_summaries__gen_<id>`
3. Индексирует в staging collections.
4. Выполняет validation:
   - chunks collection существует;
   - `count() > 0`;
   - если summaries включены, collection доступна;
   - embed model совпадает с registry/meta;
   - можно собрать `VectorStoreIndex.from_vector_store(...)`.

Если validation падает:
- registry не переключается;
- `active_generation` остаётся прежним;
- staging generation помечается failed;
- старый трафик продолжает работать.

### Фаза C. Activate

Если build успешен:

1. Захватывается короткий activation lock.
2. Registry переписывается атомарно:
   - `previous_generation = active_generation`
   - `active_generation = staging_generation`
   - `staging_generation = null`
3. Инвалидация retrieval cache.
4. `reindex_end()`.

### Фаза D. Cleanup

Отдельно, уже после activation:

1. Старый generation не удаляется мгновенно.
2. Помечается как retention candidate.
3. Cleanup может удалить:
   - `previous_generation`, если retention policy разрешает;
   - stale failed staging collections.

Это важно: cleanup не должен быть частью atomic switch.

## 8. Атомарность registry

Atomic activation достигается не Chroma swap, а swap pointer-а:

1. Записать `index_registry.json.tmp`
2. `fsync`
3. `os.replace(tmp, target)`

На Windows это самый реалистичный atomic-ish путь для текущего проекта.

Для конкурентного доступа нужен `FileLock`:
- `index_registry.json.lock`

## 9. Изменения по файлам

### 9.1. Новый модуль: `app/index_registry.py`

Новый модуль должен дать API:

- `get_index_registry()`
- `get_active_generation()`
- `begin_staging_generation()`
- `mark_staging_failed()`
- `activate_staging_generation()`
- `clear_staging_generation()`
- `list_generations()`

Плюс atomic read/write через `FileLock`.

### 9.2. `app/ingestion.py`

Что меняется:

- `build_index()` больше не вызывает `delete_collection(active_name)`.
- Вместо этого:
  - получает `staging_generation_id`;
  - вычисляет physical collection names;
  - строит индекс в staging collections;
  - вызывает activation через registry API.

Нужны новые функции:

- `_build_generation_collection_names(generation_id)`
- `_validate_staging_generation(...)`
- `_activate_generation(...)`

### 9.3. `app/retrieval_cache.py`

Сейчас `get_base_services()` жёстко открывает:
- `settings.collection_name`
- `settings.summary_collection_name`

Нужно:

1. Читать `active_generation` из registry.
2. Кэшировать base services **по generation_id**.
3. Не использовать один глобальный `_cached_index` без поколения.

Минимальный путь:

- заменить одиночные `_cached_*` на structure вида:

```python
_base_services_cache: dict[str, BaseServicesEntry]
_active_generation_id: str | None
```

где ключ — `generation_id`.

Тогда:
- in-flight запрос, уже взявший engine старого поколения, завершится нормально;
- новый запрос после activation создаст engine уже для нового generation.

Также query-engine cache key должен включать `generation_id`, иначе после swap можно случайно переиспользовать старый engine.

### 9.4. `app/retrieval.py`

`cache_key` для query engine нужно расширить:

- добавить `generation_id`.

Иначе при одинаковом вопросе и одинаковых params можно вернуть engine старого поколения.

### 9.5. `app/index_diff.py`

Сейчас:
- `get_index_stats()` смотрит только на `settings.collection_name`;
- `COLLECTION_NAME` — устаревший override seam.

Нужно:

1. Брать active collection name из registry.
2. Возвращать:
   - `generation_id`
   - `chunks_collection_name`
   - `summaries_collection_name`
   - `activated_at`

Опционально:
- сохранить поле `collection_name` как alias для chunks collection ради обратной совместимости API/UI.

### 9.6. `app/history_service.py`

Сейчас `index_version = f"{collection_name}:{last_indexed_at}"`.

Нужно:

- использовать stable version:

```text
<generation_id>:<activated_at>
```

или просто `generation_id`.

Предпочтительно:
- `generation_id` как canonical id;
- `activated_at` отдельно.

### 9.7. `app/api_models.py`

`IndexStatsResponse` стоит расширить:

- `generation_id: Optional[str]`
- `summary_collection_name: Optional[str]`
- `activated_at: Optional[str]`
- возможно `reindex_phase: Optional[str]`

### 9.8. `app/routers/query.py`

Сейчас при любом `is_reindex_in_progress()` сразу `503`.

После blue-green:
- во время `building` запросы должны обслуживаться;
- опционально блокировать только во время `activating`, если activation lock держится дольше ожиданий.

Рекомендуемая политика:
- `building`: не блокировать;
- `activating`: либо кратко ждать, либо `503 Retry-After: 1`;
- `cleanup`: не блокировать.

## 10. Совместимость с текущим API

### Не меняем

- `POST /reindex`
- `GET /reindex/status`
- `GET /index/stats`

### Меняем внутреннюю семантику

- `reindex/status` должен возвращать phase, generation ids и progress.
- `index/stats` должен уметь показывать active generation.

## 11. Предлагаемый контракт `reindex/status`

```json
{
  "status": "running",
  "phase": "building",
  "active_generation_id": "20260320T102000Z_d4e5f6",
  "staging_generation_id": "20260321T181500Z_a1b2c3",
  "processed_files": 12,
  "total_files": 42,
  "started_at": "...",
  "finished_at": null,
  "error": null
}
```

## 12. Retention policy

Минимальный MVP:

- хранить `active_generation`
- хранить `previous_generation`
- хранить `last_failed_generation`

Cleanup policy:
- удалять generations старше `previous_generation`;
- failed staging удалять по TTL, например через 24 часа.

## 13. Failure modes

### Build failed

- active generation не меняется;
- staging generation → `last_failed_generation`;
- `reindex/status` показывает `failed`;
- retrieval продолжает работать на old generation.

### Activation failed

- registry не должен оказаться в partially written state;
- если `os.replace` не прошёл, активный generation остаётся старым;
- staging collections остаются для ручной диагностики / cleanup.

### Cleanup failed

- не влияет на активный трафик;
- логируется как warning/error;
- может быть повторён позже.

## 14. Тестовая матрица

### Unit

1. `index_registry` atomic read/write.
2. `activate_staging_generation()` корректно двигает `active` → `previous`.
3. `get_base_services()` возвращает services нужного generation.
4. Query engine cache key меняется при смене generation.

### Integration

1. Reindex build success:
   - active generation old;
   - staging built;
   - activate;
   - new queries read new generation.
2. Reindex build fail:
   - active generation unchanged;
   - `ask` продолжает работать.
3. Concurrent ask during build:
   - ответы идут со старого generation;
   - нет `EmptyIndexError`.
4. Swap:
   - in-flight старый запрос завершается успешно;
   - следующий запрос получает новый generation.

### Regression

1. `history.index_version` содержит generation id.
2. `/index/stats` показывает active generation.
3. Empty index behaviour остаётся информативным на cold start.

## 15. Пошаговый план внедрения

### Шаг 1. Registry layer

- добавить `app/index_registry.py`
- добавить generation-aware metadata file

### Шаг 2. Read path

- научить `retrieval_cache` и `index_diff` читать active generation из registry
- добавить `generation_id` в stats/debug

### Шаг 3. Write path

- переписать `build_index()` на staging collections
- activation через registry swap

### Шаг 4. Cleanup and tests

- retention/cleanup
- integration tests на consistency

## 16. Минимально-инвазивный вариант

Если нужно идти совсем маленькими шагами, можно сделать это в 2 релиза:

### Phase 1

- registry file
- generation-named collections
- activation swap
- без cleanup automation

### Phase 2

- retention policy
- richer status API
- cleanup stale generations

## 17. Рекомендуемое решение

Для текущего кода лучший компромисс:

- **generation-named Chroma collections**
- **atomic registry pointer**
- **generation-aware retrieval cache**
- **no immediate deletion of old generation**

Это решает главный блокер без полной перестройки ingestion/retrieval stack.
