
# Журнал Изменений

## 2026-06-21 (multi-query-expansion-v1 closure)

- **Roadmap closure:** `multi-query-expansion-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-06-20 (llama.cpp local default: qwopus + smoke/provenance fixes)

- **Local default model:** после benchmark pack v1.7 (`2026-06-20_20-34-44`) профиль `llama-cpp` и `config.env` переведены на **`qwopus3.6-35b-a3b-v1-mtp`** (`~185 tps`, quality 11.5/11.5, real hometutor smoke PASS). Baseline **`qwen3.6-27b`** остаётся доступен через `switch_local_llm.ps1 -Model …` и LM Studio-профиль.
- **`scripts/switch_local_llm.ps1`:** дефолт llama-cpp = qwopus; добавлен опциональный `-Model` для override alias без ручного редактирования `config.env`.
- **`scripts/Smoke-HomeRag-LlamaCpp.ps1`:** `Set-Location` в корень репо; override `LLM_MODEL`/`QUIZ_LLM_MODEL` из `-Model`; дефолт smoke = qwopus. Исправляет false-negative smoke при запуске из benchmark pack (cwd) и mismatch `debug.llm_model` vs загруженный alias.
- **`app/config.py`:** `config.env` / `.env` загружаются от `BASE_DIR`, а не cwd вызывающего процесса — subprocess smoke из другого каталога больше не теряет `OPENAI_API_KEY`.
- **`app/grounded_answer.py`:** устойчивость provenance — блоки только с out-of-range `[N]` отбрасываются; footer «Источники:» фильтруется и при разбиении длинного ответа на предложения. Regression tests в `tests/test_grounded_answer_contract.py`.
- **Docs:** `doc/user_guide.md`, `doc/quickstart.md` — актуальные llama.cpp default, `-Model`, smoke cold-latency note.
- **`scripts/Warmup-HomeRagRag.ps1`:** прогрев reranker/query engine через `POST /ask` в running API; флаг `-WarmupRag` у `scripts/run_local_stack.ps1`.

## 2026-06-20 (flashcard-handoff-fast-path-v1 closure + bug fixes)

- **Roadmap closure:** `flashcard-handoff-fast-path-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-16.5` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.
- **Bug fix — `tutor_entrypoint` one-shot lifecycle** (`app/ui/tutor_chat_session.py`): `st.session_state.pop("tutor_entrypoint", None)` added after first handoff answer renders. Previously the entrypoint key was never cleared, so every subsequent normal tutor message ran in fast-path mode (fast profile, no reranker, short answer). Regression test: `test_second_tutor_message_not_handoff_after_entrypoint_cleared`.
- **Bug fix — error-path cleanup** (`app/ui/tutor_chat_session.py`): `clear_flashcard_handoff_session_fields` now also called on exception, not only on success path. Previously an exception left the handoff state active for the next turn.
- **Bug fix — cache key isolation** (`app/retrieval.py`): `is_flashcard_handoff(options)` added to the `build_query_engine` cache-key tuple. Handoff and normal tutor use different prompt templates; without this they could share a cached engine and get the wrong prompt. Regression test: `test_cache_keys_differ_for_handoff_vs_normal_tutor`.
- **Bug fix — honest `retrieval_ms`/`llm_ms` split** (`app/provider_openai.py`, `app/usage_cost.py`, `app/query_rag_execution.py`): Previously `retrieval_ms` was hardcoded `0.0` and all of `query_execute_ms` was attributed to `llm_ms`. Now each LLM call (`chat`/`achat`/`complete`/`acomplete`) is timed in `provider_openai.py` and accumulated into a contextvar bucket (`usage_cost.record_llm_generation_call_ms`); `query_rag_execution.py` sets `llm_ms = sum(calls)`, `retrieval_ms = max(0, query_execute_ms − llm_ms)`. Live baseline confirmed: `retrieval_ms 1659 / llm_ms 5530 / query_execute_ms 7189`.
- **UX fix — raw JSON shown to user** (`app/prompts/_impl.py`, `app/query_response_postprocessing.py`, `app/flashcard_handoff.py`): The v2-JSON handoff prompt (8 required fields) truncated mid-object under the 160-token output cap; `parse_tutor_rag_response` fell back to rendering raw JSON to the user (visible as the `pre_generate`-badged bubble). Fix: `FLASHCARD_HANDOFF_TUTOR_BODY` rewritten to plain friendly prose (key idea + example + check question); `process_rag_response` now skips `parse_tutor_rag_response` entirely for handoff (`not is_flashcard_handoff(options)` guard); cap raised 160 → 220. Prose degrades gracefully to readable text if token-capped. Regression tests: `test_handoff_answer_kept_as_prose_not_parsed_as_v2_json`, prose-field guards in `test_resolve_effective_prompt_uses_compact_handoff_template`.
- **Live latency baseline (cold, qwen3.6-27b @ ~43 t/s):** `total_ms 8119`, `retrieval_ms 1659`, `llm_ms 5530`. DoD ≤6 s unmet; bottleneck is LLM-bound (prompt eval ~2700 tok + generation), not RAG path. Next levers are LLM-side (shorter context, fewer output tokens), not retrieval tuning.

## 2026-06-19 (lost-in-middle-reorder-v1 closure)

- **Roadmap closure:** `lost-in-middle-reorder-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-06-19 (log-masking-policy-v1 closure)

- **Roadmap closure:** `log-masking-policy-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-06-19 (trace-to-eval-dataset-v1 closure)

- **Roadmap closure:** `trace-to-eval-dataset-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-06-19 (langfuse-trace-export-v1 closure)

- **Roadmap closure:** `langfuse-trace-export-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-06-19 (fact-source-binding-v1 closure)

- **Roadmap closure:** `fact-source-binding-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.9, US-20.8, US-12.10` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-06-11 (grounded-answer-contract-v1 closure)

- **Roadmap closure:** `grounded-answer-contract-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-06-11 (course-graph-aware-uplift-gate-v1 closure)

- **Roadmap closure:** `course-graph-aware-uplift-gate-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.7, US-12.10` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-06-11 (course-graph-relation-ux-v1 closure)

- **Roadmap closure:** `course-graph-relation-ux-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-06-11 (graph extraction max_tokens после ingest)

- **Симптом:** после `ingest.py --reset --yes` Chroma и `/index/stats` в порядке, но UI **Knowledge Graph** показывает «Нет данных для графа…».
- **Причина:** индексация и сборка графа — **разные шаги**. Course Graph Compiler (`compile_course_graph` → `write_generation_knowledge_graph_bundle`) вызывается после `activate_reset_generation`. При `fail_reasons: ["truncated graph LLM output"]` (типично `finish_reason=length` на плотном уроке, напр. «Урок 3») payload пустой → `kg.sqlite` не пишется → UI fallback на отсутствующий legacy `data/concept_graph.json`.
- **Исправление:** в `_default_llm_extract` (`app/course_graph_compiler.py`) явный `max_tokens=8192` для graph LLM (без него LM Studio обрезал JSON при дефолтном лимите).
- **Диагностика:** `data/graph_generations/by_generation/<generation_id>/graph_quality_report.json` — смотреть `gate_passed`, `fail_reasons`, `truncated`. Bundle готов, если есть `kg.sqlite` (не только sidecar).
- **Recovery:** удалить `data/llm_request_cache.db` (могли закэшироваться обрезанные ответы) → перезапустить stack → `python ingest.py --reset -y` или пересборка bundle для активной generation из `chroma_db/ingestion_extracted_documents.json`.
- **Verification:** `tests/test_course_graph_compiler.py` — 14/14.

## 2026-06-11 (course graph compiler corrective delivery)

- **Production flow restored:** compiler now receives real chunk text, validates concept/relation evidence chunk IDs against ingested documents, and stores scope/content-hash provenance.
- **Graph contract fixed:** prerequisites and related concepts use stable `concept_id` values; all typed relations participate in orphan metrics; filename-like concepts and alias conflicts block publication.
- **Atomic publication fixed:** a quality sidecar is mandatory for promote; staging provenance is retargeted to the generation assigned during activation; course binding is written only after successful promote.
- **Ingestion wiring fixed:** full, reset and partial indexing pass source paths and content hashes into graph compilation.
- **Verification:** `tests/test_course_graph_compiler.py` passed 14/14; ingestion, retrieval-cache, registry, resolver and knowledge-graph bundle passed 51/51.

## 2026-06-11 (course-graph-compiler-v1 closure)

- **Roadmap closure:** `course-graph-compiler-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-16.0` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-06-11 (folder-to-course-delight-v1 closure)

- **Roadmap closure:** `folder-to-course-delight-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-16.0` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-06-11 (prompt smoke hardening: tutor length gates + wire role contract)

- **`scripts/run_prompt_smoke.py` — tutor length gates по teaching_summary:** итоговый `answer` для tutor — `format_tutor_v2_markdown` (модельный текст + ~600 символов детерминированного скаффолда «### Кратко / Состояние понимания / Надёжность»), из-за чего `max_answer_chars` фейлился на скаффолде (ps_tutor_01: 2008 > 2000). Новый `_tutor_length_text()` передаёт `tutor_answer.teaching_summary` в гейты длины; подстрочные проверки остаются по полному видимому ответу. В отчёт добавлены `expect_length_text_source` и `answer_chars`.
- **Wire-контракт ролей для `require_system_user`:** гейт сравнивал статический `PROMPT_ROLE_CONTRACT` сам с собой (тавтология). Теперь `provider_openai._chat/_achat` пишут фактические роли каждого chat-запроса в context-window (`app/usage_cost.py: record_llm_chat_message_roles`), `execute_rag_query` возвращает их как `generation_message_roles`, `query_service` кладёт в `pipeline_trace.generate_stage.chat_message_roles`, и `prompt_smoke_checks` требует `system` первым + `user` в каждом generation-вызове (если роли записаны).
- **`app/prompt_smoke_checks.py` — починен мёртвый гейт `allow_user_only_stage`:** `llm_stage_role_contract` нигде не записывался в debug, гейт всегда падал; теперь контракт резолвится из `LLM_STAGE_USER_ONLY_ALLOWLIST` реестра.
- **`scripts/run_prompt_smoke.py` — прочие фиксы:** загрузка `.env` до проверки `OPENAI_API_KEY` (раньше скрипт падал, если ключ не экспортирован в shell); очистка temp-директории индекса после прогона с освобождением sqlite-хэндлов Chroma (`SharedSystemClient.clear_system_cache()`; раньше каждый прогон оставлял ~1.2 МБ в %TEMP%), `--keep-tmp` для отладки; `expect_pass_all` больше не вакуумно-истинен при нуле завершённых кейсов.
- **`eval_data/prompt_smoke_cases.json`:** `ps_tutor_01.max_answer_chars` возвращён к строгим 2000 (семантика длины теперь — модельный текст); описание датасета фиксирует новую семантику.
- **`tests/test_prompt_smoke_checks.py`:** +4 теста (length_text, wire-роли pass/fail/absent, allowlist-резолв стейджа, roundtrip ролей в usage_cost).

## 2026-06-11 (prompt-role-unification-v1 closure)

- **Roadmap closure:** `prompt-role-unification-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.5` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-06-11 (Flashcards malformed JSON recovery)

- Flashcard generation now performs one bounded `temperature=0` syntax-repair call when the initial LLM response contains no parseable cards.
- Invalid output is no longer failed immediately after a long generation call; repeated invalid output still stops deterministically after one repair attempt.

## 2026-06-11 (Flashcards answer depth)

- Flashcard generation now requires a direct answer plus a causal explanation and, when supported by the source, a practical consequence or example.
- Bare lists of properties no longer satisfy the generation contract for `Почему` questions.

## 2026-06-10 (Flashcards recovery undo and schedule visibility)

- Empty Flashcards review queues now show the nearest scheduled review date and card count.
- Added safe undo for the 5-day recovery spread: never-reviewed deferred cards return to due, while reviewed cards retain their SM-2 schedule.
- Normalized SQLite `next_review` comparisons through `datetime(...)`, fixing same-day ISO timestamps with a `T` separator.

## 2026-06-10 (offline Langfuse dataset pipeline)

- Added `app/langfuse_dataset.py`: JSON/JSONL export normalization, recursive PII redaction, failed-trace filtering, deterministic IDs, deduplication, and atomic dataset writes.
- Added `scripts/build_langfuse_eval_dataset.py`: offline export → `eval_data/langfuse_eval_dataset.json`; `--run-eval` explicitly reuses the existing eval/baseline pipeline and persists `eval_results/langfuse_eval_report_latest.json`.
- Added `tests/test_langfuse_dataset.py`; pipeline/eval gates pass without network calls. Live Langfuse export remains gated by PII sink coverage and explicit consent.

## 2026-06-10 (ragas-retrieval-metrics-v1 closure)

- **Roadmap closure:** `ragas-retrieval-metrics-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-06-10 (golden-e2e-graduation-v1 closure)

- **Roadmap closure:** `golden-e2e-graduation-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-17.5, US-17.9` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.
- **Golden browser path completed:** added `tests/e2e/golden_delight_graduation_loop.spec.ts` to `npm run local:course-loop`. The smoke walks Q&A → Tutor → Quiz → Card → Review → Graduation, verifies every Mission Control rail step, and asserts `qwen/qwen3.6-27b`, `llm_source=local`, `fallback_used=false`.
- **Runtime wiring fixed:** Mission Control now renders the previously unused delight progress rail. The `HOME_RAG_E2E_OFFLINE`-only completion hook invokes the real `emit_e2e_graduation_event()` path and exposes a metadata receipt for Playwright without enabling a production shortcut.
- **Verification:** 44 focused Python tests passed; `local:course-loop` passed 6/6; strict smoke-fast passed 18/18; session tape recorded an `e2e_graduation` event with local Qwen and no fallback.

## 2026-06-10 (Course Graph Compiler audit and GraphRAG execution plan)

- **Verified root cause for disconnected `ИИ Агенты` graph:** the latest matching graph generation contains 5 filename-based nodes, 0 relations and 0 triplets with heuristic provenance (`confidence=0.72`); `data/concept_graph.json` is absent. Metadata enrichment, document summaries and graph-augmented retrieval were disabled at audit time, while `GRAPH_MODEL=qwen/qwen3.6-27b` was configured.
- **Contract gap documented:** `folder-to-course-delight-v1` delivered graph availability/status UX, but did not implement a `get_graph_llm()` course extraction/compiler stage. The current builder falls back to one title concept per document and can therefore produce a visually valid but disconnected graph. Graph `ready` is also not gated by evidence-backed relation coverage.
- **New execution plan:** added `doc/next/course_graph_compiler_v1_plan.md` with the current-state matrix, root cause, typed node/relation contract, provenance/publication rules, initial quality thresholds, global-analytics boundary and kill switches.
- **Roadmap:** added proposed wave `wave-course-graph-evidence-2026-06` with packages `course-graph-compiler-v1`, `course-graph-relation-ux-v1` and `course-graph-aware-uplift-gate-v1`. The active wave/package remain unchanged.
- **Verification baseline:** current behavior is covered by focused tests; `tests/test_knowledge_graph_d3.py tests/test_folder_to_course.py` passed 63/63 before documentation changes.

## 2026-06-09 (Universal lecture prompt breakthrough: token efficiency & quality)

- **Universal prompt optimization:** refactored and compressed `doc/prompts/smart_lecture_konspekt_universal.md`, reducing prompt size from ~8.5k to ~2.7k tokens. This is a critical fix preventing context limit overflow and truncation (`finish_reason=length`) on local models like Qwen3.6-27B.
- **Cloud prompt instantiation:** restored the full-scale prompt in `doc/prompts/smart_lecture_konspekt_universal_cloud_llm.md` for cloud LLMs (9.0k+ tokens). The full prompt retains extensive formatting guidelines, rich section-by-section templates, high-quality ASR dictionaries, Mermaid safety constraints, strict verified-URL rules, and cloud-only deep/practice sections.
- **Aesthetics & Tone:** mapped HTML style properties (blue/pink boxes, stats, checklists, tag strings, quotes) to clean Markdown equivalents. Enriched the external expert persona (Senior Architect with 10+ years of experience, trade-off focus, practical analogies, and clear scenarios).
- **ASR error correction:** added a comprehensive domain-specific dictionary of technical terms (e.g., лэмка -> LLM, тулы -> tools, промт -> промпт) to automatically fix transcription errors.
- **Mermaid & Link Safety:** integrated strict Mermaid syntax safety rules to avoid rendering errors. Cloud external materials now require concrete verified URLs; search fallback links and unverified YouTube IDs are rejected.
- **Quality rubric boundary:** removed YAML `self_eval`; quality scoring belongs only in the rendered `## ✅ Рубрика качества конспекта` section, while YAML remains provenance metadata.
- **Generated konspekt quality gate:** added `scripts/validate_smart_konspekt.py` and universal course wrapper `scripts/validate_course_konspekts.ps1` for post-generation validation of `data/<course>/*.md` smart konspekts.
- **Verification:** verified and passed `lint_agent_prompts.py`, `check_llm_context_gate.py`, `check_readset.py` (marked SAFE for local, signatures-safe for cloud prompt), `tests/test_validate_smart_konspekt.py`, and all relevant `smart_konspekt` / `obsidian_export` checks.

## 2026-06-08 (SmartKonspekt local pipeline + doc alignment)

- **Local SmartKonspekt:** added `app/smart_konspekt.py` for staged `materials/<course>/<lecture>/` inputs (`txt/md/html/pdf`) → `data/<course>/<lecture>.md` output with `type: konspekt`, partial resume cache, universal compose prompt, and focused mock-LLM tests.
- **CLI/eval:** added `scripts/generate_konspekt.py` and `scripts/eval_konspekt.py` for LM Studio real-runs and structural quality checks.
- **Boundary cleanup:** moved Obsidian map/merge/compose prompt constants into `app/prompts`; universal smart-konspekt prompt is loaded through `app.prompts`; Obsidian generation uses `app.provider.get_obsidian_export_llm()`.
- **Docs:** aligned `doc/obsidian_export_todo.md` and `doc/next/smart_notes_killer_feature_plan.md` around `data/` as corpus/vault root, Phase 1 import as deferred, and Phase 2 as the active local fallback path.
- **Real-run verdict (урок 1):** `qwen3.6-27b`, 25 LLM calls, ~11.5 min, 6/6 structural checks — local is a valid offline fallback but ~3× thinner than the cloud golden (11k vs 34.6k chars). The first run suggested output truncation at `compose_max_tokens=4096`; the second run with compose `8192` stayed ~11k, but LM Studio logs showed merge calls were still clipped at 2048 tokens before compose, so the 8192 run is inconclusive as a root-cause proof.
- **Merge cap fix + clean-run verdict:** `app/smart_konspekt.py` now passes explicit `max_tokens` to `smart_konspekt.merge` calls, with regression coverage in `tests/test_smart_konspekt.py`. Clean-run after the fix failed as a quality fallback: compose used `14328` prompt tokens and hit the model/server total context cap at `16384` total tokens (`completion_tokens=2056`, `finish_reason=length`, `truncated=1`), producing an unfinished `7086`-char note with `0` Mermaid, `0` tables, and `4/6` structural checks. Package `smart-notes-native-generation-v1` is not closed as done; next valid path is section-level compose / SmartNote IR, or an explicit registry rescope.
- **Section-level design:** specified the replacement SmartKonspekt pipeline (`map→evidence reduce→outline→per-section compose→validate→assemble`) in `doc/next/smart_notes_killer_feature_plan.md`, `doc/obsidian_export_todo.md`, and `doc/backlog_registry.yaml`. The design forbids accepting `finish_reason=length` / provider `truncated=1`, requires deterministic assembly without final whole-note LLM rewrite, and adds required section/artifact gates for Mermaid, tables, terms, questions, homework, and cheatsheet.
- **Eval CLI fix:** `scripts/eval_konspekt.py:_resolve_target` now resolves relative `.md` goldens against `DATA_DIR` first (fallback `BASE_DIR`), so data-relative `--golden` paths match instead of silently reporting "missing".

## 2026-06-06 (Smart Notes plan critical review + fixes)

- **Critical review:** found 27 issues across `doc/next/smart_notes_killer_feature_plan.md` and `doc/obsidian_export_todo.md` (4 critical, 6 serious, 6 medium, 3 minor, 8 unused lecture ideas).
- **Blockers fixed:** vault path `data/vault/` → `doc/конспекты/`; added missing `SmartNoteSection` dataclass; documented tech debt (hardcoded prompts + `_get_llm()` bypass); `SmartNoteCandidate.kind` changed from `str` to `SmartNoteKind` enum.
- **Plan expanded:** added Lesson 4 reference inputs; added Phase 1.5 Smart Note → RAG Index Integration (inspired by Урок 3 lecture pattern); defined "clean note" criteria; added `validate_smart_note_markdown` acceptance criterion; added BeautifulSoup dependency note; added `backlog_registry.yaml` to session prompt write-set.
- **Todo fixed:** stale test count (8→10), stale `← СЛЕДУЮЩЕЕ` marker (Task 1→Task 3), `двухфазная`→`трёхфазная`, Phase 2 description aligned with plan, bare `python`/`pytest` → `.\.venv\Scripts\python.exe`.

## 2026-06-06 (Smart Notes existing import plan update)

- **Lesson 3 reference integrated:** `doc/next/smart_notes_killer_feature_plan.md` now covers both ready HTML smart notes and `.ts.md` files that contain an embedded smart-note layer before `# Чистый текст`.
- **Roadmap scope sharpened:** `smart-notes-html-import-v1` is broadened to existing smart-note import with conservative candidate discovery, UI status badge/default-on override, companion HTML preference, embedded Markdown extraction, and no LLM calls in Phase 1.

## 2026-06-06 (Obsidian export partial resume)

- **Partial resume:** `app/obsidian_export.py` now saves post-reduce `consolidated` notes to `.notes_cache.yaml` before compose and reuses that cache on retry when the source hash matches; successful target writes remove the cache.
- **Coverage:** added retry tests for compose failure reuse and source-change invalidation in `tests/test_obsidian_export.py`; targeted suite green (`10 passed`).

## 2026-06-06 (Smart Notes killer feature plan)

- **New plan:** `doc/next/smart_notes_killer_feature_plan.md` captures the two-step Smart Notes strategy: deterministic HTML smart-note import into Obsidian Markdown first, then native SmartNote structured generation from transcripts.
- **Roadmap links:** added `wave-smart-notes-killer-feature` with proposed packages `smart-notes-html-import-v1` and `smart-notes-native-generation-v1` to `doc/backlog_registry.yaml`; linked the plan from `doc/roadmap.md` and `doc/obsidian_export_todo.md`.

## 2026-06-06 (AI-driven design proposal — accuracy corrections)

- **Critical review applied** to `doc/next/ai_driven_design_waves_proposal.md` after verifying claims against the codebase. Fixed overstated gaps: **A3** (single-query rewrite, hybrid RRF `ParallelHybridRetriever`, and cross-encoder rerank `bge-reranker` with `enable_reranker=True` already ship — rescoped to *multi-query expansion + lost-in-the-middle reorder*); **A2** (~10 per-task models already in `config.py` — rescoped to *unified tier policy + vision/reasoning tiers*, dropped "one model for everything"); **RAGAS/I4** (`recall@k`/`MRR` already in `eval_retrieval_comparison.py` — framing narrowed to `context_precision@k` + `answer_correctness`); **A4** (acknowledge existing prompt-level abstain, gap is schema-enforcement).
- **Registry sync:** rescoped `wave-advanced-rag-rewrite-rerank` north_star and renamed its packages `query-reformulation-v1`/`answer-rerank-v1` → `multi-query-expansion-v1`/`lost-in-middle-reorder-v1` to reflect the real gap; `tasklist.md` regenerated; lint PASS.
- **Doc fixes:** corrected stale "не записаны в реестр / не тронут" statements (5 waves are promoted), and fixed broken source-link depth (`../../../exchange` → `../../../../exchange`) in the proposal and the RAGAS contract.
- **Second audit (remaining 8 waves):** verified A1/A5/U1–U4/I1/I3 against the codebase. Found 6 more overstated gaps and tightened them. Notably **I2 (promoted)** — `redact_sensitive_text` already exists in `guardrails.py`, so the wave was rescoped from "build a redactor" to "extend the existing redactor to all sinks (logs/OTel-traces/session_tape)"; package `pii-redaction-v1` → `redaction-sink-coverage-v1` in the registry. Proposal prose also tightened: **I3** (direct injection `detect_prompt_injection` + HTTP `RateLimitMiddleware` already ship → scope to indirect/ingested injection + poisoning scan + per-loop tool limits), **U2** (`debug_panel`/`sources` exist → add memory-facts/history-window receipt), **U3** (`condense_step` already compacts → add conflict-resolution + durable-fact extraction), **U4** (ad-hoc confirm-gates exist → add unified policy + memory-attack guard), **A5** (doc loading already parallel `_load_documents_parallel` → scope to agentic router + multi-stage subagent orchestration). A1/I1/U1 verified accurate.

## 2026-06-05 (AI-driven design waves — starter cluster promoted)

- **New proposal:** `doc/next/ai_driven_design_waves_proposal.md` — 13 waves / 27 packages derived from `summary_01-ai-driven-design.md`, grouped by architecture / UX / infrastructure impact and docked into the SSR killer feature. (vLLM wave dropped; cost-telemetry folded into the multi-model tier router; added A5 Agentic Orchestrator and I4 RAGAS waves.)
- **Registry promotion (proposed):** added 5 waves to `doc/backlog_registry.yaml` as the "Quality, Trust & Measurement" starter cluster — `wave-pii-masking-redaction`, `wave-grounding-abstain-contract`, `wave-advanced-rag-rewrite-rerank`, `wave-langfuse-eval-loop`, `wave-ragas-eval-harness`. All `proposed`; no `ready`/`wip` slot taken (Truth View invariant preserved; `active_wave_id`/`active_package_id` unchanged). `doc/tasklist.md` regenerated via `backlog_registry_lint.py --sync-from-index --write-sync`; lint PASS (233 items).
- **Execution contract:** expanded `ragas-retrieval-metrics-v1` into a full contract (registry item + `doc/next/ragas_retrieval_metrics_v1_contract.md`). Sharp scope after gap analysis: `recall@k`/`MRR` already exist in `app/eval_retrieval_comparison.py`, so the package adds only rank-aware `context_precision@k` + `answer_correctness` vs reference, with `ragas` as an optional `ENABLE_RAGAS_METRICS` cross-check (default off, local-first).

## 2026-06-05 (knowledge-graph D3 visualization breakthrough)

- **New beautiful Knowledge Graph:** `app/ui/knowledge_graph_d3.py` renders a self-contained D3.js force-directed concept graph (inlined `doc/assets/d3.v7.min.js`, CDN fallback) matching the `doc/doc_graph.html` quality. Learning-native encodings: node fill = difficulty level, **circular mastery ring** = quiz mastery %, node size = foundational reach, pulsing gold halo = "ready to learn" frontier (prereqs mastered, concept not yet learned).
- **Interactions:** directional prerequisite-flow highlight (blue = ancestors / "learn first", gold = descendants / "unlocks"), learning modes (Весь граф / Что учить дальше / Мой прогресс / Пробелы), search with `↑↓⏎` dropdown nav, cluster hulls, minimap, concept deep-link (`#c=<id>`), missing-prerequisite flags.
- **Tab rewrite:** `app/ui/dashboards_graph.py` now shows the D3 graph as the centerpiece with a concept selector preserving all Streamlit actions (open topic / synthesis / plan) and rich document cards; the classic `streamlit-agraph` view moved to a collapsed fallback expander. `VisualizationService` contract unchanged.
- **Tests:** existing `tests/test_knowledge_graph_viz.py` and `tests/test_mastery_dashboard.py` green; added payload coverage in `tests/test_knowledge_graph_d3.py`.

## 2026-06-05 (folder-to-course-delight-v1 closure)

- **Roadmap closure:** `folder-to-course-delight-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-16.0` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-06-05 (localhost balance breakthrough v4)

- **Planning doc sync:** `doc/next/localhost_balance_course_delight_breakthrough.md` updated to v4 after Smoke Gate v7 and ADR-024; stale running-smoke, smoke-checker-hardening, and SSR fallback gap claims were replaced with accepted evidence and the next active package `folder-to-course-delight-v1`.
- **Navigation sync:** `doc/readme.md`, `doc/index.md`, and `doc/roadmap.md` now point to breakthrough v4 / ADR-024 and show `folder-to-course-delight-v1` as the current active package instead of the old proposed localhost-balance package.
- **Roadmap sync:** `doc/roadmap.md` updated again after SSoT advanced: `folder-to-course-delight-v1` is closed and `golden-e2e-graduation-v1` is the current ready package.

## 2026-06-04 (prompt smoke gates hardening follow-up)

- **Prompt smoke gates:** `require_no_fallback`, `require_model`, and `max_reasoning_tokens` now fail closed when required telemetry is missing; `run_prompt_smoke.py` persists a compact `debug_summary` for auditability.
- **Smoke dataset:** LMS A-F cases now require local qwen model, no fallback, and zero reasoning tokens.
- **SSR fallback contract:** provider tests now cover default block on unreachable SSR loopback and explicit `SSR_ALLOW_MAIN_LLM_FALLBACK=true` opt-in; `.env.example` and user guide details document the new default.
- **Next quality package:** added proposed `prompt-role-unification-v1` to harden remaining tutor/quiz/minicheck user-only prompt paths into `system + user` or an explicit allowlist with smoke coverage.
- **ADR:** accepted ADR-024, selecting `qwen/qwen3.6-27b` as the balanced local learning-plane model based on Smoke Gate v7.

## 2026-06-03 (model-role provider hardening)

- **Model-role contract:** added typed graph LLM settings for `GRAPH_LLM_API_BASE` and `GRAPH_MODEL`, so the local graph/concept role can be enforced through `get_settings()` instead of being ignored as extra env.
- **Provider routing:** added `get_graph_llm()` and shared role routing so secondary cloud roles such as `openai/gpt-4o-mini` and `google/gemma-4-31b-it` use `OPENAI_API_BASE`, while local balanced ids such as `qwen/qwen3.6-27b` stay on the LM Studio base.
- **Graph-role enforcement:** tutor pedagogical orchestration and the experimental `PedagogicalRouter` now default to `get_graph_llm()` for graph/subgraph reasoning; quiz generation remains on the quiz role.
- **Static guard:** added `doc/next/model_role_registry.md` and `tests/test_model_role_contract.py` to guard provider-only client construction, graph-role tutor orchestration, and raw env access allowlists.
- **Regression tests:** covered graph settings, local graph LLM routing, and cloud-base routing for rewrite/classifier/judge/ingestion/evaluate roles.

## 2026-06-03 (transparent localhost balance guard)

- **Privacy guard:** primary chat cloud fallback now requires `HOME_RAG_DATA_MODE=demo` or explicit `HOME_RAG_LLM_CLOUD_CONSENT=true`; real-data balanced mode no longer silently falls back to cloud when local CB is open.
- **Source metadata:** primary chat LLM clients are annotated with `llm_source`, `llm_model`, `llm_api_base`, `fallback_used`, and `llm_profile`; `/ask` debug and `pipeline_trace.generate_stage` expose source metadata plus generation latency.
- **UI transparency:** the Q&A answer area, status sidebar, and debug panel now show the answer LLM source (`Local` / `Cloud` / `Cache`), model, fallback marker, profile, and generation latency; cloud answers also surface the consent notice.
- **Regression tests:** covered real/demo fallback policy, cross-base fallback blocking in `llm_resilience`, and `/ask` debug/trace source metadata.

## 2026-06-01 (Architecture review findings — doc guard, SSR dependency cleanup)

- **Architecture review fixes:** resolved `AR-2026-05-31-001/002/003` by documenting recent modules, removing the duplicate `retrieval_cache_discovery` staging function, and annotating `quiz_scoped.py` broad exceptions with `BLE001` degradation rationale.
- **Backend boundary cleanup:** moved exact SSR explanation cache/feedback helpers to backend-safe `app/ssr_explanation_cache.py` and Adaptive Plan teaser text to `app/adaptive_plan_progress.py`; `ssr_explain_service.py`, `ssr_feedback_collection.py`, `ssr_pregeneration.py`, and `quiz_micro_receipt.py` no longer import from `app.ui`.
- **Regression guards:** added checks for `F811` suppressions, new unannotated broad exceptions, backend→UI imports, and undocumented app modules. Full guard run still reports the carried `query_service.py` line-count debt (`845 > 800`).
- **Baseline:** archived `doc/archive/arch_review_incremental_2026-05-31.md` and updated `doc/archive/arch_review_baseline.yaml`.

## 2026-06-01 (BM25 OOM fix — lean nodes, byte-aware guard, per-chunk original_text, health check)

- **Root cause:** ChromaDB collection bloated to 21 GB for 2 docs. `_apply_contextualized_chunks`
  stored the entire source document (~91 KB) as `original_text` in every chunk's metadata before
  splitting. LlamaIndex node parsers then copied that metadata into each node's PREV/NEXT
  `RelatedNodeInfo`, tripling it to ~270 KB/node. BM25's full-corpus `collection.get` OOM'd the
  pyo3/Rust layer (`MemoryError` → uncatchable `PanicException`), crashing the Streamlit tutor.
- **Fix #1 (lean relationship nodes):** `app/ingestion_index_nodes.py` `_strip_relationship_metadata`
  clears copied neighbor metadata from PREV/NEXT/SOURCE `RelatedNodeInfo` after parsing (keeps
  node_id/node_type/hash). After reindex: `_node_content` 270 KB → 93 KB/node, DB 144 MB → 74 MB.
- **Fix #2 (byte-aware BM25 guard):** `app/hybrid_retrieval.py` `_nodes_from_chroma` projects total
  fetch bytes from the first page and aborts to vector-only fallback above `_BM25_MAX_TOTAL_BYTES`
  (~500 MB), in addition to the count-based `_BM25_MAX_NODES` guard. Panic net widened to
  `except BaseException` (pyo3 `PanicException` is not a subclass of `Exception`).
- **Fix #3 (per-chunk original_text):** `app/ingestion.py` `_apply_contextualized_chunks` no longer
  stores the full source document as `metadata["original_text"]` at the document level. Instead,
  `_build_nodes` in `app/ingestion_index_nodes.py` sets `node.metadata["original_text"] = node.text`
  per node after splitting (sentence_splitter); `SentenceWindowNodeParser` already handled this via
  `original_text_metadata_key`. After reindex: `_node_content` 93 KB → 4.4 KB/node, DB 74 MB → 5.3 MB.
  `app/knowledge_synthesis.py` synthesis path unaffected (falls back to `chunk_text` when key absent,
  and now always receives the correct per-chunk text).
- **Monitoring — regression tests:** two new tests in `tests/test_ingestion_split_metadata.py`:
  `test_apply_contextualized_chunks_does_not_store_full_doc_as_original_text` (asserts no doc-level
  `original_text`) and `test_sentence_splitter_nodes_have_per_chunk_original_text` (asserts each
  node's `original_text` ≤ 2× chunk_size chars).
- **Monitoring — health-check script:** `scripts/check_chroma_health.py` queries `chroma.sqlite3`
  directly (no embeddings/server) and reports p50/p95/max `_node_content` sizes with WARN (> 8 KB)
  and FAIL (> 30 KB) thresholds; exits non-zero for CI/post-ingest gating.
- **Test bundle green:** `test_query_service`, `test_api`, `test_hybrid_retrieval`,
  `test_ingestion_index_nodes`, `test_ingestion_split_metadata` (8 tests, all pass).

## 2026-05-31 (epoch-micro-quiz-progress-bridge-v1 closure)

- **Roadmap closure:** `epoch-micro-quiz-progress-bridge-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-5.1, US-9.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-31 (epoch-flashcard-review-progress-bridge-v1 closure)

- **Roadmap closure:** `epoch-flashcard-review-progress-bridge-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-15.2, US-9.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-31 (epoch-srs-overdue-soft-recovery-v1 closure)

- **Roadmap closure:** `epoch-srs-overdue-soft-recovery-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-7.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-31 (epoch-ssot-drift-20260531 closure)

- **Roadmap closure:** `epoch-ssot-drift-20260531` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-16.0, US-7.3` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-31 (epoch-latency-budget-quiz-surface-v1 closure)

- **Roadmap closure:** `epoch-latency-budget-quiz-surface-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-5.1, US-3.5` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-31 (epoch-latency-budget-surface-rollout-v1 closure)

- **Roadmap closure:** `epoch-latency-budget-surface-rollout-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-3.1, US-3.5` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-31 (epoch-ssr-weekly-study-narrative-v1 closure)

- **Roadmap closure:** `epoch-ssr-weekly-study-narrative-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-30 (epoch-ssr-misroute-policy-learning-v1 closure)

- **Roadmap closure:** `epoch-ssr-misroute-policy-learning-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-29 (epoch-ssr-graph-routing-v1 closure)

- **Roadmap closure:** `epoch-ssr-graph-routing-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.4, US-20.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-27 (epoch-ssr-graph-routing-eval-scaffold-v1 closure)

- **Roadmap closure:** `epoch-ssr-graph-routing-eval-scaffold-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.1, US-20.4` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-24 (strong-move-session-tape-v1 closure)

- **Roadmap closure:** `strong-move-session-tape-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-3.1, US-7.3, US-16.0` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-24 (strong-move-latency-budget-contracts-v1 closure)

- **Roadmap closure:** `strong-move-latency-budget-contracts-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-1.2, US-3.1, US-16.0` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-24 (strong-move-first-session-cold-open-v1 closure)

- **Roadmap closure:** `strong-move-first-session-cold-open-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-1.2, US-3.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-24 (strong-move-first-session-precompute-v1 closure)

- **Roadmap closure:** `strong-move-first-session-precompute-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-1.2, US-3.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.
- **Closure remediation:** Playwright chromium installed; `flashcards_course_generation.spec.ts` — API-only smoke (убран лишний Streamlit onboarding); `local:course-loop` 5/5 green; sp2 UI deferred в `deferred.md`.

## 2026-05-24 (epoch-ssr-concept-recovery-ladder-v2 closure)

- **Roadmap closure:** `epoch-ssr-concept-recovery-ladder-v2` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-23 (plan: epoch-ssr-concept-recovery-ladder-v2 sp1b+sp2)

- **backlog_registry.yaml:** добавлен `epoch-ssr-concept-recovery-ladder-v2` (`ready`, wave_position 2) — persistence learner metadata, UI wiring SSR card/tutor/adaptive, e2e recovery branch; v1 notes уточнены как sp1a-only closure.
- **Wave queue:** `wave-ssr-concept-recovery-ladder` теперь включает v1 (closed) + v2 (ready).

## 2026-05-23 (epoch-ssr-concept-recovery-ladder-v1 closure)

- **Roadmap closure:** `epoch-ssr-concept-recovery-ladder-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-23 (localhost-balance-course-delight-v1 closure)

- **Roadmap closure:** `localhost-balance-course-delight-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-1.2, US-3.1, US-16.0, US-7.3` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-23 (doc-sync: roadmap + registry after localhost-balance plan)

- **backlog_registry.yaml:** добавлена волна `wave-localhost-balance-course-delight` (proposed) и пакет `localhost-balance-course-delight-v1` (proposed, P0, cost L). Active package count: 1 proposed.
- **roadmap.md:** §8.1 статус backlog обновлён (68 волн, 1 proposed); §8.3 candidate table — строка #0 для нового прорыва; timeline mermaid — секция «Localhost Delight (proposed)»; вехи (milestone #12); waves-таблица — новая строка proposed; doc audit — ссылка на plan.

## 2026-05-23 (plan: localhost balance + course delight loop)

- **Next-level plan:** добавлен `doc/next/localhost_balance_course_delight_plan.md` — детальный контекст и план реализации Localhost Balance Mode + Course Delight Loop.
- **Product focus:** зафиксирован сдвиг от "ещё одна AI-фича" к frictionless localhost ritual: balanced provider fallback, понятный AI status, course activation, scoped answer → tutor → quiz → flashcards/SRS → adaptive next step → next-session promise.
- **Course upload:** план расширен фичей "добавить материал в активный курс из UI": persistent upload в `data/docs/<course>/`, safe partial ingest / refresh, cache invalidation и включение нового документа в scoped answers, quiz, flashcards и adaptive plan.
- **Docs index:** `doc/index.md` получил ссылку на новый next-level план в секции продуктового видения.
- **Critical review fixes (revision):** план переработан после ревью —
  (1) убрано воссоздание `app/course_graduation.py` (нарушало AR-2026-04-29-004; graduation остаётся в `app/ui/graduation_overlay.py`);
  (2) fallback политика явно ограничена primary chat LLM, secondary LLM channels (quiz/SSR/ingestion/llamaindex/classifier/rewrite/evaluate/judge) — out-of-scope;
  (3) новые soft/hard timeouts описаны как complement к существующему `LLM_LOCAL_CB_*`, не дубликат;
  (4) пути курсов унифицированы на `data/docs/<course>/` (вместо несуществующего `data/<course>/`);
  (5) `DEMO_SAFE` расщеплён на ось profile (`LOCAL_STRICT`/`BALANCED`/`CLOUD_FAST`) и ось `HOME_RAG_DATA_MODE` (`real`/`demo`);
  (6) AI status copy выровнено: явно сказано, что retrieved context уходит в LLM, добавлен отдельный статус embeddings provider;
  (7) golden E2E зафиксирован как один сценарий без "or" — pre-seeded index содержит только lecture_01+lecture_02, lecture_03 проверяет реальный upload→reindex pipeline;
  (8) промис рендерится единственным компонентом (`resume_cards_tutor.py`), mission control его подключает;
  (9) добавлен create-from-upload путь для пользователей без active course;
  (10) каждая Scope-строка помечена *(new)* / *(extend)* / *(context)*;
  (11) добавлена эвристика course candidate (≥ 3 файла в подкаталоге `data/docs/`) и порог через `HOME_RAG_COURSE_CANDIDATE_MIN_FILES`;
  (12) ingest summary дополнен embeddings status; sequencing передвинут так, чтобы Ingest summary шёл до Golden E2E;
  (13) уточнено: upload-эндпоинт защищён `HOME_RAG_API_KEY`; anti-goal про storage сужено до DB/state с carve-out на product corpus;
  (14) предложено исправление pre-existing typo `google/gemma-4-e4b` → `gemma-3n-e4b` при синхронизации `.env.example`.

## 2026-05-23 (localhost-only launchpad)

- **Local readiness gate:** добавлен `scripts/local_readiness.py` для проверки `.venv`, `.env`, локальных каталогов, портов `8000/8501`, provider URLs и health endpoints уже запущенного стека.
- **One-command local launcher:** добавлен `scripts/local_start.ps1`, который сначала выполняет readiness gate, затем делегирует запуск существующему `scripts/run_local_stack.ps1`.
- **Developer shortcuts:** добавлены `npm run local:check` и `npm run local:check:running`.
- **Docs:** README и quickstart переведены на Localhost-only launcher как рекомендуемый первый путь.

## 2026-05-23 (doc-sync: roadmap + vision + user_stories actualization)

- **Roadmap sync:** `doc/roadmap.md` актуализирован с 2026-05-06 до 2026-05-23: 27 новых волн (SSR AI Vision L1-L2, ADR-021, Expert Controls, Mission Control), обновлены все секции (timeline, milestones, distribution, candidate table).
- **Vision sync:** `doc/vision.md` актуализирован с 2026-05-04: добавлены SSR AI Vision, Mission Control, Expert Controls, ADR-021 RAG profiles; обновлён вектор развития (production deploy, AI Vision L3-L5, gamification).
- **US sync:** `doc/user_stories.md` актуализирован: 87 closed, 0 open, `open_candidates` пуст.
- **Аналитика:** создан `roadmap_analysis_2026-05-23.md` с матрицей рисков AI SSR (12 рисков, 2 critical, 5 medium).
- **Ключевой вывод:** Впервые за историю проекта backlog полностью чист — ни `proposed`, ни `wip`, ни `ready` пакетов. Все 87 US закрыты, все 13 MoT покрыты.

## 2026-05-23 (ssr-l2-tiered-explanation-gate-v1 closure)

- **Roadmap closure:** `ssr-l2-tiered-explanation-gate-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.17, US-20.2, US-20.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-22 (epoch-ssr-local-route-simulator-v1 closure)

- **Roadmap closure:** `epoch-ssr-local-route-simulator-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.13` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-22 (incremental architecture review remediation)

- **Architecture Review:** Resolved all warning-level findings from the May 22, 2026 incremental review (`inline/arch_review_incremental_2026-05-22.md`).
- **Conventions & Exceptions:** Annotated 8 lifespan/warm-up `except Exception` blocks in `app/api.py` and 38 broad exception handlers in UI/service modules with `# noqa: BLE001` + rationale, extending the regression guards accordingly.
- **Structural Splits:**
  - Split `app/eval_service.py` (916L) into dedicated helper modules (`app/eval_baseline.py` and `app/eval_helpers.py`), leaving a 434L facade.
  - Decomposed `app/ui/dashboards.py` (645L) by extracting tab renderers into `app/ui/dashboards_progress.py` and `app/ui/dashboards_graph.py` to form a 14L clean facade.
- **Regression Guards & Doc-Sync:** Updated `doc/architecture.md` with 10 split-wave modules, added line count / function size checks, and bumped top-level markdown limits to 50 in `scripts/arch_regression_guards.py`. All checks and 118+ pytest tests are fully passing.

## 2026-05-22 (epoch-ssr-source-coverage-route-guard-v1 closure)

- **Roadmap closure:** `epoch-ssr-source-coverage-route-guard-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.1, US-11.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-21 (epoch-ssot-drift-20260521 closure)

- **Roadmap closure:** `epoch-ssot-drift-20260521` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-20 (defense critical hardening)

- **Defense readiness:** added optional `HOME_RAG_API_KEY` / `X-API-Key` protection for non-health REST endpoints, with Streamlit UI forwarding the key for local API calls.
- **CI:** added `.github/workflows/ci.yml` with focused API/provider tests and Docker build verification.
- **Defense docs:** corrected deploy/CI claims in presentation materials so public URL/VPS deploy is shown as a pending target until a real server, domain, and secrets exist; clarified confidence as retrieval-source quality, not answer truth probability.

## 2026-05-20 (epoch-orchestrator-e2e-test-2 closure)

- **Roadmap closure:** `epoch-orchestrator-e2e-test-2` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-20 (epoch-orchestrator-e2e-test closure)

- **Roadmap closure:** `epoch-orchestrator-e2e-test` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-19 (trigger architecture: critical review + orchestrator design)

- **TUI trigger plan:** revised `workflow_deepseek_tui_trigger_implementation_plan.md` with 5 critical fixes: TypeScript tests (vitest) instead of Python for core parsing/validation logic; explicit cwd detection with `process.chdir(repoRoot)` guard; pre-run context estimation before spawning; session-level vs tool-level error distinction; outcome-based contract validation instead of plan-signal detection.
- **TUI trigger plan:** fixed 3 design inconsistencies: unified metrics path (`trigger_metrics.jsonl`), `_trigger_shared.ts` child process adapter extension, honest delta assessment from shared code.
- **ADR:** extended ADR-018 trigger executor classification with two new alternatives: child process adapter pattern for TUI integration, and Smart Trigger Orchestrator for automatic strategy selection.
- **Design:** created `doc/team_workflow/guides/workflow_trigger_orchestrator_design.md` — meta-trigger architecture with risk-based strategy selection, credential detection, automatic fallback chains, plan-then-execute strategy for medium-risk packages, and 4-phase implementation roadmap.
- **TUI trigger implementation:** Built full `deepseek_tui_agent_trigger.ts` with `StreamJsonAccumulator` for stdout parsing, token budget estimation gates, and outcome-based `_tui_contract_validator.ts`. 12 unit tests using `vitest`.
- **Smart Trigger Orchestrator:** Implemented Phase 0 `trigger_orchestrator.ts` with automatic credential detection, risk classification via heuristics, and strategy delegation logic (tests covered). Added `workflow_deepseek_tui_trigger_guide.md`.
- **Integration testing:** Finalized `tests/test_deepseek_tui_trigger_integration.py` passing end-to-end orchestration tests by mocking DeepSeek binary across platforms (`DEEPSEEK_CLI_CMD` dynamic injection). The autonomous DeepSeek TUI orchestration pipeline is fully verified.
- **Hardening audit (4 critical + 3 serious fixes):** Fixed `spawnSync("npx")` ENOENT on Windows (C1); added `TRIGGER_STRATEGY` validation with default-case guard (C2); fixed `startHeartbeat()` called with 0 args instead of 5 causing crash after 30s (C3); aligned `TriggerResult` shape — all returns now include `contractContent: null` (C4); `detectCredentials()` now respects `DEEPSEEK_CLI_CMD` override (S1); documented Phase 0 single-step limitation (S2); added `mkdirSync` before metrics write (M1).
- **Next-level orchestrator (Phase 1 — all 4 levels):** L1: automatic fallback chain when primary executor fails (cursor → deepseek_tui and vice versa); L2: full multi-step execution (plan_then_execute, review_execute_verify) with `ORCHESTRATOR_STEP_ROLE` env context passing between steps; L3: risk score breakdown (`classifyRiskWithScore`) written to metrics + `scripts/trigger_metrics_reporter.py` observability dashboard with per-strategy/trigger success rates and adaptive status; L4: history-based adaptive credential weighting — cursor demoted to deepseek_tui when success rate < 40% over last N runs. **Final Polish:** `.deepseekignore` added (cut TUI context from 2.4M to ~100k); fixed `DEEPSEEK_CLI_CMD` Windows spacing bug; planner correctly outputs to `doc/current_task_refined.md`; updated workflow error hints; implemented circuit breaker and self-healing retries with `ORCHESTRATOR_REJECT_REASON`. New test file `tests/trigger/orchestrator_integration.test.ts` with 16 tests (49 total, 100% pass).

## 2026-05-18 (epoch-ssr-route-confidence-ledger-v1 closure)

- **Roadmap closure:** `epoch-ssr-route-confidence-ledger-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-18 (bright-forging architecture review follow-up)

- **ADR:** added `ADR-022` for the local-first SSR-AI eval harness and artifact contract.
- **Arch baseline:** marked `AR-2026-05-17-007`, `AR-2026-05-17-010`, and the stale Telegram test finding `AR-2026-04-29-014` resolved in `doc/archive/arch_review_baseline.yaml`.
- **Logging sweep:** closed `AR-2026-05-02-005`; repo-wide inline `import logging` lines now carry `# noqa: BLE001` rationale.
- **Verification:** feedback router wiring/API docs are confirmed; no runtime behavior changed.
- **Workflow hardening:** `scripts/deepseek_agent_trigger.ts` now rejects ASCII/curly command-plan responses such as "I'll start ..." before they can become `execution_contract.md`; added a regression test for invalid command plans and valid `EXECUTION_PROOF` contracts.
- **DeepSeek workflow:** documented `deepseek_agent_trigger.ts` as an experimental Chat API handoff-only path; the target executor path is now the DeepSeek TUI trigger plan in `doc/team_workflow/guides/workflow_deepseek_tui_trigger_implementation_plan.md`.
- **ADR:** extended ADR-018 with trigger executor classification and a comparison of DeepSeek Chat API, DeepSeek TUI, Cursor SDK, manual IDE handoff, and future protocol-adapter options.

## 2026-05-17 (epoch-ssr-contrastive-why-not-others closure)

- **SSR UX:** добавлен детерминированный блок «почему не тьютор / quiz / карточки / прогресс сейчас»: `smart_study_why_not_others_ru` в `app/smart_study_recommendation.py`, баннер Mission Control (`e2e-mc-ssr-why-not-others`) и карточка «Умный следующий шаг» (`e2e-ssr-why-not-others`); маршрутизатор без изменений.
- **Regression:** расширены `tests/test_smart_study_router.py`, `tests/test_mission_control.py`, smoke `tests/e2e/smart_study_router.spec.ts`.
- **Roadmap closure:** `epoch-ssr-contrastive-why-not-others` → `closed`, волна `wave-ssr-contrastive-trust-v1` → `completed` в `doc/backlog_registry.yaml`.

## 2026-05-17 (epoch-adr-021a-a1-retrieval-router-profile-split closure)

- **Roadmap closure:** `epoch-adr-021a-a1-retrieval-router-profile-split` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.7, US-12.10` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-17 (perf: BM25 disk persistence)

- **Perf:** `app/hybrid_retrieval.py` — BM25Retriever now persists to `chroma_db/bm25_index/` via `BM25Retriever.persist()` / `from_persist_dir()`. On restart, index loads from disk (~50–200ms) instead of rebuilding from Chroma + BM25 tokenisation (~18s). Eliminates the primary cause of 4000ms `engine_acquire_ms` on every session query after restart.
- **Fix:** `app/hybrid_retrieval.py` — `invalidate_bm25_cache()` now takes `clear_disk=False` (default). Disk index is preserved on normal shutdown so the next startup benefits from the cache. `clear_disk=True` is passed only from reindex paths (`activate_staging_index`, `ingestion_index_full`) to ensure stale data is evicted after corpus changes.
- **Diag:** `app/api.py` — `_bm25_warmup_background()` logs at thread start and emits `exc_info=True` on failure, making silent skip failures visible.

## 2026-05-17 (epoch-adr-021a-architecture-lifts-design closure)

- **Roadmap closure:** `epoch-adr-021a-architecture-lifts-design` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.7, US-12.10` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-17 (kg-completeness-audit closure)

- **Roadmap closure:** `kg-completeness-audit` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.11` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-17 (epoch-adr-021-global-analytics-design closure)

- **Roadmap closure:** `epoch-adr-021-global-analytics-design` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.7, US-12.10` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-16 (epoch-adr-021-global-analytics-design closure)

- **Design ADR (ADR-021 Phase 4):** `doc/adr_021a_global_analytics_design.md` created — specifies GlobalAnalyticsJob, artifact ownership, provenance, recomputation rules (weekly scheduled + on-demand), cost ceilings, Settings-based kill switch (`enable_global_analytics`), and API/UI boundaries.
- **API reference update:** `doc/api_reference.md` — added Global Analytics section (design-time, endpoints deferred).
- **Architecture doc update:** `doc/conventions_architecture.md` — added `data/graph_analytics/` tree and Global Analytics rules.
- **Roadmap closure:** `epoch-adr-021-global-analytics-design` moved to closed.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

- **Roadmap closure:** `epoch-adr-021-profile-surfacing` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.7, US-12.10` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-16 (epoch-adr-021-prompt-selector-contract closure)

- **Roadmap closure:** `epoch-adr-021-prompt-selector-contract` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.7, US-12.10` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-15 (epoch-adr-021-graph-evidence-gating closure)

- **Roadmap closure:** `epoch-adr-021-graph-evidence-gating` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.7, US-12.10` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-15 (ssr-ai-vision-level2-level3-readiness-gate closure)

- **Roadmap closure:** `ssr-ai-vision-level2-level3-readiness-gate` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.8, US-20.9` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-15 (epoch-expert-controls-phase-2 closure)

- **Roadmap closure:** `epoch-expert-controls-phase-2` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-5.1, US-6.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-15 (epoch-expert-controls-phase-1 closure)

- **Roadmap closure:** `epoch-expert-controls-phase-1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-15.2, US-4.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-15 (ssr-misroute-feedback-collection closure)

- **Roadmap closure:** `ssr-misroute-feedback-collection` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.10` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-15 (ssr-weekly-planner-baseline closure)

- **Roadmap closure:** `ssr-weekly-planner-baseline` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.9` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-15 (ssr-ai-shared-infra-v1 closure)

- **Roadmap closure:** `ssr-ai-shared-infra-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.8` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-15 (epoch-adr-021-router-contract-phase1 closure)

- **Roadmap closure:** `epoch-adr-021-router-contract-phase1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.7, US-12.10` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-15 (mission-critical expert layer)

- **Mission Critical UX:** Added a shared collapsed expert layer for Tutor, Flashcards, and Quiz, focused on trust signals, safe actions, and one-level-deeper raw debug.
- **Adaptive Plan transparency:** Added compact **«Почему такой порядок»** trust block with review/gap/new balance, estimated time, first step, and route signals without exposing planner weight controls.
- **Docs/tests:** Updated `doc/user_guide.md` and added focused UI-helper coverage for Adaptive Plan trust summary.

## 2026-05-14 (expert controls recommendations)

- **Product recommendation:** Added `doc/expert_controls_recommendations.md` with detailed scope for Expert Controls across Flashcards, Tutor, Quiz, and Adaptive Plan.
- **Backlog registration:** Added proposed follow-up wave `wave-expert-controls-2026-05` with Phase 1 (`epoch-expert-controls-phase-1`) and Phase 2 (`epoch-expert-controls-phase-2`) packages.
- **Execution discipline:** Kept both packages `proposed` so the singleton `ready/wip` backlog slot remains unchanged until PO promotion.

## 2026-05-14 (ssr-l2-reliability-v1 closure)

- **LLM endpoint config:** Added `LLM_API_BASE` as the chat/quiz LLM base URL and routed `LLM_MODEL`, `QUIZ_LLM_MODEL`, and scoped LLM clients through it; `OPENAI_API_BASE` remains for embeddings defaulting.
- **Roadmap closure:** `ssr-l2-reliability-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.7` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-13 (epoch-mission-control-home closure)

- **Mission Control home:** Replaced the stacked home ribbon with a dedicated `Mission Control` view: SSR banner, seven destination tiles, recommended-tile highlighting, and breadcrumb return.
- **Navigation cleanup:** Added Course and Adaptive Plan destinations, moved secondary tools into the sidebar, and kept `home_hub.render_mode_selector()` as a compatibility shim.
- **Course picker polish:** Course activation now previews indexed documents, stores `source_paths` in the active scope, and confirms deactivation.
- **Regression coverage:** Added `tests/test_mission_control.py` and `tests/e2e/mission_control.spec.ts`, and updated home hub coverage for the new delegation contract.

## 2026-05-12 (nested hearth plan execution)

- **User guide truth-in-scope:** Clarified SSR AI Vision status as `Now, gated` / `Now` / `Roadmap`, added SM-2 primer, glossary link, first-5-minutes screenshots, and troubleshooting.
- **PO router Phase 3:** Added evaluation-contract validation and ML package scaffold scripts with focused pytest coverage; documented AI eval failure modes, anti-patterns, escape hatches, and Row 13 → Row 15 dependency.
- **SSR-AI roadmap registration:** Added proposed Wave 3/4/readiness-gate packages for shared infra, weekly planner baseline, misroute feedback collection, KG audit, and L2→L3 gate; reserved L3-L5 eval-contract stubs.
- **SSR-AI summary sync:** Updated `doc/team_workflow/ssr_ai_vision/ssr_ai_vision_summary.md` so Levels 1-5 reflect registry reality: L1 delivered but serving-gated, L2 delivered with fallback, L3-L5 roadmap packages only.

## 2026-05-12 (team workflow archive layout)

- **Architecture guard cleanup:** Reduced top-level `doc/team_workflow/*.md` count to the guarded limit by moving examples, SSR AI Vision materials, and one-off audit/runbook snapshots into dedicated subdirectories.
- **Docs sync:** Updated workflow links and README navigation for the new `examples/`, `ssr_ai_vision/`, and `archive/` layout.

## 2026-05-11 (incremental arch review remediation)

- **SSR architecture:** Split Smart Study Router facade into recommendation, evidence, and ML-hybrid modules; split Adaptive Daily Plan UI facade into LLM enrichment, hub layout, full-card layout, and next-step card renderers.
- **Contracts:** Added ADR-020, architecture module reference entries, regression guards, and adaptive plan facade invariant tests.
- **Quality fixes:** Routed logging toggles through `Settings`, pinned `numpy`, annotated broad exceptions with BLE001 rationale, and updated the arch-review baseline.

## 2026-05-10 (ml-ssr-serving-rollout-gate closure)

- **Roadmap closure:** `ml-ssr-serving-rollout-gate` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-10 (SSR Wave 1 Foundation — Remediation Complete ✅)

- **P0 remediation COMPLETE:** Restored full ML pipeline with `scripts/ml/data_collection_ssr.py`, train/test data artifacts under `data/ml/`, `scripts/ml/train_ssr_forgetting_curve.py`, `models/ssr_forgetting_curve_v1.pkl`, `scripts/ml/eval_ssr_forgetting_curve.py`, and `archive/ml_eval/ssr_forgetting_curve_v1_report.md`.
- **Honest eval:** Training now uses 80/20 split; report includes **Macro AUC-ROC 0.885** (target: ≥ 0.75), **Precision@5 0.985**, **Recall@5 0.985**, **p95 latency ~0.03ms** (target: < 50ms), confusion matrix.
- **Cold start policy:** Data collection records real sample count (73/1000 currently) and keeps serving in `rule_based` mode until 1000+ real samples collected; auto-enables ML when threshold reached.
- **A/B and monitoring:** Added `app/ssr_ml_monitoring.py` for local `cards_due_completion_rate` control/treatment aggregation plus latency, confidence, and fallback-rate summaries.
- **Regression coverage:** SSR ML contract tests now assert the new artifacts and monitoring/A/B surface (9 tests passing).
- **Production status:** ✅ **PRODUCTION READY** (cold-start gate active, serving rule_based until 1000+ samples)
- **Documentation updates:**
  - `doc/team_workflow/ssr_ai_vision/ssr_ai_vision_summary.md` — Updated § Implementation Status: all P0 blockers resolved
  - `doc/team_workflow/ssr_ai_vision/ssr_wave1_audit_summary.md` — **NEW** — Quick audit summary with metrics
  - `doc/ssr_ml_production_readiness.md` — **NEW** — Complete production readiness checklist
  - `archive/ml_eval/ssr_level1/evaluation_contract.yaml` — Added `actual_results` section with holdout metrics
- **Next steps:** Collect 927 more samples → auto-enable ML → run 2-week A/B test → production rollout if passes

## 2026-05-10 (SSR Wave 1 Foundation — Implementation Audit)

- **Critical audit:** Wave 1 Foundation (Level 1) implementation audited against ML package contract.
- **Status:** ⚠️ Technical implementation complete (204/204 tests passing), but **NOT PRODUCTION READY** — 5 critical deviations identified.
- **Deviations found:**
  1. 🔴 Missing real data pipeline (100 synthetic << 1000+ real sessions)
  2. 🔴 Missing train/test split (model trained on entire test set)
  3. 🔴 Missing eval report (AUC-ROC, Precision@5, Recall@5 undocumented)
  4. 🔴 Missing A/B test (primary metric `cards_due_completion_rate` unmeasured)
  5. 🟡 Missing monitoring (no p95 latency, confidence, fallback_rate tracking)
- **Remediation plan created:** 3 weeks (Phase 1 P0 blockers) + 1 week (Phase 2 P1 recommended)
- **Resolution:** ✅ All deviations resolved same day (see entry above)

## 2026-05-10 (epoch-e31-course-homework-playbook-ladder closure)

- **Roadmap closure:** `epoch-e31-course-homework-playbook-ladder` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-16.7` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-10 (ml-ssr-forgetting-curve-v1 closure)

- **Roadmap closure:** `ml-ssr-forgetting-curve-v1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-10 (ml-ssr-eval-harness closure)

- **Roadmap closure:** `ml-ssr-eval-harness` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-09 (ml-ssr-baseline-hardening closure)

- **Roadmap closure:** `ml-ssr-baseline-hardening` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-09 (Defense Presentation v2.0 — SSR AI Vision Edition)

- **Презентация защиты:** Создана новая версия презентации `defense_presentation_v2.md` с акцентом на SSR AI Vision как киллер-фичу.
- **Структура:** 13 слайдов с новыми слайдами 7-8, полностью посвящёнными SSR AI Vision (трансформация, 5 уровней, технологии, метрики, roadmap).
- **Стиль:** Использован эмоциональный и вовлекающий стиль с эмодзи, визуальными элементами, контрастными сравнениями "до/после".
- **Контент:** Добавлены детальные описания всех 5 уровней AI Vision с технологиями, метриками успеха, failure case plans, статусом реализации.
- **Roadmap:** Визуальный roadmap с Gantt-диаграммой, execution paths (sequential vs parallel), ключевыми вехами.
- **Конкурентное преимущество:** Добавлен анализ, почему конкуренты отстают на 12-18 месяцев.
- **Документация:** Обновлён раздел "Связанные документы" с полным списком SSR AI Vision документации.
- **Главный тезис:** Презентация теперь позиционирует hometutor как "первый в мире локальный учебный ассистент с полным AI-powered циклом".

## 2026-05-09 (SSR AI Vision Level 3-5 audit corrections)

- **Level 3-5 audit:** Applied all error patterns from Level 1-2 audit to Level 3 (Weekly Planner), Level 4 (Graph Router), and Level 5 (Feedback Loop).
- **Failure Case Plans:** Added BLOCK/TRY/PASS thresholds for all ML components (Level 3 ML optimization, Level 5 policy learning).
- **Detailed Risks:** Updated 17 risks with concrete mitigations (3 steps each = 51 specific actions).
- **Success Metrics:** Added "(target)" markers and warnings about non-guaranteed results for all metrics.
- **Uniformity:** All 5 levels now have identical quality standards (Failure Case Plans, Detailed Risks, Target Metrics, Concrete Thresholds, Warnings).
- **Documentation:** Created `ssr_ai_vision_audit_level3_5_report.md` and `ssr_ai_vision_audit_level3_5_corrections.md`.
- **Summary update:** Updated `ssr_ai_vision_summary.md` to v1.1 with audit history section.

## 2026-05-09 (SSR AI Vision Level 1/2 audit fixes)

- **Level 1:** aligned execution artifacts with audit recommendations: synthetic SM-2 cold-start policy, 1000+ real-sample gate, AUC-ROC `<0.70` blocker, XGBoost retry band, and required A/B test.
- **Level 2:** enforced token-budget fallback in the UI helper (`>700` tokens returns template fallback, `>500` logs compression warning) and synced evaluation/monitoring docs.
- **Readiness gate:** added `ssr-ai-vision-level1-level2-readiness-gate`; Level 1 eval/harness is GO, Level 1 ML serving is NO-GO, Level 2 integration is GO, and Level 2 automatic UI-time rollout is NO-GO until latency/human-eval gates pass.

## 2026-05-09 (llm-ssr-explanation-integration closure)

- **Roadmap closure:** `llm-ssr-explanation-integration` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.7` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-09 (llm-ssr-prompt-engineering closure)

- **Roadmap closure:** `llm-ssr-prompt-engineering` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.7` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-09 (llm-ssr-explanation-eval closure)

- **Roadmap closure:** `llm-ssr-explanation-eval` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.7` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-08 (epoch-ssr-next-quiet-mode closure)

- **Roadmap closure:** `epoch-ssr-next-quiet-mode` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.12` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-08 (epoch-ssr-next-outcome-receipts closure)

- **Roadmap closure:** `epoch-ssr-next-outcome-receipts` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.11` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-08 (epoch-ssr-next-steering-toggles closure)

- **Roadmap closure:** `epoch-ssr-next-steering-toggles` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.10` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-08 (epoch-ssr-next-learning-debt-queue closure)

- **Roadmap closure:** `epoch-ssr-next-learning-debt-queue` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.9` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-08 (epoch-ssr-next-confidence-ledger closure)

- **Roadmap closure:** `epoch-ssr-next-confidence-ledger` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.8` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-08 (epoch-ssr-next-contrastive-explanations closure)

- **Roadmap closure:** `epoch-ssr-next-contrastive-explanations` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.7` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-08 (smart-study-router-next-level planning)

- **Ideation execution:** `archive/ideation/smart_study_router_next_level_2026-05-08.md` converted into proposed Smart Study Router next-level waves.
- **CJM / US sync:** `doc/cjm.md` now tracks contrastive explanation, confidence ledger, learning debt, steering, outcome receipt, and quiet mode opportunities; `US-20.7`-`US-20.12` added as open Epic 20 stories.
- **Backlog sync:** `doc/backlog_registry.yaml` adds three proposed next-level waves and six proposed packages, with `wave-smart-study-router-next-level-trust` as the active proposed wave.

## 2026-05-06 (architecture PlantUML views)

- **Architecture docs:** `doc/architecture.md` now includes self-contained PlantUML views: C4 system context, C4 containers, query/tutor components, indexing components, `/ask` sequence, product learning loop, and local deployment/storage.
- **Doc-sync:** architecture freshness marker updated to 2026-05-06; `doc/token_safety_registry.json` and `doc/token_safety.md` refreshed after the larger architecture doc.

## 2026-05-06 (epoch-smart-study-router-surface-parity closure)

- **Roadmap closure:** `epoch-smart-study-router-surface-parity` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-06 (epoch-smart-study-router-surface-parity wip)

- **Smart Study Router:** карточка SSR на вкладке «Прогресс» монтируется в `main.py` до `_fragment_learning_progress_tab`, чтобы smoke видел её вне частичного fragment-rerun.
- **E2E smoke:** `tests/e2e/smart_study_router.spec.ts` — проверка карточки на Flashcards hub и Progress (`e2e_view=flashcards` / `progress`).
- **Backlog:** волна `wave-smart-study-router-surface-parity`, пакет `epoch-smart-study-router-surface-parity` (`wip`).

## 2026-05-06 (epoch-qbi-learning-metrics-validation closure)

- **Roadmap closure:** `epoch-qbi-learning-metrics-validation` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.9` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-06 (epoch-qbi-stage-cost-latency-budgets closure)

- **Roadmap closure:** `epoch-qbi-stage-cost-latency-budgets` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.8` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-06 (workflow router tests + auto-promote hygiene)

- **Tests:** циклы `execution_auto` с `--watch-contract` в `tests/test_workflow_router.py` изолируют `workflow.REGISTRY` во временный YAML — реальный `doc/backlog_registry.yaml` не перезаписывается.
- **Auto-promote:** учёт `covered_by: "open"` в `scripts/auto_promote_next_wave_package.py`; регрессия в `tests/test_ssot_pipeline.py`.
- **Backlog:** промоут `epoch-qbi-stage-cost-latency-budgets` → `ready`, волна `wave-quality-defense-observability` → `wip`, `active_wave_id: null`.

## 2026-05-06 (epoch-qbi-adversarial-regression-gate closure)

- **Roadmap closure:** `epoch-qbi-adversarial-regression-gate` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.10` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-06 (epoch-qbi-adversarial-corpus-runner closure)

- **Roadmap closure:** `epoch-qbi-adversarial-corpus-runner` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.10` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-06 (epoch-qbi-baseline-regression-gate closure)

- **Roadmap closure:** `epoch-qbi-baseline-regression-gate` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.7` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-06 (epoch-qbi-retrieval-mode-comparison closure)

- **Roadmap closure:** `epoch-qbi-retrieval-mode-comparison` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.7` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-06 (epoch-qbi-golden-eval-dataset closure)

- **Roadmap closure:** `epoch-qbi-golden-eval-dataset` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.7` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-06 (workflow execution contract encoding hardening)

- **Workflow router:** `scripts/workflow.py` now reads legacy UTF-16 `execution_contract.md` files best-effort and rewrites them as UTF-8 before state routing.
- **Execution handoff:** `scripts/run_autonomous.py` now emits Windows `Set-Content ... -Encoding utf8` for the STARTED marker instead of `Out-File` without encoding.
- **Guardrail:** `scripts/lint_agent_prompts.py` blocks future `Out-File ... execution_contract.md` prompt commands unless they explicitly specify UTF-8.
- **Artifact cleanup:** existing UTF-16 `archive/team_artifacts/*/execution_contract.md` files were normalized to UTF-8.

## 2026-05-06 (epoch-qbi-source-readiness-contract-parity closure)

- **Roadmap closure:** `epoch-qbi-source-readiness-contract-parity` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-2.5` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-06 (epoch-qbi-terminology-limitations-sync closure)

- **Roadmap closure:** `epoch-qbi-terminology-limitations-sync` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-11.2, US-12.11` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-06 (epoch-qbi-data-deletion-governance closure)

- **Roadmap closure:** `epoch-qbi-data-deletion-governance` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.11` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-06 (epoch-smart-study-router-accessibility-harness closure)

- **Roadmap closure:** `epoch-smart-study-router-accessibility-harness` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.6` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-06 (epoch-smart-study-router-trust-control closure)

- **Roadmap closure:** `epoch-smart-study-router-trust-control` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-06 (epoch-smart-study-router-core-policies closure)

- **Roadmap closure:** `epoch-smart-study-router-core-policies` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.3, US-20.4, US-20.5` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-06 (epoch-smart-study-router-card closure)

- **Roadmap closure:** `epoch-smart-study-router-card` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-20.1, US-20.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-06 (smart-study-router product-doc sync)

- **CJM sync:** `doc/cjm.md` now captures Smart Study Router opportunities for explainable next step, due review, weak-concept recovery, post-answer runway, and accessible preserved entry points.
- **US lifecycle sync:** added open `US-20.2`–`US-20.6` in `doc/user_stories/` and rebuilt `doc/user_stories_index.json` plus generated `doc/user_stories.md` sections.
- **Registry sync:** Smart Study Router packages now reference the more specific US slices and `doc/tasklist.md` was regenerated.

## 2026-05-06 (epoch-team-workflow-top-level-md-budget-2026-05 closure)

- **Roadmap closure:** `epoch-team-workflow-top-level-md-budget-2026-05` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-05 (ux-home-hub-navigation-polish closure)

- **Roadmap closure:** `ux-home-hub-navigation-polish` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-19.5` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-05 (ux-mastery-celebration-analytics closure)

- **Roadmap closure:** `ux-mastery-celebration-analytics` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-19.3, US-19.4` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-05 (ux-first-answer-wait-flow closure)

- **Roadmap closure:** `ux-first-answer-wait-flow` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-19.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-05 (ux-foundation-parsers-contracts closure)

- **Roadmap closure:** `ux-foundation-parsers-contracts` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-19.1, US-19.4` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-05 (epoch-us19-2-tutor-handoff-ux closure)

- **Roadmap closure:** `epoch-us19-2-tutor-handoff-ux` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-19.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-05 (UX Breakthrough Wave planning)

- **New wave:** `wave-ux-breakthrough-2026-05` added to `doc/backlog_registry.yaml` with status `proposed`.
- **New package:** `ux-breakthrough-wave` added to registry with 5 linked User Stories (US-19.1 to US-19.5).
- **Epic 19:** Created Epic 19 "UX Breakthrough Wave" with 5 User Stories covering MoT #2, #3, #9, #12, #13.
- **User Stories:** Created US-19.1 (Wait UX), US-19.2 (Tutor Handoff), US-19.3 (Celebration), US-19.4 (Session Analytics), US-19.5 (Home Hub).
- **Spec files:** Complete spec created in `.kiro/specs/ux-breakthrough-wave/` (requirements, design, tasks).
- **Documentation sync:** Updated `doc/user_stories_index.json`, `doc/user_stories.md`, `doc/user_stories_details.md`, `doc/user_scenarios.md`.

## 2026-05-05 (UX Breakthrough Wave critical review)

- **Scope correction:** Replaced the single large `ux-breakthrough-wave` package contract with five execution-sized packages in `doc/backlog_registry.yaml`: `ux-foundation-parsers-contracts`, `ux-first-answer-wait-flow`, existing ready `epoch-us19-2-tutor-handoff-ux`, `ux-mastery-celebration-analytics`, `ux-home-hub-navigation-polish`.
- **Risk reduction:** Reduced the former write-set 21 umbrella into focused package write-sets (4-8 files) with targeted pytest bundles and read-set hints.
- **Spec repair:** Rewrote `.kiro/specs/ux-breakthrough-wave/requirements.md`, `design.md`, and `tasks.md` in readable UTF-8; added cross-cutting constraints for config/provider/prompts/user_state boundaries.
- **US sync:** Updated US-19.1 to US-19.5 related package references and aligned requirement numbers after the spec split.

## 2026-05-17 (trigger runtime refactor review)

- **Workflow triggers:** shared trigger runtime now keeps Cursor proof ownership intact (`cursor_agent_trigger.ts` does not overwrite `execution_contract.md`), keeps metrics status compatible as `finished`, and only treats a literal `STARTED` proof stub as stallable.
- **Docs:** documented the shared `_trigger_shared.ts` runtime, DeepSeek trigger command, and trigger-specific env knobs in `.env.example`.

## 2026-05-04 (epoch-cursor-sdk-trigger-reliability closure)

- **Roadmap closure:** `epoch-cursor-sdk-trigger-reliability` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-03 (epoch-cjm-pain-map-ssot-sync closure)

- **Roadmap closure:** `epoch-cjm-pain-map-ssot-sync` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-3.6` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-03 (workflow-dx-p6-cursor-sdk-trigger closure)

- **Roadmap closure:** `workflow-dx-p6-cursor-sdk-trigger` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-03 (epoch-arch-review-p5b-god-modules-wave4-infra-config closure)

- **Roadmap closure:** `epoch-arch-review-p5b-god-modules-wave4-infra-config` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-03 (epoch-arch-review-p5b-god-modules-wave3-query-graph closure)

- **Roadmap closure:** `epoch-arch-review-p5b-god-modules-wave3-query-graph` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-03 (epoch-arch-review-p5b-god-modules-wave2-product-services closure)

- **Roadmap closure:** `epoch-arch-review-p5b-god-modules-wave2-product-services` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-03 (epoch-arch-review-p5b-god-modules-wave1-ingestion closure)

- **Roadmap closure:** `epoch-arch-review-p5b-god-modules-wave1-ingestion` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-03 (epoch-arch-review-p5c-ui-tabs-decompose closure)

- **Roadmap closure:** `epoch-arch-review-p5c-ui-tabs-decompose` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-03 (epoch-arch-review-p5a-knowledge-service-split closure)

- **Roadmap closure:** `epoch-arch-review-p5a-knowledge-service-split` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-03 (epoch-mot2-two-stage-answer closure)

- **Roadmap closure:** `epoch-mot2-two-stage-answer` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-3.6` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-03 (SSoT: tasklist только через lint)

- **close_package / auto-promote:** `doc/tasklist.md` больше не правится вручную в этих скриптах; после изменений реестра пересборка через `backlog_registry_lint.py --sync-from-index --write-sync`.
- **backlog_registry_lint:** при синке снимаются устаревшие блоки `### … Contract` с маркером GENERATED из реестра, затем вставляются актуальные активные контракты.
- **roadmap_sync_check:** формулировки ошибок для слотов ready/wip приведены к «Truth View slot» (источник — реестр, не markdown-таблица).

## 2026-05-03 (epoch-arch-review-p5d-learning-plan-split closure)

- **Roadmap closure:** `epoch-arch-review-p5d-learning-plan-split` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-6.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-03 (epoch-arch-review-p5e-telegram-handler-tests closure)

- **Roadmap closure:** `epoch-arch-review-p5e-telegram-handler-tests` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-03 (epoch-arch-review-p4-ingestion-loader-decompose closure)

- **Roadmap closure:** `epoch-arch-review-p4-ingestion-loader-decompose` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-03 (epoch-arch-review-p3-orphaned-modules closure)

- **Roadmap closure:** `epoch-arch-review-p3-orphaned-modules` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-03 (epoch-arch-review-p2-inline-logging-noqa closure)

- **Roadmap closure:** `epoch-arch-review-p2-inline-logging-noqa` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-03 (workflow.py conductor mode)

- **CLI:** `scripts/workflow.py` — добавлен conductor mode (`--loop`, `--loop-max`, `--watch-contract`, `--watch-timeout`): полный non-stop конвейер от `proposed` до `closed` без ручных шагов между командами. Граф переходов: `needs_plan` → `ready_fresh` → `ready_orch` (ждёт `execution_contract.md`) → `--post-agent` → re-route.
- **CLI:** `scripts/workflow.py` — флаг `--skip-review`: в состоянии `needs_plan` выдаётся hint с автоматическим вторым вызовом после Phase 7; в `ready_fresh` выполняет `generate_orchestration_prompt` без отдельного `--exec`.
- **Документация:** обновлены `doc/team_workflow/workflow_router.md`, `README.md`, `workflow_decision_tree.md`, `process.md`, `generate_plan_next_prompt.md`, `doc/prompts_usage_guide.md`, `doc/prompts_catalog.md`.

## 2026-05-03 (workflow-dx-p4-common-rules closure)

- **Roadmap closure:** `workflow-dx-p4-common-rules` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-1.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-02 (architecture review → backlog wave)

- **Registry:** добавлена волна `wave-arch-review-remediation-2026-05` в `doc/backlog_registry.yaml` (статус `proposed`): пакеты P1–P4 и P5 (эпики A–E, волны B1–B4 по модулям >600L).
- **Baseline link:** в `doc/archive/arch_review_baseline.yaml` у `last_review` указано `backlog_wave_id: wave-arch-review-remediation-2026-05`.
- **Governance:** `doc/roadmap_governance.md` — раздел «Architecture review remediation (incremental, 2026-05-02)».
- **Навигация:** `doc/index.md` — строка про `archive/arch_review_baseline.yaml` в таблице бэклога.

## 2026-05-02 (epoch-mot2-wait-ux-engagement closure)

- **Roadmap closure:** `epoch-mot2-wait-ux-engagement` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-3.5` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-02 (MoT #2 breakthrough ideation → backlog)

- **Ideation:** приняты идеи из `archive/ideation/mot2_first_answer_latency_eval_2026-05-02.md` (perceived latency UX + two-stage answer path).
- **User stories:** добавлены `US-3.5`, `US-3.6` в `doc/user_stories/`; обновлены `doc/user_stories_index.json`, генерируемые блоки в `doc/user_stories.md` и §8 `doc/cjm.md` (lint sync).
- **CJM:** `doc/cjm.md` — блок opportunities для MoT №2 / First Answer и расширена колонка Opportunity для стадии First Answer.
- **Эпоха (описание):** `doc/epochs/e31_mot2_perceived_latency.md`.
- **Registry:** волна `wave-mot2-perceived-latency` (`active_wave_id`), пакеты `epoch-mot2-wait-ux-engagement`, `epoch-mot2-two-stage-answer` в статусе `ready`; `doc/tasklist.md` пересобран.

## 2026-05-02 (epoch-ocr-docling-ingest-phase1 closure)

- **Roadmap closure:** `epoch-ocr-docling-ingest-phase1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-2.3` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-02 (epoch-us-2-3-chunk-index-proof closure)

- **Roadmap closure:** `epoch-us-2-3-chunk-index-proof` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-2.3` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-02 (epoch-demo closure)

- **Roadmap closure:** `epoch-demo` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-02 (epoch-home-mode-preview-drawer closure)

- **Roadmap closure:** `epoch-home-mode-preview-drawer` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-14.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (epoch-us-2-4-source-readiness-mvp closure)

- **Roadmap closure:** `epoch-us-2-4-source-readiness-mvp` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-2.4` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (epoch-ocr-docling-ingest-phase1 closure)

- **Roadmap closure:** `epoch-ocr-docling-ingest-phase1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-2.3` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (epoch-us-2.3-non-text-corpus-contract closure)

- **Roadmap closure:** `epoch-us-2.3-non-text-corpus-contract` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-2.3` остаётся **open** (док-пакет фиксирует только контракт до OCR; полный ingest в общий индекс — будущая работа). `user_stories` у закрытого пакета пустой.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (epoch-source-readiness-diagnostic-story closure)

- **Roadmap closure:** `epoch-source-readiness-diagnostic-story` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (epoch-ocr-docling-story-gate closure)

- **Roadmap closure:** `epoch-ocr-docling-story-gate` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** добавлена и остаётся **открытой** `US-2.3` (non-text corpus ingest); пакет не закрывает эпик OCR — только story-gate. `user_stories` у закрытого пакета пустой, чтобы не считать US покрытой реализацией.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (epoch-ocr-docling-story-gate planning)

- **Roadmap planning:** `epoch-ocr-docling-story-gate` added as the next ready package under `wave-ocr-docling-story-gate`; scope is Analyst/Product story definition, not OCR implementation.
- **Deferred guard:** `ocr-docling` remains `deferred` and now depends on a distinct open US before it can be absorbed into implementation work.
- **US lifecycle sync:** no linked US files changed; the package explicitly flags the missing non-text corpus ingest story for Analyst.

## 2026-05-01 (epoch-check-backlog-drift-token-registry closure)

- **Roadmap closure:** `epoch-check-backlog-drift-token-registry` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (epoch-home-mode-intent-ordering closure)

- **Roadmap closure:** `epoch-home-mode-intent-ordering` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-18.4` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (future roadmap archive cleanup)

- **Roadmap cleanup:** `doc/future_roadmap.md` now keeps only strategic status,
  closed-horizon links, and re-entry rules instead of duplicating closed package
  details.
- **Closed history:** added `doc/epochs/e5.md`, `doc/epochs/e7.md`, and
  `doc/epochs/e8.md`; indexed them in `doc/closed_iterations.md`.
- **Registry backfill:** historical E5.0-E5.8, E7.0-E7.3, and E8.1-E8.2 slices
  are represented in `doc/backlog_registry.yaml` as completed waves with closed
  package items.

## 2026-05-01 (epoch-course-recovery-budget-slider closure)

- **Roadmap closure:** `epoch-course-recovery-budget-slider` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (epoch-course-next-session-promise closure)

- **Roadmap closure:** `epoch-course-next-session-promise` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (epoch-course-confidence-dip-detector closure)

- **Roadmap closure:** `epoch-course-confidence-dip-detector` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (epoch-home-mode-preview-drawer closure)

- **Roadmap closure:** `epoch-home-mode-preview-drawer` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-14.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (epoch-home-mode-flashcard-time-badge closure)

- **Roadmap closure:** `epoch-home-mode-flashcard-time-badge` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-15.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (epoch-home-mode-card-labels closure)

- **Roadmap closure:** `epoch-home-mode-card-labels` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-14.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (epoch-course-retention-polish closure)

- **Roadmap closure:** `epoch-course-retention-polish` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-17.8, US-17.10, US-17.11` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (First Answer QA smoke — epoch-answer-trust DoD)

- **E2E:** добавлен `@smoke` `tests/e2e/first_answer_trust_handoff_smoke.spec.ts` — вкладка Quick Answer под offline stub проверяет confidence/источники, captions моста Q→тьютор и CTA «Учить эту тему».
- **E2E:** исправлен условный corpus-smoke в `aqe_wave_coverage_smoke.spec.ts` (убрана несуществующая подстрока «Stub source»; проверка через текст фрагмента из offline payload + заголовок «Источники»).
- **Roadmap:** в `epoch-answer-trust-to-learning-path.dod_commands` добавлен запуск этого smoke (архивная запись контракта).

## 2026-05-01 (epoch-answer-trust-to-learning-path closure)

- **Roadmap closure:** `epoch-answer-trust-to-learning-path` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-3.2, US-4.1, US-6.2, US-3.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (epoch-generate-orchestration-prompt-token-registry closure)

- **Roadmap closure:** `epoch-generate-orchestration-prompt-token-registry` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.5` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (epoch-check-llm-context-gate-token-registry closure)

- **Roadmap closure:** `epoch-check-llm-context-gate-token-registry` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.5` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (epoch-run-autonomous-token-registry closure)

- **Roadmap closure:** `epoch-run-autonomous-token-registry` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (epoch-cjm-progress-next-action closure)

- **Roadmap closure:** `epoch-cjm-progress-next-action` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-14.1, US-9.1, US-6.1, US-7.3, US-12.6` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-05-01 (epoch-backlog-active-wave-determinism closure)

- **Roadmap closure:** `epoch-backlog-active-wave-determinism` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-30 (audit chain control plane)

- **check_audit_chain_state:** regex for `## Next Action` tolerates the section at EOF; `coverage_packages_total` auto-heal with `--write-raw-check` updates `summary` anchored on `_audit_raw.json`; final summary aggregates `commands_run` from each package.
- **Workflow prompts:** coverage group files and coverage prompt document `coverage_packages_total` in Raw JSON Update.
- **Tests:** `tests/test_check_audit_chain_state.py` covers replacement, command aggregation, and auto-heal round-trip on a minimal tree.

## 2026-04-30 (epoch-context-cart-token-metrics closure)

- **Roadmap closure:** `epoch-context-cart-token-metrics` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-30 (epoch-token-registry-measure-reconcile closure)

- **Roadmap closure:** `epoch-token-registry-measure-reconcile` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-29 (epoch-ingestion-loader-token-registry closure)

- **Roadmap closure:** `epoch-ingestion-loader-token-registry` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-29 (epoch-doc-ingestion-split-arch-sync closure)

- **Roadmap closure:** `epoch-doc-ingestion-split-arch-sync` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-29 (epoch-ingestion-loader-extraction closure)

- **Roadmap closure:** `epoch-ingestion-loader-extraction` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-29 (architecture review phase 3 follow-up)

- **ADR compliance:** clarified ADR-016 so `app/metrics.py` is an explicit thin compatibility facade, while implementation logic stays in decomposed metrics modules.
- **Quality follow-up:** annotated broad exception handlers in ingestion, query post-processing, and knowledge service with explicit BLE001 rationales; removed debug-only inline logging artifacts.
- **Dependency follow-up:** pinned previously unpinned direct requirements, annotated optional voice dependencies, and added an aiogram router compatibility check.
- **Course subsystem:** added ADR-017 for Course Workspace progression, graduation, pace ownership, persistence boundaries, and metrics integration.
- **Autonomous runner:** added ADR-018 for the local autonomous control-plane runner, proof artifacts, gates, and HITL closure constraints.
- **Architecture reference:** documented `course_graduation.py`, `pace_engine.py`, `warmup_planner.py`, and `diagnostic_service.py` in the module reference.

## 2026-04-29 (architecture review phase 2 follow-up)

- **Architecture guards:** `scripts/arch_regression_guards.py` now enforces the `app/ingestion.py` 2100-line regression threshold from Phase 2 review.
- **Ingestion decomposition:** extracted ingestion environment diagnostics/preflight logging into `app/ingestion_env_diag.py`; `app/ingestion.py` is now below the guard threshold.
- **Course-mode module intent:** documented intended consumers for `diagnostic_service.py`, `warmup_planner.py`, and `course_graduation.py` to distinguish deferred wiring from anonymous dead code.
- **Roadmap:** `doc/tasklist.md` records the completed guard fix and leaves loader extraction as the next optional ingestion cleanup slice.

## 2026-04-29 (autonomous control-plane failure classes)

- **Control plane:** `failure_classifier.py` now loads exit-code classes from `policies/failure_classes.yaml`.
- **Result contract:** `pipeline_result.schema.json` documents the structured `failure_class` payload written to `result.json`.
- **Quality/observability:** `quality_gates.run_all()` results now have matrix summaries; `pipeline_status.py` aggregates `failure_class_counts`.
- **Runner integration:** `run_autonomous.py --post-agent` now uses the shared `quality_gates.run_all()` facade instead of calling pipeline guard logic directly.
- **Observability validation:** `pipeline_status.py` includes a lightweight structural validator for the `runs`/`stats` JSON subset.
- **Thin task safety:** large GUI tasks now spill into `doc/context_pack.md` while preserving `## Write-Set` in `doc/current_task.md` for drift gates.
- **Evals:** adversarial evals now cover prompt routing fallback, write-set drift, retry budget, stale result, and proof tampering.
- **Regression launcher:** added `scripts/run_control_plane_regression.ps1` with strict control-plane gates and JSON reports under `archive/team_artifacts/_regression/`.
- **Backlog sync:** formalized Wave 2 control-plane merged-continuation packages in `doc/backlog_registry.yaml` and `doc/closed_iterations.md`.
- **Runbook/observability:** refreshed `run_autonomous_runbook.md`, added pretty SLO/failure-class output, and covered stale result/retry/write-set gate negatives.
- **Hook integration:** Cursor pipeline hook now consumes shared `quality_gates.run_all()` output and emits the same gate summary shape as runners.
- **Concurrency/HITL:** documented lock call-sites and enforced HITL approval for `close_package.py` closures that skip DoD.
- **Git hygiene:** ignored generated control-plane regression reports under `archive/team_artifacts/_regression/`.
- **Tests:** added policy-loading, quality-gate matrix, observability, and prompt-routing eval coverage.

## 2026-04-28 (epoch-control-plane-v3-core closure)

- **Roadmap closure:** `epoch-control-plane-v3-core` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-28 (epoch-llm-regression-baseline closure)

- **Roadmap closure:** `epoch-llm-regression-baseline` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.4` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-28 (epoch-latency-slo-gate closure)

- **Roadmap closure:** `epoch-latency-slo-gate` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-27 (epoch-concept-remediation-step closure)

- **Roadmap closure:** `epoch-concept-remediation-step` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-4.2, US-9.2, US-14.4` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-27 (epoch-mastery-gap-routing closure)

- **Roadmap closure:** `epoch-mastery-gap-routing` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-4.1, US-8.1, US-8.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-27 (epoch-answer-quality-baseline closure)

- **Roadmap closure:** `epoch-answer-quality-baseline` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-3.1, US-3.2, US-12.4` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-27 (epoch-aqe-corpus-choice closure)

- **Roadmap closure:** `epoch-aqe-corpus-choice` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-3.1, US-3.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-27 (epoch-tour-demo-doc-refresh closure)

- **Roadmap closure:** `epoch-tour-demo-doc-refresh` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-27 (epoch-tour-scenarios-10-14 closure)

- **Roadmap closure:** `epoch-tour-scenarios-10-14` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-7.2, US-8.1, US-8.2, US-10.1, US-10.2, US-10.3, US-15.4, US-15.6, US-16.0, US-16.1, US-16.2, US-16.3, US-16.4, US-16.5, US-16.6` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-27 (epoch-demo closure)

- **Roadmap closure:** `epoch-demo` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-27 (epoch-tour-persistence-ch2-5 closure)

- **Roadmap closure:** `epoch-tour-persistence-ch2-5` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-4.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-27 (epoch-tour-skeleton-ch1 closure)

- **Roadmap closure:** `epoch-tour-skeleton-ch1` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-1.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-26 (epoch-demo-scenario-08-trust closure)

- **Roadmap closure:** `epoch-demo-scenario-08-trust` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-2.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-26 (epoch-e30-idea-2-retrieval-gates closure)

- **Roadmap closure:** `epoch-e30-idea-2-retrieval-gates` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-17.11` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-26 (epoch-e30-idea-1-daily-runway closure)

- **Roadmap closure:** `epoch-e30-idea-1-daily-runway` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-17.10` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-26 (epoch-e30-e1-course-graduation closure)

- **Roadmap closure:** `epoch-e30-e1-course-graduation` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-17.9` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-26 (epoch-e30-d2-focus-mode closure)

- **Roadmap closure:** `epoch-e30-d2-focus-mode` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-17.7` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-26 (epoch-e30-d1-smart-resume closure)

- **Roadmap closure:** `epoch-e30-d1-smart-resume` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-17.8` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-26 (epoch-e30-c2-pace-engine closure)

- **Roadmap closure:** `epoch-e30-c2-pace-engine` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-17.3` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-26 (epoch-truth-sync closure)

- **Roadmap closure:** `epoch-truth-sync` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-26 (roadmap sync autocorrect integration)

- **Roadmap guard:** `scripts/roadmap_sync_check.py` теперь запускает `scripts/auto_correct_registry_closed_status.py` перед проверкой и возвращает `exit 2`, если pre-check автокоррекция не прошла.
- **Registry autocorrect:** добавлен `scripts/auto_correct_registry_closed_status.py` для автоматического выравнивания статусов в `doc/backlog_registry.yaml` по факту закрытых пакетов из `doc/closed_iterations.md`.
- **Coverage:** добавлены тесты pre-check пути в `tests/test_roadmap_sync_check.py` и unit-тест автокоррекции в `tests/test_auto_correct_registry_closed_status.py`.

## 2026-04-26 (e30-c1-diagnostic closure)

- **Roadmap closure:** `e30-c1-diagnostic` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-17.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-26 (e30-idea-2-retrieval-gates closure)

- **Roadmap closure:** `e30-idea-2-retrieval-gates` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-17.11` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-26 (zero-click delivery optimization: Package A+B+C)

- **Performance:** Refactor close_package.py to extract `run_close_package_impl()` — eliminated subprocess cold startup; smoke time reduced 5.2s → 4.5s (~13% faster); close_package phase 3.3s → 2.97s (~9% faster).
- **Safe closure:** Added assert in `_patch_epoch_demo_allow_verification_only()` to verify `allow_verification_only` marker was patched successfully (D8 fix). Execution contract scaffold now includes Pre-existing delivery evidence block.
- **Chain graceful end:** `--allow-empty-generator` flag now exits 0 when §Now empty (not 2), preventing "contract block not found" errors on next chain step (D3 fix).
- **Idempotency:** Verified 3× consecutive smoke runs pass with clean git status; `update_tasklist()` already idempotent (no crash on missing row).
- **Tests:** All 13 close_package tests passing; 3 sequential smoke runs confirm zero hard-gate failures.

## 2026-04-26 (e30-idea-1-daily-runway closure)

- **Roadmap closure:** `e30-idea-1-daily-runway` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-17.10` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-26 (ideation — Stage #7 course learning, US-17.10 / US-17.11)

- **CJM:** `doc/cjm.md` — в блоке Stage #7 добавлена таблица **Opportunities (ideation 2026-04-26)** (Daily Course Runway + streak chip; interleaved retrieval gates).
- **User stories:** `doc/user_stories/us-17.10.md`, `doc/user_stories/us-17.11.md`; `doc/user_stories_index.json` — пересборка индекса; `scripts/regenerate_cjm_pain_table.py --write` — сгенерированные секции в `doc/user_stories.md` и `doc/cjm.md` (§8 pain table).
- **Roadmap:** `doc/tasklist.md` § Now — пакеты `e30-idea-1-daily-runway`, `e30-idea-2-retrieval-gates` (placeholders, идеи из `archive/ideation/stage7_course_learning_2026-04-26.md`).
- **Backlog:** `doc/backlog_registry.yaml` — `epoch-e30-idea-1-daily-runway` / `epoch-e30-idea-2-retrieval-gates` в волне `wave-course-learning-v2` (contract id = строке Package в `tasklist`).
- **Contract follow-up:** `doc/backlog_registry.yaml` (`last_touched_mot: "course-workspace"`), `doc/tasklist.md` (`e30-idea-1-daily-runway` → `WIP` + write-set), `doc/epochs/e30_course_mode_v2.md` (добавлен блок ideation follow-up для `US-17.10/17.11`).

## 2026-04-26 (verification-only policy unification)

- **Policy text:** единые константы `VERIFICATION_ONLY_POLICY_LINE` / `VERIFICATION_ONLY_INCONCLUSIVE_MARKER_LINE` и helper `verification_only_policy_guidance(indent)` в `scripts/prompt_utils.py`; одинаковые подсказки в `scripts/close_package.py` и `scripts/run_autonomous.py` при блокировке verification-only.
- **Tests:** `tests/test_close_package_guards.py` — проверка stderr при неполном evidence.
- **Infra (smoke):** `run_autonomous._parse_write_set` — в regex путей добавлен префикс `scripts/` (согласовано с `prompt_utils`).

## 2026-04-26 (epoch-demo closure)

- **Roadmap closure:** `epoch-demo` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-26 (architecture review corrective sync)

- **UI architecture guard:** в `app/ui/tutor_chat.py` восстановлен low fan-out import pattern (модульные intra-UI импорты вместо широкого `from ... import ...`), чтобы убрать регресс 12 → 23 и вернуть guard-compliant структуру.
- **Reliability/logging:** в `app/knowledge_service.py` для optional FAQ enrichment оставлено production-safe `warning` логирование без debug-only паттерна.
- **Architecture doc-sync:** в `doc/architecture.md` добавлен отдельный блок `Tutorial subsystem (onboarding)` с явным описанием `tutorial_guide`, `tutorial_chapters`, `tutorial_service`.
- **Verification:** `.\.venv\Scripts\python.exe -m pytest tests/test_ui_helpers.py -q`, `.\.venv\Scripts\python.exe -m pytest tests/test_knowledge_service.py -q`.

## 2026-04-26 (e30-b2-daily-briefing closure)

- **Roadmap closure:** `e30-b2-daily-briefing` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-17.6` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-26 (e30-b1-graduation-overlay closure)

- **Roadmap closure:** `e30-b1-graduation-overlay` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-17.5` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-26 (e30-a2-cockpit-rotator closure)

- **Roadmap closure:** `e30-a2-cockpit-rotator` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-17.4` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-26 (e30-a1-cockpit-scaffold closure)

- **Roadmap closure:** `e30-a1-cockpit-scaffold` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-17.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-25 (epoch-demo-scenario-09-learning-plan closure)

- **Roadmap closure:** `epoch-demo-scenario-09-learning-plan` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-8.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-25 (epoch-demo-scenario-07-progress closure)

- **Roadmap closure:** `epoch-demo-scenario-07-progress` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-9.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-25 (user stories metadata closed_date sync)

- **US metadata sync:** для `US-1.2` и `US-3.4` заполнен `closed_date` (`2026-04-25`) в frontmatter, чтобы устранить WARN в strict-линте backlog registry.
- **Index sync:** `doc/user_stories_index.json` пересобран после обновления frontmatter.

## 2026-04-25 (epoch-demo-scenario-06-srs closure)

- **Roadmap closure:** `epoch-demo-scenario-06-srs` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-11.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-25 (wave-interactive-tour registration)

- **Roadmap planning:** зарегистрирована новая волна `wave-interactive-tour` (4 пакета: `epoch-tour-skeleton-ch1` → `epoch-tour-demo-doc-refresh`) в backlog-реестре и wave queue.
- **Governance sync:** синхронизированы `doc/backlog_registry.yaml`, `doc/tasklist.md`, `doc/future_roadmap.md`, `doc/roadmap_governance.md`; source plan: `C:/Users/educa/.claude/plans/atomic-gathering-token.md`.
- **Doc-sync gate:** `doc/user_stories_index.json` пересобран идемпотентно без новых US frontmatter.

## 2026-04-25 (epoch-demo-scenario-04-quiz closure)

- **Roadmap closure:** `epoch-demo-scenario-04-quiz` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-14.4` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-25 (epoch-demo-scenario-03-tutor closure)

- **Roadmap closure:** `epoch-demo-scenario-03-tutor` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-3.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-24 (epoch-ui-main-split closure)

- **Roadmap closure:** `epoch-ui-main-split` moved to closed as verification-only; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.
- **Audit correction:** closure evidence now states that no product files changed in this run and points to a product-changing evidence commit.

## 2026-04-24 (epoch-plan-next-candidate-seed closure)

- **Roadmap closure:** `epoch-plan-next-candidate-seed` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **Audit correction:** package remains a verification-only guardrail closure; `US-12.2` was reopened because this package does not prove the maintainable UI / split `main.py` acceptance criteria.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-24 (epoch-flashcard-export-upload-r2 closure)

- **Roadmap closure:** `epoch-flashcard-export-upload-r2` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-15.4, US-15.5` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-24 (epoch-query-service-assembly-v2 closure)

- **Roadmap closure:** `epoch-query-service-assembly-v2` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-3.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-24 (epoch-architecture-review-baseline closure)

- **Roadmap closure:** `epoch-architecture-review-baseline` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.4` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-24 (epoch-query-service-assembly closure)

- **Roadmap closure:** `epoch-query-service-assembly` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-3.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-24 (epoch-flashcard-export-upload closure)

- **Roadmap closure:** `epoch-flashcard-export-upload` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-15.4, US-15.5` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-23 (audit correction for recent closures)

- **Audit correction:** `epoch-router-accuracy-baseline` reclassified as `verification_only`; closure evidence pointed to a pre-existing capability rather than a fresh product delta.
- **Audit correction:** `epoch-backup-benchmark-close`, `epoch-reindex-quiz-close`, and `epoch-srs-plan-close` reclassified as `acceptance-close`; audit trail confirmed acceptance verification but not a fresh implementation delta in those packages.
- **Audit correction:** `epoch-flashcard-export-upload` reopened; `US-15.4` and `US-15.5` returned to `open` until a new execution package provides matching product evidence.

## 2026-04-23 (epoch-router-accuracy-baseline closure)

- **Roadmap closure:** `epoch-router-accuracy-baseline` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-12.4` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-23 (epoch-first-answer-examples closure)

- **Roadmap closure:** `epoch-first-answer-examples` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-3.3` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-23 (epoch-sync-multidevice closure)

- **Roadmap closure:** `epoch-sync-multidevice` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-10.3` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-23 (epoch-sync-restore-wizard closure)

- **Roadmap closure:** `epoch-sync-restore-wizard` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-10.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-23 (epoch-plan-diff-ux closure)

- **Roadmap closure:** `epoch-plan-diff-ux` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-6.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-22 (epoch-flashcard-deck-mgmt closure)

- **Roadmap closure:** `epoch-flashcard-deck-mgmt` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-15.3, US-15.6` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-22 (epoch-wave-contract closure)

- **Roadmap closure:** `epoch-wave-contract` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-22 (epoch-backup-benchmark-close closure)

- **Roadmap closure:** `epoch-backup-benchmark-close` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-10.1, US-12.1, US-12.3` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-22 (epoch-reindex-quiz-close closure)

- **Roadmap closure:** `epoch-reindex-quiz-close` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-2.2, US-13.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-22 (epoch-srs-plan-close closure)

- **Roadmap closure:** `epoch-srs-plan-close` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-7.2, US-6.3` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-22 (epoch-srs-priority-reason closure)

- **Roadmap closure:** `epoch-srs-priority-reason` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-7.4` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-22 (epoch-citations-trust-close closure)

- **Roadmap closure:** `epoch-citations-trust-close` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-11.1, US-3.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-22 (epoch-context-cart-mvp closure)

- **Roadmap closure:** `epoch-context-cart-mvp` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-22 (epoch-mastery-after-reindex closure)

- **Roadmap closure:** `epoch-mastery-after-reindex` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-8.1, US-8.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-22 (epoch-truth-sync closure)

- **Roadmap closure:** `epoch-truth-sync` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **Audit correction:** package remains an infra truth-sync closure; `US-12.2` is not closed by this package.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-22 (epoch-ingest-first-index-progress closure)

- **Roadmap closure:** `epoch-ingest-first-index-progress` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-2.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-22 (epoch-env-required-vars closure)

- **Roadmap closure:** `epoch-env-required-vars` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-1.3` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-22 (epoch-tutor-transparency closure)

- **Roadmap closure:** `epoch-tutor-transparency` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-4.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-22 (epoch-reindex-mastery-guard closure)

- **Roadmap closure:** `epoch-reindex-mastery-guard` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-22 (epoch-quiz-hint-on-fail closure)

- **Roadmap closure:** `epoch-quiz-hint-on-fail` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-5.2` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-22 (epoch-srs-priority-queue closure)

- **Roadmap closure:** `epoch-srs-priority-queue` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-7.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-22 (epoch-adaptive-plan-today closure)

- **Roadmap closure:** `epoch-adaptive-plan-today` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** `US-6.1` marked closed in `doc/user_stories/` and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-21 (epoch-cjm-us-frontmatter closure)

- **Roadmap closure:** `epoch-cjm-us-frontmatter` moved to closed; contract removed from `doc/tasklist.md`; details in `doc/closed_iterations.md`.
- **US lifecycle sync:** no linked US files and `doc/user_stories_index.json`.
- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.

## 2026-04-21 (epoch-us7-3-resume-card closure)

- **Roadmap closure:** `epoch-us7-3-resume-card` moved out of the active backlog; `doc/tasklist.md` now keeps only the remaining proposed infra candidate in Truth View and points closed-package details to `doc/closed_iterations.md`.
- **US lifecycle sync:** `doc/user_stories/us-7.3.md` and `doc/user_stories_index.json` now mark `US-7.3` as `closed`, covered by `epoch-us7-3-resume-card`, with `closed_date=2026-04-21`.
- **Registry/history sync:** `doc/backlog_registry.yaml` marks the package `closed`, and `doc/closed_iterations.md` records the delivered day-2 resume-card outcome plus verification commands.

## 2026-04-21 (roadmap sync checker)

- **Roadmap/doc-sync gate:** added `scripts/roadmap_sync_check.py` to validate the narrow lifecycle contract across `doc/tasklist.md`, `doc/backlog_registry.yaml`, `doc/closed_iterations.md`, `doc/user_stories/*.md`, and `doc/user_stories_index.json`.
- **Focused coverage:** added `tests/test_roadmap_sync_check.py` for the repo seed plus drift cases: lingering closed-package contract in `tasklist`, missing US closure fields, and stale `user_stories_index.json`.
- **Infra contract sync:** `doc/tasklist.md` now includes `scripts/roadmap_sync_check.py` in the `epoch-cjm-us-frontmatter` target artifacts and DoD commands.
- **Local/pipeline hooks:** `package.json` now exposes `test:roadmap-sync`, `test:backlog-registry`, and `test:roadmap-docs`; `scripts/run_team_pipeline.sh` runs roadmap sync + backlog registry lint as a preflight before role execution.

## 2026-04-21 (roadmap docs cleanup)

- **Tasklist compactness:** `doc/tasklist.md` now keeps only the current `ready` package (`epoch-us7-3-resume-card`) and the next proposed infra candidate in Truth View; the closed `epoch-5min-loop-polish` contract no longer duplicates weekly backlog space.
- **Roadmap sync:** `doc/backlog_registry.yaml` now marks `epoch-5min-loop-polish` as `closed` and `epoch-us7-3-resume-card` as `ready`; downstream candidate notes now point to the current ready package.
- **Closed history:** `doc/closed_iterations.md` records the short closure summary for `epoch-5min-loop-polish`, and `doc/agent_workflow_templates.md` points at the current archived planning prompt for the active resume-card package.

## 2026-04-21 (epoch-5min-loop-polish — operational guardrail)

- **Loop runtime gate:** добавлен fail-fast runner `scripts/check_loop_metrics_gate.py` и единая команда `npm run test:loop-gate` для проверки контракта US-14.4 (`dead_end=false`, deterministic next-step, `primary_cta_count=1` на completion).
- **Local pre-push guard:** добавлен installer `scripts/install_loop_gate_pre_push.py` и npm-команда `npm run hooks:install:loop-gate`, чтобы локальный git `pre-push` запускал loop-gate до отправки изменений.
- **Smoke resilience:** `tests/e2e/micro_quiz_submit.spec.ts` переведён в устойчивый smoke-контур с browser-level проверкой и API fallback без `skip`.

## 2026-04-20 (doc/planning infrastructure gap fix)

- **US metadata:** all `doc/user_stories/us-*.md` files now have YAML frontmatter with status, CJM stage, coverage, and closure metadata; `doc/user_stories_index.json` provides a machine-readable index for planning.
- **Planning sources:** `doc/user_stories.md` now includes `Open candidates` plus Status/Coverage columns; `doc/cjm.md §8` is a structured pain-point table instead of prose-only notes.
- **Backlog automation:** `doc/backlog_registry.yaml` includes proposed next candidates, `scripts/backlog_registry_lint.py` validates registry consistency without requiring PyYAML, and `scripts/run_team_pipeline.sh` sketches the human-reviewed role pipeline.
- **Tasklist safety:** `epoch-5min-loop-polish` and its Contract remain intact; `epoch-cjm-us-frontmatter` is added as a proposed next infra candidate, not promoted over the current ready package.

## 2026-04-20 (epoch-course-workspace-f — closure)

- **Course Progress:** вкладка «Прогресс обучения» теперь показывает фильтр активного курса и отдельную панель с документами, карточками, due today, освоенными карточками, последней темой Tutor и ближайшими пробелами.
- **Course metrics:** добавлен `app/course_metrics.py` с label `course_workspace`, SLO helper-таблицей для ключевых Course Workspace сценариев и записью workflow event при открытии progress panel.
- **Hardening:** добавлен browser smoke `tests/e2e/course_progress_panel.spec.ts`: API создаёт course deck, затем Progress с seeded StudyScope должен показать course panel и label `course_workspace`.
- **Coverage:** `tests/test_progress_tab.py` покрывает active-course фильтрацию карточек и metrics label; targeted runs green — pytest 6 passed, Playwright course progress smoke 1 passed.

## 2026-04-20 (epoch-course-workspace-e — closure)

- **Flashcard gap handoff:** after reveal, review cards now offer «Не знаю, объясни»; the UI records SM-2 `quality=1` before routing to Tutor with `tutor_goal_subtopic` from the card front.
- **Return path:** Tutor footer shows «← Вернуться к карточкам» while `flashcard_review_return=True`, restoring Flashcards review without losing the review queue context.
- **Coverage:** targeted DoD run green: `tests/test_flashcard_service.py`, `tests/test_flashcards_ui.py`, `tests/test_tutor_orchestrator.py` — 40 passed.

## 2026-04-20 (epoch-course-workspace-d — closure)

- **Course Flashcards:** Flashcards generate view now exposes «Активный курс» when StudyScope is active; `/flashcards/generate` accepts `scope=course` with `source_paths`, batches generation per document, and returns one unified preview deck named after the course.
- **Review filters:** saved course decks use `source_type=course`, JSON `source_identifier` with `course_id/folder_rel`, and per-card tags `course:<id>` / `folder:<folder_rel>` so review due queues can be filtered by deck or course tags.
- **Coverage:** `tests/test_flashcard_service.py` covers course batching, API preview/save, and tag-based due filtering; targeted run green — 21 passed.

## 2026-04-20 (epoch-course-workspace-c — closure)

- **Course Prepare MVP:** во вкладке «Темы» для активного StudyScope появилась кнопка «Подготовить курс»: она одним кликом показывает состав документов, собирает synthesis по active scope и строит `/learning-plan` с `documents=scope.source_paths`.
- **Scoped cache:** добавлен JSON-кэш course artifacts (`app/course_cache.py`) с ключом от набора документов, модели и версии prompt; повторный запуск по тем же документам открывает cached plan без LLM-вызова.
- **Coverage:** добавлены `tests/test_course_cache.py`; targeted run green: `tests/test_course_cache.py`, `tests/test_knowledge_service.py`, `tests/test_study_scope.py`, `tests/test_ui_helpers.py` — 42 passed.

## 2026-04-20 (epoch-17-1-ux-tail — closure)

- **sp1 (guided entry polish):** Home/Progress surfaces now keep deterministic single primary next-step CTA with beginner-first copy and unified `Почему сейчас`/`Следующий шаг` continuity wording.
- **sp2 (QA→Tutor loop closure):** after `Учить эту тему 5 минут` handoff, Tutor flow keeps explicit completion path (`Продолжить 1 шаг` or `Готово на сегодня`) when quiz branch is unavailable, preventing dead-end states.
- **Coverage:** continuity-focused unit suite is green (`tests/test_e9_7_continuity_bridge.py`), and targeted e2e bundle for QA→Tutor context/loop (`qa_to_tutor_loop`, `unified_context_block`) is smoke-policy compatible (`env skip` accepted when no `OPENAI_API_KEY`).

## 2026-04-20 (e2e smoke bundle — unified context block)

- Added `tests/e2e/unified_context_block.spec.ts` for QA→Tutor→Home→Progress continuity assertions of `Текущий учебный контекст` + `Почему сейчас` + `Следующий шаг`.
- Updated `tests/e2e/README.md` smoke matrix and required live-key list to include the new unified-context route test.

## 2026-04-20 (epoch-unified-context-layer — closure)

- **Unified continuity UI:** `app/ui/tutor_chat.py`, `app/ui/home_hub.py`, `app/ui/pages/3_Мой_прогресс.py` now render a shared compact context block (`Текущий учебный контекст`) when QA→Tutor continuity payload is available.
- **Shared reasoning copy:** surfaces consume `tutor_reason_line_ru` and `continuity_next_step_line_ru` from `app/ui/continuity_bridge.py` for consistent user-facing reason/next-step text.
- **Coverage:** `tests/test_e9_7_continuity_bridge.py` extended to 17 passing cases with degraded payload and reason/next-step fallback checks.
- **Smoke continuity route:** `tests/e2e/qa_to_tutor_loop.spec.ts` validates that Tutor shows the unified context marker after handoff.

## 2026-04-20 (epoch-qa-tutor-handoff — closure)

- **Quick Answer → Tutor handoff:** `app/ui/query_tab.py` keeps one primary CTA and writes continuity payload via helper contract (`topic`, `last_question`, `answer_summary`, `source`) before routing to Tutor.
- **Tutor startup continuity:** `app/ui/tutor_chat_session.py` hydrates startup state from preserved QA handoff context when session fields are missing.
- **Coverage and smoke:** `tests/test_query_tab_topic_infer.py` includes handoff-summary compaction check; `tests/e2e/qa_to_tutor_loop.spec.ts` now tagged for smoke selection (`@smoke @nightly`) so package smoke command picks it deterministically.
- **Status:** package `epoch-qa-tutor-handoff` closed in `doc/tasklist.md`; closure artifacts stored in `archive/team_artifacts/epoch-qa-tutor-handoff/`.

## 2026-04-20 (docs cleanup — tasklist/changelog sync)

- **Tasklist compactness:** `doc/tasklist.md` cleaned to keep weekly backlog focused on active `Now` work; large closed execution summaries are referenced from `doc/closed_iterations.md` and `archive/team_artifacts/*` instead of being duplicated inline.
- **Backlog registry sync:** `doc/backlog_registry.yaml` now includes `epoch-5min-loop-polish` as `ready`; `epoch-context-cart-mvp` moved to queued `proposed` with explicit re-entry condition after the current user-visible package.
- **Closed index freshness:** `doc/closed_iterations.md` updated to the 2026-04-20 review date.

## 2026-04-20 (Context Cart roadmap)

- **Token planning:** `doc/archive/token_optimization_checklist.md` now fixes the Context Cart / task-aware context routing recommendations as a detailed roadmap: routing profiles, medium-doc read rules, `scripts/context_cart.py`, `--emit-agent-prompt`, DoD, tests, and P1A placement in Token Firewall.
- **MVP path:** the roadmap now prefers extending the existing JSON registry before YAML, adds mode-aware `check_readset.py` (`path:mode[:selector]`), golden cart fixtures, an `epoch-context-cart-mvp` backlog package, and `Context impact` doc-sync notes.
- **Roadmap sync:** `doc/tasklist.md` now points to the Context Cart package so the recommendation is tracked alongside the existing Token Firewall plan.

## 2026-04-20 (Cursor token guard workflow)

- **Agent workflow:** `doc/agent_workflow.md` now treats the 20k input-token hard-limit as a blocker for full Architecture Review, removes the old 80k wording, and requires phase-by-phase review.
- **Cursor-safe prompts:** planning/execution templates now separate owner/write-set from read-set and add explicit guards against full-file attachment, previous tool logs, and large test/doc reads.
- **Token estimates:** large module guidance now reflects current high-risk files such as `app/prompts.py`, `tests/test_api.py`, `doc/adr.md`, `doc/changelog.md`, and `doc/epochs/e4.md`.
- **Implementation roadmap:** `doc/archive/token_optimization_checklist.md` now includes a staged Token Firewall plan covering YAML registry, context pack builder, prompt linter, diff-only verify, signature cache, token ledger, and CI/Cursor integration.

## 2026-04-19 (LLM guard hardening)

- **P0 guards:** `app/llm_guards.py` now blocks configured expensive models, enforces the 20k hard input-token limit, and blocks unchanged retries after a recent provider error.
- **P1 accounting:** `app/provider.py` logs `OK`, `BLOCKED`, `ERR`, and `CACHE_HIT` JSONL records for sync and async chat paths.
- **Tests:** added `tests/test_llm_guards.py` and provider coverage for blocked models, hard-limit rejection, and unchanged retry rejection before provider client creation.

## 2026-04-19 (answer quality eval prerequisite)

- **Golden QA contract:** `tests/test_eval_golden_qa_contract.py` now validates in-corpus `expected_sources` as public `AskSource`-field objects (`relative_path` / `file_name`, optional `page`) and forbids internal `id` / `node_id` / `node_ids`.
- **Roadmap sync:** `doc/tasklist.md` marks `epoch-answer-quality-eval` ready for full implementation after the prerequisite split instead of leaving it as active in-progress work.

## 2026-04-19 (e2e smoke port isolation)

- **Playwright smoke:** default FastAPI/Streamlit ports moved to `18000` / `18501` for Playwright-owned runs, while `E2E_API_PORT` / `E2E_STREAMLIT_PORT` still override them.
- **Harness alignment:** Playwright config, `scripts/e2e_run_stack.mjs`, and browser-side API fixtures now share the same default API origin; the stack also exports matching `UI_API_BASE_URL` / `CORS_ORIGINS`.
- **Sync export:** `user_state_sync` now reuses the central allow-list SQL identifier quoting helpers, fixing sidebar backup export during smoke startup.
- **Backup restore smoke:** uses a narrow `e2e_restore_preview=1` query hook to test restore confirmation gating without depending on browser file-upload timing.

## 2026-04-21 (epoch-5min-loop-polish planning prompt archive)

- **Planning workflow:** archived the ready-package planning prompt for `epoch-5min-loop-polish` as `archive/agent_prompts/epoch_5min_loop_polish_planning_prompt_2026-04-21.md`.
- **Tasklist sync:** refreshed `doc/tasklist.md` date and added a compact maintenance note pointing to the archived planning prompt for the active package.
- **Prompt references:** updated `doc/agent_workflow_templates.md` archived-prompts list so fresh planning examples include the current 5-minute loop package.

## 2026-04-21 (planning prompt source correction)

- **Docs workflow:** clarified that the canonical default planning template is now the section `Шаблон planning prompt` in `doc/agent_workflow_templates.md`; `doc/agent_workflow.md` remains a slim navigation index after the split.
- **Archive sync:** refreshed `archive/agent_prompts/planning_prompt_template_2026-04-19.md`, `archive/agent_prompts/README.md`, and `doc/tasklist.md` so current instructions point to split workflow docs and the active 12k/20k token-budget contract.

## 2026-04-19 (planning prompt consolidation)

- **Docs workflow:** consolidated the default planning prompt in `doc/agent_workflow.md` as the canonical planning template for new agent threads.
- **Reference alignment:** `AGENTS.md` and `doc/token_safety.md` now point to the canonical planning template instead of duplicating prompt text.

## 2026-04-19 (roadmap cleanup)

- **Tasklist cleanup:** `doc/tasklist.md` reduced back to weekly execution backlog: active AQE-R Truth View, recent closures, next-start decision, compact `epoch-answer-quality-eval` contract, and Deferred table only.
- **Closed history sync:** closed CORS details no longer live in `tasklist.md`; `doc/closed_iterations.md` now includes the 2026-04-19 ingest acceleration slice.
- **Horizon sync:** `doc/future_roadmap.md` points to the AQE-R-gated next start instead of stale 2026-04-18 wording.

## 2026-04-19 (ingest acceleration)

- **Ingest no-op fast path:** `build_index(reset=False)` now builds a cheap file manifest before embedding preflight/PDF parsing and exits with `INGEST_SUMMARY run_kind=noop` when files, embedding model, chunking fingerprint, and the active Chroma collection are already current.
- **Extraction cache:** parsed/expanded/metadata-normalized `Document` fragments are cached in `chroma_db/ingestion_extracted_documents.json`; unchanged files reuse cached fragments, so partial reindex no longer has to re-parse every PDF/HTML/DOCX before deciding what changed.
- **Content state:** `ingestion_content_hashes.json` now stores the file manifest plus previous source-fragment/node counts for accurate no-op summaries.
- **Ops notes:** ingest prints `documents_extraction_cache` progress with reused/dirty file counts, and README / `.env.example` document the fastest normal path plus `DOC_LOAD_NUM_WORKERS` tuning.
- **Tests:** focused ingest coverage updated for manifest matching, no-op summaries, and no-op lifecycle behavior (`16 passed` on the affected subset).

## 2026-04-18 (OpenRouter embeddings recovery)

- **Embeddings provider:** `app/provider.get_embed_model()` now passes custom OpenRouter embedding IDs through `model_name` while keeping a llama-index enum-safe wrapper model, so `perplexity/pplx-embed-v1-0.6b` works through `OpenAIEmbedding`.
- **Embedding dimensions:** added `EMBED_DIMENSIONS` / `Settings.embed_dimensions` so the 1024-dimension OpenRouter embedding size is explicit and configurable.
- **Ingest recovery:** rebuilt the active Chroma index with `perplexity/pplx-embed-v1-0.6b` (1024 dimensions), `EMBED_BATCH_SIZE=32`, and 1791 nodes; `index_meta.json` now records the new embedding model.
- **Ingest diagnostics:** startup and snapshot logs now include `.env` vs process `EMBED_*` sources, and embeddings preflight validates the configured batch/model/dimensions before loading documents or deleting Chroma collections.
- **Docs/tests:** README/check-env defaults and E2E dimension-mismatch diagnostics were updated away from the stale `1536, got 768` assumption.

## 2026-04-17 (Refactoring & E2E)

- **Metrics Decomposition (`epoch-metrics-decomposition`):** Полная архитектурная декомпозиция монолитного модуля `app/metrics.py` (~1900 строк) на специализированные подмодули: `metrics_core` (схемы/пути), `metrics_storage` (JSONL), `metrics_aggregator` (in-memory), `metrics_graph_expansion` (графы), `metrics_summarizer` (аналитика/SLO), `metrics_db` (SQLite). Внедрен `MetricsModule` (Class Injection Facade) для поддержки динамического патчинга констант в тестах и надежной изоляции состояния между прогонами. Все тесты (`test_metrics.py`, `test_quality_benchmark_metrics.py`) проходят (20/20).

- **UI Refactoring:** декомпозиция `app/ui/tutor_chat.py`. Основной файл разделен на функциональные модули: `tutor_chat_header.py` (заголовки/стили), `tutor_chat_controls.py` (сессии/глубина), `tutor_chat_footer.py` (экспорт/статистика). Повышена читаемость и упрощено тестирование UI-компонентов.
- **E2E Tests:** добавлен [`long_learning_continuity.spec.ts`](../tests/e2e/long_learning_continuity.spec.ts) для верификации "North Star" сценария: Quick Answer → Tutor → Micro-quiz → Adaptive Plan.

## 2026-04-16 (stability + local hybrid embeddings runbook)

- **Stability fix:** удалено shadowing `logging` через локальные `import logging` в `app/query_response_postprocessing.py`, `app/query_service.py`, `app/pipeline_steps.py`; это устранило `UnboundLocalError` в `/ask`/retrieval path.
- **Tests:** узкий регрессионный контур по падениям -> `13 passed`; полный non-integration прогон `python -m pytest tests/ -m "not integration" -q` -> `870 passed, 1 skipped, 7 deselected`; integration retrieval `python -m pytest tests/test_integration_retrieval.py -q` -> `7 passed`.
- **Integration guard:** `tests/test_integration_retrieval.py` переведен на fail-fast диагностику chat/embeddings недоступности вместо позднего падения внутри `VectorStoreIndex`.
- **Local hybrid docs:** добавлены runbook и troubleshooting для схемы cloud LLM + local embeddings в `.env.example` и `README.md`.
- **Helper script:** добавлен `scripts/run_integration_local.ps1` для one-command локального запуска integration retrieval с временной установкой env.

## 2026-04-16 (epoch-query-service-decomposition Packages A-D)

- **Session persistence boundary:** `app/query_session_persistence.py` owns compact source metadata and chat-session persistence helpers; `app/query_service.py` keeps compatibility wrappers for existing tests/callers.
- **RAG execution boundary:** `app/query_rag_execution.py` owns QueryEngine execution, tracing, generation token accounting, graph-expansion trace propagation, and retrieval self-correction; `query_service._execute_rag_query()` delegates while preserving monkeypatch compatibility for `query_service.build_query_engine`.
- **Tutor post-processing boundary:** `app/query_response_postprocessing.py` owns answer text post-processing, source parsing, Tutor v2 parsing/formatting bridge, inline quiz generation hook, tutor decision/profile update, and auto-quiz attachment; `query_service._process_rag_response()` delegates.
- **Fallback boundary:** `app/query_fallbacks.py` owns safe fallback response assembly after output guardrail failures; `query_service._build_safe_fallback_result()` delegates while keeping local trace/quality helper compatibility.
- **Roadmap:** `doc/tasklist.md`, `doc/closed_iterations.md`, and `archive/architecture_review.md` mark `epoch-query-service-decomposition` closed on Packages A-D; Package E/final response assembly is deferred until a concrete follow-up risk appears.
- **Tests:** `.\.venv\Scripts\python.exe -m pytest tests/test_query_service.py tests/test_multi_turn.py tests/test_api.py -v` -> `107 passed`; `git diff --check` -> no whitespace errors (CRLF warnings only).

## 2026-04-16 (epoch-adr-010-acceptance)

- **ADR:** `doc/adr.md` — ADR-010 принят как `Accepted`; решение фиксирует local-first single-user persistence model и optional Telegram entrypoint на той же локальной машине.
- **Persistence boundary:** ADR-010 явно разделяет user-state таблицы (`app/user_state.py` / `_with_db()`) и независимые documented stores/artifacts: `SessionStore` (`sessions.db`), `event_tracking` (`ui_events.db`), metrics dashboard cache (`metrics_dashboard_db_path`) и KG bundle (`kg.sqlite`).
- **Roadmap:** `doc/tasklist.md`, `doc/closed_iterations.md` и `archive/architecture_review.md` синхронизированы: `epoch-adr-010-acceptance` закрыт; следующие remediation-кандидаты остаются `epoch-query-service-decomposition` и `epoch-local-cors-defaults`.

## 2026-04-15 (epoch-user-state-decomposition)

- **Persistence split:** `app/user_state.py` is now a compatibility facade over domain modules: `user_state_core`, `user_state_reading`, `user_state_research`, `user_state_quiz`, `user_state_tutor`, `user_state_flashcards`, and `user_state_sync`.
- **Contract preserved:** all domain persistence still routes through `user_state_core._with_db()`; facade monkeypatch compatibility for learner-state lineage overrides is preserved.
- **Prompt SSoT bridge:** tutor prompt helper exports remain compatible through `app/tutor_prompts.py`, while prompt logic/source lives in `app/prompts.py`.
- **Tests:** full suite passed: `862 passed, 1 skipped`.

## 2026-04-13 (epoch-local-store-contracts)

- **Persistence convention:** clarified that `app/user_state.py` / `_with_db()` owns user-state tables, while independent local SQLite stores must stay behind documented module wrappers or artifact writers.
- **Allowed stores documented:** `app/session_store.py`, `app/event_tracking.py`, `app/metrics.py`, and `app/knowledge_graph_bundle.py` now have explicit ownership notes in `doc/conventions_architecture.md`.
- **Roadmap:** `doc/tasklist.md` and `doc/closed_iterations.md` mark `epoch-local-store-contracts` closed as a documentation/architecture-contract slice.

## 2026-04-13 (epoch-exception-hygiene)

- **`/ask` boundary:** `app/routers/query.py` — broad catches for best-effort history/FAQ persistence and final unknown-error HTTP 500 mapping now have explicit `# noqa: BLE001` justifications.
- **Pipeline fallback:** `app/pipeline_steps.py` — broad fallback catches in `run_step_safe`, subquestion generation, optional KG lookup, and tutor orchestrator fallback now document their graceful-degradation purpose.
- **Tests:** `tests/test_api.py` covers history/FAQ persistence failures that must not fail `/ask`; `tests/test_pipeline_steps.py` covers subquestion failure and optional KG lookup fallback.
- **Artifacts:** orchestration and role reports saved under `archive/team_artifacts/epoch-exception-hygiene/`.

## 2026-04-13 (epoch-prompt-source-of-truth)

- **Prompt SSoT:** `app/prompts.py` расширен как единый источник prompt-текста для pipeline/tutor/quiz/ingestion (включая `CLASSIFY_SYSTEM_PROMPT`, `REWRITE_SYSTEM_PROMPT`, `SUBQUESTION_SYSTEM_PROMPT`, `INGESTION_*`, tutor/orchestrator и quiz follow-up шаблоны).
- **Pipeline/quiz/ingestion:** `app/pipeline_steps.py`, `app/quiz_service.py`, `app/ingestion_metadata.py` переведены с локальных строковых шаблонов на импорты из `app/prompts.py`.
- **Tutor/UI:** `app/tutor_prompts.py` переключён на bridge к `app/prompts.py` для prompt-констант (builder/helper API сохранены); `app/ui/interactive_quiz.py` и `app/ui/tutor_chat.py` используют `QUIZ_PROMPT` из `app/prompts.py`.
- **Тесты:** целевой набор для tutor/pipeline/ingestion/quiz прогоняется как регрессия на эквивалентность поведения.

## 2026-04-12 (architecture oversight — guardrails admin/debug slice)

- **Audit:** `archive/architecture_review.md` — зафиксирован periodic architecture oversight 2026-04-12: findings snapshot, metrics snapshot, positive patterns, remediation backlog.
- **HTTP/admin:** `app/routers/admin.py` — question-bearing debug/admin endpoints (`/faq/similar`, `/cache/answer-benchmark`, `/profile/query`, `/profile/compare`, `/profile/compare-eval`) теперь проходят через `prepare_ask_request()` / input guardrails перед вызовом query/profiler services.
- **Tests:** `tests/test_api.py` — регрессия на prompt-injection для admin benchmark endpoint и нормализацию вопроса/фильтров для `/profile/query`.

## 2026-04-12 (E28-A — US-8.2: бейдж «Профиль обновлён после переиндексации»)

- **`app/learner_model_service.py`:** в метаданные rehydrate из истории профиля добавлено `history_rehydrated_row_timestamp` (fallback даты для бейджа).
- **`app/ui/learner_profile_panel.py`:** единая отрисовка US-8.2 — `render_us_8_2_reindex_badge`, хелперы даты/текста; бейдж во всех вариантах панели профиля (AI).
- **`app/ui/tutor_mastery_forecast_panel.py`:** `render_learner_profile_migration_badge` для сценария `history_rehydrated` делегирует в `render_us_8_2_reindex_badge` (без дублирования текста).
- **Тесты:** `tests/test_learner_profile_panel.py`, `tests/test_learner_migration_badge.py`.
- **Документация:** `doc/tasklist.md`, `doc/closed_iterations.md`, `doc/user_guide.md`, `doc/user_guide_details.md`.

## 2026-04-12 (E27-A — Backup/restore discoverability, US-10.2)

- **`app/ui/sidebar.py`:** блок backup и восстановления вынесен в верхнеуровневый expander «Перенос прогресса (backup / восстановление)» (до секции «Индекс»); в «Расширенном управлении» остаётся только **Голос** (без вложенной синхронизации).
- **`app/ui/continuity_bridge.py`:** подписи `sync_transfer_*`, `home_sync_transfer_hint_ru`; уточнён текст `expert_controls_sidebar_blurb_ru`.
- **`app/ui/home_hub.py`:** подсказка в «Ещё инструменты» на главной.
- **Тесты:** `tests/test_e11_beginner_copy.py`, `tests/test_e11_expert_controls.py`.
- **Документация:** `doc/user_guide.md`, `doc/tasklist.md`, `doc/closed_iterations.md`.

## 2026-04-12 (E26-A — Flashcards soft-recovery / due tail)

- **`app/user_state.py`:** `defer_due_flashcards_for_recovery` — сдвиг `next_review` для хвоста очереди (как KG SRS recovery).
- **`app/flashcard_service.py`:** `defer_overdue_flashcards_for_recovery`.
- **HTTP:** `POST /flashcards/due/recovery` (`app/routers/flashcards.py`).
- **UI:** `app/ui/flashcards_ui.py` — предупреждение и кнопка при **>20** due в выбранной колоде/тегах.
- **Тесты:** `tests/test_flashcard_service.py`, `tests/test_api.py` (`test_flashcards_due_recovery_endpoint`).
- **Документация:** `doc/api_reference.md`, `doc/user_guide.md`, `doc/tasklist.md`, `doc/closed_iterations.md`.

## 2026-04-12 (perf — Streamlit bootstrap + BM25 warm-up)

- **`app/ui_client.py`:** TTL кэша `_cached_ui_bootstrap` увеличен до **300** с (реже GET `/ui/bootstrap` при rerun).
- **`app/api.py`:** после прогрева `get_base_services` фоновый поток вызывает `warm_bm25_cache_if_configured` (`app/hybrid_retrieval.py`) для режимов **hybrid** / **bm25_only**, чтобы первый вопрос не оплачивал холодную сборку BM25.
- **`doc/user_guide.md`:** опционально — несколько воркеров uvicorn для разнесения тяжёлого CPU и HTTP.

## 2026-04-12 (docs — user guide: Flashcards E16)

- **`doc/user_guide.md`:** краткий раздел Flashcards (preview, ≥5 карточек, итог сессии повторения).
- **`doc/user_guide_details.md`:** § Streamlit — список разделов + подраздел **Flashcards** (создание, повторение, API-заметка).

## 2026-04-12 (E16 — Flashcards MoT №11–12)

- **HTTP:** `POST /flashcards/decks` — минимум **5** карточек в теле запроса (`app/routers/flashcards.py`).
- **UI:** `app/ui/flashcards_ui.py` — предупреждение при сохранении с &lt;5 валидных карточек; итог review-сессии с ближайшим `next_review` среди оценённых; явная ошибка при сбое `POST /flashcards/review` без «тихого» пропуска.
- **Тесты:** `tests/test_flashcard_service.py`, `tests/test_flashcards_ui.py`.
- **Roadmap:** `doc/tasklist.md`, `doc/closed_iterations.md` — **E16** `closed`.
- **Проверки:** `pytest tests/test_flashcards_ui.py tests/test_flashcard_service.py tests/test_api.py -v` → 85 passed.

## 2026-04-12 (docs — вычистка `tasklist` и связок)

- **`doc/tasklist.md`:** сжаты § Now / горизонт / Truth View; убрано дублирование с `closed_iterations.md`; приоритет — E16/TBD.
- **`doc/cjm.md`:** убран внешний путь к арх. плану; ссылка на следующий срез через `tasklist`.
- **`doc/roadmap_governance.md`**, **`AGENTS.md`:** уточнено разделение `tasklist` vs `closed_iterations`.

## 2026-04-12 (E24-B-2 tail — home + сброс + закрытие итерации)

- **UI:** `app/ui/home_hub.py` — `persist_tutor_goal_snapshot_from_session` после onboarding и кнопок входа «Понять тему» / экзамен / ДЗ; «Сбросить цель сессии» вызывает `clear_tutor_goal_and_snapshot()` (`app/ui/session_state.py`: `DELETE` snapshot + очистка `tutor_goal_*` + re-hydrate на следующем заходе).
- **Roadmap:** `doc/tasklist.md`, `doc/closed_iterations.md` — **E24-B-2** `closed`.

## 2026-04-12 (E24-B-2-2 — Streamlit: гидратация цели + persist после CTA)

- **UI:** `app/ui/session_state.py` — `hydrate_tutor_goal_snapshot_once()` (один раз за Streamlit-сессию из `get_learner_goal_snapshot`), `persist_tutor_goal_snapshot_from_session()`, чистая карта `goal_snapshot_context_to_session_patch` для тестов.
- **Точки входа:** `app/ui/main.py` вызывает hydrate после `hydrate_tutor_mastery_from_db`; `app/ui/query_tab.py` после CTA «Учить эту тему 5 минут» сохраняет снимок.
- **Тесты:** `tests/test_e24_goal_ui.py` — маппинг `goal_context` → session patch.
- **Документация:** `doc/api_reference.md` (Streamlit).

## 2026-04-12 (E24-B-2-1 — Learner goal snapshot → `POST /ask`)

- **HTTP:** `app/routers/query.py` перед `prepare_ask_request` вызывает `merge_learner_goal_snapshot_into_ask` из `app/ask_goal_snapshot_merge.py`: при отсутствии `tutor_goal_*` в теле подставляются `subtopic` / `target_level` / `desired_outcome` / `time_budget_min` из сохранённого `goal_context`; явные поля запроса имеют приоритет.
- **Документация:** `doc/api_reference.md` — связка snapshot и `POST /ask`.
- **Проверки:** `pytest tests/test_api.py tests/test_e24_goal_context.py tests/test_user_state.py tests/test_e24_goal_persistence.py -q`.

## 2026-04-12 (E24-B — Learner goal snapshot persistence + HTTP)

- **Persistence:** таблица `learner_goal_snapshot` в `app/user_state.py` (версия `LEARNER_GOAL_SNAPSHOT_SCHEMA_VERSION`), функции `upsert_learner_goal_snapshot`, `get_learner_goal_snapshot`, `clear_learner_goal_snapshot`, `normalize_learner_goal_snapshot_payload` / `learner_goal_snapshot_api_empty`.
- **HTTP:** `app/routers/learner.py` — `GET/PUT/DELETE /learner/goal-snapshot`; `app/api_requests.py` (`LearnerGoalSnapshotPutRequest`), `app/api_models.py` (`LearnerGoalSnapshotOut`, `LearnerGoalContextOut`).
- **Документация:** `doc/api_reference.md` — тег `learner`; `doc/tasklist.md` / `doc/closed_iterations.md` — закрытие E24-B.
- **Проверки:** `pytest tests/test_user_state.py tests/test_e24_goal_persistence.py -q` → 35 passed (локально 2026-04-12).
- **Не в scope:** автозагрузка снимка в `POST /ask` или UI — следующий пакет.

## 2026-04-12 (E24-A — Learner goal contract / Learning Kernel kickoff)

- **E24-A (closed):** узкий контракт цели для короткого tutor loop (Iteration 24): опциональные поля `tutor_goal_subtopic`, `tutor_goal_target_level`, `tutor_goal_desired_outcome`, `tutor_goal_time_budget_min` в `POST /ask` / `QueryOptions`; нормализация в `app/input_validation.py`; `build_learner_goal_context_dict` + `learner_profile["goal_context"]` в `app/tutor_orchestrator.py`; передача из `app/query_service.py` в tutor-ветке.
- **UI:** `app/ui/session_state.py`, `app/ui/tutor_chat.py` (`_tutor_query_options`, строка «Сейчас: …», closure `e24_five_min_closure_combined_ru`), `app/ui/query_tab.py` (seed из «Учить эту тему 5 минут»), хелперы в `app/ui/continuity_bridge.py`.
- **Документация API:** `doc/api_reference.md` — список полей `tutor_goal_*`.
- **Проверки:** `pytest tests/test_e24_goal_context.py tests/test_e24_goal_ui.py tests/test_e11_learning_loop.py tests/test_models.py tests/test_api.py tests/test_tutor_orchestrator.py -q` → 95 passed (локально 2026-04-12).
- **Артефакты конвейера:** `archive/team_artifacts/E24-A/`.

## 2026-04-12 (E15-A - Flashcards deck progress + tag filter)

- **E15-A:** closed Retain slice for flashcards: deck detail now has deck-level progress sourced from `GET /flashcards/decks/{deck_id}/progress`.
- **Review filters:** `/flashcards/due` and `/flashcards/due/count` accept `deck_id` + canonical OR tag filters; review UI loads filtered queues from the backend and resets stale session state when filters change.
- **Verification:** `.\.venv\Scripts\python.exe -m pytest tests\test_flashcards_ui.py tests\test_flashcard_service.py tests\test_api.py -q` -> 81 passed.

## 2026-04-12 (docs — E14-D doc sweep: Flashcards, ADR-009, testing notes)

- **E14-D:** синхронизация `doc/architecture.md` и `doc/conventions_architecture.md` с runtime E12 Flashcards (`app/routers/flashcards.py`, `app/flashcard_service.py`, таблицы `flashcard_decks` / `flashcards` в `app/user_state.py`, Anki через `app/export_utils.py`).
- **ADR-009:** статус `Proposed` → **`Deferred`** — путь «HDBSCAN при reindex + LLM naming» в коде не реализован; фактический каталог тем — lightweight-кластеризация в `app/knowledge_service.py`, решение владельца отложено.
- **`doc/conventions_reference.md` § Тестирование:** зафиксированы `pytest_configure` (отключение reranker / Windows), ограничение покрытия reranker в unit-тестах, различие `patch_retrieval_faq_cache_enabled` vs `patch_faq_cache_enabled`.

## 2026-04-12 (roadmap — E11-R Router Intent Repair closed)

- `doc/tasklist.md`: эпоха **E11** переведена в `closed` (включая **E11-R**); **Now**, **Closed Horizon Notes**, **Truth View** — синхронизированы с exit artifact `eval_results/router_eval_e11_r.json`.
- `doc/closed_iterations.md`: добавлена секция **E11-R: Router Intent Repair** с критериями закрытия и ссылкой на отчёт full router eval.
- `doc/tasklist.md`: закрытые E11/E12/E13 детали свернуты до коротких ссылок на `doc/closed_iterations.md`, чтобы weekly backlog снова оставался коротким.
- `doc/future_roadmap.md`, `doc/cjm.md`, `doc/user_stories.md`, `doc/roadmap_governance.md`: убраны устаревшие формулировки про conditional E11-R; re-entry описан как новый owner-scoped package при свежей регрессии.

## 2026-04-12 (roadmap — E13 home UX tail)

- `doc/tasklist.md`: добавлен закрытый epoch-package **E13 Home Mode Selector / UX Tail** с owner decision, CJM/US, DoD и `Files to inspect first`.
- `doc/closed_iterations.md`, `doc/future_roadmap.md`, `doc/cjm.md`, `doc/user_stories.md`, `doc/user_scenarios.md`, `doc/roadmap_governance.md`, `doc/readme.md`: синхронизирован факт закрытия E13-A и re-entry для deferred `17.1 UX tail`.

## 2026-04-12 (docs — per-US acceptance split)

- `doc/user_stories/`: details-файл разложен на отдельные `us-*.md` — один файл на одну user story; `doc/user_stories_details.md` оставлен лёгким compatibility-индексом.
- `doc/user_stories.md`, `doc/agent_workflow.md`, `doc/readme.md`, `doc/index.md`, `doc/tasklist.md`: ссылки на полные acceptance criteria переведены на `doc/user_stories/`.

## 2026-04-11 (roadmap cleanup — E11/E12 status sync)

- `doc/tasklist.md`: E11 переведён из `active` в `conditional`; E12 свернут до closed exit artifact; удалены устаревшие хвосты про “E11-D next”.
- `doc/future_roadmap.md`, `doc/roadmap_governance.md`, `doc/cjm.md`, `doc/user_stories.md`: синхронизированы формулировки — E11-A/B/C/D/Q/P и E12 закрыты, E11-R остаётся только условным intent-repair tail.
- `doc/user_stories.md` + `doc/user_stories_details.md`: основной файл сокращён до shortlists, индекса и связей; полные INVEST / Given-When-Then acceptance criteria вынесены в details-файл без удаления.
- `doc/closed_iterations.md`: добавлены короткие записи для закрытых E11-P и E11-Q.

## 2026-04-10 (документация — снижение «полотен» для чтения и контекста)

- `doc/conventions.md`: TL;DR и навигация; детали в `conventions_architecture.md`, `conventions_reference.md`.
- `doc/tasklist.md`: таблица активного горизонта сверху; E8.x сведены к ссылке на `closed_iterations.md`; exit criteria и архив **This Week** — `archive/tasklist_historical.md`.
- `doc/vision.md`: блок «стек и границы» в начале; убрано дублирование с conventions/architecture.
- `doc/user_guide.md` + `user_guide_details.md`: быстрый старт отдельно от деталей.
- `.cursor/rules/workflow.mdc`, `conventions.mdc`, `doc/readme.md`, `doc/index.md`, `.cursor/README.md`: навигация на новые файлы.

## 2026-04-09 (E7.3 — gate triage automation and failure routing)

- `scripts/check_tutor_regression_gate.py`: `schema_version` **2**; объект `triage` (`next_action`, `owner_hint`, `rerun_recommended`) через `compute_triage()` для `pass` / `regression_fail` / `infra_fail`; тесты расширены.
- `scripts/smoke_tutor_regression_gate.py`: offline/online gate payload согласован с `triage`; `diagnostic_summary` включает `recommended_next_action`, `recommended_owner_hint`, `rerun_recommended`.
- `.github/workflows/tutor-regression-gate.yml`: diagnostic summary печатает triage-поля из `gate.triage`.
- `doc/observability_slo.md`: таблица и decision tree (Operator quick path, E7.3).
- `doc/tasklist.md`, `doc/future_roadmap.md`: E7.3 закрыт.

## 2026-04-09 (E7.2 — eval artifact retention and triage)

- `scripts/check_tutor_regression_gate.py`: стабильный envelope JSON-отчёта (`schema_version`, `generated_at_utc`, `status`, `exit_code`, `artifact.eval_output_path`, fail-поля), опция `--report-json` для сохранения полного отчёта; покрыто `tests/test_check_tutor_regression_gate.py`.
- `.github/workflows/tutor-regression-gate.yml`: извлечение standalone `tutor-gate-healthy.json` / `tutor-gate-degraded.json` из smoke payload; загрузка bundle `tutor-regression-gate-artifacts` (retention 14 дней); в `GITHUB_STEP_SUMMARY` — блок Artifacts с именами файлов для triage.
- `doc/observability_slo.md`: runbook triage (E7.2) — порядок разбора `regression_fail` vs `infra_fail` по CI-артефактам без полного локального репродуса.
- `doc/tasklist.md`, `doc/future_roadmap.md`: E7.2 закрыт; следующий E7 owner-slice — по планированию.

## 2026-04-09 (E7.1 — tutor gate reliability hardening)

- `scripts/check_tutor_regression_gate.py`: gate-контур различает `pass` / `regression_fail` / `infra_fail` через `status`, `error_kind`, `error_type`, `error_message` и exit codes `0/2/3`.
- `scripts/smoke_tutor_regression_gate.py`: deterministic smoke-path дополнен `diagnostic_summary` для `healthy` / `degraded` сценариев без live LLM/provider зависимости.
- `.github/workflows/tutor-regression-gate.yml`: workflow запускает оба smoke-сценария (`healthy`, `degraded`) и публикует короткий diagnostic summary в job log и `GITHUB_STEP_SUMMARY`.
- `doc/observability_slo.md`: runbook синхронизирован с E7.1 smoke/CI contour и правилами интерпретации `diagnostic_summary`.
- `doc/tasklist.md`, `doc/future_roadmap.md`: E7.1 отмечен как закрытый execution-slice; активный горизонт остаётся E7, следующий owner-slice ещё не зафиксирован.
- Тесты: `tests/test_check_tutor_regression_gate.py`, `tests/test_smoke_tutor_regression_gate.py`.

## 2026-04-09 (E6.5 — Agent B: typed tutor pipeline scalars + UI summary)

- `app/api_models.py` / `app/query_service.py`: в `TutorPayload` и ответ `/ask` — явные поля `orchestration_phase`, `orchestration_decision_source`, `selected_agent`, `should_trigger_microquiz`, `policy_clamped`, `policy_clamp_reasons` (копия из `tutor_orchestration_pipeline` для typed read-path).
- `app/ui/helpers.py`, `app/ui/main.py`: «Контекст тьютора» учитывает typed-поля и показывает агент / micro-quiz при наличии.
- `app/ui/resume_cards.py`: для resume — приоритет typed-полей над вложенным pipeline.
- `app/ui/tutor_mastery_forecast_panel.py`: caption «Последний снимок тьютора» из KV `load_orchestration_state()` (фаза / источник / агент / след. шаг).
- `app/ui/tutor_mastery_forecast_panel.py`: `render_tutor_orchestration_snapshot_expander` — общий expander KV-снимка + опционально `current_concept`.
- `app/ui/main.py` — «Прогресс обучения» и «Knowledge Graph»: тот же expander; на KG дополнительно строка фокуса концепта.
- `app/ui/topics_tab.py` — вкладка «Темы»: тот же expander (с фокусом концепта).
- `app/ui/query_tab.py` — «Быстрый ответ»: тот же expander (`key_prefix=query_tab`).
- Тесты: `tests/test_query_service.py`, `tests/test_ui_helpers.py`, `tests/test_tutor_mastery_forecast_panel.py`.

## 2026-04-08 (E6.2 follow-up — Agent B: query_service logging + resume orch hints)

- `app/query_service.py`: при сбоях merge adaptive daily plan, FAQ `find_similar_questions` и `persist_orchestration_state` — `log_event(..., WARNING, ...)` вместо тихого `except`; ответ пользователю не ломается.
- `app/ui/resume_cards.py`: в `recommended_next` из последнего ответа тьютора — `orchestration_phase`, `orchestration_decision_source` из `tutor_orchestration_pipeline`; caption «Оркестрация (последний ответ)».
- Тесты: `tests/test_query_service.py` (регрессия).

## 2026-04-08 (E6.2 — Agent B: tutor payload + UI exposure)

- `app/query_service.py`: `_build_tutor_payload` пробрасывает `tutor_orchestration_pipeline` и `tutor_pipeline` из `ctx.metadata` / `ctx.trace`.
- `app/tutor_learner_contract.py`: `build_orchestration_state_dict` опционально вкладывает снимок pipeline в persisted JSON (KV).
- `app/api_models.py`: поля `TutorPayload.tutor_orchestration_pipeline`, `tutor_pipeline`.
- `app/ui/helpers.py`, `app/ui/main.py`: summary + expander «Шаги оркестрации».
- Тесты: `tests/test_query_service.py`, `tests/test_ui_helpers.py`, `tests/test_tutor_learner_contract.py`.

## 2026-04-08 (E6.1 — Agent A: personalization policy + orchestrator clamp)

- `app/tutor_personalization_policy.py`: `attach_personalization_policy_to_learner_profile`, `apply_orchestrator_policy_clamp` (due review / `quiz_emphasis`, override MotivationCoach → MicroQuizGenerator).
- `app/pipeline_steps.py`: enrich профиль перед LLM, clamp после JSON; `trace["orchestrator_policy_clamp"]`; `apply_pedagogical_orchestrator_to_metadata(..., policy_clamp_meta=...)`.
- `app/tutor_orchestrator.py`: опциональный `policy_clamp_meta` в merge pipeline-контракта.
- `app/orchestrator_router.py`: тот же attach политики в `_resolve_learner_profile`.
- `doc/conventions.md`, `doc/tasklist.md`: E6.1, Truth View.
- `tests/test_tutor_personalization_policy.py`.

## 2026-04-08 (E6.0 — tutor orchestration contract)

- `app/tutor_pipeline_contract.py`: контракт `metadata["tutor_orchestration_pipeline"]` (schema_version, phase, decision_source, selected_agent, should_trigger_microquiz) и `trace["tutor_pipeline"]`.
- `app/tutor_orchestrator.py`: `make_rule_fallback_orchestrator_decision` (ConceptExplainer, без micro-quiz); JSON/LLM-сбои и исключения шага → rule fallback; `apply_pedagogical_orchestrator_to_metadata` заполняет pipeline-контракт.
- `app/pipeline_steps.py`: запись шагов tutor-пайплайна в trace + merge контракта; ветки disabled / no profile.
- `app/query_service.py`: инициализация `trace["tutor_pipeline"]` перед `build_tutor_pipeline`.
- `app/orchestrator_router.py`: уточнён статус относительно продового tutor-пайплайна (E6.0).
- `doc/conventions.md`, `doc/tasklist.md`, `doc/future_roadmap.md`, `doc/closed_iterations.md`: § E6, Truth View, Now/Next, owner decision.
- `.cursor/rules/conventions.mdc`: ссылка на tutor orchestration contract.
- Тесты: `tests/test_pipeline_steps.py`, `tests/test_tutor_orchestrator.py`.

## 2026-04-08 (E5.8 — learner lineage sync on index activation)

- `app/user_state.py`: `run_learner_state_lineage_sync()` — eager вызов `sync_current_learner_state_lineage` после смены активной generation.
- `app/index_lifecycle.py`: `apply_index_activation_hooks` всегда выполняет sync и возвращает `learner_state_lineage` в результате.
- `doc/index_lifecycle.md`: строка в таблице reindex + связанные модули.
- `tests/test_index_backup.py`: `test_apply_index_activation_hooks_syncs_learner_lineage`.
- `doc/tasklist.md`: E5.8 в E5 horizon / This Week.

## 2026-04-08 (E5.7 — learner migration smoke gate in CI)

- `.github/workflows/learner-migration-smoke-gate.yml`: новый CI merge-gate workflow (pytest + `scripts/smoke_learner_migration_gate.py --profile strict`) на `pull_request` и `push` в `main/master`.
- `doc/observability_slo.md`: добавлены learner migration gate recipes (local/strict/smoke healthy/degraded) и ссылка на CI workflow.
- `doc/tasklist.md`: E5.7 отмечен как выполненный.

## 2026-04-08 (E5.6 — smoke learner migration gate command)

- `scripts/smoke_learner_migration_gate.py`: smoke workflow, который генерирует learner profile history и сразу запускает `check_learner_migration_gate` (auto-expand rows под профиль).
- `tests/test_smoke_learner_migration_gate.py`: покрытие smoke history generation, main JSON-output и strict auto-expand path.
- `doc/tasklist.md`: E5.6 отмечен как выполненный.

## 2026-04-08 (E5.5 — ready learner migration gate command)

- `scripts/check_learner_migration_gate.py`: готовая quality-gate команда для learner migration (`local` / `strict`, `exit code 2` при провале).
- `tests/test_check_learner_migration_gate.py`: покрытие threshold presets, pass/fail сценариев и `run_gate`.
- `doc/tasklist.md`: E5.5 отмечен в E5 horizon / This Week.

## 2026-04-08 (E5.4 — learner migration SLO alert)

- `app/config.py`: новый порог `slo_max_learner_rehydrated_rate`.
- `app/metrics.py`: `evaluate_slo_alerts` учитывает learner migration rollup (`get_learner_profile_migration_metrics`) и генерирует alert по метрике `learner_rehydrated_rate`.
- `tests/test_metrics.py`: `test_evaluate_slo_alerts_includes_learner_rehydrated_rate_alert`.
- `tests/test_config.py`: проверка типа нового SLO поля.
- `doc/tasklist.md`: E5.4 добавлен в E5 horizon / This Week.

## 2026-04-08 (E5.3 — learner migration rollups in metrics)

- `app/learner_model_service.py`: добавлен `get_learner_profile_migration_metrics` (windowed rollups: rehydrated/index_changed rates, generations).
- `app/routers/metrics.py`: endpoint `GET /metrics/learner` для операционной диагностики learner migration.
- `app/api_services.py`: экспорт `get_learner_profile_migration_metrics`.
- `tests/test_learner_model_service.py`: `test_get_learner_profile_migration_metrics_rollup`.
- `tests/test_api.py`: `test_metrics_learner_endpoint`.
- `doc/tasklist.md`: E5.3 отмечен в backlog/This Week.

## 2026-04-08 (E5.2 — learner profile history diagnostics API)

- `app/routers/knowledge.py`: добавлен endpoint `GET /kb/learner/profile-history` (current `index_context` / `state_migration` + versioned history).
- `app/api_services.py`: экспортированы `get_personalized_learner_profile`, `get_learner_profile_history` для роутера knowledge.
- `tests/test_api.py`: `test_learner_profile_history_endpoint`.
- `doc/tasklist.md`: E5.2 отмечен как выполненный.

## 2026-04-08 (E5.1 — migration-safe learner state rehydrate)

- `app/learner_model_service.py`: history snapshots теперь хранят `mastery_vector`; добавлен fallback `_rehydrate_mastery_from_profile_history` в `get_personalized_learner_profile` для случая, когда текущий mastery после смены индекса полностью orphaned.
- `tests/test_learner_model_service.py`: `test_profile_rehydrates_mastery_from_history_when_current_is_orphaned`.
- `doc/tasklist.md`: E5.1 отмечен как выполненный в E5 Learner Horizon.

## 2026-04-08 (E5.0 — versioned learner profile history)

- `app/learner_model_service.py`: добавлен KV-ключ `personalized_learner_model_history_json` и история snapshots профиля (`get_learner_profile_history`), обновляемая при `save_learner_profile`.
- `tests/test_learner_model_service.py`: `test_save_learner_profile_appends_versioned_history`.
- `doc/tasklist.md`: E5.0 отмечен как выполненный под E5 Learner Horizon.

## 2026-04-07 (Owner decision — E4 sprint closure, horizon -> E5)

- `doc/tasklist.md`: `E4 Graph horizon` переведён в `closed` по sprint exit criteria; добавлен `E5 Learner horizon` как следующий active horizon.
- `doc/future_roadmap.md`: зафиксирован переход активного горизонта на `E5` после прохождения E4 quality gates и sprint closure.
- `doc/closed_iterations.md`: добавлена историческая запись о закрытии E4 как delivery-sprint и переходе к E5.

## 2026-04-07 (E4.15 — compare presets + multi-query smoke runbook)

- `scripts/graph_expansion_compare.py`: added ready-to-run `--preset` scenarios (`overall-local`, `overall-strict`, `synthesis-strict`, `learning-plan-local` and related variants) so targeted gate can be launched without rebuilding CLI flags by hand.
- `scripts/smoke_graph_expansion_gate.py`: smoke traffic now supports multiple `query_type` values via `--query-types`; default smoke window covers `synthesis,learning_plan`.
- `scripts/smoke_graph_expansion_compare.py`: supports the same presets and multi-query smoke window, preserving compare-gate JSON contract.
- `.github/workflows/graph-expansion-smoke-gate.yml`: CI now runs compare/smoke-compare tests and an additional targeted merge-gate via `scripts/smoke_graph_expansion_compare.py --preset synthesis-strict --enforce-gate`.
- `doc/observability_slo.md`: added runbook section with ready commands for overall, targeted and smoke compare-gate scenarios.
- `tests/test_graph_expansion_compare.py`, `tests/test_smoke_graph_expansion_compare.py`, `tests/test_smoke_graph_expansion_gate.py`: coverage for presets, multi-query smoke traffic and runbook-facing CLI behavior.

## 2026-04-07 (E4.14 — query-type-specific compare gate profiles)

- `scripts/graph_expansion_compare.py`: added `--gate-query-type-profile query_type=local|strict`; targeted `compare_gate.query_type_checks` now include their own `thresholds`, so per-query-type budgets can differ from the global compare profile.
- `scripts/smoke_graph_expansion_compare.py`: smoke off/on runner supports the same `--gate-query-type-profile` passthrough and reports `compare_gate_query_type_profiles`.
- `tests/test_graph_expansion_compare.py`, `tests/test_smoke_graph_expansion_compare.py`: coverage for stricter per-query-type profile and CLI/profile passthrough.

## 2026-04-07 (E4.13 — query-type-aware graph compare gate)

- `scripts/graph_expansion_compare.py`: compare-gate расширен параметром `--gate-query-type`; в JSON-отчёте `compare_gate` теперь содержит `query_type_checks` и список `gate_query_types`.
- `scripts/smoke_graph_expansion_compare.py`: smoke off/on runner поддерживает тот же `--gate-query-type`, чтобы targeted gate использовался без дополнительной обвязки.
- `tests/test_graph_expansion_compare.py`, `tests/test_smoke_graph_expansion_compare.py`: покрытие targeted query-type gate и CLI passthrough.

## 2026-04-07 (E4.12 — query-type-aware graph compare diagnostics)

- `scripts/graph_expansion_compare.py`: compare-report расширен отдельными блоками `query_type_compare` и `graph_expansion_counter_compare`, чтобы baseline/candidate и smoke off/on можно было разбирать по каждому `query_type`, `skip_reasons` и `error_types`.
- `tests/test_graph_expansion_compare.py`, `tests/test_smoke_graph_expansion_compare.py`: покрытие query-type-aware compare path и smoke JSON-формата.

## 2026-04-07 (E4.11 — segmented graph expansion diagnostics)

- `app/metrics.py`: `graph_expansion` summary теперь публикует breakdown по `query_type` (`by_query_type`) и диагностические счётчики `skip_reasons` / `error_types`; те же разрезы доступны и в `summarize_metrics_store`.
- `app/graph_retrieval.py`: error-trace graph expansion теперь сохраняет `error_type`, чтобы метрики и benchmark различали классы отказов, а не только текст ошибки.
- `scripts/graph_expansion_benchmark.py`, `scripts/graph_expansion_compare.py`: benchmark нормализует сегментированные breakdown из JSONL и `GET /metrics`, compare-report дополнен delta по `skipped_rate`.
- `tests/test_metrics.py`, `tests/test_graph_expansion_benchmark.py`, `tests/test_graph_expansion_compare.py`: покрытие breakdown по `query_type`, skip/error причинам и compare delta; целевой pytest green.

## 2026-04-06 (E4.10 — delta compare gate for graph off/on)

- `scripts/graph_expansion_compare.py`: compare-report теперь умеет считать `compare_gate` и валидировать правило «допустимая latency-регрессия vs прирост applied_rate»; добавлены профили `local` / `strict`, `--enforce-gate` и non-zero exit code при провале.
- `scripts/smoke_graph_expansion_compare.py`: off/on smoke runner теперь печатает `compare_gate`, поддерживает те же пороги и умеет работать как готовый smoke delta-gate; `--json-out` больше не загрязняется startup/shutdown логами.
- `tests/test_graph_expansion_compare.py`, `tests/test_smoke_graph_expansion_compare.py`: покрытие оправданной и не оправданной latency-регрессии, а также smoke enforce path.

## 2026-04-06 (E4.9 — graph off/on smoke compare runner)

- `scripts/smoke_graph_expansion_gate.py`: новый режим `--graph-mode off|on` для детерминированной генерации baseline/candidate traces.
- `scripts/smoke_graph_expansion_compare.py`: единый smoke-runner, который сам создаёт `graph_off` и `graph_on` JSONL, затем печатает compare-report по delta latency/quality.
- `tests/test_smoke_graph_expansion_gate.py`, `tests/test_smoke_graph_expansion_compare.py`: покрытие off-mode и off/on compare runner.

## 2026-04-06 (E4.8 — graph compare report + provenance UX)

- `scripts/graph_expansion_compare.py`: compare-report для baseline/candidate окон или прогонов; показывает delta по `p95_total_answer_ms`, `p95_graph_expansion_ms`, `applied_rate`, `error_rate`, `avg_extra_chunks_when_applied`.
- `app/graph_retrieval.py`: trace `graph_expansion` расширен `seed_concept_ids_sample`, `concept_route_sample`, `added_doc_reason_sample`.
- `app/ui/debug_panel.py`: expander graph expansion показывает seed/added doc chips и краткие provenance-линии «почему были добавлены чанки».
- `tests/test_graph_expansion_compare.py`, `tests/test_graph_retrieval.py`, `tests/test_debug_panel.py`: покрытие compare-report и richer provenance UX.

## 2026-04-06 (E4.7 — graph expansion smoke gate in CI)

- `.github/workflows/graph-expansion-smoke-gate.yml`: новый GitHub Actions workflow для `pull_request` и `push` в `main/master`; ставит зависимости, прогоняет целевые pytest-файлы и `scripts/smoke_graph_expansion_gate.py --profile strict`.
- CI публикует `logs/graph_expansion_smoke_ci.jsonl` как artifact для разбора провалов merge-gate.

## 2026-04-06 (E4.6 — graph expansion smoke gate command)

- `scripts/check_graph_expansion_gate.py`: готовая команда для quality gate с профилями `local` / `strict` и рекомендуемыми порогами.
- `scripts/smoke_graph_expansion_gate.py`: детерминированный smoke workflow, который генерирует `graph_expansion` request-события через `/ask` и сразу запускает gate по изолированному JSONL.
- `scripts/graph_expansion_benchmark.py`: хелпер `build_report_from_jsonl_path` для переиспользования отчёта в gate wrappers.
- `tests/test_check_graph_expansion_gate.py`, `tests/test_smoke_graph_expansion_gate.py`: покрытие wrapper-команды и smoke path.

## 2026-04-06 (E4.5 — graph expansion quality gate)

- `scripts/graph_expansion_benchmark.py`: quality gate по порогам (`--min-events`, `--max-p95-ms`, `--min-applied-rate`, `--max-error-rate`, `--min-avg-extra-chunks`), JSON-отчёт с `quality_gate`, exit code `2` при провале.
- `app/metrics.py`: derived rates `applied_rate`, `skipped_rate`, `error_rate`, `unknown_outcome_rate` в публичном `graph_expansion` summary.
- `tests/test_graph_expansion_benchmark.py`, `tests/test_metrics.py`: покрытие quality gate и derived rates.

## 2026-04-06 (E4.4 — graph expansion benchmark CLI)

- `app/metrics.py`: `aggregate_graph_expansion_from_request_events`, `_new_graph_expansion_accumulator`; `summarize_metrics_store` использует ту же агрегацию.
- `scripts/graph_expansion_benchmark.py`: отчёт по JSONL или `--metrics-url` (снимок `graph_expansion` с API).
- `tests/test_metrics.py`: `test_aggregate_graph_expansion_from_request_events`.

## 2026-04-06 (E4.3 — graph expansion в debug UI)

- `app/ui/debug_panel.py`: expander «Расширение графа (retrieval)» при `pipeline_trace.graph_expansion`; хелпер `graph_expansion_rows_for_ui`.
- `tests/test_debug_panel.py`.

## 2026-04-06 (E4.2 — graph expansion metrics)

- `app/metrics.py`: `compact_graph_expansion_for_metrics`, агрегаты в `get_metrics()` / `summarize_metrics_store` (поле `graph_expansion`); опциональный ключ `graph_expansion` в JSONL request-событиях.
- `tests/test_metrics.py`: `test_graph_expansion_metrics_latency_and_quality`.

## 2026-04-06 (E4.1 — graph expansion observability)

- `app/graph_retrieval.py`: trace `concept_ids_sample` (до 32 id) из `expand_doc_ids_via_graph`; `graph_expansion_ms` для всех веток `GraphExpansionPostprocessor`.
- `tests/fixtures/graph_eval_baseline.json` schema **v3**.

## 2026-04-06 (E4.0 — multi-hop graph expand)

- `app/graph_retrieval.py`: волны обхода `prerequisites` / `related_concepts` (`_expand_concepts_multi_hop`); `expand_doc_ids_via_graph(..., max_hops=...)`; trace `max_hops`, `hops_applied`.
- `app/config.py`: `graph_expand_max_hops` (env `GRAPH_EXPAND_MAX_HOPS`, по умолчанию 3).
- `tests/fixtures/graph_eval_baseline.json` schema **v2**, кейс цепочки T1→T2→T3; `tests/test_graph_retrieval.py`, `tests/test_graph_eval_baseline.py`.
- `doc/tasklist.md` (Truth View E4 **partial**), `doc/conventions.md`.

## 2026-04-06 (итерации 19 platform tail, 18 Core tail embed, tail sweep)

- **19 platform tail:** `app/session_store.py` v2 (`session_metadata`, bounded history, `get_record` / `patch_metadata`); `app/config.py` — `session_history_max_messages`; `app/query_service.py` — `debug.session_history`; `app/routers/query.py` — не пишем FAQ при `session_id`; `app/routers/sessions.py` — GET 404, PATCH metadata; `ask.py` — `--session-id`, `--new-session`, `--query-mode` (+ `getattr` для моков CLI).
- **18 Core tail:** `embed_request_timeout`, `embed_connect_timeout_sec` в `Settings`; `app/provider.get_embed_model` — httpx + retries; тесты `tests/test_provider.py`.
- **Документация / governance:** операционный tail sweep и parking «What Changed» / synthesis archive — `doc/tail_sweep.md`, § Parking lot в `doc/tasklist.md`; `doc/future_roadmap.md`, `doc/closed_iterations.md`.
- **Тесты:** `tests/test_multi_turn.py` — изолированный `session_store` через `importlib.import_module("app.session_store")`; правка alias gpt-5-mini в `test_provider.py`.

## 2026-04-05 (итерация 17 Core MVP — пробелы DoD + 16 tail)

- `app/ingestion.py`: `page_range` из `page_label` (PDF), агрегат для summary-документов; строка `Pages:` в contextualized chunks.
- `tests/fixtures/graph_eval_baseline.json`, `tests/test_graph_eval_baseline.py`: версионируемый baseline для `expand_doc_ids_via_graph`.
- `tests/test_doc_sync_gate.py`: лёгкий gate для `doc/tasklist.md`, `doc/vision.md`, `architecture.md`, graph-eval фикстуры.
- Streamlit `app/ui/sidebar.py`: expander «Актуальность индекса (freshness)» (`index_version`, `generation_id`, активация реестра).
- `doc/architecture.md`: раздел «Зависимости delivery-итераций»; `doc/tasklist.md`: статусы 16/17, чеклисты.

## 2026-04-05 (синхронизация Live-документации с кодом)

- Единая дата актуализации **2026-04-05** в `vision.md`, `index.md`, `architecture.md`, `technical_specification.md`, `api_reference.md`, `user_guide.md`, `user_scenarios.md`, `personalized_learner_model.md`, `observability_slo.md`.
- Explain/content: зафиксирована поддержка `.docx` (как в `app/explain_service.py`); убрано устаревшее ограничение в `technical_specification.md`; обновлены `api_reference.md`, `user_guide.md`, `architecture.md`.
- `architecture.md`: каталог `data/graph_generations/`, модули `knowledge_graph_bundle.py` / `graph_generation_paths.py`; mermaid-схема зависимостей `16 tail → 17 Core MVP → 17 Core Extension → 18 Core → 19 platform tail → E4`.
- `technical_specification.md`: каталог `data/graph_generations/` в списке хранилищ.
- `readme.md`: в таблицу «Карта файлов» добавлен `index_lifecycle.md`.

## 2026-04-05 (документация — roadmap в `tasklist.md`)

- `doc/tasklist.md`: переразложен в weekly execution backlog; первые секции теперь дают `Now / Next / Deferred / Truth View / Exit Criteria`, чтобы уменьшить когнитивную нагрузку daily usage.
- Добавлены `doc/roadmap_governance.md` и `doc/future_roadmap.md`: governance и дальний horizon вынесены из основного backlog, чтобы не смешивать исполнение, policy и стратегию в одном файле.
- `doc/readme.md`, `doc/index.md`: обновлена навигация по новым roadmap-документам.
- `doc/tasklist.md`: сокращён до рабочего roadmap; убраны исторические дубли, явно разведены закрытая foundation-часть итерации 16 и открытые хвосты (`FAQ Chroma`, `Freshness UI`), зафиксированы merge-gate'ы для `17 Core MVP` и `17 Core Extension`.
- Согласованы **эпохи E4–E7** (срезы `20.0`–`23.x`), **итерации поставки 24–26** и исторические **T1–T25 / Batch A–F**; добавлены словарь нумерации, обзорная карта эпох в узкой колонке, актуализация статусов на 2026-04-05.
- `doc/readme.md`: навигация к `tasklist.md` как к единому плану работ и эпох.

## 2026-04-05 (итерация 16 tail — explain/content parity)

- `app/explain_service.py`: поддержка `.docx`, улучшенное чтение HTML; LLM-fallback при коротком извлечённом тексте; зависимость `python-docx`.
- Streamlit: `TEXT_PREVIEW_EXTENSIONS` — `.pdf`, `.docx` для превью источников и вкладки explain.
- Тесты: расширены `tests/test_explain_service.py`, `tests/test_ui_helpers.py`.

## 2026-04-05 (итерация 16 tail — PropertyGraph bundle / ADR-020 MVP)

- Концепт-граф по generation: `app/graph_generation_paths.py`, `app/knowledge_graph_bundle.py`; payload в `kg.sqlite`, артефакт LlamaIndex `property_graph_store.json`; чтение через `get_active_knowledge_graph()`; promote staging → `by_generation/<generation_id>/` в `activate_staging_index`; инвалидация кэша экземпляра в `clear_retrieval_cache`.
- Ingestion: `write_staging_knowledge_graph_bundle` / `write_generation_knowledge_graph_bundle`; backup включает `data/graph_generations/`.
- Тесты: `tests/test_property_graph_generation.py`.

## 2026-04-05 (итерация 16 tail — backup / lifecycle)

- Резервное копирование индексных артефактов: `app/index_backup.py`, CLI `scripts/backup_index.py` (create/restore ZIP с `manifest.json`).
- Политика reindex/reset и производных файлов: `doc/index_lifecycle.md`; хуки после активации индекса — `app/index_lifecycle.py`; опциональная очистка `faq_memory.jsonl` — `Settings.clear_faq_on_index_activation` / `CLEAR_FAQ_ON_INDEX_ACTIVATION`.
- Упрощён импорт `app/faq_memory` (lazy `get_base_services` в `_get_embed_model`).
- Тесты: `tests/test_index_backup.py`; smoke-check включает этот файл.

## 2026-03-31 (итерации 19.3–19.5 — tutor contract)

- **19.3:** `app/tutor_cycle.py` — `tutor.tutor_cycle` в ответе (`phase`, `default_next_step`, quiz/review state); `POST /quiz/evaluate` → `diagnostic_feedback_status`; тесты `tests/test_tutor_cycle.py`; кейс `tutor_16` в `eval_data/tutor_regression.json`.
- **19.4:** `app/tutor_learner_contract.py` — typed `orchestration_state` + KV persistence; `tutor.socratic`; homework ladder `next_homework_level`; тесты `tests/test_tutor_learner_contract.py`.
- **19.5:** `app/tutor_personalization_policy.py` + `tutor_cycle.personalization_policy`; `scripts/check_tutor_regression_gate.py` (baseline через `EVAL_TUTOR_BASELINE_JSON`); обновлены `user_guide.md`, `vision.md`.
- **Закрепление DoD:** `eval_data/tutor_regression_baseline.json` (summary для merge-gate); зафиксированы прогон pytest (tutor/persona/регрессии) и gate с `EVAL_TUTOR_BASELINE_JSON=eval_data/tutor_regression_baseline.json` в `doc/tasklist.md`.

## 2026-03-31 (аудит doc ↔ код)

- Проверено соответствие `app/routers/*` и `doc/api_reference.md` — расхождений по перечисленным маршрутам не найдено.
- В `conventions.md` убрана устаревшая таблица endpoints; актуальный каталог — `api_reference.md` и `/docs`. Исправлено описание ключевых документов: продукт (`vision.md`) vs архитектура (`architecture.md`).
- Уточнены каналы доступа в `architecture.md`, `technical_specification.md`, `user_guide.md`: CLI вызывает `app.query_service` напрямую; Telegram использует `app.api_services` (как HTTP-роутеры), без обходного HTTP.

## 2026-03-31

- Критически пересинхронизирована живая документация в `doc/` с текущим кодом проекта.
- Исправлены архитектурные расхождения по каналам доступа: Streamlit работает через HTTP API; CLI вызывает `query_service` напрямую; Telegram использует `api_services` без HTTP.
- Обновлены `architecture.md`, `technical_specification.md`, `api_reference.md`, `user_guide.md`, `user_scenarios.md`, `vision.md`.
- Уточнены reference-документы `observability_slo.md` и `personalized_learner_model.md`.
- В навигационных файлах `readme.md` и `index.md` усилено разделение между `Live`, `Reference`, `Roadmap`, `ADR` и historical/archive-документами.

## 2026-04-20 — epoch-agent-workflow-split

Split `doc/agent_workflow.md` (1228 строк, `full_read: forbidden`)
на 5 topic-файлов + slim index:
- `agent_workflow_rules.md` — Token Budget & Retry Safety v1
- `agent_workflow_cycle.md` — base cycle, parallelism, A/B/C split
- `agent_workflow_templates.md` — Planning / Verify / Contract / Task templates
- `agent_workflow_arch_review.md` — 5-phase architecture review
- `agent_workflow_test_bundles.md` — standard bundles + low-budget fallback

Все split-файлы ≤ 500 строк, `full_read: allowed`. Slim index сохраняет
inbound-ссылки без breaking change. `scripts/sync_architecture_review_prompt.py`
перенастроен на `agent_workflow_arch_review.md`. Исправлен баг `re.subn` с
backslash-in-replacement. Обновлены hard refs (AGENTS.md, CLAUDE.md,
.cursor/rules/workflow.mdc) и soft refs (team_workflow, doc index, checklist).

Contract: `doc/tasklist.md § epoch-agent-workflow-split`.

## epoch-answer-quality-eval — Answer quality eval gate for First Answer (2026-04-20)

- Added a CI-visible `/ask` answer-quality eval path with golden QA coverage for ordinary and tutor responses.
- Kept `expected_sources` on stable public `AskSource` fields and preserved mock/no-key structural mode for local/CI checks.
- Fixed checked-in thresholds and baseline for `source_precision_at_3`, groundedness, latency p95, and tutor coherence.
- Strengthened the CI gate report so failures include component, metric, threshold/baseline context, and failed case details.

## epoch-micro-quiz-feedback-tail — Micro-quiz submit immediately returns status, explanation, and next CTA. (2026-04-20)

- Submit result appears in <2 seconds.
- Status is one of correct/partial/incorrect.
- Explanation is short and user-facing.
- Next CTA routes to retry, continue tutor, review, or progress.
- epoch-micro-quiz-feedback-tail (closed, 2026-04-20):
  - sp1: stable feedback block (status/explanation/CTA) in quiz_panel.py + scoped_quiz.py.
  - sp2: test contract locked — 22 tests green (status normalization, explanation sanitization, CTA determinism, partial branch isolation).
## 2026-04-22 — workflow launcher hardening

- Added `scripts/run_start_workflow.ps1` as the stable entrypoint for AI-agent workflow execution via the project `.venv`.
- Updated `doc/team_workflow/start_workflow.md` and `doc/team_workflow/run_start_workflow_prompt.md` to route agents through the PowerShell launcher instead of ad-hoc Python command assembly.
- Hardened `scripts/start_workflow.py` to propagate the active interpreter with `sys.executable`, so delegated workflow scripts stay inside the same `.venv`.
- Extended contract parsing in `scripts/prompt_utils.py` and `scripts/generate_next_prompt.py` to support the current `doc/tasklist.md` bullet formats, including backtick keys and same-level bullet values.

## Reopened: epoch-control-plane-v3-core (2026-04-28)

- Reason: admin reopen: batch last-3-days window 2026-04-26..2026-04-28 — operator-confirmed
- Affected US: —
- Action: status closed → ready; closed_iterations Step C.2 applied
- CJM: `closed:` token for package not found in §8 generated table (N/A or alias-only rows).

## Reopened: epoch-demo (2026-04-28)

- Reason: admin reopen: batch last-3-days window 2026-04-26..2026-04-28 — operator-confirmed
- Affected US: —
- Action: status closed → ready; closed_iterations Step C.2 applied
- CJM: `closed:` token for package not found in §8 generated table (N/A or alias-only rows).

## Reopened: epoch-e30-a1-cockpit-scaffold (2026-04-28)

- Reason: admin reopen: batch last-3-days window 2026-04-26..2026-04-28 — operator-confirmed
- Affected US: US-17.2
- Action: status closed → ready; closed_iterations Step C.2 applied
- CJM: `closed:` token for package not found in §8 generated table (N/A or alias-only rows).

## Reopened: epoch-e30-a2-cockpit-rotator (2026-04-28)

- Reason: admin reopen: batch last-3-days window 2026-04-26..2026-04-28 — operator-confirmed
- Affected US: US-17.4
- Action: status closed → ready; closed_iterations Step C.2 applied
- CJM: `closed:` token for package not found in §8 generated table (N/A or alias-only rows).

## Reopened: epoch-e30-b1-graduation-overlay (2026-04-28)

- Reason: admin reopen: batch last-3-days window 2026-04-26..2026-04-28 — operator-confirmed
- Affected US: US-17.5
- Action: status closed → ready; closed_iterations Step C.2 applied
- CJM: `closed:` token for package not found in §8 generated table (N/A or alias-only rows).

## Reopened: epoch-e30-b2-daily-briefing (2026-04-28)

- Reason: admin reopen: batch last-3-days window 2026-04-26..2026-04-28 — operator-confirmed
- Affected US: US-17.6
- Action: status closed → ready; closed_iterations Step C.2 applied
- CJM: `closed:` token for package not found in §8 generated table (N/A or alias-only rows).

## Reopened: epoch-e30-c1-diagnostic (2026-04-28)

- Reason: admin reopen: batch last-3-days window 2026-04-26..2026-04-28 — operator-confirmed
- Affected US: US-17.1
- Action: status closed → ready; closed_iterations Step C.2 applied
- CJM: `closed:` token for package not found in §8 generated table (N/A or alias-only rows).

## Reopened: epoch-e30-c2-pace-engine (2026-04-28)

- Reason: admin reopen: batch last-3-days window 2026-04-26..2026-04-28 — operator-confirmed
- Affected US: US-17.3
- Action: status closed → ready; closed_iterations Step C.2 applied
- CJM: `closed:` token for package not found in §8 generated table (N/A or alias-only rows).

## Reopened: epoch-e30-d1-smart-resume (2026-04-28)

- Reason: admin reopen: batch last-3-days window 2026-04-26..2026-04-28 — operator-confirmed
- Affected US: US-17.8
- Action: status closed → ready; closed_iterations Step C.2 applied
- CJM: `closed:` token for package not found in §8 generated table (N/A or alias-only rows).

## Reopened: epoch-e30-d2-focus-mode (2026-04-28)

- Reason: admin reopen: batch last-3-days window 2026-04-26..2026-04-28 — operator-confirmed
- Affected US: US-17.7
- Action: status closed → ready; closed_iterations Step C.2 applied
- CJM: `closed:` token for package not found in §8 generated table (N/A or alias-only rows).

## Reopened: epoch-e30-e1-course-graduation (2026-04-28)

- Reason: admin reopen: batch last-3-days window 2026-04-26..2026-04-28 — operator-confirmed
- Affected US: US-17.9
- Action: status closed → ready; closed_iterations Step C.2 applied
- CJM: `closed:` token for package not found in §8 generated table (N/A or alias-only rows).

## Reopened: epoch-e30-idea-1-daily-runway (2026-04-28)

- Reason: admin reopen: batch last-3-days window 2026-04-26..2026-04-28 — operator-confirmed
- Affected US: US-17.10
- Action: status closed → ready; closed_iterations Step C.2 applied
- CJM: `closed:` token for package not found in §8 generated table (N/A or alias-only rows).

## Reopened: epoch-e30-idea-2-retrieval-gates (2026-04-28)

- Reason: admin reopen: batch last-3-days window 2026-04-26..2026-04-28 — operator-confirmed
- Affected US: US-17.11
- Action: status closed → ready; closed_iterations Step C.2 applied
- CJM: `closed:` token for package not found in §8 generated table (N/A or alias-only rows).
## 2026-05-01 (LLM cost log location)

- Runtime LLM cost logs now default to `logs/cost_logs/` via `Settings.llm_cost_log_dir` / `LLM_COST_LOG_DIR`.
- `doc/cost_logs/README.md` now documents the format and explains why mutable daily JSONL logs do not belong under `doc/`.
- Updated cost-log summary/bottleneck scripts, focused tests, and observability path docs.

## Reopened: epoch-home-mode-preview-drawer (2026-05-01)

- **Reason:** audit DoD FAIL — Playwright smoke `tests/e2e/home_mode_selection.spec.ts` (`@smoke secondary tools expander`): locator «История вопросов» not visible within timeout.
- **Affected US:** US-14.2
- **Action:** `doc/backlog_registry.yaml` status `closed` → `ready`; `re_entry_condition` set; `doc/user_stories_index.json` + `doc/user_stories/us-14.2.md` — `status` → `open`, `covered_by` cleared; `doc/cjm.md` MoT row marked reopened; `doc/closed_iterations.md` inline REOPENED note.

## Reopened: epoch-home-mode-preview-drawer (2026-05-02)

- **Reason:** после исправления UI/conтракта (`app/ui/fragments.py` — вкладка «История» без `@st.fragment`; `app/ui/main.py` — `e2e_view=...` применяется перед selectbox) smoke `home_mode_selection` зелёный; пакет снова **ready** для формального закрытия в конвейере.
- **Product delta:** стабильный рендер панели «История вопросов» при deep-link `?e2e_view=history`.
- **Affected US:** US-14.2 → `open`, `covered_by` cleared в индексе и frontmatter.
- **Action:** повторный Step C (registry / CI блок / US / CJM / changelog / lint sync).

## 2026-05-03 (план: Cursor SDK trigger для workflow router)

- Волна `wave-workflow-dx`: в список пакетов добавлен `workflow-dx-p6-cursor-sdk-trigger`; north_star дополнен опциональным путём `--trigger-cmd` + Cursor SDK.
- Новый пакет `workflow-dx-p6-cursor-sdk-trigger` (`status: proposed`): автозапуск агента из терминала после генерации `doc/current_task.md`, без ручного шага в IDE (после принятия контракта).
- Эпоха планирования: `doc/epochs/e32_workflow_sdk_trigger.md`.
- Регенерация `doc/tasklist.md`: `scripts/backlog_registry_lint.py --sync-from-index --write-sync`.

## Reopened: epoch-demo (2026-05-02)

- **Reason:** clean execution smoke: touch scripts/prompt_utils.py for post-agent
- **Affected US:** нет привязок `covered_by: epoch-demo` в `doc/user_stories_index.json` (скрипт индекс не меняет).
- **Action:** автоматический Step C (`scripts/reopen_epoch_demo_step_c.py`): `doc/backlog_registry.yaml` closed→ready; пометка в `doc/closed_iterations.md` (Recent); `doc/current_task.md`; два прогона `backlog_registry_lint.py --sync-from-index --write-sync` (второй с `--strict`).
- **CJM:** `doc/cjm.md` не изменялся (для токена пакета `epoch-demo` строк обычно нет).

## 2026-05-08 (PO router AI Vision planning docs)

- Added the AI Vision evaluation gate and ML package planning prompt for Product Owner workflows.
- Extended breakthrough ideation with `MODE=AI_VISION_IDEATION`, AI-specific constraints, and required ML/data/eval fields.
- Added Hybrid Intelligence scope guidance plus reusable evaluation/ML package templates and SSR examples.

## 2026-05-11 (SSR critical review fixes)

- Corrected SSR architecture docs to point at `app/smart_study_router.py` as the core contract and documented `ml_audit_ru`, Level 1 ML constraints, SSR ↔ PedagogicalRouter boundaries, trust/defer behavior, and outcome receipts.
- Expanded SSR LLM profiling docs with JSONL schema, concrete `outcome` enum, OTEL attributes, privacy/retention guidance, and operational targets.
- Added scenario YAML entries for scenarios 15 and 20 plus `scripts/check_scenario_ids.py`; updated scenario docs with SSR negative paths and demo frame numbering.
- Added typed SSR `EvidenceItem` support and filtered runtime ledger rendering to show only influencing signals by default.

## 2026-05-15 (ADR-021 critical review amendments)

- Added a verified Current state table at the top of `doc/adr_021_smart_router_rag_modes.md`, distinguishing implemented contracts (`KNOWN_RETRIEVAL_MODES`, graph postprocessor, `trace["graph_expansion"]`, `PipelineOverrides.retrieval_mode`/`rag_profile`) from aspirational ones (`trace["retrieval_routing"]`, `/ask` profile override, dedicated retrieval router).
- Introduced `RagProfile` (§4.6) as the user-facing override surface (`fast` / `quality` / `graph_aware`) composing retrieval mode, reranker, `graph_augmented` and `top_k`; product labels resolve to profiles, not raw mode names.
- Rewrote §6 to type the routing decision (`RetrievalRoutingDecision` in `app/models.py`), pin `classify_step` relationship (no re-classification), fix low-confidence fallback wording (default `quality`, applies only without explicit override), and add decision caching keyed on `(question_hash, profile, settings_signature)` reusing `app/query_faq_cache.py` namespace.
- Tightened graph-aware gating (§4.4) from query_type-only membership to composite rule `enable AND query_type ∈ S AND confidence ≥ θ AND (thin baseline OR explicit profile)`; introduced `GraphEvidence` typed payload (§7.2) with weak-evidence rendering threshold.
- De-scoped §7.3 to artifact-level `GlobalAnalyticsJob` contract (record colocated with `data/graph_generations/by_generation/<gid>/`); concrete summary schema deferred to Phase 4 design ADR.
- Resolved §10 SLO namespace conflict (`slo_latency_by_mode` is keyed by `query_mode`, table is keyed by RAG profile) by deferring wiring to a follow-up SLO task with explicit options.
- Added §9.1 metric ownership through existing `metrics_slo.py` / `metrics_summarizer.py` and §9.2 no-uplift demotion rule for `graph_aware`.
- Re-scoped §12 Phase 0 from "document" to "patch drift"; inserted §12 Phase 3 (Prompt selector contract owned by `app/prompts/`) and renumbered subsequent phases.
- Extended §13 acceptance criteria (typed routing trace, typed `GraphEvidence`, single classify pass per request, schema tests) and added §15 explicit ADR-019 ownership lines (query side owns router, graph side owns evidence and expansion).
- ADR remains `Accepted`; no code changes in this entry — all amendments are doc-only and route follow-up implementation through `doc/backlog_registry.yaml`.
- Applied the follow-up audit fixes for ADR-021: restored monotonic §5 numbering, removed `prompt_variant` / undefined `graph_caps` from `RagProfile`, added `effective_*` routing trace fields, typed `RetrievalSource`, required graph evidence confidence/direction/id, concrete conservative setting defaults, demotion persistence/metrics, global analytics kill-switch language, and `conventions_architecture.md` profile sync.
- Added proposed backlog wave/package `wave-adr-021-routing-contract` / `epoch-adr-021-router-contract-phase1` to scope ADR-021 Phase 1 implementation without changing retrieval defaults or public raw `retrieval_mode` exposure.
- Added proposed backlog wave/package `wave-adr-021-graph-aware-uplift` / `epoch-adr-021-graph-evidence-gating` for ADR-021 Phase 2 (`GraphEvidence`, composite graph gating, weak-evidence rendering, uplift/demotion metrics), explicitly excluding shadow-mode, dry-run, strategy decorators, and global analytics.
- Added proposed backlog wave/package `wave-adr-021-prompt-selector` / `epoch-adr-021-prompt-selector-contract` for ADR-021 Phase 3 (`PromptSelector` in `app/prompts/`), explicitly preserving tutor prompt ownership and excluding UI controls/global analytics prompts.
- Added proposed backlog wave/package `wave-adr-021-global-analytics-design` / `epoch-adr-021-global-analytics-design` for ADR-021 Phase 4 design-only global analytics scoping before any runtime endpoint/job implementation.
- Added proposed backlog wave/package `wave-adr-021-product-surfacing` / `epoch-adr-021-profile-surfacing` for ADR-021 Phase 5 safe UI/debug surfacing of RAG profiles and route explanations without exposing raw retrieval modes or conflating SSR routing.
- Added proposed backlog wave/package `wave-adr-021a-architecture-lifts` / `epoch-adr-021a-architecture-lifts-design` for the final audit follow-up: an explicit ADR-021a disposition pass over router/profile-resolver split, strategy decorator, data-driven profiles, debug/dry-run APIs, graph-aware shadow-mode, resilience policy, anti-goals, and measurable adoption horizon before implementation.
- Implemented ADR-021 Phase 1 routing contract: `/ask.profile` validates `fast` / `quality` / `graph_aware`, raw public `retrieval_mode` remains rejected, and `QueryContext.trace["retrieval_routing"]` records selected/effective profile, retrieval mode, graph decision, fallback reason, classify inputs, and explicit override status.


## 2026-05-24 (perf baseline fixes + strong moves architecture)

- **`app/api.py` — lifespan warmup restructure:** `_readiness_warmup_background`, `_index_stats_warmup_background`, and `_ssr_semantic_cache_warmup_background` moved outside `try: get_base_services()` block so they always start even with an empty index. Previously all background warmups were skipped when the collection was empty (caught by the same `except`), causing 35 s lazy SSR semantic cache init and 4 s first-bootstrap readiness scan.
- **`app/retrieval_cache.py` — negative-result cache:** Added `_cached_empty` flag. After the first `EmptyIndexError` (empty Chroma collection), subsequent calls short-circuit in O(1) without re-running Chroma client init. Reset by `clear_retrieval_cache()` so reindex re-checks correctly. Eliminates per-request "Initializing retrieval base services..." log spam and intermittent latency spikes on `/topics` with empty index.
- **`config.env` — `LLAMAINDEX_METADATA_FALLBACK_MODEL` fixed:** Changed from `google/gemma-4-31b-it` to `gpt-4o-mini`. LlamaIndex validates token limits against this value using the OpenAI model registry; non-OpenAI IDs caused silent validation failures.
- **`scripts/check_env.py` — OS env override detection:** Script now parses `config.env` as a reference before loading `.env`, and warns when any of `LLM_MODEL`, `SSR_LLM_MODEL`, `QUIZ_LLM_MODEL`, `LLAMAINDEX_METADATA_FALLBACK_MODEL` differ between OS env and `config.env` (stale export override). Also warns when a cloud provider prefix (`openai/`, `google/`, etc.) appears in a local-profile model var. Prints PowerShell unset commands for stale vars.
- **`.env.example` — `SSR_LLM_MODEL` added to BALANCED block:** Explicit `SSR_LLM_MODEL=qwen2.5-coder-7b-instruct` prevents "SSR effective model empty" warning at startup.
- **`doc/user_guide.md`** — fixed stale `SSR_LLM_MODEL=google/gemma-4-e4b` example line.
- **`doc/user_guide_details.md`** — added "Pre-flight: environment check" section documenting `check_env.py` usage, warning formats, and the `load_dotenv` OS env precedence explanation; added `/ui/bootstrap` slow troubleshooting entry.
- **`doc/backlog_registry.yaml`** — `wave-perf-baseline-fixes-2026-05` marked `completed`; `perf-retrieval-init-fix-v1` deliverables and exit_artifact updated to reflect actual write-set (`app/api.py`, `app/retrieval_cache.py`, `scripts/check_env.py`).
- **`doc/next/localhost_balance_course_delight_plan.md`** (commit 1376) — Phase 5/6 reorder (Ingest Without Fog → Phase 5, Golden Test → Phase 6); bootstrap acceptance criterion tightened to p95 < 2 s; upload constraint generalised to `<course-folder>` for `create_from_upload`; dummy key auto-inject at loopback (no new env key); `CLOUD_*` env vars confirmed non-parsed by Settings; Move 3 ADR gate made explicit; degradation ladder reranker condition corrected.
- **`archive/team_artifacts/strong-move-first-session-precompute-v1/3_architect_contract.md`** — new architect contract for First Session Artifact precompute at ingest tail (cold open = disk read, no LLM call); artifact schema, 5 invariants (LOCAL_STRICT, atomic write, scope hash guard, non-fatal builder), write-set, DoD.


## 2026-06-10 (smart-notes-konspekt-surfacing-v1: konspekt badge + smart batch button)

- **`app/konspekt_discovery.py`** (новый) — сканирует `data/<course>/*.md`, парсит YAML frontmatter, возвращает `KonspektMeta` (path, source, presentation, generated, tags) только для файлов с `type: konspekt`. `find_konspekt_for_source_in_data(rel_path)` — точный матч по нормализованному `source`-полю (lower + collapse punct/whitespace). `coverage_summary(paths)` → `CoverageSummary(covered, total, pct)`. Malformed/missing frontmatter пропускается без исключений.
- **`app/ui/topics_tab_right_column.py` — badge и умный батч:** `_render_konspekt_badge()` выводит `✅ конспект готов · [дата]` и кнопку `⬇ Скачать конспект` под каждым документом темы, у которого найден конспект. `render_obsidian_course_batch()` получил параметр `skip_with_konspekt=True`: показывает `✅ N из M уже имеют конспект — будет обработано K` и исключает покрытые документы из батча.
- **`app/ui/topics_tab.py` — умная кнопка курса:** `«Весь курс → Obsidian»` заменена на `_render_course_obsidian_button()`: при 100% покрытии показывает `✅ Все конспекты готовы` вместо кнопки; при частичном — кнопка с подсказкой `«N из M уже имеют конспект»`.
- **`tests/test_konspekt_discovery.py`** — 16 тестов: frontmatter parse, source match, case-insensitive match, no-match, wrong-course isolation, malformed/missing frontmatter graceful skip, coverage full/partial/zero/empty. 16/16 pass.
- **`doc/backlog_registry.yaml`** — `smart-notes-konspekt-surfacing-v1` → `closed` (2026-06-10); `wave-smart-notes-killer-feature` и `smart-notes-native-generation-v1` актуализированы под cloud-first реальность.


## 2026-06-10 (konspekt quality audit + universal prompt image fixes)

- **`doc/prompts/smart_lecture_konspekt_universal_cloud_llm.md` — mandatory image links (5 fixes):** Rewrote the visual section generation logic to make `![Слайд N](assets/<prefix>_slide_NN.png)` links unconditional. Root cause: the old escape-hatch "if path unavailable → text brief only" always fired because PNGs are created by `export_slide_assets.py --from-konspekt` *after* konspekt generation. Fixes: (1) added "Порядок работы с картинками" block explaining the two-phase pipeline, (2) rewrote escape-hatch to apply only when PDF is not provided at all, (3) changed section template from "insert if available" to "always write deterministic path", (4) clarified path-unavailable definition in general Формат вставки block, (5) updated DoD checklist to require image link + brief together for every heading.
- **`doc/prompts/run_smart_konspekt_cloud_llm.md` — renamed + extended:** Renamed from `generate_lesson_clean_text_cloud_llm.md`; added launcher/orchestrator DoD gate requiring canonical 10-criterion rubric and `### Слайд N` heading format.
- **`scripts/export_slide_assets.py` — plural-range heading support:** `KONSPEKT_SLIDE_HEADING_RE` now matches `Слайды N–M` (plural), expanding ranges to individual page numbers. Added guard: `Слайд N — Title` (em-dash before title) is not a range.
- **`tests/test_export_slide_assets.py` — 3 new tests:** `test_heading_with_plural_range`, `test_heading_with_build_pages_takes_leading_number`, `test_heading_with_dash_before_title_not_a_range`.
- **`data/ИИ Агенты/урок 1 Введение в концепцию AI-агентов.md` — full quality fix:** Added 32 `![Слайд N](assets/урок_1_slide_NN.png)` links across 11 visual headings. Replaced non-canonical 8-criterion rubric (used forbidden names `Покрытие TXT-транскрипта`, `Внешняя проверка`) with canonical 10-criterion rubric in `N/5` format. Moved non-video project pages from Видео section to Статьи.
- **`data/ИИ Агенты/урок_2_как_агент_думает_и_действует.md` — visual briefs + карта:** Added 12 `> **Визуальный brief:**` blockquotes under existing image links (were missing entirely). Fixed rubric format `5` → `5/5`. Added карта row for slide 17 (`transition / QR` — service separator «ВЫБОР МОДЕЛИ»).
- **`data/ИИ Агенты/Урок_3_Автономность_память_стейт_и_контроль_поведения.md` — Q&A slides + rubric:** Added карта rows for slides 8, 49, 54 (Q&A service slides confirmed via PDF text extraction). Fixed rubric format `5` → `5/5`; updated `Сохранение графической информации` from 4/5 to 5/5 (27 PNGs verified on disk); updated `Использование презентации` from 4/5 to 5/5 (all 70 slides accounted for).


## 2026-06-06 (course-scope isolation fixes + deactivate button)

- **`app/ui/study_scope.py` — extended state reset:** Added `last_answer` to `_SCOPE_DERIVED_STATE_KEYS`. New `_clear_scope_derived_state()` helper clears static keys and pattern-matches all `topic_scope_quiz_*` keys (resetting to `{}`) on both `activate_scope` and `deactivate_scope`. Prevents stale quiz/answer artifacts leaking across scope switches.
- **`app/ui/sidebar.py` — persistent deactivation chip:** `render_sidebar` now calls `get_active_scope()` after the gamification row; when a course is active it renders `st.info("🎯 Активный курс: <title>")` and a `× Деактивировать курс` button that calls `deactivate_scope()` and `st.rerun()`. Button is visible on every page/tab.
- **`app/ui/tutor_chat_session.py` — tutor scope:** `build_tutor_query_options` now passes `folder_rel=scope_folder_rel()` to `QueryOptions`. When a course is active the tutor's RAG retrieval is restricted to the course folder via `build_filters` in `pipeline_factory.py`.
- **`doc/user_guide.md`** — added scope-boundary caveat to §8 Course Workspace.
- **`doc/api_reference.md`** — added Course scope note under `/quiz/generate`, clarifying which endpoints support course-scope and how.
- **`tests/test_study_scope.py`** — two new tests: `test_activate_scope_clears_last_answer_and_quiz_keys`, `test_deactivate_scope_clears_last_answer_and_quiz_keys`.
