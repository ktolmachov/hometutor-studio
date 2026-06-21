from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "run_local_stack.ps1"


def _launcher_source() -> str:
    return LAUNCHER.read_text(encoding="utf-8-sig")


def test_streamlit_is_bound_to_loopback() -> None:
    source = _launcher_source()

    assert '"--server.address", "127.0.0.1"' in source
    assert '"--server.port", "8501"' in source


def test_streamlit_does_not_start_when_api_readiness_times_out() -> None:
    source = _launcher_source()

    assert "Streamlit launch aborted" in source
    assert "starting Streamlit anyway" not in source


def test_startup_banner_does_not_claim_unmeasured_cache_hit_rate() -> None:
    source = _launcher_source()

    assert "80%+ hit rate" not in source
    assert "hit rate depends on workload" in source
