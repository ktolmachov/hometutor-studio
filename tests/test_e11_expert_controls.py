"""E11-C / US-14.3: расширенный слой управления не конкурирует с beginner copy; контролы достижимы в коде."""

from __future__ import annotations

from pathlib import Path

from app.ui.continuity_bridge import (
    expert_controls_expander_label_ru,
    expert_controls_sidebar_blurb_ru,
    qa_tab_expert_pointer_caption_ru,
)
from tests.test_e11_beginner_copy import _assert_no_forbidden_ru_copy


def test_expert_layer_copy_matches_beginner_contract():
    for fn in (
        expert_controls_expander_label_ru,
        expert_controls_sidebar_blurb_ru,
        qa_tab_expert_pointer_caption_ru,
    ):
        _assert_no_forbidden_ru_copy(fn())


from tests.studio_layout import product_app_path


def test_expert_controls_wired_in_sidebar_and_query_tab():
    sidebar_src = product_app_path("ui", "sidebar.py").read_text(encoding="utf-8")
    query_answer_src = product_app_path("ui", "query_tab_answer_section.py").read_text(
        encoding="utf-8"
    )
    assert "expert_controls_expander_label_ru()" in sidebar_src
    assert "expert_controls_expander_label_ru()" in query_answer_src
    # E27-A: backup/restore — отдельный expander, один вызов панели (не дублирование мастера в «Голос»).
    assert "sync_transfer_sidebar_expander_label_ru()" in sidebar_src
    assert "_render_sidebar_backup_restore_panel()" in sidebar_src
    assert "Голос и синхронизация" not in sidebar_src
