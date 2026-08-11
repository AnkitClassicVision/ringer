#!/usr/bin/env python3
from datetime import date, timedelta
import importlib.util
import json
import os
from pathlib import Path
import sys


path = Path(__file__).with_name("fixed-bland_gateway.py")
sys.path.insert(0, str(Path(__file__).with_name("gwtest") / "container"))
spec = importlib.util.spec_from_file_location("gw54_proof_gateway", path)
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)


def anchor(time_pref, verbatim):
    normalized = gateway.enforce_verbatim_meridiem_authority(time_pref, verbatim)
    _, minutes = gateway._normalized_anchor_clock(normalized)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


today = date.today()
probe = today + timedelta(days=2)
friday = probe + timedelta(days=(4 - probe.weekday()) % 7)
_from_value = friday.strftime("%Y-%m-%d")

print(f"CASE=strip-invented-am ANCHOR={anchor('anchor=3:00 am', 'What about either 3 or 4')}")
print(f"CASE=keep-stated-pm ANCHOR={anchor('anchor=3:00 pm', '3 pm works')}")
print(f"CASE=keep-stated-morning ANCHOR={anchor('anchor=9:00 am', '9 in the morning')}")
print(f"CASE=spelled-hour-strip ANCHOR={anchor('anchor=4:00 am', 'four works for me')}")
print(f"CASE=bare-inference-unchanged ANCHOR={anchor('anchor=5:00', 'around 5')}")

os.environ["CVC_HOURS_JSON"] = json.dumps({"stores": {"711": {"mon": ["09:00", "17:00"], "tue": ["09:00", "17:00"], "wed": ["09:00", "17:00"], "thu": ["09:00", "17:00"], "fri": ["09:00", "17:00"]}}})
saturday = friday + timedelta(days=1)
print(f"CASE=closed-day-weekend CLOSED={str(gateway.availability_window_closed('711', saturday, saturday)).lower()}")
print(f"CASE=open-day-not-closed CLOSED={str(gateway.availability_window_closed('711', friday, friday)).lower()}")
