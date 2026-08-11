#!/usr/bin/env python3
from datetime import date, datetime, timedelta
import importlib.util
import logging
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "gwtest" / "container"))
spec = importlib.util.spec_from_file_location("gw52_proof_gateway", ROOT / "fixed-bland_gateway.py")
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)
logging.disable(logging.CRITICAL)

today = date.today()
gateway._eastern_today = lambda: datetime.combine(today, datetime.min.time())
ctx = today + timedelta(days=14)
ctx_str = ctx.strftime("%m/%d/%Y 10:30 am")
mon = ctx - timedelta(days=ctx.weekday())
tue = mon + timedelta(days=1)
next_mon = today - timedelta(days=today.weekday()) + timedelta(days=7)


def window(from_text, verbatim, context=ctx_str):
    body = {
        "store": "958",
        "from": from_text,
        "to": from_text,
        "user_verbatim": verbatim,
        "context_date": context,
    }
    argv, _ = gateway.build_argv("/availability", body)
    return argv[argv.index("--from") + 1], argv[argv.index("--to") + 1]


def iso(value):
    return datetime.strptime(value, "%m/%d/%Y").date().isoformat()


next_week_wording = window("monday next week", "What about Monday that week?")[0]
assert next_week_wording == mon.strftime("%m/%d/%Y")
print(f"CASE=anaphora-next-week-wording FROM={iso(next_week_wording)}")
week_of = "monday the week of " + ctx.strftime("%m/%d/%Y")
week_of_result = window(week_of, "What about Monday that week?")[0]
assert week_of_result == mon.strftime("%m/%d/%Y")
print(f"CASE=anaphora-week-of-wording FROM={iso(week_of_result)}")
wrong_week = "monday the week of " + (ctx - timedelta(days=7)).strftime("%m/%d/%Y")
wrong_week_result = window(wrong_week, "What about Monday that week?")[0]
assert wrong_week_result == mon.strftime("%m/%d/%Y")
print(f"CASE=anaphora-wrong-week-of FROM={iso(wrong_week_result)}")
no_anaphor = window("monday next week", "how about monday next week?")[0]
assert no_anaphor == next_mon.strftime("%m/%d/%Y")
print(f"CASE=no-anaphor-next-week FROM={iso(no_anaphor)}")
tuesday_result = window("tuesday", "could we do Tuesday that week")[0]
assert tuesday_result == tue.strftime("%m/%d/%Y")
print(f"CASE=anaphora-tuesday FROM={iso(tuesday_result)}")
no_context = window("monday next week", "What about Monday that week?", "")[0]
assert no_context == next_mon.strftime("%m/%d/%Y")
print(f"CASE=anaphora-no-context FROM={iso(no_context)}")
full_week = window("that week", "anything that week?")
assert full_week == (
    max(mon, today).strftime("%m/%d/%Y"),
    (mon + timedelta(days=6)).strftime("%m/%d/%Y"),
)
print(f"CASE=anaphora-no-weekday WINDOW={iso(full_week[0])}..{iso(full_week[1])}")
