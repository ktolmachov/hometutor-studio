#!/usr/bin/env python3
"""Build a ready-to-paste prompt for an "evolutionary analysis" ("сильный ход").

This script does NOT call an LLM and does NOT produce the analysis itself. An
evolutionary analysis requires reading real code/data and making judgment calls
(parts 2 РЕАЛЬНОСТЬ and 5 ВЕРДИКТЫ) that only an agent with repo access can do
honestly — that step is inherently not scriptable. What this script does is the
mechanical part: fill the proven 8-part template (see
../evolutionary_analysis_guide.md) with your area's specifics so you don't
retype boilerplate each time.

Workflow
--------
1. Run this script with your area's specifics:

     python generate_analysis_prompt.py \\
         --area "Первые 10 минут" \\
         --coverage-area "Маршрут, навигация и следующий шаг" \\
         --role "новый студент" \\
         --action "впервые открывает приложение" \\
         --reality-domain "в онбординге (app/ui/mission_control.py, app/ui/onboarding*.py)" \\
         --tension "простота ↔ глубина" \\
         --tension "мощь ↔ фокус" \\
         --pain "<факт, который сам проверишь по коду перед запуском>" \\
         --learning-stage "1. Первый запуск" \\
         --outcome-signal "время до первого содержательного действия" \\
         --cross-pain "PAIN-03" \\
         --different-from "№2: проверяется новый экземпляр боли"

2. Paste the printed prompt into a FRESH agent session — not mixed into an
   ongoing code-editing session (see guide's section "Когда это работает").

3. Save the resulting self-contained HTML in this same folder as `NN_slug.html`
   and add a row to the table in README.md.

If --pain is omitted, the script leaves an explicit placeholder — do not run
the analysis until you've replaced it with a fact you can confirm by grep or a
command in under a minute (see the guide's checklist, item 3).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TEMPLATE = """\
# Эволюционный разбор: {area}

Нужен сильный ход.

ПАСПОРТ РАЗБОРА.
- Область покрытия: {coverage_area}
- Стадия учебного цикла: {learning_stage}
- Сигнал результата: {outcome_signal}
- Сквозная болезнь: {cross_pain}
- Отличие от прошлого разбора: {different_from}

До выводов сверь карту покрытия README, реестр cross_cutting_pains.md и прошлые
якоря по repo/path/symbol. Пересечение с прошлым разбором не запрещено, но его
нельзя замалчивать.

1. СУТЬ. Чего по-настоящему хочет {role}, когда {action}?
   В чём суть этого действия? (не фичи — первые принципы)

2. РЕАЛЬНОСТЬ. Посмотри с высоты на всё, что уже есть {reality_domain},
   включая живые данные пользователя (корпуса материалов, сайдкары, активные
   бандлы/БД — не только код). Собери, классифицируй, сгруппируй. Для каждого:
   зачем, плюсы, минусы, и как связать, чтобы вместе давало новый эффект.

3. ПРОТИВОРЕЧИЯ. Разреши напряжения (не выбери сторону — найди синтез):
{tensions}

4. БОЛЬ-ЯКОРЬ. Вот конкретная проверяемая боль: {pain}
   Найди её точную причину в реальности (код/данные), а не в теории.
   Где возможно — подтверди причину живым прогоном или прямым запросом
   к данным, а не только чтением кода.
   Зафиксируй якорь как repo@commit:path::symbol; file:line оставь подсказкой,
   а не идентификатором.

5. ВЕРДИКТЫ. Для каждого элемента — решение: оставить / спрятать глубже /
   объединить / починить / убрать. Не обзор опций — позиция.
   Отдельным блоком — «НЕ делать»: отклонённые ходы с причиной (это тоже вердикты).

6. ЦЕННОСТЬ. В чём уникальность — и как её доказать измеримо.
   Одна North star-метрика: какое число изменится, если ход удался.
   Укажи формулу, источник данных, baseline, target и wiring-status:
   wired-existing / wire-in-P0 / not-measurable с причиной.

7. ПУТЬ. Один золотой путь пользователя + лестница уровней,
   которые легко достигать и приятно проходить.

8. ПЛАН. P0–P2 по соотношению «эффект / усилие». P0 — не больше двух ходов.
   North star wired входит в DoD P0: используй существующий сигнал или подключи
   минимальное измерение. Неизмеримый эффект нельзя объявлять доказанным.
   Kill switch: условия, при которых P0 останавливается (типовые: потребовалась
   новая схема/хранилище/пайплайн, или LLM там, где хватает арифметики готовых данных).

Если вердикт зависит от LLM-выхода, зафиксируй рубрику до генерации и оцени
полный семпл: минимум 3 входа × 3 повтора; для P0 — 5 входов × 3 повтора.
Единичный пример — иллюстрация, не доказательство.

Планка: шедевр. Гениальность — в простоте. Ничего не выдумывать:
каждое утверждение должно опираться на реальное и проверяемое.
"""

PAIN_PLACEHOLDER = (
    "<ЗАПОЛНИ ПЕРЕД ЗАПУСКОМ — конкретный проверяемый факт, не гипотеза; должен "
    "подтверждаться одним grep/командой за минуту (см. чек-лист гайда)>"
)

DEFAULT_TENSIONS = ["<простота> ↔ <глубина>", "<мощь> ↔ <фокус>"]


def build_prompt(
    *,
    area: str,
    coverage_area: str,
    role: str,
    action: str,
    reality_domain: str,
    tensions: list[str],
    pain: str | None,
    learning_stage: str,
    outcome_signal: str,
    cross_pain: str,
    different_from: str,
) -> str:
    chosen_tensions = tensions or DEFAULT_TENSIONS
    tension_lines = "\n".join(f"   - {t}" for t in chosen_tensions)
    return TEMPLATE.format(
        area=area,
        coverage_area=coverage_area,
        role=role,
        action=action,
        reality_domain=reality_domain,
        tensions=tension_lines,
        pain=pain or PAIN_PLACEHOLDER,
        learning_stage=learning_stage,
        outcome_signal=outcome_signal,
        cross_pain=cross_pain,
        different_from=different_from,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Fill the evolutionary-analysis template (see module docstring / "
            "../evolutionary_analysis_guide.md) with your area's specifics and "
            "print the ready-to-paste prompt."
        ),
    )
    parser.add_argument("--area", required=True, help='Название области, напр. "Первые 10 минут"')
    parser.add_argument(
        "--coverage-area",
        required=True,
        help="Область из карты покрытия README.md",
    )
    parser.add_argument("--role", required=True, help='Кто, напр. "новый студент"')
    parser.add_argument(
        "--action",
        required=True,
        help='Что делает, напр. "впервые открывает приложение"',
    )
    parser.add_argument(
        "--reality-domain",
        default="в коде / данных / процессе",
        help='Где искать реальность, напр. "в онбординге (app/ui/mission_control.py)"',
    )
    parser.add_argument(
        "--tension",
        action="append",
        default=[],
        metavar="A ↔ B",
        help="Пара противоречия; повторяй флаг для каждой (по умолчанию — 2 общих плейсхолдера)",
    )
    parser.add_argument(
        "--pain",
        default=None,
        help="Конкретный проверяемый факт боли (если не задан — печатается плейсхолдер)",
    )
    parser.add_argument(
        "--learning-stage",
        required=True,
        help="Основная стадия учебного цикла 1–10 из гайда",
    )
    parser.add_argument(
        "--outcome-signal",
        required=True,
        help="Наблюдаемый сигнал учебного или пользовательского результата",
    )
    parser.add_argument(
        "--cross-pain",
        required=True,
        help="PAIN-NN из cross_cutting_pains.md или обоснованный новый класс",
    )
    parser.add_argument(
        "--different-from",
        required=True,
        help='Отличие от пересекающегося разбора №N или "пересечений нет"',
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Файл для записи промпта (по умолчанию — печать в stdout)",
    )
    args = parser.parse_args()

    prompt = build_prompt(
        area=args.area,
        coverage_area=args.coverage_area,
        role=args.role,
        action=args.action,
        reality_domain=args.reality_domain,
        tensions=args.tension,
        pain=args.pain,
        learning_stage=args.learning_stage,
        outcome_signal=args.outcome_signal,
        cross_pain=args.cross_pain,
        different_from=args.different_from,
    )

    if args.out:
        Path(args.out).write_text(prompt, encoding="utf-8")
        print(f"Промпт записан в {args.out}")
    else:
        print(prompt)


if __name__ == "__main__":
    main()
