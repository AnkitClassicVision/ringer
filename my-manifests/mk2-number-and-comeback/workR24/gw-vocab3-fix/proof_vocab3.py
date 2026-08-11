#!/usr/bin/env python3
from calendar import monthrange
from datetime import date, timedelta
import importlib.util
from pathlib import Path
import sys


def load_gateway():
    path = Path(__file__).with_name("fixed-bland_gateway.py")
    sys.path.insert(0, str(Path(__file__).with_name("gwtest") / "container"))
    spec = importlib.util.spec_from_file_location("vocab3_proof_gateway", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def nearest_future_day(today, day):
    year, month = today.year, today.month
    if today.day >= day:
        month += 1
        if month == 13:
            year, month = year + 1, 1
    while day > monthrange(year, month)[1]:
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return date(year, month, day)


def iso_date(value):
    return date.fromisoformat(value[6:10] + "-" + value[0:2] + "-" + value[3:5]).isoformat()


gateway = load_gateway()
today = date.today()
fortnight = gateway.extract_date_from_text("not this wk, fortnight from now")
fortnight_article = gateway.extract_date_from_text("a fortnight from now")
twenty_seventh = gateway.extract_date_from_text("I meant the twenty-seventh")
third = gateway.extract_date_from_text("the third")
tail_end = gateway.extract_date_from_text("tail end of next month")
regular_end = gateway.extract_date_from_text("end of next month")
fortnightly = gateway.extract_date_from_text("see me fortnightly")

expected_fortnight = today + timedelta(days=14)
expected_twenty_seventh = nearest_future_day(today, 27)
expected_third = nearest_future_day(today, 3)
assert iso_date(fortnight) == expected_fortnight.isoformat()
assert iso_date(fortnight_article) == expected_fortnight.isoformat()
assert iso_date(twenty_seventh) == expected_twenty_seventh.isoformat()
assert iso_date(third) == expected_third.isoformat()
assert tail_end == regular_end and tail_end is not None
assert fortnightly is None

print(f"CASE=fortnight-no-article DATE={expected_fortnight.isoformat()}")
print(f"CASE=fortnight-article DATE={expected_fortnight.isoformat()}")
print(f"CASE=spelled-twentyseventh DATE={expected_twenty_seventh.isoformat()}")
print(f"CASE=spelled-third DATE={expected_third.isoformat()}")
print(f"CASE=tail-end-next-month WINDOW={str(tail_end == regular_end and tail_end is not None).lower()}")
print(f"CASE=fortnightly-not-matched UNRESOLVED={str(fortnightly is None).lower()}")
