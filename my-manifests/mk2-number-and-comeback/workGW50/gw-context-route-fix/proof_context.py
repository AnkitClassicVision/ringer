#!/usr/bin/env python3
"""Offline GW50 contract proof."""

import importlib.util
from pathlib import Path
import sys


path = Path(__file__).with_name("deployed-bland_gateway.py")
sys.path.insert(0, str(Path(__file__).with_name("gwtest") / "container"))
spec = importlib.util.spec_from_file_location("gw50_proof", path)
gateway = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(gateway)
gateway._RAW_TEXT_DATES = False

weekday = {
    "from": "Monday that week",
    "to": "Monday that week",
    "context_date": "08/18/2026 10:30 am",
}
gateway.clamp_availability_range(weekday)
print(f"CASE=anaphora-context FROM={gateway.datetime.strptime(weekday['from'], '%m/%d/%Y'):%Y-%m-%d}")

week = {"from": "that week", "to": "that week", "context_date": "08/18/2026"}
gateway.clamp_availability_range(week)
print(
    "CASE=bare-that-week "
    f"FROM={gateway.datetime.strptime(week['from'], '%m/%d/%Y'):%Y-%m-%d} "
    f"TO={gateway.datetime.strptime(week['to'], '%m/%d/%Y'):%Y-%m-%d}"
)

pref = "anchor=10:30 am"
cases = {
    "exact": {"ok": True, "result": gateway.availability_envelope(
        [{"start": "08/17/2026 10:30 AM", "end": "08/17/2026 11:00 AM"}], pref)},
    "closest": {"ok": True, "result": gateway.availability_envelope(
        [{"start": "08/17/2026 11:00 AM", "end": "08/17/2026 11:30 AM"}], pref)},
    "none": {"ok": True, "result": gateway.availability_envelope([], pref)},
    "error": {"ok": False, "error": "offline-proof"},
}
for name, payload in cases.items():
    result = gateway.finalize_anchor_route(payload, pref)["result"]
    print(f"CASE=route-{name} ROUTE={result['anchor_route']}")
