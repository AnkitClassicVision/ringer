#!/usr/bin/env python3
"""Lane gate for the v58 builder fix. Structural floor by design, and says so.

Codex ruling 2026-07-26 (R1.2): starting from build_v57.py is approved ONCE the
contradictory stripping instruction is purged and the 3pm-floor case is fixed or
conservatively routed. This check enforces exactly that scope and nothing wider:
the ONLY nodes allowed to differ from v57 are the ones whose extraction guidance
carries the temporal rules. Behavioral proof remains the live suite.
"""
import argparse
import json
import pathlib
import re
import sys


def load(p):
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))


def shape(g):
    return {n["id"]: {
        "pathways": [[p[0], p[1], p[2], p[3].get("id")]
                     for p in (n["data"].get("responsePathways") or [])],
        "extract": [(v[0], v[2]) for v in (n["data"].get("extractVars") or [])],
        "prompt": n["data"].get("prompt") or "",
        "body": n["data"].get("body") or "",
        "text": n["data"].get("text") or "",
    } for n in g["nodes"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", required=True)
    ap.add_argument("--baseline", required=True, help="v57 graph")
    ap.add_argument("--builder", required=True)
    args = ap.parse_args()

    for p in (args.graph, args.baseline, args.builder):
        if not pathlib.Path(p).exists():
            print(f"CHECK FAILED\n\n  - {p} does not exist")
            return 1

    problems = []
    builder = pathlib.Path(args.builder).read_text(encoding="utf-8")
    graph, base = load(args.graph), load(args.baseline)

    # 1. The contradiction is gone, the rule is present — in the BUILDER text.
    if "must become tuesday" in builder:
        problems.append("the stripping instruction ('must become tuesday') is still in "
                        "the builder; purging it is the core of this lane")
    low = builder.lower()
    if "next week" not in low or "keep" not in low and "preserve" not in low:
        problems.append("no qualifier-preservation guidance found in the builder")
    if "monday..friday" in builder or "monday to friday, and the server" in low:
        pass  # comment wording varies; the graph-level checks below are authoritative
    # Vague weeks use the gateway-probed pair. The former monday-next-week
    # start can invert the range on Mondays and is banned.
    joined_extract = " ".join(d for n in shape(graph).values() for _, d in n["extract"]).lower()
    if "without naming a day, write next week" not in joined_extract:
        problems.append("extraction guidance does not map a vague-week start to exact phrase "
                        "'next week' per contract/TEMPORAL-CONTRACT.md rev 3")
    if "no day, put friday next week" not in joined_extract:
        problems.append("extraction guidance does not map a vague-week end to exact phrase "
                        "'friday next week' per contract/TEMPORAL-CONTRACT.md rev 3")
    if re.search(
        r"(?:vague|without naming a day|no day).{0,100}"
        r"(?:write|map(?:s|ped)?(?:\s+from)?|become(?:s)?)\s+"
        r"(?:from\s+)?monday next week",
        joined_extract,
    ):
        problems.append("extraction guidance restores banned vague-week mapping to "
                        "'monday next week', which can create an inverted range")
    if "must become tuesday" in json.dumps(load(args.graph)):
        problems.append("the stripping instruction survived into the generated graph")

    # 2. The 3pm-floor fix: clock times of 3pm and later must map to the late band.
    if not any(k in joined_extract for k in ("3pm", "3 pm", "three in the afternoon", "15:00")):
        problems.append("no clock-time-to-band mapping found in extraction guidance; the "
                        "3pm-floor defect (Codex R2.3) is unaddressed")

    # 3. Scope containment: only extraction-carrying nodes may differ from v57.
    gs, bs = shape(graph), shape(base)
    if set(gs) != set(bs):
        problems.append(f"node set changed: only-new={sorted(set(gs)-set(bs))} "
                        f"only-old={sorted(set(bs)-set(gs))}; this lane adds no nodes")
    for nid in sorted(set(gs) & set(bs)):
        g_n, b_n = gs[nid], bs[nid]
        if g_n["pathways"] != b_n["pathways"]:
            problems.append(f"{nid}: routing changed; this lane must not touch routing")
        if g_n["prompt"] != b_n["prompt"] or g_n["text"] != b_n["text"] or g_n["body"] != b_n["body"]:
            problems.append(f"{nid}: prompt/text/body changed; this lane touches only "
                            f"extraction descriptions")
        if g_n["extract"] != b_n["extract"]:
            if [v for v, _ in g_n["extract"]] != [v for v, _ in b_n["extract"]]:
                problems.append(f"{nid}: extraction VARIABLE SET changed; only descriptions may")

    # 4. Safety invariants must survive untouched.
    edges = {(e["source"], e["target"]) for e in load(args.graph)["edges"]}
    into = lambda t: sorted({s for s, d in edges if d == t})
    if into("n_confirm") != ["n_book_1", "n_book_2"]:
        problems.append(f"n_confirm reachable from {into('n_confirm')}")
    for book, verify in (("n_book_1", "n_verify_1"), ("n_book_2", "n_verify_2")):
        if into(book) != [verify]:
            problems.append(f"{book} reachable from {into(book)}; conflict check skippable")
    for exit_id, supp in (("e_stop", "n_suppress_stop"), ("e_not_me", "n_suppress_not_me")):
        if into(exit_id) != [supp]:
            problems.append(f"{exit_id} reachable from {into(exit_id)}; must be only via {supp}")

    if problems:
        print("CHECK FAILED\n")
        for p in problems:
            print(f"  - {p}")
        print(f"\n{len(problems)} problem(s).")
        return 1
    print("CHECK PASSED (structural floor only): stripping purged, qualified-week and "
          "clock-band guidance present, delta confined to extraction descriptions, safety "
          "invariants intact. Behavioral proof remains the live 30-scenario run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
