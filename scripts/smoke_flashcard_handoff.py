"""Flashcard -> Tutor handoff smoke for the "Не знаю / Объясни" product path.

This is intentionally deterministic: the first visible answer is seeded from the
clicked card itself, so the smoke verifies the learner-facing contract without a
live LLM call.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _build_smoke_card() -> dict[str, Any]:
    return {
        "id": 101,
        "front": "Зачем нужны idempotency keys в AI-агентах?",
        "back": (
            "Idempotency keys нужны, чтобы повторный вызов инструмента не менял "
            "состояние системы второй раз и не создавал нестабильный результат."
        ),
        "deck_name": "ИИ Агенты",
        "tags": "course:ai-agents, source:ИИ Агенты/Урок_3_Автономность_память_стейт_и_контроль_поведения.md",
    }


def run_smoke() -> dict[str, Any]:
    from app.flashcard_handoff import build_flashcard_handoff_seed

    deepen_with_sources_cta = "Углубить по источникам"
    seed = build_flashcard_handoff_seed(_build_smoke_card())
    assistant = str(seed.get("assistant_content") or "")
    meta = seed.get("assistant_metadata") if isinstance(seed.get("assistant_metadata"), dict) else {}
    tutor_answer = meta.get("tutor_answer") if isinstance(meta.get("tutor_answer"), dict) else {}
    sources = meta.get("sources") if isinstance(meta.get("sources"), list) else []
    first_source = sources[0] if sources and isinstance(sources[0], dict) else {}
    ctas = tutor_answer.get("suggested_ctas") if isinstance(tutor_answer.get("suggested_ctas"), list) else []

    checks = {
        "plain_text": bool(assistant.strip()) and not assistant.lstrip().startswith("{"),
        "detailed_enough": len(assistant.strip()) >= 360,
        "source_line_visible": "Источник карточки" in assistant,
        "source_metadata_present": bool(first_source.get("relative_path")),
        "source_text_contains_card": "Idempotency keys" in str(first_source.get("text") or ""),
        "deepen_cta_present": deepen_with_sources_cta in ctas,
        "smart_study_overlay_suppressed": bool((meta.get("tutor") or {}).get("suppress_smart_study_overlay")),
    }
    return {
        "schema_version": 1,
        "surface": "flashcard_handoff",
        "card_id": _build_smoke_card()["id"],
        "pass": all(checks.values()),
        "checks": checks,
        "answer_chars": len(assistant.strip()),
        "source_relative_path": first_source.get("relative_path"),
        "answer_preview": assistant[:420],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test flashcard -> tutor handoff seed.")
    parser.add_argument("--report-json", type=Path, default=None)
    args = parser.parse_args()

    report = run_smoke()
    out = json.dumps(report, ensure_ascii=False, indent=2)
    print(out)
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(out, encoding="utf-8")
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
