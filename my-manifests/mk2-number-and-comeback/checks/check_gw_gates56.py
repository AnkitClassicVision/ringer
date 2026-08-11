#!/usr/bin/env python3
"""Assert the lane-56 live probe output (gw_gates56.py).

usage: check_gw_gates56.py <gates56.txt>

- afternoon-dropped: extraction passed only 'friday' but the patient said
  'Friday afternoon' - the first offered slot must be a pm time;
- morning-control: 'friday morning' must offer an am first slot;
- greeting-guard: 'good afternoon, do you have friday?' must NOT be windowed
  to the afternoon when the day opens in the morning - the first slot keeps
  the day's normal earliest (am on the current calendar).
"""

import re
import sys


def main():
    if len(sys.argv) != 2:
        print("usage: check_gw_gates56.py <gates56.txt>")
        return 1
    text = open(sys.argv[1], encoding="utf-8").read()
    failures = []
    lines = {}
    for line in text.splitlines():
        match = re.match(r"GATE56=(\S+) (.*)", line)
        if match:
            lines[match.group(1)] = match.group(2)

    for label, ampm in (("afternoon-dropped", "pm"), ("morning-control", "am"),
                        ("greeting-guard", "am")):
        got = lines.get(label)
        if got is None:
            failures.append(f"{label} probe line missing")
            continue
        if "STATUS=200" not in got:
            failures.append(f"{label} bad status: {got}")
        elif not re.search(r"first=\d{2}/\d{2}/\d{4} \d{2}:\d{2} " + ampm, got):
            failures.append(f"{label} expected an {ampm} first slot: {got}")

    if failures:
        print("FAIL: " + " | ".join(failures))
        return 1
    print("PASS: lane-56 live probes green - day-part windows applied, greeting guarded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
