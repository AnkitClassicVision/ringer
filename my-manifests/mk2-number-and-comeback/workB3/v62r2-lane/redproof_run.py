#!/usr/bin/env python3
"""In-memory mutation proof for the v62 structural candidate gate."""

from __future__ import annotations

import copy
import json
import pathlib
import sys

import check_candidate_gate

ROOT = pathlib.Path(__file__).resolve().parent


def node(graph, nid):
    return next(item for item in graph["nodes"] if item["id"] == nid)


def remove_offer_edge(graph):
    graph["edges"] = [e for e in graph["edges"]
                      if not (e["source"] == "n_offer" and e["target"] == "n_which_intent")]


def direct_clarification_to_book(graph):
    next(e for e in graph["edges"] if e["source"] == "n_which_intent")["target"] = "n_book_1"


def delete_outside_route(graph):
    search = node(graph, "n_search")
    search["data"]["responsePathways"] = [p for p in search["data"]["responsePathways"]
                                                   if not (p[0] == "day_part" and p[2] == "outside")]
    graph["edges"] = [e for e in graph["edges"]
                      if not (e["source"] == "n_search" and e["target"] == "n_miss_time")]


def reorder_outside_route(graph):
    paths = node(graph, "n_search")["data"]["responsePathways"]
    outside = next(p for p in paths if p[0] == "day_part" and p[2] == "outside")
    paths.remove(outside)
    paths.append(outside)


def delete_outside_day_part_token(graph):
    target = next(v for v in node(graph, "n_ask")["data"]["extractVars"] if v[0] == "day_part")
    target[2] = target[2].replace("outside", "removed")


def reinsert_stripping_instruction(graph):
    node(graph, "n_ask")["data"]["extractVars"][0][2] += " The phrase tues nxt wk must become tuesday."


def restore_monday_next_week_inverted_range(graph):
    target = node(graph, "n_ask")["data"]["extractVars"][0]
    target[2] = target[2].replace("without naming a day, write next week",
                                  "without naming a day, write monday next week")


def delete_preference_to_week_end_field_rule(graph):
    target = next(v for v in node(graph, "n_ask")["data"]["extractVars"] if v[0] == "preference_to")
    target[2] = target[2].replace(
        "preference_to is friday followed by that same full week qualifier",
        "preference_to end-field rule removed",
    )


def second_booking_claim(graph):
    node(graph, "e_booked")["data"]["text"] += " Your appointment is booked."


def third_slot(graph):
    node(graph, "n_offer")["data"]["prompt"] += " Or choose {{slot_3_start}}."


def bypass_suppression(graph):
    graph["edges"].append({"id": "redproof-direct-stop", "source": "n_offer",
                           "target": "e_stop", "type": "custom", "data": {"label": "bypass"}})


# v62 M1-M7.
def restore_855(graph):
    node(graph, "e_office")["data"]["text"] = node(graph, "e_office")["data"]["text"].replace(
        "(212) 219-2219", "(855) 750-6688")


def delete_close(graph):
    prompt = node(graph, "n_confirm")["data"]["prompt"]
    node(graph, "n_confirm")["data"]["prompt"] = prompt.replace(check_candidate_gate.CLOSE, "close removed")


def move_close_to_booked(graph):
    delete_close(graph)
    node(graph, "e_booked")["data"]["text"] += " " + check_candidate_gate.CLOSE


def paraphrase_defer(graph):
    node(graph, "e_defer")["data"]["text"] = "Please contact the office."


def readd_confirm_office(graph):
    graph["edges"].append({"id": "redproof-confirm-office", "source": "n_confirm",
                           "target": "n_office", "type": "custom", "data": {"label": "change"}})


def delete_appt_check(graph):
    graph["nodes"] = [n for n in graph["nodes"] if n["id"] != "n_appt_check"]


def reorder_appt_defer_route(graph):
    paths = node(graph, "n_appt_check")["data"]["responsePathways"]
    defer = next(p for p in paths if p[0] == "appt_count" and p[1] == ">=")
    paths.remove(defer)
    paths.append(defer)


def bypass_appt_check(graph):
    paths = node(graph, "n_identity")["data"]["responsePathways"]
    route = next(p for p in paths if p[:3] == ["count", "==", "1"])
    route[3] = {"id": "n_ask", "name": "Identity confirmed"}


def remove_appt_count_mapping(graph):
    data = node(graph, "n_appt_check")["data"]
    data["responseData"] = [x for x in data["responseData"] if x["name"] != "appt_count"]


def strip_label_exclusion(graph):
    label = node(graph, "n_office")["data"]["globalLabel"]
    node(graph, "n_office")["data"]["globalLabel"] = label.replace(
        " This does not apply once a booking is confirmed.", "")


def main() -> int:
    graph_path = ROOT / "v62_graph.json"
    clean = json.loads(graph_path.read_text(encoding="utf-8"))
    clean_problems = check_candidate_gate.check_graph(clean, ROOT / "scenarios.py")
    if clean_problems:
        print("REDPROOF FAILED: clean candidate did not pass", file=sys.stderr)
        for problem in clean_problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    mutations = [
        ("remove offer-to-clarification edge", remove_offer_edge),
        ("rewire clarification directly to book", direct_clarification_to_book),
        ("delete outside-hours route", delete_outside_route),
        ("order outside-hours route after offers", reorder_outside_route),
        ("delete outside token", delete_outside_day_part_token),
        ("reinsert qualifier stripping", reinsert_stripping_instruction),
        ("restore inverted vague-week range", restore_monday_next_week_inverted_range),
        ("delete preference_to week-end rule", delete_preference_to_week_end_field_rule),
        ("add second booking claim", second_booking_claim),
        ("expose third slot", third_slot),
        ("bypass suppression recorder", bypass_suppression),
        ("M1 restore 855", restore_855),
        ("M2 delete close", delete_close),
        ("M3 move close to e_booked", move_close_to_booked),
        ("M4 paraphrase e_defer", paraphrase_defer),
        ("M5 re-add n_confirm to n_office", readd_confirm_office),
        ("M6 delete n_appt_check", delete_appt_check),
        ("M6 reorder defer after n_ask", reorder_appt_defer_route),
        ("M6 retarget count==1 to n_ask", bypass_appt_check),
        ("M6 remove appt_count mapping", remove_appt_count_mapping),
        ("M7 strip label exclusion", strip_label_exclusion),
    ]
    caught = 0
    for name, mutate in mutations:
        candidate = copy.deepcopy(clean)
        mutate(candidate)
        if not check_candidate_gate.check_graph(candidate):
            print(f"REDPROOF FAILED: gate passed mutation: {name}", file=sys.stderr)
            return 1
        caught += 1
    print(f"mutations_caught={caught}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
