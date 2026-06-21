"""Structural checklist for a generated smart konspekt."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import BASE_DIR, DATA_DIR


@dataclass(frozen=True)
class Metrics:
    lines: int
    chars: int
    headings: int
    mermaid: int
    tables: int
    terms: bool
    questions: bool
    cheatsheet: bool


def _resolve_target(value: str) -> Path:
    raw = Path(value)
    if raw.is_absolute():
        return raw
    if raw.suffix.lower() == ".md":
        # Konspekts live under DATA_DIR; prefer it for relative .md paths and
        # fall back to BASE_DIR (e.g. doc/-relative goldens) only if absent.
        data_candidate = (DATA_DIR / raw).resolve()
        if data_candidate.exists():
            return data_candidate
        return (BASE_DIR / raw).resolve()
    return (DATA_DIR / raw).with_suffix(".md").resolve()


def _metrics(path: Path) -> Metrics:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    return Metrics(
        lines=len(lines),
        chars=len(text),
        headings=sum(1 for line in lines if line.startswith("##")),
        mermaid=text.count("```mermaid"),
        tables=sum(1 for line in lines if line.strip().startswith("|") and line.strip().endswith("|")),
        terms="термин" in text.lower(),
        questions="контрольные вопросы" in text.lower() or "вопрос" in text.lower(),
        cheatsheet="шпаргал" in text.lower(),
    )


def _print_metrics(label: str, metrics: Metrics) -> None:
    print(f"{label:>10}  {metrics.lines:5d} lines  {metrics.chars:6d} chars  "
          f"h={metrics.headings:2d}  mermaid={metrics.mermaid}  "
          f"tables={metrics.tables:2d}  terms={metrics.terms}  "
          f"questions={metrics.questions}  cheatsheet={metrics.cheatsheet}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("konspekt", help="data-relative target or markdown path")
    parser.add_argument("--golden", help="Optional golden markdown path for comparison")
    args = parser.parse_args()

    target = _resolve_target(args.konspekt)
    if not target.exists():
        raise FileNotFoundError(target)

    target_metrics = _metrics(target)
    _print_metrics("local", target_metrics)

    if args.golden:
        golden = _resolve_target(args.golden)
        if golden.exists():
            _print_metrics("golden", _metrics(golden))
        else:
            print(f"golden    missing: {golden}")

    score = sum(
        [
            target_metrics.headings >= 6,
            target_metrics.mermaid >= 1,
            target_metrics.tables >= 2,
            target_metrics.terms,
            target_metrics.questions,
            target_metrics.cheatsheet,
        ]
    )
    verdict = "local-ok" if score >= 4 else "needs-review"
    print(f"verdict   {verdict} ({score}/6 structural checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
