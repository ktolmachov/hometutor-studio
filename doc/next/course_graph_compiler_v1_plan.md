# Course Graph Compiler v1: evidence-backed GraphRAG for active courses

**Status:** proposed  
**Audit date:** 2026-06-10  
**Backlog wave:** `wave-course-graph-evidence-2026-06`

## 1. Executive decision

The next GraphRAG quality step is not a second retrieval stack and not immediate
community/global summarization. The missing foundation is a **Course Graph Compiler**
that turns an activated course into a normalized, evidence-backed concept graph.

The current Knowledge Graph UI is visually mature, but for the active course
`ИИ Агенты` it is rendering a document-title fallback rather than a semantic graph.
The compiler must make graph quality an explicit activation artifact with measurable
acceptance gates. Only after those gates pass should graph-aware retrieval be enabled
for the course.

## 2. Verified audit snapshot

Observed on 2026-06-10:

- Latest matching graph generation artifact:
  `data/graph_generations/by_generation/gen_home_rag_v2__staging__1781095403476_2026_06_10T12_43/`.
- `property_graph_store.json`: **5 nodes, 0 relations, 0 triplets**.
- Node identifiers are lesson filenames, not normalized domain concepts.
- Node provenance is `extraction_method=heuristic`, `confidence=0.72`.
- `data/concept_graph.json` is absent.
- Runtime settings at audit time:
  - `enable_metadata_enrichment=False`;
  - `enable_document_summaries=False`;
  - `GRAPH_MODEL=qwen/qwen3.6-27b` is configured;
  - graph LLM base is configured;
  - `enable_graph_augmented_retrieval=False`.
- `data/cache/course_artifacts.json` contained a four-document course artifact at
  12:15, while the later graph generation contained five lesson nodes at 12:43.
  Course cache and graph generation therefore need an explicit generation/scope link.
- Focused regression check passed:
  `tests/test_knowledge_graph_d3.py tests/test_folder_to_course.py` — **63 passed**.

Conclusion: this is current contract behavior, not a D3 rendering regression.

## 3. Root cause

1. `build_graph_payload_from_documents()` reads `topic`, `key_concepts`, and
   `concepts` from ingestion metadata.
2. With metadata enrichment disabled, those fields are absent, so the builder falls
   back to section/title/file name and creates one coarse node per lesson.
3. The heuristic builder creates prerequisites only between multiple ordered concepts
   found inside the same document. One fallback concept per document means zero edges.
4. `graph_llm_probe_ok()` proves only that `get_graph_llm()` can construct a client;
   it does not run graph extraction.
5. `resolve_graph_status()` can report `ready` when concepts exist and refresh succeeded,
   even if relation count and cross-document coverage are zero.
6. The D3 payload currently renders only `prerequisites`; `related_concepts` and future
   typed relations are not represented.

The closed `folder-to-course-delight-v1` package delivered activation/status UX and
status variants. Its write-set did not include a real graph-LLM extraction/compiler
stage. The phrase "graph DNA" therefore exceeded the delivered semantic depth.

## 4. What already exists

| Capability | State |
|---|---|
| Rich D3 graph, mastery rings, clusters, search, health panel | Implemented |
| JSON/SQLite property graph generations | Implemented |
| Prerequisite-aware tutor/SSR routing | Implemented |
| `fast`, `quality`, `graph_aware` profiles and typed routing trace | Implemented |
| Bounded multi-hop graph expansion | Implemented |
| Typed `GraphEvidence`, weak-evidence rendering, uplift eval scaffolding | Implemented |
| Retrieval prompt selector and learner-facing profile surfacing | Implemented |
| Global GraphRAG Analytics artifact/API design | Design only |
| Course-level semantic extraction and entity normalization | Missing |
| Evidence-backed typed cross-document relations | Missing |
| Course graph quality gate and honest status | Missing |
| Runtime community/global summaries and analytics jobs | Missing |

## 5. Target graph contract

### 5.1 Nodes

Nodes represent normalized concepts, not files. Every node carries:

- stable `concept_id` and display label;
- aliases and normalization method;
- description;
- source documents/chunks;
- extraction method, model, confidence, and generation id;
- optional difficulty and curriculum position.

Documents remain provenance objects linked to concepts; they are not substituted for
concepts in the normal graph-ready path.

### 5.2 Relations

Initial relation vocabulary:

- `prerequisite` — concept A must be understood before B;
- `uses` — B applies A without claiming strict prerequisite order;
- `extends` — B develops or specializes A;
- `contrasts` — A and B clarify each other through differences;
- `part_of` — A is a component of B;
- `precedes` — explicit lesson/curriculum order, never silently promoted to prerequisite;
- `related` — weak fallback relation, excluded from prerequisite routing.

Every semantic relation must include source document/chunk evidence, confidence,
extraction method, and generation id. Unsupported relations are dropped or marked
weak/inferred according to the existing `GraphEvidence` contract.

### 5.3 Publication

Compilation is staged and atomic:

1. resolve the exact course scope and source hashes;
2. extract per-document concepts and candidate relations through `get_graph_llm()`;
3. normalize aliases and merge cross-document entities;
4. validate evidence, dangling references, cycles, and quality metrics;
5. persist JSON + SQLite/property graph bundle under one generation id;
6. publish only when the quality gate passes;
7. bind course cache/status to that generation id and source scope.

If the graph model is unavailable or the gate fails, the indexed course remains usable,
but UI status is `pending` or `unavailable`, never semantic `ready`.

## 6. Quality gates

The first production gate for a course with at least three documents:

| Metric | Required |
|---|---:|
| normalized concept count | >= 12 |
| evidence-backed semantic relation count | >= 10 |
| documents participating in at least one concept | 100% |
| concepts with source evidence | 100% |
| semantic relations with source evidence | 100% |
| cross-document semantic relations | >= 3 |
| orphan concept rate | <= 25% |
| dangling relation references | 0 |
| unresolved prerequisite cycles | 0 |
| filename-fallback nodes in graph-ready publication | 0 |

Thresholds are initial operational values and must be calibrated with fixtures from
`ИИ Агенты`; they cannot be weakened merely to turn the badge green.

## 7. Delivery sequence

### Package 1 — `course-graph-compiler-v1`

Build the compiler, typed extraction payload, normalization, relation provenance,
generation publication, quality report, and honest graph status. Use only
`get_settings()`, `get_graph_llm()`, prompts from `app/prompts/`, and existing graph
bundle ownership.

### Package 2 — `course-graph-relation-ux-v1`

Render typed relations with a legend and filters. Preserve prerequisite directional
semantics, expose evidence/confidence in node/relation details, show generation/scope,
and clearly distinguish curriculum `precedes` from semantic `prerequisite`.

### Package 3 — `course-graph-aware-uplift-gate-v1`

Run graph-shaped eval questions against hybrid baseline and graph-aware retrieval.
Enable graph-aware behavior only after evidence quality, answer correctness/uplift,
latency, and no-uplift demotion gates pass. Do not make graph expansion universally on.

## 8. Global GraphRAG boundary

`doc/adr_021a_global_analytics_design.md` remains the accepted design for explicit
community/global analytics jobs. Runtime jobs, communities, summaries, API, UI,
provenance indexes, ceilings, and kill switch are still unimplemented.

They should receive a separate execution wave only after Course Graph Compiler and the
graph-aware uplift gate prove that entity normalization and relation evidence are good
enough. `global_graph` must not become an ordinary retrieval mode or `/ask` fallback.

## 9. Non-goals and kill switches

- No Neo4j or second primary graph store.
- No direct LLM client outside `app/provider.py`.
- No prompt hardcoding outside `app/prompts/`.
- No silent cloud extraction.
- No automatic conversion of lesson order into prerequisites.
- No `ready` status based only on node count or successful refresh.
- No graph-aware default before uplift evidence.
- No global analytics work hidden inside ordinary course activation.

Stop publication if evidence is missing, source scope/generation is stale, relations
are dangling, prerequisite cycles remain unresolved, or accepted LLM output is truncated.

## 10. Success criterion

For `ИИ Агенты`, the graph must visibly connect reusable concepts across lessons — for
example agent loop, tools, memory/state, guardrails, observability, and multi-agent
coordination — with inspectable source evidence. A user should be able to understand
why two concepts are connected and the retrieval pipeline should demonstrate measurable
quality uplift on relationship questions.
