import json

from app.langfuse_dataset import (
    build_eval_dataset,
    load_trace_export,
    trace_to_eval_case,
    write_eval_dataset,
)
from scripts import build_langfuse_eval_dataset


def _failed_trace(**overrides):
    trace = {
        "id": "trace-1",
        "status": "ERROR",
        "input": {"question": "Why did test@example.com fail?"},
        "expectedOutput": {"answer": "Use token: abcdefgh"},
        "metadata": {
            "expected_sources": ["docs/a.md"],
            "category": "qa",
        },
    }
    trace.update(overrides)
    return trace


def test_trace_to_eval_case_redacts_and_preserves_eval_fields():
    case = trace_to_eval_case(_failed_trace())

    assert case is not None
    assert "test@example.com" not in case["question"]
    assert "abcdefgh" not in case["reference_answer"]
    assert case["expected_sources"] == ["docs/a.md"]
    assert case["source_trace_id"] == "trace-1"


def test_trace_to_eval_case_filters_success_and_incomplete_rows():
    assert trace_to_eval_case(_failed_trace(status="OK")) is None
    assert trace_to_eval_case(_failed_trace(input={})) is None
    assert trace_to_eval_case(_failed_trace(status="OK"), failed_only=False) is not None


def test_build_eval_dataset_deduplicates_deterministically():
    first = _failed_trace(id="one")
    duplicate = _failed_trace(id="two")
    cases = build_eval_dataset([duplicate, first])

    assert len(cases) == 1
    assert cases[0]["source_trace_id"] == "two"


def test_load_and_write_dataset_support_json_envelope_and_jsonl(tmp_path):
    envelope = tmp_path / "traces.json"
    envelope.write_text(json.dumps({"data": [_failed_trace()]}), encoding="utf-8")
    assert len(load_trace_export(envelope)) == 1

    jsonl = tmp_path / "traces.jsonl"
    jsonl.write_text(json.dumps(_failed_trace()) + "\n", encoding="utf-8")
    traces = load_trace_export(jsonl)
    output = tmp_path / "dataset.json"
    write_eval_dataset(output, build_eval_dataset(traces))
    assert json.loads(output.read_text(encoding="utf-8"))[0]["source"] == "langfuse_export"
    assert not output.with_suffix(".json.tmp").exists()


def test_cli_builds_dataset_without_running_eval(tmp_path, capsys):
    export = tmp_path / "traces.json"
    output = tmp_path / "dataset.json"
    export.write_text(json.dumps([_failed_trace()]), encoding="utf-8")

    rc = build_langfuse_eval_dataset.main([str(export), "--output", str(output)])

    assert rc == 0
    assert len(json.loads(output.read_text(encoding="utf-8"))) == 1
    assert "wrote 1 eval cases" in capsys.readouterr().out


def test_cli_reports_missing_export_without_traceback(tmp_path, capsys):
    missing = tmp_path / "missing.json"

    rc = build_langfuse_eval_dataset.main([str(missing)])

    captured = capsys.readouterr()
    assert rc == 2
    assert "Langfuse export not found" in captured.err
    assert str(missing.resolve()) in captured.err
    assert "Traceback" not in captured.err
