#!/usr/bin/env python3
"""
Smart Demo workflow orchestrator.

Единая точка входа для актуализации Smart Demo:
preflight → capture (Playwright) → GIF → publish → strict validate.

Примеры:

    .\\.venv\\Scripts\\python.exe scripts/demo_workflow.py list
    .\\.venv\\Scripts\\python.exe scripts/demo_workflow.py preflight
    .\\.venv\\Scripts\\python.exe scripts/demo_workflow.py capture --run 2026-06-20
    .\\.venv\\Scripts\\python.exe scripts/demo_workflow.py preview --run 2026-06-20
    .\\.venv\\Scripts\\python.exe scripts/demo_workflow.py publish --run 2026-06-20
    .\\.venv\\Scripts\\python.exe scripts/demo_workflow.py full
    .\\.venv\\Scripts\\python.exe scripts/demo_workflow.py full --scenario-id scenario_21

Переменные окружения:
    DEMO_SHOT_RUN — папка прогона `doc/screenshots/<YYYY-MM-DD>/` (задаётся автоматически).
    HOME_RAG_E2E_OFFLINE=1 — offline-съёмка без live LLM (default для capture/full).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_DIR = ROOT / "doc" / "scenarios"
DEMOS_DIR = ROOT / "tests" / "e2e" / "demos"
SCREENSHOTS_ROOT = ROOT / "doc" / "screenshots"
FINAL_DIR = SCREENSHOTS_ROOT / "final"
PREVIEW_DOC = ROOT / "doc" / "quickstart_demo.preview.md"
PUBLISH_DOC = ROOT / "doc" / "quickstart_demo.md"

RUN_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
YAML_ID_RE = re.compile(r"^id:\s*(scenario_\d{2})\s*$", re.MULTILINE)
YAML_SHOT_SLUG_RE = re.compile(r'^\s*-\s*slug:\s*["\']?([^"\']+)["\']?\s*$', re.MULTILINE)
RECORDER_RE = re.compile(r"createDemoRecorder\(\s*page\s*,\s*['\"](scenario_\d{2})['\"]")
SPEC_SHOT_RE = re.compile(r"\.shot\(\s*['\"]([^'\"]+)['\"]")


@dataclass(frozen=True)
class ScenarioRow:
    scenario_id: str
    yaml_path: Path | None
    spec_path: Path | None
    shot_count: int
    captured_count: int
    run_dir: Path | None


def _python_exe() -> Path:
    venv = ROOT / ".venv" / "Scripts" / "python.exe"
    if venv.is_file():
        return venv
    return Path(sys.executable)


def _today_run() -> str:
    return date.today().isoformat()


def _resolve_run_dir(run: str | None) -> tuple[str, Path]:
    run_name = (run or os.environ.get("DEMO_SHOT_RUN") or _today_run()).strip()
    if not RUN_DIR_RE.match(run_name):
        raise SystemExit(f"Invalid run folder name (expected YYYY-MM-DD): {run_name!r}")
    return run_name, SCREENSHOTS_ROOT / run_name


def _resolve_path_command(name: str) -> str:
    """Resolve CLI on Windows (`npm.cmd`, `npx.cmd`) for subprocess without shell."""
    if os.name == "nt":
        for candidate in (f"{name}.cmd", f"{name}.exe", name):
            path = shutil.which(candidate)
            if path:
                return path
    path = shutil.which(name)
    if not path:
        raise SystemExit(
            f"[demo-workflow] command not found: {name!r}. "
            "Install Node.js/npm or run Playwright manually: npm run test:e2e:demo"
        )
    return path


def _run(
    cmd: list[str],
    *,
    env: dict[str, str] | None = None,
    dry_run: bool = False,
) -> int:
    label = " ".join(cmd)
    print(f"[demo-workflow] $ {label}")
    if dry_run:
        return 0
    merged = os.environ.copy()
    if env:
        merged.update(env)
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=merged,
        check=False,
    )
    if proc.returncode != 0:
        print(f"[demo-workflow] FAILED ({proc.returncode}): {label}", file=sys.stderr)
    return proc.returncode


def _load_yaml_ids() -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    for path in sorted(SCENARIOS_DIR.glob("scenario_*.yaml")):
        text = path.read_text(encoding="utf-8")
        match = YAML_ID_RE.search(text)
        if match:
            mapping[match.group(1)] = path
    return mapping


def _load_spec_ids() -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    for path in sorted(DEMOS_DIR.glob("scenario_*.spec.ts")):
        text = path.read_text(encoding="utf-8")
        match = RECORDER_RE.search(text)
        if match:
            mapping[match.group(1)] = path
    return mapping


def _count_yaml_shots(path: Path) -> int:
    return len(YAML_SHOT_SLUG_RE.findall(path.read_text(encoding="utf-8")))


def _count_spec_shots(path: Path) -> int:
    return len(SPEC_SHOT_RE.findall(path.read_text(encoding="utf-8")))


def _count_captured(run_dir: Path | None, scenario_id: str) -> int:
    if run_dir is None:
        return 0
    scenario_dir = run_dir / scenario_id
    if not scenario_dir.is_dir():
        return 0
    return len(list(scenario_dir.glob("*.png")))


def _collect_rows(run: str | None) -> list[ScenarioRow]:
    yaml_map = _load_yaml_ids()
    spec_map = _load_spec_ids()
    all_ids = sorted(set(yaml_map) | set(spec_map))
    _, run_dir = _resolve_run_dir(run)
    run_path = run_dir if run_dir.is_dir() else None

    rows: list[ScenarioRow] = []
    for scenario_id in all_ids:
        yaml_path = yaml_map.get(scenario_id)
        spec_path = spec_map.get(scenario_id)
        shot_count = 0
        if yaml_path is not None:
            shot_count = _count_yaml_shots(yaml_path)
        elif spec_path is not None:
            shot_count = _count_spec_shots(spec_path)
        rows.append(
            ScenarioRow(
                scenario_id=scenario_id,
                yaml_path=yaml_path,
                spec_path=spec_path,
                shot_count=shot_count,
                captured_count=_count_captured(run_path, scenario_id),
                run_dir=run_path,
            )
        )
    return rows


def _status_icon(row: ScenarioRow) -> str:
    if row.yaml_path is None or row.spec_path is None:
        return "WARN"
    if row.captured_count == 0:
        return "MISS"
    if row.captured_count >= row.shot_count and row.shot_count > 0:
        return "OK"
    return "PART"


def cmd_list(args: argparse.Namespace) -> int:
    rows = _collect_rows(args.run)
    run_name, run_dir = _resolve_run_dir(args.run)
    print(f"Smart Demo scenarios ({len(rows)} total)")
    print(f"Run folder: {run_name} ({'exists' if run_dir.is_dir() else 'missing'})")
    print()
    print(f"{'ID':<14} {'YAML':<5} {'SPEC':<5} {'Shots':<7} {'PNG':<7} Status")
    print("-" * 58)
    for row in rows:
        yaml_ok = "yes" if row.yaml_path else "no"
        spec_ok = "yes" if row.spec_path else "no"
        shots = f"{row.captured_count}/{row.shot_count}" if row.shot_count else "-"
        print(
            f"{row.scenario_id:<14} {yaml_ok:<5} {spec_ok:<5} {row.shot_count:<7} "
            f"{row.captured_count:<7} {_status_icon(row)} {shots}"
        )
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    py = str(_python_exe())
    code = 0
    code |= _run([py, "scripts/check_scenario_ids.py"], dry_run=args.dry_run)
    validate_cmd = [py, "scripts/validate_demo_contract.py"]
    if args.run:
        _, run_dir = _resolve_run_dir(args.run)
        validate_cmd.extend(["--screenshots-dir", str(run_dir)])
    for scenario_id in args.scenario_id:
        validate_cmd.extend(["--scenario-id", scenario_id])
    code |= _run(validate_cmd, dry_run=args.dry_run)
    return 1 if code else 0


def _playwright_cmd(scenario_ids: list[str]) -> list[str]:
    npm = _resolve_path_command("npm")
    cmd = [npm, "run", "test:e2e:demo", "--"]
    if scenario_ids:
        for scenario_id in scenario_ids:
            matches = sorted(DEMOS_DIR.glob(f"{scenario_id}_*.spec.ts"))
            if not matches:
                matches = sorted(DEMOS_DIR.glob(f"{scenario_id}.spec.ts"))
            if not matches:
                raise SystemExit(f"No demo spec found for {scenario_id}")
            cmd.append(str(matches[0].relative_to(ROOT)).replace("\\", "/"))
    return cmd


def cmd_capture(args: argparse.Namespace) -> int:
    run_name, run_dir = _resolve_run_dir(args.run)
    env = {
        "DEMO_SHOT_RUN": run_name,
        "HOME_RAG_E2E_OFFLINE": os.environ.get("HOME_RAG_E2E_OFFLINE", "1"),
    }
    print(f"[demo-workflow] capture → {run_dir}")
    return _run(_playwright_cmd(args.scenario_id), env=env, dry_run=args.dry_run)


def cmd_gifs(args: argparse.Namespace) -> int:
    py = str(_python_exe())
    cmd = [py, "scripts/make_demo_gifs.py"]
    if getattr(args, "fast", False):
        cmd.extend(["--no-optimize", "--colors", "64"])
    run_name, run_dir = _resolve_run_dir(args.run)
    env = {"DEMO_SHOT_RUN": run_name}
    return _run(cmd, env=env, dry_run=args.dry_run)


def cmd_preview(args: argparse.Namespace) -> int:
    py = str(_python_exe())
    _, run_dir = _resolve_run_dir(args.run)
    return _run(
        [
            py,
            "scripts/generate_demo_doc.py",
            "--screenshots-dir",
            str(run_dir),
            "--output",
            str(PREVIEW_DOC),
            "--no-final-sync",
        ],
        dry_run=args.dry_run,
    )


def cmd_publish(args: argparse.Namespace) -> int:
    py = str(_python_exe())
    _, run_dir = _resolve_run_dir(args.run)
    return _run(
        [
            py,
            "scripts/generate_demo_doc.py",
            "--screenshots-dir",
            str(run_dir),
            "--output",
            str(PUBLISH_DOC),
        ],
        dry_run=args.dry_run,
    )


def cmd_validate(args: argparse.Namespace) -> int:
    py = str(_python_exe())
    _, run_dir = _resolve_run_dir(args.run)
    cmd = [
        py,
        "scripts/validate_demo_contract.py",
        "--screenshots-dir",
        str(FINAL_DIR if FINAL_DIR.is_dir() and getattr(args, "use_final", False) else run_dir),
        "--require-screenshots",
        "--strict-captures",
        "--require-unique-shots",
    ]
    for scenario_id in args.scenario_id:
        cmd.extend(["--scenario-id", scenario_id])
    return _run(cmd, dry_run=args.dry_run)


def cmd_full(args: argparse.Namespace) -> int:
    steps: list[tuple[str, int]] = []

    def _step(name: str, rc: int) -> None:
        steps.append((name, rc))
        if rc and not args.continue_on_error:
            raise SystemExit(rc)

    _step("preflight", cmd_preflight(args))
    if not args.skip_capture:
        _step("capture", cmd_capture(args))
    if not args.skip_gifs:
        _step("gifs", cmd_gifs(args))
    _step("publish", cmd_publish(args))
    _step("validate", cmd_validate(argparse.Namespace(**{**vars(args), "use_final": True})))

    failed = [name for name, rc in steps if rc]
    print()
    print("[demo-workflow] summary:")
    for name, rc in steps:
        mark = "OK" if rc == 0 else "FAIL"
        print(f"  {mark}: {name}")
    if failed:
        print(f"[demo-workflow] full workflow failed at: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("[demo-workflow] full workflow complete")
    print(f"  screenshots: {SCREENSHOTS_ROOT / _resolve_run_dir(args.run)[0]}")
    print(f"  final:       {FINAL_DIR}")
    print(f"  doc:         {PUBLISH_DOC}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        default="",
        help="Папка прогона YYYY-MM-DD (default: сегодня или DEMO_SHOT_RUN).",
    )
    parser.add_argument(
        "--scenario-id",
        action="append",
        default=[],
        help="Ограничить capture/validate одним или несколькими scenario_XX.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Показать команды без запуска.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="Таблица YAML/spec/screenshots по всем сценариям.").set_defaults(
        func=cmd_list
    )

    preflight = sub.add_parser("preflight", help="check_scenario_ids + мягкий validate.")
    preflight.set_defaults(func=cmd_preflight)

    capture = sub.add_parser("capture", help="Playwright demo-съёмка в doc/screenshots/<RUN>/.")
    capture.set_defaults(func=cmd_capture)

    gifs = sub.add_parser("gifs", help="Сборка GIF из PNG прогона.")
    gifs.add_argument("--fast", action="store_true", help="Быстрая сборка (--no-optimize --colors 64).")
    gifs.set_defaults(func=cmd_gifs)

    preview = sub.add_parser("preview", help="Черновик doc/quickstart_demo.preview.md без final/.")
    preview.set_defaults(func=cmd_preview)

    publish = sub.add_parser("publish", help="Публикация doc/quickstart_demo.md + doc/screenshots/final/.")
    publish.set_defaults(func=cmd_publish)

    validate = sub.add_parser("validate", help="Strict quality gate для прогона или final/.")
    validate.add_argument(
        "--use-final",
        action="store_true",
        help="Проверять doc/screenshots/final/ вместо RUN (default для full).",
    )
    validate.set_defaults(func=cmd_validate, use_final=False)

    full = sub.add_parser("full", help="preflight → capture → gifs → publish → validate.")
    full.add_argument("--skip-capture", action="store_true", help="Пропустить Playwright-съёмку.")
    full.add_argument("--skip-gifs", action="store_true", help="Пропустить make_demo_gifs.py.")
    full.add_argument("--fast", action="store_true", help="Быстрая сборка GIF (--no-optimize --colors 64).")
    full.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Не останавливаться после первой ошибки (для диагностики).",
    )
    full.set_defaults(func=cmd_full, use_final=True)

    parser.set_defaults(
        fast=False,
        skip_capture=False,
        skip_gifs=False,
        continue_on_error=False,
    )

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    selected = [str(s).strip() for s in (args.scenario_id or []) if str(s).strip()]
    args.scenario_id = list(dict.fromkeys(selected))
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
