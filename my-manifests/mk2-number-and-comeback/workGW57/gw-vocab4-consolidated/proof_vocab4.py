#!/usr/bin/env python3
from datetime import date, datetime, timedelta
import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "gwtest" / "container"))
spec = importlib.util.spec_from_file_location("gw57_gateway", ROOT / "fixed-bland_gateway.py")
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)

today = date.today()
wan_anchor = today + timedelta(days=14)
wan = wan_anchor - timedelta(days=wan_anchor.weekday())
ctx_date = today + timedelta(days=21)
ctx = ctx_date.strftime("%m/%d/%Y 10:30 am")
fw = ctx_date - timedelta(days=ctx_date.weekday()) + timedelta(days=7)
sdnw = ctx_date + timedelta(days=7)
next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
eom_lo = max(today, today.replace(day=25))
bnm_lo = next_month


def resolved(text, **extra):
    body = {
        "from": text, "to": text, "user_verbatim": text,
        "after": "none", "before": "none", "time_pref": "none",
    }
    body.update(extra)
    gateway.clamp_availability_range(body)
    return body


assert datetime.strptime(resolved("week after next")["from"], "%m/%d/%Y").date() == max(wan, today)
assert datetime.strptime(resolved("the following week", context_date=ctx)["from"], "%m/%d/%Y").date() == fw
assert datetime.strptime(resolved("same day next week", context_date=ctx)["from"], "%m/%d/%Y").date() == sdnw
assert datetime.strptime(resolved("end of the month")["from"], "%m/%d/%Y").date() == eom_lo
assert datetime.strptime(resolved("beginning of next month")["from"], "%m/%d/%Y").date() == bnm_lo
assert resolved("after lunch")["after"] == "01:00 pm"
assert (resolved("lunchtime")["after"], resolved("lunchtime")["before"]) == ("11:00 am", "02:00 pm")
assert resolved("after work")["after"] == "04:00 pm"
assert resolved("first thing")["before"] == "12:00 pm"
between = resolved("between 2 and 4")
assert (between["after"], between["before"]) == ("02:00 pm", "04:00 pm")
assert resolved("no earlier than 3")["after"] == "03:00 pm"
assert resolved("before noon")["before"] == "12:00 pm"
assert resolved("half past four")["time_pref"] == "anchor=16:30"
assert resolved("quarter to five")["time_pref"] == "anchor=16:45"
explicit = resolved("between 2 and 4", after="03:00 pm")
assert (explicit["after"], explicit["before"]) == ("03:00 pm", "none")

print(f"CASE=week-after-next FROM={max(wan, today).isoformat()}")
print(f"CASE=following-week FROM={fw.isoformat()} (context={ctx})")
print(f"CASE=same-day-next-week FROM={sdnw.isoformat()} (context={ctx})")
print(f"CASE=end-of-month FROM={eom_lo.isoformat()}")
print(f"CASE=beginning-next-month FROM={bnm_lo.isoformat()}")
print("CASE=after-lunch AFTER=13:00")
print("CASE=lunchtime WINDOW=11:00-14:00")
print("CASE=after-work AFTER=16:00")
print("CASE=first-thing BEFORE=12:00")
print("CASE=between-2-and-4 AFTER=14:00 BEFORE=16:00")
print("CASE=no-earlier-than-3 AFTER=15:00")
print("CASE=before-noon BEFORE=12:00")
print("CASE=half-past-four ANCHOR=16:30")
print("CASE=quarter-to-five ANCHOR=16:45")
print("CASE=explicit-kept AFTER=15:00 (verbatim='between 2 and 4', after='03:00 pm' - extraction wins, no override)")
