# Implementation Plan: Quality Breakthrough Implementation

## Overview

This implementation plan transforms home-rag_v2 from "it works well" claims to "here's the reproducible eval-run proving it works well" by adding comprehensive evaluation infrastructure, retrieval mode comparison, cost/latency transparency, educational metrics, adversarial testing, and data governance procedures.

**Implementation Language:** Python

**Integration Strategy:** 4-phase rollout over 4 weeks
- Phase 1: Evaluation Infrastructure (Week 1)
- Phase 2: Metrics & Profiling (Week 2)
- Phase 3: Adversarial Testing (Week 3)
- Phase 4: Data Governance & Documentation (Week 4)

**Key Principles:**
- Incremental implementation with checkpoints
- Property-based tests for universal correctness properties
- Unit tests for specific examples and edge cases
- Backward compatibility maintained throughout

## Tasks

### Phase 1: Evaluation Infrastructure (Week 1)

- [ ] 1. Create golden evaluation dataset
  - [ ] 1.1 Create `eval_data/defense_eval_questions.json` with schema
    - Implement JSON schema with version, created_at, categories structure
    - Add 6 categories: qa, keyword, overview, synthesis, negative, injection
    - Each question must have: id, query, expected_characteristics
    - Ensure at least 3 questions per category (target: 20+ total)
    - _Requirements: 1.1, 1.6_
  
  - [ ]* 1.2 Write property test for golden dataset schema validation
    - **Property 1: Round-trip serialization consistency**
    - **Validates: Requirements 1.7**
    - Test that parsing JSON → modifying → serializing → parsing produces equivalent structure
    - Verify all required fields present in each question
  
  - [ ] 1.3 Create adversarial test documents in `eval_data/adversarial/`
    - Create `injection/` subdirectory with 5+ prompt injection test documents
    - Create `conflicting/` subdirectory with 3+ contradictory source pairs
    - Create `no_answer/` subdirectory with 5+ out-of-scope queries
    - _Requirements: 1.4, 7.1, 7.2, 7.3_

- [ ] 2. Implement retrieval comparison engine
  - [ ] 2.1 Create `app/eval_retrieval_comparison.py` with core data models
    - Implement `RetrievalModeResult` dataclass with recall@k, MRR, hit rate, latency metrics
    - Implement `RetrievalComparisonReport` dataclass with results_by_mode, winner_by_metric
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  
  - [ ] 2.2 Implement `RetrievalComparisonEngine` class
    - Implement `compare_modes()` to execute queries across all 4 retrieval modes
    - Implement `calculate_recall_at_k()` for k in [1, 3, 5, 10]
    - Implement `calculate_mrr()` for Mean Reciprocal Rank calculation
    - Implement `calculate_hit_rate()` for percentage with at least one relevant result
    - Track p50, p95, p99 latency per mode
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  
  - [ ]* 2.3 Write property test for retrieval comparison idempotence
    - **Property 2: Idempotence of retrieval comparison**
    - **Validates: Requirements 2.7**
    - Test that running same query set twice produces metrics within 5% variance
    - Verify for all 4 retrieval modes: vector_only, hybrid, bm25_only, doc_then_chunk
  
  - [ ]* 2.4 Write unit tests for retrieval metrics calculations
    - Test recall@k calculation with known retrieved/relevant sets
    - Test MRR calculation with known rankings
    - Test hit rate calculation with edge cases (no hits, all hits)
    - _Requirements: 2.2, 2.3, 2.4_

- [ ] 3. Implement baseline registry and comparator
  - [ ] 3.1 Create `app/baseline_comparator.py` with baseline data models
    - Implement `BaselineReport` dataclass with run_id, timestamp, git_commit, config_snapshot, metrics
    - Include fields for retrieval_comparison, educational_metrics, adversarial_results
    - Implement JSON serialization/deserialization methods
    - _Requirements: 1.5, 10.1, 10.2_
  
  - [ ] 3.2 Implement `BaselineComparator` class
    - Implement `load_baseline()` to read baseline reports from disk
    - Implement `compare()` to compute metric deltas between current and baseline
    - Implement `detect_regressions()` with configurable thresholds
    - Default thresholds: faithfulness 10%, context_recall 15%, answer_relevancy 10%
    - _Requirements: 10.3, 10.4_
  
  - [ ]* 3.3 Write property test for baseline serialization round-trip
    - **Property 3: Round-trip serialization for baseline reports**
    - **Validates: Requirements 1.7, 10.7**
    - Test that serializing → parsing → serializing produces equivalent JSON
    - Verify all nested structures preserved (config_snapshot, metrics, etc.)
  
  - [ ]* 3.4 Write unit tests for regression detection
    - Test regression detection with metrics exceeding thresholds
    - Test no regression when metrics within thresholds
    - Test edge cases: missing metrics, invalid baseline
    - _Requirements: 10.4_

- [ ] 4. Implement regression gate for CI/CD
  - [ ] 4.1 Create `RegressionGate` class in `app/baseline_comparator.py`
    - Implement `run()` method to execute evaluation and check regressions
    - Implement `exit_code()` to return 0 for pass, 1 for fail (CI-compatible)
    - Generate actionable failure messages with metric names and deltas
    - _Requirements: 12.1, 12.2, 12.3, 12.5_
  
  - [ ] 4.2 Add `--regression-gate` CLI command to `run_eval.py`
    - Add argument parser for `--regression-gate` and `--baseline` flags
    - Load baseline from specified path
    - Execute evaluation on golden dataset
    - Compare results and exit with appropriate code
    - Support `--json-output` for CI parsing
    - _Requirements: 12.1, 12.6_
  
  - [ ]* 4.3 Write integration test for regression gate end-to-end
    - Test gate passes when metrics meet baseline
    - Test gate fails when metrics degrade beyond thresholds
    - Test actionable error messages generated
    - Verify exit codes correct for CI integration
    - _Requirements: 12.2, 12.3, 12.5_

- [ ] 5. Enhance eval_service.py with baseline support
  - [ ] 5.1 Add baseline report generation to `app/eval_service.py`
    - Capture git commit hash using subprocess
    - Serialize current `RetrievalSettings` as config_snapshot
    - Generate unique run_id (UUID)
    - Save baseline reports to `eval_results/baselines/<ISO-timestamp>_<run_id>.json`
    - _Requirements: 1.5, 10.1, 10.2_
  
  - [ ] 5.2 Add `--save-baseline` flag to `run_eval.py`
    - Add argument parser for `--save-baseline` flag
    - Call baseline report generation after evaluation completes
    - Print baseline path for user reference
    - _Requirements: 10.1, 10.2_

- [ ] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

### Phase 2: Metrics & Profiling (Week 2)

- [ ] 7. Enhance cost profiler with stage budgets
  - [ ] 7.1 Add latency budget data models to `app/pipeline_profiler.py`
    - Implement `StageProfile` dataclass with stage_name, duration_ms, tokens, cost, budget_ms, budget_exceeded
    - Implement `QueryProfile` dataclass with query_id, total_duration_ms, total_cost_usd, stages, budget_violations
    - Define `DEFAULT_LATENCY_BUDGETS` dict with per-stage targets
    - _Requirements: 3.1, 3.2, 8.1_
  
  - [ ] 7.2 Enhance `PipelineProfiler` class with budget tracking
    - Add `__init__()` to accept latency_budgets dict
    - Implement `start_stage()` to begin profiling a pipeline stage
    - Implement `end_stage()` to end profiling, check budget, log violations
    - Track budget_exceeded flag per stage
    - _Requirements: 3.1, 3.2, 3.5, 8.2, 8.3_
  
  - [ ] 7.3 Add cost/latency aggregation and reporting
    - Implement `generate_cost_report()` to aggregate from cost logs
    - Calculate total cost and latency by stage across time period
    - Generate summary with most violated stages
    - _Requirements: 3.4, 3.6_
  
  - [ ]* 7.4 Write unit tests for latency budget tracking
    - Test budget violation detection when stage exceeds budget
    - Test no violation when stage within budget
    - Test cost calculation consistency (same input → same token count)
    - _Requirements: 3.7, 8.2, 8.3_

- [ ] 8. Create educational metrics collector
  - [ ] 8.1 Create `app/educational_metrics.py` with data models
    - Implement `ConceptMetrics` dataclass with quiz_correctness_rate, retention_rate, transfer_rate, srs_stability
    - Implement `EducationalMetricsReport` dataclass with system-wide aggregates
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  
  - [ ] 8.2 Implement `EducationalMetricsCollector` class
    - Implement `collect_concept_metrics()` to aggregate metrics for single concept
    - Query user_state.db for quiz attempts, correctness, retention checks
    - Calculate retention rate for concepts after 7+ days
    - Calculate transfer task performance from user_state
    - Calculate SRS stability from scheduled vs completed reviews
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  
  - [ ] 8.3 Implement system-wide reporting
    - Implement `generate_report()` to create `EducationalMetricsReport`
    - Implement `identify_struggling_concepts()` with configurable threshold (default 0.6)
    - Aggregate across all concepts in user_state
    - _Requirements: 6.6_
  
  - [ ]* 8.4 Write unit tests for educational metrics calculations
    - Test quiz correctness rate calculation
    - Test retention rate calculation with 7+ day filter
    - Test transfer rate calculation
    - Test SRS stability calculation
    - Test struggling concept identification
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 9. Implement mastery validation metrics
  - [ ] 9.1 Create `app/mastery_validation.py` with validation logic
    - Implement correlation calculation between mastery scores and quiz correctness
    - Implement mastery stability tracking (≥80% mastery should maintain ≥70% on retests)
    - Implement false positive detection (graduated concepts failing transfer tasks)
    - Verify monotonic increase after successful learning events
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.7_
  
  - [ ]* 9.2 Write unit tests for mastery validation
    - Test correlation calculation with known data
    - Test stability tracking over time
    - Test false positive detection
    - Test monotonic increase invariant
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.7_

- [ ] 10. Add metrics API endpoints
  - [ ] 10.1 Create `app/routers/metrics.py` with new endpoints
    - Implement `GET /metrics/educational` endpoint returning `EducationalMetricsReport`
    - Implement `GET /metrics/latency-violations` endpoint with period parameter
    - Implement `GET /metrics/mastery-validation` endpoint
    - Register router in `app/api.py`
    - _Requirements: 6.5, 8.5, 9.5_
  
  - [ ]* 10.2 Write integration tests for metrics endpoints
    - Test educational metrics endpoint returns valid report
    - Test latency violations endpoint with period filter
    - Test mastery validation endpoint returns correlation data
    - _Requirements: 6.5, 8.5, 9.5_

- [ ] 11. Create cost/latency reporting script
  - [ ] 11.1 Create `scripts/generate_cost_report.py`
    - Add CLI argument parser for `--period` and `--output` flags
    - Load cost logs from `LLM_COST_LOG_DIR`
    - Aggregate by pipeline stage
    - Generate markdown report with tables and summaries
    - _Requirements: 3.4, 3.6_

- [ ] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

### Phase 3: Adversarial Testing (Week 3)

- [ ] 13. Implement adversarial test runner
  - [ ] 13.1 Create `app/adversarial_test_runner.py` with test data models
    - Implement `InjectionTest` dataclass with test_id, query, injected_document_path, injection_type, expected_behavior
    - Implement `ConflictingSourceTest` dataclass with source_a_path, source_b_path, conflict_type
    - Implement `NoAnswerTest` dataclass with expected_response
    - _Requirements: 7.1, 7.2, 7.3_
  
  - [ ] 13.2 Implement `AdversarialTestRunner` class
    - Implement `run_injection_tests()` to execute prompt injection tests
    - Implement `run_conflicting_source_tests()` to execute conflicting source tests
    - Implement `run_no_answer_tests()` to execute no-answer tests
    - Implement `measure_guardrail_effectiveness()` to calculate percentage blocked
    - _Requirements: 7.4, 7.5, 7.6_
  
  - [ ] 13.3 Add adversarial test execution to eval pipeline
    - Integrate adversarial runner into `run_eval.py`
    - Add `--adversarial` flag to run adversarial tests
    - Include adversarial results in baseline reports
    - Log failures with detailed trace for security review
    - _Requirements: 7.7_
  
  - [ ]* 13.4 Write integration tests for adversarial runner
    - Test prompt injection detection with mock injected documents
    - Test conflicting source handling
    - Test no-answer case detection
    - Test guardrail effectiveness calculation
    - _Requirements: 7.4, 7.5, 7.6, 7.7_

- [ ] 14. Integrate adversarial tests with regression gate
  - [ ] 14.1 Add adversarial metrics to regression thresholds
    - Add guardrail_effectiveness threshold (default: 80%)
    - Add answer_grounding threshold (default: 85%)
    - Include adversarial metrics in regression detection
    - _Requirements: 7.4, 7.5_
  
  - [ ] 14.2 Update regression gate to check adversarial metrics
    - Extend `detect_regressions()` to include adversarial metrics
    - Generate actionable messages for adversarial failures
    - _Requirements: 12.3, 12.5_

- [ ] 15. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

### Phase 4: Data Governance & Documentation (Week 4)

- [ ] 16. Implement data deletion service
  - [ ] 16.1 Create `scripts/delete_all_data.py` with deletion logic
    - Define `DELETION_TARGETS` dict with all data storage locations
    - Implement `DataDeletionService` class with `delete_all_data()` method
    - Require explicit `--confirm` flag for safety
    - Generate `DeletionReport` with deleted and failed items
    - _Requirements: 4.1, 4.2, 4.3_
  
  - [ ] 16.2 Implement deletion verification
    - Implement `verify_deletion()` to check all targets removed
    - Add `--verify` CLI flag to check deletion completeness
    - _Requirements: 4.4_
  
  - [ ]* 16.3 Write property test for deletion completeness
    - **Property 4: Deletion completeness**
    - **Validates: Requirements 4.7**
    - Test that after deletion, attempting data access returns empty results
    - Verify all DELETION_TARGETS no longer exist
    - Test with various data states (empty, partial, full)

- [ ] 17. Implement source readiness diagnostics
  - [ ] 17.1 Create `app/source_readiness.py` with classification logic
    - Implement `DocumentReadiness` enum with TEXT_READY, NEEDS_OCR, EXTRACTION_FAILED, UNSUPPORTED_FORMAT
    - Implement `SourceReadinessReport` dataclass with counts and readiness_score
    - Implement `ActionableItem` dataclass with file_path, status, recommendation
    - _Requirements: 11.1, 11.2_
  
  - [ ] 17.2 Implement document classification logic
    - Classify documents by parsing success and text extraction quality
    - Calculate readiness_score as percentage text-ready
    - Generate actionable recommendations per document
    - _Requirements: 11.1, 11.2, 11.3_
  
  - [ ] 17.3 Add source readiness API endpoint
    - Implement `GET /kb/source-readiness` endpoint in appropriate router
    - Return `SourceReadinessReport` with classification results
    - _Requirements: 11.4, 11.5_
  
  - [ ]* 17.4 Write unit tests for source readiness classification
    - Test classification of text-ready documents
    - Test detection of documents needing OCR
    - Test handling of extraction failures
    - Test readiness score calculation
    - _Requirements: 11.1, 11.2, 11.7_

- [ ] 18. Update terminology: confidence → retrieval_confidence
  - [ ] 18.1 Add `retrieval_confidence` field to `QueryResponse` model
    - Add new `retrieval_confidence` field as primary
    - Add `@property confidence` with deprecation warning for backward compatibility
    - Include `retrieval_confidence_explanation` field
    - _Requirements: 5.1, 5.2, 5.7_
  
  - [ ] 18.2 Update API response to include both fields during transition
    - Return both `retrieval_confidence` and `confidence` (deprecated) in JSON
    - Add `_deprecation_notice` field to API response
    - _Requirements: 5.7_
  
  - [ ] 18.3 Update all internal code to use `retrieval_confidence`
    - Update `app/query_service.py` to use new field name
    - Update pipeline steps to use new field name
    - Update UI code to display `retrieval_confidence`
    - _Requirements: 5.1_
  
  - [ ]* 18.4 Write unit tests for backward compatibility
    - Test that `confidence` property returns same value as `retrieval_confidence`
    - Test deprecation warning is logged when accessing `confidence`
    - Test API response includes both fields
    - _Requirements: 5.7_

- [ ] 19. Create comprehensive documentation
  - [ ] 19.1 Write `doc/data_governance.md`
    - Document complete data deletion procedure
    - List all data storage locations and what gets deleted
    - Document verification procedure
    - Document privacy boundaries: local-first vs cloud inference trade-offs
    - Clarify that cloud mode transmits query context to LLM provider
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  
  - [ ] 19.2 Write `doc/eval_baseline_procedure.md`
    - Document baseline creation procedure with step-by-step commands
    - Document baseline promotion procedure
    - Document regression detection workflow
    - Include CI integration examples
    - _Requirements: 10.1, 10.2, 10.5, 10.6_
  
  - [ ] 19.3 Write `doc/latency_budgets.md`
    - Document per-stage SLO targets with rationale
    - Document monitoring and violation checking procedures
    - Document how to adjust budgets via configuration
    - Include latency budget table from design
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_
  
  - [ ] 19.4 Write `doc/terminology_updates.md`
    - Document confidence → retrieval_confidence migration rationale
    - Document migration timeline (v1.1 → v1.5 → v2.0)
    - Clarify that retrieval_confidence is explainability signal, NOT probability of truth
    - Document API changes and backward compatibility approach
    - _Requirements: 5.1, 5.2, 5.4, 5.6, 5.7_
  
  - [ ] 19.5 Update `.env.example` with new configuration options
    - Add latency budget environment variables
    - Add regression threshold configuration
    - Add educational metrics thresholds
    - Document all new settings
    - _Requirements: 3.1, 8.1, 8.6_

- [ ] 20. Create baseline promotion script
  - [ ] 20.1 Create `scripts/promote_baseline.py`
    - Add CLI argument parser for `--run-id` and `--mark-as` flags
    - Implement baseline promotion to mark as "latest"
    - Create symlink or copy to `eval_results/baselines/latest.json`
    - _Requirements: 10.5_

- [ ] 21. Update existing documentation for limitations
  - [ ] 21.1 Update project documentation with honest limitations
    - Replace "production-ready" with "production-oriented for local one-user deployment"
    - Document BM25 in-memory constraints
    - Document OCR/PDF parsing gaps
    - Document local model quality trade-offs
    - Document course workspace boundary (folder/course scope, not multi-tenant)
    - _Requirements: 5.3, 5.4, 5.5_

- [ ] 22. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at phase boundaries
- Property tests validate universal correctness properties from design
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows
- Backward compatibility maintained through dual-field approach with deprecation warnings
- All Python code follows project conventions: use `get_settings()` for config, `app/provider.py` for LLM/embeddings, `app/prompts.py` for prompts
- Test commands use `.\.venv\Scripts\python.exe -m pytest` per project conventions
