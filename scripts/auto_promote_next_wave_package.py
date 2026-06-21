#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_promote_next_wave_package.py — Автоматически активирует следующий пакет волны в registry.

Когда в registry нет активного ready/wip пакета, находит следующий готовый пакет
из active wave в backlog_registry.yaml и переводит его в ready. tasklist.md
после этого только регенерируется как derived view.

Критерии выбора:
1. Пакет из активной волны (из waves/active_wave_id в backlog_registry.yaml)
2. Статус proposed/ready/open (и не closed/completed/deferred/frozen)
3. Все depends_on уже закрыты

Использование:
    python scripts/auto_promote_next_wave_package.py          # активировать кандидата в registry
    python scripts/auto_promote_next_wave_package.py --dry-run # показать кандидата без записи
    python scripts/auto_promote_next_wave_package.py --list    # перечислить готовых кандидатов

Выход:
    0 — кандидат активирован (или active registry view уже не пуст)
    1 — нет кандидатов (active registry view пуст, волна исчерпана)
    2 — ошибка парсинга/записи
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
import json

try:
    import yaml
    _YAML_OK = True
except ImportError:
    _YAML_OK = False

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _perf_timer import PhaseTimer  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BACKLOG_REGISTRY = ROOT / "doc" / "backlog_registry.yaml"
USER_STORIES_INDEX = ROOT / "doc" / "user_stories_index.json"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class WavePackage:
    id: str
    wave_id: str
    wave_position: int
    status: str
    user_stories: list[str] = field(default_factory=list)
    cjm_moments: list[str] = field(default_factory=list)
    blocks: str = ""
    depends_on: list[str] = field(default_factory=list)
    write_set_max: int = 5
    read_set_hint: list[str] = field(default_factory=list)
    exit_artifact: str = ""
    notes: str = ""
    cost_estimate: str = "M"
    dod_commands: list[str] = field(default_factory=list)

    @property
    def contract_id(self) -> str:
        """Short contract id without 'epoch-' prefix."""
        return self.id.removeprefix("epoch-")


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _get_active_wave_from_registry() -> str | None:
    """Determine active wave id reading only from backlog_registry.yaml.

    Uses same priority logic as backlog_registry_lint.get_active_wave:
    explicit active_wave_id → first wip wave → first ready wave → first proposed wave.
    """
    if not _YAML_OK or not BACKLOG_REGISTRY.exists():
        return None
    try:
        data = yaml.safe_load(BACKLOG_REGISTRY.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    # Check explicit active_wave_id
    explicit = data.get("active_wave_id")
    if explicit:
        waves = data.get("waves") or []
        w = next((w for w in waves if isinstance(w, dict) and w.get("id") == explicit), None)
        if w and str(w.get("status", "")).strip().lower() not in ("completed", "frozen"):
            return str(explicit)
    waves = data.get("waves") or []
    for target_status in ("wip", "ready", "proposed"):
        matched = [w for w in waves if isinstance(w, dict) and str(w.get("status", "")).strip().lower() == target_status]
        if matched:
            return str(matched[0]["id"])
    return None


def _get_now_package_ids_from_registry() -> list[str]:
    """Return ids of registry-active packages (status wip or ready)."""
    if not _YAML_OK or not BACKLOG_REGISTRY.exists():
        return []
    try:
        data = yaml.safe_load(BACKLOG_REGISTRY.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = data.get("items", []) if isinstance(data, dict) else []
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("status", "")).strip().lower() in ("wip", "ready"):
            item_id = str(item.get("id", "")).strip()
            if item_id:
                result.append(item_id)
                if item_id.startswith("epoch-"):
                    result.append(item_id.removeprefix("epoch-"))
    return result


def _load_wave_packages(active_wave: str) -> list[WavePackage]:
    """Load packages from backlog_registry.yaml for the given wave."""
    if not _YAML_OK:
        print("ERROR: pyyaml not installed", file=sys.stderr)
        return []
    if not BACKLOG_REGISTRY.exists():
        print(f"ERROR: {BACKLOG_REGISTRY} not found", file=sys.stderr)
        return []

    with BACKLOG_REGISTRY.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    items = data.get("items", []) or data.get("packages", [])
    result = []
    for item in items:
        if item.get("wave_id") != active_wave:
            continue
        rsh = item.get("read_set_hint") or []
        if isinstance(rsh, str):
            rsh = [rsh]
        dod = item.get("dod_commands") or []
        if isinstance(dod, str):
            dod = [dod]
        result.append(WavePackage(
            id=item["id"],
            wave_id=item.get("wave_id", ""),
            wave_position=item.get("wave_position", 99),
            status=item.get("status", "proposed"),
            user_stories=item.get("user_stories", []) or [],
            cjm_moments=item.get("cjm_moments", []) or [],
            blocks=item.get("blocks", ""),
            depends_on=item.get("depends_on", []) or [],
            write_set_max=item.get("write_set_max", 5),
            read_set_hint=rsh,
            exit_artifact=item.get("exit_artifact", ""),
            notes=item.get("notes", ""),
            cost_estimate=item.get("cost_estimate", "M"),
            dod_commands=dod,
        ))
    result.sort(key=lambda p: p.wave_position)
    return result


def _load_wave_packages_map() -> dict[str, list[WavePackage]]:
    """Load all wave packages grouped by wave_id."""
    if not _YAML_OK:
        print("ERROR: pyyaml not installed", file=sys.stderr)
        return {}
    if not BACKLOG_REGISTRY.exists():
        print(f"ERROR: {BACKLOG_REGISTRY} not found", file=sys.stderr)
        return {}

    with BACKLOG_REGISTRY.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    items = data.get("items", []) or data.get("packages", [])
    grouped: dict[str, list[WavePackage]] = {}
    for item in items:
        wave_id = item.get("wave_id")
        if not wave_id:
            continue
        rsh = item.get("read_set_hint") or []
        if isinstance(rsh, str):
            rsh = [rsh]
        dod = item.get("dod_commands") or []
        if isinstance(dod, str):
            dod = [dod]
        grouped.setdefault(wave_id, []).append(
            WavePackage(
                id=item["id"],
                wave_id=wave_id,
                wave_position=item.get("wave_position", 99),
                status=item.get("status", "proposed"),
                user_stories=item.get("user_stories", []) or [],
                cjm_moments=item.get("cjm_moments", []) or [],
                blocks=item.get("blocks", ""),
                depends_on=item.get("depends_on", []) or [],
                write_set_max=item.get("write_set_max", 5),
                read_set_hint=rsh,
                exit_artifact=item.get("exit_artifact", ""),
                notes=item.get("notes", ""),
                cost_estimate=item.get("cost_estimate", "M"),
                dod_commands=dod,
            )
        )
    for wave_id in grouped:
        grouped[wave_id].sort(key=lambda p: p.wave_position)
    return grouped


def _load_closed_item_ids_from_registry() -> set[str]:
    """Load closed package ids directly from backlog registry."""
    if not _YAML_OK or not BACKLOG_REGISTRY.exists():
        return set()
    try:
        data = yaml.safe_load(BACKLOG_REGISTRY.read_text(encoding="utf-8"))
    except Exception:
        return set()
    items = data.get("items", []) if isinstance(data, dict) else []
    closed: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("status", "")).strip().lower() != "closed":
            continue
        item_id = str(item.get("id", "")).strip()
        if not item_id:
            continue
        closed.add(item_id)
        if item_id.startswith("epoch-"):
            closed.add(item_id.removeprefix("epoch-"))
    return closed


def _load_story_index() -> dict[str, dict]:
    """Load US index as map us_id -> metadata."""
    if not USER_STORIES_INDEX.exists():
        return {}
    try:
        payload = json.loads(USER_STORIES_INDEX.read_text(encoding="utf-8"))
    except Exception:
        return {}
    items = payload.get("items", []) if isinstance(payload, dict) else []
    result: dict[str, dict] = {}
    for entry in items:
        if isinstance(entry, dict) and isinstance(entry.get("us_id"), str):
            result[entry["us_id"]] = entry
    return result


def _is_story_open_and_uncovered(story_meta: dict | None) -> bool:
    if not isinstance(story_meta, dict):
        return False
    status = str(story_meta.get("status", "")).strip().lower()
    covered_by = story_meta.get("covered_by")
    covered_norm = str(covered_by).strip().lower() if covered_by is not None else ""
    # Index marks uncovered open stories as covered_by: "open" (see backlog_registry_lint).
    return status == "open" and covered_norm in {"", "none", "null", "n/a", "open"}


def _first_promotable(
    wave_packages: list[WavePackage],
    *,
    closed: set[str],
    now_packages: list[str],
    promotable_statuses: set[str],
    story_index: dict[str, dict],
    verbose: bool,
    wave_label: str,
) -> WavePackage | None:
    """Pick first package that can be auto-promoted from a wave."""
    for pkg in wave_packages:
        short_id = pkg.contract_id
        full_id = pkg.id
        if short_id in now_packages or full_id in now_packages:
            if verbose:
                print(f"  Skip {short_id}: already active in registry")
            continue
        if short_id in closed or full_id in closed:
            if verbose:
                print(f"  Skip {short_id}: already closed")
            continue
        if str(pkg.status).strip().lower() not in promotable_statuses:
            if verbose:
                print(f"  Skip {short_id}: status={pkg.status!r} not promotable")
            continue
        if not pkg.user_stories:
            # Infra/doc/pipeline packages legitimately have no user stories.
            # Warn but do NOT block — lint allows ready status without user_stories.
            if verbose:
                print(f"  ⚠ {short_id}: has no user_stories — promoting (infra/doc package)")
        else:
            # Guard: ready/wip lint requires referenced user stories to be open and uncovered.
            bad_story = next(
                (us for us in pkg.user_stories if not _is_story_open_and_uncovered(story_index.get(us))),
                None,
            )
            if bad_story:
                if verbose:
                    print(f"  Skip {short_id}: user story '{bad_story}' is not open/uncovered")
                continue
        deps_ok = True
        for dep in pkg.depends_on:
            dep_short = dep.removeprefix("epoch-")
            if dep_short not in closed and dep not in closed:
                if verbose:
                    print(f"  Skip {short_id}: dependency '{dep}' not closed")
                deps_ok = False
                break
        if deps_ok:
            if verbose:
                print(f"  ✓ Candidate ({wave_label}): {short_id} (wave_position={pkg.wave_position})")
            return pkg
    return None


def find_next_candidate(*, verbose: bool = False) -> WavePackage | None:
    """Find the next wave package ready to be promoted in backlog_registry.yaml.

    Reads exclusively from backlog_registry.yaml (and user_stories_index.json).

    Returns None if no suitable candidate found.
    """
    # Authoritative source: registry only. No markdown parsing for decisions.
    closed = _load_closed_item_ids_from_registry()
    now_packages = _get_now_package_ids_from_registry()
    active_wave = _get_active_wave_from_registry()

    if verbose:
        print(f"  Active wave (from registry): {active_wave}")
        print(f"  Active packages (registry): {now_packages}")
        print(f"  Closed packages ({len(closed)}): {sorted(closed)[:5]}...")

    promotable_statuses = {"proposed", "open"}  # ready/wip are already active
    story_index = _load_story_index()

    if active_wave:
        wave_packages = _load_wave_packages(active_wave)
        if verbose:
            print(f"  Wave packages ({len(wave_packages)}): {[p.id for p in wave_packages]}")
        candidate = _first_promotable(
            wave_packages,
            closed=closed,
            now_packages=now_packages,
            promotable_statuses=promotable_statuses,
            story_index=story_index,
            verbose=verbose,
            wave_label=active_wave,
        )
        if candidate:
            return candidate

    # Fallback: scan all waves for a promotable package.
    grouped = _load_wave_packages_map()
    if not grouped:
        if verbose:
            print("  No waves found in registry — returning None")
        return None
    skip_wave = active_wave or ""

    def get_wave_priority(wave_id: str) -> int:
        # Priority of the wave is the minimum wave_position of its packages
        return min((p.wave_position for p in grouped[wave_id]), default=99)

    other_waves = sorted((w for w in grouped if w != skip_wave), key=get_wave_priority)
    for wave_id in other_waves:
        candidate = _first_promotable(
            grouped[wave_id],
            closed=closed,
            now_packages=now_packages,
            promotable_statuses=promotable_statuses,
            story_index=story_index,
            verbose=verbose,
            wave_label=wave_id,
        )
        if candidate:
            return candidate

    return None


# ---------------------------------------------------------------------------
# Contract block generation
# ---------------------------------------------------------------------------

def _build_contract_block(pkg: WavePackage) -> str:
    """Build a contract block from backlog_registry data (real DoD commands, no placeholders)."""
    cid = pkg.id  # Use full id (with epoch- prefix) to match lint._render_active_contracts format
    us_list = ", ".join(pkg.user_stories) if pkg.user_stories else "n/a"
    cjm = pkg.cjm_moments[0] if pkg.cjm_moments else "unknown"
    outcomes = pkg.blocks or pkg.exit_artifact or "(see notes)"
    read_hint = "\n".join(f"  - {r}" for r in pkg.read_set_hint) if pkg.read_set_hint else "  - (see backlog_registry.yaml)"
    notes_line = f"\n- **Notes:** {pkg.notes}" if pkg.notes else ""

    if pkg.dod_commands:
        dod_str = "\n".join(f"  - `{cmd}`" for cmd in pkg.dod_commands)
    else:
        dod_str = "  - (add dod_commands to backlog_registry.yaml)"

    return f"""
### {cid} Contract

<!-- GENERATED from backlog_registry.yaml — do not edit manually -->

- **Title:** {outcomes[:120]}
- **CJM:** #{cjm}
- **User story:** {us_list}
- **DoD commands:**
{dod_str}
- **Outcomes:**
  - {outcomes}
- **Write-set max:** {pkg.write_set_max} files
- **Target artifacts:** {pkg.exit_artifact or outcomes[:80]}
- **Read-set hint:**
{read_hint}{notes_line}
"""


def _update_registry_status(pkg: WavePackage, new_status: str = "ready") -> bool:
    """
    Update the package's status in backlog_registry.yaml to new_status.
    Returns True if updated, False if not found or yaml unavailable.
    """
    if not _YAML_OK or not BACKLOG_REGISTRY.exists():
        return False
    try:
        text = BACKLOG_REGISTRY.read_text(encoding="utf-8")
        # Update status for the package (by full id or short id)
        targets = {pkg.id, pkg.contract_id, f"epoch-{pkg.contract_id}"}
        updated = False
        lines = text.splitlines(keepends=True)
        in_target = False
        result_lines = []
        for line in lines:
            # Detect entry start: "  - id: <pkg_id>"
            if re.match(r"\s*-\s+id:\s+(" + "|".join(re.escape(t) for t in targets) + r")\s*$", line):
                in_target = True
            elif in_target and re.match(r"\s*-\s+id:", line):
                in_target = False  # Different item started
            # Strict indentation match: "  status:" or "    status:" (BUG-12)
            if in_target and re.match(r"^( {2,6})status:\s+", line):
                old_status = re.sub(r"^( {2,6})status:\s+", "", line).strip()
                if old_status != new_status:
                    line = re.sub(r"^( {2,6}status:\s+)\S+", rf"\g<1>{new_status}", line)
                    updated = True
                in_target = False
            result_lines.append(line)
        if updated:
            BACKLOG_REGISTRY.write_text("".join(result_lines), encoding="utf-8")
        return updated
    except Exception as exc:
        print(f"  ⚠ Could not update backlog_registry.yaml: {exc}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    timer = PhaseTimer()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", "-n", action="store_true", help="Show candidate without writing")
    parser.add_argument("--list", "-l", action="store_true", help="List all ready candidates")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if not BACKLOG_REGISTRY.exists():
        print(f"ERROR: {BACKLOG_REGISTRY} not found", file=sys.stderr)
        return 2

    # List mode — all reads from registry only
    if args.list:
        closed = _load_closed_item_ids_from_registry()
        now_packages = _get_now_package_ids_from_registry()
        active_wave = _get_active_wave_from_registry()
        print(f"Active wave (registry): {active_wave or '(none)'}")
        print(f"Active packages (registry): {now_packages or '(empty)'}")
        if active_wave:
            wave_pkgs = _load_wave_packages(active_wave)
            print(f"\nCandidates from {active_wave}:")
            for pkg in wave_pkgs:
                cid = pkg.contract_id
                if cid in now_packages or pkg.id in now_packages:
                    sym = "→"
                elif cid in closed or pkg.id in closed:
                    sym = "✓"
                else:
                    deps_ok = all(
                        d.removeprefix("epoch-") in closed or d in closed
                        for d in pkg.depends_on
                    )
                    sym = "★" if deps_ok else "⋯"
                print(f"  {sym} [{pkg.wave_position}] {cid} (deps: {pkg.depends_on})")
        return 0

    try:
        # Check if registry already has active (wip/ready) packages
        now_packages = _get_now_package_ids_from_registry()
        if now_packages:
            print(f"Registry already has active packages: {now_packages}")
            return 0

        with timer.phase("find_next_candidate"):
            candidate = find_next_candidate(verbose=args.verbose)
        if candidate is None:
            print(
                "ℹ  No ready wave package found. Either:\n"
                "   - All wave packages are closed (phase complete!)\n"
                "   - Dependencies not yet satisfied\n"
                "   - Update Wave queue manually or run plan-next.",
                file=sys.stderr,
            )
            return 1

        cid = candidate.contract_id
        print(f"→ Auto-promoting: {cid} (wave={candidate.wave_id}, pos={candidate.wave_position})")
        print(f"  Depends on: {candidate.depends_on}")
        print(f"  User stories: {candidate.user_stories}")

        if args.dry_run:
            print("\n--- Contract block (dry run) ---")
            print(_build_contract_block(candidate))
            print("--- (no files written) ---")
            return 0

        with timer.phase("promote_to_now"):
            if _update_registry_status(candidate, new_status="ready"):
                print(f"  ✓ Updated {candidate.id} status → 'ready' in backlog_registry.yaml")
            else:
                print(f"  ⚠ backlog_registry.yaml not updated (check manually if sync_check fails)")

            import subprocess
            sync_cmd = [sys.executable, "scripts/backlog_registry_lint.py", "--sync-from-index", "--write-sync"]
            try:
                result = subprocess.run(sync_cmd, cwd=str(ROOT))
                if result.returncode != 0:
                    # Lint failed — roll back registry status to avoid registry/tasklist drift
                    print(
                        f"  ⚠ backlog_registry_lint.py exited {result.returncode} — "
                        f"rolling back {candidate.id} status to 'proposed' to keep SSoT consistent.",
                        file=sys.stderr,
                    )
                    _update_registry_status(candidate, new_status="proposed")
                    return 2
            except Exception as exc:
                print(
                    f"  ⚠ Sync step raised exception: {exc} — "
                    f"rolling back {candidate.id} status to 'proposed'.",
                    file=sys.stderr,
                )
                _update_registry_status(candidate, new_status="proposed")
                return 2
            print(f"  ✓ Regenerated doc/tasklist.md from registry.")


        print(f"  Next: run orchestration or generate next prompt for {cid}")
        return 0
    finally:
        timer.flush()
        timer.total_only_when_top_level()


if __name__ == "__main__":
    # Ensure unicode works in Windows terminal
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
