#!/usr/bin/env python3
"""Fail unless a named-time turn offers exactly one opening, at the named time."""
import json, re, sys

def main():
    if len(sys.argv) != 3:
        print("usage: check_single_slot_pick.py <turn.json> <HH:MM>")
        return 1
    path, want = sys.argv[1], sys.argv[2]
    data = json.load(open(path, encoding="utf-8")).get("data") or {}
    said = " ".join(str(x) for x in (data.get("assistant_responses") or []))
    times = re.findall(r"\b\d{1,2}:\d{2}\s*(?:am|pm)\b", said, re.I)
    distinct = {t.lower().replace(" ", "") for t in times}
    failures = []
    if not any(t.startswith(want.replace(":", "")[:2] + ":" + want.split(":")[1]) or want in t for t in distinct):
        failures.append(f"named time {want} not offered; times seen: {sorted(distinct)}")
    if len(distinct) > 1:
        failures.append(f"expected a single opening, got {sorted(distinct)}")
    print(f"SAID={said[:160]!r}")
    if failures:
        print("FAIL: " + "; ".join(failures))
        return 1
    print(f"PASS: single opening offered at {want}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
