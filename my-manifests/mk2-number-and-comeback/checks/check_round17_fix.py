#!/usr/bin/env python3
"""Executable check for round 17: no invented times, no false booking claims.

1. worker validator passes the new draft and rejects the v112 draft citing assertion 17;
2. every patient-facing wait node except the confirm nodes carries the
   NO-BOOKING-CLAIM marker;
3. n_goal_response carries TIME-GRID (only literal slot values may be spoken,
   off-grid asks get the nearest real slots) and keeps OFFER-INTEGRITY;
4. n_goal_ask (pre-offer) still holds no slot templates - it must never speak a
   clock time at all;
5. only n_confirm_1/n_confirm_2 may assert a completed booking, and each is
   reachable only from its matching book webhook.
"""

import json
import re
import subprocess
import sys

WAIT_NODES = (
    "n_goal_ask", "n_goal_response", "n_mixed_intent",
    "n_gate_1", "n_gate_2", "n_post_booking",
    "n_date_conflict", "n_date_conflict_retry",
)


def run(validator, draft):
    proc = subprocess.run(
        [sys.executable, validator, "--draft", draft],
        capture_output=True, text=True, timeout=300,
    )
    return proc.returncode, proc.stdout + proc.stderr


def main():
    if len(sys.argv) != 4:
        print("usage: check_round17_fix.py <validator.py> <new_draft> <v112_draft>")
        return 1
    validator, new_draft, old_draft = sys.argv[1:]
    failures = []

    rc_new, out_new = run(validator, new_draft)
    if rc_new != 0 or "PASS" not in out_new:
        failures.append(f"validator fails the new draft: {out_new[-200:]}")
    rc_old, out_old = run(validator, old_draft)
    if rc_old == 0:
        failures.append("validator still passes the v112 draft - assertion 17 toothless")
    elif not re.search(r"(?i)assertion\s*#?\s*17", out_old):
        failures.append(f"v112 rejection does not cite assertion 17: {out_old[-200:]}")

    graph = json.load(open(new_draft, encoding="utf-8"))
    nodes = {n.get("id"): n for n in graph.get("nodes", [])}
    edges = graph.get("edges", [])

    for nid in WAIT_NODES:
        node = nodes.get(nid)
        if node is None:
            continue
        prompt = str(node.get("data", {}).get("prompt", ""))
        if "NO-BOOKING-CLAIM:" not in prompt:
            failures.append(f"{nid} prompt lacks the NO-BOOKING-CLAIM marker")

    resp = str(nodes.get("n_goal_response", {}).get("data", {}).get("prompt", ""))
    if "TIME-GRID:" not in resp:
        failures.append("n_goal_response prompt lacks the TIME-GRID rule")
    if "OFFER-INTEGRITY" not in resp:
        failures.append("n_goal_response lost the OFFER-INTEGRITY rule")

    ask = str(nodes.get("n_goal_ask", {}).get("data", {}).get("prompt", ""))
    if "{{slot_" in ask:
        failures.append("n_goal_ask prompt gained slot templates - it must never speak a time")

    for idx in ("1", "2"):
        cid = f"n_confirm_{idx}"
        if cid not in nodes:
            failures.append(f"{cid} missing")
            continue
        sources = {e.get("source") for e in edges if e.get("target") == cid}
        book_sources = {s for s in sources if s == f"n_book_{idx}"}
        if not book_sources:
            rp = json.dumps(nodes.get(f"n_book_{idx}", {}).get("data", {}))
            if cid not in rp:
                failures.append(f"{cid} is not reached from n_book_{idx}")
        stray = {s for s in sources if s not in (f"n_book_{idx}", f"n_reconcile_{idx}")}
        if stray:
            failures.append(f"{cid} reachable from non-booking nodes {sorted(stray)}")

    if failures:
        print("FAIL: " + " | ".join(failures))
        return 1
    print("PASS: booking-claim ban, time-grid rule, and confirm-node containment verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
