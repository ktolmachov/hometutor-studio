#!/usr/bin/env python3
"""Validate and inspect replay artifacts for one autonomous run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_recorder import build_replay_manifest, validate_replay_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    manifest = build_replay_manifest(args.run_id)
    errors = validate_replay_manifest(manifest)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return 0

    snapshots = manifest["snapshots"]
    print(f"Replay manifest OK: {args.run_id} ({len(snapshots)} snapshots)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
