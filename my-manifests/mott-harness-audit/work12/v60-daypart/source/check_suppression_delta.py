#!/usr/bin/env python3
"""Structural suppression gate; a pass never substitutes for the live behavioral suite."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

HEADER = "STRUCTURAL SUPPRESSION GATE: a pass never substitutes for the live behavioral suite."
EXIT_WEBHOOK = {"e_stop": "n_suppress_stop", "e_not_me": "n_suppress_not_me"}
VALID_REASONS = {"stop", "unsubscribe", "complaint", "manual", "wrong_number"}
VALID_SOURCES = {"sms_reply", "voice", "manual", "import"}


def load_json(path: str | pathlib.Path) -> dict[str, Any]:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def _nodes(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {node["id"]: node for node in graph.get("nodes", [])}


def check_suppression(
    graph: dict[str, Any], baseline: dict[str, Any], expected_changed: set[str]
) -> list[str]:
    problems: list[str] = []
    nodes, base_nodes = _nodes(graph), _nodes(baseline)
    edges = graph.get("edges", [])
    suppressors = {
        nid: node for nid, node in nodes.items()
        if node.get("type") == "Webhook"
        and str(node.get("data", {}).get("url") or "").endswith("/sms-suppression")
    }
    if not suppressors:
        problems.append(
            "suppression subgraph: no Webhook targets endpoint path /sms-suppression"
        )
    suppressor_ids = set(suppressors)

    for exit_id, required_webhook in sorted(EXIT_WEBHOOK.items()):
        if exit_id not in nodes:
            problems.append(f"{exit_id}: missing opt-out exit")
            continue
        inbound = {e.get("source") for e in edges if e.get("target") == exit_id}
        if not inbound:
            problems.append(f"{exit_id}: unreachable; suppression invariant requires an inbound webhook")
        bypass = sorted(inbound - suppressor_ids)
        if bypass:
            problems.append(
                f"{exit_id}: direct inbound source(s) {bypass}; both opt-out exits must be "
                "reachable only through their suppression webhook"
            )
        if inbound & suppressor_ids and inbound & suppressor_ids != {required_webhook}:
            problems.append(
                f"{exit_id}: suppression inbound {sorted(inbound & suppressor_ids)}; its correct "
                f"webhook is {required_webhook}"
            )

    for nid, node in suppressors.items():
        data = node.get("data", {})
        url = str(data.get("url") or "")
        if not re.fullmatch(r"https://[^/]+/sms-suppression", url):
            problems.append(
                f"{nid}: endpoint {url!r}; suppression invariant requires exact path /sms-suppression"
            )
        try:
            body = json.loads(str(data.get("body") or ""))
        except json.JSONDecodeError as exc:
            problems.append(f"{nid}: suppression body is not JSON: {exc}")
            continue
        if set(body) != {"phone_e164", "reason", "source"}:
            problems.append(
                f"{nid}: body fields {sorted(body)}; exact contract is phone_e164, reason, source"
            )
        if body.get("reason") not in VALID_REASONS:
            problems.append(f"{nid}: invalid reason {body.get('reason')!r}")
        if body.get("source") not in VALID_SOURCES:
            problems.append(f"{nid}: invalid source {body.get('source')!r}")
        if not re.fullmatch(r"\{\{\s*[a-z0-9_]+\s*\}\}", str(body.get("phone_e164", ""))):
            problems.append(
                f"{nid}: phone_e164 {body.get('phone_e164')!r}; must be one interpolated variable"
            )
        retry = data.get("modelOptions", {}).get("retryAttempts")
        if retry != 0:
            problems.append(f"{nid}: retryAttempts is {retry!r}; exact invariant requires 0")

    persisted_claim = re.compile(
        r"you (?:have been|are|'ve been) (?:removed|taken off|unsubscribed|opted out)"
        r"|we(?:'ve| have) (?:removed|taken you off|unsubscribed)"
        r"|you (?:will|won't|will not) (?:no longer )?(?:receive|get)",
        re.I,
    )
    for nid, node in nodes.items():
        blob = " ".join(str(node.get("data", {}).get(k) or "") for k in ("prompt", "text"))
        if persisted_claim.search(blob):
            problems.append(
                f"{nid}: patient-facing text claims opt-out persistence; endpoint success is not "
                "proven to the conversation"
            )

    all_ids = set(nodes) | set(base_nodes)
    actual_changed = {
        nid for nid in all_ids
        if nodes.get(nid) != base_nodes.get(nid)
    }
    undeclared = sorted(actual_changed - expected_changed)
    if undeclared:
        problems.append(
            f"declared delta: node(s) {undeclared} differ outside --expect-changed; invariant 7 "
            "requires every undeclared node to be structurally identical to baseline"
        )
    unknown = sorted(expected_changed - all_ids)
    if unknown:
        problems.append(
            f"declared delta: --expect-changed names absent node(s) {unknown}; declarations must "
            "refer to graph or baseline"
        )

    # Node pathways are the executable edge manifest. Also compare standalone edges whose
    # endpoints are both outside the declared delta, catching bypasses not reflected in pathways.
    def edge_shape(g: dict[str, Any]) -> set[str]:
        shaped = set()
        for edge in g.get("edges", []):
            if edge.get("source") in expected_changed or edge.get("target") in expected_changed:
                continue
            shaped.add(json.dumps(edge, sort_keys=True, separators=(",", ":")))
        return shaped

    if edge_shape(graph) != edge_shape(baseline):
        problems.append(
            "declared delta: edge structure changed wholly outside --expect-changed nodes; "
            "invariant 7 requires structural identity"
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=HEADER)
    parser.add_argument("--graph", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--expect-changed", nargs="+", required=True, metavar="NODE_ID")
    args = parser.parse_args(argv)
    print(HEADER)
    try:
        graph, baseline = load_json(args.graph), load_json(args.baseline)
        problems = check_suppression(graph, baseline, set(args.expect_changed))
    except (OSError, json.JSONDecodeError) as exc:
        problems = [f"cannot load graph or baseline JSON: {exc}"]
    if problems:
        print("CHECK FAILED")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(
        f"CHECK PASSED: suppression subgraph valid; all nodes outside the "
        f"{len(set(args.expect_changed))}-node declared delta are structurally identical"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
