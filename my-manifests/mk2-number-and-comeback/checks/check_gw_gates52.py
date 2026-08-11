#!/usr/bin/env python3
"""Assert the lane-52 live probe output (gw_gates52.py).

usage: check_gw_gates52.py <gates52.txt>

- anaphor-next-week-wording: 'monday next week' + verbatim 'that week' +
  context 08/19 must offer Monday 08/17/2026 (the context week), not 08/10;
- anaphor-wrong-week-of: an extraction-hallucinated week-of qualifier must
  lose to the context week (08/17/2026);
- no-anaphor-control: without the anaphor the same from-text must keep the
  normal resolution (08/10/2026) - proves the override does not overreach.
"""

import re
import sys

EXPECT = {
    "anaphor-next-week-wording": "08/17/2026",
    "anaphor-wrong-week-of": "08/17/2026",
    "no-anaphor-control": "08/10/2026",
}


def main():
    if len(sys.argv) != 2:
        print("usage: check_gw_gates52.py <gates52.txt>")
        return 1
    text = open(sys.argv[1], encoding="utf-8").read()
    failures = []
    lines = {}
    for line in text.splitlines():
        match = re.match(r"GATE52=(\S+) (.*)", line)
        if match:
            lines[match.group(1)] = match.group(2)
    for label, want in EXPECT.items():
        got = lines.get(label)
        if got is None:
            failures.append(f"{label} probe line missing")
            continue
        if "STATUS=200" not in got:
            failures.append(f"{label} bad status: {got}")
        elif f"first={want}" not in got:
            failures.append(f"{label} expected first={want}: {got}")
    if failures:
        print("FAIL: " + " | ".join(failures))
        return 1
    print("PASS: lane-52 live probes green - context week wins under the anaphor, control unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
