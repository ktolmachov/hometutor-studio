#!/usr/bin/env python3
"""
Smart Demo Doc generator.

Читает YAML-манифесты из ``doc/scenarios/*.yaml`` и соответствующие им
скриншоты / ``meta.json`` из ``doc/screenshots/<scenario_id>/``, собирает
читабельный markdown-документ ``doc/quickstart_demo.md`` с раскадровкой
каждого сценария, подписями, нарративом и ссылкой на каталог сценариев.

Использование:

    python scripts/generate_demo_doc.py
    python scripts/generate_demo_doc.py --scenarios-dir doc/scenarios \\
        --screenshots-dir doc/screenshots --output doc/quickstart_demo.md

Перед записью `doc/quickstart_demo.md` пересобирает ``doc/screenshots/final/``
(копия актуального прогона), ссылки в markdown ведут в ``final/``.

Требования:
    - PyYAML (обычно уже установлен; fallback: minimal YAML parser)

Как работает ссылочная модель:
    YAML (source of truth) ──┐
                             ├─► markdown
    screenshots/meta.json ───┘

Если у сценария нет скриншотов (demo-тест не прогонялся),
раздел всё равно попадает в документ с плашкой «ещё не снято»,
чтобы было видно где дырки.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    import yaml  # type: ignore

    _HAVE_YAML = True
except ImportError:  # pragma: no cover - fallback branch
    yaml = None  # type: ignore
    _HAVE_YAML = False


DEFAULT_SCENARIOS = Path("doc/scenarios")
DEFAULT_SCREENSHOTS = Path("doc/screenshots")
DEFAULT_OUTPUT = Path("doc/quickstart_demo.md")
# Стабильные относительные пути в markdown: `doc/screenshots/final/<scenario_id>/…`
FINAL_DIR = Path("doc/screenshots/final")
FINAL_PREFIX = "screenshots/final"
DEFAULT_SCENARIO_ORDER = [
    "scenario_01",
    "scenario_02",
    "scenario_03",
    "scenario_04",
    "scenario_05",
    "scenario_06",
    "scenario_07",
    "scenario_08",
    "scenario_09",
    "scenario_10",
    "scenario_11",
    "scenario_12",
    "scenario_13",
    "scenario_14",
    "scenario_15",
    "scenario_16",
    "scenario_17",
    "scenario_18",
    "scenario_19",
    "scenario_20",
    "scenario_21",
    "scenario_22",
    "scenario_23",
    "scenario_24",
    "scenario_25",
    "scenario_26",
    "scenario_27",
    "scenario_28",
    "scenario_29",
    "scenario_30",
    "scenario_31",
    "scenario_32",
    "scenario_33",
    "scenario_34",
    "scenario_35",
    "scenario_36",
    "scenario_37",
    "scenario_38",
]
_SCENARIO_ORDER_INDEX = {scenario_id: i for i, scenario_id in enumerate(DEFAULT_SCENARIO_ORDER)}


def _find_runtime_repo_root() -> Path | None:
    """Discover sibling hometutor runtime repo from script location."""
    candidate = Path(__file__).resolve().parents[1].parent / "hometutor"
    if candidate.is_dir() and (candidate / ".git").is_dir():
        return candidate.resolve()
    return None


def _run_git(repo_root: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, check=False,
            cwd=str(repo_root),
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _compute_freshness(repo_root: Path | None, session_meta: dict | None) -> dict[str, Any]:
    """Return {capture_sha, current_sha, gap} or all-unknown on failure."""
    info: dict[str, Any] = {"capture_sha": "unknown", "current_sha": "unknown", "gap": -1}
    if repo_root is None:
        return info

    try:
        current = _run_git(repo_root, ["rev-parse", "--short", "HEAD"])
        if current:
            info["current_sha"] = current

        capture_full = ""
        capture_short = ""

        if session_meta and session_meta.get("started_at"):
            started = session_meta["started_at"]
            full = _run_git(repo_root, [
                "log", "--before", str(started),
                "--format=%H", "--max-count=1",
            ])
            if full:
                capture_full = full
                capture_short = _run_git(repo_root, ["rev-parse", "--short", full])

        if not capture_full:
            for candidate in [
                ["log", "--format=%H", "--diff-filter=A", "--reverse",
                 "--", "docs/screenshots/final/scenario_01/"],
                ["log", "--format=%H", "--diff-filter=A", "--reverse",
                 "--", "docs/screenshots/final/"],
            ]:
                output = _run_git(repo_root, candidate)
                if output:
                    first = output.splitlines()[0].strip()
                    if first:
                        capture_full = first
                        capture_short = _run_git(repo_root, ["rev-parse", "--short", first])
                        break

        if not capture_full:
            full = _run_git(repo_root, ["rev-list", "--max-parents=0", "HEAD"])
            if full:
                capture_full = full
                capture_short = _run_git(repo_root, ["rev-parse", "--short", full])

        if capture_full:
            info["capture_sha"] = capture_short if capture_short else capture_full[:10]
            if current:
                gap_str = _run_git(repo_root, [
                    "rev-list", "--count", f"{capture_full}..HEAD",
                ])
                try:
                    info["gap"] = int(gap_str)
                except (ValueError, TypeError):
                    pass
    except Exception:  # noqa: BLE001
        pass

    return info


def _path_is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return path.resolve() == parent.resolve()


_RUN_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _resolve_screenshots_dir(requested: Path) -> Path:
    """Согласовано с `validate_demo_contract.py` для default `doc/screenshots`."""
    if requested != DEFAULT_SCREENSHOTS:
        return requested
    run = (os.environ.get("DEMO_SHOT_RUN") or "").strip()
    if run and _RUN_DIR_RE.match(run) and (DEFAULT_SCREENSHOTS / run).is_dir():
        return DEFAULT_SCREENSHOTS / run
    if (DEFAULT_SCREENSHOTS / "scenario_01").is_dir() or (DEFAULT_SCREENSHOTS / "scenario_02").is_dir():
        return DEFAULT_SCREENSHOTS
    dated = sorted(
        (p for p in DEFAULT_SCREENSHOTS.iterdir() if p.is_dir() and _RUN_DIR_RE.match(p.name)),
        key=lambda p: p.name,
    )
    if dated:
        return dated[-1]
    return requested


def _rel_prefix_to_doc(screenshots_dir: Path) -> str:
    """Префикс ссылок в `doc/quickstart_demo.md` (от каталога `doc/`)."""
    try:
        return screenshots_dir.resolve().relative_to(Path("doc").resolve()).as_posix()
    except ValueError:
        return "screenshots"


def _sync_run_dir_to_final(
    resolved: Path, *, no_sync: bool
) -> tuple[Path, str]:
    """
    Пересобирает `doc/screenshots/final/`: копия актуального прогона
    (папка `…/doc/screenshots/<RUN>/` с `scenario_XX/`, либо плоская вёрстка
    `scenario_XX` прямо в `doc/screenshots`).
    Возвращает (каталог_для_чтения_кадров, markdown_prefix).
    """
    root = Path("doc/screenshots")

    if no_sync:
        if FINAL_DIR.is_dir() and any(
            c.is_dir() and c.name.startswith("scenario_") for c in FINAL_DIR.iterdir()
        ):
            return FINAL_DIR, FINAL_PREFIX
        return resolved, _rel_prefix_to_doc(resolved)

    if not _path_is_under(resolved, root) and not resolved.resolve() == root.resolve():
        return resolved, _rel_prefix_to_doc(resolved)
    if resolved.resolve() == FINAL_DIR.resolve():
        return resolved, FINAL_PREFIX

    if FINAL_DIR.exists():
        shutil.rmtree(FINAL_DIR, ignore_errors=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)

    def is_scenario_dir(p: Path) -> bool:
        return p.is_dir() and p.name.startswith("scenario_")

    copied = False
    if _RUN_DIR_RE.match(resolved.name):
        for child in sorted(resolved.iterdir()):
            if is_scenario_dir(child):
                shutil.copytree(child, FINAL_DIR / child.name)
                copied = True
    elif resolved.resolve() == root.resolve():
        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.name == "final":
                continue
            if _RUN_DIR_RE.match(child.name):
                continue
            if is_scenario_dir(child):
                shutil.copytree(child, FINAL_DIR / child.name)
                copied = True
    else:
        for child in sorted(resolved.iterdir()):
            if is_scenario_dir(child):
                shutil.copytree(child, FINAL_DIR / child.name)
                copied = True

    if copied:
        return FINAL_DIR, FINAL_PREFIX
    return resolved, _rel_prefix_to_doc(resolved)


@dataclass
class ShotSpec:
    slug: str
    caption: str = ""
    narration: str = ""
    duration_sec: int | None = None


@dataclass
class ScreenshotMeta:
    file: str
    caption: str | None = None
    narration: str | None = None
    taken_at: str | None = None


@dataclass
class ScenarioSpec:
    id: str
    title: str
    level: str = ""
    persona: str = ""
    duration_min: int | None = None
    why: str = ""
    wow_moment: str = ""
    takeaway: str = ""
    scenario_link: str = ""
    shots: list[ShotSpec] = field(default_factory=list)
    requires: dict[str, Any] = field(default_factory=dict)
    manifest_path: Path | None = None
    captured: list[ScreenshotMeta] = field(default_factory=list)
    session_meta: dict[str, Any] | None = None


def _simple_yaml_load(text: str) -> dict[str, Any]:
    """
    Крайне простой fallback YAML-парсер: поддерживает только уровень
    структуры, который мы используем в манифестах (ключ-значение,
    блочный скаляр с ``|``, список под ключом ``shots``). При отсутствии
    PyYAML этот парсер позволяет сгенерировать документ без доп. зависимостей.
    """
    root: dict[str, Any] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        indent = len(raw) - len(raw.lstrip(" "))

        if indent == 0 and stripped.endswith(":") and stripped != "shots:":
            key = stripped[:-1].strip()
            # Block scalar with | on the next line or inline?
            # Collect nested map until dedent.
            block: dict[str, Any] = {}
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if not nxt.strip() or nxt.strip().startswith("#"):
                    i += 1
                    continue
                n_indent = len(nxt) - len(nxt.lstrip(" "))
                if n_indent == 0:
                    break
                sub = nxt.strip()
                if ": " in sub:
                    k, v = sub.split(": ", 1)
                    block[k.strip()] = v.strip().strip('"').strip("'")
                i += 1
            root[key] = block
            continue

        if indent == 0 and ": " in stripped:
            key, value = stripped.split(": ", 1)
            key = key.strip()
            value = value.strip()
            if value == "|":
                # Block scalar
                buf: list[str] = []
                i += 1
                while i < len(lines):
                    nxt = lines[i]
                    if not nxt.strip() and (i + 1 >= len(lines) or not lines[i + 1].startswith(" ")):
                        break
                    if nxt and not nxt.startswith(" ") and nxt.strip():
                        break
                    buf.append(nxt[2:] if nxt.startswith("  ") else nxt.strip())
                    i += 1
                root[key] = "\n".join(buf).strip()
                continue
            root[key] = value.strip('"').strip("'")
            i += 1
            continue

        if stripped == "shots:":
            shots: list[dict[str, Any]] = []
            i += 1
            current: dict[str, Any] | None = None
            while i < len(lines):
                nxt = lines[i]
                if not nxt.strip():
                    i += 1
                    continue
                nxt_stripped = nxt.strip()
                n_indent = len(nxt) - len(nxt.lstrip(" "))
                if n_indent == 0 and nxt_stripped.endswith(":"):
                    break
                if nxt_stripped.startswith("- "):
                    if current is not None:
                        shots.append(current)
                    current = {}
                    first = nxt_stripped[2:]
                    if ": " in first:
                        k, v = first.split(": ", 1)
                        current[k.strip()] = v.strip().strip('"').strip("'")
                elif ": " in nxt_stripped and current is not None:
                    k, v = nxt_stripped.split(": ", 1)
                    current[k.strip()] = v.strip().strip('"').strip("'")
                i += 1
            if current is not None:
                shots.append(current)
            root["shots"] = shots
            continue

        i += 1
    return root


def _load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if _HAVE_YAML:
        return yaml.safe_load(text) or {}
    return _simple_yaml_load(text)


def load_scenarios(scenarios_dir: Path) -> list[ScenarioSpec]:
    scenarios: list[ScenarioSpec] = []
    for yaml_path in sorted(scenarios_dir.glob("scenario_*.yaml")):
        raw = _load_yaml(yaml_path)
        shots_raw = raw.get("shots") or []
        shots = [
            ShotSpec(
                slug=str(s.get("slug", "")),
                caption=str(s.get("caption", "")),
                narration=str(s.get("narration", "")),
                duration_sec=_to_int(s.get("duration_sec")),
            )
            for s in shots_raw
            if s.get("slug")
        ]
        scenarios.append(
            ScenarioSpec(
                id=str(raw.get("id", yaml_path.stem)),
                title=str(raw.get("title", yaml_path.stem)),
                level=str(raw.get("level", "")),
                persona=str(raw.get("persona", "")),
                duration_min=_to_int(raw.get("duration_min")),
                why=str(raw.get("why", "")).strip(),
                wow_moment=str(raw.get("wow_moment", "")).strip(),
                takeaway=str(raw.get("takeaway", "")).strip(),
                scenario_link=str(raw.get("scenario_link", "")),
                shots=shots,
                requires=raw.get("requires") or {},
                manifest_path=yaml_path,
            )
        )
    return sorted(scenarios, key=_scenario_sort_key)


def _scenario_sort_key(scenario: ScenarioSpec) -> tuple[int, str]:
    known_pos = _SCENARIO_ORDER_INDEX.get(scenario.id)
    if known_pos is not None:
        return known_pos, scenario.id
    return len(DEFAULT_SCENARIO_ORDER), scenario.id


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def enrich_with_screenshots(
    scenario: ScenarioSpec, screenshots_dir: Path
) -> ScenarioSpec:
    scn_dir = screenshots_dir / scenario.id
    if not scn_dir.exists():
        return scenario

    meta_file = scn_dir / "meta.json"
    if meta_file.exists():
        try:
            raw = json.loads(meta_file.read_text(encoding="utf-8"))
            scenario.session_meta = raw
            for entry in raw.get("shots", []):
                scenario.captured.append(
                    ScreenshotMeta(
                        file=str(entry.get("file", "")),
                        caption=entry.get("caption"),
                        narration=entry.get("narration"),
                        taken_at=entry.get("taken_at"),
                    )
                )
            return scenario
        except json.JSONDecodeError:
            pass

    # Fallback: сканируем PNG в алфавитном порядке (они сами начинаются с 01_, 02_...).
    for png in sorted(scn_dir.glob("*.png")):
        scenario.captured.append(ScreenshotMeta(file=png.name))
    return scenario


def _freshness_badge(info: dict[str, Any]) -> str:
    if info["capture_sha"] == "unknown":
        return ""
    return (
        f"> **Freshness:** снято на HEAD `{info['capture_sha']}` · "
        f"текущий HEAD `{info['current_sha']}` · "
        f"freshness gap `{info['gap']}` коммитов.\n"
    )


_FRESHNESS_OVERRIDES: dict[str, str] = {}


def _register_freshness_note(scenario_id: str, note: str) -> None:
    _FRESHNESS_OVERRIDES[scenario_id] = note


def _freshness_footer(scenario_id: str) -> str:
    note = _FRESHNESS_OVERRIDES.get(scenario_id)
    if note:
        return f"\n> **{note}**\n"
    return ""


def render_document(
    scenarios: list[ScenarioSpec],
    screenshots_dir: Path,
    link_prefix: str,
    freshness: dict[str, Any] | None = None,
    *,
    docs_tree: str = "doc",
) -> str:
    """Build quickstart_demo markdown.

    ``docs_tree`` is the repo-relative docs root label used in captions:
    studio uses ``doc/``, runtime hometutor uses ``docs/``.
    """
    sprefix = link_prefix
    tree = (docs_tree or "doc").strip().strip("/") or "doc"
    lines: list[str] = []
    lines.append("# Smart Demo — автоматически снятые кадры сценариев\n")

    if freshness:
        lines.append(_freshness_badge(freshness))

    if tree == "docs":
        scenarios_hint = (
            "YAML-манифесты — source-of-truth в `hometutor-studio/doc/scenarios/*.yaml`; "
            f"кадры в runtime — `{tree}/{sprefix}/<scenario_id>/`"
        )
        rebuild_hint = (
            f"перед публикацией генератор синхронизирует `final/`; "
            f"**активные ссылки на картинки** — относительные `{sprefix}/…`. "
            "Не правь вручную — `python scripts/generate_demo_doc.py` из studio."
        )
    else:
        scenarios_hint = (
            f"YAML-манифесты `{tree}/scenarios/*.yaml` и скриншоты "
            f"из `{tree}/{sprefix}/<scenario_id>/` после `npm run test:e2e:demo`"
        )
        rebuild_hint = (
            f"(съём в `{tree}/screenshots/<RUN>/`; перед этим генератор пересобирает "
            f"`{tree}/screenshots/final/`, **ссылки ведут в `final/`**). "
            "Не правь вручную — манифесты и `python scripts/generate_demo_doc.py`."
        )

    lines.append(
        f"> Документ собран из {scenarios_hint}. {rebuild_hint}\n"
    )
    lines.append("## О чём этот документ\n")
    lines.append(
        "Каждый сценарий здесь — это последовательность **реальных кадров** "
        "из Streamlit UI, снятых Playwright'ом в ходе demo-теста. Это доказательство, "
        "что продукт делает то, что обещано в [user_scenarios.md](user_scenarios.md) "
        "и [quickstart.md](quickstart.md), — не рендеры, не мокапы.\n"
    )
    lines.append("## 🎓 Интерактивный тур внутри приложения — 5 глав\n")
    lines.append(
        "Новый формат Smart Demo доступен прямо в UI: на главном экране нажмите "
        "**«Пройти интерактивный тур (5 глав)»**.\n"
    )
    lines.append("- Глава 1: Первый ответ (~3 мин)")
    lines.append("- Глава 2: От ответа к обучению (~5 мин)")
    lines.append("- Глава 3: Возвращаюсь завтра (~4 мин)")
    lines.append("- Глава 4: Flashcards и долгая память (~6 мин)")
    lines.append("- Глава 5: Курс под ключ (~8 мин)\n")
    lines.append(
        "Overlay тура показывает текущую главу/шаг, ведёт по экранам и сохраняет прогресс между сессиями.\n"
    )
    lines.append(
        "![Interactive Guide Overlay](screenshots/final/scenario_10/01_home_resume_card.png)\n"
    )
    if any(scn.id in {"scenario_21", "scenario_22"} for scn in scenarios):
        lines.append("## 🧭 Demo lane — Умный Маршрутизатор\n")
        lines.append(
            "Сценарии 21–22 раскрывают слайды 6–7 защиты как demo-путь: "
            "**Умный Маршрутизатор сейчас** показывает один лучший следующий шаг "
            "с объяснением, а **Умный Маршрутизатор с ИИ** показывает AI Vision "
            "из 5 уровней поверх той же local-first логики.\n"
        )
        lines.append(
            "![Smart Study Router: когнитивный автопилот и логика маршрутизации]"
            "(screenshots/mastery_engine/mastery_engine_slide_06.png)\n"
        )
    lines.append(
        "<sub>Существующие сценарии ниже сохранены как PR-витрина для внешнего просмотра.</sub>\n"
    )
    lines.append("## Quality gate\n")
    lines.append(
        "Для публикации демо считается готовым только сценарий со статусом "
        "`✅ полностью снят`: все slug-и из YAML имеют PNG в `final/`, а прогон "
        "оставил `meta.json`. Перед внешним показом запускай:\n"
    )
    validate_dir = (
        "doc/screenshots/final"
        if tree == "doc"
        else "docs/screenshots/final  # runtime; studio validate uses doc/screenshots/final"
    )
    lines.append(
        "```bash\n"
        f"npm run demo:validate -- --screenshots-dir {validate_dir} "
        "--require-screenshots --strict-captures --require-unique-shots\n"
        "```\n"
    )
    lines.append(
        "Статус `🟡 частично снят` означает, что ссылки есть только на найденные "
        "кадры; отсутствующие кадры перечислены прямо в разделе сценария. "
        "Статус `⚠️ ещё не снят` означает, что ссылок нет, потому что в `final/` "
        "нет PNG-артефактов для этого сценария.\n"
    )

    # TOC
    lines.append("## Оглавление\n")
    for scn in scenarios:
        anchor = _anchor(scn.id + "-" + scn.title)
        status_marker, _status_label = _coverage_status(scn)
        lines.append(f"- [{scn.id} — {scn.title}](#{anchor}) — {status_marker}")
    lines.append("")

    # Summary table
    lines.append("## Покрытие\n")
    lines.append("| ID | Название | Уровень | Кадров снято | LLM нужен | Статус |")
    lines.append("|---|---|---|:---:|:---:|---|")
    for scn in scenarios:
        llm = "да" if (scn.requires.get("openai_api_key") is True) else "нет"
        status_icon, status_label = _coverage_status(scn)
        captured_count = _matched_shot_count(scn)
        expected_count = len(scn.shots)
        count_str = f"{captured_count}/{expected_count}"
        lines.append(
            f"| `{scn.id}` | {scn.title} | {scn.level} | {count_str} | {llm} | {status_icon} {status_label} |"
        )
    lines.append("")

    # Register freshness footnotes for out-of-date captures
    _register_freshness_note(
        "scenario_06",
        "⚠️ Кадры сняты до Full Circle P0. После завершения P0 интервальный алгоритм "
        "получил UI/API-доработки, и часть кадров может не соответствовать текущему поведению. "
        "Требуется пересъёмка после Full Circle P0.",
    )
    _register_freshness_note(
        "scenario_30",
        "⚠️ Кадры сняты до Full Circle P0. SSR micro-outcome receipt расширен после съёмки; "
        "`03_local_metrics_changed` может не совпадать с текущим интерфейсом. "
        "Требуется пересъёмка после Full Circle P0.",
    )

    for scn in scenarios:
        lines.extend(
            _render_scenario(
                scn, screenshots_dir, sprefix, freshness, docs_tree=tree,
            )
        )

    lines.append(
        "_Документ сгенерирован `scripts/generate_demo_doc.py`. "
        "См. [scenarios/README.md](scenarios/README.md) — как добавить новый сценарий, "
        "и [screenshots/README.md](screenshots/README.md) — как устроены артефакты._"
    )
    return "\n".join(lines) + "\n"


def _render_scenario(
    scn: ScenarioSpec, screenshots_dir: Path, screenshots_link_prefix: str,
    freshness: dict[str, Any] | None = None,
    *,
    docs_tree: str = "doc",
) -> list[str]:
    tree = (docs_tree or "doc").strip().strip("/") or "doc"
    out: list[str] = []
    anchor_title = f"{scn.id} — {scn.title}"
    out.append(f"\n## {anchor_title}\n")

    if scn.level or scn.persona or scn.duration_min:
        badges = []
        if scn.level:
            badges.append(f"**{scn.level}**")
        if scn.duration_min:
            badges.append(f"⏱ {scn.duration_min} мин")
        if scn.persona:
            badges.append(f"👤 {scn.persona}")
        out.append(" · ".join(badges) + "\n")

    if scn.why:
        out.append(f"**Зачем:** {scn.why}\n")

    if scn.wow_moment:
        out.append(f"> 🔥 **Wow-момент:** {scn.wow_moment}\n")

    if not scn.captured:
        scn_dir = screenshots_dir / scn.id
        missing_reason = (
            f"Папка `{tree}/{screenshots_link_prefix}/{scn.id}/` есть, но PNG-кадров нет."
            if scn_dir.exists()
            else f"Папка `{tree}/{screenshots_link_prefix}/{scn.id}/` отсутствует."
        )
        out.append(
            "> ⚠️ Кадры ещё не снимались. Запусти `npm run test:e2e:demo` "
            "и повтори генерацию документа.\n"
        )
        out.append(f"> Причина отсутствия ссылок: {missing_reason}\n")
    else:
        # Анимированный GIF — главный кадр сценария, если собран через scripts/make_demo_gifs.py.
        gif_path = screenshots_dir / scn.id / "demo.gif"
        if gif_path.exists():
            out.append("### Анимированный разбор\n")
            out.append(
                f"![{scn.title}]({screenshots_link_prefix}/{scn.id}/demo.gif)\n"
            )
            size_kb = gif_path.stat().st_size // 1024
            out.append(
                f"<sub>файл: `{tree}/{screenshots_link_prefix}/{scn.id}/demo.gif` · "
                f"{size_kb} KB · собран через `python scripts/make_demo_gifs.py`</sub>\n"
            )

        captured_by_slug = _captured_by_slug(scn.captured)
        missing_shots: list[ShotSpec] = []
        # Статичная раскадровка — для подробного разбора или если GIF не отображается.
        out.append("<details><summary><b>Статичная раскадровка (кадр за кадром)</b></summary>\n")
        if scn.shots:
            for i, shot in enumerate(scn.shots, start=1):
                real = captured_by_slug.get(shot.slug)
                if real is None:
                    # Пробуем по номеру (если slug в манифесте без prefix 01_)
                    real = _match_by_number(scn.captured, i)
                if real:
                    out.append(f"#### Шаг {i} — {shot.caption or shot.slug}\n")
                    out.append(
                        f"![{shot.caption}]({screenshots_link_prefix}/{scn.id}/{real.file})\n"
                    )
                    if shot.narration:
                        out.append(f"_{shot.narration}_\n")
                    dur = f" · ⏱ {shot.duration_sec}s" if shot.duration_sec else ""
                    out.append(
                        f"<sub>файл: `{tree}/{screenshots_link_prefix}/{scn.id}/{real.file}`"
                        f"{dur}</sub>\n"
                    )
                else:
                    missing_shots.append(shot)
                    out.append(f"#### Шаг {i} — {shot.caption or shot.slug}\n")
                    out.append(
                        "> ⚠️ Кадр отсутствует: в `final/` нет PNG, который соответствует "
                        f"`{shot.slug}` из YAML-манифеста.\n"
                    )
        else:
            # Если нет shots в манифесте — просто выводим captured по порядку.
            for i, real in enumerate(scn.captured, start=1):
                out.append(f"#### Шаг {i} — {real.caption or real.file}\n")
                out.append(
                    f"![{real.caption or ''}]({screenshots_link_prefix}/{scn.id}/{real.file})\n"
                )
                if real.narration:
                    out.append(f"_{real.narration}_\n")

        out.append("</details>\n")

        if missing_shots:
            out.append(
                "> 🟡 Сценарий снят частично. Проверь, что demo-test вызывает "
                "`demo.shot(...)` для каждого slug из YAML и что прогон завершился "
                "с `meta.json`.\n"
            )

        if scn.session_meta:
            session = scn.session_meta
            env_pairs = [
                f"{k}={v}" for k, v in (session.get("env") or {}).items() if v
            ]
            if env_pairs:
                out.append("")
                out.append("<details><summary>Технические метаданные прогона</summary>\n")
                out.append(
                    f"- Старт: `{session.get('started_at', '-')}`\n"
                    f"- Финиш: `{session.get('finished_at', '-')}`\n"
                    f"- Статус: `{session.get('status', '-')}`\n"
                    f"- Env: `{', '.join(env_pairs)}`\n"
                )
                out.append("</details>\n")

    if scn.takeaway:
        out.append(f"**Takeaway:** {scn.takeaway}\n")

    footer = _freshness_footer(scn.id)
    if footer:
        out.append(footer.strip() + "\n")

    if freshness:
        gap = freshness.get("gap", -1)
        if gap >= 0:
            out.append(
                f"<sub>Freshness: снято на HEAD `{freshness['capture_sha']}` · "
                f"текущий HEAD `{freshness['current_sha']}` · "
                f"gap `{gap}` коммитов</sub>\n"
            )

    if scn.scenario_link:
        out.append(f"[→ Полный сценарий в каталоге]({scn.scenario_link})\n")

    out.append("---")
    return out


def _anchor(text: str) -> str:
    return (
        text.lower()
        .replace(" ", "-")
        .replace("—", "")
        .replace(":", "")
        .replace(".", "")
        .replace(",", "")
        .replace("_", "-")
        .strip("-")
    )


def _strip_prefix(slug: str) -> str:
    # '01_home_mode_selector' -> 'home_mode_selector'
    if len(slug) > 3 and slug[:2].isdigit() and slug[2] == "_":
        return slug[3:]
    return slug


def _captured_by_slug(shots: list[ScreenshotMeta]) -> dict[str, ScreenshotMeta]:
    captured: dict[str, ScreenshotMeta] = {}
    for meta in shots:
        slug = meta.file.replace(".png", "")
        captured[slug] = meta
        captured[_strip_prefix(slug)] = meta
    return captured


def _matched_shot_count(scn: ScenarioSpec) -> int:
    if not scn.shots:
        return len(scn.captured)
    captured_by_slug = _captured_by_slug(scn.captured)
    matched = 0
    for i, shot in enumerate(scn.shots, start=1):
        if captured_by_slug.get(shot.slug) or _match_by_number(scn.captured, i):
            matched += 1
    return matched


def _coverage_status(scn: ScenarioSpec) -> tuple[str, str]:
    expected = len(scn.shots)
    matched = _matched_shot_count(scn)
    if expected > 0 and matched >= expected:
        return "✅", "полностью снят"
    if matched > 0:
        return "🟡", "частично снят"
    return "⚠️", "ещё не снят"


def _match_by_number(shots: list[ScreenshotMeta], step: int) -> ScreenshotMeta | None:
    prefix = f"{step:02d}_"
    for s in shots:
        if s.file.startswith(prefix):
            return s
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--scenarios-dir",
        type=Path,
        default=DEFAULT_SCENARIOS,
        help="Папка с YAML-манифестами (default: doc/scenarios)",
    )
    parser.add_argument(
        "--screenshots-dir",
        type=Path,
        default=DEFAULT_SCREENSHOTS,
        help="Папка со скриншотами (default: doc/screenshots)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Куда писать smart-документ (default: doc/quickstart_demo.md)",
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Exit 2 если хотя бы у одного сценария отсутствуют скриншоты",
    )
    parser.add_argument(
        "--no-final-sync",
        action="store_true",
        help="Не пересобирать doc/screenshots/final/ (использовать уже существующую final или префикс RUN).",
    )
    args = parser.parse_args()
    resolved = _resolve_screenshots_dir(args.screenshots_dir)
    content_dir, link_prefix = _sync_run_dir_to_final(
        resolved, no_sync=args.no_final_sync
    )

    if not args.scenarios_dir.exists():
        print(f"[demo-doc] ERROR: не найден {args.scenarios_dir}", file=sys.stderr)
        return 2

    scenarios = load_scenarios(args.scenarios_dir)
    if not scenarios:
        print(
            f"[demo-doc] ERROR: не найдено scenario_*.yaml в {args.scenarios_dir}",
            file=sys.stderr,
        )
        return 2

    missing: list[str] = []
    runtime_repo = _find_runtime_repo_root()

    for scn in scenarios:
        enrich_with_screenshots(scn, content_dir)
        if not scn.captured:
            missing.append(scn.id)

    first_meta = None
    for scn in scenarios:
        if scn.session_meta is not None:
            first_meta = scn.session_meta
            break
    freshness = _compute_freshness(runtime_repo, first_meta)

    # Studio tree uses doc/; runtime hometutor docs-root is docs/.
    document = render_document(
        scenarios, content_dir, link_prefix, freshness, docs_tree="doc",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(document, encoding="utf-8")

    total = len(scenarios)
    done = total - len(missing)
    print(f"[demo-doc] scenarios: {done}/{total} captured")
    print(f"[demo-doc] output: {args.output}")
    if freshness.get("current_sha") != "unknown":
        print(
            f"[demo-doc] freshness: capture={freshness.get('capture_sha')} "
            f"current={freshness.get('current_sha')} gap={freshness.get('gap')}"
        )

    product_docs = Path(__file__).resolve().parents[1].parent / "hometutor" / "docs"
    if product_docs.is_dir():
        product_doc = render_document(
            scenarios, content_dir, link_prefix, freshness, docs_tree="docs",
        )
        out_path = product_docs / args.output.name
        out_path.write_text(product_doc, encoding="utf-8")
        print(f"[demo-doc] synced → {out_path} (docs_tree=docs)")

    if missing:
        print("[demo-doc] missing screenshots for: " + ", ".join(missing))
        if args.fail_on_missing:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
