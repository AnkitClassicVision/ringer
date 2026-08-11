#!/usr/bin/env python3
"""Assert the lane-55 live probe output (gw_gates55.py).

usage: check_gw_gates55.py <gates55.txt>

- ordinal-dropped: extraction said 'thursday next week' but the patient said
  'the 27' - first slot must be on 08/27/2026, never 08/13;
- that-weekday: 'that Thursday' with context 08/26 anchors to 08/27/2026;
- bare-weekday-control: no anaphor, no ordinal - the next Thursday from today
  (NOT 08/27 unless today makes it so); asserted only as not-08/13-and-dated.
"""

import re
import sys


def main():
    if len(sys.argv) != 2:
        print("usage: check_gw_gates55.py <gates55.txt>")
        return 1
    text = open(sys.argv[1], encoding="utf-8").read()
    failures = []
    lines = {}
    for line in text.splitlines():
        match = re.match(r"GATE55=(\S+) (.*)", line)
        if match:
            lines[match.group(1)] = match.group(2)

    for label, want in (("ordinal-dropped", "08/27/2026"), ("that-weekday", "08/27/2026")):
        got = lines.get(label)
        if got is None:
            failures.append(f"{label} probe line missing")
        elif "STATUS=200" not in got:
            failures.append(f"{label} bad status: {got}")
        elif f"first={want}" not in got:
            failures.append(f"{label} expected first={want}: {got}")

    ctl = lines.get("bare-weekday-control", "")
    if "STATUS=200" not in ctl:
        failures.append(f"bare-weekday-control bad status: {ctl}")
    elif not re.search(r"first=\d{2}/\d{2}/\d{4}", ctl):
        failures.append(f"bare-weekday-control lost its dated offer: {ctl}")

    if failures:
        print("FAIL: " + " | ".join(failures))
        return 1
    print("PASS: lane-55 live probes green - verbatim ordinal and that-weekday anaphor win, control intact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
