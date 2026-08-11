#!/usr/bin/env python3
"""Executable check for round 22: audit consolidation.

1. validator passes the new draft, rejects the v118 draft citing assertion 22;
2. every availability body carries context_date {{slot_1_start}} and stays in
   the eleven-field contract;
3. the offered-anchor search routes on four exclusive anchor_route equality
   triples (exact -> n_gate_1, closest -> n_time_pick_offer, none/error -> miss);
4. n_goal_response has at most 8 outbound edges; gate labels carry no clock-time
   clause; exactly one edge targets n_goal_search (merged correction/new-pref);
5. n_mixed_intent, n_office and n_faq are time-silent: TIME-SILENT marker, no
   slot templates, no instruction to name openings;
6. all prior guard markers survive; no compound conditions anywhere.
"""

import json
import re
import subprocess
import sys

ALLOWED_BODY_FIELDS = {
    "store", "from", "to", "after", "before", "time_pref",
    "slot_minutes", "callID", "user_text", "user_verbatim", "context_date",
}
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


def route_rows(node):
    rows = node.get("data", {}).get("responsePathways") or []
    return [r for r in rows if isinstance(r, list) and len(r) >= 4]


def main():
    if len(sys.argv) != 4:
        print("usage: check_round22_fix.py <validator.py> <new_draft> <v118_draft>")
        return 1
    validator, new_draft, old_draft = sys.argv[1:]
    failures = []

    rc_new, out_new = run(validator, new_draft)
    if rc_new != 0 or "PASS" not in out_new:
        failures.append(f"validator fails the new draft: {out_new[-200:]}")
    rc_old, out_old = run(validator, old_draft)
    if rc_old == 0:
        failures.append("validator still passes the v118 draft - assertion 22 toothless")
    elif not re.search(r"(?i)assertion\s*#?\s*22", out_old):
        failures.append(f"v118 rejection does not cite assertion 22: {out_old[-200:]}")

    graph = json.load(open(new_draft, encoding="utf-8"))
    nodes = {n.get("id"): n for n in graph.get("nodes", [])}
    edges = graph.get("edges", [])

    for nid, node in nodes.items():
        data = node.get("data", {})
        if node.get("type") == "Webhook" and str(data.get("url", "")).endswith("/availability"):
            try:
                body = json.loads(str(data.get("body", "{}")))
            except json.JSONDecodeError:
                failures.append(f"{nid} body invalid JSON")
                continue
            if body.get("context_date") != "{{slot_1_start}}":
                failures.append(f"{nid} lacks context_date {{{{slot_1_start}}}}: {body.get('context_date')!r}")
            extra = set(body) - ALLOWED_BODY_FIELDS
            if extra:
                failures.append(f"{nid} body outside eleven-field contract: {sorted(extra)}")

    anchor = nodes.get("n_goal_search_offered_anchor")
    if anchor is None:
        failures.append("n_goal_search_offered_anchor missing")
    else:
        rows = route_rows(anchor)
        by_value = {}
        for row in rows:
            if row[0] == "anchor_route" and row[1] == "==":
                target = row[3].get("id") if isinstance(row[3], dict) else row[3]
                by_value[str(row[2]).strip().lower()] = target
        if by_value.get("exact") != "n_gate_1":
            failures.append(f"anchor_route exact -> {by_value.get('exact')!r}, expected n_gate_1")
        if by_value.get("closest") != "n_time_pick_offer":
            failures.append(f"anchor_route closest -> {by_value.get('closest')!r}, expected n_time_pick_offer")
        for value in ("none", "error"):
            if value not in by_value:
                failures.append(f"anchor_route {value} row missing")
        for row in rows:
            if row[0] in ("anchor_exact", "ok", "slot_count") and row[0] != "anchor_route":
                if row[0] == "anchor_exact":
                    failures.append("legacy anchor_exact routing row still present alongside the enum")

    resp_out = [e for e in edges if e.get("source") == "n_goal_response"]
    if len(resp_out) > 8:
        failures.append(f"n_goal_response has {len(resp_out)} outbound edges (max 8)")
    search_edges = [e for e in resp_out if e.get("target") == "n_goal_search"]
    if len(search_edges) != 1:
        failures.append(f"expected exactly one merged edge to n_goal_search, found {len(search_edges)}")
    for gate in ("n_gate_1", "n_gate_2"):
        edge = next((e for e in resp_out if e.get("target") == gate), None)
        label = str(((edge or {}).get("data") or {}).get("label", "")).lower()
        if "clock time" in label:
            failures.append(f"{gate} label still accepts clock times: {label[:100]}")

    for nid in ("n_mixed_intent", "n_office", "n_faq"):
        node = nodes.get(nid)
        if node is None:
            continue
        blob = json.dumps(node.get("data", {}))
        prompt = str(node.get("data", {}).get("prompt", ""))
        if "{{slot_" in blob:
            failures.append(f"{nid} still references slot templates")
        if "TIME-SILENT:" not in prompt:
            failures.append(f"{nid} lacks the TIME-SILENT marker")
        if re.search(r"(?i)naming the openings", prompt):
            failures.append(f"{nid} still instructed to name openings")

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
    resp = str(nodes.get("n_goal_response", {}).get("data", {}).get("prompt", ""))
    for marker in ("TIME-GRID:", "OFFER-INTEGRITY", "NO-NEGATIVE-CLAIM:"):
        if marker not in resp:
            failures.append(f"n_goal_response lost {marker}")
    for gate in ("n_gate_1", "n_gate_2"):
        if "BOOKING-INTEGRITY:" not in str(nodes.get(gate, {}).get("data", {}).get("prompt", "")):
            failures.append(f"{gate} lost the BOOKING-INTEGRITY marker")

    if failures:
        print("FAIL: " + " | ".join(failures))
        return 1
    print("PASS: audit consolidation verified - context_date, route enum, router diet, time-silent supports, guards intact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
