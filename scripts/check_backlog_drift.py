#!/usr/bin/env python3
"""
check_backlog_drift.py — Backlog drift guard: verify 6 consistency invariants.

Runs pre-flight checks before plan-next to ensure all truth sources are in sync.
Used by generate_plan_next_prompt.md Phase 0.

Invariants checked:
  1. Every US with status=closed in user_stories_index.json has a closed package in registry.
  2. open_candidates in user_stories_index.json contains no closed US.
  3. cjm.md § 8 pain table package_status matches registry.
  4. All packages in closed_iterations.md exist in registry as closed.
  5. Wave references are consistent (schema_version >= 2 only).
  6. Wave.packages list matches items[].wave_id back-references (schema_version >= 2 only).

Usage:
    python scripts/check_backlog_drift.py
    python scripts/check_backlog_drift.py --explain   # verbose: show all violations + fix hints

Exit codes:
    0 = OK — no drift
    1 = WARN — reserved for future non-critical issues. As of 2026-05-02, ``run_checks``
        emits no warnings; only exits 0 and 2 are returned.
    2 = DRIFT — at least one invariant violated
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
# Legacy compatibility constant (some tests/tools monkeypatch it).
TASKLIST = ROOT / "doc" / "tasklist.md"
BACKLOG_REGISTRY = ROOT / "doc" / "backlog_registry.yaml"
US_INDEX = ROOT / "doc" / "user_stories_index.json"
CJM_MD = ROOT / "doc" / "cjm.md"

try:
    import yaml as _yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


# ---------------------------------------------------------------------------
# Loaders
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
        return [p.strip().strip('"').strip("'") for p in inner.split(",")]
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    return value


def _load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if _HAS_YAML:
        data = _yaml.safe_load(text)
        return data if isinstance(data, dict) else {}

    # Minimal fallback parser
    data: dict[str, Any] = {}
    items: list[dict[str, Any]] = []
    waves: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_list_key: str | None = None
    section: str | None = None  # "items" or "waves"

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith(" ") and ":" in stripped:
            key, raw_value = stripped.split(":", 1)
            if key == "items":
                section = "items"
                data["items"] = items
                current = None
                continue
            if key == "waves":
                section = "waves"
                data["waves"] = waves
                current = None
                continue
            data[key] = _parse_scalar(raw_value.strip())
            continue
        if section and stripped.startswith("- "):
            payload = stripped[2:]
            if ":" in payload:
                key, raw_value = payload.split(":", 1)
                current = {key.strip(): _parse_scalar(raw_value.strip())}
                (items if section == "items" else waves).append(current)
                current_list_key = None
            elif current is not None and current_list_key:
                current[current_list_key].append(payload.strip().strip('"').strip("'"))
            continue
        if section and current is not None and ":" in stripped:
            key, raw_value = stripped.split(":", 1)
            if raw_value.strip() == "":
                current[key.strip()] = []
                current_list_key = key.strip()
            else:
                current[key.strip()] = _parse_scalar(raw_value.strip())
                current_list_key = None

    return data


def _load_us_index(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _parse_closed_iterations_refs(path: Path) -> set[str]:
    """Extract package IDs from closed_iterations.md headings and inline refs."""
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    ids: set[str] = set()
    heading_pattern = re.compile(r"^### ([A-Za-z0-9][A-Za-z0-9._/-]*)\b", re.MULTILINE)
    inline_pattern = re.compile(r"`([A-Za-z0-9][A-Za-z0-9._/-]*)`")
    for match in heading_pattern.finditer(text):
        ids.add(match.group(1))
    for pkg_id in inline_pattern.findall(text):
        if "/" in pkg_id:
            continue
        if pkg_id.startswith(("epoch-", "E")):
            ids.add(pkg_id)
    return ids


def _parse_cjm_pain_table(path: Path) -> list[dict[str, str]]:
    """Parse cjm.md § 8 pain table rows.
    Returns list of {pain, us_id, package_status}.
    """
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    # Find section 8
    section_match = re.search(r"## 8\. CJM pain table.*?(?=\n## |\Z)", text, re.DOTALL)
    if not section_match:
        return []
    section = section_match.group(0)

    rows = []
    for line in section.splitlines():
        # Table rows: | pain text | `US-X.Y` | `status` |
        m = re.match(r"\|\s*(.+?)\s*\|\s*`(US-[\d.]+)`\s*\|\s*`([^`]+)`\s*\|", line)
        if m:
            rows.append({
                "pain": m.group(1).strip(),
                "us_id": m.group(2).strip(),
                "package_status": m.group(3).strip(),
            })
    return rows


# ---------------------------------------------------------------------------
# Invariant checks
# ---------------------------------------------------------------------------

Violation = tuple[str, str]  # (invariant_id, message)


def _check_inv1(us_index: dict[str, Any], registry: dict[str, Any]) -> list[Violation]:
    """INV1: Every US with status=closed in index has a closed package covering it in registry."""
    violations: list[Violation] = []
    registry_items = {item["id"]: item for item in (registry.get("items") or []) if isinstance(item, dict) and "id" in item}

    for item in us_index.get("items", []):
        if not isinstance(item, dict):
            continue
        if item.get("status") != "closed":
            continue
        us_id = item.get("us_id", "")
        covered_by = item.get("covered_by")
        if not covered_by:
            violations.append(("INV1", f"US {us_id} is closed in index but has no covered_by"))
            continue
        # covered_by can be "E10.4-A / E13-A" or a single id
        for pkg_id in re.split(r"\s*/\s*|\s+or\s+", str(covered_by)):
            pkg_id = pkg_id.strip()
            if not pkg_id:
                continue
            reg_entry = registry_items.get(pkg_id)
            if reg_entry and reg_entry.get("status") == "closed":
                break  # at least one covering package is closed in registry
        else:
            # None of the covered_by packages are in registry as closed
            # Only flag if covered_by doesn't look like a legacy id that may be
            # absent from backlog_registry historical closed items.
            if not re.match(r"^(unknown-closed|E\d+[-.]|e\d+-|epoch-tour-|epoch-demo-)", str(covered_by)):
                violations.append((
                    "INV1",
                    f"US {us_id} closed with covered_by={covered_by!r} but not found as closed in registry",
                ))
    return violations


def _check_inv2(us_index: dict[str, Any]) -> list[Violation]:
    """INV2: open_candidates contains no closed US."""
    violations: list[Violation] = []
    closed_ids = {
        item["us_id"]
        for item in (us_index.get("items") or [])
        if isinstance(item, dict) and item.get("status") == "closed"
    }
    for cand in (us_index.get("open_candidates") or []):
        if not isinstance(cand, dict):
            continue
        us_id = cand.get("us_id", "")
        if us_id in closed_ids:
            violations.append(("INV2", f"open_candidates contains closed US: {us_id}"))
    return violations


def _check_inv3(us_index: dict[str, Any], cjm_rows: list[dict[str, str]]) -> list[Violation]:
    """INV3: cjm.md § 8 pain table package_status matches index status."""
    violations: list[Violation] = []
    index_by_id = {
        item["us_id"]: item
        for item in (us_index.get("items") or [])
        if isinstance(item, dict) and "us_id" in item
    }
    for row in cjm_rows:
        us_id = row["us_id"]
        pkg_status = row["package_status"]
        index_item = index_by_id.get(us_id)
        if index_item is None:
            continue  # US not in index, can't check
        if index_item.get("status") == "closed":
            expected_prefix = "closed:"
            if not pkg_status.startswith(expected_prefix):
                violations.append((
                    "INV3",
                    f"cjm § 8: {us_id} status in index=closed but pain table shows {pkg_status!r}",
                ))
        elif index_item.get("status") == "open":
            if pkg_status != "open":
                violations.append((
                    "INV3",
                    f"cjm § 8: {us_id} status in index=open but pain table shows {pkg_status!r}",
                ))
    return violations


def _check_inv4(closed_refs: set[str], registry: dict[str, Any]) -> list[Violation]:
    """INV4: All packages in closed_iterations references are closed in registry."""
    violations: list[Violation] = []
    registry_items = {
        item["id"]: item
        for item in (registry.get("items") or [])
        if isinstance(item, dict) and "id" in item
    }
    for pkg_id in sorted(closed_refs):
        reg_entry = registry_items.get(pkg_id)
        if reg_entry is None:
            violations.append((
                "INV4",
                f"closed_iterations lists {pkg_id!r} as closed but registry has no such item",
            ))
            continue
        if reg_entry.get("status") != "closed":
            violations.append((
                "INV4",
                f"closed_iterations lists {pkg_id!r} as closed but registry shows status={reg_entry['status']!r}",
            ))
    return violations


def _check_inv5_inv6(registry: dict[str, Any]) -> list[Violation]:
    """INV5+INV6: Wave cross-references (schema_version >= 2 only)."""
    violations: list[Violation] = []
    schema_version = registry.get("schema_version", 1)
    if not (isinstance(schema_version, int) and schema_version >= 2):
        return violations  # not applicable

    wave_ids = {w["id"] for w in registry.get("waves", []) if isinstance(w, dict) and "id" in w}
    items_by_id = {
        item["id"]: item
        for item in (registry.get("items") or [])
        if isinstance(item, dict) and "id" in item
    }

    # INV5: items with wave_id must reference existing wave
    for item in (registry.get("items") or []):
        if not isinstance(item, dict):
            continue
        wave_id = item.get("wave_id")
        if wave_id and wave_id not in wave_ids:
            violations.append(("INV5", f"item {item.get('id')!r} references unknown wave_id={wave_id!r}"))

    # INV6: waves.packages entries must exist in items and back-link to this wave
    for wave in registry.get("waves", []):
        if not isinstance(wave, dict):
            continue
        w_id = wave.get("id", "")
        for pkg_id in wave.get("packages", []):
            item = items_by_id.get(pkg_id)
            if item is None:
                violations.append(("INV6", f"wave {w_id!r} references unknown package {pkg_id!r}"))
            elif item.get("wave_id") != w_id:
                violations.append((
                    "INV6",
                    f"wave {w_id!r} package {pkg_id!r} has wave_id={item.get('wave_id')!r} (expected {w_id!r})",
                ))

    return violations


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

FIX_HINTS: dict[str, str] = {
    "INV1": "Run: python scripts/rebuild_user_stories_index.py --write",
    "INV2": "Run: python scripts/rebuild_user_stories_index.py --write",
    "INV3": "Run: python scripts/regenerate_cjm_pain_table.py --write",
    "INV4": "Add or fix the package entry in doc/backlog_registry.yaml",
    "INV5": "Fix wave_id in doc/backlog_registry.yaml items or waves block",
    "INV6": "Fix wave.packages list or item.wave_id in doc/backlog_registry.yaml",
}


def run_checks(explain: bool = False) -> tuple[list[Violation], list[Violation]]:
    """Returns (drift_violations, warn_violations)."""
    registry = _load_registry(BACKLOG_REGISTRY)
    us_index = _load_us_index(US_INDEX)
    closed_iterations = BACKLOG_REGISTRY.with_name("closed_iterations.md")
    closed_refs = _parse_closed_iterations_refs(closed_iterations)
    cjm_rows = _parse_cjm_pain_table(CJM_MD)

    violations: list[Violation] = []
    violations.extend(_check_inv1(us_index, registry))
    violations.extend(_check_inv2(us_index))
    violations.extend(_check_inv3(us_index, cjm_rows))
    violations.extend(_check_inv4(closed_refs, registry))
    violations.extend(_check_inv5_inv6(registry))

    return violations, []  # warnings reserved for future use


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--explain", "-e", action="store_true",
        help="Show detailed violation descriptions and fix hints",
    )
    args = parser.parse_args(argv)

    violations, warnings = run_checks(explain=args.explain)

    if not violations and not warnings:
        print("OK: no drift — all 6 invariants hold")
        return 0

    seen_invs: set[str] = set()
    for inv_id, msg in violations:
        print(f"DRIFT [{inv_id}]: {msg}")
        seen_invs.add(inv_id)

    if args.explain and seen_invs:
        print()
        print("Fix hints:")
        for inv_id in sorted(seen_invs):
            hint = FIX_HINTS.get(inv_id, "See spec")
            print(f"  [{inv_id}] {hint}")

    if violations:
        if not args.explain:
            print()
            print("Run with --explain for fix hints.")
            print("Quick fix: python scripts/rebuild_user_stories_index.py --write && python scripts/regenerate_cjm_pain_table.py --write")
        return 2

    return 1  # warnings only


if __name__ == "__main__":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
