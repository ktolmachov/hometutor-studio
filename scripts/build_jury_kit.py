#!/usr/bin/env python3
"""
Собирает Jury Demo Kit — один ZIP-артефакт для презентации на конкурсе.

Что попадает в ZIP:
  - doc/pitch.md                    — one-page battle card
  - doc/presenter_script.md         — скрипт выступления на 3 минуты
  - doc/quickstart.md               — быстрый старт для тех, кто захочет запустить
  - doc/quickstart_demo.md          — smart demo-документ с GIF и раскадровкой
  - doc/user_scenarios.md           — каталог сценариев (режиссёрский план)
  - doc/user_guide.md               — hero-документ продукта
  - doc/screenshots/scenario_*/     — все PNG-кадры и собранные GIF

Опции:
  --output PATH       путь к ZIP (default: dist/jury_kit_<date>.zip)
  --include-details   добавить `user_guide_details.md` и `architecture.md` (для подробного жюри)
  --dry-run           вывести список файлов без создания ZIP

Запуск (обычно идёт из `npm run demo:kit`):

    python scripts/build_jury_kit.py
    python scripts/build_jury_kit.py --include-details
    python scripts/build_jury_kit.py --output dist/hometutor-jury-v1.zip
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

CORE_DOCS = [
    "doc/pitch.md",
    "doc/presenter_script.md",
    "doc/quickstart.md",
    "doc/quickstart_demo.md",
    "doc/user_scenarios.md",
    "doc/user_guide.md",
]

DETAILS_DOCS = [
    "doc/user_guide_details.md",
    "doc/architecture.md",
    "doc/vision.md",
    "doc/cjm.md",
]

SCREENSHOTS_ROOT = Path("doc/screenshots")


def _collect_screenshots() -> list[Path]:
    result: list[Path] = []
    root = REPO_ROOT / SCREENSHOTS_ROOT
    if not root.exists():
        return result
    for scenario_dir in sorted(root.iterdir()):
        if not scenario_dir.is_dir() or not scenario_dir.name.startswith("scenario_"):
            continue
        for ext in ("*.png", "*.gif", "meta.json"):
            result.extend(sorted(scenario_dir.glob(ext)))
    readme = root / "README.md"
    if readme.exists():
        result.append(readme)
    return result


def _collect_files(include_details: bool) -> list[Path]:
    collected: list[Path] = []
    docs = CORE_DOCS + (DETAILS_DOCS if include_details else [])
    for rel in docs:
        abs_path = REPO_ROOT / rel
        if abs_path.exists():
            collected.append(abs_path)
        else:
            print(f"[jury-kit] WARN: нет файла {rel} — пропущен")
    collected.extend(_collect_screenshots())
    return collected


def _default_output() -> Path:
    stamp = _dt.date.today().isoformat()
    return REPO_ROOT / "dist" / f"jury_kit_{stamp}.zip"


def _write_readme_top(zf: zipfile.ZipFile) -> None:
    """Кладёт README.md в корень ZIP — первое, что видит жюри при распаковке."""
    readme = (
        "# Jury Demo Kit — hometutor\n"
        "\n"
        "> Личный тьютор из ваших конспектов. Local-first. 5 минут до wow.\n"
        "\n"
        "## С чего начать\n"
        "\n"
        "1. Откройте **`doc/pitch.md`** — одна страница с ключевыми отличиями от конкурентов.\n"
        "2. Пролистайте **`doc/quickstart_demo.md`** — реальные GIF-анимации из продукта.\n"
        "3. Прочитайте **`doc/presenter_script.md`** — что и как говорить за 3 минуты.\n"
        "\n"
        "## Запустить самостоятельно\n"
        "\n"
        "```bash\n"
        "git clone <repo> && cd hometutor-studio\n"
        "copy .env.example .env\n"
        "docker compose up --build\n"
        "```\n"
        "\n"
        "→ http://localhost:8501\n"
        "\n"
        "## Что внутри ZIP\n"
        "\n"
        "- `doc/pitch.md` — battle card одной страницей\n"
        "- `doc/presenter_script.md` — скрипт выступления\n"
        "- `doc/quickstart.md` — онбординг за 10 шагов\n"
        "- `doc/quickstart_demo.md` — GIF + раскадровка (автоматически снято Playwright'ом)\n"
        "- `doc/user_scenarios.md` — каталог из 14 сценариев\n"
        "- `doc/user_guide.md` — hero-обзор продукта\n"
        "- `doc/screenshots/scenario_*/` — PNG-кадры и GIF-анимации\n"
        "\n"
        "Сборка: `npm run demo:kit` в исходном репо.\n"
    )
    zf.writestr("README.md", readme)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Путь к ZIP-артефакту (default: dist/jury_kit_<date>.zip).",
    )
    parser.add_argument(
        "--include-details",
        action="store_true",
        help="Добавить user_guide_details.md, architecture.md, vision.md, cjm.md.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только вывести список файлов, без создания ZIP.",
    )
    args = parser.parse_args()

    files = _collect_files(args.include_details)
    if not files:
        print("[jury-kit] ERROR: нет файлов для архивирования.", file=sys.stderr)
        return 1

    if args.dry_run:
        for f in files:
            print(f.relative_to(REPO_ROOT).as_posix())
        print(f"[jury-kit] dry-run: {len(files)} files")
        return 0

    out_path = args.output or _default_output()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        _write_readme_top(zf)
        for f in files:
            arcname = f.relative_to(REPO_ROOT).as_posix()
            zf.write(f, arcname=arcname)

    size_kb = out_path.stat().st_size // 1024
    print(
        f"[jury-kit] built: {out_path.relative_to(REPO_ROOT).as_posix()} "
        f"({len(files)} files, {size_kb} KB)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
