"""
Run eval across several RAG configurations and print a compact comparison table.

Each configuration is executed in a subprocess so env overrides do not leak.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

EVAL_COMPARE_CONFIGS = [
    {"name": "fast", "env": {"RAG_PROFILE": "fast"}},
    {"name": "quality", "env": {"RAG_PROFILE": "quality"}},
]


def run_eval_for_config(config: dict, eval_questions: str = "eval_questions.json") -> dict | None:
    """Run `run_eval.py` for one config and return the parsed artifact."""
    env = {**os.environ, **config["env"]}
    env["EVAL_QUESTIONS_FILE"] = eval_questions

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, dir=BASE_DIR) as temp_file:
        out_path = temp_file.name
    env["EVAL_OUTPUT_JSON"] = out_path

    try:
        result = subprocess.run(
            [sys.executable, "run_eval.py"],
            env=env,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        if result.returncode not in (0, 2):
            print(result.stderr or result.stdout, file=sys.stderr)
            return None

        with open(out_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return {
            "summary": data.get("summary") or {},
            "baseline_comparison": data.get("baseline_comparison"),
            "artifact_path": data.get("artifact_path") or out_path,
            "returncode": result.returncode,
        }
    except Exception as exc:
        print(f"Error for config {config['name']}: {exc}", file=sys.stderr)
        return None
    finally:
        try:
            os.unlink(out_path)
        except Exception:
            pass


def main():
    print("Comparing RAG configurations via eval...\n")
    rows = []

    for cfg in EVAL_COMPARE_CONFIGS:
        print(f"Running eval: {cfg['name']} ...")
        result = run_eval_for_config(cfg)
        if result is None:
            rows.append((cfg["name"], None))
            continue

        summary = result["summary"]
        rows.append((cfg["name"], result))
        print(
            f"  dataset_version={summary.get('dataset_version')} "
            f"avg_latency_sec={summary.get('avg_latency_sec')} "
            f"answer_relevancy={summary.get('avg_answer_relevancy')} "
            f"faithfulness={summary.get('avg_faithfulness')}"
        )
        baseline_comparison = result.get("baseline_comparison")
        if baseline_comparison:
            print(
                f"  baseline_passed={baseline_comparison.get('passed')} "
                f"regressions={baseline_comparison.get('regressions') or []}"
            )

    print("\n=== Summary ===")
    print(f"{'Config':<20} {'Dataset':<24} {'Latency':>12} {'AnswerRel':>12} {'Faithful':>12} {'Gate':>8}")
    print("-" * 96)

    failed_gate = False
    for name, result in rows:
        if result is None:
            print(f"{name:<20} {'(error)':>12}")
            continue

        summary = result["summary"]
        baseline_comparison = result.get("baseline_comparison")
        gate_status = "n/a"
        if baseline_comparison:
            passed = baseline_comparison.get("passed", True)
            gate_status = "pass" if passed else "fail"
            failed_gate = failed_gate or not passed

        print(
            f"{name:<20} "
            f"{str(summary.get('dataset_version') or '-'): <24} "
            f"{summary.get('avg_latency_sec') or '-':>12} "
            f"{summary.get('avg_answer_relevancy') or '-':>12} "
            f"{summary.get('avg_faithfulness') or '-':>12} "
            f"{gate_status:>8}"
        )

    if failed_gate:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
