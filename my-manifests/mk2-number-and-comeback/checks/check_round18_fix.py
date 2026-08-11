#!/usr/bin/env python3
"""Executable check for round 18: deterministic single-slot time picks.

1. worker validator passes the new draft and rejects the v113 draft citing assertion 18;
2. n_goal_response has a named-time-pick edge to n_goal_search_anchor whose label
   covers naming a specific clock time (including bare digit forms);
3. n_goal_response prompt carries a SINGLE-SLOT rule marker;
4. the anchor search still pins time_pref to anchor={{goal_anchor}} and its
   success path reaches n_goal_response;
5. every earlier guard survives: NO-BOOKING-CLAIM on the wait nodes, TIME-GRID
   and OFFER-INTEGRITY on n_goal_response, BOOKING-INTEGRITY on both gates.
"""

import json
import re
import subprocess
import sys

WAIT_NODES = (
    "n_goal_ask", "n_goal_response", "n_mixed_intent",
    "n_gate_1", "n_gate_2", "n_post_booking",
)


def run(validator, draft):
    proc = subprocess.run(
        [sys.executable, validator, "--draft", draft],
        capture_output=True, text=True, timeout=300,
    )
    return proc.returncode, proc.stdout + proc.stderr


def main():
    if len(sys.argv) != 4:
        print("usage: check_round18_fix.py <validator.py> <new_draft> <v113_draft>")
        return 1
    validator, new_draft, old_draft = sys.argv[1:]
    failures = []

    rc_new, out_new = run(validator, new_draft)
    if rc_new != 0 or "PASS" not in out_new:
        failures.append(f"validator fails the new draft: {out_new[-200:]}")
    rc_old, out_old = run(validator, old_draft)
    if rc_old == 0:
        failures.append("validator still passes the v113 draft - assertion 18 toothless")
    elif not re.search(r"(?i)assertion\s*#?\s*18", out_old):
        failures.append(f"v113 rejection does not cite assertion 18: {out_old[-200:]}")

    graph = json.load(open(new_draft, encoding="utf-8"))
    nodes = {n.get("id"): n for n in graph.get("nodes", [])}
    edges = graph.get("edges", [])

    pick = [
        e for e in edges
        if e.get("source") == "n_goal_response"
        and e.get("target") == "n_goal_search_anchor"
        and re.search(r"(?i)names?\b.*\b(clock )?time", str((e.get("data") or {}).get("label", "")))
    ]
    if not pick:
        failures.append("no named-time-pick edge n_goal_response -> n_goal_search_anchor")
    else:
        label = str((pick[0].get("data") or {}).get("label", "")).lower()
        if "1115" not in label.replace(":", "").replace(" ", ""):
            failures.append(f"pick edge label lacks a bare-digit example: {label[:120]}")

    resp = str(nodes.get("n_goal_response", {}).get("data", {}).get("prompt", ""))
    for marker in ("SINGLE-SLOT:", "TIME-GRID:", "OFFER-INTEGRITY", "NO-BOOKING-CLAIM:"):
        if marker not in resp:
            failures.append(f"n_goal_response prompt lacks {marker}")

    anchor = nodes.get("n_goal_search_anchor")
    if anchor is None:
        failures.append("n_goal_search_anchor missing")
    else:
        body = json.loads(str(anchor.get("data", {}).get("body", "{}")))
        if body.get("time_pref") != "anchor={{goal_anchor}}":
            failures.append(f"anchor search time_pref changed: {body.get('time_pref')!r}")
        if "n_goal_response" not in json.dumps(anchor.get("data", {}).get("responsePathways") or []):
            failures.append("anchor search success path does not reach n_goal_response")

    for nid in WAIT_NODES:
        node = nodes.get(nid)
        if node is None:
            continue
        prompt = str(node.get("data", {}).get("prompt", ""))
        if "NO-BOOKING-CLAIM:" not in prompt:
            failures.append(f"{nid} lost the NO-BOOKING-CLAIM marker")
    for gate in ("n_gate_1", "n_gate_2"):
        if "BOOKING-INTEGRITY:" not in str(nodes.get(gate, {}).get("data", {}).get("prompt", "")):
            failures.append(f"{gate} lost the BOOKING-INTEGRITY marker")

    if failures:
        print("FAIL: " + " | ".join(failures))
        return 1
    print("PASS: deterministic single-slot pick wired, all prior guards intact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
