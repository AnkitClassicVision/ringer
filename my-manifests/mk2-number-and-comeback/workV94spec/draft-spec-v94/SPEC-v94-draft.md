# SPEC v94 DRAFT: contracted hybrid funnel

Status: **DRAFT FOR ANKIT'S REVIEW. DO NOT BUILD, MINT, ATTACH, FLIP, OR DEPLOY.**

Base: `pathway-v92.json` (48 nodes, 125 edges).
Proposed target: `pathway-v94-draft.json` (35 nodes; edge count is intentionally not frozen until the approved graph is minted and mechanically inventoried).
Direction: **Contracted-Hybrid-Funnel.** The live v92 graph is authoritative where a report and the graph disagree.

---

## 0. RULINGS

The following owner rulings are copied verbatim and are not builder choices:

1. **interpretation stays HYBRID (pathway extracts AND gateway re-interprets)**
2. **week-level disagreement or detected ambiguity gets exactly ONE clarifying question offering the candidate dates, then proceeds (fail-open-to-search, never fail-stay; at most one re-ask - carry forward the v93 convergence design from /home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workCFX/conflict-node-autopsy/report.md)**
3. **clock times may NEVER be stated by any node without fresh slot data from the availability funnel (time-authority containment - enumerate the only nodes allowed to state times)**
4. **every answer <=15s so NO filler sentences anywhere ('One moment while I check the schedule for you.' and 'Let me check that for you.' are both banned strings)**
5. **corrections resolve offer-relative (offered date + 7 for 'no the following X' - as shipped in the gateway)**
6. **no booking claims outside the confirmation node**
7. **the mandated close copy is unchanged**
8. **CVC portability is OUT OF SCOPE for this draft (owner: ignore CVC for now)**

Interpretation of ruling 2 for implementation: the ordinary case gets one candidate-date question. If that answer contains no usable day/date, the v93 bounded retry may ask once more. Every answer from that retry proceeds to search. `clarification_count >= 1` also prevents the gateway from returning another disagreement for the same decision. Thus there is one logical clarify gate, no self-loop, no fail-stay, and no third question.

## 1. SPINE

The pathway has one scheduling spine: greet at `n_ask` after silent identity and existing-appointment checks; identify the patient's scheduling intent through the single canonical extraction definition `EXTRACT_SCHEDULING_INTENT_V94`, which produces exactly `user_verbatim`, `preference_from`, `day_part`, `time_after`, and `preference_to`; enter `n_availability` through its one request-body contract; let the gateway compare the pathway hint with its own reading, resolve the search band and any later/closest progression, and return either two fresh offer candidates, one miss route, or one presentation-safe ambiguity; offer only through `n_offer`; route all week-level ambiguity through the single logical `n_clarify_gate` described by T2; resolve a patient's choice through `n_select`, ask for booking consent through `n_gate`, verify and write through the single selected-slot chain `n_verify -> n_book -> n_reconcile` as needed; make the only booking claim in `n_confirm`; then close through the existing terminal outcome. In shorthand: **greet -> identify -> one extraction definition -> one availability funnel -> offer progression -> one clarify gate -> confirm -> close.**

### Deltas

| id | exact delta | source of truth |
|---|---|---|
| D1 | Replace nine copied extraction configurations with references to `EXTRACT_SCHEDULING_INTENT_V94`. | v92 inventory; owner direction |
| D2 | Replace `n_search`, `n_page_2`, `n_page_3`, `n_page_near`, and the filler-only `n_negotiate` hop with `n_availability`. | Contracted-Hybrid-Funnel evaluation; rulings 1 and 4 |
| D3 | Replace four offer nodes with `n_offer`; response metadata controls ordinary versus relaxed wording. | Contracted-Hybrid-Funnel evaluation |
| D4 | Replace slot-1/slot-2 gate, verify, book, and reconcile copies with one selected-slot chain. | owner direction; v92 webhook contracts |
| D5 | Replace `n_date_conflict` and `n_clarify` with the T2 logical gate (`n_clarify_gate`, `n_clarify_retry`). | v93 convergence design; ruling 2 |
| D6 | Remove all filler instructions and both banned strings; keep every patient response within the 15-second budget. | ruling 4 |
| D7 | Delete vestigial zero-inbound `e_booking_failed`; merge reconciliation success into `n_confirm`; retain `e_book_unknown` as the conservative unknown-write terminal. | live v92 graph; ruling 6 |

## 2. NODE CONTRACTION MAP

The target is **35 nodes from 48**. “Merged” means the old id must not exist in v94; behavior moves to the named target. “Kept” does not authorize byte-for-byte prompt carryover: shared rules, filler, extraction copies, and time authority are rewritten by this spec.

| v92 node id | v94 fate | reason / retained responsibility |
|---|---|---|
| `n_identity` | kept | sole silent start and identity lookup |
| `n_ask` | kept | sole greeting owner; references canonical extraction |
| `n_date_conflict` | merged-into-`n_clarify_gate` | presentation-safe week disagreement |
| `n_miss_empty` | kept | searched window empty |
| `n_miss_unread` | kept | availability unavailable/unreadable |
| `n_miss_thin` | kept | requested band empty |
| `n_miss_unbookable` | kept | selected slot lost/not bookable |
| `n_clarify` | merged-into-`n_clarify_gate` | unclear timeframe uses same bounded gate |
| `n_miss_time` | kept | requested clock bound outside clinic hours |
| `n_offer` | kept as the sole `n_offer` | all ordinary and relaxed offers |
| `n_offer_2` | merged-into-`n_offer` | afternoon copy selected by response metadata |
| `n_offer_3` | merged-into-`n_offer` | late copy selected by response metadata |
| `n_offer_near` | merged-into-`n_offer` | closest-match copy selected by response metadata |
| `n_which_intent` | merged-into-`n_select` | resolves choice or mixed selection/change intent |
| `n_gate_1` | merged-into-`n_gate` | selected-slot confirmation |
| `n_gate_2` | merged-into-`n_gate` | selected-slot confirmation |
| `n_negotiate` | merged-into-`n_availability` | silent direct search; filler node removed |
| `n_search` | merged-into-`n_availability` | single availability entry |
| `n_page_2` | merged-into-`n_availability` | gateway-owned band progression |
| `n_page_3` | merged-into-`n_availability` | gateway-owned band progression |
| `n_page_near` | merged-into-`n_availability` | gateway-owned relaxation |
| `n_verify_1` | merged-into-`n_verify` | verify selected slot |
| `n_book_1` | merged-into-`n_book` | write selected slot, retry 0 |
| `n_verify_2` | merged-into-`n_verify` | verify selected slot |
| `n_book_2` | merged-into-`n_book` | write selected slot, retry 0 |
| `n_recheck` | kept | exact slot-loss notice, then `n_availability` |
| `n_confirm` | kept | only booking-claim owner and mandated close |
| `n_help` | kept | global HELP/INFO response and auto-return |
| `n_office` | kept | global office handoff |
| `n_faq` | kept | global insurance/cost deferral |
| `e_safe_identity` | kept | identity-safe terminal |
| `e_safe_failure` | kept | scheduling/verification-safe terminal |
| `e_booking_failed` | deleted | zero inbound in v92; superseded by `e_book_unknown` |
| `e_booked` | kept | post-confirmation silence terminal |
| `e_office` | kept | office handoff terminal |
| `e_declined` | kept | decline terminal/global behavior retained |
| `n_suppress_stop` | kept | global suppression write |
| `e_stop` | kept | STOP terminal |
| `n_suppress_not_me` | kept | global wrong-person suppression write |
| `e_not_me` | kept | wrong-person terminal |
| `e_existing` | kept | global existing-appointment handoff |
| `e_timeout` | kept | timeout terminal |
| `e_defer` | kept | post-booking deferral terminal |
| `n_appt_check` | kept | silent thread-start appointment check |
| `n_reconcile_1` | merged-into-`n_reconcile` | one conservative write reconciliation read |
| `n_reconcile_2` | merged-into-`n_reconcile` | one conservative write reconciliation read |
| `e_booked_recovered` | merged-into-`n_confirm` | reconciliation success enters the sole booking-claim owner in recovered mode |
| `e_book_unknown` | kept | unknown-write terminal; no booking claim |

New logical ids present in the 35-node target are `n_availability`, `n_select`, `n_gate`, `n_verify`, `n_book`, `n_reconcile`, `n_clarify_gate`, and `n_clarify_retry`; each replaces one or more ids above, so none is an additive side branch.

## 3. EXTRACTION DEFINITION

Name: `EXTRACT_SCHEDULING_INTENT_V94`.

This is one canonical configuration, written once here. Any patient-waiting node that can receive scheduling language references this definition by name; it must not embed or fork any part of it. The intended reference sites are `n_ask`, `n_offer`, `n_select`, `n_gate`, `n_clarify_gate`, `n_clarify_retry`, `n_miss_empty`, `n_miss_unread`, `n_miss_thin`, `n_miss_unbookable`, and `n_miss_time`. If the pathway export format cannot reference a shared extraction object, the build is blocked for an owner ruling; copying the prompt back into multiple nodes is not compliant.

### Full canonical extraction prompt

```text
NAME: EXTRACT_SCHEDULING_INTENT_V94

ROLE
Read the full conversation and the user's most recent message. Return exactly five string variables: user_verbatim, preference_from, day_part, time_after, preference_to. Extract only scheduling intent for a new appointment. Never return null or an empty string. Do not calculate calendar dates and do not guess which weekday a date falls on.

1. user_verbatim
Copy the entire most recent USER message exactly as typed. Preserve spelling, shorthand, punctuation, and language. Do not correct, summarize, translate, interpret, or include assistant text. Replace double-quote characters with single quotes. There is always a most recent user message.

2. preference_from
Return the first future day the user wants for the new appointment. Ignore dates of existing appointments. If the user proposes or accepts a day, use it. If the user rejects a day, do not use the rejected day; retain the last offered date that was not rejected unless the user supplies a replacement. A bare weekday means the next occurrence and stays bare. Preserve and expand week qualifiers: 'tues nxt wk' becomes 'tuesday next week'. 'next week' stays 'next week'. 'this weekend' becomes 'saturday'; 'next weekend' stays 'next weekend'. A month plus day becomes a form such as 'august 5'; today, tomorrow, and day after tomorrow pass through. ASAP, next available, first opening, soonest, earliest, or whenever becomes 'tomorrow'. Return 'unclear' only when the user named a timeframe that cannot be passed in an accepted form, such as 'the week after that', 'in two weeks', 'in about a month', or a bare month. If the user named no day or week and the assistant has offered a date, use the last offered date not rejected. If neither happened, return 'monday'. For correction language of the form 'no, the following X', resolve X relative to the offered date: the working date is offered date + 7 days, preserving the user's requested weekday; do not resolve relative to today.

3. day_part
Return exactly one of morning, afternoon, late, outside, none. Morning means the user requested morning or a morning clock time within opening hours. Afternoon includes afternoon, midday, lunchtime, and noon through 2:59 PM. Late includes after 3, after 4, 3 PM or later, late afternoon, late in the day, latest, or end of day; the boundary is 3:00 PM. Outside means an exact clock time outside clinic hours. None means no part of day was requested. A rejected part of day or one mentioned only as context is not the request. A request for something later than a fresh offered pair advances from none/morning to afternoon and from afternoon to late; gateway progression remains authoritative and must compare this hint with the fresh offer context.

4. time_after
Return a 12-hour clock time with AM or PM, such as '02:00 PM', or exactly 'none'. Phrases such as after 2, not before 3, 2 o'clock or later, and anything after noon supply a bound. 'Busy until 2' means '02:00 PM'. Noon is '12:00 PM'. If the user named only morning, afternoon, or late without a clock time, return 'none'. A previously named bound remains working until the user replaces or rejects it.

5. preference_to
Return the last acceptable day in the same accepted forms as preference_from. For one day, mirror preference_from, including its week qualifier. For a span, return the later accepted day. 'Next week' with no day returns 'friday next week'. 'This weekend' returns 'sunday'; 'next weekend' returns 'sunday next week'. If preference_from is 'unclear', return 'unclear'. If no day or week was named and no offer supplies a working date, return 'friday'. Apply the same offer-relative correction rule as preference_from.

ACCEPTANCE AND REJECTION
Direct agreement, a repeated offered date/time, YES, OK, 'that works', and equivalent language accept the relevant offered value unless the same message contradicts it. Direct rejection, 'not that day/time', exclusion language, requests for alternatives, or statements that the user is busy reject the named value. A reply that both selects an opening and asks for a different day/time is mixed intent, not booking consent. Questions do not accept an offer. Use conversation context to retain the last non-rejected working preference.

OUTPUT
Return only the five named strings in the pathway's extraction result. Do not emit prose, dates calculated by the model, booking status, internal reasoning, or any sixth variable.
```

Extraction is a hint, not sole authority. `/availability` independently reads the latest patient text, compares its result with this packet, and records the decision contract in §4. That is the locked HYBRID behavior.

## 4. AVAILABILITY FUNNEL CONTRACT

### D2: single entry node and request body

`n_availability` is the only `/availability` call site. It is silent (`text: ""`, `skipUserResponse: true`) and uses the one body below for initial searches, later-in-day progression, clarified searches, miss recovery, and slot-loss rechecks.

```json
{
  "store": "{{store}}",
  "from": "{{preference_from}}",
  "to": "{{preference_to}}",
  "after": "{{time_after}}",
  "before": "none",
  "time_pref": "{{day_part}}",
  "slot_minutes": "15",
  "callID": "{{callID}}",
  "user_text": "{{lastUserMessage}}",
  "user_verbatim": "{{user_verbatim}}",
  "clarification_count": "{{clarification_count}}"
}
```

No caller owns a second body. The v92 constants collapse as parameters:

| v92 body variant | v94 parameter result | authority |
|---|---|---|
| `n_search time_pref=none` | `day_part=none` | canonical extraction compared with gateway reading |
| `n_page_2 time_pref=afternoon` | `day_part=afternoon` | same contract |
| `n_page_3 time_pref=late` | `day_part=late` | same contract |
| `n_page_near time_pref=afternoon` | no caller rewrite; gateway returns `offer_mode=closest` after its bounded relaxation | gateway funnel state |
| explicit clock bound | `after={{time_after}}`; gateway gives it precedence over a broad band, matching current semantics | canonical extraction + gateway validation |
| “later” after an offer | canonical `day_part` advances using fresh offer context; gateway independently reads the message and owns the final progression | HYBRID comparison |

The gateway returns a typed object, not the v92 positional conflict tuple:

```json
{
  "ok": true,
  "result": {
    "pathway_hint": {"from": "...", "to": "...", "day_part": "...", "after": "..."},
    "gateway_read": {"from": "...", "to": "...", "day_part": "...", "after": "..."},
    "decision": {"from": "...", "to": "...", "time_pref": "...", "after": "..."},
    "decision_source": "agreement|clarified_current_turn|gateway_read|pathway_fallback|offer_relative_correction",
    "disagreement_kind": "none|week|ambiguous",
    "clarification_count": 0,
    "clarification_options": [
      {"iso_date": "YYYY-MM-DD", "display_en": "Friday 08/07", "display_zh": "08/07 星期五"},
      {"iso_date": "YYYY-MM-DD", "display_en": "Monday 08/17", "display_zh": "08/17 星期一"}
    ],
    "route_code": "offer|clarify|empty|unreadable|outside_hours|thin",
    "offer_mode": "standard|closest",
    "slots": [
      {"start": "...", "end": "...", "doctor_id": "...", "day_name": "..."},
      {"start": "...", "end": "...", "doctor_id": "...", "day_name": "..."}
    ]
  }
}
```

The gateway owns band progression and relaxation and returns at most two offerable slots. It must not return a clock time in `clarification_options`. `n_availability` routes only by `ok`, `route_code`, and `clarification_count`; duplicated `day_part` and page-node routing disappears.

### D4: one selected-slot chain

The current graph proves Bland can send webhook bodies containing current variables and route on response fields. It does not prove Bland can assign a variable on an edge. Therefore v94 does not depend on edge assignment. `n_select` is one silent gateway selection call that submits `slot_1`, `slot_2`, `lastUserMessage`, and `callID`; the gateway returns `selection_status=selected|mixed|unclear|change_requested` plus `selected_slot_start`, `selected_slot_end`, `selected_slot_doctor`, and `selected_slot_day_name`. It may select only a member of the fresh two-slot response already offered. `mixed` or `unclear` produces one direct selection question at `n_select`; `change_requested` returns to `n_availability`; `selected` reaches `n_gate`.

`n_verify`, `n_book`, and `n_reconcile` reuse the v92 endpoint semantics with `selected_slot_*` variables. `n_book.retryAttempts` is exactly `0`; ambiguous writes go to `n_reconcile`, never retry. Reconciliation success routes to `n_confirm` with `recon_count>=1`; `n_confirm` then emits the existing slot-agnostic recovered close and must not name a time. This keeps every affirmative booking claim in the confirmation node without pretending reconciliation proved slot attribution. The gateway selection endpoint and its exact request contract are a required implementation artifact, not a claimed existing capability.

## 5. CLARIFY GATE

The single logical gate comprises `n_clarify_gate` and its bounded fallback node `n_clarify_retry`. Both reference `EXTRACT_SCHEDULING_INTENT_V94`. The first node renders only presentation-safe resolved candidates from the current `/availability` response. Raw tuple prose, internal parser fragments, and clock times are forbidden.

English exact first question:

```text
I want to make sure I get the right day. Did you mean {{clarification_option_1_display_en}} or {{clarification_option_2_display_en}}? You can also reply with a different date.
```

English exact and only re-ask:

```text
Please reply with one specific day or date, such as August 12. I’ll search using the best date I have after this reply.
```

### T2 routing rule

This table is executable routing policy, not explanatory prose. Evaluate top to bottom.

| row | input state | patient reply / gateway result | route | required state change | forbidden result |
|---:|---|---|---|---|---|
| T2.1 | `disagreement_kind=none` | any | `n_availability` searches and routes by result | retain `clarification_count` | clarify |
| T2.2 | `disagreement_kind in {week, ambiguous}` and `clarification_count=0` | gateway supplies two presentation-safe candidate dates | `n_clarify_gate` | set `clarification_count=1` when the question is emitted | raw tuple copy; clock time; search stall |
| T2.3 | at `n_clarify_gate` | either offered candidate or any usable replacement day/date | `n_availability` | use clarified current-turn extraction; retain `clarification_count=1` | return to either clarify node |
| T2.4 | at `n_clarify_gate` | no usable day/date | `n_clarify_retry` | emit the one allowed re-ask; retain `clarification_count=1` | self-loop; return to `n_clarify_gate` |
| T2.5 | at `n_clarify_retry` | any reply, usable or not | `n_availability` | search with current usable extraction or last best working date | any clarification node |
| T2.6 | `clarification_count>=1` | gateway still detects disagreement or ambiguity | `n_availability` searches | force `decision_source=clarified_current_turn` when usable, else best non-null working date | `route_code=clarify` |

Adjacency is exactly `adjacency(n_clarify_gate)={n_availability,n_clarify_retry}` and `adjacency(n_clarify_retry)={n_availability}`. If Bland has no true catch-all edge, T2.5 is represented by two exhaustive edges, usable and not usable, both targeting `n_availability`. No node in the graph may have a reply class with no outbound route.

## 6. COPY INVENTORY

All copy below is English. ZH parity is required before flip; authoring may follow this draft. “Exact” means byte-for-byte except variable substitution. “Contract” means the renderer may vary natural wording only inside the stated bounds. No row may contain either banned filler string.

| owner / outcome | surviving English patient-facing copy or contract | exact? | ZH parity before flip |
|---|---|---:|---|
| `n_ask` | `Hi {{patient_first}}, this is MK2 Optical.\n\nWe noticed that it's been awhile since your last visit with us. Staying on top of your eye health with a comprehensive eye exam is important.\n\nMany vision insurance benefits renew yearly, so don't let your benefits go unused!\n\nWhen would you like to come in? Just reply with a day and a time that works for you and I will check what we have. Reply STOP to opt out.\n\n如需中文服务，请直接用中文回复。` | exact | [ ] Existing ZH opening reviewed for semantic parity |
| `n_clarify_gate` | `I want to make sure I get the right day. Did you mean {{clarification_option_1_display_en}} or {{clarification_option_2_display_en}}? You can also reply with a different date.` | exact | [ ] Same dates/order; no internal prose |
| `n_clarify_retry` | `Please reply with one specific day or date, such as August 12. I’ll search using the best date I have after this reply.` | exact | [ ] Required |
| `n_miss_empty` | `I don't have anything open for that day. What other day works for you, such as Tuesday or August 5?` | exact | [ ] Required |
| `n_miss_unread` | `I couldn't check that date. Please reply with one specific day, such as Tuesday or August 5.` | exact | [ ] Required |
| `n_miss_thin` | `I don't have anything in that part of the day. What other day works for you, such as Tuesday or August 5?` | exact | [ ] Required |
| `n_miss_unbookable` | `Sorry, that time is no longer available. What other day works for you, such as Tuesday or August 5?` | exact | [ ] Required |
| `n_miss_time` | `I don't have anything available at that time. What other day works for you?` | exact | [ ] Required |
| `n_offer`, standard | `I have {{slot_1_day_name}} {{slot_1_start}} or {{slot_2_day_name}} {{slot_2_start}} at MK2 Optical. Reply 1 or 2 to take one, or tell me another day or time.` | exact | [ ] Existing ZH offer reviewed |
| `n_offer`, closest | `I don't have anything open in that part of the day. The closest I have is {{slot_1_day_name}} {{slot_1_start}} or {{slot_2_day_name}} {{slot_2_start}} at MK2 Optical. Reply 1 or 2 to take one, or tell me another day.` | exact | [ ] Existing ZH offer corrected to band-agnostic parity |
| `n_select`, mixed/unclear | `Did you mean the opening you selected, or should I look for the different day or time you requested?` | exact | [ ] Required |
| `n_gate` | `To confirm, your eye exam would be {{selected_slot_day_name}} {{selected_slot_start}} at MK2 Optical. Reply YES to book it, or NO to look at other times.` | exact | [ ] Existing ZH gate adapted to selected slot |
| `n_recheck` | `That time was just taken. I’m checking what else is open.` Then immediately enter `n_availability`; do not wait. | exact | [ ] Required |
| `n_confirm` | Name only `selected_slot_day_name` and `selected_slot_start` from the verified/booked selection, then end exactly: `You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219` | close exact | [ ] Existing mandated ZH close unchanged |
| `n_help` | `This is MK2 Optical's appointment scheduling assistant. For help, call (212) 219-2219. Reply STOP to opt out.` | exact | [ ] Required |
| `n_office` | Give `(212) 219-2219` for the outside-booking request, then ask whether the patient would like to continue scheduling. Do not name prior openings unless they came from fresh funnel data in this turn. | contract | [ ] Required |
| `n_faq` | Coverage: `Vision insurance typically has an allowance with co-pays. For details, call MK2 Optical at (212) 219-2219.` Cost: `What you pay depends on your benefits. The office can help at (212) 219-2219.` Then ask whether to continue scheduling. | exact branches | [ ] Required |
| `e_safe_identity` | `I couldn't safely continue this scheduling request. Please call MK2 Optical at (212) 219-2219.` | exact | [ ] Required |
| `e_safe_failure` | `I couldn't access scheduling right now and no appointment was booked. Please call MK2 Optical at (212) 219-2219.` | exact | [ ] Required |
| `e_booked` | `Thank you. We look forward to seeing you.` | exact | [ ] Required |
| `e_office` | `Please call MK2 Optical at (212) 219-2219.` | exact | [ ] Required |
| `e_declined` | `Ok, thank you for letting us know. If you need anything, call the office at (212) 219-2219.` | exact | [ ] Required |
| `e_stop` | `Understood. If you would like to be taken off our list, please call MK2 Optical at (212) 219-2219 and the office can take care of it.` | exact | [ ] Required |
| `e_not_me` | `Sorry about that. If you would like to be taken off our list, please call MK2 Optical at (212) 219-2219 and the office can take care of it.` | exact | [ ] Required |
| `e_existing` | `Please call MK2 Optical at (212) 219-2219 and the office can help with that appointment.` | exact | [ ] Required |
| `e_timeout` | `Closing this conversation.` | exact | [ ] Required |
| `e_defer` | `For that you'll have to contact the MK2 Optical office at (212) 219-2219` | exact | [ ] Required |
| `n_confirm`, recovered mode | `You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219` and no clock time | exact | [ ] Existing mandated ZH recovery parity checked |
| `e_book_unknown` | `I wasn't able to confirm whether that booking went through. The MK2 Optical office will double-check it and reach out to you. If you'd like, you can also call them at (212) 219-2219.` | exact | [ ] Required |

### Time-authority containment

The only nodes allowed to state a clock time are:

1. `n_offer`, using only `slot_1_start` and `slot_2_start` from the immediately preceding successful `n_availability` response in the same turn;
2. `n_gate`, using only `selected_slot_start` returned by `n_select` and proven to be a member of that fresh offer;
3. `n_confirm`, using only the selected slot just verified and successfully written by `n_book`;
4. `n_confirm` in recovered mode may not state a clock time because v92 reconciliation proves existence/count, not slot attribution.

No other node may render a clock-time pattern, repeat a patient's clock time, repeat a stale offer, or infer a time from conversation memory. Candidate-date clarification is date-only and is not authority to state a clock time.

## 7. VALIDATOR PLAN

Implement `checks/check_v94_graph.py`. It must print a specific failure for every assertion. `exit 0`, `true`, string presence without ownership, or an unexecuted branch is not proof.

### Structure and contraction assertions

1. Node count is exactly 35; all ids are unique; every edge source and target resolves.
2. Every v92 node appears exactly once in the §2 classification, and the graph contains no id whose fate is merged or deleted.
3. The only availability URL call site is `n_availability`; the only offer prompt owner is `n_offer`; the only verify, booking-write, and reconcile ids are `n_verify`, `n_book`, and `n_reconcile`.
4. `e_booking_failed`, `e_booked_recovered`, `n_page_2`, `n_page_3`, `n_page_near`, `n_offer_2`, `n_offer_3`, `n_offer_near`, `n_gate_1`, `n_gate_2`, `n_verify_1`, `n_verify_2`, `n_book_1`, `n_book_2`, `n_reconcile_1`, `n_reconcile_2`, and `n_negotiate` are absent.
5. `n_identity` remains the sole start. `n_ask` is the sole recall greeting owner. `n_identity` and `n_appt_check` are silent.
6. Global status, labels, auto-return behavior, and suppression endpoints for `n_help`, `n_office`, `n_faq`, `e_declined`, `n_suppress_stop`, `n_suppress_not_me`, and `e_existing` remain present and keep post-booking exclusions where v92 has them.

### Extraction and funnel assertions

7. Exactly one serialized canonical extraction definition named `EXTRACT_SCHEDULING_INTENT_V94` exists; it defines exactly the five variables in §3. Every permitted extraction site references it by name. No node embeds a copied extraction prompt.
8. `n_availability.body` parses as JSON and is byte-identical to §4, including `callID`, both raw-text carriers, and `clarification_count`. No other `/availability` body exists.
9. The response contract exposes `pathway_hint`, `gateway_read`, `decision`, `decision_source`, `disagreement_kind`, `clarification_count`, presentation-safe `clarification_options`, `route_code`, `offer_mode`, and exactly two candidate slot objects.
10. No JSONPath or prompt reads positional `date_conflict` tuple indexes. Clarification copy reads only `clarification_option_*_display_en|zh`.
11. Offer-relative correction fixtures assert offered date + 7 for `no, the following X`; today/current date must not affect the result.

### Adjacency and convergence assertions

12. Every non-terminal node has a complete outbound classification or an explicitly evidenced global auto-return. There is **no fail-stay anywhere**: no reply class may leave a patient-waiting node resident because no edge matched.
13. No self-loop exists. `adjacency(n_clarify_gate)` is exactly `{n_availability,n_clarify_retry}`; `adjacency(n_clarify_retry)` is exactly `{n_availability}`.
14. T2.1-T2.6 are each represented by a response pathway/edge pair. `clarification_count>=1` can never target either clarify node.
15. `n_offer` routes selection/mixed intent to `n_select`, new preference to `n_availability`, explicit decline to `e_declined`, and timeout to `e_timeout`.
16. The only write path is `n_select -> n_gate -> n_verify -> n_book`; `n_book` routes slot conflict to `n_recheck`, success to `n_confirm`, and unknown result to `n_reconcile`. `n_reconcile` routes only to `n_confirm` in recovered mode or `e_book_unknown`.
17. `n_book.retryAttempts == 0`. No node whose body contains `"verb":"appt.book"` may have a nonzero retry.
18. No path from `n_confirm`, `e_defer`, or `e_booked` returns to availability, offer, selection, verification, or booking.

### Copy, booking-claim, and latency assertions

19. The exact strings `One moment while I check the schedule for you.` and `Let me check that for you.` occur zero times in the full serialized graph, case-sensitive. Their normalized case-insensitive forms also occur zero times.
20. No prompt instructs filler, waiting copy, “hold on,” or an acknowledgement-only message before a webhook result. `n_negotiate` is absent.
21. The static copy inventory in §6 matches graph copy owners exactly. The mandated English and Chinese close strings in `n_confirm` are byte-identical to v92.
22. Booking-claim terms `booked|scheduled|held|reserved|confirmed|all set` in affirmative patient-facing use are owned only by `n_confirm`. Conservative negations such as `no appointment was booked` and uncertainty text in `e_book_unknown` are allowed by an explicit allowlist. No terminal node may claim a booking.
23. Clock-time regex `(?i)\b(?:0?[1-9]|1[0-2]):[0-5][0-9]\s*(?:am|pm)\b` and slot placeholders may appear in patient-facing prompt/copy only in `n_offer`, `n_gate`, and `n_confirm`. Every such placeholder has the provenance relation in §6. Recovered-mode `n_confirm` contains neither.
24. No non-offer node prompt contains a literal clock time or instruction to repeat/name the patient's time. Validator scans prompts, texts, labels, and global labels separately and names the offending owner.
25. Every patient-visible turn is instrumented for response latency; draft acceptance is 100% at or below 15.0 seconds and p95 is reported. A missing measurement is inconclusive, not pass.
26. English copy has a corresponding reviewed ZH artifact/checklist row before flip. Missing parity blocks flip, not draft review.

### Redproof mutations

Each mutation must be observed failing with the named assertion:

| id | mutation | must trip |
|---|---|---|
| R1 | restore `n_page_2` | 1, 3, 4 |
| R2 | add a second `/availability` body | 3, 8 |
| R3 | copy the extraction prompt into `n_offer` | 7 |
| R4 | remove `user_verbatim` from the body | 8 |
| R5 | return raw tuple field `[3]` to clarify copy | 10 |
| R6 | add a self-loop to `n_clarify_retry` | 12-14 |
| R7 | remove the catch-all path from `n_clarify_retry` | 12-14 |
| R8 | route `clarification_count=1` back to clarify | 14 |
| R9 | restore either banned filler sentence | 19 |
| R10 | place `{{slot_1_start}}` in `n_office` | 23, 24 |
| R11 | add an affirmative booking claim to `n_gate` | 22 |
| R12 | set `n_book.retryAttempts=1` | 17 |
| R13 | bypass `n_verify` | 16 |
| R14 | change the mandated close by one character | 21 |
| R15 | make correction relative to today instead of offered date | 11 |
| R16 | remove one v92 node from the contraction classification | 2 |
| R17 | omit one latency measurement | 25 |

The clean draft graph must pass. The validator must fail on unmodified `pathway-v92.json` and on every R1-R17 mutation. A validator that passes the base graph or an intended defect is not a validator.

## 8. HARNESS PLAN

Run only against an unattached v94 draft after Ankit approves this spec and the graph is built. No live patient, attachment, flip, or deployment is authorized here.

### Parity suite

1. Port today's 33 scenarios without deleting, weakening, or silently reclassifying any expectation. Required: **33/33 pass**. Where node ids contracted, update expected ids to the §2 target while preserving patient behavior, webhook evidence, and terminal outcome.
2. Keep the existing real-write Phase 2 separately gated: one synthetic booking round trip, post-booking deferral, and booked re-entry. No write run occurs from this draft.
3. Record per turn: visited node ids, selected edge, webhook request/response envelope with secrets removed, patient-visible copy, fresh slot inventory id, and latency.

### New v94 scenarios

| id | scenario | required evidence |
|---|---|---|
| H34 | pathway and gateway agree on day/week | one `n_availability` call, no clarify, fresh offer |
| H35 | week disagreement | one clean candidate-date question; answer chooses candidate; exactly one subsequent search; no repeated clarify |
| H36 | ambiguity -> replacement third date | replacement date reaches one search and offer; candidate choice is not required |
| H37 | ambiguity -> irrelevant -> valid retry | exactly two total clarify messages (initial plus one re-ask), then search; neither clarify node revisited |
| H38 | ambiguity -> irrelevant -> irrelevant retry | fail-open search with best non-null working date; no third question; no fail-stay |
| H39 | gateway attempts a second conflict after `clarification_count=1` | forced search with `decision_source=clarified_current_turn|pathway_fallback`; never clarify |
| H40 | `no, the following Friday` after a dated offer | resolved search date is offered date + 7; test with system date before and after the offered date |
| H41 | initial none-band search | one request body, `time_pref=none`, standard offer |
| H42 | afternoon request | same body, `time_pref=afternoon`, only fresh matching slots offered |
| H43 | late request | same body, `time_pref=late`, only fresh matching slots offered |
| H44 | late/afternoon band empty | gateway relaxation in same funnel call, `offer_mode=closest`, band-agnostic closest copy |
| H45 | “later” after standard offer | one new `n_availability` call, strictly later real inventory when fixture provides it; no filler message |
| H46 | choose slot 1 | `n_select` returns member 1; single gate/verify/book chain; confirmation names selected slot |
| H47 | choose slot 2 | same nodes as H46; selected fields equal member 2; no slot-2 branch ids exist |
| H48 | mixed “2, but do you have Tuesday?” | no consent; one direct intent question or change route; no write |
| H49 | selected slot lost before verify/write | `n_verify`/signer conflict reaches `n_recheck`, then one availability call; no booking claim |
| H50 | ambiguous write outcome | no retry; one reconcile read; recovered `n_confirm` mode or unknown terminal chosen conservatively |
| H51 | stale slot variables present on a non-offer turn | no clock-time pattern in output |
| H52 | HELP/office/FAQ during stale offer context | no clock time unless a fresh availability response occurred in that same turn |
| H53 | both banned strings, case and punctuation variants | zero occurrence in all output and serialized prompt text |
| H54 | latency envelope | every patient answer <=15.0s; report max and p95; missing timestamps fail |
| H55 | greeting cardinality | one `n_ask` message per inbound start event; silent identity and appointment check |
| H56 | no fail-stay sweep | generated representative reply for every outgoing classifier class; every nonterminal advances or validly waits after a delivered question |
| H57 | ZH parity sweep | same routes, dates, slot membership, booking boundaries, and close semantics as EN |

Fresh-slot membership is relational: every clock time stated by `n_offer` must equal one of that turn's returned candidates; `n_gate` and `n_confirm` must equal the `selected_slot_start` produced from that same candidate set. An invented, stale, reformatted, or third time fails even if it looks plausible.

## 9. OPEN QUESTIONS FOR ANKIT

These are not delegated to the builder. Recommended defaults preserve the locked rulings and minimize unproven behavior.

| id | genuinely open decision | recommended default | if wrong |
|---|---|---|---|
| OPEN-1 | Does the pathway/export tooling actually support one reusable extraction definition by reference? The v92 graph proves only copied `extractVars`, not shared config references. | **Block build until proven in an unattached toy graph.** If unsupported, move the canonical extraction execution behind one silent gateway call rather than restoring nine copies. | A fake reference could leave variables unset; copying would violate the contraction goal. |
| OPEN-2 | Approve a gateway selection operation that receives both fresh candidates and the patient reply, then returns one selected slot? This is how the spec removes parallel slot branches without assuming Bland edge assignment. | **Approve the gateway selection contract**, with strict candidate membership and no booking side effect. | A selection error could verify/book the wrong candidate; membership and confirmation gates contain it. |
| OPEN-3 | Should the bounded second question from v93 remain when the first clarification answer is irrelevant? | **Keep it.** It is the stated “at most one re-ask”; after it, always search. | Removing it is faster but can search on a weak fallback after one ignored reply. |
| OPEN-5 | The owner mandated every answer <=15s. Is acceptance max <=15.0s, or only p95 <=15s? | **Use max <=15.0s and report p95.** | A strict maximum may block flip for one infrastructure outlier, but it matches “every answer.” |
| OPEN-6 | The v92 opening has an English/Chinese semantic mismatch. May ZH authoring update it during v94? | **Yes, parity-only copy review before flip; no new offer or policy.** | Leaving it unchanged preserves a known mismatch. |

No question above authorizes CVC work. CVC remains out of scope.

## 10. MACHINE LINE

TARGET_NODES=35 FROM=48
