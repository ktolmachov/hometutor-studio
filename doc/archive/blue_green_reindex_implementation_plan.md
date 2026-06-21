# План Внедрения Blue-Green Reindex

Статус: `Historical`
Роль: исторический implementation plan по внедрению blue-green reindex.
Читать как контекст выполнения работ, а не как источник правды о текущем поведении системы.

Дата: 2026-03-21  
Статус: Proposed  
Основано на [blue_green_reindex_design.md](/doc/blue_green_reindex_design.md)

## Цель

Разбить внедрение blue-green reindex на небольшие PR, чтобы:
- не ломать текущий read path;
- быстро получить generation-aware architecture;
- минимизировать риск при переходе.

## Общая стратегия

Порядок PR:

1. `PR-1`: registry layer + generation metadata
2. `PR-2`: read path на active generation
3. `PR-3`: write path на staging generation + activation
4. `PR-4`: retention/cleanup + integration tests

Ключевой принцип:
- сначала научить систему **читать active generation**,
- потом научить **строить staging generation**,
- и только потом включать atomic activation.

---

## PR-1: Registry Layer

### Цель

Добавить источник правды для active/staging generations, не меняя пока ingestion-алгоритм.

### Новые файлы

- `app/index_registry.py`

### Изменяемые файлы

- `app/config.py`
- `app/api_models.py`
- `app/routers/admin.py`
- `app/api_services.py`

### Что добавить

#### 1. `app/index_registry.py`

Новый API:

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class GenerationInfo:
    generation_id: str
    chunks_collection: str
    summaries_collection: str | None
    activated_at: str | None = None
    embed_model: str | None = None
    documents_count: int | None = None
    nodes_count: int | None = None
    summary_documents_count: int | None = None

def get_registry_path() -> Path: ...
def load_registry() -> dict[str, Any]: ...
def save_registry_atomic(data: dict[str, Any]) -> None: ...
def get_active_generation() -> GenerationInfo | None: ...
def begin_staging_generation(generation: GenerationInfo) -> None: ...
def mark_staging_generation_failed(error: str | None = None) -> None: ...
def activate_staging_generation(activated_at: str) -> GenerationInfo: ...
def clear_staging_generation() -> None: ...
def list_known_generations() -> list[GenerationInfo]: ...
```

#### 2. Файл registry

Добавить путь:

- `BASE_DIR / "index_registry.json"`

И lock-файл:

- `BASE_DIR / "index_registry.json.lock"`

#### 3. Fallback policy

Если registry ещё не существует:
- считать активным legacy mode:
  - chunks collection = `settings.collection_name`
  - summaries collection = `settings.summary_collection_name`
  - `generation_id = "legacy"`

Это даст обратную совместимость без миграции на старте.

### Критерий готовности PR-1

- registry можно читать/писать атомарно;
- старый код продолжает работать без blue-green;
- есть unit-тесты на `load/save/activate`.

---

## PR-2: Read Path на Active Generation

### Цель

Сделать retrieval generation-aware, не меняя пока reindex write path.

### Изменяемые файлы

- `app/retrieval_cache.py`
- `app/retrieval.py`
- `app/index_diff.py`
- `app/history_service.py`
- `app/api_models.py`

### Что изменить

#### 1. `app/retrieval_cache.py`

Вместо singleton base services:

```python
@dataclass
class BaseServicesEntry:
    generation_id: str
    client: Any
    collection: Any
    vector_store: Any
    storage_context: Any
    embed_model: Any
    llm: Any
    index: Any
    summary_collection: Any | None
    summary_vector_store: Any | None
    summary_storage_context: Any | None
    summary_index: Any | None

_base_services_cache: dict[str, BaseServicesEntry] = {}
```

Новые функции:

```python
def get_active_generation_id() -> str: ...
def clear_generation_cache(generation_id: str | None = None) -> None: ...
def get_base_services() -> dict[str, Any]:
    generation = get_active_generation()
    ...
```

Read path:
- получает `active_generation` из registry;
- кэширует services по `generation_id`;
- возвращает `generation_id` вместе с services.

#### 2. `app/retrieval.py`

В `cache_key` query engine добавить:

```python
services = get_base_services()
generation_id = services["generation_id"]
```

И включить `generation_id` в tuple cache key.

#### 3. `app/index_diff.py`

`get_index_stats()` должен:
- читать active generation из registry;
- открывать именно его collections;
- возвращать:
  - `generation_id`
  - `collection_name` как active chunks collection
  - `summary_collection_name`
  - `activated_at`

#### 4. `app/history_service.py`

Изменить `_index_version()`:

с:
```python
f"{collection_name}:{last_indexed_at}"
```

на:
```python
generation_id
```

или
```python
f"{generation_id}:{activated_at}"
```

Рекомендация:
- хранить отдельно `generation_id`
- и отдельно `index_activated_at`

### Критерий готовности PR-2

- retrieval читает active generation через registry;
- query engine cache не переиспользует engine между generations;
- `index/stats` и history знают про generation id;
- legacy fallback всё ещё работает.

---

## PR-3: Write Path на Staging Generation

### Цель

Перевести `build_index()` с delete-and-rebuild на build-validate-activate.

### Изменяемые файлы

- `app/ingestion.py`
- `app/routers/admin.py`
- `app/retrieval_cache.py`
- `app/index_registry.py`

### Что изменить

#### 1. Новые helper-функции в `app/ingestion.py`

```python
def _new_generation_id() -> str: ...
def _generation_collection_names(settings, generation_id: str) -> tuple[str, str]: ...
def _build_staging_collections(client, settings, generation_id: str): ...
def _validate_generation(client, embed_model, chunks_collection_name: str, summaries_collection_name: str | None): ...
def _activate_generation(...): ...
```

#### 2. Новый flow `build_index()`

Вместо:
- `delete_collection(active)`
- `create_collection(active)`

делаем:

1. `generation_id = _new_generation_id()`
2. `begin_staging_generation(...)`
3. создать staging collections
4. построить chunks/summaries в staging
5. validation
6. `activate_staging_generation(...)`
7. `clear_retrieval_cache()`
8. `reindex_end()`

Если ошибка:
- `mark_staging_generation_failed(...)`
- не трогать active generation

#### 3. `app/routers/admin.py`

Сейчас:

```python
try:
    services.build_index(reset=reset)
finally:
    services.reindex_end()
```

Нужно:
- вызывать `reindex_end()` только если lifecycle не завершился сам;
- либо оставить `finally`, но сделать `reindex_end()` idempotent и phase-aware.

Рекомендация:
- lifecycle держать в ingestion/service layer;
- router не должен “вслепую” завершать reindex.

### Критерий готовности PR-3

- при успешном reindex active generation меняется только в конце;
- при провале старый generation остаётся активным;
- удаление активной коллекции больше не происходит в `build_index()`.

---

## PR-4: Cleanup, Retention, Integration Tests

### Цель

Закрыть production-grade consistency story.

### Изменяемые файлы

- `app/index_registry.py`
- `app/ingestion.py`
- `app/retrieval_cache.py`
- `tests/...`

### Что добавить

#### 1. Retention policy

Функции:

```python
def cleanup_old_generations(keep_active: bool = True, keep_previous: bool = True) -> dict: ...
def cleanup_failed_staging_generations(max_age_hours: int = 24) -> dict: ...
```

#### 2. `reindex/status`

Расширить статус:
- `phase`
- `active_generation_id`
- `staging_generation_id`
- `previous_generation_id`

#### 3. Integration tests

Минимальный набор:

1. `test_reindex_build_failure_keeps_old_generation`
2. `test_active_generation_switches_only_after_validation`
3. `test_query_engine_cache_is_generation_aware`
4. `test_ask_during_build_reads_old_generation`

### Критерий готовности PR-4

- retention работает;
- integration tests подтверждают old-or-new consistency;
- можно считать `P0 reindex consistency` закрытым.

---

## Детализация по функциям

## `app/index_registry.py`

### `get_active_generation()`

Логика:

1. загрузить registry;
2. если есть `active_generation` — вернуть его;
3. иначе вернуть legacy generation:
   - `generation_id="legacy"`
   - names из settings.

### `begin_staging_generation()`

Логика:

1. взять file lock;
2. проверить, что `staging_generation` пуст;
3. записать новый staging generation;
4. не менять active.

### `activate_staging_generation()`

Логика:

1. взять file lock;
2. перечитать registry;
3. убедиться, что staging generation есть;
4. `previous = active`;
5. `active = staging`;
6. `staging = null`;
7. atomic save.

---

## Детализация по кэшу

## `app/retrieval_cache.py`

### Что удалить/заменить

Старые singleton поля:
- `_cached_collection`
- `_cached_index`
- `_cached_summary_index`

необязательно убирать сразу, но они должны стать internal state внутри `BaseServicesEntry`.

### Новый контракт `get_base_services()`

Возвращаем:

```python
{
  "generation_id": "...",
  "client": ...,
  "collection": ...,
  "index": ...,
  "summary_collection": ...,
  "summary_index": ...,
  ...
}
```

### Инвалидация

После activation:
- очищаем query-engine cache целиком;
- base services cache можно:
  - либо оставить generation-keyed,
  - либо удалить всё кроме active generation.

Рекомендация:
- на первом этапе чистить весь cache полностью.

---

## Детализация по stats/history

## `app/index_diff.py`

Нужно минимально расширить `get_index_stats()`:

```python
{
  "status": "ready",
  "generation_id": "...",
  "collection_name": "...",
  "summary_collection_name": "...",
  "documents_count": ...,
  "nodes_count": ...,
  "files": [...],
  "last_indexed_at": "...",
  "activated_at": "..."
}
```

## `app/history_service.py`

Рекомендация по формату:

```json
{
  "index_version": "20260321T181500Z_a1b2c3",
  "index_activated_at": "2026-03-21T18:16:10Z"
}
```

Так меньше двусмысленности, чем у `collection:last_indexed_at`.

---

## Риски внедрения

### 1. Legacy compatibility

Если сразу убрать старые fixed collection names, можно сломать существующий индекс.

Снижение риска:
- fallback на `legacy` generation;
- миграция только при первом новом reindex.

### 2. Кэш поколений

Если забыть добавить `generation_id` в query engine cache key, система будет выглядеть “почти работающей”, но ответы пойдут со старого индекса.

Это самый опасный скрытый баг после swap.

### 3. Cleanup timing

Если удалить previous generation слишком рано, in-flight запросы могут упасть.

На первом этапе:
- не удалять previous generation автоматически.

---

## Рекомендуемый порядок реальной реализации

1. Сделать `index_registry.py`.
2. Перевести `get_base_services()` на active generation.
3. Добавить `generation_id` в query engine cache key.
4. Перевести `get_index_stats()` и history на generation metadata.
5. Только после этого переписать `build_index()` на staging.
6. Затем добавить cleanup и integration tests.

---

## Definition of Done

Blue-green reindex можно считать реализованным, если выполняются все условия:

1. `build_index()` больше не удаляет активную коллекцию до завершения build.
2. Активная коллекция определяется через registry pointer, а не жёстко через settings.
3. Retrieval cache и query engine cache generation-aware.
4. При ошибке build active generation остаётся прежним.
5. Есть integration-тест, где параллельный `ask` во время reindex видит либо old, либо new generation.
