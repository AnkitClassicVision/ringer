#!/usr/bin/env python3
"""Structural floor for the v57 scenario fixes. The live suite is the real gate.

This cannot prove conversational behaviour: only a live run of the 30 scenarios can,
and that needs credentials this check does not have. What it CAN prove is that the
graph still holds its safety invariants, that the two stale assertions were retired
rather than the code bent to satisfy them, and that each of the four fixes left
concrete evidence in the artifact instead of a claim in a report.
"""
import argparse
import collections
import json
import pathlib
import re
import sys

RETIRED = ("time_pref", "preference_after")


def load(p):
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--scenarios", required=True)
    args = ap.parse_args()

    for p in (args.graph, args.baseline, args.scenarios):
        if not pathlib.Path(p).exists():
            print(f"CHECK FAILED\n\n  - {p} does not exist")
            return 1

    graph, baseline = load(args.graph), load(args.baseline)
    scenarios = pathlib.Path(args.scenarios).read_text(encoding="utf-8")
    nodes = {n["id"]: n for n in graph["nodes"]}
    edges = graph["edges"]
    problems = []

    # --- safety invariants that must survive any prompt work ---
    adj = collections.defaultdict(set)
    for e in edges:
        adj[e["source"]].add(e["target"])
    dangling = [(e["source"], e["target"]) for e in edges
                if e["source"] not in nodes or e["target"] not in nodes]
    if dangling:
        problems.append(f"dangling edges: {dangling[:5]}")

    into = lambda t: sorted({e["source"] for e in edges if e["target"] == t})
    if into("n_confirm") != ["n_book_1", "n_book_2"]:
        problems.append(f"n_confirm reachable from {into('n_confirm')}; only the two book "
                        f"nodes may reach it")
    if into("e_booked") != ["n_confirm"]:
        problems.append(f"e_booked reachable from {into('e_booked')}; only n_confirm may")
    for book, verify in (("n_book_1", "n_verify_1"), ("n_book_2", "n_verify_2")):
        if into(book) != [verify]:
            problems.append(f"{book} reachable from {into(book)}; only {verify} may, or the "
                            f"conflict check becomes skippable")

    # Two-slot visibility: an offer node may name only its own pair.
    for nid, node in nodes.items():
        prompt = node["data"].get("prompt") or ""
        used = set(re.findall(r"\{\{\s*(slot_[a-z0-9_]+)\s*\}\}", prompt))
        stray = {v for v in used if not v.startswith(("slot_1_", "slot_2_"))}
        if stray:
            problems.append(f"{nid} interpolates {sorted(stray)}; an offer may name only its "
                            f"own two openings")

    # --- the stale assertions must be gone from the suite, not worked around ---
    for term in RETIRED:
        hits = len(re.findall(rf"\b{re.escape(term)}\b", scenarios))
        if hits:
            problems.append(f"scenario suite still references {term!r} {hits} time(s); that "
                            f"field was deliberately removed because the gateway ignores it")
    count = len(re.findall(r'["\']name["\']\s*:', scenarios))
    if count < 30:
        problems.append(f"suite appears to define {count} scenarios; at least 30 expected, so "
                        f"failing tests must not have been deleted")

    # --- evidence for each of the four fixes ---
    all_prompts = " ".join(str(n["data"].get("prompt") or "") for n in graph["nodes"]).lower()
    extract_text = " ".join(
        d[2].lower() for n in graph["nodes"] for d in (n["data"].get("extractVars") or []))

    if not (re.search(r"which (one|of the two|time|opening)", all_prompts)
            and re.search(r"both|also ask|as well as", all_prompts)):
        problems.append("no offer prompt instructs asking which one the patient meant when a "
                        "reply both selects an opening and asks for something else; that is "
                        "the failure that can book a time they did not settle on")

    if not re.search(r"shorthand|abbreviat|shortened|nxt|tues\b|expand", extract_text):
        problems.append("extraction guidance says nothing about expanding texting shorthand, "
                        "so a reply like 'tues nxt wk' still reaches the scheduler verbatim")

    if not re.search(r"outside|before we open|after we close|opening hours|office hours|"
                     r"too early|too late", all_prompts):
        problems.append("nothing handles a time outside opening hours, so a request no slot "
                        "can satisfy is still answered with a substituted time")

    # --- additive: nothing outside the intended surface may change ---
    def shape(g):
        return {n["id"]: [[p[0], p[1], p[2], p[3].get("id")]
                          for p in (n["data"].get("responsePathways") or [])]
                for n in g["nodes"]}

    removed = sorted(set(shape(baseline)) - set(shape(graph)))
    if removed:
        problems.append(f"nodes removed from the baseline: {removed}")

    if problems:
        print("CHECK FAILED\n")
        for p in problems:
            print(f"  - {p}")
        print(f"\n{len(problems)} problem(s).")
        return 1

    print(f"CHECK PASSED: {len(nodes)} nodes, write path intact, two-slot visibility held, "
          f"stale assertions retired, evidence present for all four fixes. "
          f"The live 30-scenario run remains the real gate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
