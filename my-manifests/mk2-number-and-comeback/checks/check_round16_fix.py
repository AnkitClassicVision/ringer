#!/usr/bin/env python3
"""Executable check for round 16: correction routing + fail-closed booking guard.

1. worker validator passes the new draft and rejects the v111 draft citing assertion 16;
2. a correction-labeled edge runs n_goal_response -> n_goal_search;
3. both gates carry the BOOKING-INTEGRITY marker and a structural re-check edge
   back to the fresh search;
4. gate copy still templates its own slot variables (no untemplated restatement).
"""

import json
import re
import subprocess
import sys


def run(validator, draft):
    proc = subprocess.run(
        [sys.executable, validator, "--draft", draft],
        capture_output=True, text=True, timeout=300,
    )
    return proc.returncode, proc.stdout + proc.stderr


def main():
    if len(sys.argv) != 4:
        print("usage: check_round16_fix.py <validator.py> <new_draft> <v111_draft>")
        return 1
    validator, new_draft, old_draft = sys.argv[1:]
    failures = []

    rc_new, out_new = run(validator, new_draft)
    if rc_new != 0 or "PASS" not in out_new:
        failures.append(f"validator fails the new draft: {out_new[-200:]}")
    rc_old, out_old = run(validator, old_draft)
    if rc_old == 0:
        failures.append("validator still passes the v111 draft - assertion 16 toothless")
    elif not re.search(r"(?i)assertion\s*#?\s*16", out_old):
        failures.append(f"v111 rejection does not cite assertion 16: {out_old[-200:]}")

    graph = json.load(open(new_draft, encoding="utf-8"))
    nodes = {n.get("id"): n for n in graph.get("nodes", [])}
    edges = graph.get("edges", [])

    corrections = [
        e for e in edges
        if e.get("source") == "n_goal_response" and e.get("target") == "n_goal_search"
        and "correct" in str((e.get("data") or {}).get("label", "")).lower()
    ]
    if not corrections:
        failures.append("no correction-labeled edge n_goal_response -> n_goal_search")

    for gate in ("n_gate_1", "n_gate_2"):
        data = nodes.get(gate, {}).get("data", {})
        prompt = str(data.get("prompt", ""))
        if "BOOKING-INTEGRITY:" not in prompt:
            failures.append(f"{gate} prompt lacks the BOOKING-INTEGRITY marker")
        if not any(e.get("source") == gate and e.get("target") == "n_goal_search" for e in edges):
            failures.append(f"{gate} has no re-check edge to n_goal_search")
        idx = gate[-1]
        if f"{{{{slot_{idx}_start}}}}" not in json.dumps(data):
            failures.append(f"{gate} no longer templates slot_{idx}_start")

    if failures:
        print("FAIL: " + " | ".join(failures))
        return 1
    print("PASS: correction routing + fail-closed booking-integrity guard verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
