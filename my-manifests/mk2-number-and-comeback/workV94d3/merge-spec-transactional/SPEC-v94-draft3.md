# SPEC v94 DRAFT 3: persistent transactional goal loop

Status: **DRAFT FOR ANKIT'S REVIEW. DO NOT BUILD, MINT, ATTACH, FLIP, OR DEPLOY.**

Base: `pathway-v92.json` (48 nodes, 125 edges). Target: 13 nodes. The live v92 graph is authoritative where prior prose and the graph disagree.

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

1. **UPDATE:** interpret every patient message as a patch to one persistent scheduling goal: book an eye exam, within a bounded date and time range, with a direction, in a lifecycle status.
2. **ATTEMPT:** apply the patch, repair drift through the gateway echo, then make exactly one availability call for the goal's current bounds.
3. **RESPOND:** offer fresh slots under an expiring offer contract, or ask one targeted question when the update is ambiguous or the current range is empty.
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
| `time_from` | normalized local 12-hour time or `none` | `none` | candidate lower bound; omitted means retain | authoritative normalized lower bound |
| `time_to` | normalized local 12-hour time or `none` | `none` | candidate upper bound; omitted means retain | authoritative normalized upper bound |
| `goal_day_part` | enum: `morning|afternoon|late|none` | `none` | candidate patch; rejection clears or replaces | authoritative band and derived bounds |
| `direction` | enum: `earliest|latest` | `earliest` | `last/latest slot` sets `latest`; earliest/ASAP sets `earliest` | authoritative ordering direction |
| `goal_status` | `unsatisfied|offered|confirmed|abandoned` | `unsatisfied` | may propose abandonment from explicit decline/STOP; never confirms | authoritative lifecycle transition subject to booking evidence |
| `goal_revision` | nonnegative integer | `0` | never | increments once for every accepted update/repair |
| `goal_clarify_count` | integer `0|1|2` | `0` | never | `1` after the targeted question; `2` after the one re-ask; never permits another question for that ambiguity |
| `goal_ambiguity_key` | string or `none` | `none` | candidate descriptor only | stable key for the unresolved decision; cleared after search proceeds |
| `last_offered_dates` | array of 0-2 ISO dates | `[]` | never | fresh offer dates only; supports offer-relative correction |
| `offer_id` | opaque string or `none` | `none` | never | identifies exactly one normalized two-choice offer |
| `offer_expires_at` | timestamp or `none` | `none` | never | issued-at plus TTL |
| `selected_slot` | slot object or `none` | `none` | candidate selection only | exact member bound to `offer_id` |

Patch semantics are mandatory: absence means retain, explicit replacement means replace, and explicit rejection means clear only the rejected constraint. A patient changing the range does not recreate the object, clear unrelated preferences, or return to intake.

Lifecycle: `unsatisfied -> offered -> confirmed` or `unsatisfied|offered -> abandoned`. A new search moves `offered -> unsatisfied` before the attempt; a successful fresh offer moves it to `offered`. Only successful atomic booking or conservative reconciliation evidence may move it to `confirmed`. Confirmed and abandoned are terminal for scheduling.

Drift repair implements the HYBRID ruling. The pathway sends its extracted patch plus the prior goal. The gateway independently reads the latest message, merges it with the prior goal, and returns the full authoritative `goal_echo`. The pathway must replace its stored object with that echo atomically. On disagreement, the gateway echo wins, records `decision_source` and the differing fields, and either searches or returns one presentation-safe ambiguity. No pathway field may silently override the echo on the next call.

## 3. NODE MAP

### v94 nodes

| id | type | purpose |
|---|---|---|
| `n_identity` | webhook | silent identity lookup and safe entry |
| `n_appt_check` | webhook | silent fail-safe existing-appointment guard |
| `n_goal_update` | default/extraction | sole inbound scheduling node; greeting only on revision 0; patches without reset |
| `n_availability` | webhook | sole goal interpreter/echo and bounded availability call |
| `n_goal_response` | default | sole fresh offer or targeted-question renderer; returns to `n_goal_update` |
| `n_select` | webhook | binds reply to a live `offer_id`, silently refreshes stale offers, or returns a goal patch |
| `n_consent` | default | date-only booking consent; no clock time and no booking claim |
| `n_atomic_book` | webhook | governed `/sign` conflict-check-and-book with idempotency |
| `n_reconcile` | webhook | exact attempted-offer reconciliation after unknown outcome |
| `n_confirm` | default | sole affirmative booking-claim owner; mandated close |
| `n_service_guard` | global/default | help, office, and FAQ modes; returns to same goal unless terminal |
| `n_suppress` | webhook | STOP and wrong-person suppression modes |
| `e_close` | end | identity/failure, office, decline, suppression, existing, timeout, defer, booked, and unknown-write terminal copy |

Only `n_goal_update -> n_availability -> n_goal_response -> n_goal_update` is the scheduling loop. Selection either enters the guarded transactional chain or produces a patch that re-enters `n_goal_update`.

### v92-to-v94 contraction

| v92 node | lands in v94 | retained responsibility |
|---|---|---|
| `n_identity` | `n_identity` | identity lookup |
| `n_ask` | `n_goal_update` | first-turn greeting and initial update |
| `n_date_conflict`, `n_miss_empty`, `n_miss_thin`, `n_miss_unbookable`, `n_clarify`, `n_miss_time`, `n_offer`, `n_offer_2`, `n_offer_3`, `n_offer_near`, `n_recheck` | `n_goal_response` | parameterized ambiguity, empty, offer, nearest, and lost-slot response |
| `n_miss_unread` | `e_close` | safe scheduling failure mode |
| `n_which_intent` | `n_select` | live selection versus goal change |
| `n_gate_1`, `n_gate_2` | `n_consent` | one date-only consent gate |
| `n_negotiate` | `n_goal_update` | patient update; filler removed |
| `n_search`, `n_page_2`, `n_page_3`, `n_page_near` | `n_availability` | bounded current-range request; morning/afternoon/late compensation paging removed |
| `n_verify_1`, `n_verify_2`, `n_book_1`, `n_book_2` | `n_atomic_book` | serialized check-and-book transaction |
| `n_confirm` | `n_confirm` | sole booking claim and close |
| `n_help`, `n_office`, `n_faq` | `n_service_guard` | global assistance modes and return |
| `e_safe_identity`, `e_safe_failure`, `e_booking_failed`, `e_book_unknown`, `e_booked`, `e_office`, `e_declined`, `e_stop`, `e_not_me`, `e_existing`, `e_timeout`, `e_defer` | `e_close` | parameterized safe/terminal modes |
| `n_suppress_stop`, `n_suppress_not_me` | `n_suppress` | parameterized suppression write |
| `n_appt_check` | `n_appt_check` | fail-safe existing-appointment read |
| `n_reconcile_1`, `n_reconcile_2` | `n_reconcile` | exact attempted appointment reconciliation |
| `e_booked_recovered` | `n_confirm` | recovered confirmation mode |

All 48 v92 ids appear exactly once above, including ids grouped only when they share the same target and responsibility.

## 4. TURN AND LOOP CONTRACT

1. **Guard.** STOP/not-me, confirmed-booking defer, existing appointment, help/office/FAQ, timeout, and explicit abandonment route outside the loop. **FAIL SAFE:** `n_appt_check.ok != true`, including timeout, malformed, or blank, routes to the office/defer guard and never proceeds to availability, selection, or booking.
2. **Extract update once.** `n_goal_update` invokes `EXTRACT_GOAL_UPDATE_V94`. Missing fields retain prior values.
3. **Interpret and merge.** Send prior goal, patch, raw text, offer context, and call id. Gateway echoes the full authoritative goal and increments revision.
4. **Ambiguity decision.** Ask one targeted question, allow one re-ask, then fail open to one search using the best retained non-null range. No clarify self-loop.
5. **Attempt.** Make exactly one availability query using `goal_from`, `goal_to`, `time_from`, `time_to`, and `direction`. The existing gateway `before` parameter receives `time_to`, not the hard-coded string `none`; `after` receives `time_from`. No hidden paging branches remain.
6. **Respond.** Return two normalized choices under one `offer_id`, or a bounded empty/ambiguity response. With `direction=latest`, order from the end of the day and return the true latest two available slots in the standard offer pattern. **PENDING-ANKIT-RULING; recommended default: true latest two slots.**
7. **Continue or book.** Every new preference, including one expressed while resolving an offer, is a goal patch. A choice is valid only while its offer is live. Consent routes to `n_atomic_book`; unknown outcome reconciles once; only `n_confirm` claims success.

Use one Bland native goal loop if, and only if, an unattached throwaway pathway proves its condition semantics. Cap at 8 completed UPDATE -> ATTEMPT -> RESPOND iterations per conversation. On the ninth scheduling update, exit gracefully with: `I’m sorry I couldn’t finish scheduling here. Please call MK2 Optical at (212) 219-2219 for help.` ZH must carry the same meaning. Guard interrupts and terminal states do not consume or reset the cap. The cap is a safety bound, not a patient-visible countdown.

## 5. EXTRACTION DEFINITION

Name: `EXTRACT_GOAL_UPDATE_V94`. It is serialized once and referenced only by `n_goal_update`.

```text
Read the full conversation and latest USER message. Return exactly:
user_verbatim: exact latest user text, with double quotes changed to single quotes.
intent_update: book_exam|abandon|retain.
from_update: an accepted future day/range phrase, unclear, clear, or retain.
to_update: an accepted future range end, unclear, clear, or retain.
time_from_update: 12-hour time with AM/PM, none|clear|retain.
time_to_update: 12-hour time with AM/PM, none|clear|retain.
day_part_update: morning|afternoon|late|none|clear|retain.
direction_update: earliest|latest|retain.
selection_update: 1|2|yes|no|unclear|none.

Rules: update only what the latest user changed. Never reset omitted fields. Rejections clear only the rejected value. Bare weekdays mean the next occurrence. Preserve week qualifiers. ASAP/next available/earliest means tomorrow and direction=earliest. Last/latest slot means direction=latest. A correction 'no, the following X' resolves relative to the offered date plus 7 days, never relative to today. A question is not consent. A message that selects and changes a preference is a goal update, not booking consent. Do not calculate or emit slot times, booking status, prose, or any other field.
```

This extraction is a hint. The gateway re-interprets the message and echoes the authoritative full goal on every availability call.

## 6. AVAILABILITY AND OFFER CONTRACT

`n_availability` is the only `/availability` call site and goal-echo authority. Its request includes store, prior goal, pathway update, raw text, current `offer_id`, call ID, `after=time_from`, `before=time_to`, `direction`, and `slot_minutes=15`.

The response contains `ok`, the complete `goal_echo`, pathway/gateway reads, decision source, disagreement fields, response/question kinds, inventory token, and exactly two normalized choices when `response_kind=offer|empty_nearest`. Each choice contains `choice`, `slot_id`, ISO date, normalized start, store, and inventory token. It also contains opaque `offer_id`, `offer_issued_at`, and `offer_expires_at`.

Recommended TTL is **10 minutes**. An offer becomes invalid at expiry or immediately after any accepted goal change. A stale acceptance never produces a patient-visible error: `n_select` silently re-runs the normal single availability attempt for the retained goal and renders a fresh offer or normal empty response. It never books from stale inventory. TTL value remains an open owner ruling.

## 7. ATOMIC BOOKING, RETRY, AND RECONCILIATION

`n_atomic_book` calls the governed `/sign` contract once with operation `check_and_book`, exact selected `offer_id` and slot payload, patient/store identifiers, and idempotency key `conversation_id + ':' + offer_id`. **FAIL SAFE:** blank, missing, or non-boolean `slot_conflict` never proceeds toward booking or confirmation. The gateway serializes conflict-check and create because the EMR cannot conditionally create.

The safe retry rule is now: retry the identical `/sign` request with the identical idempotency key after timeout/transport failure, up to 2 retries with bounded backoff; never mint a new key or change the payload. The gateway returns the stored first terminal result for duplicate keys and never repeats the EMR create. This unblocks B5. A definite conflict returns to the goal loop as a lost-slot response. A definite success goes to `n_confirm`. An exhausted unknown outcome goes once to `n_reconcile`.

Reconciliation must query the exact attempted appointment by `offer_id`, `slot_id`, store, patient, and attempted date/start. Patient+store appointment count is insufficient. Confirm only on a unique exact match; zero or ambiguous matches close with unknown-write copy and no booking claim.

## 8. COPY INVENTORY

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
| `e_close`, loop cap | `I’m sorry I couldn’t finish scheduling here. Please call MK2 Optical at (212) 219-2219 for help.` | [ ] same limit, apology, and call-for-help meaning |

The two filler sentences in §Rulings occur zero times. Only `n_goal_response` in `offer` or `nearest` mode may state a clock time, and every stated time must be a member of the immediately returned normalized choices under the same `offer_id` and `inventory_token`. `n_consent`, `n_confirm`, guards, errors, questions, stale refresh, and terminals may not state, repeat, infer, or interpolate clock times. Booking claims are allowed only in `n_confirm`; conservative negation and uncertainty remain allowlisted in safe terminal copy.

ZH parity checklist: [ ] same route; [ ] same goal update retained; [ ] same dates/ranges/bounds/direction; [ ] same fresh offer membership and TTL behavior; [ ] same question/re-ask/loop-cap bounds; [ ] same atomic booking boundary; [ ] mandated close unchanged; [ ] no extra clock times; [ ] both banned fillers absent.

## 9. VALIDATOR PLAN

Implement `checks/check_v94_graph.py`; fail with the offending node, edge, or field.

1. Shape: exactly 13 unique nodes; all edges resolve; all 48 source ids appear exactly once; only mapped ids exist.
2. Goal schema: exact fields/types/lifecycle, including `time_from`, `time_to`, and `direction`; one persistent object; retain/replace/clear; only gateway echo writes authoritative fields.
3. Loop: exact scheduling adjacency; proven cap 8 and graceful exit; no self-loop, conflict node, paging branch, reply without target, or fail-stay.
4. Availability: one call site; request sends both time bounds through `after`/`before` and direction; no hard-coded `before=none`; one inventory query per ordinary update.
5. Offer: response has `offer_id`, exactly two normalized choices, issued/expiry values, stated TTL rule, invalidation on goal change, and silent stale refresh.
6. Hybrid/extraction: complete echo persisted; prior goal, patch, raw text, reads, disagreement and decision source present; singleton extraction referenced once.
7. Safety/copy: banned fillers absent; clock times confined to same-offer offer/nearest output; nearest slots are real; clarification bound and close copy hold; `appt_check.ok != true` cannot schedule; blank/non-boolean `slot_conflict` cannot book.
8. Atomic booking: sole write path `n_select -> n_consent -> n_atomic_book`; governed `/sign` check-and-book, exact payload, idempotency formula, identical-key retry <=2, no verify/create split.
9. Reconciliation: one read after exhausted unknown, exact offer/slot match required; only confirm owns affirmative claim.
10. Copy/latency: all draft 2 copy owners and byte-identical mandated EN/ZH close; every visible answer <=15.0s and p95 reported; missing telemetry fails.

Redproof mutations include every draft 2 mutation plus: missing `time_to`; missing direction; hard-coded `before=none`; missing/expired offer accepted; TTL absent; goal change retaining offer; one or three choices; split verify/create; changed idempotency key on retry; retry count 3; blank conflict proceeding; appt-check error scheduling; count-only reconciliation; wrong offer/slot reconciliation; loop cap absent or ninth update continuing.

## 10. HARNESS PLAN

Port today's 33 scenarios as goal-loop tests and retain 33/33 acceptance. Record per turn: goal before, patch, gateway read/disagreement/echo, bounded inventory request and count, direction, inventory token, offer id/expiry/choices, response/copy/edge, goal after, booking key/result, reconciliation match, and latency.

Required structural suites carry forward: persistence, refinement, hybrid drift, ambiguity, empty range, offer/selection, booking, guards, convergence, copy/locale, and latency. Extend with:

| scenario | required proof |
|---|---|
| `between 1 and 3` | `time_from=1:00 PM`, `time_to=3:00 PM`; both sent; no compensation paging; offered slots inside bounds |
| stale-offer accept | expire offer and change goal variants; no stale booking, no visible error, one silent fresh search |
| atomic-book conflict | one `/sign` transaction; definite conflict creates nothing and returns to loop |
| atomic retry | transport failure then identical-key retry; at most one EMR create |
| appt-check error | `ok=false`, missing, malformed, and timeout all reach office/defer guard with zero availability/book calls |
| blank conflict | blank/missing/non-boolean conflict never reaches create or confirmation |
| exact reconciliation | only exact `offer_id`/slot match confirms; count-only, zero, duplicate, and mismatched results do not |
| last slot | phrase sets `direction=latest`; gateway returns true last two daily slots in normal offer pattern, pending ruling |
| loop cap | eight iterations continue; ninth uses graceful exit; throwaway pathway proves native condition semantics |

## 11. MIGRATION

1. **Prove loop primitive:** on a throwaway unattached pathway, prove Bland native loop condition, counter persistence, guard interruption, cap, and graceful exit. Do not build against assumed semantics.
2. **Build:** create an unattached 13-node v94 from the served 49-node state, not the stale unversioned 42-node editor base. Implement bounded availability, expiring offers, and atomic `/sign`; do not copy scenario branches.
3. **Validate (T8):** validate served source, generated candidate, schema, contraction, adjacency, copy, safety, transaction, and all redproof mutations before minting.
4. **Mint:** only after Ankit approves spec and validator output. Mint creates an unattached immutable candidate; it does not attach, flip, or deploy.
5. **Harness:** run 33 ported tests and all structural/transactional suites. Real booking writes remain separately approved and synthetic.
6. **Flip:** require 33/33, all suites, EN/ZH parity, max <=15.0s, rollback artifact, and explicit owner approval for exact Mott target. CVC remains out of scope.

Provenance wart: Bland's unversioned editor base is stale at 42 nodes versus served v94 at 49 nodes, so dashboard edits begin from stale state. The standing answer is T8 validate-then-mint: source from the served artifact, validate exact provenance and structure, then mint unattached.

## 12. DESIGN DECISIONS

Reject the proposed two-loop split (`collect-preference` plus `offer-resolve`). The boundary between those loops is exactly where tonight's live trap occurred. The single persistent goal loop subsumes revise-at-offer-time because every message is a goal patch; selection is merely a validated transition out of that loop.

Accept bounded time, expiring normalized offers, gateway-serialized atomic booking, exact reconciliation, fail-safe guards, latest-direction capability, and a proven/capped native loop. These remove compensation branches and make retries safe without weakening patient-facing safety.

## 13. OPEN QUESTIONS FOR ANKIT

| id | question | recommended default |
|---|---|---|
| OPEN-1 | Can the pathway artifact serialize a reusable extraction definition by reference? | Prove in unattached toy; otherwise configure only `n_goal_update`, never duplicate. |
| OPEN-2 | What safe initial range exists before the patient supplies any date? | Current v92 default, explicit in config, retained until updated. |
| OPEN-3 | Should a newly empty range reset clarify allowance? | Only for a new ambiguity key. |
| OPEN-4 | Can availability return real nearest alternatives without a second query? | Require endpoint proof; otherwise ask the targeted range question. |
| OPEN-5 | Does offer-only clock time remove it from consent and confirmation? | Yes; those remain date-only. |
| OPEN-6 | Is latency acceptance max or p95 <=15s? | Max <=15.0s, with p95 reported. |
| OPEN-7 | May ZH copy be parity-edited where v92 differs semantically? | Yes, parity-only before flip. |
| OPEN-8 | What offer TTL value is approved? | 10 minutes; any goal change invalidates immediately. |
| OPEN-9 | Does Bland's native loop condition behave correctly for counter, guard interrupt, and terminal exit? | Prove on throwaway unattached pathway before build depends on it. |
| OPEN-10 | Should `direction=latest` return the true latest two slots of the day? | Yes, in the standard two-choice offer pattern. **PENDING-ANKIT-RULING.** |

No open question authorizes CVC work, attachment, live writes, flip, or deployment.

## 14. MACHINE LINE

TARGET_NODES=13 FROM=48 SPINE=goal-loop LAYER=transactional
