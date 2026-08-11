# SPEC v94 DRAFT 2: persistent goal loop

Status: **DRAFT FOR ANKIT'S REVIEW. DO NOT BUILD, MINT, ATTACH, FLIP, OR DEPLOY.**

Base: `pathway-v92.json` (48 nodes, 125 edges). Target: 14 nodes. The live v92 graph is authoritative where prior prose and the graph disagree.

## Rulings

The following owner rulings are locked:

1. **HYBRID interpretation stays (pathway extracts, gateway re-interprets - the gateway is the goal interpreter and echoes the authoritative goal back each call so pathway and gateway cannot silently diverge)**
2. **at most ONE clarifying question per ambiguity, fail-open-to-search never fail-stay, at most one re-ask**
3. **clock times only from fresh slot data and ONLY in the offer step**
4. **both filler sentences banned**: `One moment while I check the schedule for you.` and `Let me check that for you.`
5. **corrections resolve offer-relative (offered date + 7)**
6. **no booking claims outside confirmation**
7. **mandated close copy unchanged**
8. **<=15s per answer**
9. **CVC out of scope**

## 1. SPINE

1. **UPDATE:** interpret every patient message as a patch to one persistent scheduling goal: book an eye exam, within a date range, with a time preference, in a lifecycle status.
2. **ATTEMPT:** apply the patch, repair drift through the gateway echo, then make exactly one availability call for the goal's current range.
3. **RESPOND:** offer fresh slots, or ask one targeted question when the update is ambiguous or the current range is empty.
4. **LOOP:** the next patient message updates the same goal and repeats UPDATE -> ATTEMPT -> RESPOND; the goal refines and never resets until confirmed or abandoned.
5. **GUARDS OUTSIDE THE LOOP:** booked-defer, help/office/FAQ, booking consent/confirm, close, suppression, identity failure, timeout, and existing-appointment handling interrupt or terminate the loop; none creates a second scheduling spine.

Convergence is structural. There is no scenario-specific recovery tree and no patient-waiting conflict node. Every nonterminal scheduling response has one next inbound destination: `n_goal_update`. Ambiguity state only bounds what the next iteration may ask; it does not create a place to remain.

## 2. GOAL OBJECT

The pathway stores exactly one object, `scheduling_goal_v94`. It exists after identity succeeds and remains in scope for the conversation.

| variable | type / allowed values | initial value | pathway extraction writes | gateway echo writes |
|---|---|---|---|---|
| `goal_intent` | enum: `book_exam` | `book_exam` | may reaffirm; cannot change to another product | authoritative `book_exam` |
| `goal_from` | ISO date or accepted unresolved date phrase | configured safe initial range start | candidate patch from latest message and retained context | authoritative normalized start |
| `goal_to` | ISO date or accepted unresolved date phrase | configured safe initial range end | candidate patch; omitted fields retain prior value | authoritative normalized end |
| `goal_day_part` | enum: `morning|afternoon|late|none` | `none` | candidate patch; rejection clears or replaces | authoritative band |
| `goal_time_after` | 12-hour bound or `none` | `none` | candidate patch; never patient-facing copy | authoritative normalized bound |
| `goal_status` | `unsatisfied|offered|confirmed|abandoned` | `unsatisfied` | may propose abandonment from explicit decline/STOP; never confirms | authoritative lifecycle transition subject to booking evidence |
| `goal_revision` | nonnegative integer | `0` | never | increments once for every accepted update/repair |
| `goal_clarify_count` | integer `0|1|2` | `0` | never | `1` after the targeted question; `2` after the one re-ask; never permits another question for that ambiguity |
| `goal_ambiguity_key` | string or `none` | `none` | candidate descriptor only | stable key for the unresolved decision; cleared after search proceeds |
| `last_offered_dates` | array of 0-2 ISO dates | `[]` | never | fresh offer dates only; supports offer-relative correction |
| `last_offer_token` | opaque string or `none` | `none` | never | binds offered slots to the fresh availability result |
| `selected_slot` | slot object or `none` | `none` | candidate selection only | exact member of slots bound to `last_offer_token` |

Patch semantics are mandatory: absence means retain, explicit replacement means replace, and explicit rejection means clear only the rejected constraint. A patient changing the range does not recreate the object, clear unrelated preferences, or return to intake.

Lifecycle: `unsatisfied -> offered -> confirmed` or `unsatisfied|offered -> abandoned`. A new search moves `offered -> unsatisfied` before the attempt; a successful fresh offer moves it to `offered`. Only successful booking or conservative reconciliation evidence may move it to `confirmed`. Confirmed and abandoned are terminal for scheduling.

Drift repair implements the HYBRID ruling. The pathway sends its extracted patch plus the prior goal. The gateway independently reads the latest message, merges it with the prior goal, and returns the full authoritative `goal_echo`. The pathway must replace its stored object with that echo atomically. On disagreement, the gateway echo wins, records `decision_source` and the differing fields, and either searches or returns one presentation-safe ambiguity. No pathway field may silently override the echo on the next call.

## 3. NODE MAP

### v94 nodes

| id | type | purpose |
|---|---|---|
| `n_identity` | webhook | silent identity lookup and safe entry |
| `n_appt_check` | webhook | silent existing-appointment guard |
| `n_goal_update` | default/extraction | sole inbound scheduling node; emits greeting only on revision 0, applies the one canonical extraction reference, and forwards a patch without resetting the goal |
| `n_availability` | webhook | sole goal interpreter/echo and sole availability call; exactly one current-range attempt per loop iteration |
| `n_goal_response` | default | sole response renderer: fresh offer or one targeted date/range question; all scheduling replies return to `n_goal_update` |
| `n_select` | webhook | binds a reply to a member of the fresh offer or returns a goal patch |
| `n_consent` | default | date-only booking consent; no clock time and no booking claim |
| `n_verify` | webhook | verifies selected-slot availability without patient copy |
| `n_book` | webhook | single booking write, retry 0 |
| `n_reconcile` | webhook | one conservative read after unknown write outcome |
| `n_confirm` | default | sole affirmative booking-claim owner; mandated close |
| `n_service_guard` | global/default | help, office, and FAQ modes; returns to the same goal unless terminal policy applies |
| `n_suppress` | webhook | STOP and wrong-person suppression modes |
| `e_close` | end | mode-specific identity/safe failure, office, decline, suppression, existing, timeout, defer, booked, and unknown-write terminal copy |

Only `n_goal_update -> n_availability -> n_goal_response -> n_goal_update` is the scheduling loop. Selection may either enter the guarded booking chain or produce a patch that re-enters `n_goal_update`.

### v92-to-v94 contraction

| v92 node | lands in v94 | retained responsibility |
|---|---|---|
| `n_identity` | `n_identity` | identity lookup |
| `n_ask` | `n_goal_update` | first-turn greeting and initial update |
| `n_date_conflict` | `n_goal_response` | ambiguity presentation, no conflict node |
| `n_miss_empty` | `n_goal_response` | empty-range targeted question |
| `n_miss_unread` | `e_close` | safe scheduling failure mode |
| `n_miss_thin` | `n_goal_response` | empty band handled as current-goal response |
| `n_miss_unbookable` | `n_goal_response` | lost selection returns to goal loop |
| `n_clarify` | `n_goal_response` | one bounded ambiguity response |
| `n_miss_time` | `n_goal_response` | invalid bound response without repeating a clock time |
| `n_offer`, `n_offer_2`, `n_offer_3`, `n_offer_near` | `n_goal_response` | one fresh-offer renderer |
| `n_which_intent` | `n_select` | selection versus goal change |
| `n_gate_1`, `n_gate_2` | `n_consent` | one date-only consent gate |
| `n_negotiate` | `n_goal_update` | patient update; filler removed |
| `n_search`, `n_page_2`, `n_page_3`, `n_page_near` | `n_availability` | one current-range request; progression becomes goal refinement |
| `n_verify_1`, `n_verify_2` | `n_verify` | selected-slot verification |
| `n_book_1`, `n_book_2` | `n_book` | selected-slot write |
| `n_recheck` | `n_goal_response` | lost-slot response and loop continuation |
| `n_confirm` | `n_confirm` | sole booking claim and close |
| `n_help`, `n_office`, `n_faq` | `n_service_guard` | global assistance modes and return |
| `e_safe_identity`, `e_safe_failure`, `e_booking_failed` | `e_close` | safe terminal modes; vestigial zero-inbound booking-failed id removed |
| `e_booked`, `e_office`, `e_declined` | `e_close` | terminal modes |
| `n_suppress_stop`, `n_suppress_not_me` | `n_suppress` | parameterized suppression write |
| `e_stop`, `e_not_me`, `e_existing`, `e_timeout`, `e_defer` | `e_close` | terminal modes |
| `n_appt_check` | `n_appt_check` | existing-appointment read |
| `n_reconcile_1`, `n_reconcile_2` | `n_reconcile` | one conservative reconciliation read |
| `e_booked_recovered` | `n_confirm` | recovered confirmation mode |
| `e_book_unknown` | `e_close` | unknown-write terminal without booking claim |

All 48 v92 ids appear exactly once above, including ids grouped only when they share the same target and responsibility.

## 4. TURN CONTRACT

For any patient message, evaluate this deterministic sequence:

1. **Guard.** STOP/not-me, confirmed-booking defer, existing appointment, help/office/FAQ, timeout, and explicit abandonment route outside the loop. Otherwise continue with the existing goal.
2. **Extract update once.** `n_goal_update` invokes `EXTRACT_GOAL_UPDATE_V94` against the latest patient message and conversation context. Missing fields are `retain`, not defaults.
3. **Interpret and merge.** `n_availability` sends the prior goal, pathway patch, raw latest text, offer context, and call id. The gateway independently interprets the message, merges it, repairs drift, increments revision, and echoes the entire authoritative goal.
4. **Ambiguity decision.** If the update has two materially different date/range interpretations and `goal_clarify_count=0`, the same gateway response returns two date-only candidates and no availability search. `n_goal_response` asks exactly one targeted question. If the reply is still unusable, one re-ask is allowed (`goal_clarify_count=2`); the following reply must fail open to step 5 using the best retained non-null range. There is no clarify self-loop or separate conflict node.
5. **Attempt.** Unless step 4 emitted a question, the gateway makes exactly one availability query for `goal_echo.goal_from..goal_to` with its current band/bound. It does not page through hidden scenario branches.
6. **Respond.** With slots, `n_goal_response` offers at most two fresh candidates and sets status `offered`. With an empty range, it returns nearest real alternatives when the endpoint supplies them; otherwise it asks one targeted range question and preserves the goal. It never invents a date or clock time. Unreadable infrastructure failure closes safely.
7. **Continue or book.** Any new preference returns to step 1 as a patch. A selection is accepted only if `n_select` proves membership in `last_offer_token`. Consent then runs `n_verify -> n_book -> n_reconcile` as needed. Only `n_confirm` claims success.

Empty-range and ambiguity questions are both responses inside the same loop. They do not suspend, replace, or recreate the goal. The one-re-ask bound is keyed to the current ambiguity; once fail-open search occurs, the key clears. A later genuinely different ambiguity may ask once under a new key.

## 5. EXTRACTION DEFINITION

Name: `EXTRACT_GOAL_UPDATE_V94`. It is serialized once and referenced only by `n_goal_update`.

```text
Read the full conversation and latest USER message. Return exactly:
user_verbatim: exact latest user text, with double quotes changed to single quotes.
intent_update: book_exam|abandon|retain.
from_update: an accepted future day/range phrase, unclear, clear, or retain.
to_update: an accepted future range end, unclear, clear, or retain.
day_part_update: morning|afternoon|late|none|clear|retain.
time_after_update: 12-hour time with AM/PM, none|clear|retain.
selection_update: 1|2|yes|no|unclear|none.

Rules: update only what the latest user changed. Never reset omitted fields. Rejections clear only the rejected value. Bare weekdays mean the next occurrence. Preserve week qualifiers. ASAP/next available/earliest means tomorrow. A correction 'no, the following X' resolves relative to the offered date plus 7 days, never relative to today. A question is not consent. A message that selects and changes a preference is a goal update, not booking consent. Do not calculate or emit slot times, booking status, prose, or any other field.
```

This extraction is a hint. The gateway re-interprets the message and echoes the authoritative full goal on every availability call.

## 6. AVAILABILITY FUNNEL

`n_availability` is the only `/availability` call site and the only goal-echo authority.

```json
{
  "store": "{{store}}",
  "prior_goal": "{{scheduling_goal_v94}}",
  "pathway_update": "{{goal_update_v94}}",
  "user_text": "{{lastUserMessage}}",
  "user_verbatim": "{{user_verbatim}}",
  "last_offer_token": "{{last_offer_token}}",
  "callID": "{{callID}}",
  "slot_minutes": 15
}
```

The single response contract is:

```json
{
  "ok": true,
  "goal_echo": {
    "goal_intent": "book_exam",
    "goal_from": "YYYY-MM-DD",
    "goal_to": "YYYY-MM-DD",
    "goal_day_part": "none",
    "goal_time_after": "none",
    "goal_status": "unsatisfied",
    "goal_revision": 1,
    "goal_clarify_count": 0,
    "goal_ambiguity_key": "none",
    "last_offered_dates": [],
    "last_offer_token": "opaque",
    "selected_slot": null
  },
  "pathway_read": {},
  "gateway_read": {},
  "decision_source": "agreement|gateway_repair|clarified|retained_fallback|offer_relative_correction",
  "disagreement_fields": [],
  "response_kind": "offer|ambiguity|empty_nearest|empty_question|unreadable",
  "question_kind": "none|first|reask",
  "date_candidates": [],
  "slots": [],
  "nearest_slots": [],
  "inventory_token": "opaque"
}
```

For every non-ambiguity update, gateway orchestration performs at most one underlying inventory query for the echoed current range. `slots` and `nearest_slots` contain at most two real inventory members. Nearest alternatives may be returned only by the availability service from real slot data; the pathway and language model may not synthesize them. The response must contain no patient-ready clock-time prose.

## 7. COPY INVENTORY

| owner / mode | surviving English copy or contract | ZH parity before flip |
|---|---|---|
| `n_goal_update`, first turn | Existing v92 opening beginning `Hi {{patient_first}}, this is MK2 Optical.` and ending `如需中文服务，请直接用中文回复。`, byte-identical pending parity review | [ ] same scheduling ask and opt-out meaning |
| `n_goal_response`, ambiguity | `I want to make sure I get the right day. Did you mean {{date_candidate_1_en}} or {{date_candidate_2_en}}? You can also reply with a different date.` | [ ] same candidates/order, date-only |
| `n_goal_response`, re-ask | `Please reply with one specific day or date, such as August 12. I’ll search using the best date I have after this reply.` | [ ] same bound and fail-open meaning |
| `n_goal_response`, empty question | `I don't have anything open in that range. What other day or date range works for you?` | [ ] same range meaning |
| `n_goal_response`, offer | `I have {{slot_1_day_name}} {{slot_1_start}} or {{slot_2_day_name}} {{slot_2_start}} at MK2 Optical. Reply 1 or 2 to take one, or tell me another day or time.` | [ ] same two fresh slots |
| `n_goal_response`, nearest | `I don't have anything open in that range. The nearest openings are {{slot_1_day_name}} {{slot_1_start}} or {{slot_2_day_name}} {{slot_2_start}} at MK2 Optical. Reply 1 or 2 to take one, or tell me another date range.` | [ ] same provenance and alternatives |
| `n_goal_response`, lost slot | `That opening is no longer available. What other day or date range works for you?` | [ ] no stale time |
| `n_consent` | `To confirm, you want the eye exam on {{selected_slot_day_name}} at MK2 Optical. Reply YES to book it, or NO to keep looking.` | [ ] date-only, no clock time |
| `n_confirm` | May name the confirmed date but no clock time, then exactly: `You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219` | [ ] mandated existing ZH close byte-identical |
| `n_confirm`, recovered | exactly `You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219` | [ ] existing recovery parity |
| `n_service_guard`, help | `This is MK2 Optical's appointment scheduling assistant. For help, call (212) 219-2219. Reply STOP to opt out.` | [ ] required |
| `n_service_guard`, office/FAQ | Preserve the v92 office number, coverage, and cost branches; ask whether to continue scheduling; never repeat an offer | [ ] required |
| `e_close` modes | Preserve v92 safe identity/failure, office, decline, STOP, not-me, existing, timeout, defer, booked, and unknown-write strings; mandated close remains owned by `n_confirm` | [ ] byte/semantic parity per mode |

The two filler sentences in §Rulings occur zero times. Only `n_goal_response` in `offer` or `nearest` mode may state a clock time, and every stated time must be a member of the immediately returned `slots` or `nearest_slots` under the same `inventory_token`. `n_consent`, `n_confirm`, guards, errors, questions, and terminals may not state, repeat, infer, or interpolate clock times. Booking claims are allowed only in `n_confirm`; conservative negation and uncertainty remain allowlisted in safe terminal copy.

ZH parity checklist: [ ] same route; [ ] same goal update retained; [ ] same dates/ranges; [ ] same fresh slot membership; [ ] same question/re-ask bound; [ ] same booking boundary; [ ] mandated close unchanged; [ ] no extra clock times; [ ] both banned fillers absent.

## 8. VALIDATOR PLAN

Implement `checks/check_v94_graph.py`; it must fail with the offending node, edge, or field.

1. **Shape:** exactly 14 unique nodes; all edges resolve; every v92 id appears exactly once in §3; only the ids in the v94 map exist.
2. **Goal schema:** `scheduling_goal_v94` has exactly the fields/types/lifecycle in §2; no node initializes a second goal; update semantics contain retain/replace/clear; only gateway echo writes authoritative goal fields.
3. **Loop adjacency:** scheduling adjacency is `n_goal_update -> n_availability -> n_goal_response -> n_goal_update`; booking/guard exits are explicit. No self-loop, conflict node, paging branch, or reply class without a target exists. No fail-stay exists anywhere.
4. **Attempt cardinality:** one `/availability` call site and one request schema; each ordinary update causes exactly one inventory query for the echoed range; ambiguity questions cause none until the next update.
5. **Hybrid echo:** request contains prior goal, pathway update, and raw text; response contains pathway/gateway reads, complete goal echo, disagreement fields, and decision source; persisted goal equals the echo.
6. **Extraction singleton:** exactly one `EXTRACT_GOAL_UPDATE_V94` definition exists, referenced once by `n_goal_update`; no copied extraction instructions or `extractVars` blocks exist elsewhere.
7. **Banned strings:** both filler sentences, plus normalized case/punctuation variants, occur zero times in graph text, prompts, labels, and configuration.
8. **Time containment:** clock-time regexes, literals, and slot-time placeholders occur only in `n_goal_response` offer/nearest modes. Runtime assertions prove same-turn inventory membership. No clock time appears in consent or confirmation.
9. **Clarification bound:** one first question and at most one re-ask per ambiguity key; after re-ask every reply searches with the best retained goal; `question_kind` cannot target a clarification node because none exists.
10. **Empty provenance:** nearest alternatives are service-returned members with the same inventory token; an empty response without real alternatives can only ask the targeted range question.
11. **Booking:** the sole write path is `n_select -> n_consent -> n_verify -> n_book`; retry is 0; unknown goes once to reconcile; only `n_confirm` contains affirmative booking language; confirmed/defer has no route into the loop.
12. **Copy and latency:** copy owners match §7; mandated EN/ZH close is byte-identical to v92; every visible answer has timing evidence and max is <=15.0s, with p95 reported. Missing telemetry fails.

Redproof mutations must demonstrate failure for: second goal initialization, omitted echo field, echo not persisted, second extraction block, second availability site, added paging edge, response-to-self edge, missing catch-all edge, third clarify question, invented nearest slot, stale offer time, time in consent/confirm, either filler string, booking claim outside confirm, booking retry 1, verify bypass, altered close, correction relative to today, and missing latency measurement. The validator must fail on unmodified v92 and on every mutation.

## 9. HARNESS PLAN

Port today's 33 scenarios as **goal-loop tests**, preserving patient behavior, webhook evidence, safety outcomes, and 33/33 acceptance. Replace expectations about scenario nodes with assertions on: prior goal, extracted patch, gateway echo, one attempt, response kind, persisted next goal, and terminal/guard outcome.

Add these structural suites:

| suite | required cases / proof |
|---|---|
| persistence | patient changes range three times; one object identity, revisions +1 each turn, unrelated constraints retained, exactly one search per update |
| refinement | add morning, clear morning, add clock bound, reject one date, offer-relative `following Friday`; no reset and correction equals offered date + 7 regardless of today |
| hybrid drift | pathway/gateway agree; disagree on week; disagree on band; stale pathway patch; stored-object tamper; gateway echo wins and becomes next prior goal |
| ambiguity | first question -> candidate; first question -> third date; irrelevant -> one re-ask -> valid; irrelevant twice -> fail-open search; no third question and no resident node |
| empty range | real nearest alternatives offered; no alternatives asks one targeted range question; reply refines same goal; zero invented date/time |
| offer/selection | choose either fresh member; mixed selection plus new range becomes update; stale token rejected; clock copy exactly matches same-turn inventory |
| booking | consent contains no time/claim; lost slot returns to same goal loop; success claims only in confirm; unknown write reconciles once; recovered copy has no time |
| guards | HELP/office/FAQ preserve goal and return; STOP/not-me/decline abandon; confirmed re-entry defers; existing appointment, timeout, and safe failures close correctly |
| convergence sweep | generated message for every classifier outcome; every nonterminal either advances immediately or waits after one delivered question; no fail-stay or scenario-specific node |
| copy/locale | both banned strings absent; EN/ZH route, goal, dates, membership, question bound, booking semantics, and close parity |
| latency | every visible response <=15.0s; report max and p95; missing timestamp fails |

Record per turn: goal before, extracted patch, gateway read, disagreement, full echo, inventory request count, inventory token, response kind, visible copy, chosen edge, goal after, and latency. A test passes convergence by loop invariants across turns, not by enumerating a preferred dialogue path.

## 10. MIGRATION

1. **Build:** create an unattached v94 draft with the 14-node map, singleton extraction definition, goal schema, gateway echo contract, and parameterized copy modes. Do not copy v92 scenario branches.
2. **Validate:** run schema, contraction, adjacency, singleton, banned-copy, time-containment, provenance, booking-boundary, close-copy, and redproof checks. A clean graph and every intentional mutation must behave as specified.
3. **Mint:** mint only after Ankit approves the spec and validator output. Minting creates an unattached immutable candidate; it does not attach, flip, or deploy.
4. **Harness:** run the 33 ported tests plus §9 structural suites on the unattached candidate. Any real booking write remains separately approved and synthetic.
5. **Flip:** require 33/33, all structural suites, EN/ZH parity, max <=15.0s, rollback artifact, and explicit owner approval for the exact Mott target. CVC remains out of scope.

Tonight's v94-mint work carries forward where it established node-contraction evidence, copied-string inventory, validator design, harness instrumentation, selected-slot consolidation, verify/book/reconcile safety, and presentation-safe gateway candidates. Its conflict-node convergence design does **not** survive as a node pair. It becomes `n_goal_response`'s ambiguity mode plus `goal_ambiguity_key`/`goal_clarify_count`, with every answer returning through the same goal-update loop. Paging, miss, negotiation, and conflict subgraphs do not carry forward.

## 11. OPEN QUESTIONS FOR ANKIT

| id | question | recommended default |
|---|---|---|
| OPEN-1 | Can the pathway artifact serialize a reusable extraction definition by reference? | Prove it in an unattached toy artifact. If unsupported, perform pathway extraction in the sole `n_goal_update` configuration; never duplicate it. |
| OPEN-2 | What safe initial range exists before the patient supplies any date? | Use the current v92 default range, recorded explicitly in configuration, then preserve it until updated. Do not hide a new default in prompts. |
| OPEN-3 | Should a newly empty range reset the clarify allowance? | Yes only for a new `goal_ambiguity_key`; never reset merely because a response was irrelevant. |
| OPEN-4 | Can `/availability` return real nearest alternatives in the same request without a second inventory query? | Require endpoint proof. Until proven, use the empty-range targeted question; do not make a second call or invent alternatives. |
| OPEN-5 | Does "ONLY in the offer step" intentionally remove the clock time from consent and confirmation? | Yes. Treat the ruling literally: consent and confirmation are date-only; the offered slot remains bound internally by token. |
| OPEN-6 | Is strict latency acceptance max <=15.0s or p95 <=15s? | Max <=15.0s, with p95 reported, because the ruling says every answer. |
| OPEN-7 | May ZH copy be parity-edited where current v92 wording differs semantically? | Yes, parity-only before flip; no policy or offer expansion. |

No open question authorizes CVC work, attachment, live writes, flip, or deployment.

## 12. MACHINE LINE

TARGET_NODES=14 FROM=48 SPINE=goal-loop
