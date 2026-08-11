#!/usr/bin/env python3
"""Fail when a turn claims a booking that did not happen, or speaks an off-grid time.

For each captured turn envelope:
- booking-claim language ("booked", "got you down", "you're all set",
  "see you then", "confirmed for", "reserved", "scheduled you") is only allowed
  when that turn's variables show a completed booking (book_success true or a
  new_appt_id present);
- every clock time spoken must sit on the 15-minute grid (:00/:15/:30/:45).
"""

import glob
import json
import os
import re
import sys

CLAIM = re.compile(
    r"(?i)\b(?:booked|got you down|you'?re all set|we'?ll see you then|"
    r"see you then|reserved|i'?ve scheduled|scheduled you|confirmed for)\b"
)
CLOCK = re.compile(r"\b(\d{1,2}):(\d{2})\s*(?:am|pm)\b", re.I)
REFUSAL = re.compile(
    r"(?i)\b(?:not available|isn'?t available|no openings?|don'?t have|"
    r"do not have|unavailable|cannot|can'?t (?:do|book|offer))\b"
)


def main():
    cap = sys.argv[1] if len(sys.argv) > 1 else "."
    numbered = []
    for path in glob.glob(os.path.join(cap, "turn*.json")):
        match = re.search(r"turn(\d+)\.json$", os.path.basename(path))
        if match:
            numbered.append((int(match.group(1)), path))
    if not numbered:
        print(f"FAIL: no turn envelopes in {cap}")
        return 1

    failures = []
    for n, path in sorted(numbered):
        data = json.load(open(path, encoding="utf-8")).get("data") or {}
        variables = data.get("variables") or {}
        said = " ".join(str(x) for x in (data.get("assistant_responses") or []))
        booked = bool(variables.get("new_appt_id")) or str(
            variables.get("book_success", "")
        ).lower() in ("true", "1")

        claim = CLAIM.search(said)
        if claim and not booked:
            failures.append(
                f"turn {n} claimed a booking ({claim.group(0)!r}) with no booking in variables"
            )
        offgrid = []
        for sentence in re.split(r"(?<=[.!?])\s+|\n", said):
            refusing = REFUSAL.search(sentence)
            for hour, minute in CLOCK.findall(sentence):
                if int(minute) % 15 != 0 and not refusing:
                    offgrid.append(f"{hour}:{minute}")
        if offgrid:
            failures.append(f"turn {n} spoke off-grid time(s) {offgrid}")
        print(f"TURN={n} booked={booked} claim={bool(claim)} offgrid={offgrid} said={said[:80]!r}")

    if failures:
        for line in failures:
            print("FAIL: " + line)
        return 1
    print("PASS: no false booking claims and every spoken time is on the 15-minute grid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
