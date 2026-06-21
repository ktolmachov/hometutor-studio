#!/usr/bin/env python3
"""
Router eval baseline (US-12.4 / E10.3): точность выбора pedagogical orchestrator vs gold labels.

Пример:
  python scripts/run_router_eval.py
  python scripts/run_router_eval.py --limit 3
  python scripts/run_router_eval.py --report-json /tmp/router_eval.json
  python scripts/run_router_eval.py --baseline eval_data/router_eval_baseline.json

Прогресс идёт в stderr (по одной строке на кейс); полный JSON — в stdout в конце.
``--quiet`` отключает прогресс; ``--limit N`` — только первые N кейсов (**smoke-only**:
регрессия к full baseline **отключена**, отчёт помечен как несопоставимый с полным прогоном).

Требует OPENAI_API_KEY (реальный вызов LLM оркестратора).

Регрессия (только ``overall_accuracy``, не per-category): ``delta = new - old``;
срабатывает при ``delta < -threshold_pp/100`` (строгое сравнение: ровно −5.00 п.п. ещё OK,
−5.01 п.п. уже fail при default threshold 5).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = ROOT / "scripts"
for _p in (ROOT, _SCRIPTS):
    s = str(_p)
    if s not in sys.path:
        sys.path.insert(0, s)

DEFAULT_DATASET = ROOT / "eval_data" / "tutor_regression.json"
DEFAULT_BASELINE = ROOT / "eval_data" / "router_eval_baseline.json"

from script_stdio_utf8 import configure_stdio_utf8, write_stdout_utf8_line


def _validate_gold_rationale_contract(cases: list[dict]) -> None:
    """Gold labels must ship with contract text (US-12.5 / E11-Q): no silent relabeling."""
    missing: list[str] = []
    for c in cases:
        case_id = str(c.get("id") or "")
        rev = c.get("router_eval") if isinstance(c.get("router_eval"), dict) else {}
        gold = str((rev or {}).get("gold_selected_agent") or "").strip()
        if not gold:
            continue
        rat = str((rev or {}).get("gold_rationale") or "").strip()
        if not rat:
            missing.append(case_id or "?")
    if missing:
        raise SystemExit(
            "Gold contract: каждый кейс с gold_selected_agent должен иметь непустой gold_rationale "
            f"(US-12.5). Отсутствует для id: {', '.join(missing)}"
        )


def _load_dataset(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = raw.get("test_cases") or []
    if len(cases) < 26:
        raise SystemExit(f"Expected at least 26 test_cases for router eval, got {len(cases)}")
    _validate_gold_rationale_contract(cases)
    return raw


def _load_baseline(path: Path | None) -> dict | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _regression_overall(
    new_acc: float | None,
    baseline: dict | None,
    threshold_pp: float,
) -> tuple[bool, str | None]:
    if new_acc is None:
        return False, None
    if not baseline:
        return False, None
    raw_old = baseline.get("overall_accuracy")
    if raw_old is None:
        return False, None
    try:
        old = float(raw_old)
        new = float(new_acc)
    except (TypeError, ValueError):
        return False, None
    # Сравнение в п.п.; округляем, чтобы 0.60 vs 0.65 не давали −5.000…004 из-за float.
    delta_pp = round((new - old) * 100.0, 6)
    if delta_pp < -float(threshold_pp):
        return True, f"overall_accuracy {new:.4f} vs baseline {old:.4f} (delta {delta_pp:.2f} pp)"
    return False, None


# US-12.5: продуктово критичные категории (quiz / Socratic / SRS / feedback / anti-overhelp).
US125_CRITICAL_CATEGORIES: tuple[str, ...] = (
    "quiz_quality",
    "socratic_quality",
    "spaced_repetition",
    "quiz_feedback_loop",
    "anti_overhelp_homework",
)


def _check_per_category_guardrails(
    new_per_cat: dict | None,
    baseline: dict | None,
) -> tuple[list[str], list[str]]:
    """Return (violations, low_n_skipped_notes).

    Rules (E11-Q):
    - Baseline category was >= 0.8 accuracy and new run < 0.5 → violation.
    - For **US-12.5** critical categories (quiz/socratic/SRS/feedback/anti-overhelp): always
      evaluate (even n=1 — contract intent).
    - For **other** categories: only if baseline ``total >= 2`` — single-case baselines are
      high-variance (1/1 → 0/1 is not comparable to multi-case stability).
    """
    if not new_per_cat or not baseline:
        return [], []
    old_per_cat = baseline.get("per_category") or {}
    violations: list[str] = []
    low_n_skipped: list[str] = []
    us125 = frozenset(US125_CRITICAL_CATEGORIES)
    for cat, old_v in old_per_cat.items():
        try:
            old_acc = float(old_v.get("accuracy", 0))
        except (TypeError, ValueError):
            continue
        if old_acc < 0.8:
            continue  # category was already weak at baseline — not a guardrail
        new_v = new_per_cat.get(cat)
        if new_v is None:
            continue
        try:
            new_acc = float(new_v.get("accuracy", 0))
        except (TypeError, ValueError):
            continue
        try:
            old_total = int(old_v.get("total", 0) or 0)
        except (TypeError, ValueError):
            old_total = 0
        if cat not in us125 and old_total < 2:
            if new_acc < 0.5:
                low_n_skipped.append(
                    f"{cat}: baseline had n={old_total} (<2), drop {old_acc:.2f}→{new_acc:.2f} "
                    "— not a formal guardrail (high variance); see case row + US-12.5 block for product intents"
                )
            continue
        if new_acc < 0.5:
            old_frac = f"{int(old_v.get('correct',0))}/{int(old_v.get('total',1))}"
            new_frac = f"{int(new_v.get('correct',0))}/{int(new_v.get('total',1))}"
            violations.append(
                f"per_category guardrail: {cat} dropped from {old_acc:.2f} ({old_frac}) "
                f"to {new_acc:.2f} ({new_frac}) — was green (>=0.8) at baseline"
            )
    return violations, low_n_skipped


def _critical_category_diagnostics(
    new_per_cat: dict | None,
    baseline_per_cat: dict | None,
) -> dict[str, Any]:
    """Per-category строки для US-12.5 + сравнение с baseline (если есть)."""
    out: dict[str, Any] = {}
    for cat in US125_CRITICAL_CATEGORIES:
        nv = (new_per_cat or {}).get(cat) if new_per_cat else None
        bv = (baseline_per_cat or {}).get(cat) if baseline_per_cat else None
        entry: dict[str, Any] = {
            "accuracy": None,
            "correct": None,
            "total": None,
            "baseline_accuracy": None,
            "delta_pp_vs_baseline": None,
            "guardrail_status": "unknown",
            "guardrail_detail": None,
        }
        if nv:
            entry["accuracy"] = nv.get("accuracy")
            entry["correct"] = nv.get("correct")
            entry["total"] = nv.get("total")
        if bv:
            try:
                entry["baseline_accuracy"] = float(bv.get("accuracy", 0))
            except (TypeError, ValueError):
                entry["baseline_accuracy"] = None
        if entry["accuracy"] is not None and entry["baseline_accuracy"] is not None:
            entry["delta_pp_vs_baseline"] = round(
                (float(entry["accuracy"]) - float(entry["baseline_accuracy"])) * 100.0,
                2,
            )
        # Статус: warn если упали относительно baseline >=0.8 до <0.5 (как общий guardrail).
        try:
            na = float(entry["accuracy"]) if entry["accuracy"] is not None else None
            ba = float(entry["baseline_accuracy"]) if entry["baseline_accuracy"] is not None else None
        except (TypeError, ValueError):
            na = ba = None
        if na is None:
            entry["guardrail_status"] = "no_data"
        elif ba is not None and ba >= 0.8 and na < 0.5:
            entry["guardrail_status"] = "violation"
            entry["guardrail_detail"] = "was >=0.8 at baseline, now <0.5"
        elif na < 1.0:
            entry["guardrail_status"] = "watch"
        else:
            entry["guardrail_status"] = "ok"
        out[cat] = entry
    return {
        "contract": "US-12.5",
        "categories": out,
    }


def _usage_totals(rows: list[dict]) -> dict[str, Any]:
    pt = ct = tt = 0
    n = 0
    for r in rows:
        u = r.get("usage")
        if not isinstance(u, dict):
            continue
        pt += int(u.get("prompt_tokens") or 0)
        ct += int(u.get("completion_tokens") or 0)
        tt += int(u.get("total_tokens") or 0)
        n += 1
    return {
        "llm_calls_with_usage": n,
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "total_tokens": tt,
    }


def _latency_stats(rows: list[dict]) -> dict[str, Any] | None:
    ms_list = [int(r["latency_ms"]) for r in rows if r.get("latency_ms") is not None]
    if not ms_list:
        return None
    s = sum(ms_list)
    return {
        "cases_with_latency": len(ms_list),
        "total_ms": s,
        "avg_ms": round(s / len(ms_list), 1),
        "max_ms": max(ms_list),
    }


def _baseline_comparison_state(
    *,
    baseline_loaded: bool,
    limited_vs_full: bool,
    baseline_for_regression: dict | None,
) -> str:
    if limited_vs_full:
        return "skipped_smoke_only_not_comparable_to_full_baseline"
    if not baseline_loaded:
        return "baseline_file_missing"
    if baseline_for_regression is None:
        return "inactive"
    if (baseline_for_regression.get("overall_accuracy")) is None:
        return "baseline_missing_overall_accuracy"
    return "active_vs_baseline"


def main() -> int:
    ap = argparse.ArgumentParser(description="Pedagogical router accuracy vs tutor_regression gold labels.")
    ap.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    ap.add_argument("--report-json", type=Path, default=None)
    ap.add_argument("--baseline", type=Path, default=None, help="JSON с полем overall_accuracy")
    ap.add_argument(
        "--regression-threshold-pp",
        type=float,
        default=5.0,
        help="Макс. допустимое падение overall_accuracy в процентных пунктах (default: 5)",
    )
    ap.add_argument(
        "--write-baseline",
        type=Path,
        default=None,
        help="Записать текущий aggregate как baseline JSON (для локальной калибровки)",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Обработать только первые N кейсов (smoke / отладка)",
    )
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="Не печатать прогресс в stderr (только JSON в stdout в конце)",
    )
    args = ap.parse_args()

    configure_stdio_utf8()

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set; router eval aborted.", file=sys.stderr)
        return 2

    baseline_path = args.baseline if args.baseline is not None else DEFAULT_BASELINE
    baseline = _load_baseline(baseline_path)

    raw = _load_dataset(args.dataset)
    all_cases = raw.get("test_cases") or []
    full_n = len(all_cases)
    if args.limit is not None:
        n = max(0, int(args.limit))
        cases = all_cases[:n]
    else:
        cases = all_cases

    limited_vs_full = args.limit is not None and len(cases) < full_n
    baseline_for_regression = None if limited_vs_full else baseline
    if limited_vs_full and baseline is not None and not args.quiet:
        print(
            "router_eval: частичный прогон (--limit) — сравнение с full baseline отключено "
            "(иначе смешиваются несопоставимые accuracy).",
            file=sys.stderr,
            flush=True,
        )

    from app.router_eval import aggregate_router_accuracy, run_single_router_case

    total = len(cases)
    if not args.quiet:
        print(
            f"router_eval: {total} вызов(ов) оркестратора к LLM (порядка минут), прогресс ниже…",
            file=sys.stderr,
            flush=True,
        )

    rows: list[dict] = []
    for i, c in enumerate(cases, start=1):
        row = run_single_router_case(c)
        rows.append(row)
        if not args.quiet:
            cid = row.get("id", "?")
            st = row.get("status", "?")
            extra = ""
            if st == "completed":
                extra = f" match={row.get('match')} pred={row.get('predicted_agent')}"
            elif st == "skipped":
                extra = f" ({row.get('reason')})"
            lm = row.get("latency_ms")
            time_part = f" {int(lm)}ms" if lm is not None else ""
            print(
                f"  [{i}/{total}] {cid} {st}{time_part}{extra}",
                file=sys.stderr,
                flush=True,
            )

    agg = aggregate_router_accuracy(rows)

    from app.config import get_settings
    from app.tutor_prompts import ORCHESTRATOR_PROMPT_FINGERPRINT, ORCHESTRATOR_PROMPT_LEVEL

    settings = get_settings()
    baseline_ds = str((baseline or {}).get("dataset_version") or "")
    current_ds = str(raw.get("version") or "unknown")
    dataset_baseline_mismatch = bool(baseline_ds and baseline_ds != current_ds)

    report: dict[str, Any] = {
        "schema_version": 2,
        "eval_mode": "smoke_limited" if limited_vs_full else "full",
        "smoke_only": bool(limited_vs_full),
        "smoke_only_note": (
            "Прогон с --limit: только sanity-check оркестратора; не сравнивать accuracy/guardrails "
            "с полным baseline и не использовать как решение о качестве (US-12.5)."
            if limited_vs_full
            else None
        ),
        "comparable_to_full_baseline": not limited_vs_full,
        "dataset_version": current_ds,
        "dataset_file": str(args.dataset.resolve()),
        "cases_in_this_run": len(cases),
        "cases_total_in_dataset": full_n,
        "aggregate": agg,
        "cases": rows,
        "usage_totals": _usage_totals(rows),
        "latency_summary": _latency_stats(rows),
        "prompt_request_metadata": {
            "orchestrator_prompt_level": ORCHESTRATOR_PROMPT_LEVEL,
            "orchestrator_prompt_fingerprint_sha256_16": ORCHESTRATOR_PROMPT_FINGERPRINT,
            "orchestrator_prompt_blocks": "ORCHESTRATOR_SYSTEM_PROMPT + ORCHESTRATOR_DECISION_PROMPT",
            "llm_model_configured": str(settings.llm_model or ""),
            "note": "Fingerprint меняется при правке system/user шаблонов оркестратора в tutor_prompts.py",
        },
        "dataset_baseline_version_mismatch": dataset_baseline_mismatch,
        "dataset_baseline_mismatch_detail": (
            f"dataset {current_ds} vs baseline file dataset_version {baseline_ds}"
            if dataset_baseline_mismatch
            else None
        ),
        "gold_rationale_contract": {
            "enforced": True,
            "policy": "Каждый кейс с gold_selected_agent содержит непустой gold_rationale (изменение gold только с явной contract note).",
        },
    }

    oa = agg.get("overall_accuracy")
    reg, reg_msg = _regression_overall(
        float(oa) if oa is not None else None,
        baseline_for_regression,
        args.regression_threshold_pp,
    )
    # Per-category guardrails (E11-Q): flag any previously-green category that crashed.
    new_per_cat = agg.get("per_category")
    cat_violations, guardrail_low_n_notes = _check_per_category_guardrails(
        new_per_cat,
        baseline_for_regression,
    )
    report["per_category_guardrail_low_n_notes"] = guardrail_low_n_notes
    old_per_cat = (baseline_for_regression or {}).get("per_category") if baseline_for_regression else None
    report["us125_critical_category_diagnostics"] = _critical_category_diagnostics(new_per_cat, old_per_cat)

    report["baseline_path"] = str(baseline_path) if baseline_path else None
    report["baseline_loaded"] = baseline is not None
    _old_acc = (baseline_for_regression or {}).get("overall_accuracy")
    report["regression_compared"] = baseline_for_regression is not None and _old_acc is not None
    report["baseline_comparison_state"] = _baseline_comparison_state(
        baseline_loaded=baseline is not None,
        limited_vs_full=limited_vs_full,
        baseline_for_regression=baseline_for_regression,
    )
    report["regression_note"] = (
        "overall_accuracy gated at threshold_pp; per-category guardrail flags previously-green (>=0.8) categories; "
        "US-12.5 critical categories — в us125_critical_category_diagnostics. "
        "Intent repair (E11-R) — только если после E11-Q всё ещё нужен фикс роутера; см. doc/roadmap_governance.md."
    )
    if limited_vs_full:
        report["regression_skipped_reason"] = "limited_run_not_comparable_to_full_baseline"
    report["regression_vs_baseline"] = bool(reg)
    if reg_msg:
        report["regression_detail"] = reg_msg
    report["per_category_guardrail_violations"] = cat_violations
    report["per_category_guardrail_passed"] = len(cat_violations) == 0
    report["per_category_guardrail_note"] = (
        "Жёсткий per-category gate: US-12.5 всегда; прочие категории только при baseline n≥2 "
        "(один кейс в baseline даёт шум 1.0↔0.0 — см. per_category_guardrail_low_n_notes)."
    )

    # Строки кейсов: gold_rationale из датасета (дублируем в JSON отчёта для diff-ревью).
    gold_by_id = {
        str(c.get("id") or ""): str((c.get("router_eval") or {}).get("gold_rationale") or "").strip()
        for c in cases
    }
    for row in rows:
        gid = str(row.get("id") or "")
        gr = gold_by_id.get(gid, "").strip()
        if gr:
            row["gold_rationale"] = gr

    # Per-category failure summary for quick diagnosis.
    if new_per_cat:
        failing_cats = {
            cat: v for cat, v in new_per_cat.items() if float(v.get("accuracy", 1)) < 1.0
        }
        report["failing_categories"] = failing_cats
        if not args.quiet:
            print(
                f"router_eval: {len(failing_cats)} failing categories: "
                + ", ".join(f"{c}({v['correct']}/{v['total']})" for c, v in failing_cats.items()),
                file=sys.stderr,
                flush=True,
            )

    out = json.dumps(report, ensure_ascii=False, indent=2)
    write_stdout_utf8_line(out)

    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(out, encoding="utf-8")

    if args.write_baseline:
        snap = {
            "schema_version": 1,
            "dataset_version": report["dataset_version"],
            "overall_accuracy": oa,
            "per_category": agg.get("per_category"),
            "recorded_note": "Создано через scripts/run_router_eval.py --write-baseline",
        }
        args.write_baseline.parent.mkdir(parents=True, exist_ok=True)
        args.write_baseline.write_text(
            json.dumps(snap, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    if reg:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
