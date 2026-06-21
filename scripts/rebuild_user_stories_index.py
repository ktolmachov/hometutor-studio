#!/usr/bin/env python3
"""
rebuild_user_stories_index.py — Rebuild doc/user_stories_index.json from truth sources.

Truth sources (in priority order):
  1. doc/backlog_registry.yaml — which packages are closed and which US they cover
  2. doc/user_stories/*.md     — frontmatter for US metadata (epic, priority, cjm_stage, etc.)

This script replaces the stale `open_candidates` section and corrects `status`/`covered_by`
for any US that was closed via a registry package but not reflected in the index.

CJM-generated tables read the same canonical index via `doc/user_stories_index.json`
(`scripts/backlog_registry_lint.sync_docs_from_index`).

Usage:
    python scripts/rebuild_user_stories_index.py          # dry-run: check if rebuild needed
    python scripts/rebuild_user_stories_index.py --write  # write updated index to disk
    python scripts/rebuild_user_stories_index.py --check  # exit 1 if rebuild would change anything

Exit codes:
    0 = OK (no changes needed, or write succeeded)
    1 = CHECK mode: index is stale (rebuild needed)
    2 = Error (parse error, missing file)
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKLOG_REGISTRY = ROOT / "doc" / "backlog_registry.yaml"
USER_STORIES_DIR = ROOT / "doc" / "user_stories"
US_INDEX = ROOT / "doc" / "user_stories_index.json"

try:
    import yaml as _yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


# ---------------------------------------------------------------------------
# Priority ordering for open_candidates ranking
# ---------------------------------------------------------------------------
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}

# Pain points map (sourced from backlog_registry_lint.py — shared knowledge)
PAIN_POINT_BY_US = {
    "US-2.5": "Source readiness diagnostics lack a stable API contract and explicit failure categories",
    "US-11.2": "Retrieval confidence can be mistaken for probability of truth",
    "US-12.7": "Quality claims are not tied to a reproducible defense eval run",
    "US-12.8": "Slow or expensive answers cannot be explained by pipeline stage",
    "US-12.9": "Mastery and graduation claims are not validated against learning outcomes",
    "US-12.10": "RAG adversarial failures are not measured against retrieved documents",
    "US-12.11": "Local-first privacy claims lack deletion verification and cloud-boundary docs",
    "US-1.2": "Stack trace / пустой экран / missing env",
    "US-2.3": "Сканы и изображения не попадают в общий knowledge base для Q&A",
    "US-2.4": "Непонятно, какие файлы в data/ готовы к ответу, а какие «пустые» для retrieval",
    "US-3.1": "\"Не нашёл информации\" на тривиальный вопрос",
    "US-3.4": "\"Не нашёл информации\" на тривиальный вопрос",
    "US-3.5": "Субъективно долгое или непрозрачное ожидание первого ответа",
    "US-3.6": "Полная генерация при уже достаточном retrieval-покрытии (лишняя стоимость/латентность)",
    "US-4.1": "Тьютор стартует с нуля, забывая тему",
    "US-4.2": "Learner не понимает решений тьютора",
    "US-5.1": "Fail без объяснения / вопрос не по теме",
    "US-5.2": "Fail без объяснения / вопрос не по теме",
    "US-6.1": "Нет плана на сегодня после первой сессии",
    "US-7.1": "50+ overdue без приоритизации",
    "US-7.3": "\"Где я был вчера?\" — нет resume card",
    "US-7.4": "50+ overdue без приоритизации",
    "US-8.1": "Mastery обнуляется / история теряется",
    "US-8.2": "Mastery обнуляется / история теряется",
    "US-9.1": "Метрики разбросаны",
    "US-9.2": "Нет ощущения завершения",
    "US-14.1": "10 равных действий вместо одного next step",
    "US-14.2": "10 равных действий вместо одного next step",
    "US-14.3": "10 равных действий вместо одного next step",
    "US-14.4": "10 равных действий вместо одного next step",
    "US-15.1": "Карточки без preview / course scope",
    "US-15.2": "Нет summary после сессии",
    "US-16.0": "Нельзя изолировать scope по конкретному курсу",
    "US-16.1": "Нельзя изолировать scope по конкретному курсу",
    "US-16.2": "Нельзя изолировать scope по конкретному курсу",
    "US-16.3": "Нельзя изолировать scope по конкретному курсу",
    "US-16.4": "Нельзя изолировать scope по конкретному курсу",
    "US-16.5": "Нельзя изолировать scope по конкретному курсу",
    "US-16.6": "Нельзя изолировать scope по конкретному курсу",
    "US-16.7": "Ручная навигация между табами ломает поток: ДЗ и плейбук вне Course Mode",
}


# ---------------------------------------------------------------------------
# Registry loader
# ---------------------------------------------------------------------------

def _parse_scalar(value: str) -> Any:
    value = value.split("  #", 1)[0].strip()
    if value in {"null", "None", "~"}:
        return None
    if value == "[]":
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(p.strip().strip('"').strip("'")) for p in inner.split(",")]
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    return value


def _load_registry(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if _HAS_YAML:
        data = _yaml.safe_load(text)
        if not isinstance(data, dict):
            raise ValueError(f"{path}: top-level YAML must be a mapping")
        return data

    # Minimal fallback parser for items list
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
            data[key] = _parse_scalar(raw_value.strip())
            continue
        if in_items and stripped.startswith("- "):
            payload = stripped[2:]
            if ":" in payload:
                key, raw_value = payload.split(":", 1)
                current = {key.strip(): _parse_scalar(raw_value.strip())}
                items.append(current)
                current_list_key = None
            elif current is not None and current_list_key:
                current[current_list_key].append(_parse_scalar(payload.strip().strip('"').strip("'")))
            continue
        if in_items and current is not None and ":" in stripped:
            key, raw_value = stripped.split(":", 1)
            if raw_value.strip() == "":
                current[key.strip()] = []
                current_list_key = key.strip()
            else:
                current[key.strip()] = _parse_scalar(raw_value.strip())
                current_list_key = None

    return data


# ---------------------------------------------------------------------------
# Frontmatter parser
# ---------------------------------------------------------------------------

def _parse_frontmatter(path: Path) -> dict[str, Any] | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end]
    if _HAS_YAML:
        parsed = _yaml.safe_load(block)
        return parsed if isinstance(parsed, dict) else None
    result: dict[str, Any] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        result[key.strip()] = _parse_scalar(raw_value.strip())
    return result


# ---------------------------------------------------------------------------
# Registry analysis: build a map of us_id → (covered_by, closed_date)
# ---------------------------------------------------------------------------

def _build_coverage_map(registry: dict[str, Any]) -> dict[str, tuple[str, str | None]]:
    """Return {us_id: (package_id, closed_date)} for each US covered by a closed package."""
    coverage: dict[str, tuple[str, str | None]] = {}
    for item in (registry.get("items") or []):
        if not isinstance(item, dict):
            continue
        if item.get("status") != "closed":
            continue
        pkg_id = str(item.get("id", ""))
        if not pkg_id:
            continue
        closed_date = item.get("last_review") or item.get("created")
        if isinstance(closed_date, date):
            closed_date = closed_date.isoformat()
        elif closed_date is not None:
            closed_date = str(closed_date)
        for us_id in item.get("user_stories", []):
            if isinstance(us_id, str) and us_id:
                coverage[us_id] = (pkg_id, closed_date)
    return coverage


# ---------------------------------------------------------------------------
# Main rebuild logic
# ---------------------------------------------------------------------------

def rebuild(write: bool = False) -> tuple[dict[str, Any], bool]:
    """Rebuild the index from registry truth + frontmatter files.

    Returns (new_index_dict, changed: bool).
    """
    if not BACKLOG_REGISTRY.exists():
        raise FileNotFoundError(f"Registry not found: {BACKLOG_REGISTRY}")

    registry = _load_registry(BACKLOG_REGISTRY)
    coverage_map = _build_coverage_map(registry)

    # Load all US files sorted by id
    us_files = sorted(USER_STORIES_DIR.glob("us-*.md"))
    if not us_files:
        raise FileNotFoundError(f"No us-*.md files found in {USER_STORIES_DIR}")

    # Load existing index to preserve fields we don't recompute (epic_name, title, etc.)
    existing: dict[str, Any] = {}
    if US_INDEX.exists():
        try:
            payload = json.loads(US_INDEX.read_text(encoding="utf-8"))
            existing = {it["us_id"]: it for it in payload.get("items", []) if isinstance(it, dict) and "us_id" in it}
        except Exception:  # noqa: BLE001
            pass

    items: list[dict[str, Any]] = []
    for us_file in us_files:
        fm = _parse_frontmatter(us_file)
        if fm is None:
            print(f"  ⚠ Skipping {us_file.name}: missing frontmatter", file=sys.stderr)
            continue

        us_id = str(fm.get("us_id", "")).strip()
        if not us_id:
            # Derive from filename: us-3.2.md → US-3.2
            stem = us_file.stem  # "us-3.2"
            us_id = "US-" + stem[3:]  # "US-3.2"

        # Determine status from registry (authoritative for *whether* it's closed)
        # then frontmatter for covered_by (authoritative for *which package* closed it,
        # since historical frontmatter may reference older epoch IDs not in registry).
        fm_covered = fm.get("covered_by")
        fm_covered_str = str(fm_covered).strip() if fm_covered else None
        fm_status = str(fm.get("status", "open")).strip()
        fm_closed_date = fm.get("closed_date")

        if us_id in coverage_map:
            registry_pkg_id, closed_date_reg = coverage_map[us_id]
            status = "closed"
            # Prefer frontmatter covered_by if it already has a specific historical value;
            # use registry package id only when frontmatter is unset.
            covered_by = fm_covered_str if fm_covered_str else registry_pkg_id
            # Prefer frontmatter closed_date if set, else registry date
            closed_date = fm_closed_date or closed_date_reg
            if isinstance(closed_date, date):
                closed_date = closed_date.isoformat()
            elif closed_date is not None:
                closed_date = str(closed_date)
        elif fm_status == "closed" and fm_covered_str:
            # Not in registry coverage_map, but frontmatter already marks it closed
            status = "closed"
            covered_by = fm_covered_str
            closed_date = fm_closed_date
            if isinstance(closed_date, date):
                closed_date = closed_date.isoformat()
            elif closed_date is not None:
                closed_date = str(closed_date)
        else:
            status = "open"
            covered_by = fm_covered_str if fm_covered_str else "open"
            closed_date = None

        # Prefer existing index fields for stable metadata; override status/covered_by/closed_date
        existing_item = existing.get(us_id, {})
        item: dict[str, Any] = {
            "us_id": us_id,
            "epic": existing_item.get("epic") or fm.get("epic") or 0,
            "epic_name": existing_item.get("epic_name") or str(fm.get("epic_name", "")),
            "title": existing_item.get("title") or str(fm.get("title", us_id)),
            "priority": existing_item.get("priority") or str(fm.get("priority", "P2")),
            "cjm_stage": existing_item.get("cjm_stage") or str(fm.get("cjm_stage", "")),
            "cjm_moment_name": existing_item.get("cjm_moment_name") or str(fm.get("cjm_moment_name", "")),
            "status": status,
            "covered_by": covered_by,
            "closed_date": closed_date,
            "path": f"doc/user_stories/{us_file.name}",
        }
        items.append(item)

    # Compute open_candidates: top 8 open by (priority, cjm_stage, us_id)
    open_items = [it for it in items if it["status"] == "open"]
    open_items.sort(key=lambda it: (
        PRIORITY_ORDER.get(str(it.get("priority")), 99),
        str(it.get("cjm_stage", "")),
        str(it.get("us_id", "")),
    ))
    open_candidates: list[dict[str, Any]] = []
    for rank, it in enumerate(open_items[:8], start=1):
        open_candidates.append({
            "rank": rank,
            "us_id": it["us_id"],
            "title": it["title"],
            "priority": it["priority"],
            "cjm_stage": it["cjm_stage"],
            "status": it["status"],
            "coverage": "open",
            "pain_point": PAIN_POINT_BY_US.get(it["us_id"]),
        })

    new_index: dict[str, Any] = {
        "version": 1,
        "generated": date.today().isoformat(),
        "items": items,
        "open_candidates": open_candidates,
    }

    # Check if changed (compare items + open_candidates, ignore generated timestamp)
    changed = True
    if US_INDEX.exists():
        try:
            old = json.loads(US_INDEX.read_text(encoding="utf-8"))
            old_cmp = {"items": old.get("items", []), "open_candidates": old.get("open_candidates", [])}
            new_cmp = {"items": items, "open_candidates": open_candidates}
            changed = json.dumps(old_cmp, ensure_ascii=False, sort_keys=True) != json.dumps(new_cmp, ensure_ascii=False, sort_keys=True)
        except Exception:  # noqa: BLE001
            changed = True

    if write and changed:
        US_INDEX.write_text(json.dumps(new_index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return new_index, changed


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--write", "-w", action="store_true",
        help="Write updated index to doc/user_stories_index.json",
    )
    parser.add_argument(
        "--check", "-c", action="store_true",
        help="Exit 1 if index is stale (rebuild would change anything); do not write",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress informational output",
    )
    args = parser.parse_args(argv)

    try:
        new_index, changed = rebuild(write=args.write)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: rebuild failed: {exc}", file=sys.stderr)
        return 2

    n_open = len(new_index.get("open_candidates", []))
    n_items = len(new_index.get("items", []))

    if not args.quiet:
        if changed:
            if args.write:
                print(f"✅ Rebuilt doc/user_stories_index.json — {n_items} items, {n_open} open candidates")
            elif args.check:
                print(f"⚠ Index is stale — rebuild needed ({n_items} items, {n_open} open candidates)")
            else:
                print(f"ℹ Index is stale. Run with --write to update. ({n_items} items, {n_open} open candidates)")
        else:
            print(f"✅ Index is up-to-date — {n_items} items, {n_open} open candidates")

    if args.check and changed:
        return 1
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
