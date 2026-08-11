#!/usr/bin/env python3
"""Verify the End-node patient-facing text audit (lane 2, manifestD).

Asserts the worker covered every End Call node in pathway-v87.json, quoted each
node's data.text byte-for-byte, classified every claim with an allowed label,
and analyzed ambiguous-response reachability with substantive rationale.
e_booking_failed and e_safe_failure must carry at least one concrete inbound
path, because both have inbound webhook edges in the graph.
Prints every failure reason; exit 0 only when all assertions hold.
"""

import argparse
import json
import sys

CLASSIFICATIONS = {"definite_negative", "definite_positive", "neutral"}
SEVERITIES = {"critical", "major", "minor", "none"}
MUST_HAVE_PATHS = {"e_booking_failed", "e_safe_failure"}


def load_json(path, label, errors):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        errors.append(f"{label} not found at {path}")
    except json.JSONDecodeError as exc:
        errors.append(f"{label} is not valid JSON: {exc}")
    return None


def need_text(obj, key, minlen, ctx, errors):
    value = obj.get(key)
    if not isinstance(value, str) or len(value.strip()) < minlen:
        errors.append(f"{ctx}: '{key}' must be a string of at least {minlen} chars")


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

    end_nodes = {n["id"]: n for n in pathway["nodes"] if n["type"] == "End Call"}

    entries = report.get("end_nodes")
    if not isinstance(entries, list):
        print("FAIL: report has no 'end_nodes' list")
        return 1
    by_id = {e.get("id"): e for e in entries if isinstance(e, dict)}

    missing = sorted(set(end_nodes) - set(by_id))
    extra = sorted(set(by_id) - set(end_nodes))
    if missing:
        errors.append(f"end_nodes: missing End Call nodes {missing}")
    if extra:
        errors.append(f"end_nodes: ids that are not End Call nodes in the pathway: {extra}")

    for nid, entry in by_id.items():
        if nid not in end_nodes:
            continue
        actual = end_nodes[nid]["data"]
        ctx = f"end_nodes.{nid}"
        if entry.get("outcome") != actual.get("outcome"):
            errors.append(
                f"{ctx}: outcome mismatch — pathway says {actual.get('outcome')!r}, report says {entry.get('outcome')!r}"
            )
        if entry.get("text") != actual.get("text"):
            errors.append(
                f"{ctx}: text is not byte-for-byte identical to the pathway.\n"
                f"  pathway: {actual.get('text')!r}\n  report:  {entry.get('text')!r}"
            )
        claims = entry.get("claims")
        if not isinstance(claims, list) or not claims:
            errors.append(f"{ctx}: 'claims' must be a non-empty list")
        else:
            for i, claim in enumerate(claims):
                if not isinstance(claim, dict):
                    errors.append(f"{ctx}: claims[{i}] is not an object")
                    continue
                if claim.get("classification") not in CLASSIFICATIONS:
                    errors.append(
                        f"{ctx}: claims[{i}].classification must be one of {sorted(CLASSIFICATIONS)}, "
                        f"got {claim.get('classification')!r}"
                    )
                if not isinstance(claim.get("claim_text"), str) or not claim.get("claim_text", "").strip():
                    errors.append(f"{ctx}: claims[{i}].claim_text must be a non-empty string")
        amb = entry.get("ambiguous_reachability")
        if not isinstance(amb, dict):
            errors.append(f"{ctx}: 'ambiguous_reachability' object is required")
        else:
            if not isinstance(amb.get("reachable_from_ambiguous_gateway_response"), bool):
                errors.append(f"{ctx}: ambiguous_reachability.reachable_from_ambiguous_gateway_response must be a bool")
            paths = amb.get("paths")
            if not isinstance(paths, list):
                errors.append(f"{ctx}: ambiguous_reachability.paths must be a list (may be empty)")
            elif nid in MUST_HAVE_PATHS and not paths:
                errors.append(
                    f"{ctx}: ambiguous_reachability.paths must be non-empty — this node has inbound "
                    "webhook edges in the graph and the paths are enumerable facts"
                )
            need_text(amb, "explanation", 100, f"{ctx}.ambiguous_reachability", errors)
        defect = entry.get("defect")
        if not isinstance(defect, dict):
            errors.append(f"{ctx}: 'defect' object is required")
        else:
            if defect.get("severity") not in SEVERITIES:
                errors.append(f"{ctx}: defect.severity must be one of {sorted(SEVERITIES)}, got {defect.get('severity')!r}")
            need_text(defect, "explanation", 80, f"{ctx}.defect", errors)

    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        print(f"\n{len(errors)} failure(s) in {args.report}")
        return 1
    print(f"PASS: all {len(end_nodes)} End Call nodes audited with verbatim text and complete claim analysis.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
