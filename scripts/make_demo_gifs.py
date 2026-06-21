#!/usr/bin/env python3
"""
Собирает анимированные GIF из последовательности PNG-кадров каждого demo-сценария.

Читает:
  - doc/scenarios/scenario_*.yaml  (для per-shot duration_sec и порядка слайдов)
  - doc/screenshots/<scenario_id>/*.png (снятые Playwright'ом кадры)

Пишет:
  - doc/screenshots/<scenario_id>/demo.gif

Почему GIF, а не MP4:
  - один бинарный артефакт, встраивается прямо в markdown (GitHub/VS Code рендерят GIF);
  - не требует ffmpeg в окружении (только Pillow, уже есть в зависимостях);
  - подходит для pitch-документа, README и презентационных слайдов.

Запуск:

    python scripts/make_demo_gifs.py
    python scripts/make_demo_gifs.py --fps 1.5 --max-width 1100
    python scripts/make_demo_gifs.py --scenario scenario_02 --loop 0

Если для сценария нет ни одного PNG — пропускается без ошибки.
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import re
import sys
import time
from dataclasses import dataclass
from functools import partial
from pathlib import Path

try:
    from PIL import Image  # type: ignore
except ImportError:  # pragma: no cover
    print(
        "[demo-gifs] ERROR: Pillow не установлен. Установите `pip install pillow`.",
        file=sys.stderr,
    )
    raise

try:
    import yaml  # type: ignore

    _HAVE_YAML = True
    _YAML_ERROR_TYPES = (OSError, yaml.YAMLError)
except ImportError:
    yaml = None  # type: ignore
    _HAVE_YAML = False
    _YAML_ERROR_TYPES = (OSError,)


DEFAULT_SCENARIOS = Path("doc/scenarios")
DEFAULT_SCREENSHOTS = Path("doc/screenshots")

_RUN_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _resolve_screenshots_dir(requested: Path) -> Path:
    if requested != DEFAULT_SCREENSHOTS:
        return requested
    run = (os.environ.get("DEMO_SHOT_RUN") or "").strip()
    if run and _RUN_DIR_RE.match(run) and (DEFAULT_SCREENSHOTS / run).is_dir():
        return DEFAULT_SCREENSHOTS / run
    if (DEFAULT_SCREENSHOTS / "scenario_01").is_dir() or (DEFAULT_SCREENSHOTS / "scenario_02").is_dir():
        return DEFAULT_SCREENSHOTS
    dated = sorted(
        (p for p in DEFAULT_SCREENSHOTS.iterdir() if p.is_dir() and _RUN_DIR_RE.match(p.name)),
        key=lambda p: p.name,
    )
    if dated:
        return dated[-1]
    return requested
DEFAULT_FPS = 1.2  # 1.2 кадра в секунду = ~830ms на кадр — комфортно для чтения
DEFAULT_MAX_WIDTH = 1100
DEFAULT_DURATION_MS = 2600  # fallback per-frame duration если нет duration_sec в YAML


@dataclass
class ShotFrame:
    slug: str
    path: Path
    duration_ms: int


def _load_yaml_shots_duration(yaml_path: Path) -> dict[str, int]:
    """Возвращает dict slug -> duration_ms из YAML-манифеста сценария."""
    if not yaml_path.exists():
        return {}
    result: dict[str, int] = {}
    try:
        if _HAVE_YAML:
            raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        else:
            # Мини-парсер — только slug и duration_sec из списка shots
            raw = _minimal_yaml(yaml_path.read_text(encoding="utf-8"))
        for shot in raw.get("shots", []) or []:
            slug = str(shot.get("slug", "")).strip()
            if not slug:
                continue
            dur_sec = shot.get("duration_sec")
            if dur_sec is None:
                continue
            try:
                result[slug] = int(float(dur_sec) * 1000)
            except (TypeError, ValueError):
                continue
    except _YAML_ERROR_TYPES as exc:
        print(f"[demo-gifs] ERROR: failed to read {yaml_path}: {exc}", file=sys.stderr)
        raise
    return result


def _minimal_yaml(text: str) -> dict:
    """Минимальный парсер для случая без PyYAML: только shots[].slug/duration_sec."""
    shots: list[dict] = []
    current: dict | None = None
    in_shots = False
    for raw in text.splitlines():
        if raw.rstrip() == "shots:":
            in_shots = True
            continue
        if not in_shots:
            continue
        if raw and not raw.startswith(" ") and raw.strip() and not raw.lstrip().startswith("-"):
            break
        stripped = raw.strip()
        if stripped.startswith("- "):
            if current is not None:
                shots.append(current)
            current = {}
            rest = stripped[2:]
            if ": " in rest:
                k, v = rest.split(": ", 1)
                current[k.strip()] = v.strip().strip('"').strip("'")
        elif ": " in stripped and current is not None:
            k, v = stripped.split(": ", 1)
            current[k.strip()] = v.strip().strip('"').strip("'")
    if current is not None:
        shots.append(current)
    return {"shots": shots}


def _collect_frames(
    scenario_dir: Path, duration_overrides: dict[str, int], default_ms: int
) -> list[ShotFrame]:
    frames: list[ShotFrame] = []
    for png in sorted(scenario_dir.glob("*.png")):
        # имя: 01_home_mode_selector.png → slug 'home_mode_selector' или '01_home_mode_selector'
        stem = png.stem
        slug_no_prefix = stem[3:] if len(stem) > 3 and stem[:2].isdigit() and stem[2] == "_" else stem
        duration_ms = (
            duration_overrides.get(stem)
            or duration_overrides.get(slug_no_prefix)
            or default_ms
        )
        frames.append(ShotFrame(slug=stem, path=png, duration_ms=duration_ms))
    return frames


def _normalize_frame(img: Image.Image, max_width: int, colors: int) -> Image.Image:
    """Ресайз под max_width с сохранением аспекта; конверт в P (палитра) для компактного GIF."""
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    if img.width > max_width:
        ratio = max_width / img.width
        new_size = (max_width, max(1, int(img.height * ratio)))
        img = img.resize(new_size, Image.LANCZOS)
    # RGB для GIF-оптимизации (alpha gif даёт артефакты на Streamlit-шэдоах)
    rgb = Image.new("RGB", img.size, (255, 255, 255))
    if img.mode == "RGBA":
        rgb.paste(img, mask=img.split()[3])
    else:
        rgb.paste(img)
    return rgb.convert("P", palette=Image.ADAPTIVE, colors=colors)


def build_gif_for_scenario(
    scenario_id: str,
    screenshots_dir: Path,
    scenarios_dir: Path,
    max_width: int,
    default_ms: int,
    loop: int,
    colors: int = 64,
    optimize: bool = False,
) -> Path | None:
    scenario_dir = screenshots_dir / scenario_id
    if not scenario_dir.exists():
        return None

    yaml_candidates = list(scenarios_dir.glob(f"{scenario_id}_*.yaml")) + list(
        scenarios_dir.glob(f"{scenario_id}.yaml")
    )
    yaml_path = yaml_candidates[0] if yaml_candidates else Path()
    durations = _load_yaml_shots_duration(yaml_path) if yaml_path else {}

    frames = _collect_frames(scenario_dir, durations, default_ms)
    if not frames:
        return None

    images = []
    per_frame_durations: list[int] = []
    encode_started = time.perf_counter()
    for fr in frames:
        with Image.open(fr.path) as im:
            images.append(_normalize_frame(im, max_width, colors))
            per_frame_durations.append(fr.duration_ms)
    encode_sec = time.perf_counter() - encode_started

    # +500ms хвост для последнего кадра — чтобы «финальный слайд» задерживался
    per_frame_durations[-1] = per_frame_durations[-1] + 500

    out_path = scenario_dir / "demo.gif"
    save_started = time.perf_counter()
    images[0].save(
        out_path,
        save_all=True,
        append_images=images[1:],
        duration=per_frame_durations,
        loop=loop,
        optimize=optimize,
        disposal=2,
    )
    save_sec = time.perf_counter() - save_started
    size_kb = out_path.stat().st_size // 1024
    print(
        f"[demo-gifs] {scenario_id}: encode={encode_sec:.2f}s save={save_sec:.2f}s "
        f"{len(frames)} frames -> {out_path} ({size_kb} KB)"
    )
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--scenarios-dir",
        type=Path,
        default=DEFAULT_SCENARIOS,
        help="Каталог YAML-манифестов (default: doc/scenarios).",
    )
    parser.add_argument(
        "--screenshots-dir",
        type=Path,
        default=DEFAULT_SCREENSHOTS,
        help="Каталог скриншотов (default: doc/screenshots).",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        default=None,
        help="Конкретный scenario_id (можно повторять). По умолчанию — все.",
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=DEFAULT_MAX_WIDTH,
        help=f"Максимальная ширина GIF в пикселях (default: {DEFAULT_MAX_WIDTH}).",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=DEFAULT_FPS,
        help=(
            "Fallback FPS для кадров без duration_sec в YAML. "
            f"Default: {DEFAULT_FPS} (~{int(1000 / DEFAULT_FPS)} ms/frame)."
        ),
    )
    parser.add_argument(
        "--loop",
        type=int,
        default=0,
        help="Сколько раз повторять GIF (0 = бесконечно).",
    )
    parser.add_argument(
        "--colors",
        type=int,
        default=64,
        help="GIF palette size (default: 64).",
    )
    parser.add_argument(
        "--optimize",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable Pillow GIF optimization (default: false for faster demo builds).",
    )
    args = parser.parse_args()
    args.screenshots_dir = _resolve_screenshots_dir(args.screenshots_dir)

    default_ms = max(200, int(1000 / max(args.fps, 0.1)))

    if args.scenario:
        scenario_ids = args.scenario
    else:
        scenario_ids = sorted(
            p.name
            for p in args.screenshots_dir.iterdir()
            if p.is_dir() and p.name.startswith("scenario_")
        ) if args.screenshots_dir.exists() else []

    if not scenario_ids:
        print(
            f"[demo-gifs] нет папок scenario_* в {args.screenshots_dir}; "
            "запустите `npm run test:e2e:demo` сначала."
        )
        return 0

    worker_count = min(os.cpu_count() or 1, len(scenario_ids))
    build = partial(
        build_gif_for_scenario,
        screenshots_dir=args.screenshots_dir,
        scenarios_dir=args.scenarios_dir,
        max_width=args.max_width,
        default_ms=default_ms,
        loop=args.loop,
        colors=max(2, min(256, int(args.colors))),
        optimize=bool(args.optimize),
    )
    if worker_count <= 1:
        results = [build(sid) for sid in scenario_ids]
    else:
        with mp.Pool(processes=worker_count) as pool:
            results = pool.map(build, scenario_ids)
    built = sum(1 for result in results if result)

    print(f"[demo-gifs] done: {built}/{len(scenario_ids)} GIFs built")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
