from __future__ import annotations

import json

from app import tutorial_service


def test_save_tutorial_progress_persists_json(monkeypatch):
    captured: dict[str, str] = {}

    def _fake_set_kv(key: str, value: str) -> None:
        captured["key"] = key
        captured["value"] = value

    monkeypatch.setattr(tutorial_service.user_state, "set_kv", _fake_set_kv)

    tutorial_service.save_tutorial_progress(
        "alice",
        "ch1_first_answer",
        2,
        ["ch1_first_answer", "ch2_answer_to_learning", "ch1_first_answer"],
    )

    assert captured["key"] == "tutorial_progress_v1:alice"
    payload = json.loads(captured["value"])
    assert payload["chapter_id"] == "ch1_first_answer"
    assert payload["step_index"] == 2
    assert payload["completed_chapters"] == [
        "ch1_first_answer",
        "ch2_answer_to_learning",
    ]


def test_load_tutorial_progress_handles_bad_payload(monkeypatch):
    monkeypatch.setattr(tutorial_service.user_state, "get_kv", lambda _k: "{bad-json")
    assert tutorial_service.load_tutorial_progress("alice") is None


def test_load_tutorial_progress_normalizes_fields(monkeypatch):
    monkeypatch.setattr(
        tutorial_service.user_state,
        "get_kv",
        lambda _k: json.dumps(
            {
                "chapter_id": "ch3_return_tomorrow",
                "step_index": "1",
                "completed_chapters": ["ch1_first_answer", "", "ch2_answer_to_learning"],
            }
        ),
    )

    payload = tutorial_service.load_tutorial_progress("alice")
    assert payload == {
        "chapter_id": "ch3_return_tomorrow",
        "step_index": 1,
        "completed_chapters": ["ch1_first_answer", "ch2_answer_to_learning"],
    }
