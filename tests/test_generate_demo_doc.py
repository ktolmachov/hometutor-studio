from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import generate_demo_doc as gdd


def test_load_scenarios_uses_narrative_order_with_unknowns_last(tmp_path):
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()
    for scenario_id in ["scenario_02", "scenario_99", "scenario_03", "scenario_01"]:
        (scenarios_dir / f"{scenario_id}.yaml").write_text(
            f"id: {scenario_id}\ntitle: {scenario_id}\n",
            encoding="utf-8",
        )

    scenarios = gdd.load_scenarios(scenarios_dir)

    assert [scenario.id for scenario in scenarios] == [
        "scenario_01",
        "scenario_02",
        "scenario_03",
        "scenario_99",
    ]
