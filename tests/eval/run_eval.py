#!/usr/bin/env python3
"""Answer-quality eval runner for the public POST /ask contract."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
for candidate in (ROOT, SCRIPTS_DIR):
    value = str(candidate)
    if value not in sys.path:
        sys.path.insert(0, value)

from script_stdio_utf8 import configure_stdio_utf8

DEFAULT_DATASET = Path(__file__).resolve().with_name("golden_qa.jsonl")
DEFAULT_THRESHOLDS = Path(__file__).resolve().with_name("thresholds.json")
DEFAULT_EVAL_CORPUS = Path(__file__).resolve().with_name("corpus")
SCHEMA_VERSION = 1
OUT_OF_CORPUS_PHRASES = (
    "недостаточно информации",
    "не найден",
    "не найдено",
    "не наш",
)

CaseTransport = Callable[[dict[str, Any], dict[str, Any]], tuple[int, dict[str, Any]]]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _portable_path(path: Path) -> str:
    """Return a stable repo-relative path when possible."""
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}: invalid JSONL at line {line_no}: {exc}") from exc
    return rows


def _validate_dataset(cases: list[dict[str, Any]], *, require_full_contract: bool) -> None:
    required = {"id", "question", "expected_sources", "expected_concepts", "difficulty", "tags"}
    missing_ids: list[str] = []
    seen_ids: set[str] = set()
    counts = {
        "factual": 0,
        "multi-hop": 0,
        "out-of-corpus": 0,
        "tutor-mode": 0,
        "edge": 0,
    }
    for item in cases:
        case_id = str(item.get("id") or "").strip()
        if not case_id:
            missing_ids.append("<missing-id>")
        elif case_id in seen_ids:
            raise SystemExit(f"Duplicate eval case id: {case_id}")
        else:
            seen_ids.add(case_id)
        missing = sorted(required - set(item))
        if missing:
            raise SystemExit(f"Eval case {case_id or '<missing-id>'} is missing fields: {', '.join(missing)}")
        if not isinstance(item.get("expected_sources"), list):
            raise SystemExit(f"Eval case {case_id} must define expected_sources as a list")
        for index, expected_source in enumerate(item.get("expected_sources") or [], start=1):
            if isinstance(expected_source, str):
                if require_full_contract:
                    raise SystemExit(
                        f"Eval case {case_id} expected_sources[{index}] must use public AskSource fields"
                    )
                continue
            if not isinstance(expected_source, dict):
                raise SystemExit(f"Eval case {case_id} expected_sources[{index}] must be a string or object")
            if any(key in expected_source for key in ("node_id", "node_ids", "id")):
                raise SystemExit(f"Eval case {case_id} expected_sources[{index}] must not use internal node ids")
            if not (expected_source.get("relative_path") or expected_source.get("file_name")):
                raise SystemExit(
                    f"Eval case {case_id} expected_sources[{index}] must include relative_path or file_name"
                )
        if not isinstance(item.get("expected_concepts"), list):
            raise SystemExit(f"Eval case {case_id} must define expected_concepts as a list")
        tags = item.get("tags")
        if not isinstance(tags, list) or not tags:
            raise SystemExit(f"Eval case {case_id} must define non-empty tags")
        for tag in counts:
            if tag in tags:
                counts[tag] += 1
    if missing_ids:
        raise SystemExit(f"Eval dataset contains cases without id: {missing_ids}")
    if require_full_contract:
        if len(cases) != 20:
            raise SystemExit(f"Expected 20 eval cases, got {len(cases)}")
        expected_counts = {
            "factual": 8,
            "multi-hop": 4,
            "out-of-corpus": 3,
            "tutor-mode": 3,
            "edge": 2,
        }
        if counts != expected_counts:
            raise SystemExit(f"Eval dataset category counts mismatch: expected {expected_counts}, got {counts}")


def _normalize_source_key(value: str | None) -> str:
    return (value or "").strip().lower()


def _source_keys(source: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    rel = _normalize_source_key(source.get("relative_path"))
    name = _normalize_source_key(source.get("file_name"))
    page = _normalize_source_key(source.get("page"))
    for base in (rel, name):
        if not base:
            continue
        keys.add(base)
        basename = base.replace("\\", "/").rsplit("/", 1)[-1]
        if basename:
            keys.add(basename)
        if page and page != "?":
            keys.add(f"{base}::{page}")
            if basename:
                keys.add(f"{basename}::{page}")
    return keys


def _source_display_key(source: dict[str, Any]) -> str:
    rel = _normalize_source_key(source.get("relative_path"))
    if rel:
        return rel
    name = _normalize_source_key(source.get("file_name"))
    if name:
        return name
    return ""


def _expected_source_keys(expected_source: Any) -> set[str]:
    if isinstance(expected_source, str):
        normalized = _normalize_source_key(expected_source)
        return {normalized} if normalized else set()
    if isinstance(expected_source, dict):
        return _source_keys(expected_source)
    return set()


def _source_match_summary(sources: list[dict[str, Any]], expected_sources: list[Any]) -> dict[str, Any]:
    top_sources = list(sources[:3])
    expected: set[str] = set()
    for item in expected_sources:
        expected.update(_expected_source_keys(item))
    matched: list[str] = []
    retrieved: list[str] = []
    for source in top_sources:
        display_key = _source_display_key(source)
        if display_key:
            retrieved.append(display_key)
        keys = _source_keys(source)
        if expected and any(item in keys for item in expected):
            matched.append(display_key or "<matched>")
    precision = None if not expected else round(len(matched) / 3.0, 3)
    return {
        "retrieved_sources": retrieved,
        "retrieved_sources_top3": retrieved,
        "matched_sources": matched,
        "source_precision_at_3": precision,
    }


def _extract_latency_sec(payload: dict[str, Any], *, fallback_wall_sec: float) -> float:
    debug = payload.get("debug") if isinstance(payload.get("debug"), dict) else {}
    for key in ("total_answer_ms", "pipeline_ms", "query_execute_ms"):
        raw = debug.get(key)
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if value > 0:
            return round(value / 1000.0, 3)
    return round(fallback_wall_sec, 3)


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * 0.95 + 0.999999) - 1))
    return round(float(ordered[index]), 3)


def _is_tutor_case(case: dict[str, Any]) -> bool:
    return "tutor-mode" in (case.get("tags") or [])


def _is_out_of_corpus(case: dict[str, Any]) -> bool:
    return "out-of-corpus" in (case.get("tags") or [])


def _is_trivial_in_corpus_case(case: dict[str, Any]) -> bool:
    """Easy in-corpus golden rows (US-3.6 / CJM «тривиальный вопрос» gate)."""
    if _is_out_of_corpus(case):
        return False
    if str(case.get("difficulty") or "").strip().lower() != "easy":
        return False
    return bool(case.get("expected_sources"))


def _answer_is_graceful_not_found(answer: str) -> bool:
    normalized = (answer or "").strip().lower()
    return any(token in normalized for token in OUT_OF_CORPUS_PHRASES)


def _mock_answer_text(case: dict[str, Any]) -> str:
    question = str(case.get("question") or "").strip()
    concepts = ", ".join(case.get("expected_concepts") or [])
    if _is_out_of_corpus(case):
        return "В доступных материалах недостаточно информации по этому вопросу."
    if _is_tutor_case(case):
        return (
            f"Разберем тему по шагам: {question} "
            f"Ключевые идеи: {concepts}. "
            "Вопрос для самопроверки: как ты объяснишь это своими словами?"
        ).strip()
    return f"Краткий ответ по теме '{question}'. Ключевые идеи: {concepts}.".strip()


def _mock_sources(case: dict[str, Any]) -> list[dict[str, Any]]:
    if _is_out_of_corpus(case):
        return []
    out = []
    seeds = list(case.get("expected_sources") or [])
    if not seeds:
        return out
    while len(seeds) < 3:
        seeds.append(seeds[-1])
    for index, seed in enumerate(seeds[:3], start=1):
        if isinstance(seed, dict):
            key = _source_display_key(seed) or str(seed.get("file_name") or "")
            page = str(seed.get("page") or "?")
        else:
            key = str(seed)
            page = "?"
        out.append(
            {
                "cite_index": index,
                "route": "mock",
                "rank_reason": "mock expected source",
                "file_name": key,
                "relative_path": key,
                "page": page,
                "score": round(max(0.5, 1.0 - ((index - 1) * 0.1)), 3),
                "text": f"Mock context excerpt for {key}",
            }
        )
    return out


def _build_mock_transport() -> CaseTransport:
    def _transport(body: dict[str, Any], case: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        query_mode = str(body.get("query_mode") or "").strip().lower() or "qa"
        answer = _mock_answer_text(case)
        payload: dict[str, Any] = {
            "answer": answer,
            "sources": _mock_sources(case),
            "debug": {
                "query_mode": query_mode if query_mode != "qa" else None,
                "query_type": "tutor" if query_mode == "tutor" else "qa",
                "total_answer_ms": 50.0 if query_mode == "tutor" else 35.0,
                "pipeline_ms": 30.0 if query_mode == "tutor" else 20.0,
            },
        }
        if query_mode == "tutor":
            payload["tutor"] = {"teaching": {"summary": answer}}
        return 200, payload

    return _transport


def _build_live_transport() -> tuple[Any, CaseTransport]:
    from fastapi.testclient import TestClient

    from app.api import app

    client = TestClient(app)

    def _transport(body: dict[str, Any], case: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        response = client.post("/ask", json=body)
        payload = {}
        try:
            payload = response.json()
        except ValueError:
            payload = {"detail": response.text}
        return response.status_code, payload

    return client, _transport


def _build_eval_transport(eval_index) -> tuple[Any, CaseTransport]:
    from llama_index.core import VectorStoreIndex

    if not isinstance(eval_index, VectorStoreIndex):
        raise ValueError("eval_index must be a VectorStoreIndex")

    query_engine = eval_index.as_query_engine(similarity_top_k=3)

    def _transport(body: dict[str, Any], case: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        question = str(body.get("question") or "").strip()
        query_mode = str(body.get("query_mode") or "").strip().lower() or "qa"

        try:
            response = query_engine.query(question)
            sources = []
            for i, node in enumerate(response.source_nodes, start=1):
                metadata = node.node.metadata or {}
                sources.append({
                    "cite_index": i,
                    "route": "eval",
                    "rank_reason": "similarity",
                    "file_name": metadata.get("file_name", "unknown"),
                    "relative_path": metadata.get("file_name", "unknown"),
                    "page": metadata.get("page", "?"),
                    "score": node.score if hasattr(node, "score") else 1.0,
                    "text": node.node.get_content()[:200] if node.node else "",
                })

            answer = response.response or ""
            if query_mode == "tutor":
                payload = {
                    "answer": answer,
                    "sources": sources,
                    "debug": {
                        "query_mode": "tutor",
                        "query_type": "tutor",
                        "total_answer_ms": 50.0,
                        "pipeline_ms": 30.0,
                    },
                    "tutor": {"teaching": {"summary": answer}},
                }
            else:
                payload = {
                    "answer": answer,
                    "sources": sources,
                    "debug": {
                        "query_mode": query_mode if query_mode != "qa" else None,
                        "query_type": "qa",
                        "total_answer_ms": 35.0,
                        "pipeline_ms": 20.0,
                    },
                }
            return 200, payload
        except Exception as exc:  # noqa: BLE001 - eval transport records backend failures per case.
            return 500, {"detail": f"{type(exc).__name__}: {exc}"}

    return query_engine, _transport


def _build_request_body(case: dict[str, Any]) -> dict[str, Any]:
    body = {"question": str(case.get("question") or "").strip()}
    if _is_tutor_case(case):
        body["query_mode"] = "tutor"
    return body


def _score_result(result: Any, *, scale: float) -> float | None:
    from app.eval_service import _safe_score

    score = _safe_score(result)
    if score is None:
        return None
    return round(float(score) * scale, 3)


def _judge_case(
    *,
    question: str,
    answer: str,
    sources: list[dict[str, Any]],
    is_tutor_case: bool,
    evaluators: dict[str, Any] | None,
) -> tuple[float | None, float | None]:
    if not evaluators:
        return None, None
    from app.eval_service import _extract_contexts

    contexts = _extract_contexts(sources)
    if not contexts or not (answer or "").strip():
        return None, None
    faithfulness = evaluators["faithfulness"].evaluate(
        query=question,
        response=answer,
        contexts=contexts,
    )
    groundedness = _score_result(faithfulness, scale=3.0)
    tutor_coherence = None
    if is_tutor_case:
        answer_rel = evaluators["answer_relevancy"].evaluate(
            query=question,
            response=answer,
            contexts=contexts,
        )
        tutor_coherence = _score_result(answer_rel, scale=2.0)
    return groundedness, tutor_coherence


def _run_cases(
    *,
    cases: list[dict[str, Any]],
    transport: CaseTransport,
    evaluators: dict[str, Any] | None,
    quiet: bool,
    latency_cap_sec: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        body = _build_request_body(case)
        case_id = str(case["id"])
        if not quiet:
            print(f"eval: running {case_id}", file=sys.stderr, flush=True)
        started = time.perf_counter()
        status_code = 500
        payload: dict[str, Any] = {}
        try:
            status_code, payload = transport(body, case)
        except Exception as exc:  # noqa: BLE001 - eval runner must record heterogeneous transport failures.
            payload = {"detail": f"{type(exc).__name__}: {exc}"}
        wall_sec = time.perf_counter() - started

        answer = str(payload.get("answer") or "")
        sources = list(payload.get("sources") or [])
        match_summary = _source_match_summary(sources, list(case.get("expected_sources") or []))
        groundedness, tutor_coherence = _judge_case(
            question=str(case["question"]),
            answer=answer,
            sources=sources,
            is_tutor_case=_is_tutor_case(case),
            evaluators=evaluators,
        )
        latency_sec = _extract_latency_sec(payload, fallback_wall_sec=wall_sec)
        graceful_out_of_corpus = None
        if _is_out_of_corpus(case):
            graceful_out_of_corpus = (not sources) and _answer_is_graceful_not_found(answer)
        row = {
            "id": case_id,
            "question": case["question"],
            "difficulty": case["difficulty"],
            "tags": list(case.get("tags") or []),
            "query_mode": body.get("query_mode") or "qa",
            "status_code": status_code,
            "status": "pass" if status_code == 200 else "error",
            "expected_sources": list(case.get("expected_sources") or []),
            "expected_concepts": list(case.get("expected_concepts") or []),
            "retrieved_sources": match_summary["retrieved_sources"],
            "retrieved_sources_top3": match_summary["retrieved_sources_top3"],
            "matched_sources": match_summary["matched_sources"],
            "source_precision_at_3": match_summary["source_precision_at_3"],
            "latency_sec": latency_sec,
            "answer_groundedness": groundedness,
            "tutor_coherence": tutor_coherence,
            "out_of_corpus_graceful": graceful_out_of_corpus,
            "trivial_in_corpus_gate": _is_trivial_in_corpus_case(case),
            "component_status": {
                "retrieval": (
                    "pass"
                    if match_summary["source_precision_at_3"] is None or match_summary["source_precision_at_3"] > 0
                    else "fail"
                ),
                "generation": (
                    "pass"
                    if groundedness is None or groundedness >= 2.0
                    else "fail"
                ),
                "latency": "pass" if latency_sec <= latency_cap_sec else "fail",
            },
        }
        if _is_tutor_case(case):
            row["component_status"]["generation"] = (
                "pass" if tutor_coherence is None or tutor_coherence >= 1.5 else "fail"
            )
        if status_code != 200:
            row["error"] = payload.get("detail") or f"http_{status_code}"
        rows.append(row)
    return rows


def _build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    precisions = [float(row["source_precision_at_3"]) for row in rows if row.get("source_precision_at_3") is not None]
    latencies = [float(row["latency_sec"]) for row in rows if row.get("latency_sec") is not None]
    grounded = [float(row["answer_groundedness"]) for row in rows if row.get("answer_groundedness") is not None]
    tutor = [float(row["tutor_coherence"]) for row in rows if row.get("tutor_coherence") is not None]
    ooc = [bool(row["out_of_corpus_graceful"]) for row in rows if row.get("out_of_corpus_graceful") is not None]
    failed = [row for row in rows if row.get("status") != "pass"]
    return {
        "cases_total": len(rows),
        "cases_completed": len(rows) - len(failed),
        "cases_failed": len(failed),
        "source_precision_at_3": round(mean(precisions), 3) if precisions else None,
        "latency_p95_sec": _p95(latencies),
        "answer_groundedness": round(mean(grounded), 3) if grounded else None,
        "tutor_coherence": round(mean(tutor), 3) if tutor else None,
        "out_of_corpus_graceful_rate": round(mean(1.0 if item else 0.0 for item in ooc), 3) if ooc else None,
        "trivial_in_corpus_avg_precision": round(
            mean(
                float(row["source_precision_at_3"])
                for row in rows
                if row.get("trivial_in_corpus_gate") and row.get("source_precision_at_3") is not None
            ),
            3,
        )
        if any(row.get("trivial_in_corpus_gate") and row.get("source_precision_at_3") is not None for row in rows)
        else None,
    }


def _passes_thresholds(summary: dict[str, Any], thresholds: dict[str, Any]) -> bool:
    threshold_values = thresholds.get("thresholds") if isinstance(thresholds.get("thresholds"), dict) else thresholds
    source_threshold = threshold_values.get("source_precision_at_3")
    latency_threshold = threshold_values.get("latency_p95_sec")
    grounded_threshold = threshold_values.get("answer_groundedness")
    tutor_threshold = threshold_values.get("tutor_coherence")
    if source_threshold is not None and summary.get("source_precision_at_3") is not None:
        if float(summary["source_precision_at_3"]) < float(source_threshold):
            return False
    if latency_threshold is not None and summary.get("latency_p95_sec") is not None:
        if float(summary["latency_p95_sec"]) > float(latency_threshold):
            return False
    if grounded_threshold is not None and summary.get("answer_groundedness") is not None:
        if float(summary["answer_groundedness"]) < float(grounded_threshold):
            return False
    if tutor_threshold is not None and summary.get("tutor_coherence") is not None:
        if float(summary["tutor_coherence"]) < float(tutor_threshold):
            return False
    triv = threshold_values.get("trivial_in_corpus_avg_precision")
    if triv is not None and summary.get("trivial_in_corpus_avg_precision") is not None:
        if float(summary["trivial_in_corpus_avg_precision"]) < float(triv):
            return False
    return True


def run_eval(
    *,
    dataset_path: Path = DEFAULT_DATASET,
    thresholds_path: Path = DEFAULT_THRESHOLDS,
    eval_corpus_path: Path | None = None,
    limit: int | None = None,
    mock: bool | None = None,
    transport: CaseTransport | None = None,
    quiet: bool = False,
) -> tuple[dict[str, Any], int]:
    thresholds = _read_json(thresholds_path)
    cases = _read_jsonl(dataset_path)
    _validate_dataset(cases, require_full_contract=dataset_path == DEFAULT_DATASET)
    if limit is not None:
        cases = cases[:limit]

    threshold_block = thresholds.get("thresholds") if isinstance(thresholds.get("thresholds"), dict) else thresholds
    raw_latency_cap = threshold_block.get("latency_p95_sec") if isinstance(threshold_block, dict) else None
    latency_cap_sec = float(raw_latency_cap) if raw_latency_cap is not None else 10.0

    if mock is None:
        from app.config import get_settings

        use_mock = not bool(get_settings().openai_api_key)
    else:
        use_mock = bool(mock)
    eval_index = None
    eval_index_cleanup = None
    evaluators = None
    owned_client = None
    try:
        if eval_corpus_path and eval_corpus_path.is_dir() and not use_mock:
            from llama_index.core import Document, VectorStoreIndex, StorageContext
            from llama_index.core.ingestion import IngestionPipeline
            from llama_index.core.node_parser import SentenceSplitter
            from app.provider import get_embed_model

            embed_model = get_embed_model()

            corpus_files = list(eval_corpus_path.glob("*.md"))
            documents = []
            for f in corpus_files:
                documents.append(Document(text=f.read_text(encoding="utf-8"), metadata={"file_name": f.name}))

            eval_chroma_dir = eval_corpus_path.parent / "corpus_chroma"
            if eval_chroma_dir.exists():
                import shutil
                shutil.rmtree(eval_chroma_dir)

            from llama_index.vector_stores.chroma import ChromaVectorStore
            import chromadb

            eval_client = chromadb.PersistentClient(path=str(eval_chroma_dir))
            eval_collection = eval_client.get_or_create_collection("eval")
            eval_vector_store = ChromaVectorStore(chroma_collection=eval_collection)
            eval_storage_context = StorageContext.from_defaults(vector_store=eval_vector_store)

            pipeline = IngestionPipeline(
                transformations=[SentenceSplitter(chunk_size=512, chunk_overlap=128), embed_model],
            )
            nodes = pipeline.run(documents=documents, show_progress=False)
            eval_index = VectorStoreIndex(
                nodes,
                storage_context=eval_storage_context,
                embed_model=embed_model,
                show_progress=False,
            )

            def eval_index_cleanup():
                eval_client.delete_collection("eval")
                if eval_chroma_dir.exists():
                    import shutil
                    shutil.rmtree(eval_chroma_dir)

        if transport is None:
            if use_mock:
                transport = _build_mock_transport()
            else:
                from app.eval_service import build_evaluators

                if eval_index is not None:
                    owned_client, transport = _build_eval_transport(eval_index)
                else:
                    owned_client, transport = _build_live_transport()
                evaluators = build_evaluators()
        elif not use_mock:
            from app.eval_service import build_evaluators

            evaluators = build_evaluators()
        rows = _run_cases(
            cases=cases,
            transport=transport,
            evaluators=evaluators,
            quiet=quiet,
            latency_cap_sec=latency_cap_sec,
        )
    finally:
        if eval_index_cleanup is not None:
            try:
                eval_index_cleanup()
            except Exception:  # noqa: BLE001 - cleanup must not mask the eval result.
                pass
        if owned_client is not None:
            owned_client.close()

    summary = _build_summary(rows)
    eval_corpus_info = None
    if not use_mock and eval_corpus_path is not None and eval_corpus_path.exists():
        eval_corpus_info = _portable_path(eval_corpus_path)
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "mode": "eval_corpus" if eval_corpus_info else ("mock" if use_mock else "live"),
        "judge_mode": "skipped" if use_mock else "llamaindex_evaluators",
        "dataset_path": _portable_path(dataset_path),
        "thresholds_path": _portable_path(thresholds_path),
        "eval_corpus_path": eval_corpus_info,
        "comparable_to_baseline": (not use_mock and eval_corpus_info is None) or (eval_corpus_info is not None and limit is None),
        "summary": summary,
        "cases": rows,
        "pass": _passes_thresholds(summary, thresholds),
    }
    if use_mock and not quiet:
        report["note"] = "OPENAI_API_KEY missing or --mock requested; judge metrics skipped."
    return report, 0 if report["pass"] else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Run answer-quality eval against the public /ask contract.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS)
    parser.add_argument("--eval-corpus", type=Path, default=DEFAULT_EVAL_CORPUS, help="Path to eval corpus directory for synthetic eval.")
    parser.add_argument("--report-json", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--mock", action="store_true", help="Force offline/mock mode even if OPENAI_API_KEY exists.")
    parser.add_argument("--baseline", action="store_true", help="Write the checked-in baseline report preset.")
    parser.add_argument("--eval", type=str, default=None, help="Eval preset: epoch-answer-quality-eval, golden")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-case stderr progress.")
    args = parser.parse_args()
    if args.baseline:
        args.eval = "epoch-answer-quality-eval"
    if args.eval:
        tests_eval_dir = Path(__file__).parent
        if args.eval == "epoch-answer-quality-eval":
            args.dataset = tests_eval_dir / "golden_qa.jsonl"
            args.thresholds = tests_eval_dir / "thresholds.json"
            args.report_json = tests_eval_dir / "results" / "baseline.json"
            args.eval_corpus = tests_eval_dir / "corpus"
        elif args.eval == "golden":
            args.dataset = tests_eval_dir / "golden_qa.jsonl"
            args.thresholds = tests_eval_dir / "thresholds.json"
            args.report_json = tests_eval_dir / "results" / "golden_eval.json"
        else:
            parser.error(f"Unknown --eval preset: {args.eval}")
    if args.report_json is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        args.report_json = Path(__file__).resolve().with_name("results") / f"run_{stamp}.json"
    configure_stdio_utf8()

    try:
        report, rc = run_eval(
            dataset_path=args.dataset,
            thresholds_path=args.thresholds,
            eval_corpus_path=args.eval_corpus if args.eval_corpus.exists() else None,
            limit=args.limit,
            mock=True if args.mock else None,
            quiet=args.quiet,
        )
    except Exception as exc:  # noqa: BLE001 - CLI must serialize unexpected eval failures.
        report = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now_iso(),
            "mode": "error",
            "summary": {
                "cases_total": 0,
                "cases_completed": 0,
                "cases_failed": 0,
                "source_precision_at_3": None,
                "latency_p95_sec": None,
                "answer_groundedness": None,
                "tutor_coherence": None,
                "out_of_corpus_graceful_rate": None,
            },
            "cases": [],
            "pass": False,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
        rc = 1

    if args.report_json and args.report_json.name == "baseline.json" and report.get("mode") == "mock":
        print(
            "ERROR: refusing to write mock report to baseline.json — "
            "run live eval with OPENAI_API_KEY or choose a different filename.",
            file=sys.stderr,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(output, encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
