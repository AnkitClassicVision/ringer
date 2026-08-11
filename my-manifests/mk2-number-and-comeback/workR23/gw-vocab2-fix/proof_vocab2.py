#!/usr/bin/env python3
"""Offline acceptance proof for Mott gateway lane 51."""
from datetime import datetime
import importlib.util
import logging
from pathlib import Path
import sys


path = Path(__file__).with_name("deployed-bland_gateway.py")
sys.path.insert(0, str(Path(__file__).with_name("gwtest") / "container"))
spec = importlib.util.spec_from_file_location("gw51_gateway", path)
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)
logging.disable(logging.CRITICAL)
gateway._eastern_today = lambda: datetime(2026, 8, 5, 12, 0)

bounds = (9 * 60, 17 * 60)
print(f"CASE=around-five ANCHOR={gateway._clock_minutes('around 5', bounds) // 60:02d}:00")
print(f"CASE=at-seven ANCHOR={gateway._clock_minutes('at 7') // 60:02d}:00")
nine_thirty = gateway._clock_minutes("9:30", bounds)
print(f"CASE=nine-thirty-bare ANCHOR={nine_thirty // 60:02d}:{nine_thirty % 60:02d}")

slots = [
    {"start": "08/05/2026 09:00 AM", "end": "08/05/2026 09:30 AM"},
    {"start": "08/05/2026 04:30 PM", "end": "08/05/2026 05:00 PM"},
]
envelope = {}
gateway.add_out_of_hours_flag(envelope, slots, {"after": "midnight"}, slots)
print(f"CASE=midnight OOB={str(envelope['out_of_hours']).lower()}")

fortnight = datetime.strptime(gateway.resolve_relative_date("a fortnight"), "%m/%d/%Y")
eleven = datetime.strptime(gateway.resolve_relative_date("in eleven days"), "%m/%d/%Y")
print(f"CASE=fortnight DATE={fortnight.date().isoformat()}")
print(f"CASE=eleven-days DATE={eleven.date().isoformat()}")

week = {
    "from": "the week after that",
    "to": "the week after that",
    "context_date": "08/18/2026",
}
gateway.clamp_availability_range(week)
week_from = datetime.strptime(week["from"], "%m/%d/%Y").date().isoformat()
print(f"CASE=week-after-that FROM={week_from}")

month = {"from": "end of next month", "to": "end of next month"}
gateway.clamp_availability_range(month)
print(f"CASE=end-next-month WINDOW={str(month['from'] != month['to']).lower()}")
