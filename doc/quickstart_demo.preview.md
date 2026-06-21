# Smart Demo — автоматически снятые кадры сценариев

> Документ собран из YAML-манифестов `doc/scenarios/*.yaml` и скриншотов из `doc/screenshots/final/<scenario_id>/` после `npm run test:e2e:demo` (съём в `doc/screenshots/<RUN>/`; перед этим генератор пересобирает `doc/screenshots/final/`, **ссылки ведут в `final/`**). Не правь вручную — манифесты и `python scripts/generate_demo_doc.py`.

## О чём этот документ

Каждый сценарий здесь — это последовательность **реальных кадров** из Streamlit UI, снятых Playwright'ом в ходе demo-теста. Это доказательство, что продукт делает то, что обещано в [user_scenarios.md](user_scenarios.md) и [quickstart.md](quickstart.md), — не рендеры, не мокапы.

## 🎓 Интерактивный тур внутри приложения — 5 глав

Новый формат Smart Demo доступен прямо в UI: на главном экране нажмите **«Пройти интерактивный тур (5 глав)»**.

- Глава 1: Первый ответ (~3 мин)
- Глава 2: От ответа к обучению (~5 мин)
- Глава 3: Возвращаюсь завтра (~4 мин)
- Глава 4: Flashcards и долгая память (~6 мин)
- Глава 5: Курс под ключ (~8 мин)

Overlay тура показывает текущую главу/шаг, ведёт по экранам и сохраняет прогресс между сессиями.

![Interactive Guide Overlay](screenshots/final/scenario_10/01_home_resume_card.png)

<sub>Существующие сценарии ниже сохранены как PR-витрина для внешнего просмотра.</sub>

## Оглавление

- [scenario_01 — Первый запуск: от папки до первого ответа](#scenario-01-первый-запуск-от-папки-до-первого-ответа) — ✅
- [scenario_03 — Ответ → Tutor за один клик](#scenario-03-ответ-→-tutor-за-один-клик) — ✅
- [scenario_04 — Мини-квиз: проверь понимание за 2 мин](#scenario-04-мини-квиз-проверь-понимание-за-2-мин) — ✅
- [scenario_05 — Flashcards: сгенерировать, отредактировать, сохранить](#scenario-05-flashcards-сгенерировать-отредактировать-сохранить) — ✅
- [scenario_06 — SRS: повторение по интервальному алгоритму](#scenario-06-srs-повторение-по-интервальному-алгоритму) — ✅
- [scenario_07 — Прогресс и слабые места](#scenario-07-прогресс-и-слабые-места) — ✅
- [scenario_09 — Персональный план обучения](#scenario-09-персональный-план-обучения) — ✅
- [scenario_10 — Возвращение на день 2: resume + soft-recovery](#scenario-10-возвращение-на-день-2-resume-+-soft-recovery) — ✅
- [scenario_11 — Flashcards → экспорт в Anki](#scenario-11-flashcards-→-экспорт-в-anki) — ✅
- [scenario_12 — Quiz → колода карточек](#scenario-12-quiz-→-колода-карточек) — ✅
- [scenario_13 — Course Workspace: полный цикл](#scenario-13-course-workspace-полный-цикл) — ✅
- [scenario_14 — Полный export/sync и восстановление](#scenario-14-полный-export/sync-и-восстановление) — ✅
- [scenario_02 — Home Mode Selector: навигация за 30 секунд](#scenario-02-home-mode-selector-навигация-за-30-секунд) — ⚠️ ещё не снят
- [scenario_08 — Доверие к ответу: источники и confidence](#scenario-08-доверие-к-ответу-источники-и-confidence) — ✅

## Покрытие

| ID | Название | Уровень | Кадров снято | LLM нужен | Статус |
|---|---|---|:---:|:---:|:---:|
| `scenario_01` | Первый запуск: от папки до первого ответа | 🟢 Первые шаги | 5/5 | нет | ✅ |
| `scenario_03` | Ответ → Tutor за один клик | 🟡 Learning loop | 5/5 | нет | ✅ |
| `scenario_04` | Мини-квиз: проверь понимание за 2 мин | 🟡 Learning loop | 4/4 | нет | ✅ |
| `scenario_05` | Flashcards: сгенерировать, отредактировать, сохранить | 🔵 Учебный ритм | 4/4 | нет | ✅ |
| `scenario_06` | SRS: повторение по интервальному алгоритму | 🟠 Retention engine | 5/5 | нет | ✅ |
| `scenario_07` | Прогресс и слабые места | 🟠 Retention engine | 4/4 | нет | ✅ |
| `scenario_09` | Персональный план обучения | 🔴 Orchestration | 5/5 | нет | ✅ |
| `scenario_10` | Возвращение на день 2: resume + soft-recovery | 🟠 Retention engine | 4/4 | нет | ✅ |
| `scenario_11` | Flashcards → экспорт в Anki | 🔵 Учебный ритм | 3/3 | нет | ✅ |
| `scenario_12` | Quiz → колода карточек | 🔵 Учебный ритм | 4/4 | нет | ✅ |
| `scenario_13` | Course Workspace: полный цикл | 🔴 Orchestration | 6/6 | нет | ✅ |
| `scenario_14` | Полный export/sync и восстановление | 🔴 Orchestration | 4/4 | нет | ✅ |
| `scenario_02` | Home Mode Selector: навигация за 30 секунд | 🟢 Первые шаги | 0/5 | нет | ⏸ |
| `scenario_08` | Доверие к ответу: источники и confidence | 🔵 Trust drill-down | 4/4 | нет | ✅ |


## scenario_01 — Первый запуск: от папки до первого ответа

**🟢 Первые шаги** · ⏱ 5 мин · 👤 Аня, студентка. Скачала home-rag впервые.

**Зачем:** За 5 минут превратить папку с конспектами в поисковую систему по своим материалам
с источниками. Момент, ради которого пользователь решает остаться.

> 🔥 **Wow-момент:** Ответ с confidence 87% и тремя фрагментами из реальных файлов пользователя —
клик по фрагменту открывает подсветку в исходнике.

### Анимированный разбор

![Первый запуск: от папки до первого ответа](screenshots/final/scenario_01/demo.gif)

<sub>файл: `doc/screenshots/final/scenario_01/demo.gif` · 769 KB · собран через `python scripts/make_demo_gifs.py`</sub>

<details><summary><b>Статичная раскадровка (кадр за кадром)</b></summary>

#### Шаг 1 — Home Mode Selector: 6 карточек режимов

![Home Mode Selector: 6 карточек режимов](screenshots/final/scenario_01/01_home_mode_selector.png)

_UI встречает шестью режимами, а не пустым чатом._

<sub>файл: `doc/screenshots/final/scenario_01/01_home_mode_selector.png` · ⏱ 3s</sub>

#### Шаг 2 — Быстрый ответ: готов принять вопрос

![Быстрый ответ: готов принять вопрос](screenshots/final/scenario_01/02_quick_answer_empty.png)

_Аня спрашивает как есть — без магических промптов._

<sub>файл: `doc/screenshots/final/scenario_01/02_quick_answer_empty.png` · ⏱ 3s</sub>

#### Шаг 3 — Ответ получен: confidence + источники

![Ответ получен: confidence + источники](screenshots/final/scenario_01/03_quick_answer_with_sources.png)

_Ответ — с confidence-оценкой и точными фрагментами из её лекций._

<sub>файл: `doc/screenshots/final/scenario_01/03_quick_answer_with_sources.png` · ⏱ 5s</sub>

#### Шаг 4 — Раскрытые источники с превью

![Раскрытые источники с превью](screenshots/final/scenario_01/04_sources_expanded.png)

_Никаких галлюцинаций: каждый тезис подкреплён фрагментом._

<sub>файл: `doc/screenshots/final/scenario_01/04_sources_expanded.png` · ⏱ 4s</sub>

#### Шаг 5 — Кнопка «Учить эту тему 5 минут»

![Кнопка «Учить эту тему 5 минут»](screenshots/final/scenario_01/05_learn_this_topic_cta.png)

_А если вдруг захотелось разобраться — одна кнопка превращает ответ в учебный разбор._

<sub>файл: `doc/screenshots/final/scenario_01/05_learn_this_topic_cta.png` · ⏱ 3s</sub>

</details>


<details><summary>Технические метаданные прогона</summary>

- Старт: `2026-04-25T16:42:11.753Z`  
- Финиш: `2026-04-25T16:43:06.175Z`  
- Статус: `passed`  
- Env: `E2E_API_PORT=18000, E2E_STREAMLIT_PORT=18501`

</details>

**Takeaway:** Положил папку → через 5 минут получил поиск по своим материалам
с источниками. Локально. Бесплатно по privacy.

[→ Полный сценарий в каталоге](user_scenarios.md#сценарий-1--первый-запуск-от-папки-до-первого-ответа)

---

## scenario_03 — Ответ → Tutor за один клик

**🟡 Learning loop** · ⏱ 5 мин · 👤 Аня после scenario_01. Хочет разобраться в теме глубже.

**Зачем:** Один клик превращает поисковый ответ в guided learning session без ручной
сборки промптов. Контекст (тема + исходный вопрос) передаётся автоматически.

> 🔥 **Wow-момент:** Один клик на «Учить эту тему 5 минут» — и Tutor уже знает вопрос,
тему и предлагает структурированный план разбора.

### Анимированный разбор

![Ответ → Tutor за один клик](screenshots/final/scenario_03/demo.gif)

<sub>файл: `doc/screenshots/final/scenario_03/demo.gif` · 637 KB · собран через `python scripts/make_demo_gifs.py`</sub>

<details><summary><b>Статичная раскадровка (кадр за кадром)</b></summary>

#### Шаг 1 — Готовый ответ с кнопкой «Учить эту тему 5 минут»

![Готовый ответ с кнопкой «Учить эту тему 5 минут»](screenshots/final/scenario_03/01_answer_with_learn_cta.png)

_Аня видит ответ — и прямо здесь предложение перейти в режим обучения._

<sub>файл: `doc/screenshots/final/scenario_03/01_answer_with_learn_cta.png` · ⏱ 3s</sub>

#### Шаг 2 — Tutor открыт: контекст темы и вопроса сохранён

![Tutor открыт: контекст темы и вопроса сохранён](screenshots/final/scenario_03/02_tutor_context_handoff.png)

_Переход без потери контекста — тема и исходный вопрос уже в Tutor._

<sub>файл: `doc/screenshots/final/scenario_03/02_tutor_context_handoff.png` · ⏱ 4s</sub>

#### Шаг 3 — План разбора темы: 3 шага

![План разбора темы: 3 шага](screenshots/final/scenario_03/03_tutor_topic_plan.png)

_Система предлагает структуру: что объяснить и в каком порядке._

<sub>файл: `doc/screenshots/final/scenario_03/03_tutor_topic_plan.png` · ⏱ 4s</sub>

#### Шаг 4 — Объяснение простыми словами — шаг 1

![Объяснение простыми словами — шаг 1](screenshots/final/scenario_03/04_tutor_simple_explanation.png)

_Первый шаг плана: концепция объяснена без жаргона._

<sub>файл: `doc/screenshots/final/scenario_03/04_tutor_simple_explanation.png` · ⏱ 5s</sub>

#### Шаг 5 — CTA «Следующий шаг: проверь понимание»

![CTA «Следующий шаг: проверь понимание»](screenshots/final/scenario_03/05_tutor_next_step_cta.png)

_Tutor сам предлагает перейти к проверке — мост к мини-квизу._

<sub>файл: `doc/screenshots/final/scenario_03/05_tutor_next_step_cta.png` · ⏱ 3s</sub>

</details>


<details><summary>Технические метаданные прогона</summary>

- Старт: `2026-04-25T16:43:41.738Z`  
- Финиш: `2026-04-25T16:44:57.114Z`  
- Статус: `passed`  
- Env: `E2E_API_PORT=18000, E2E_STREAMLIT_PORT=18501`

</details>

**Takeaway:** RAG-ответ — не конец пути, а точка входа в обучение.
Система сама передаёт контекст, студент не теряет нить.

[→ Полный сценарий в каталоге](user_scenarios.md#сценарий-3--ответ-tutor-за-один-клик)

---

## scenario_04 — Мини-квиз: проверь понимание за 2 мин

**🟡 Learning loop** · ⏱ 2 мин · 👤 Аня после scenario_03. Хочет убедиться, что поняла тему.

**Зачем:** После объяснения от Tutor — один клик запускает квиз.
Система генерирует вопрос по теме, показывает варианты и даёт
мгновенный feedback. Без переключения контекста.

> 🔥 **Wow-момент:** Вопрос уже по твоей теме — не надо ничего настраивать.
Выбрал ответ — сразу видишь ✅ или ❌ с объяснением.

### Анимированный разбор

![Мини-квиз: проверь понимание за 2 мин](screenshots/final/scenario_04/demo.gif)

<sub>файл: `doc/screenshots/final/scenario_04/demo.gif` · 489 KB · собран через `python scripts/make_demo_gifs.py`</sub>

<details><summary><b>Статичная раскадровка (кадр за кадром)</b></summary>

#### Шаг 1 — Вопрос квиза: 3 варианта ответа

![Вопрос квиза: 3 варианта ответа](screenshots/final/scenario_04/01_quiz_question_presented.png)

_Система сформулировала вопрос по теме — Аня выбирает из трёх._

<sub>файл: `doc/screenshots/final/scenario_04/01_quiz_question_presented.png` · ⏱ 3s</sub>

#### Шаг 2 — Выбранный вариант подсвечен

![Выбранный вариант подсвечен](screenshots/final/scenario_04/02_quiz_answer_selected.png)

_Один клик — вариант зафиксирован, ожидание feedback._

<sub>файл: `doc/screenshots/final/scenario_04/02_quiz_answer_selected.png` · ⏱ 2s</sub>

#### Шаг 3 — Feedback: ✅ правильно или ❌ + подсказка

![Feedback: ✅ правильно или ❌ + подсказка](screenshots/final/scenario_04/03_quiz_feedback_correct_or_hint.png)

_Мгновенный ответ с объяснением — не просто «неверно»._

<sub>файл: `doc/screenshots/final/scenario_04/03_quiz_feedback_correct_or_hint.png` · ⏱ 4s</sub>

#### Шаг 4 — CTA: «Создать flashcard» / «Продолжить»

![CTA: «Создать flashcard» / «Продолжить»](screenshots/final/scenario_04/04_quiz_next_action_cta.png)

_Правильно? Идём дальше. Ошиблись? Карточка в SRS-очередь._

<sub>файл: `doc/screenshots/final/scenario_04/04_quiz_next_action_cta.png` · ⏱ 3s</sub>

</details>


<details><summary>Технические метаданные прогона</summary>

- Старт: `2026-04-25T16:44:57.581Z`  
- Финиш: `2026-04-25T16:45:39.090Z`  
- Статус: `passed`  
- Env: `E2E_API_PORT=18000, E2E_STREAMLIT_PORT=18501`

</details>

**Takeaway:** Квиз встроен в поток: ответил → понял → проверил.
Нет отдельного «перейти в режим проверки».

[→ Полный сценарий в каталоге](user_scenarios.md#сценарий-4--мини-квиз)

---

## scenario_05 — Flashcards: сгенерировать, отредактировать, сохранить

**🔵 Учебный ритм** · ⏱ 5 мин · 👤 Аня, через неделю экзамен. Хочет колоду по главе 3.

**Зачем:** Показать, что home-rag заменяет ручное создание Anki-колод — с preview и редактированием.
Ни одна LLM-генерация не попадает в колоду без человеческой проверки.

> 🔥 **Wow-момент:** Редактируемый preview: правишь или удаляешь плохую карточку ДО сохранения.
Другие генераторы скидывают всё подряд.

### Анимированный разбор

![Flashcards: сгенерировать, отредактировать, сохранить](screenshots/final/scenario_05/demo.gif)

<sub>файл: `doc/screenshots/final/scenario_05/demo.gif` · 498 KB · собран через `python scripts/make_demo_gifs.py`</sub>

<details><summary><b>Статичная раскадровка (кадр за кадром)</b></summary>

#### Шаг 1 — Раздел Flashcards: три подвкладки

![Раздел Flashcards: три подвкладки](screenshots/final/scenario_05/01_flashcards_section.png)

_Три зоны: что есть, что создать, что повторить._

<sub>файл: `doc/screenshots/final/scenario_05/01_flashcards_section.png` · ⏱ 3s</sub>

#### Шаг 2 — Создание карточек: загрузка файла

![Создание карточек: загрузка файла](screenshots/final/scenario_05/02_create_new_upload.png)

_5–20 карточек из любого документа._

<sub>файл: `doc/screenshots/final/scenario_05/02_create_new_upload.png` · ⏱ 3s</sub>

#### Шаг 3 — Preview сгенерированных карточек

![Preview сгенерированных карточек](screenshots/final/scenario_05/03_preview_generated.png)

_LLM даёт first draft — человек проверяет._

<sub>файл: `doc/screenshots/final/scenario_05/03_preview_generated.png` · ⏱ 5s</sub>

#### Шаг 4 — Сохранение колоды

![Сохранение колоды](screenshots/final/scenario_05/04_save_deck.png)

_Минимум 5 валидных карточек — колода в базе._

<sub>файл: `doc/screenshots/final/scenario_05/04_save_deck.png` · ⏱ 3s</sub>

</details>


<details><summary>Технические метаданные прогона</summary>

- Старт: `2026-04-25T17:05:19.583Z`  
- Финиш: `2026-04-25T17:05:56.836Z`  
- Статус: `passed`  
- Env: `E2E_API_PORT=18000, E2E_STREAMLIT_PORT=18501`

</details>

**Takeaway:** Колода по главе — за минуту, не за час. И ты контролируешь каждую карточку.

[→ Полный сценарий в каталоге](user_scenarios.md#сценарий-5--flashcards-генерация-и-сохранение)

---

## scenario_06 — SRS: повторение по интервальному алгоритму

**🟠 Retention engine** · ⏱ 4 мин · 👤 Аня через 3 дня. Получила напоминание — пора повторить.

**Зачем:** Система сама знает, когда карточки пора повторить (SM-2 алгоритм).
Аня видит бейдж «К повторению: 12», открывает очередь,
оценивает карточки — система обновляет расписание автоматически.

> 🔥 **Wow-момент:** Система сама отслеживает что и когда повторять.
Аня не думает «надо бы повторить» — бейдж говорит за неё.

### Анимированный разбор

![SRS: повторение по интервальному алгоритму](screenshots/final/scenario_06/demo.gif)

<sub>файл: `doc/screenshots/final/scenario_06/demo.gif` · 649 KB · собран через `python scripts/make_demo_gifs.py`</sub>

<details><summary><b>Статичная раскадровка (кадр за кадром)</b></summary>

#### Шаг 1 — Бейдж «К повторению» на главном экране

![Бейдж «К повторению» на главном экране](screenshots/final/scenario_06/01_home_due_badge.png)

_Аня заходит — система уже знает: 12 карточек пора повторить._

<sub>файл: `doc/screenshots/final/scenario_06/01_home_due_badge.png` · ⏱ 3s</sub>

#### Шаг 2 — Очередь повторения открыта: верхняя карточка

![Очередь повторения открыта: верхняя карточка](screenshots/final/scenario_06/02_review_queue_opened.png)

_Одна карточка за раз — без перегрузки._

<sub>файл: `doc/screenshots/final/scenario_06/02_review_queue_opened.png` · ⏱ 3s</sub>

#### Шаг 3 — Карточка раскрыта: ответ + 4 кнопки SM-2

![Карточка раскрыта: ответ + 4 кнопки SM-2](screenshots/final/scenario_06/03_card_flipped_answer.png)

_Оцени насколько помнишь: от «Забыл» до «Легко»._

<sub>файл: `doc/screenshots/final/scenario_06/03_card_flipped_answer.png` · ⏱ 4s</sub>

#### Шаг 4 — Оценка выбрана — карточка уходит из очереди

![Оценка выбрана — карточка уходит из очереди](screenshots/final/scenario_06/04_grade_selected_state_update.png)

_Выбрал «Хорошо» — карточка переносится на +4 дня._

<sub>файл: `doc/screenshots/final/scenario_06/04_grade_selected_state_update.png` · ⏱ 3s</sub>

#### Шаг 5 — Прогресс очереди: «11 осталось, ~4 мин»

![Прогресс очереди: «11 осталось, ~4 мин»](screenshots/final/scenario_06/05_queue_progress.png)

_Видно сколько осталось и когда закончишь — не бесконечный список._

<sub>файл: `doc/screenshots/final/scenario_06/05_queue_progress.png` · ⏱ 3s</sub>

</details>


<details><summary>Технические метаданные прогона</summary>

- Старт: `2026-04-25T16:57:33.328Z`  
- Финиш: `2026-04-25T16:58:10.636Z`  
- Статус: `passed`  
- Env: `E2E_API_PORT=18000, E2E_STREAMLIT_PORT=18501`

</details>

**Takeaway:** Не надо вспоминать, что учил. Система помнит и сама напоминает.

[→ Полный сценарий в каталоге](user_scenarios.md#сценарий-6--srs-повторение)

---

## scenario_07 — Прогресс и слабые места

**🟠 Retention engine** · ⏱ 3 мин · 👤 Аня через неделю. Хочет понять, что усвоила, а что нет.

**Зачем:** Прогресс-дашборд показывает mastery по темам, streak и слабые места.
Аня видит не просто «сколько карточек сделано», а конкретные темы
с mastery < 50% и CTA «Разобрать» по каждой.

> 🔥 **Wow-момент:** Не надо гадать что учить дальше — система показывает три слабых темы
и предлагает разобрать прямо сейчас.

### Анимированный разбор

![Прогресс и слабые места](screenshots/final/scenario_07/demo.gif)

<sub>файл: `doc/screenshots/final/scenario_07/demo.gif` · 509 KB · собран через `python scripts/make_demo_gifs.py`</sub>

<details><summary><b>Статичная раскадровка (кадр за кадром)</b></summary>

#### Шаг 1 — Полоса прогресса: тема / mastery% / due / streak

![Полоса прогресса: тема / mastery% / due / streak](screenshots/final/scenario_07/01_progress_unified_strip.png)

_Один взгляд — вся картина: что знаешь, что пора повторить._

<sub>файл: `doc/screenshots/final/scenario_07/01_progress_unified_strip.png` · ⏱ 3s</sub>

#### Шаг 2 — График mastery за 7 дней

![График mastery за 7 дней](screenshots/final/scenario_07/02_mastery_timeline.png)

_Кривая роста — видно, что знания накапливаются._

<sub>файл: `doc/screenshots/final/scenario_07/02_mastery_timeline.png` · ⏱ 4s</sub>

#### Шаг 3 — Слабые темы (mastery < 50%) + CTA «Разобрать»

![Слабые темы (mastery < 50%) + CTA «Разобрать»](screenshots/final/scenario_07/03_weak_spots_panel.png)

_Три темы, требующие внимания — система сама их нашла._

<sub>файл: `doc/screenshots/final/scenario_07/03_weak_spots_panel.png` · ⏱ 4s</sub>

#### Шаг 4 — Streak 5 дней + предложение на сегодня

![Streak 5 дней + предложение на сегодня](screenshots/final/scenario_07/04_streak_and_next_action.png)

_Серия не прерывается — система знает когда ты учился._

<sub>файл: `doc/screenshots/final/scenario_07/04_streak_and_next_action.png` · ⏱ 3s</sub>

</details>


<details><summary>Технические метаданные прогона</summary>

- Старт: `2026-04-25T16:47:55.193Z`  
- Финиш: `2026-04-25T16:48:14.386Z`  
- Статус: `passed`  
- Env: `E2E_API_PORT=18000, E2E_STREAMLIT_PORT=18501`

</details>

**Takeaway:** Прогресс — это не счётчик карточек, а карта знаний.
Система ведёт к слабым местам сама.

[→ Полный сценарий в каталоге](user_scenarios.md#сценарий-7--прогресс-и-слабые-места)

---

## scenario_09 — Персональный план обучения

**🔴 Orchestration** · ⏱ 5 мин · 👤 Аня в начале недели. Хочет понять что учить на этой неделе.

**Зачем:** Система строит персональный план на неделю на основе weak spots,
истории сессий и целей. Аня видит не просто список тем,
а приоритеты с объяснением «Почему здесь» и CTA на сегодня.

> 🔥 **Wow-момент:** «Сегодня: разобрать X (8 мин)» — система знает твой темп
и строит план под него, а не под идеального студента.

### Анимированный разбор

![Персональный план обучения](screenshots/final/scenario_09/demo.gif)

<sub>файл: `doc/screenshots/final/scenario_09/demo.gif` · 661 KB · собран через `python scripts/make_demo_gifs.py`</sub>

<details><summary><b>Статичная раскадровка (кадр за кадром)</b></summary>

#### Шаг 1 — Обзор плана на неделю: 3 приоритетные темы

![Обзор плана на неделю: 3 приоритетные темы](screenshots/final/scenario_09/01_plan_overview.png)

_Система отобрала три темы — не весь учебник, а именно эти._

<sub>файл: `doc/screenshots/final/scenario_09/01_plan_overview.png` · ⏱ 4s</sub>

#### Шаг 2 — «Почему здесь»: weak spot по каждой теме

![«Почему здесь»: weak spot по каждой теме](screenshots/final/scenario_09/02_plan_derived_from_gaps.png)

_Не просто список — объяснение почему эта тема приоритетна._

<sub>файл: `doc/screenshots/final/scenario_09/02_plan_derived_from_gaps.png` · ⏱ 4s</sub>

#### Шаг 3 — Diff с прошлой сессией: что изменилось

![Diff с прошлой сессией: что изменилось](screenshots/final/scenario_09/03_plan_diff_since_last.png)

_План живёт вместе с прогрессом — обновился с последней сессии._

<sub>файл: `doc/screenshots/final/scenario_09/03_plan_diff_since_last.png` · ⏱ 3s</sub>

#### Шаг 4 — «Сегодня: разобрать X (8 мин)»

![«Сегодня: разобрать X (8 мин)»](screenshots/final/scenario_09/04_plan_today_action.png)

_Одно действие на сегодня — не список на неделю вперёд._

<sub>файл: `doc/screenshots/final/scenario_09/04_plan_today_action.png` · ⏱ 3s</sub>

#### Шаг 5 — Корректировка приоритета → пересчёт плана

![Корректировка приоритета → пересчёт плана](screenshots/final/scenario_09/05_plan_accepts_adjust.png)

_Сдвинула тему вниз — план пересчитался мгновенно._

<sub>файл: `doc/screenshots/final/scenario_09/05_plan_accepts_adjust.png` · ⏱ 4s</sub>

</details>


<details><summary>Технические метаданные прогона</summary>

- Старт: `2026-04-25T16:48:43.691Z`  
- Финиш: `2026-04-25T16:49:09.181Z`  
- Статус: `passed`  
- Env: `E2E_API_PORT=18000, E2E_STREAMLIT_PORT=18501`

</details>

**Takeaway:** Персональный план — это не расписание, а живой маршрут.
Он меняется с твоим прогрессом, без ручной настройки.

[→ Полный сценарий в каталоге](user_scenarios.md#сценарий-9--персональный-план)

---

## scenario_10 — Возвращение на день 2: resume + soft-recovery

**🟠 Retention engine** · ⏱ 4 мин · 👤 Аня после паузы. Хочет быстро восстановить ритм без перегруза.

**Зачем:** Показать, что после перерыва система даёт мягкий план возврата:
resume-карта, дозированная due-очередь и сохранённый прогресс после reindex.

> 🔥 **Wow-момент:** Просроченные повторения не обрушиваются сразу —
система распределяет нагрузку и сохраняет мотивацию.

<details><summary><b>Статичная раскадровка (кадр за кадром)</b></summary>

#### Шаг 1 — Resume-карта на главной

![Resume-карта на главной](screenshots/final/scenario_10/01_home_resume_card.png)

_Сразу видно, откуда продолжить и какой следующий шаг._

<sub>файл: `doc/screenshots/final/scenario_10/01_home_resume_card.png` · ⏱ 3s</sub>

#### Шаг 2 — План на сегодня с diff «что изменилось»

![План на сегодня с diff «что изменилось»](screenshots/final/scenario_10/02_plan_diff_today.png)

_План подстроился под паузу и текущий контекст._

<sub>файл: `doc/screenshots/final/scenario_10/02_plan_diff_today.png` · ⏱ 4s</sub>

#### Шаг 3 — Due-очередь после пропуска без перегруза

![Due-очередь после пропуска без перегруза](screenshots/final/scenario_10/03_due_queue_soft_recovery.png)

_Очередь распределена мягко, без лавины overdue._

<sub>файл: `doc/screenshots/final/scenario_10/03_due_queue_soft_recovery.png` · ⏱ 4s</sub>

#### Шаг 4 — Бейдж обновления профиля после reindex

![Бейдж обновления профиля после reindex](screenshots/final/scenario_10/04_reindex_profile_badge.png)

_Учебное состояние сохраняется после обновления индекса._

<sub>файл: `doc/screenshots/final/scenario_10/04_reindex_profile_badge.png` · ⏱ 3s</sub>

</details>


<details><summary>Технические метаданные прогона</summary>

- Старт: `2026-04-25T16:49:12.407Z`  
- Финиш: `2026-04-25T16:50:07.200Z`  
- Статус: `passed`  
- Env: `E2E_API_PORT=18000, E2E_STREAMLIT_PORT=18501`

</details>

**Takeaway:** На следующий день можно просто вернуться и продолжить с нужного шага.

[→ Полный сценарий в каталоге](user_scenarios.md#сценарий-10--day-2-resume-и-soft-recovery)

---

## scenario_11 — Flashcards → экспорт в Anki

**🔵 Учебный ритм** · ⏱ 3 мин · 👤 Аня хочет забрать колоду в Anki для внешнего повторения.

**Зачем:** Показать end-to-end путь от локальной колоды к экспорту, без потери структуры карточек.

> 🔥 **Wow-момент:** Один клик формирует пакет экспорта, который готов к импорту в Anki.

<details><summary><b>Статичная раскадровка (кадр за кадром)</b></summary>

#### Шаг 1 — Колода готова к экспорту

![Колода готова к экспорту](screenshots/final/scenario_11/01_flashcards_deck_ready.png)

_Карточки уже сохранены и доступны для выгрузки._

<sub>файл: `doc/screenshots/final/scenario_11/01_flashcards_deck_ready.png` · ⏱ 3s</sub>

#### Шаг 2 — Кнопка экспорта в Anki

![Кнопка экспорта в Anki](screenshots/final/scenario_11/02_export_button.png)

_Экспорт запускается из интерфейса без дополнительных шагов._

<sub>файл: `doc/screenshots/final/scenario_11/02_export_button.png` · ⏱ 3s</sub>

#### Шаг 3 — Подтверждение успешного экспорта

![Подтверждение успешного экспорта](screenshots/final/scenario_11/03_export_success.png)

_Система сообщает, что пакет для Anki сформирован._

<sub>файл: `doc/screenshots/final/scenario_11/03_export_success.png` · ⏱ 3s</sub>

</details>


<details><summary>Технические метаданные прогона</summary>

- Старт: `2026-04-25T16:50:09.246Z`  
- Финиш: `2026-04-25T16:50:54.521Z`  
- Статус: `passed`  
- Env: `E2E_API_PORT=18000, E2E_STREAMLIT_PORT=18501`

</details>

**Takeaway:** Локальная практика и внешний инструмент повторения работают в одной цепочке.

[→ Полный сценарий в каталоге](user_scenarios.md#сценарий-11--anki-export)

---

## scenario_12 — Quiz → колода карточек

**🔵 Учебный ритм** · ⏱ 4 мин · 👤 Аня хочет превратить ошибки из квиза в карточки на повторение.

**Зачем:** Показать цикл «проверка знаний → автоматическое усиление слабых мест».

> 🔥 **Wow-момент:** Результаты квиза сразу преобразуются в колоду для интервального повторения.

<details><summary><b>Статичная раскадровка (кадр за кадром)</b></summary>

#### Шаг 1 — Итоги квиза по теме

![Итоги квиза по теме](screenshots/final/scenario_12/01_quiz_summary.png)

_Видны сильные и слабые концепты._

<sub>файл: `doc/screenshots/final/scenario_12/01_quiz_summary.png` · ⏱ 3s</sub>

#### Шаг 2 — CTA «Сделать колоду из квиза»

![CTA «Сделать колоду из квиза»](screenshots/final/scenario_12/02_convert_to_deck.png)

_Переход к карточкам запускается напрямую из summary._

<sub>файл: `doc/screenshots/final/scenario_12/02_convert_to_deck.png` · ⏱ 3s</sub>

#### Шаг 3 — Предпросмотр карточек из ошибок

![Предпросмотр карточек из ошибок](screenshots/final/scenario_12/03_generated_cards_preview.png)

_Можно проверить и отредактировать карточки перед сохранением._

<sub>файл: `doc/screenshots/final/scenario_12/03_generated_cards_preview.png` · ⏱ 4s</sub>

#### Шаг 4 — Колода сохранена и готова к review

![Колода сохранена и готова к review](screenshots/final/scenario_12/04_saved_deck_review_ready.png)

_Новая колода сразу попадает в цикл повторений._

<sub>файл: `doc/screenshots/final/scenario_12/04_saved_deck_review_ready.png` · ⏱ 3s</sub>

</details>


<details><summary>Технические метаданные прогона</summary>

- Старт: `2026-04-25T16:50:54.733Z`  
- Финиш: `2026-04-25T16:51:06.162Z`  
- Статус: `passed`  
- Env: `E2E_API_PORT=18000, E2E_STREAMLIT_PORT=18501`

</details>

**Takeaway:** Ошибки становятся учебным активом, а не тупиком.

[→ Полный сценарий в каталоге](user_scenarios.md#сценарий-12--quiz-в-деck)

---

## scenario_13 — Course Workspace: полный цикл

**🔴 Orchestration** · ⏱ 8 мин · 👤 Аня запускает обучение по целому курсу из папки.

**Зачем:** Показать весь pipeline курса: активация области, scoped-вопросы, план, карточки,
tutor-поддержка и сигнал mastery/graduation.

> 🔥 **Wow-момент:** За одну сессию проходит полный цикл «курс активирован → освоение подтверждено».

<details><summary><b>Статичная раскадровка (кадр за кадром)</b></summary>

#### Шаг 1 — Активация папки как курса

![Активация папки как курса](screenshots/final/scenario_13/01_activate_course_scope.png)

_Курс выбирается в Темах и становится активной областью._

<sub>файл: `doc/screenshots/final/scenario_13/01_activate_course_scope.png` · ⏱ 4s</sub>

#### Шаг 2 — Scoped быстрый ответ внутри курса

![Scoped быстрый ответ внутри курса](screenshots/final/scenario_13/02_scoped_quick_answer.png)

_Запросы автоматически ограничены материалами курса._

<sub>файл: `doc/screenshots/final/scenario_13/02_scoped_quick_answer.png` · ⏱ 4s</sub>

#### Шаг 3 — План изучения курса

![План изучения курса](screenshots/final/scenario_13/03_course_plan.png)

_План формируется на основе структуры и текущего прогресса._

<sub>файл: `doc/screenshots/final/scenario_13/03_course_plan.png` · ⏱ 4s</sub>

#### Шаг 4 — Генерация карточек курса

![Генерация карточек курса](screenshots/final/scenario_13/04_course_flashcards.png)

_Карточки запускают закрепление ключевых концептов._

<sub>файл: `doc/screenshots/final/scenario_13/04_course_flashcards.png` · ⏱ 4s</sub>

#### Шаг 5 — Маршрут «Не знаю» через Tutor

![Маршрут «Не знаю» через Tutor](screenshots/final/scenario_13/05_tutor_unknown_recovery.png)

_Тьютор помогает пройти сложные места без срыва сессии._

<sub>файл: `doc/screenshots/final/scenario_13/05_tutor_unknown_recovery.png` · ⏱ 4s</sub>

#### Шаг 6 — Dashboard курса и mastery

![Dashboard курса и mastery](screenshots/final/scenario_13/06_course_mastery_dashboard.png)

_Видно рост mastery и сигнал graduation по курсу._

<sub>файл: `doc/screenshots/final/scenario_13/06_course_mastery_dashboard.png` · ⏱ 4s</sub>

</details>


<details><summary>Технические метаданные прогона</summary>

- Старт: `2026-04-25T16:51:06.527Z`  
- Финиш: `2026-04-25T16:52:21.004Z`  
- Статус: `passed`  
- Env: `E2E_API_PORT=18000, E2E_STREAMLIT_PORT=18501`

</details>

**Takeaway:** Course Mode делает обучение управляемым и измеримым на уровне целой папки.

[→ Полный сценарий в каталоге](user_scenarios.md#сценарий-13--course-workspace-цикл)

---

## scenario_14 — Полный export/sync и восстановление

**🔴 Orchestration** · ⏱ 5 мин · 👤 Аня переносит учебное состояние между устройствами.

**Зачем:** Проверить, что прогресс, карточки и профиль можно безопасно экспортировать и восстановить.

> 🔥 **Wow-момент:** Полный пакет sync восстанавливает состояние обучения без ручной сборки данных.

<details><summary><b>Статичная раскадровка (кадр за кадром)</b></summary>

#### Шаг 1 — Открыты expert controls синхронизации

![Открыты expert controls синхронизации](screenshots/final/scenario_14/01_open_sync_controls.png)

_В одном месте собраны export/import действия._

<sub>файл: `doc/screenshots/final/scenario_14/01_open_sync_controls.png` · ⏱ 3s</sub>

#### Шаг 2 — Экспорт полного sync-bundle

![Экспорт полного sync-bundle](screenshots/final/scenario_14/02_export_bundle.png)

_Файл включает learner state, прогресс и учебные артефакты._

<sub>файл: `doc/screenshots/final/scenario_14/02_export_bundle.png` · ⏱ 3s</sub>

#### Шаг 3 — Импорт и восстановление

![Импорт и восстановление](screenshots/final/scenario_14/03_import_bundle.png)

_После импорта система подтверждает восстановление состояния._

<sub>файл: `doc/screenshots/final/scenario_14/03_import_bundle.png` · ⏱ 4s</sub>

#### Шаг 4 — Проверка после restore

![Проверка после restore](screenshots/final/scenario_14/04_post_restore_validation.png)

_Resume, due-очередь и прогресс доступны сразу._

<sub>файл: `doc/screenshots/final/scenario_14/04_post_restore_validation.png` · ⏱ 3s</sub>

</details>


<details><summary>Технические метаданные прогона</summary>

- Старт: `2026-04-25T16:52:23.811Z`  
- Финиш: `2026-04-25T16:52:48.438Z`  
- Статус: `passed`  
- Env: `E2E_API_PORT=18000, E2E_STREAMLIT_PORT=18501`

</details>

**Takeaway:** Экосистема обучения переносима: можно продолжить с того же места на другом окружении.

[→ Полный сценарий в каталоге](user_scenarios.md#сценарий-14--full-sync-export-import)

---

## scenario_02 — Home Mode Selector: навигация за 30 секунд

**🟢 Первые шаги** · ⏱ 1 мин · 👤 Максим, пользователь второго дня. Проверяет, где что лежит.

**Зачем:** Показать, что главный экран — это 6 режимов с ясной навигацией, а не набор
виджетов-конкурентов.

> 🔥 **Wow-момент:** Два клика — и ты в нужном режиме. Все вторичные инструменты собраны в collapsed-блоке,
чтобы не спорить с основным выбором.

> ⚠️ Кадры ещё не снимались. Запусти `npm run test:e2e:demo` и повтори генерацию документа.

**Takeaway:** Home Mode Selector решает pain «10 равных действий вместо одного next step»
(см. CJM moment of truth #10 и #13).

[→ Полный сценарий в каталоге](user_scenarios.md)

---

## scenario_08 — Доверие к ответу: источники и confidence

**🔵 Trust drill-down** · ⏱ 2 мин · 👤 Аня скептически смотрит на ответ. Хочет проверить источники.

**Зачем:** RAG-ответ без источников — это просто текст. С источниками — это документ
с доказательной базой. Аня видит confidence-чип, список источников
с match-score, и может раскрыть фрагмент прямо в интерфейсе.

> 🔥 **Wow-момент:** Нажала на источник — видит точный фрагмент из лекции.
Нет «AI сказал» — есть «профессор написал на стр. 12».

### Анимированный разбор

![Доверие к ответу: источники и confidence](screenshots/final/scenario_08/demo.gif)

<sub>файл: `doc/screenshots/final/scenario_08/demo.gif` · 517 KB · собран через `python scripts/make_demo_gifs.py`</sub>

<details><summary><b>Статичная раскадровка (кадр за кадром)</b></summary>

#### Шаг 1 — Ответ + чип «Confidence 87%»

![Ответ + чип «Confidence 87%»](screenshots/final/scenario_08/01_answer_with_confidence_chip.png)

_Система сама показывает насколько уверена в ответе._

<sub>файл: `doc/screenshots/final/scenario_08/01_answer_with_confidence_chip.png` · ⏱ 3s</sub>

#### Шаг 2 — 3 источника с именами файлов и match-score

![3 источника с именами файлов и match-score](screenshots/final/scenario_08/02_three_sources_listed.png)

_Каждый источник — с весом релевантности, не просто список._

<sub>файл: `doc/screenshots/final/scenario_08/02_three_sources_listed.png` · ⏱ 4s</sub>

#### Шаг 3 — Фрагмент источника с подсвеченным текстом

![Фрагмент источника с подсвеченным текстом](screenshots/final/scenario_08/03_source_preview_expanded.png)

_Раскрыла источник — видит точный абзац из лекции._

<sub>файл: `doc/screenshots/final/scenario_08/03_source_preview_expanded.png` · ⏱ 4s</sub>

#### Шаг 4 — Deep link к строке в исходном файле

![Deep link к строке в исходном файле](screenshots/final/scenario_08/04_jump_to_file_at_line.png)

_Хочет читать полный контекст — один клик до файла._

<sub>файл: `doc/screenshots/final/scenario_08/04_jump_to_file_at_line.png` · ⏱ 3s</sub>

</details>


<details><summary>Технические метаданные прогона</summary>

- Старт: `2026-04-25T16:48:16.120Z`  
- Финиш: `2026-04-25T16:48:41.132Z`  
- Статус: `passed`  
- Env: `E2E_API_PORT=18000, E2E_STREAMLIT_PORT=18501`

</details>

**Takeaway:** Confidence + источники превращают ответ в доверенный документ.
Галлюцинации проверяемы — это и есть доверие.

[→ Полный сценарий в каталоге](user_scenarios.md#сценарий-8--доверие-к-ответу)

---
_Документ сгенерирован `scripts/generate_demo_doc.py`. См. [scenarios/README.md](scenarios/README.md) — как добавить новый сценарий, и [screenshots/README.md](screenshots/README.md) — как устроены артефакты._
