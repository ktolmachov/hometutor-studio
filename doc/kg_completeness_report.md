# KG completeness audit (SSR L4 gate)

_Generated `2026-06-11T15:06:42+00:00` (UTC) from `_gather_metrics()`._

## Classification

- **SSR L4 readiness:** `patchable`
- **Graph path:** `D:\Projects\hometutor-studio\data\concept_graph.json`
- **Readable path:** `False`

### Notes

- Graph file missing — treat coverage as incomplete; populate/export JSON before trusting L4 scoping.

## Metrics

| Metric | Value |
| --- | ---: |
| Concept count | 0 |
| Concepts declaring any prerequisites | 0 |
| Internal prerequisite edges (among declared IDs) | 0 |
| Dangling prerequisite refs | 0 |
| Cycle count | 0 |
| Topological order OK | True |
| Orphan spine nodes (no in/out prereq edges in-graph) | 0 |
| Invalid concept entries | 0 |

## Follow-ups

- This package is **audit-only**; repair belongs to separate backlog work.
- For SQLite bundle deployments, audit the bundle export JSON or staged `concept_graph.json` explicitly.
