#!/usr/bin/env python3
"""Standalone offline proof for GW48 slot ordering."""

import importlib.util
import sys
import types
from pathlib import Path


stub = types.ModuleType("capability_registry")
stub.QueryError = Exception
stub.load_manifest = lambda: {}
stub.prepare_query = lambda *args, **kwargs: None
stub.render_query_result = lambda *args, **kwargs: None
sys.modules["capability_registry"] = stub

path = Path(__file__).with_name("deployed-bland_gateway.py")
spec = importlib.util.spec_from_file_location("gw48_gateway", path)
gateway = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(gateway)

slots = [
    {"start": "08/07/2026 11:00 AM"},
    {"start": "08/07/2026 11:15 AM"},
    {"start": "08/07/2026 11:30 AM"},
    {"start": "08/07/2026 11:45 AM"},
    {"start": "08/07/2026 02:00 PM"},
]


def clock(slot):
    return slot["start"].split(" ", 1)[1].lower()


print(f"CASE=anchor-1115 FIRST={clock(gateway._order_availability_slots(slots, 'anchor=11:15 AM')[0])}")
print(f"CASE=anchor-2pm FIRST={clock(gateway._order_availability_slots(slots, 'anchor=2 pm')[0])}")
print(f"CASE=latest FIRST={clock(gateway._order_availability_slots(slots, 'latest')[0])}")
print(f"CASE=none FIRST={clock(gateway._order_availability_slots(slots, 'none')[0])}")
