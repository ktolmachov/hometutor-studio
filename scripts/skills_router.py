"""JIT skill recommendations for task routing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = ROOT / "policies" / "skills_router.yaml"


@dataclass(frozen=True)
class SkillRecommendation:
    skill: str
    reason: str
    matched_by: str


def load_policy(path: Path | str = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError("skills router policy must be a mapping")
    return dict(data)


def _norm_path(path: str) -> str:
    return path.strip().replace("\\", "/").lower()


def _matches_path(path: str, rule: Mapping[str, Any]) -> str | None:
    normalized = _norm_path(path)
    for prefix in rule.get("path_prefixes", []) or []:
        p = _norm_path(str(prefix))
        if normalized == p or normalized.startswith(p.rstrip("/") + "/"):
            return f"path_prefix:{prefix}"
    for suffix in rule.get("path_suffixes", []) or []:
        s = str(suffix).lower()
        if normalized.endswith(s):
            return f"path_suffix:{suffix}"
    return None


def recommend(
    *,
    paths: Sequence[str] = (),
    text: str = "",
    policy: Mapping[str, Any] | None = None,
) -> list[SkillRecommendation]:
    """Return de-duplicated skill recommendations ordered by policy rules."""
    doc = policy or load_policy()
    haystack = text.casefold()
    recs: list[SkillRecommendation] = []
    seen: set[str] = set()
    for rule in doc.get("rules", []) or []:
        if not isinstance(rule, Mapping):
            continue
        skill = str(rule.get("skill", "")).strip()
        if not skill or skill in seen:
            continue
        matched_by: str | None = None
        for path in paths:
            matched_by = _matches_path(path, rule)
            if matched_by:
                break
        if matched_by is None:
            for keyword in rule.get("keywords", []) or []:
                needle = str(keyword).casefold()
                if needle and needle in haystack:
                    matched_by = f"keyword:{keyword}"
                    break
        if matched_by:
            seen.add(skill)
            recs.append(
                SkillRecommendation(
                    skill=skill,
                    reason=str(rule.get("reason", "")),
                    matched_by=matched_by,
                )
            )
    return recs
