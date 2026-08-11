#!/usr/bin/env python3
"""Executable check for round 20: named times keep the date and go straight to confirm.

1. validator passes the new draft, rejects the v115 draft citing assertion 20;
2. n_goal_search_offered_anchor exists: body from/to pinned to {{slot_1_start}},
   time_pref anchor={{goal_anchor}}, inside the ten-field gateway contract, and
   maps anchor_exact from the response;
3. the n_goal_response named-time edge targets it (post-offer keeps the date),
   while the pre-offer named-time edge from n_goal_ask still targets the
   unpinned n_goal_search_anchor;
4. its exact-match pathway reaches n_gate_1 directly (single confirmation) and
   its non-exact pathway reaches n_time_pick_offer;
5. every prior guard marker survives.
"""

import json
import re
import subprocess
import sys

WAIT_NODES = (
    "n_goal_ask", "n_goal_response", "n_mixed_intent",
    "n_gate_1", "n_gate_2", "n_post_booking", "n_time_pick_offer",
)
ALLOWED_BODY_FIELDS = {
    "store", "from", "to", "after", "before", "time_pref",
    "slot_minutes", "callID", "user_text", "user_verbatim",
}


def run(validator, draft):
    proc = subprocess.run(
        [sys.executable, validator, "--draft", draft],
        capture_output=True, text=True, timeout=300,
    )
    return proc.returncode, proc.stdout + proc.stderr


def main():
    if len(sys.argv) != 4:
        print("usage: check_round20_fix.py <validator.py> <new_draft> <v115_draft>")
        return 1
    validator, new_draft, old_draft = sys.argv[1:]
    failures = []

    rc_new, out_new = run(validator, new_draft)
    if rc_new != 0 or "PASS" not in out_new:
        failures.append(f"validator fails the new draft: {out_new[-200:]}")
    rc_old, out_old = run(validator, old_draft)
    if rc_old == 0:
        failures.append("validator still passes the v115 draft - assertion 20 toothless")
    elif not re.search(r"(?i)assertion\s*#?\s*20", out_old):
        failures.append(f"v115 rejection does not cite assertion 20: {out_old[-200:]}")

    graph = json.load(open(new_draft, encoding="utf-8"))
    nodes = {n.get("id"): n for n in graph.get("nodes", [])}
    edges = graph.get("edges", [])

    pinned = nodes.get("n_goal_search_offered_anchor")
    if pinned is None:
        failures.append("n_goal_search_offered_anchor missing")
    else:
        data = pinned.get("data", {})
        try:
            body = json.loads(str(data.get("body", "{}")))
        except json.JSONDecodeError:
            body = {}
            failures.append("offered-anchor body is not valid JSON")
        if body.get("from") != "{{slot_1_start}}" or body.get("to") != "{{slot_1_start}}":
            failures.append(f"offered-anchor not pinned to the offered date: from={body.get('from')!r}")
        if body.get("time_pref") != "anchor={{goal_anchor}}":
            failures.append(f"offered-anchor time_pref wrong: {body.get('time_pref')!r}")
        extra = set(body) - ALLOWED_BODY_FIELDS
        if extra:
            failures.append(f"offered-anchor body outside contract: {sorted(extra)}")
        if "anchor_exact" not in json.dumps(data.get("responseData") or []):
            failures.append("offered-anchor does not map anchor_exact")
        routes = json.dumps(data.get("responsePathways") or []) + json.dumps(
            [e for e in edges if e.get("source") == "n_goal_search_offered_anchor"]
        )
        if "n_gate_1" not in routes:
            failures.append("offered-anchor exact-match path does not reach n_gate_1")
        if "n_time_pick_offer" not in routes:
            failures.append("offered-anchor non-exact path does not reach n_time_pick_offer")

    named_from_response = [
        e.get("target") for e in edges
        if e.get("source") == "n_goal_response"
        and re.search(r"(?i)names?\b.*time", str((e.get("data") or {}).get("label", "")))
    ]
    if "n_goal_search_offered_anchor" not in named_from_response:
        failures.append(f"n_goal_response named-time edge does not target the pinned search: {named_from_response}")
    named_from_ask = [
        e.get("target") for e in edges
        if e.get("source") == "n_goal_ask"
        and re.search(r"(?i)names?\b.*time|near|around", str((e.get("data") or {}).get("label", "")))
    ]
    if named_from_ask and "n_goal_search_offered_anchor" in named_from_ask:
        failures.append("pre-offer named time must not use the offered-date-pinned search")

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
    print("PASS: date-pinned anchor search wired straight to confirmation, guards intact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
