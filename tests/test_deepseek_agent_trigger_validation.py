from __future__ import annotations

from pathlib import Path

import pytest

from deepseek_tsx_support import ROOT, requires_tsx, run_tsx_script

pytestmark = requires_tsx


def _run_validation_case(tmp_path: Path, content: str) -> tuple[bool, str | None]:
    script = tmp_path / "validate_deepseek_contract.ts"
    trigger_path = (ROOT / "scripts" / "deepseek_agent_trigger.ts").as_posix()
    script.write_text(
        "\n".join(
            [
                'import { pathToFileURL } from "node:url";',
                "async function main() {",
                f'  const mod = await import(pathToFileURL("{trigger_path}").href);',
                f"  const result = mod.validateDeepSeekExecutionProof({content!r});",
                "  console.log(JSON.stringify(result));",
                "}",
                "main().catch((err) => { console.error(err); process.exit(1); });",
            ]
        ),
        encoding="utf-8",
    )
    result = run_tsx_script(script, cwd=ROOT, check=True)
    payload = result.stdout.strip()
    assert payload
    if '"ok":true' in payload:
        return True, None
    reason = payload.split('"reason":"', 1)[1].split('"', 1)[0]
    return False, reason


def test_deepseek_validation_accepts_blocked_api_refusal(tmp_path: Path) -> None:
    ok, reason = _run_validation_case(
        tmp_path,
        "BLOCKED: no local tool access",
    )

    assert ok
    assert reason is None


def test_deepseek_validation_accepts_multiline_blocked_proof(tmp_path: Path) -> None:
    ok, reason = _run_validation_case(
        tmp_path,
        "BLOCKED: cannot proceed via chat API only.\n\nLast step: read orchestration.\nBlocker: no filesystem.",
    )

    assert ok
    assert reason is None


def test_deepseek_validation_rejects_ascii_command_plan(tmp_path: Path) -> None:
    ok, reason = _run_validation_case(
        tmp_path,
        "I'll start by creating the execution contract with STARTED.\n"
        "```bash\n"
        "echo \"STARTED\" > archive/team_artifacts/pkg/execution_contract.md\n"
        "cat archive/team_artifacts/pkg/orchestration_continue.md\n"
        "```",
    )

    assert not ok
    assert reason == "DeepSeek response looks like a command plan, not execution proof"


def test_deepseek_validation_accepts_substantive_execution_proof(tmp_path: Path) -> None:
    ok, reason = _run_validation_case(
        tmp_path,
        "EXECUTION_PROOF:\n\n"
        "Summary: Delivered the requested behavior.\n\n"
        "Changed files:\n"
        "- app/smart_study_router.py\n"
        "- tests/test_smart_study_router.py\n\n"
        "Verification:\n"
        "- .\\.venv\\Scripts\\python.exe -m pytest tests/test_smart_study_router.py -v --tb=short: PASS\n",
    )

    assert ok
    assert reason is None


def test_deepseek_validation_accepts_proof_after_plan_like_preamble(tmp_path: Path) -> None:
    """Reasoning models often prefix steps like «I'll read …»; gate must not reject valid proof."""
    ok, reason = _run_validation_case(
        tmp_path,
        "I'll read the orchestration file first, then apply edits.\n\n"
        "EXECUTION_PROOF:\n\n"
        "Summary: Done.\n\n"
        "Changed files:\n"
        "- app/foo.py\n\n"
        "Verification:\n"
        "- pytest tests/test_foo.py: PASS\n",
    )

    assert ok
    assert reason is None


def test_deepseek_validation_allows_no_tool_access_mention_in_verification(tmp_path: Path) -> None:
    ok, reason = _run_validation_case(
        tmp_path,
        "EXECUTION_PROOF:\n\n"
        "Changed files:\n"
        "- app/foo.py\n\n"
        "Verification:\n"
        "- Confirmed no tool access issues during pytest run.\n",
    )

    assert ok
    assert reason is None
