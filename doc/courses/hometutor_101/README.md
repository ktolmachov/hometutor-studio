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
├── videos/                  ← 6 собранных MP4-роликов курса
│                              (`*.silent.mp4` — варианты без озвучки)
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

   Не копируй в индекс `video_scripts/`, `video_scripts/_build/`, `videos/` и
   `slides/`: это production/media-артефакты, а не основной учебный корпус.
   Готовые MP4 можно хранить рядом как медиа-выдачу курса, например в
   `D:\AI\app\data\uploads\hometutor_101_media\videos\`.
2. Запусти переиндексацию в приложении.
3. Проверь петлю на самом курсе:
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
  `doc/courses/hometutor_101/videos/`. Финальная проверка:
  `07_final_gate.ps1 -RequireVideos` → `Final gate passed`.
- **Слайды** — по [`html_deck_guide.md`](../../presentations/html_deck_guide.md);
  палитру дека не смешивать с notebook-стилем разборов.

---

<sub>hometutor 101 · v1.0 · 2026-07-14 · выпущен разбором №16 (первый разбор
типа «обучение»). Вопросы качества конспектов — см. разбор №14, факт-банк —
разбор №11 и `docs/quickstart_demo.md`.</sub>
