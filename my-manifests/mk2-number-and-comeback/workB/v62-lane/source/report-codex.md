# v62 engineering design review

CANARY: blue paperclip

## 1. Change list

The safest v62 shape adds one fixed-copy `End Call` node, `e_postbook_deferral`, and never sends a known-booked patient through the generative pre-booking handoff nodes. Default nodes do not contain fixed patient-visible text, so for those nodes the quoted v61 text below is the actual prompt language that controls generated copy, not a claim that every patient saw the same sentence.

| Node | Current v61 patient-visible line or controlling copy | Exact v62 change | Routing and rule effects |
|---|---|---|---|
| `n_confirm` | Dynamic confirmation; prompt says, `If the patient then asks to change, cancel or move it, give them the office number (855) 750-6688 and explain the office will take care of it.` | Replace that sentence with: `If the patient makes any further request after confirmation, reply exactly: "For that you'll have to contact the MK2 Optical office at (212) 219-2219".` | Replace `n_confirm -> n_office` with `n_confirm -> e_postbook_deferral` for **any further patient request**, not only change/cancel/move. Preserve the sole positive booking claim and named time here. Preserve language switching and `NO_LEAK`; do not append `NO_CLAIM` because this is the one node allowed to confirm. For Chinese input, require a faithful Chinese equivalent with the same number, so the English-verbatim rule applies to English replies.
| `n_office` | Dynamic; `Give the office number (855) 750-6688 for what they asked about.` | Same prompt with `(212) 219-2219`. | No routing change. Keep answer-then-steer-back behavior, `NO_CLAIM`, `NO_LEAK`, and language switching. It must be unreachable from post-booking state.
| `n_faq` | Dynamic; `If they say they want to speak to someone, give them the office number (855) 750-6688.` | Same prompt with `(212) 219-2219`. | No routing change. Keep coverage/cost deferral, steer-back, `NO_CLAIM`, `NO_PRICE`, `NO_LEAK`, and language switching.
| `e_safe_identity` | `I couldn't safely continue this scheduling request. Please call Mott Optical at (855) 750-6688.` | `I couldn't safely continue this scheduling request. Please call Mott Optical at (212) 219-2219.` | Copy only.
| `e_safe_failure` | `I couldn't access scheduling right now and no appointment was booked. Please call Mott Optical at (855) 750-6688.` | `I couldn't access scheduling right now and no appointment was booked. Please call Mott Optical at (212) 219-2219.` | Copy only. This negative statement remains consistent with `NO_CLAIM` only where identity lookup failed before a booking attempt.
| `e_booking_failed` | `I couldn't confirm that booking. Please call Mott Optical at (855) 750-6688 so they can check it for you.` | `I couldn't confirm that booking. Please call Mott Optical at (212) 219-2219 so they can check it for you.` | Copy only. Keep the uncertainty wording; transport failure may follow a committed write.
| `e_office` | `Please call Mott Optical at (855) 750-6688.` | `Please call Mott Optical at (212) 219-2219.` | Copy only.
| `e_declined` | `Ok, thank you for letting us know. If you need anything, call the office at (855) 750-6688.` | `Ok, thank you for letting us know. If you need anything, call the office at (212) 219-2219.` | Copy only; do not turn a question into a decline.
| `e_stop` | `Understood. If you would like to be taken off our list, please call Mott Optical at (855) 750-6688 and the office can take care of it.` | `Understood. If you would like to be taken off our list, please call Mott Optical at (212) 219-2219 and the office can take care of it.` | Copy only. Suppression webhook and route must remain unchanged; do not claim opt-out completion.
| `e_not_me` | `Sorry about that. If you would like to be taken off our list, please call Mott Optical at (855) 750-6688 and the office can take care of it.` | `Sorry about that. If you would like to be taken off our list, please call Mott Optical at (212) 219-2219 and the office can take care of it.` | Copy only. Wrong-person suppression and non-disclosure remain unchanged.
| `e_existing` | `Please call Mott Optical at (855) 750-6688 and the office can help with that appointment.` | `Please call Mott Optical at (212) 219-2219 and the office can help with that appointment.` | Copy only; this is a pre-existing-appointment outcome, not proof that this pathway booked it.
| `e_booked` | `Thank you. We look forward to seeing you.` | `Thank you. We look forward to seeing you. You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219` | Fixed text must **end** with the mandated sentence exactly. This is currently a second positive booking claim (`You're all set`), so the existing gate's `n_confirm` confirmation monopoly must be revised narrowly: allow this exact mandated suffix only at `e_booked`, and prohibit all other positive booking claims there. `NO_LEAK` is naturally satisfied by fixed copy.
| `n_identity` | Silent `/patient-search`; maps only `ok`, `count`, `patient_first`, `patient_id`, `exam_type_id`; `count == 1` routes to `n_ask`. | Map a new boolean such as `campaign_booking_complete`; add a higher-priority `campaign_booking_complete == true -> e_postbook_deferral` pathway. | The gateway value must mean a successful booking by this recall campaign/patient binding, not merely any appointment. Evaluate it before `count == 1`; malformed/missing values must not be treated as true. Existing identity/safe-failure routes remain. No patient-visible copy and no internal value may leak.
| **new** `e_postbook_deferral` | None. | Exact fixed English text: `For that you'll have to contact the MK2 Optical office at (212) 219-2219` | Terminal post-booking outcome. It has no path to search, verify, book, `n_office`, or `n_faq`. If bilingual output is mandatory, a fixed English End Call cannot switch languages; use a dedicated post-booking Default node with a strict language rule followed by a silent/substantively empty end, or paired deterministic language terminals if Bland exposes a trustworthy language value. That mechanics detail is unknown from these files and must be tested. Preserve `NO_LEAK`.

The build source must generate all of the above; editing JSON alone would drift on regeneration.

## 2. Come-back design

Known mechanics: outbound `/v1/sms/send` starts with `new_conversation: true` and a `start_node_id`; `n_identity` is `isStart: true`; End Call sends a final text and closes. What an inbound SMS does after End Call is explicitly **unmeasured**.

Run these production-like Bland probes on a test number and a non-production gateway fixture before release:

1. Complete a booking, observe `n_confirm` and `e_booked`, then reply in the same SMS thread with an office question. Record conversation ID, first resumed node, webhook calls, emitted text, and whether any search/verify/book endpoint is called.
2. Repeat after a delay and after Bland considers the conversation finished. Repeat once with a Chinese reply. Confirm whether inbound resumes a closed execution, creates a conversation, or does nothing.
3. Send two replies after close. Confirm both defer and neither can book again. Also probe `STOP` and wrong-person language after booking to establish whether platform-level/global suppression routing outranks the booked deferral; safety suppression should win.

Behavior matrix:

| Observed Bland behavior | v62 result |
|---|---|
| Re-enters at `isStart`/`n_identity` | Gateway flag routes directly to `e_postbook_deferral`; passes if no booking endpoints run. |
| Creates a new conversation that starts at `n_identity` | Same safe result, provided request data still supplies the binding fields. Whether inbound populates those fields is unknown and part of the probe. Missing binding fails closed to existing safe identity handling, but does not meet the exact-deferral requirement. |
| Resumes the prior active node before End Call | `n_confirm` routes any request to `e_postbook_deferral`. |
| Remains dead after End Call | No reply and no double-booking: safe, but the comeback requirement fails. Bland configuration/support must provide an inbound restart hook; neither a gateway flag nor graph-only routing can execute when Bland invokes nothing. |
| Resumes at an arbitrary pre-booking node | Unsafe/unproven because it can re-enter booking without checking the flag. Do not ship until Bland can force inbound through `n_identity`, or place an authoritative booked check ahead of every booking-capable re-entry surface. |

Recommendation: use the gateway extension plus a dedicated post-booking terminal, conditional on probes proving every post-End-Call inbound execution passes through `n_identity`. It is a second deployment surface, but it provides durable state across conversations; Bland-only conversation variables may disappear on a new conversation and cannot help if the thread restarts at `isStart`. Keeping a Bland node open indefinitely avoids End Call but does not satisfy the specified finished-thread behavior and may have timeout behavior not documented here.

## 3. Scenario additions

The present runner models turns inside one execution; a true comeback needs a runner extension/fixture that can start a second inbound execution while retaining gateway booking state.

| Scenario name | Turns/setup | Expected node/outcome |
|---|---|---|
| `post-booked extra ask` | Complete successful booking, then ask `are my glasses ready?` before closure/resumption boundary. | `e_postbook_deferral`; exact mandated deferral; path excludes `n_office`, `n_faq`, search, verify, and book. |
| `post-booked change request` | Successful booking, then ask to cancel or move it. | `e_postbook_deferral`, not `n_office`; exact deferral. |
| `text-back after close` | Finish at `e_booked`; new inbound execution with gateway flag true; ask any question. | `n_identity -> e_postbook_deferral`; exact deferral; no booking webhook. |
| `text-back after close Chinese` | Same setup; inbound message in Chinese. | Post-booking deferral in Chinese with `(212) 219-2219`; no Chinese opener invitation; no booking path. Exact approved Chinese wording is not supplied in source, so it requires product approval rather than invention in the test. |
| `booked flag false preserves recall` | Fresh patient, flag false, unique identity. | `n_identity -> n_ask`; normal booking remains possible. |
| `booked flag missing or malformed` | Gateway response omits flag or returns a non-true value. | Never interpret as booked. Follow documented identity behavior; no internal leak. Release should also test gateway failure separately. |
| `post-booked repeated replies` | Two inbound replies after close with flag true. | Both end at `e_postbook_deferral`; zero search/verify/book calls. |
| `post-booked STOP` / `post-booked wrong person` | Reply after close with each safety intent. | Suppression outcome (`e_stop` / `e_not_me`) if Bland supports a higher-priority global route; otherwise this is an unresolved safety design decision that must be settled before release. |
| `pre-booking office detour` | Ask about glasses before booking. | Existing steer-back (`n_office` then booking node) with `212`, not post-booking deferral. |
| `pre-booking FAQ detour` | Ask insurance/cost before booking. | Existing `n_faq` steer-back, with no price/coverage claim and no post-booking deferral. |
| `booking close exact suffix` | Successful booking. | `e_booked`; text ends byte-for-byte with the mandated close. |

Update the two existing scenarios that expect `855` to expect `(212) 219-2219` or an escaped `212` pattern.

## 4. Gate and redproof additions

Add deterministic candidate-gate rules:

1. Across every node `prompt` and `text`, old-number occurrence count is zero. New-number occurrence count is at least the expected fixed inventory, but validate exact required nodes rather than relying only on a total.
2. Each of the eleven named nodes contains `(212) 219-2219`; none contains `(855) 750-6688`.
3. `e_booked.text.endswith("You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219")` exactly.
4. `e_postbook_deferral.text` equals the mandated deferral exactly, and it is an End Call with no outgoing edges.
5. `n_confirm` has an edge for any further request to `e_postbook_deferral`, has no edge to `n_office`, and has no path to any search/verify/book node.
6. `n_identity` extracts `campaign_booking_complete`, routes explicit true to `e_postbook_deferral`, and the booked route precedes the ordinary `count == 1 -> n_ask` route. Require fail-closed exact-true semantics.
7. From `e_postbook_deferral` and all known booked-state entry nodes, graph reachability to search/verify/book is empty. Conversely, pre-booking `n_office` and `n_faq` retain their existing steer-back topology.
8. Narrow the positive-claim checker only for the exact mandated `e_booked` suffix; any extra booking claim still fails. Check `NO_CLAIM` text remains in pre-booking generative prompts and `NO_LEAK`/language rules remain in all changed generative prompts.
9. Scenario inventory contains all named cases and the runner supports/asserts path exclusion or webhook-call counts; merely naming unsupported assertion keys must fail.

Add one redproof mutation per rule: reinsert old number in one prompt; remove the new number from each named-node check (table-driven submutations); alter one character of each mandated line; append an extra booking claim to `e_booked`; delete/rewire the `n_confirm -> e_postbook_deferral` edge; restore `n_confirm -> n_office`; add a post-book route to search; delete the new extraction field; delete, reorder, or loosen the identity booked predicate; add an outgoing edge from the terminal; remove `NO_CLAIM`, `NO_LEAK`, or language-switch text from a changed prompt; change pre-booking `n_office`/`n_faq` to terminate; and remove each required scenario. Each mutation must make the clean candidate gate fail for the intended reason.

## 5. Regression risks

- **NO_CLAIM:** the mandated `You're all set` conflicts with the current structural monopoly. Permit only that exact `e_booked` suffix after success; do not broadly exempt the node or duplicate the confirmation/time.
- **Never rebook after success:** the current `n_confirm -> n_office` route enters a node whose purpose is to return to booking. Removing that edge and checking booked-state reachability are release blockers.
- **Bilingual switching:** fixed End Call copy cannot visibly infer language from the graph material. Prove a deterministic language mechanism or use a tightly constrained generative post-book node. English must remain exact for English; approved Chinese copy is currently unknown.
- **STOP/wrong-person suppression:** a blanket booked-first identity route could swallow later STOP/wrong-person messages. Probe and ensure suppression has priority; never disclose identity or promise suppression completion.
- **Gateway state:** false negatives allow rebooking; false positives block legitimate recall booking. Key the flag to verified patient binding plus this campaign's successful booking write, make the write/read atomic enough for immediate replies, and test retries and transport-loss cases.
- **End Call/inbound behavior:** no source evidence proves re-entry. A structural pass cannot certify comeback behavior; release requires the empirical probes.
- **Brand:** 26 nodes say `Mott Optical`, while both mandated lines say `MK2 Optical`; the number-only edits preserve mixed branding and make it more visible. Recommendation: standardize patient-facing practice naming to `MK2 Optical` if that is the legal/operating patient brand, while retaining “MK2 office” only as a location label. This is Ankit's call and should be a separate approved copy sweep, not silently bundled into the eleven locked number replacements.

**Verdict:** review-required. The graph-side design is specific, but v62 is not ready until Bland inbound behavior, request-data availability on restart, bilingual post-book copy, and suppression priority are measured.
