#!/usr/bin/env python3
"""Offline Local Route Simulator entrypoint for maintainer fixture runs.

Usage:
    .venv\Scripts\python.exe scripts/run_ssr_route_simulator.py \\
        --fixtures tests/eval/ssr_route_simulator_fixtures.json

Outputs one JSON line per fixture scenario with:
    - label, chosen_route, reason_trace, local_signals,
      counterfactual (str|null), limitation (str|null)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.smart_study_recommendation import SmartStudyRecommendation
from app.smart_study_route_simulator import SimulatedRoute, simulate_what_if


def _load_json(path: Path) -> list[dict]:
    if not path.exists():
        print(f"ERROR: Fixture file not found: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(data, list):
        print(f"ERROR: Fixture file must contain a JSON array, got {type(data).__name__}", file=sys.stderr)
        sys.exit(1)
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            print(f"ERROR: Fixture [{i}] must be a JSON object", file=sys.stderr)
            sys.exit(1)
        if "label" not in item:
            print(f"ERROR: Fixture [{i}] missing 'label' field", file=sys.stderr)
            sys.exit(1)
        if "rec_params" not in item or not isinstance(item["rec_params"], dict):
            print(f"ERROR: Fixture [{i}] missing or invalid 'rec_params' (must be object)", file=sys.stderr)
            sys.exit(1)
        if "secondary_action_id" not in item:
            print(f"ERROR: Fixture [{i}] missing 'secondary_action_id' field", file=sys.stderr)
            sys.exit(1)
    return data


def _build_rec(**kwargs: object) -> SmartStudyRecommendation:
    """Build a SmartStudyRecommendation from fixture rec_params.

    Uses the same pattern as test fixtures to avoid importing
    build_smart_study_recommendation (which has UI-layer deps).
    """
    # Build a minimal SmartStudyRecommendation via the public API.
    # Import locally to avoid circular deps at module level.
    # pylint: disable=import-outside-toplevel
    from app.smart_study_router import build_smart_study_recommendation

    # Type-narrow kwargs for known params.
    kw: dict[str, object] = dict(kwargs)
    surface = str(kw.pop("surface", "home"))
    flashcard_due_n = int(kw.pop("flashcard_due_n", 0))
    sm2_due_n = int(kw.pop("sm2_due_n", 0))
    quiz_feedback_status = kw.pop("quiz_feedback_status", None)
    has_tutor_resume = bool(kw.pop("has_tutor_resume", False))
    tutor_topic = kw.pop("tutor_topic", None)
    has_last_answer_qa = bool(kw.pop("has_last_answer_qa", False))
    has_reading_resume = bool(kw.pop("has_reading_resume", False))
    first_weak_concept = kw.pop("first_weak_concept", None)
    plan_primary_block = kw.pop("plan_primary_block", None)
    retrieval_confidence = kw.pop("retrieval_confidence", None)
    source_evidence_count = kw.pop("source_evidence_count", None)

    return build_smart_study_recommendation(
        surface=surface,  # type: ignore[arg-type]
        flashcard_due_n=flashcard_due_n,
        sm2_due_n=sm2_due_n,
        quiz_feedback_status=quiz_feedback_status,
        has_tutor_resume=has_tutor_resume,
        tutor_topic=tutor_topic,
        has_last_answer_qa=has_last_answer_qa,
        has_reading_resume=has_reading_resume,
        first_weak_concept=first_weak_concept,
        plan_primary_block=plan_primary_block,
        retrieval_confidence=retrieval_confidence,
        source_evidence_count=source_evidence_count,
    )


def _format_output(
    fixture: dict,
    rec: SmartStudyRecommendation,
    result: SimulatedRoute,
) -> dict[str, object]:
    return {
        "label": fixture["label"],
        "chosen_route": str(rec.primary_nav),
        "reason_trace": _format_reason_trace(rec),
        "local_signals": result.signals_summary,
        "counterfactual": result.counterfactual_primary_label_ru or None,
        "limitation": result.limitation_reason or None,
    }


def _format_reason_trace(rec: SmartStudyRecommendation) -> str:
    parts = [f"hint={rec.hint_kind}", f"nav={rec.primary_nav}"]
    if rec.route_pedagogy_ru:
        parts.append(f"pedagogy={rec.route_pedagogy_ru[:80]}")
    return " | ".join(parts)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="SSR Local Route Simulator — offline fixture runner"
    )
    parser.add_argument(
        "--fixtures",
        required=True,
        type=str,
        help="Path to JSON fixture file (array of {label, rec_params, secondary_action_id})",
    )
    args = parser.parse_args()

    fixtures_path = Path(args.fixtures)
    fixtures = _load_json(fixtures_path)

    results: list[dict[str, object]] = []
    for fixture in fixtures:
        rec = _build_rec(**fixture["rec_params"])
        result = simulate_what_if(rec, fixture["secondary_action_id"])
        output = _format_output(fixture, rec, result)
        results.append(output)
        print(json.dumps(output, ensure_ascii=False))

    if not results:
        print(json.dumps({"note": "Empty fixture array — no scenarios to simulate."}, ensure_ascii=False))

    sys.exit(0)


if __name__ == "__main__":
    main()
