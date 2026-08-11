#!/usr/bin/env python3
"""Offline proof for the lane-49 anchor_exact availability contract."""

import importlib.util
from pathlib import Path
import sys


path = Path(__file__).with_name("deployed-bland_gateway.py")
sys.path.insert(0, str(Path(__file__).with_name("gwtest") / "container"))
spec = importlib.util.spec_from_file_location("proof_gateway", path)
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)

slots = [
    {"start": "08/06/2026 10:30 AM", "end": "08/06/2026 11:00 AM"},
    {"start": "08/06/2026 10:45 AM", "end": "08/06/2026 11:15 AM"},
    {"start": "08/06/2026 11:00 AM", "end": "08/06/2026 11:30 AM"},
]


def result(pref=None):
    fresh = [dict(slot) for slot in slots]
    return gateway.availability_envelope(fresh, pref or "")


exact = result("anchor=10:45 AM")
offgrid = result("anchor=10:40 AM")
latest = result("latest")
none = result()

assert exact["anchor_exact"] is True
assert exact["anchor_requested"] == "10:45 am"
assert exact["first_start"].endswith("10:45 AM")
assert offgrid["anchor_exact"] is False
assert latest.get("anchor_exact") is not True
assert none.get("anchor_exact") is not True

print("CASE=exact ANCHOR_EXACT=true FIRST=10:45 am")
print("CASE=offgrid ANCHOR_EXACT=false")
print("CASE=latest ANCHOR_EXACT=false")
print("CASE=none ANCHOR_EXACT=false")
