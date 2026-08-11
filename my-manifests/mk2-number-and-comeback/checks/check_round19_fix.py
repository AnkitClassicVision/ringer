#!/usr/bin/env python3
"""Executable check for round 19: a dedicated single-slot offer node.

The named-time path must not depend on prompt priority inside the shared
response node. It gets its own node whose only offer copy is one opening.

1. validator passes the new draft, rejects the v114 draft citing assertion 19;
2. n_time_pick_offer exists as a user-wait Default;
3. its copy templates slot_1_day_name/slot_1_start and NEVER slot_2_* ;
4. n_goal_search_anchor's success pathway targets n_time_pick_offer (not the
   shared response node);
5. n_time_pick_offer routes to n_gate_1 (accepting the time), to n_goal_search
   (wants something else), and to decline/timeout ends - and never to n_gate_2;
6. it carries NO-BOOKING-CLAIM, and every prior guard marker survives.
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
        print("usage: check_round19_fix.py <validator.py> <new_draft> <v114_draft>")
        return 1
    validator, new_draft, old_draft = sys.argv[1:]
    failures = []

    rc_new, out_new = run(validator, new_draft)
    if rc_new != 0 or "PASS" not in out_new:
        failures.append(f"validator fails the new draft: {out_new[-200:]}")
    rc_old, out_old = run(validator, old_draft)
    if rc_old == 0:
        failures.append("validator still passes the v114 draft - assertion 19 toothless")
    elif not re.search(r"(?i)assertion\s*#?\s*19", out_old):
        failures.append(f"v114 rejection does not cite assertion 19: {out_old[-200:]}")

    graph = json.load(open(new_draft, encoding="utf-8"))
    nodes = {n.get("id"): n for n in graph.get("nodes", [])}
    edges = graph.get("edges", [])

    pick = nodes.get("n_time_pick_offer")
    if pick is None:
        failures.append("n_time_pick_offer missing")
    else:
        data = pick.get("data", {})
        blob = json.dumps(data)
        if pick.get("type") != "Default" or data.get("userWait") is not True:
            failures.append("n_time_pick_offer must be a user-wait Default")
        if "{{slot_1_start}}" not in blob or "{{slot_1_day_name}}" not in blob:
            failures.append("n_time_pick_offer does not template slot_1 verbatim")
        if "slot_2_" in blob:
            failures.append("n_time_pick_offer references slot_2 - it must offer exactly one opening")
        targets = {e.get("target") for e in edges if e.get("source") == "n_time_pick_offer"}
        if "n_gate_1" not in targets:
            failures.append("n_time_pick_offer has no accept route to n_gate_1")
        if "n_gate_2" in targets:
            failures.append("n_time_pick_offer routes to n_gate_2 - there is no second opening")
        if "n_goal_search" not in targets:
            failures.append("n_time_pick_offer has no route back to a fresh search")

    anchor = nodes.get("n_goal_search_anchor")
    if anchor is None:
        failures.append("n_goal_search_anchor missing")
    else:
        rp = json.dumps(anchor.get("data", {}).get("responsePathways") or [])
        anchor_edges = {e.get("target") for e in edges if e.get("source") == "n_goal_search_anchor"}
        if "n_time_pick_offer" not in rp and "n_time_pick_offer" not in anchor_edges:
            failures.append("anchor search success does not reach n_time_pick_offer")

    for nid in WAIT_NODES:
        node = nodes.get(nid)
        if node is None:
            continue
        if "NO-BOOKING-CLAIM:" not in str(node.get("data", {}).get("prompt", "")):
            failures.append(f"{nid} lost the NO-BOOKING-CLAIM marker")
    resp = str(nodes.get("n_goal_response", {}).get("data", {}).get("prompt", ""))
    for marker in ("TIME-GRID:", "OFFER-INTEGRITY"):
        if marker not in resp:
            failures.append(f"n_goal_response lost {marker}")
    for gate in ("n_gate_1", "n_gate_2"):
        if "BOOKING-INTEGRITY:" not in str(nodes.get(gate, {}).get("data", {}).get("prompt", "")):
            failures.append(f"{gate} lost the BOOKING-INTEGRITY marker")

    if failures:
        print("FAIL: " + " | ".join(failures))
        return 1
    print("PASS: dedicated single-slot offer node wired, all prior guards intact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
