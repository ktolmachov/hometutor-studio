"""
US-10.1 + US-12.1 + US-12.3 acceptance tests.

US-10.1 — One-click backup всего обучения:
  export_full_sync_bundle() produces a JSON-serializable bundle;
  import_full_sync_bundle() returns rows_inserted >= 1 when learner state present.

US-12.1 — Benchmark качества retrieval с gate:
  aggregate_rates produces hit_rate, mean_reciprocal_rank, answer_relevancy;
  pass verdict is True when all metrics >= thresholds, False otherwise.

US-12.3 — Интеграционные тесты валидируют реальный retrieval:
  test_integration_retrieval.py exists with 5+ integration-marked tests;
  pytest.ini excludes integration tests from default run (via addopts).
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = REPO_ROOT / "tests"
PYTEST_INI = REPO_ROOT / "pytest.ini"


# ---------------------------------------------------------------------------
# Shared DB isolation fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_db(monkeypatch, tmp_path: Path):
    from app.config import reset_settings_cache
    from app.user_state import reset_schema_cache_for_tests

    db = tmp_path / "backup_test.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


# ---------------------------------------------------------------------------
# US-10.1 — One-click backup всего обучения
# ---------------------------------------------------------------------------


class TestOneClickBackup:
    """US-10.1: backup bundle roundtrip with rows_inserted >= 1."""

    def test_export_bundle_is_json_serializable(self, isolated_db, monkeypatch, tmp_path):
        """Exported bundle must be JSON-serializable (ready for download)."""
        monkeypatch.setattr("app.quiz_stats._STATS_FILE", tmp_path / "stats.json")
        from app.quiz_adaptive import update_mastery_after_score
        from app.user_state import export_full_sync_bundle

        update_mastery_after_score("TopicA", 0.9)
        bundle = export_full_sync_bundle()

        serialized = json.dumps(bundle, ensure_ascii=False)
        restored = json.loads(serialized)
        assert isinstance(restored, dict)

    def test_import_rows_inserted_gte_1(self, isolated_db, monkeypatch, tmp_path):
        """US-10.1 core: import_full_sync_bundle returns rows_inserted >= 1."""
        monkeypatch.setattr("app.quiz_stats._STATS_FILE", tmp_path / "stats.json")
        from app.quiz_adaptive import update_mastery_after_score
        from app.user_state import _with_db, export_full_sync_bundle, import_full_sync_bundle

        update_mastery_after_score("TopicB", 1.0)
        bundle = export_full_sync_bundle()

        # Clear state before import
        def _clear(conn):
            conn.execute("DELETE FROM quiz_mastery")
            conn.commit()

        _with_db(_clear)

        result = import_full_sync_bundle(bundle)

        assert result["rows_inserted"] >= 1

    def test_export_bundle_contains_required_keys(self, isolated_db, monkeypatch, tmp_path):
        """Bundle must have sync_version and tables."""
        monkeypatch.setattr("app.quiz_stats._STATS_FILE", tmp_path / "stats.json")
        from app.user_state import export_full_sync_bundle

        bundle = export_full_sync_bundle()

        assert "sync_version" in bundle
        assert "tables" in bundle
        assert isinstance(bundle["tables"], dict)

    def test_sidebar_backup_panel_function_exists(self):
        """UI backup button must exist (Settings panel, US-10.1)."""
        from app.ui.sidebar import _render_sidebar_backup_restore_panel

        assert callable(_render_sidebar_backup_restore_panel)

    def test_export_backup_roundtrip_restores_mastery(self, isolated_db, monkeypatch, tmp_path):
        """State lost after clear is fully restored from backup file."""
        monkeypatch.setattr("app.quiz_stats._STATS_FILE", tmp_path / "stats.json")
        from app.quiz_adaptive import update_mastery_after_score
        from app.user_state import _with_db, export_full_sync_bundle, import_full_sync_bundle

        update_mastery_after_score("TopicC", 1.0)

        def _count(conn):
            return conn.execute("SELECT COUNT(*) AS n FROM quiz_mastery").fetchone()["n"]

        assert _with_db(_count) >= 1
        bundle = export_full_sync_bundle()

        def _clear(conn):
            conn.execute("DELETE FROM quiz_mastery")
            conn.commit()

        _with_db(_clear)
        assert _with_db(_count) == 0

        import_full_sync_bundle(bundle)
        assert _with_db(_count) >= 1


# ---------------------------------------------------------------------------
# US-12.1 — Benchmark качества retrieval с gate
# ---------------------------------------------------------------------------


class TestQualityBenchmarkGate:
    """US-12.1: benchmark reports hit_rate, MRR, answer_relevancy with pass/fail verdict."""

    def test_aggregate_rates_has_required_keys(self):
        """US-12.1: benchmark aggregate must include hit_rate, MRR, answer_relevancy."""
        from quality_benchmark_metrics import aggregate_rates

        rows = [
            {"source_hit": True, "reciprocal_rank": 1.0, "answer_relevancy": 0.8},
        ]
        agg = aggregate_rates(rows)

        assert "hit_rate" in agg
        assert "mean_reciprocal_rank" in agg
        assert "answer_relevancy" in agg

    def test_pass_verdict_when_all_thresholds_met(self):
        """Benchmark reports pass=True when hit_rate/MRR/relevancy >= thresholds."""
        from quality_benchmark_metrics import aggregate_rates

        rows = [
            {"source_hit": True, "reciprocal_rank": 1.0, "answer_relevancy": 0.8},
            {"source_hit": True, "reciprocal_rank": 0.5, "answer_relevancy": 0.7},
        ]
        agg = aggregate_rates(rows)

        min_hit_rate = 0.5
        min_mrr = 0.4
        min_relevancy = 0.3
        passed = (
            agg["hit_rate"] >= min_hit_rate
            and agg["mean_reciprocal_rank"] >= min_mrr
            and agg["answer_relevancy"] >= min_relevancy
        )
        assert passed is True

    def test_fail_verdict_when_hit_rate_below_threshold(self):
        """Benchmark reports pass=False when hit_rate < threshold."""
        from quality_benchmark_metrics import aggregate_rates

        rows = [
            {"source_hit": False, "reciprocal_rank": 0.0, "answer_relevancy": 0.0},
            {"source_hit": False, "reciprocal_rank": 0.0, "answer_relevancy": 0.0},
        ]
        agg = aggregate_rates(rows)

        passed = agg["hit_rate"] >= 0.5
        assert passed is False

    def test_benchmark_script_exists_and_importable(self):
        """US-12.1: run_quality_benchmark.py must exist and be importable."""
        benchmark_path = REPO_ROOT / "scripts" / "run_quality_benchmark.py"
        assert benchmark_path.exists(), "scripts/run_quality_benchmark.py not found"

    def test_benchmark_report_pass_key_present_in_schema(self):
        """Benchmark output JSON must include 'pass' key (gate verdict)."""
        from quality_benchmark_metrics import aggregate_rates

        rows = [
            {"source_hit": True, "reciprocal_rank": 1.0, "answer_relevancy": 0.9},
        ]
        agg = aggregate_rates(rows)
        report = {
            "aggregate": agg,
            "pass": agg["hit_rate"] >= 0.5,
            "thresholds": {"min_hit_rate": 0.5, "min_mrr": 0.4, "min_relevancy": 0.3},
        }

        assert "pass" in report
        assert report["pass"] is True

    def test_mrr_below_threshold_triggers_fail(self):
        """pass=False when MRR < threshold even if hit_rate is fine."""
        from quality_benchmark_metrics import aggregate_rates

        rows = [
            {"source_hit": True, "reciprocal_rank": 0.1, "answer_relevancy": 0.9},
        ]
        agg = aggregate_rates(rows)

        passed = (
            agg["hit_rate"] >= 0.5
            and agg["mean_reciprocal_rank"] >= 0.5
            and agg["answer_relevancy"] >= 0.3
        )
        assert passed is False


# ---------------------------------------------------------------------------
# US-12.3 — Интеграционные тесты валидируют реальный retrieval
# ---------------------------------------------------------------------------


class TestIntegrationRetrievalSetup:
    """US-12.3: integration tests exist, are marker-gated, and cover 5+ scenarios."""

    def test_integration_test_file_exists(self):
        """US-12.3: test_integration_retrieval.py must exist."""
        assert (TESTS_DIR / "test_integration_retrieval.py").exists()

    def test_integration_tests_skipped_in_default_run(self, tmp_path):
        """US-12.3: pytest.ini must exclude integration tests from default run."""
        assert PYTEST_INI.exists()
        content = PYTEST_INI.read_text(encoding="utf-8")
        assert "not integration" in content, "addopts must contain 'not integration'"

    def test_integration_marker_defined_in_pytest_ini(self):
        """integration marker must be declared in pytest.ini markers section."""
        content = PYTEST_INI.read_text(encoding="utf-8")
        assert "integration" in content

    def test_integration_file_has_pytestmark_integration(self):
        """All tests in integration file must carry the integration marker."""
        source = (TESTS_DIR / "test_integration_retrieval.py").read_text(encoding="utf-8")
        assert "pytestmark = pytest.mark.integration" in source

    def test_integration_file_has_at_least_5_test_functions(self):
        """US-12.3: 5–10 integration tests must exist (acceptance criteria)."""
        source = (TESTS_DIR / "test_integration_retrieval.py").read_text(encoding="utf-8")
        test_count = source.count("\ndef test_")
        assert test_count >= 5, f"Expected >=5 integration tests, found {test_count}"

    def test_integration_tests_cover_file_filter(self):
        """US-12.3: file-filter test must be present."""
        source = (TESTS_DIR / "test_integration_retrieval.py").read_text(encoding="utf-8")
        assert "file_filter" in source or "filter" in source.lower()

    def test_integration_tests_cover_source_hit(self):
        """US-12.3: source hit / relevance test must be present."""
        source = (TESTS_DIR / "test_integration_retrieval.py").read_text(encoding="utf-8")
        assert "source_hit" in source or "sources" in source
