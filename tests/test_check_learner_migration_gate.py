from scripts import check_learner_migration_gate as gate


def test_resolve_thresholds_uses_profile_defaults():
    local = gate.resolve_thresholds(profile="local")
    strict = gate.resolve_thresholds(profile="strict")
    assert local["min_window"] == 10
    assert strict["min_window"] == 30
    assert strict["max_rehydrated_rate"] < local["max_rehydrated_rate"]


def test_evaluate_gate_fails_when_rate_above_threshold():
    metrics = {"window_size": 20, "rehydrated_rate": 0.4}
    thresholds = {"min_window": 10, "max_rehydrated_rate": 0.2}
    out = gate.evaluate_gate(metrics, thresholds)
    assert out["passed"] is False
    assert any(c["metric"] == "rehydrated_rate" and c["passed"] is False for c in out["checks"])


def test_run_gate_returns_pass_with_local_profile(monkeypatch):
    monkeypatch.setattr(
        "app.learner_model_service.get_learner_profile_migration_metrics",
        lambda limit=200: {"window_size": 50, "rehydrated_rate": 0.1},
    )
    report, rc = gate.run_gate(profile="local", limit_history=50)
    assert rc == 0
    assert report["quality_gate"]["passed"] is True


def test_run_gate_returns_fail_with_strict_profile(monkeypatch):
    monkeypatch.setattr(
        "app.learner_model_service.get_learner_profile_migration_metrics",
        lambda limit=200: {"window_size": 50, "rehydrated_rate": 0.3},
    )
    report, rc = gate.run_gate(profile="strict", limit_history=50)
    assert rc == 2
    assert report["quality_gate"]["passed"] is False

