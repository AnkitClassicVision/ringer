#!/usr/bin/env python3
"""Offline proof of the fixed reference-window clock-bound decision."""

import importlib.util
import sys
import types
from pathlib import Path


capability_registry = types.ModuleType("capability_registry")
capability_registry.QueryError = Exception
capability_registry.load_manifest = lambda: {}
capability_registry.prepare_query = lambda *args, **kwargs: None
capability_registry.render_query_result = lambda *args, **kwargs: None
sys.modules["capability_registry"] = capability_registry

spec = importlib.util.spec_from_file_location(
    "fixed_bland_gateway", Path(__file__).with_name("fixed-bland_gateway.py")
)
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)

REFERENCE_SLOTS = [
    {"start": "08/04/2026 10:30 AM", "end": "08/04/2026 11:00 AM"},
    {"start": "08/05/2026 04:45 PM", "end": "08/05/2026 05:15 PM"},
]
PARTIAL_DAY_SLOTS = [
    {"start": "08/04/2026 03:30 PM", "end": "08/04/2026 04:00 PM"},
]


def prove(name, body, request_slots):
    envelope = {}
    gateway.add_out_of_hours_flag(envelope, request_slots, body, REFERENCE_SLOTS)
    value = str(envelope["out_of_hours"]).lower()
    print(f"CASE={name} OUT_OF_HOURS={value}")


prove("partial-day-3pm", {"after": "03:00 PM"}, PARTIAL_DAY_SLOTS)
prove("3am-after", {"after": "03:00 am"}, REFERENCE_SLOTS)
prove("2pm-anchor", {"time_pref": "anchor=14:00"}, REFERENCE_SLOTS)
