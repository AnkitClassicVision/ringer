#!/usr/bin/env python3
"""Deterministically derive the goal-loop graph from the production graph."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "source-v93-pathway.json"
V96_SOURCE = HERE / "production-v96-graph.json"
OUTPUT = HERE / "pathway-goalloop-draft.json"
FROZEN_EXTRACTORS = HERE / "frozen-extractors.json"

COLLAPSED = {
    "n_ask": "n_goal_ask", "n_miss_empty": "n_goal_ask",
    "n_miss_unread": "n_goal_ask", "n_miss_thin": "n_goal_ask",
    "n_miss_unbookable": "n_goal_ask", "n_clarify": "n_goal_ask",
    "n_miss_time": "n_goal_ask", "n_offer": "n_goal_response",
    "n_offer_2": "n_goal_response", "n_offer_3": "n_goal_response",
    "n_offer_near": "n_goal_response", "n_negotiate": "n_goal_response",
    "n_recheck": "n_goal_response", "n_which_intent": "n_goal_response",
    "n_search": "n_goal_search", "n_page_2": "n_goal_search",
    "n_page_3": "n_goal_search", "n_page_near": "n_goal_search",
}

KEEP = {
    "n_identity", "n_appt_check", "e_defer", "n_help", "n_office", "n_faq",
    "n_gate_1", "n_gate_2", "n_verify_1", "n_verify_2",
    "n_book_1", "n_book_2", "n_reconcile_1", "n_reconcile_2",
    "e_booked", "e_booking_failed", "e_book_unknown", "e_booked_recovered",
    "e_declined", "e_timeout", "e_stop", "e_not_me", "n_suppress_stop",
    "n_suppress_not_me", "n_date_conflict", "n_date_conflict_retry",
    "e_safe_identity", "e_safe_failure", "e_office", "e_existing",
}

GOAL_ANCHOR = [
    "goal_anchor", "string",
    "Extract a clock time like 09:30 am only when the patient names a specific target clock time. Otherwise leave this value empty.",
    False, False, True,
]

DIRECT_SEARCH_SOURCES = {
    "n_goal_ask", "n_goal_response", "n_date_conflict", "n_date_conflict_retry",
    "n_gate_1", "n_gate_2", "n_book_1", "n_book_2",
}
USER_WAIT_SEARCH_SOURCES = DIRECT_SEARCH_SOURCES - {"n_book_1", "n_book_2"}

OFFER_TEMPLATE = ("I have {{slot_1_day_name}} {{slot_1_start}} or "
                  "{{slot_2_day_name}} {{slot_2_start}} at MK2 Optical. "
                  "Reply 1 or 2 to take one, or tell me another day or time.")
CONFIRM_TEMPLATE = (
    "Your eye exam is booked for {{slot_{index}_day_name}} {{slot_{index}_start}} at MK2 Optical. "
    "You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219"
)
CONFIRM_TEMPLATE_ZH = (
    "您的眼科检查已预约在 {{slot_{index}_day_name}} {{slot_{index}_start}}（地点：MK2 Optical）。"
    "您都安排好了。如有其他问题，请致电 MK2 Optical，电话：(212) 219-2219"
)
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

AVAILABILITY_RULE = (
    "\n\n## Availability Interpretation\n"
    "- Interpret the WHOLE sentence. When the patient mentions leaving, being away, being out of town, "
    "being unavailable, or that they won't be back until some period, extract the date or period they CAN "
    "come in: their return or availability date. Never extract a date they state as unavailable.\n"
    "- Canonical example: the message \"I'm leaving town today and won't be back for 2 weeks - how about then?\" "
    "extracts \"in 2 weeks\", not \"today\"."
)

ANAPHORIC_WEEK_RULE = (
    "\n\n## Anaphoric Week References\n"
    "- When the patient references a day relative to an already-discussed or already-offered date or week, "
    "including forms like \"monday that week\", \"the monday of that week\", or \"monday the same week\", "
    "resolve it against that established date and emit the explicit form \"monday the week of MM/DD/YYYY\" "
    "using the established date.\n"
    "- Canonical example: with Tuesday 08/18/2026 offers standing, \"What about Monday that week?\" extracts "
    "\"monday the week of 08/18/2026\"."
)


def scheduling_extractors(v96_by: dict) -> list:
    """Return the five production extractors with only the two date descriptions extended."""
    extractors = copy.deepcopy(v96_by["n_ask"]["data"]["extractVars"])
    for extractor in extractors:
        if extractor[0] in {"preference_from", "preference_to"}:
            extractor[2] += AVAILABILITY_RULE + ANAPHORIC_WEEK_RULE
    return extractors


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
    v96 = json.loads(V96_SOURCE.read_text(encoding="utf-8"))
    source_by = {n["id"]: n for n in src["nodes"]}
    v96_by = {n["id"]: n for n in v96["nodes"]}
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
        ["appt_count", "==", "0", {"id": "n_goal_ask", "name": "No upcoming appointment"}],
        ["ok", "!=", "true", {"id": "e_defer", "name": "Appointment check unavailable"}],
    ]
    # Port assertion [33]: confirmation copy must carry the date-bearing partner
    # whenever it renders a slot time.
    for index in (1, 2):
        gate = next(n for n in nodes if n["id"] == f"n_gate_{index}")
        gate["data"]["prompt"] = gate["data"]["prompt"].replace(
            f"{{{{slot_{index}_start}}}}", f"{{{{slot_{index}_day_name}}}} {{{{slot_{index}_start}}}}"
        )

    # A booking-success branch may only render the exact slot that its signer
    # wrote. Split the former free-form confirmation node by booked branch.
    old_confirm = copy.deepcopy(source_by["n_confirm"])
    old_task = old_confirm["data"]["prompt"].split("\n\nTASK. ", 1)[1].split("\n\nNEVER. ", 1)[0]
    for index in (1, 2):
        confirm = copy.deepcopy(old_confirm)
        confirm["id"] = f"n_confirm_{index}"
        confirm["data"]["name"] = f"Booked opening {index}"
        exact_task = (
            "TEMPLATE-VERBATIM. Send exactly one of the following templates, substituting only the supplied "
            "slot values. Do not summarize, paraphrase, infer, restate, or add text. For an English-language "
            f"thread send exactly: \"{CONFIRM_TEMPLATE.replace('{index}', str(index))}\" For a Chinese-language thread "
            f"send exactly: \"{CONFIRM_TEMPLATE_ZH.replace('{index}', str(index))}\""
        )
        confirm["data"]["prompt"] = confirm["data"]["prompt"].replace(
            "TASK. " + old_task, exact_task
        ).replace(PROMISE_SENTENCE, NO_SLOT_SENTENCE)
        nodes.append(confirm)

    for index in (1, 2):
        book = next(n for n in nodes if n["id"] == f"n_book_{index}")
        for pathway in book["data"].get("responsePathways", []):
            if pathway[:3] == ["book_success", "==", "true"]:
                pathway[3]["id"] = f"n_confirm_{index}"

    scheduling_extract_vars = scheduling_extractors(v96_by)

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
    search["data"]["responseData"].extend([
        {"data": "$.result.out_of_hours", "name": "out_of_hours"},
        {"data": "$.result.requested_clock", "name": "requested_clock"},
        {"data": "$.result.from_unresolved", "name": "from_unresolved"},
    ])
    production_body = json.loads(v96_by["n_search"]["data"]["body"])
    search["data"]["body"] = json.dumps(production_body, separators=(",", ":"))
    search["data"]["responsePathways"] = [
        ["ok", "!=", "true", {"id": "n_goal_ask", "name": "Search unavailable"}],
        ["date_conflict_detected", "==", "conflict", {"id": "n_date_conflict", "name": "Two dates disagree"}],
        ["from_unresolved", "==", "true", {"id": "n_goal_ask", "name": "Requested day unresolved"}],
        ["out_of_hours", "==", "true", {"id": "n_goal_ask", "name": "Requested clock outside office hours"}],
        ["slot_count", "==", "0", {"id": "n_goal_ask", "name": "No openings"}],
        ["slot_count", "==", "1", {"id": "n_goal_response", "name": "One opening"}],
        ["slot_count", ">=", "2", {"id": "n_goal_response", "name": "Two openings"}],
    ]
    nodes.append(search)

    for node_id, name, time_pref in (
        ("n_goal_search_latest", "Goal search latest (silent)", "latest"),
        ("n_goal_search_anchor", "Goal search anchor (silent)", "anchor={{goal_anchor}}"),
        ("n_goal_search_offered_latest", "Goal search offered date latest (silent)", "latest"),
        ("n_goal_search_offered_time", "Goal search offered date time (silent)", "none"),
    ):
        variant = copy.deepcopy(search)
        variant["id"] = node_id
        variant["data"]["name"] = name
        body = copy.deepcopy(production_body)
        body["time_pref"] = time_pref
        if node_id in {"n_goal_search_offered_latest", "n_goal_search_offered_time"}:
            body["from"] = "{{slot_1_start}}"
            body["to"] = "{{slot_1_start}}"
        variant["data"]["body"] = json.dumps(body, separators=(",", ":"))
        nodes.append(variant)

    ask = copy.deepcopy(source_by["n_ask"])
    ask["id"] = "n_goal_ask"
    ask["data"]["name"] = "Goal ask and search miss"
    ask_prompt = source_by["n_ask"]["data"]["prompt"]
    opening = ask_prompt.split('TASK. Send this message with the patient\'s first name filled in: "', 1)[1].split('" If the patient writes in Chinese', 1)[0]
    ask["data"]["prompt"] = f'''ROLE. You schedule comprehensive eye exams for MK2 Optical by text. This is the pre-offer stage. You have no appointment openings and must never speak, infer, repeat, or estimate an opening.

OPENING. On conversation entry, send exactly this opening and nothing else: "{opening}"

ASK. Otherwise ask when they would like to come in. Get one usable day, weekday, date, week, weekend, or time preference, then route to search. A first available, soonest, earliest, whenever, late, latest, last-appointment, end-of-day, near, around, or close-to-clock request is usable and routes to its labelled search. Agreement-phrased clock preferences such as "3pm works for me" are also usable even though no opening has been offered.

MISSES. Unusable input gets a request for a day or time. For an unrenderable timeframe such as "the week after that," ask once for a date, e.g. August 12. When from_unresolved is true, do not trust or speak returned slots; ask plainly for the day. After zero results, say the requested window has no match and ask for another day or time. After a search error, say openings could not be retrieved and ask once. Never clarify again after usable input.

OUT OF HOURS. When out_of_hours is true, say there are no openings at {{{{requested_clock}}}} and ask for another day or time. Never state or imply that the requested clock is available.

SAFETY. Send exactly one patient-facing message per turn in English or Chinese; switch after the patient writes in Chinese. Never expose variables, IDs, values, or internal work. Never mention, render, or fabricate slot variables or an offer. Never promise a future reply or ask the patient to wait while a search runs. Nothing is held or booked here. Declines route to decline; 72-hour silence routes to timeout.'''
    ask["data"]["userWait"] = True
    ask["data"]["extractVars"] = copy.deepcopy(scheduling_extract_vars) + [copy.deepcopy(GOAL_ANCHOR)]
    nodes.append(ask)

    response = copy.deepcopy(source_by["n_offer"])
    response["id"] = "n_goal_response"
    response["data"]["name"] = "Goal response and offer"
    # Post-offer only: protected offer and consent behavior, with no entry copy.
    response["data"]["prompt"] = f'''ROLE. You schedule comprehensive eye exams for MK2 Optical by text. Your only goal is one booked appointment. The system supplies the patient name and real openings.

ONE MESSAGE. Send exactly one patient-facing message per turn in English or Chinese. Never expose variables, IDs, values or internal work. Switch after the patient writes in Chinese.

OFFER. With two fresh slots, send exactly: "{OFFER_TEMPLATE}" Substitute only its four values. For Chinese use: "我这里有 {{{{slot_1_day_name}}}} {{{{slot_1_start}}}} 或 {{{{slot_2_day_name}}}} {{{{slot_2_start}}}}（地点：MK2 Optical）。回复1或2选择，或告诉我其他日期或时间。" Each day-name includes the proven MM/DD/YYYY date. Preserve values exactly; do not paraphrase or append text.

OFFER-INTEGRITY: Every clock time or date spoken in an offer must be one of the literal rendered slot values ({{{{slot_1_day_name}}}} {{{{slot_1_start}}}} / {{{{slot_2_day_name}}}} {{{{slot_2_start}}}}). If the current slot values do not answer what the patient asked, never state any other time or date; instead say what the available slot values are or ask for the patient's preference.

TIME SAFETY. Clock times may appear only at offer steps and only from slot variables returned by a lookup in THIS turn. Never invent, infer, convert, reformat, or repeat one from memory or patient words. Without fresh results, state no date or time. Never promise a future reply or ask the patient to wait while a search runs. Nothing is held or booked here. Never say booked, scheduled, held, reserved, or confirmed; only confirmation after system success may do that.

ROUTING. A bare 1 or 2, yes to one opening, or its offered clock time accepts it. Mixed acceptance plus another day/time is not consent; route to the mixed-intent clarification. A new day, date, week, or time preference different from the offered date routes to search. Late, latest, last-appointment, or end-of-day on the offered date routes to offered-date-latest. Another time preference on the offered date routes to offered-date-time.

OUT OF HOURS. When out_of_hours is true, say there are no openings at {{{{requested_clock}}}}. Offer the nearest real slots verbatim from slot variables and ask for another day or time. Never state or imply that requested clock is available.

UNRESOLVED DAY. When from_unresolved is true, do not trust or speak the returned slots; ask the patient plainly for the day.

OFFER LIMITS. These are the only openings known and the soonest shown for that day; you have not seen the full day. Never claim they are the office's latest or nothing later exists. For later requests, name no other time and search. Search another requested day. Declines route to decline; 72-hour silence to timeout.

OTHER BANS. Do not claim you can book or check booking success. Do not say free or mention discounts, packages, savings, prices, or plan coverage. The Chinese-service invitation appears only in the exact opening.''' 
    response["data"]["userWait"] = True
    response["data"]["extractVars"] = copy.deepcopy(scheduling_extract_vars) + [copy.deepcopy(GOAL_ANCHOR)]
    nodes.append(response)

    # Round 10 restores the production-v96 consent clarification as a distinct
    # user-wait node. Only its graph identity and extractor ownership change.
    mixed = copy.deepcopy(v96_by["n_which_intent"])
    mixed["id"] = "n_mixed_intent"
    mixed["data"]["name"] = "Clarify mixed offered-opening and new-time intent"
    mixed["data"]["extractVars"] = copy.deepcopy(scheduling_extract_vars)
    nodes.append(mixed)

    node_ids = {n["id"] for n in nodes}
    edges = []
    # Preserve every edge whose endpoints survive and whose route remains valid.
    for e in src["edges"]:
        if e["source"] in node_ids and e["target"] in node_ids:
            edges.append(copy.deepcopy(e))

    def add(s, t, label):
        edges.append(edge(s, t, label, len(edges)))

    # Entry and loop. Webhook labels are executable Bland conditions.
    add("n_appt_check", "n_goal_ask", "appt_count == 0")
    add("n_appt_check", "e_defer", "ok != true")
    add("n_goal_search", "n_goal_ask", "ok != true")
    add("n_goal_search", "n_date_conflict", "date_conflict_detected == conflict")
    add("n_goal_search", "n_goal_ask", "from_unresolved == true")
    add("n_goal_search", "n_goal_ask", "out_of_hours == true")
    add("n_goal_search", "n_goal_ask", "slot_count == 0")
    add("n_goal_search", "n_goal_response", "slot_count == 1")
    add("n_goal_search", "n_goal_response", "slot_count >= 2")
    for search_id in (
        "n_goal_search_latest", "n_goal_search_anchor",
        "n_goal_search_offered_latest", "n_goal_search_offered_time",
    ):
        add(search_id, "n_goal_ask", "ok != true")
        add(search_id, "n_date_conflict", "date_conflict_detected == conflict")
        add(search_id, "n_goal_ask", "from_unresolved == true")
        add(search_id, "n_goal_ask", "out_of_hours == true")
        add(search_id, "n_goal_ask", "slot_count == 0")
        add(search_id, "n_goal_response", "slot_count == 1")
        add(search_id, "n_goal_response", "slot_count >= 2")
    # Pre-offer routing owns broad intent enumeration but is physically unable to offer.
    add("n_goal_ask", "n_goal_search", "says any day, weekday, date, week, weekend, or time preference - including Saturday, this weekend, next week, or a month and day - or asks for the first available, soonest, earliest, or whenever opening - or gives only a time preference when no date has been offered yet - including agreement-phrased times like 3pm works for me when no opening has been offered yet")
    add("n_goal_ask", "n_goal_search_latest", "wants late, latest, last appointment, or end of day")
    add("n_goal_ask", "n_goal_search_anchor", "asks for a time near, around, or close to a specific clock time")
    add("n_goal_ask", "e_declined", "declines scheduling")
    add("n_goal_ask", "e_timeout", "72-hour timeout")
    # Post-offer routing is sharply disjoint.
    add("n_goal_response", "n_gate_1", "takes only the first opening offered, including by naming that opening's clock time")
    add("n_goal_response", "n_gate_2", "takes only the second opening offered, including by naming that opening's clock time")
    add("n_goal_response", "n_goal_search", "states a NEW day, date, week, or time preference different from the offered date")
    add("n_goal_response", "n_goal_search_offered_latest", "after an opening has been offered, wants late, latest, last appointment, or end of day on the offered date")
    add("n_goal_response", "n_goal_search_offered_time", "after an opening has been offered, gives only a time preference on the already offered date, excluding late, latest, last appointment, or end of day - or asks for the earliest, soonest, or first available time on that date")
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
    for index in (1, 2):
        confirm_id = f"n_confirm_{index}"
        add(f"n_book_{index}", confirm_id, "book_success == true")
        add(confirm_id, "e_booked", "72-hour silence after booking")
        add(confirm_id, "e_booked", "confirmation delivered")
        add(confirm_id, "e_defer", "change requested after confirmation")
        add(confirm_id, "e_defer", "anything else requested after booking")

    # Append round-10 edges so every unrelated derived edge keeps its prior ID.
    add("n_goal_response", "n_mixed_intent", "both selects an opening and asks for a different day or time")
    add("n_mixed_intent", "n_gate_1", "confirms they want the first offered opening, including by naming its clock time")
    add("n_mixed_intent", "n_gate_2", "confirms they want the second offered opening, including by naming its clock time")
    add("n_mixed_intent", "n_goal_search", "states a new day, date, or time preference")
    add("n_mixed_intent", "e_declined", "declines both choices")
    add("n_mixed_intent", "e_timeout", "72-hour timeout")

    graph = {k: copy.deepcopy(v) for k, v in src.items() if k not in ("nodes", "edges")}
    graph["nodes"] = nodes
    graph["edges"] = edges
    graph["derivation"] = {"source": str(SOURCE), "kept_verbatim": sorted(KEEP), "collapsed": COLLAPSED}
    return graph


def assert_kept_verbatim(graph: dict) -> int:
    src = json.loads(SOURCE.read_text(encoding="utf-8"))
    old = {n["id"]: n for n in src["nodes"]}
    new = {n["id"]: n for n in graph["nodes"]}
    changed = {"n_appt_check", "n_gate_1", "n_gate_2", "n_book_1", "n_book_2", "n_date_conflict", "n_date_conflict_retry", "n_help", "n_office", "n_faq"}
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
    v96 = json.loads(V96_SOURCE.read_text(encoding="utf-8"))
    FROZEN_EXTRACTORS.write_text(
        json.dumps(scheduling_extractors({n["id"]: n for n in v96["nodes"]}), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    graph = build()
    kept = assert_kept_verbatim(graph)
    OUTPUT.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if "--fixtures" in sys.argv:
        write_fixtures(graph)
    print(f"WROTE={OUTPUT.name}")
    print(f"KEPT_VERBATIM={kept} nodes")
