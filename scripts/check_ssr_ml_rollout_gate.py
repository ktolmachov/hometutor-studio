#!/usr/bin/env python3
"""
Automated checks for SSR ML serving rollout (package ml-ssr-serving-rollout-gate).

Exit codes:
  0 — PASS
  2 — FAIL (contract / thresholds / weights / pytest)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
EXIT_OK = 0
EXIT_FAIL = 2

CONTRACT_PATH = ROOT / "eval_data" / "ml_eval" / "ssr_level1" / "evaluation_contract.yaml"


def _weights_path() -> Path:
    """Weights live in the pip-installed ``app`` package (split studio layout)."""
    try:
        import app.config as cfg

        candidate = Path(cfg.__file__).resolve().parent / "ssr_ml_reranking_weights.json"
        if candidate.is_file():
            return candidate
    except ImportError:
        pass
    return ROOT / "app" / "ssr_ml_reranking_weights.json"


WEIGHTS_PATH = _weights_path()

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    yaml = None


def _contract_doc() -> dict | None:
    raw = CONTRACT_PATH.read_text(encoding="utf-8")
    if yaml is None:
        return None
    loaded = yaml.safe_load(raw)
    return loaded if isinstance(loaded, dict) else None


def collect_static_violations() -> list[str]:
    """Checks independent of pytest; used by tests and CLI."""
    errs: list[str] = []
    if not CONTRACT_PATH.exists():
        return [f"missing contract file {CONTRACT_PATH.relative_to(ROOT)}"]

    text = CONTRACT_PATH.read_text(encoding="utf-8")
    if "serving_rollout_gates:" not in text:
        errs.append("missing serving_rollout_gates section in evaluation_contract.yaml")
        return errs

    max_bytes = 1048576
    doc = _contract_doc()
    if yaml is not None:
        ec = doc.get("evaluation_contract") if isinstance(doc, dict) else None
        gates = ec.get("serving_rollout_gates") if isinstance(ec, dict) else None
        if not isinstance(gates, dict):
            errs.append("evaluation_contract.serving_rollout_gates must be a mapping when YAML is available")
        else:
            wmax = gates.get("weights_max_bytes")
            if wmax is not None:
                try:
                    max_bytes = int(wmax)
                except (TypeError, ValueError):
                    errs.append("weights_max_bytes must be int-compatible")
            th = gates.get("thresholds_align_with_settings_defaults")
            if not isinstance(th, dict):
                errs.append("serving_rollout_gates.thresholds_align_with_settings_defaults missing or not a mapping")
            else:
                from app.config import Settings

                exp_enabled = Settings.model_fields["ssr_ml_rerank_enabled"].default
                exp_conf = Settings.model_fields["ssr_ml_rerank_confidence_min"].default
                exp_lat = Settings.model_fields["ssr_ml_rerank_latency_budget_ms"].default
                if th.get("ssr_ml_rerank_enabled") != exp_enabled:
                    errs.append(
                        "YAML ssr_ml_rerank_enabled default mismatch vs Settings.model_fields "
                        f"(yaml={th.get('ssr_ml_rerank_enabled')} vs settings={exp_enabled})"
                    )
                if float(th.get("ssr_ml_rerank_confidence_min", -1)) != float(exp_conf):
                    errs.append(
                        "YAML ssr_ml_rerank_confidence_min mismatch vs Settings defaults "
                        f"(yaml={th.get('ssr_ml_rerank_confidence_min')} vs settings={exp_conf})"
                    )
                if float(th.get("ssr_ml_rerank_latency_budget_ms", -1)) != float(exp_lat):
                    errs.append(
                        "YAML ssr_ml_rerank_latency_budget_ms mismatch vs Settings defaults "
                        f"(yaml={th.get('ssr_ml_rerank_latency_budget_ms')} vs settings={exp_lat})"
                    )

    if not WEIGHTS_PATH.exists():
        errs.append(f"missing weights file {WEIGHTS_PATH.relative_to(ROOT)}")
    elif WEIGHTS_PATH.stat().st_size > max_bytes:
        errs.append(
            f"weights file exceeds limit ({WEIGHTS_PATH.stat().st_size} bytes > {max_bytes})"
        )

    return errs


def run_pytest_gate_modules() -> tuple[int, str]:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/eval/test_ssr_ml_reranking.py",
        "tests/test_ssr_ml_integration.py",
        "-v",
        "--tb=short",
    ]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, out


def main() -> int:
    parser = argparse.ArgumentParser(description="SSR ML serving rollout gate")
    parser.add_argument("--skip-pytest", action="store_true", help="Static checks only")
    parser.add_argument("--json-out", action="store_true")
    args = parser.parse_args()

    violations = collect_static_violations()
    pytest_rc = 0
    pytest_out = ""
    if not args.skip_pytest:
        pytest_rc, pytest_out = run_pytest_gate_modules()

    passed = not violations and pytest_rc == 0
    payload = {
        "gate_kind": "ssr_ml_serving_rollout_gate",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "exit_code": EXIT_OK if passed else EXIT_FAIL,
        "static_violations": violations,
        "pytest_returncode": pytest_rc,
    }

    if args.json_out:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return EXIT_OK if passed else EXIT_FAIL

    print(f"SSR ML rollout gate: {'PASS' if passed else 'FAIL'}")
    if violations:
        for v in violations:
            print(f"  - {v}")
    if not args.skip_pytest and pytest_rc != 0:
        print(pytest_out[-8000:] if len(pytest_out) > 8000 else pytest_out)

    return EXIT_OK if passed else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
