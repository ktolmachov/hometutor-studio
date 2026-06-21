#!/usr/bin/env python3
"""
Scaffold нового Smart Demo сценария: YAML + Playwright demo spec.

Пример:

    .\\.venv\\Scripts\\python.exe scripts/scaffold_demo_scenario.py \\
        --number 25 --slug ssr_example --title "SSR Example: короткое название" \\
        --level "🔴 Orchestration" --shots 3 --update-order

После scaffold:
1. Допишите шаги в YAML (why, wow_moment, takeaway, scenario_link).
2. Реализуйте навигацию и demo.shot(...) в spec.
3. Добавьте раздел в doc/user_scenarios.md (если ещё нет).
4. Прогон: .\\.venv\\Scripts\\python.exe scripts/demo_workflow.py capture --scenario-id scenario_25
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_DIR = ROOT / "doc" / "scenarios"
DEMOS_DIR = ROOT / "tests" / "e2e" / "demos"
GENERATE_DOC = ROOT / "scripts" / "generate_demo_doc.py"
ORDER_MARKER = "DEFAULT_SCENARIO_ORDER = ["

YAML_TEMPLATE = """id: {scenario_id}
title: "{title}"
level: "{level}"
persona: "TODO: краткое описание героя."
duration_min: 3
why: |
  TODO: зачем показываем этот сценарий (1–2 фразы).
requires:
  openai_api_key: false
  offline_friendly: true
wow_moment: |
  TODO: главный wow-кадр.
takeaway: |
  TODO: что зритель должен запомнить.
scenario_link: "user_scenarios.md#сценарий-{number}--{anchor_slug}"

shots:
{shots_yaml}
"""

SPEC_TEMPLATE = """import {{ test }} from "@playwright/test";
import {{ gotoAndWaitForStreamlitReady, waitForStreamlitReady }} from "../fixtures/streamlit_ready";
import {{ createDemoRecorder }} from "../fixtures/demo_recorder";
import {{ DEMO }} from "../fixtures/demo_timeouts";
import {{ completeFirstRunOnboarding }} from "../fixtures/onboarding";

test.describe("@demo Scenario {number} — {title_short}", () => {{
  test("@demo captures {slug} flow", async ({{ page }}) => {{
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "{scenario_id}");

    try {{
      await completeFirstRunOnboarding(page);

      // TODO: навигация к нужному экрану
      await gotoAndWaitForStreamlitReady(page, "/");
      await waitForStreamlitReady(page);

{shots_spec}

      await demo.finalize("passed");
    }} catch (err) {{
      await demo.finalize("failed");
      throw err;
    }}
  }});
}});
"""

SHOT_YAML = """  - slug: "{slug}"
    caption: "TODO: подпись кадра {index}"
    narration: "TODO: нарратив кадра {index}."
    duration_sec: 3"""

SHOT_SPEC = """      // {slug}
      await demo.shot("{slug}", {{
        caption: "TODO: подпись кадра {index}",
        narration: "TODO: нарратив кадра {index}.",
        waitMs: 800,
      }});"""


def _slugify(value: str) -> str:
    value = value.casefold().replace("ё", "е")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "scenario"


def _title_short(title: str, max_len: int = 48) -> str:
    compact = re.sub(r"\s+", " ", title.strip())
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 1].rstrip() + "…"


def _next_free_number(scenarios_dir: Path) -> int:
    numbers: list[int] = []
    for path in scenarios_dir.glob("scenario_*.yaml"):
        match = re.match(r"scenario_(\d{2})_", path.name)
        if match:
            numbers.append(int(match.group(1)))
    return (max(numbers) + 1) if numbers else 1


def _append_scenario_order(scenario_id: str) -> bool:
    text = GENERATE_DOC.read_text(encoding="utf-8")
    if f'"{scenario_id}"' in text:
        return False
    start = text.find(ORDER_MARKER)
    if start < 0:
        raise SystemExit(f"Cannot find {ORDER_MARKER!r} in {GENERATE_DOC}")

    close = text.find("]", start)
    if close < 0:
        raise SystemExit(f"Cannot find closing ] for scenario order in {GENERATE_DOC}")

    block = text[start:close]
    if not block.rstrip().endswith(","):
        text = text[:close].rstrip() + ",\n" + f'    "{scenario_id}",\n' + text[close:]
    else:
        text = text[:close].rstrip() + f'\n    "{scenario_id}",\n' + text[close:]
    GENERATE_DOC.write_text(text, encoding="utf-8")
    return True


def _build_shots(prefix: str, count: int) -> tuple[str, str]:
    yaml_parts: list[str] = []
    spec_parts: list[str] = []
    for index in range(1, count + 1):
        slug = f"{index:02d}_{prefix}_step"
        yaml_parts.append(SHOT_YAML.format(slug=slug, index=index))
        spec_parts.append(SHOT_SPEC.format(slug=slug, index=index))
    return "\n".join(yaml_parts), "\n\n".join(spec_parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--number", type=int, default=0, help="Номер сценария (01–99). 0 = следующий свободный.")
    parser.add_argument("--slug", required=True, help="Короткий slug латиницей, напр. ssr_trust_v2.")
    parser.add_argument("--title", required=True, help='Читаемое название, напр. "SSR Trust: ...".')
    parser.add_argument("--level", default="🟢 Первые шаги", help="Уровень сценария для YAML.")
    parser.add_argument("--shots", type=int, default=3, help="Число placeholder-кадров (default: 3).")
    parser.add_argument("--force", action="store_true", help="Перезаписать существующие файлы.")
    parser.add_argument(
        "--update-order",
        action="store_true",
        help=f'Добавить scenario_XX в DEFAULT_SCENARIO_ORDER в {GENERATE_DOC.name}.',
    )
    parser.add_argument("--dry-run", action="store_true", help="Показать план без записи файлов.")
    args = parser.parse_args()

    if args.shots < 1 or args.shots > 12:
        raise SystemExit("--shots must be between 1 and 12")

    slug = _slugify(args.slug)
    if not re.match(r"^[a-z][a-z0-9_]*$", slug):
        raise SystemExit(f"Invalid slug after normalization: {slug!r}")

    number = args.number or _next_free_number(SCENARIOS_DIR)
    if number < 1 or number > 99:
        raise SystemExit("--number must be between 1 and 99")

    scenario_id = f"scenario_{number:02d}"
    yaml_name = f"{scenario_id}_{slug}.yaml"
    spec_name = f"{scenario_id}_{slug}.spec.ts"
    yaml_path = SCENARIOS_DIR / yaml_name
    spec_path = DEMOS_DIR / spec_name
    anchor_slug = _slugify(args.title)

    for path in (yaml_path, spec_path):
        if path.exists() and not args.force:
            raise SystemExit(f"Already exists: {path} (use --force to overwrite)")

    shots_yaml, shots_spec = _build_shots(slug, args.shots)
    yaml_body = YAML_TEMPLATE.format(
        scenario_id=scenario_id,
        title=args.title.replace('"', '\\"'),
        level=args.level,
        number=number,
        anchor_slug=anchor_slug,
        shots_yaml=shots_yaml,
    )
    spec_body = SPEC_TEMPLATE.format(
        number=number,
        title_short=_title_short(args.title),
        slug=slug,
        scenario_id=scenario_id,
        shots_spec=shots_spec,
    )

    print(f"[scaffold] scenario_id: {scenario_id}")
    print(f"[scaffold] yaml:        {yaml_path.relative_to(ROOT)}")
    print(f"[scaffold] spec:        {spec_path.relative_to(ROOT)}")
    print(f"[scaffold] shots:       {args.shots}")

    if args.dry_run:
        print("[scaffold] dry-run: files not written")
        return 0

    yaml_path.write_text(yaml_body, encoding="utf-8")
    spec_path.write_text(spec_body, encoding="utf-8")
    print("[scaffold] wrote YAML + spec")

    if args.update_order:
        if _append_scenario_order(scenario_id):
            print(f"[scaffold] appended {scenario_id} to DEFAULT_SCENARIO_ORDER")
        else:
            print(f"[scaffold] {scenario_id} already present in DEFAULT_SCENARIO_ORDER")

    print()
    print("Next steps:")
    print(f"  1. Edit {yaml_path.relative_to(ROOT)} — why/wow/takeaway/shots.")
    print(f"  2. Implement navigation in {spec_path.relative_to(ROOT)}.")
    print("  3. Add heading to doc/user_scenarios.md if missing.")
    print(f"  4. Preflight: .\\.venv\\Scripts\\python.exe scripts/demo_workflow.py preflight --scenario-id {scenario_id}")
    print(
        f"  5. Capture:  .\\.venv\\Scripts\\python.exe scripts/demo_workflow.py capture --scenario-id {scenario_id}"
    )
    print(
        f"  6. Publish:  .\\.venv\\Scripts\\python.exe scripts/demo_workflow.py publish --run <YYYY-MM-DD>"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
