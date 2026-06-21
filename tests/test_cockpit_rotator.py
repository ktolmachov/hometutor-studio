"""Юнит-тесты ротатора кабины (без Streamlit runtime)."""

from app.ui.cockpit_rotator import (
    DEFAULT_SLOTS,
    next_slot_index,
    normalize_slot_index,
    slot_id_at,
)


def test_normalize_slot_index_clamps():
    assert normalize_slot_index(0) == 0
    assert normalize_slot_index(3) == 0
    assert normalize_slot_index(-1) == 2
    assert normalize_slot_index("x") == 0


def test_next_slot_index_wraps():
    assert next_slot_index(0, 1) == 1
    assert next_slot_index(len(DEFAULT_SLOTS) - 1, 1) == 0
    assert next_slot_index(0, -1) == len(DEFAULT_SLOTS) - 1


def test_slot_id_at():
    assert slot_id_at(0) == DEFAULT_SLOTS[0]
    assert slot_id_at(100) == DEFAULT_SLOTS[100 % len(DEFAULT_SLOTS)]


def test_default_slots_tuple():
    assert len(DEFAULT_SLOTS) == 3
