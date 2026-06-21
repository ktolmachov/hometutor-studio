---
us_id: "US-2.5"
epic: 2
epic_name: "Epic 2: Ingest"
title: "Source readiness API contract parity"
priority: "P2"
cjm_stage: "2"
cjm_moment_name: "Ingest / corpus quality"
status: "closed"
covered_by: "epoch-qbi-source-readiness-contract-parity"
closed_date: "2026-05-06"
---

# US-2.5 - Source readiness API contract parity (P2)

## Epic 2: Ingest

[<- Back to user stories index](../user_stories.md)

---

### US-2.5 - Source readiness API contract parity (P2)

**As a** learner or maintainer checking corpus readiness before asking questions,
**I want** source readiness diagnostics exposed through a stable API contract,
**so that** UI, CLI, and future automation can distinguish text-ready files from OCR, extraction, and unsupported-format problems.

**Acceptance:**
- Given files exist in `data/`,
- When source readiness diagnostics run,
- Then every supported file is classified into explicit contract categories: `text_ready`, `needs_ocr`, `extraction_failed`, or `unsupported_format`.
- And the report includes a readiness score and actionable next step per non-ready file.
- And `/kb/source-readiness` returns the same contract without requiring UI bootstrap internals.
- And the story extends the closed US-2.4 MVP without reopening OCR/Docling implementation scope.

**Related:** `epoch-us-2-4-source-readiness-mvp`, `epoch-qbi-source-readiness-contract-parity`.

## Status History

- 2026-05-06 | status: `open` | created as residual parity gap from quality-breakthrough Requirement 11 / task 17.
