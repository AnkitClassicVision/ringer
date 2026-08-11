#!/usr/bin/env python3
"""Verify the reachability / dead-end report (lane 3, manifestD).

Recomputes the mechanical layer independently from pathway-v87.json — start
node, edges-only forward reachability, zero-inbound End nodes, edges-only
path-to-End, and the exact set of isGlobal nodes — and requires the worker's
mechanical fields to match. Judgment fields (effective unreachability under
global-node semantics, condition-order shadowing, never-match conditions) are
checked for coverage, allowed values, and substantive rationale.
Prints every failure reason; exit 0 only when all assertions hold.
"""

import argparse
import json
import sys

ORDER_VERDICTS = {"no_shadowing", "shadowed", "cannot_determine"}


def load_json(path, label, errors):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        errors.append(f"{label} not found at {path}")
    except json.JSONDecodeError as exc:
        errors.append(f"{label} is not valid JSON: {exc}")
    return None


def bfs(adj, starts):
    seen = set(starts)
    frontier = list(starts)
    while frontier:
        node = frontier.pop()
        for nxt in adj.get(node, ()):
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
    return seen


def expect_sorted_equal(report, key, expected, errors):
    got = report.get(key)
    if not isinstance(got, list) or sorted(map(str, got)) != sorted(expected):
        errors.append(f"'{key}' must equal the computed set {sorted(expected)}; reported {got!r}")
        return False
    return True


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
    adj, radj = {}, {}
    for e in edges:
        adj.setdefault(e["source"], []).append(e["target"])
        radj.setdefault(e["target"], []).append(e["source"])

    start_nodes = [nid for nid, n in nodes.items() if n["data"].get("isStart")]
    end_ids = {nid for nid, n in nodes.items() if n["type"] == "End Call"}
    global_ids = {nid for nid, n in nodes.items() if n["data"].get("isGlobal")}
    webhook_ids = {nid for nid, n in nodes.items() if n["type"] == "Webhook"}

    reachable = bfs(adj, start_nodes)
    edges_only_unreachable = sorted(node_ids - reachable)
    zero_inbound_ends = sorted(nid for nid in end_ids if nid not in radj)
    can_reach_end = bfs(radj, list(end_ids))
    edges_only_no_path_to_end = sorted(node_ids - can_reach_end)

    # Mechanical layer: must match exactly.
    if report.get("start_node") not in start_nodes:
        errors.append(f"start_node must be one of {start_nodes} (isStart in the pathway); reported {report.get('start_node')!r}")
    expect_sorted_equal(report, "edges_only_unreachable_from_start", edges_only_unreachable, errors)
    expect_sorted_equal(report, "zero_inbound_edge_end_nodes", zero_inbound_ends, errors)
    expect_sorted_equal(report, "edges_only_no_path_to_end", edges_only_no_path_to_end, errors)

    # Global nodes: exact id coverage, substantive effect analysis.
    gentries = report.get("global_nodes")
    if not isinstance(gentries, list):
        errors.append("'global_nodes' must be a list")
    else:
        got_ids = sorted(str(g.get("id")) for g in gentries if isinstance(g, dict))
        if got_ids != sorted(global_ids):
            errors.append(f"global_nodes ids must equal the computed isGlobal set {sorted(global_ids)}; reported {got_ids}")
        for g in gentries:
            if isinstance(g, dict):
                effect = g.get("effect_on_reachability")
                if not isinstance(effect, str) or len(effect.strip()) < 40:
                    errors.append(f"global_nodes.{g.get('id')}: 'effect_on_reachability' must be at least 40 chars")

    # Judgment layer: effectively unreachable must be a defensible subset.
    eff = report.get("effectively_unreachable")
    if not isinstance(eff, list):
        errors.append("'effectively_unreachable' must be a list (may be empty)")
    else:
        for entry in eff:
            if not isinstance(entry, dict) or "id" not in entry:
                errors.append(f"effectively_unreachable entries must be objects with 'id': {entry!r}")
                continue
            nid = entry["id"]
            if nid not in edges_only_unreachable:
                errors.append(f"effectively_unreachable.{nid}: not in the edges-only unreachable set, so it cannot be effectively unreachable")
            if nid in global_ids:
                errors.append(f"effectively_unreachable.{nid}: node is isGlobal, hence reachable from anywhere — contradiction")
            reason = entry.get("reason")
            if not isinstance(reason, str) or len(reason.strip()) < 40:
                errors.append(f"effectively_unreachable.{nid}: 'reason' must be at least 40 chars")

    # Condition-order review: one verdict per webhook node.
    order = report.get("condition_order_review")
    if not isinstance(order, list):
        errors.append("'condition_order_review' must be a list")
    else:
        got = {str(o.get("node")): o for o in order if isinstance(o, dict)}
        missing = sorted(webhook_ids - set(got))
        extra = sorted(set(got) - webhook_ids)
        if missing:
            errors.append(f"condition_order_review: missing webhook nodes {missing}")
        if extra:
            errors.append(f"condition_order_review: ids that are not webhook nodes: {extra}")
        for nid, o in got.items():
            if o.get("verdict") not in ORDER_VERDICTS:
                errors.append(f"condition_order_review.{nid}: verdict must be one of {sorted(ORDER_VERDICTS)}, got {o.get('verdict')!r}")
            reason = o.get("reason")
            if not isinstance(reason, str) or len(reason.strip()) < 60:
                errors.append(f"condition_order_review.{nid}: 'reason' must be at least 60 chars")

    # Never-match conditions: may be empty, but entries must be grounded.
    never = report.get("never_match_conditions")
    if not isinstance(never, list):
        errors.append("'never_match_conditions' must be a list (may be empty)")
    else:
        for entry in never:
            if not isinstance(entry, dict):
                errors.append(f"never_match_conditions entries must be objects: {entry!r}")
                continue
            if entry.get("node") not in node_ids:
                errors.append(f"never_match_conditions: node {entry.get('node')!r} does not exist in the pathway")
            why = entry.get("why_never_matches")
            if not isinstance(why, str) or len(why.strip()) < 60:
                errors.append(f"never_match_conditions.{entry.get('node')}: 'why_never_matches' must be at least 60 chars")

    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        print(f"\n{len(errors)} failure(s) in {args.report}")
        return 1
    print(
        "PASS: mechanical reachability layer matches the recomputation "
        f"({len(node_ids)} nodes, {len(edges)} edges, {len(global_ids)} globals) and judgment layers are complete."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
