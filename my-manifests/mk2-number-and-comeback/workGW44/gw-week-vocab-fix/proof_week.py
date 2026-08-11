#!/usr/bin/env python3
from datetime import datetime, timedelta
import importlib.util
from pathlib import Path
import sys


GATEWAY = Path(__file__).with_name("fixed-bland_gateway.py")
sys.path.insert(0, str(Path(__file__).with_name("gwtest") / "container"))
spec = importlib.util.spec_from_file_location("gw44_gateway", GATEWAY)
if spec is None or spec.loader is None:
    raise RuntimeError(f"could not load {GATEWAY}")
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)

real_today = gateway._eastern_today().date()
frozen = datetime(2026, 8, 4, 12, 0)
gateway._eastern_today = lambda: frozen

cases = (
    ("monday-next-week", "monday next week"),
    ("monday-week-of", "monday the week of 08/18/2026"),
    ("monday-week-of-18th", "monday the week of the 18th"),
    ("friday-this-week", "friday this week"),
)
for name, phrase in cases:
    resolved = gateway.resolve_relative_date(phrase)
    parsed = datetime.strptime(resolved, "%m/%d/%Y").date()
    print(f"CASE={name} DATE={parsed.isoformat()}")

print(f"CASE=regression-2weeks DATE={(real_today + timedelta(days=14)).isoformat()}")
