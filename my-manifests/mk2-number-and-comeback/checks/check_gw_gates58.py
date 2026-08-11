#!/usr/bin/env python3
"""Assert the lane-58 live probe output (gw_gates58.py).

usage: check_gw_gates58.py <gates58.txt>

- later-floored: 'Any other later time ?' with context 10:30 am must offer a
  first slot strictly later than 10:30 am (an honest empty n=0 also accepted
  when the day is booked out past that time);
- zh-afternoon: '下午' must window to the afternoon - pm first slot or honest
  empty, never a morning first slot;
- later-this-week-control: 'later this week' is a date phrase - no time floor,
  first slot keeps the day's normal earliest (am when the day opens am).
"""

import datetime
import re
import sys


def first_time_minutes(row):
    match = re.search(r"first=\d{2}/\d{2}/\d{4} (\d{2}):(\d{2}) (am|pm)", row)
    if not match:
        return None
    hour, minute, meridiem = int(match.group(1)), int(match.group(2)), match.group(3)
    hour = hour % 12 + (12 if meridiem == "pm" else 0)
    return hour * 60 + minute


def main():
    if len(sys.argv) != 2:
        print("usage: check_gw_gates58.py <gates58.txt>")
        return 1
    text = open(sys.argv[1], encoding="utf-8").read()
    failures = []
    lines = {}
    for line in text.splitlines():
        match = re.match(r"GATE58=(\S+) (.*)", line)
        if match:
            lines[match.group(1)] = match.group(2)

    for label in ("later-floored", "zh-afternoon", "later-this-week-control"):
        if label not in lines:
            failures.append(f"{label} probe line missing")

    lf = lines.get("later-floored", "")
    minutes = first_time_minutes(lf)
    if "STATUS=200" not in lf:
        failures.append(f"later-floored bad status: {lf}")
    elif minutes is None:
        if "n=0" not in lf:
            failures.append(f"later-floored neither floored offer nor honest empty: {lf}")
    elif minutes <= 10 * 60 + 30:
        failures.append(f"later-floored first slot not after 10:30 am: {lf}")

    zh = lines.get("zh-afternoon", "")
    zh_minutes = first_time_minutes(zh)
    if "STATUS=200" not in zh:
        failures.append(f"zh-afternoon bad status: {zh}")
    elif zh_minutes is not None and zh_minutes < 12 * 60:
        failures.append(f"zh-afternoon offered a morning slot: {zh}")

    ctl = lines.get("later-this-week-control", "")
    ctl_minutes = first_time_minutes(ctl)
    if "STATUS=200" not in ctl:
        failures.append(f"control bad status: {ctl}")
    elif ctl_minutes is not None and ctl_minutes > 12 * 60:
        failures.append(f"control was wrongly time-floored: {ctl}")

    if failures:
        print("FAIL: " + " | ".join(failures))
        return 1
    print("PASS: lane-58 live probes green - later floored, Chinese afternoon windowed, date-phrase control intact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
