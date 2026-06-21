from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from skills_router import load_policy, recommend


def test_recommends_streamlit_for_ui_path() -> None:
    recs = recommend(
        paths=["app/ui/main.py"],
        policy={
            "rules": [
                {
                    "skill": "developing-with-streamlit",
                    "path_prefixes": ["app/ui/"],
                    "reason": "ui",
                }
            ]
        },
    )
    assert [r.skill for r in recs] == ["developing-with-streamlit"]
    assert recs[0].matched_by == "path_prefix:app/ui/"


def test_recommends_by_keyword_without_paths() -> None:
    recs = recommend(
        text="Add Playwright smoke for the sync flow",
        policy={"rules": [{"skill": "playwright-best-practices", "keywords": ["playwright"]}]},
    )
    assert recs[0].skill == "playwright-best-practices"


def test_deduplicates_skill_recommendations() -> None:
    recs = recommend(
        paths=["app/ui/main.py"],
        text="streamlit st.button",
        policy={
            "rules": [
                {
                    "skill": "developing-with-streamlit",
                    "path_prefixes": ["app/ui/"],
                    "keywords": ["streamlit"],
                },
                {"skill": "developing-with-streamlit", "keywords": ["st."]},
            ]
        },
    )
    assert [r.skill for r in recs] == ["developing-with-streamlit"]


def test_default_policy_loads() -> None:
    policy = load_policy()
    assert policy["rules"]
