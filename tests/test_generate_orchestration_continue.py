from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_orchestration_prompt as gop  # noqa: E402
import prompt_utils  # noqa: E402


def test_continue_agent_adapter_is_registered_and_parseable() -> None:
    adapter_path = prompt_utils.resolve_agent_adapter_file("continue")
    assert gop.AGENT_ADAPTERS["continue"] == adapter_path

    assert adapter_path.name == "agent_adapter_continue.md"
    assert adapter_path.exists()

    adapter = gop._parse_adapter(adapter_path)

    assert adapter["MAX_PARALLEL"] == "1"
    assert "DeepSeek" in adapter["AGENT_SPAWN"]
    assert "execution_contract.md" in adapter["WRITE_FILE"]
