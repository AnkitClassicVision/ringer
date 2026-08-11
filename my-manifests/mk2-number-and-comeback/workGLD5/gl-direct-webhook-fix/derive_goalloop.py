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
    "n_ask": "n_goal_response", "n_miss_empty": "n_goal_response",
    "n_miss_unread": "n_goal_response", "n_miss_thin": "n_goal_response",
    "n_miss_unbookable": "n_goal_response", "n_clarify": "n_goal_response",
    "n_miss_time": "n_goal_response", "n_offer": "n_goal_response",
    "n_offer_2": "n_goal_response", "n_offer_3": "n_goal_response",
    "n_offer_near": "n_goal_response", "n_negotiate": "n_goal_response",
    "n_recheck": "n_goal_response", "n_which_intent": "n_goal_response",
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
    ("goal_anchor", "string", "Re-extract the persistent requested anchor on every scheduling turn. Use the newest explicit value: day-open, day-close, noon, an explicit 12-hour time with AM/PM, or clear. If this turn does not change it, carry the prior goal_anchor forward by returning retain."),
    ("goal_relation", "string", "Re-extract the persistent requested relation on every scheduling turn. Use the newest explicit value: nearest, before, after, or clear. If this turn does not change it, carry the prior goal_relation forward by returning retain."),
    ("time_from", "string", "Re-extract the persistent lower time bound on every scheduling turn. Use a 12-hour time with AM/PM, none, or clear when explicitly changed. If this turn does not change it, carry the prior time_from forward by returning retain."),
    ("time_to", "string", "Re-extract the persistent upper time bound on every scheduling turn. Use a 12-hour time with AM/PM, none, or clear when explicitly changed. If this turn does not change it, carry the prior time_to forward by returning retain."),
]

DIRECT_SEARCH_SOURCES = {
    "n_goal_response", "n_date_conflict", "n_date_conflict_retry",
    "n_gate_1", "n_gate_2", "n_book_1", "n_book_2",
}
USER_WAIT_SEARCH_SOURCES = DIRECT_SEARCH_SOURCES - {"n_book_1", "n_book_2"}

OFFER_TEMPLATE = ("I have {{slot_1_day_name}} {{slot_1_start}} or "
                  "{{slot_2_day_name}} {{slot_2_start}} at MK2 Optical. "
                  "Reply 1 or 2 to take one, or tell me another day or time.")
D4 = ("These are the latest openings you have been shown for that day, and you have not been shown "
      "everything the day holds. If they ask for something later, do NOT claim this is the latest "
      "the office has and do NOT say the day has nothing later, because you have not been told that. "
      "Do not name any other time. Say you will look at another day for them, ask which day they "
      "would like, and take the path labelled \"wants a different day\".")
PROMISE_SENTENCE = ("If the lookup has not returned in this turn, or the patient is nudging after a silence, "
                    "never state or estimate any date or time from memory or from the patient's words; say "
                    "'One moment while I check the schedule for you.' and run the schedule search. ")
NO_SLOT_SENTENCE = ("If the lookup has not returned in this turn, never state or estimate any date or time "
                    "from memory or from the patient's words. ")


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

    # D7 promise fillers are forbidden graph-wide, including inherited prompts.
    for node in nodes:
        prompt = node.get("data", {}).get("prompt")
        if isinstance(prompt, str):
            node["data"]["prompt"] = prompt.replace(PROMISE_SENTENCE, NO_SLOT_SENTENCE)

    # v92's webhook entry convention is a silent auto-advance whose responsePathway
    # destination and custom-edge destination are the same live node. The collapsed
    # graph retires n_ask, so update both appointment-check routes explicitly.
    appt = next(n for n in nodes if n["id"] == "n_appt_check")
    appt["data"]["responsePathways"] = [
        ["appt_count", ">=", "1", {"id": "e_defer", "name": "Upcoming appointment found"}],
        ["appt_count", "==", "0", {"id": "n_goal_response", "name": "No upcoming appointment"}],
        ["ok", "!=", "true", {"id": "e_defer", "name": "Appointment check unavailable"}],
    ]
    # Port assertion [33]: confirmation copy must carry the date-bearing partner
    # whenever it renders a slot time.
    for index in (1, 2):
        gate = next(n for n in nodes if n["id"] == f"n_gate_{index}")
        gate["data"]["prompt"] = gate["data"]["prompt"].replace(
            f"{{{{slot_{index}_start}}}}", f"{{{{slot_{index}_day_name}}}} {{{{slot_{index}_start}}}}"
        )

    scheduling_extract_vars = copy.deepcopy(source_by["n_ask"]["data"]["extractVars"])
    for name, typ, prompt in EXTRA_FIELDS:
        scheduling_extract_vars.append([name, typ, prompt, False, False, True])

    # Bland CHAT mode extracts on the current user-wait node. Every conversational
    # source that searches must own the complete request input set itself.
    for node in nodes:
        if node["id"] in USER_WAIT_SEARCH_SOURCES:
            node["data"]["extractVars"] = copy.deepcopy(scheduling_extract_vars)

    search = copy.deepcopy(source_by["n_search"])
    search["id"] = "n_goal_search"
    search["data"]["name"] = "Goal search (silent)"
    # Producer names are an exact byte-for-byte copy of the working n_search.
    search["data"]["responseData"] = copy.deepcopy(source_by["n_search"]["data"]["responseData"])
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
    # Start from the working n_offer prompt. Preserve its literal offer sentence and
    # add deterministic rendering discipline rather than asking the model to summarize.
    ask_prompt = source_by["n_ask"]["data"]["prompt"]
    opening = ask_prompt.split('TASK. Send this message with the patient\'s first name filled in: "', 1)[1].split('" If the patient writes in Chinese', 1)[0]
    offer_prompt = source_by["n_offer"]["data"]["prompt"]
    offer_prompt = offer_prompt.replace(
        PROMISE_SENTENCE,
        NO_SLOT_SENTENCE,
    )
    old_later = ("If they ask for something later in the day, a different time of day, or the latest "
                 "you have, do NOT name any time: say you will look and take the path for later in the day.")
    offer_prompt = offer_prompt.replace(old_later, D4)
    render_contract = (
        "RENDER CONTRACT. Send exactly one patient-facing message per turn. When two fresh slots are "
        "present, render this template literally, substituting only the four supplied values: \"" +
        OFFER_TEMPLATE + "\" The day-name values include the gateway's proven MM/DD/YYYY date; preserve "
        "each complete value exactly. Do not summarize, paraphrase, infer, interpolate, claim a latest "
        "time, or append a future-action promise or a second message. "
        "When fresh slots are absent on the entry turn, send exactly this greeting and nothing else: \"" +
        opening + "\""
    )
    response["data"]["prompt"] = offer_prompt + "\n\n" + render_contract
    response["data"]["userWait"] = True
    response["data"]["extractVars"] = copy.deepcopy(scheduling_extract_vars)
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
    add("n_appt_check", "e_defer", "ok != true")
    add("n_goal_search", "n_goal_response", "ok != true")
    add("n_goal_search", "n_date_conflict", "date_conflict_detected == conflict")
    add("n_goal_search", "n_goal_response", "slot_count == 0")
    add("n_goal_search", "n_goal_response", "slot_count == 1")
    add("n_goal_search", "n_goal_response", "slot_count >= 2")
    # Patient response routing is copied in meaning from n_offer and searches directly.
    add("n_goal_response", "n_gate_1", "takes only the first opening offered")
    add("n_goal_response", "n_gate_2", "takes only the second opening offered")
    add("n_goal_response", "n_goal_search", "wants a different day or time")
    add("n_goal_response", "e_declined", "declines this offer")
    add("n_goal_response", "e_timeout", "72-hour timeout")
    # Kept D6 nodes now return directly to the one search call.
    add("n_date_conflict", "n_goal_search", "patient provides any usable day, weekday, or date, including either conflicting option or a new replacement date")
    add("n_date_conflict_retry", "n_goal_search", "after the one allowed re-ask, always continue to search using the best extracted date; never remain on this node")
    # Existing consent and lost-slot routes that formerly entered retired nodes.
    add("n_gate_1", "n_goal_search", "says no or wants other times")
    add("n_gate_2", "n_goal_search", "says no or wants other times")
    add("n_verify_1", "n_goal_response", "slot_conflict == true")
    add("n_verify_1", "n_goal_response", "conflict_reason != ")
    add("n_verify_2", "n_goal_response", "slot_conflict == true")
    add("n_verify_2", "n_goal_response", "conflict_reason != ")
    add("n_book_1", "n_goal_search", "book_error == slot_conflict")
    add("n_book_2", "n_goal_search", "book_error == slot_conflict")

    graph = {k: copy.deepcopy(v) for k, v in src.items() if k not in ("nodes", "edges")}
    graph["nodes"] = nodes
    graph["edges"] = edges
    graph["derivation"] = {"source": str(SOURCE), "kept_verbatim": sorted(KEEP), "collapsed": COLLAPSED}
    return graph


def assert_kept_verbatim(graph: dict) -> int:
    src = json.loads(SOURCE.read_text(encoding="utf-8"))
    old = {n["id"]: n for n in src["nodes"]}
    new = {n["id"]: n for n in graph["nodes"]}
    changed = {"n_appt_check", "n_gate_1", "n_gate_2", "n_date_conflict", "n_date_conflict_retry", "n_confirm", "n_help", "n_office", "n_faq"}
    for node_id in KEEP:
        if node_id in changed:
            continue
        assert new[node_id] == old[node_id], f"kept node changed: {node_id}"
    return len(KEEP) - len(changed)


def write_fixtures(graph: dict) -> None:
    fixtures = {"conformant": copy.deepcopy(graph)}
    x = copy.deepcopy(graph)
    x["edges"].append(edge("n_goal_response", "n_goal_response", "tamper wait self-loop", 999))
    fixtures["A-wait-self-loop"] = x
    x = copy.deepcopy(graph)
    x["edges"].append(edge("n_date_conflict", "e_declined", "tamper negotiation terminal", 999))
    fixtures["B-negotiation-terminal"] = x
    x = copy.deepcopy(graph)
    next(n for n in x["nodes"] if n["id"] == "n_goal_response")["data"]["prompt"] = "Checking availability for you"
    fixtures["C-banned-promise"] = x
    x = copy.deepcopy(graph)
    next(n for n in x["nodes"] if n["id"] == "n_date_conflict")["data"]["prompt"] = "Come at 3:15 pm"
    fixtures["D-clock-containment"] = x
    x = copy.deepcopy(graph)
    next(n for n in x["nodes"] if n["id"] == "n_gate_1")["data"]["extractVars"].append(["duplicate_goal", "string", "duplicate"])
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
