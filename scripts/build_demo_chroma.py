#!/usr/bin/env python3
"""Собрать прединдексированный Chroma для demo_data → demo_chroma_db/."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = ROOT / "scripts"
for candidate in (ROOT, _SCRIPTS):
    value = str(candidate)
    if value not in sys.path:
        sys.path.insert(0, value)

from dotenv import load_dotenv

from script_stdio_utf8 import configure_stdio_utf8, write_stdout_utf8_line

load_dotenv(ROOT / ".env")

DEMO_DATA = ROOT / "demo_data"
DEMO_CHROMA = ROOT / "demo_chroma_db"


def main() -> int:
    configure_stdio_utf8()
    if not os.getenv("OPENAI_API_KEY"):
        write_stdout_utf8_line("OPENAI_API_KEY is not set; cannot build embeddings.")
        return 2
    if not DEMO_DATA.is_dir():
        write_stdout_utf8_line(f"Missing demo corpus: {DEMO_DATA}")
        return 2

    from tests.integration_paths import apply_integration_layout_for_script

    tmp = Path(tempfile.mkdtemp(prefix="demo_chroma_build_"))
    restore = apply_integration_layout_for_script(tmp)
    try:
        data_dir = tmp / "data"
        chroma_dir = tmp / "chroma_db"
        shutil.copytree(DEMO_DATA, data_dir, dirs_exist_ok=True)

        from app.index_diff import update_snapshot_after_index
        from app.ingestion import build_index
        from app.retrieval_cache import clear_retrieval_cache

        clear_retrieval_cache()
        write_stdout_utf8_line("Building index from demo_data …")
        build_index(reset=True)
        update_snapshot_after_index()
        clear_retrieval_cache()

        if DEMO_CHROMA.exists():
            shutil.rmtree(DEMO_CHROMA)
        shutil.copytree(chroma_dir, DEMO_CHROMA)
        write_stdout_utf8_line(f"Wrote {DEMO_CHROMA}")
        return 0
    finally:
        restore()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
