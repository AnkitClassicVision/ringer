#!/usr/bin/env python3
from datetime import date, datetime, timedelta
import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "gwtest" / "container"))
spec = importlib.util.spec_from_file_location("gw55_gateway", ROOT / "fixed-bland_gateway.py")
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)


today = date.today()
ctx_date = today + timedelta(days=21)
ctx = ctx_date.strftime("%m/%d/%Y 10:30 am")
thu = ctx_date - timedelta(days=ctx_date.weekday()) + timedelta(days=3)

year, month = today.year, today.month
if today.day >= 27:
    month += 1
    if month == 13:
        year, month = year + 1, 1
o27 = date(year, month, 27)
next_thu = today + timedelta(days=(3 - today.weekday()) % 7 or 7)
gateway._eastern_today = lambda: datetime.combine(today, datetime.min.time())


def resolved(from_text, verbatim, context=ctx):
    body = {
        "store": "711",
        "from": from_text,
        "to": from_text,
        "user_verbatim": verbatim,
        "context_date": context,
    }
    argv, _ = gateway.build_argv("/availability", body)
    value = argv[argv.index("--from") + 1]
    return datetime.strptime(value, "%m/%d/%Y").date().isoformat()


print(f"CASE=ordinal-dropped FROM={resolved('thursday next week', 'No Thursday the 27')} (from='thursday next week', verbatim='No Thursday the 27', context=ctx)")
print(f"CASE=ordinal-present-unchanged FROM={resolved('thursday the 27', 'No Thursday the 27')} (from='thursday the 27', verbatim='No Thursday the 27', context=ctx)")
print(f"CASE=that-weekday FROM={resolved('thursday', 'How late can I come in that Thursday')} (from='thursday', verbatim='How late can I come in that Thursday', context=ctx)")
print(f"CASE=bare-weekday-no-anaphor FROM={resolved('thursday', 'how about thursday?')} (from='thursday', verbatim='how about thursday?', context=ctx - no override)")
print(f"CASE=clock-not-ordinal FROM={resolved('thursday', 'thursday at 4:27 pm?', '')} (from='thursday', verbatim='thursday at 4:27 pm?', context='' - the 27 in a clock time must not trigger)")
print(f"CASE=ordinal-beats-anaphor FROM={resolved('thursday', 'that Thursday, the 27th')} (from='thursday', verbatim='that Thursday, the 27th', context=ctx)")


assert resolved("thursday next week", "No Thursday the 27") == o27.isoformat()
assert resolved("thursday", "How late can I come in that Thursday") == thu.isoformat()
assert resolved("thursday", "how about thursday?") == next_thu.isoformat()
