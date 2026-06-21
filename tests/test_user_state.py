import json
import sqlite3
import threading

import pytest

import app.user_state as user_state
from app.config import reset_settings_cache


def test_learning_plan_steps_from_markdown_numbered():
    md = "1. Первый шаг\nдетали\n\n2. Второй шаг\nещё"
    steps = user_state.learning_plan_steps_from_markdown(md)
    assert len(steps) >= 2
    assert "Первый" in steps[0]


def test_topic_resource_roundtrip(tmp_path, monkeypatch):
    db = tmp_path / "u.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()

    tid = "t1"
    user_state.upsert_reading_status(
        resource_type="topic",
        resource_id=user_state.topic_resource_id(tid),
        progress=0.42,
        display_title="Тема X",
        index_version="c:ts",
    )
    assert abs((user_state.get_topic_progress(tid) or 0) - 0.42) < 1e-6

    states = user_state.get_topic_states([tid])
    assert states[tid]["progress"] == pytest.approx(0.42)

    user_state.toggle_bookmark("topic", user_state.topic_resource_id(tid))
    states2 = user_state.get_topic_states([tid])
    assert states2[tid]["bookmarked"] is True

    user_state.toggle_bookmark("topic", user_state.topic_resource_id(tid))
    states3 = user_state.get_topic_states([tid])
    assert states3[tid]["bookmarked"] is False


def test_annotations_and_resume(tmp_path, monkeypatch):
    db = tmp_path / "u2.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()

    user_state.add_note("topic", user_state.topic_resource_id("z"), "hello")
    rows = user_state.list_annotations(limit=5)
    assert len(rows) == 1
    nid = rows[0]["id"]
    user_state.delete_annotation(nid)
    assert user_state.list_annotations(limit=5) == []

    user_state.upsert_reading_status(
        resource_type="learning_plan",
        resource_id=user_state.learning_plan_resource_id("tid"),
        step_index=2,
        step_label="3. Читать главу",
        progress=0.5,
        display_title="План по RAG",
        index_version="v1",
    )
    r = user_state.get_latest_resume()
    assert r is not None
    assert r["resource_type"] == "learning_plan"
    assert r["step_index"] == 2


def test_weekly_goals_and_preferred_style(tmp_path, monkeypatch):
    db = tmp_path / "p5.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()

    assert user_state.get_preferred_style() == "balanced"
    user_state.set_preferred_style("practice")
    assert user_state.get_preferred_style() == "practice"

    s0 = user_state.get_weekly_goals_state()
    assert "targets" in s0 and "done" in s0
    user_state.increment_weekly_progress("quizzes", 1)
    s1 = user_state.get_weekly_goals_state()
    assert int(s1["done"]["quizzes"]) >= 1


def test_smart_study_steering_preference_roundtrip(tmp_path, monkeypatch):
    db = tmp_path / "ssr_steer.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()

    assert user_state.get_smart_study_steering_preference() == ""
    user_state.set_smart_study_steering_preference("gentle")
    assert user_state.get_smart_study_steering_preference() == "gentle"
    user_state.clear_smart_study_steering_preference()
    assert user_state.get_smart_study_steering_preference() == ""


def test_app_kv_roundtrip(tmp_path, monkeypatch):
    db = tmp_path / "kv.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()

    assert user_state.get_kv("tutor_mastery_level") is None
    user_state.set_kv("tutor_mastery_level", "advanced")
    assert user_state.get_kv("tutor_mastery_level") == "advanced"


def test_tutor_learning_resume_roundtrip(tmp_path, monkeypatch):
    db = tmp_path / "tutor_resume.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()

    assert user_state.get_tutor_learning_resume() is None
    user_state.upsert_tutor_learning_resume(
        session_id="sess-1",
        topic="RAG",
        mastery_level="intermediate",
        last_action_kind="micro_quiz",
        last_action_label="Мини-проверка: correct",
        quiz_feedback={"status": "correct"},
        recommended_next={"next_action": "Следующий шаг"},
        due_reviews_count=2,
    )
    r = user_state.get_tutor_learning_resume()
    assert r is not None
    assert r["session_id"] == "sess-1"
    assert r["topic"] == "RAG"
    assert r["quiz_feedback"]["status"] == "correct"
    assert r["recommended_next"]["next_action"] == "Следующий шаг"
    assert r["due_reviews_count"] == 2
    user_state.clear_tutor_learning_resume()
    assert user_state.get_tutor_learning_resume() is None


def test_tutor_learning_resume_persists_fields_used_by_home_resume_card(tmp_path, monkeypatch):
    db = tmp_path / "tutor_resume_home.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()

    user_state.upsert_tutor_learning_resume(
        session_id="sess-home-1",
        topic="Vector DB",
        mastery_level="intermediate",
        last_action_kind="tutor_answer",
        last_action_label="Получен ответ тьютора",
        due_reviews_count=4,
        index_version="idx-v2",
    )
    snap = user_state.get_tutor_learning_resume()
    assert snap is not None
    assert snap["topic"] == "Vector DB"
    assert snap["last_action_label"] == "Получен ответ тьютора"
    assert snap["due_reviews_count"] == 4
    assert snap["index_version"] == "idx-v2"


def test_learner_goal_snapshot_empty_then_roundtrip(tmp_path, monkeypatch):
    db = tmp_path / "lgs.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()

    assert user_state.get_learner_goal_snapshot() is None
    assert user_state.learner_goal_snapshot_api_empty() == {
        "schema_version": None,
        "updated_at": None,
        "goal_context": None,
    }

    out = user_state.upsert_learner_goal_snapshot(
        subtopic="vectors",
        target_level="recall",
        desired_outcome="understand dot product",
        time_budget_min=12,
        preferred_style="practice",
        learning_goal="exam_prep",
    )
    assert out["schema_version"] == user_state.LEARNER_GOAL_SNAPSHOT_SCHEMA_VERSION
    assert out["goal_context"]["topic"] == "general"
    assert out["goal_context"]["subtopic"] == "vectors"
    assert out["goal_context"]["time_budget_min"] == 12

    loaded = user_state.get_learner_goal_snapshot()
    assert loaded is not None
    assert loaded["goal_context"] == out["goal_context"]
    assert loaded["updated_at"] == out["updated_at"]

    user_state.clear_learner_goal_snapshot()
    assert user_state.get_learner_goal_snapshot() is None


def test_tutor_learner_profile_roundtrip(tmp_path, monkeypatch):
    db = tmp_path / "tutor_profile.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()

    base = user_state.get_tutor_learner_profile()
    assert base["preferred_style"] == "balanced"
    updated = user_state.set_tutor_learner_profile(
        {
            "sessions_count": 3,
            "preferred_style": "practice",
            "last_route": "due_review",
            "last_focus_topic": "RAG",
            "weak_concepts": ["retrieval"],
        }
    )
    assert updated["preferred_style"] == "practice"
    assert updated["last_route"] == "due_review"

    roundtrip = user_state.get_tutor_learner_profile()
    assert roundtrip["sessions_count"] == 3
    assert roundtrip["last_focus_topic"] == "RAG"
    assert roundtrip["weak_concepts"] == ["retrieval"]


def test_research_sessions_crud(tmp_path, monkeypatch):
    db = tmp_path / "rs.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()

    pl = user_state.normalize_research_payload(
        current_view="Темы",
        active_topic_id="t1",
        last_studied_document="docs/a.md",
        last_answer=None,
        last_synthesis={"topic": "X"},
        last_learning_plan=None,
        history=[],
        question_draft="",
        topic_document_selections={"t1": ["a.md"]},
    )
    rid = user_state.save_research_session("Моя сессия", pl, index_version="col:ts1")
    assert rid > 0

    rows = user_state.list_research_sessions(current_index_version="col:ts1")
    assert len(rows) == 1
    assert rows[0]["is_stale"] is False

    rows_stale = user_state.list_research_sessions(current_index_version="col:ts2")
    assert rows_stale[0]["is_stale"] is True

    full = user_state.get_research_session(rid)
    assert full is not None
    assert full["payload"]["active_topic_id"] == "t1"
    assert full["payload"]["last_studied_document"] == "docs/a.md"
    assert full["payload"]["topic_document_selections"]["t1"] == ["a.md"]

    user_state.delete_research_session(rid)
    assert user_state.get_research_session(rid) is None


def test_parse_quiz_json():
    from app.quiz_service import parse_quiz_json

    raw = """```json
[
  {"question": "Q1?", "options": ["a","b","c","d"], "correct_index": 0},
  {"question": "Q2?", "options": ["a","b","c","d"], "correct_index": 1},
  {"question": "Q3?", "options": ["a","b","c","d"], "correct_index": 2},
  {"question": "Q4?", "options": ["a","b","c","d"], "correct_index": 3},
  {"question": "Q5?", "options": ["a","b","c","d"], "correct_index": 0}
]
```"""
    qs, err = parse_quiz_json(raw)
    assert err is None
    assert len(qs) == 5


def test_quiz_results_are_scoped_to_current_generation(tmp_path, monkeypatch):
    db = tmp_path / "quiz_lineage.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()

    monkeypatch.setattr(
        user_state,
        "get_current_learner_state_lineage",
        lambda: {"generation_id": "gen-a", "index_version": 1},
    )
    monkeypatch.setattr(user_state, "_active_concept_ids_for_lineage", lambda: {"TopicA"})
    user_state.save_quiz_result(concept="TopicA", level="recognition", score=0.4)

    monkeypatch.setattr(
        user_state,
        "get_current_learner_state_lineage",
        lambda: {"generation_id": "gen-b", "index_version": 2},
    )
    user_state.save_quiz_result(concept="TopicA", level="transfer", score=0.4)

    assert user_state.get_recent_quiz_levels_low_score("TopicA") == ["transfer"]

    def _work(conn):
        return [
            dict(row)
            for row in conn.execute(
                """
                SELECT concept, level, generation_id, index_version
                FROM quiz_results
                ORDER BY id ASC
                """
            ).fetchall()
        ]

    rows = user_state._with_db(_work)
    assert [row["generation_id"] for row in rows] == ["gen-a", "gen-b"]
    assert [row["index_version"] for row in rows] == [1, 2]


def test_restore_and_purge_archived_learner_state(tmp_path, monkeypatch):
    db = tmp_path / "archive_restore.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()

    monkeypatch.setattr(
        user_state,
        "get_current_learner_state_lineage",
        lambda: {"generation_id": "gen-a", "index_version": 1},
    )
    monkeypatch.setattr(user_state, "_active_concept_ids_for_lineage", lambda: {"A"})

    from app.quiz_adaptive import update_mastery_after_score
    from app.spaced_repetition import update_spaced_repetition

    update_mastery_after_score("A", 1.0)
    update_spaced_repetition("A", 5)

    monkeypatch.setattr(
        user_state,
        "get_current_learner_state_lineage",
        lambda: {"generation_id": "gen-b", "index_version": 2},
    )
    diag = user_state.get_learner_state_diagnostics()
    assert diag["archive_counts"]["total"] == 2

    archived = user_state.list_archived_learner_state(source_generation_id="gen-a")
    assert archived["total"] == 2

    restored = user_state.restore_archived_learner_state(source_generation_id="gen-a")
    assert restored["restored_total"] == 2
    assert restored["restored_by_table"]["quiz_mastery"] == 1
    assert restored["restored_by_table"]["spaced_repetition"] == 1

    def _live_counts(conn):
        mastery = conn.execute("SELECT COUNT(*) AS n FROM quiz_mastery WHERE concept = 'A'").fetchone()
        spaced = conn.execute("SELECT COUNT(*) AS n FROM spaced_repetition WHERE concept = 'A'").fetchone()
        return int(mastery["n"] or 0), int(spaced["n"] or 0)

    mastery_n, spaced_n = user_state._with_db(_live_counts)
    assert mastery_n == 1
    assert spaced_n == 1

    purged = user_state.purge_archived_learner_state(source_generation_id="gen-a")
    assert purged["deleted_total"] == 2
    assert user_state.list_archived_learner_state(source_generation_id="gen-a")["total"] == 0


def test_restore_archived_learner_state_skips_inactive_concepts(tmp_path, monkeypatch):
    db = tmp_path / "archive_restore_inactive.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()

    monkeypatch.setattr(
        user_state,
        "get_current_learner_state_lineage",
        lambda: {"generation_id": "gen-a", "index_version": 1},
    )
    monkeypatch.setattr(user_state, "_active_concept_ids_for_lineage", lambda: {"A"})

    from app.quiz_adaptive import update_mastery_after_score
    from app.spaced_repetition import update_spaced_repetition

    update_mastery_after_score("A", 1.0)
    update_spaced_repetition("A", 5)

    monkeypatch.setattr(
        user_state,
        "get_current_learner_state_lineage",
        lambda: {"generation_id": "gen-b", "index_version": 2},
    )
    monkeypatch.setattr(user_state, "_active_concept_ids_for_lineage", lambda: {"B"})
    user_state.get_learner_state_diagnostics()

    restored = user_state.restore_archived_learner_state(source_generation_id="gen-a")
    assert restored["restored_total"] == 0
    assert restored["skipped_inactive"] == 2


def _reset_user_state_db(monkeypatch, tmp_path, name="concurrent.db"):
    db = tmp_path / name
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()
    # Ensure pragmas are re-applied for this fresh DB path inside the process.
    user_state._DB_PRAGMA_APPLIED.discard(str(db))
    return db


def test_user_state_pragmas_wal_enabled(tmp_path, monkeypatch):
    db = _reset_user_state_db(monkeypatch, tmp_path, "pragma.db")
    # Trigger schema init via any read.
    user_state.list_annotations(limit=1)
    # journal_mode=WAL persists in the DB file itself.
    probe = sqlite3.connect(str(db))
    try:
        mode = probe.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        probe.close()
    assert str(mode).lower() == "wal"
    assert str(db) in user_state._DB_PRAGMA_APPLIED
    # synchronous is per-connection — verify _connect() applies it.
    conn = user_state._connect()
    try:
        sync = conn.execute("PRAGMA synchronous").fetchone()[0]
    finally:
        conn.close()
    assert int(sync) == 1


def test_schema_migration_is_idempotent(tmp_path, monkeypatch):
    """Calling schema initialisation a second time on the same DB must not raise
    or duplicate columns. This guards against a regression where ALTER TABLE
    re-runs would surface as OperationalError instead of being absorbed."""
    _reset_user_state_db(monkeypatch, tmp_path, "schema.db")
    # First touch creates schema.
    user_state.set_kv("k1", "v1")
    # Force a fresh connection and re-run _ensure_schema several times.
    for _ in range(5):
        conn = user_state._connect()
        try:
            user_state._ensure_schema(conn)
        finally:
            conn.close()
    # Data must survive idempotent re-runs.
    assert user_state.get_kv("k1") == "v1"
    # Inspect quiz_results columns to make sure ALTER TABLE re-application is a no-op.
    conn = user_state._connect()
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(quiz_results)").fetchall()]
    finally:
        conn.close()
    # generation_id / index_version were added via _ensure_column; they must
    # appear exactly once even after repeated migrations.
    assert cols.count("generation_id") == 1
    assert cols.count("index_version") == 1


def test_kv_edge_cases(tmp_path, monkeypatch):
    _reset_user_state_db(monkeypatch, tmp_path, "kv_edge.db")

    # Empty / whitespace key is rejected silently and returns the default.
    user_state.set_kv("", "ignored")
    assert user_state.get_kv("", default="d") == "d"
    user_state.set_kv("   ", "ignored")
    assert user_state.get_kv("   ", default="d") == "d"

    # Oversized key (>128 chars) is rejected.
    huge = "k" * 200
    user_state.set_kv(huge, "ignored")
    assert user_state.get_kv(huge, default="d") == "d"

    # None value coerced to empty string.
    user_state.set_kv("nullable", None)  # type: ignore[arg-type]
    assert user_state.get_kv("nullable") == ""

    # Round-trip with realistic JSON payload.
    payload = {"a": 1, "b": [1, 2, 3], "c": {"d": "ё"}}
    user_state.set_kv("json_payload", json.dumps(payload, ensure_ascii=False))
    raw = user_state.get_kv("json_payload")
    assert raw is not None
    assert json.loads(raw) == payload

    # Default fall-through for missing key.
    assert user_state.get_kv("does_not_exist", default="fallback") == "fallback"
    assert user_state.get_kv("does_not_exist") is None


def test_corrupt_kv_json_recovers_gracefully(tmp_path, monkeypatch):
    """Corrupted JSON blobs in app_kv must not crash high-level helpers; they
    fall back to a fresh default snapshot. Regression for the silent JSON
    decode path that previously absorbed errors without producing a usable
    fallback."""
    _reset_user_state_db(monkeypatch, tmp_path, "corrupt.db")

    # Tutor learner profile: garbage JSON → returns default model.
    user_state.set_kv("tutor_learner_profile_json", "{not_json")
    profile = user_state.get_tutor_learner_profile()
    assert profile["preferred_style"] == "balanced"
    assert profile["sessions_count"] == 0
    assert profile["recent_topics"] == []

    # Tutor learner profile: structurally wrong JSON (list instead of dict).
    user_state.set_kv("tutor_learner_profile_json", json.dumps([1, 2, 3]))
    profile2 = user_state.get_tutor_learner_profile()
    assert profile2["preferred_style"] == "balanced"

    # Weekly goals: garbage JSON falls back to default for current week.
    user_state.set_kv("weekly_goals_json", "{still_broken")
    state = user_state.get_weekly_goals_state()
    assert "week_id" in state and state["targets"]
    assert all(state["done"][k] == 0 for k in state["done"])

    # Preferred style with invalid stored value normalises back to balanced.
    user_state.set_kv("tutor_preferred_style", "not_a_style")
    assert user_state.get_preferred_style() == "balanced"
    user_state.set_preferred_style("EXAMPLES")
    assert user_state.get_preferred_style() == "examples"
    user_state.set_preferred_style("garbage")
    assert user_state.get_preferred_style() == "balanced"


def test_corrupt_research_session_payload(tmp_path, monkeypatch):
    """A research session row with broken payload_json must round-trip as an
    empty dict instead of raising — prior code silently returned wrong
    structure under JSONDecodeError."""
    _reset_user_state_db(monkeypatch, tmp_path, "research_corrupt.db")

    sid = user_state.save_research_session("ok", {"k": "v"}, index_version="iv-1")
    fetched = user_state.get_research_session(sid)
    assert fetched is not None
    assert fetched["payload"] == {"k": "v"}

    # Manually corrupt the row's payload_json column via a direct connection.
    conn = user_state._connect()
    try:
        conn.execute(
            "UPDATE research_sessions SET payload_json = ? WHERE id = ?",
            ("{broken", sid),
        )
        conn.commit()
    finally:
        conn.close()

    fetched2 = user_state.get_research_session(sid)
    assert fetched2 is not None
    assert fetched2["payload"] == {}
    assert fetched2["name"] == "ok"


def test_research_session_lifecycle_and_listing(tmp_path, monkeypatch):
    _reset_user_state_db(monkeypatch, tmp_path, "research_lifecycle.db")

    ids: list[int] = []
    for i in range(4):
        ids.append(
            user_state.save_research_session(
                name=f"session_{i}",
                payload={"step": i, "history": [f"q{i}", f"a{i}"]},
                index_version="iv-current" if i % 2 == 0 else "iv-old",
            )
        )

    listed = user_state.list_research_sessions(limit=10, current_index_version="iv-current")
    assert len(listed) == 4
    by_id = {row["id"]: row for row in listed}
    for i, sid in enumerate(ids):
        row = by_id[sid]
        assert row["name"] == f"session_{i}"
        # Stale rows are those whose index_version differs from current.
        assert row["is_stale"] is (row["index_version"] == "iv-old")

    # Delete one and verify removal from listing.
    user_state.delete_research_session(ids[1])
    remaining = {row["id"] for row in user_state.list_research_sessions(limit=10)}
    assert ids[1] not in remaining
    assert remaining == {ids[0], ids[2], ids[3]}

    # get_research_session returns None for missing id.
    assert user_state.get_research_session(ids[1]) is None


def test_weekly_goals_rollover_preserves_targets(tmp_path, monkeypatch):
    """When the stored week_id no longer matches the current ISO week the done
    counters reset to zero but customised targets must persist into the new
    week — prior bug overwrote tweaked targets with defaults."""
    _reset_user_state_db(monkeypatch, tmp_path, "weekly.db")

    # Seed with stale week + customised targets + non-zero done values.
    stale = {
        "week_id": "1900-W01",
        "targets": {"new_topics": 9, "reviews": 7, "quizzes": 11},
        "done": {"new_topics": 3, "reviews": 2, "quizzes": 5},
    }
    user_state.set_kv("weekly_goals_json", json.dumps(stale))

    rolled = user_state.get_weekly_goals_state()
    assert rolled["week_id"] != "1900-W01"
    # Customised targets must survive the rollover.
    assert rolled["targets"]["new_topics"] == 9
    assert rolled["targets"]["reviews"] == 7
    assert rolled["targets"]["quizzes"] == 11
    # Done counters must be zeroed for the new week.
    assert rolled["done"] == {"new_topics": 0, "reviews": 0, "quizzes": 0}


def test_increment_weekly_progress(tmp_path, monkeypatch):
    _reset_user_state_db(monkeypatch, tmp_path, "weekly_inc.db")

    # Unknown key is a no-op (but still returns a valid state snapshot).
    state0 = user_state.increment_weekly_progress("nope")
    assert state0["done"]["quizzes"] == 0

    state1 = user_state.increment_weekly_progress("quizzes", 2)
    assert state1["done"]["quizzes"] == 2
    state2 = user_state.increment_weekly_progress("quizzes")
    assert state2["done"]["quizzes"] == 3
    state3 = user_state.increment_weekly_progress("reviews", 4)
    assert state3["done"]["reviews"] == 4
    assert state3["done"]["quizzes"] == 3


def test_bookmark_and_notes_lifecycle(tmp_path, monkeypatch):
    _reset_user_state_db(monkeypatch, tmp_path, "anno.db")

    rid = user_state.topic_resource_id("alpha")
    assert user_state.has_bookmark("topic", rid) is False

    # toggle: add → present → toggle: remove → absent
    user_state.toggle_bookmark("topic", rid)
    assert user_state.has_bookmark("topic", rid) is True
    user_state.toggle_bookmark("topic", rid)
    assert user_state.has_bookmark("topic", rid) is False

    # Notes are independent and listed in reverse chronological order.
    nid1 = user_state.add_note("topic", rid, "first")
    nid2 = user_state.add_note("topic", rid, "second")
    rows = user_state.list_annotations(limit=10)
    assert {r["id"] for r in rows} == {nid1, nid2}
    bodies = [r["body"] for r in rows]
    assert "first" in bodies and "second" in bodies

    user_state.delete_annotation(nid1)
    rows2 = user_state.list_annotations(limit=10)
    assert {r["id"] for r in rows2} == {nid2}


def test_resource_id_helpers_and_label():
    assert user_state.topic_resource_id("alpha") == "topic:alpha"
    assert user_state.document_resource_id("docs/a.md") == "doc:docs/a.md"
    assert user_state.qa_resource_id("Что такое RAG?").startswith("qa:")
    assert user_state.learning_plan_resource_id("alpha") == "plan:alpha"

    assert "тема" in user_state.format_resource_label("topic", "topic:alpha")
    assert user_state.format_resource_label("doc", "doc:docs/a.md") == "docs/a.md"
    assert "план" in user_state.format_resource_label("plan", "plan:alpha")
    assert user_state.format_resource_label("qa", "qa:abcdef").startswith("ответ")
    assert user_state.format_resource_label("other", "raw").startswith("other:")


def test_learning_plan_steps_from_markdown_variants():
    md_numbered = "1. Шаг A\n2. Шаг B\n3. Шаг C"
    steps = user_state.learning_plan_steps_from_markdown(md_numbered)
    assert len(steps) == 3
    assert "Шаг A" in steps[0]

    # Empty / whitespace input returns an empty list.
    assert user_state.learning_plan_steps_from_markdown("") == []
    assert user_state.learning_plan_steps_from_markdown("   \n\n   ") == []


def test_micro_quiz_outcome_and_tutor_resume(tmp_path, monkeypatch):
    _reset_user_state_db(monkeypatch, tmp_path, "micro.db")

    # Save a couple of micro-quiz outcomes; they go to micro_quiz_events.
    rid_a = user_state.save_micro_quiz_outcome(
        topic="rag",
        quiz_feedback={"status": "correct", "score": 1.0},
        recommended_next={"next_action": "Следующий шаг"},
    )
    rid_b = user_state.save_micro_quiz_outcome(
        topic="indexing",
        quiz_feedback={"status": "incorrect"},
        recommended_next={"next_action": "Объясни проще"},
    )
    assert rid_a > 0 and rid_b > 0 and rid_b != rid_a

    # Tutor learning resume: upsert is the single-row "where I left off" snapshot.
    user_state.upsert_tutor_learning_resume(
        session_id="sess-1",
        topic="rag",
        mastery_level="intermediate",
        last_action_kind="micro_quiz",
        last_action_label="checked",
        quiz_feedback={"status": "correct"},
        recommended_next={"next_action": "Следующий шаг"},
        due_reviews_count=2,
        index_version="iv-current",
    )
    snap = user_state.get_tutor_learning_resume()
    assert snap is not None
    assert snap["topic"] == "rag"
    assert snap["mastery_level"] == "intermediate"
    assert snap["due_reviews_count"] == 2
    assert snap["quiz_feedback"]["status"] == "correct"
    assert snap["recommended_next"]["next_action"] == "Следующий шаг"

    # Re-upsert collapses to the same single row (id=1), updating fields.
    user_state.upsert_tutor_learning_resume(
        session_id="sess-1",
        topic="indexing",
        mastery_level="advanced",
        last_action_kind="explanation",
        last_action_label="explained",
        due_reviews_count=0,
    )
    snap2 = user_state.get_tutor_learning_resume()
    assert snap2 is not None
    assert snap2["topic"] == "indexing"
    assert snap2["mastery_level"] == "advanced"
    assert snap2["due_reviews_count"] == 0

    user_state.clear_tutor_learning_resume()
    assert user_state.get_tutor_learning_resume() is None

    # Empty session_id is a silent no-op rather than persisting garbage.
    user_state.upsert_tutor_learning_resume(
        session_id="",
        topic="t",
        mastery_level="intermediate",
        last_action_kind="x",
        last_action_label="y",
    )
    assert user_state.get_tutor_learning_resume() is None


def test_reading_status_listing_and_progress(tmp_path, monkeypatch):
    _reset_user_state_db(monkeypatch, tmp_path, "reading.db")

    for i, title in enumerate(["A", "B", "C"]):
        user_state.upsert_reading_status(
            resource_type="topic",
            resource_id=user_state.topic_resource_id(title),
            progress=0.1 * (i + 1),
            display_title=f"тема {title}",
            index_version="iv-1",
        )

    rows = user_state.list_topic_reading_rows(limit=10)
    assert len(rows) == 3
    titles = {r["topic_id"] for r in rows}
    assert titles == {"A", "B", "C"}

    states = user_state.get_topic_states(["A", "B", "C", "Z"])
    assert states["A"]["progress"] == pytest.approx(0.1)
    assert states["Z"]["progress"] is None

    # >= threshold counter (gamification badge).
    n = user_state.count_reading_at_least_progress(0.25)
    assert n == 1  # only C (0.3) is above 0.25

    n_all = user_state.count_reading_at_least_progress(0.0)
    assert n_all == 3

    # Resume returns most recently touched row.
    user_state.upsert_reading_status(
        resource_type="topic",
        resource_id=user_state.topic_resource_id("A"),
        progress=0.99,
        display_title="тема A",
        index_version="iv-2",
    )
    resume = user_state.get_latest_resume()
    assert resume is not None
    assert resume["progress"] == pytest.approx(0.99)


def test_full_sync_bundle_roundtrip(tmp_path, monkeypatch):
    """Export → wipe → import must preserve at least the row counts of the
    user_state tables that the bundle covers."""
    src_db = tmp_path / "src.db"
    monkeypatch.setenv("USER_STATE_DB", str(src_db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()
    user_state._DB_PRAGMA_APPLIED.discard(str(src_db))

    user_state.upsert_reading_status(
        resource_type="topic",
        resource_id=user_state.topic_resource_id("alpha"),
        progress=0.5,
        display_title="alpha",
    )
    user_state.add_note("topic", user_state.topic_resource_id("alpha"), "n1")
    user_state.set_kv("k", "v")

    bundle = user_state.export_full_sync_bundle()
    assert bundle["sync_version"] == user_state.SYNC_BUNDLE_VERSION
    assert isinstance(bundle["tables"], dict)
    assert any(rows for rows in bundle["tables"].values())

    # Switch to a fresh DB file and import.
    dst_db = tmp_path / "dst.db"
    monkeypatch.setenv("USER_STATE_DB", str(dst_db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()
    user_state._DB_PRAGMA_APPLIED.discard(str(dst_db))

    # Sanity-check destination is empty.
    assert user_state.list_annotations(limit=10) == []
    assert user_state.get_kv("k") is None

    result = user_state.import_full_sync_bundle(
        {k: v for k, v in bundle.items() if k != "quiz_ui_stats"}
    )
    assert result["sync_version"] == user_state.SYNC_BUNDLE_VERSION
    assert result["rows_inserted"] >= 1

    # Imported rows must be visible through the high-level API.
    assert user_state.get_kv("k") == "v"
    notes = user_state.list_annotations(limit=10)
    assert any(r["body"] == "n1" for r in notes)


def test_preview_full_sync_bundle_counts_and_rejects_version(tmp_path, monkeypatch):
    _reset_user_state_db(monkeypatch, tmp_path, "preview.db")

    with pytest.raises(ValueError):
        user_state.preview_full_sync_bundle({"sync_version": 999, "tables": {}})

    with pytest.raises(ValueError):
        user_state.preview_full_sync_bundle(
            {"sync_version": user_state.SYNC_BUNDLE_VERSION, "tables": "nope"}
        )

    bundle = user_state.export_full_sync_bundle()
    prev = user_state.preview_full_sync_bundle(bundle)
    assert prev["sync_version"] == user_state.SYNC_BUNDLE_VERSION
    assert prev["total_rows"] >= 0
    assert isinstance(prev["table_row_counts"], dict)
    assert "app_kv" in prev["table_row_counts"]


def test_import_full_sync_bundle_rejects_bad_input(tmp_path, monkeypatch):
    _reset_user_state_db(monkeypatch, tmp_path, "import_bad.db")

    with pytest.raises(ValueError):
        user_state.import_full_sync_bundle({"sync_version": 999, "tables": {}})

    with pytest.raises(ValueError):
        user_state.import_full_sync_bundle(
            {"sync_version": user_state.SYNC_BUNDLE_VERSION, "tables": "nope"}
        )

    bundle = user_state.export_full_sync_bundle()
    bundle["tables"]["app_kv"] = [{"key) VALUES ('x'); DROP TABLE app_kv; --": "boom"}]
    with pytest.raises(ValueError, match="app_kv column"):
        user_state.import_full_sync_bundle(bundle)


def test_set_tutor_learner_profile_normalises(tmp_path, monkeypatch):
    """Tutor learner profile must clamp / normalise unusual fields rather than
    persisting them verbatim, otherwise the orchestrator could be handed an
    invalid `preferred_style` and crash on lookup."""
    _reset_user_state_db(monkeypatch, tmp_path, "tutor_norm.db")

    merged = user_state.set_tutor_learner_profile(
        {
            "preferred_style": "INVALID",
            "last_route": "  ",
            "last_focus_topic": "",
            "recent_topics": ["a", "b", "a", "  ", "c"],
            "weak_concepts": ["x", "x", "y"],
        }
    )
    assert merged["preferred_style"] == "balanced"
    assert merged["last_route"] == "standard"
    assert merged["last_focus_topic"] == "general"
    # Stored value round-trips through KV without losing normalisation.
    profile = user_state.get_tutor_learner_profile()
    assert profile["preferred_style"] == "balanced"
    assert profile["last_route"] == "standard"
    assert profile["last_focus_topic"] == "general"
    assert "a" in profile["recent_topics"]
    assert "y" in profile["weak_concepts"]


def test_update_tutor_learner_profile_from_session_increments(tmp_path, monkeypatch):
    _reset_user_state_db(monkeypatch, tmp_path, "tutor_session.db")

    user_state.set_tutor_learner_profile(
        {"sessions_count": 2, "last_focus_topic": "old", "recent_topics": ["old"]}
    )

    updated = user_state.update_tutor_learner_profile_from_session(
        {
            "learner_profile": {
                "focus_topic": "new_topic",
                "preferred_style": "examples",
                "route": "guided",
                "weak_concepts": ["w1"],
                "due_review_count": 4,
            }
        }
    )
    assert updated["sessions_count"] == 3
    assert updated["preferred_style"] == "examples"
    assert updated["last_route"] == "guided"
    assert updated["last_focus_topic"] == "new_topic"
    assert updated["due_review_count"] == 4
    assert "new_topic" in updated["recent_topics"]
    assert "old" in updated["recent_topics"]


def test_user_state_concurrent_writes_no_loss(tmp_path, monkeypatch):
    _reset_user_state_db(monkeypatch, tmp_path, "concurrent.db")

    n_threads = 6
    per_thread = 100
    errors: list[BaseException] = []

    def worker(tid: int) -> None:
        try:
            for i in range(per_thread):
                user_state.add_note(
                    "topic",
                    user_state.topic_resource_id(f"t{tid}"),
                    f"thread={tid} idx={i}",
                )
        except BaseException as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [], f"worker exceptions: {errors!r}"
    rows = user_state.list_annotations(limit=n_threads * per_thread + 10)
    assert len(rows) == n_threads * per_thread
    # Per-thread distribution must match exactly — proves no lost writes under contention.
    by_thread: dict[int, int] = {}
    for r in rows:
        body = str(r.get("body") or "")
        if body.startswith("thread="):
            tid = int(body.split("=", 1)[1].split(" ", 1)[0])
            by_thread[tid] = by_thread.get(tid, 0) + 1
    assert by_thread == {t: per_thread for t in range(n_threads)}


# --- epoch-srs-overdue-soft-recovery-v1: registry DoD (due_queue / overdue) ---


def test_due_queue_summary_overdue_120_matches_display_contract(tmp_path, monkeypatch):
    """Integration: SQLite due rows → summary overflow caption for UI surfaces."""
    import json
    from datetime import datetime, timedelta, timezone

    from app.config import reset_settings_cache
    from app.knowledge_graph import JsonKnowledgeGraph
    from app.learner_state_scope import due_reviews_summary_for_kg

    db = tmp_path / "due_queue.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    monkeypatch.setattr(
        "app.user_state.get_current_learner_state_lineage",
        lambda: {"generation_id": "", "index_version": None},
    )
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()

    concepts = {f"c{i}": {"description": "", "prerequisites": []} for i in range(120)}
    kg_path = tmp_path / "kg120.json"
    kg_path.write_text(
        json.dumps({"concepts": concepts, "documents": {}, "edges": {}}, ensure_ascii=False),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(kg_path)
    now = datetime.now(timezone.utc)

    def seed(conn):
        for i in range(120):
            days_ago = max(1, 30 - (i % 30))
            nr = (now - timedelta(days=days_ago)).isoformat()
            conn.execute(
                """
                INSERT INTO spaced_repetition(
                    concept, easiness, interval_days, repetitions, next_review, last_review
                ) VALUES (?, 2.5, 1, 0, ?, ?)
                """,
                (f"c{i}", nr, nr),
            )
        conn.commit()

    user_state._with_db(seed)
    summary = due_reviews_summary_for_kg(kg)
    assert summary["count"] == 120
    assert summary["overflow_caption"] == "ещё 113 отложено"
    assert summary["overflow_mode"] is True
    assert len(summary["preview_concepts"]) == 7


def test_due_queue_summary_overdue_50_no_overflow_mode(tmp_path, monkeypatch):
    import json
    from datetime import datetime, timedelta, timezone

    from app.config import reset_settings_cache
    from app.knowledge_graph import JsonKnowledgeGraph
    from app.learner_state_scope import due_reviews_summary_for_kg

    db = tmp_path / "due_queue50.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    monkeypatch.setattr(
        "app.user_state.get_current_learner_state_lineage",
        lambda: {"generation_id": "", "index_version": None},
    )
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()

    concepts = {f"c{i}": {"description": "", "prerequisites": []} for i in range(50)}
    kg_path = tmp_path / "kg50.json"
    kg_path.write_text(
        json.dumps({"concepts": concepts, "documents": {}, "edges": {}}, ensure_ascii=False),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(kg_path)
    now = datetime.now(timezone.utc)

    def seed(conn):
        for i in range(50):
            nr = (now - timedelta(days=5)).isoformat()
            conn.execute(
                """
                INSERT INTO spaced_repetition(
                    concept, easiness, interval_days, repetitions, next_review, last_review
                ) VALUES (?, 2.5, 1, 0, ?, ?)
                """,
                (f"c{i}", nr, nr),
            )
        conn.commit()

    user_state._with_db(seed)
    summary = due_reviews_summary_for_kg(kg)
    assert summary["count"] == 50
    assert summary["overflow_mode"] is False
    assert summary["overflow_caption"] == "ещё 43 отложено"
