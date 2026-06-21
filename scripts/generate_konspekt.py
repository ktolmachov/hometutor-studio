"""Generate a local smart konspekt from materials/<course>/<lecture>/."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lecture", help="Lecture materials folder, e.g. 'ИИ Агенты/урок 1'")
    parser.add_argument("--model", help="Override OBSIDIAN_EXPORT_MODEL for this run")
    parser.add_argument("--force", action="store_true", help="Regenerate even if target hash matches")
    args = parser.parse_args()

    if args.model:
        os.environ["OBSIDIAN_EXPORT_MODEL"] = args.model

    from app.smart_konspekt import generate_smart_konspekt

    t0 = time.perf_counter()

    def progress(stage: str, current: int, total: int) -> None:
        suffix = f"{current}/{total}" if total > 0 else str(current)
        print(f"{stage:>12} {suffix:<8} t={time.perf_counter() - t0:6.1f}s", flush=True)

    result = generate_smart_konspekt(args.lecture, force=args.force, progress=progress)
    stats = result.stats
    print()
    print("phase      value")
    print("---------  ----------------")
    print(f"action     {result.action}")
    print(f"target     {result.target_abs}")
    print(f"duration   {stats.duration_sec:.1f}s")
    print(f"llm_calls  {stats.llm_calls}")
    print(f"input      {stats.input_chars} chars")
    print(f"output     {stats.output_chars} chars")
    print(f"cache      {'yes' if stats.cache_used else 'no'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
