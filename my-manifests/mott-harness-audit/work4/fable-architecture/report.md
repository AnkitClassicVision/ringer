# Architecture Review

## Summary

- The three failures share one root cause: the design uses the language model as a data bus — every boundary crossing (patient words → search parameters, slot list → booking payload, follow-up → new window) requires the model to re-author multiple structured fields in free text, and the platform converts any miss into a fatal null or a stale search.
- The minimum the model must carry can be reduced to one closed-class token per decision: an ordinal (1/2/3) selecting from slot variables the platform already holds, and two closed-vocabulary day words for the window. Field values (start, end, doctor) never need to pass through the model at all, because fixed-index extraction into named variables is measured as working and webhook bodies can interpolate those variables directly.
- The graph's spine (identity → ask → search → offer → verify → book → confirm) is the right shape and its safety ordering is sound; what must go is the payload capture at `n_offer`, the frozen window, and the positional-guess nodes `n_search_pm`/`n_search_late`.

## Findings

### Finding: The model is used as the transport for structured payload data, which it measurably cannot do
Evidence: `n_offer` extractVars `chosen_start`, `chosen_end`, `chosen_doctor` ask the model to copy three values "character for character" out of `all_slots`. Live capture: `chosen_start = '07/28/2026 05:15 pm'`, `chosen_end = None`, `chosen_doctor = None`. Earlier, the five-field preference capture failed 2 runs in 6 on one phrasing. Three rounds of description-tightening moved the rate without fixing it.
Impact: The patient picks a real, available time, is told scheduling is unavailable, and the booking is lost at the moment of highest intent.
Fix: The model carries only an ordinal. `n_search` already extracts `slots[0]`/`slots[1]` triples into `slot_1_*`/`slot_2_*` (add `slots[2]` for a third). The offer message interpolates those variables; the patient replies 1, 2, or 3; the model extracts a single one-token choice; routing on `choice == "1"` (single-condition compare against a literal — measured supported) leads to a verify node whose body hardcodes `{{slot_1_start}}`/`{{slot_1_end}}`/`{{slot_1_doctor}}`, and so on per ordinal. The payload is then provably traceable to a gateway response because no model output ever appears in it. Cost: a verify+book node per menu position (3 each), and the patient books from a menu rather than free-naming a time — free-named times route to re-search, not to selection.
Priority: P0
Confidence: high

### Finding: A capture miss terminates the conversation at a safety exit instead of recovering
Evidence: A null `chosen_end` makes the `n_verify` body invalid (unfilled variable → JSON null → gateway 400, per the measured platform constraint), so `ok != true` routes to `e_safe_failure`, which tells the patient scheduling is unavailable and ends. This is exactly the live transcript's outcome.
Impact: A recoverable extraction miss is indistinguishable from a gateway outage; the patient is dead-ended with no retry.
Fix: The ordinal design removes the class structurally — `n_verify` bodies interpolate webhook-sourced `slot_k_*` variables that are filled before `n_offer` ever runs, so a null body cannot occur. Note that no interim guard is expressible today: `Default` nodes have only model-chosen edges, not variable conditions, so "route to re-offer when chosen_end is empty" cannot be written; this is another reason the fix must be structural rather than a patch.
Priority: P0
Confidence: high

### Finding: The search window is written once and every later search reuses it verbatim
Evidence: `n_search`, `n_search_pm`, and `n_search_late` all post the identical body `{"from":"{{preference_from}}","to":"{{preference_to}}",...}`. The edge `edge-n_offer-n_search_late-asks-for-a-later-or-the-last-time-that-day` reaches a search with no re-extraction step in between, so "anything later on any other day" re-runs Tuesday→Tuesday. Only `n_negotiate` re-extracts, and its global label overlaps the offer node's local "later" edge, so which one fires on that phrasing is a model coin-flip.
Impact: The agent truthfully describes a window the patient has already moved past — "I only have availability for Tuesday, July 28th" — and reads as unable or unwilling to help.
Fix: Exactly one search node, reached only through nodes that re-extract the day window. Delete `n_search_pm`/`n_search_late` and the `n_offer → n_search_late` edge; route every navigation intent ("later", "another day", "that week") through `n_negotiate`, whose extraction rewrites `preference_from`/`preference_to` each pass. Defaults are closed-class: "any other day" with no day named widens to monday..friday and the server does the date arithmetic (measured: weekday-word ranges work; `next week` now accepted).
Priority: P0
Confidence: high

### Finding: The positional-guess mechanism of failure 3 is still live in the graph
Evidence: `n_search_pm` extracts `slots[8]`/`slots[9]`; `n_search_late` extracts `slots[16]`/`slots[15]`. On the measured 27-slot day, position 16 is mid-afternoon — this is the exact mechanism that answered "latest" with 3:00 pm when the real answer was 5:15 pm. `n_search` routes `time_pref == "afternoon"` into this path unconditionally.
Impact: A patient asking for late in the day is shown times that are not the latest, or (when the day has fewer than 17 slots) bounced to `n_reask` as if the request could not be served.
Fix: Delete both nodes (subsumed by the previous finding). Within-day navigation is replaced by deterministic paging: page nodes re-run the identical availability search but map different fixed indices into the *same* `slot_1_*`..`slot_3_*` variable names — the remapping pattern `n_search_late` already proves works — so the verify/book fan-out never grows. "Latest" jumps to the last page via an ordered ladder of `slot_count >= N` routes.
Priority: P1
Confidence: high

### Finding: Three of the five captured preference fields feed parameters the gateway is measured to ignore
Evidence: `preference_after`, `preference_before`, and `time_pref` are captured in `n_ask`, `n_reask`, and `n_negotiate`, and sent in every availability body — but the brief measures `after`, `before`, and `time_pref` as accepted and ignored (identical responses with and without). These are also the fields where "next week" and "afternoon" landed wrongly in the 2-in-6 failure.
Impact: Most of the capture surface that fails carries zero benefit; every extra field is another chance to poison the search or the conversation.
Fix: Reduce capture to two fields from a closed vocabulary — `preference_from` and `preference_to`, weekday words / `tomorrow` / a plain date — and send the literal `none` for the ignored parameters. Keep `time_pref` only if within-day paging routes on it, as a routing enum that never enters a payload.
Priority: P1
Confidence: high

### Finding: n_book's success detection depends on unverified ordered-first-match evaluation
Evidence: `n_book` responsePathways list `book_http_status == "201" → n_confirm` *after* `== "200"` but a separate `!= "200" → e_booking_failed` also matches a 201. Correct behavior requires pathways to be evaluated strictly in order, first match wins — plausible (the graph relies on it elsewhere) but not among the measured constraints.
Impact: If evaluation is ever unordered, a 201-created appointment routes to `e_booking_failed`, the patient is told "No appointment was booked" when one exists, and a later re-book double-books them.
Fix: Make the terminal route unambiguous: replace `!= "200"` with explicit non-success matches, or confirm ordering semantics with the vendor and record it as a measured constraint.
Priority: P2
Confidence: medium

## Clean

- `n_identity` fails closed on every input gap and on non-unique matches (`count == 0`, `count >= 2`, empty `recall_cell`/`recall_patient_id`/`store` all route to `e_safe_identity`).
- Verify-before-book is structurally enforced: `n_book` is reachable only via `n_verify`'s `overlap_id == ""` route, and `n_verify` checks both `conflict_reason` and `overlap_id`, matching the measured contract that both must be inspected.
- Only `n_confirm` claims a booking exists, and it is reachable only from `n_book` success routes.
- Opt-out, wrong-person, decline, and existing-appointment exits (`e_stop`, `e_not_me`, `e_declined`, `e_existing`) are global and terminal.
- Date arithmetic is server-side via weekday words; the model is never asked to compute a calendar date.

## Assumptions

- Routing pathways evaluate in listed order, first match wins (the current graph already depends on this; flagged above).
- Routing conditions may reference any variable, not just the node's own response data (evidenced by `n_identity` routing on the input variables `recall_cell` and `store`).
- Variables interpolate into `Default`-node message text (evidenced by `{{patient_first}}` in `n_ask` and the `OFFER_EN` template in build_v49.py using `{{slot_1_start}}`).
- Re-posting the availability search is side-effect-free, so paging may re-run it.
- One-token closed-class extraction (an ordinal or a weekday word) is reliable where multi-field free-text capture is not; supported by the evidence that the single simplest field (`chosen_start`) was the one captured correctly, and that the `none` sentinel discipline works in production.

## Recommended Architecture

The platform is suited to this task if and only if the model's job is reduced to routing and closed-class tokens. The architecture is not fundamentally unsuited; the current *assignment of responsibilities* is. Shape (existing nodes keep their ids; new nodes are written as NEW:name to distinguish them from anything in v49):

- **`n_identity`** — unchanged. Decides: whether exactly one patient matches. Forbidden: nothing new.
- **`n_ask`** (speak, wait) — recall message. Decides: the initial day window as two closed-vocabulary tokens (`preference_from`, `preference_to`). Forbidden: naming any time, capturing clock times or time-of-day, computing dates.
- **`n_search`** (webhook, silent; the only availability node) — body: `store`, `from`, `to`, `slot_minutes`, literal `none` for ignored params. Extracts `slot_count`, `all_starts` (read-only conversational context), and three menu triples `slot_1_*`, `slot_2_*`, `slot_3_*` from `slots[0..2]`. Routes: `ok != true` and `slot_count == "0"` → `n_reask`; else → offer. Decides: nothing; it is a pure function of the window.
- **NEW:offer-menu** (speak, wait; replaces `n_offer`'s dual role) — message interpolates the three menu starts, "reply 1, 2 or 3"; prompt may read `all_starts` to *answer questions* ("the latest that day is X — want me to pull it up?"). Decides: which edge — choice made (extract single-token `choice` ∈ 1/2/3), wants later that day (→ next page), wants the latest (→ count-ladder jump), wants different days (→ `n_negotiate`), declines. Forbidden: offering as bookable any time not currently in `slot_1..3_*`, capturing any field value, claiming a day is empty beyond what its own list shows. A model error here costs one extra conversational turn, never a payload.
- **NEW:page-2 … NEW:page-n** (webhook, silent) — identical search body; extract `slots[3..5]`, `slots[6..8]`, … into the *same* `slot_1..3_*` names (the remapping pattern `n_search_late` proves). A descending ordered ladder on `slot_count` selects the last page for "latest". Decide: nothing.
- **NEW:verify-1/2/3** (webhook, silent; replace `n_verify`) — reached by `choice == "k"`; body hardcodes `{{slot_k_start}}`/`{{slot_k_end}}`/`{{slot_k_doctor}}`. Routes as today: `conflict_reason != ""` → `n_reask`; `overlap_id != ""` → `n_negotiate`; clear → the matching book node. Structurally unskippable: each book node has exactly one inbound edge, from its verify.
- **NEW:book-1/2/3** (webhook, silent) — same body discipline; routes as today's `n_book`, with the 201 ambiguity fixed.
- **`n_negotiate`** (global, speak-then-continue) — unchanged role, reduced extraction: the two day words only. Decides: the new window. Forbidden: times, payload fields. Every re-entry rewrites the window, which is how the window re-scopes as the conversation moves.
- **`n_reask`, `n_confirm`, globals and terminals** — unchanged.

The model interprets intent everywhere — that is the only place intent *can* live — but expresses it exclusively as an edge choice plus, at most, one closed-class token. It is forbidden from deciding anything that enters a payload, whether a booking happened, or whether availability exists beyond the list it holds.

## Migration

Each step leaves the system no worse than the step before.

1. **Shrink the capture surface.** Drop `preference_after`/`preference_before` from extraction in `n_ask`/`n_reask`/`n_negotiate`; send literal `none` in search bodies. No behavior depends on them (gateway ignores them); risk removed, none added.
2. **Fix `n_book`'s 201/`!= 200` ambiguity.** One-line pathway change.
3. **Introduce the ordinal path.** Add `slot_3_*` extraction to `n_search`; replace `n_offer`'s prompt and extraction with the menu prompt + single `choice` token; add the three NEW:verify and three NEW:book nodes; retire `chosen_*`. This kills failure 1 and the null-payload dead-end. The pm/late nodes still remap into `slot_1_*`/`slot_2_*`, so they remain compatible during the transition.
4. **Unfreeze the window.** Delete `n_search_pm`/`n_search_late` and the `n_offer → n_search_late` edge; route all navigation through `n_negotiate` → `n_search`. Interim cost: "later that day" re-shows page 1 (worse for that one intent, safe), which step 5 restores.
5. **Add paging** and the `slot_count` ladder for "latest"/"afternoon" within-day navigation.

## Not Fixed By This

- **Gateway ignores `time_pref`/`after`/`before`** (filed, other team). Until fixed, within-day preference costs paging turns instead of one filtered search. If the gateway team can also return an opaque slot id accepted by `/sign` (book-by-reference), the verify/book fan-out and paging ladder shrink dramatically — worth requesting explicitly.
- **Ambiguous outcome on booking timeout.** With `retryAttempts: 0`, a timed-out `/sign` may have written; `e_booking_failed` then tells the patient nothing was booked. Needs gateway idempotency keys or a booking-status lookup; no graph shape can resolve it.
- **Global-node matching is still model-judged.** Which global fires on an ambiguous message remains probabilistic; this design bounds the consequence to a wasted turn, not a bad booking.
- **Free-text discipline still relies on prompts** (no booking claims, no prices, language switching, no internal names). This design removes prompts from the data path, not from the messaging path.
- **Platform limits stand**: no variable-indexed extraction, no end-of-list indexing, no compound routing conditions, no set-variable primitive. Vendor fixes to any of these would simplify the paging ladder and fan-out.
- **14-day span cap**: a patient wanting a date beyond two weeks out needs a fresh window or the office.
- **Verify-to-book race (TOCTOU)** is mitigated, not eliminated, by the signer's own `slot_conflict` error — acceptable as-is.
