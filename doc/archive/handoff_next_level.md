# Hand-off: следующий уровень demo-пакета для конкурса

> **Для кого этот документ:** для новой сессии ИИ-агента (цель-модель — Claude Sonnet 4.6 / medium-thinking). Контекст предыдущих сессий недоступен — поэтому ниже **всё, что нужно знать**, чтобы реализовать две фичи без разведки.
>
> **Цель:** довести demo-пакет для конкурса до состояния «запустил — увидел заполненный продукт» + «получил готовый MP4 для YouTube-тизера».
>
> **Статус предыдущих сессий:** собраны `doc/pitch.md`, `doc/presenter_script.md`, `doc/quickstart.md`, `doc/quickstart_demo.md`, smart-демо с GIF, `npm run demo:kit` → `dist/jury_kit_*.zip`. См. также: `doc/user_guide.md`, `doc/user_scenarios.md`.

---

## 1. Обзор двух фич

| Фича | Приоритет | Примерный объём | Выход |
|---|:---:|:---:|---|
| **F1. Seeded Demo User** | P0 | 1 день | `npm run demo:seed` → при `docker compose up` жюри видит UI с 3 due-флэшкартами, mastery-картой, активным курсом, историей |
| **F2. MP4 тизер** | P1 | 0.5 дня | `npm run demo:mp4` → `dist/home-rag_teaser_<date>.mp4` (60 сек, монтаж 3 GIF) |

Оба пути **независимы** — можно реализовать параллельно или по очереди. F1 сложнее и важнее для живого демо; F2 — для дистрибуции.

---

## 2. Текущее устройство кода (факты, без воды)

### 2.1 Где живёт state

- **БД:** `data/user_state.db` (SQLite, WAL). Путь конфигурируется через `user_state_db` в `app/config.py`, fallback: `BASE_DIR / "data" / "user_state.db"`.
- **Подключение:** `app/user_state_core.py` → `_connect()`, декоратор `_with_db`.
- **Инициализация схемы:** `_ensure_schema()` в `app/user_state_core.py` (~строки 281–523) — идемпотентно, создаёт все таблицы при первом обращении.
- **Фасад CRUD:** `app/user_state.py` (реэкспорт всех операций из sub-модулей).

### 2.2 Таблицы, релевантные для seed

| Таблица | Что сидируем | Модуль-писатель |
|---|---|---|
| `flashcard_decks` | 2–3 колоды (общая + курс) | `app/user_state_flashcards.py` → `create_flashcard_deck()` |
| `flashcards` | ~15 карточек с уже выставленными SM-2 полями | `app/user_state_flashcards.py` → `save_flashcards_to_deck()` + `update_flashcard_sr()` |
| `spaced_repetition` | 8–12 концептов с `next_review` в прошлом/сегодня | `app/spaced_repetition.py` (writer внутри), напрямую SQL |
| `quiz_mastery` | 6–8 концептов с уровнями `recognition/recall/transfer` | `app/quiz_adaptive.py` → `update_mastery_after_score()` |
| `quiz_results` | 20–30 исторических событий квизов | `app/quiz_adaptive.py` (writer) |
| `micro_quiz_events` | 5–10 micro-quiz событий | `app/user_state_quiz.py` |
| `reading_status` | 3–5 документов с progress 20–80% | `app/user_state_reading.py` |
| `tutor_learning_resume` | 1 запись id=1 — «продолжи с темы X» | `app/user_state_tutor.py` |
| `app_kv` | `ADAPTIVE_DAILY_PLAN_KV_KEY` + 1–2 других KV | `app/adaptive_plan.py` |
| `flashcard_decks`, `flashcards` с тегом `course:<id>` | колода для demo-курса | стандартный `create_flashcard_deck(source_type="course", source_id=json.dumps({...}))` |

**ВАЖНО:**
- `sync_bundle` (в `app/user_state_sync.py`) **не включает** таблицы `flashcard_decks` и `flashcards`. Для seed **нельзя** идти через `import_full_sync_bundle` — нужен прямой SQL **или** комбинация `user_state_flashcards` API + прямой SQL для SM-2 полей.
- Метод `save_flashcards_to_deck()` при bulk insert НЕ трогает поля `easiness/interval_days/repetitions/next_review` → остаются NULL/дефолты. Чтобы карточки стали «due сегодня», после вставки нужно **напрямую UPDATE** или вызывать `update_flashcard_sr(...)` с рассчитанным `next_review <= now`.

### 2.3 Что такое «активный курс»

**Подвох:** `StudyScope` (активный курс) живёт **в Streamlit `session_state`**, не в БД. Ключ: `active_study_scope`.

**Последствия для seed:**
- Невозможно «активировать курс» просто записью в БД — при перезапуске Streamlit scope пропадёт.
- **Два решения на выбор:**
  - **A (проще):** сидировать данные без scope-активации; UI покажет mastery/due/флэшкарты глобально. Жюри всё равно увидит заполненное состояние.
  - **B (полноценный курс):** добавить в UI чтение scope из `app_kv` (ключ `demo_active_scope`) при первом рендере — один раз, а дальше как обычно. Это микро-патч в `app/ui/study_scope.py` — ищи `_load_active_scope_from_session()` и добавь fallback `_load_active_scope_from_kv()`.
- **Рекомендация для первой итерации:** путь A. Путь B опционально.

### 2.4 Mini-KB для индексации

- Ожидаемый путь в `scripts/run_quality_benchmark.py`: `eval_data/quality_benchmark_kb/` — **сейчас пусто/отсутствует локально**.
- `ingest.py` **НЕ принимает аргумент директории** (жёстко `data/`). Чтобы проиндексировать demo-KB, нужно:
  1. Скопировать файлы mini-KB в `data/demo/` (или `data/`).
  2. Запустить `python ingest.py --reset`.
- Поддерживаемые форматы: `.pdf`, `.txt`, `.md`, `.docx`, `.html` (из `_DOC_SUPPORTED_EXTS` в `app/ingestion.py`).
- **Вариант:** генерировать 5–7 коротких `.md`-файлов прямо в скрипте seed (тема: ML basics). Это быстрее, чем тянуть чужие PDF, и воспроизводимо.

### 2.5 Docker compose

- `docker-compose.yml`: один сервис `home-rag`, один контейнер, команда запускает `uvicorn` и `streamlit` параллельно через bash `&`/`wait`.
- **Entrypoint-скрипта НЕТ** — seed добавляется либо как отдельная ступень, либо через override команды.
- Volumes: `./data:/app/data`, `./chroma_db:/app/chroma_db`, `./.env:/app/.env:ro`.
- **Следствие:** если `data/user_state.db` подготовлен на хосте, он автоматически попадёт в контейнер через volume. Это упрощает путь: сид делается на **хосте**, а не внутри контейнера.

### 2.6 Видео-стек (для F2)

- `requirements.txt` **не содержит** `moviepy`, `imageio-ffmpeg`, `opencv-python`.
- В образе `python:3.11-slim` **нет ffmpeg**.
- **Решение:** добавить `imageio-ffmpeg>=0.4.9` — он тянет статический бинарник ffmpeg, **не требует apt-get install**. Лицензия LGPL, для локальной сборки OK.

---

## 3. F1 — Seeded Demo User

### 3.1 Цель (definition of done)

После выполнения:
```bash
npm run demo:seed
docker compose up
```
Открыв `http://localhost:8501`, жюри **в течение 5 секунд** видит:

1. **Sidebar или Home:** подсказка «Сегодня: 3 флэшкарты к повторению, 1 due-review концепт, 2 мин чтения».
2. **Progress tab / Mastery:** тепловая карта с ≥6 концептами на разных уровнях (зелёный/жёлтый/красный), ≥1 графуированный (`graduated`).
3. **Flashcards tab:** видна колода «ML Basics (demo course)» с ~8 карточками, минимум 3 в due-статусе.
4. **Topics / Knowledge Graph:** KB проиндексирована на 5–7 концептов.
5. **Quick Answer:** ввод «что такое регуляризация» возвращает ответ с источниками из demo-KB (если LLM настроен — живой ответ; если нет — fallback offline stub).

### 3.2 Файлы, которые создаём

#### `scripts/seed_demo_user.py` (новый, ~400 строк)

Основной seed-скрипт. Разделить на блоки:

```python
"""
Seeded Demo User — готовит data/user_state.db и data/demo/ так,
чтобы при `docker compose up` UI демонстрировал заполненный продукт.

Запуск:
    python scripts/seed_demo_user.py
    python scripts/seed_demo_user.py --fresh         # стереть существующий state
    python scripts/seed_demo_user.py --kb-only       # только mini-KB, state не трогать
    python scripts/seed_demo_user.py --state-only    # только state, KB не трогать
"""

# Основные шаги:
# 1. _ensure_clean_data_dirs() — опц. rm -rf data/user_state.db, data/demo/, chroma_db/
# 2. _write_mini_kb(target_dir: Path) — создать 5–7 .md файлов в data/demo/
# 3. _run_ingest() — subprocess python ingest.py --reset -y
# 4. _seed_mastery() — заполнить quiz_mastery + spaced_repetition + quiz_results
# 5. _seed_flashcards() — создать 2 колоды, вставить карточки, проставить SM-2 на due
# 6. _seed_reading_progress() — 3 записи в reading_status
# 7. _seed_adaptive_plan() — записать ADAPTIVE_DAILY_PLAN_KV_KEY с 3 шагами на сегодня
# 8. _seed_tutor_resume() — записать tutor_learning_resume id=1 «продолжи с регуляризации»
# 9. _seed_course_scope_kv() — опц. записать demo_active_scope в app_kv (если путь B)
# 10. _print_summary() — напечатать что посеяно и куда
```

**Список концептов для демо-KB (ML-Basics):**
1. `supervised_learning` — mastery: `transfer` (graduated)
2. `unsupervised_learning` — mastery: `recall`, due_review: вчера
3. `overfitting` — mastery: `recall`, due_review: сегодня
4. `regularization` — mastery: `recognition`, due_review: сегодня
5. `gradient_descent` — mastery: `recognition`
6. `cross_validation` — mastery: `recognition`, due_review: сегодня
7. `neural_networks` — mastery: отсутствует (новый концепт)

Это даёт палитру состояний: освоено / повторяется / изучается / новое.

**Содержимое mini-KB (каждый файл ~300–500 слов, .md):**
- `data/demo/01_supervised_learning.md`
- `data/demo/02_unsupervised_learning.md`
- `data/demo/03_overfitting_and_regularization.md`
- `data/demo/04_gradient_descent.md`
- `data/demo/05_cross_validation.md`
- `data/demo/06_neural_networks_intro.md`
- `data/demo/README.md` — краткое описание, чтобы жюри видел в файл-менеджере «это demo-данные».

Можно взять тексты с Wikipedia (короткие summary) или сгенерировать в скрипте статической строкой.

#### `scripts/seed_helpers/` (новый пакет)

Разделим seed на модули для читаемости:

```
scripts/seed_helpers/
├── __init__.py
├── mini_kb.py          # DEMO_CONCEPTS = [...] + генератор .md
├── mastery.py          # сидирование quiz_mastery/spaced_repetition/quiz_results
├── flashcards.py       # 2 колоды, 15 карточек с SM-2 полями
├── reading.py          # reading_status 3–5 документов
├── adaptive.py         # ADAPTIVE_DAILY_PLAN_KV_KEY структура
└── tutor.py            # tutor_learning_resume snapshot
```

#### `package.json` (патч)

Добавить скрипты:

```json
"demo:seed": "python scripts/seed_demo_user.py",
"demo:seed:fresh": "python scripts/seed_demo_user.py --fresh",
"demo:jury": "python scripts/seed_demo_user.py --fresh && docker compose up --build -d && echo Open http://localhost:8501"
```

#### `docker-compose.override.yml` (опционально)

Если нужен «автоматический» seed при `docker compose up`, создать override:

```yaml
services:
  home-rag:
    depends_on:
      seeder:
        condition: service_completed_successfully
  seeder:
    build:
      context: .
    command: python scripts/seed_demo_user.py --state-only
    volumes:
      - ./data:/app/data
```

Но **рекомендация:** seed запускается на **хосте** через `npm run demo:seed` до `docker compose up`. Не усложняй compose. Override может быть полезен для CI, но для живого демо не нужен.

### 3.3 Ключевой SQL: как сидировать флэшкарты с due-статусом

Проблема: `save_flashcards_to_deck()` не заполняет SM-2 поля. Пишем сразу после:

```python
import datetime as dt
import sqlite3

def _force_due(deck_id: int, front: str, days_overdue: int = 1) -> None:
    past = (dt.datetime.utcnow() - dt.timedelta(days=days_overdue)).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            UPDATE flashcards
               SET easiness = 2.5,
                   interval_days = 1,
                   repetitions = 1,
                   next_review = ?,
                   last_review = ?
             WHERE deck_id = ? AND front = ?
            """,
            (past, past, deck_id, front),
        )
```

### 3.4 Ключевой SQL: `spaced_repetition` на концептах

```python
def _seed_sr_concept(concept: str, *, due_in_days: int, easiness: float = 2.5) -> None:
    now = dt.datetime.utcnow()
    next_review = (now + dt.timedelta(days=due_in_days)).isoformat()
    last_review = (now - dt.timedelta(days=3)).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO spaced_repetition
                (concept, easiness, interval_days, repetitions, next_review, last_review,
                 generation_id, index_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (concept, easiness, max(1, abs(due_in_days)), 2,
             next_review, last_review, _current_generation_id(), _current_index_version()),
        )
```

`generation_id` и `index_version` берутся из `app/user_state_core.py` — функции `get_active_generation_id()` / `get_active_index_version()` (посмотри реальные имена в коде, они рядом).

### 3.5 Ключ: adaptive_plan KV

Посмотри формат через `app/adaptive_plan.py` — функция `get_adaptive_daily_plan()` показывает структуру. Сид должен быть зеркальным:

```python
plan = {
    "generated_at": dt.datetime.utcnow().isoformat(),
    "valid_date": dt.date.today().isoformat(),
    "steps": [
        {"type": "due_review", "concept": "overfitting", "minutes": 3},
        {"type": "flashcard_batch", "deck_id": deck_id_ml, "count": 3, "minutes": 5},
        {"type": "new_concept", "concept": "neural_networks", "minutes": 7},
    ],
    "rationale": "3 концепта на повторение + 1 новый — в пределах 15 минут.",
}
set_kv(ADAPTIVE_DAILY_PLAN_KV_KEY, json.dumps(plan))
```

**Проверь реальную схему** — в `app/adaptive_plan.py` может быть иное именование полей.

### 3.6 Acceptance tests

Добавить `tests/e2e/demos/scenario_00_seeded_state.spec.ts` — e2e проверка:

1. Открывает Home.
2. Переключается на вкладку «Flashcards» → видит колоду с именем `ML Basics (demo)`.
3. Переключается на «Progress» / «Mastery» → видит ≥1 концепт в статусе `graduated`, ≥3 due.
4. Пишет вопрос «что такое регуляризация» → получает ответ с ≥1 источником (offline-stub допустим).
5. Capture screenshot → `doc/screenshots/scenario_00_seeded/` для smart-demo.

### 3.7 Подводные камни

1. **Chroma index должен соответствовать сиду.** Если сеял концепты, которых нет в KB, mastery-карта покажет концепты без связанных документов → trust panel пустой. **Строго:** набор концептов в mastery ⊂ набор тегов/тем в KB.
2. **`index_version` и `generation_id`.** Сид должен использовать текущие значения после `ingest.py --reset`. Порядок: сначала ingest, потом seed state. Иначе lineage-фильтр скроет записи.
3. **Streamlit cache.** Если UI был открыт до сида — нужен hard-refresh браузера (Ctrl+Shift+R). Упомяни это в `--print-summary`.
4. **Time-zone.** `datetime.utcnow()` VS `datetime.now()` — в коде используется UTC isoformat. Проверь, чтобы `next_review` шёл в том же формате.
5. **chroma_db volume.** Если жюри делает `docker compose up -v`, volume удаляется и сид нужно запускать снова. В `demo:jury` можно добавить `docker compose down -v` перед сидом — для полной чистоты.
6. **OPENAI_API_KEY.** Если его нет, Quick Answer вернёт заглушку. Для жюри-демо без ключа: добавить в seed `.env.demo` с `OFFLINE_MODE=1` или заранее объяснить, что квесты работают, а LLM-ответы — нет.

### 3.8 Финальный чек-лист F1

- [ ] `scripts/seed_helpers/` пакет из 5–6 модулей.
- [ ] `scripts/seed_demo_user.py` CLI с `--fresh`, `--state-only`, `--kb-only`.
- [ ] `data/demo/` с 5–7 .md-файлами (генерируется скриптом, в git **не** коммитится — уже в `.gitignore` как `data/`).
- [ ] `package.json` обновлён: `demo:seed`, `demo:seed:fresh`, `demo:jury`.
- [ ] `README.md` секция «Для жюри»: 3 команды до первого живого UI.
- [ ] `tests/e2e/demos/scenario_00_seeded_state.spec.ts` зелёный.
- [ ] `doc/quickstart_demo.md` пересобран с новым сценарием `scenario_00`.
- [ ] `doc/presenter_script.md` обновлён: в 0:45-секунду ссылка не на scenario_01, а на scenario_00 (живое состояние).

---

## 4. F2 — MP4 тизер из GIF

### 4.1 Цель (definition of done)

После выполнения:
```bash
npm run demo:mp4
```
В `dist/` появляется файл `home-rag_teaser_<date>.mp4`:

- длительность: 60 секунд (±5),
- разрешение: 1280×720 (YouTube-friendly),
- кодек: H.264 (libx264), аудио — опционально (см. ниже),
- монтаж: титр 3 сек → GIF сценария 1 (15 сек) → переход → GIF сценария 5 (15 сек) → GIF сценария 2 (15 сек) → outro-титр 12 сек с QR на репо,
- bitrate: ~2 Mbps (файл ≤15 MB).

### 4.2 Зависимости

Добавить в `requirements.txt`:

```
imageio-ffmpeg>=0.4.9
```

**Почему не `moviepy`:** moviepy притащит numpy/decorator и ~15 MB зависимостей. Для простого монтажа достаточно ffmpeg CLI через `imageio-ffmpeg.get_ffmpeg_exe()`.

**Почему не apt-get ffmpeg:** не требует изменения Dockerfile, не ломает slim-базу.

### 4.3 Файлы, которые создаём

#### `scripts/make_teaser_mp4.py` (новый, ~200 строк)

```python
"""
Сборка MP4-тизера из GIF-кадров сценариев для YouTube/твиттера.

Требует:
    pip install imageio-ffmpeg
    python scripts/make_demo_gifs.py  # GIF должны быть собраны заранее

Запуск:
    python scripts/make_teaser_mp4.py
    python scripts/make_teaser_mp4.py --duration 60 --resolution 1280x720
    python scripts/make_teaser_mp4.py --config doc/teaser/montage.yaml
"""

# Алгоритм:
# 1. Прочитать конfig YAML: список сегментов {gif_path | title_text, duration_sec, transition}
# 2. Для каждого сегмента:
#     - GIF → временная mp4 через ffmpeg -i input.gif -c:v libx264 -t <dur> ...
#     - title → ffmpeg с filter drawtext или заранее сгенерированный PNG через Pillow
# 3. Конкатенация через ffmpeg concat demuxer (-f concat -i segments.txt)
# 4. Финальный rescale/pad до 1280x720 (letterbox, чтобы не резать)
# 5. Вывод в dist/home-rag_teaser_<date>.mp4
```

#### `doc/teaser/montage.yaml` (новый)

Конфиг монтажа — отдельный файл, чтобы не править код при изменении плана:

```yaml
# Монтажный план YouTube-тизера home-rag.
# Длительности в секундах. Резолюция и fps — глобальные.

output:
  resolution: 1280x720
  fps: 24
  bitrate: 2M
  codec: libx264

segments:
  - type: title
    text: |
      home-rag
      personal tutor from your own notes
    subtitle: "local-first · 5 minutes to wow"
    duration_sec: 3
    bg_color: "#0B1020"
    fg_color: "#FFFFFF"

  - type: gif
    path: doc/screenshots/scenario_01/demo.gif
    caption: "Drop your PDFs → ask questions → get sources"
    duration_sec: 15
    fit: contain   # letterbox if aspect differs

  - type: transition
    kind: fade_black
    duration_sec: 1

  - type: gif
    path: doc/screenshots/scenario_05/demo.gif
    caption: "Your folder → a learning course in one click"
    duration_sec: 15

  - type: transition
    kind: fade_black
    duration_sec: 1

  - type: gif
    path: doc/screenshots/scenario_02/demo.gif
    caption: "One UI, six modes, zero confusion"
    duration_sec: 15

  - type: outro
    text: "github.com/your-org/home-rag_v2"
    subtitle: "3 commands → your own tutor"
    qr_url: "https://github.com/your-org/home-rag_v2"
    duration_sec: 10
    bg_color: "#0B1020"
```

#### `package.json` (патч)

```json
"demo:mp4": "python scripts/make_teaser_mp4.py",
"demo:mp4:custom": "python scripts/make_teaser_mp4.py --config doc/teaser/montage.yaml"
```

#### `.gitignore` (патч)

Уже есть `dist/` — это покрывает вывод. Временные файлы `scripts/.mp4_workdir/` добавить, если используются.

### 4.4 Реализация: ключевые фрагменты

**Получить путь к ffmpeg (без установки apt):**

```python
import imageio_ffmpeg
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()  # путь к статическому бинарнику
```

**GIF → MP4-сегмент:**

```python
subprocess.run([
    FFMPEG, "-y",
    "-i", str(gif_path),
    "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,fps={FPS}",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",      # критично для совместимости с плеерами
    "-preset", "medium",
    "-crf", "23",
    "-t", str(duration_sec),
    str(out_mp4),
], check=True)
```

**Title-слайд (PNG через Pillow → MP4):**

```python
from PIL import Image, ImageDraw, ImageFont

def make_title_slide(text: str, subtitle: str, out_png: Path, size=(1280, 720)) -> None:
    img = Image.new("RGB", size, "#0B1020")
    draw = ImageDraw.Draw(img)
    # Используй стандартный шрифт — Pillow даёт default, но для презентации
    # лучше загрузить .ttf из requirements, например fonts/Inter-Bold.ttf.
    # ...
    img.save(out_png)

subprocess.run([
    FFMPEG, "-y",
    "-loop", "1",
    "-i", str(slide_png),
    "-c:v", "libx264", "-t", str(dur), "-pix_fmt", "yuv420p",
    "-vf", f"scale={W}:{H}",
    str(out_mp4),
], check=True)
```

**Конкатенация:**

```python
concat_list = workdir / "concat.txt"
concat_list.write_text("\n".join(f"file '{p.as_posix()}'" for p in segment_files))

subprocess.run([
    FFMPEG, "-y",
    "-f", "concat", "-safe", "0",
    "-i", str(concat_list),
    "-c", "copy",          # если все сегменты совместимы по кодеку/fps/размеру
    str(final_mp4),
], check=True)
```

**Транзишены fade_black:** проще всего реализовать как отдельный 1-секундный сегмент — чёрный фон с fade-in предыдущего на 0.5s и fade-out на следующий. Для первой итерации — просто пустой чёрный сегмент без fade (ffmpeg concat склеит встык, визуально приемлемо).

**QR-код в outro:**

```python
# добавить в requirements.txt: qrcode>=7.4
import qrcode
qr = qrcode.make("https://github.com/your-org/home-rag_v2")
qr.save(workdir / "qr.png")
# затем overlay через ffmpeg: -filter_complex "overlay=W-w-40:H-h-40"
```

### 4.5 Acceptance tests

1. `python scripts/make_teaser_mp4.py` без аргументов собирает файл и печатает путь.
2. Файл воспроизводится в VLC и в Windows Media Player без ошибок кодека.
3. Длительность в пределах 58–62 сек (`ffprobe` + assert).
4. Файл ≤ 20 MB.
5. Файл загружен в `dist/` и включается в Jury Kit (патч `scripts/build_jury_kit.py` — добавить `dist/home-rag_teaser_*.mp4` в список).

### 4.6 Подводные камни

1. **Pillow 12 и шрифты.** Дефолтный шрифт Pillow даёт мелкий текст. Для титров загрузи `Inter-Bold.ttf` или `Roboto-Bold.ttf` в `scripts/assets/fonts/`. Или используй ffmpeg `drawtext` с системным шрифтом (на Windows: `C:/Windows/Fonts/arial.ttf`, на Linux в контейнере — нужен DejaVu).
2. **GIF-кадровая частота.** Наши GIF собраны на 1.2 fps (один кадр ~830ms). Прямое конвертирование даст дёрганое видео. В `-vf` фильтре добавь `minterpolate=fps=24:mi_mode=dup` или проще: `fps=24` (дублирование кадров).
3. **concat demuxer и `-c copy`.** Работает только если все сегменты закодированы одним и тем же кодеком/fps/res. Если бьётся — пересобери финал с `-c:v libx264` вместо `-c copy`.
4. **pix_fmt yuv420p.** Без него некоторые плееры (iOS Safari, ряд ТВ) не покажут видео.
5. **Кодировка stdout на Windows.** Вывод `subprocess.run(...)` с кириллицей может упасть → используй `encoding="utf-8"` + `errors="replace"` при print, либо сохраняй логи в файл.
6. **Аудио.** В первой версии — без аудио (тихий MP4). Для YouTube допустимо. Если нужен музыкальный фон, добавь `-i bg_music.mp3 -map 0:v -map 1:a -shortest` в финальный ffmpeg-вызов, но это отдельная задача с подбором роялти-free музыки.

### 4.7 Финальный чек-лист F2

- [ ] `imageio-ffmpeg` добавлен в `requirements.txt`.
- [ ] `qrcode` добавлен в `requirements.txt`.
- [ ] `scripts/make_teaser_mp4.py` CLI работает.
- [ ] `doc/teaser/montage.yaml` документирован, с примерами.
- [ ] `scripts/assets/fonts/Inter-Bold.ttf` (или аналог) присутствует, либо fallback на системный.
- [ ] `package.json`: `demo:mp4`, `demo:mp4:custom`.
- [ ] `scripts/build_jury_kit.py` включает MP4 в ZIP (если файл есть).
- [ ] `doc/pitch.md` упоминает MP4-тизер и ссылку на YouTube (placeholder).

---

## 5. Интеграция обеих фич

### 5.1 Обновить `npm run demo:kit`

Текущий pipeline:
```
test:e2e:demo → make_demo_gifs.py → generate_demo_doc.py → build_jury_kit.py
```

Новый pipeline:
```
seed_demo_user.py → test:e2e:demo → make_demo_gifs.py → generate_demo_doc.py → make_teaser_mp4.py → build_jury_kit.py
```

В `package.json`:
```json
"demo:kit": "python scripts/seed_demo_user.py --fresh && playwright test --project=demo && python scripts/make_demo_gifs.py && python scripts/generate_demo_doc.py && python scripts/make_teaser_mp4.py && python scripts/build_jury_kit.py"
```

### 5.2 Обновить документы

- `doc/user_guide.md` — в «Для жюри» добавить строку: «🎬 **`dist/home-rag_teaser_*.mp4`** — 60-секундный тизер для быстрого превью без запуска продукта».
- `doc/presenter_script.md` — страховка: «Если компьютер жюри не тянет живое демо — открой MP4».
- `doc/pitch.md` — в конце добавить placeholder QR/ссылку на YouTube-видео.

---

## 6. Порядок работы для Sonnet 4.6

**Сценарий 1: делать последовательно.**

1. Прочитать этот документ целиком.
2. Запустить разведку по подтверждению фактов (5–10 минут):
   - `rg _ensure_schema app/user_state_core.py` — убедиться, что имена таблиц совпадают.
   - `cat app/adaptive_plan.py | head -100` — подтвердить формат ADAPTIVE_DAILY_PLAN_KV_KEY.
   - `cat requirements.txt` — убедиться, что `imageio-ffmpeg` действительно отсутствует.
3. Реализовать F1 по чек-листу §3.8.
4. Прогнать `npm run demo:jury` на своей машине → проверить UI глазами.
5. Реализовать F2 по чек-листу §4.7.
6. Интегрировать в `demo:kit` по §5.
7. Финальный пакет: `npm run demo:kit` + визуальная проверка `dist/jury_kit_<date>.zip` и `dist/home-rag_teaser_<date>.mp4`.

**Сценарий 2: параллельная работа (если два агента).**
- Агент A: F1 (seed). Агент B: F2 (mp4). Не пересекаются. Интеграцию делает тот, кто закончит первым.

---

## 7. Необходимый контекст для открытия сессии Sonnet 4.6

При старте новой сессии дай модели:

### 7.1 Короткая вводная (copy-paste)

> Я работаю над `home-rag_v2` — локальным учебным RAG-продуктом для конкурса. Нужно реализовать две фичи из `doc/handoff_next_level.md`: (1) Seeded Demo User — сид БД + mini-KB так, чтобы `docker compose up` сразу показывал заполненный UI; (2) MP4-тизер 60 сек из готовых GIF через `imageio-ffmpeg`. Все факты об устройстве кода, таблицах БД, путях и подводных камнях — в `doc/handoff_next_level.md`. Начни с его чтения, потом следуй разделу §6 «Порядок работы».

### 7.2 Обязательные файлы для Read

Модель должна прочесть в первые 5 минут работы:

1. `doc/handoff_next_level.md` (этот файл) — целиком.
2. `app/user_state_core.py` — только `_ensure_schema()` (строки ~281–523) для точной схемы.
3. `app/user_state_flashcards.py` — функции `create_flashcard_deck`, `save_flashcards_to_deck`, `update_flashcard_sr`.
4. `app/adaptive_plan.py` — функция чтения плана (подтвердить формат KV).
5. `app/spaced_repetition.py` — `get_due_reviews` и writer-функции.
6. `ingest.py` + `app/ingestion.py` (первые 60 строк) — убедиться, что `data_dir` действительно жёстко `DATA_DIR`.
7. `scripts/make_demo_gifs.py` — понять, как читается YAML (переиспользовать подход в `make_teaser_mp4.py`).
8. `scripts/build_jury_kit.py` — куда добавить mp4.
9. `docker-compose.yml` и `Dockerfile` — чтобы не ломать компоуз.
10. `package.json` — паттерн команд для добавления новых.

### 7.3 Референсные артефакты (уже существуют)

- `doc/screenshots/scenario_01/demo.gif` (677 KB)
- `doc/screenshots/scenario_02/demo.gif` (591 KB)
- `doc/screenshots/scenario_05/demo.gif` (625 KB)
- `doc/screenshots/scenario_*/meta.json` — готовая структура метаданных.
- `doc/scenarios/scenario_*.yaml` — как устроены demo-манифесты.

### 7.4 Запрещённые модификации

- **Не менять** `app/user_state_core.py` (DDL схемы) — только читать. Если нужны новые поля — поднимать с пользователем.
- **Не трогать** существующие e2e-тесты кроме `tests/e2e/demos/`.
- **Не коммитить** `data/*`, `dist/*`, `doc/screenshots/scenario_*/*.png`, `doc/screenshots/scenario_*/*.gif` (они в `.gitignore`).
- **Не включать** `OPENAI_API_KEY` в seed-скрипты. Если скрипту нужен ключ — читать из `.env`.

---

## 8. Желательные будущие фичи (backlog, не в этой итерации)

Не реализовывать сейчас, но зафиксировать для записи в `doc/backlog_registry.yaml`:

1. **`docker-compose.override.yml` для CI** — автоматический seed при каждом `docker compose up` в чистом окружении.
2. **YouTube Shorts-версия** — MP4 9:16 (1080×1920), 30 сек, для мобильной аудитории. Просто отдельный конфиг `doc/teaser/montage_shorts.yaml`.
3. **GIF с субтитрами.** Сейчас GIF без текстовых подписей. Опция: наложить caption из YAML-манифеста на каждый кадр через Pillow перед сборкой GIF.
4. **Live HTML preview.** Отдельная HTML-страница `dist/jury/index.html`, которая встраивает GIF, MP4, ссылки на markdown. Для раздачи одной папкой без ZIP.
5. **Full cycle e2e scenario.** Один 90-секундный сценарий, который проходит весь учебный цикл (`scenario_flagship`), а не три отдельных. Для самого убедительного GIF/MP4.
6. **Seeded demo на двух языках.** Сейчас концепты на английском, описания на русском — миксованно. Разделить: `data/demo_ru/` и `data/demo_en/`, флаг `--lang`.
7. **«Anonymous telemetry» для жюри.** В Home — счётчик «вы запустили продукт X минут назад, освоили Y концептов». Эффект wow-демо без живого использования.

---

## 9. Если что-то пойдёт не по плану

Быстрые escape hatches:

- **Сид ломает UI:** удалить `data/user_state.db`, перезапустить `docker compose down && docker compose up`. UI создаст пустой state.
- **ffmpeg не найден:** `python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"` — проверить установку.
- **GIF для mp4 слишком мелкие:** пересобрать `make_demo_gifs.py --max-width 1280 --fps 1.5` — теперь GIF станут шире и плавнее.
- **ingest падает на demo-KB:** проверить `app/ingestion.py` — возможно нужен `EMBED_API_BASE` из `.env`. Fallback — использовать существующий `eval_data/` если он есть, или skip ingest и положить готовую `chroma_db/` через `git lfs`.

---

## 10. Метрики успеха (когда F1+F2 можно считать готовыми)

Критерии для self-review после реализации:

| Метрика | Целевое значение | Как измерить |
|---|---|---|
| Время от `git clone` до «UI с прогрессом» | ≤ 5 минут | Ручной прогон по README |
| Команды для жюри | ≤ 3 | `git clone`, `npm run demo:seed`, `docker compose up` |
| Размер MP4 | ≤ 20 MB | `ls -la dist/` |
| Длительность MP4 | 55–65 сек | `ffprobe` |
| Размер Jury Kit ZIP | ≤ 15 MB | `ls -la dist/` |
| E2E тесты (включая `scenario_00_seeded`) | все зелёные | `npm run test:e2e:demo` |
| GIF в `quickstart_demo.md` | ≥ 3 | визуальный inspection |

---

<sub>Документ написан: 2026-04-22. Автор: предыдущая сессия Claude Opus 4.7. Адресат: следующая сессия (Claude Sonnet 4.6 / medium-thinking).</sub>
