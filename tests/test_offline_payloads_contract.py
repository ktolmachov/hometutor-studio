from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from app.api_models import AskSource


FIXTURES_DIR = Path("tests/e2e/fixtures/offline_payloads")


class Scenario03Payload(BaseModel):
    topic: str
    plan: list[str]
    learner_state: dict[str, str]


class Scenario04Question(BaseModel):
    id: str
    q: str
    options: list[str]
    correct: str
    explanation: str
    concept: str
    level: str


class Scenario04Payload(BaseModel):
    success: bool
    scope: str
    identifier: str
    num_questions: int
    motivation: str
    motivation_detail: str
    adaptive_level: str
    mastery_estimate_percent: int
    xp_max: int
    questions: list[Scenario04Question]


class Scenario06Deck(BaseModel):
    id: int
    name: str
    card_count: int
    due_count: int


class Scenario06Card(BaseModel):
    id: int
    deck_id: int
    deck_name: str
    front: str
    back: str
    tags: str
    interval_days: int
    repetitions: int
    ease_factor: float
    next_review: str


class Scenario06Payload(BaseModel):
    deck: Scenario06Deck
    cards: list[Scenario06Card]


class Scenario07Payload(BaseModel):
    quiz_mastery_rows: list[dict[str, float | int | str]]
    mastery_vector: dict[str, float]
    weekly_goals: dict[str, int]
    gamification: dict[str, int]


class Scenario09Block(BaseModel):
    title: str
    minutes: int
    why: str
    action: str


class Scenario09Payload(BaseModel):
    date: str
    blocks: list[Scenario09Block]
    diff_since_last: list[str]
    summary: str


PAYLOAD_TO_MODEL: dict[str, type[BaseModel] | None] = {
    "scenario_03.json": Scenario03Payload,
    "scenario_04.json": Scenario04Payload,
    "scenario_06.json": Scenario06Payload,
    "scenario_07.json": Scenario07Payload,
    "scenario_08.json": None,  # handled via AskSource list below
    "scenario_09.json": Scenario09Payload,
}


@pytest.mark.parametrize("payload_file", sorted(PAYLOAD_TO_MODEL.keys()))
def test_offline_payload_contract(payload_file: str) -> None:
    payload = json.loads((FIXTURES_DIR / payload_file).read_text(encoding="utf-8"))
    try:
        if payload_file == "scenario_08.json":
            sources = payload.get("sources")
            if not isinstance(sources, list):
                raise AssertionError("scenario_08.json: missing 'sources' list")
            for source in sources:
                AskSource.model_validate(source)
            return
        model = PAYLOAD_TO_MODEL[payload_file]
        assert model is not None
        model.model_validate(payload)
    except ValidationError as exc:
        raise AssertionError(f"{payload_file}: contract drift detected\n{exc}") from exc
