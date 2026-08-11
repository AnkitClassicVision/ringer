from datetime import datetime
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def gateway():
    path = Path(__file__).resolve().parents[1] / "container" / "bland_gateway.py"
    spec = importlib.util.spec_from_file_location("refwindow_gateway", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REFERENCE_SLOTS = [
    {"start": "08/04/2026 10:30 AM", "end": "08/04/2026 11:00 AM"},
    {"start": "08/05/2026 04:45 PM", "end": "08/05/2026 05:15 PM"},
]
PARTIAL_DAY_SLOTS = [
    {"start": "08/04/2026 03:30 PM", "end": "08/04/2026 04:00 PM"},
]


def _flag(gateway, body, slots=REFERENCE_SLOTS):
    envelope = {}
    gateway.add_out_of_hours_flag(envelope, slots, body, REFERENCE_SLOTS)
    return envelope["out_of_hours"]


def test_partial_day_3pm_uses_reference_bounds(gateway):
    assert _flag(gateway, {"after": "03:00 PM"}, PARTIAL_DAY_SLOTS) is False


def test_3am_after_remains_out_of_hours_even_with_later_slots(gateway):
    assert _flag(gateway, {"after": "03:00 am"}) is True


def test_11pm_before_is_out_of_hours(gateway):
    assert _flag(gateway, {"before": "11:00 pm"}) is True


def test_3am_anchor_is_out_of_hours(gateway):
    assert _flag(gateway, {"time_pref": "anchor=03:00"}) is True


def test_2pm_anchor_is_in_hours(gateway):
    assert _flag(gateway, {"time_pref": "anchor=14:00"}) is False


def test_reference_window_is_fixed_today_through_today_plus_13(gateway, monkeypatch):
    monkeypatch.setattr(gateway, "_eastern_today", lambda: datetime(2026, 8, 4, 9, 0))
    body = gateway.availability_reference_body({
        "store": "711", "from": "08/04/2026", "to": "08/04/2026",
        "after": "03:00 PM", "slot_minutes": "30",
    })
    assert body == {
        "store": "711", "slot_minutes": "30",
        "from": "08/04/2026", "to": "08/17/2026",
    }
