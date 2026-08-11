#!/usr/bin/env python3
"""Verify the SPEC-v62 conformance report against pathway v87 (lane 5, manifestD).

Recomputes the mechanically checkable facts from pathway-v87.json — which nodes
carry the (212) 219-2219 number, any '855' remnants, where the CLOSE line
lives, e_defer's existence/type/edges/text, n_confirm's adjacency, and the
analysis_options value — and requires the worker's reported facts to match
exactly. Gate verdicts G1-G6 and design items 1-7 are judgment: they must be
present, use an allowed verdict, and carry substantive evidence.
Prints every failure reason; exit 0 only when all assertions hold.
"""

import argparse
import json
import sys

VERDICTS = {"PASS", "FAIL", "NOT_VERIFIABLE"}
NUMBER = "(212) 219-2219"
CLOSE = "You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219"
DEFER = "For that you'll have to contact the MK2 Optical office at (212) 219-2219"
TEXT_FIELDS = ("prompt", "text", "globalLabel", "name")
GATES = ["G1", "G2", "G3", "G4", "G5", "G6"]
DESIGN_ITEMS = [1, 2, 3, 4, 5, 6, 7]


def load_json(path, label, errors):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        errors.append(f"{label} not found at {path}")
    except json.JSONDecodeError as exc:
        errors.append(f"{label} is not valid JSON: {exc}")
    return None


def node_text_blob(node):
    return "\n".join(str(node["data"].get(field, "")) for field in TEXT_FIELDS)


def expect_sorted_equal(container, key, expected, ctx, errors):
    got = container.get(key)
    if not isinstance(got, list) or sorted(map(str, got)) != sorted(expected):
        errors.append(f"{ctx}.{key} must equal the computed list {sorted(expected)}; reported {got!r}")


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

    number_nodes = sorted(nid for nid, n in nodes.items() if NUMBER in node_text_blob(n))
    nodes_855 = sorted(nid for nid, n in nodes.items() if "855" in node_text_blob(n))
    close_nodes = sorted(nid for nid, n in nodes.items() if CLOSE in node_text_blob(n))
    n_confirm_adj = sorted({e["target"] for e in edges if e["source"] == "n_confirm"})

    e_defer = nodes.get("e_defer")
    defer_facts = {
        "exists": e_defer is not None,
        "node_type": e_defer["type"] if e_defer else None,
        "outgoing_edge_count": sum(1 for e in edges if e["source"] == "e_defer"),
        "text_matches_defer_verbatim": bool(e_defer) and e_defer["data"].get("text") == DEFER,
    }
    analysis_options = pathway.get("analysis_options")

    facts = report.get("facts")
    if not isinstance(facts, dict):
        errors.append("report has no 'facts' object")
    else:
        expect_sorted_equal(facts, "number_carrier_nodes", number_nodes, "facts", errors)
        expect_sorted_equal(facts, "nodes_containing_855", nodes_855, "facts", errors)
        expect_sorted_equal(facts, "close_carrier_nodes", close_nodes, "facts", errors)
        expect_sorted_equal(facts, "n_confirm_adjacency", n_confirm_adj, "facts", errors)
        got_defer = facts.get("e_defer")
        if not isinstance(got_defer, dict):
            errors.append("facts.e_defer object is required")
        else:
            for key, expected in defer_facts.items():
                if got_defer.get(key) != expected:
                    errors.append(f"facts.e_defer.{key} must be {expected!r} (computed); reported {got_defer.get(key)!r}")
        if "analysis_options_value" not in (facts or {}):
            errors.append("facts.analysis_options_value is required (report the pathway's literal value, null included)")
        elif facts.get("analysis_options_value") != analysis_options:
            errors.append(
                f"facts.analysis_options_value must equal the pathway's actual value {analysis_options!r}; "
                f"reported {facts.get('analysis_options_value')!r}"
            )

    def check_verdict_entries(key, wanted, label_field, errors):
        entries = report.get(key)
        if not isinstance(entries, list):
            errors.append(f"report has no '{key}' list")
            return
        by_label = {e.get(label_field): e for e in entries if isinstance(e, dict)}
        for label in wanted:
            entry = by_label.get(label)
            if entry is None:
                errors.append(f"{key}: entry for {label!r} is missing")
                continue
            if entry.get("verdict") not in VERDICTS:
                errors.append(f"{key}.{label}: verdict must be one of {sorted(VERDICTS)}, got {entry.get('verdict')!r}")
            evidence = entry.get("evidence")
            if not isinstance(evidence, str) or len(evidence.strip()) < 80:
                errors.append(f"{key}.{label}: 'evidence' must be a string of at least 80 chars")

    check_verdict_entries("gates", GATES, "gate", errors)
    check_verdict_entries("design_items", DESIGN_ITEMS, "item", errors)

    if not isinstance(report.get("extra_findings"), list):
        errors.append("'extra_findings' must be a list (may be empty)")

    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        print(f"\n{len(errors)} failure(s) in {args.report}")
        return 1
    print("PASS: conformance facts match the recomputation; all gates G1-G6 and design items 1-7 carry verdicts with evidence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
