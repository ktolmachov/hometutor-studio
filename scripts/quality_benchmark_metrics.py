"""Метрики для quality benchmark (hit rate, MRR, lexical relevancy)."""

from __future__ import annotations

import re
from typing import Any


def _tokenize(text: str) -> set[str]:
    raw = (text or "").lower()
    parts = re.findall(r"[\w\-]+", raw, flags=re.UNICODE)
    return {p for p in parts if len(p) > 1}


def word_jaccard(answer: str, reference: str) -> float:
    a, b = _tokenize(answer), _tokenize(reference)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _source_blob(src: dict[str, Any]) -> str:
    parts = [
        str(src.get("file_name") or ""),
        str(src.get("relative_path") or ""),
        str(src.get("doc_id") or ""),
    ]
    return " ".join(parts).lower()


def source_hit_and_rr(
    sources: list[dict[str, Any]], expected_sources: list[str]
) -> tuple[bool, float]:
    """
    Первое вхождение любого из ``expected_sources`` в ранжированном списке источников.

    Возвращает ``(hit, reciprocal_rank)``; если ``expected_sources`` пуст — ``(True, 1.0)``.
    """
    if not expected_sources:
        return True, 1.0
    for i, src in enumerate(sources, start=1):
        blob = _source_blob(src)
        for exp in expected_sources:
            if exp and exp.lower() in blob:
                return True, 1.0 / float(i)
    return False, 0.0


def aggregate_rates(rows: list[dict[str, Any]]) -> dict[str, float]:
    n = len(rows) or 1
    hit = sum(1 for r in rows if r.get("source_hit")) / n
    mrr = sum(float(r.get("reciprocal_rank") or 0.0) for r in rows) / n
    rel = sum(float(r.get("answer_relevancy") or 0.0) for r in rows) / n
    return {"hit_rate": hit, "mean_reciprocal_rank": mrr, "answer_relevancy": rel}
