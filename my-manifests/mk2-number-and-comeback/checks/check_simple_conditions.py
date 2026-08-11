#!/usr/bin/env python3
"""Assert responsePathway conditions are simple triples and the exact route is armed.

usage: check_simple_conditions.py <draft.json>
"""

import json
import re
import sys


def main():
    if len(sys.argv) != 2:
        print("usage: check_simple_conditions.py <draft.json>")
        return 1
    graph = json.load(open(sys.argv[1], encoding="utf-8"))
    failures = []

    for node in graph.get("nodes", []):
        for row in node.get("data", {}).get("responsePathways") or []:
            if isinstance(row, list) and len(row) >= 3 and isinstance(row[2], str):
                if re.search(r"\s+(and|or)\s+", row[2], re.I):
                    failures.append(f"{node.get('id')}: compound condition value {row[:3]!r}")

    nodes = {n.get("id"): n for n in graph.get("nodes", [])}
    anchor = nodes.get("n_goal_search_offered_anchor")
    if anchor is None:
        failures.append("n_goal_search_offered_anchor missing")
    else:
        rows = anchor.get("data", {}).get("responsePathways") or []
        exact = [
            r for r in rows
            if isinstance(r, list) and len(r) >= 4
            and r[0] == "anchor_exact" and r[1] == "==" and str(r[2]).strip().lower() == "true"
        ]
        if not exact:
            failures.append(f"no simple anchor_exact == true pathway; rows={json.dumps(rows)[:200]}")
        else:
            target = exact[0][3]
            tid = target.get("id") if isinstance(target, dict) else target
            if tid != "n_gate_1":
                failures.append(f"anchor_exact == true routes to {tid!r}, expected n_gate_1")
        nonexact = [
            r for r in rows
            if isinstance(r, list) and len(r) >= 4
            and r[0] == "anchor_exact" and r[1] == "!=" and str(r[2]).strip().lower() == "true"
        ]
        if not nonexact:
            failures.append("no simple anchor_exact != true fallback pathway")
        else:
            target = nonexact[0][3]
            tid = target.get("id") if isinstance(target, dict) else target
            if tid != "n_time_pick_offer":
                failures.append(f"anchor_exact != true routes to {tid!r}, expected n_time_pick_offer")

    if failures:
        for item in failures:
            print("FAIL: " + item)
        return 1
    print("PASS: conditions are simple triples and the exact-match route targets the confirmation gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
