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

TEMPLATE = """\
Продолжи актуализацию витрины сценариев hometutor по разбору №11.

Контекст:
- Runtime repo: {runtime_repo}
- Studio repo: {studio_repo}
- Scenario manifests: {scenario_dir}
- Demo document: {demo_doc}
- Detail-plan: {plan_path}

Сначала прочитай:
1. {scenario_dir}/README.md
2. {plan_path}
3. {demo_doc}
4. Релевантные YAML-манифесты scenario_*.yaml и meta.json/screenshots только по выбранным gap-зонам.

Правила:
- YAML-манифесты остаются SSoT.
- Не меняй структуру YAML и demo workflow без явной необходимости.
- Не запускай пересъёмку, если задача только подготовить манифесты.
- Не выдумывай покрытие: каждое новое обещание должно ссылаться на существующий UI/API/runtime путь или явно быть pending.

P0:
1. Добавь freshness stamp в генерацию витрины: HEAD съёмки, текущий HEAD и freshness gap.
2. Подготовь YAML-манифесты слепых зон:
{gap_lines}

DoD:
- Новые/изменённые YAML проходят schema/strict validation.
- `docs/quickstart_demo.md` честно показывает freshness.
- Сценарии 06/30 не обещают больше, чем видно на текущих кадрах, либо имеют сноску до пересъёмки.
- В финале перечисли изменённые файлы, проверки и следующий шаг capture/publish.
"""


def build_prompt(
    *,
    runtime_repo: str,
    studio_repo: str,
    scenario_dir: str,
    demo_doc: str,
    plan_path: str,
    gaps: list[str],
) -> str:
    chosen = gaps or list(DEFAULT_GAPS)
    gap_lines = "\n".join(f"   - {item}" for item in chosen)
    return TEMPLATE.format(
        runtime_repo=runtime_repo,
        studio_repo=studio_repo,
        scenario_dir=scenario_dir,
        demo_doc=demo_doc,
        plan_path=plan_path,
        gap_lines=gap_lines,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a usage-scenarios refresh prompt.")
    parser.add_argument("--runtime-repo", default=r"D:\Projects\hometutor")
    parser.add_argument("--studio-repo", default=r"D:\Projects\hometutor-studio")
    parser.add_argument("--scenario-dir", default=r"D:\Projects\hometutor-studio\doc\scenarios")
    parser.add_argument("--demo-doc", default=r"D:\Projects\hometutor\docs\quickstart_demo.md")
    parser.add_argument("--plan-path", default=r"D:\Projects\hometutor-studio\doc\next\usage_scenarios_refresh_plan.md")
    parser.add_argument("--gap", action="append", default=[], help="Gap zone to include; repeatable.")
    parser.add_argument("--out", default=None, help="Optional file to write instead of stdout.")
    args = parser.parse_args()

    prompt = build_prompt(
        runtime_repo=args.runtime_repo,
        studio_repo=args.studio_repo,
        scenario_dir=args.scenario_dir,
        demo_doc=args.demo_doc,
        plan_path=args.plan_path,
        gaps=args.gap,
    )
    if args.out:
        Path(args.out).write_text(prompt, encoding="utf-8")
        print(f"Промпт записан в {args.out}")
    else:
        print(prompt)


if __name__ == "__main__":
    main()
