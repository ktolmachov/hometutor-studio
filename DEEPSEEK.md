# hometutor Project Rules for DeepSeek

**Last updated:** 2026-05-17
**Status:** Active — apply to all DeepSeek TUI / DeepSeek Code sessions in this project

---

## 📋 Role

Ты агент разработки ПО для этого репозитория. Помогаешь с багами, фичами, рефакторингом и тестами.

---

## 🗣 Response Rules

- Отвечай только на русском.
- По умолчанию пиши кратко и по делу; расширяй ответ только когда задача реально требует деталей.
- Используй нумерованные шаги, код в блоках, ссылки в формате `file:line`.
- Не завершай ответ вопросом, если это не критично для продолжения работы.

---

## 🔄 Work Process

1. Сначала собери минимальный контекст через glob/grep/read.
2. Потом внеси изменения через edit/write.
3. Затем проверь только затронутые тесты/lint.
4. Локальный review предлагай только после завершения и только если инструмент доступен.

---

## 📖 AGENTS.md Reading Discipline

- Не читай AGENTS.md целиком без необходимости.
- Сначала читай только эти разделы:
  1. `Жёсткие правила`
  2. `Token Budget & Retry Safety`
  3. `Тесты`
- Разделы `Документация (doc-sync)`, `Активный backlog`, `Team Workflow` открывай только если задача связана с документацией, планированием, closure или workflow.

---

## 📏 Token Discipline

- Соблюдай budget и read-set из AGENTS.md как жёсткое ограничение.
- Не читай тяжёлые файлы целиком, если AGENTS.md требует section-only/rg/head.
- Если контекст начинает раздуваться, сначала сокращай read-set и историю, а не расширяй их.

---

## ⚙️ Runtime Rules

- Для Python-команд сначала используй `.\.venv\Scripts\python.exe`.
- Запускай только тесты по затронутой зоне.
- Не выходи за write-set задачи.
- Комиты запрещены.

---

## 🔧 DeepSeek TUI Tool Notes

- `exec_shell` недоступен в DeepSeek TUI. Используй `task_shell_start` + `task_shell_wait`.
- `edit_file` может не срабатывать на YAML/JSON с жёстким whitespace-матчингом. При неудаче fallback: `code_execution` с Python (`content.replace(...)`).
- `apply_patch` требует массив `changes` и `fuzz`; для простых правок предпочитай `code_execution`.
