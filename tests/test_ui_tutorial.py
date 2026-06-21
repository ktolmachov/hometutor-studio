from __future__ import annotations

from app.ui.tutorial_chapters import CHAPTERS


def test_chapters_count_and_order():
    assert len(CHAPTERS) == 5
    assert CHAPTERS[0].id == "ch1_first_answer"
    assert CHAPTERS[-1].id == "ch5_course_workspace"


def test_each_chapter_has_steps_and_us_refs():
    for chapter in CHAPTERS:
        assert chapter.steps, f"{chapter.id} should have at least one step"
        for step in chapter.steps:
            assert step.id
            assert step.title_ru
            assert step.cta_label_ru
            assert step.us_refs, f"{chapter.id}/{step.id} should map to US refs"


def test_has_wow_step_in_every_chapter():
    for chapter in CHAPTERS:
        assert any(step.wow for step in chapter.steps), f"{chapter.id} should contain wow step"


def test_each_chapter_has_core_metadata():
    for chapter in CHAPTERS:
        assert chapter.title_ru.strip(), f"{chapter.id} should have title"
        assert chapter.summary_ru.strip(), f"{chapter.id} should have summary"
        assert chapter.estimated_minutes > 0, f"{chapter.id} should have positive duration"
        assert chapter.cjm_stages, f"{chapter.id} should map to CJM stages"
