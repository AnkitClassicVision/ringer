#!/usr/bin/env python3
"""Assert the lane-51 live probe output (gw_gates51.py).

usage: check_gw_gates51.py <gates51.txt>

- around-five must anchor to the AFTERNOON: first offered slot is a pm time
  (lane-50 reads bare 5 as 5:00 AM and offers a morning slot);
- midnight must come back out_of_hours=True;
- eleven-days must resolve (from_unresolved falsy) - that is the vocabulary
  fix under test. Slot presence depends on the clinic calendar (today+11 can
  land on a closed Sunday), so a dated first slot is only range-checked
  against [today+11, today+13] when one exists; an empty day is acceptable.
"""

import datetime
import re
import sys


def main():
    if len(sys.argv) != 2:
        print("usage: check_gw_gates51.py <gates51.txt>")
        return 1
    text = open(sys.argv[1], encoding="utf-8").read()
    failures = []
    lines = {}
    for line in text.splitlines():
        match = re.match(r"GATE51=(\S+) (.*)", line)
        if match:
            lines[match.group(1)] = match.group(2)

    for label in ("around-five", "midnight", "eleven-days"):
        if label not in lines:
            failures.append(f"{label} probe line missing")

    five = lines.get("around-five", "")
    if "STATUS=200" not in five:
        failures.append(f"around-five bad status: {five}")
    elif not re.search(r"first=\d{2}/\d{2}/\d{4} \d{2}:\d{2} pm", five):
        failures.append(f"around-five did not offer an afternoon slot: {five}")

    mid = lines.get("midnight", "")
    if "oob=True" not in mid:
        failures.append(f"midnight not flagged out-of-hours: {mid}")

    lo = re.search(r"EXPECT51_ELEVEN_LO=(\S+)", text)
    hi = re.search(r"EXPECT51_ELEVEN_HI=(\S+)", text)
    eleven = lines.get("eleven-days", "")
    if "STATUS=200" not in eleven:
        failures.append(f"eleven-days bad status: {eleven}")
    if "unresolved=True" in eleven:
        failures.append(f"eleven-days left from unresolved: {eleven}")
    first = re.search(r"first=(\d{2}/\d{2}/\d{4})", eleven)
    if first and lo and hi:
        fmt = "%m/%d/%Y"
        got = datetime.datetime.strptime(first.group(1), fmt).date()
        lo_d = datetime.datetime.strptime(lo.group(1), fmt).date()
        hi_d = datetime.datetime.strptime(hi.group(1), fmt).date()
        if not (lo_d <= got <= hi_d):
            failures.append(
                f"eleven-days first slot {got} outside [{lo_d}, {hi_d}]")

    if failures:
        print("FAIL: " + " | ".join(failures))
        return 1
    print("PASS: lane-51 live probes green - pm anchor, midnight OOB, spelled-number relative")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
