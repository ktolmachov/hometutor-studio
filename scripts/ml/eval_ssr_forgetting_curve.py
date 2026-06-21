"""Evaluate the contract SSR forgetting-curve model on holdout data."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from ssr_forgetting_curve_common import (
    AUC_TARGET,
    HINT_CLASSES,
    MODEL_PATH,
    REPORT_PATH,
    TEST_PATH,
    evaluate_rows,
    load_contract_cases,
    load_model,
    model_serving_decision,
    read_rows,
)


def _matrix_markdown(matrix: list[list[int]]) -> str:
    header = "| expected \\ predicted | " + " | ".join(HINT_CLASSES) + " |"
    sep = "|---" * (len(HINT_CLASSES) + 1) + "|"
    lines = [header, sep]
    for label, row in zip(HINT_CLASSES, matrix):
        lines.append("| " + label + " | " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def _status(ok: bool) -> str:
    return "PASS" if ok else "BLOCK"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default=str(REPORT_PATH))
    args = parser.parse_args()

    if not MODEL_PATH.exists():
        raise SystemExit("Missing models/ssr_forgetting_curve_v1.pkl. Run scripts/ml/train_ssr_forgetting_curve.py first.")
    if not TEST_PATH.exists():
        raise SystemExit("Missing data/ml/ssr_forgetting_curve_test.parquet. Run scripts/ml/data_collection_ssr.py first.")

    model = load_model(MODEL_PATH)
    holdout_rows = read_rows(TEST_PATH)
    contract_rows = load_contract_cases()
    holdout = evaluate_rows(model, holdout_rows)
    contract = evaluate_rows(model, contract_rows)
    meta = dict(model.get("metadata", {}))
    real_samples = int(meta.get("real_samples", 0))
    serving_mode, serving_reason = model_serving_decision(real_samples=real_samples, auc_roc=float(holdout["macro_auc_roc"]))
    report = [
        "# SSR forgetting-curve v1 eval report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Gate summary",
        "",
        f"- Serving mode: `{serving_mode}`",
        f"- Serving reason: {serving_reason}",
        f"- Real samples: {real_samples}",
        f"- Synthetic samples: {int(meta.get('synthetic_samples', 0))}",
        f"- AUC-ROC target: >= {AUC_TARGET:.2f}",
        "",
        "## Holdout metrics",
        "",
        f"- Rows: {holdout['n']}",
        f"- Macro AUC-ROC: {holdout['macro_auc_roc']:.3f} ({_status(float(holdout['macro_auc_roc']) >= AUC_TARGET)})",
        f"- Retention AUC-ROC: {holdout['retention_auc_roc']:.3f}",
        f"- Accuracy: {holdout['accuracy']:.3f}",
        f"- Precision@5: {holdout['precision_at_5']:.3f}",
        f"- Recall@5: {holdout['recall_at_5']:.3f}",
        f"- Inference latency p95: {holdout['inference_latency_p95_ms']:.3f} ms",
        "",
        "## Contract harness metrics",
        "",
        f"- Rows: {contract['n']}",
        f"- Macro AUC-ROC: {contract['macro_auc_roc']:.3f}",
        f"- Retention AUC-ROC: {contract['retention_auc_roc']:.3f}",
        f"- Accuracy: {contract['accuracy']:.3f}",
        f"- Precision@5: {contract['precision_at_5']:.3f}",
        f"- Recall@5: {contract['recall_at_5']:.3f}",
        f"- Inference latency p95: {contract['inference_latency_p95_ms']:.3f} ms",
        "",
        "## Holdout confusion matrix",
        "",
        _matrix_markdown(holdout["confusion_matrix"]),
        "",
        "## Production readiness note",
        "",
        "The model remains rule-only for serving until the cold-start gate has at least 1000 real samples and AUC-ROC >= 0.70.",
        "Synthetic bootstrap rows are allowed for pipeline validation, not for enabling production ML by default.",
        "",
    ]
    report_path = REPORT_PATH if args.report == str(REPORT_PATH) else REPORT_PATH.__class__(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report), encoding="utf-8")
    print(f"Wrote {report_path}")
    print(f"holdout_auc={holdout['macro_auc_roc']:.3f} serving_mode={serving_mode}")


if __name__ == "__main__":
    main()
