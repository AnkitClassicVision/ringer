#!/usr/bin/env python3
"""Assert a named-time turn keeps the established date and confirms in one step.

usage: check_keepdate_confirm.py <turn.json> <MM/DD/YYYY> <HH:MM>

Requires: the response names the expected date and time, states a booking
confirmation prompt (reply YES / confirm), and mentions no other date.
"""

import json
import re
import sys


def main():
    if len(sys.argv) != 4:
        print("usage: check_keepdate_confirm.py <turn.json> <MM/DD/YYYY> <HH:MM>")
        return 1
    path, want_date, want_time = sys.argv[1:]
    data = json.load(open(path, encoding="utf-8")).get("data") or {}
    said = " ".join(str(x) for x in (data.get("assistant_responses") or []))
    node = data.get("current_node_id")
    failures = []

    dates = set(re.findall(r"\d{2}/\d{2}/\d{4}", said))
    if want_date not in dates:
        failures.append(f"expected date {want_date} not offered (saw {sorted(dates) or 'none'})")
    stray = dates - {want_date}
    if stray:
        failures.append(f"a different date appeared: {sorted(stray)}")
    if want_time not in said:
        failures.append(f"expected time {want_time} not stated")
    if not re.search(r"(?i)\b(reply yes|to confirm|confirm)\b", said):
        failures.append("no booking confirmation step - the named time did not go straight to confirm")
    if re.search(r"(?i)reply 1 to take it", said):
        failures.append("still using the intermediate 'reply 1 to take it' offer step")

    print(f"NODE={node} SAID={said[:180]!r}")
    if failures:
        for item in failures:
            print("FAIL: " + item)
        return 1
    print(f"PASS: kept {want_date} and confirmed {want_time} in one step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
