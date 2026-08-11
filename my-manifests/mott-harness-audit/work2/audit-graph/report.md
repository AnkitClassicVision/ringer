# Graph Audit

## Summary
- Both conflict-check webhooks (`n_verify_1`, `n_verify_2`) evaluate `overlap_id == ""` before `ok != "true"`, so a failed verify call is misread as "explicitly clear" and books the slot — a complement condition landing on a booking node exactly as the rules doc warns against.
- The two global detour nodes (`n_office`, `n_faq`) have exactly one outgoing edge each and it is not back into booking, and neither has a timeout edge despite waiting on the patient — they promise a return that cannot happen and have no guaranteed way out.
- `n_search`'s gateway-failure branch (`ok != "true"`) is routed to `n_reask` instead of the `gateway_failed` exit used by every sibling webhook, hiding real outages behind a "nothing found" experience.

## Findings

### Finding: Failed conflict-check can book an unverified slot
Evidence: `n_verify_1.data.responsePathways` (identical in `n_verify_2`) is ordered:
`["overlap_id","!=","", -> n_negotiate]`, `["overlap_id","==","", -> n_book_1]`, `["ok","!=","true", -> e_safe_failure]`.
Impact: When `/conflict-check` fails outright (timeout, 401, 5xx), the response never populates `overlapping_appt_id`, so extracted `overlap_id` reads as empty — indistinguishable from an explicit "no conflict." Because the empty-string check runs before the `ok` health check, the pathway falls into `n_book_1`/`n_book_2` and writes a real appointment without confirming the slot was clear. The patient hears a normal "you're all set," but the office may later find a real double-booking. This is the exact pattern the rules doc's "order the complement onto the conservative branch" example warns against; the gateway check is in the wrong position relative to it.
Fix: Move `["ok","!=","true", -> e_safe_failure]` to the first position in both `n_verify_1` and `n_verify_2`'s `responsePathways`, ahead of the `overlap_id` checks, so a failed or malformed verify call never falls through to `overlap_id == ""`.
Priority: P0
Confidence: high

### Finding: Detour nodes cannot structurally return to booking
Evidence: The only edge with `source: "n_office"` is `edge-n_office-e_office-office-direction-delivered` (n_office → e_office, an End Call). The only edge with `source: "n_faq"` is `edge-n_faq-n_office-patient-asks-to-speak-to-someone` (n_faq → n_office). Both nodes' prompts (`n_office`, `n_faq`) instruct: "Then ALWAYS return to the goal with a direct question: ask whether they would like you to get them scheduled now... Only an explicit no ends this." Both set `enableGlobalAutoReturn: true`.
Impact: A patient who answers "yes, schedule me" after being routed through `n_office` or `n_faq` has no edge back to `n_offer`, `n_negotiate`, or `n_search`. The model is told to keep the conversation open and offer booking, but the only transition the graph provides ends the call with outcome `office` — an interested patient is stranded and no appointment is booked.
Fix: Add an edge from `n_office` (and from the `n_faq → n_office` chain) back into the booking flow, e.g. `n_office → n_offer` labeled "wants to continue booking," so an affirmative reply can actually route there.
Priority: P0
Confidence: high (see Assumptions on `enableGlobalAutoReturn` platform semantics)

### Finding: Detour nodes wait on the patient with no timeout exit
Evidence: `n_office.data.userWait` is `true` and `n_faq.data.userWait` is `true`, yet neither node has any edge resembling the `"72-hour timeout"` edges present for every other waiting node (`n_ask`, `n_reask`, `n_offer`, `n_negotiate` each have an explicit edge to `e_timeout`). `n_office`'s and `n_faq`'s only edges are the single non-timeout edges described above.
Impact: A patient handed off to the office/FAQ detour who never replies again has no defined exit from that node — unlike every other patient-facing node, there is no guaranteed way out.
Fix: Add an explicit `"72-hour timeout"` edge from `n_office` and from `n_faq` to `e_timeout`, matching the pattern used elsewhere.
Priority: P1
Confidence: high

### Finding: Search-webhook failures are silently relabeled as "no openings"
Evidence: `n_search.data.responsePathways` routes `["ok","!=","true", -> n_reask]`, while the structurally identical checks in `n_identity`, `n_verify_1`, and `n_verify_2` all route `ok != "true"` to `e_safe_failure` (outcome `gateway_failed`).
Impact: If `/availability` fails (auth error, timeout, 5xx), the patient is told the same thing as a real "no slots that day" result and asked to try another day — the real cause is a gateway outage, but the conversation never reaches a `gateway_failed` tag, so this failure mode is invisible to analytics and conflated with genuine scheduling misses.
Fix: Route `n_search`'s `ok != "true"` pathway to `e_safe_failure`, consistent with the other three webhook nodes.
Priority: P2
Confidence: medium

### Finding: Outcome enum is missing a tag actually used in the graph
Evidence: `e_existing.data.outcome` is `"existing_appointment"`, but `analysis_options.fields[0].values` (the `outcome` enum) lists only `booked, declined, no_reply, office, wrong_person, stopped, identity_failed, gateway_failed, booking_failed` — nine values, omitting `existing_appointment`.
Impact: If the platform enforces this enum for its analysis schema, conversations that end at `e_existing` may have their outcome silently dropped or normalized, undercounting that failure mode in reporting even though the node itself carries a distinct tag.
Fix: Add `"existing_appointment"` to the `outcome` enum values in `analysis_options`.
Priority: P3
Confidence: medium (rules doc itself notes `analysis_options` may not persist on this account at all)

## Clean
- **String-literal comparisons**: every `responsePathways` condition value is a quoted string (`"1"`, `"true"`, `"200"`, `""`, etc.); no boolean or numeric literals found.
- **Value-range coverage**: `n_identity` covers `count` at 0, 1, 2+; `n_search` covers `slot_count` at 0, 1, 2+. Both exhaustive.
- **Boolean health checks positioned last**: in `n_identity` and `n_search`, the `ok != "true"` catch-all is the final pathway entry, matching the recommended ordering (the `n_verify_1`/`n_verify_2` ordering issue is called out separately above).
- **No template comparisons**: no `responsePathways` condition compares against a `{{...}}` interpolation.
- **Edges well-formed**: every edge has a unique `id` and `type: "custom"`; every node has `position`, `x`, `y`, `width`, `height`.
- **No duplicate node display names** across all 22 nodes.
- **Webhook credentials**: every `Webhook` node's `Authorization` header is `{{ SECRET.MottGatewayToken }}`; `build_v39.py` refuses to emit the graph otherwise (`unauthed` guard).
- **Booking claims gated to confirmation**: only `n_confirm` is permitted to state a booking exists; every other patient-facing prompt (`n_ask`, `n_reask`, `n_offer`, `n_negotiate`, `n_office`, `n_faq`) carries an explicit "never say or imply booked" prohibition.
- **Post-confirmation silence is success**: `n_confirm` routes both "confirmation delivered" and "72-hour silence after booking" to `e_booked`.
- **No same-turn ping-pong**: `n_negotiate` (`userWait: false`) hands off silently to `n_search` (also non-waiting), which always lands on a waiting node (`n_offer` or `n_reask`); no cycle returns to `n_negotiate` without a patient wait between.
- **Interpolated times not reformatted**: `n_offer`'s prompt instructs presenting `slot_1_start`/`slot_2_start` "exactly as given."
- **Write payloads sourced from webhooks only**: `n_book_1`/`n_book_2` bodies use `patient_id`/`exam_type_id` (from `n_identity`) and `slot_*_doctor`/`start`/`end` (from `n_search`), never model-extracted fields.

## Assumptions
- Could not verify whether `enableGlobalAutoReturn: true` triggers an undocumented platform-level return to the prior flow independent of explicit edges; the `n_office`/`n_faq` finding assumes it does not, per the rules doc's wording that a detour "must... end with an explicit return to the goal."
- `store`, `recall_cell`, and `recall_patient_id` are referenced by `n_identity` but produced by no node in this graph; assumed to be call-level/request variables set outside the graph, per `build_v39.py`'s own comment.
- Could not verify live behavior of `n_negotiate`'s `globalLabel` restriction ("does not apply once a booking is confirmed") — a prompt-level instruction, not a structural gate, so whether it reliably blocks re-triggering search/booking after `n_confirm` is unconfirmed.
- Did not independently verify gateway response shapes (e.g. whether a failed call truly returns empty `overlapping_appt_id`); the `n_verify_1`/`n_verify_2` finding follows the extraction behavior the rules doc itself describes for a missing/malformed value.
