#!/usr/bin/env python3
import importlib.util
import logging
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "gwtest" / "container"))
SPEC = importlib.util.spec_from_file_location("gw58_gateway", ROOT / "fixed-bland_gateway.py")
gateway = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gateway)
logging.disable(logging.CRITICAL)


def clamp(text, context="08/07/2026 12:15 pm", **overrides):
    body = {
        "from": "08/07/2026", "to": "08/07/2026",
        "user_verbatim": text, "context_date": context,
        "after": "none", "before": "none", "time_pref": "none",
    }
    body.update(overrides)
    gateway.clamp_availability_range(body)
    return body


later = clamp("Any other later time ?")
assert gateway._clock_minutes(later["after"]) > gateway._clock_minutes("12:15 pm")
print("CASE=later-floored AFTER_GT=12:15 (verbatim='Any other later time ?', context='08/07/2026 12:15 pm', after/before none -> effective after strictly later than 12:15 pm)")

earlier = clamp("anything earlier?", context="08/07/2026 12:00 pm")
assert gateway._clock_minutes(earlier["before"]) == gateway._clock_minutes("12:00 pm")
print("CASE=earlier-ceilinged BEFORE=12:00 (verbatim='anything earlier?', context='08/07/2026 12:00 pm')")

week = clamp("later this week works")
assert (week["after"], week["before"]) == ("none", "none")
print("CASE=later-this-week-not-time UNCHANGED=true (verbatim='later this week works', context same - no time floor)")

latest = clamp("last appointment please", time_pref="latest")
assert (latest["after"], latest["before"]) == ("none", "none")
print("CASE=latest-still-wins UNCHANGED=true (verbatim='last appointment please', time_pref='latest' - floor must not fire)")

afternoon = clamp("下午")
assert afternoon["after"] == "12:00 pm"
print("CASE=zh-afternoon AFTER=12:00 (verbatim='下午')")

morning = clamp("早上")
assert morning["before"] == "12:00 pm"
print("CASE=zh-morning BEFORE=12:00 (verbatim='早上')")

evening = clamp("晚上")
assert evening["after"] == "04:00 pm"
print("CASE=zh-evening AFTER=16:00 (verbatim='晚上')")

zh_later = clamp("晚一点")
assert gateway._clock_minutes(zh_later["after"]) > gateway._clock_minutes("12:15 pm")
print("CASE=zh-later AFTER_GT=12:15 (verbatim='晚一点', context='08/07/2026 12:15 pm')")
