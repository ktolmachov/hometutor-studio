# Гайд: генерация полированного самодостаточного HTML-дека

> **Что это.** Воспроизводимая методика, по которой собран
> [`defense_presentation_v5.html`](defense_presentation_v5.html). Один файл `.html`,
> без внешних зависимостей и без хрупких путей к скриншотам: открывается в любом
> браузере, листается с клавиатуры, печатается в PDF клавишей `F`.
>
> **Зачем отдельный формат.** После миграции `home-rag_v2 → hometutor + hometutor-studio`
> matplotlib-пайплайн v4 и его картинки (`screenshots/2026-06-20/...`) разъехались по
> двум репозиториям → битые изображения. Самодостаточный HTML это исключает: вся
> графика — инлайновый SVG, всё оформление — внутренний CSS.
>
> **Версия гайда:** 1.0 (2026-06-23). Эталон: `defense_presentation_v5.html`.

---

## 0. TL;DR — как сделать новый дек за 6 шагов

1. **Собери факты** из репозиториев (раздел 1) — никаких чисел «по памяти».
2. **Скопируй каркас** `defense_presentation_v5.html` как шаблон.
3. **Замени `:root`-токены**, если нужна другая палитра (раздел 3).
4. **Наполни слайды** из библиотеки компонентов (раздел 5).
5. **Проверь** по чек-листу (раздел 8): нумерация слайдов, печать, факты.
6. **Экспортируй PDF** (раздел 7) при необходимости.

Каркас неизменен: design-токены → слайды (`<section class="slide">`) → панель навигации → `<script>`. Меняется только содержимое слайдов и, опционально, палитра.

---

## 1. Сначала — факты, потом дизайн (правило фабрики)

Дек — это витрина, но числа в нём должны быть **воспроизводимы из репозиториев**.
Эталонный набор источников (резолвить пути по нужному репо: `hometutor` = CODE_ROOT,
`hometutor-studio` = DOCS_ROOT):

| Метрика | Команда / источник | Репо |
|---|---|---|
| User Stories | `user_stories_index.json` → `items[].status` | studio |
| Пакеты закрыто | `grep -c "status: closed" doc/backlog_registry.yaml` | studio |
| Волны завершено | `grep -c "status: completed" doc/backlog_registry.yaml` | studio |
| Тест-функции | `grep -rc "def test_" tests/` (суммировать) | studio |
| FastAPI endpoints | `grep -rE "@router\.(get\|post\|put\|delete\|patch)" app/routers/ \| wc -l` | product |
| ADR | `grep -cE "^\| ?ADR-" doc/adr.md` | studio |
| Архитектура / стек | `docs/architecture.md`, `docs/technical_specification.md` (актуальные по коду) | product |
| Local LLM throughput | последний benchmark-прогон (`doc/local_llm_*`) | studio |

**Правило:** каждое число на слайде «Метрики» должно иметь строку-источник.
Eval-метрики на demo-наборе — помечать явно («demo, N вопросов»).

> Помни про разъезд после миграции: проверь, что числа не взяты из старого дека.
> На 2026-06: US 96/96 (не 87), тесты 3 011 (не 3008), docs пересобраны 2026-06-23.

---

## 2. Анатомия файла

Один `.html`, четыре блока, строго в этом порядке:

```
<head>
  └─ <style>  ─ design-токены (:root) + классы компонентов + @media print
<body>
  ├─ .progress          ─ полоса прогресса сверху
  ├─ .hint              ─ подсказка управления (правый верх)
  ├─ .stage > .deck     ─ контейнер 16:9, внутри все <section class="slide">
  ├─ .nav               ─ ‹ счётчик ›
  └─ <script>           ─ навигация, клавиши, клик по краям, печать
```

Каждый слайд — `<section class="slide">`. Первый имеет класс `active`. Скрипт
показывает по одному. **Никаких внешних `<link>`, `<img src="http...">`, шрифтов
с CDN** — иначе теряется самодостаточность.

---

## 3. Design-токены (`:root`) — единственное место правки цвета

Вся палитра и геометрия — в CSS-переменных. Меняешь тему → меняешь только `:root`.

```css
:root{
  --bg:#0b1020; --bg2:#0e1430;            /* фон сцены */
  --panel:#141b38; --panel2:#1a2348;      /* карточки (градиент) */
  --ink:#eef2ff; --muted:#9aa6d4;         /* текст / приглушённый */
  --line:#283163;                         /* границы */
  --accent:#6d8bff; --accent2:#33e0c8;    /* акценты: индиго → циан */
  --gold:#ffcb6b; --good:#5ee0a0; --bad:#ff7a90;
  --grad:linear-gradient(120deg,#6d8bff,#33e0c8);  /* фирменный градиент */
  --shadow:0 20px 60px rgba(0,0,0,.45);
  --radius:18px;
  --font:'Segoe UI',system-ui,-apple-system,Roboto,Arial,sans-serif;
  --mono:'JetBrains Mono','Cascadia Code',Consolas,monospace;
}
```

**Светлая тема для раздаток (печать).** Подмени токены:
`--bg:#f6f8ff; --bg2:#ffffff; --panel:#ffffff; --panel2:#f0f3ff;
--ink:#12183a; --muted:#5a648c; --line:#d7ddf2`. Градиент-акценты оставить —
они читаются на обоих фонах.

**Фирменный приём — градиентный текст** (заголовок-акцент, цифры-метрики):

```css
.accent{ background:var(--grad); -webkit-background-clip:text;
         background-clip:text; color:transparent; }
```

---

## 4. Сетка слайда и три типа

Каждый слайд: `kicker` (номер + рубрика) → `h2` (заголовок с `<span class="accent">`)
→ опц. `.sub` → `.body` (контент, скроллится) → `.foot` (бренд + подпись).

**Тип A — контент** (большинство):
```html
<section class="slide">
  <div class="kicker"><span class="num">06</span> RAG — ядро системы</div>
  <h2>Пайплайн запроса <span class="accent">с заземлением</span></h2>
  <div class="sub">Один абзац-подзаголовок (опционально).</div>
  <div class="body"> … компоненты … </div>
  <div class="foot"><span class="brand"><span class="dot"></span>hometutor</span><span>RAG pipeline</span></div>
</section>
```

**Тип B — обложка** (`class="slide cover active"`): `.logo`, крупный `h1`, `.tag`,
ряд `.badge` в `.meta`.

**Тип C — разделитель/итог** (`class="slide divider"`): центрированный `.big`
+ ряд `.badge`. Радиальный фон уже в CSS.

> **Высота — главный риск.** Слайд имеет фикс. аспект 16:9. Контент должен влезать
> без скролла на 1080p. `.body` скроллится как страховка, но цель — чтобы скролла
> не было. Меньше текста, больше карточек; длинные списки → 2–3 колонки `.grid`.

---

## 5. Библиотека компонентов (копировать как есть)

| Компонент | Класс | Когда |
|---|---|---|
| Карточка | `.card` (+ `h3`, `p`, `ul`) | блок-контейнер, 2–3 в ряд |
| Сетка | `.grid.g2` / `.g3` | колонки |
| Цифры-метрики | `.stats > .stat (.v .l)` | KPI-слайд |
| Таблица | `<table>` | сравнения, статусы |
| Тезис/цитата | `.thesis` / `.thesis.small` | ключевая мысль |
| Моноблок-схема | `.flow` | ASCII-пайплайн, `white-space:pre` |
| Пилюли | `.pillrow > .pill` | теги стека / закрытого скоупа |
| Маркеры | `ul > li` | квадратный градиент-буллет авто |

**Семантические инлайн-классы текста:** `.accent-t` (циан), `.gold-t` (золото,
«новое/важное»), `.muted`, `.yes`/`.no`/`.part` в таблицах (зелёный/красный/жёлтый
для ✅/✗/частично).

**Цифровой KPI-слайд** — самый сильный визуально:
```html
<div class="stats">
  <div class="stat"><div class="v">96/96</div><div class="l">User Stories</div></div>
  <!-- 8 штук в сетке 4×2 -->
</div>
```

---

## 6. Диаграммы — инлайновый SVG, не картинки

Любая схема рисуется `<svg viewBox="0 0 W H">` прямо в слайде. Это и есть причина
самодостаточности. Паттерн:

```html
<div class="diagram">
  <svg viewBox="0 0 1000 250" width="100%" style="max-width:980px">
    <defs>
      <linearGradient id="gA" x1="0" x2="1">
        <stop offset="0" stop-color="#6d8bff"/><stop offset="1" stop-color="#33e0c8"/>
      </linearGradient>
    </defs>
    <!-- блок: rect + text -->
    <rect x="70" y="110" width="380" height="120" rx="14" fill="#141b38" stroke="url(#gA)"/>
    <text x="260" y="138" fill="#33e0c8" font-size="15" text-anchor="middle" font-weight="700">Заголовок</text>
    <!-- связь -->
    <path d="M500 60 L500 86" stroke="url(#gA)" stroke-width="2.5" fill="none"/>
  </svg>
</div>
```

Правила SVG:
- Цвета SVG **дублируют** значения токенов вручную (SVG не видит CSS-переменные
  при печати надёжно) — держи их синхронными с `:root`.
- `text-anchor="middle"`, `font-family` наследуется — стрелки `path` с
  `fill="none"`, циклические связи — `stroke-dasharray="5 5"`.
- Уникальные `id` градиентов на каждый SVG (`gA`, `gC`, `gJ`…), иначе конфликт.
- Использованы в v5: split-диаграмма миграции, цикл обучения (7 узлов + обратная
  связь), трёхслойный judge.

> Реальные скриншоты **можно** добавлять, но тогда встраивай их через
> `data:` base64 (`<img src="data:image/png;base64,…">`), чтобы не зависеть от путей.
> Для дека защиты предпочтительнее чистый SVG — он векторный и печатается резко.

---

## 7. Навигация и печать в PDF

**JS (≈25 строк, копировать целиком из эталона).** Даёт:
`←/→/PageUp/PageDown/Space` — листание; `Home/End` — края; `F` — печать; клик по
правой/левой половине дека — вперёд/назад; полоса `.progress` и счётчик `.nav`.
При смене слайда сбрасывает `scrollTop` у `.body`.

**Печать в PDF — критичный блок `@media print`:**
```css
@media print{
  @page{size:1280px 720px;margin:0}
  .stage{position:static;display:block}
  .deck{width:1280px;height:720px;max-height:none;aspect-ratio:auto}
  .slide{display:flex!important;position:relative;
    page-break-after:always;break-after:page;
    width:1280px;height:720px;border-radius:0;box-shadow:none;border:none}
  .nav,.progress,.hint{display:none!important}
}
```
Логика: в печати показываются **все** слайды (override `display:none`), каждый —
ровно одна страница 1280×720 (16:9), хром скрыт.

**Экспорт PDF:**
- Вручную: открыть в браузере → `F` (или Ctrl+P) → «Сохранить как PDF», поля
  «Нет», фон-графика **включена** (Chrome: «Background graphics»), размер из `@page`.
- Headless (Chrome/Edge):
  ```powershell
  & "C:\Program Files\Google\Chrome\Application\chrome.exe" `
    --headless --disable-gpu --no-pdf-header-footer `
    --print-to-pdf="defense_presentation_v5.pdf" `
    "file:///D:/Projects/hometutor-studio/doc/presentations/defense_presentation_v5.html"
  ```

---

## 8. Чек-лист перед сдачей

- [ ] Каждое число на «Метриках» имеет источник; ничего «по памяти»
- [ ] Числа сверены с текущими репо (не скопированы из прошлого дека)
- [ ] Ни одного внешнего ресурса: нет `http(s)://`, CDN-шрифтов, внешних `<img>`
- [ ] Все слайды влезают без скролла на 1080p (проверить визуально)
- [ ] `count` стартует `1 / N`, где **N = число `<section class="slide">`** (обновить!)
- [ ] У каждого SVG свой `id` градиента; цвета синхронны с `:root`
- [ ] Печать (`F`): все слайды, по одной странице, фон-графика на месте
- [ ] `.foot` подпись осмысленна на каждом слайде; первый слайд — `active`
- [ ] Рубрики `kicker .num` идут по порядку

---

## 9. Частые ошибки

| Симптом | Причина | Фикс |
|---|---|---|
| Счётчик врёт (`1 / 16`, а слайдов 15) | строка `count` или вёрстка разошлись | N считается из DOM автоматически; проверь, что не осталось `<section>` без `slide` |
| При печати белые слайды без фона | отключена фон-графика | в диалоге печати включить «Background graphics» |
| Контент уезжает за край | слишком много текста на слайде | резать текст, выносить в `.grid`/`.card`, дробить слайд |
| Градиент-текст невидим в Firefox-печати | `background-clip:text` | дублировать важное обычным `color` или печатать из Chrome/Edge |
| Два SVG «слиплись» по цвету | одинаковый `id` градиента | дать уникальные `id` |

---

## 10. Связанные файлы

- [`defense_presentation_v5.html`](defense_presentation_v5.html) — эталонный дек (шаблон)
- [`defense_presentation_v5.md`](defense_presentation_v5.md) — markdown-источник тех же 15 слайдов (текстовая правда)
- `hometutor/docs/architecture.md`, `hometutor/docs/technical_specification.md` — актуальная по коду архитектура/стек (CODE_ROOT)
- `doc/backlog_registry.yaml`, `doc/user_stories_index.json` — источники чисел

---

<sub>Гайд по полированному HTML-деку · v1.0 · 2026-06-23 · фабрика hometutor-studio.
Принцип: «факты из репозитория → токены → компоненты → печать». Самодостаточность — обязательна.</sub>
