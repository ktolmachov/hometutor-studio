"""Контрактные проверки для EQE-A: tests/eval/golden_qa.jsonl (golden dataset).

Верификация expected_sources (ключи AskSource, а не внутренние fragment_id):
- Референсный KB: ``eval_data/quality_benchmark_kb`` (mini-KB для US-12.1).
- Список допустимых имён файлов: ``Get-ChildItem eval_data/quality_benchmark_kb`` (PowerShell)
  или ``dir eval_data\\quality_benchmark_kb`` / ``ls eval_data/quality_benchmark_kb``.
- Дополнительное согласование паттерна expected_sources с ``eval_data/quality_benchmark.json``
  (поле expected_sources — имена ``*.md`` из того же каталога).

См. пакет ``epoch-answer-quality-eval`` в ``doc/backlog_registry.yaml`` (SSoT); человекочитаемый
снимок — ``doc/tasklist.md``. Фаза A / EQE; публичный контракт источников —
``AskSource`` в ``app/api_models.py`` (relative_path / file_name / page).
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.eval.run_eval import _validate_dataset

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = REPO_ROOT / "tests" / "eval" / "golden_qa.jsonl"
REFERENCE_KB_DIR = REPO_ROOT / "eval_data" / "quality_benchmark_kb"
REFERENCE_KB_FILES = frozenset(
    p.name for p in REFERENCE_KB_DIR.glob("*.md") if p.is_file()
)
CATEGORY_TAGS = frozenset({"factual", "multi-hop", "out-of-corpus", "tutor-mode", "edge"})


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise AssertionError(f"{path}: invalid JSONL at line {line_no}: {exc}") from exc
    return rows


def test_golden_qa_jsonl_contract() -> None:
    assert GOLDEN_PATH.is_file(), f"missing {GOLDEN_PATH}"
    assert REFERENCE_KB_DIR.is_dir(), f"missing reference KB {REFERENCE_KB_DIR}"
    assert REFERENCE_KB_FILES, f"no *.md under {REFERENCE_KB_DIR}"

    cases = _read_jsonl(GOLDEN_PATH)
    _validate_dataset(cases, require_full_contract=True)

    for item in cases:
        cid = item["id"]
        diff = item.get("difficulty")
        assert isinstance(diff, str) and diff.strip(), f"{cid}: difficulty must be non-empty str"
        concepts = item.get("expected_concepts")
        assert isinstance(concepts, list) and concepts, f"{cid}: expected_concepts must be non-empty list"
        assert all(isinstance(c, str) and c.strip() for c in concepts), f"{cid}: expected_concepts strings"
        tags = item.get("tags") or []
        primary = [t for t in tags if t in CATEGORY_TAGS]
        assert len(primary) == 1, f"{cid}: must have exactly one category tag, got {primary!r} in {tags!r}"

        srcs = list(item.get("expected_sources") or [])
        if "out-of-corpus" in tags:
            assert srcs == [], f"{cid}: out-of-corpus cases must have expected_sources == []"
        else:
            assert srcs, f"{cid}: in-corpus cases need non-empty expected_sources"
            for s in srcs:
                assert isinstance(s, dict), f"{cid}: expected_source entry must be object, got {s!r}"
                forbidden = {"id", "node_id", "node_ids"} & set(s)
                assert not forbidden, f"{cid}: expected_source must not use internal ids: {sorted(forbidden)}"
                rel = s.get("relative_path")
                name = s.get("file_name")
                assert (
                    isinstance(rel, str) and rel.strip()
                ) or (
                    isinstance(name, str) and name.strip()
                ), f"{cid}: expected_source must include relative_path or file_name"
                source_key = rel if isinstance(rel, str) and rel.strip() else name
                assert isinstance(source_key, str)
                base = source_key.replace("\\", "/").rsplit("/", 1)[-1]
                assert base in REFERENCE_KB_FILES, (
                    f"{cid}: expected_sources entry {s!r} not found in reference KB filenames "
                    f"{sorted(REFERENCE_KB_FILES)}"
                )
