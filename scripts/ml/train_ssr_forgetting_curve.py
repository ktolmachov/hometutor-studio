"""Train the contract SSR forgetting-curve model with an 80/20 split."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from ssr_forgetting_curve_common import (
    HINT_CLASSES,
    MODEL_PATH,
    TEST_PATH,
    TRAIN_PATH,
    WEIGHTS_PATH,
    dump_model,
    normalize_train_matrix,
    read_rows,
    rows_to_xy,
    train_multinomial_logistic,
    write_json_weights,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=1200)
    parser.add_argument("--export-json-weights", action="store_true")
    args = parser.parse_args()

    if not TRAIN_PATH.exists() or not TEST_PATH.exists():
        raise SystemExit("Missing data/ml train/test files. Run scripts/ml/data_collection_ssr.py first.")

    train_rows = read_rows(TRAIN_PATH)
    X, y = rows_to_xy(train_rows)
    Xn, mean, std = normalize_train_matrix(X)
    W, b = train_multinomial_logistic(Xn, y, n_classes=len(HINT_CLASSES), epochs=args.epochs)
    train_acc = float((Xn @ W.T + b).argmax(axis=1).astype("int64").tolist().count(0))
    train_acc = float(((Xn @ W.T + b).argmax(axis=1) == y).mean())
    manifest_path = TRAIN_PATH.parent / "ssr_forgetting_curve_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    model = {
        "hint_classes": list(HINT_CLASSES),
        "mean": mean,
        "std": std,
        "W": W,
        "b": b,
        "metadata": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "train_rows": len(train_rows),
            "test_rows": len(read_rows(TEST_PATH)),
            "train_acc_approx": round(train_acc, 4),
            "real_samples": int(manifest.get("real_samples", 0)),
            "synthetic_samples": int(manifest.get("synthetic_samples", 0)),
            "source_train": str(TRAIN_PATH.relative_to(TRAIN_PATH.parents[2])).replace("\\", "/"),
            "source_test": str(TEST_PATH.relative_to(TEST_PATH.parents[2])).replace("\\", "/"),
        },
    }
    dump_model(MODEL_PATH, model)
    if args.export_json_weights:
        write_json_weights(WEIGHTS_PATH, model)
    print(f"Wrote {MODEL_PATH} train_acc~={train_acc:.3f}")
    if args.export_json_weights:
        print(f"Wrote {WEIGHTS_PATH}")


if __name__ == "__main__":
    main()
