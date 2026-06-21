"""Shared utilities for the SSR forgetting-curve ML pipeline."""

from __future__ import annotations

import csv
import json
import math
import pickle
import random
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HINT_CLASSES = (
    "adaptive_plan",
    "answer_ready",
    "cards_due",
    "mastery_stale",
    "quiz_failed",
    "safe_default",
    "sm2_due",
    "tutor_resume",
)

FEATURE_COLUMNS = (
    "time_since_last_review_hours",
    "quiz_score_last_3_avg",
    "concept_difficulty",
    "session_duration_avg_minutes",
    "time_of_day_hour",
    "day_of_week",
    "cards_due_count",
    "sm2_due_count",
    "quiz_failed_recent",
    "session_fatigue",
    "mastery_gap_score",
    "adaptive_plan_backlog_signals",
    "tutor_stub_active",
    "prior_rule_top_hint_kind",
)

TRAIN_PATH = ROOT / "data" / "ml" / "ssr_forgetting_curve_train.parquet"
TEST_PATH = ROOT / "data" / "ml" / "ssr_forgetting_curve_test.parquet"
MODEL_PATH = ROOT / "models" / "ssr_forgetting_curve_v1.pkl"
REPORT_PATH = ROOT / "eval_data" / "ml_eval" / "ssr_forgetting_curve_v1_report.md"
CONTRACT_CASES_PATH = ROOT / "tests" / "eval" / "ssr_ml_reranking_test_cases.json"
WEIGHTS_PATH = ROOT / "app" / "ssr_ml_reranking_weights.json"

MIN_REAL_SAMPLES = 1000
SYNTHETIC_BOOTSTRAP_MIN = 500
AUC_SERVING_MIN = 0.70
AUC_TARGET = 0.75


def feature_row_from_features(feats: dict[str, Any], prior_s: str | None = None) -> np.ndarray:
    prior_map = {h: i for i, h in enumerate(HINT_CLASSES)}
    prior = prior_map.get(str(prior_s or feats.get("prior_rule_top_hint_kind")), prior_map["safe_default"])
    return np.array(
        [
            float(feats["time_since_last_review_hours"]),
            float(feats["quiz_score_last_3_avg"]),
            float(feats["concept_difficulty"]),
            float(feats["session_duration_avg_minutes"]),
            float(feats["time_of_day_hour"]),
            float(feats["day_of_week"]),
            float(feats["cards_due_count"]),
            float(feats["sm2_due_count"]),
            1.0 if feats["quiz_failed_recent"] else 0.0,
            float(feats["session_fatigue"]),
            float(feats["mastery_gap_score"]),
            float(feats["adaptive_plan_backlog_signals"]),
            1.0 if feats["tutor_stub_active"] else 0.0,
            float(prior) / max(1.0, float(len(HINT_CLASSES) - 1)),
        ],
        dtype=np.float64,
    )


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - np.max(z)
    e = np.exp(z)
    return e / np.clip(e.sum(), 1e-12, None)


def train_multinomial_logistic(
    X: np.ndarray,
    y: np.ndarray,
    *,
    n_classes: int,
    epochs: int = 8000,
    lr: float = 0.08,
    l2: float = 0.02,
) -> tuple[np.ndarray, np.ndarray]:
    n_features = X.shape[1]
    rng = np.random.default_rng(42)
    W = rng.normal(0.0, 0.02, size=(n_classes, n_features))
    b = np.zeros(n_classes, dtype=np.float64)
    idx = np.arange(X.shape[0])
    for ep in range(epochs):
        rng.shuffle(idx)
        for i in idx:
            xi = X[i]
            yi = int(y[i])
            p = softmax(W @ xi + b)
            grad_w = np.outer(p, xi)
            grad_w[yi] -= xi
            grad_b = p.copy()
            grad_b[yi] -= 1.0
            W -= lr * grad_w + lr * l2 * W
            b -= lr * grad_b
        if ep % 1000 == 0 and ep > 0:
            lr *= 0.92
    return W, b


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import pandas as pd  # type: ignore

        pd.DataFrame(rows).to_parquet(path, index=False)
        return
    except (ImportError, ValueError, OSError, ModuleNotFoundError):
        pass
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def read_rows(path: Path) -> list[dict[str, Any]]:
    try:
        import pandas as pd  # type: ignore

        return pd.read_parquet(path).to_dict(orient="records")
    except (ImportError, ValueError, OSError, ModuleNotFoundError):
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def rows_to_xy(rows: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    X = np.stack([feature_row_from_features(r, str(r["prior_rule_top_hint_kind"])) for r in rows], axis=0)
    y = np.array([HINT_CLASSES.index(str(r["ground_truth_best_hint_kind"])) for r in rows], dtype=np.int64)
    return X, y


def normalize_train_matrix(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std = np.where(std < 1e-6, 1.0, std)
    return (X - mean) / std, mean, std


def predict_proba(model: dict[str, Any], feats: dict[str, Any]) -> np.ndarray:
    x = feature_row_from_features(feats, str(feats["prior_rule_top_hint_kind"]))
    xn = (x - np.array(model["mean"], dtype=np.float64)) / np.array(model["std"], dtype=np.float64)
    return softmax(np.array(model["W"], dtype=np.float64) @ xn + np.array(model["b"], dtype=np.float64))


def dump_model(path: Path, model: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(model, f)


def load_model(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        return pickle.load(f)


def load_contract_cases() -> list[dict[str, Any]]:
    raw = json.loads(CONTRACT_CASES_PATH.read_text(encoding="utf-8"))
    rows = []
    for case in raw:
        feats = dict(case["features"])
        rows.append(
            {
                **{k: feats[k] for k in FEATURE_COLUMNS},
                "ground_truth_best_hint_kind": str(case["ground_truth_best_hint_kind"]),
                "retention_probability_label": int(case["retention_probability_label"]),
                "sample_source": "contract_case",
                "source_id": str(case["id"]),
            }
        )
    return rows


def split_rows(rows: list[dict[str, Any]], *, seed: int = 42, test_ratio: float = 0.2) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(seed)
    shuffled = list(rows)
    rng.shuffle(shuffled)
    test_n = max(1, int(round(len(shuffled) * test_ratio)))
    return shuffled[test_n:], shuffled[:test_n]


def auc_roc_binary(y_true: list[int], scores: list[float]) -> float:
    pairs = sorted(zip(scores, y_true), key=lambda x: x[0])
    pos = sum(y_true)
    neg = len(y_true) - pos
    if pos == 0 or neg == 0:
        return 0.5
    rank_sum = 0.0
    for rank, (_score, label) in enumerate(pairs, start=1):
        if label == 1:
            rank_sum += rank
    return (rank_sum - pos * (pos + 1) / 2.0) / (pos * neg)


def macro_auc_ovr(y_true: list[int], probabilities: list[list[float]]) -> float:
    aucs = []
    for cls_idx in range(len(HINT_CLASSES)):
        binary = [1 if y == cls_idx else 0 for y in y_true]
        aucs.append(auc_roc_binary(binary, [p[cls_idx] for p in probabilities]))
    return float(sum(aucs) / len(aucs))


def precision_recall_at_k(y_true: list[int], probabilities: list[list[float]], *, k: int = 5) -> tuple[float, float]:
    hits = 0
    for expected, probs in zip(y_true, probabilities):
        top_k = np.argsort(np.array(probs))[-k:]
        if expected in top_k:
            hits += 1
    hit_rate = hits / max(1, len(y_true))
    return hit_rate, hit_rate


def confusion_matrix(y_true: list[int], y_pred: list[int]) -> list[list[int]]:
    matrix = [[0 for _ in HINT_CLASSES] for _ in HINT_CLASSES]
    for expected, predicted in zip(y_true, y_pred):
        matrix[expected][predicted] += 1
    return matrix


def retention_score(prob_map: dict[str, float]) -> float:
    return (
        0.35 * prob_map.get("cards_due", 0.0)
        + 0.25 * prob_map.get("sm2_due", 0.0)
        + 0.15 * prob_map.get("quiz_failed", 0.0)
        + 0.10 * prob_map.get("mastery_stale", 0.0)
        + 0.10 * prob_map.get("adaptive_plan", 0.0)
        + 0.05 * prob_map.get("tutor_resume", 0.0)
    )


def evaluate_rows(model: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    y_true: list[int] = []
    y_pred: list[int] = []
    probabilities: list[list[float]] = []
    retention_labels: list[int] = []
    retention_scores: list[float] = []
    latencies_ms: list[float] = []
    for row in rows:
        t0 = time.perf_counter()
        probs_np = predict_proba(model, row)
        latencies_ms.append((time.perf_counter() - t0) * 1000.0)
        probs = [float(x) for x in probs_np]
        prob_map = {h: probs[i] for i, h in enumerate(HINT_CLASSES)}
        probabilities.append(probs)
        y = HINT_CLASSES.index(str(row["ground_truth_best_hint_kind"]))
        y_true.append(y)
        y_pred.append(int(np.argmax(probs_np)))
        retention_labels.append(int(row.get("retention_probability_label", 0)))
        retention_scores.append(retention_score(prob_map))
    precision_at_5, recall_at_5 = precision_recall_at_k(y_true, probabilities, k=5)
    return {
        "n": len(rows),
        "macro_auc_roc": macro_auc_ovr(y_true, probabilities),
        "retention_auc_roc": auc_roc_binary(retention_labels, retention_scores),
        "accuracy": sum(1 for a, b in zip(y_true, y_pred) if a == b) / max(1, len(y_true)),
        "precision_at_5": precision_at_5,
        "recall_at_5": recall_at_5,
        "inference_latency_p95_ms": float(np.percentile(latencies_ms, 95)) if latencies_ms else math.inf,
        "confusion_matrix": confusion_matrix(y_true, y_pred),
    }


def model_serving_decision(*, real_samples: int, auc_roc: float) -> tuple[str, str]:
    if real_samples < MIN_REAL_SAMPLES:
        return "rule_based", f"real_samples {real_samples} < {MIN_REAL_SAMPLES}"
    if auc_roc < AUC_SERVING_MIN:
        return "rule_based", f"AUC-ROC {auc_roc:.3f} < {AUC_SERVING_MIN:.2f}"
    return "hybrid_ml", "cold-start and AUC gates passed"


def write_json_weights(path: Path, model: dict[str, Any]) -> None:
    payload = {
        "hint_classes": list(HINT_CLASSES),
        "feature_dim": len(FEATURE_COLUMNS),
        "mean": np.array(model["mean"], dtype=np.float64).tolist(),
        "std": np.array(model["std"], dtype=np.float64).tolist(),
        "W": np.array(model["W"], dtype=np.float64).tolist(),
        "b": np.array(model["b"], dtype=np.float64).tolist(),
        "metadata": dict(model.get("metadata", {})),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
