import os
import json
import sys
from pathlib import Path

from deepseek_tsx_support import requires_tsx, run_tsx_script

pytestmark = requires_tsx


def _run_tui_trigger(env: dict[str, str], *, timeout: float | None = None):
    script_path = Path("scripts/deepseek_tui_agent_trigger.ts").resolve()
    return run_tsx_script(script_path, env=env, cwd=Path.cwd(), timeout=timeout)


def test_deepseek_tui_trigger_success(tmp_path: Path):
    """
    Test that the TUI trigger can successfully spawn a process, read stream-json,
    and report success to the metrics file.
    """
    # 1. Create a fake deepseek.cmd
    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    fake_cmd = fake_bin_dir / "deepseek.py"
    success_json = (
        '{"type":"metadata","model":"deepseek-v4","input_tokens":100,"output_tokens":50,"status":"completed"}\\n'
        '{"type":"content","content":"Done."}\\n'
        '{"type":"done"}\\n'
    )
    fake_cmd.write_text(f'import sys\nprint("""{success_json}""")\n', encoding="utf-8")

    # 2. Set up environment
    env = os.environ.copy()
    env["DEEPSEEK_CLI_CMD"] = f'{sys.executable} {fake_cmd}'
    env["DEEPSEEK_API_KEY"] = "fake-key"
    env["DEEPSEEK_TUI_MAX_INPUT_TOKENS"] = "10000000" # avoid budget gate fail
    env["DEEPSEEK_MODEL"] = "deepseek-v4-test"
    
    # We need a fake execution contract so that _trigger_shared doesn't fail on missing EXECUTION_PROOF
    # Wait, the trigger wrapper itself validates the contract. If the child process doesn't write it,
    # the contract validator will fail.
    # Let's write the contract *before* calling the script, to fake that the agent wrote it.
    contract_path = tmp_path / "execution_contract.md"
    contract_path.write_text(
        "EXECUTION_PROOF:\n\nChanged files:\n- none\n\nVerification:\n- none\n", 
        encoding="utf-8"
    )

    # Set WORKFLOW_CURRENT_CONTRACT_PATH so the script checks our fake contract
    env["WORKFLOW_CURRENT_CONTRACT_PATH"] = str(contract_path)

    # 3. Create a unique metrics file for this test
    metrics_path = tmp_path / "trigger_metrics.jsonl"
    env["DEEPSEEK_TUI_TRIGGER_TRIGGER_METRICS_PATH"] = str(metrics_path)
    
    # We also need a fake current_task.md
    task_path = tmp_path / "current_task.md"
    task_path.write_text("Hello task", encoding="utf-8")
    env["WORKFLOW_CURRENT_TASK_PATH"] = str(task_path)

    # 4. Run the TS script
    result = _run_tui_trigger(env)

    # Note: process exits with 0 on success
    print("STDOUT:\n", result.stdout)
    print("STDERR:\n", result.stderr)
    if result.returncode != 0:
        if metrics_path.exists():
            print("METRICS:", metrics_path.read_text(encoding="utf-8"))
    assert result.returncode == 0

    # 5. Verify metrics
    assert metrics_path.exists()
    
    with open(metrics_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 1
        metric = json.loads(lines[0])
        assert metric["event"] == "deepseek_tui_agent_prompt"
        assert metric["status"] == "finished"
        assert metric["model"] == "deepseek-v4-test"
        assert metric["process_exit_code"] == 0


def test_deepseek_tui_trigger_session_error(tmp_path: Path):
    """
    Test that a stream-json error event causes the wrapper to exit with an error metric.
    """
    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    fake_cmd = fake_bin_dir / "deepseek.py"
    error_json = '{"type":"error","message":"Invalid API key"}\\n'
    fake_cmd.write_text(f'import sys\nprint("""{error_json}""")\n', encoding="utf-8")

    env = os.environ.copy()
    env["DEEPSEEK_CLI_CMD"] = f'{sys.executable} {fake_cmd}'
    env["DEEPSEEK_API_KEY"] = "fake-key"
    env["DEEPSEEK_TUI_MAX_INPUT_TOKENS"] = "10000000"

    metrics_path = tmp_path / "trigger_metrics.jsonl"

    env["DEEPSEEK_TUI_TRIGGER_TRIGGER_METRICS_PATH"] = str(metrics_path)
    
    task_path = tmp_path / "current_task.md"
    task_path.write_text("Hello task", encoding="utf-8")
    env["WORKFLOW_CURRENT_TASK_PATH"] = str(task_path)

    result = _run_tui_trigger(env)

    # Exits with 2 on agent failure (as per runTrigger contract)
    assert result.returncode == 2

    assert metrics_path.exists()
    
    with open(metrics_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 1
        metric = json.loads(lines[0])
        assert metric["event"] == "deepseek_tui_agent_prompt"
        assert metric["status"] == "error"


def test_deepseek_tui_pre_run_estimate_is_advisory(tmp_path: Path):
    """
    A pessimistic repository-size estimate must not block the trigger before the
    CLI reports actual stream metadata. The hard gate is enforced on input_tokens.
    """
    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    fake_cmd = fake_bin_dir / "deepseek.py"
    success_json = (
        '{"type":"metadata","model":"deepseek-v4","input_tokens":10,"output_tokens":5,"status":"completed"}\\n'
        '{"type":"content","content":"Done."}\\n'
        '{"type":"done"}\\n'
    )
    fake_cmd.write_text(f'import sys\nprint("""{success_json}""")\n', encoding="utf-8")

    env = os.environ.copy()
    env["DEEPSEEK_CLI_CMD"] = f'{sys.executable} {fake_cmd}'
    env["DEEPSEEK_API_KEY"] = "fake-key"
    env["DEEPSEEK_TUI_MAX_INPUT_TOKENS"] = "50"
    env["DEEPSEEK_TUI_WARN_INPUT_TOKENS"] = "25"
    env["DEEPSEEK_MODEL"] = "deepseek-v4-test"

    metrics_path = tmp_path / "trigger_metrics.jsonl"
    env["DEEPSEEK_TUI_TRIGGER_TRIGGER_METRICS_PATH"] = str(metrics_path)

    contract_path = tmp_path / "execution_contract.md"
    contract_path.write_text(
        "EXECUTION_PROOF:\n\nChanged files:\n- none\n\nVerification:\n- fake stream-json success\n",
        encoding="utf-8",
    )
    env["WORKFLOW_CURRENT_CONTRACT_PATH"] = str(contract_path)

    task_path = tmp_path / "current_task.md"
    task_path.write_text("Hello task", encoding="utf-8")
    env["WORKFLOW_CURRENT_TASK_PATH"] = str(task_path)

    result = _run_tui_trigger(env)

    print("STDOUT:\n", result.stdout)
    print("STDERR:\n", result.stderr)
    if result.returncode != 0 and metrics_path.exists():
        print("METRICS:", metrics_path.read_text(encoding="utf-8"))
    assert result.returncode == 0

    metric = json.loads(metrics_path.read_text(encoding="utf-8").splitlines()[0])
    assert metric["status"] == "finished"
    assert metric["input_tokens"] == 10
    assert metric["pre_run_token_estimate"] > 50


def test_deepseek_tui_missing_input_tokens_is_warning_not_budget_failure(tmp_path: Path):
    """
    Some DeepSeek CLI versions omit input_tokens from metadata. A completed
    session with a substantive proof should continue; the budget is unknown,
    not exceeded.
    """
    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    fake_cmd = fake_bin_dir / "deepseek.py"
    success_json = (
        '{"type":"metadata","model":"deepseek-v4","output_tokens":5,"status":"completed"}\\n'
        '{"type":"content","content":"Done."}\\n'
        '{"type":"done"}\\n'
    )
    fake_cmd.write_text(f'import sys\nprint("""{success_json}""")\n', encoding="utf-8")

    contract_path = tmp_path / "execution_contract.md"
    contract_path.write_text(
        "EXECUTION_PROOF:\n\nChanged files:\n- none\n\nVerification:\n- fake stream-json success\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["DEEPSEEK_CLI_CMD"] = f'{sys.executable} {fake_cmd}'
    env["DEEPSEEK_API_KEY"] = "fake-key"
    env["DEEPSEEK_TUI_MAX_INPUT_TOKENS"] = "50"
    env["DEEPSEEK_TUI_WARN_INPUT_TOKENS"] = "25"
    env["WORKFLOW_CURRENT_CONTRACT_PATH"] = str(contract_path)

    metrics_path = tmp_path / "trigger_metrics.jsonl"
    env["DEEPSEEK_TUI_TRIGGER_TRIGGER_METRICS_PATH"] = str(metrics_path)

    task_path = tmp_path / "current_task.md"
    task_path.write_text("Hello task", encoding="utf-8")
    env["WORKFLOW_CURRENT_TASK_PATH"] = str(task_path)

    result = _run_tui_trigger(env)

    print("STDOUT:\n", result.stdout)
    print("STDERR:\n", result.stderr)
    if result.returncode != 0 and metrics_path.exists():
        print("METRICS:", metrics_path.read_text(encoding="utf-8"))
    assert result.returncode == 0

    metric = json.loads(metrics_path.read_text(encoding="utf-8").splitlines()[0])
    assert metric["status"] == "finished"
    assert metric["budget_warning"] is True
    assert metric["budget_input_tokens_missing"] is True
    assert metric["budget_warning_reason"] == "input_tokens missing from metadata"
    assert "input_tokens" not in metric or metric["input_tokens"] is None


def test_deepseek_tui_trigger_rejects_started_contract_after_success(tmp_path: Path):
    """A completed TUI process is not enough; the proof must be substantive."""
    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    fake_cmd = fake_bin_dir / "deepseek.py"
    success_json = (
        '{"type":"metadata","model":"deepseek-v4","input_tokens":10,"output_tokens":5,"status":"completed"}\\n'
        '{"type":"content","content":"Done."}\\n'
        '{"type":"done"}\\n'
    )
    fake_cmd.write_text(f'import sys\nprint("""{success_json}""")\n', encoding="utf-8")

    contract_path = tmp_path / "execution_contract.md"
    contract_path.write_text("STARTED\n", encoding="utf-8")

    env = os.environ.copy()
    env["DEEPSEEK_CLI_CMD"] = f'{sys.executable} {fake_cmd}'
    env["DEEPSEEK_API_KEY"] = "fake-key"
    env["DEEPSEEK_TUI_MAX_INPUT_TOKENS"] = "10000000"
    env["WORKFLOW_CURRENT_CONTRACT_PATH"] = str(contract_path)

    metrics_path = tmp_path / "trigger_metrics.jsonl"
    env["DEEPSEEK_TUI_TRIGGER_TRIGGER_METRICS_PATH"] = str(metrics_path)

    task_path = tmp_path / "current_task.md"
    task_path.write_text("Hello task", encoding="utf-8")
    env["WORKFLOW_CURRENT_TASK_PATH"] = str(task_path)

    result = _run_tui_trigger(env)

    assert result.returncode == 2
    metric = json.loads(metrics_path.read_text(encoding="utf-8").splitlines()[0])
    assert metric["status"] == "invalid_contract"
    assert metric["invalid_contract_reason"] == "execution_contract_not_substantive"


def test_deepseek_tui_trigger_timeout_returns_control(tmp_path: Path):
    """Timeout must stop the heartbeat and return a structured rc=2 to orchestrator."""
    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    fake_cmd = fake_bin_dir / "deepseek.py"
    fake_cmd.write_text("import time\ntime.sleep(5)\n", encoding="utf-8")

    contract_path = tmp_path / "execution_contract.md"
    contract_path.write_text("STARTED\n", encoding="utf-8")

    env = os.environ.copy()
    env["DEEPSEEK_CLI_CMD"] = f'{sys.executable} {fake_cmd}'
    env["DEEPSEEK_API_KEY"] = "fake-key"
    env["DEEPSEEK_TUI_TIMEOUT_MS"] = "100"
    env["DEEPSEEK_TUI_TIMEOUT_KILL_GRACE_MS"] = "100"
    env["DEEPSEEK_TUI_TRIGGER_HEARTBEAT_MS"] = "0"
    env["WORKFLOW_CURRENT_CONTRACT_PATH"] = str(contract_path)

    metrics_path = tmp_path / "trigger_metrics.jsonl"
    env["DEEPSEEK_TUI_TRIGGER_TRIGGER_METRICS_PATH"] = str(metrics_path)

    task_path = tmp_path / "current_task.md"
    task_path.write_text("Hello task", encoding="utf-8")
    env["WORKFLOW_CURRENT_TASK_PATH"] = str(task_path)

    result = _run_tui_trigger(env, timeout=5)

    assert result.returncode == 2
    metric = json.loads(metrics_path.read_text(encoding="utf-8").splitlines()[0])
    assert metric["status"] == "error"
    assert metric["timed_out"] is True
    assert metric["error_reason"].startswith("timeout: exceeded")


def test_deepseek_tui_trigger_returns_when_contract_becomes_substantive(tmp_path: Path):
    """Once proof is ready, workflow should not wait for the TUI process to finish."""
    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    fake_cmd = fake_bin_dir / "deepseek.py"

    contract_path = tmp_path / "execution_contract.md"
    contract_path.write_text("STARTED\n", encoding="utf-8")
    contract_literal = repr(str(contract_path))
    fake_cmd.write_text(
        "import pathlib, time\n"
        f"path = pathlib.Path({contract_literal})\n"
        "time.sleep(0.2)\n"
        "path.write_text('EXECUTION_PROOF:\\n\\nChanged files:\\n- none\\n\\nVerification:\\n- proof-ready fast exit\\n', encoding='utf-8')\n"
        "time.sleep(5)\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["DEEPSEEK_CLI_CMD"] = f'{sys.executable} {fake_cmd}'
    env["DEEPSEEK_API_KEY"] = "fake-key"
    env["DEEPSEEK_TUI_PROOF_POLL_MS"] = "100"
    env["DEEPSEEK_TUI_TIMEOUT_KILL_GRACE_MS"] = "100"
    env["DEEPSEEK_TUI_TRIGGER_HEARTBEAT_MS"] = "0"
    env["WORKFLOW_CURRENT_CONTRACT_PATH"] = str(contract_path)

    metrics_path = tmp_path / "trigger_metrics.jsonl"
    env["DEEPSEEK_TUI_TRIGGER_TRIGGER_METRICS_PATH"] = str(metrics_path)

    task_path = tmp_path / "current_task.md"
    task_path.write_text("Hello task", encoding="utf-8")
    env["WORKFLOW_CURRENT_TASK_PATH"] = str(task_path)

    result = _run_tui_trigger(env, timeout=5)

    assert result.returncode == 0
    metric = json.loads(metrics_path.read_text(encoding="utf-8").splitlines()[0])
    assert metric["status"] == "finished"
    assert metric["proof_ready_return"] is True
    assert metric["timed_out"] is False
