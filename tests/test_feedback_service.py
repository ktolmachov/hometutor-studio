import json

import app.feedback_service as feedback_service


def test_append_and_summary_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback_service, "FEEDBACK_PATH", tmp_path / "fb.jsonl")
    feedback_service.append_feedback(helpful=True, request_id="r1", question_preview="hello")
    feedback_service.append_feedback(helpful=False, request_id="r1", question_preview="hello2")
    summary = feedback_service.get_feedback_summary(limit_lines=10)
    assert summary["total_events"] == 2
    assert summary["helpful_yes"] == 1
    assert summary["helpful_no"] == 1
    assert summary["helpful_rate"] == 0.5
    lines = (tmp_path / "fb.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert json.loads(lines[0])["schema_version"] == feedback_service.FEEDBACK_SCHEMA_VERSION
