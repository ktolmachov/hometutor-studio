# Адаптер: OpenAI Codex CLI

Файл читается `generate_orchestration_prompt.md` в Phase 3.
Содержит значения плейсхолдеров шаблона для Codex CLI.

---

## Значения плейсхолдеров

```yaml
MAX_PARALLEL: 1

AGENT_SPAWN: |
  Codex CLI не поддерживает spawn подагентов в одном вызове.
  Роли выполняются последовательно в одном потоке.
  Переключение роли — явным текстом в промпте:
    "Act as <Role>. Read doc/team_workflow/<role>.md and follow Prompt N."
  Альтернатива для изоляции: /agent <name> (создаёт отдельный thread).

PARALLEL_SYNTAX: |
  [SEQUENTIAL — Codex CLI не поддерживает параллельные агенты нативно]
  Step 3 разбивается на:
    STEP 3a — Architect  (выполняется первым)
    STEP 3b — Designer   (выполняется после Architect)
  Преимущество: Designer видит write-set контракт Architect'а.
  Для параллелизма: использовать Agents SDK wrapper (см. адаптер, Приложение).

READ_FILE: |
  Shell команда через Shell Tool MCP:
    cat path/to/file.md
  Для частичного чтения:
    head -N path/to/file.md
    tail -N path/to/file.md
    grep -n "pattern" path/to/file.md | head -50
    sed -n 'N,Mp' path/to/file.md

WRITE_FILE: |
  Shell heredoc через Shell Tool MCP:
    cat > path/to/artifact.md << 'ARTIFACT_EOF'
    [content]
    ARTIFACT_EOF
  НЕ использовать echo — теряются переносы строк и спецсимволы.
  mkdir -p перед записью если директория новая.

RUN_CMD: |
  Shell Tool MCP (sandboxed bash):
    [команда]
  Примеры:
    python -m pytest tests/test_flashcard_service.py -v 2>&1
    git diff --name-only HEAD~5..HEAD
    grep -n "pattern" app/module.py
```

---

## Step 3: последовательный запуск (3a → 3b)

```text
─── STEP 3a — Architect ──────────────────────────────────────────
Act as Architect. Read doc/team_workflow/architect.md.

cat archive/team_artifacts/{{PACKAGE_ID}}/2_analyst_spec.md
cat doc/conventions.md
[... остальные файлы ...]

Execute Architect Prompt 1. Split into sub-packages.
Include copy-paste developer prompts for each.

cat > archive/team_artifacts/{{PACKAGE_ID}}/3_architect_contract.md << 'EOF'
[output]
EOF

─── STEP 3b — Designer ───────────────────────────────────────────
Act as Designer. Read doc/team_workflow/designer.md.

cat archive/team_artifacts/{{PACKAGE_ID}}/2_analyst_spec.md
cat archive/team_artifacts/{{PACKAGE_ID}}/3_architect_contract.md  ← write-set
cat app/ui/<relevant>.py
[... остальные файлы ...]

Execute Designer Prompt 1.
Note: Designer runs AFTER Architect and can reference its write-set.
This is the sequential trade-off — Designer benefits from seeing the contract.

cat > archive/team_artifacts/{{PACKAGE_ID}}/4_designer_ui_spec.md << 'EOF'
[output]
EOF
```

---

## Специфика передачи артефактов

Все роли работают в одном thread — контекст **общий**.
Артефакты передаются через FS: `cat > file` → `cat file`.
Не нужно вставлять содержимое в промпт руками — следующая роль
читает через `cat`.

```bash
# После Step 1 (PO):
cat archive/team_artifacts/{{PACKAGE_ID}}/1_po_package.md
# Step 2 (Analyst) видит его через cat в своих инструкциях
```

---

## AGENTS.md (автоматически подхватывается Codex)

`AGENTS.md` в корне проекта уже создан.
Codex CLI читает его перед каждым сеансом.
Содержит жёсткие правила проекта (conventions, write-set, тесты).

---

## Обработка FAIL вердикта

```bash
# После Step 5 (Tester):
VERDICT=$(grep "VERDICT:" archive/team_artifacts/{{PACKAGE_ID}}/6a_tester_sp1.md)
echo "Verdict: $VERDICT"

# PASS → continue
# CONDITIONAL PASS → show conditions, ask user
# FAIL → show blocker, ask user:
#   "Blocker found. Re-run Developer with fix? (y/n)"
```

---

## Closure (Step 8): shell-команды

```bash
# Обновить doc/backlog_registry.yaml и регенерировать tasklist.md:
DATE=$(date +%Y-%m-%d)
# (Ручное редактирование или sed — зависит от структуры файла)

# Список артефактов:
ls -lh archive/team_artifacts/{{PACKAGE_ID}}/

# Изменённые файлы:
git diff --name-only HEAD~10..HEAD | sort -u
```

---

## Ограничения Codex CLI

| Ограничение | Влияние на оркестрацию |
|------------|------------------------|
| Нет нативных параллельных агентов | Step 3 — последовательный |
| Один активный thread | Все роли в одном контексте |
| Weekly quota по плану | Длинный pipeline может упереться в лимит |
| Shell sandbox | Некоторые системные команды могут быть ограничены |

---

## Приложение: параллельный Step 3 через Agents SDK

Если параллелизм Step 3 критичен, вынести в отдельный Python скрипт:

```python
# scripts/parallel_step3.py
# Запуск: python scripts/parallel_step3.py --package {{PACKAGE_ID}}

import asyncio, argparse
from openai import AsyncOpenAI
from pathlib import Path

client = AsyncOpenAI()

async def run_role(role: str, instructions_file: str,
                   context_files: list[str], save_to: str) -> None:
    instructions = Path(instructions_file).read_text()
    context = "\n\n".join(
        f"=== {f} ===\n{Path(f).read_text()}" for f in context_files
    )
    r = await client.responses.create(
        model="codex-mini-latest",
        instructions=instructions,
        input=context
    )
    Path(save_to).parent.mkdir(parents=True, exist_ok=True)
    Path(save_to).write_text(r.output_text)
    print(f"✓ {role}: saved to {save_to}")

async def main(package_id: str):
    artifacts = f"archive/team_artifacts/{package_id}"
    spec = f"{artifacts}/2_analyst_spec.md"

    await asyncio.gather(
        run_role(
            "Architect",
            "doc/team_workflow/architect.md",
            [spec, "doc/conventions.md", "doc/conventions_architecture.md",
             "doc/adr.md", "app/flashcard_service.py", "app/user_state.py"],
            f"{artifacts}/3_architect_contract.md"
        ),
        run_role(
            "Designer",
            "doc/team_workflow/designer.md",
            [spec, "doc/cjm.md", "app/ui/flashcards_ui.py",
             "app/ui/home_hub.py", "app/ui_theme.css"],
            f"{artifacts}/4_designer_ui_spec.md"
        )
    )
    print(f"Step 3 parallel complete for {package_id}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True)
    asyncio.run(main(parser.parse_args().package))
```
