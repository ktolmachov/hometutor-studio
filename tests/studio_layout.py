"""Split-repo helpers: studio checkout (tests/doc/eval_data) vs pip-installed product (app/)."""

from __future__ import annotations

import importlib
from pathlib import Path

import app.config as app_config

STUDIO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_ROOT = Path(app_config.__file__).resolve().parent.parent


def is_split_layout() -> bool:
    return STUDIO_ROOT.resolve() != PRODUCT_ROOT.resolve()


def product_app_path(*parts: str) -> Path:
    """Resolve a path under the installed ``app`` package (e.g. ``ui/main.py``)."""
    return Path(app_config.__file__).resolve().parent.joinpath(*parts)


def _rebind_eval_harness(root: Path) -> None:
    eh = importlib.import_module("app.ssr_ai.eval_harness")
    pfx = "".join(("s", "s", "r"))
    eh.ROOT = root
    # ``dataset.repo_root()`` reads module-level ``ROOT`` copied at import time.
    ds = importlib.import_module("app.ssr_ai.dataset")
    ds.ROOT = root
    eval_dir = root / "tests" / "eval"
    archive = root / "eval_data" / "ml_eval"
    eh.CASES_PATH = eval_dir / f"{pfx}_ml_reranking_test_cases.json"
    eh.RUBRIC_PATH = root / "doc" / "eval" / f"{pfx}_ml_reranking_rubric.md"
    eh.CONTRACT_PATH = archive / f"{pfx}_level1" / "evaluation_contract.yaml"
    eh.ML_PACKAGE_PATH = archive / f"{pfx}_level1" / f"ml_{pfx}_local_reranking_v1_package.yaml"
    eh.TRAIN_DATA_PATH = root / "data" / "ml" / f"{pfx}_forgetting_curve_train.parquet"
    eh.TEST_DATA_PATH = root / "data" / "ml" / f"{pfx}_forgetting_curve_test.parquet"
    eh.DATA_SCRIPT_PATH = root / "scripts" / "ml" / f"data_collection_{pfx}.py"
    eh.TRAIN_SCRIPT_PATH = root / "scripts" / "ml" / f"train_{pfx}_forgetting_curve.py"
    eh.EVAL_SCRIPT_PATH = root / "scripts" / "ml" / f"eval_{pfx}_forgetting_curve.py"
    eh.MODEL_PATH = root / "models" / f"{pfx}_forgetting_curve_v1.pkl"
    eh.REPORT_PATH = archive / f"{pfx}_forgetting_curve_v1_report.md"


def _rebind_adversarial_runner(root: Path) -> None:
    atr = importlib.import_module("app.adversarial_test_runner")
    atr.EVAL_ROOT = root / "eval_data"
    atr.DEFENSE_DATASET = atr.EVAL_ROOT / "defense_eval_questions.json"
    atr.ADVERSARIAL_MANIFEST = atr.EVAL_ROOT / "adversarial" / "adversarial_rag_cases.json"


def _rebind_eval_uplift(root: Path) -> None:
    import app.eval_uplift as eu

    def _path() -> Path:
        return root / eu.GRAPH_SHAPED_DATASET_REL

    eu.graph_shaped_dataset_path = _path  # type: ignore[assignment]


def _rebind_eval_service(root: Path) -> None:
    es = importlib.import_module("app.eval_service")
    es.EVAL_DATA_DIR = root / "eval_data"
    es.EVAL_RESULTS_DIR = root / "eval_results"


def apply_studio_root_patches() -> None:
    """Point studio-owned assets (eval_data, archive, tests/eval) at the checkout root."""
    if not is_split_layout():
        return
    root = STUDIO_ROOT
    app_config.BASE_DIR = root
    _rebind_eval_harness(root)
    _rebind_adversarial_runner(root)
    _rebind_eval_uplift(root)
    _rebind_eval_service(root)
