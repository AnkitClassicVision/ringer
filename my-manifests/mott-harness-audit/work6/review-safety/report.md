# v55 Write Path Safety Review

## Summary

- Both reported v54 defects are genuinely closed in the v55 artifact: `n_confirm` is reachable only through `book_success == "true"` on `$.success`, and both verify nodes now extract `$.result.conflict` and block on it before any positive route.
- The change is sound on the fail-unsafe axis: no ordering or reachability path books or confirms without the signer's own flags. Remaining findings are fail-closed (patient can't book, or is told less than the truth), not wrong-write.
- The single route into each book node still keys on `overlap_id`, a field the catalog does not define. That is the builder's explicit no-regression choice, and it is the weakest link: it works only while the gateway keeps emitting an undocumented field as an empty string.

## Findings

### Finding: The only route into booking depends on the undocumented field $.result.overlapping_appt_id
Evidence: `n_verify_1` and `n_verify_2` route to `n_book_1`/`n_book_2` solely on `["overlap_id", "==", ""]`, where `overlap_id` extracts `$.result.overlapping_appt_id`. The catalog's `/conflict-check` entry (`availability.conflict_check`) defines only `$.ok`, `$.result.conflict`, and `$.result.reason` — `overlapping_appt_id` does not exist in the contract, and the catalog's own positive pathway is `slot_conflict == false`. If the gateway ever omits the undocumented field, the platform substitutes null, `["overlap_id", "!=", ""]` matches, and every clean slot routes to `n_recheck`. The same applies to `["conflict_reason", "!=", ""]` if `$.result.reason` is omitted rather than empty on clean responses (the catalog describes it only as the reason "for the conflict").
Impact: The patient says yes to a real, free slot and is told "that time was just taken, I'm checking what else is open," then offered new times, says yes again, and loses that one too — every slot, forever. They can never book by SMS.
Fix: Make the positive route `["slot_conflict", "==", "false"]` targeting `n_book_1` (and `n_book_2` in the second verify node) — the catalog-endorsed pathway, keep `overlap_id`/`conflict_reason` as additional blocking checks if desired, and add a final catch-all to `e_safe_failure` so a no-match response cannot dangle.
Priority: P1
Confidence: medium

### Finding: The positive route books on absence of blocking signals, not on an affirmative all-clear
Evidence: In `n_verify_1`/`n_verify_2`, first-match order is `ok != "true"`, `slot_conflict == "true"`, `conflict_reason != ""`, `overlap_id != ""`, then `overlap_id == ""` → book. Build comments state this is deliberate no-regression: a gateway that does not populate `$.result.conflict` books exactly as v54 did. On the explicit question — a response with `conflict` true but `overlapping_appt_id` empty is caught at the second condition and goes to `n_recheck`, so the v54 outside-schedule hole is closed. But a response where `conflict` is absent or stringifies as anything other than exactly `"true"` (e.g. Python-style `"True"`), with `reason` and `overlap_id` both empty strings, proceeds straight to the write.
Impact: If a gateway change drops or reshapes `conflict` while keeping the legacy empty strings, an outside-schedule slot again reads as clear; the patient is protected only by the signer's own re-check at write time (catalog warning: "/sign performs its own conflict check again," and `n_book_1`/`n_book_2` route `book_error == "slot_conflict"` back to `n_recheck`).
Fix: Same as the P1 fix: gate booking on `slot_conflict == "false"` so the write requires the contract's affirmative signal. This is a hole papered over by the signer's redundancy, not a safe design.
Priority: P2
Confidence: high

### Finding: e_booking_failed asserts "No appointment was booked" on outcomes where the write state is unknown
Evidence: `n_book_1`/`n_book_2` route `["book_success", "!=", "true"]` to `e_booking_failed`, whose text is "No appointment was booked. Please call Mott Optical…". That catch-all also fires when the webhook fails in transport (all response variables unfilled → null → `!= "true"` matches), where the signer may have committed the write before the response was lost. `retryAttempts: 0` correctly prevents an automatic double-write.
Impact: A patient whose booking actually went through is told flatly that nothing was booked; if they don't call, they may no-show or rebook elsewhere, and staff see a phantom appointment.
Fix: Soften the exit text to "I couldn't confirm a booking — please call…" or split the transport-failure case (no `$.success` at all) to `e_safe_failure`, reserving the definitive "No appointment was booked" for an explicit `success:false`.
Priority: P2
Confidence: medium

### Finding: Near-band pages offer the literal null when the slot index is absent
Evidence: `n_page_near` (also `n_page_2`, `n_page_3`) guards emptiness with `["slot_1_start", "==", ""]`, but it extracts `$.result.slots[8].start` — if fewer than nine slots exist, the variable is null, `["slot_1_start", "!=", ""]` matches, and `n_offer_near` texts the patient "the first is {{slot_1_start}}" with null substituted. Per the platform brief, only the literal `none` is a safe sentinel; `""` cannot distinguish absent from empty.
Impact: The patient receives a garbled offer containing the word "null"; if they accept, the verify body carries JSON null, the gateway rejects it as a type error, and they are dumped to the `e_safe_failure` dead end mid-conversation. No bad write occurs.
Fix: Have the gateway (or extraction defaults) emit `none` for missing slots and compare against `"none"`, or route on `slot_count` before offering banded indices.
Priority: P3
Confidence: high

## Clean

- **Confirmation gating.** No path reaches `n_confirm` without `book_success == "true"`: the full-graph sweep of `responsePathways` destinations shows only `n_book_1` and `n_book_2` target `n_confirm`, both on that exact condition, and `e_booked` is reachable only from `n_confirm`. No node in v55 routes on `book_http_status` or `error_status` anywhere. Defect 1 is closed.
- **Conflict-check gating.** Only `n_verify_1` targets `n_book_1` and only `n_verify_2` targets `n_book_2`; the verify nodes are entered only from `n_gate_1`/`n_gate_2` on explicit patient yes. Every book is preceded by a conflict check. Defect 2 is closed.
- **Condition ordering.** In both verify nodes every blocking condition (`ok`, `slot_conflict`, `conflict_reason`, `overlap_id != ""`) precedes the positive route; in both book nodes the `slot_conflict` error precedes success. First-match-wins cannot skip a blocking signal here; null substitution on any routing variable resolves to a blocking or failure route, never a positive one.
- **Failure exits and recheck honesty.** `e_safe_failure` ("couldn't access scheduling… no appointment was booked") is accurate for its verify-stage entries, and the `n_recheck` prompt hard-forbids claiming a booking exists; `n_recheck` returns to `n_search`, so lost slots re-verify rather than re-book stale variables. The near-page path reuses the same `slot_1_*`/`slot_2_*` variables, so the slot verified and booked is the slot offered.

## Assumptions

- Routing comparisons see JSON booleans as the strings `"true"`/`"false"`; both the catalog pathways and every `ok`/`success` condition in v54 and v55 rely on this.
- An unfilled routing variable substitutes as null, which fails `== ""` and matches `!= ""` (per the platform brief, `none` is the only safe sentinel).
- Webhook routing truth is `responsePathways`; the `edges` array mirrors it for display and adds only LLM-node routes.
- The P1 finding is latent, not active: v54 booked in production on the same `overlap_id == ""` route, so the gateway currently emits the undocumented field as an empty string on clean responses.
