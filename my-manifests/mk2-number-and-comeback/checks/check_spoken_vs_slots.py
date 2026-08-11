#!/usr/bin/env python3
"""Fail when a turn speaks a date the live slot variables do not hold.

Reads turn*.json envelopes in a capture directory. For each turn that both
speaks an MM/DD/YYYY date and holds slot_N_start variables, the spoken dates
must be a subset of the slot dates. Prints every turn for the record.
"""

import glob
import json
import os
import re
import sys


def main():
    cap = sys.argv[1] if len(sys.argv) > 1 else "."
    numbered = []
    for path in glob.glob(os.path.join(cap, "turn*.json")):
        match = re.search(r"turn(\d+)\.json$", os.path.basename(path))
        if match:
            numbered.append((int(match.group(1)), path))
    paths = [p for _, p in sorted(numbered)]
    if not paths:
        print(f"FAIL: no turn envelopes in {cap}")
        return 1
    bad = []
    for path in paths:
        n = int(re.search(r"turn(\d+)", path).group(1))
        data = json.load(open(path, encoding="utf-8")).get("data") or {}
        variables = data.get("variables") or {}
        said = " ".join(str(x) for x in (data.get("assistant_responses") or []))
        spoken = set(re.findall(r"\d{2}/\d{2}/\d{4}", said))
        slots = {
            str(variables[k]).split()[0]
            for k in ("slot_1_start", "slot_2_start")
            if variables.get(k)
        }
        print(
            f"TURN={n} node={data.get('current_node_id')} spoken={sorted(spoken)} "
            f"slots={sorted(slots)} said={said[:90]!r}"
        )
        if spoken and slots and not spoken.issubset(slots):
            bad.append((n, sorted(spoken), sorted(slots)))
    if bad:
        for n, spoken, slots in bad:
            print(f"FAIL: turn {n} spoke {spoken} while slot variables held {slots}")
        return 1
    print("PASS: every spoken date is backed by a live slot variable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
