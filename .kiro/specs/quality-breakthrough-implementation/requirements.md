# Requirements Document: Quality Breakthrough Implementation

## Introduction

This specification defines requirements for implementing expert panel recommendations from two virtual defense sessions (`defense_virtual_defense.md` and `defense_expert_panel.md`) to achieve a measurable quality breakthrough for the home-rag_v2 project. The goal is to transform expert feedback into a structured, implementable specification that significantly improves the project's evaluation rigor, transparency, and defensibility.

**Context:** home-rag_v2 is a local-first educational RAG assistant (FastAPI + Streamlit + CLI + Telegram) using Chroma + llama-index for retrieval with configurable LLM providers. The core learning cycle is: answer → tutor → quiz → SRS → mastery → plan.

**North Star:** Move from "it works well" claims to "here's the reproducible eval-run proving it works well" — with retrieval metrics, adversarial test sets, cost/latency breakdowns, and honest limitation documentation.

## Glossary

- **System**: The home-rag_v2 RAG pipeline and learning orchestration system
- **Eval_Service**: The evaluation infrastructure in `app/eval_service.py` and `run_eval.py`
- **Retrieval_Pipeline**: The document retrieval and ranking system (vector/hybrid/BM25/doc_then_chunk modes)
- **Defense_Baseline**: A reproducible evaluation run with fixed dataset, metrics, and configuration
- **Adversarial_Corpus**: Test cases designed to expose RAG vulnerabilities (prompt injection, conflicting sources, no-answer scenarios)
- **Retrieval_Confidence**: An explainability signal indicating retrieval quality, NOT probability of truth
- **Cost_Profiler**: The pipeline profiler and cost logging system tracking latency and token usage by stage
- **Data_Deletion_Flow**: Documented procedure for complete removal of user data from all storage systems
- **Golden_Dataset**: A curated evaluation dataset with known-good answers for regression testing
- **LLM_Judge**: LLM-as-Judge evaluation using Faithfulness, Context Recall, Answer Relevancy metrics

## Requirements

### Requirement 1: Evaluation Framework Enhancement

**User Story:** As a project defender, I want a comprehensive evaluation framework with reproducible baselines, so that I can prove quality claims with evidence rather than assertions.

#### Acceptance Criteria

1. THE System SHALL create `eval_data/defense_eval_questions.json` with at least 6 categories: qa, keyword, overview, synthesis, negative, injection
2. WHEN evaluation is run, THE Eval_Service SHALL measure recall@k, MRR (Mean Reciprocal Rank), hit rate, and latency for each retrieval mode
3. THE System SHALL support comparative evaluation of vector_only, hybrid, bm25_only, and doc_then_chunk retrieval modes
4. THE Adversarial_Corpus SHALL include at least 3 test categories: prompt injection within documents, conflicting sources, and no-answer cases
5. WHEN evaluation completes, THE System SHALL generate a reproducible baseline report with run-id, timestamp, configuration snapshot, and all metrics
6. THE Golden_Dataset SHALL contain at least 20 questions covering all 6 categories with expected answer characteristics
7. FOR ALL evaluation runs, THE System SHALL preserve the eval results with run-id for reproducibility verification (round-trip property)

### Requirement 2: Retrieval Mode Comparison

**User Story:** As a RAG architect, I want empirical evidence comparing retrieval strategies, so that I can justify hybrid retrieval over vector-only with data.

#### Acceptance Criteria

1. THE System SHALL execute identical queries across all 4 retrieval modes: vector_only, hybrid, bm25_only, doc_then_chunk
2. WHEN retrieval mode comparison runs, THE System SHALL measure recall@k for k in [1, 3, 5, 10]
3. THE System SHALL calculate MRR (Mean Reciprocal Rank) for each retrieval mode
4. THE System SHALL measure hit rate (percentage of queries with at least one relevant result in top-k)
5. THE System SHALL record p50, p95, and p99 latency for each retrieval mode
6. THE System SHALL generate a comparison table showing relative performance across all metrics
7. FOR ALL retrieval mode comparisons, running the same query set twice SHALL produce metrics within 5% variance (idempotence property)

### Requirement 3: Cost and Performance Transparency

**User Story:** As an MLOps engineer, I want detailed cost and latency breakdowns by pipeline stage, so that I can identify bottlenecks and optimize resource usage.

#### Acceptance Criteria

1. THE Cost_Profiler SHALL track latency for each pipeline stage: classify, rewrite, embedding_query, retrieval, rerank, generation, judge
2. THE System SHALL log token usage and estimated cost per stage to `LLM_COST_LOG_DIR`
3. WHEN a query completes, THE System SHALL include stage-by-stage timing in `QueryContext.trace`
4. THE System SHALL generate a cost summary report aggregating token usage and cost by stage across all queries in a time period
5. THE System SHALL expose latency budget violations when any stage exceeds configured thresholds
6. THE System SHALL provide a CLI command to generate cost/latency breakdown from profiler logs
7. FOR ALL cost calculations, THE System SHALL use consistent token counting (invariant: same input → same token count)

### Requirement 4: Data Governance and Privacy

**User Story:** As a privacy engineer, I want documented data deletion procedures, so that users can exercise data sovereignty and comply with privacy requirements.

#### Acceptance Criteria

1. THE System SHALL document the complete Data_Deletion_Flow covering Chroma index, SQLite user_state, logs, history, feedback, and cost logs
2. THE System SHALL provide a CLI command to execute complete data deletion with confirmation prompt
3. WHEN data deletion executes, THE System SHALL remove all user data from: `chroma_db/`, `data/user_state.db`, `logs/`, `faq_memory.jsonl`, `sessions.db`
4. THE System SHALL verify deletion completeness by checking for residual user data after deletion
5. THE System SHALL document privacy boundaries: local-first storage vs cloud LLM inference trade-offs
6. THE System SHALL clarify in documentation that cloud mode transmits query context to LLM provider
7. FOR ALL deletion operations, executing deletion then attempting data access SHALL return empty results (deletion completeness property)

### Requirement 5: Terminology Accuracy

**User Story:** As a project reviewer, I want accurate terminology that doesn't overstate capabilities, so that I can trust the system's claims and understand its limitations.

#### Acceptance Criteria

1. THE System SHALL rename "confidence" to "retrieval_confidence" in all user-facing surfaces
2. THE System SHALL document that retrieval_confidence is an explainability signal, NOT probability of truth
3. THE System SHALL clarify course workspace boundary: folder/course scope currently, ACL/tenant isolation for future multi-user
4. THE System SHALL replace "production-ready" with "production-oriented for local one-user deployment" in documentation
5. THE System SHALL document limitations: BM25 in-memory constraints, OCR/PDF parsing gaps, local model quality trade-offs
6. THE System SHALL avoid absolute quality claims without citing specific eval-run results
7. FOR ALL terminology changes, THE System SHALL maintain backward compatibility in API contracts (no breaking changes)

### Requirement 6: Educational Metrics

**User Story:** As an educational AI researcher, I want metrics beyond answer quality that measure learning outcomes, so that I can validate the pedagogical effectiveness of the tutor system.

#### Acceptance Criteria

1. THE System SHALL track quiz correctness rate per concept over time
2. THE System SHALL measure retention: percentage of concepts with stable mastery after 7+ days
3. THE System SHALL track transfer task performance: ability to apply concepts in new contexts
4. THE System SHALL calculate SRS stability: percentage of reviews completed within scheduled interval
5. THE System SHALL expose educational metrics through `/metrics/educational` endpoint
6. THE System SHALL generate a learning outcomes report showing quiz correctness, retention, transfer, and SRS stability
7. FOR ALL educational metrics, THE System SHALL aggregate data across multiple learner sessions (metamorphic property: more sessions → more data points)

### Requirement 7: Adversarial RAG Test Set

**User Story:** As an AI safety engineer, I want adversarial test cases that expose RAG vulnerabilities, so that I can validate guardrails and identify security gaps.

#### Acceptance Criteria

1. THE Adversarial_Corpus SHALL include at least 5 prompt injection test cases with instructions embedded in documents
2. THE Adversarial_Corpus SHALL include at least 3 conflicting source scenarios where documents contradict each other
3. THE Adversarial_Corpus SHALL include at least 5 no-answer cases where the correct response is "insufficient information"
4. WHEN adversarial tests run, THE System SHALL measure guardrail effectiveness: percentage of injections blocked
5. THE System SHALL measure answer grounding: percentage of responses that cite sources vs hallucinate
6. THE System SHALL detect and flag when the system follows instructions from retrieved documents instead of system prompts
7. FOR ALL adversarial tests, THE System SHALL log failures with detailed trace for security review (error condition testing)

### Requirement 8: Latency Budget Documentation

**User Story:** As a performance engineer, I want documented latency budgets per pipeline stage, so that I can identify regressions and set SLO targets.

#### Acceptance Criteria

1. THE System SHALL document target latency budgets: classify ≤100ms, rewrite ≤200ms, retrieval ≤500ms, generation ≤2000ms, judge ≤1000ms
2. THE System SHALL measure actual latency against budget for each stage
3. WHEN latency exceeds budget, THE System SHALL log a latency violation event with stage name and overage percentage
4. THE System SHALL generate a latency budget compliance report showing percentage of queries meeting budget per stage
5. THE System SHALL expose latency budget violations through `/metrics/latency-violations` endpoint
6. THE System SHALL support configurable latency budgets through `RetrievalSettings`
7. FOR ALL latency measurements, THE System SHALL use consistent timing methodology (wall-clock time per stage)

### Requirement 9: Mastery Model Validation

**User Story:** As an educational AI researcher, I want validation that mastery scores reflect actual learning, so that I can trust the adaptive plan recommendations.

#### Acceptance Criteria

1. THE System SHALL correlate mastery scores with quiz correctness: higher mastery → higher quiz success rate
2. THE System SHALL measure mastery stability: concepts with mastery ≥80% should maintain ≥70% on retests after 7 days
3. THE System SHALL track false positives: concepts marked "graduated" that fail subsequent transfer tasks
4. THE System SHALL validate that mastery increases after successful quiz/review sessions
5. THE System SHALL expose mastery validation metrics through `/metrics/mastery-validation` endpoint
6. THE System SHALL generate a mastery model validation report with correlation coefficients and stability metrics
7. FOR ALL mastery updates, THE System SHALL ensure monotonic increase after successful learning events (invariant: success → mastery increases or stays same)

### Requirement 10: Eval Baseline Reproducibility

**User Story:** As a project maintainer, I want reproducible evaluation baselines, so that I can detect regressions and validate improvements across versions.

#### Acceptance Criteria

1. THE System SHALL generate a baseline report with: run-id, timestamp, git commit, configuration snapshot, all metrics
2. THE System SHALL store baseline reports in `eval_results/baselines/` with ISO timestamp naming
3. WHEN baseline comparison runs, THE System SHALL load previous baseline and compute metric deltas
4. THE System SHALL flag regressions: any metric degradation >10% from baseline
5. THE System SHALL support baseline promotion: marking a run as the new reference baseline
6. THE System SHALL document baseline creation procedure in `doc/eval_baseline_procedure.md`
7. FOR ALL baseline runs, executing the same eval dataset twice SHALL produce metrics within 5% variance (reproducibility property)

### Requirement 11: Source Readiness Diagnostics

**User Story:** As a learner, I want to understand which materials are ready for learning and which need preprocessing, so that I can make informed decisions about corpus quality.

#### Acceptance Criteria

1. THE System SHALL classify documents into categories: text-ready, needs-ocr, extraction-failed, unsupported-format
2. THE System SHALL provide readiness scores: percentage of corpus that is text-ready
3. WHEN source readiness diagnostic runs, THE System SHALL identify specific files needing OCR or manual intervention
4. THE System SHALL expose source readiness through `/kb/source-readiness` endpoint
5. THE System SHALL display source readiness summary in UI before ingestion
6. THE System SHALL document OCR/Docling integration as separate scope from text-ready ingestion
7. FOR ALL readiness classifications, THE System SHALL provide actionable next steps per document category

### Requirement 12: Regression Gate for Answer Quality

**User Story:** As a CI/CD engineer, I want automated regression gates that block merges when answer quality degrades, so that I can prevent silent quality regressions.

#### Acceptance Criteria

1. THE System SHALL provide a CLI command `run_eval.py --regression-gate` that exits non-zero on quality regression
2. WHEN regression gate runs, THE System SHALL compare current metrics against baseline
3. THE System SHALL fail the gate if: Faithfulness drops >10%, Context Recall drops >15%, or Answer Relevancy drops >10%
4. THE System SHALL distinguish retrieval failures from generation failures in regression reports
5. THE System SHALL provide actionable failure messages: which metric regressed and by how much
6. THE System SHALL support CI integration with JSON output format for automated parsing
7. FOR ALL regression gate runs, THE System SHALL complete within 5 minutes on the golden dataset (performance constraint)

## Special Requirements Guidance

### Parser and Serializer Requirements

**Eval Results Serialization:**
- THE System SHALL serialize evaluation results to JSON format
- THE System SHALL provide a pretty-printer for human-readable eval reports
- THE System SHALL support round-trip: parse eval JSON → generate report → parse report → equivalent data structure
- This is ESSENTIAL for reproducibility and regression detection

**Example Parser Requirements:**
```markdown
### Requirement 13: Eval Results Serialization

**User Story:** As a project maintainer, I want eval results in machine-readable format, so that I can automate regression detection and comparison.

#### Acceptance Criteria

1. WHEN evaluation completes, THE System SHALL serialize results to `eval_results/<run_id>/results.json`
2. WHEN invalid eval results are provided, THE System SHALL return a descriptive parse error
3. THE System SHALL format eval results into human-readable reports with tables and summaries
4. FOR ALL valid eval result objects, serializing then parsing then serializing SHALL produce equivalent JSON (round-trip property)
```

## Iteration and Feedback Rules

- The model MUST make modifications if the user requests changes
- The model MUST incorporate all user feedback before proceeding
- The model MUST offer to return to previous steps if gaps are identified

## Phase Completion

After completing this requirements document, the model MUST stop. The user will click a button in the UI to move to the next phase (design).
