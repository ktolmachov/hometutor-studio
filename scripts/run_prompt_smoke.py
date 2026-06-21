#!/usr/bin/env python3
"""
Prompt smoke: эталонные вопросы по mini-KB + латентность/токены + лёгкие эвристики.

Требует OPENAI_API_KEY; поднимает изолированный индекс из ``eval_data/quality_benchmark_kb``
(как quality benchmark).

Пример:
  python scripts/run_prompt_smoke.py
  python scripts/run_prompt_smoke.py --strict
  python scripts/run_prompt_smoke.py --strict --smoke-fast
  python scripts/run_prompt_smoke.py --report-json /tmp/prompt_smoke.json

``--smoke-fast`` (DoD / closure): quality-lite retrieval (hybrid top-k=4),
reranker off, один LLM-вызов на tutor (без отдельного inline-quiz и
auto-quiz loop). Ослабляет только latency-путь, не ``expect`` gates.

В каждом завершённом кейсе: ``token_usage_stages`` — разбивка ``debug.token_usage.stages``
(classify / rewrite / retrieval / generation / judge) для разбора выбросов по токенам.

``--strict`` → exit 2, если хотя бы одна эвристика ``expect`` не прошла.
Без ``--strict`` отчёт для человека; exit 2 только при исключении в пайплайне.

Для tutor-кейсов гейты длины (``min/max_answer_chars``) меряются по
``tutor_answer.teaching_summary`` (модельный текст), а не по итоговому markdown
со скаффолдом; подстрочные проверки — по полному видимому ответу.
``require_system_user`` дополнительно проверяет фактические роли generation
chat-вызовов (``debug.pipeline_trace.generate_stage.chat_message_roles``).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = ROOT / "scripts"
for _p in (ROOT, _SCRIPTS):
    s = str(_p)
    if s not in sys.path:
        sys.path.insert(0, s)

DEFAULT_CASES = ROOT / "eval_data" / "prompt_smoke_cases.json"
DEFAULT_KB = ROOT / "eval_data" / "quality_benchmark_kb"

from script_stdio_utf8 import configure_stdio_utf8, write_stdout_utf8_line


def _percentile(sorted_vals: list[float], p: float) -> float | None:
    if not sorted_vals:
        return None
    n = len(sorted_vals)
    idx = int(round(p * (n - 1)))
    return round(sorted_vals[idx], 3)


def _norm_usage_dict(u: dict | None) -> dict[str, int] | None:
    if not isinstance(u, dict):
        return None
    out = {
        "prompt_tokens": int(u.get("prompt_tokens") or 0),
        "completion_tokens": int(u.get("completion_tokens") or 0),
        "total_tokens": int(u.get("total_tokens") or 0),
    }
    if "reasoning_tokens" in u:
        out["reasoning_tokens"] = int(u.get("reasoning_tokens") or 0)
    return out


def _total_tokens(debug: dict | None) -> dict[str, int] | None:
    if not debug:
        return None
    tu = (debug.get("token_usage") or {}).get("total")
    return _norm_usage_dict(tu if isinstance(tu, dict) else None)


def _token_usage_stages_for_report(debug: dict | None) -> dict[str, object] | None:
    """Копия debug.token_usage (stages + total) для JSON-отчёта."""
    if not debug:
        return None
    tu = debug.get("token_usage")
    if not isinstance(tu, dict):
        return None
    stages_in = tu.get("stages")
    stages_out: dict[str, dict[str, int] | None] = {}
    if isinstance(stages_in, dict):
        known = ("classify", "rewrite", "retrieval", "generation", "judge")
        for name in known:
            stages_out[name] = _norm_usage_dict(stages_in.get(name))
        for name, v in stages_in.items():
            if name in known:
                continue
            stages_out[str(name)] = _norm_usage_dict(v) if isinstance(v, dict) else None
    total = _norm_usage_dict(tu.get("total") if isinstance(tu.get("total"), dict) else None)
    if total is None:
        total = _total_tokens(debug)
    if not stages_out and total is None:
        return None
    return {"stages": stages_out, "total": total}


def _debug_for_expect(debug: dict | None) -> dict[str, object]:
    """Compact debug payload used by smoke gates and persisted in reports."""
    if not isinstance(debug, dict):
        return {}
    out: dict[str, object] = {}
    if "total_answer_ms" in debug:
        out["total_answer_ms"] = debug.get("total_answer_ms")
    for key in ("llm_source", "llm_model", "llm_api_base", "fallback_used", "llm_profile"):
        if key in debug:
            out[key] = debug.get(key)

    trace = debug.get("pipeline_trace")
    generate = trace.get("generate_stage") if isinstance(trace, dict) else None
    if isinstance(generate, dict):
        if not out.get("llm_model"):
            out["llm_model"] = generate.get("llm_model") or generate.get("model")
        for key in ("llm_source", "llm_api_base", "fallback_used", "llm_profile"):
            if key not in out and key in generate:
                out[key] = generate.get(key)
        if isinstance(generate.get("chat_message_roles"), list):
            out["chat_message_roles"] = generate.get("chat_message_roles")
        prompt_key = generate.get("prompt_key")
        if prompt_key:
            out["prompt_key"] = prompt_key
            try:
                from app.prompts import get_prompt_role_contract

                out["prompt_role_contract"] = get_prompt_role_contract(str(prompt_key))
            except Exception:
                pass

    token_usage = debug.get("token_usage")
    if isinstance(token_usage, dict):
        out["token_usage"] = token_usage
    return out


def _summary_token_stage_spikes(rows: list[dict]) -> dict[str, object]:
    """Для быстрого поиска кейса с максимальным prompt в стадии ``generation`` и т.д."""

    def _max_for_stage(stage: str) -> dict[str, object] | None:
        best_p = -1
        best_id: str | None = None
        for r in rows:
            if r.get("status") != "completed":
                continue
            tus = r.get("token_usage_stages")
            if not isinstance(tus, dict):
                continue
            st = (tus.get("stages") or {}).get(stage)
            if not isinstance(st, dict):
                continue
            p = int(st.get("prompt_tokens") or 0)
            if p > best_p:
                best_p = p
                best_id = str(r.get("id") or "")
        if best_id is None or best_p < 0:
            return None
        return {"case_id": best_id, "prompt_tokens": best_p}

    out: dict[str, object] = {}
    for s in ("generation", "classify", "rewrite", "retrieval"):
        m = _max_for_stage(s)
        if m:
            out[f"max_prompt_tokens_{s}"] = m
    return out


def _quality_gate(
    summary: dict,
    *,
    strict: bool,
    max_p95_latency_sec: float | None,
    max_total_tokens: int | None,
) -> dict:
    checks: dict[str, dict[str, object]] = {}
    failed = False

    expect_pass = bool(summary.get("expect_pass_all"))
    checks["expect_pass_all"] = {"pass": expect_pass, "strict_only": True}
    failed = failed or (strict and not expect_pass)

    p95 = (summary.get("latency_sec") or {}).get("p95")
    if max_p95_latency_sec is not None:
        ok = p95 is not None and float(p95) <= float(max_p95_latency_sec)
        checks["max_p95_latency_sec"] = {
            "pass": ok,
            "actual": p95,
            "threshold": float(max_p95_latency_sec),
        }
        failed = failed or not ok

    total_tokens = (summary.get("token_usage_sum") or {}).get("total_tokens")
    if max_total_tokens is not None:
        ok = total_tokens is not None and int(total_tokens) <= int(max_total_tokens)
        checks["max_total_tokens"] = {
            "pass": ok,
            "actual": total_tokens,
            "threshold": int(max_total_tokens),
        }
        failed = failed or not ok

    return {
        "pass": not failed,
        "checks": checks,
        "note": "Canary/smoke only; does not replace full router_eval or quality_benchmark.",
    }


_SMOKE_FAST_ENV: dict[str, str] = {
    "RAG_PROFILE": "quality",
    "RETRIEVAL_MODE": "hybrid",
    "ENABLE_RERANKER": "false",
    "SIMILARITY_TOP_K": "4",
    "TUTOR_INLINE_QUIZ_SEPARATE_LLM_CALL": "false",
    "ENABLE_TUTOR_AUTO_QUIZ_LOOP": "false",
}


def _cleanup_tmp_index_dir(tmp: Path) -> None:
    """Удалить временный KB/index dir, освободив sqlite-хэндлы Chroma (Windows).

    PersistentClient кэшируется глобально в chromadb (SharedSystemClient), поэтому
    без clear_system_cache() rmtree молча оставляет залоченный chroma_db.
    """
    try:
        from app.retrieval_cache import clear_retrieval_cache

        clear_retrieval_cache()
    except Exception:  # noqa: BLE001 - cleanup is best-effort
        pass
    try:
        from chromadb.api.client import SharedSystemClient

        SharedSystemClient.clear_system_cache()
    except Exception:  # noqa: BLE001 - chromadb internals may change between versions
        pass
    import gc

    gc.collect()
    shutil.rmtree(tmp, ignore_errors=True)
    if tmp.exists():
        print(f"  [smoke] tmp dir not fully removed (locked files): {tmp}", file=sys.stderr)


def apply_smoke_fast_env() -> None:
    """Apply DoD-friendly overrides before any ``get_settings()`` in this process."""
    for key, value in _SMOKE_FAST_ENV.items():
        os.environ[key] = value
    from app.config import reset_settings_cache

    reset_settings_cache()


def _tutor_length_text(result: dict, options: "QueryOptions") -> tuple[str | None, str]:
    """Текст для гейтов длины tutor-кейсов.

    Итоговый ``answer`` для tutor — ``format_tutor_v2_markdown``: модельный
    ``teaching_summary`` плюс детерминированный markdown-скаффолд (~600+ символов
    заголовков и trust-блока). Лимиты ``max_answer_chars`` в кейсах калиброваны на
    модельный текст, поэтому длину меряем по ``tutor_answer.teaching_summary``.
    Если teaching-конверт не распарсился, ``teaching_summary`` уже содержит сырой
    ответ модели целиком — гейт остаётся fail-closed.
    """
    if (options.query_mode or "").strip().lower() != "tutor":
        return None, "answer"
    tutor_answer = result.get("tutor_answer")
    if not isinstance(tutor_answer, dict):
        return None, "answer"
    ts = str(tutor_answer.get("teaching_summary") or "").strip()
    if not ts:
        return None, "answer"
    return ts, "tutor_teaching_summary"


def _build_options(case: dict, *, smoke_fast: bool = False) -> "QueryOptions":
    from app.models import QueryOptions

    qm = (case.get("query_mode") or "qa").strip().lower()
    hm = bool(case.get("homework_mode"))
    al = case.get("assistance_level")
    return QueryOptions(
        session_id=case.get("session_id") or f"prompt_smoke_{case.get('id', 'x')}",
        query_mode=qm,
        homework_mode=hm,
        assistance_level=str(al) if hm and al else None,
        rag_profile="quality" if smoke_fast else None,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Prompt smoke over mini-KB + latency/token report.")
    ap.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    ap.add_argument("--kb-dir", type=Path, default=DEFAULT_KB)
    ap.add_argument("--report-json", type=Path, default=None)
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit 2 if any expect-heuristic fails (default: only hard failures / exceptions)",
    )
    ap.add_argument(
        "--max-p95-latency-sec",
        type=float,
        default=None,
        help="Optional smoke gate for p95 latency; intended for local canary only",
    )
    ap.add_argument(
        "--max-total-tokens",
        type=int,
        default=None,
        help="Optional smoke gate for summed token usage; intended for local canary only",
    )
    ap.add_argument("--quiet", action="store_true", help="No stderr progress lines")
    ap.add_argument(
        "--keep-tmp",
        action="store_true",
        help="Keep the temporary KB/index dir after the run (path is in report tmp_root)",
    )
    ap.add_argument(
        "--smoke-fast",
        action="store_true",
        help=(
            "DoD mode: quality-lite hybrid top-k=4, reranker off, tutor without extra quiz LLM calls "
            "(same expect gates; lower latency)"
        ),
    )
    args = ap.parse_args()
    configure_stdio_utf8()

    if args.smoke_fast:
        apply_smoke_fast_env()
        if not args.quiet:
            print(
                "  [smoke-fast] quality-lite hybrid top-k=4, reranker off, tutor single-LLM path",
                file=sys.stderr,
                flush=True,
            )

    import app.config  # noqa: F401 — side effect: load_dotenv(config.env/.env) до проверки ключа

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set; prompt smoke aborted.", file=sys.stderr)
        return 2

    raw = json.loads(args.cases.read_text(encoding="utf-8"))
    cases = raw.get("cases") or []
    if not cases:
        print("No cases in dataset.", file=sys.stderr)
        return 2

    from tests.integration_paths import apply_integration_layout_for_script

    tmp = Path(tempfile.mkdtemp(prefix="prompt_smoke_"))
    restore = apply_integration_layout_for_script(tmp)
    try:
        data_dir = tmp / "data"
        shutil.copytree(args.kb_dir, data_dir, dirs_exist_ok=True)

        from app.config import get_retrieval_settings, get_settings
        from app.index_diff import update_snapshot_after_index
        from app.ingestion import build_index
        from app.prompt_smoke_checks import evaluate_prompt_smoke_expect
        from app.query_service import answer_question
        from app.retrieval_cache import clear_retrieval_cache

        clear_retrieval_cache()
        build_index(reset=True)
        update_snapshot_after_index()
        clear_retrieval_cache()

        rows: list[dict] = []
        latencies: list[float] = []
        total_tokens_sum = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        for i, case in enumerate(cases, start=1):
            cid = case.get("id", f"case_{i}")
            q = str(case.get("question") or "").strip()
            if not q:
                rows.append({"id": cid, "status": "skipped", "reason": "empty_question"})
                continue

            options = _build_options(case, smoke_fast=bool(args.smoke_fast))
            if not args.quiet:
                print(f"  [{i}/{len(cases)}] {cid} ({options.query_mode}) …", file=sys.stderr, flush=True)

            t0 = time.perf_counter()
            try:
                result = answer_question(q, options)
            except Exception as e:
                rows.append(
                    {
                        "id": cid,
                        "status": "error",
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                )
                continue

            dt = time.perf_counter() - t0
            latencies.append(dt)
            answer = str(result.get("answer") or "")
            sources = list(result.get("sources") or [])
            dbg = result.get("debug") if isinstance(result.get("debug"), dict) else {}
            total_ms = dbg.get("total_answer_ms")
            tt = _total_tokens(dbg)
            if tt:
                for k in total_tokens_sum:
                    total_tokens_sum[k] += tt.get(k, 0)

            expect = case.get("expect") if isinstance(case.get("expect"), dict) else None
            debug_for_expect = _debug_for_expect(dbg)
            length_text, length_text_source = _tutor_length_text(result, options)
            pass_h, check_detail = evaluate_prompt_smoke_expect(
                answer,
                expect,
                sources=sources,
                debug=debug_for_expect,
                length_text=length_text,
            )

            rows.append(
                {
                    "id": cid,
                    "status": "completed",
                    "query_mode": options.query_mode,
                    "latency_sec": round(dt, 3),
                    "total_answer_ms": total_ms,
                    "token_total": tt,
                    "token_usage_stages": _token_usage_stages_for_report(dbg),
                    "debug_summary": debug_for_expect,
                    "source_count": len(sources),
                    "expect_pass": pass_h,
                    "expect_length_text_source": length_text_source,
                    "expect_detail": check_detail,
                    "answer_preview": answer[:400] + ("…" if len(answer) > 400 else ""),
                    "review_ru": case.get("review_ru"),
                }
            )

        lat_sorted = sorted(latencies)
        nlat = len(lat_sorted)
        cases_completed = sum(1 for r in rows if r.get("status") == "completed")
        summary = {
            "cases_total": len(cases),
            "cases_completed": cases_completed,
            "cases_error": sum(1 for r in rows if r.get("status") == "error"),
            # cases_completed > 0: без завершённых кейсов "все прошли" вакуумно истинно.
            "expect_pass_all": cases_completed > 0
            and all(r.get("expect_pass") for r in rows if r.get("status") == "completed"),
            "latency_sec": {
                "avg": round(sum(latencies) / nlat, 3) if nlat else None,
                "p50": _percentile(lat_sorted, 0.50),
                "p95": _percentile(lat_sorted, 0.95),
            },
            "token_usage_sum": total_tokens_sum,
            "token_usage_stage_spikes": _summary_token_stage_spikes(rows),
        }
        gate = _quality_gate(
            summary,
            strict=bool(args.strict),
            max_p95_latency_sec=args.max_p95_latency_sec,
            max_total_tokens=args.max_total_tokens,
        )
        settings = get_settings()

        report = {
            "schema_version": 1,
            "dataset": str(args.cases.resolve()),
            "kb_dir": str(args.kb_dir.resolve()),
            "tmp_root": str(tmp),
            "strict": bool(args.strict),
            "smoke_fast": bool(args.smoke_fast),
            "metadata": {
                "model": settings.llm_model,
                "embed_model": settings.embed_model,
                "query_modes": sorted({str(c.get("query_mode") or "qa") for c in cases}),
                "canary_scope": "prompt_smoke_only",
                "rag_profile": get_retrieval_settings().rag_profile,
                "tutor_inline_quiz_separate_llm_call": settings.tutor_inline_quiz_separate_llm_call,
                "enable_tutor_auto_quiz_loop": settings.enable_tutor_auto_quiz_loop,
            },
            "summary": summary,
            "quality_gate": gate,
            "cases": rows,
        }

        out = json.dumps(report, ensure_ascii=False, indent=2)
        write_stdout_utf8_line(out)

        if args.report_json:
            args.report_json.parent.mkdir(parents=True, exist_ok=True)
            args.report_json.write_text(out, encoding="utf-8")

        if any(r.get("status") == "error" for r in rows):
            return 2
        if not gate["pass"]:
            return 2
        return 0
    finally:
        restore()
        if not args.keep_tmp:
            _cleanup_tmp_index_dir(tmp)


if __name__ == "__main__":
    raise SystemExit(main())
