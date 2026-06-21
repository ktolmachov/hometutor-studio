"""US-2.1: стабильный формат строк прогресса индексации (INGEST_PROGRESS)."""

from __future__ import annotations

import time

from app.ingestion import format_ingest_progress_line


def test_format_ingest_progress_line_has_stable_tokens() -> None:
    t0 = time.perf_counter() - 2.0
    line = format_ingest_progress_line(
        phase="enrichment",
        processed=3,
        total=10,
        current="folder/notes.md",
        started_monotonic=t0,
        extra="unique_docs=4",
    )
    assert line.startswith("INGEST_PROGRESS ")
    assert "phase=enrichment" in line
    assert "processed=3" in line
    assert "total=10" in line
    assert "items_per_s=" in line
    assert "eta_sec=" in line
    assert "folder/notes.md" in line
    assert "unique_docs=4" in line
