# Промпт: добавить новый контрактный prompt в архив

Скопируйте блок ниже в новый чат с агентом (или выполните сами). Один запрос = одна запись в архиве.

---

```text
Goal: add one execution prompt as a separate archive file.

Target folder:
archive/agent_prompts/

Input prompt to archive:
<paste the full execution prompt here>

Rules:
- Do not paste the execution prompt into ARCHIVE_ADD_PROMPT.md.
- Do not modify ARCHIVE_ADD_PROMPT.md unless explicitly asked.
- Create a new markdown file under archive/agent_prompts/.
- Use filename format:
  <package_id_lower_snake>_<short_slug>_YYYY-MM-DD.md
  Example: e10_4_b_progress_tab_2026-04-12.md
- If a file for the same package/date already exists, do not overwrite it. Create a distinct variant slug, e.g.:
  e10_4_a_concept_graduation_contract_2026-04-11.md

New file structure:
- H1:
  # Архив: контрактный prompt — <Package> (<short human title>)
- Metadata table:
  | Поле | Значение |
  |------|----------|
  | Пакет | **<Package>** |
  | Дата добавления в архив | YYYY-MM-DD |
  | User story | <US-* or "—"> |
  | Источник | planning session → execution contract |
- Then:
  Текст ниже можно копировать в новый чат агента как единый запрос.
- Horizontal rule
- Full prompt inside one fenced ```text block.

Index update:
- Append one row to archive/agent_prompts/README.md:
  | YYYY-MM-DD | <Package> | <short description> | [<filename>](<filename>) |

Do not touch:
- app/
- tests/
- unrelated doc/ files
- archive/agent_prompts/ARCHIVE_ADD_PROMPT.md

DoD:
- New .md archive file exists in archive/agent_prompts/
- README index has exactly one new row linking to it
- Existing archive files are not overwritten
- ARCHIVE_ADD_PROMPT.md remains unchanged

Output:
- New archive file path
- README index update summary
- Any duplicate/variant decision made
```

---

## Имя файла (кратко)

| Часть | Пример |
|-------|--------|
| Пакет | `e10_4_b`, `e11_a` |
| Короткий slug | `progress_tab`, `guided_cta` |
| Дата | `2026-04-12` (день фиксации в архиве) |

Итог: `e10_4_b_progress_tab_2026-04-12.md`
