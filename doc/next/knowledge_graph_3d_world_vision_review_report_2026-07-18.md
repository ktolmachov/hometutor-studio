# Отчёт: deep review + правка vision «Мнемополис»

| Поле | Значение |
|---|---|
| Дата | 2026-07-18 |
| Объект | `doc/next/knowledge_graph_3d_world_vision.md` |
| План-предшественник | `doc/next/knowledge_graph_3d_game_plan.md` |
| Runtime (hometutor) | HEAD @ `ec9a3c250` «275» |
| Принципы | `hometutor/docs/evolutionary_development.md` |
| Промпт | `prompt_deep_review_kg_3d_world_vision.md` |
| Результат | vision **v0 → v1**; game plan cross-links синхронизированы |

**Статус документов (studio):** изменены, **не закоммичены** (ожидают решения владельца).

---

## 1. Задача

1. Провести глубокое, придирчивое ревью vision «Мнемополис» (этапы 0–2 промпта).
2. По итогам — **аккуратно исправить** vision (и согласовать ссылки в game plan).

---

## 2. Что сделано (процесс)

### 2.1 Загрузка контекста

- Полностью прочитан `docs/evolutionary_development.md`.
- Полностью прочитан план G0–G3 + U0–U4 + V2′ / Ревизия v2.
- Полностью прочитан vision v0.
- Сверены ключевые runtime-файлы: `kg_3d_template.html`, `knowledge_graph_d3.py`,
  `dashboards_graph.py`, `gamification_service.py`, `provider.py`, action whitelist
  (`start|collect`), `PENDING_CURRENT_VIEW_KEY`, `feature_registry`.

### 2.2 Живой прогон (@275)

- Export HTML через `build_kg_3d_html` (12 узлов, route 6).
- Playwright viewport matrix: **1366×768**, **860×768**, **390×844**.
- Targeted tests: `tests/test_knowledge_graph_counters.py` — **68 passed**.

### 2.3 Deep review (вывод)

| Оценка | Балл |
|---|---:|
| Общее качество vision v0 | **7.1 / 10** |
| Продуктовая идея (§3) | 9.0 |
| Эволюционность волн | 5.5 |
| Актуальность evidence | 5.0 |
| **Вердикт v0** | **не готов к промоуту as-is** |

**Сильная сторона:** «мир = честная проекция learner-данных», не скин поверх XP.
**Главный риск:** stale baseline @270 + толстые волны W4–W6 + LLM/scene-DSL без числового контракта.

### 2.4 Правка документов

| Файл | Действие |
|---|---|
| `knowledge_graph_3d_world_vision.md` | полная ревизия **v1** (~38 KB) |
| `knowledge_graph_3d_game_plan.md` | синхронизация хвоста «→ Мнемополис», статусов, residual W0′ |
| `doc/presentations/evolutionary_analyses/19_mnemopolis_world.html` | добавлен разбор №19 / презентационный артефакт |

Runtime-код hometutor **не менялся**.

---

## 3. Ключевые находки ревью (v0)

### Критические

| ID | Проблема |
|---|---|
| C1 | Evidence @270 при коде @275: W0/G4 partial уже сделаны; residual не описан |
| C2 | Волны W4–W6 — monoblock, нарушают эволюционный стиль |
| C3 | scene-DSL (F) = новый command bus без schema/security DoD |
| C4 | LLM unlock без числового budget / non-blocking first paint |
| C5 | Конфликт «Мнемополис = home» vs Mission Control |
| C6 | W2 склеивал fog visual + новый action `review` |
| C7 | Разлом зависел от недоказанной prereq-семантики `precedes` |

### Живой прогон residual (после W0 @273–274)

| Residual | Суть |
|---|---|
| W0′-R1 | Desktop: маршрут всё ещё в верхней половине (пустота снизу) |
| W0′-R2 | Две легенды: floor-ось + компас (ДАЛ/СЕГ) |
| W0′-R3 | Mobile 390: callout ∩ compass ∩ nav |
| W0′-R4 | Dev-hint `#hint` в learner surface |
| W0′-R5 | Chip `due true` (boolean/English) |
| W0′-R6 | Ring @0% слабо читается |
| W0′-R7 | Export CTA hierarchy |

---

## 4. Что исправлено в vision v1

| Тема | Было (v0) | Стало (v1) |
|---|---|---|
| Baseline | @270 | **@275** + §0 «уже DONE» |
| Q1–Q9 | открытый долг | **bulk закрыт W0**, но не 100%; residual **W0′-R1…R7 → W0′** |
| G4 | «ещё не реализован» | **G4.1+G4.2 ✅**; G4.3 ⬜; Летописец поверх scrubber |
| Home | мир как home привычки | **Mission Control = home**; мир = ceremonial hub |
| Районы | 10 сразу | каталог + **MVP 4 двери** (glyph) |
| LLM | «≤N» | **budget table**: ≤4 calls, input/output/session caps, timeout, cache, circuit-breaker, privacy gate, fail-closed |
| scene-DSL | W5 implementation | **design spike**, go/no-go |
| Волны | W0–W6 monoblock | W0′/W1/W2a·b/W3a·b·c/W4a–d/… |
| §3 декор | двусмысленно | **data-bound** vs **structural** cues |
| Стрик | «свет гаснет» | свет **остывает**, прогресс не откатывается |
| Туман a11y | partial glyphs | полное имя всегда в side card |
| Разлом | сразу в W6 | **blocked on data audit** |
| Промоут | неявный | **только W0′ + W1 (+opt W2a)** |
| ED | слабо | §12 checklist + write-set/DoD per wave |

### Kill switch → **v3.1**

Сохранено: freeze domain, no second currency, first route frame, no WebGL.
Уточнено: числовой LLM budget; G0 `+review` только отдельной волной; scene-DSL не в near-term backlog; MC = home.

---

## 5. Актуальная дорожная карта (из v1)

### Можно промоутить в backlog сейчас

| Волна | Содержание | P | Effort |
|---|---|---|---|
| **W0′** | Residual W0′-R1…R7 (fitRouteCamera, одна легенда, mobile, hint, chips, ring contrast, export CTA) | P0 | ≤1 дня |
| **W1** | Рассвет + фонари из quiz-route progress | P0 | ≤1 дня |
| **W2a** (opt.) | Туман visual + «Спокойный мир» (без нового action) | P1 | 1–2 дня |

### Следом (после live W0′+W1)

| Волна | Содержание |
|---|---|
| W2b | action `review` → Flashcards |
| W3a → W3b → W3c | LLM infra → Keeper A → Keeper B |
| W4a–d | sidebar deep link, return CTA, 4 doors, multi-channel trophy |
| W5… | tutor handoff; scene-DSL spike; later catalog |
| W6… | Призрак; Разлом (после audit); летописец-текст; стройка |

### Не делать (зафиксировано)

Аватар / open-world / экономика / punish / LLM в домен / подмена Mission Control /
толстые monoblock-волны / scene-DSL и Разлом без go.

---

## 6. Изменённые файлы

```
hometutor-studio/
  doc/next/knowledge_graph_3d_world_vision.md          (v1, rewrite)
  doc/next/knowledge_graph_3d_game_plan.md             (cross-links)
  doc/next/knowledge_graph_3d_world_vision_review_report_2026-07-18.md  (этот отчёт)
```

**hometutor (runtime):** без изменений в рамках этой задачи.

---

## 7. Рекомендации владельцу

1. **Принять vision v1** как актуальный candidate №19 (вместо v0).
2. **Промоут в backlog только среза** `W0′ → W1` (+ опционально `W2a`).
3. Отдельно решить (когда понадобится):
   - переоткрывать MC = home только при явном owner override; в vision это уже принято как рекомендация;
   - go/no-go scene-DSL spike;
   - data audit `precedes` перед Разломом;
   - privacy DoD для G4.3.
4. Коммит studio-доков — по желанию владельца; перед коммитом проверять `git status`,
   не переносить в отчет устаревший статус рабочей копии без фактической проверки.
5. Реализацию W0′/W1 вести в runtime `hometutor` эволюционными волнами с V2′ gate
   и живым прогоном (как в game plan Memory Run).

---

## 8. Итоговый вердикт

| Вопрос | Ответ |
|---|---|
| Готов ли vision v0 к backlog? | **Нет** |
| Готов ли vision **v1** как candidate + first slice? | **Да** — срез W0′+W1 |
| Нужна ли ещё серьёзная переписка vision? | **Нет**, при согласии с product decisions §5/§6/§7 |
| Блокеры runtime? | Нет; residual polish и механики — будущие волны |
| Оценка после правки (doc quality) | **candidate**, но не engineering-ready до live-gate W0′+W1 и закрытия числовых контрактов |

**Одной фразой:** идея Мнемополиса сильная; документ приведён к эволюционному
стилю и актуальному коду; в работу сейчас — только полировка зала и «Рассвет»,
не «весь город сразу».
