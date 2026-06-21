#!/usr/bin/env python3
"""
Schema/consistency linter for doc/backlog_registry.yaml (PoC, schema v1).

Usage:
    python scripts/backlog_registry_lint.py
    python scripts/backlog_registry_lint.py --path doc/backlog_registry.yaml
    python scripts/backlog_registry_lint.py --ci

Exit codes:
    0 = OK
    1 = WARN (non-blocking issues, e.g. stale last_review)
    2 = FAIL (schema or consistency violation)

The registry feeds generate_plan_next_prompt.md Phase 2 candidate discovery.
Keep the schema minimal until consumers prove they need more.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _perf_timer import PhaseTimer  # noqa: E402
from prompt_utils import lint_active_package_pointer  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "doc" / "backlog_registry.yaml"
USER_STORIES_DIR = ROOT / "doc" / "user_stories"
USER_STORIES_INDEX_PATH = ROOT / "doc" / "user_stories_index.json"
TASKLIST_PATH = ROOT / "doc" / "tasklist.md"
CLOSED_ITERATIONS_PATH = ROOT / "doc" / "closed_iterations.md"
USER_STORIES_MD_PATH = ROOT / "doc" / "user_stories.md"
CJM_MD_PATH = ROOT / "doc" / "cjm.md"

ALLOWED_STATUS = {"proposed", "ready", "wip", "deferred", "closed"}
ALLOWED_IMPACT = {"loop-blocker", "loop-improvement", "infra", "eval", "dx"}
ALLOWED_COST = {"S", "M", "L"}
REQUIRED_KEYS = {"id", "status", "impact", "created", "last_review"}
SCHEMA_VERSION = 2  # current supported schema version (bumped from 1 in epoch-wave-contract)
_MIN_SCHEMA_VERSION = 1
US_FRONTMATTER_REQUIRED_KEYS = {
    "us_id",
    "epic",
    "priority",
    "cjm_stage",
    "status",
    "covered_by",
}
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}
RESUME_CARD_PACKAGE_ID = "epoch-us7-3-resume-card"
PAIN_POINT_BY_US = {
    "US-2.5": "Source readiness diagnostics lack a stable API contract and explicit failure categories",
    "US-11.2": "Retrieval confidence can be mistaken for probability of truth",
    "US-12.7": "Quality claims are not tied to a reproducible defense eval run",
    "US-12.8": "Slow or expensive answers cannot be explained by pipeline stage",
    "US-12.9": "Mastery and graduation claims are not validated against learning outcomes",
    "US-12.10": "RAG adversarial failures are not measured against retrieved documents",
    "US-12.11": "Local-first privacy claims lack deletion verification and cloud-boundary docs",
    "US-1.1": "Понять, для чего нужен hometutor",
    "US-1.2": "Stack trace / пустой экран / missing env",
    "US-1.3": "Неочевидные обязательные env-переменные",
    "US-2.1": "Не вижу прогресс первой индексации",
    "US-2.2": "Долгая переиндексация вместо инкрементальной",
    "US-3.1": "\"Не нашёл информации\" на тривиальный вопрос",
    "US-3.2": "Не понимаю, почему фрагмент попал в ответ",
    "US-3.3": "Пустой экран без примеров вопросов",
    "US-3.4": "\"Не нашёл информации\" на тривиальный вопрос",
    "US-3.5": "Субъективно долгое или непрозрачное ожидание первого ответа",
    "US-3.6": "Полная генерация при уже достаточном retrieval-покрытии (лишняя стоимость/латентность)",
    "US-4.1": "Тьютор стартует с нуля, забывая тему",
    "US-4.2": "Learner не понимает решений тьютора",
    "US-5.1": "Fail без объяснения / вопрос не по теме",
    "US-5.2": "Fail без объяснения / вопрос не по теме",
    "US-6.1": "Нет плана на сегодня после первой сессии",
    "US-6.2": "Непонятно, что изменилось в плане",
    "US-6.3": "Слишком много due — нужен recovery-режим",
    "US-7.1": "50+ overdue без приоритизации",
    "US-7.2": "50+ overdue — нужен план восстановления",
    "US-7.3": "\"Где я был вчера?\" — нет resume card",
    "US-7.4": "50+ overdue без приоритизации",
    "US-8.1": "Mastery обнуляется / история теряется",
    "US-8.2": "Mastery обнуляется / история теряется",
    "US-9.1": "Метрики разбросаны",
    "US-9.2": "Нет ощущения завершения",
    "US-10.1": "Нет простого backup/restore обучения",
    "US-10.2": "Нет понятного restore wizard на новой машине",
    "US-10.3": "Нет понятной multi-device политики синка",
    "US-11.1": "SRS не напоминает вовремя / нет due-очереди",
    "US-12.1": "Backup/import не гарантирует вставку данных",
    "US-12.2": "Drift/линт ломают planning-цикл",
    "US-12.3": "Backup benchmark не даёт уверенности в восстановлении",
    "US-12.4": "Нет воспроизводимого accuracy baseline роутера",
    "US-13.1": "После reindex ломается quiz/контракты",
    "US-14.1": "10 равных действий вместо одного next step",
    "US-14.2": "10 равных действий вместо одного next step",
    "US-14.3": "10 равных действий вместо одного next step",
    "US-14.4": "10 равных действий вместо одного next step",
    "US-15.1": "Карточки без preview / course scope",
    "US-15.2": "Нет summary после сессии",
    "US-15.3": "Нельзя управлять колодами/карточками в UI",
    "US-15.4": "Нет экспорта колоды в Anki",
    "US-15.5": "Нет загрузки файла для генерации карточек",
    "US-15.6": "Нельзя создать колоду из квиза",
    "US-16.0": "Нельзя изолировать scope по конкретному курсу",
    "US-16.1": "Нельзя изолировать scope по конкретному курсу",
    "US-16.2": "Нельзя изолировать scope по конкретному курсу",
    "US-16.3": "Нельзя изолировать scope по конкретному курсу",
    "US-16.4": "Нельзя изолировать scope по конкретному курсу",
    "US-16.5": "Нельзя изолировать scope по конкретному курсу",
    "US-16.6": "Нельзя изолировать scope по конкретному курсу",
    "US-16.7": "Ручная навигация между табами ломает поток: ДЗ и плейбук вне Course Mode",
    "US-17.1": "Course mode: нет диагностического старта",
    "US-17.2": "Course cockpit: нет единого entry surface",
    "US-17.3": "Course pace: нет режима Steady/Deep",
    "US-17.4": "Course rotation: нет rotator/policy переходов",
    "US-17.5": "Нет явного graduation overlay",
    "US-17.6": "Нет daily briefing/debrief в course режиме",
    "US-17.7": "Нет focus-mode / deep work цикла",
    "US-17.8": "Нет smart resume в course режиме",
    "US-17.9": "Нет course graduation/knowledge vault",
    "US-17.10": "Нет daily runway микро-цели",
    "US-17.11": "Нет retrieval-gates между модулями плана",
}


_CLOSED_BASELINE_STORY_MARKER = "closed baseline story"


def _allows_empty_user_stories(entry: dict[str, Any]) -> bool:
    if entry.get("impact") == "infra":
        return True
    notes = str(entry.get("notes") or "").lower()
    return _CLOSED_BASELINE_STORY_MARKER in notes


def _load_closed_package_ids() -> set[str]:
    closed_ids: set[str] = set()
    markdown_sources = [TASKLIST_PATH, CLOSED_ITERATIONS_PATH]
    table_pattern = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`closed`", re.MULTILINE)
    inline_pattern = re.compile(r"`([A-Za-z0-9][A-Za-z0-9._/-]*)`")

    for path in markdown_sources:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        closed_ids.update(table_pattern.findall(text))

        # closed_iterations.md stores historical package ids outside a Truth View table,
        # so accept inline backticked epoch ids there as known-closed references.
        if path == CLOSED_ITERATIONS_PATH:
            for package_id in inline_pattern.findall(text):
                if package_id.startswith(("epoch-", "E")):
                    closed_ids.add(package_id)

    return closed_ids


def _parse_frontmatter(path: Path) -> dict[str, Any] | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    closing = text.find("\n---\n", 4)
    if closing == -1:
        return None
    block = text[4:closing]
    if yaml is not None:
        parsed = yaml.safe_load(block)
        return parsed if isinstance(parsed, dict) else None

    parsed_fallback: dict[str, Any] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        parsed_fallback[key.strip()] = _parse_scalar(raw_value.strip())
    return parsed_fallback


def _normalize_coverage_value(value: Any) -> str:
    if value is None:
        return "open"
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "open"


def _coverage_tokens(value: Any) -> list[str]:
    normalized = _normalize_coverage_value(value)
    if normalized == "open":
        return []
    return [token.strip() for token in normalized.split("/") if token.strip()]


def _load_user_story_index(index_path: Path, errors: list[str]) -> dict[str, dict[str, Any]]:
    if not index_path.is_file():
        _fail(errors, f"user_stories_index not found at {index_path.relative_to(ROOT)}")
        return {}
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        _fail(errors, f"user_stories_index JSON parse error: {exc}")
        return {}

    items = payload.get("items")
    if not isinstance(items, list):
        _fail(errors, "user_stories_index: 'items' must be a list")
        return {}

    stories_by_id: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            _fail(errors, f"user_stories_index item must be a mapping: {item!r}")
            continue
        us_id = item.get("us_id")
        if not isinstance(us_id, str) or not us_id.strip():
            _fail(errors, f"user_stories_index item missing valid us_id: {item!r}")
            continue
        stories_by_id[us_id] = item
    return stories_by_id


def _load_user_story_index_payload(index_path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not index_path.is_file():
        _fail(errors, f"user_stories_index not found at {index_path.relative_to(ROOT)}")
        return None
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        _fail(errors, f"user_stories_index JSON parse error: {exc}")
        return None
    if not isinstance(payload, dict):
        _fail(errors, "user_stories_index: top-level JSON must be object")
        return None
    items = payload.get("items")
    if not isinstance(items, list):
        _fail(errors, "user_stories_index: 'items' must be a list")
        return None
    return payload


def _parse_scalar(value: str) -> Any:
    value = value.split("  #", 1)[0].strip()
    if value in {"null", "None"}:
        return None
    if value == "[]":
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if value.isdigit():
        return int(value)
    return value


def _replace_section(text: str, start_header: str, end_marker: str, new_block: str) -> str:
    if end_marker.startswith("#"):
        end_title = end_marker.lstrip("#").strip()
        end_pattern = rf"^###?\s+{re.escape(end_title)}\n"
    elif end_marker == "---":
        end_pattern = r"^---\n"
    else:
        end_pattern = rf"^###?\s+{re.escape(end_marker)}\n"
    pattern = re.compile(rf"(?ms)^###?\s+{re.escape(start_header)}\n.*?(?={end_pattern})")
    return pattern.sub(new_block.rstrip() + "\n\n", text, count=1)


def _upsert_contracts_in_now(tasklist_text: str, contracts_block: str) -> str:
    """Insert/replace contract blocks inside generated active section of tasklist.md.

    Contract blocks are `### <id> Contract` headers.  For each block in
    contracts_block we either replace an existing block (same header) or
    insert it before the Wave queue subsection (or at end of the generated active section).
    If no generated active section is found, returns text unchanged.
    """
    import re as _re
    now_match = _re.search(r"(?ms)^## Now\s*\n(?P<body>.*?)(?=^## |\Z)", tasklist_text)
    if not now_match:
        return tasklist_text

    now_start = now_match.start("body")
    now_end = now_match.end("body")
    now_body = tasklist_text[now_start:now_end]

    # Parse individual contract blocks from contracts_block
    contract_headers = _re.findall(r"^### (.+ Contract)", contracts_block, _re.MULTILINE)
    for header_title in contract_headers:
        # Extract this specific contract block text from contracts_block
        block_match = _re.search(
            rf"(?ms)^### {_re.escape(header_title)}\n.*?(?=^### |\Z)",
            contracts_block,
        )
        if not block_match:
            continue
        new_block = block_match.group(0).rstrip()
        # Replace existing or insert before Wave queue
        existing = _re.search(
            rf"(?ms)^### {_re.escape(header_title)}\n.*?(?=^### |\Z)",
            now_body,
        )
        if existing:
            now_body = now_body[:existing.start()] + new_block + "\n\n" + now_body[existing.end():]
        else:
            wave_queue_m = _re.search(r"^### Wave queue", now_body, _re.MULTILINE)
            if wave_queue_m:
                now_body = (
                    now_body[:wave_queue_m.start()]
                    + new_block + "\n\n"
                    + now_body[wave_queue_m.start():]
                )
            else:
                now_body = now_body.rstrip() + "\n\n" + new_block + "\n\n"

    return tasklist_text[:now_start] + now_body + tasklist_text[now_end:]


def _strip_registry_generated_contracts(now_body: str) -> str:
    """Drop ``### … Contract`` blocks that were rendered from the registry (GENERATED marker).

    Removes stale blocks anywhere under ``## Now`` (e.g. after a package closed) even when
    section replacements left an orphan layout. Manual contract blocks without the marker
    are kept.
    """
    import re as _re

    mark = "<!-- GENERATED from backlog_registry.yaml"
    pattern = _re.compile(
        r"(?ms)^(?P<head>(?-s:### .+ Contract\n))(?P<body>.*?)(?=^(?:###|## )|\Z)",
    )

    def repl(match: _re.Match[str]) -> str:
        block = match.group("head") + match.group("body")
        return "" if mark in block else block

    collapsed = pattern.sub(repl, now_body)
    return _re.sub(r"\n{3,}", "\n\n", collapsed)


def _reconcile_generated_contracts_in_now(tasklist_text: str, contracts_rendered: str) -> str:
    """Remove stale registry-rendered contracts under ``## Now``, then insert current active set."""
    import re as _re

    now_match = _re.search(r"(?ms)^## Now\s*\n(?P<body>.*?)(?=^## |\Z)", tasklist_text)
    if not now_match:
        return tasklist_text
    stripped = _strip_registry_generated_contracts(now_match.group("body"))
    tasklist_text = (
        tasklist_text[: now_match.start("body")] + stripped + tasklist_text[now_match.end("body") :]
    )
    if (contracts_rendered or "").strip():
        tasklist_text = _upsert_contracts_in_now(tasklist_text, contracts_rendered)
    return tasklist_text


def _render_open_candidates(items: list[dict[str, Any]]) -> str:
    open_items = [item for item in items if item.get("status") == "open"]
    open_items.sort(
        key=lambda item: (
            PRIORITY_ORDER.get(str(item.get("priority")), 99),
            str(item.get("cjm_stage")),
            str(item.get("us_id")),
        ),
    )
    top_items = open_items[:8]
    lines = [
        "## Open candidates",
        "",
        "<!-- GENERATED: user_stories_index.open_candidates (do not edit manually) -->",
        "",
        "Machine-readable shortlist for planning. Full status/coverage lives in `doc/user_stories_index.json`.",
        "",
        "| Rank | Story | CJM | Coverage | Why now |",
        "|---|---|---|---|---|",
    ]
    for rank, item in enumerate(top_items, start=1):
        lines.append(
            (
                f"| {rank} | `{item['us_id']}` - {item['title']} | {item['cjm_stage']} | "
                f"`{_normalize_coverage_value(item.get('covered_by'))}` | "
                f"{item['priority']} candidate from index |"
            ),
        )
    return "\n".join(lines)


def _render_coverage_index(items: list[dict[str, Any]]) -> str:
    lines = [
        "## Coverage-aware index view",
        "",
        "<!-- GENERATED: user_stories_index.items (do not edit manually) -->",
        "",
        "Полные INVEST-формулировки и acceptance criteria вынесены по одной US в `doc/user_stories/`.",
        "`Coverage` — это package id из `covered_by`; для незакрытых US используется `open`.",
        "",
        "| Epic | Story | Priority | Status | Coverage | Details |",
        "|---|---|---|---|---|---|",
    ]
    sorted_items = sorted(items, key=lambda item: (int(item.get("epic", 999)), str(item.get("us_id"))))
    for item in sorted_items:
        coverage = _normalize_coverage_value(item.get("covered_by"))
        lines.append(
            (
                f"| {item['epic_name']} | `{item['us_id']}` - {item['title']} | `{item['priority']}` | "
                f"`{item['status']}` | `{coverage}` | [`details`](user_stories/{item['us_id'].lower()}.md) |"
            ),
        )
    return "\n".join(lines)


def _render_cjm_section_8(items: list[dict[str, Any]]) -> str:
    by_id = {item["us_id"]: item for item in items if isinstance(item, dict) and "us_id" in item}
    rows: list[str] = []
    for us_id, pain in PAIN_POINT_BY_US.items():
        item = by_id.get(us_id)
        if item is None:
            continue
        status = str(item.get("status"))
        coverage = _normalize_coverage_value(item.get("covered_by"))
        package_status = "open" if status == "open" else f"closed:{coverage}"
        rows.append(f"| {pain} | `{us_id}` | `{package_status}` |")

    lines = [
        "## 8. CJM pain table для planning automation (`infra`)",
        "",
        "<!-- GENERATED: user_stories_index.items + pain map (do not edit manually) -->",
        "",
        "| Pain point | US | package_status |",
        "|---|---|---|",
        *rows,
    ]
    return "\n".join(lines)


def get_active_wave(registry_data: dict[str, Any]) -> str | None:
    """Return the active wave id from registry_data.

    Priority: explicit active_wave_id field → first wip wave → first ready wave
    → first proposed wave.  Never returns a completed/frozen wave.
    Never reads tasklist.md — only registry YAML.
    """
    explicit = registry_data.get("active_wave_id")
    if explicit:
        waves = registry_data.get("waves") or []
        w = next((w for w in waves if isinstance(w, dict) and w.get("id") == explicit), None)
        if w and str(w.get("status", "")).strip().lower() not in ("completed", "frozen"):
            return str(explicit)

    waves = registry_data.get("waves") or []
    for target_status in ("wip", "ready", "proposed"):
        matched = [w for w in waves if isinstance(w, dict) and str(w.get("status", "")).strip().lower() == target_status]
        if matched:
            return str(matched[0]["id"])
    return None


def _render_truth_view(registry_data: dict[str, Any]) -> str:
    lines = [
        "### Truth View",
        "",
        "<!-- GENERATED: tasklist.truth_view (do not edit manually) -->",
        "",
        "| Package | Status | CJM | Primary US | Owner | Notes |",
        "|---|---|---|---|---|---|",
    ]
    items = registry_data.get("items", [])
    active_items = [item for item in items if isinstance(item, dict) and str(item.get("status", "")).strip().lower() in ("wip", "ready")]
    # Registry must keep len(active_items) <= 1 — enforced post-sync by roadmap_sync_check.py
    # ( Truth View invariant in doc/backlog_registry.yaml header ).
    # Put wip first, then ready
    active_items.sort(key=lambda x: (str(x.get("status", "")).strip().lower() != "wip", x.get("id", "")))
    
    for item in active_items:
        cjm = ", ".join(item.get("cjm_moments", [])) or "-"
        us = ", ".join(item.get("user_stories", [])) or "-"
        notes = str(item.get("notes") or "").replace("\n", " ")
        lines.append(f"| `{item.get('id')}` | `{item.get('status')}` | {cjm} | {us} | Auto | {notes} |")
    
    return "\n".join(lines)


def _render_wave_queue(registry_data: dict[str, Any]) -> str:
    lines = [
        "### Wave queue",
        "",
        "<!-- GENERATED: tasklist.wave_queue (do not edit manually) -->",
        "",
    ]
    waves = registry_data.get("waves", [])
    if not waves:
        lines.append("No active waves.")
        return "\n".join(lines)

    # Active wave selection priority:
    # 1) first wip wave
    # 2) first ready wave
    # 3) first proposed wave
    # Never fall back to completed/frozen as active.
    wip_waves = [w for w in waves if isinstance(w, dict) and str(w.get("status", "")).strip().lower() == "wip"]
    ready_waves = [w for w in waves if isinstance(w, dict) and str(w.get("status", "")).strip().lower() == "ready"]
    proposed_waves = [w for w in waves if isinstance(w, dict) and str(w.get("status", "")).strip().lower() == "proposed"]
    active_wave = (
        wip_waves[0]
        if wip_waves
        else ready_waves[0]
        if ready_waves
        else proposed_waves[0]
        if proposed_waves
        else None
    )
    
    if active_wave:
        active_wave_id = active_wave.get("id", "")
        lines.append(f"<!-- ACTIVE_WAVE: {active_wave_id} -->")
        lines.append(f"- **Active wave:** `{active_wave_id}`")
        lines.append("- **Queued (same wave):**")
        for pkg in active_wave.get("packages", []):
            lines.append(f"  - `{pkg}`")
    else:
        lines.append("<!-- ACTIVE_WAVE: none -->")
        lines.append("- **Active wave:** None")
        lines.append("- **Queued (same wave):** None")

    lines.append("- **Queued (other waves):**")
    for w in waves:
        if isinstance(w, dict) and w != active_wave and str(w.get("status", "")).strip().lower() in ("proposed", "ready"):
            pkgs = ", ".join(f"`{p}`" for p in w.get("packages", []))
            lines.append(f"- `{w.get('id')}`: {pkgs}")
            if w.get("kill_switch"):
                lines.append(f"  - Kill switch: {w.get('kill_switch')}")
                
    if active_wave and active_wave.get("north_star"):
        lines.append(f"- **North star:** {active_wave.get('north_star')}")
    if active_wave and active_wave.get("kill_switch"):
        lines.append(f"- **Kill switch:** {active_wave.get('kill_switch')}")
        
    return "\n".join(lines)


def _render_active_contracts(registry_data: dict[str, Any]) -> str:
    """Render contract blocks for all active (ready/wip) packages from registry.

    Produces one ### <id> Contract block per active item, sourcing real
    dod_commands, outcomes, and read_set_hint from yaml — never from tasklist.md.
    """
    items = registry_data.get("items", []) or []
    active_items = [
        item for item in items
        if isinstance(item, dict) and str(item.get("status", "")).strip().lower() in ("wip", "ready")
    ]
    if not active_items:
        return ""

    blocks = []
    for item in active_items:
        full_id = str(item.get("id", ""))
        cid = full_id  # use full id so parse_contract can find the block
        us_list = ", ".join(item.get("user_stories", []) or []) or "n/a"
        cjm = ", ".join(item.get("cjm_moments", []) or []) or "unknown"
        outcomes_raw = str(item.get("blocks") or item.get("exit_artifact") or item.get("notes") or "(see registry)")
        read_set = item.get("read_set_hint") or []
        if isinstance(read_set, str):
            read_set = [read_set]
        read_hint = "\n".join(f"  - {r}" for r in read_set) if read_set else "  - (see backlog_registry.yaml)"
        notes = str(item.get("notes") or "")
        notes_line = f"\n- **Notes:** {notes}" if notes else ""

        dod_cmds = item.get("dod_commands", []) or []
        if isinstance(dod_cmds, str):
            dod_cmds = [dod_cmds]
        if dod_cmds:
            inner = "\n".join(f"  {cmd}" for cmd in dod_cmds)
            dod_formatted = f"  ```\n{inner}\n  ```"
        else:
            dod_formatted = "  (fill in dod_commands in backlog_registry.yaml)"

        policy_marker = "  - allow_verification_only\n" if item.get("allow_verification_only") else ""
        block = (
            f"### {cid} Contract\n\n"
            f"<!-- GENERATED from backlog_registry.yaml — do not edit manually -->\n\n"
            f"- **Title:** {outcomes_raw[:120]}\n"
            f"- **CJM:** #{cjm}\n"
            f"- **User story:** {us_list}\n"
            f"- **DoD commands:**\n{dod_formatted}\n"
            f"- **Outcomes:**\n"
            f"{policy_marker}"
            f"  - {outcomes_raw}\n"
            f"- **Write-set max:** {item.get('write_set_max', 5)} files\n"
            f"- **Target artifacts:** {item.get('exit_artifact') or outcomes_raw[:80]}\n"
            f"- **Read-set hint:**\n{read_hint}{notes_line}"
        )
        blocks.append(block)
    return "\n\n".join(blocks)


def _render_recent_closed() -> str:
    lines = [
        "### Recent closed references",
        "",
        "<!-- GENERATED: tasklist.recent_closed (do not edit manually) -->",
        "",
    ]
    
    closed_items = []
    if CLOSED_ITERATIONS_PATH.is_file():
        text = CLOSED_ITERATIONS_PATH.read_text(encoding="utf-8")
        # Match lines like "### <id> — <date>"
        pattern = re.compile(r"^### ([a-zA-Z0-9][a-zA-Z0-9._/-]+) — ([0-9]{4}-[0-9]{2}-[0-9]{2})", re.MULTILINE)
        for match in pattern.finditer(text):
            closed_items.append((match.group(1), match.group(2)))
            if len(closed_items) >= 10:
                break
                
    for pkg_id, date in closed_items:
        lines.append(f"- `{pkg_id}` закрыт {date}; см. `doc/closed_iterations.md`.")
        
    lines.append("- Более ранние закрытия, audit-corrections и архивные детали: `doc/closed_iterations.md` и `archive/team_artifacts/*`.")
    return "\n".join(lines)


def _render_deferred(registry_data: dict[str, Any]) -> str:
    lines = [
        "## Deferred",
        "",
        "<!-- GENERATED: tasklist.deferred (do not edit manually) -->",
        "",
        "| Item | Re-entry condition | Last review |",
        "|-----|--------------------|-------------|",
    ]
    items = registry_data.get("items", [])
    deferred_items = [item for item in items if isinstance(item, dict) and str(item.get("status", "")).strip().lower() == "deferred"]
    for item in deferred_items:
        re_entry = str(item.get("re_entry_condition") or "").replace("\n", " ")
        last_review = item.get("last_review", "")
        if isinstance(last_review, date):
            last_review = last_review.isoformat()
        lines.append(f"| `{item.get('id')}` | {re_entry} | {last_review} |")
        
    return "\n".join(lines)


def _compute_open_candidates(items: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    open_items = [item for item in items if str(item.get("status", "")).strip().lower() == "open"]
    open_items.sort(
        key=lambda item: (
            PRIORITY_ORDER.get(str(item.get("priority")), 99),
            str(item.get("cjm_stage")),
            str(item.get("us_id")),
        ),
    )
    result: list[dict[str, Any]] = []
    for rank, item in enumerate(open_items[:limit], start=1):
        result.append(
            {
                "rank": rank,
                "us_id": item["us_id"],
                "title": item["title"],
                "priority": item["priority"],
                "cjm_stage": item["cjm_stage"],
                "status": item["status"],
                "coverage": _normalize_coverage_value(item.get("covered_by")),
                "pain_point": PAIN_POINT_BY_US.get(item["us_id"]),
            },
        )
    return result


def sync_docs_from_index(index_path: Path, write: bool = False, registry_data: dict[str, Any] | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    payload = _load_user_story_index_payload(index_path, errors)
    if payload is None:
        return errors, warnings
    original_payload = copy.deepcopy(payload)

    items = [item for item in payload["items"] if isinstance(item, dict)]
    payload["generated"] = date.today().isoformat()
    payload["open_candidates"] = _compute_open_candidates(items)
    index_next = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    index_prev = json.dumps(original_payload, ensure_ascii=False, indent=2) + "\n"
    if write:
        index_path.write_text(index_next, encoding="utf-8")
    elif index_next != index_prev:
        _fail(
            errors,
            (
                f"{index_path.relative_to(ROOT)} is out of sync with generated metadata; "
                "run backlog_registry_lint.py --sync-from-index --write-sync"
            ),
        )

    if not USER_STORIES_MD_PATH.is_file():
        _fail(errors, f"user stories markdown not found at {USER_STORIES_MD_PATH.relative_to(ROOT)}")
        return errors, warnings
    user_stories_text = USER_STORIES_MD_PATH.read_text(encoding="utf-8")
    user_stories_text = _replace_section(
        user_stories_text,
        "Open candidates",
        "Coverage-aware index view",
        _render_open_candidates(items),
    )
    user_stories_text = _replace_section(
        user_stories_text,
        "Coverage-aware index view",
        "Связи",
        _render_coverage_index(items),
    )
    if write:
        USER_STORIES_MD_PATH.write_text(user_stories_text, encoding="utf-8")
    else:
        current_text = USER_STORIES_MD_PATH.read_text(encoding="utf-8")
        if user_stories_text != current_text:
            _fail(
                errors,
                (
                    f"{USER_STORIES_MD_PATH.relative_to(ROOT)} is out of sync with user_stories_index.json; "
                    "run backlog_registry_lint.py --sync-from-index --write-sync"
                ),
            )

    if not CJM_MD_PATH.is_file():
        _fail(errors, f"cjm markdown not found at {CJM_MD_PATH.relative_to(ROOT)}")
        return errors, warnings
    cjm_text = CJM_MD_PATH.read_text(encoding="utf-8")
    cjm_text = _replace_section(
        cjm_text,
        "8. CJM pain table для planning automation (`infra`)",
        "---",
        _render_cjm_section_8(items),
    )
    if write:
        CJM_MD_PATH.write_text(cjm_text, encoding="utf-8")
    else:
        current_text = CJM_MD_PATH.read_text(encoding="utf-8")
        if cjm_text != current_text:
            _fail(
                errors,
                (
                    f"{CJM_MD_PATH.relative_to(ROOT)} is out of sync with user_stories_index.json; "
                    "run backlog_registry_lint.py --sync-from-index --write-sync"
                ),
            )
            
    if registry_data and TASKLIST_PATH.is_file():
        tasklist_text = TASKLIST_PATH.read_text(encoding="utf-8")
        tasklist_text = _replace_section(
            tasklist_text,
            "Truth View",
            "Wave queue",
            _render_truth_view(registry_data),
        )
        tasklist_text = _replace_section(
            tasklist_text,
            "Wave queue",
            "Recent closed references",
            _render_wave_queue(registry_data),
        )
        tasklist_text = _replace_section(
            tasklist_text,
            "Recent closed references",
            "Maintenance (compact)",
            _render_recent_closed(),
        )
        tasklist_text = _replace_section(
            tasklist_text,
            "Deferred",
            "Архив Roadmap",
            _render_deferred(registry_data),
        )
        # Render active contract blocks from registry into the generated active section.
        contracts_rendered = _render_active_contracts(registry_data)
        tasklist_text = _reconcile_generated_contracts_in_now(tasklist_text, contracts_rendered)
        if write:
            TASKLIST_PATH.write_text(tasklist_text, encoding="utf-8")
        else:
            current_text = TASKLIST_PATH.read_text(encoding="utf-8")
            if tasklist_text != current_text:
                _fail(
                    errors,
                    (
                        f"{TASKLIST_PATH.relative_to(ROOT)} is out of sync with generated blocks; "
                        "run backlog_registry_lint.py --sync-from-index --write-sync"
                    ),
                )

    return errors, warnings


def _load_registry_text(text: str) -> dict[str, Any]:
    if yaml is not None:
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            raise ValueError("top-level YAML must be a mapping with schema_version + items")
        return data

    # Tiny fallback for the registry subset used here: top-level schema_version
    # plus a list of flat item mappings with optional scalar lists.
    data: dict[str, Any] = {}
    items: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_list_key: str | None = None
    in_items = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith(" ") and ":" in stripped:
            key, raw_value = stripped.split(":", 1)
            if key == "items":
                in_items = True
                data["items"] = items
                continue
            data[key] = _parse_scalar(raw_value)
            continue
        if in_items and stripped.startswith("- "):
            payload = stripped[2:]
            if ":" in payload:
                key, raw_value = payload.split(":", 1)
                current = {key: _parse_scalar(raw_value)}
                items.append(current)
                current_list_key = None
            elif current is not None and current_list_key:
                current[current_list_key].append(_parse_scalar(payload))
            continue
        if in_items and current is not None and ":" in stripped:
            key, raw_value = stripped.split(":", 1)
            if raw_value.strip() == "":
                current[key] = []
                current_list_key = key
            else:
                current[key] = _parse_scalar(raw_value)
                current_list_key = None

    return data


def _fail(errors: list[str], msg: str) -> None:
    errors.append(msg)


def _warn(warnings: list[str], msg: str) -> None:
    warnings.append(msg)


def _compute_registry_active_package_id(data: dict[str, Any]) -> str | None:
    ids = [
        str(entry.get("id"))
        for entry in data.get("items") or []
        if isinstance(entry, dict)
        and str(entry.get("status", "")).strip().lower() in {"ready", "wip"}
        and entry.get("id")
    ]
    if len(ids) != 1:
        return None
    return ids[0]


def patch_registry_active_package_id(registry_path: Path, data: dict[str, Any]) -> bool:
    """Keep top-level ``active_package_id`` aligned with the sole ready/wip package (if any)."""
    desired = _compute_registry_active_package_id(data)
    line = f"active_package_id: {desired}" if desired else "active_package_id: null"
    try:
        text = registry_path.read_text(encoding="utf-8")
    except OSError:
        return False
    if re.search(r"^active_package_id:\s*", text, flags=re.MULTILINE):
        new_text = re.sub(r"^active_package_id:\s*.*$", line, text, count=1, flags=re.MULTILINE)
    elif re.search(r"^active_wave_id:\s*", text, flags=re.MULTILINE):
        new_text = re.sub(
            r"(^active_wave_id:\s*.*$)",
            rf"\1\n{line}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        new_text = re.sub(
            r"(^schema_version:\s*.*$)",
            rf"\1\n{line}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    if new_text != text:
        registry_path.write_text(new_text, encoding="utf-8")
        return True
    return False


def _parse_date(value: Any, field: str, item_id: str, errors: list[str]) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            _fail(errors, f"{item_id}: {field} is not ISO date (YYYY-MM-DD): {value!r}")
            return None
    _fail(errors, f"{item_id}: {field} must be a date, got {type(value).__name__}")
    return None


def lint(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    closed_package_ids = _load_closed_package_ids()
    index_rel = data.get("user_stories_index")
    if index_rel is None:
        index_path = USER_STORIES_INDEX_PATH
    elif isinstance(index_rel, str):
        index_path = ROOT / index_rel
    else:
        _fail(errors, "user_stories_index must be a string path")
        index_path = USER_STORIES_INDEX_PATH
    stories_in_index = _load_user_story_index(index_path, errors)
    story_ids_in_index = set(stories_in_index)
    story_files = sorted(USER_STORIES_DIR.glob("us-*.md"))
    story_ids_on_disk = {f"US-{path.stem.split('-', 1)[1]}" for path in story_files}
    missing_in_index = sorted(story_ids_on_disk - story_ids_in_index)
    extra_in_index = sorted(story_ids_in_index - story_ids_on_disk)
    for us_id in missing_in_index:
        _fail(errors, f"user_stories_index missing US present on disk: {us_id}")
    for us_id in extra_in_index:
        _fail(errors, f"user_stories_index references missing US file: {us_id}")

    schema = data.get("schema_version")
    if not isinstance(schema, int) or not (_MIN_SCHEMA_VERSION <= schema <= SCHEMA_VERSION):
        _fail(errors, f"schema_version must be {_MIN_SCHEMA_VERSION}–{SCHEMA_VERSION}, got {schema!r}")

    items = data.get("items")
    if not isinstance(items, list):
        _fail(errors, "items: must be a list")
        return errors, warnings

    seen_ids: set[str] = set()
    all_ids: set[str] = set()
    for entry in items:
        if not isinstance(entry, dict):
            _fail(errors, f"item is not a mapping: {entry!r}")
            continue
        item_id = entry.get("id", "<no-id>")
        all_ids.add(str(item_id))

    today = date.today()

    for entry in items:
        if not isinstance(entry, dict):
            continue
        item_id = str(entry.get("id", "<no-id>"))

        missing = REQUIRED_KEYS - entry.keys()
        if missing:
            _fail(errors, f"{item_id}: missing required keys: {sorted(missing)}")

        if item_id in seen_ids:
            _fail(errors, f"{item_id}: duplicate id")
        else:
            seen_ids.add(item_id)

        status = entry.get("status")
        if status not in ALLOWED_STATUS:
            _fail(errors, f"{item_id}: status {status!r} not in {sorted(ALLOWED_STATUS)}")
        if status == "deferred" and not entry.get("re_entry_condition"):
            _fail(errors, f"{item_id}: deferred items must set re_entry_condition")
        # dod_commands is mandatory for ready/wip — ensures pipeline can use real DoD.
        if status in {"ready", "wip"}:
            dod_cmds = entry.get("dod_commands")
            if not dod_cmds:
                _fail(errors, f"{item_id}: {status} items must have dod_commands (non-empty list)")
        if item_id == RESUME_CARD_PACKAGE_ID and status == "ready":
            _fail(errors, f"{item_id}: must not be promoted to 'ready' (contract invariant)")

        impact = entry.get("impact")
        if impact is not None and impact not in ALLOWED_IMPACT:
            _fail(errors, f"{item_id}: impact {impact!r} not in {sorted(ALLOWED_IMPACT)}")

        cost = entry.get("cost_estimate")
        if cost is not None and cost not in ALLOWED_COST:
            _fail(errors, f"{item_id}: cost_estimate {cost!r} not in {sorted(ALLOWED_COST)}")

        created = _parse_date(entry.get("created"), "created", item_id, errors)
        last_review = _parse_date(entry.get("last_review"), "last_review", item_id, errors)
        if created and last_review and last_review < created:
            _fail(errors, f"{item_id}: last_review {last_review} precedes created {created}")
        if last_review and (today - last_review).days > 60 and status in {"ready", "deferred"}:
            _warn(warnings, f"{item_id}: last_review {last_review} is >60d old for status {status!r}")

        deps = entry.get("depends_on", []) or []
        if not isinstance(deps, list):
            _fail(errors, f"{item_id}: depends_on must be a list")
        else:
            for dep in deps:
                if dep == item_id:
                    _fail(errors, f"{item_id}: depends_on includes self")
                elif dep not in all_ids and dep not in closed_package_ids:
                    _warn(warnings, f"{item_id}: depends_on {dep!r} not found in registry")

        user_stories = entry.get("user_stories", []) or []
        if not isinstance(user_stories, list):
            _fail(errors, f"{item_id}: user_stories must be a list")
        else:
            # Infra packages may not map cleanly to a single user story. For those,
            # allow empty `user_stories` even in ready/wip (DoD still mandatory).
            # Extension packages may also leave user_stories empty when notes document
            # a closed baseline story they extend without reopening.
            if status in {"ready", "wip"} and not user_stories and not _allows_empty_user_stories(entry):
                _fail(errors, f"{item_id}: {status} items must reference at least one user story")
            for us_id in user_stories:
                if not isinstance(us_id, str):
                    _fail(errors, f"{item_id}: user story reference must be a string: {us_id!r}")
                    continue
                story_name = us_id.lower().replace(".", ".")
                story_path = USER_STORIES_DIR / f"{story_name}.md"
                if not story_path.is_file():
                    _fail(errors, f"{item_id}: user story {us_id!r} does not exist at {story_path.relative_to(ROOT)}")
                if us_id not in story_ids_in_index:
                    _fail(errors, f"{item_id}: user story {us_id!r} not found in {index_path.relative_to(ROOT)}")
                    continue

                story_item = stories_in_index[us_id]
                expected_rel_path = Path("doc") / "user_stories" / f"{us_id.lower()}.md"
                expected_rel_path_str = str(expected_rel_path).replace("\\", "/")
                index_path_value = story_item.get("path")
                if index_path_value != expected_rel_path_str:
                    _fail(
                        errors,
                        (
                            f"{item_id}: user story {us_id!r} has non-canonical path in index: "
                            f"{index_path_value!r}, expected {expected_rel_path_str!r}"
                        ),
                    )

                frontmatter = _parse_frontmatter(story_path)
                if frontmatter is None:
                    _fail(errors, f"{item_id}: {story_path.relative_to(ROOT)} missing valid YAML frontmatter")
                    continue
                missing_keys = sorted(US_FRONTMATTER_REQUIRED_KEYS - set(frontmatter))
                if missing_keys:
                    _fail(
                        errors,
                        f"{item_id}: {story_path.relative_to(ROOT)} missing frontmatter keys: {missing_keys}",
                    )

                fm_us_id = frontmatter.get("us_id")
                if fm_us_id != us_id:
                    _fail(
                        errors,
                        (
                            f"{item_id}: {story_path.relative_to(ROOT)} us_id mismatch: "
                            f"{fm_us_id!r} != {us_id!r}"
                        ),
                    )

                fm_status = frontmatter.get("status")
                index_status = story_item.get("status")
                if fm_status != index_status:
                    _fail(
                        errors,
                        (
                            f"{item_id}: {story_path.relative_to(ROOT)} status mismatch with index: "
                            f"{fm_status!r} != {index_status!r}"
                        ),
                    )

                fm_coverage = _normalize_coverage_value(frontmatter.get("covered_by"))
                index_coverage = _normalize_coverage_value(story_item.get("covered_by"))
                if fm_coverage != index_coverage:
                    _fail(
                        errors,
                        (
                            f"{item_id}: {story_path.relative_to(ROOT)} covered_by mismatch with index: "
                            f"{fm_coverage!r} != {index_coverage!r}"
                        ),
                    )

                if status in {"ready", "wip"} and impact != "infra":
                    # Soft policy: keep warnings (not hard failures) so non-stop automation
                    # can proceed even when the US index is already closed/covered.
                    if index_status != "open":
                        _warn(
                            warnings,
                            (
                                f"{item_id}: {status} references non-open story {us_id!r} "
                                f"(index status={index_status!r})"
                            ),
                        )
                    if index_coverage != "open":
                        _warn(
                            warnings,
                            (
                                f"{item_id}: {status} references already-covered story {us_id!r} "
                                f"(covered_by={story_item.get('covered_by')!r})"
                            ),
                        )

                if index_status == "closed":
                    if not _coverage_tokens(story_item.get("covered_by")):
                        _fail(errors, f"{item_id}: closed story {us_id!r} must define non-empty covered_by")
                    if story_item.get("closed_date") is None:
                        _warn(warnings, f"{item_id}: closed story {us_id!r} has null closed_date")
                else:
                    if _normalize_coverage_value(story_item.get("covered_by")) != "open":
                        _fail(errors, f"{item_id}: open story {us_id!r} must not have covered_by package")

        write_max = entry.get("write_set_max")
        if write_max is not None and (not isinstance(write_max, int) or write_max < 1):
            _fail(errors, f"{item_id}: write_set_max must be a positive int")

    now_ready_wip = [
        str(entry.get("id"))
        for entry in items
        if isinstance(entry, dict)
        and str(entry.get("status", "")).strip().lower() in {"ready", "wip"}
        and entry.get("id")
    ]
    if len(now_ready_wip) > 1:
        _fail(
            errors,
            (
                "Truth View invariant: at most one package may be ready or wip, "
                f"found {sorted(now_ready_wip)}"
            ),
        )

    errors.extend(lint_active_package_pointer(data))

    return errors, warnings


def lint_strict(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Strict validation of optional wave_id/wave_position fields (schema_version >= 2).

    Returns (errors, warnings). Skipped silently when schema_version < 2.
    """
    errors: list[str] = []
    warnings: list[str] = []

    schema_version = data.get("schema_version", 1)
    if not (isinstance(schema_version, int) and schema_version >= 2):
        return errors, warnings  # not applicable for schema v1

    waves = data.get("waves", []) or []
    wave_ids: set[str] = set()
    for wave in waves:
        if not isinstance(wave, dict):
            _fail(errors, f"waves: entry is not a mapping: {wave!r}")
            continue
        w_id = wave.get("id")
        if not w_id:
            _fail(errors, "waves: entry missing 'id'")
            continue
        if w_id in wave_ids:
            _fail(errors, f"waves: duplicate wave id: {w_id!r}")
        wave_ids.add(str(w_id))
        if not wave.get("packages"):
            _warn(warnings, f"wave {w_id!r}: 'packages' list is empty")
        if not wave.get("north_star"):
            _warn(warnings, f"wave {w_id!r}: 'north_star' is missing (recommended)")
        status = wave.get("status")
        allowed_wave_status = {"proposed", "ready", "wip", "completed", "frozen"}
        if status and status not in allowed_wave_status:
            _fail(errors, f"wave {w_id!r}: status {status!r} not in {sorted(allowed_wave_status)}")

    items = data.get("items", []) or []
    items_by_id = {item["id"]: item for item in items if isinstance(item, dict) and "id" in item}

    # INV5: items with wave_id must reference existing wave
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "<no-id>"))
        wave_id = item.get("wave_id")
        if wave_id is None:
            continue
        if str(wave_id) not in wave_ids:
            _fail(errors, f"{item_id}: wave_id {wave_id!r} references unknown wave")
        wave_pos = item.get("wave_position")
        if wave_pos is not None and (not isinstance(wave_pos, int) or wave_pos < 1):
            _fail(errors, f"{item_id}: wave_position must be a positive int, got {wave_pos!r}")

    # INV6: wave.packages must reference existing items with matching wave_id
    for wave in waves:
        if not isinstance(wave, dict):
            continue
        w_id = str(wave.get("id", ""))
        for pkg_id in wave.get("packages", []):
            if not isinstance(pkg_id, str):
                _fail(errors, f"wave {w_id!r}: package reference must be a string: {pkg_id!r}")
                continue
            item = items_by_id.get(pkg_id)
            if item is None:
                _fail(errors, f"wave {w_id!r}: package {pkg_id!r} not found in items")
            elif str(item.get("wave_id", "")) != w_id:
                _fail(
                    errors,
                    f"wave {w_id!r}: package {pkg_id!r} has wave_id={item.get('wave_id')!r} (expected {w_id!r})",
                )

    return errors, warnings


def main() -> int:  # noqa: C901
    timer = PhaseTimer()
    parser = argparse.ArgumentParser(description="Lint the backlog registry YAML.")
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_PATH,
        help=f"Registry YAML path (default: {DEFAULT_PATH.relative_to(ROOT)})",
    )
    parser.add_argument(
        "--sync-from-index",
        action="store_true",
        help="Refresh user_stories.md/cjm.md blocks and generated date using user_stories_index.json",
    )
    parser.add_argument(
        "--write-sync",
        action="store_true",
        help="Apply --sync-from-index changes to files (otherwise dry-run).",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI mode: enforce generated sync in dry-run (equivalent to --sync-from-index).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Strict mode: additionally validate optional wave_id/wave_position fields "
            "when schema_version >= 2 (INV5+INV6 cross-reference checks)."
        ),
    )
    args = parser.parse_args()
    if args.ci:
        args.sync_from_index = True
        args.write_sync = False

    path: Path = args.path
    if not path.is_absolute():
        path = ROOT / path

    if not path.is_file():
        print(f"FAIL: registry not found at {path}")
        return 2

    try:
        with timer.phase("parse_yaml"):
            data = _load_registry_text(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - linter entrypoint must report parser failures clearly.
        print(f"FAIL: YAML parse error: {exc}")
        return 2

    if not isinstance(data, dict):
        print("FAIL: top-level YAML must be a mapping with schema_version + items")
        return 2

    if args.write_sync:
        if patch_registry_active_package_id(path, data):
            try:
                data = _load_registry_text(path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                print(f"FAIL: YAML parse error after active_package_id patch: {exc}")
                return 2

    try:
        with timer.phase("validate_schema"):
            errors, warnings = lint(data)

        if args.sync_from_index:
            with timer.phase("sync_tasklist_md"):
                sync_errors, sync_warnings = sync_docs_from_index(
                    index_path=USER_STORIES_INDEX_PATH,
                    write=args.write_sync,
                    registry_data=data,
                )
                errors.extend(sync_errors)
                warnings.extend(sync_warnings)

        if getattr(args, "strict", False):
            with timer.phase("validate_schema_strict"):
                strict_errors, strict_warnings = lint_strict(data)
                errors.extend(strict_errors)
                warnings.extend(strict_warnings)

        for msg in errors:
            print(f"FAIL: {msg}")
        for msg in warnings:
            print(f"WARN: {msg}")

        if errors:
            return 2
        # Warnings should not block automation / non-stop mode. They are printed above.
        print(f"PASS: {path.relative_to(ROOT)} - {len(data.get('items', []))} items")
        return 0
    finally:
        timer.flush()
        timer.total_only_when_top_level()


if __name__ == "__main__":
    sys.exit(main())
