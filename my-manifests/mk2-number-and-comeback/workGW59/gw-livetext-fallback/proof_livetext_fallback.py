#!/usr/bin/env python3
from datetime import datetime
import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "gwtest" / "container"))
spec = importlib.util.spec_from_file_location("gw59_proof_gateway", ROOT / "fixed-bland_gateway.py")
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)
gateway._eastern_today = lambda: datetime(2026, 8, 5, 12, 0)


def run(verbatim, live, **overrides):
    body = {
        "store": "711", "from": "thursday", "to": "thursday",
        "user_verbatim": verbatim, "user_text": live,
        "after": "none", "before": "none", "time_pref": "none",
    }
    body.update(overrides)
    gateway.clamp_availability_range(body)
    return body


zh = run("一午", "下午")
print(f"CASE=garbled-zh-daypart AFTER={gateway._clock_minutes(zh['after']) // 60:02d}:00")

winner = run("晚上", "早上")
print(f"CASE=verbatim-wins AFTER={gateway._clock_minutes(winner['after']) // 60:02d}:00")

later = run("一点晚", "晚一点", context_date="08/06/2026 10:30 am")
assert gateway._clock_minutes(later["after"]) > gateway._clock_minutes("10:30 am")
print("CASE=garbled-later-floor AFTER_GT=10:30")

empty = run("", "")
print(f"CASE=both-empty UNCHANGED={str((empty['after'], empty['before']) == ('none', 'none')).lower()}")

explicit = run("一午", "下午", after="03:00 pm")
print(f"CASE=explicit-still-wins AFTER={gateway._clock_minutes(explicit['after']) // 60:02d}:00")

english = run("morninng typo mrnng", "friday morning")
print(f"CASE=english-garble-window BEFORE={gateway._clock_minutes(english['before']) // 60:02d}:00")
