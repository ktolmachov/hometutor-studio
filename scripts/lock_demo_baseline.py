#!/usr/bin/env python3
"""Lock/verify demo screenshot baseline using normalized image hashes."""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
from pathlib import Path

from PIL import Image


def _normalized_sha256(image_path: Path) -> str:
    with Image.open(image_path) as image:
        rgb = image.convert("RGB")
        buf = BytesIO()
        rgb.save(buf, format="PNG", optimize=False)
    return hashlib.sha256(buf.getvalue()).hexdigest()


def _iter_pngs(screenshots_dir: Path) -> list[Path]:
    return sorted(path for path in screenshots_dir.glob("scenario_*/*.png") if path.is_file())


def _write_baseline(screenshots_dir: Path, baseline_dir: Path) -> int:
    files = _iter_pngs(screenshots_dir)
    if not files:
        raise SystemExit(f"No PNG files found in {screenshots_dir}")
    for image_path in files:
        scenario = image_path.parent.name
        frame_name = image_path.stem
        out_dir = baseline_dir / scenario
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{frame_name}.sha256").write_text(
            _normalized_sha256(image_path) + "\n",
            encoding="utf-8",
        )
    print(f"[baseline] wrote {len(files)} hashes into {baseline_dir}")
    return 0


def _verify_baseline(screenshots_dir: Path, baseline_dir: Path) -> int:
    files = _iter_pngs(screenshots_dir)
    if not files:
        raise SystemExit(f"No PNG files found in {screenshots_dir}")

    mismatches: list[str] = []
    missing_hash_files: list[str] = []
    for image_path in files:
        scenario = image_path.parent.name
        frame_name = image_path.stem
        hash_path = baseline_dir / scenario / f"{frame_name}.sha256"
        if not hash_path.exists():
            missing_hash_files.append(f"{scenario}/{frame_name}.sha256")
            continue
        expected = hash_path.read_text(encoding="utf-8").strip()
        actual = _normalized_sha256(image_path)
        if expected != actual:
            mismatches.append(
                f"{scenario}/{image_path.name}: expected={expected[:12]} actual={actual[:12]}"
            )

    if missing_hash_files or mismatches:
        if missing_hash_files:
            print("[baseline] missing hash files:")
            for item in missing_hash_files:
                print(f"  - {item}")
        if mismatches:
            print("[baseline] hash mismatches:")
            for item in mismatches:
                print(f"  - {item}")
        return 1
    print(f"[baseline] verify OK for {len(files)} frames")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screenshots-dir", type=Path, required=True)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    if args.verify:
        return _verify_baseline(args.screenshots_dir, args.baseline_dir)
    return _write_baseline(args.screenshots_dir, args.baseline_dir)


if __name__ == "__main__":
    raise SystemExit(main())
