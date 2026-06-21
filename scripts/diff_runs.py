#!/usr/bin/env python3
"""Tiny structural diff for two autonomous run manifests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_recorder import build_replay_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left_run_id")
    parser.add_argument("right_run_id")
    args = parser.parse_args(argv)

    left = build_replay_manifest(args.left_run_id)
    right = build_replay_manifest(args.right_run_id)
    diff = {
        "left_run_id": left["run_id"],
        "right_run_id": right["run_id"],
        "left_snapshots": len(left["snapshots"]),
        "right_snapshots": len(right["snapshots"]),
    }
    print(json.dumps(diff, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
