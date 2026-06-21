#!/usr/bin/env python3
"""
Префлайт переоткрытия пакета: статус в backlog_registry + напоминание Step C.

Не выполняет правки — только диагностика и ссылки на канон.

Примеры:

  .\\.venv\\Scripts\\python.exe scripts/print_reopen_package_workflow.py --package epoch-demo
  .\\.venv\\Scripts\\python.exe scripts/print_reopen_package_workflow.py --package epoch-home-mode-preview-drawer --reason "DOD FAIL e2e"

Канон процедуры (ручные правки): doc/team_workflow/reopen_package_step_c_prompt.md
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "doc" / "backlog_registry.yaml"
REOPEN_DOC = ROOT / "doc" / "team_workflow" / "reopen_package_step_c_prompt.md"

sys.path.insert(0, str(ROOT / "scripts"))
from script_stdio_utf8 import configure_stdio_utf8  # noqa: E402

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def load_registry_package_status(package_id: str) -> str | None:
    """Статус записи пакета в ``doc/backlog_registry.yaml`` или ``None``, если записи нет."""
    if yaml is None:
        raise RuntimeError("PyYAML is required (same as backlog_registry_lint).")
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    for pkg in data.get("items") or []:
        if pkg.get("id") == package_id:
            st = pkg.get("status")
            return str(st).strip() if st else None
    return None


def _validate_today(s: str) -> str:
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use YYYY-MM-DD for --today") from exc
    return s


def main() -> int:
    configure_stdio_utf8()
    ap = argparse.ArgumentParser(
        description="Print reopen Step C hints and backlog status for PACKAGE_ID.",
    )
    ap.add_argument("--package", required=True, help="Package id, e.g. epoch-demo")
    ap.add_argument(
        "--reason",
        default="(укажи REASON: INDEX_FAIL / DOD FAIL / STALE + кратко)",
        help="Подставляется в напоминание для оператора",
    )
    ap.add_argument(
        "--today",
        type=_validate_today,
        default=None,
        metavar="YYYY-MM-DD",
        help="Дата для полей Step C (по умолчанию сегодня по локальному календарю)",
    )
    args = ap.parse_args()
    today = args.today or date.today().isoformat()

    try:
        status = load_registry_package_status(args.package)
    except FileNotFoundError:
        print(f"ERROR: registry not found: {REGISTRY}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    exe = sys.executable
    lint_cmd = f"{exe} scripts/backlog_registry_lint.py --sync-from-index --write-sync"

    print(f"Package:           {args.package}")
    print(f"registry status:   {status!r}")
    print(f"TODAY (для Step C): {today}")
    print(f"REASON (шаблон):   {args.reason}")
    print()
    print(f"Канон + копипаста: {REOPEN_DOC}")
    print()

    if status is None:
        print("→ Записи нет в doc/backlog_registry.yaml.")
        print("  Для epoch-demo: см. scripts/print_epoch_demo_agent_prompts.py package или")
        print("  run_autonomous.py --smoke --auto-prepare-epoch-demo (каркас, не полный Step C).")
        return 1

    if status == "closed":
        print("→ Статус closed: перед smoke/orchestration нужен полный Step C (C.1–C.8 + doc/current_task.md).")
        print("  Флаги --auto-prepare-epoch-demo / минимальный scaffold не заменяют audit-grade reopen.")
        print()
        print("После правок документов:")
        print(f"  {lint_cmd}")
        return 0

    if status in ("ready", "wip", "proposed", "deferred"):
        print(f"→ Статус «{status}»: отдельный audit reopen (closed→ready) не требуется.")
        print("  Перед прогоном: synced tasklist, при необходимости выровняй doc/current_task.md под этот PACKAGE_ID.")
        print()
        print("При смене фокуса пакета вручную:")
        print(f"  {lint_cmd}")
        return 0

    print(f"→ Нестандартный статус {status!r} — сверься с backlog_registry_lint ALLOWED_STATUS.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
