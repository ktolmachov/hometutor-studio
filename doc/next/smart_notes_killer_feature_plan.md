# Smart Notes Killer Feature Plan

Updated: 2026-06-08

> **Revision 2026-06-08 — стратегия пересмотрена и частично реализована.**
> Облачная генерация по `doc/prompts/smart_lecture_konspekt_universal.md` с мультимодальными входами (txt + черновик + HTML + PDF) даёт конспект существенно выше локального pipeline (эталон `урок 1 Введение в концепцию AI-агентов.md`: 693 строки, Mermaid, таблицы, ДЗ, шпаргалка — против 134 строк локального урока 2). Новый приоритетный путь — **готовый `.md` как документ корпуса в `data/`** (см. `doc/obsidian_export_todo.md` → Задача 0). Phase 1 (детерминированный HTML→MD parser/import) **superseded/deferred**: облако уже поглощает HTML как вход, а `data/`-конспект индексируется напрямую. Phase 2 (локальная native-генерация) реализуется как **оффлайн/no-cloud fallback** через `materials/` + `app/smart_konspekt.py` + CLI + eval (источник плана: `C:\Users\Kostya\.claude\plans\clever-sprouting-church.md`).

Updated (original): 2026-06-06

Status: Phase 2 first slice implemented; Phase 1 import deferred  
Owner: product / learning experience  
Related docs:
- `doc/obsidian_export_todo.md`
- `doc/roadmap.md`
- `doc/backlog_registry.yaml`
- `doc/changelog.md`

## Goal

Сделать "умный конспект" новой killer feature для Obsidian export: пользователь выбирает урок или транскрипт, а система готовит качественный Markdown-конспект с минимальной потерей смысла, структуры и визуальной полезности.

Ключевой продуктовый ход: текущая система должна уметь использовать уже готовые умные конспекты, если они существуют, вместо повторной генерации. Это сокращает время, снижает стоимость и дает пользователю ощущение "система понимает мои материалы".

## Reference Inputs

### Lesson 2

Source transcript:
- `D:\exchange\ИИ Агенты\урок 2 Как агент думает и дейс.txt`

Reference smart note prepared by another model:
- `D:\exchange\ИИ Агенты\урок 2 Как агент думает и дейс.html`

Current generated Markdown:
- `D:\Projects\home-rag_v2\doc\конспекты\ИИ Агенты\урок 2 Как агент думает и дейс.md`

### Lesson 3

Combined transcript + smart note prepared by another model:
- `D:\exchange\ИИ Агенты\Урок 3. Автономность- память, стейт и контроль поведения.ts.md`

Reference smart HTML note:
- `D:\exchange\ИИ Агенты\Урок 3 Автономность- память ст.html`

Observed structure:
- The `.ts.md` file contains a ready smart-note layer before `# Чистый текст`.
- Raw transcript starts at `# Чистый текст`.
- Timestamped transcript starts at `# С таймкодами`.
- The embedded smart note contains stable headings:
  - `### **О ЛЕКЦИИ**`
  - `### **ВВЕДЕНИЕ И КОНТЕКСТ**`
  - `### **ГЛАВНАЯ СУТЬ**`
  - `### **ХРОНОЛОГИЯ И ЛОГИКА**`
  - `### **КЛЮЧЕВЫЕ ТЕЗИСЫ**`
  - `### **ПРИМЕРЫ И КЕЙСЫ**`
  - `### **ПРАКТИЧЕСКОЕ ПРИМЕНЕНИЕ**`
  - `### **ТЕРМИНЫ**`
  - `### **ЗАКЛЮЧЕНИЕ**`
  - `### **ЦИТАТЫ И УПОМИНАНИЯ**`
- The HTML file has a richer visual hierarchy: title, subtitle, tags, six major sections, subsections, accent callouts, quotes and checklist items.

### Lesson 4

Source transcript:
- `D:\exchange\ИИ Агенты\Урок 4 Катим в прод- надежност.txt`

Reference smart HTML note:
- `D:\exchange\ИИ Агенты\Урок 4 Катим в прод- надежност.html`

Combined transcript + smart note:
- `D:\exchange\ИИ Агенты\Урок 4. Катим в прод- надежность, безопасность и остановка.ts.md`

## Product Decision

Phase 1 should not be limited to "HTML import". The optimal first implementation is:

**Existing Smart Note Import**

The export pipeline should discover and reuse the best available smart-note candidate:

1. Directly selected `.html` / `.htm` smart note.
2. Companion `.html` / `.htm` near the selected source, matched by normalized lesson title.
3. Embedded smart-note layer in `.md` / `.ts.md`, before `# Чистый текст`.
4. Existing Markdown source copy, when it is already a clean note (has ≥3 headings, no raw timestamps, has frontmatter or structured sections).
5. Plain transcript generation / conversion fallback.

See [Candidate Discovery Rules](#candidate-discovery-rules) for normalization and matching details. The ranking above is the single source of truth; other sections reference it.

This gives the user the most convenient workflow: select the lesson once, see that a smart note was found, and export it without needing to paste paths manually.

## UX Proposal

### Single Document Export

In the current document import / Obsidian export UI, each row should show smart-note status:

| Status | Meaning |
|---|---|
| `smart HTML найден` | A companion or selected HTML smart note can be imported. |
| `smart summary внутри .md` | The selected Markdown contains a ready smart-note layer. |
| `обычный импорт` | No smart candidate was found; use current export path. |

Button behavior:

| Candidate | Default button |
|---|---|
| Smart candidate found | `Импортировать умный конспект` |
| No candidate | `Подготовить для Obsidian` |

Add a default-on option near the button:

`Использовать найденный умный конспект`

If unchecked, the pipeline should use the current generation / copy behavior. This is important for control and debugging: the user can compare "готовый умный конспект" versus "сгенерировать заново".

### Batch Export

Batch mode should default to using discovered smart candidates and report separate counters:

| Counter | Meaning |
|---|---|
| `imported-smart-html` | HTML smart note imported. |
| `imported-smart-md` | Embedded Markdown smart-note layer imported. |
| `converted` | Plain source converted through current pipeline. |
| `copied` | Existing Markdown copied. |
| `cached` | Target already existed and force was disabled. |

### Why Not Manual Flag Only

Manual UI flag "у этого файла уже есть умный конспект" is useful as a visible option, but should not be the main model. It forces the user to know and remember file relationships.

Better flow:

1. System auto-discovers candidates.
2. UI displays what was found and why.
3. User can accept default or disable smart import for this run.

## Target Architecture

```text
source file selected in UI / batch
        |
        v
resolve_source(rel_path)
        |
        v
discover_smart_note_candidates(source_abs)
        |
        +-- selected .html/.htm
        +-- companion .html/.htm by normalized title
        +-- embedded smart markdown before "# Чистый текст"
        +-- existing markdown copy
        +-- plain transcript fallback
        |
        v
to_obsidian_markdown(..., smart_import=True)
        |
        +-- smart_note_from_html(...)
        +-- smart_note_from_embedded_markdown(...)
        +-- current txt/md export path
        |
        v
render_smart_note_markdown(...)
        |
        v
validate_smart_note_markdown(...)
        |
        v
data/<relative path>.md
```

## Proposed Module Boundary

Create a small focused module:

`app/smart_notes.py`

Responsibilities:

- Discover existing smart-note candidates.
- Parse reference HTML into a normalized intermediate model.
- Extract embedded smart-note Markdown from `.md` / `.ts.md`.
- Render final Obsidian Markdown.
- Validate output quality.

Do not put parser logic into UI or router code.

Suggested contracts:

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class SmartNoteKind(Enum):
    HTML = "html"
    EMBEDDED_MD = "embedded_md"
    MARKDOWN_COPY = "markdown_copy"
    GENERATED = "generated"


@dataclass(frozen=True)
class SmartNoteCandidate:
    path: Path
    kind: SmartNoteKind
    confidence: float
    reason: str


def discover_smart_note_candidates(source_abs: Path) -> list[SmartNoteCandidate]:
    ...


def smart_note_from_html(html: str) -> SmartNote:
    ...


def extract_embedded_smart_markdown(markdown: str) -> str | None:
    ...


def smart_note_from_embedded_markdown(markdown: str) -> SmartNote:
    ...


def render_smart_note_markdown(note: SmartNote) -> str:
    ...


def validate_smart_note_markdown(markdown: str) -> list[str]:
    ...
```

`SmartNote` and `SmartNoteSection` can start as simple dataclasses:

```python
@dataclass(frozen=True)
class SmartNoteSection:
    heading: str
    level: int  # 2 = ##, 3 = ###, etc.
    body: str   # rendered Markdown body of this section
    role: str   # semantic role: intro | abstract | timeline | key_points |
                # examples | practical | glossary | summary | quotes | other


@dataclass(frozen=True)
class SmartNote:
    title: str
    subtitle: str | None
    tags: tuple[str, ...]
    sections: tuple[SmartNoteSection, ...]
    source_kind: SmartNoteKind
```

Avoid over-engineering. The first version only needs enough structure to preserve headings, callouts, lists, quotes, checklists and links.

## Candidate Discovery Rules

Ranking:

1. Direct selected HTML file.
2. Companion HTML in the same folder with normalized title match.
3. Embedded smart summary in selected Markdown / `.ts.md`.
4. Selected Markdown as regular copy.
5. Plain transcript generation fallback.

Normalization:

- lower-case
- replace punctuation with spaces
- collapse whitespace
- strip common suffixes: `.ts`, `transcript`, `таймкоды`, `чистый текст`
- match lesson number when present
- require same folder for automatic companion matching

Do not use broad fuzzy matching in v1. Wrong smart-note import is worse than missing smart-note import.

## HTML to Markdown Mapping

| HTML element / class | Markdown output |
|---|---|
| `h1` | `# Title` |
| subtitle / lead paragraph | short intro paragraph |
| tag chips | YAML `tags` or inline `#tag` block |
| `h2` | `## Section` |
| `h3` | `### Subsection` |
| `h4` | `#### Detail` |
| normal paragraphs | paragraphs |
| ordered / unordered lists | Markdown lists |
| check items | `- [ ]` or `- [x]` depending on source |
| quote blocks | Obsidian quote callout or Markdown quote |
| blue / pink / accent boxes | Obsidian callouts |
| strong / emphasis | Markdown bold / italic |
| code | Markdown inline code / fenced code |

Recommended callout mapping:

| Source block | Obsidian callout |
|---|---|
| key idea / blue box | `> [!note]` |
| warning / risk / pink box | `> [!warning]` |
| quote | `> [!quote]` |
| practical checklist | `> [!todo]` |

## Embedded Markdown Mapping

For lesson 3 style `.ts.md`, treat everything before `# Чистый текст` as the smart-note layer.

| Marker / heading | SmartNote role |
|---|---|
| content before `# Чистый текст` | smart-note layer |
| `### **О ЛЕКЦИИ**` | metadata / intro |
| `### **ВВЕДЕНИЕ И КОНТЕКСТ**` | context |
| `### **ГЛАВНАЯ СУТЬ**` | abstract / main idea |
| `### **ХРОНОЛОГИЯ И ЛОГИКА**` | timeline |
| `### **КЛЮЧЕВЫЕ ТЕЗИСЫ**` | main sections / bullets |
| `### **ПРИМЕРЫ И КЕЙСЫ**` | examples |
| `### **ПРАКТИЧЕСКОЕ ПРИМЕНЕНИЕ**` | checklist / action section |
| `### **ТЕРМИНЫ**` | glossary |
| `### **ЗАКЛЮЧЕНИЕ**` | summary |
| `### **ЦИТАТЫ И УПОМИНАНИЯ**` | quote callouts / references |

The extractor should stop before raw transcript markers:

- `# Чистый текст`
- `# С таймкодами`
- `## Транскрипт`
- `## Transcript`

## Quality Bar

A converted smart note is acceptable only if:

- Title is preserved.
- At least three meaningful sections are preserved.
- Callouts / accent blocks are not flattened into anonymous paragraphs.
- Lists remain lists.
- Quotes remain visually distinct.
- Tags are preserved when present.
- Markdown is readable in Obsidian without HTML noise.
- No raw CSS / JS / navigation boilerplate leaks into the note.
- For `.ts.md`, raw transcript is not duplicated into the smart-note output unless explicitly requested.

## Known Tech Debt (existing code)

The following AGENTS.md violations existed in `app/obsidian_export.py` and must not be reintroduced:

| Violation | Location | AGENTS.md rule |
|-----------|----------|----------------|
| `_MAP_PROMPT`, `_MERGE_PROMPT`, `_COMPOSE_PROMPT` hardcoded in module | fixed: exported from `app/prompts` | Промпты: только пакет `app/prompts/` |
| `_get_llm()` constructed `OpenAI()` directly | fixed: delegates to `app.provider.get_obsidian_export_llm()` | LLM / embeddings: только `app/provider.py` |

Phase 2 must keep this boundary: prompt access through `app/prompts`, LLM construction through `app/provider.py`.

## Phase 1: Existing Smart Note Import (Superseded / Deferred)

**Status 2026-06-08:** not the next implementation step. Keep this section as historical design notes only. Do not run the old Phase 1 session prompt unless the owner explicitly reopens HTML/.ts.md direct import.

Package intent:

`smart-notes-html-import-v1` should be broadened to existing smart-note import while keeping the package id for roadmap continuity.

Deliverables:

- `app/smart_notes.py`
- HTML smart-note parser.
- Embedded smart Markdown extractor.
- Candidate discovery with conservative companion matching.
- Integration into `app/obsidian_export.py`.
- UI badge and default-on option in `app/ui/topics_tab_right_column.py`.
- Focused tests in `tests/test_smart_notes.py` and existing Obsidian export tests.
- Changelog entry.

Read-set:

- `app/obsidian_export.py`
- `tests/test_obsidian_export.py`
- `doc/obsidian_export_todo.md`
- `app/ui/topics_tab_right_column.py`:
  - `_render_obsidian_export_button`
  - `_render_obsidian_batch_button`
  - status/list rendering around the Obsidian export controls
- `D:\exchange\ИИ Агенты\урок 2 Как агент думает и дейс.html`
- `D:\exchange\ИИ Агенты\Урок 3. Автономность- память, стейт и контроль поведения.ts.md`
- `D:\exchange\ИИ Агенты\Урок 3 Автономность- память ст.html`

Write-set:

- `app/smart_notes.py`
- `tests/test_smart_notes.py`
- `app/obsidian_export.py`
- `app/ui/topics_tab_right_column.py`
- `doc/changelog.md`

Tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_smart_notes.py tests\test_obsidian_export.py -q --tb=short
.\.venv\Scripts\python.exe scripts\lint_agent_prompts.py
.\.venv\Scripts\python.exe scripts\check_llm_context_gate.py
```

Suggested test cases:

- `test_extract_embedded_smart_markdown_stops_before_clean_text`
- `test_smart_note_from_embedded_markdown_extracts_summary_terms_quotes`
- `test_discover_smart_note_candidates_prefers_companion_html_over_embedded_md`
- `test_obsidian_export_imports_selected_html_without_llm`
- `test_obsidian_export_imports_embedded_smart_markdown_without_llm`
- `test_obsidian_export_uses_discovered_companion_html_when_enabled`
- `test_obsidian_export_can_force_plain_generation_when_smart_candidate_disabled`
- `test_render_smart_note_markdown_preserves_callouts_lists_and_tags`

Acceptance criteria:

- Selecting the lesson 2 HTML produces a clean Obsidian Markdown smart note without LLM calls.
- Selecting the lesson 3 `.ts.md` imports the embedded smart-note layer without copying raw transcript.
- Selecting a transcript with a matching companion HTML imports the HTML candidate by default.
- When both companion HTML and embedded `.ts.md` smart layer exist, companion HTML is preferred.
- UI clearly shows that a smart candidate was found.
- UI lets the user disable smart import and use the normal export path.
- Batch export reports smart imports separately from generated / copied files.
- `validate_smart_note_markdown` rejects output with raw CSS/JS, missing title, or fewer than 3 sections.

Dependency note: HTML parsing should use `BeautifulSoup` with `html.parser` backend (stdlib). If `BeautifulSoup` is unavailable, fall back to `html.parser` directly. Do not add `lxml` as a dependency.

## Phase 2: Native Smart Note Generation (Local Pipeline)

**Статус:** first slice implemented and rejected as quality fallback after real-runs (2026-06-08/09).  
**Полный план:** `C:\Users\Kostya\.claude\plans\clever-sprouting-church.md`

**Run 3 verdict:** single universal compose is not viable on local `qwen/qwen3.6-27b` with the current prompt shape. After merge `max_tokens` fix, compose used `14328` prompt tokens and hit the model/server total context cap at `16384` total tokens (`completion_tokens=2056`, `finish_reason=length`, `truncated=1`). The note was unfinished (`7086` chars, `0` Mermaid, `0` tables, `4/6` structural checks). The next implementation must replace the single final compose with section-level generation and validation gates.

**Новая архитектура:** section-level SmartKonspekt pipeline — `map→evidence reduce→outline→per-section compose→validate→assemble`. The final Markdown is assembled deterministically from validated sections; no single large final Markdown compose is allowed.

**Папка исходников:** `materials/<курс>/<лекция>/` (не индексируется; корпус в `data/`).

```
materials/<курс>/<лекция>/
   ├── *.txt   → транскрипт (map→reduce)
   ├── *.md    → черновой конспект (в compose как есть, с обрезкой)
   ├── *.html  → HTML-конспект (strip тегов → текст)
   └── *.pdf   → презентация (extract текст, обрезка до бюджета)
data/<курс>/<лекция>.md   → ВЫХОД (type: konspekt, попадает в ингест/RAG)
```

**Новый модуль `app/smart_konspekt.py`** (не раздувает `obsidian_export.py`):

- `gather_lecture_inputs(lecture_dir) → LectureInputs` — классифицирует файлы по ролям
- `_extract_text(path) → str` — `.html` → HTMLTextReader; `.pdf` → PyPDF; `.md`/`.txt` → flat read
- `_build_evidence_context(...)` — подготавливает bounded evidence packets для outline/section compose
- `_plan_sections(evidence) → SmartKonspektPlan` — генерирует/валидирует список секций и evidence refs
- `_compose_section(section_id, section_spec, evidence_slice) → SectionDraft` — отдельный LLM-вызов на одну секцию
- `_validate_section(section) → SectionValidation` — структурные проверки, non-truncation, required artifacts
- `_assemble_sections(plan, sections) → str` — детерминированная сборка Markdown + frontmatter
- `generate_smart_konspekt(lecture_dir, *, force, progress) → SmartKonspektResult` — orchestrator: gather → partial resume → map/evidence reduce → outline → per-section compose → validate → assemble → write `data/`

**Section-level pipeline contract:**

1. **Map evidence.** Split transcript as today, but map output must preserve typed evidence, not prose-only summaries:
   - `concepts`: term, definition, why it matters, source chunk id
   - `examples`: concrete story/demo/code/tool mention, source chunk id
   - `comparisons`: pairs/axes suitable for tables
   - `processes`: ordered steps suitable for Mermaid/flow diagrams
   - `risks`: anti-pattern, failure mode, mitigation
   - `homework`: task, constraints, expected outcome
   - `quotes_or_phrases`: short source-backed phrases worth preserving
2. **Reduce by role, not one global prose blob.** Merge evidence into bounded buckets: `overview`, `concepts`, `architecture`, `planning`, `tools_memory`, `examples`, `risks`, `practice`, `glossary`, `quiz`, `cheatsheet`. Each bucket must fit a small section prompt and keep source ids.
3. **Outline pass.** Produce `SmartKonspektPlan` with stable `section_id`, heading, required artifacts, evidence refs, and target output budget. The plan must include at least:
   - `main_thesis`
   - `lecture_map`
   - `key_topics`
   - `architecture_flow`
   - `comparison_tables`
   - `examples`
   - `risks_antipatterns`
   - `practical_takeaways`
   - `glossary`
   - `control_questions`
   - `homework`
   - `cheatsheet`
4. **Per-section compose.** Each section is generated in its own call with a narrow prompt and evidence slice. Target: prompt ≤ 6k actual model tokens, output budget 1k-3k tokens per section. Sections that need tables/diagrams must generate only that artifact plus short explanation, not the whole note.
5. **Assemble, do not rewrite.** The final step only concatenates validated section Markdown in plan order and adds frontmatter. It must not ask the LLM to rewrite the whole note.

**Validation gates (blocking):**

- Every LLM call used for accepted output must expose finish metadata. Any accepted `map`, `merge`, `outline`, or `section` response with `finish_reason == "length"` or provider `truncated == 1` is a hard failure.
- If a section hits `length`, retry once with a smaller evidence slice or split the section into child sections. If the retry also hits `length`, stop and keep partial artifacts/cache for debugging; do not write final `data/<course>/<lecture>.md`.
- Required artifact gates:
  - at least 1 Mermaid block in `architecture_flow`
  - at least 3 Markdown tables across `comparison_tables` / `glossary` / `cheatsheet`
  - glossary/terms present
  - control questions present
  - homework/practice task present
  - cheatsheet present
- Markdown integrity gates:
  - no unclosed fenced code blocks
  - no incomplete final sentence/word heuristic at section end
  - tables have header separator rows
  - Mermaid fences are balanced and use `mermaid`
  - generated section does not contain frontmatter
- Quality gates:
  - section count ≥ 10
  - headings ≥ 25 for lesson-1 sized input
  - output chars should target 20k-35k for 300k+ char transcript; below 15k is a warning unless source is short
  - section evidence refs cover at least 70% of map chunks for long transcripts

**Implementation note for `finish_reason`:** current `_complete()` returns only text. Section-level implementation needs a small result wrapper, e.g. `LLMTextResult(text, finish_reason, prompt_tokens, completion_tokens, total_tokens, truncated)`, populated from llama-index/OpenAI-compatible response metadata where available. Validation must consume this wrapper before stripping fences/frontmatter.

**Новые/обновлённые поля `app/config.py`:**

```python
obsidian_export_prompt_path: str = "doc/prompts/smart_lecture_konspekt_universal.md"
obsidian_export_materials_dir: str = "materials"
smart_konspekt_transcript_budget: int = 12000   # chars
smart_konspekt_draft_budget: int = 8000
smart_konspekt_html_budget: int = 4000
smart_konspekt_pdf_budget: int = 4000
smart_konspekt_section_prompt_token_budget: int = 6000
smart_konspekt_section_output_tokens: int = 2500
smart_konspekt_section_retry_on_length: bool = True
smart_konspekt_min_mermaid_blocks: int = 1
smart_konspekt_min_tables: int = 3
smart_konspekt_min_output_chars_long: int = 20000
```

**CLI и eval:**

- `scripts/generate_konspekt.py` — аргумент `<курс>/<лекция>` или путь; `--model`, `--force`; печатает таблицу фаз/времён
- `scripts/eval_konspekt.py` — структурный чек-лист (Mermaid, таблицы, термины, вопросы, шпаргалка) + сравнение local vs cloud по метрикам + вердикт «стоит ли локально»

**Тесты `tests/test_smart_konspekt.py`** (все с mock LLM):

- `test_gather_lecture_inputs_classifies_by_role`
- `test_extract_text_html_strips_tags` / `test_extract_text_md_flat`
- `test_build_compose_context_respects_budgets`
- `test_universal_prompt_loaded_and_appended`
- `test_generate_writes_konspekt_to_data`
- `test_partial_resume_skips_map_reduce`
- `test_section_compose_rejects_finish_reason_length`
- `test_section_compose_retries_with_smaller_evidence`
- `test_assemble_requires_mermaid_tables_terms_questions_cheatsheet`
- `test_final_markdown_not_written_when_validation_fails`
- `test_section_prompts_stay_under_budget`

**Aprori оценка:** `qwen/qwen3.6-27b` не выдерживает one-shot rich Markdown compose при 16k effective context. Локальный путь остаётся оправданным при оффлайне / приватности только через section-level compose with hard validation.

Prompts must be accessed through `app/prompts` (`get_smart_lecture_konspekt_universal_prompt`, Obsidian map/merge/compose prompt constants). Model access must go through `app.provider.get_obsidian_export_llm()`.

Quality comparison uses `data/ИИ Агенты/урок 1 Введение в концепцию AI-агентов.md` (693 строки, облачный эталон) as golden example.

Generated smart-konspekt quality gate:

```powershell
.\.venv\Scripts\python.exe scripts\validate_smart_konspekt.py "data\<курс>\<конспект>.md" --expect-source-sha --strict
.\scripts\validate_course_konspekts.ps1 -Course "<курс>"
.\scripts\validate_course_konspekts.ps1 -AllCourses
```

`validate_course_konspekts.ps1` is the universal wrapper for course folders under `data/`. Course-specific wrappers are intentionally not used; pass `-Course`, `-CourseDir`, or `-AllCourses`.

## Phase 3: Smart Note Review and Regeneration

Add review tools:

- "compare with source"
- "find missing key ideas"
- "make shorter"
- "make more practical"
- "add quiz cards"
- "add spaced repetition reminders"

This phase connects smart notes to the existing learning loop: answer -> tutor -> quiz -> spaced repetition -> plan.

## Phase 1.5: Smart Note → RAG Index Integration (Superseded)

Superseded by **Задача 0: конспект-как-документ в `data/`**. The smart note no longer lives only in `doc/конспекты/`; it is the indexed corpus document itself. No separate Chroma integration layer is needed for the current workflow.

Historical approach if section-level smart-note indexing is reopened:

- Each `SmartNoteSection` becomes a separate chunk with metadata: `{source, section_role, heading, tags}`.
- Contextual enrichment: add topic keywords, difficulty level, prerequisite concepts to chunk metadata.
- Hybrid search: vector search for semantics + exact match for terms from the glossary section.
- When a smart note is re-imported (source changed), old chunks are replaced (versioned by source SHA).

This is inspired by the lecture pattern: *"Multi-layer RAG — raw data → extract insights → store insights in RAG (don't dump everything raw)"* (Урок 3).

## Risks

| Risk | Mitigation |
|---|---|
| Wrong companion file matched | Same-folder requirement, lesson-number check, conservative normalized title match. |
| HTML parser loses visual hierarchy | Use structured parser and golden fixtures from lesson 2 / lesson 3. |
| Embedded `.ts.md` imports raw transcript by accident | Stop extraction at raw transcript markers and test this explicitly. |
| UI becomes confusing | Show one status badge and one default-on option only. |
| Parser becomes too generic | Support observed structures first; expand only with tests. |
| Output is pretty but not useful | Quality bar requires terms, examples, action points and callouts. |

## Separate Session Prompt

Use this prompt to continue Phase 2 verification or polish in a separate Codex session:

```text
Продолжи Phase 2 из doc/next/smart_notes_killer_feature_plan.md:
Local Smart Konspekt generation.

Цель:
- проверить/доработать `app/smart_konspekt.py`;
- входы брать из `materials/<курс>/<лекция>/`;
- выход писать в `data/<курс>/<лекция>.md` с `type: konspekt`;
- не трогать UI-перенаправление без отдельного решения владельца.

Жесткие ограничения проекта:
- соблюдать AGENTS.md;
- write-set не расширять без причины;
- prompt access только через `app/prompts`;
- LLM access только через `app/provider.py`;
- Python запускать через .\.venv\Scripts\python.exe.

Read-set:
- app/smart_konspekt.py
- app/obsidian_export.py
- app/prompts/_impl.py
- app/provider.py
- tests/test_smart_konspekt.py
- doc/obsidian_export_todo.md

Write-set:
- app/smart_konspekt.py
- tests/test_smart_konspekt.py
- scripts/generate_konspekt.py
- scripts/eval_konspekt.py
- app/config.py
- app/prompts/_impl.py
- app/provider.py
- doc/changelog.md

План:
1. Проверь targeted tests:
   .\.venv\Scripts\python.exe -m pytest tests\test_smart_konspekt.py tests\test_obsidian_export.py tests\test_ingestion_konspekt.py -q --tb=short
2. При наличии LM Studio выполни real-run:
   .\.venv\Scripts\python.exe scripts\generate_konspekt.py "ИИ Агенты/урок 1" --force
   .\.venv\Scripts\python.exe scripts\eval_konspekt.py "ИИ Агенты/урок 1" --golden "ИИ Агенты/урок 1 Введение в концепцию AI-агентов.md"
3. Прогони post-generation gate:
   .\.venv\Scripts\python.exe scripts\validate_smart_konspekt.py "data\ИИ Агенты\урок 1 Введение в концепцию AI-агентов.md" --expect-source-sha --strict
   .\scripts\validate_course_konspekts.ps1 -Course "ИИ Агенты"
4. По результатам eval/gate либо зафиксируй local fallback как достаточный, либо открой follow-up на качество.
5. Обнови doc/changelog.md.

Acceptance:
- app/smart_konspekt.py generates `data/<курс>/<лекция>.md`;
- no prompt logic outside app/prompts;
- no LLM construction outside app/provider.py;
- generated markdown passes `scripts/validate_smart_konspekt.py` or is explicitly marked as draft/failed;
- targeted tests stay green.
```
