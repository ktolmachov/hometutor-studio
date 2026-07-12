# Active Runtime Task — invisible-half-p0-closure-v1

Package: `invisible-half-p0-closure-v1`
Source of truth: `doc/backlog_registry.yaml`
Runtime repo: `D:\Projects\hometutor`
Studio docs: read-only context only.

## Task

Continue/verify the active corrective package from registry: Invisible Half P0 closure.
Work only in `D:\Projects\hometutor` runtime write-set unless the user explicitly asks for studio/doc-sync.
Do **not** switch working directory to `D:\Projects\hometutor-studio`.
Do **not** run workflow commands, `close_package.py`, `run_autonomous.py`, registry sync, or package closure scripts.

## Runtime Write-Set

- `app/fact_source_binding.py`
- `app/flashcard_service.py`
- `app/learner_model_service.py`
- `app/llm_resilience.py`
- `app/query_response_postprocessing.py`
- `config.env`
- `tests/test_memory_loop_closure.py`

## Acceptance Focus

- `mastery_vector` keys are canonical graph concept ids only, never free text.
- Tutor/flashcard outcomes use the shared learner-model gateway and do not pollute mastery when cid is unresolved.
- `sessions_completed` grows only for quiz/session completion; tutor/flashcard use interaction counters.
- Quiz mastery overwrite semantics are preserved.
- Provider resilience is wired to the local circuit breaker without enabling cloud fallback.
- Agent default/config is honest until a UI door exists.

## Verification

Run only targeted runtime checks from `D:\Projects\hometutor`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_memory_loop_closure.py tests\test_flashcards_review_keyboard.py tests\test_flashcards_interactive_card.py tests\test_flashcards_scheduling.py tests\test_provider_openai_structured.py
.\.venv\Scripts\python.exe -m ruff check app\fact_source_binding.py app\flashcard_service.py app\learner_model_service.py app\llm_resilience.py app\query_response_postprocessing.py tests\test_memory_loop_closure.py
```

If ruff is unavailable because of sandbox/tooling, report it; do not compensate by running studio workflow commands.

## Final Report

Include:

- package selected and why (`invisible-half-p0-closure-v1`, active in registry);
- stale/dirty state noticed at start, if any;
- changed runtime files;
- targeted tests and ruff result;
- remaining runtime risks;
- short next step for owner/maintainer, without workflow command syntax.
