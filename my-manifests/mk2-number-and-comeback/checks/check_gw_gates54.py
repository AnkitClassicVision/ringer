#!/usr/bin/env python3
"""Assert the lane-54 live probe output (gw_gates54.py).

usage: check_gw_gates54.py <gates54.txt>

- strip-invented-am: extractor said 'anchor=3:00 am' but the verbatim ('either
  3 or 4') has no meridiem, so the gateway must anchor to the AFTERNOON - the
  first offered slot is a pm time, never a morning slot;
- keep-stated-am: the patient literally said '11 am', so the stated meridiem
  must be preserved - first slot is an am time;
- closed-day-saturday: a Saturday request returns closed=True.
"""

import re
import sys


def main():
    if len(sys.argv) != 2:
        print("usage: check_gw_gates54.py <gates54.txt>")
        return 1
    text = open(sys.argv[1], encoding="utf-8").read()
    failures = []
    lines = {}
    for line in text.splitlines():
        match = re.match(r"GATE54=(\S+) (.*)", line)
        if match:
            lines[match.group(1)] = match.group(2)

    strip = lines.get("strip-invented-am", "")
    if "STATUS=200" not in strip:
        failures.append(f"strip-invented-am bad status: {strip}")
    elif not re.search(r"first=\d{2}/\d{2}/\d{4} \d{2}:\d{2} pm", strip):
        failures.append(f"strip-invented-am did not anchor to the afternoon: {strip}")

    keep = lines.get("keep-stated-am", "")
    if "STATUS=200" not in keep:
        failures.append(f"keep-stated-am bad status: {keep}")
    elif not re.search(r"first=\d{2}/\d{2}/\d{4} \d{2}:\d{2} am", keep):
        failures.append(f"keep-stated-am lost the patient's stated morning: {keep}")

    closed = lines.get("closed-day-saturday", "")
    if "closed=True" not in closed:
        failures.append(f"closed-day-saturday not flagged closed: {closed}")

    for label in ("strip-invented-am", "keep-stated-am", "closed-day-saturday"):
        if label not in lines:
            failures.append(f"{label} probe line missing")

    if failures:
        print("FAIL: " + " | ".join(failures))
        return 1
    print("PASS: lane-54 live probes green - verbatim meridiem wins, stated meridiem kept, closed day flagged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
