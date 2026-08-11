#!/usr/bin/env python3
"""Mott recall pathway v26 — real webhooks, tonight's copy rules, phone-based identity.

Changes from v23:
  * identity resolves by PHONE with the patient id as a filter, because the
    gateway's id lookup returns zero while the phone index works. A mismatched
    pair returns count 0, so the binding check is preserved.
  * store is sourced from request_data and guarded, since the identity call can
    no longer return it.
  * owner copy rules: no "free", no discount language, FAQ defers to the
    opticians, Chinese invite line on the opener only, never offer a day that was
    not asked for without saying so.
"""
import json

GW = "https://mott-booking-gw.mail.mybcat.com"
SR = "{{ SECRET.MottGatewayToken }}"
ZH_INVITE = "如需中文服务，请直接用中文回复。"

LANG_OPENER = (" Send the English message; it ends with the Chinese-service invitation line. That "
               "line appears on this opening message ONLY. Switch to Chinese only if the patient "
               "replies in Chinese, then stay in Chinese.")
LANG_REPLY = (" Reply in the language of the patient's most recent message. If they switch "
              "languages, switch with them, in either direction, every time. The Chinese-service "
              "invitation line belongs to the opening message only; never add it here. A bare "
              "number, YES or OK carries no language signal, so stay in the language already in use.")

TIMES = (" Every time shown comes from the schedule already formatted and is America/New_York "
         "clinic local time. Present it exactly as given: do not convert it, do not reformat it, "
         "and do not restate it in another style.")

# R12: the defect that told a live patient they were booked when nothing was written.
# Structural gating stops the WRITE; only an explicit prohibition stops the CLAIM.
NO_CLAIM = (" You cannot book anything and you have no way to check whether a booking succeeded. "
            "NEVER say or imply that an appointment is booked, scheduled, held, reserved, "
            "confirmed, or that you have someone down for a time, and never refer to a booking as "
            "though it already exists. Only the confirmation step may say that, and only after the "
            "booking system reports success. If the patient asks whether they are booked, say you "
            "are still getting them scheduled and have not completed it yet.")

# Loop 2 (answer other requests) always returns to Loop 1 (find and book).
BACK = (" Then ALWAYS return to the goal with a direct question: ask whether they would like you to "
        "get them scheduled now, naming the openings still on offer. A question from the patient is "
        "never a decline. Only an explicit no ends this; if it is unclear whether they still want an "
        "appointment, ask them plainly to confirm.")

NO_PRICE = (" Never say free. Never mention a discount, a package, or saving money. Never state "
            "what any specific plan covers and never quote a price or a dollar amount.")

# A live patient was shown "preference_from: monday / preference_to: monday" because the
# node's task described what to CAPTURE. Capture is the extraction config's job and happens
# automatically; the prompt must only ever describe what to SAY.
NO_LEAK = (" The message you send is read by a patient on their phone. Write only ordinary "
           "conversational English or Chinese. Never write an internal field name, a variable "
           "name, an underscore_name, a colon-and-value line, a list of captured values, a "
           "record id, or any note about what you are storing or doing internally.")

# Measured against the live gateway on 2026-07-25, not assumed:
#   accepted -> monday, next monday, mon, tuesday, tomorrow, august 3, 08/03/2026, 2026-08-03
#   REJECTED -> next week, this week, in 2 weeks, next month
# A weekday word resolves to the next occurrence of that weekday server-side, and a range of
# two weekday words works (monday..friday returned 126 openings across Mon-Fri). So a vague
# week request becomes monday..friday and the SERVER does the date arithmetic. The model is
# never asked to work out a calendar date, which is the failure mode this design avoids.
# EVERY field must always receive a value. An unfilled variable is substituted as a real
# JSON null, which drops the quotes out of the body template and makes the gateway answer
# 400 "field 'after' must be a string". Measured: the literal word none is accepted and
# ignored, so it is the sentinel for "the patient did not say". Never leave one blank.
PREFERENCE_VARS = [
    ("preference_from",
     "The first day the patient is willing to come. This field holds a DAY and nothing else: "
     "a weekday word such as monday or tuesday, or a plain date such as august 3 or "
     "08/03/2026. A clock time is NOT a day, so never put a time, a phrase like after 3pm, "
     "or a part of the day in this field; those belong in preference_after, "
     "preference_before or time_pref. If they asked for a week in general, for example next "
     "week, put monday here. If they named only a time and no day at all, put monday here "
     "too. This field must NEVER be left blank: when in doubt the answer is monday."),
    ("preference_to",
     "The last day the patient is willing to come, in the same form as preference_from. If "
     "they named one single day, repeat that same day here. If they gave a span such as "
     "tuesday or wednesday, put the later one here. If they asked for a week in general, or "
     "named only a time with no day, put friday here. This field holds a DAY and nothing "
     "else; never put a clock time in it. This field must NEVER be left blank: when in "
     "doubt the answer is friday."),
    ("preference_after",
     "The earliest clock time the patient said they could come, for example 2pm, and only when "
     "they actually gave one. If they gave no earliest time, put the single word none. This "
     "field must NEVER be left blank."),
    ("preference_before",
     "The latest clock time the patient said they could come, for example 11am, and only when "
     "they actually gave one. If they gave no latest time, put the single word none. This "
     "field must NEVER be left blank."),
    ("time_pref",
     "Exactly one of these four words: morning, afternoon, evening, none. Use morning, "
     "afternoon or evening only when the patient used that word about time of day. If they "
     "said nothing about time of day, put none. Never put a date, a weekday, a week, a month "
     "or any other phrase in this field. This field must NEVER be left blank."),
]

OPENER_EN = (
    "Hi {{patient_first}}, this is Mott Optical. We noticed that it's been awhile since your last "
    "visit with us. This is a great time to update your lenses, explore our newest eyewear "
    "collection, and even find a new pair of sunglasses while staying on top of your eye health "
    "with a comprehensive eye exam. Many vision insurance benefits renew yearly, so don't let your "
    "benefits go unused! When would you like to come in? Just reply with a day and a time that "
    "works for you and I will check what we have. Reply STOP to opt out. " + ZH_INVITE)

# Offering happens AFTER the patient says when they want to come, so the offer message is
# short and carries only the openings found for the day they actually asked for.
OFFER_EN = ("Great news, I have {{slot_1_start}} or {{slot_2_start}} at MK2. Reply 1 or 2 to take "
            "one, or tell me another day or time.")
OFFER_ZH = ("好消息，我这里有 {{slot_1_start}} 或 {{slot_2_start}}（地点：MK2）。"
            "回复 1 或 2 预约，或告诉我们其他合适的时间。")

OPENER_ZH = (
    "您好 {{patient_first}}，这里是 Mott Optical。我们注意到您距离上次到访已经有一段时间了。"
    "现在正是更新镜片、挑选新眼镜、并通过全面眼科检查守护眼睛健康的好时机。"
    "许多视力保险福利每年都会更新，请不要浪费您的福利！"
    "您希望什么时候来诊所？请直接回复适合您的日期和时间，我来为您查询。回复 STOP 退订。")

SLOT_FIELDS = ["slot_count", "slot_1_start", "slot_1_end", "slot_1_doctor",
               "slot_2_start", "slot_2_end", "slot_2_doctor", "time_pref_relaxed",
               "all_starts", "all_slots"]

RESP = {
    "ok": "$.ok", "count": "$.result.count", "patient_first": "$.result.patients[0].name_first",
    "patient_id": "$.result.patients[0].patient_id", "exam_type_id": "$.result.exam_type_id",
    "slot_count": "$.result.count",
    "slot_1_start": "$.result.slots[0].start", "slot_1_end": "$.result.slots[0].end",
    "slot_1_doctor": "$.result.slots[0].doctor_id",
    "slot_2_start": "$.result.slots[1].start", "slot_2_end": "$.result.slots[1].end",
    "slot_2_doctor": "$.result.slots[1].doctor_id",
    "pm_1_start": "$.result.slots[8].start", "pm_1_end": "$.result.slots[8].end",
    "pm_1_doctor": "$.result.slots[8].doctor_id",
    "pm_2_start": "$.result.slots[9].start", "pm_2_end": "$.result.slots[9].end",
    "pm_2_doctor": "$.result.slots[9].doctor_id",
    "all_starts": "$.result.slots[*].start",
    "all_slots": "$.result.slots",
    "late_1_start": "$.result.slots[16].start", "late_1_end": "$.result.slots[16].end",
    "late_1_doctor": "$.result.slots[16].doctor_id",
    "late_2_start": "$.result.slots[15].start", "late_2_end": "$.result.slots[15].end",
    "late_2_doctor": "$.result.slots[15].doctor_id",
    "time_pref_relaxed": "$.result.time_pref_relaxed",
    "overlap_id": "$.result.overlapping_appt_id", "conflict_reason": "$.result.reason", "book_http_status": "$.http_status", "book_error": "$.error", "error_status": "$.status",
    "new_appt_id": "$.new_appt_id",
}


LATE_RESP = dict(RESP)
LATE_RESP.update({
    "slot_1_start": RESP["late_1_start"], "slot_1_end": RESP["late_1_end"],
    "slot_1_doctor": RESP["late_1_doctor"],
    "slot_2_start": RESP["late_2_start"], "slot_2_end": RESP["late_2_end"],
    "slot_2_doctor": RESP["late_2_doctor"],
})

PM_RESP = dict(RESP)
PM_RESP.update({
    "slot_1_start": PM_RESP["pm_1_start"], "slot_1_end": PM_RESP["pm_1_end"],
    "slot_1_doctor": PM_RESP["pm_1_doctor"],
    "slot_2_start": PM_RESP["pm_2_start"], "slot_2_end": PM_RESP["pm_2_end"],
    "slot_2_doctor": PM_RESP["pm_2_doctor"],
})


def wh(nid, name, path, body, resp, pathways, start=False, resp_map=None):
    d = {"name": name, "url": GW + path, "body": body, "method": "POST",
         "headers": {"Content-Type": "application/json", "Authorization": SR},
         "modelOptions": {"retryAttempts": 0, "skipUserResponse": True},
         "responseData": [{"data": (resp_map or RESP)[n], "name": n} for n in resp],
         "responsePathways": pathways}
    if start:
        d["isStart"] = True
    return {"id": nid, "type": "Webhook", "data": d}


WORLD = ("BACKGROUND. You are the scheduling assistant for Mott Optical, an optometry practice. "
         "You are texting a patient by name who has not been in for a while, to get them booked for "
         "a comprehensive eye exam at the MK2 office. The practice management system supplies the "
         "patient's name and the real open appointment times; you never invent either. Your single "
         "purpose in this whole conversation is to get one appointment booked. Every detour comes "
         "back to that. ")


def framed(background, goal, task, never):
    """Background / Goal / Task / Never. The model running these nodes is small and
    does not infer context, so every prompt states the world explicitly rather than
    relying on the conversation so far."""
    return (WORLD + background.strip() + "\n\nGOAL. " + goal.strip()
            + "\n\nTASK. " + task.strip() + "\n\nNEVER. " + never.strip() + NO_LEAK)


def wait(nid, name, prompt, extract=None, glabel=None, auto=False, skip=False):
    d = {"name": name, "prompt": prompt, "userWait": not skip}
    # skipUserResponse: speak, then continue immediately instead of parking for another
    # patient message. This is the pattern the mature production pathway on the same
    # account uses for its own hand-off nodes. Without it a node that only announces
    # "let me check" strands the conversation until the patient texts again.
    if skip:
        d["modelOptions"] = {"skipUserResponse": True}
    # Each variable carries its OWN description. A shared placeholder like "collected from
    # the patient reply" tells the model nothing about which field is which, and it put
    # "next week" into time_pref, which only accepts morning/afternoon/evening. Extraction
    # guidance belongs here, never in the prompt, or the model prints it to the patient.
    if extract:
        d["extractVars"] = [[n, "string", desc] for n, desc in extract]
    if glabel:
        d.update({"isGlobal": True, "globalLabel": glabel, "enableGlobalAutoReturn": auto})
    return {"id": nid, "type": "Default", "data": d}


def end(nid, outcome, text, glabel=None):
    d = {"name": outcome, "text": text, "outcome": outcome}
    if glabel:
        d.update({"isGlobal": True, "globalLabel": glabel, "enableGlobalAutoReturn": False})
    return {"id": nid, "type": "End Call", "data": d}


def safe(name):
    return {"id": "e_safe_failure", "name": name}


nodes = [
    # Identity resolves by PHONE with the id as a filter: the id index returns zero,
    # the phone index works, and a mismatched pair still yields count 0.
    wh("n_identity", "Resolve identity (silent)", "/patient-search",
       '{"phone":"{{recall_cell}}","patient_id":"{{recall_patient_id}}"}',
       ["ok", "count", "patient_first", "patient_id", "exam_type_id"],
       [["recall_cell", "==", "", {"id": "e_safe_identity", "name": "No mobile supplied"}],
        ["recall_patient_id", "==", "", {"id": "e_safe_identity", "name": "No patient id supplied"}],
        ["store", "==", "", {"id": "e_safe_identity", "name": "No booking store supplied"}],
        ["count", "==", "1", {"id": "n_ask", "name": "Identity confirmed"}],
        ["count", "==", "0", {"id": "e_safe_identity", "name": "Phone and id do not bind to one patient"}],
        ["count", ">=", "2", {"id": "e_safe_identity", "name": "Not a unique patient"}],
        ["ok", "!=", "true", safe("Identity lookup unavailable")]], start=True),

    # The conversation now OPENS by asking when they want to come, instead of guessing two
    # consecutive slots the practice happened to have first. Same capture fields as the
    # negotiation step, so one loop serves both the first answer and every later change of
    # mind: ask -> search -> offer -> validate -> book.
    wait("n_ask", "Asked when",
         framed(
             "This is the very first message this patient receives. They have not been in for a "
             "while and nothing has been looked up for them yet. You do not have any appointment "
             "times in hand, and you are not going to guess at any. The moment they answer, the "
             "practice schedule is searched automatically for what they said, and the real "
             "openings come back as an offer.",
             "Send the recall message and find out when this patient would like to come in.",
             "Send this message with the patient's first name filled in: \"" + OPENER_EN + "\" "
             "If the patient writes in Chinese, send this form instead: \"" + OPENER_ZH + "\" "
             "Any answer about timing is enough to move forward, whether it is a weekday, a date, "
             "a part of the day, or a whole week. If they answer with something that is not about "
             "timing at all, answer them and then ask again when they would like to come in.",
             "Never name, invent or imply a specific appointment time here, because you do not "
             "have one yet and nothing has been checked." + NO_CLAIM + NO_PRICE + LANG_OPENER),
         extract=PREFERENCE_VARS),

    wait("n_reask", "Ask again for a day",
         framed(
             "The practice schedule was just searched for what this patient asked for and "
             "nothing usable came back, either because there were no openings in that window or "
             "because the request could not be understood well enough to search. The patient has "
             "no idea any of that happened. Nothing is booked and nothing is being held.",
             "Get one concrete day out of this patient so the schedule can be searched again.",
             "Apologise briefly for not having something to show them yet, without explaining "
             "anything technical and without claiming any day or time of day is empty, then ask "
             "them for a specific day. Give them two easy examples "
             "of what works, such as Tuesday, or August 3. Ask for one day only.",
             "Never blame the patient for how they phrased it and never mention searching, "
             "systems, errors or anything internal. Never state that a day, a morning or an "
             "afternoon has no openings, because you have not been shown enough to know that. Never name a time you have not been given."
             + NO_CLAIM + NO_PRICE + LANG_REPLY),
         extract=PREFERENCE_VARS),

    wait("n_offer", "Offered",
         framed(
             "The practice schedule has been searched for what this patient asked for and EVERY "
             "open time it found is listed for you. all_starts is the complete list of open times, "
             "in order, earliest first: {{all_starts}}. all_slots holds the same openings with the "
             "matching finish time and doctor for each one: {{all_slots}}. Because you can see the "
             "whole list, you can answer questions about what is available and you never need to "
             "guess or say you cannot see. Nothing is booked yet.",
             "Have a normal conversation about when they can come, and get them booked at a time "
             "that genuinely suits them.",
             "Offer at most two times in one message, picked from the list to match what they "
             "asked for. Read the list before you answer: "
             "if they ask what the latest is, name the LAST time in the list. "
             "If they ask for something later than a time you already mentioned, look through the "
             "list for times after that one and offer the next ones up; if there are none later, "
             "say plainly that the one you named is the latest the office has that day, and offer "
             "to look at another day. "
             "If they ask for a part of the day, or after or before a particular hour, answer from "
             "the list: offer the times that actually match, and if none match say so plainly and "
             "name the closest you do have. "
             "Never offer a time that is earlier than one they have already turned down. "
             "When they settle on a time, whether they reply with a number, name the time, or just "
             "say yes to one, copy that exact time into chosen_start, and copy the matching end "
             "time and doctor for it out of all_slots into chosen_end and chosen_doctor. Copy all "
             "three exactly as they appear, character for character, and never adjust them."
             + TIMES,
             "Never name, offer or confirm a time that is not in the list you were given, and "
             "never invent an end time or a doctor." + NO_CLAIM + NO_PRICE + LANG_OPENER),
         extract=[
             ("chosen_start", "The exact start time the patient settled on, copied character for "
                              "character from all_starts. Empty until they have actually chosen one."),
             ("chosen_end", "The finish time that all_slots gives for that same opening, copied "
                            "character for character. Empty until they have chosen."),
             ("chosen_doctor", "The doctor id that all_slots gives for that same opening, copied "
                               "exactly. Empty until they have chosen."),
         ]),

    wait("n_negotiate", "Negotiating",
         framed(
             "The patient has seen the openings and does not want them, or none were found. You are "
             "the step that collects what they DO want. Immediately after you, the practice "
             "schedule is searched automatically using whatever you capture, and the results come "
             "back as a fresh offer. You are not the end of anything.",
             "Tell the patient you are looking, and nothing more. The search happens the instant "
             "you finish, without waiting for them to reply again.",
             "Send ONE short, friendly line saying you are checking the schedule for what they "
             "asked for. Something like \"Let me check that for you.\" and nothing else. Do not ask "
             "them a question, do not repeat their request back to them, and do not offer any "
             "times, because you do not have the new ones yet." + NO_LEAK,
             "Never convert their words into a calendar date yourself and never guess today's date."
             + NO_CLAIM + NO_PRICE + LANG_REPLY),
         skip=True,
         extract=PREFERENCE_VARS,
         glabel=("Before any booking is confirmed, the patient asks for a different date, time or "
                 "range for this new appointment. Does not match a reply that also selects an "
                 "offered opening, and does not apply once a booking is confirmed.")),

    wh("n_search", "Search by preference (silent)", "/availability",
       '{"store":"{{store}}","from":"{{preference_from}}","to":"{{preference_to}}",'
       '"after":"{{preference_after}}","before":"{{preference_before}}",'
       '"time_pref":"{{time_pref}}","slot_minutes":"15"}',
       ["ok"] + SLOT_FIELDS,
       [["ok", "!=", "true", {"id": "n_reask", "name": "Search rejected or unavailable"}],
        ["slot_count", "==", "0", {"id": "n_reask", "name": "Nothing found, ask for another day"}],
        ["time_pref", "==", "afternoon", {"id": "n_search_pm", "name": "Wants the afternoon"}],
        ["time_pref", "==", "evening", {"id": "n_search_late", "name": "Wants the evening"}],
        ["slot_count", "==", "1", {"id": "n_offer", "name": "One opening found"}],
        ["slot_count", ">=", "2", {"id": "n_offer", "name": "Two or more found"}]]),

    # Same call, same day, read from later in the list. The gateway ignores time_pref, so
    # this is how an afternoon becomes reachable at all. If that day is too thin to have a
    # slot at this position the value comes back empty and the patient is asked for another
    # day, rather than being shown nothing or being shown a morning they did not ask for.
    wh("n_search_late", "Late in the day (silent)", "/availability",
       '{"store":"{{store}}","from":"{{preference_from}}","to":"{{preference_to}}",'
       '"after":"{{preference_after}}","before":"{{preference_before}}",'
       '"time_pref":"{{time_pref}}","slot_minutes":"15"}',
       ["ok"] + SLOT_FIELDS,
       [["ok", "!=", "true", {"id": "n_reask", "name": "Search rejected or unavailable"}],
        ["slot_1_start", "==", "", {"id": "n_search_pm", "name": "Too thin for a late slot"}],
        ["slot_1_start", "!=", "", {"id": "n_offer", "name": "Late openings found"}]],
       resp_map=LATE_RESP),

    wh("n_search_pm", "Later in the day (silent)", "/availability",
       '{"store":"{{store}}","from":"{{preference_from}}","to":"{{preference_to}}",'
       '"after":"{{preference_after}}","before":"{{preference_before}}",'
       '"time_pref":"{{time_pref}}","slot_minutes":"15"}',
       ["ok"] + SLOT_FIELDS,
       [["ok", "!=", "true", {"id": "n_reask", "name": "Search rejected or unavailable"}],
        ["slot_1_start", "==", "", {"id": "n_reask", "name": "That day has nothing later"}],
        ["slot_1_start", "!=", "", {"id": "n_offer", "name": "Later openings found"}]],
       resp_map=PM_RESP),

    wh("n_verify", "Verify the chosen time (silent)", "/conflict-check",
       '{"store":"{{store}}","doctor":"{{chosen_doctor}}","start":"{{chosen_start}}","end":"{{chosen_end}}"}',
       ["ok", "overlap_id", "conflict_reason"],
       [["ok", "!=", "true", safe("Conflict check unavailable")],
        ["conflict_reason", "!=", "", {"id": "n_reask", "name": "Not a real bookable opening"}],
        ["overlap_id", "!=", "", {"id": "n_negotiate", "name": "Something already booked there"}],
        ["overlap_id", "==", "", {"id": "n_book", "name": "Real, free and clear"}]]),

    wh("n_book", "Book the chosen time (silent)", "/sign",
       '{"verb":"appt.book","target":"{{patient_id}}","store":"{{store}}","reason":"new-booking",'
       '"params":{"doctor":"{{chosen_doctor}}","start":"{{chosen_start}}","end":"{{chosen_end}}",'
       '"type":"{{exam_type_id}}"}}',
       ["book_http_status", "book_error", "new_appt_id", "error_status"],
       [["book_error", "==", "slot_conflict", {"id": "n_negotiate", "name": "Signer found a conflict"}],
        ["book_http_status", "==", "200", {"id": "n_confirm", "name": "Signer wrote the appointment"}],
        ["book_http_status", "==", "201", {"id": "n_confirm", "name": "Signer created the appointment"}],
        ["book_http_status", "!=", "200", {"id": "e_booking_failed", "name": "Booking did not succeed"}]]),

    wait("n_confirm", "Booked",
         framed(
             "The booking system has just written a real appointment into the practice schedule for "
             "this patient and reported success. The appointment genuinely exists. This is the only "
             "point in the whole conversation where that is true.",
             "Tell the patient their appointment is booked, and make sure they do not end up with a "
             "second one.",
             "Confirm the appointment that was booked, in plain language. If the patient then asks "
             "to change, cancel or move it, give them the office number (855) 750-6688 and explain "
             "the office will take care of it.",
             "Never go back to searching, verifying or booking after this point, because that would "
             "give this patient two appointments. Never show internal identifiers." + LANG_REPLY)),

    wait("n_office", "Office handoff",
         framed(
             "The patient asked about something this conversation cannot handle, such as an order, "
             "the status of their glasses, or a medical question. You are in the middle of trying "
             "to book them an eye exam and that is still the point of the conversation.",
             "Give them the office number for the thing you cannot help with, then get back to "
             "booking the appointment.",
             "Give the office number (855) 750-6688 for what they asked about." + BACK,
             "Never treat their question as a decline and never end the conversation here."
             + NO_CLAIM + LANG_REPLY),
         glabel=("The patient asks for something outside booking this new appointment and outside "
                 "insurance or cost, such as orders, glasses status or a medical question."),
         auto=True),

    wait("n_faq", "Insurance question deferral",
         framed(
             "The patient asked about insurance, coverage, cost, contact lenses, frames or "
             "sunglasses. You do not have this patient's benefits and you have no way to look them "
             "up. The office staff can. You are in the middle of trying to book them an eye exam.",
             "Answer honestly that this needs the office, then get back to booking the appointment.",
             "If they asked whether insurance COVERS something, say that vision benefits are "
             "usually separate coverage with their own copays, and our staff will be able to help "
             "them with this. If they asked what something COSTS or what they would pay, say it "
             "depends on their benefits and someone at the office can help with that. If they say "
             "they want to speak to someone, give them the office number (855) 750-6688." + BACK,
             "Never invent, guess or generate any other answer. Never treat their question as a "
             "decline and never end the conversation here." + NO_CLAIM + NO_PRICE + LANG_REPLY),
         glabel=("The patient asks anything about insurance, coverage, cost, contact lenses, frames "
                 "or sunglasses. Answering is deferred to the office staff."),
         auto=True),

    end("e_safe_identity", "identity_failed",
        "I couldn't safely continue this scheduling request. Please call Mott Optical at (855) 750-6688."),
    end("e_safe_failure", "gateway_failed",
        "I couldn't access scheduling right now and no appointment was booked. Please call Mott Optical at (855) 750-6688."),
    end("e_booking_failed", "booking_failed",
        "No appointment was booked. Please call Mott Optical at (855) 750-6688."),
    end("e_booked", "booked", "You're all set. We look forward to seeing you."),
    end("e_office", "office", "Please call Mott Optical at (855) 750-6688."),
    end("e_declined", "declined",
        "Ok, thank you for letting us know. If you need anything, call the office at (855) 750-6688.",
        glabel="The patient is not interested or declines this offer without revoking consent."),
    end("e_stop", "stopped",
        "Understood. If you would like to be taken off our list, please call Mott Optical at "
        "(855) 750-6688 and the office can take care of it.",
        glabel="The patient wants the texts to stop. This includes a message that is just the word STOP, STOPALL, UNSUBSCRIBE, CANCEL, END, QUIT or REMOVE on its own in any casing, and any message asking to be taken off the list, to stop texting, or to not be contacted again. Match this even when the message is a single word with no other context."),
    end("e_not_me", "wrong_person",
        "Sorry about that. If you would like to be taken off our list, please call Mott Optical at "
        "(855) 750-6688 and the office can take care of it.",
        glabel="The person holding this phone is not the patient. This includes a message that is just NOT ME or WRONG NUMBER, and any message saying they are not that person, they do not know that person, this is the wrong number, or asking who this is because they were not expecting to hear from an eye doctor."),
    end("e_existing", "existing_appointment",
        "Please call Mott Optical at (855) 750-6688 and the office can help with that appointment.",
        glabel="The patient already has a different appointment they want to cancel or move."),
    end("e_timeout", "no_reply", "Closing this conversation."),
]

edges = [
    ("n_ask", "n_search", "says when they want to come in"),
    ("n_reask", "n_search", "names a specific day"),
    ("n_search", "n_search_pm", "wants later in the day"),
    ("n_search", "n_search_late", "wants the latest in the day"),
    ("n_search_late", "n_search_pm", "too thin for a late slot"),
    ("n_offer", "n_search_late", "asks for a later or the last time that day"),
    ("n_reask", "e_declined", "gives up on booking"),
    ("n_reask", "e_timeout", "72-hour timeout"),
    ("n_ask", "e_declined", "declines at the opening"),
    ("n_ask", "e_timeout", "72-hour timeout"),
    ("n_offer", "n_verify", "chooses a specific time"),
    ("n_offer", "n_negotiate", "wants a different day or time"),
    ("n_offer", "e_declined", "declines this offer"),
    ("n_offer", "e_timeout", "72-hour timeout"),
    ("n_negotiate", "n_search", "preference collected"),
    ("n_negotiate", "e_declined", "declines after negotiating"),
    ("n_negotiate", "e_timeout", "72-hour timeout"),
    ("n_confirm", "e_booked", "confirmation delivered"),
    ("n_confirm", "n_office", "change requested after confirmation"),
    ("n_confirm", "e_booked", "72-hour silence after booking"),
    ("n_office", "e_office", "office direction delivered"),
    ("n_faq", "n_office", "patient asks to speak to someone"),
]
for node in nodes:
    for pw in node["data"].get("responsePathways", []):
        edges.append((node["id"], pw[3]["id"], f"{pw[0]} {pw[1]} {pw[2]}"))

# Match the remaining node-data fields present in the graph Bland's own UI
# renders and executes: `active` on every node, `text` on webhooks, and an
# outcome `tag` on every end node.
for node in nodes:
    d = node["data"]
    d.setdefault("active", False)
    if node["type"] == "Webhook":
        d.setdefault("text", "")
    if node["type"] == "End Call":
        d.setdefault("tag", {"name": "outcome:" + d.get("outcome", "unknown"),
                             "color": "#455A64"})

# Layout and identity metadata. NOT cosmetic: an edge without an id and
# type "custom" is not a usable transition, so conversational nodes can never
# move. Webhook nodes route on responsePathways and globals on their label,
# which is why only those two worked before this was added.
LANES = {
    "n_identity": (0, 0), "n_ask": (0, 200), "n_reask": (-450, 600), "n_search_pm": (-900, 750), "n_search_late": (-1350, 750), "n_offer": (0, 400),
    "n_verify": (0, 620), "n_book": (0, 820),
    "n_confirm": (0, 1020), "n_negotiate": (-900, 400), "n_search": (-900, 600),
    "n_office": (900, 400), "n_faq": (900, 200),
    "e_safe_identity": (-1350, 0), "e_safe_failure": (-1350, 200),
    "e_booking_failed": (-1350, 820), "e_booked": (0, 1220),
    "e_office": (1350, 400), "e_declined": (1350, 200), "e_stop": (1350, 0),
    "e_not_me": (1350, -200), "e_existing": (900, 0), "e_timeout": (-900, 1020),
}
for node in nodes:
    x, y = LANES.get(node["id"], (0, 0))
    node.update({"x": x, "y": y, "width": 320, "height": 115,
                 "position": {"x": x, "y": y},
                 "sourcePosition": "bottom", "targetPosition": "top"})

def slug(text):
    out = "".join(c if c.isalnum() else "-" for c in text.lower())
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")[:60]

built, seen = [], set()
for s, tgt, lbl in edges:
    eid = f"edge-{s}-{tgt}-{slug(lbl)}"
    n = 2
    while eid in seen:
        eid = f"edge-{s}-{tgt}-{slug(lbl)}-{n}"; n += 1
    seen.add(eid)
    built.append({
        "id": eid,
        "data": {"label": lbl, "description": f"Route from {s} to {tgt} when: {lbl}.",
                 "isHighlighted": False},
        "type": "custom", "source": s, "target": tgt, "animated": True,
        "sourceHandle": None, "targetHandle": None,
    })

graph = {
    "nodes": nodes,
    "edges": built,
    "analysis_options": {"fields": [
        {"name": "outcome", "type": "enum",
         "values": ["booked", "declined", "no_reply", "office", "wrong_person", "stopped",
                    "identity_failed", "gateway_failed", "booking_failed"]},
        {"name": "slot_chosen", "type": "enum", "values": ["slot_1", "slot_2", "negotiated", "none"]},
        {"name": "negotiation_loop_ran", "type": "boolean"},
        {"name": "faq_answered", "type": "boolean"},
    ]},
}

# Owner requirement: every webhook carries credentials, and it is checked, not assumed.
# The value stays a stored-secret reference so the raw bearer never lives in the pathway
# definition. A dashboard edit that pastes the literal value in is a credential leak.
unauthed = []
for _n in nodes:
    if _n.get("type") != "Webhook":
        continue
    _h = (_n["data"].get("headers") or {})
    _a = _h.get("Authorization") or _h.get("authorization")
    if _a != SR:
        unauthed.append(f"{_n['id']}={_a!r}")
if unauthed:
    raise SystemExit("REFUSED: webhook nodes without the stored-secret reference: " + ", ".join(unauthed))
if any(len(v) < 40 for v in (SR,)) and "SECRET." not in SR:
    raise SystemExit("REFUSED: authorization is not a stored-secret reference")
print(f"guard_webhook_auth=all {sum(1 for n in nodes if n.get('type')=='Webhook')} webhooks carry {SR}")

out = "/tmp/claude-1000/-mnt-d-drive-repos-mott/66a30f00-0b0a-4d69-9d35-534c73631697/scratchpad/v49_graph.json"
with open(out, "w", encoding="utf-8") as fh:
    json.dump(graph, fh, indent=2, ensure_ascii=False)
print(f"nodes {len(nodes)} edges {len(edges)} -> {out}")
