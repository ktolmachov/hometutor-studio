"""Compatibility exporter for runtime SSR ML JSON weights.

Preferred contract path:
  1. scripts/ml/data_collection_ssr.py
  2. scripts/ml/train_ssr_forgetting_curve.py --export-json-weights
  3. scripts/ml/eval_ssr_forgetting_curve.py

This wrapper keeps the old command working, but it trains on the train split
only. If data/ml is missing, it creates a deterministic 80/20 split from the
contract cases instead of fitting on all 100 evaluation cases.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ssr_forgetting_curve_common import (
    HINT_CLASSES,
    TEST_PATH,
    TRAIN_PATH,
    WEIGHTS_PATH,
    load_contract_cases,
    normalize_train_matrix,
    read_rows,
    rows_to_xy,
    split_rows,
    train_multinomial_logistic,
    write_json_weights,
    write_rows,
)


def main() -> None:
    if not TRAIN_PATH.exists() or not TEST_PATH.exists():
        train_rows, test_rows = split_rows(load_contract_cases(), seed=42, test_ratio=0.2)
        write_rows(TRAIN_PATH, train_rows)
        write_rows(TEST_PATH, test_rows)
    train_rows = read_rows(TRAIN_PATH)
    X, y = rows_to_xy(train_rows)
    Xn, mean, std = normalize_train_matrix(X)
    W, b = train_multinomial_logistic(Xn, y, n_classes=len(HINT_CLASSES), epochs=1200)
    acc = float(((Xn @ W.T + b).argmax(axis=1) == y).mean())
    model = {
        "mean": mean,
        "std": std,
        "W": W,
        "b": b,
        "metadata": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_train": str(TRAIN_PATH.relative_to(TRAIN_PATH.parents[2])).replace("\\", "/"),
            "source_test": str(TEST_PATH.relative_to(TEST_PATH.parents[2])).replace("\\", "/"),
            "train_rows": len(train_rows),
            "train_acc_approx": round(acc, 4),
        },
    }
    write_json_weights(WEIGHTS_PATH, model)
    print(f"Wrote {WEIGHTS_PATH} train_acc~={acc:.3f}")


if __name__ == "__main__":
    main()
