import argparse
import os

from app.eval_service import run_eval, run_tutor_regression


def main():
    parser = argparse.ArgumentParser(description="Offline eval: default RAG dataset or tutor regression.")
    parser.add_argument(
        "--mode",
        choices=["default", "tutor"],
        default=os.environ.get("EVAL_MODE", "default"),
        help="default: eval_questions.json; tutor: tutor_regression.json",
    )
    parser.add_argument(
        "--dataset",
        default="eval_questions.json",
        help="Dataset filename under eval_data/ (mode=default)",
    )
    parser.add_argument(
        "--tutor-dataset",
        default="tutor_regression.json",
        help="Tutor regression JSON under eval_data/ (mode=tutor)",
    )
    parser.add_argument(
        "--tutor-baseline",
        default=None,
        help="Baseline JSON for tutor regression (overrides EVAL_TUTOR_BASELINE_JSON)",
    )
    args = parser.parse_args()

    if args.mode == "tutor":
        output_path, output = run_tutor_regression(
            args.tutor_dataset,
            baseline_path=args.tutor_baseline,
        )
    else:
        output_path, output = run_eval(args.dataset)

    print("\n=== EVAL SUMMARY ===")
    for k, v in output["summary"].items():
        print(f"{k}: {v}")

    print("\n=== BY CATEGORY ===")
    for category, metrics in output.get("category_summary", {}).items():
        print(f"\n[{category}]")
        for k, v in metrics.items():
            print(f"{k}: {v}")

    baseline_comparison = output.get("baseline_comparison")
    if baseline_comparison:
        print("\n=== BASELINE COMPARISON ===")
        print(f"passed: {baseline_comparison.get('passed')}")
        regressions = baseline_comparison.get("regressions") or []
        if regressions:
            print("regressions:", ", ".join(regressions))

    print(f"\nSaved to: {output_path}")

    if baseline_comparison and not baseline_comparison.get("passed", True):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
