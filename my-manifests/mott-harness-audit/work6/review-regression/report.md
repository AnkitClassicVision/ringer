# v55 Regression Review

## Summary
- Both booking nodes now confirm solely on `$.success`, a field the catalog documents but no measurement proves the live signer populates; if absent, no patient can ever be told they are booked, even when the write happened.
- The verify-stage "not a real bookable opening" path lost its exit: v54 asked for a different day, v55 re-searches the same window and can re-offer the same unbookable time forever.
- Removing the monday fallback turns two rows that work today ("what's the latest you have?" as a fresh reply, "the week after, say Wednesday") into a clarifying question instead of times.

## Findings

### Finding: Booking success now depends on an unmeasured `$.success` field; if the signer omits it, every booking fails closed after the write
Evidence: `n_book_1` and `n_book_2` in v55 route into `n_confirm` only on `book_success == "true"` (`$.success`); anything else goes to `e_booking_failed`. v54 routed on `book_http_status` 200/201 and never read `$.success` — and v54 was built against measured live behaviour. The catalog documents the field on `/sign`, but TEMPORAL-BRIEF's measured section covers `/availability` only; no captured signer response shows `$.success`.
Impact: if the live signer returns 200 + `new_appt_id` without `$.success`, the appointment is written but the patient is told "No appointment was booked. Please call Mott Optical" — a real booking denied, inviting a duplicate by phone. This would break every row that currently ends in a confirmed booking.
Fix: before ship, run one governed test-patient `/sign` write and capture the raw response. Confirm `$.success` is present and stringifies to `"true"` for routing (precedent: `n_identity` routes on `$.ok` against the string `"true"` live). If absent or unproven, keep 200/201 as an additional positive route rather than gating solely on the flag.
Priority: P0
Confidence: medium

### Finding: A slot that fails conflict-check as "not real" now loops instead of escaping to a different day
Evidence: in v54, `n_verify_1`/`n_verify_2` with `conflict_reason != ""` routed to `n_reask`, which asked for a different concrete day. In v55 the same condition (and the new `slot_conflict == "true"` route) goes to `n_recheck`, whose only outbound edge is "looking again with the same preference" into `n_search`. The catalog defines `$.result.conflict` as true when the slot "collides or is outside the schedule"; an outside-schedule slot is still returned by `/availability`, so the identical query returns the identical `slots[0]`/`slots[1]`.
Impact: a patient who confirms a phantom slot is told "that time was just taken, checking what else is open," then shown the very same time again as good news, and the cycle repeats every time they accept it. There is no exit except giving up; v54 asked for another day on the first failure. (The `overlap_id` genuinely-taken case converges, because a booked slot drops out of availability.)
Fix: keep `n_recheck` for `overlap_id != ""` and `book_error == slot_conflict`, but route `conflict_reason != ""` and the outside-schedule flavour of `slot_conflict` to `n_miss_unread` (or a dedicated miss node) that asks for a different day, as v54 did.
Priority: P1
Confidence: high

### Finding: The unclear sentinel demotes two working brief rows to a clarifying question
Evidence: v54 `preference_from` guidance ended "If they named only a time, or no timing at all, put monday." v55 replaces this with "If they named only a part of the day... write unclear," and adds "any request whose week you would have to work out." `n_search` now routes `preference_from == "unclear"` to `n_clarify` before anything else. Affected working rows: "what's the latest you have?" when it arrives at an extraction node (`n_ask` as the first reply, or via the `n_negotiate` global) — v54 searched monday and showed real late slots; and "the week after, say Wednesday" — v54 emitted `wednesday next week`, which the brief notes "happens to parse," while v55's instruction explicitly maps that phrasing to `unclear`.
Impact: patients who today receive appointment times in the next message instead get "which date would you like, for example August 12." One extra round-trip, plus a second-order loss: after the patient answers `n_clarify` with a bare date, `day_part` is re-extracted from that date-only reply as `none`, so a patient who asked for "the latest" is then shown morning slots (offset 0) rather than page 3.
Fix: accept the clarify step as the designed trade if the owner agrees, but carry `day_part` forward: `n_clarify`'s extraction guidance should repeat the previously stated part of the day unless the patient changes it. The mid-conversation page-climb rows are unaffected — see Clean.
Priority: P2
Confidence: high

### Finding: n_miss_thin invites an answer the new extraction rules cannot use
Evidence: `n_miss_thin` asks "whether another time that day would work or whether they would rather try a different day." A reply like "morning would be fine" names only a part of the day, which v55's `preference_from` rule maps to `unclear`, so `n_search` sends them to `n_clarify`, which demands a date they already gave. v54's `n_reask` asked only for "one specific day," so every answer was usable.
Impact: a patient who cooperates with the exact question asked is then asked for a date as if they had said nothing.
Fix: either have `n_miss_thin` ask only for a different day (matching its edges), or extend its extraction guidance to repeat the previously captured window when the reply names only a part of the day.
Priority: P2
Confidence: medium

## Clean
- "Tuesday afternoon", "August 12 in the afternoon", "I need a late afternoon appointment next week", "sometime next week": identical extraction outputs and identical routes (`n_search` → `n_page_2`/`n_page_3` → `n_offer_2`/`n_offer_3`, or straight to `n_offer`). The week-in-general → monday/friday rule survives verbatim ahead of the unclear clause.
- "anything later in the day?" / "anything later still?" / "what's the latest you have?" at an offer node: the climb edges `n_offer` → `n_page_2` and `n_offer_2` → `n_page_3` are unchanged and offer nodes carry no extractVars, so the sentinel cannot fire on this path.
- Sentinel-before-gateway ordering at `n_search`: when `preference_from` is `unclear`, both the sentinel and `ok != "true"` match; first-match-wins lands on `n_clarify`, the honest destination, at the cost of one rejected gateway call.
- The arrival classes of the removed `n_reask` land as: search rejected → `n_miss_unread` (×3), window empty → `n_miss_empty`, afternoon thin → `n_miss_thin`, verify not-real → `n_recheck` (the one dishonest landing, Finding 2). All new miss nodes have forward edges to `n_search`, `e_declined`, `e_timeout`.
- `overlap_id` lost-slot handling improved: `n_recheck` has no extractVars, so the confirmed window survives instead of v54's reset-to-monday via `n_negotiate`.
- Thin-late path improved: `n_page_3` → `n_page_near` → `n_offer_near` names the miss instead of the "Great news" afternoon substitution.
- Identity, globals, FAQ/office, gates, language and no-claim rules: unchanged.

## Assumptions
- Extraction at a node with extractVars runs on the latest patient message and overwrites prior values; both builders' comments rely on this.
- `/availability` excludes genuinely booked slots (so the `overlap_id` re-search converges) but can return outside-schedule slots — the catalog's stated reason `/conflict-check` exists — which is what makes Finding 2 a loop.
- Boolean gateway fields stringify to `"true"` for routing, proven live only for `$.ok`; assumed for `$.success` if populated.
- The brief's "works" notes on the later-in-day rows describe the offer-node climb path, not fresh extraction.
