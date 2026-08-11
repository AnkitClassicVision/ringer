#!/usr/bin/env python3
"""Verify a graph actually persists opt-outs, and did not break anything doing it.

Two failure modes this guards against. First, a node that claims an opt-out was saved
when nothing was written, which is worse than the current honest silence. Second, a
"wire suppression" change that quietly reshapes the rest of the booking graph.

So this checks the new nodes against the real gateway contract, AND diffs every other
node against the baseline to prove the change was additive.
"""
import argparse
import json
import pathlib
import re
import sys

VALID_REASONS = {"stop", "unsubscribe", "complaint", "manual", "wrong_number"}
VALID_SOURCES = {"sms_reply", "voice", "manual", "import"}
OPT_OUT_EXITS = ("e_stop", "e_not_me")


def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def structural(graph):
    return {
        n["id"]: {
            "type": n.get("type"),
            "pathways": [[p[0], p[1], p[2], p[3].get("id")]
                         for p in (n.get("data", {}).get("responsePathways") or [])],
            "extract": [v[0] for v in (n.get("data", {}).get("extractVars") or [])],
            "url": n.get("data", {}).get("url"),
            "body": n.get("data", {}).get("body"),
            "text": n.get("data", {}).get("text"),
            "prompt": n.get("data", {}).get("prompt"),
        }
        for n in graph["nodes"]
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", required=True)
    ap.add_argument("--baseline", required=True)
    args = ap.parse_args()

    for p in (args.graph, args.baseline):
        if not pathlib.Path(p).exists():
            print(f"CHECK FAILED\n\n  - {p} does not exist")
            return 1

    graph, baseline = load(args.graph), load(args.baseline)
    nodes = {n["id"]: n for n in graph["nodes"]}
    edges = graph["edges"]
    problems = []

    suppressors = [n for n in graph["nodes"]
                   if n.get("type") == "Webhook"
                   and "/sms-suppression" in str(n.get("data", {}).get("url", ""))]
    if not suppressors:
        print("CHECK FAILED\n\n  - no webhook node posts to /sms-suppression; "
              "the opt-out is still not persisted anywhere")
        return 1

    # Every opt-out exit must be reached THROUGH a suppression call, never directly
    # from a conversational node, or a STOP can still slip out unrecorded.
    supp_ids = {n["id"] for n in suppressors}
    for exit_id in OPT_OUT_EXITS:
        if exit_id not in nodes:
            problems.append(f"{exit_id} is missing from the graph entirely")
            continue
        inbound = {e["source"] for e in edges if e["target"] == exit_id}
        if not inbound:
            problems.append(f"{exit_id} is unreachable")
            continue
        unguarded = inbound - supp_ids
        if unguarded:
            problems.append(
                f"{exit_id} is reachable directly from {sorted(unguarded)} without passing "
                f"through a suppression call, so a STOP on that path is never recorded")

    for node in suppressors:
        nid = node["id"]
        body = str(node["data"].get("body") or "")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            problems.append(f"{nid}: body is not valid JSON: {body[:120]}")
            continue
        if set(parsed) != {"phone_e164", "reason", "source"}:
            problems.append(f"{nid}: body keys {sorted(parsed)}; the contract is exactly "
                            f"phone_e164, reason, source")
        reason, source = str(parsed.get("reason")), str(parsed.get("source"))
        if reason not in VALID_REASONS:
            problems.append(f"{nid}: reason {reason!r} is not one of {sorted(VALID_REASONS)}; "
                            f"the gateway returns 400")
        if source not in VALID_SOURCES:
            problems.append(f"{nid}: source {source!r} is not one of {sorted(VALID_SOURCES)}; "
                            f"the gateway returns 400")
        phone = str(parsed.get("phone_e164", ""))
        if not re.fullmatch(r"\{\{\s*[a-z0-9_]+\s*\}\}", phone):
            problems.append(f"{nid}: phone_e164 is {phone!r}; it must interpolate a variable, "
                            f"never a literal or a composed value")
        if node["data"].get("modelOptions", {}).get("retryAttempts") not in (0, None):
            problems.append(f"{nid}: retryAttempts must be 0")

    # Nothing may claim the opt-out stuck. The endpoint can return 503, and only an
    # ok=true response means the record landed.
    claim = re.compile(r"you (?:have been|are|'ve been) (?:removed|taken off|unsubscribed|opted out)"
                       r"|we(?:'ve| have) (?:removed|taken you off|unsubscribed)"
                       r"|(?:you (?:will|won't|will not) (?:no longer )?(?:receive|get))", re.I)
    for nid, node in nodes.items():
        blob = " ".join(str(node["data"].get(k) or "") for k in ("text", "prompt"))
        if claim.search(blob):
            problems.append(f"{nid}: claims the opt-out was applied. Only a response with "
                            f"ok true proves that, and the endpoint can answer 503")

    base_s, new_s = structural(baseline), structural(graph)
    changed = [nid for nid in set(base_s) & set(new_s) if base_s[nid] != new_s[nid]]
    removed = sorted(set(base_s) - set(new_s))
    allowed_change = set(OPT_OUT_EXITS)
    unexpected = sorted(set(changed) - allowed_change)
    if removed:
        problems.append(f"nodes removed from the baseline: {removed}; this change must be additive")
    if unexpected:
        problems.append(f"nodes changed that are not opt-out exits: {unexpected}; "
                        f"wiring suppression must not reshape the booking graph")

    if problems:
        print("CHECK FAILED\n")
        for p in problems:
            print(f"  - {p}")
        print(f"\n{len(problems)} problem(s).")
        return 1

    print(f"CHECK PASSED: {len(suppressors)} suppression call(s), both opt-out exits reachable "
          f"only through one, contract fields valid, no false opt-out claim, "
          f"{len(set(new_s) - set(base_s))} node(s) added and nothing else changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
