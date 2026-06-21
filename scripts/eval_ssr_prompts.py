"""Offline helper for SSR Level 2 prompt evaluation artifacts.

This script validates the local scenario set and reports scaffold metrics that
can be combined with human ratings after generated explanations are collected.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CASES = ROOT / "tests" / "eval" / "ssr_explanation_test_cases.json"
DEFAULT_OUT = ROOT / "eval_data" / "ml_eval" / "ssr_level2" / "generated_explanations_v1.json"
DEFAULT_HUMAN_SHEET = ROOT / "eval_data" / "ml_eval" / "ssr_level2" / "human_eval_sheet.csv"
LLM_ROLES = frozenset({"main", "classifier", "rewrite", "ssr"})
RATERS = ("rater1", "rater2", "rater3")
RATING_DIMS = ("clarity", "personalization", "pedagogical_value", "accuracy")


def _word_count(text: str) -> int:
    return len((text or "").split())


def summarize_cases(path: Path) -> dict[str, object]:
    cases = load_cases(path)
    by_kind: dict[str, int] = {}
    template_words: list[int] = []
    for case in cases:
        kind = str(case["hint_kind"])
        by_kind[kind] = by_kind.get(kind, 0) + 1
        template_words.append(_word_count(str(case["why_now_template"])))
    return {
        "case_count": len(cases),
        "by_hint_kind": by_kind,
        "template_words_max": max(template_words) if template_words else 0,
        "template_words_avg": round(sum(template_words) / len(template_words), 2) if template_words else 0,
    }


def load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("SSR explanation cases must be a JSON array")
    return data


def _case_to_recommendation(case: dict[str, Any]):
    from app.ui.adaptive_plan_card import SmartStudyRecommendation

    return SmartStudyRecommendation(
        hint_kind=case["hint_kind"],
        primary_label_ru=case["primary_label_ru"],
        why_now_ru=case["why_now_template"],
        primary_nav=case["primary_nav"],
        secondaries=(),
        route_pedagogy_ru=str(case.get("route_pedagogy_ru") or ""),
    )


def _prompt_kwargs(case: dict[str, Any], rec: Any) -> dict[str, str]:
    ctx = dict(case.get("context") or {})
    return {
        "last_session_topic": str(ctx.get("last_session_topic") or "нет данных"),
        "last_session_date": str(ctx.get("last_session_date") or "нет данных"),
        "quiz_score_last_3": str(ctx.get("quiz_score_last_3") or "нет данных"),
        "cards_due_count": str(ctx.get("cards_due_count") or ctx.get("flashcard_due_n") or 0),
        "sm2_due_count": str(ctx.get("sm2_due_count") or 0),
        "weak_concepts_list": str(ctx.get("weak_concepts_list") or "нет данных"),
        "local_evidence": str(ctx.get("local_evidence") or "нет дополнительных локальных сигналов"),
        "primary_label_ru": rec.primary_label_ru,
        "primary_nav": rec.primary_nav,
        "hint_kind": rec.hint_kind,
        "why_now_template": rec.why_now_ru,
    }


def _generate_raw_llm_explanation(case: dict[str, Any], rec: Any, *, llm: Any) -> tuple[str, float, str | None]:
    from app.llm_resilience import complete_with_resilience
    from app.prompts import SSR_LLM_EXPLANATION_PROMPT

    prompt = SSR_LLM_EXPLANATION_PROMPT.format(**_prompt_kwargs(case, rec))
    started = time.monotonic()
    try:
        result = complete_with_resilience(
            llm,
            prompt,
            stage="ssr_llm_explanation_eval",
            max_tokens=220,
            temperature=0.2,
        )
    except Exception as exc:  # noqa: BLE001 - eval artifact records fallback rows for review.
        return rec.why_now_ru, time.monotonic() - started, type(exc).__name__
    text = " ".join(str(getattr(result, "text", result)).strip().split())
    if not text:
        return rec.why_now_ru, time.monotonic() - started, "empty_output"
    return text, time.monotonic() - started, None


def generate_explanations(
    cases: list[dict[str, Any]],
    *,
    llm: Any | None = None,
    llm_role: str = "ssr",
    offline_template: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    from app.prompts import SSR_LLM_EXPLANATION_PROMPT_VERSION

    if llm is None and not offline_template:
        from app import provider

        role = llm_role if llm_role in LLM_ROLES else "ssr"
        if role == "main":
            llm = provider.get_llm()
        elif role == "ssr":
            llm = provider.get_ssr_llm()
        elif role == "rewrite":
            llm = provider.get_rewrite_llm()
        else:
            llm = provider.get_classifier_llm()

    selected = cases[: max(0, limit)] if limit is not None else cases
    generated_at = datetime.now(UTC).isoformat()
    rows: list[dict[str, Any]] = []
    for case in selected:
        rec = _case_to_recommendation(case)
        context = dict(case.get("context") or {})
        if offline_template:
            explanation = rec.why_now_ru
            latency_sec = 0.0
            error_type = None
        else:
            explanation, latency_sec, error_type = _generate_raw_llm_explanation(case, rec, llm=llm)
        rows.append(
            {
                "case_id": case["id"],
                "hint_kind": rec.hint_kind,
                "primary_label_ru": rec.primary_label_ru,
                "primary_nav": rec.primary_nav,
                "template_explanation": rec.why_now_ru,
                "generated_explanation": explanation,
                "generated_word_count": _word_count(explanation),
                "used_template_fallback": explanation == rec.why_now_ru,
                "latency_sec": round(latency_sec, 3),
                "error_type": error_type,
                "must_preserve": case.get("must_preserve", []),
                "forbidden_claims": case.get("forbidden_claims", []),
            }
        )
    return {
        "generated_at": generated_at,
        "prompt_version": SSR_LLM_EXPLANATION_PROMPT_VERSION,
        "case_count": len(rows),
        "offline_template": offline_template,
        "llm_role": llm_role,
        "records": rows,
    }


def make_human_eval_sheet(generated_path: Path, out_path: Path) -> dict[str, object]:
    artifact = json.loads(generated_path.read_text(encoding="utf-8"))
    rows = artifact.get("records") or []
    fieldnames = [
        "case_id",
        "hint_kind",
        "primary_label_ru",
        "primary_nav",
        "template_explanation",
        "generated_explanation",
        "generated_word_count",
        "latency_sec",
        "must_preserve",
        "forbidden_claims",
    ]
    for rater in RATERS:
        for dim in RATING_DIMS:
            fieldnames.append(f"{rater}_{dim}")
        fieldnames.append(f"{rater}_notes")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "case_id": row.get("case_id", ""),
                    "hint_kind": row.get("hint_kind", ""),
                    "primary_label_ru": row.get("primary_label_ru", ""),
                    "primary_nav": row.get("primary_nav", ""),
                    "template_explanation": row.get("template_explanation", ""),
                    "generated_explanation": row.get("generated_explanation", ""),
                    "generated_word_count": row.get("generated_word_count", ""),
                    "latency_sec": row.get("latency_sec", ""),
                    "must_preserve": "; ".join(str(x) for x in row.get("must_preserve", [])),
                    "forbidden_claims": "; ".join(str(x) for x in row.get("forbidden_claims", [])),
                }
            )
    return {"out": str(out_path), "rows": len(rows), "raters": len(RATERS)}


def _rating_value(raw: str) -> float | None:
    text = (raw or "").strip()
    if not text:
        return None
    value = float(text)
    if value < 1 or value > 5:
        raise ValueError(f"rating out of range 1..5: {raw!r}")
    return value


def summarize_human_eval_sheet(path: Path) -> dict[str, object]:
    rows = list(csv.DictReader(path.open("r", encoding="utf-8-sig", newline="")))
    scores: dict[str, list[float]] = {dim: [] for dim in RATING_DIMS}
    missing = 0
    for row in rows:
        for rater in RATERS:
            for dim in RATING_DIMS:
                value = _rating_value(row.get(f"{rater}_{dim}", ""))
                if value is None:
                    missing += 1
                else:
                    scores[dim].append(value)
    means = {
        dim: round(sum(vals) / len(vals), 3) if vals else None
        for dim, vals in scores.items()
    }
    complete = missing == 0 and bool(rows)
    return {
        "rows": len(rows),
        "missing_ratings": missing,
        "means": means,
        "passes_clarity": complete and (means["clarity"] or 0) >= 4.0,
        "passes_accuracy_floor": complete and bool(scores["accuracy"]) and min(scores["accuracy"]) >= 3.0,
        "ready_for_metric_decision": complete,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable summary")
    parser.add_argument("--generate", action="store_true", help="Generate explanation artifact")
    parser.add_argument("--offline-template", action="store_true", help="Write template fallback output without LLM calls")
    parser.add_argument("--limit", type=int, default=None, help="Generate only first N cases")
    parser.add_argument(
        "--llm-role",
        choices=sorted(LLM_ROLES),
        default="ssr",
        help="Provider LLM role for live generation",
    )
    parser.add_argument("--make-human-sheet", action="store_true", help="Create CSV for 3-rater human evaluation")
    parser.add_argument("--human-sheet", type=Path, default=DEFAULT_HUMAN_SHEET)
    parser.add_argument("--summarize-human-sheet", action="store_true", help="Summarize completed human evaluation CSV")
    args = parser.parse_args()

    if args.make_human_sheet:
        summary = make_human_eval_sheet(args.out, args.human_sheet)
        print(json.dumps(summary, ensure_ascii=False, indent=2) if args.json else f"Wrote {summary['out']}")
        return 0

    if args.summarize_human_sheet:
        summary = summarize_human_eval_sheet(args.human_sheet)
        print(json.dumps(summary, ensure_ascii=False, indent=2) if args.json else summary)
        return 0

    if args.generate:
        artifact = generate_explanations(
            load_cases(args.cases),
            llm_role=args.llm_role,
            offline_template=args.offline_template,
            limit=args.limit,
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.json:
            print(json.dumps({"out": str(args.out), **summarize_cases(args.cases)}, ensure_ascii=False, indent=2))
        else:
            print(f"Wrote SSR explanations: {args.out}")
            print(f"Records: {artifact['case_count']}")
        return 0

    summary = summarize_cases(args.cases)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"SSR explanation cases: {summary['case_count']}")
        print(f"By hint kind: {summary['by_hint_kind']}")
        print(f"Template words avg/max: {summary['template_words_avg']}/{summary['template_words_max']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
