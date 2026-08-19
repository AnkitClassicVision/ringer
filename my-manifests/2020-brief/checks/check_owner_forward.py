#!/usr/bin/env python3
"""Deterministic check for the owner-forward red-team lane.

Usage: python3 check_owner_forward.py <findings.json>
Exit 0 = the lane produced a parseable verdict with the required fields.
"""
import json
import sys

REQUIRED = [
    "ai_tell_density_per_1000w",
    "human_read_score_1_5",
    "taste_compliance_pct",
    "would_forward",
]


def main() -> int:
    if len(sys.argv) != 2:
        print("WHY: usage: check_owner_forward.py <findings.json>")
        return 1
    try:
        with open(sys.argv[1], encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"WHY: findings.json not parseable: {exc}")
        return 1
    missing = [k for k in REQUIRED if k not in data]
    if missing:
        print(f"WHY: findings.json missing fields: {', '.join(missing)}")
        return 1
    if not isinstance(data["would_forward"], bool):
        print("WHY: would_forward must be a boolean")
        return 1
    print("PASS: owner-forward findings parse with required fields")
    return 0


if __name__ == "__main__":
    sys.exit(main())
