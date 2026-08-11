#!/usr/bin/env python3
"""Validate a failure_mode_run.py transcript independently of its own verdict.

Greps the transcript for the mode's required evidence lines and prints exactly
which assertion broke. Exit 0 only when all hold.
"""
import argparse
import re
import sys

REQUIRED = {
    "unknown": [
        (r"^GW_COUNT_BEFORE=0$", "run must start with zero upcoming appointments"),
        (r"^END_NODE=e_book_unknown$", "conversation must end at e_book_unknown"),
        (r"wasn'?t able to confirm whether that booking went through",
         "the uncertainty copy must have been said to the patient"),
        (r"^GW_COUNT_AFTER=0$", "no appointment may exist after a 404'd write"),
        (r"^VERDICT: PASS mode=unknown", "driver's own verdict must be PASS"),
    ],
    "recovered": [
        (r"^GW_COUNT_BEFORE=0$", "run must start with zero upcoming appointments"),
        (r"^INJECT direct book .*(success=True|count=[1-9])",
         "the mid-conversation injection booking must have committed"),
        (r"^END_NODE=e_booked_recovered$", "conversation must end at e_booked_recovered"),
        (r"You'?re all set\. If you have further questions",
         "the mandated close must have been said"),
        (r"^GW_COUNT_AFTER=1$", "exactly the injected appointment must exist"),
        (r"^CLEANUP_FINAL_COUNT=0$", "the dummy account must be left clean"),
        (r"^VERDICT: PASS mode=recovered", "driver's own verdict must be PASS"),
    ],
    "happy": [
        (r"^GW_COUNT_BEFORE=0$", "run must start with zero upcoming appointments"),
        (r"^END_NODE=e_booked$", "conversation must end at e_booked"),
        (r"You'?re all set\. If you have further questions",
         "the mandated close must have been said"),
        (r"^GW_COUNT_AFTER=1$", "the pathway's booking must exist in the EMR"),
        (r"^CLEANUP_FINAL_COUNT=0$", "the dummy account must be left clean"),
        (r"^VERDICT: PASS mode=happy", "driver's own verdict must be PASS"),
    ],
}
FORBIDDEN = {
    "unknown": [(r"You'?re all set", "unknown mode claimed success to the patient")],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--mode", required=True, choices=sorted(REQUIRED))
    args = ap.parse_args()
    try:
        text = open(args.file, encoding="utf-8", errors="replace").read()
    except OSError as exc:
        print(f"FAIL: cannot read transcript: {exc}")
        sys.exit(1)

    fails = []
    for pattern, why in REQUIRED[args.mode]:
        if not re.search(pattern, text, re.I | re.M):
            fails.append(f"missing /{pattern}/ — {why}")
    for pattern, why in FORBIDDEN.get(args.mode, []):
        if re.search(pattern, text, re.I):
            fails.append(f"matched forbidden /{pattern}/ — {why}")

    if fails:
        print(f"FAIL ({args.mode}): {len(fails)} assertion(s) broke:")
        for f in fails:
            print(" -", f)
        sys.exit(1)
    print(f"PASS ({args.mode}): all evidence lines present, state clean")


if __name__ == "__main__":
    main()
