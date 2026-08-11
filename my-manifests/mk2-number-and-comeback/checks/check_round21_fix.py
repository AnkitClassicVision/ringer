#!/usr/bin/env python3
"""Executable check for round 21: after-N refinements route to a search, and
negative availability claims are banned without a fresh search.

1. validator passes the new draft, rejects the v117 draft citing assertion 21;
2. the offered_time edge label covers after/before-hour refinement phrasing
   with an 'after 1' style example;
3. n_goal_response prompt carries a NO-NEGATIVE-CLAIM marker;
4. no responsePathway condition anywhere contains AND/OR in its value;
5. all prior guard markers survive.
"""

import json
import re
import subprocess
import sys

WAIT_NODES = (
    "n_goal_ask", "n_goal_response", "n_mixed_intent",
    "n_gate_1", "n_gate_2", "n_post_booking", "n_time_pick_offer",
)


def run(validator, draft):
    proc = subprocess.run(
        [sys.executable, validator, "--draft", draft],
        capture_output=True, text=True, timeout=300,
    )
    return proc.returncode, proc.stdout + proc.stderr


def main():
    if len(sys.argv) != 4:
        print("usage: check_round21_fix.py <validator.py> <new_draft> <v117_draft>")
        return 1
    validator, new_draft, old_draft = sys.argv[1:]
    failures = []

    rc_new, out_new = run(validator, new_draft)
    if rc_new != 0 or "PASS" not in out_new:
        failures.append(f"validator fails the new draft: {out_new[-200:]}")
    rc_old, out_old = run(validator, old_draft)
    if rc_old == 0:
        failures.append("validator still passes the v117 draft - assertion 21 toothless")
    elif not re.search(r"(?i)assertion\s*#?\s*21", out_old):
        failures.append(f"v117 rejection does not cite assertion 21: {out_old[-200:]}")

    graph = json.load(open(new_draft, encoding="utf-8"))
    nodes = {n.get("id"): n for n in graph.get("nodes", [])}
    edges = graph.get("edges", [])

    ot_edge = next(
        (e for e in edges if e.get("source") == "n_goal_response"
         and e.get("target") == "n_goal_search_offered_time"), None)
    label = str(((ot_edge or {}).get("data") or {}).get("label", "")).lower()
    if "after" not in label or not re.search(r"after 1\b|after \d", label):
        failures.append(f"offered_time label lacks after-hour refinement coverage: {label[:140]}")

    resp = str(nodes.get("n_goal_response", {}).get("data", {}).get("prompt", ""))
    if "NO-NEGATIVE-CLAIM:" not in resp:
        failures.append("n_goal_response lacks the NO-NEGATIVE-CLAIM marker")
    for marker in ("TIME-GRID:", "OFFER-INTEGRITY", "NO-BOOKING-CLAIM:"):
        if marker not in resp:
            failures.append(f"n_goal_response lost {marker}")

    for node in graph.get("nodes", []):
        for row in node.get("data", {}).get("responsePathways") or []:
            if isinstance(row, list) and len(row) >= 3 and isinstance(row[2], str):
                if re.search(r"\s+(and|or)\s+", row[2], re.I):
                    failures.append(f"{node.get('id')}: compound condition {row[:3]!r}")

    for nid in WAIT_NODES:
        node = nodes.get(nid)
        if node is None:
            continue
        if "NO-BOOKING-CLAIM:" not in str(node.get("data", {}).get("prompt", "")):
            failures.append(f"{nid} lost the NO-BOOKING-CLAIM marker")
    for gate in ("n_gate_1", "n_gate_2"):
        if "BOOKING-INTEGRITY:" not in str(nodes.get(gate, {}).get("data", {}).get("prompt", "")):
            failures.append(f"{gate} lost the BOOKING-INTEGRITY marker")

    if failures:
        print("FAIL: " + " | ".join(failures))
        return 1
    print("PASS: after-N refinement routed, negative claims banned, guards intact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
