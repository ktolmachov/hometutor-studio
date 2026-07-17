# Knowledge graph 3D: report of done work

**Дата:** 2026-07-16  
**Базовый план:** `doc/next/knowledge_graph_3d_plan.md`  
**Поправка после UX-аудита:** `doc/next/knowledge_graph_3d_reorientation_plan.md`  
**Runtime repo:** `D:\Projects\hometutor`  
**Статус:** кодовые P0/P1 по node-worth, day-route и offline 3D-export закрыты; после
визуального аудита B1 доведён от технического DoD до читаемой route-first сцены.

---

## Executive summary

План №15 начинался как «дать узлам цену, построить маршрут дня и вынести это в
самодостаточный 3D-зал». Техническая часть была закрыта: один payload, `day_route`,
offline HTML, canvas, без CDN, безопасная JSON-вставка, экспорт из UI.

После живых экспортов `knowledge_graph_3d (2).html` → `(7).html` стало видно, что
первый B1 закрывал контракт файла, но не контракт пользователя: сцена была похожа на
облако узлов без ориентиров. Поэтому была введена поправка №17: `route-first`, чистый
первый кадр, понятная дорожка `1 → N` (обычно шесть остановок), режимы
`Маршрут / Локально / Вся карта`.

Итог: 3D-зал больше не пытается первым экраном показать весь граф. Он открывается как
персональная маршрутная карта дня: шесть остановок, причина, следующий шаг, тихие
lesson-якоря и полный граф только по запросу.

---

## Status by original plan #15

| Пункт | Статус | Что фактически сделано | Evidence |
|---|---:|---|---|
| A1 «Цена на узле» | ✅ done | Узлы получают `due`, `novel`, `worth`, `worth_reason`; due больше не выбрасывается после сборки; novelty считается из личного слоя. | `app/ui/knowledge_graph_d3.py`, `app/ui/knowledge_graph_d3_analysis.py`, `tests/test_knowledge_graph_counters.py` |
| A2 «Маршрут дня по ценности» | ✅ done | `select_day_route(nodes, k=6)` строит серверный `day_route`; 2D и 3D используют один маршрут; каждая остановка имеет причину. | `app/ui/knowledge_graph_d3.py:636-657`, `app/ui/knowledge_graph_d3_analysis.py:234,386`, `app/ui/assets/knowledge_graph_d3_template.html:245,767` |
| B1 «3D-зал» | ✅ done after redesign | Offline HTML сохранён, но первый кадр пересобран из full graph в route scene: `1 → N`, active reason callout, hover reasons, click-to-local, quiet lesson anchors. | `app/ui/assets/kg_3d_template.html`, `app/ui/knowledge_graph_d3.py`, `tests/test_knowledge_graph_counters.py` |
| B2 audio/rubric in worth | ⏸ not done by design | Не включали в P0. Audio/rubric должны быть бейджами/действиями выбранного узла, а не причиной двигать геометрию или worth. | Решение из reorientation plan №17 |
| C1 3D iframe in product | ⏸ deferred | Не продвигалось. Экспорт должен доказать ориентацию до iframe. | План №15 / №17 |
| C2 route trace + metric age | ⏸ not done | След маршрута и возраст метрик остаются отдельной P2-волной. | План №15 |

---

## What changed in 3D hall

### 1. First frame is route-first, not full graph

- Default `viewMode = 'route'`.
- Первый кадр показывает маршрут дня и тихие lesson-якоря.
- Полный граф скрыт до режима **Вся карта**.
- Контекст активной остановки раскрывается в **Локально**, а не засоряет первый кадр.

**Evidence:** `app/ui/assets/kg_3d_template.html`
- `visibleIdSet()` разделяет `route / local / all`;
- `edgeVisibleInMode()` в route mode возвращает `false` для графовых рёбер;
- `scenePos()` сохраняет отдельную геометрию для route/local и исходную для all.

### 2. Route scene got its own geometry

- Добавлена `routeStopPos(id)`: остановки `1 → N` раскладываются как дорожка, а не
  прыгают по этажам уроков.
- Добавлена `lessonAnchorRoutePos(id)`: lesson-якоря ставятся рядом с маршрутом,
  но остаются тихими.
- Добавлена `drawRoutePlatform()`: простая платформа и направление `курс →`.
- `worth` не участвует в координатах; он остаётся rank/reason.

**Evidence:** `app/ui/assets/kg_3d_template.html:280,293,313,447`.

### 3. Camera and fit became product-facing

- `fitRouteCamera()` учитывает bounds маршрута, тихих lesson-якорей и платформы,
  затем делает screen-space подгонку под canvas.
- `Home` всегда возвращает в чистый route mode.
- Завершение тура тоже возвращает общий fit всего маршрута, а не оставляет пользователя
  на последней остановке в пустоте.
- Resize в route mode сразу делает refit, чтобы маршрут не уезжал после изменения окна.

**Evidence:** `routePlatformWorldPoints()`, `fitRouteCamera()`, `homebtn.onclick`,
`scheduleNextTour()`.

### 4. Tour is controlled, not timer jumps

- `tourState`: `idle`, `playing`, `paused`, `step`.
- Кнопки: назад, тур/пауза/продолжить, вперёд.
- Нет `setInterval`; используется управляемый state-machine + `setTimeout`/animation.
- `prefers-reduced-motion` учитывается.

**Evidence:** `tests/test_knowledge_graph_counters.py` проверяет наличие `tourState`
и отсутствие `setInterval`.

### 5. Visual noise reduced

- Убрана верхняя `topbar`, которая дублировала правую панель и обрезалась.
- Подписи маршрута проходят через `drawSmartLabel()` с collision-avoidance.
- Активная остановка получает canvas-callout `Стоп N/M · reason`; active/next labels
  получают приоритет перед остальными route labels.
- Hover показывает label/rank/reason в hint; клик по route stop раскрывает локальный
  контекст вместо простого центрирования камеры.
- Lesson-якоря в route mode стали маленькими, серыми, без подписей.
- Радиус route-stop ограничен, активное кольцо приглушено.
- Графовые рёбра в route mode не рисуются; пунктир маршрута остаётся главным каналом.
- Мёртвые audio/rubric бейджи удалены из шаблона до появления этих полей в payload.

**Evidence:** `drawSmartLabel()`, `labelIntersects()`, `quietRouteAnchor`,
`edgeVisibleInMode()`.

---

## DoD verification

| DoD | Result |
|---|---:|
| Offline HTML, no external scripts/CDN | ✅ tested |
| Same payload, no separate 3D schema | ✅ preserved |
| `DAY_ROUTE` embedded as id strings | ✅ tested |
| Route uses A2 server route | ✅ done |
| First frame is route mode | ✅ tested |
| Full graph only by request | ✅ done |
| Worth is rank/reason, not height | ✅ tested |
| Lesson order uses `precedes`, file variants collapse | ✅ tested in helper + shipped JS contract |
| Tour is controlled, no `setInterval` | ✅ tested |
| Safe script-context JSON escaping | ✅ tested |
| User guide updated | ✅ done |
| Active stop reason near point | ✅ implemented + contract-tested |
| Click in route opens local context | ✅ implemented + contract-tested |
| Resize refits route | ✅ implemented + contract-tested |
| Visual screenshot/canvas automation | ⚠️ opt-in Playwright smoke only; not mandatory CI |

Commands run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_knowledge_graph_counters.py
```

Result after route-hall hardening: normal targeted suite `39 passed, 1 skipped`
because the browser smoke is opt-in.

Opt-in visual smoke:

```powershell
$env:HT_RUN_KG_3D_VISUAL='1'
.\.venv\Scripts\python.exe -m pytest tests\test_knowledge_graph_counters.py::Test3DCoverageAndContracts::test_3d_visual_smoke_opt_in -q
```

Checks: generated offline HTML renders a non-empty canvas, opens in route mode, has no
topbar, exposes six stops in the sidebar, and passes both 1366x768 and 1920x1080
viewports. This is not a required CI check yet because Playwright browser binaries are
not a standard dependency. Latest local result: `1 passed`.

Additional check:

```powershell
node --check <extracted script from app/ui/assets/kg_3d_template.html>
```

Result: OK.

---

## Manual visual QA trail

The 3D export was iterated through live screenshots. These files are local QA artifacts,
not reproducible repository evidence; the reproducible evidence is the targeted unit
suite plus opt-in Playwright smoke.

- `(2)` — failed: full graph cloud, no floor/orientation/depth, unreadable.
- `(4)` — route visible, but still full graph with noisy context and clustered stops.
- `(5)` — route scene appears; context moved out, but labels/anchors still noisy.
- `(7)` — readable route map: six stops, quiet anchors, no topbar, no full-graph noise.
- Latest code after `(7)` additionally improves fit/centering and tour-completion reset.

Current expected first frame:

- route occupies meaningful canvas area;
- route stops visible as `1 → N` (standard A2 route = six stops);
- right panel names current stop, reason, and next stop;
- active stop also shows `Стоп N/M · reason` near the point on canvas;
- no topbar;
- route labels avoid overlaps where possible;
- hover explains reason/rank; click opens local context;
- `Home` and tour completion return to the same clean route overview.

---

## Files touched in runtime

Main implementation:

- `app/ui/assets/kg_3d_template.html`

Contracts/tests:

- `tests/test_knowledge_graph_counters.py`

Doc-sync:

- `docs/user_guide.md`

Previously involved plan/code surfaces:

- `app/ui/knowledge_graph_d3.py`
- `app/ui/knowledge_graph_d3_analysis.py`
- `app/ui/assets/knowledge_graph_d3_template.html`
- `app/ui/dashboards_graph.py`

---

## Product verdict

Original B1 should no longer be described simply as «3D-зал с полётом». The useful product
is:

> **offline route hall**: a self-contained daily route map over the knowledge graph.

The route hall is valuable because it compresses the graph into a human decision:

1. where I am;
2. where I go next;
3. why this stop is worth it.

That matches the North star from plan №15:

> время от открытия карты до старта достойной остановки — минуты → секунды;
> каждая остановка маршрута отвечает «почему я здесь» одной строкой.

---

## Remaining work

### Keep out of P0

- B2 audio/rubric in worth: keep as metadata/actions, not geometry.
- C1 iframe: wait until export route hall is accepted by actual use.
- C2 trace/exposure: separate product loop, not part of offline export polish.

### Useful next hardening

1. Promote the opt-in Playwright smoke to a stable CI job only if browser binaries become
   acceptable for the test environment.
2. Add a narrow-laptop viewport smoke after the desktop contract is stable.
3. Keep B2 audio/rubric as selected-node metadata/actions until those fields exist in
   the payload.
4. If 3D iframe is promoted into the product UI, require the same route-first contract
   before embedding.

---

## Commit note draft

```text
polish kg 3d export as route-first hall

- make 3D export open in sparse route mode instead of full graph
- add route-scene geometry, quiet lesson anchors, route platform and auto-fit
- add controlled tour state, Home reset, and tour completion reset
- reduce first-frame noise: no topbar, no route-mode graph edges, smart labels
- extend 3D export contract tests and user guide
```
