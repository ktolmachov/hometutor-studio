#!/usr/bin/env python3
"""
Roadmap/doc-sync consistency checker.

Truth View invariant (must match doc/backlog_registry.yaml header and
doc/roadmap_governance.md § Truth View Contract):
    Among all registry ``items``, at most ONE package may be ``ready`` or ``wip``
    at the same time. Enforced via ``get_backlog_truth_view`` → ``truth_view``.
    Optional top-level ``active_package_id`` mirrors that sole package (validated by
    ``lint_active_package_pointer``); kept in sync by ``backlog_registry_lint.py --write-sync``.

Usage:
    python scripts/roadmap_sync_check.py

Exit codes:
    0 = OK
    2 = FAIL
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TASKLIST_PATH = ROOT / "doc" / "tasklist.md"
BACKLOG_REGISTRY_PATH = ROOT / "doc" / "backlog_registry.yaml"
CLOSED_ITERATIONS_PATH = ROOT / "doc" / "closed_iterations.md"
USER_STORIES_DIR = ROOT / "doc" / "user_stories"
USER_STORIES_INDEX_PATH = ROOT / "doc" / "user_stories_index.json"
AUTO_CORRECT_SCRIPT = ROOT / "scripts" / "auto_correct_registry_closed_status.py"
sys.path.insert(0, str(ROOT / "scripts"))
from prompt_utils import get_backlog_truth_view, lint_active_package_pointer, load_backlog_registry  # noqa: E402


@dataclass
class StoryFrontmatter:
    us_id: str
    status: str | None
    covered_by: str | None
    closed_date: str | None
    path: Path


def _normalize_open_coverage(value: Any) -> str:
    """Treat open-story sentinel values as equivalent across generated docs."""
    if value is None:
        return "open"
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped.lower() in {"none", "null", "n/a", "open"}:
            return "open"
        return stripped
    return str(value)


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


def _load_yaml_like(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError:  # pragma: no cover
        yaml = None

    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            raise ValueError(f"{path}: top-level YAML must be a mapping")
        return data

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


def _load_registry_items(path: Path) -> list[dict[str, Any]]:
    data = _load_yaml_like(path)
    items = data.get("items")
    if not isinstance(items, list):
        raise ValueError(f"{path}: items must be a list")
    return [item for item in items if isinstance(item, dict)]


def _load_story_frontmatter(path: Path) -> StoryFrontmatter:
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        raise ValueError(f"{path}: missing YAML frontmatter")

    data: dict[str, Any] = {}
    for raw_line in lines[1:]:
        if raw_line.strip() == "---":
            break
        if ":" not in raw_line:
            continue
        key, raw_value = raw_line.split(":", 1)
        data[key.strip()] = _parse_scalar(raw_value)

    us_id = data.get("us_id")
    if not isinstance(us_id, str):
        raise ValueError(f"{path}: frontmatter us_id missing")

    return StoryFrontmatter(
        us_id=us_id,
        status=data.get("status"),
        covered_by=data.get("covered_by"),
        closed_date=data.get("closed_date"),
        path=path,
    )


def _load_user_stories(directory: Path) -> dict[str, StoryFrontmatter]:
    stories: dict[str, StoryFrontmatter] = {}
    for path in sorted(directory.glob("us-*.md")):
        story = _load_story_frontmatter(path)
        stories[story.us_id] = story
    return stories


def _load_user_stories_index(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items")
    if not isinstance(items, list):
        raise ValueError(f"{path}: items must be a list")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("us_id"), str):
            result[item["us_id"]] = item
    return result


def _parse_contract_ids(tasklist_text: str) -> set[str]:
    return set(re.findall(r"^### ([A-Za-z0-9][A-Za-z0-9._/-]*) Contract$", tasklist_text, flags=re.MULTILINE))


def _package_in_closed_iterations(package_id: str, closed_iterations_text: str) -> bool:
    heading = re.compile(rf"^### {re.escape(package_id)}\b", re.MULTILINE)
    return bool(heading.search(closed_iterations_text) or f"`{package_id}`" in closed_iterations_text)


_TRUTH_VIEW_MISSING_ITEM = "Truth View active package not found under items[].id"
_MISSING_STATUS_FIELD = "missing `status` field"


def _active_slot_errors_transient_retryable(slot_errors: list[str]) -> bool:
    """True only for lookup-miss noise (empty items snapshot); never for bad YAML data."""
    if not slot_errors:
        return False
    if any(_MISSING_STATUS_FIELD in message for message in slot_errors):
        return False
    return any(_TRUTH_VIEW_MISSING_ITEM in message for message in slot_errors)


def _collect_active_package_slot_errors(registry_data: dict[str, Any]) -> list[str]:
    """Truth View singleton + active pointer + registry row match (ready/wip slot)."""
    errors: list[str] = []
    registry_items = [item for item in registry_data.get("items") or [] if isinstance(item, dict)]
    truth_view_data = get_backlog_truth_view(registry_data=registry_data)
    truth_view = [
        (str(row["package"]), str(row["status"]).lower())
        for row in truth_view_data.get("truth_view", [])
        if isinstance(row, dict) and "package" in row and "status" in row
    ]
    registry_by_id: dict[str, dict] = {}
    for item in registry_items:
        if "id" not in item:
            continue
        rid = str(item["id"])
        registry_by_id[rid] = item
        if rid.startswith("epoch-"):
            registry_by_id[rid[len("epoch-") :]] = item

    active_truth_slots = [(pkg, status) for pkg, status in truth_view if status in {"ready", "wip"}]
    if len(active_truth_slots) > 1:
        errors.append(
            "backlog_registry.yaml: expected at most one active ready/wip package in Truth View, "
            f"found {active_truth_slots}"
        )

    errors.extend(lint_active_package_pointer(registry_data))

    for package_id, status in active_truth_slots:
        registry_item = registry_by_id.get(package_id) or registry_by_id.get(f"epoch-{package_id}")
        if registry_item is None:
            errors.append(
                f"{package_id}: Truth View active package not found under items[].id in backlog_registry.yaml"
            )
            continue
        registry_status = registry_item.get("status")
        if registry_status is None:
            errors.append(
                f"{package_id}: backlog_registry item is missing `status` field "
                f"(Truth View slot status={status!r})"
            )
            continue
        status_ok = registry_status == status or (
            status in ("ready", "wip") and registry_status in ("proposed", "open", "ready", "wip")
        )
        if not status_ok:
            errors.append(
                f"{package_id}: Truth View slot status={status!r} but backlog_registry status={registry_status!r}"
            )

    return errors


def check_roadmap_sync(
    *,
    tasklist_path: Path = TASKLIST_PATH,
    backlog_registry_path: Path = BACKLOG_REGISTRY_PATH,
    closed_iterations_path: Path = CLOSED_ITERATIONS_PATH,
    user_stories_dir: Path = USER_STORIES_DIR,
    user_stories_index_path: Path = USER_STORIES_INDEX_PATH,
) -> list[str]:
    errors: list[str] = []
    workspace_root = user_stories_dir.parent.parent

    tasklist_text = tasklist_path.read_text(encoding="utf-8")
    closed_iterations_text = closed_iterations_path.read_text(encoding="utf-8")
    contract_ids = _parse_contract_ids(tasklist_text)
    registry_data = load_backlog_registry(backlog_registry_path)
    slot_errors = _collect_active_package_slot_errors(registry_data)
    attempt = 0
    while _active_slot_errors_transient_retryable(slot_errors) and attempt < 2:
        time.sleep(0.05 + 0.05 * attempt)
        registry_data = load_backlog_registry(backlog_registry_path)
        slot_errors = _collect_active_package_slot_errors(registry_data)
        attempt += 1
    errors.extend(slot_errors)

    registry_items = [item for item in registry_data.get("items") or [] if isinstance(item, dict)]
    stories = _load_user_stories(user_stories_dir)
    index_items = _load_user_stories_index(user_stories_index_path)

    for item in registry_items:
        package_id = str(item.get("id"))
        status = item.get("status")
        user_stories = item.get("user_stories") or []
        if status == "closed":
            if package_id in contract_ids:
                errors.append(f"{package_id}: closed package must not keep a full Contract section in tasklist.md")
            if not _package_in_closed_iterations(package_id, closed_iterations_text):
                errors.append(f"{package_id}: closed package missing from doc/closed_iterations.md")
            for us_id in user_stories:
                if not isinstance(us_id, str):
                    continue
                story = stories.get(us_id)
                if story is None:
                    errors.append(f"{package_id}: user story {us_id!r} is missing from doc/user_stories/")
                    continue
                if story.status != "closed":
                    errors.append(f"{package_id}: {us_id} must be status=closed, got {story.status!r}")
                if not story.covered_by:
                    errors.append(f"{package_id}: {us_id} must set covered_by when package is closed")
                if not story.closed_date:
                    errors.append(f"{package_id}: {us_id} must set closed_date when package is closed")

        for us_id in user_stories:
            if not isinstance(us_id, str):
                continue
            story = stories.get(us_id)
            index_entry = index_items.get(us_id)
            if story is None or index_entry is None:
                continue
            expected_path = story.path.relative_to(workspace_root).as_posix()
            mismatches: list[str] = []
            for field in ("status", "covered_by", "closed_date"):
                index_value = index_entry.get(field)
                story_value = getattr(story, field)
                matches = (
                    _normalize_open_coverage(index_value) == _normalize_open_coverage(story_value)
                    if field == "covered_by"
                    else index_value == story_value
                )
                if not matches:
                    mismatches.append(
                        f"{field}: story={story_value!r} index={index_value!r}"
                    )
            if index_entry.get("path") != expected_path:
                mismatches.append(f"path: story={expected_path!r} index={index_entry.get('path')!r}")
            if mismatches:
                errors.append(f"{us_id}: doc/user_stories_index.json is stale ({'; '.join(mismatches)})")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check roadmap/doc-sync consistency.")
    parser.add_argument("--tasklist", type=Path, default=TASKLIST_PATH)
    parser.add_argument("--registry", type=Path, default=BACKLOG_REGISTRY_PATH)
    parser.add_argument("--closed-iterations", type=Path, default=CLOSED_ITERATIONS_PATH)
    parser.add_argument("--user-stories-dir", type=Path, default=USER_STORIES_DIR)
    parser.add_argument("--user-stories-index", type=Path, default=USER_STORIES_INDEX_PATH)
    args = parser.parse_args()

    # Keep pipelines simple: roadmap_sync_check self-heals known status drift first.
    if AUTO_CORRECT_SCRIPT.exists():
        autocorrect = subprocess.run(
            [sys.executable, str(AUTO_CORRECT_SCRIPT)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
        )
        if autocorrect.returncode != 0:
            print("FAIL: pre-check auto-correction failed")
            output = (autocorrect.stdout + autocorrect.stderr).strip()
            if output:
                for line in output.splitlines():
                    print(f" - {line}")
            return 2

    errors = check_roadmap_sync(
        tasklist_path=args.tasklist,
        backlog_registry_path=args.registry,
        closed_iterations_path=args.closed_iterations,
        user_stories_dir=args.user_stories_dir,
        user_stories_index_path=args.user_stories_index,
    )
    if errors:
        print("FAIL: roadmap sync check")
        for error in errors:
            print(f" - {error}")
        return 2

    print("PASS: roadmap sync is consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
