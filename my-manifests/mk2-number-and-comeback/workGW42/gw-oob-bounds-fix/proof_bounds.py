#!/usr/bin/env python3
"""Offline proof for GW42 out-of-hours decisions using synthetic inventory."""

import importlib.util
from pathlib import Path


GATEWAY_PATH = Path(__file__).parent / "gwtest" / "container" / "bland_gateway.py"
SPEC = importlib.util.spec_from_file_location("gw42_proof_gateway", GATEWAY_PATH)
gateway = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gateway)


def slot(start, end):
    return {"start": f"08/04/2026 {start}", "end": f"08/04/2026 {end}"}


full_day = [
    slot("09:00 AM", "09:30 AM"),
    slot("03:30 PM", "04:00 PM"),
    slot("04:30 PM", "05:00 PM"),
]
remaining = full_day[1:]

partial = gateway.availability_envelope(remaining)
gateway.add_out_of_hours_flag(
    partial, remaining, {"from": "today", "after": "03:00 PM"}, full_day
)

three_am = gateway.availability_envelope([])
gateway.add_out_of_hours_flag(
    three_am, [], {"from": "today", "after": "3:00 am"}, full_day
)

print(f"CASE=partial-day-3pm OUT_OF_HOURS={str(partial['out_of_hours']).lower()}")
print(f"CASE=3am OUT_OF_HOURS={str(three_am['out_of_hours']).lower()}")

assert partial["count"] == 2
assert partial["out_of_hours"] is False
assert three_am["out_of_hours"] is True
