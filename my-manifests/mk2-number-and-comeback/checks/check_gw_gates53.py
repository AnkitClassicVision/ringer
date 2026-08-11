#!/usr/bin/env python3
"""Assert the lane-53 live probe output (gw_gates53.py).

usage: check_gw_gates53.py <gates53.txt>

- fortnight-no-article: resolves (unresolved falsy); a dated first slot, when
  present, sits in [today+14, today+16] (closed days can push it; an empty day
  is acceptable only with unresolved falsy);
- spelled-twentyseventh: resolves with the first slot on the expected 27th when
  slots exist (unresolved must be falsy);
- tail-end-next-month: resolves (unresolved falsy).
"""

import datetime
import re
import sys


def main():
    if len(sys.argv) != 2:
        print("usage: check_gw_gates53.py <gates53.txt>")
        return 1
    text = open(sys.argv[1], encoding="utf-8").read()
    failures = []
    lines = {}
    for line in text.splitlines():
        match = re.match(r"GATE53=(\S+) (.*)", line)
        if match:
            lines[match.group(1)] = match.group(2)

    for label in ("fortnight-no-article", "spelled-twentyseventh", "tail-end-next-month"):
        got = lines.get(label)
        if got is None:
            failures.append(f"{label} probe line missing")
            continue
        if "STATUS=200" not in got:
            failures.append(f"{label} bad status: {got}")
        if "unresolved=True" in got:
            failures.append(f"{label} left from unresolved: {got}")

    fmt = "%m/%d/%Y"
    lo = re.search(r"EXPECT53_FORTNIGHT_LO=(\S+)", text)
    hi = re.search(r"EXPECT53_FORTNIGHT_HI=(\S+)", text)
    first = re.search(r"first=(\d{2}/\d{2}/\d{4})", lines.get("fortnight-no-article", ""))
    if first and lo and hi:
        got = datetime.datetime.strptime(first.group(1), fmt).date()
        lo_d = datetime.datetime.strptime(lo.group(1), fmt).date()
        hi_d = datetime.datetime.strptime(hi.group(1), fmt).date()
        if not (lo_d <= got <= hi_d):
            failures.append(f"fortnight first slot {got} outside [{lo_d}, {hi_d}]")

    o27 = re.search(r"EXPECT53_ORD27=(\S+)", text)
    first27 = re.search(r"first=(\d{2}/\d{2}/\d{4})", lines.get("spelled-twentyseventh", ""))
    if o27 and first27 and first27.group(1) != o27.group(1):
        failures.append(
            f"twenty-seventh first slot {first27.group(1)} is not {o27.group(1)}")

    if failures:
        print("FAIL: " + " | ".join(failures))
        return 1
    print("PASS: lane-53 live probes green - fortnight, spelled ordinal, tail-end month all resolve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
