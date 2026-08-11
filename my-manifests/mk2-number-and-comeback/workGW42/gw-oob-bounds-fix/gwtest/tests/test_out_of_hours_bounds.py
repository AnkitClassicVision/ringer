import datetime
import importlib.util
from pathlib import Path


def load_gateway():
    path = Path(__file__).parents[1] / "container" / "bland_gateway.py"
    spec = importlib.util.spec_from_file_location("gw42_bland_gateway", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def slot(day, start, end):
    return {"start": f"{day} {start}", "end": f"{day} {end}"}


def decide(gateway, filtered, body, unfiltered):
    envelope = gateway.availability_envelope(filtered)
    return gateway.add_out_of_hours_flag(envelope, filtered, body, unfiltered)


def test_partial_day_after_3pm_has_slots_and_is_not_out_of_hours():
    gateway = load_gateway()
    gateway._eastern_today = lambda: datetime.datetime(2026, 8, 4, 14, 0)
    remaining = [slot("08/04/2026", "03:30 PM", "04:00 PM")]
    full_day = [slot("08/04/2026", "09:00 AM", "09:30 AM"), *remaining]

    result = decide(gateway, remaining, {"from": "today", "after": "03:00 PM"}, full_day)

    assert result["count"] == 1
    assert result["out_of_hours"] is False


def test_uppercase_3pm_parses_like_lowercase_unpadded_3pm():
    gateway = load_gateway()
    assert gateway._clock_minutes("03:00 PM") == gateway._clock_minutes("3:00 pm")


def test_full_window_bounds_regression():
    gateway = load_gateway()
    slots = [
        slot("08/04/2026", "09:00 AM", "09:30 AM"),
        slot("08/05/2026", "03:30 PM", "04:00 PM"),
        slot("08/06/2026", "04:30 PM", "05:00 PM"),
    ]
    result = decide(gateway, slots[1:], {"after": "3:00 pm"}, slots)
    assert gateway.availability_clock_bounds(slots) == (9 * 60, 17 * 60)
    assert result["out_of_hours"] is False


def test_3am_remains_out_of_hours_when_filtered_inventory_is_empty():
    gateway = load_gateway()
    full_day = [
        slot("08/04/2026", "09:00 AM", "09:30 AM"),
        slot("08/04/2026", "04:30 PM", "05:00 PM"),
    ]
    result = decide(gateway, [], {"from": "today", "after": "3:00 am"}, full_day)
    assert result["out_of_hours"] is True
    assert result["requested_clock"] == "3:00 am"
