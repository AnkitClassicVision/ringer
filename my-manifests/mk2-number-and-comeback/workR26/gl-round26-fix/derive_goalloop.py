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

CORRECTION_ROUTE = ("states or corrects to a different day, date, week, or weekday than offered - "
                    "including replies beginning with no, actually, or I meant")
BOOKING_INTEGRITY_RULE = ("BOOKING-INTEGRITY: If the patient's agreed time or date does not match the slot values "
                          "you are about to confirm, do NOT confirm and do NOT proceed to booking; instead say you "
                          "want to re-check that date and ask them to confirm the day, which routes back to a fresh search.")
BOOKING_MISMATCH_ROUTE = "the patient names a date or time that does not match the opening being confirmed"
NO_BOOKING_CLAIM_RULE = ("NO-BOOKING-CLAIM: You have NOT booked anything. Never say or imply an appointment is "
                         "booked, held, confirmed, reserved, set, or that we will see them then. Only the system's "
                         "own confirmation message after a completed booking may say that. If the patient believes "
                         "they are booked and you have not confirmed a booking, tell them plainly that nothing is "
                         "booked yet and continue.")
GOAL_ASK_NO_BOOKING_CLAIM_RULE = (NO_BOOKING_CLAIM_RULE + " Never state a clock time at all; do not infer, repeat, "
                                  "render, or estimate one from any source.")
POST_BOOKING_NO_BOOKING_CLAIM_RULE = ("NO-BOOKING-CLAIM: The patient's existing appointment stands. Never claim any "
                                      "NEW or CHANGED booking, hold, confirmation, reservation, or setting. Changes "
                                      "go to the office at (212) 219-2219.")
TIME_GRID_RULE = ("TIME-GRID: Appointment times exist only at :00, :15, :30 and :45. State ONLY the literal rendered "
                  "slot values ({{slot_1_day_name}} {{slot_1_start}} / {{slot_2_day_name}} {{slot_2_start}}). If the "
                  "patient names any other time, including a typo or an off-grid minute like 10:40, say that time is "
                  "not available, re-state the real slot values verbatim, then ask which they want.")
NAMED_TIME_PICK_ROUTE = ("names a specific clock time to take, including bare digit forms like 1115, 11 15, or "
                         "11:15, rather than replying 1 or 2, excluding after or before-hour windows")
HUMAN_REQUEST_ROUTE = ("asks to speak with a person, call the office, talk to the front desk or staff, or requests "
                       "a phone call instead of texting")
TIME_PICK_TEMPLATE = ("I have {{slot_1_day_name}} {{slot_1_start}} at MK2 Optical. "
                      "Reply 1 to take it, or tell me another day or time.")

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
    "n_identity", "n_appt_check", "n_help", "n_office", "n_faq",
    "n_gate_1", "n_gate_2", "n_verify_1", "n_verify_2",
    "n_book_1", "n_book_2", "n_reconcile_1", "n_reconcile_2",
    "e_booked", "e_booking_failed", "e_book_unknown", "e_booked_recovered",
    "e_declined", "e_timeout", "e_stop", "e_not_me", "n_suppress_stop",
    "n_suppress_not_me", "n_date_conflict", "n_date_conflict_retry",
    "e_safe_identity", "e_safe_failure", "e_office", "e_existing",
}

POST_BOOKING_PROMPT = f"""ROLE. The patient's appointment is already booked. Confirm that it is set and provide polite post-booking support.

{POST_BOOKING_NO_BOOKING_CLAIM_RULE}

COPY. Say their appointment is set. For every request to change, cancel, or reschedule it, tell them to call the office at (212) 219-2219. Never state or imply that you can modify, cancel, move, rebook, or otherwise change the appointment.

SUPPORT. Keep answering politely while the conversation remains active. Answer simple appointment-related questions when the known facts are sufficient. For every change, cancellation, or rescheduling request, repeat the office referral. Do not offer openings, search availability, invoke booking, or route back into scheduling. Never expose variables, IDs, values, or internal work. Opt-out language routes to stop. A 72-hour silence routes to timeout."""

GOAL_ANCHOR = [
    "goal_anchor", "string",
    "Extract a clock time like 09:30 am only when the patient names a specific target clock time. Bare 3-4 digit times such as 1115, 1015, or 930 map to HH:MM am/pm using the conversation context. Otherwise leave this value empty.",
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

    post_booking = {
        "id": "n_post_booking",
        "type": "Default",
        "data": {
            "name": "Booked - support",
            "prompt": POST_BOOKING_PROMPT,
            "text": "",
            "userWait": True,
        },
    }
    nodes.append(post_booking)

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
        ["appt_count", ">=", "1", {"id": "n_post_booking", "name": "Upcoming appointment found"}],
        ["appt_count", "==", "0", {"id": "n_goal_ask", "name": "No upcoming appointment"}],
        ["ok", "!=", "true", {"id": "n_post_booking", "name": "Appointment check unavailable"}],
    ]
    # Port assertion [33]: confirmation copy must carry the date-bearing partner
    # whenever it renders a slot time.
    for index in (1, 2):
        gate = next(n for n in nodes if n["id"] == f"n_gate_{index}")
        gate["data"]["prompt"] = gate["data"]["prompt"].replace(
            f"{{{{slot_{index}_start}}}}", f"{{{{slot_{index}_day_name}}}} {{{{slot_{index}_start}}}}"
        )
        gate["data"]["prompt"] = gate["data"]["prompt"].replace(
            "\n\nNEVER. ", f"\n\n{BOOKING_INTEGRITY_RULE}\n\nNEVER. ", 1
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
        {"data": "$.result.closed_day", "name": "closed_day"},
        {"data": "$.result.requested_clock", "name": "requested_clock"},
        {"data": "$.result.from_unresolved", "name": "from_unresolved"},
    ])
    production_body = json.loads(v96_by["n_search"]["data"]["body"])
    production_body["context_date"] = "{{slot_1_start}}"
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
        ("n_goal_search_offered_anchor", "Goal search offered date anchor (silent)", "anchor={{goal_anchor}}"),
        ("n_goal_search_offered_latest", "Goal search offered date latest (silent)", "latest"),
        ("n_goal_search_offered_time", "Goal search offered date time (silent)", "none"),
    ):
        variant = copy.deepcopy(search)
        variant["id"] = node_id
        variant["data"]["name"] = name
        body = copy.deepcopy(production_body)
        body["time_pref"] = time_pref
        if node_id in {"n_goal_search_offered_anchor", "n_goal_search_offered_latest", "n_goal_search_offered_time"}:
            body["from"] = "{{slot_1_start}}"
            body["to"] = "{{slot_1_start}}"
        variant["data"]["body"] = json.dumps(body, separators=(",", ":"))
        if node_id == "n_goal_search_anchor":
            variant["data"]["responsePathways"] = [
                copy.deepcopy(pathway)
                for pathway in search["data"]["responsePathways"]
                if pathway[:3] not in (["slot_count", "==", "1"], ["slot_count", ">=", "2"])
            ] + [["slot_count", ">=", "1", {"id": "n_time_pick_offer", "name": "Named-time opening"}]]
        elif node_id == "n_goal_search_offered_anchor":
            variant["data"]["responseData"].extend([
                {"data": "$.result.anchor_exact", "name": "anchor_exact"},
                {"data": "$.result.anchor_requested", "name": "anchor_requested"},
                {"data": "$.result.anchor_route", "name": "anchor_route"},
            ])
            variant["data"]["responsePathways"] = [
                ["anchor_route", "==", "exact", {"id": "n_gate_1", "name": "Exact named time"}],
                ["anchor_route", "==", "closest", {"id": "n_time_pick_offer", "name": "Closest named time"}],
                ["anchor_route", "==", "none", {"id": "n_goal_ask", "name": "No openings"}],
                ["anchor_route", "==", "error", {"id": "n_goal_ask", "name": "Search unavailable"}],
            ]
        nodes.append(variant)

    ask = copy.deepcopy(source_by["n_ask"])
    ask["id"] = "n_goal_ask"
    ask["data"]["name"] = "Goal ask and search miss"
    ask_prompt = source_by["n_ask"]["data"]["prompt"]
    opening = ask_prompt.split('TASK. Send this message with the patient\'s first name filled in: "', 1)[1].split('" If the patient writes in Chinese', 1)[0]
    ask["data"]["prompt"] = f'''ROLE. Schedule MK2 Optical eye exams. Before an offer, never speak, infer, repeat, or estimate an opening.

OPENING. On conversation entry, send exactly this opening and nothing else: "{opening}"

ASK. Ask when they want to come. Route every usable date or time preference to its labelled search, including first available, late, end-of-day, near, and clock preferences.

MISSES. Ask unusable input once for a day or time. For an unrenderable timeframe, ask for a date. If from_unresolved is true, do not speak slots; ask for the day. After zero results, say the window has no match and ask for another day or time. After an error, say openings could not be retrieved and ask once. Never clarify usable input.

OUT OF HOURS. When out_of_hours is true, say that requested time is unavailable without repeating it, then ask for another day or time.

CLOSED-DAY: If closed_day is true, say the office is closed that day, is not open weekends, and ask what weekday works. Reply in Chinese when the patient wrote Chinese, otherwise English. Never call the day unavailable or imply it was booked out.

{GOAL_ASK_NO_BOOKING_CLAIM_RULE}

SAFETY. Send one message; switch after Chinese. Never expose variables, IDs, internal work, slots, or offers. Never promise a reply or ask the patient to wait. Declines route to decline; 72-hour silence to timeout.'''
    ask["data"]["userWait"] = True
    ask["data"]["extractVars"] = copy.deepcopy(scheduling_extract_vars) + [copy.deepcopy(GOAL_ANCHOR)]
    nodes.append(ask)

    response = copy.deepcopy(source_by["n_offer"])
    response["id"] = "n_goal_response"
    response["data"]["name"] = "Goal response and offer"
    # Post-offer only: protected offer and consent behavior, with no entry copy.
    offered_time_route = "after an opening has been offered, asks for any time qualifier on the already offered date, including after, before, around, later than, from a given hour, earliest, soonest, or first available; this route applies even if the message also references an offered option such as the later one, option 2, or that one - examples include after 4, before noon, later than 3, around 5, or any evening ones; Chinese examples 下午, 早上, 晚上, 中午, 晚一点 route here even alone as a single word"
    response["data"]["prompt"] = f'''ROLE. You schedule comprehensive eye exams for MK2 Optical by text. Your only goal is one booked appointment. The system supplies the patient name and real openings.

ONE MESSAGE. Send exactly one patient-facing message per turn in English or Chinese. Never expose variables, IDs, values or internal work. Switch after the patient writes in Chinese.

OFFER. With two fresh slots, send exactly: "{OFFER_TEMPLATE}" Substitute only its four values. For Chinese use: "我这里有 {{{{slot_1_day_name}}}} {{{{slot_1_start}}}} 或 {{{{slot_2_day_name}}}} {{{{slot_2_start}}}}（地点：MK2 Optical）。回复1或2选择，或告诉我其他日期或时间。" Each day-name includes the proven MM/DD/YYYY date. Preserve values exactly; do not paraphrase or append text.

OFFER-INTEGRITY: Every clock time or date spoken in an offer must be one of the literal rendered slot values ({{{{slot_1_day_name}}}} {{{{slot_1_start}}}} / {{{{slot_2_day_name}}}} {{{{slot_2_start}}}}). If the current slot values do not answer what the patient asked, never state any other time or date; instead say what the available slot values are or ask for the patient's preference.

{TIME_GRID_RULE}

{NO_BOOKING_CLAIM_RULE}

NO-NEGATIVE-CLAIM: Never say a time, window, day, or date has no availability unless the MOST RECENT search was run with that exact constraint and returned no matching slots. If the patient asks about a window you have not just searched, do not answer from memory - the routing must run a fresh search first. When in doubt, ask or search, never assert absence.

NEGATIVE-REQUIRES-SEARCH: Never state or imply that a time, day, or window has no availability unless the immediately preceding webhook result for that exact constraint shows it. When a patient asks about a different time and no such result exists, the ONLY valid move is routing to a search - answer nothing about availability inline.

CLOSED-DAY: When closed_day is true, say the office is closed that day (weekends) rather than implying it was booked out - for example, "We're closed that day - the office isn't open on weekends. What weekday works for you?" Never name closed-day availability. When closed_day is not true, keep the honest-miss copy exactly as written.

TIME SAFETY. Clock times may appear only at offer steps and only from slot variables returned by a lookup in THIS turn. Never invent, infer, convert, reformat, or repeat one from memory or patient words. Without fresh results, state no date or time. Never promise a future reply or ask the patient to wait while a search runs. Nothing is held or booked here. Never say booked, scheduled, held, reserved, or confirmed; only confirmation after system success may do that.

ROUTING. A bare 1 or 2, or yes to one opening, accepts it only when the message contains no clock-time or after, before, around, later-than, or evening qualifier. A patient who {NAMED_TIME_PICK_ROUTE} routes to anchor search before either gate route. Mixed acceptance plus another day is not consent; route to the mixed-intent clarification, but any offered-day time qualifier routes to offered-date-time. A patient who {CORRECTION_ROUTE} routes to a fresh search. Late, latest, last-appointment, or end-of-day on the offered date routes to offered-date-latest. A patient who {offered_time_route} routes to offered-date-time.

OUT OF HOURS. When out_of_hours is true, say there are no openings at {{{{requested_clock}}}}. Offer the nearest real slots verbatim from slot variables and ask for another day or time. Never state or imply that requested clock is available.

UNRESOLVED DAY. When from_unresolved is true, do not trust or speak the returned slots; ask the patient plainly for the day.

OFFER LIMITS. These are the only openings known and the soonest shown for that day; you have not seen the full day. Never claim they are the office's latest or nothing later exists. For later requests, name no other time and search. Search another requested day. Declines route to decline; 72-hour silence to timeout.

OTHER BANS. Do not claim you can book or check booking success. Do not say free or mention discounts, packages, savings, prices, or plan coverage. The Chinese-service invitation appears only in the exact opening.''' 
    response["data"]["userWait"] = True
    response["data"]["extractVars"] = copy.deepcopy(scheduling_extract_vars) + [copy.deepcopy(GOAL_ANCHOR)]
    nodes.append(response)

    time_pick_offer = copy.deepcopy(source_by["n_offer"])
    time_pick_offer["id"] = "n_time_pick_offer"
    time_pick_offer["data"]["name"] = "Named-time offer"
    time_pick_offer["data"]["prompt"] = f'''ROLE. Offer one returned opening for the specific time the patient named.

TEMPLATE-VERBATIM. When the returned first slot matches the time the patient named, send exactly: "{TIME_PICK_TEMPLATE}" Substitute only the supplied day-name and start values. Never add another opening.

MISMATCH. If the returned first slot does not match the time the patient named, say that exact time is not available, state {{{{slot_1_day_name}}}} {{{{slot_1_start}}}} as the closest opening at MK2 Optical, and ask if they want it.

ROUTING. Taking the opening by replying 1, yes, or naming its exact rendered clock time routes to its booking gate. A different day or date routes to search. A different time on this same date routes to search, except late, latest, last appointment, or end of day routes to latest search. Declines route to decline; 72-hour silence routes to timeout.

{NO_BOOKING_CLAIM_RULE}

SAFETY. Send one patient-facing message. Use only the returned first-slot values. Never expose variables, IDs, values, or internal work. Never promise a future reply or ask the patient to wait.'''
    time_pick_offer["data"]["userWait"] = True
    time_pick_offer["data"]["extractVars"] = copy.deepcopy(scheduling_extract_vars)
    nodes.append(time_pick_offer)

    # Round 10 restores the production-v96 consent clarification as a distinct
    # user-wait node. Only its graph identity and extractor ownership change.
    mixed = copy.deepcopy(v96_by["n_which_intent"])
    mixed["id"] = "n_mixed_intent"
    mixed["data"]["name"] = "Clarify mixed offered-opening and new-time intent"
    mixed["data"]["extractVars"] = copy.deepcopy(scheduling_extract_vars)
    mixed["data"]["prompt"] = mixed["data"]["prompt"].replace(
        "did they mean the opening they selected, or should you look for the different day or time they requested?",
        "did they mean the opening you selected, or should you look for the different day or time they requested?",
    ).replace(
        "Never claim an appointment exists and never name any time other than the two already offered.",
        "Never claim an appointment exists.\n\nTIME-SILENT: Do not state any clock time or date. Refer only to 'the opening you selected'.",
    )
    nodes.append(mixed)

    for node_id in ("n_office", "n_faq"):
        support = next(n for n in nodes if n["id"] == node_id)
        support["data"]["prompt"] = support["data"]["prompt"].replace(
            ", naming the openings still on offer", ""
        ) + ("\n\nTIME-SILENT: Do not state any clock time or date. Route the patient back to scheduling "
             "with a question only; do not repeat or reconstruct any opening.")

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
    add("n_appt_check", "n_post_booking", "appt_count >= 1")
    add("n_appt_check", "n_post_booking", "ok != true")
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
        if search_id == "n_goal_search_anchor":
            add(search_id, "n_time_pick_offer", "slot_count >= 1")
        else:
            add(search_id, "n_goal_response", "slot_count == 1")
            add(search_id, "n_goal_response", "slot_count >= 2")
    # Pre-offer routing owns broad intent enumeration but is physically unable to offer.
    add("n_goal_ask", "n_goal_search", "says any day, weekday, date, week, weekend, or general time preference - including Saturday, this weekend, next week, or a month and day - or asks for the first available, soonest, earliest, or whenever opening - or gives only a general time preference when no date has been offered yet - explicitly excluding latest or end-of-day requests and near, around, close-to, or other named-clock asks")
    add("n_goal_ask", "n_goal_search_latest", "wants late, latest, last appointment, or end of day")
    add("n_goal_ask", "n_goal_search_anchor", "asks for a time near, around, or close to a specific clock time")
    add("n_goal_ask", "n_office", HUMAN_REQUEST_ROUTE)
    add("n_goal_ask", "e_declined", "declines scheduling")
    add("n_goal_ask", "e_timeout", "72-hour timeout")
    # Post-offer routing is sharply disjoint.
    add("n_goal_response", "n_gate_1", "takes only the first opening offered and contains no clock-time or after, before, around, later-than, or evening qualifier")
    add("n_goal_response", "n_gate_2", "takes only the second opening offered and contains no clock-time or after, before, around, later-than, or evening qualifier")
    add("n_goal_response", "n_goal_search_offered_anchor", NAMED_TIME_PICK_ROUTE)
    add("n_goal_response", "n_goal_search", CORRECTION_ROUTE)
    add("n_goal_response", "n_goal_search_offered_latest", "after an opening has been offered, wants late, latest, last appointment, or end of day on the offered date")
    add("n_goal_response", "n_goal_search_offered_time", offered_time_route)
    add("n_goal_response", "n_office", HUMAN_REQUEST_ROUTE)
    add("n_time_pick_offer", "n_gate_1", "takes the opening offered by replying 1, yes, or naming its exact rendered clock time")
    add("n_time_pick_offer", "n_goal_search", "wants a different day or date than the one offered, excluding a different time on this date")
    add("n_time_pick_offer", "n_goal_search", "wants a different time on this date, excluding a different day or date and excluding late, latest, last appointment, or end of day")
    add("n_time_pick_offer", "n_goal_search_latest", "wants late, latest, last appointment, or end of day")
    add("n_time_pick_offer", "e_declined", "declines this offer")
    add("n_time_pick_offer", "e_timeout", "72-hour timeout")
    # Kept D6 nodes now return directly to the one search call.
    add("n_date_conflict", "n_goal_search", "patient provides any usable day, weekday, or date, including either conflicting option or a new replacement date")
    add("n_date_conflict_retry", "n_goal_search", "after the one allowed re-ask, always continue to search using the best extracted date; never remain on this node")
    # Existing consent and lost-slot routes that formerly entered retired nodes.
    add("n_gate_1", "n_goal_search", "says no or wants other times")
    add("n_gate_2", "n_goal_search", "says no or wants other times")
    add("n_gate_1", "n_goal_search", BOOKING_MISMATCH_ROUTE)
    add("n_gate_2", "n_goal_search", BOOKING_MISMATCH_ROUTE)
    add("n_verify_1", "n_goal_response", "slot_conflict == true")
    add("n_verify_1", "n_goal_response", "conflict_reason != ")
    add("n_verify_2", "n_goal_response", "slot_conflict == true")
    add("n_verify_2", "n_goal_response", "conflict_reason != ")
    add("n_book_1", "n_goal_search", "book_error == slot_conflict")
    add("n_book_2", "n_goal_search", "book_error == slot_conflict")
    for index in (1, 2):
        confirm_id = f"n_confirm_{index}"
        add(f"n_book_{index}", confirm_id, "book_success == true")
        add(confirm_id, "e_timeout", "72-hour silence after booking")
        add(confirm_id, "n_post_booking", "confirmation delivered")
        add(confirm_id, "n_post_booking", "change requested after confirmation")
        add(confirm_id, "n_post_booking", "anything else requested after booking")

    add("n_post_booking", "e_stop", "opt-out language")
    add("n_post_booking", "e_timeout", "72-hour timeout")

    # Append round-10 edges so every unrelated derived edge keeps its prior ID.
    add("n_goal_response", "n_mixed_intent", "both selects an opening and asks for a different day, excluding any clock-time or after, before, around, later-than, or evening qualifier on the offered day")
    add("n_mixed_intent", "n_gate_1", "confirms they want the first offered opening, including by naming its clock time")
    add("n_mixed_intent", "n_gate_2", "confirms they want the second offered opening, including by naming its clock time")
    add("n_mixed_intent", "n_goal_search", "states a new day, date, or time preference")
    add("n_mixed_intent", "e_declined", "declines both choices")
    add("n_mixed_intent", "e_timeout", "72-hour timeout")

    # Round 20 appends the new webhook edges so every pre-existing derived edge
    # retains its round-19 identity and ordinal.
    add("n_goal_search_offered_anchor", "n_gate_1", "anchor_route == exact")
    add("n_goal_search_offered_anchor", "n_time_pick_offer", "anchor_route == closest")
    add("n_goal_search_offered_anchor", "n_goal_ask", "anchor_route == none")
    add("n_goal_search_offered_anchor", "n_goal_ask", "anchor_route == error")

    # Every patient-facing wait node carries the same fail-closed booking-claim
    # boundary. The ask, response, and post-booking prompts use their specialized
    # forms above; append the general form to the remaining wait nodes here.
    protected_waits = {
        "n_mixed_intent", "n_gate_1", "n_gate_2",
        "n_date_conflict", "n_date_conflict_retry",
    }
    for node in nodes:
        if node["id"] in protected_waits:
            node["data"]["prompt"] = node["data"]["prompt"].rstrip() + "\n\n" + NO_BOOKING_CLAIM_RULE

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
