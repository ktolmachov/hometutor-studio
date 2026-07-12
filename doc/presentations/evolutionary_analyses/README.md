# Эволюционные разборы («нескучные разборы»)

Готовые HTML-разборы по формату из
[`../evolutionary_analysis_guide.md`](../evolutionary_analysis_guide.md). Каждый —
самодостаточная страница (без внешних зависимостей, светлая/тёмная тема, inline
SVG-диаграммы). Формат подтверждён владельцем как эталонный после разбора
2026-07-10.

**Визуальный стиль зафиксирован (v1.0, 2026-07-12)** —
[`../notebook_deck_guide.md`](../notebook_deck_guide.md) /
[`../notebook_template.html`](../notebook_template.html). Палитра, типографика и
восемь секций там финальны; новый CSS с нуля не изобретать. Разборы №1–8
предшествуют фиксации и палитру не наследуют (исторический снимок, см.
guide §9) — начиная с №9 все разборы используют один и тот же локон.

## Как сделать новый разбор

1. Заполни промпт скриптом из этой же папки:

   ```bash
   python generate_analysis_prompt.py \
     --area "Первые 10 минут" \
     --role "новый студент" \
     --action "впервые открывает приложение" \
     --reality-domain "в онбординге (app/ui/mission_control.py, ...)" \
     --tension "простота ↔ глубина" \
     --tension "мощь ↔ фокус" \
     --pain "<факт, проверенный по коду перед запуском>"
   ```

   Скрипт не вызывает LLM — он только собирает готовый промпт из проверенного
   шаблона. Сама «РЕАЛЬНОСТЬ» и «ВЕРДИКТЫ» требуют агента с доступом к коду.

2. Скопируй вывод в **новую** сессию агента — не смешивай с правкой кода в той
   же сессии (см. гайд, раздел «Когда это работает»).

3. Оформление разбора начинай с копии
   [`../notebook_template.html`](../notebook_template.html), не с CSS с нуля и не
   с копипаста прошлого файла — палитра и компоненты зафиксированы в
   [`../notebook_deck_guide.md`](../notebook_deck_guide.md).

4. Сохрани готовый HTML сюда же как `NN_slug.html`, добавь строку в таблицу
   ниже. Если разбор тянет за собой реализацию — actionable-план кладётся
   отдельно в [`../../next/`](../../next/) (гайд, раздел 4), не сюда.

## Разборы

| № | Область | Статус | Файл | Detail-plan |
|---|---|---|---|---|
| 1 | Судьба одного знания (петля памяти) | готово (2026-07-11) | [`01_knowledge_fate.html`](01_knowledge_fate.html) | [`../../next/knowledge_fate_memory_loop_plan.md`](../../next/knowledge_fate_memory_loop_plan.md) |
| 2 | Первые 10 минут (онбординг, time-to-first-insight) | готово (2026-07-11) | [`02_first_ten_minutes.html`](02_first_ten_minutes.html) | [`../../next/first_ten_minutes_onboarding_plan.md`](../../next/first_ten_minutes_onboarding_plan.md) |
| 3 | Материал как продукт (конспект, граф, таймкоды) | готово (2026-07-11) | [`03_material_as_product.html`](03_material_as_product.html) | [`../../next/material_as_product_quality_plan.md`](../../next/material_as_product_quality_plan.md) |
| 4 | Агент как одна кнопка (Agent Coach → UI) | готово (2026-07-11) | [`04_agent_as_one_button.html`](04_agent_as_one_button.html) | [`../../next/agent_as_one_button_plan.md`](../../next/agent_as_one_button_plan.md) |
| 5 | Доверие под нагрузкой (провайдер, скорость, честность fallback) | готово (2026-07-11) | [`05_trust_under_load.html`](05_trust_under_load.html) | [`../../next/trust_under_load_provider_plan.md`](../../next/trust_under_load_provider_plan.md) |
| 6 | Инфографика: живая карта материала (спецвыпуск, вне очереди) | готово (2026-07-11) | [`06_infographics.html`](06_infographics.html) | [`../../next/infographics_living_map_plan.md`](../../next/infographics_living_map_plan.md) |
| 7 | План обучения: стол, который забывает, где вы сидите | готово (2026-07-11) | [`07_learning_plan.html`](07_learning_plan.html) | [`../../next/learning_plan_single_source_plan.md`](../../next/learning_plan_single_source_plan.md) |
| 8 | Невидимая половина (метаразбор серии: сильный ход к шедевру) | готово (2026-07-12) | [`08_invisible_half.html`](08_invisible_half.html) | [`../../next/invisible_half_closure_plan.md`](../../next/invisible_half_closure_plan.md) |
| 9 | Своя комната (цветовые схемы «миры» + фоны мирового уровня) | готово (2026-07-12) | [`09_color_worlds.html`](09_color_worlds.html) | [`../../next/color_worlds_theming_plan.md`](../../next/color_worlds_theming_plan.md) |
| 10 | Кольцо замкнулось, но беззвучно (финал: синтез разборов №1–№9) | готово (2026-07-12) | [`10_full_circle.html`](10_full_circle.html) | [`../../next/full_circle_visibility_plan.md`](../../next/full_circle_visibility_plan.md) |

Приоритизация и обоснование очерёдности (2026-07-11) сохранены отдельно в
памяти агента (`evolutionary-series-2026-07`).


