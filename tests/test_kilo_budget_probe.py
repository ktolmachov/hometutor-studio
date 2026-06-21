from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import kilo_budget_probe as probe  # noqa: E402


def _record_with_marker(marker: str, *, body_chars: int, level: str, blocked: bool) -> dict:
    return {
        "path": "/v1/chat/completions",
        "request": {
            "body_chars": body_chars,
            "messages_count": 4,
            "body_raw": marker,
            "message_stats": [
                {
                    "index": 0,
                    "role": "tool",
                    "chars": 1234,
                    "summary": {
                        "preview_start": "<path>doc\\tasklist.md</path> <type>file</type>"
                    },
                }
            ],
        },
        "guard": {
            "level": level,
            "blocked": blocked,
            "risk_flags": ["planning prompt injected"] if level != "ok" else [],
        },
    }


def test_match_probe_id_from_body_raw():
    record = _record_with_marker("[KILO-PROBE: ORCH-LAUNCHER]", body_chars=100, level="ok", blocked=False)
    assert probe._match_probe_id(record) == "orch_launcher"


def test_build_probe_summary_aggregates_levels_and_contributors():
    records = [
        _record_with_marker("[KILO-PROBE: PLANNING-LAUNCHER]", body_chars=82000, level="warn", blocked=False),
        _record_with_marker("[KILO-PROBE: PLANNING-LAUNCHER]", body_chars=95000, level="soft_block", blocked=True),
    ]
    summary = probe._build_probe_summary(records, "planning_launcher")
    assert summary["requests"] == 2
    assert summary["blocked"] == 1
    assert summary["max_body_chars"] == 95000
    assert "planning prompt injected" in summary["risk_flags"]
    assert any("doc\\tasklist.md" in item for item in summary["top_contributors"])


def test_global_recommendations_include_block_and_budget_signal():
    records = []
    probe_summaries = [
        {
            "probe_id": "orch_launcher",
            "requests": 1,
            "blocked": 1,
            "max_body_chars": 98000,
            "max_messages": 9,
            "levels": {"soft_block": 1},
            "risk_flags": ["planning prompt injected", "full backlog registry injected"],
            "top_contributors": [],
        }
    ]
    recs = probe._global_recommendations(records, probe_summaries)
    joined = " ".join(recs)
    assert "Relay blocked" in joined
    assert "exceeded the soft budget threshold" in joined
    assert "Backlog registry" in joined
    assert "Session history" in joined
