# v55 Spec Conformance Review

## Summary

- Steps 1 and 2: implemented as specified. Step 3: implemented differently (a third miss class, `n_miss_thin`, justified by the step-4 deferral). Step 5: implemented as specified at its core, with two residues (Findings 2, 3).
- One spec '## Clean' item is broken: booking success now routes on an undocumented `$.success` field instead of the proven 200/201 signer response (Finding 1).
- The miss rule and two-slot rule hold everywhere, including the new nodes; deferring steps 4 and 6 strands nothing, though half of step 6 quietly shipped anyway (Finding 4).

**Step 1 — implemented as specified.** `n_page_3` pathway `slot_1_start == ""` now targets `n_page_near`, a webhook re-issuing the identical availability body and remapping `slots[8]`/`slots[9]` onto `slot_1_*`/`slot_2_*` — the `n_page_2` pattern the P0 fix prescribed — targeting `n_offer_near`, whose script is "I don't have anything that late that day. The closest I have is {{slot_1_start}} or {{slot_2_start}}…" and whose NEVER block forbids a good-news opener.

**Step 2 — implemented as specified.** Every extractor (`n_ask`, `n_negotiate`, the miss nodes, `n_clarify`) replaces "when in doubt the answer is monday" with "write the single word unclear … never a day they did not name", with `preference_to` mirroring it. `n_search`'s first responsePathway, `preference_from == "unclear"` → `n_clarify`, precedes the `ok`, `slot_count` and band pathways, so no offer is reachable on a sentinel. `n_clarify` asks for one month-and-day form and forbids implying a search or emptiness.

**Step 3 — implemented differently.** `n_reask` is gone. `n_search` `slot_count == "0"` → `n_miss_empty`, that node's only inbound edge, so its "no openings at all in that window" is routing-proven. All four `ok != "true"` edges (`n_search`, `n_page_2`, `n_page_3`, `n_page_near`) → `n_miss_unread`, which claims only "couldn't check yet". Differences: (a) `n_page_2` `slot_1_start == ""` goes to a third node, `n_miss_thin`, not the spec's nearest-band offer — justified, see Clean; (b) verify `conflict_reason != ""` went to `n_recheck`, not a miss node — Finding 2.

**Step 5 — implemented as specified.** `n_verify_1`/`n_verify_2` route `overlap_id != ""` → `n_recheck` (`extractVars: null`, `userWait: false`, `skipUserResponse: true`), which says the time was just taken and chains to `n_search` with `preference_from`/`preference_to` untouched — the "YES"-re-extraction path through `n_negotiate` is gone. `n_book_1`/`n_book_2` `book_error == "slot_conflict"` → `n_recheck` extends this to write-time conflicts. Residues: Findings 2 and 3.

## Findings

### Finding: Booking success routes on an undocumented `$.success` field, breaking the Clean 200/201 invariant
Evidence: `n_book_1` and `n_book_2` extract `book_success` from `$.success` and route `book_success == "true"` → `n_confirm`, `book_success != "true"` → `e_booking_failed`. v54 routed `book_http_status == "200"`/`"201"` → `n_confirm`, the mechanism the spec's '## Clean' certifies ("reachable only from a 200/201 signer response"). Nothing attests a `success` field; `book_http_status` is still extracted but unused. The same pattern on `n_verify_1`/`n_verify_2` (`slot_conflict` from `$.result.conflict`) is harmless there: the proven conditions follow.
Impact: if `/sign` returns no `success` field, `book_success` stays unfilled, so a patient whose appointment was actually written is told the booking failed and never gets confirmation — they hold an appointment they don't know they have. Even if the field exists, a certified-clean invariant changed outside the claimed steps.
Fix: restore `book_http_status == "200"` and `== "201"` → `n_confirm` (keeping the `slot_conflict` check first); drop `$.success` and `$.result.conflict` until measured against the live gateway.
Priority: P1
Confidence: medium

### Finding: A verify-rejected ("not real") slot is silently re-searched and can be re-offered unchanged
Evidence: `n_verify_1`/`n_verify_2` route `conflict_reason != ""` ("Not a real bookable opening") → `n_recheck` → `n_search`, re-issuing the identical query at the same literal offsets. A structurally unbookable slot still appears in availability, so the same position yields the same slot. v54 sent this case to `n_reask`; the spec's step-5 fix covers only `overlap_id` conflicts.
Impact: a patient confirms a time, is told it was just taken, then is offered the identical time; confirming repeats the cycle indefinitely.
Fix: route `conflict_reason != ""` to an `n_miss_unread`-style node that asks for a different day, instead of re-running the same query at the same offsets.
Priority: P2
Confidence: medium

### Finding: After a lost slot, the re-search lands on a "Great news" offer instead of the miss-rule framing
Evidence: `n_recheck` → `n_search` routes to the ordinary offer nodes; `n_offer` and `n_offer_2` open "Great news, I have {{slot_1_start}} or {{slot_2_start}}…". The step-5 fix requires "the resulting offer framed by the miss rule ('that time was just taken — closest I now have is…')"; only `n_recheck`'s one-liner carries that framing.
Impact: a patient who just lost their confirmed Tuesday 2:00 receives "Great news, I have…" in the next message — replacements presented as good news rather than as the closest remaining.
Fix: add a post-conflict offer variant scripted "the closest I now have is X or Y", reached from the recheck re-search, same two-slot interpolation.
Priority: P3
Confidence: high

### Finding: Half of deferred step 6 shipped inside the v55 extraction guidance, untested and undeclared
Evidence: every v55 extractor's `preference_to` guidance (e.g. `n_ask`, `n_negotiate`) adds "If they excluded the last day of a week already being discussed, such as not friday, put the day before it" — absent from v54, and defined by the spec as migration step 6, which must ship alone and be "test scripted before live". The builder claims steps 1, 2, 3, 5 only.
Impact: if the model misapplies the trim (e.g. to a mid-window exclusion), the patient's window is silently narrowed and the results presented as matching their request.
Fix: remove the sentence until step 6's scripted-run pass, or declare it shipped and run that pass now.
Priority: P3
Confidence: high

## Clean

- **Uniform miss rule holds.** `n_miss_empty` is reachable solely via `slot_count == "0"`; `n_miss_unread` claims nothing was checked; `n_miss_thin` and `n_offer_near` claim only band thinness and forbid "that day has no openings". No thin band is described as an empty day.
- **Two-slot visibility holds.** `n_offer`, `n_offer_2`, `n_offer_3`, and `n_offer_near` interpolate exactly `{{slot_1_start}}`/`{{slot_2_start}}`; gates interpolate one slot each; no other node interpolates any time.
- Justified: thin-afternoon goes to `n_miss_thin` rather than a nearest-band offer, because the band-1 webhook (`page_first`) is deferred step 4, so no earlier-band slots can be fetched; `n_miss_thin` stays honest about seeing no times.
- Justified: the `unclear` check sits on `n_search`'s responsePathways, so one garbage query fires before routing to `n_clarify` — the platform allows deterministic conditions only on webhook pathways; the silent call is patient-invisible.
- Justified: the thin-late path costs a third gateway read (`n_search` → `n_page_3` → `n_page_near`); the P0 fix itself mandates the remap webhook.
- **Deferral strands nothing.** Every node stays reachable; "anything earlier?" resolves through global `n_negotiate` to `unclear` → `n_clarify` — an honest date question, no wrong-week search.
- Other Clean items intact: `n_book_1`/`n_book_2` reachable only via `overlap_id == ""`; `n_search` still sends the `none` sentinels and checks `ok`/`slot_count` before band routing.

## Assumptions

- A responsePathway condition on an unfilled variable fails to match (basis of Finding 1's failure scenario).
- Extraction runs against the patient's most recent message at node entry (the spec's own marked-medium assumption).
- Band-offset calibration (0/8/16, ≥18 slots per open weekday) holds; `n_miss_thin`'s claim is only as sound as that measurement, as the spec concedes.
- Availability re-reads are idempotent within a turn (`n_page_near` pages the list `n_page_3` saw).
