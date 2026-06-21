import json
import sys

from scripts import smoke_learner_migration_gate as smoke_gate


def test_generate_learner_migration_smoke_history_writes_rows(monkeypatch):
    store: dict[str, str] = {}
    monkeypatch.setattr("app.user_state.set_kv", lambda key, value: store.__setitem__(key, value))
    result = smoke_gate.generate_learner_migration_smoke_history(rows=6, mode="healthy")
    assert result["rows_written"] == 6
    raw = store[result["history_key"]]
    payload = json.loads(raw)
    assert len(payload) == 6
    assert payload[0]["state_migration"]["index_changed"] is True


def test_main_runs_smoke_and_gate(monkeypatch, capsys):
    monkeypatch.setattr(
        smoke_gate,
        "generate_learner_migration_smoke_history",
        lambda **kwargs: {"rows_written": 12, "mode": "healthy", "history_key": "k"},
    )
    monkeypatch.setattr(
        "scripts.check_learner_migration_gate.run_gate",
        lambda **kwargs: ({"quality_gate": {"passed": True}, "learner_profile_migration": {"window_size": 12}}, 0),
    )
    monkeypatch.setattr(
        "scripts.check_learner_migration_gate.resolve_thresholds",
        lambda **kwargs: {"min_window": 10, "max_rehydrated_rate": 0.35},
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "smoke_learner_migration_gate.py",
            "--profile",
            "local",
            "--rows",
            "12",
            "--json-out",
        ],
    )
    rc = smoke_gate.main()
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    assert payload["smoke"]["rows_written"] == 12
    assert payload["gate"]["quality_gate"]["passed"] is True


def test_main_strict_profile_auto_expands_rows(monkeypatch, capsys):
    called: dict[str, int] = {}

    def _fake_generate(**kwargs):
        called["rows"] = int(kwargs["rows"])
        return {"rows_written": called["rows"], "mode": "healthy", "history_key": "k"}

    monkeypatch.setattr(smoke_gate, "generate_learner_migration_smoke_history", _fake_generate)
    monkeypatch.setattr(
        "scripts.check_learner_migration_gate.run_gate",
        lambda **kwargs: ({"quality_gate": {"passed": True}, "learner_profile_migration": {"window_size": called["rows"]}}, 0),
    )
    monkeypatch.setattr(
        "scripts.check_learner_migration_gate.resolve_thresholds",
        lambda **kwargs: {"min_window": 30, "max_rehydrated_rate": 0.2},
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "smoke_learner_migration_gate.py",
            "--profile",
            "strict",
            "--json-out",
        ],
    )
    rc = smoke_gate.main()
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    assert called["rows"] >= 30
    assert payload["smoke"]["rows_written"] >= 30

