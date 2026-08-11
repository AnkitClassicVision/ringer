#!/usr/bin/env python3
"""Assert the lane-59 live probe output (gw_gates59.py).

usage: check_gw_gates59.py <gates59.txt>

- garbled-zh-daypart: verbatim garbled to 一午 with the true 下午 in user_text
  must window to the afternoon (pm first slot or honest empty, never am);
- verbatim-wins: verbatim 晚上 (evening) beats a conflicting 早上 in user_text -
  first slot 4pm+ or honest empty;
- clean-path-control: 早上 both sides windows to the morning (am first slot or
  honest empty, never pm).
"""

import re
import sys


def check_meridiem(row, want, label, failures):
    if "STATUS=200" not in row:
        failures.append(f"{label} bad status: {row}")
        return
    match = re.search(r"first=\d{2}/\d{2}/\d{4} (\d{2}):\d{2} (am|pm)", row)
    if match is None:
        if "count=0" not in row and "n=0" not in row:
            failures.append(f"{label} neither windowed offer nor honest empty: {row}")
        return
    if match.group(2) != want:
        failures.append(f"{label} expected an {want} first slot: {row}")
    if label == "verbatim-wins" and match.group(2) == "pm" and int(match.group(1)) % 12 < 4:
        failures.append(f"{label} pm slot before 4pm - evening window not applied: {row}")


def main():
    if len(sys.argv) != 2:
        print("usage: check_gw_gates59.py <gates59.txt>")
        return 1
    text = open(sys.argv[1], encoding="utf-8").read()
    failures = []
    lines = {}
    for line in text.splitlines():
        match = re.match(r"GATE59=(\S+) (.*)", line)
        if match:
            lines[match.group(1)] = match.group(2)
    for label, want in (("garbled-zh-daypart", "pm"), ("verbatim-wins", "pm"),
                        ("clean-path-control", "am")):
        row = lines.get(label)
        if row is None:
            failures.append(f"{label} probe line missing")
        else:
            check_meridiem(row, want, label, failures)
    if failures:
        print("FAIL: " + " | ".join(failures))
        return 1
    print("PASS: lane-59 live probes green - garbled verbatim falls back to live text, verbatim still wins, clean path intact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
