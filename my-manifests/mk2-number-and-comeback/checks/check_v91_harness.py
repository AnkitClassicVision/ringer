#!/usr/bin/env python3
"""Validate a v91_harness.py transcript independently of the driver's own verdict."""
import argparse
import re
import sys

REQUIRED = {
    "gate_booked": [
        (r"^SEED_OK appt_id=\S+", "the seed appointment must have been created"),
        (r"^END_NODE=e_defer$", "a booked subject saying hi must end at e_defer"),
        (r"contact the MK2 Optical office at \(212\) 219-2219",
         "the DEFER line must have been said"),
        (r"^CLEANUP_FINAL_COUNT=0$", "the seed appointment must be cancelled afterward"),
        (r"^VERDICT: PASS mode=gate_booked", "driver verdict must be PASS"),
    ],
    "gate_clean": [
        (r"^GW_COUNT_BEFORE=0$", "subject must start clean"),
        (r"^END_NODE=n_ask$", "a clean subject saying hi must reach n_ask"),
        (r"^APPT_COUNT_VAR=0$", "conversation variable appt_count must be 0"),
        (r"^VERDICT: PASS mode=gate_clean", "driver verdict must be PASS"),
    ],
    "incident": [
        (r"^OFFER_FIRST=.*\d{2}:\d{2} [ap]m", "the first (afternoon) offer must be captured"),
        (r"^OFFER_LATER=.*\d{2}:\d{2} [ap]m", "the later-request offer must be captured"),
        (r"^LATER_STRICTLY_GREATER=True$",
         "later-request offers must be strictly later than the first offers"),
        (r"^OFFERS_IN_INVENTORY=True$",
         "every offered time must be a member of the gateway's real slot inventory"),
        (r"^NEVER_DENIED=True$",
         "the agent must never claim no later times exist while inventory holds them"),
        (r"^VERDICT: PASS mode=incident", "driver verdict must be PASS"),
    ],
    "happy": [
        (r"^GW_COUNT_BEFORE=0$", "run must start with zero upcoming appointments"),
        (r"^END_NODE=e_booked$", "conversation must end at e_booked"),
        (r"You'?re all set\. If you have further questions", "the mandated close must be said"),
        (r"^GW_COUNT_AFTER=1$", "the booking must exist in the EMR"),
        (r"^CLEANUP_FINAL_COUNT=0$", "the dummy account must be left clean"),
        (r"^VERDICT: PASS mode=happy", "driver verdict must be PASS"),
    ],
}
FORBIDDEN = {
    "incident": [
        (r"latest the office has", "the retired false-latest claim was said"),
        (r"nothing later", "a nothing-later denial was said"),
    ],
    "gate_clean": [],
    "gate_booked": [(r"When would you like to come in",
                     "a booked subject must never be offered booking")],
    "happy": [],
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
    print(f"PASS ({args.mode}): all evidence lines present")


if __name__ == "__main__":
    main()
