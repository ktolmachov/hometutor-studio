import json
import sys

from scripts import learner_state_health


def test_learner_state_health_cli_json(monkeypatch, capsys):
    monkeypatch.setattr(
        learner_state_health,
        "build_report",
        lambda **kwargs: {
            "schema_version": 1,
            "status": "ok",
            "is_stale": False,
            "user_id": kwargs["user_id"],
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["learner_state_health.py", "--user-id", "local", "--json-out"],
    )

    rc = learner_state_health.main()
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["status"] == "ok"
    assert payload["user_id"] == "local"
