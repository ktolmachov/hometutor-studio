#!/usr/bin/env python3
"""Build a ready-to-paste prompt for refreshing hometutor usage scenarios.

The script does not call an LLM. It only assembles a focused handoff prompt for
an agent that can inspect the runtime repo, scenario manifests and screenshots.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_GAPS = (
    "честный сбой LLM",
    "гость HF Spaces",
    "экспорт живой карты",
    "возврат в таймкод видео",
    "приватность / offline-проверка",
)

DEFAULT_DAILY_STORIES = (
    "Соня: первый вечер → второе утро",
    "Павел: будни в электричке",
    "Кирилл: месяц спустя",
    "Наталья: честный сбой LLM",
    "шпаргалка первой недели",
)

TEMPLATE = """\
Продолжи актуализацию витрины сценариев hometutor по разбору №11.

Контекст:
- Runtime repo: {runtime_repo}
- Studio repo: {studio_repo}
- Scenario manifests: {scenario_dir}
- Demo document: {demo_doc}
- Detail-plan: {plan_path}
- Daily-use stories: {daily_use_readme}

Сначала прочитай:
1. {runtime_repo}\\AGENTS.md
2. {runtime_repo}\\docs\\conventions.md
3. {plan_path}
4. {scenario_dir}/README.md
5. {demo_doc}
6. {daily_use_readme}
7. Релевантные YAML-манифесты scenario_*.yaml, demo/e2e specs и meta.json/screenshots только по выбранным gap-зонам.

Правила:
- YAML-манифесты остаются SSoT.
- Не меняй структуру YAML и demo workflow без явной необходимости.
- Не запускай пересъёмку, если задача только подготовить манифесты.
- Не выдумывай покрытие: каждое новое обещание должно ссылаться на существующий UI/API/runtime путь или явно быть pending.
- Истории ежедневного использования — отдельный жанр: они учат ритуалу, а не доказывают screenshot-покрытие. Не превращай иллюстративные диалоги из daily-use stories в обещания фич без evidence-сноски `из чего собрано`.

P0:
1. Добавь freshness stamp в генерацию витрины: HEAD съёмки, текущий HEAD и freshness gap.
2. Подготовь YAML-манифесты слепых зон:
{gap_lines}

P1:
1. Синхронизируй prompt/документацию с daily-use stories:
{story_lines}
2. Проверь, что quickstart demo и daily-use stories не конфликтуют: витрина продаёт момент, daily-use stories объясняют ежедневный ритуал.

DoD:
- Новые/изменённые YAML проходят schema/strict validation.
- `docs/quickstart_demo.md` честно показывает freshness.
- Сценарии 06/30 не обещают больше, чем видно на текущих кадрах, либо имеют сноску до пересъёмки.
- README daily-use stories включён в handoff prompt; новые истории перечислены как контекст, но не подменяют YAML/e2e-доказательства.
- В финале перечисли изменённые файлы, проверки и следующий шаг capture/publish.
"""


def build_prompt(
    *,
    runtime_repo: str,
    studio_repo: str,
    scenario_dir: str,
    demo_doc: str,
    plan_path: str,
    daily_use_readme: str,
    gaps: list[str],
    stories: list[str],
) -> str:
    chosen = gaps or list(DEFAULT_GAPS)
    gap_lines = "\n".join(f"   - {item}" for item in chosen)
    chosen_stories = stories or list(DEFAULT_DAILY_STORIES)
    story_lines = "\n".join(f"   - {item}" for item in chosen_stories)
    return TEMPLATE.format(
        runtime_repo=runtime_repo,
        studio_repo=studio_repo,
        scenario_dir=scenario_dir,
        demo_doc=demo_doc,
        plan_path=plan_path,
        daily_use_readme=daily_use_readme,
        gap_lines=gap_lines,
        story_lines=story_lines,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a usage-scenarios refresh prompt.")
    parser.add_argument("--runtime-repo", default=r"D:\Projects\hometutor")
    parser.add_argument("--studio-repo", default=r"D:\Projects\hometutor-studio")
    parser.add_argument("--scenario-dir", default=r"D:\Projects\hometutor-studio\doc\scenarios")
    parser.add_argument("--demo-doc", default=r"D:\Projects\hometutor\docs\quickstart_demo.md")
    parser.add_argument("--plan-path", default=r"D:\Projects\hometutor-studio\doc\next\usage_scenarios_refresh_plan.md")
    parser.add_argument(
        "--daily-use-readme",
        default=r"D:\Projects\hometutor-studio\doc\presentations\daily_use_stories\README.md",
    )
    parser.add_argument("--gap", action="append", default=[], help="Gap zone to include; repeatable.")
    parser.add_argument("--story", action="append", default=[], help="Daily-use story to include; repeatable.")
    parser.add_argument("--out", default=None, help="Optional file to write instead of stdout.")
    args = parser.parse_args()

    prompt = build_prompt(
        runtime_repo=args.runtime_repo,
        studio_repo=args.studio_repo,
        scenario_dir=args.scenario_dir,
        demo_doc=args.demo_doc,
        plan_path=args.plan_path,
        daily_use_readme=args.daily_use_readme,
        gaps=args.gap,
        stories=args.story,
    )
    if args.out:
        Path(args.out).write_text(prompt, encoding="utf-8")
        print(f"Промпт записан в {args.out}")
    else:
        print(prompt)


if __name__ == "__main__":
    main()
