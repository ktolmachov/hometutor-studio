from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import app.metrics as metrics
from scripts import run_eval_loop as loop


def _patch_common(monkeypatch, *, alerts=None):
    monkeypatch.setattr(loop, "_cost_summary", lambda limit_events=20000: None)
    monkeypatch.setattr(
        loop,
        "_run_slo_alerts",
        lambda *, latency_by_mode, webhook, limit_events: {"alerts": alerts or [], "anomalies": []},
    )


def test_eval_loop_ci_profile_skips_llm_phases(monkeypatch):
    _patch_common(monkeypatch)
    called: list[str] = []

    monkeypatch.setattr(loop, "run_prompt_smoke_phase", lambda *, profile: called.append("prompt") or {"status": "pass"})
    monkeypatch.setattr(loop, "run_judge_sweep_phase", lambda *, limit_events=20000: called.append("judge") or {"status": "skipped", "sample_size": 0})
    monkeypatch.setattr(loop, "run_latency_by_mode_phase", lambda *, limit_events=20000: called.append("latency") or {"status": "skipped", "by_mode": {}})
    monkeypatch.setattr(loop, "run_quality_benchmark_phase", lambda: called.append("quality") or {"status": "pass"})
    monkeypatch.setattr(loop, "run_router_eval_phase", lambda: called.append("router") or {"status": "pass"})

    report, rc = loop.run_eval_loop(profile="ci")

    assert rc == 0
    assert called == ["prompt", "judge", "latency"]
    assert report["phases"]["quality_benchmark"] is None
    assert report["phases"]["router_eval"] is None


def test_eval_loop_nightly_runs_all_phases(monkeypatch):
    _patch_common(monkeypatch)
    called: list[str] = []

    monkeypatch.setattr(loop, "run_prompt_smoke_phase", lambda *, profile: called.append("prompt") or {"status": "pass"})
    monkeypatch.setattr(loop, "run_quality_benchmark_phase", lambda: called.append("quality") or {"status": "pass"})
    monkeypatch.setattr(loop, "run_router_eval_phase", lambda: called.append("router") or {"status": "pass"})
    monkeypatch.setattr(loop, "run_judge_sweep_phase", lambda *, limit_events=20000: called.append("judge") or {"status": "pass"})
    monkeypatch.setattr(loop, "run_latency_by_mode_phase", lambda *, limit_events=20000: called.append("latency") or {"status": "pass", "by_mode": {}})

    report, rc = loop.run_eval_loop(profile="nightly")

    assert rc == 0
    assert called == ["prompt", "quality", "router", "judge", "latency"]
    assert report["profile"] == "nightly"


def test_eval_loop_fail_on_slo_breach(monkeypatch):
    _patch_common(
        monkeypatch,
        alerts=[
            {
                "kind": "slo",
                "metric": "p95_total_answer_ms_by_query_type",
                "query_type": "tutor",
            }
        ],
    )
    monkeypatch.setattr(loop, "run_prompt_smoke_phase", lambda *, profile: {"status": "pass"})
    monkeypatch.setattr(loop, "run_judge_sweep_phase", lambda *, limit_events=20000: {"status": "skipped"})
    monkeypatch.setattr(loop, "run_latency_by_mode_phase", lambda *, limit_events=20000: {"status": "fail", "by_mode": {}})

    report, rc = loop.run_eval_loop(profile="ci")

    assert rc == 2
    assert report["overall_status"] == "fail"
    assert report["slo_alerts"]["alerts"][0]["query_type"] == "tutor"


def test_eval_loop_pass_all_green(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(loop, "run_prompt_smoke_phase", lambda *, profile: {"status": "pass"})
    monkeypatch.setattr(loop, "run_quality_benchmark_phase", lambda: {"status": "pass"})
    monkeypatch.setattr(loop, "run_router_eval_phase", lambda: {"status": "pass"})
    monkeypatch.setattr(loop, "run_judge_sweep_phase", lambda *, limit_events=20000: {"status": "pass"})
    monkeypatch.setattr(loop, "run_latency_by_mode_phase", lambda *, limit_events=20000: {"status": "pass", "by_mode": {}})

    report, rc = loop.run_eval_loop(profile="nightly")

    assert rc == 0
    assert report["overall_status"] == "pass"


def test_eval_loop_report_schema_valid(monkeypatch, tmp_path, capsys):
    _patch_common(monkeypatch)
    monkeypatch.setattr(loop, "run_prompt_smoke_phase", lambda *, profile: {"status": "pass"})
    monkeypatch.setattr(loop, "run_judge_sweep_phase", lambda *, limit_events=20000: {"status": "skipped"})
    monkeypatch.setattr(loop, "run_latency_by_mode_phase", lambda *, limit_events=20000: {"status": "skipped", "by_mode": {}})
    report_path = tmp_path / "report.json"
    monkeypatch.setattr(sys, "argv", ["run_eval_loop.py", "--profile", "ci", "--report-json", str(report_path)])

    rc = loop.main()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    printed = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["schema_version"] == loop.REPORT_SCHEMA_VERSION
    assert set(["phases", "slo_alerts", "overall_status"]).issubset(payload)
    assert printed["profile"] == "ci"


def test_per_mode_latency_slo_alert(monkeypatch, tmp_path):
    # Загрузить цепочку импортов до monkeypatch get_settings, иначе resolve второго
    # патча тянет learner_model_service → index_registry с «левым» _S и рвётся,
    # а откат первого патча может не выполниться — портятся последующие тесты.
    import app.learner_model_service  # noqa: F401

    module = importlib.reload(metrics)
    module.METRICS_STORE_PATH = tmp_path / "metrics_store.jsonl"
    module.record_request(
        request_id="slow-tutor",
        question="q",
        query_type="tutor",
        total_answer_ms=1500.0,
        pipeline_ms=100.0,
        engine_acquire_ms=10.0,
        query_execute_ms=80.0,
        source_count=1,
        fallback_applied=False,
        estimated_cost_usd=0.001,
        answer_empty=False,
    )

    class _S:
        slo_max_fallback_rate = None
        slo_min_source_coverage = None
        slo_max_p95_latency_ms = None
        slo_latency_by_mode = {"tutor": 1000.0}
        slo_max_avg_cost_usd = None
        slo_min_judge_score = None
        slo_max_learner_rehydrated_rate = None
        slo_anomaly_recent_window = 0
        slo_anomaly_sigma = 2.0
        alert_webhook_url = None

    monkeypatch.setattr("app.config.get_settings", lambda: _S())
    monkeypatch.setattr(
        "app.learner_model_service.get_learner_profile_migration_metrics",
        lambda limit=20000: {"window_size": 0, "rehydrated_rate": None},
    )

    out = module.evaluate_slo_alerts(limit_events=50)

    assert any(
        a.get("metric") == "p95_total_answer_ms_by_query_type" and a.get("query_type") == "tutor"
        for a in out["alerts"]
    )
    assert out["observed"]["latency_by_mode"]["by_mode"]["tutor"]["slo_status"] == "fail"
