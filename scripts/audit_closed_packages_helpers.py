"""Helpers for closed-package audit Phase A2.

Mirrors `doc/team_workflow/generate_audit_closed_packages_prompt.md`
(registry period filter, closed_iterations headings, user_stories index).
"""
from __future__ import annotations

import calendar
import re
from datetime import date
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

__all__ = [
    "dstr",
    "parse_scope_csv",
    "parse_period",
    "parse_iso_date_like",
    "date_in_period",
    "iter_registry_items",
    "iter_closed_packages_for_period",
    "iter_closed_packages_for_month",
    "find_closed_iteration_headings_for_period",
    "find_closed_iteration_headings_for_month",
    "user_stories_by_package_for_period",
    "user_stories_by_package_for_month",
    "get_registry_item",
    "get_exit_artifact",
]


def dstr(v: object) -> str:
    """Normalize YAML/JSON date or string to YYYY-MM-DD (or str) for prefix checks."""
    if v is None:
        return ""
    if v == "":
        return ""
    if hasattr(v, "isoformat"):
        return str(v.isoformat())
    return str(v)


def parse_scope_csv(scope_csv: str) -> List[str]:
    return [s.strip() for s in scope_csv.split(",") if s.strip()]


def parse_period(spec: str) -> Tuple[date, date]:
    """Inclusive date range.

    Supported:
    - ``YYYY-MM`` — whole calendar month
    - ``YYYY-MM..YYYY-MM`` — inclusive span of calendar months (start .. end month)
    - ``YYYY-MM-DD..YYYY-MM-DD`` — inclusive exact dates

    Whitespace around ``..`` is allowed. If ``start > end``, bounds are swapped.
    """
    raw = spec.strip()
    if not raw:
        raise ValueError("empty PERIOD")

    if ".." in raw:
        a, b = [x.strip() for x in raw.split("..", 1)]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", a) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", b):
            d1, d2 = date.fromisoformat(a), date.fromisoformat(b)
            if d1 > d2:
                d1, d2 = d2, d1
            return d1, d2
        if re.fullmatch(r"\d{4}-\d{2}", a) and re.fullmatch(r"\d{4}-\d{2}", b):
            y1, m1 = (int(a[:4]), int(a[5:7]))
            y2, m2 = (int(b[:4]), int(b[5:7]))
            start = date(y1, m1, 1)
            last_d = calendar.monthrange(y2, m2)[1]
            end = date(y2, m2, last_d)
            if start > end:
                start, end = end, start
            return start, end
        raise ValueError(
            f"invalid PERIOD range {spec!r}: use YYYY-MM..YYYY-MM or YYYY-MM-DD..YYYY-MM-DD"
        )

    if re.fullmatch(r"\d{4}-\d{2}", raw):
        y, m = int(raw[:4]), int(raw[5:7])
        start = date(y, m, 1)
        last_d = calendar.monthrange(y, m)[1]
        end = date(y, m, last_d)
        return start, end

    raise ValueError(
        f"invalid PERIOD {spec!r}: use YYYY-MM, YYYY-MM..YYYY-MM, or YYYY-MM-DD..YYYY-MM-DD"
    )


def parse_iso_date_like(value: object) -> Optional[date]:
    """Parse YAML/JSON date or ISO prefix to calendar date."""
    raw = dstr(value)
    if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            return None
    # month-only pseudo-date: first day of month (matching behaviour for plain strings)
    if len(raw) == 7 and raw[4] == "-":
        try:
            y, m = int(raw[:4]), int(raw[5:7])
            return date(y, m, 1)
        except ValueError:
            return None
    return None


def date_in_period(d: date, start: date, end: date) -> bool:
    return start <= d <= end


def iter_registry_items(data: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    raw = data.get("items", data.get("packages", []))
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, Mapping)]


def _display_title(p: Mapping[str, Any]) -> str:
    text = p.get("title") or p.get("blocks") or p.get("notes") or ""
    if not isinstance(text, str):
        text = str(text)
    return text.strip().replace("\n", " ")


def _field_hits_period(field_val: object, start: date, end: date) -> bool:
    """True if date or YYYY-MM month bucket intersects ``[start, end]``."""
    raw = dstr(field_val).strip()
    if not raw:
        return False
    if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
        try:
            d = date.fromisoformat(raw[:10])
            return date_in_period(d, start, end)
        except ValueError:
            return False
    if re.fullmatch(r"\d{4}-\d{2}", raw):
        y, m = int(raw[:4]), int(raw[5:7])
        ms = date(y, m, 1)
        me = date(y, m, calendar.monthrange(y, m)[1])
        return not (me < start or ms > end)
    return False


def iter_closed_packages_for_period(
    data: Mapping[str, Any],
    start: date,
    end: date,
    scopes: Sequence[str],
) -> Iterator[Dict[str, Any]]:
    want = set(scopes)
    for p in iter_registry_items(data):
        st = p.get("status")
        if st not in want:
            continue
        lr_raw, cr_raw = p.get("last_review"), p.get("closed_date")
        if not (_field_hits_period(lr_raw, start, end) or _field_hits_period(cr_raw, start, end)):
            continue
        lr, cr = dstr(lr_raw), dstr(cr_raw)
        pid = p.get("id")
        if not isinstance(pid, str):
            continue
        yield {
            "id": pid,
            "title": _display_title(p),
            "date_for_display": lr or cr,
            "last_review": lr,
            "closed_date": cr,
            "exit_artifact": p.get("exit_artifact") or "",
        }


def iter_closed_packages_for_month(
    data: Mapping[str, Any],
    month: str,
    scopes: Sequence[str],
) -> Iterator[Dict[str, Any]]:
    """Backward-compatible: ``month`` is ``YYYY-MM`` (whole calendar month)."""
    start, end = parse_period(month)
    return iter_closed_packages_for_period(data, start, end, scopes)


def find_closed_iteration_headings_for_period(
    content: str, start: date, end: date
) -> List[tuple[str, str]]:
    """Return (package_id, ymd) for ``### <id> — YYYY-MM-DD`` headings where date ⊆ [start,end]."""
    pat = re.compile(r"^###\s+(\S+)\s+—\s+(\d{4}-\d{2}-\d{2})", re.MULTILINE)
    out: List[tuple[str, str]] = []
    for m in pat.finditer(content):
        ymd = date.fromisoformat(m.group(2))
        if date_in_period(ymd, start, end):
            out.append((m.group(1), m.group(2)))
    return out


def find_closed_iteration_headings_for_month(content: str, month: str) -> List[tuple[str, str]]:
    """Backward-compatible wrapper for one ``YYYY-MM`` month."""
    start, end = parse_period(month)
    return find_closed_iteration_headings_for_period(content, start, end)


def _user_story_root(data: Any) -> List[Mapping[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, Mapping)]
    if isinstance(data, dict):
        arr = data.get("items", data.get("stories", []))
        if isinstance(arr, list):
            return [x for x in arr if isinstance(x, Mapping)]
    return []


def user_stories_by_package_for_period(
    data: Any,
    start: date,
    end: date,
) -> Dict[str, List[str]]:
    seen: Dict[str, List[str]] = {}
    for us in _user_story_root(data):
        if not _field_hits_period(us.get("closed_date"), start, end):
            continue
        pkg = (us.get("covered_by") or "") or ""
        if not isinstance(pkg, str):
            pkg = str(pkg)
        uid = us.get("us_id", us.get("id", ""))
        if not isinstance(uid, str):
            uid = str(uid) if uid is not None else ""
        if not uid:
            continue
        seen.setdefault(pkg, []).append(uid)
    for k in list(seen.keys()):
        seen[k] = sorted(seen[k])
    return dict(sorted(seen.items()))


def user_stories_by_package_for_month(
    data: Any,
    month: str,
) -> Dict[str, List[str]]:
    """Backward-compatible: ``month`` is ``YYYY-MM``."""
    start, end = parse_period(month)
    return user_stories_by_package_for_period(data, start, end)


def get_registry_item(data: Mapping[str, Any], package_id: str) -> Optional[Mapping[str, Any]]:
    for p in iter_registry_items(data):
        if p.get("id") == package_id:
            return p
    return None


def get_exit_artifact(data: Mapping[str, Any], package_id: str) -> str:
    p = get_registry_item(data, package_id)
    if p is None:
        return "NOT_FOUND"
    ex = p.get("exit_artifact", "")
    if ex is None:
        return ""
    if not isinstance(ex, str):
        return str(ex)
    return ex
