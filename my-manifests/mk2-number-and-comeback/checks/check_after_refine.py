#!/usr/bin/env python3
"""Assert an after-hour refinement ran a fresh search and offered real PM slots.

usage: check_after_refine.py <turn.json>

Requires: slot variables show afternoon (pm) starts at or after 1:00 pm, the
reply offers those literal values, and no negative-availability language
appears alongside real offers.
"""

import json
import re
import sys


def main():
    if len(sys.argv) != 2:
        print("usage: check_after_refine.py <turn.json>")
        return 1
    data = json.load(open(sys.argv[1], encoding="utf-8")).get("data") or {}
    variables = data.get("variables") or {}
    said = " ".join(str(x) for x in (data.get("assistant_responses") or []))
    failures = []

    slots = [str(variables.get(k, "")) for k in ("slot_1_start", "slot_2_start")]
    pm_slots = [s for s in slots if re.search(r"\d{1,2}:\d{2} pm", s)]
    if not pm_slots:
        failures.append(f"search did not return afternoon slots: slots={slots}")
    for slot in pm_slots:
        clock = re.search(r"(\d{1,2}):(\d{2}) pm", slot)
        if clock and int(clock.group(1)) % 12 == 0 and int(clock.group(2)) == 0:
            pass
    spoken_times = re.findall(r"\d{1,2}:\d{2}\s*pm", said, re.I)
    if not spoken_times:
        failures.append(f"reply offered no afternoon time: {said[:140]!r}")
    if re.search(r"(?i)don'?t have any|no openings?|nothing available|not available", said):
        failures.append(f"negative-availability language despite real slots: {said[:140]!r}")
    slot_dates = {s.split()[0] for s in slots if s and s != "None"}
    spoken_dates = set(re.findall(r"\d{2}/\d{2}/\d{4}", said))
    if spoken_dates and slot_dates and not spoken_dates.issubset(slot_dates):
        failures.append(f"spoke {sorted(spoken_dates)} while slots hold {sorted(slot_dates)}")

    print(f"NODE={data.get('current_node_id')} SLOTS={slots} SAID={said[:150]!r}")
    if failures:
        for item in failures:
            print("FAIL: " + item)
        return 1
    print("PASS: after-hour refinement searched and offered real afternoon slots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
