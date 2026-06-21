#!/usr/bin/env python3
"""Validate demo scenario manifests, Playwright demo specs, and screenshots."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: install project dependencies first") from exc


DEFAULT_SCENARIOS_DIR = Path("doc/scenarios")
DEFAULT_DEMOS_DIR = Path("tests/e2e/demos")
DEFAULT_SCREENSHOTS_DIR = Path("doc/screenshots")

# Папка прогона: `YYYY-MM-DD`
RUN_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def resolve_screenshots_dir_arg(requested: Path) -> Path:
    """Если default `doc/screenshots` — выбрать датированный прогон или плоскую вёрстку."""
    if requested != DEFAULT_SCREENSHOTS_DIR:
        return requested
    run = (os.environ.get("DEMO_SHOT_RUN") or "").strip()
    if run and RUN_DIR_RE.match(run) and (DEFAULT_SCREENSHOTS_DIR / run).is_dir():
        return DEFAULT_SCREENSHOTS_DIR / run
    if (DEFAULT_SCREENSHOTS_DIR / "scenario_01").is_dir() or (
        DEFAULT_SCREENSHOTS_DIR / "scenario_02"
    ).is_dir():
        return DEFAULT_SCREENSHOTS_DIR
    dated = sorted(
        (
            p
            for p in DEFAULT_SCREENSHOTS_DIR.iterdir()
            if p.is_dir() and RUN_DIR_RE.match(p.name)
        ),
        key=lambda p: p.name,
    )
    if dated:
        return dated[-1]
    return requested

RECORDER_RE = re.compile(r"createDemoRecorder\(\s*page\s*,\s*['\"]([^'\"]+)['\"]")
SHOT_RE = re.compile(r"\.shot\(\s*['\"]([^'\"]+)['\"]")


@dataclass
class Scenario:
    scenario_id: str
    manifest_path: Path
    shots: list[str]
    requires: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def _load_scenarios(scenarios_dir: Path, result: ValidationResult) -> list[Scenario]:
    scenarios: list[Scenario] = []
    seen_ids: set[str] = set()

    for path in sorted(scenarios_dir.glob("scenario_*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            result.error(f"{path}: cannot parse YAML: {exc}")
            continue

        if not isinstance(data, dict):
            result.error(f"{path}: manifest root must be a mapping")
            continue

        scenario_id = data.get("id")
        if not isinstance(scenario_id, str) or not scenario_id:
            result.error(f"{path}: missing string id")
            continue
        if scenario_id in seen_ids:
            result.error(f"{path}: duplicate scenario id {scenario_id!r}")
        seen_ids.add(scenario_id)

        raw_shots = data.get("shots")
        if not isinstance(raw_shots, list) or not raw_shots:
            result.error(f"{path}: shots must be a non-empty list")
            shots: list[str] = []
        else:
            shots = []
            seen_shots: set[str] = set()
            for index, shot in enumerate(raw_shots, start=1):
                slug = shot.get("slug") if isinstance(shot, dict) else None
                if not isinstance(slug, str) or not slug:
                    result.error(f"{path}: shots[{index}] missing string slug")
                    continue
                if not re.match(r"^\d{2}_[a-z0-9_.-]+$", slug):
                    result.error(f"{path}: shot slug must start with NN_ and be path-safe: {slug}")
                if slug in seen_shots:
                    result.error(f"{path}: duplicate shot slug {slug!r}")
                seen_shots.add(slug)
                shots.append(slug)

        requires = data.get("requires")
        if requires is None:
            result.warn(f"{path}: missing requires block")
            requires = {}
        elif not isinstance(requires, dict):
            result.error(f"{path}: requires must be a mapping")
            requires = {}

        scenarios.append(
            Scenario(
                scenario_id=scenario_id,
                manifest_path=path,
                shots=shots,
                requires=requires,
            )
        )

    if not scenarios:
        result.error(f"{scenarios_dir}: no scenario_*.yaml manifests found")
    return scenarios


def _load_demo_specs(demos_dir: Path, result: ValidationResult) -> dict[str, tuple[Path, list[str]]]:
    specs: dict[str, tuple[Path, list[str]]] = {}

    for path in sorted(demos_dir.glob("scenario_*.spec.ts")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            result.error(f"{path}: cannot read demo spec: {exc}")
            continue

        recorder_ids = RECORDER_RE.findall(text)
        if not recorder_ids:
            result.error(f"{path}: missing createDemoRecorder(page, 'scenario_XX')")
            continue
        if len(set(recorder_ids)) != 1:
            result.error(f"{path}: multiple scenario ids in createDemoRecorder: {recorder_ids}")
            continue

        scenario_id = recorder_ids[0]
        shots = _unique_in_order(SHOT_RE.findall(text))
        if not shots:
            result.error(f"{path}: no demo.shot(...) calls found")
        if scenario_id in specs:
            result.error(f"{path}: duplicate demo spec for {scenario_id}; first is {specs[scenario_id][0]}")
        specs[scenario_id] = (path, shots)

    return specs


def _unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value not in seen:
            unique.append(value)
            seen.add(value)
    return unique


def _is_expected_png(file_name: str, slug: str) -> bool:
    return file_name == f"{slug}.png" or re.match(rf"^\d{{2}}_{re.escape(slug)}\.png$", file_name) is not None


def _is_known_or_legacy_png(file_name: str, known_files: set[str], known_legacy_files: set[str]) -> bool:
    return file_name in known_files or file_name in known_legacy_files


def _validate_specs(
    scenarios: list[Scenario],
    specs: dict[str, tuple[Path, list[str]]],
    result: ValidationResult,
) -> None:
    expected_ids = {scenario.scenario_id for scenario in scenarios}

    for scenario in scenarios:
        spec = specs.get(scenario.scenario_id)
        if spec is None:
            result.error(f"{scenario.scenario_id}: missing demo spec")
            continue

        spec_path, spec_shots = spec
        if spec_shots != scenario.shots:
            result.error(
                f"{scenario.scenario_id}: YAML shots != spec shots "
                f"({scenario.manifest_path} vs {spec_path}); "
                f"yaml={scenario.shots}, spec={spec_shots}"
            )
        else:
            result.summary.append(f"{scenario.scenario_id}: YAML/spec shots OK ({len(scenario.shots)})")

        offline_friendly = scenario.requires.get("offline_friendly")
        openai_required = scenario.requires.get("openai_api_key")
        if offline_friendly is True and openai_required is True:
            result.error(f"{scenario.scenario_id}: cannot be offline_friendly and require openai_api_key")

    for scenario_id, (path, _shots) in specs.items():
        if scenario_id not in expected_ids:
            result.error(f"{path}: demo spec has no YAML manifest for {scenario_id}")


def _validate_unique_shots(
    scenario_id: str,
    scenario_dir: Path,
    meta_shots: list,
    require_unique_shots: bool,
    result: ValidationResult,
) -> None:
    """Каждый PNG внутри сценария должен быть визуально уникален.

    Истина: если два кадра одного сценария — байт-идентичные файлы, тест
    очевидно не произвёл действия между ними (см. регрессию scenario_01 shots
    03–05 до этого фикса). Считаем хеш от сырых байтов PNG; коллизия -> error
    при `require_unique_shots`, иначе warn.
    """
    import hashlib

    seen: dict[str, str] = {}
    duplicates: list[tuple[str, str, str]] = []
    for shot in meta_shots:
        if not isinstance(shot, dict):
            continue
        slug = shot.get("slug")
        file_name = shot.get("file")
        if not isinstance(slug, str) or not isinstance(file_name, str):
            continue
        path = scenario_dir / file_name
        if not path.exists():
            continue
        try:
            digest = hashlib.md5(path.read_bytes()).hexdigest()
        except OSError:
            continue
        if digest in seen:
            duplicates.append((slug, seen[digest], digest))
        else:
            seen[digest] = slug
    for slug, other_slug, digest in duplicates:
        message = (
            f"{scenario_id}: shot {slug!r} byte-identical to {other_slug!r} "
            f"(md5={digest}) -- test did not change DOM between captures"
        )
        if require_unique_shots:
            result.error(message)
        else:
            result.warn(message)


def _validate_screenshots(
    scenarios: list[Scenario],
    screenshots_dir: Path,
    strict_captures: bool,
    require_screenshots: bool,
    require_unique_shots: bool,
    result: ValidationResult,
) -> None:
    expected_ids = {scenario.scenario_id for scenario in scenarios}

    if not screenshots_dir.exists():
        message = f"{screenshots_dir}: screenshots directory does not exist"
        if require_screenshots:
            result.error(message)
        else:
            result.warn(message)
        return

    for scenario in scenarios:
        scenario_dir = screenshots_dir / scenario.scenario_id
        meta_path = scenario_dir / "meta.json"
        if not meta_path.exists():
            message = f"{scenario.scenario_id}: missing {meta_path}"
            if require_screenshots:
                result.error(message)
            else:
                result.warn(message)
            continue

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            result.error(f"{meta_path}: cannot parse JSON: {exc}")
            continue

        if meta.get("scenario_id") != scenario.scenario_id:
            result.error(f"{meta_path}: scenario_id mismatch: {meta.get('scenario_id')!r}")
        if meta.get("status") == "failed":
            result.error(f"{meta_path}: status is failed")

        meta_shots = meta.get("shots")
        if not isinstance(meta_shots, list):
            result.error(f"{meta_path}: shots must be a list")
            continue

        captured_slugs: list[str] = []
        for index, shot in enumerate(meta_shots, start=1):
            if not isinstance(shot, dict):
                result.error(f"{meta_path}: shots[{index}] must be an object")
                continue
            slug = shot.get("slug")
            file_name = shot.get("file")
            if not isinstance(slug, str) or not slug:
                result.error(f"{meta_path}: shots[{index}] missing slug")
                continue
            captured_slugs.append(slug)
            if slug not in scenario.shots:
                result.error(f"{meta_path}: captured unknown shot {slug!r}")
            if not isinstance(file_name, str) or not file_name:
                result.error(f"{meta_path}: shot {slug!r} missing file")
                continue
            if not (scenario_dir / file_name).exists():
                result.error(f"{meta_path}: shot {slug!r} file does not exist: {file_name}")
            if not _is_expected_png(file_name, slug):
                result.warn(f"{meta_path}: shot {slug!r} file is {file_name!r}, expected {slug}.png")

        if captured_slugs != scenario.shots:
            missing = [slug for slug in scenario.shots if slug not in captured_slugs]
            extra = [slug for slug in captured_slugs if slug not in scenario.shots]
            message = (
                f"{scenario.scenario_id}: captured shots differ from YAML; "
                f"missing={missing}, extra={extra}, captured={captured_slugs}"
            )
            if strict_captures:
                result.error(message)
            else:
                result.warn(message)
        else:
            result.summary.append(f"{scenario.scenario_id}: screenshots/meta shots OK ({len(captured_slugs)})")

        _validate_unique_shots(
            scenario.scenario_id,
            scenario_dir,
            meta_shots,
            require_unique_shots,
            result,
        )

        png_files = sorted(path.name for path in scenario_dir.glob("*.png"))
        known_files = {f"{slug}.png" for slug in scenario.shots}
        known_legacy_files = {f"{index:02d}_{slug}.png" for index, slug in enumerate(scenario.shots, start=1)}
        stale_files = [
            name for name in png_files if not _is_known_or_legacy_png(name, known_files, known_legacy_files)
        ]
        if stale_files:
            message = f"{scenario.scenario_id}: stale PNG files not present in YAML: {stale_files}"
            if require_screenshots:
                result.error(message)
            else:
                result.warn(message)

    for scenario_dir in sorted(path for path in screenshots_dir.iterdir() if path.is_dir()):
        if scenario_dir.name not in expected_ids:
            result.warn(f"{scenario_dir}: screenshots directory has no YAML manifest")


def validate(args: argparse.Namespace) -> ValidationResult:
    result = ValidationResult()
    scenarios = _load_scenarios(args.scenarios_dir, result)
    selected_ids = [str(s).strip() for s in getattr(args, "scenario_id", []) if str(s).strip()]
    if not selected_ids:
        # Safety net for partial runs: when screenshots-dir contains exactly one
        # scenario_* folder, validate that scenario only instead of requiring all.
        try:
            present_dirs = sorted(
                path.name
                for path in args.screenshots_dir.iterdir()
                if path.is_dir() and re.match(r"^scenario_\d{2}$", path.name)
            )
        except OSError:
            present_dirs = []
        if len(present_dirs) == 1:
            selected_ids = [present_dirs[0]]
    if selected_ids:
        selected_set = set(selected_ids)
        known_ids = {scenario.scenario_id for scenario in scenarios}
        unknown_ids = [scenario_id for scenario_id in selected_ids if scenario_id not in known_ids]
        for scenario_id in unknown_ids:
            result.error(f"unknown --scenario-id: {scenario_id}")
        scenarios = [scenario for scenario in scenarios if scenario.scenario_id in selected_set]
        if not scenarios:
            result.error("no scenarios matched --scenario-id filter")
    specs = _load_demo_specs(args.demos_dir, result)
    if selected_ids:
        # When validating only selected scenario ids, do not require YAML manifests
        # for every demo spec in the repo.
        selected_set = set(selected_ids)
        specs = {sid: spec for sid, spec in specs.items() if sid in selected_set}
    _validate_specs(scenarios, specs, result)
    _validate_screenshots(
        scenarios,
        args.screenshots_dir,
        strict_captures=args.strict_captures,
        require_screenshots=args.require_screenshots,
        require_unique_shots=args.require_unique_shots,
        result=result,
    )
    if args.verify_baseline:
        cmd = [
            sys.executable,
            str(Path("scripts") / "lock_demo_baseline.py"),
            "--screenshots-dir",
            str(args.screenshots_dir),
            "--baseline-dir",
            str(args.verify_baseline),
            "--verify",
        ]
        check = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if check.returncode != 0:
            result.error(
                "baseline verification failed: "
                + (check.stdout.strip() or check.stderr.strip() or "unknown error")
            )
        elif check.stdout.strip():
            result.summary.append(f"baseline verify: {check.stdout.strip()}")
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios-dir", type=Path, default=DEFAULT_SCENARIOS_DIR)
    parser.add_argument("--demos-dir", type=Path, default=DEFAULT_DEMOS_DIR)
    parser.add_argument("--screenshots-dir", type=Path, default=DEFAULT_SCREENSHOTS_DIR)
    parser.add_argument(
        "--require-screenshots",
        action="store_true",
        help="Fail when screenshot meta is missing.",
    )
    parser.add_argument(
        "--strict-captures",
        action="store_true",
        help="Fail when meta.json does not contain every YAML shot.",
    )
    parser.add_argument(
        "--require-unique-shots",
        action="store_true",
        help=(
            "Fail when two shots of the same scenario are byte-identical PNGs. "
            "Catches regressions where a test takes multiple screenshots without "
            "actually interacting with the UI between them."
        ),
    )
    parser.add_argument(
        "--verify-baseline",
        type=Path,
        default=None,
        help="Path to baseline hashes directory produced by lock_demo_baseline.py.",
    )
    parser.add_argument(
        "--scenario-id",
        action="append",
        default=[],
        help=(
            "Validate only selected scenario id(s), e.g. --scenario-id scenario_07. "
            "Can be passed multiple times."
        ),
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    args.screenshots_dir = resolve_screenshots_dir_arg(args.screenshots_dir)
    selected_ids = [str(s).strip() for s in (args.scenario_id or []) if str(s).strip()]
    if selected_ids:
        args.scenario_id = list(dict.fromkeys(selected_ids))
    else:
        args.scenario_id = []
    result = validate(args)

    for line in result.summary:
        print(f"OK: {line}")
    for warning in result.warnings:
        print(f"WARN: {warning}")
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)

    if result.errors:
        print(
            f"DEMO CONTRACT FAILED: {len(result.errors)} error(s), {len(result.warnings)} warning(s)",
            file=sys.stderr,
        )
        return 1

    print(f"DEMO CONTRACT OK: {len(result.warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
