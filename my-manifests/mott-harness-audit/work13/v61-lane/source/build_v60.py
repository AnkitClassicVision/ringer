#!/usr/bin/env python3
"""Mott recall pathway v57 — ambiguity and unsatisfied-time safety routing.

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
import os

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
# next-week request becomes next week..friday next week and the SERVER does the date
# arithmetic. The model is never asked to work out a calendar date, which is the failure mode
# this design avoids.
# EVERY field must always receive a value. An unfilled variable is substituted as a real
# JSON null, which drops the quotes out of the body template and makes the gateway answer
# 400 "field 'after' must be a string". Measured: the literal word none is accepted and
# ignored, so it is the sentinel for "the patient did not say". Never leave one blank.
# Two closed-vocabulary tokens, nothing more. Every field the model used to carry beyond
# these fed a gateway parameter measured to be ignored, so they added failure modes and no
# capability. Clock times and parts of the day are deliberately NOT captured: the gateway
# cannot filter on them, so capturing them only invited values into the wrong fields.
PREFERENCE_VARS = [
    ("preference_from",
     "The first day the patient wants, written in one of these forms and nothing else. A "
     "weekday on its own, such as monday or wednesday, means the next one coming up. If they "
     "used a week qualifier, ALWAYS PRESERVE it by writing the weekday followed by its full "
     "qualifier. For example, wednesday next week stays wednesday next week. If they name "
     "a weekday in texting shorthand, expand it to the full accepted weekday: mon becomes "
     "monday, tue or tues becomes tuesday, wed becomes wednesday, thu or thurs becomes "
     "thursday, and fri becomes friday. Expand clipped week qualifiers too: `tues nxt wk` and "
     "every clipped variant become tuesday next week, never a bare weekday and never shorthand. "
     "If they asked for next week without naming a day, write next week. Bare weekdays "
     "with no week qualifier stay bare. If they name "
     "a month and a day, write the month and the number, such as august 5 or aug 12, or write "
     "08/05/2026. Never write a month on its own. Never write phrases like the week after that "
     "or in two weeks, because the schedule cannot read them. Never work out a calendar date "
     "yourself: pass the patient's own wording through in one of the forms above. Never put a "
     "clock time or a part of the day here. Write the single word unclear ONLY when the "
     "patient NAMED a timeframe you cannot write in one of the forms above: the week after "
     "that, in two weeks, in about a month, a bare month name, or any week you would have to "
     "work out for yourself. If the patient named NO day and NO week at all, whether they said "
     "nothing about timing or spoke only about a part of the day such as the latest you have, "
     "put monday: they have not asked for a week, so searching the soonest one contradicts "
     "nothing they said, and the offer they get back carries its own date. This field must "
     "NEVER be left blank. The distinction that matters: unclear means they told you a "
     "timeframe you cannot render, never that they told you nothing."),
    ("day_part",
     "Exactly one of these five words: morning, afternoon, late, outside, none. Use morning if the "
     "patient said morning. Morning clock times within opening hours map to morning. Use afternoon "
     "if they said afternoon, midday, or lunchtime. Noon to 2:59pm maps to afternoon. Use late if "
     "they said after 3, after 4, 3pm or later, late afternoon, late in the day, the latest, or end "
     "of day. All of those phrases map to late, and the 3pm boundary is exact. Use outside if they "
     "asked for an exact clock time outside normal clinic hours, such as 3am or 11pm. "
     "This is a routing token only and is never sent to the scheduler. Use none "
     "if they said nothing about what part of the day suits them. Never put a "
     "date, a weekday or a clock time in this field. This field must NEVER be left blank."),
    ("preference_to",
     "The last day the patient will accept, in exactly the same forms as preference_from. If "
     "they named one day, repeat it here unchanged, INCLUDING any next week qualifier. If they "
     "used texting shorthand, expand it to the same full accepted weekday written in "
     "preference_from; never pass abbreviations such as tues, nxt or wk through verbatim. If they "
     "gave a span, put the later day. If they asked for next week in general with no day, put "
     "friday next week. If they named no day and no week at all, put friday. Bare weekdays with "
     "no week qualifier stay bare. Never put a clock time here. This field must NEVER be "
     "left blank: whenever preference_from is unclear, write unclear here too."),
]

# The clarify node asks ONLY which date the patient means, so a reply there is a bare date
# and re-extracting day_part from it would come back none. A patient who said "the latest
# you have" and was then asked for a date would be shown morning slots. A variable that is
# not in a node's extractVars keeps the value it already had, so leaving day_part out here
# is the platform's own carry-forward and needs no memory the platform does not have.
WINDOW_VARS = [v for v in PREFERENCE_VARS if v[0] != "day_part"]

OPENER_EN = (
    "Hi {{patient_first}}, this is Mott Optical. We noticed that it's been awhile since your last "
    "visit with us. This is a great time to update your lenses, explore our newest eyewear "
    "collection, and even find a new pair of sunglasses while staying on top of your eye health "
    "with a comprehensive eye exam. Many vision insurance benefits renew yearly, so don't let your "
    "benefits go unused! When would you like to come in? Just reply with a day and a time that "
    "works for you and I will check what we have. Reply STOP to opt out. " + ZH_INVITE)

# Offering happens AFTER the patient says when they want to come, so the offer message is
# short and carries only the openings found for the day they actually asked for.
# Owner decision 2026-07-26: an offer states what is available and asks them to book.
# It does not celebrate. "Great news" front-loads enthusiasm onto a time the patient has
# not agreed to yet, and it reads worst in exactly the case where the time is a near miss
# rather than a match. Warmth belongs at the confirmation, once there is something real
# to be pleased about.
OFFER_EN = ("I have {{slot_1_start}} or {{slot_2_start}} at MK2. Reply 1 or 2 to take "
            "one, or tell me another day or time.")
OFFER_ZH = ("我这里有 {{slot_1_start}} 或 {{slot_2_start}}（地点：MK2）。"
            "回复 1 或 2 预约，或告诉我们其他合适的时间。")

# The nearest-band offer. A patient who asked for late in the day on a day too thin to hold
# a late slot used to be sent to the afternoon page, whose message opens "Great news" and
# calls the times afternoon openings. That is a silent substitution: they asked for after 4
# and were shown midday as though it answered them. This line names the miss first.
NEAR_EN = ("I don't have anything that late that day. The closest I have is {{slot_1_start}} "
           "or {{slot_2_start}} at MK2. Reply 1 or 2 to take one, or tell me another day.")
NEAR_ZH = ("那天没有那么晚的时段了。最接近的是 {{slot_1_start}} 或 {{slot_2_start}}"
           "（地点：MK2）。回复 1 或 2 预约，或告诉我们其他日期。")

OPENER_ZH = (
    "您好 {{patient_first}}，这里是 Mott Optical。我们注意到您距离上次到访已经有一段时间了。"
    "现在正是更新镜片、挑选新眼镜、并通过全面眼科检查守护眼睛健康的好时机。"
    "许多视力保险福利每年都会更新，请不要浪费您的福利！"
    "您希望什么时候来诊所？请直接回复适合您的日期和时间，我来为您查询。回复 STOP 退订。")

SLOT_FIELDS = ["slot_count", "slot_1_start", "slot_1_end", "slot_1_doctor",
               "slot_2_start", "slot_2_end", "slot_2_doctor", "time_pref_relaxed",]

RESP = {
    "ok": "$.ok", "count": "$.result.count", "patient_first": "$.result.patients[0].name_first",
    "patient_id": "$.result.patients[0].patient_id", "exam_type_id": "$.result.exam_type_id",
    "slot_count": "$.result.count",
    "slot_1_start": "$.result.slots[0].start", "slot_1_end": "$.result.slots[0].end",
    "slot_1_doctor": "$.result.slots[0].doctor_id",
    "slot_2_start": "$.result.slots[1].start", "slot_2_end": "$.result.slots[1].end",
    "slot_2_doctor": "$.result.slots[1].doctor_id",
    "p2_1_start": "$.result.slots[8].start", "p2_1_end": "$.result.slots[8].end",
    "p2_1_doctor": "$.result.slots[8].doctor_id",
    "p2_2_start": "$.result.slots[9].start", "p2_2_end": "$.result.slots[9].end",
    "p2_2_doctor": "$.result.slots[9].doctor_id",
    "p3_1_start": "$.result.slots[16].start", "p3_1_end": "$.result.slots[16].end",
    "p3_1_doctor": "$.result.slots[16].doctor_id",
    "p3_2_start": "$.result.slots[17].start", "p3_2_end": "$.result.slots[17].end",
    "p3_2_doctor": "$.result.slots[17].doctor_id", "pm_1_end": "$.result.slots[8].end", "pm_2_end": "$.result.slots[9].end",
    "time_pref_relaxed": "$.result.time_pref_relaxed",
    "overlap_id": "$.result.overlapping_appt_id", "conflict_reason": "$.result.reason", "book_http_status": "$.http_status", "book_error": "$.error", "error_status": "$.status",
    "new_appt_id": "$.new_appt_id",
    # The catalog defines $.result.conflict as true when the slot COLLIDES OR IS OUTSIDE THE
    # SCHEDULE. overlapping_appt_id only ever carries the collision case, so a slot outside
    # clinic hours with nothing booked over it read as free and clear and went to the write.
    # Routed as an extra blocking signal ahead of the existing ones, never as the sole
    # positive route, so a gateway that does not populate it behaves exactly as before.
    "slot_conflict": "$.result.conflict",
    # $.status is error-only and $.http_status is transport, not outcome. The signer's own
    # success flag is the only thing the catalog permits a patient-facing confirmation on.
    "book_success": "$.success",
}



SEARCH_BODY = ('{"store":"{{store}}","from":"{{preference_from}}","to":"{{preference_to}}",'
               '"after":"none","before":"none",'
               '"time_pref":"none","slot_minutes":"15"}')


def page_map(prefix):
    """Remap a page's offsets onto slot_1_*/slot_2_* so downstream nodes are page-agnostic."""
    m = dict(RESP)
    for slot, src in (("1", prefix + "_1"), ("2", prefix + "_2")):
        for field in ("start", "end", "doctor"):
            m["slot_" + slot + "_" + field] = RESP[src + "_" + field]
    return m


PAGE2_RESP = page_map("p2")
PAGE3_RESP = page_map("p3")


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


def offer_page(nid, name, window, later_hint, extra_never="", line_en=None, line_zh=None,
               opening=None):
    """One offer node per page. It sees exactly two openings and nothing else, which is what
    stops it naming a time it cannot book.

    line_en / line_zh override the offer sentence. The nearest-band variant uses that to
    say plainly that the band the patient asked for could not be served, instead of
    presenting a substitution as good news."""
    return wait(nid, name,
         framed(
             (opening or "Exactly two openings exist as far as you are concerned: the first is "
             "{{slot_1_start}} and the second is {{slot_2_start}}. They are " + window + ". You "
             "have not been shown any other time and you do not know what else the schedule "
             "holds. Nothing is booked and nothing is held."),
             "Get this patient to take one of the two openings you have, or find out what they "
             "would rather have so the schedule can be looked at again.",
             "Send this message with the two openings filled in: \"" + (line_en or OFFER_EN) + "\" "
             "If the patient writes in Chinese, use this form instead: \"" + (line_zh or OFFER_ZH) + "\" "
             + later_hint +
             "If they want another day entirely, take the path for a different day. "
             "If they ask for a week further out than next week, or describe it only in relation "
             "to a week already discussed, such as the week after that, do NOT search and do NOT "
             "repeat the times you already gave: ask which date they would like and give an "
             "example of a form that works, such as August 12. Stay here until they name it. "
             "If they take the first opening, take the path for the first. If they take the "
             "second, take the path for the second. A bare 1 or 2, a YES to one of them, or "
             "naming one of those two times all count as taking it. If one reply both takes "
             "an opening AND asks for a different day or time, take the clarification path; "
             "that mixed reply is not consent to either choice. Ask which one the patient meant: "
             "the opening they selected, or the different day or time they requested. "
             + TIMES,
             "NEVER write any appointment time other than the two given to you above, in any "
             "message, for any reason. You have no other times. Inventing one, or repeating one "
             "from earlier in the conversation, misleads the patient about what is being booked."
             + extra_never + NO_CLAIM + NO_PRICE + LANG_OPENER))


def suppression(nid, name, reason, exit_id, exit_name, glabel):
    """A silent recorder sitting in FRONT of an opt-out exit.

    The global trigger lives here rather than on the end node, so the exit cannot be
    reached without the record being attempted. Both routes land on the same exit: a
    gateway that answers 503 must not trap the patient in a conversation they asked to
    leave, and the exit wording never claims the opt-out was saved, so an unrecorded
    STOP is still honest. Carrier-level STOP remains the actual compliance control.
    """
    node = wh(
        nid, name, "/sms-suppression",
        ('{"phone_e164":"{{recall_cell}}","reason":"' + reason
         + '","source":"sms_reply"}'),
        ["suppression_ok"],
        [["suppression_ok", "==", "true", {"id": exit_id, "name": exit_name}],
         ["suppression_ok", "!=", "true", {"id": exit_id, "name": exit_name}]],
        resp_map={"suppression_ok": "$.ok"},
    )
    node["data"].update({
        "isGlobal": True,
        "globalLabel": glabel,
        "enableGlobalAutoReturn": False,
    })
    return node


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

    # n_reask used to be the single target of six different edges: search rejected, window
    # empty, band too thin, and slot not real. One apology had to cover "we looked and there
    # is nothing", "we never managed to look", and "your part of the day is thin", so it was
    # forbidden from saying any of them and the patient could not tell what to change. The
    # arrival edge, not the prompt, now decides which of these three the patient hears.

    # Reached ONLY by slot_count == 0. Emptiness is proven here, so it may be stated.
    wait("n_miss_empty", "Window had no openings",
         framed(
             "The practice schedule was just searched for exactly what this patient asked for "
             "and it came back with no openings at all in that window. That is a real, checked "
             "answer, not a failure. Nothing is booked and nothing is being held.",
             "Get one different concrete day out of this patient so the schedule can be "
             "searched again.",
             "Tell them plainly that you do not have anything open in what they asked for, then "
             "ask for one different day. Give two examples of what always works, a weekday such "
             "as Tuesday, or a month and day such as August 5. If they have been asking for "
             "something further out than the next two weeks, ask for the month and the day. "
             "Ask for one day only.",
             "Never say a morning, an afternoon or a part of the day is empty, because only the "
             "whole window was checked. Never blame the patient for how they phrased it and "
             "never mention searching, systems, errors or anything internal. Never name a time "
             "you have not been given." + NO_CLAIM + NO_PRICE + LANG_REPLY),
         extract=PREFERENCE_VARS),

    # Reached when the search never ran or was rejected, and when the request could not be
    # rendered in a form the schedule reads. Nothing was checked, so nothing may be claimed.
    wait("n_miss_unread", "Could not search yet",
         framed(
             "Nothing has been checked for this patient. Either the request could not be put "
             "into a form the practice schedule reads, or the schedule could not be reached at "
             "all. No day and no part of any day has been looked at. The patient has no idea "
             "any of that happened. Nothing is booked and nothing is being held.",
             "Get one concrete day out of this patient so the schedule can be searched.",
             "Apologise briefly for not having something to show them yet, then ask them for "
             "one specific day. Give two examples of what always works, a weekday such as "
             "Tuesday, or a month and day such as August 5. If they have been asking for a week "
             "further out than next week, or described it only in relation to a week already "
             "discussed, ask for the month and the day. Ask for one day only.",
             "Never state or imply that any day, morning or afternoon has no openings, because "
             "nothing was checked. Never blame the patient for how they phrased it and never "
             "mention searching, systems, errors or anything internal. Never name a time you "
             "have not been given." + NO_CLAIM + NO_PRICE + LANG_REPLY),
         extract=PREFERENCE_VARS),

    # Reached when the day exists and has openings, but not at the offset the requested part
    # of the day lives at. The band is proven thin. The day is NOT proven empty.
    wait("n_miss_thin", "Part of the day is thin",
         framed(
             "This patient asked for a particular part of the day. That day does have openings, "
             "but not in the part they asked for. You have not been shown the times that day "
             "does have, so you cannot name any of them. Nothing is booked and nothing is held.",
             "Get one different concrete day out of this patient so the schedule can be "
             "searched again.",
             "Tell them you do not have anything in the part of the day they asked for on that "
             "day, then ask them for one different day. Give two examples of what always "
             "works, a weekday such as Tuesday, or a month and day such as August 5. Ask for "
             "one day only. Do NOT offer to look at another time on the same day: there is no "
             "way to move to a different part of that day from here, so offering it would set "
             "up an answer that cannot be used.",
             "Never say that day has no openings, because it does and you simply have not been "
             "shown them. Never name a time you have not been given. Never mention searching, "
             "systems, errors or anything internal."
             + NO_CLAIM + NO_PRICE + LANG_REPLY),
         extract=PREFERENCE_VARS),

    # The slot the patient agreed to was checked and came back not bookable, with no other
    # appointment sitting on it: it is outside the schedule. Availability still returns such a
    # slot, so re-running the same search hands back the identical time. Sending this class to
    # the silent re-search would offer the same unbookable time again every single round.
    # This node breaks that loop the way v54 did, by asking for a different day.
    wait("n_miss_unbookable", "That opening is not real",
         framed(
             "The opening this patient agreed to was checked and cannot be booked. Nothing is "
             "sitting on top of it; it is simply not a time the office can take. Nothing was "
             "written and this patient has no appointment. Searching that same day again would "
             "hand back the very same time, so it is not worth doing.",
             "Get one different concrete day out of this patient so the schedule can be "
             "searched somewhere it can actually book.",
             "Apologise briefly that the time turned out not to be available after all, then "
             "ask them for one different day. Give two examples of what always works, a "
             "weekday such as Tuesday, or a month and day such as August 5. Ask for one day "
             "only.",
             "Never say the appointment was booked, because it was not. Never offer that same "
             "time again and never name any time you have not been given. Never say the day "
             "has no openings, because other times that day were never checked. Never mention "
             "searching, systems, errors or anything internal."
             + NO_CLAIM + NO_PRICE + LANG_REPLY),
         extract=PREFERENCE_VARS),

    # The replacement for "when in doubt the answer is monday". That fallback made a patient
    # who said "the week after that in August" get next Monday to Friday searched, with real
    # times offered as though they matched; the date inside the slot string was the only clue
    # the window was wrong. Extraction now emits the literal `unclear` instead, and this node
    # asks rather than guesses. It runs BEFORE any offer, so no wrong times are ever shown.
    wait("n_clarify", "Ask for one concrete day",
         framed(
             "This patient said something about when they want to come, but not in a form the "
             "practice schedule can read. Nothing has been looked up and no day has been "
             "checked. The patient has no idea of any of that. Nothing is booked or held.",
             "Get one concrete day out of this patient, in a form the schedule accepts.",
             "Ask which date they would like, and give an example of a form that works, such as "
             "August 12. If they have already named a weekday, ask which week it falls in by "
             "asking for the month and the day. Ask for one day only and stay here until they "
             "name it.",
             "Never guess a day or a week on their behalf and never work out a calendar date "
             "yourself. Never state or imply that any day or part of a day is empty, because "
             "nothing has been checked. Never name a time you have not been given."
             + NO_CLAIM + NO_PRICE + LANG_REPLY),
         extract=WINDOW_VARS),

    wait("n_miss_time", "Requested clock time is unavailable",
         framed(
             "This patient asked for an exact clock time outside normal clinic hours. The "
             "schedule cannot satisfy that request. The ordinary openings returned for the day "
             "are not substitutes and must not be shown. Nothing is booked and nothing is held.",
             "Say plainly that there is nothing available at that time and get one different "
             "day from the patient.",
             "Tell them you do not have anything available at the time they requested, then ask "
             "for another day. Do not offer the unrelated openings that came back.",
             "Never name any appointment time. Never imply a different opening satisfies the "
             "request. Never say anything was booked."
             + NO_CLAIM + NO_PRICE + LANG_REPLY),
         extract=PREFERENCE_VARS),

    offer_page("n_offer", "Offered, first openings", "the soonest openings that day", "If they ask for something later in the day, a different time of day, or the latest you have, do NOT name any time: say you will look and take the path for later in the day. "),

    offer_page("n_offer_2", "Offered, afternoon", "in the afternoon", "If they ask for something later still, or the latest you have, do NOT name any time: say you will look and take the path for later in the day. "),

    offer_page("n_offer_3", "Offered, late in the day", "late in the day", "These are as late as this day goes. If they want something later, say plainly that this is the latest the office has that day and offer to look at another day. ", extra_never=" Never suggest there is anything later that day than these two."),

    # The nearest-band offer. Reached only when the patient asked for late in the day and the
    # day was too thin to hold one, so these are afternoon times being offered as the closest
    # thing rather than as a match. Same two-slot visibility rule as every other offer node.
    offer_page("n_offer_near", "Offered, closest to what they asked for", "the closest this day has to what they asked for",
               "If they want to look at a different day instead, take the path for a different day. ",
               extra_never=" Never describe these as matching what they asked for and never open with good news, because they are not what the patient asked for.",
               line_en=NEAR_EN, line_zh=NEAR_ZH,
               opening=("Exactly two openings exist as far as you are concerned: the first is "
                        "{{slot_1_start}} and the second is {{slot_2_start}}. This patient asked "
                        "for something LATE in the day and that day does not have one. These two "
                        "are the closest the day has, and they are earlier than what was asked "
                        "for. You have not been shown any other time and you do not know what "
                        "else the schedule holds. Nothing is booked and nothing is held.")),

    wait("n_which_intent", "Clarify selected opening versus different time",
         framed(
             "The patient sent one reply that both selected one of the two offered openings and "
             "asked for a different day or time. Those instructions conflict. Nothing has been "
             "written, held or confirmed.",
             "Make the patient choose which instruction they mean before any booking path can run.",
             "Ask one direct question: did they mean the opening they selected, or should you look "
             "for the different day or time they requested? Do not interpret the reply for them.",
             "Never route this mixed reply toward a booking. Never claim an appointment exists and "
             "never name any time other than the two already offered."
             + NO_CLAIM + NO_PRICE + LANG_REPLY)),

    wait("n_gate_1", "Confirm opening 1",
         framed(
             "The patient has picked the first opening. Nothing has been written yet. The very "
             "next step, if they say yes, sends this exact appointment to the booking system.",
             "Get a clear yes or no to this specific appointment before anything is written.",
             "Send this message with the time filled in: \"To confirm, your eye exam would be "
             "{{slot_1_start}} at MK2. Reply YES to book it, or NO to look at other times.\" "
             "If the patient writes in Chinese, send: \"确认一下，您的眼科检查时间为 "
             "{{slot_1_start}}（地点：MK2）。回复 YES 确认预约，或回复 NO 查看其他时间。\"",
             "NEVER write any time other than the one interpolated above. Do not restate it in "
             "another form, do not use a time from earlier in the conversation, and do not treat "
             "anything other than a clear yes as a yes. The time in your message must be the "
             "time being booked." + NO_CLAIM + NO_PRICE + LANG_REPLY)),

    wait("n_gate_2", "Confirm opening 2",
         framed(
             "The patient has picked the second opening. Nothing has been written yet. The very "
             "next step, if they say yes, sends this exact appointment to the booking system.",
             "Get a clear yes or no to this specific appointment before anything is written.",
             "Send this message with the time filled in: \"To confirm, your eye exam would be "
             "{{slot_2_start}} at MK2. Reply YES to book it, or NO to look at other times.\" "
             "If the patient writes in Chinese, send: \"确认一下，您的眼科检查时间为 "
             "{{slot_2_start}}（地点：MK2）。回复 YES 确认预约，或回复 NO 查看其他时间。\"",
             "Never add a time of your own and never treat anything other than a clear yes as a "
             "yes." + NO_CLAIM + NO_PRICE + LANG_REPLY)),


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
       SEARCH_BODY,
       ["ok"] + SLOT_FIELDS,
       # The unclear guard is FIRST. A node either waits or continues, so the call cannot be
       # gated before it fires; the request goes out carrying the sentinel, is refused, and
       # this condition catches it ahead of every other route. One wasted read is the price
       # of never showing a patient times from a week they did not ask for.
       [["preference_from", "==", "unclear", {"id": "n_clarify", "name": "Could not read the week they meant"}],
        ["ok", "!=", "true", {"id": "n_miss_unread", "name": "Search rejected or unavailable"}],
        ["day_part", "==", "outside", {"id": "n_miss_time", "name": "Requested clock time is outside clinic hours"}],
        ["slot_count", "==", "0", {"id": "n_miss_empty", "name": "Window checked and empty"}],
        ["day_part", "==", "late", {"id": "n_page_3", "name": "Asked for late in the day"}],
        ["day_part", "==", "afternoon", {"id": "n_page_2", "name": "Asked for the afternoon"}],
        ["slot_count", "==", "1", {"id": "n_offer", "name": "One opening found"}],
        ["slot_count", ">=", "2", {"id": "n_offer", "name": "Two or more found"}]]),

    # The same question asked again, with a later offset of the answer read instead. If the
    # day is too thin to hold an opening at that offset the value arrives empty and the patient
    # is asked for another day, never shown a morning they did not ask for.
    wh("n_page_2", "Afternoon openings (silent)", "/availability",
       SEARCH_BODY,
       ["ok"] + SLOT_FIELDS,
       [["ok", "!=", "true", {"id": "n_miss_unread", "name": "Search rejected or unavailable"}],
        # The day has openings, just none at this offset. Band thin, day NOT empty. Moving
        # down to the morning band needs the page_first node, which is v56 work, so this
        # states the miss honestly rather than substituting a time silently.
        ["slot_1_start", "==", "", {"id": "n_miss_thin", "name": "Nothing in the afternoon that day"}],
        ["slot_1_start", "!=", "", {"id": "n_offer_2", "name": "Afternoon openings found"}]],
       resp_map=PAGE2_RESP),

    wh("n_page_3", "Late openings (silent)", "/availability",
       SEARCH_BODY,
       ["ok"] + SLOT_FIELDS,
       [["ok", "!=", "true", {"id": "n_miss_unread", "name": "Search rejected or unavailable"}],
        # Was routed at n_page_2, whose offer node opens "Great news" and calls the times
        # afternoon openings. A patient who said "after 4" was shown midday as though it
        # answered them. Same offsets, but the offer node now names the miss first.
        ["slot_1_start", "==", "", {"id": "n_page_near", "name": "Too thin for late, offer the closest"}],
        ["slot_1_start", "!=", "", {"id": "n_offer_3", "name": "Late openings found"}]],
       resp_map=PAGE3_RESP),

    # Identical call and identical offsets to n_page_2. It exists as its own node purely so
    # the thin-late path lands on the nearest-band offer instead of the afternoon offer.
    wh("n_page_near", "Closest openings to a late request (silent)", "/availability",
       SEARCH_BODY,
       ["ok"] + SLOT_FIELDS,
       [["ok", "!=", "true", {"id": "n_miss_unread", "name": "Search rejected or unavailable"}],
        ["slot_1_start", "==", "", {"id": "n_miss_thin", "name": "Nothing in the afternoon either"}],
        ["slot_1_start", "!=", "", {"id": "n_offer_near", "name": "Closest openings found"}]],
       resp_map=PAGE2_RESP),

    # Same call, same day, read from later in the list. The gateway ignores time_pref, so
    # this is how an afternoon becomes reachable at all. If that day is too thin to have a
    # slot at this position the value comes back empty and the patient is asked for another
    # day, rather than being shown nothing or being shown a morning they did not ask for.
    wh("n_verify_1", "Verify opening 1 (silent)", "/conflict-check",
       '{"store":"{{store}}","doctor":"{{slot_1_doctor}}","start":"{{slot_1_start}}","end":"{{slot_1_end}}"}',
       ["ok", "slot_conflict", "conflict_reason"],
       # $.result.overlapping_appt_id, which every version up to v54 routed on, DOES NOT
       # EXIST. It appears in no gateway source file, in no contract test, and in no row of
       # the 350-row endpoint field catalog, whose only /conflict-check response fields are
       # $.ok, $.result.conflict -> slot_conflict, $.result.reason -> conflict_reason and
       # $.error. The gateway passes the CLI payload through untouched and the CLI documents
       # `conflict` and `reason`, nothing else. So overlap_id always arrived unfilled, and
       # since v54 demonstrably booked in production on `overlap_id == ""`, an unfilled
       # routing variable matches the empty-string test. The consequence is that v54's
       # positive route ALWAYS matched: the only block that could ever fire was the reason
       # string, and a conflict that set `conflict` without `reason` went straight to the
       # write. The authoritative flag was never read by any version of this graph.
       #
       # Ordering: both real blockers first, then two positive routes. The second positive
       # route exists because the catalog marks `conflict` conditional and no capture proves
       # it is emitted on a CLEAN slot. If it is absent, matching it against the empty string
       # books exactly as v54 did rather than deadlocking every booking forever; if it is
       # present it must be an explicit false. Strictly more blocking than v54, never less.
       [["ok", "!=", "true", safe("Conflict check unavailable")],
        ["slot_conflict", "==", "true", {"id": "n_miss_unbookable", "name": "Slot collides or is outside the schedule"}],
        ["conflict_reason", "!=", "", {"id": "n_miss_unbookable", "name": "Not a real bookable opening"}],
        ["slot_conflict", "==", "false", {"id": "n_book_1", "name": "Checked and clear"}],
        ["slot_conflict", "==", "", {"id": "n_book_1", "name": "No conflict flag returned, no blocker raised"}]]),

    wh("n_book_1", "Book opening 1 (silent)", "/sign",
       '{"verb":"appt.book","target":"{{patient_id}}","store":"{{store}}","reason":"new-booking",'
       '"params":{"doctor":"{{slot_1_doctor}}","start":"{{slot_1_start}}","end":"{{slot_1_end}}",'
       '"type":"{{exam_type_id}}"}}',
       ["book_success", "book_http_status", "book_error", "new_appt_id", "error_status"],
       # v54 routed 200/201 straight to the confirmation node and never read $.success at
       # all, so a signer reply carrying success:false under an HTTP 200 told the patient
       # they were all set for a write that never happened. The signer's own flag is now the
       # single route into n_confirm, and anything that is not an explicit true fails closed.
       [["book_error", "==", "slot_conflict", {"id": "n_recheck", "name": "Signer found a conflict"}],
        ["book_success", "==", "true", {"id": "n_confirm", "name": "Signer reported the write succeeded"}],
        ["book_success", "!=", "true", {"id": "e_booking_failed", "name": "Signer did not report success"}]]),

    wh("n_verify_2", "Verify opening 2 (silent)", "/conflict-check",
       '{"store":"{{store}}","doctor":"{{slot_2_doctor}}","start":"{{slot_2_start}}","end":"{{slot_2_end}}"}',
       ["ok", "slot_conflict", "conflict_reason"],
       [["ok", "!=", "true", safe("Conflict check unavailable")],
        ["slot_conflict", "==", "true", {"id": "n_miss_unbookable", "name": "Slot collides or is outside the schedule"}],
        ["conflict_reason", "!=", "", {"id": "n_miss_unbookable", "name": "Not a real bookable opening"}],
        ["slot_conflict", "==", "false", {"id": "n_book_2", "name": "Checked and clear"}],
        ["slot_conflict", "==", "", {"id": "n_book_2", "name": "No conflict flag returned, no blocker raised"}]]),

    wh("n_book_2", "Book opening 2 (silent)", "/sign",
       '{"verb":"appt.book","target":"{{patient_id}}","store":"{{store}}","reason":"new-booking",'
       '"params":{"doctor":"{{slot_2_doctor}}","start":"{{slot_2_start}}","end":"{{slot_2_end}}",'
       '"type":"{{exam_type_id}}"}}',
       ["book_success", "book_http_status", "book_error", "new_appt_id", "error_status"],
       [["book_error", "==", "slot_conflict", {"id": "n_recheck", "name": "Signer found a conflict"}],
        ["book_success", "==", "true", {"id": "n_confirm", "name": "Signer reported the write succeeded"}],
        ["book_success", "!=", "true", {"id": "e_booking_failed", "name": "Signer did not report success"}]]),

    # The conflict return. v54 sent every lost-slot path to n_negotiate, which carries the
    # full extraction block; the patient's most recent message on this path is their "YES",
    # which contains no timing, so the window was re-extracted from it and reset to monday.
    # A patient who confirmed Tuesday 2:00 and lost it was shown next Monday with no
    # explanation. This node has NO extractVars, so the window it searched with survives.
    wait("n_recheck", "Slot lost, looking again",
         framed(
             "The opening this patient just agreed to is no longer bookable. It was taken, or "
             "it turned out not to be a real opening. Nothing was written and this patient has "
             "no appointment. The same day and window they asked for is about to be searched "
             "again automatically, the instant you finish, without waiting for them to reply.",
             "Tell the patient that time has gone and that you are looking again, and nothing "
             "more.",
             "Send ONE short line saying the time was just taken and you are checking what else "
             "is open. Do not ask them a question and do not offer any times, because you do "
             "not have the new ones yet." + NO_LEAK,
             "Never say the appointment was booked, because it was not. Never name any time. "
             "Never ask them to repeat when they wanted to come, because that is already known."
             + NO_CLAIM + NO_PRICE + LANG_REPLY),
         skip=True),


    wait("n_confirm", "Booked",
         framed(
             "The booking system has just written a real appointment into the practice schedule for "
             "this patient and reported success. The appointment genuinely exists. This is the only "
             "point in the whole conversation where that is true.",
             "Tell the patient their appointment is booked, and make sure they do not end up with a "
             "second one.",
             "Confirm the appointment that was booked, in plain language, and name the time. This "
             "is the one place warmth belongs: opening with something like \"Great, you're all "
             "set for\" is right here and nowhere earlier, because here the appointment actually "
             "exists. If the patient then asks to change, cancel or move it, give them the office "
             "number (855) 750-6688 and explain the office will take care of it.",
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
    # Was "No appointment was booked." This node is also where a transport failure lands: the
    # signer may have committed the write before the response was lost, and every routing
    # variable arrives unfilled. Stating flatly that nothing was booked would be a guess in
    # exactly the case where the system does not know, and a patient who believed it could
    # no-show a real appointment or book a second one.
    end("e_booking_failed", "booking_failed",
        "I couldn't confirm that booking. Please call Mott Optical at (855) 750-6688 so they "
        "can check it for you."),
    # n_confirm already delivered the sole statement that the appointment exists. This end
    # node closes silently in substance instead of making a second booking claim.
    end("e_booked", "booked", "Thank you. We look forward to seeing you."),
    end("e_office", "office", "Please call Mott Optical at (855) 750-6688."),
    end("e_declined", "declined",
        "Ok, thank you for letting us know. If you need anything, call the office at (855) 750-6688.",
        glabel="The patient is not interested or declines this offer without revoking consent."),
    suppression("n_suppress_stop", "Record STOP suppression (silent)", "stop",
                "e_stop", "STOP response delivered",
                'The patient wants the texts to stop. This includes a message that is just the word STOP, STOPALL, UNSUBSCRIBE, CANCEL, END, QUIT or REMOVE on its own in any casing, and any message asking to be taken off the list, to stop texting, or to not be contacted again. Match this even when the message is a single word with no other context.'),
    end("e_stop", "stopped",
        "Understood. If you would like to be taken off our list, please call Mott Optical at "
        "(855) 750-6688 and the office can take care of it."),
    suppression("n_suppress_not_me", "Record wrong-person suppression (silent)", "complaint",
                "e_not_me", "Wrong-person response delivered",
                'The person holding this phone is not the patient. This includes a message that is just NOT ME or WRONG NUMBER, and any message saying they are not that person, they do not know that person, this is the wrong number, or asking who this is because they were not expecting to hear from an eye doctor.'),
    end("e_not_me", "wrong_person",
        "Sorry about that. If you would like to be taken off our list, please call Mott Optical at "
        "(855) 750-6688 and the office can take care of it."),
    end("e_existing", "existing_appointment",
        "Please call Mott Optical at (855) 750-6688 and the office can help with that appointment.",
        glabel="The patient already has a different appointment they want to cancel or move."),
    end("e_timeout", "no_reply", "Closing this conversation."),
]

edges = [
    ("n_ask", "n_search", "says when they want to come in"),
    ("n_ask", "e_declined", "declines at the opening"),
    ("n_ask", "e_timeout", "72-hour timeout"),
]
# The four nodes that replaced n_reask all lead back into the same search loop and all offer
# the same two ways out. Generated rather than written four times so they cannot drift apart.
for _miss in ("n_miss_empty", "n_miss_unread", "n_miss_thin", "n_miss_unbookable",
              "n_miss_time", "n_clarify"):
    edges += [
        (_miss, "n_search", "names a specific day"),
        (_miss, "e_declined", "gives up on booking"),
        (_miss, "e_timeout", "72-hour timeout"),
    ]
edges += [
    # No extraction on this node, so this edge carries the window the patient already gave.
    ("n_recheck", "n_search", "looking again with the same preference"),
    ("n_offer_near", "n_which_intent", "both selects an opening and asks for a different day or time"),
    ("n_offer_near", "n_gate_1", "takes only the first opening offered"),
    ("n_offer_near", "n_gate_2", "takes only the second opening offered"),
    ("n_offer_near", "n_negotiate", "wants a different day"),
    ("n_offer_near", "e_declined", "declines this offer"),
    ("n_offer_near", "e_timeout", "72-hour timeout"),
    ("n_offer", "n_which_intent", "both selects an opening and asks for a different day or time"),
    ("n_offer", "n_gate_1", "takes only the first opening offered"),
    ("n_offer", "n_gate_2", "takes only the second opening offered"),
    ("n_offer", "n_page_2", "wants later in the day"),
    ("n_offer_2", "n_which_intent", "both selects an opening and asks for a different day or time"),
    ("n_offer_2", "n_gate_1", "takes only the first opening offered"),
    ("n_offer_2", "n_gate_2", "takes only the second opening offered"),
    ("n_offer_2", "n_page_3", "wants later still in the day"),
    ("n_offer_2", "n_negotiate", "wants a different day"),
    ("n_offer_2", "e_declined", "declines this offer"),
    ("n_offer_2", "e_timeout", "72-hour timeout"),
    ("n_offer_3", "n_which_intent", "both selects an opening and asks for a different day or time"),
    ("n_offer_3", "n_gate_1", "takes only the first opening offered"),
    ("n_offer_3", "n_gate_2", "takes only the second opening offered"),
    ("n_offer_3", "n_negotiate", "wants a different day"),
    ("n_offer_3", "e_declined", "declines this offer"),
    ("n_offer_3", "e_timeout", "72-hour timeout"),
    ("n_which_intent", "n_gate_1", "clarifies that only the first opening was intended"),
    ("n_which_intent", "n_gate_2", "clarifies that only the second opening was intended"),
    ("n_which_intent", "n_negotiate", "clarifies that the different day or time was intended"),
    ("n_which_intent", "e_declined", "declines both choices"),
    ("n_which_intent", "e_timeout", "72-hour timeout"),
    ("n_gate_1", "n_verify_1", "confirms yes to the first opening"),
    ("n_gate_1", "n_negotiate", "says no or wants other times"),
    ("n_gate_1", "e_timeout", "72-hour timeout"),
    ("n_gate_2", "n_verify_2", "confirms yes to the second opening"),
    ("n_gate_2", "n_negotiate", "says no or wants other times"),
    ("n_gate_2", "e_timeout", "72-hour timeout"),
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
    "n_identity": (0, 0), "n_ask": (0, 200), "n_offer": (0, 400),
    "n_miss_empty": (-450, 600), "n_miss_unread": (-450, 740), "n_miss_thin": (-450, 880),
    "n_miss_time": (-450, 1020), "n_clarify": (-450, 1160),
    "n_miss_unbookable": (-450, 1300),
    "n_gate_1": (-420, 560), "n_verify_1": (-420, 700), "n_book_1": (-420, 860),
    "n_gate_2": (420, 560), "n_verify_2": (420, 700), "n_book_2": (420, 860),
    "n_recheck": (0, 780),
    "n_confirm": (0, 1020), "n_negotiate": (-900, 400), "n_search": (-900, 600), "n_page_2": (-1350, 500), "n_page_3": (-1350, 700),
    "n_page_near": (-1350, 900), "n_offer_near": (-450, 100),
    "n_offer_2": (-450, 400), "n_offer_3": (-450, 250), "n_which_intent": (0, 560),
    "n_office": (900, 400), "n_faq": (900, 200),
    "e_safe_identity": (-1350, 0), "e_safe_failure": (-1350, 200),
    "e_booking_failed": (-1350, 820), "e_booked": (0, 1220),
    "e_office": (1350, 400), "e_declined": (1350, 200), "e_stop": (1350, 0),
    "n_suppress_stop": (1125, 0), "n_suppress_not_me": (1125, -200),
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

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v60_graph.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump(graph, fh, indent=2, ensure_ascii=False)
print(f"nodes {len(nodes)} edges {len(edges)} -> {out}")
