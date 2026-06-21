#!/usr/bin/env python3
"""
Резервное копирование / восстановление индексных артефактов (итерация 16 tail).

Запуск из корня репозитория:

  python scripts/backup_index.py create backups/index_2026.zip
  python scripts/backup_index.py create backups/index.zip --include-faq
  python scripts/backup_index.py restore backups/index_2026.zip

Перед restore остановите API. После restore перезапустите процесс — поднимется с восстановленным индексом.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    from app.index_backup import create_backup_zip, restore_backup_zip

    parser = argparse.ArgumentParser(description="Backup / restore index artifacts")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_create = sub.add_parser("create", help="Создать ZIP")
    p_create.add_argument("archive", type=Path, help="Путь к .zip")
    p_create.add_argument(
        "--include-faq",
        action="store_true",
        help="Включить faq_memory.jsonl (если есть)",
    )
    p_create.add_argument(
        "--no-concept-graph",
        action="store_true",
        help="Не включать data/concept_graph.json",
    )

    p_restore = sub.add_parser("restore", help="Восстановить из ZIP в корень проекта")
    p_restore.add_argument("archive", type=Path, help="Путь к .zip")

    args = parser.parse_args()

    if args.cmd == "create":
        m = create_backup_zip(
            args.archive.resolve(),
            include_concept_graph=not args.no_concept_graph,
            include_faq_memory=args.include_faq,
        )
        print(f"OK: {len(m.get('entries', []))} files -> {args.archive}")
        return 0

    if args.cmd == "restore":
        m = restore_backup_zip(args.archive.resolve())
        print(f"OK: restored {len(m.get('entries', []))} entries (see logs)")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
