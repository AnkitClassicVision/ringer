#!/usr/bin/env python3
"""Deterministically derive the goal-loop graph from the production graph."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = Path("/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workV93/build-v93/pathway-v93-draft.json")
OUTPUT = HERE / "pathway-goalloop-draft.json"

COLLAPSED = {
    "n_ask": "n_goal_update", "n_miss_empty": "n_goal_response",
    "n_miss_unread": "n_goal_response", "n_miss_thin": "n_goal_response",
    "n_miss_unbookable": "n_goal_response", "n_clarify": "n_goal_response",
    "n_miss_time": "n_goal_response", "n_offer": "n_goal_response",
    "n_offer_2": "n_goal_response", "n_offer_3": "n_goal_response",
    "n_offer_near": "n_goal_response", "n_negotiate": "n_goal_update",
    "n_recheck": "n_goal_update", "n_which_intent": "n_goal_update",
    "n_search": "n_goal_search", "n_page_2": "n_goal_search",
    "n_page_3": "n_goal_search", "n_page_near": "n_goal_search",
}

KEEP = {
    "n_identity", "n_appt_check", "e_defer", "n_help", "n_office", "n_faq",
    "n_gate_1", "n_gate_2", "n_confirm", "n_verify_1", "n_verify_2",
    "n_book_1", "n_book_2", "n_reconcile_1", "n_reconcile_2",
    "e_booked", "e_booking_failed", "e_book_unknown", "e_booked_recovered",
    "e_declined", "e_timeout", "e_stop", "e_not_me", "n_suppress_stop",
    "n_suppress_not_me", "n_date_conflict", "n_date_conflict_retry",
    "e_safe_identity", "e_safe_failure", "e_office", "e_existing",
}

EXTRA_FIELDS = [
    ("goal_anchor", "string", "Extract the requested anchor exactly as defined by SPEC v94 DRAFT 4: day-open, day-close, noon, an explicit 12-hour time with AM/PM, clear, or retain."),
    ("goal_relation", "string", "Extract the requested relation exactly as defined by SPEC v94 DRAFT 4: nearest, before, after, clear, or retain."),
    ("time_from", "string", "Extract the lower time bound exactly as defined by SPEC v94 DRAFT 4: a 12-hour time with AM/PM, none, clear, or retain."),
    ("time_to", "string", "Extract the upper time bound exactly as defined by SPEC v94 DRAFT 4: a 12-hour time with AM/PM, none, clear, or retain."),
]


def edge(source: str, target: str, label: str, ordinal: int) -> dict:
    """Copy the production custom-edge encoding and change only route fields."""
    return {
        "animated": True,
        "data": {"description": f"Route from {source} to {target} when: {label}.", "isHighlighted": False, "label": label},
        "id": f"edge-{source}-{target}-derived-{ordinal}",
        "source": source, "sourceHandle": None, "target": target,
        "targetHandle": None, "type": "custom",
    }


def build() -> dict:
    src = json.loads(SOURCE.read_text(encoding="utf-8"))
    source_by = {n["id"]: n for n in src["nodes"]}
    nodes = [copy.deepcopy(n) for n in src["nodes"] if n["id"] in KEEP]

    update = copy.deepcopy(source_by["n_appt_check"])
    update["id"] = "n_goal_update"
    update["data"]["name"] = "Goal update (silent)"
    update["data"].pop("url", None)
    update["data"].pop("body", None)
    update["data"].pop("headers", None)
    update["data"].pop("method", None)
    update["data"].pop("responseData", None)
    update["type"] = "Default"
    update["data"]["prompt"] = "SILENT PROCESSOR."
    update["data"]["text"] = ""
    update["data"]["userWait"] = False
    update["data"]["modelOptions"] = copy.deepcopy(source_by["n_appt_check"]["data"]["modelOptions"])
    update["data"]["extractVars"] = copy.deepcopy(source_by["n_ask"]["data"]["extractVars"])
    for name, typ, prompt in EXTRA_FIELDS:
        update["data"]["extractVars"].append([name, typ, prompt, False, False, True])
    update["data"]["responsePathways"] = [["user_verbatim", "!=", "", {"id": "n_goal_search", "name": "Goal extracted"}]]
    nodes.append(update)

    search = copy.deepcopy(source_by["n_search"])
    search["id"] = "n_goal_search"
    search["data"]["name"] = "Goal search (silent)"
    body = json.loads(search["data"]["body"])
    body["time_pref"] = "{{goal_relation}}"
    body["anchor"] = "{{goal_anchor}}"
    body["time_from"] = "{{time_from}}"
    body["time_to"] = "{{time_to}}"
    search["data"]["body"] = json.dumps(body, separators=(",", ":"))
    search["data"]["responsePathways"] = [
        ["ok", "!=", "true", {"id": "n_goal_response", "name": "Search unavailable"}],
        ["date_conflict_detected", "==", "conflict", {"id": "n_date_conflict", "name": "Two dates disagree"}],
        ["slot_count", "==", "0", {"id": "n_goal_response", "name": "No openings"}],
        ["slot_count", "==", "1", {"id": "n_goal_response", "name": "One opening"}],
        ["slot_count", ">=", "2", {"id": "n_goal_response", "name": "Two openings"}],
    ]
    nodes.append(search)

    response = copy.deepcopy(source_by["n_offer"])
    response["id"] = "n_goal_response"
    response["data"]["name"] = "Goal response and offer"
    # Production prompt is retained; only references to retired paging/negotiation
    # nodes are removed. The production opening is embedded verbatim for entry.
    ask_prompt = source_by["n_ask"]["data"]["prompt"]
    opening = ask_prompt.split('TASK. Send this message with the patient\'s first name filled in: "', 1)[1].split('" If the patient writes in Chinese', 1)[0]
    offer_prompt = source_by["n_offer"]["data"]["prompt"]
    offer_prompt = offer_prompt.replace("; say 'One moment while I check the schedule for you.' and run the schedule search", "")
    response["data"]["prompt"] = offer_prompt + "\n\nFIRST RESPONSE ONLY:\n" + opening
    nodes.append(response)

    node_ids = {n["id"] for n in nodes}
    edges = []
    # Preserve every edge whose endpoints survive and whose route remains valid.
    for e in src["edges"]:
        if e["source"] in node_ids and e["target"] in node_ids:
            edges.append(copy.deepcopy(e))

    def add(s, t, label):
        edges.append(edge(s, t, label, len(edges)))

    # Entry and loop. Webhook labels are executable Bland conditions.
    add("n_appt_check", "n_goal_response", "appt_count == 0")
    add("n_goal_update", "n_goal_search", "user_verbatim != ")
    add("n_goal_search", "n_goal_response", "ok != true")
    add("n_goal_search", "n_date_conflict", "date_conflict_detected == conflict")
    add("n_goal_search", "n_goal_response", "slot_count == 0")
    add("n_goal_search", "n_goal_response", "slot_count == 1")
    add("n_goal_search", "n_goal_response", "slot_count >= 2")
    # Patient response routing is copied in meaning from n_offer and collapsed to UPDATE.
    add("n_goal_response", "n_gate_1", "takes only the first opening offered")
    add("n_goal_response", "n_gate_2", "takes only the second opening offered")
    add("n_goal_response", "n_goal_update", "wants a different day or time")
    add("n_goal_response", "e_declined", "declines this offer")
    add("n_goal_response", "e_timeout", "72-hour timeout")
    # Kept D6 nodes now return to the one search call through UPDATE.
    add("n_date_conflict", "n_goal_update", "patient provides any usable day, weekday, or date, including either conflicting option or a new replacement date")
    add("n_date_conflict_retry", "n_goal_update", "after the one allowed re-ask, always continue to search using the best extracted date; never remain on this node")
    # Existing consent and lost-slot routes that formerly entered retired nodes.
    add("n_gate_1", "n_goal_update", "says no or wants other times")
    add("n_gate_2", "n_goal_update", "says no or wants other times")
    add("n_verify_1", "n_goal_response", "slot_conflict == true")
    add("n_verify_1", "n_goal_response", "conflict_reason != ")
    add("n_verify_2", "n_goal_response", "slot_conflict == true")
    add("n_verify_2", "n_goal_response", "conflict_reason != ")
    add("n_book_1", "n_goal_update", "book_error == slot_conflict")
    add("n_book_2", "n_goal_update", "book_error == slot_conflict")

    graph = {k: copy.deepcopy(v) for k, v in src.items() if k not in ("nodes", "edges")}
    graph["nodes"] = nodes
    graph["edges"] = edges
    graph["derivation"] = {"source": str(SOURCE), "kept_verbatim": sorted(KEEP), "collapsed": COLLAPSED}
    return graph


def assert_kept_verbatim(graph: dict) -> int:
    src = json.loads(SOURCE.read_text(encoding="utf-8"))
    old = {n["id"]: n for n in src["nodes"]}
    new = {n["id"]: n for n in graph["nodes"]}
    for node_id in KEEP:
        assert new[node_id] == old[node_id], f"kept node changed: {node_id}"
    return len(KEEP)


def write_fixtures(graph: dict) -> None:
    fixtures = {"conformant": copy.deepcopy(graph)}
    x = copy.deepcopy(graph)
    x["edges"].append(edge("n_goal_response", "n_goal_response", "tamper wait self-loop", 999))
    fixtures["A-wait-self-loop"] = x
    x = copy.deepcopy(graph)
    x["edges"].append(edge("n_goal_update", "e_declined", "tamper negotiation terminal", 999))
    fixtures["B-negotiation-terminal"] = x
    x = copy.deepcopy(graph)
    next(n for n in x["nodes"] if n["id"] == "n_goal_update")["data"]["prompt"] = "Checking availability for you"
    fixtures["C-banned-promise"] = x
    x = copy.deepcopy(graph)
    next(n for n in x["nodes"] if n["id"] == "n_goal_update")["data"]["prompt"] = "Come at 3:15 pm"
    fixtures["D-clock-containment"] = x
    x = copy.deepcopy(graph)
    next(n for n in x["nodes"] if n["id"] == "n_gate_1")["data"]["extractVars"] = [["duplicate_goal", "string", "duplicate"]]
    fixtures["E-duplicate-extraction"] = x
    for name, value in fixtures.items():
        (HERE / f"fixture-{name}.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    graph = build()
    kept = assert_kept_verbatim(graph)
    OUTPUT.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if "--fixtures" in sys.argv:
        write_fixtures(graph)
    print(f"WROTE={OUTPUT.name}")
    print(f"KEPT_VERBATIM={kept} nodes")
