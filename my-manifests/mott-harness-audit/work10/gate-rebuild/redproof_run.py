#!/usr/bin/env python3
"""In-memory red proof for both structural gates. Performs no network or filesystem writes."""

from __future__ import annotations

import copy
import json
import pathlib
import sys

import check_candidate_gate
import check_suppression_delta

ROOT = pathlib.Path(__file__).resolve().parent
EXPECTED_CHANGED = {
    "e_booked", "n_ask", "n_clarify", "n_miss_empty", "n_miss_thin",
    "n_miss_time", "n_miss_unbookable", "n_miss_unread", "n_negotiate",
    "n_offer", "n_offer_2", "n_offer_3", "n_offer_near", "n_search",
    "n_which_intent",
}


def node(graph, nid):
    return next(item for item in graph["nodes"] if item["id"] == nid)


def clean_candidate(source):
    """Apply the reviewer's temporal correction in memory; source fixture is intentionally stale."""
    graph = copy.deepcopy(source)
    canon = (
        " Normalize `tues nxt wk` as tuesday next week, preserving the qualifier. "
        "A vague request for next week maps from monday next week through friday next week."
    )
    for item in graph["nodes"]:
        for var in item.get("data", {}).get("extractVars") or []:
            if var[0] == "preference_from":
                var[2] = var[2].replace(
                    "`tues nxt wk` must become tuesday, never pass the shorthand through verbatim.",
                    "`tues nxt wk` preserves its week qualifier."
                ) + canon
    graph["edges"] = [
        edge for edge in graph["edges"]
        if not (edge["source"] == "n_miss_time" and edge["target"] == "n_search")
    ]
    return graph


def remove_offer_edge(graph):
    graph["edges"] = [
        e for e in graph["edges"]
        if not (e["source"] == "n_offer" and e["target"] == "n_which_intent")
    ]


def direct_clarification_to_book(graph):
    edge = next(e for e in graph["edges"] if e["source"] == "n_which_intent")
    edge["target"] = "n_book_1"


def delete_outside_route(graph):
    search = node(graph, "n_search")
    search["data"]["responsePathways"] = [
        p for p in search["data"]["responsePathways"]
        if not (p[0] == "day_part" and p[2] == "outside")
    ]
    graph["edges"] = [
        e for e in graph["edges"]
        if not (e["source"] == "n_search" and e["target"] == "n_miss_time")
    ]


def reorder_outside_route(graph):
    paths = node(graph, "n_search")["data"]["responsePathways"]
    outside = next(p for p in paths if p[0] == "day_part" and p[2] == "outside")
    paths.remove(outside)
    paths.append(outside)


def reinsert_stripping_instruction(graph):
    target = node(graph, "n_ask")["data"]["extractVars"][0]
    target[2] += " The phrase tues nxt wk must become tuesday."


def second_booking_claim(graph):
    node(graph, "e_booked")["data"]["text"] += " Your appointment is booked."


def third_slot(graph):
    node(graph, "n_offer")["data"]["prompt"] += " Or choose {{slot_3_start}}."


def bypass_suppression(graph):
    graph["edges"].append({
        "id": "redproof-direct-stop",
        "source": "n_offer",
        "target": "e_stop",
        "type": "custom",
        "data": {"label": "bypass"},
    })


def main() -> int:
    source = json.loads((ROOT / "source/v57_graph.json").read_text(encoding="utf-8"))
    baseline = json.loads((ROOT / "source/v56_graph.json").read_text(encoding="utf-8"))
    clean = clean_candidate(source)

    candidate_problems = check_candidate_gate.check_graph(clean)
    suppression_problems = check_suppression_delta.check_suppression(
        clean, baseline, EXPECTED_CHANGED
    )
    if candidate_problems or suppression_problems:
        print("REDPROOF FAILED: clean candidate did not pass", file=sys.stderr)
        for problem in candidate_problems + suppression_problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    mutations = [
        ("remove offer-to-clarification edge", remove_offer_edge, "candidate"),
        ("rewire clarification directly to book", direct_clarification_to_book, "candidate"),
        ("delete outside-hours route", delete_outside_route, "candidate"),
        ("order outside-hours route after offers", reorder_outside_route, "candidate"),
        ("reinsert qualifier-stripping instruction", reinsert_stripping_instruction, "candidate"),
        ("add second booking claim", second_booking_claim, "candidate"),
        ("expose third slot variable", third_slot, "candidate"),
        ("bypass suppression webhook", bypass_suppression, "suppression"),
    ]
    caught = 0
    for name, mutate, checker in mutations:
        graph = copy.deepcopy(clean)
        mutate(graph)
        if checker == "candidate":
            problems = check_candidate_gate.check_graph(graph)
        else:
            problems = check_suppression_delta.check_suppression(
                graph, baseline, EXPECTED_CHANGED
            )
        if not problems:
            print(f"REDPROOF FAILED: checker passed mutation: {name}", file=sys.stderr)
            return 1
        caught += 1
    print(f"mutations_caught={caught}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
