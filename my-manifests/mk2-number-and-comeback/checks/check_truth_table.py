#!/usr/bin/env python3
"""Verify the booking error-routing truth table report (lane 1, manifestD).

Cross-checks every mechanically derivable claim in the worker's truth-table.json
against pathway-v87.json itself: the exact responsePathways tuples of the four
write-path webhook nodes, their outgoing edges, the inbound set of
e_safe_failure, and the direct/transitive reachability of e_safe_failure from
the book nodes. Judgment fields (scenario destinations, the 502 verdict) are
checked for coverage, allowed values, and substantive rationale.
Prints every failure reason; exit 0 only when all assertions hold.
"""

import argparse
import json
import sys

AUDIT_NODES = ["n_book_1", "n_book_2", "n_verify_1", "n_verify_2"]
REQUIRED_SCENARIOS = [
    "success_true",
    "success_false_no_error_code",
    "slot_conflict",
    "http_502_gateway_unreachable",
    "http_423_write_unverified",
    "http_403_authorization_denied",
    "timeout_or_empty_response",
]


def load_json(path, label, errors):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        errors.append(f"{label} not found at {path}")
    except json.JSONDecodeError as exc:
        errors.append(f"{label} is not valid JSON: {exc}")
    return None


def norm_val(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def pathway_rp_tuples(node):
    out = []
    for entry in node["data"].get("responsePathways", []):
        var, op, value, dest = entry
        out.append((str(var), str(op), norm_val(value), dest["id"]))
    return out


def worker_rp_tuples(entries, ctx, errors):
    out = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"{ctx}: response_pathways[{i}] is not an object")
            return None
        missing = [k for k in ("variable", "operator", "value", "destination") if k not in entry]
        if missing:
            errors.append(f"{ctx}: response_pathways[{i}] missing keys {missing}")
            return None
        out.append(
            (
                str(entry["variable"]),
                str(entry["operator"]),
                norm_val(entry["value"]),
                str(entry["destination"]),
            )
        )
    return out


def need_text(obj, key, minlen, ctx, errors):
    value = obj.get(key)
    if not isinstance(value, str) or len(value.strip()) < minlen:
        errors.append(f"{ctx}: '{key}' must be a string of at least {minlen} chars (got {value!r:.80})")
        return False
    return True


def bfs(adj, starts):
    seen = set(starts)
    frontier = list(starts)
    while frontier:
        node = frontier.pop()
        for nxt in adj.get(node, ()):  # noqa: B023
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
    return seen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pathway", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    errors = []
    pathway = load_json(args.pathway, "pathway JSON", errors)
    report = load_json(args.report, "worker report", errors)
    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        return 1

    nodes = {n["id"]: n for n in pathway["nodes"]}
    edges = pathway["edges"]
    node_ids = set(nodes)
    adj = {}
    for e in edges:
        adj.setdefault(e["source"], []).append(e["target"])

    # 1. Exact responsePathways + edges per audited node.
    rnodes = report.get("nodes")
    if not isinstance(rnodes, dict):
        errors.append("report has no 'nodes' object")
        rnodes = {}
    for nid in AUDIT_NODES:
        entry = rnodes.get(nid)
        if not isinstance(entry, dict):
            errors.append(f"nodes.{nid}: missing from report")
            continue
        expected = pathway_rp_tuples(nodes[nid])
        got = worker_rp_tuples(entry.get("response_pathways", []), f"nodes.{nid}", errors)
        if got is not None and got != expected:
            errors.append(
                f"nodes.{nid}: response_pathways do not match the pathway JSON.\n"
                f"  expected (in order): {expected}\n  reported: {got}"
            )
        exp_edges = sorted(
            (e["target"], (e.get("data", {}) or {}).get("label") or "") for e in edges if e["source"] == nid
        )
        rep_edges = entry.get("edges", [])
        if not isinstance(rep_edges, list):
            errors.append(f"nodes.{nid}: 'edges' must be a list")
        else:
            got_edges = sorted((str(x.get("target")), str(x.get("label") or "")) for x in rep_edges if isinstance(x, dict))
            if got_edges != exp_edges:
                errors.append(
                    f"nodes.{nid}: outgoing edges do not match the pathway JSON.\n"
                    f"  expected: {exp_edges}\n  reported: {got_edges}"
                )

    # 2. Inbound set of e_safe_failure.
    expected_inbound = sorted({e["source"] for e in edges if e["target"] == "e_safe_failure"})
    got_inbound = report.get("e_safe_failure_inbound")
    if not isinstance(got_inbound, list) or sorted(map(str, got_inbound)) != expected_inbound:
        errors.append(
            f"e_safe_failure_inbound must list exactly the edge sources into e_safe_failure: "
            f"expected {expected_inbound}, reported {got_inbound}"
        )

    # 3. Direct / transitive reachability of e_safe_failure from the book nodes.
    direct = any(e["source"] in ("n_book_1", "n_book_2") and e["target"] == "e_safe_failure" for e in edges)
    transitive = "e_safe_failure" in bfs(adj, ["n_book_1", "n_book_2"])
    reach = report.get("e_safe_failure_reachable_from_booking_write")
    if not isinstance(reach, dict):
        errors.append("report has no 'e_safe_failure_reachable_from_booking_write' object")
    else:
        if reach.get("direct_route_from_book_nodes") is not direct:
            errors.append(
                f"direct_route_from_book_nodes must be {direct} (computed from edges out of n_book_1/n_book_2); "
                f"reported {reach.get('direct_route_from_book_nodes')!r}"
            )
        if reach.get("transitive_route_exists") is not transitive:
            errors.append(
                f"transitive_route_exists must be {transitive} (computed by BFS from the book nodes); "
                f"reported {reach.get('transitive_route_exists')!r}"
            )
        need_text(reach, "explanation", 150, "e_safe_failure_reachable_from_booking_write", errors)

    # 4. Scenario coverage.
    scenarios = report.get("scenarios")
    if not isinstance(scenarios, list):
        errors.append("report has no 'scenarios' list")
        scenarios = []
    by_id = {s.get("scenario_id"): s for s in scenarios if isinstance(s, dict)}
    for sid in REQUIRED_SCENARIOS:
        sc = by_id.get(sid)
        if sc is None:
            errors.append(f"scenarios: required scenario '{sid}' is missing")
            continue
        dest = sc.get("destination")
        if dest not in node_ids and dest != "fallthrough_unknown":
            errors.append(
                f"scenarios.{sid}: destination {dest!r} is neither an existing node id nor 'fallthrough_unknown'"
            )
        if not isinstance(sc.get("variables_after_extraction"), dict):
            errors.append(f"scenarios.{sid}: 'variables_after_extraction' object is required")
        need_text(sc, "destination_reasoning", 120, f"scenarios.{sid}", errors)

    # 5. The 502 verdict.
    verdict = report.get("verdict_502_distinguishable")
    if not isinstance(verdict, dict):
        errors.append("report has no 'verdict_502_distinguishable' object")
    else:
        if verdict.get("verdict") not in ("yes", "no", "partial"):
            errors.append(
                f"verdict_502_distinguishable.verdict must be yes|no|partial, got {verdict.get('verdict')!r}"
            )
        need_text(verdict, "explanation", 200, "verdict_502_distinguishable", errors)

    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        print(f"\n{len(errors)} failure(s) in {args.report}")
        return 1
    print(
        "PASS: truth table matches pathway-v87 routing exactly "
        f"({len(AUDIT_NODES)} nodes, {len(REQUIRED_SCENARIOS)} scenarios, 502 verdict present)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
