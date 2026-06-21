"""Tests for scripts/check_roadmap_health.py."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK_PATH = ROOT / "scripts" / "check_roadmap_health.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_roadmap_health", CHECK_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_roadmap(path: Path, *, update: str = "2026-05-06", platform: str = "39.5") -> None:
    rows = "\n".join(
        f"| **#{index} Moment** | `wave-{index}` | Result |" for index in range(1, 14)
    )
    candidates = "\n".join(
        f"| {index} | #7 Spaced Rep Due | US-7.1 | Pain | SRS | source | P1 | retention | M | M | Follow-up |"
        for index in range(1, 6)
    )
    path.write_text(
        f"""# Roadmap

Актуализировано: **{update}**

### 6.1 Распределение по типам

| Тип | Волн | Пакетов | % от общего | Комментарий |
|-----|------|---------|-------------|-------------|
| 🎯 UX | 9 | 28 | 23.5% | Прямое улучшение опыта |
| 🧠 Intelligence | 4 | 15 | 12.6% | Персонализация |
| 🔄 Retention | 3 | 7 | 5.9% | Механики возврата |
| 📚 Content | 4 | 8 | 6.7% | Работа с материалами |
| ⚙️ Platform | 16 | 47 | {platform}% | Инфраструктура |
| 🎓 Learning | 4 | 14 | 11.8% | Педагогика |

### 6.3 Связь волн с CJM моментами истины

| CJM Moment | Волны, которые усилили момент | Результат |
|------------|-------------------------------|-----------|
{rows}

## 7. Связь с CJM и User Stories

### 8.3 Примеры прорывных направлений

| # | CJM Stage / Moment | US | Pain point | Feature area | Источник | Критичность | Влияние | Актуальность | Сила сигнала | Порог / блокеры |
|---|-------------------|----|-----------|--------------|---------| ------------|---------|--------------|--------------|-----------------|
{candidates}
""",
        encoding="utf-8",
    )


def test_repo_roadmap_is_healthy():
    module = _load_module()
    health = module.check_roadmap_health(today=date(2026, 5, 6))
    assert health.warnings == []
    assert health.cjm_moment_count == 13
    assert health.candidate_count >= 5


def test_stale_roadmap_warns(tmp_path: Path):
    module = _load_module()
    roadmap = tmp_path / "roadmap.md"
    _write_roadmap(roadmap, update="2026-03-01")

    health = module.check_roadmap_health(roadmap, today=date(2026, 5, 6))

    assert any("stale" in warning for warning in health.warnings)


def test_platform_heavy_roadmap_warns(tmp_path: Path):
    module = _load_module()
    roadmap = tmp_path / "roadmap.md"
    _write_roadmap(roadmap, platform="56.8")

    health = module.check_roadmap_health(roadmap, today=date(2026, 5, 6))

    assert any("platform-heavy" in warning for warning in health.warnings)


def test_incomplete_cjm_and_candidate_table_warn(tmp_path: Path):
    module = _load_module()
    roadmap = tmp_path / "roadmap.md"
    _write_roadmap(roadmap)
    text = roadmap.read_text(encoding="utf-8")
    text = text.replace("| **#13 Moment** | `wave-13` | Result |\n", "")
    text = text.replace(
        "| 5 | #7 Spaced Rep Due | US-7.1 | Pain | SRS | source | P1 | retention | M | M | Follow-up |\n",
        "",
    )
    roadmap.write_text(text, encoding="utf-8")

    health = module.check_roadmap_health(roadmap, today=date(2026, 5, 6))

    assert any("CJM coverage is incomplete" in warning for warning in health.warnings)
    assert any("CANDIDATE_TABLE is too small" in warning for warning in health.warnings)
