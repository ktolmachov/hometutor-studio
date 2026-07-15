# hometutor 101 — учебный курс для новичков

Курс «от папки с лекциями до карты знаний»: 6 уроков, каждый — одна большая
идея и одно новое «могу сам». Произведён эволюционным разбором №16
([`../../presentations/evolutionary_analyses/16_beginner_course.html`](../../presentations/evolutionary_analyses/16_beginner_course.html))
по варианту шаблона «разбор-обучение»
([`evolutionary_analysis_guide.md` §2.1](../../presentations/evolutionary_analysis_guide.md)).

**Планка курса:** каждый экран, кнопка и число в материалах существуют в
продукте. На момент P1-финала `2026-07-14` курс был сверен с витриной
сценариев runtime-репозитория `hometutor/docs/quickstart_demo.md` (38
сценариев; `scenario_36–38` закрывают недостающие кадры курса) и рабочим
состоянием hometutor на HEAD `6a3dddbae`. Production-кадры для видео хранятся
в studio-репозитории: `hometutor-studio/doc/screenshots/final/`. При пересборке
витрины HEAD/stamp нужно обновлять явно, а не считать текущим автоматически.

## Программа

| Урок | Большая идея | «Могу сам» после урока |
|---|---|---|
| 1. Первый ответ | Папка становится репетитором | Получить ответ по своей папке и проверить источник кликом |
| 2. Петля памяти | Знание закрепляет «вспомнил вовремя» | Пройти петлю ответ → тьютор → квиз → карточки; вернуться на бейдж «К повторению» |
| 3. Один следующий шаг | Навигатор, а не карта | Начать день с «Сейчас важнее…», прочитать «почему» и квитанцию «было → стало» |
| 4. Карта знаний | Прогресс — местность, а не число | Найти слабый узел, пройти «Авто: маршрут дня», скачать живую карту (HTML) |
| 5. Конспект с паспортом | Конспект — собеседник | Прочитать рубрику качества, отметить статусы, закрыть свой вопрос у тьютора |
| 6. Хозяин системы | Доверие проверяется в плохой день | Пережить честный сбой, знать офлайн-ядро, сделать полный экспорт |

## Структура папки

```
hometutor_101/
├── README.md                ← этот файл
├── lectures/                ← 6 лекций (markdown, пригодны для индексации продуктом)
├── konspekts/               ← 6 конспектов формата smart-конспекта
│                              (обязательная «Рубрика качества конспекта»;
│                               все проходят scripts/validate_smart_konspekt.py --profile local)
├── video_scripts/           ← 6 сценариев коротких видео (60–90 сек)
│                              (раскадровки на реальных кадрах
│                               hometutor-studio/doc/screenshots/final/)
├── videos/                  ← 6 собранных MP4-роликов курса (без звука;
│                              см. «Видео / P1 закрыт» ниже — почему)
└── slides/
    └── hometutor_101_deck.html  ← слайды курса, 16 слайдов 16:9
                                    (самодостаточный HTML; F = печать в PDF)
```

## 🐶 Dogfood: как пройти курс внутри самого hometutor

Продукт умеет учить чему угодно из папки markdown-файлов. Курс о продукте —
это папка markdown-файлов. Поэтому:

1. Из studio-репозитория `D:\Projects\hometutor-studio\doc\courses\hometutor_101\`
   скопируй в data-папку приложения только учебные markdown-материалы:
   `README.md`, `lectures/` и `konspekts/`.

   Для runtime-репозитория hometutor:

   ```powershell
   $src = "D:\Projects\hometutor-studio\doc\courses\hometutor_101"
   $dst = "D:\Projects\hometutor\data\uploads\hometutor_101"
   New-Item -ItemType Directory -Force $dst | Out-Null
   Copy-Item "$src\README.md" $dst -Force
   Copy-Item "$src\lectures"  $dst -Recurse -Force
   Copy-Item "$src\konspekts" $dst -Recurse -Force
   ```

   Для рабочей data-папки `D:\AI\app\data\`:

   ```powershell
   $src = "D:\Projects\hometutor-studio\doc\courses\hometutor_101"
   $dst = "D:\AI\app\data\uploads\hometutor_101"
   New-Item -ItemType Directory -Force $dst | Out-Null
   Copy-Item "$src\README.md" $dst -Force
   Copy-Item "$src\lectures"  $dst -Recurse -Force
   Copy-Item "$src\konspekts" $dst -Recurse -Force
   ```

   **Демо-режим** (`scripts/build_demo_chroma.py`) индексирует не `data\`, а
   `demo_data\` (`HOME_RAG_DATA_DIR=demo_data`). Если курс поднимается как демо,
   целевая data-папка —
   `D:\Projects\hometutor\demo_data\uploads\hometutor_101` (туда же `videos/`,
   там же запускается `attach_whole_lesson_video.py`). Пути в sidecar —
   data-relative (`uploads/hometutor_101/...`), поэтому копия портируется между
   любыми DATA_DIR без правок, лишь бы сохранялась структура `uploads/hometutor_101/`.

   Не копируй в текстовый корпус `video_scripts/`, `video_scripts/_build/` и
   `slides/`: это production-артефакты, а не основной учебный материал. Особенно
   `slides/`: ingestion встраивает `.html` как документ (`app/ingestion.py`,
   `HTMLTextReader`), так что дек внутри `uploads/hometutor_101/` попал бы в RAG
   мусорным дублёром лекций.

   Для **текстового dogfood** этого достаточно. Для **мультимедийного Living
   Konspekt** дополнительно скопируй `videos/` внутрь той же data-папки курса:

   ```powershell
   Copy-Item "$src\videos" $dst -Recurse -Force
   ```

   Локальные видео для `media_sidecar` должны лежать внутри `DATA_DIR`
   (`D:\AI\app\data\...` или `D:\Projects\hometutor\data\...`): приложение
   отклоняет абсолютные пути и файлы вне data-папки. При этом `.mp4` не попадают
   в текстовый индекс — ingestion берёт `.pdf`, `.txt`, `.md`, `.docx`, `.html`,
   но не видеофайлы.
2. Запусти переиндексацию в приложении.
3. Если нужен мультимедийный режим, прикрепи ролики к data-копиям конспектов как
   «видео урока целиком» (Tier A, без фейковых таймкодов):

   ```powershell
   cd D:\Projects\hometutor
   .\.venv\Scripts\python.exe scripts\attach_whole_lesson_video.py "uploads/hometutor_101/konspekts/urok_1_pervyi_otvet.konspekt.md" --video "uploads/hometutor_101/videos/video_1_pervyi_otvet.mp4" --title "Урок 1 · Первый ответ" --force
   .\.venv\Scripts\python.exe scripts\attach_whole_lesson_video.py "uploads/hometutor_101/konspekts/urok_2_petlya_pamyati.konspekt.md" --video "uploads/hometutor_101/videos/video_2_petlya_pamyati.mp4" --title "Урок 2 · Петля памяти" --force
   .\.venv\Scripts\python.exe scripts\attach_whole_lesson_video.py "uploads/hometutor_101/konspekts/urok_3_odin_sleduyushchiy_shag.konspekt.md" --video "uploads/hometutor_101/videos/video_3_odin_shag.mp4" --title "Урок 3 · Один следующий шаг" --force
   .\.venv\Scripts\python.exe scripts\attach_whole_lesson_video.py "uploads/hometutor_101/konspekts/urok_4_karta_znaniy.konspekt.md" --video "uploads/hometutor_101/videos/video_4_karta_znaniy.mp4" --title "Урок 4 · Карта знаний" --force
   .\.venv\Scripts\python.exe scripts\attach_whole_lesson_video.py "uploads/hometutor_101/konspekts/urok_5_konspekt_s_pasportom.konspekt.md" --video "uploads/hometutor_101/videos/video_5_konspekt_s_pasportom.mp4" --title "Урок 5 · Конспект с паспортом" --force
   .\.venv\Scripts\python.exe scripts\attach_whole_lesson_video.py "uploads/hometutor_101/konspekts/urok_6_khozyain_sistemy.konspekt.md" --video "uploads/hometutor_101/videos/video_6_khozyain_sistemy.mp4" --title "Урок 6 · Хозяин системы" --force
   ```

   Эти ролики — короткие silent/promotional MP4, поэтому ASR-конвейер
   `Run-MediaKonspektBatch.ps1` для них не запускать: он нужен для настоящих
   озвученных лекций и потаймкодового выравнивания разделов. Текущий честный
   режим курса — панель `🎞 Все видео урока` в Living Konspekt.
4. Проверь петлю на самом курсе:
   - спроси в «Быстром ответе»: *«что делает кнопка „Авто: маршрут дня“?»* —
     и раскрой источники (должен найтись урок 4);
   - нажми «Учить эту тему 5 минут» → квиз → карточки: первая карточка
     о самом продукте попадёт в SM-2;
   - открой конспекты курса в продукте — их рубрики качества читаются как
     паспорта (фича разбора №14);
   - если индексация, извлечение концептов и сборка графа прошли успешно,
     у курса появится собственная карта знаний — карта знаний курса о карте
     знаний.

Так курс одновременно учит продукту и тестирует его.

## Производство и обновление

- **Правило витрины:** ни одного выдуманного экрана. Изменился UI — сначала
  пересъёмка сценария в витрине, потом правка лекции/раскадровки. Мокапы
  запрещены. Для фактов читать runtime-документ `hometutor/docs/quickstart_demo.md`;
  для видео брать опубликованные кадры из `hometutor-studio/doc/screenshots/final/`.
- **Конспекты** после любой правки прогонять:
  из `D:\Projects\hometutor-studio` командой
  `.\.venv\Scripts\python.exe scripts\validate_smart_konspekt.py doc\courses\hometutor_101\konspekts\<файл> --profile local`
  (все шесть выпускались со статусом OK).
- **Видео / P1 закрыт**: недостающие экранные состояния сняты реальными
  Playwright-кадрами и опубликованы в витрине:
  `scenario_36/01_route_day_auto.png` («Авто: маршрут дня»),
  `scenario_37/01_konspekt_quality_passport.png`,
  `scenario_37/02_konspekt_status_controls.png`,
  `scenario_37/03_konspekt_status_counters.png` и
  `scenario_38/01_appearance_worlds.png`. Шесть MP4-роликов собраны в
  `doc/courses/hometutor_101/videos/` (звука нет — см. видео-сценарии,
  `*.silent.mp4`-дубликаты удалены как мёртвый вес). Проверка воспроизводима
  двумя штатными инструментами: `validate_smart_konspekt.py --profile local`
  на всех шести конспектах (OK×6) и `load_media_sidecar_for_konspekt()` на
  data-копиях после `attach_whole_lesson_video.py` (видео резолвится,
  `sidecar_stale_reasons()` пусто).
- **Слайды** — по [`html_deck_guide.md`](../../presentations/html_deck_guide.md);
  палитру дека не смешивать с notebook-стилем разборов. Runtime-копия дека лежит
  **вне** индексируемого data-дира:
  `hometutor/docs/courses/hometutor_101/slides/hometutor_101_deck.html`
  (не в `demo_data/uploads/...`, иначе дек уйдёт в RAG — см. dogfood выше).

---

<sub>hometutor 101 · v1.0 · 2026-07-14 · выпущен разбором №16 (первый разбор
типа «обучение»). Вопросы качества конспектов — см. разбор №14, факт-банк —
разбор №11 и `docs/quickstart_demo.md`.</sub>
