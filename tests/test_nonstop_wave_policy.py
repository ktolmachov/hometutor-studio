from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from nonstop_wave_policy import NonStopPolicy, evaluate


def test_policy_clamps_cli_max_next_tasks() -> None:
    verdict = evaluate(
        requested_non_stop=True,
        chain_step=3,
        cli_max_next_tasks=50,
        policy=NonStopPolicy(max_next_tasks=5),
        env={},
    )
    assert verdict.ok is True
    assert verdict.effective_max_next_tasks == 5


def test_policy_blocks_disabled_non_stop() -> None:
    verdict = evaluate(
        requested_non_stop=True,
        chain_step=0,
        cli_max_next_tasks=50,
        policy=NonStopPolicy(enabled=False),
        env={},
    )
    assert verdict.ok is False
    assert "disabled" in verdict.reason


def test_policy_blocks_runtime_over_limit() -> None:
    verdict = evaluate(
        requested_non_stop=True,
        chain_step=1,
        cli_max_next_tasks=50,
        policy=NonStopPolicy(max_runtime_seconds=10),
        env={"HOME_RAG_NON_STOP_STARTED_AT": "100"},
        now=111,
    )
    assert verdict.ok is False
    assert "runtime" in verdict.reason
