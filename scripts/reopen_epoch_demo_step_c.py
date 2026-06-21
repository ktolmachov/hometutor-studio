#!/usr/bin/env python3
"""
Автоматический полный Step C (closed → ready) для пакета ``epoch-demo``.

Охват для smoke-пакета (``user_stories: []`` в registry):
  C.1  doc/backlog_registry.yaml — status, re_entry_condition, last_review;
       перед lint: прочие пакеты со статусом ``ready``/``wip`` переводятся в ``proposed``
       (инвариант Truth View «один активный»). Отключить: ``--no-demote-other-active``.
  C.2  doc/closed_iterations.md — пометка REOPENED в последнем заголовке ``### epoch-demo —``
       (секция «Индекс Эпох» для этого id не используется — строк не удаляем)
  C.3–C.5  не применяются (нет US под covered_by; CJM не сканируется)
  C.6  append в doc/changelog.md (идемпотентно по заголовку дня)
  доп. doc/current_task.md — шаблон под ready-пакет
  доп. archive/team_artifacts/epoch-demo/execution_contract.md — короткий чистый шаблон (сброс
       после прошлого закрытия / verification-append)
  доп. scripts/prompt_utils.py — удалить верхнеуровневую ``epoch_demo_placeholder_text``
       (демо после прошлого execution-smoke); убрать ``import uuid``, если он больше не нужен
  C.7  два вызова backlog_registry_lint.py --sync-from-index --write-sync (+ второй с --strict)

Не выполняет C.8 (git commit).

Usage:
  .\\.venv\\Scripts\\python.exe scripts/reopen_epoch_demo_step_c.py --reason "smoke post-agent"
  .\\.venv\\Scripts\\python.exe scripts/reopen_epoch_demo_step_c.py --reason "..." --dry-run

Exit codes:
  0 — уже ready/wip или переоткрытие выполнено и lint прошёл
  1 — lint завершился с ошибкой после правок
  2 — ошибка ввода / нет записи epoch-demo в registry

После перевода epoch-demo в ``ready`` по умолчанию все остальные ``items`` со статусом
``ready``/``wip`` получают ``proposed``, чтобы lint и roadmap_sync не падали на двух активных пакетах.
Восстановите статус реального backlog-пакета вручную после smoke при необходимости.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ID = "epoch-demo"
REGISTRY_PATH = ROOT / "doc" / "backlog_registry.yaml"
CLOSED_ITERATIONS_PATH = ROOT / "doc" / "closed_iterations.md"
CHANGELOG_PATH = ROOT / "doc" / "changelog.md"
CURRENT_TASK_PATH = ROOT / "doc" / "current_task.md"
EXEC_CONTRACT_PATH = ROOT / "archive" / "team_artifacts" / PACKAGE_ID / "execution_contract.md"
PROMPT_UTILS_PATH = ROOT / "scripts" / "prompt_utils.py"

_SCRIPTS = ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from print_reopen_package_workflow import load_registry_package_status  # noqa: E402
from script_stdio_utf8 import configure_stdio_utf8  # noqa: E402

CURRENT_TASK_TEMPLATE = """# TASK: epoch-demo (`ready`)

**SSoT:** запись `epoch-demo` в `doc/backlog_registry.yaml` (`status: ready`).

## Goal

Инфра-пакет smoke / верификации post-agent CLI для `epoch-demo` (scaffolding, не продуктовая фича).

## Write-set

По реестру `write_set_max: 1`; фактический write-set — из контракта исполнителя / `archive/team_artifacts/epoch-demo/` (например точечные правки `scripts/prompt_utils.py` или workflow-доков по DoD).

## DoD (из registry)

```bash
.\\.venv\\Scripts\\python.exe -m py_compile scripts/prompt_utils.py
```

## Артефакты и smoke

- `archive/team_artifacts/epoch-demo/`
- Post-agent smoke: `doc/team_workflow/archive/epoch_demo_post_agent_smoke.md` — там же префлайт и порядок до `run_autonomous.py` при `closed` (переоткрытие скриптом Step C или вручную по канону; `run_autonomous.py` пакет сам не переоткрывает).

## User stories

В реестре для пакета `user_stories: []` — отдельные US в индексе под этот `PACKAGE_ID` скрипт не переводит.
"""

EXEC_CONTRACT_TEMPLATE_BODY = """# epoch-demo execution contract

Шаблон после автоматического reopen (`scripts/reopen_epoch_demo_step_c.py`): предыдущий прогон и auto-append из `--post-agent` сброшены. При необходимости дополни текст по промпту `package` и точечным изменениям в `scripts/prompt_utils.py`.

## Pre-existing delivery evidence

- commit: {commit_sha}
- files: scripts/prompt_utils.py

Infra smoke (`epoch-demo`): целевой модуль уже доставлен в истории репозитория; типичный DoD — только ``py_compile`` без новых изменений в рабочем дереве.

evidence_inconclusive_allowed
"""


def _git_latest_touch_sha(root: Path, rel_path: str) -> str | None:
    """Latest commit touching ``rel_path`` (stable verification-only evidence for that file)."""
    try:
        proc = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", rel_path],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        if proc.returncode != 0:
            return None
        sha = (proc.stdout or "").strip()
        return sha[:40] if sha else None
    except OSError:
        return None


def _epoch_demo_evidence_commit_sha(root: Path) -> str | None:
    """SHA for evidence block (epoch-demo DoD targets ``scripts/prompt_utils.py``)."""
    return _git_latest_touch_sha(root, "scripts/prompt_utils.py")


def _execution_contract_body(commit_sha: str | None) -> str:
    sha_disp = commit_sha if commit_sha else "REPLACE_RUN_git_log_minus_1_scripts_prompt_utils_py"
    return EXEC_CONTRACT_TEMPLATE_BODY.format(commit_sha=sha_disp)


def _re_replace_item_status(yaml_text: str, item_id: str, new_status: str) -> str:
    """Replace the first ``status:`` line inside the ``items`` entry for ``item_id``."""
    lines = yaml_text.splitlines(keepends=True)
    in_item = False
    result: list[str] = []
    for line in lines:
        bare = line.rstrip("\n\r")
        if re.match(rf"\s*-\s+id:\s+{re.escape(item_id)}(?:\s+#.*)?$", bare):
            in_item = True
        elif in_item and re.match(r"\s*-\s+id:\s", bare):
            in_item = False
        if in_item and re.match(r"\s+status:\s+\S+", bare):
            new_bare = re.sub(r"(status:\s+)\S+", rf"\g<1>{new_status}", bare, count=1)
            eol = line[len(bare) :]
            line = new_bare + eol
            in_item = False
        result.append(line)
    return "".join(result)


def _iter_other_now_package_ids(registry_text: str, keep_id: str) -> list[str]:
    """Return ids (other than ``keep_id``) whose items[].status is ready or wip."""
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        return []
    try:
        data = yaml.safe_load(registry_text)
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    items = data.get("items") or []
    out: list[str] = []
    for entry in items:
        if not isinstance(entry, dict):
            continue
        pid = entry.get("id")
        if not pid or str(pid) == keep_id:
            continue
        st = str(entry.get("status", "")).strip().lower()
        if st in {"ready", "wip"}:
            out.append(str(pid))
    return sorted(set(out))


def _demote_other_now_packages(registry_text: str, keep_id: str) -> tuple[str, list[str]]:
    """Demote every ready/wip item except ``keep_id`` to ``proposed`` (Truth View singleton)."""
    ids = _iter_other_now_package_ids(registry_text, keep_id)
    text = registry_text
    for pid in ids:
        text = _re_replace_item_status(text, pid, "proposed")
    return text, ids


def _strip_epoch_demo_placeholder(text: str) -> tuple[str, bool]:
    """Удаляет верхнеуровневую ``def epoch_demo_placeholder_text``... если есть."""
    lines = text.splitlines(keepends=True)
    start: int | None = None
    for i, raw in enumerate(lines):
        stripped = raw.lstrip()
        if not stripped.startswith("def epoch_demo_placeholder_text"):
            continue
        if raw[:1] in ("\t", " "):
            continue
        start = i
        break
    if start is None:
        return text, False

    end = len(lines)
    for j in range(start + 1, len(lines)):
        raw = lines[j]
        if not raw.strip():
            continue
        if raw[0] in " \t#":
            continue
        end = j
        break

    new_text = "".join(lines[:start] + lines[end:])
    new_text = re.sub(r"\n{4,}\Z", "\n\n", new_text)
    return new_text, True


def _remove_uuid_import_if_unused(text: str) -> tuple[str, bool]:
    """Удаляет строку ``import uuid``, если ``uuid.`` больше не встречается."""
    if re.search(r"\buuid\.", text):
        return text, False
    out: list[str] = []
    changed = False
    for line in text.splitlines(keepends=True):
        if line.strip() == "import uuid":
            changed = True
            continue
        out.append(line)
    return "".join(out), changed


def _py_compile_prompt_utils() -> int:
    return subprocess.run(
        [sys.executable, "-m", "py_compile", str(PROMPT_UTILS_PATH)],
        cwd=ROOT,
    ).returncode


def _validate_today(s: str) -> str:
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", s):
        raise argparse.ArgumentTypeError("Use YYYY-MM-DD for --today")
    return s


def _yaml_escape_double_quoted(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _patch_registry_reopen(text: str, today: str, reason: str) -> tuple[str, bool]:
    """В блоке ``epoch-demo``: closed → ready, re_entry_condition, last_review."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    in_demo = False
    touched = False
    id_line = re.compile(r"^(\s*-\s+id:\s*)(\S+)(\s*(?:#.*)?)$")

    esc_reason = _yaml_escape_double_quoted(reason.strip())
    rec_line = f'    re_entry_condition: "audit {today}: {esc_reason}"\n'

    for line in lines:
        id_match = id_line.match(line.rstrip("\n"))
        if id_match:
            raw_id = id_match.group(2).split("#", 1)[0].strip()
            in_demo = raw_id == PACKAGE_ID

        if in_demo:
            if re.match(r"^\s+status:\s+closed\b", line):
                line = re.sub(r"\bclosed\b", "ready", line, count=1)
                touched = True
            elif re.match(r"^\s+re_entry_condition:\s*", line):
                line = rec_line
                touched = True
            elif re.match(r"^\s+last_review:\s*", line):
                line = f"    last_review: {today}\n"
                touched = True

        out.append(line)

    return "".join(out), touched


def _patch_closed_iterations(text: str, today: str) -> tuple[str, bool]:
    lines = text.splitlines(keepends=True)
    idxs = [i for i, ln in enumerate(lines) if ln.startswith("### epoch-demo —")]
    if not idxs:
        return text, False
    i = idxs[-1]
    raw = lines[i].rstrip("\n")
    if today in raw:
        return text, False
    if "REOPENED" in raw:
        lines[i] = raw + f", {today}\n"
    else:
        lines[i] = raw + f" ⚠️ REOPENED {today}\n"
    return "".join(lines), True


def _append_changelog(text: str, today: str, reason: str) -> tuple[str, bool]:
    marker = f"## Reopened: epoch-demo ({today})"
    if marker in text:
        return text, False
    block = f"""

{marker}

- **Reason:** {reason.strip()}
- **Affected US:** нет привязок `covered_by: epoch-demo` в `doc/user_stories_index.json` (скрипт индекс не меняет).
- **Action:** автоматический Step C (`scripts/reopen_epoch_demo_step_c.py`): `doc/backlog_registry.yaml` closed→ready; при необходимости прочие пакеты `ready`/`wip`→`proposed` (инвариант Truth View); пометка в `doc/closed_iterations.md` (Recent); сброс `archive/team_artifacts/epoch-demo/execution_contract.md`; удаление демо-функции `epoch_demo_placeholder_text` (и неиспользуемого `import uuid`) в `scripts/prompt_utils.py`; `doc/current_task.md`; два прогона `backlog_registry_lint.py --sync-from-index --write-sync` (второй с `--strict`).
- **CJM:** `doc/cjm.md` не изменялся (для токена пакета `epoch-demo` строк обычно нет).
"""
    out = text.rstrip() + block
    if not out.endswith("\n"):
        out += "\n"
    return out + "\n", True


def _run_lint(strict_second: bool = True) -> int:
    exe = sys.executable
    base = [
        exe,
        str(ROOT / "scripts/backlog_registry_lint.py"),
        "--sync-from-index",
        "--write-sync",
    ]
    r1 = subprocess.run(base, cwd=ROOT)
    if r1.returncode != 0:
        return r1.returncode
    if not strict_second:
        return 0
    r2 = subprocess.run([*base, "--strict"], cwd=ROOT)
    return r2.returncode


def main() -> int:
    configure_stdio_utf8()
    ap = argparse.ArgumentParser(
        description="Apply automated Step C reopen for epoch-demo (infra smoke package).",
    )
    ap.add_argument(
        "--reason",
        required=True,
        help="REASON для re_entry_condition и changelog (одна строка)",
    )
    ap.add_argument(
        "--today",
        type=_validate_today,
        default=None,
        metavar="YYYY-MM-DD",
        help="Дата полей Step C (по умолчанию локальная дата)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Только печать плана; файлы не трогать",
    )
    ap.add_argument(
        "--no-strict-lint",
        action="store_true",
        help="Второй прогон lint без --strict",
    )
    ap.add_argument(
        "--no-demote-other-active",
        action="store_true",
        help="Не переводить прочие пакеты ready/wip→proposed (lint может упасть при втором активном)",
    )
    args = ap.parse_args()
    today = args.today or date.today().isoformat()

    try:
        status = load_registry_package_status(PACKAGE_ID)
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if status is None:
        print(f"ERROR: package '{PACKAGE_ID}' not in {REGISTRY_PATH}", file=sys.stderr)
        return 2

    if status in ("ready", "wip"):
        print(f"noop: registry status is already {status!r} — Step C reopen not needed.")
        return 0

    if status != "closed":
        print(
            f"ERROR: expected status 'closed' for automated reopen, got {status!r}",
            file=sys.stderr,
        )
        return 2

    reg_before = REGISTRY_PATH.read_text(encoding="utf-8")
    reg_after, reg_changed = _patch_registry_reopen(reg_before, today, args.reason)
    if not reg_changed:
        print(
            "ERROR: registry patch did not apply (epoch-demo block missing fields?)",
            file=sys.stderr,
        )
        return 2

    demoted: list[str] = []
    if not args.no_demote_other_active:
        reg_after, demoted = _demote_other_now_packages(reg_after, PACKAGE_ID)
    ci_before = CLOSED_ITERATIONS_PATH.read_text(encoding="utf-8")
    ci_after, ci_changed = _patch_closed_iterations(ci_before, today)

    cl_before = CHANGELOG_PATH.read_text(encoding="utf-8")
    cl_after, cl_changed = _append_changelog(cl_before, today, args.reason)

    if args.dry_run:
        print("DRY-RUN: would write:")
        print(f"  - {REGISTRY_PATH.relative_to(ROOT)} (closed→ready + dates)")
        if not args.no_demote_other_active:
            if demoted:
                print(f"  - demote other active → proposed: {demoted}")
            else:
                print("  - no other ready/wip packages to demote")
        print(f"  - {CLOSED_ITERATIONS_PATH.relative_to(ROOT)} (append REOPENED {today})" if ci_changed else f"  - {CLOSED_ITERATIONS_PATH.relative_to(ROOT)} (unchanged)")
        print(f"  - {CHANGELOG_PATH.relative_to(ROOT)} (append reopen block)" if cl_changed else f"  - {CHANGELOG_PATH.relative_to(ROOT)} (already has header)")
        print(f"  - {CURRENT_TASK_PATH.relative_to(ROOT)} (template)")
        print(f"  - {EXEC_CONTRACT_PATH.relative_to(ROOT)} (clean template + verification-only evidence)")
        print(f"  - {PROMPT_UTILS_PATH.relative_to(ROOT)} (strip epoch_demo_placeholder_text + optional uuid import)")
        print("  - py_compile scripts/prompt_utils.py")
        print("  - backlog_registry_lint.py ×2")
        return 0

    REGISTRY_PATH.write_text(reg_after, encoding="utf-8")
    if ci_changed:
        CLOSED_ITERATIONS_PATH.write_text(ci_after, encoding="utf-8")
    if cl_changed:
        CHANGELOG_PATH.write_text(cl_after, encoding="utf-8")
    CURRENT_TASK_PATH.write_text(CURRENT_TASK_TEMPLATE, encoding="utf-8")

    touch_sha = _epoch_demo_evidence_commit_sha(ROOT)
    if not touch_sha:
        print(
            "WARN: git log for scripts/prompt_utils.py failed — verification-only evidence uses placeholder SHA; "
            "post-agent may exit 6 until you fix archive/team_artifacts/epoch-demo/execution_contract.md.",
            file=sys.stderr,
        )

    EXEC_CONTRACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXEC_CONTRACT_PATH.write_text(_execution_contract_body(touch_sha), encoding="utf-8")

    pu_before = PROMPT_UTILS_PATH.read_text(encoding="utf-8")
    pu_after, pu_fn = _strip_epoch_demo_placeholder(pu_before)
    pu_after, pu_uuid = _remove_uuid_import_if_unused(pu_after)
    if pu_fn or pu_uuid:
        PROMPT_UTILS_PATH.write_text(pu_after, encoding="utf-8")
        compile_rc = _py_compile_prompt_utils()
        if compile_rc != 0:
            print("ERROR: py_compile scripts/prompt_utils.py failed after strip", file=sys.stderr)
            return 2
        if pu_fn:
            print("Removed epoch_demo_placeholder_text() from scripts/prompt_utils.py.")
        if pu_uuid:
            print("Removed unused import uuid from scripts/prompt_utils.py.")

    print(f"Applied Step C reopen for {PACKAGE_ID} (today={today}).")
    if demoted:
        joined = ", ".join(demoted)
        print(f"Truth View: demoted ready/wip→proposed for {joined} (restore manually after smoke if needed).")
    print(f"Wrote clean template {EXEC_CONTRACT_PATH.relative_to(ROOT)}.")
    if not ci_changed:
        print(f"NOTE: no '### epoch-demo —' heading patched in {CLOSED_ITERATIONS_PATH.name}")
    if not cl_changed:
        print(f"NOTE: changelog already contained reopen header for {today}")

    lint_rc = _run_lint(strict_second=not args.no_strict_lint)
    if lint_rc != 0:
        print(f"ERROR: backlog_registry_lint.py exited {lint_rc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
