import importlib
import os
import sys
import types
from datetime import datetime

import pytest


registry = types.ModuleType("capability_registry")
registry.QueryError = type("QueryError", (Exception,), {})
registry.load_manifest = lambda *args, **kwargs: {}
registry.prepare_query = lambda *args, **kwargs: None
registry.render_query_result = lambda *args, **kwargs: None
sys.modules["capability_registry"] = registry

os.environ["ECP_TENANT_ID"] = "mott"
os.environ["ECP_RAW_TEXT_DATES"] = "1"
gateway = importlib.import_module("bland_gateway")


@pytest.fixture(autouse=True)
def freeze_today(monkeypatch):
    monkeypatch.setattr(
        gateway, "_eastern_today", lambda: datetime(2026, 7, 29, 12, 0, 0)
    )


def test_availability_envelope_adds_day_names():
    slots = [
        {"start": "07/30/2026 10:45 am"},
        {"start": "07/31/2026 1:00 pm"},
    ]

    result = gateway.availability_envelope(slots)

    assert result["first_day_name"] == "Thursday"
    assert result["slot_day_names"] == ["Thursday", "Friday"]
    assert result["slots"][0]["day_name"] == "Thursday"
    assert result["slots"][1]["day_name"] == "Friday"


def test_single_explicit_date_is_not_a_conflict():
    result = gateway.extract_date_from_text("july 31st")
    assert result == "07/31/2026"
    assert isinstance(result, str)


def test_agreeing_compound_is_not_a_conflict():
    assert gateway.extract_date_from_text("thursday july 31st") == "07/31/2026"


def test_conflicting_compound_has_descriptions_with_weekdays():
    result = gateway.extract_date_from_text("tomorrow the 31st")

    assert isinstance(result, tuple)
    assert result[0] == "conflict"
    assert result[1:3] == ("07/30/2026", "07/31/2026")
    assert "Thursday" in result[3]
    assert "Friday" in result[4]


def test_conflicting_weekday_and_date():
    result = gateway.extract_date_from_text("monday august 5th")

    assert result[0] == "conflict"
    assert set(result[1:3]) == {"08/03/2026", "08/05/2026"}
    assert "Monday" in result[3] + result[4]
    assert "Wednesday" in result[3] + result[4]


def test_negation_leaves_one_date():
    assert gateway.extract_date_from_text("not the 30th, the 31st") == "07/31/2026"


def test_clamp_wires_conflict_without_overriding_dates(monkeypatch):
    monkeypatch.setattr(
        gateway,
        "_fetch_conversation",
        lambda call_id: [{"sender": "USER", "message": "tomorrow the 31st"}],
    )
    body = {"callID": "abcdefgh"}

    gateway.clamp_availability_range(body)

    assert body["date_conflict"][0] == "conflict"
    assert "from" not in body
    assert "to" not in body
