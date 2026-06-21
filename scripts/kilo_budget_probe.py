#!/usr/bin/env python3
"""Prepare and analyze Kilo budget/guard probes via the local relay log.

This script is intentionally split into two phases:
1. prepare  - reset relay log, start relay, and write narrow Kilo probe prompts
2. analyze  - inspect logs/kilo_relay.jsonl and build a forensic report

Kilo itself remains the QA harness for the budget/guard logic. The script
does not automate the Kilo GUI; instead it generates fresh-session probe
prompts with unique markers so the resulting relay traffic can be segmented.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "logs" / "kilo_relay.jsonl"
STATE_PATH = ROOT / "logs" / "kilo_budget_probe_state.json"
REPORT_PATH = ROOT / "logs" / "kilo_budget_probe_report.md"
PROMPTS_DIR = ROOT / "doc" / "kilo_budget_probes"
PYTHON_EXE = sys.executable or "python"


@dataclass(frozen=True)
class ProbeSpec:
    probe_id: str
    title: str
    prompt_text: str


PROBES: tuple[ProbeSpec, ...] = (
    ProbeSpec(
        probe_id="orch_launcher",
        title="Orchestration launcher path",
        prompt_text=(
            "[KILO-PROBE: ORCH-LAUNCHER]\n\n"
            "Проверка логики лимитов и budget guard только для orchestration launcher.\n\n"
            "Правила:\n"
            "1. Это fresh Kilo session. Не используй историю прошлых задач.\n"
            "2. Выполни только команду:\n"
            "   python scripts/generate_orchestration_prompt.py --agent kilo --budget-profile strict\n"
            "3. Дальше следуй только launcher-указанию из stdout.\n"
            "4. Не открывай backlog/history docs, если launcher не требует ровно один файл.\n"
            "5. Если read-set начинает расширяться или relay блокирует запрос, остановись.\n"
            "6. Цель: проверить pointer-only handoff и guard behavior, а не выполнить весь pipeline.\n"
        ),
    ),
    ProbeSpec(
        probe_id="planning_launcher",
        title="Planning launcher path",
        prompt_text=(
            "[KILO-PROBE: PLANNING-LAUNCHER]\n\n"
            "Проверка budget logic только для planning launcher.\n\n"
            "Правила:\n"
            "1. Это fresh Kilo session. Без reuse истории.\n"
            "2. Выполни только команду:\n"
            "   python scripts/generate_next_prompt.py --budget-profile strict\n"
            "3. Если команда вернёт launcher, работай только по указанному prompt file.\n"
            "4. Не открывай broad docs сверх launcher file.\n"
            "5. Если relay предупреждает или блокирует - остановись и коротко зафиксируй blocker.\n"
            "6. Цель: проверить, что planning path остаётся launcher-sized.\n"
        ),
    ),
    ProbeSpec(
        probe_id="autonomous_handoff",
        title="Autonomous Kilo handoff path",
        prompt_text=(
            "[KILO-PROBE: AUTONOMOUS-HANDOFF]\n\n"
            "Проверка Kilo handoff logic для run_autonomous.\n\n"
            "Правила:\n"
            "1. Это fresh Kilo session. Без истории прошлых workflow.\n"
            "2. Выполни только команду:\n"
            "   python scripts/run_autonomous.py --agent kilo --budget-profile strict\n"
            "3. После этого прочитай только `doc/current_task.md`.\n"
            "4. Выполни только первый указанный шаг handoff-а.\n"
            "5. Если task требует новый этап, planning или execution в отдельной сессии - остановись, не продолжай здесь.\n"
            "6. Не открывай backlog/history docs, если task явно не указывает ровно один файл.\n"
            "7. Цель: проверить, что Kilo path теперь разделён на fresh-session phases.\n"
        ),
    ),
)


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _reset_log() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("", encoding="utf-8")


def _relay_env(port: int, guard_mode: str) -> dict[str, str]:
    env = os.environ.copy()
    env["KILO_RELAY_PORT"] = str(port)
    env["KILO_RELAY_GUARD_MODE"] = guard_mode
    env.setdefault("KILO_RELAY_WARN_BODY_CHARS", "70000")
    env.setdefault("KILO_RELAY_MAX_BODY_CHARS", "90000")
    env.setdefault("KILO_RELAY_HARD_BLOCK_BODY_CHARS", "110000")
    env.setdefault("KILO_RELAY_MAX_MESSAGES", "8")
    env.setdefault("KILO_RELAY_MAX_LARGEST_MESSAGE_CHARS", "24000")
    env.setdefault("KILO_RELAY_MAX_TOOLS", "13")
    return env


def _start_relay(port: int, guard_mode: str) -> dict[str, Any]:
    stdout_path = ROOT / "logs" / "kilo_probe_relay.stdout.log"
    stderr_path = ROOT / "logs" / "kilo_probe_relay.stderr.log"
    stdout_fh = stdout_path.open("w", encoding="utf-8")
    stderr_fh = stderr_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [PYTHON_EXE, "scripts/kilo_proxy_relay.py"],
        cwd=str(ROOT),
        stdout=stdout_fh,
        stderr=stderr_fh,
        env=_relay_env(port, guard_mode),
    )
    time.sleep(1.2)
    return {
        "pid": proc.pid,
        "stdout_log": str(stdout_path.resolve()),
        "stderr_log": str(stderr_path.resolve()),
        "port": port,
        "guard_mode": guard_mode,
    }


def _stop_relay_if_known() -> bool:
    state = _load_state()
    pid = int(state.get("relay_pid") or 0)
    if pid <= 0:
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return False
    return True


def _write_probe_prompts(port: int) -> list[str]:
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for probe in PROBES:
        path = PROMPTS_DIR / f"{probe.probe_id}.md"
        text = (
            f"# {probe.title}\n\n"
            f"Relay base URL for this run: `http://127.0.0.1:{port}/v1`\n\n"
            f"{probe.prompt_text}"
        )
        path.write_text(text, encoding="utf-8")
        written.append(str(path.resolve()))
    return written


def cmd_prepare(args: argparse.Namespace) -> int:
    _stop_relay_if_known()
    if args.reset_log:
        _reset_log()
    relay = _start_relay(port=args.port, guard_mode=args.guard_mode)
    prompt_files = _write_probe_prompts(port=int(relay["port"]))
    state = {
        "prepared_at": time.time(),
        "relay_pid": relay["pid"],
        "relay_port": relay["port"],
        "guard_mode": relay["guard_mode"],
        "prompt_files": prompt_files,
        "log_path": str(LOG_PATH.resolve()),
    }
    _save_state(state)
    print(f"Relay started on http://127.0.0.1:{relay['port']}/v1")
    print(f"Guard mode: {relay['guard_mode']}")
    print(f"Relay log: {LOG_PATH.resolve()}")
    print("Probe prompts:")
    for prompt_file in prompt_files:
        print(f"  - {prompt_file}")
    print()
    print("Next step:")
    print("  Run each probe prompt in a separate fresh Kilo session.")
    print(f"  After all probes, run: {PYTHON_EXE} scripts/kilo_budget_probe.py analyze")
    return 0


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _match_probe_id(record: dict[str, Any]) -> str | None:
    request = record.get("request") or {}
    body_raw = str(request.get("body_raw") or "")
    for probe in PROBES:
        marker = f"[KILO-PROBE: {probe.probe_id.replace('_', '-').upper()}]"
        if marker in body_raw:
            return probe.probe_id
    return None


def _extract_contributor_name(message_stat: dict[str, Any]) -> str:
    summary = message_stat.get("summary") or {}
    preview_start = str(summary.get("preview_start") or "")
    if "<path>" in preview_start and "</path>" in preview_start:
        start = preview_start.find("<path>") + len("<path>")
        end = preview_start.find("</path>")
        if 0 <= start < end:
            return preview_start[start:end]
    role = message_stat.get("role") or "unknown"
    return f"{role} message #{message_stat.get('index', '?')}"


def _top_contributors(record: dict[str, Any], limit: int = 3) -> list[str]:
    request = record.get("request") or {}
    stats = request.get("message_stats") or []
    top = sorted(stats, key=lambda item: int(item.get("chars") or 0), reverse=True)[:limit]
    result: list[str] = []
    for item in top:
        name = _extract_contributor_name(item)
        chars = int(item.get("chars") or 0)
        result.append(f"{name} ({chars} chars)")
    return result


def _build_probe_summary(records: list[dict[str, Any]], probe_id: str) -> dict[str, Any]:
    matched = [r for r in records if _match_probe_id(r) == probe_id]
    if not matched:
        return {
            "probe_id": probe_id,
            "requests": 0,
            "max_body_chars": 0,
            "max_messages": 0,
            "levels": {},
            "blocked": 0,
            "risk_flags": [],
            "top_contributors": [],
        }
    max_record = max(matched, key=lambda r: int(((r.get("request") or {}).get("body_chars")) or 0))
    levels: dict[str, int] = {}
    blocked = 0
    all_flags: dict[str, int] = {}
    for record in matched:
        guard = record.get("guard") or {}
        level = str(guard.get("level") or "ok")
        levels[level] = levels.get(level, 0) + 1
        if guard.get("blocked") is True:
            blocked += 1
        for flag in guard.get("risk_flags") or []:
            all_flags[str(flag)] = all_flags.get(str(flag), 0) + 1
    return {
        "probe_id": probe_id,
        "requests": len(matched),
        "max_body_chars": int(((max_record.get("request") or {}).get("body_chars")) or 0),
        "max_messages": int(((max_record.get("request") or {}).get("messages_count")) or 0),
        "levels": levels,
        "blocked": blocked,
        "risk_flags": [k for k, _ in sorted(all_flags.items(), key=lambda item: (-item[1], item[0]))[:6]],
        "top_contributors": _top_contributors(max_record),
    }


def _global_recommendations(records: list[dict[str, Any]], probe_summaries: list[dict[str, Any]]) -> list[str]:
    recs: list[str] = []
    if any(summary["blocked"] > 0 for summary in probe_summaries):
        recs.append("Relay blocked at least one probe. Keep block mode enabled and narrow the offending handoff path.")
    if any(summary["max_body_chars"] > 90000 for summary in probe_summaries):
        recs.append("At least one probe exceeded the soft budget threshold. Keep Kilo on pointer-only handoffs and split phases into fresh sessions.")
    if any("planning prompt injected" in summary["risk_flags"] for summary in probe_summaries):
        recs.append("Planning prompt text is still reaching Kilo payloads. Prefer launcher-only outputs and fresh-session pivots.")
    if any("full backlog registry injected" in summary["risk_flags"] for summary in probe_summaries):
        recs.append("Backlog registry still enters Kilo payloads. Keep it out of GUI sessions and require a narrower handoff file.")
    if any(summary["max_messages"] > 8 for summary in probe_summaries):
        recs.append("Session history is still accumulating. Restart Kilo between planning, execution, and commit phases.")
    if not recs:
        recs.append("Current probe run stayed within guardrails. Keep relay in block mode and continue using fresh-session pointer-only workflow.")
    return recs


def _render_report(records: list[dict[str, Any]], probe_summaries: list[dict[str, Any]]) -> str:
    chat_records = [r for r in records if r.get("path") == "/v1/chat/completions"]
    if chat_records:
        max_record = max(chat_records, key=lambda r: int(((r.get("request") or {}).get("body_chars")) or 0))
        max_body = int(((max_record.get("request") or {}).get("body_chars")) or 0)
        max_messages = int(((max_record.get("request") or {}).get("messages_count")) or 0)
        max_level = str(((max_record.get("guard") or {}).get("level")) or "ok")
    else:
        max_body = 0
        max_messages = 0
        max_level = "n/a"
    lines = [
        "# Kilo Budget Probe Report",
        "",
        f"- Log file: `{LOG_PATH}`",
        f"- Chat requests: `{len(chat_records)}`",
        f"- Max body chars: `{max_body}`",
        f"- Max messages count: `{max_messages}`",
        f"- Max request guard level: `{max_level}`",
        "",
        "## Probe Results",
        "",
    ]
    for summary in probe_summaries:
        lines.append(f"### {summary['probe_id']}")
        lines.append(f"- Requests: `{summary['requests']}`")
        lines.append(f"- Blocked: `{summary['blocked']}`")
        lines.append(f"- Max body chars: `{summary['max_body_chars']}`")
        lines.append(f"- Max messages: `{summary['max_messages']}`")
        levels = ", ".join(f"{k}:{v}" for k, v in sorted(summary["levels"].items())) or "none"
        lines.append(f"- Guard levels: `{levels}`")
        if summary["risk_flags"]:
            lines.append(f"- Risk flags: `{'; '.join(summary['risk_flags'])}`")
        if summary["top_contributors"]:
            lines.append(f"- Top contributors: `{'; '.join(summary['top_contributors'])}`")
        if summary["requests"] == 0:
            lines.append("- Status: probe marker not found in relay log")
        lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for rec in _global_recommendations(records, probe_summaries):
        lines.append(f"- {rec}")
    lines.append("")
    return "\n".join(lines)


def cmd_analyze(args: argparse.Namespace) -> int:
    records = _read_jsonl(LOG_PATH)
    probe_summaries = [_build_probe_summary(records, probe.probe_id) for probe in PROBES]
    report = _render_report(records, probe_summaries)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print()
    print(f"Report saved: {REPORT_PATH}")
    return 0


def cmd_stop_relay(args: argparse.Namespace) -> int:
    stopped = _stop_relay_if_known()
    if stopped:
        print("Relay stop requested.")
    else:
        print("No known relay process to stop.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_prepare = sub.add_parser("prepare", help="Reset log, start relay, and write Kilo probe prompts")
    p_prepare.add_argument("--reset-log", action="store_true", default=True)
    p_prepare.add_argument("--port", type=int, default=8790)
    p_prepare.add_argument("--guard-mode", choices=("warn", "block"), default="block")
    p_prepare.set_defaults(func=cmd_prepare)

    p_analyze = sub.add_parser("analyze", help="Analyze relay log and build a Kilo probe report")
    p_analyze.set_defaults(func=cmd_analyze)

    p_stop = sub.add_parser("stop-relay", help="Stop relay process started by prepare")
    p_stop.set_defaults(func=cmd_stop_relay)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
