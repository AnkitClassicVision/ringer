# Capture Contract

## Summary

- The current contract at `n_offer` requires a small model to copy three strings verbatim; every failure mode of that contract is live, and one of them — a real-but-wrong slot in `chosen_*` — sails through `n_verify` and books a patient at a time they never agreed to.
- The narrowest safe contract the measured platform can express is: the model emits one word from a closed set (`1`, `2`, `none`, then `yes`/`no`), and every gateway payload is built only from webhook-extracted `slot_k_*` variables at fixed indices — the model never carries a time, an end, or a doctor id anywhere.
- The wrong-time failure is closed structurally, not by prompt: the final confirmation message and the `/sign` body interpolate the *same* platform variable, so the booked time is always the exact string the patient saw and affirmed in the immediately preceding message.

## Findings

### Finding: Three-field verbatim copy at n_offer is the root defect; one missed field nulls the payload and kills the conversation
Evidence: `n_offer.extractVars` defines `chosen_start`, `chosen_end`, `chosen_doctor` as character-for-character copies from `all_slots`. Live run: `chosen_start` captured, other two empty. The platform substitutes unfilled variables as JSON null, so `n_verify`'s body (`{"doctor":"{{chosen_doctor}}",...}`) reached `/conflict-check` malformed, `ok != true` routed to `e_safe_failure`, and the patient was told scheduling was unavailable. Third instance of the class (earlier: 5 preference fields, 2 cross-contaminated, 2-in-6 failure rate on one phrasing).
Impact: Bookings lost at the moment of highest intent; failure is misreported to the patient as a system outage.
Fix: Remove all three `chosen_*` extractVars. No model-copied value may appear in any webhook body (see Recommended Contract).
Priority: P0
Confidence: high

### Finding: Nothing links the time offered in the message to the time in the payload, so a wrong-time booking is reachable
Evidence: `n_offer`'s message is free model text over `{{all_starts}}`; `chosen_start` is a separate model act. If the model names 5:15 pm in the SMS but writes `07/28/2026 03:00 pm` (another real entry from `all_starts`) into `chosen_start`, `n_verify` finds it real and free (`conflict_reason == ""`, `overlap_id == ""`) and routes to `n_book`, which signs it. `/conflict-check` validates bookability, never agreement.
Impact: A patient is booked at a time they did not choose — the worst available outcome; no node can detect it.
Fix: Make message and payload draw from one variable: the confirmation template and the `/sign` body must interpolate the same `slot_k_start` (Recommended Contract). Prompt wording cannot fix this.
Priority: P0
Confidence: high

### Finding: No fail-closed guard between n_offer and n_verify on empty capture
Evidence: The only route into `n_verify` is the semantic edge `edge-n_offer-n_verify-chooses-a-specific-time`. There is no condition `chosen_start == ""` (or `chosen_end`, `chosen_doctor`) diverting an incomplete capture before the webhook fires, unlike `n_identity`, which guards `recall_cell == ""` etc. before calling out.
Impact: A capture slip becomes a malformed gateway call and a terminal `e_safe_failure` instead of a harmless re-ask.
Fix: Superseded by the recommended contract (no copied fields to guard); if the current shape is kept interim, add ordered conditions `chosen_start == "" → n_reask`, `chosen_end == "" → n_reask`, `chosen_doctor == "" → n_reask` ahead of the verify call.
Priority: P1
Confidence: high

### Finding: Fixed-index pinning in n_search_pm and n_search_late selects arbitrary slots and becomes bookable under any positional contract
Evidence: `n_search_pm` extracts `slots[8]`/`slots[9]`, `n_search_late` extracts `slots[16]`/`slots[15]`, as `slot_1_*`/`slot_2_*`. Measured: "latest" answered 3:00 pm when the truth was 5:15 pm; the gateway ignores `after`/`before`/`time_pref`, so these indices are guesses about list shape.
Impact: Under the recommended ordinal contract these pinned slots are what gets offered and booked, so a bad pin offers a mediocre time (never a wrong-time booking — the patient still sees and confirms the exact string — but conversion suffers and "latest" stays unanswerable).
Fix: Keep the contract independent of pin choice; fix pinning separately — file for a gateway `order=desc` or per-slot id (do not assume it), and meanwhile derive pins only from `slot_count` comparisons (`slot_count >= "N"` ladders), never from hoped-for daypart positions.
Priority: P1
Confidence: high

### Finding: Ambiguous /sign outcome at n_book is reported as "nothing booked"
Evidence: `n_book` pathways are ordered `book_error == "slot_conflict"`, `book_http_status == "200"`, `== "201"`, then `book_http_status != "200" → e_booking_failed`. A timeout or empty status matches the final inequality, and `e_booking_failed` tells the patient no appointment was booked even though the write may have landed (`retryAttempts: 0` means no confirmation of either outcome).
Impact: Possible silent double-booking if the patient re-engages, or a booked patient told they are not booked.
Fix: Route empty/unknown `book_http_status` to a distinct "outcome unknown, office will confirm" ending rather than asserting no booking exists.
Priority: P2
Confidence: medium

## Clean

- `n_book` is reachable only via `n_verify` on `overlap_id == ""`, so the conflict check is structurally impossible to skip before a write, as required.
- `n_verify` checks `conflict_reason != ""` before `overlap_id`, correctly handling the gateway's "outside schedule template with empty overlap" behaviour.
- Only `n_confirm` states a booking exists, and it is reachable only from `n_book` success statuses.
- `n_identity` fails closed on empty inputs and non-unique matches before any patient-facing turn.

## Assumptions

- Routing conditions are evaluated in listed order with first match winning (observed in `n_identity` and `n_book`; the design below depends on ordered fallbacks).
- Condition edges on extracted variables are available after Default (model) nodes, not only on webhooks. If they are not, the same guarantee holds using two semantic edges ("picks the first offered time" / "picks the second") in place of the `chosen_slot` conditions, because the confirmation gate — not the routing — is what prevents a wrong-time booking.
- `slot_k_*` variables are frozen at extraction time, so the confirmed string cannot drift between offer and book; staleness (someone else takes the slot) is covered by `/conflict-check`.
- No gateway change is assumed: no slot token exists in `/availability` responses and `/sign` accepts only `doctor`/`start`/`end`/`type`, so any token scheme is unavailable today.

## Recommended Contract

**Options costed.** For each: what the model produces / on nothing / on wrong / wrong-time booking possible? / test.

1. **Copy all fields (current).** Produces three verbatim strings. Nothing → null payload → gateway 400 → `e_safe_failure` (live). Wrong → if fields mix slots, usually `conflict_reason` catches it; if all three describe a different real slot, it books. **Wrong-time possible: yes** (Finding 2). Testable only statistically (rerun phrasings); measured 2-in-6 failure. Rejected.
2. **Single ordinal.** Produces one word, `1` or `2`. Nothing → matches no equality → re-ask; gateway never called. Wrong ordinal → books the *other displayed* slot — still a time shown in the message, but possibly not the one meant. **Wrong-time possible: yes, within the offered pair**, unless a confirmation gate is added. Testable deterministically. Adopted, with gate.
3. **Gateway-minted opaque token.** Ideal (one meaningless string, gateway resolves it, garbage fails closed server-side), but the measured `/availability` response carries no token and `/sign` accepts none. Building on it would invent a gateway field. Rejected today; file as the long-term ask alongside the `after`/`before` defect.
4. **Carry nothing; purely positional offer via semantic edges.** Produces nothing; the intent classifier picks the edge. Nothing/unclear → no edge → re-ask. Wrong edge → other displayed slot booked. Same residual as option 2, with a less inspectable failure (no variable to log). Equivalent safety only with the same confirmation gate; option 2 is preferred for auditability.
5. **Ordinal + verbatim confirmation gate (recommended).** Option 2 plus a fixed-template confirmation whose displayed time is the same variable the `/sign` body uses. Wrong ordinal is surfaced to the patient before any write and dies on "no".

**The contract.** The model produces, across the whole booking path, exactly three closed-vocabulary words, one per turn:

- At `n_offer` (rebuilt): `chosen_slot` ∈ {`1`, `2`, `none`}. The patient-facing offer of bookable times is a fixed template interpolating `{{slot_1_start}}` and `{{slot_2_start}}` (interpolation is verbatim; the model cannot reformat it). The prompt may still use `{{all_starts}}` to *answer questions*, but may never present a time as bookable unless it is one of the two pinned slots; a pick outside them is `none`.
- At two new confirmation nodes, CONFIRM-1 / CONFIRM-2 (proposed ids, not yet in the graph): `confirm_ans` ∈ {`yes`, `no`}. Fixed template: "To confirm: your eye exam would be {{slot_1_start}} at Mott Optical MK2. Reply YES to book it, or NO for other times." (`slot_2_start` in the CONFIRM-2 twin.)
- `chosen_start`, `chosen_end`, `chosen_doctor` are deleted. No model-written value appears in any webhook body.

**Graph.** `n_verify` and `n_book` are duplicated per ordinal as new nodes VERIFY-1/BOOK-1 and VERIFY-2/BOOK-2. VERIFY-1 body: `{"store":"{{store}}","doctor":"{{slot_1_doctor}}","start":"{{slot_1_start}}","end":"{{slot_1_end}}"}`; BOOK-1 params likewise from `slot_1_*`; the -2 twins use `slot_2_*`. All four bodies contain only webhook-extracted variables, satisfying "traceable to a gateway response" by construction. Existing `n_verify` pathway logic (`ok != "true" → e_safe_failure`; `conflict_reason != "" → n_reask`; `overlap_id != "" → n_negotiate`; `overlap_id == ""` → that twin's BOOK node) is kept in each twin.

**Routing conditions (equality/inequality against string literals only, evaluated in order).**

From `n_offer`:
1. `chosen_slot == "1"` → CONFIRM-1
2. `chosen_slot == "2"` → CONFIRM-2
3. `chosen_slot == "none"` → `n_negotiate`
4. `chosen_slot != "1"` → `n_reask`  (ordered last: catches empty and garbage; fails closed)

From CONFIRM-1 (mirrored for CONFIRM-2):
1. `slot_1_start == ""` → `n_reask`  (belt-and-braces: never confirm a hole)
2. `confirm_ans == "yes"` → VERIFY-1
3. `confirm_ans != "yes"` → `n_negotiate`  (a "no", empty, or anything else re-opens negotiation; fails closed)

**Behaviour under failure.** Model produces nothing: condition 4 / condition 3 fire; no webhook is called; the patient is re-asked. Model produces something wrong (`3`, a time string, mixed text): same fallbacks; nothing reaches the gateway. Model swaps `1`↔`2`: the confirmation template prints the slot that would actually be booked; the patient sees the wrong time *before* any write and replies no. A booking for a time the patient did not choose therefore requires the patient to read the exact time string and affirm it — the failure class is closed structurally, and the prompt is reduced to a usability aid, not a guarantee.

**Cost.** One extra SMS round-trip per booking, four nodes instead of two on the verify/book path, and bookable offers limited to the pinned pair per search round (mitigated by `n_negotiate` re-search loops; pin quality is Finding 4, orthogonal to this contract).

## Proof

Property test, runnable against the graph engine with a mock gateway; no live API.

Setup: mock `/availability` returns a fixed slot list S; mock `/conflict-check` returns clear; mock `/sign` records every request body. Replace the model with an adversarial stub that, at `n_offer` and the CONFIRM nodes, emits each value from: `""`, `"1"`, `"2"`, `"3"`, `"none"`, `"yes"`, `"no"`, `"07/28/2026 05:15 pm"`, a 1k junk string, and `"null"` — exhaustively over both turns (100 driver runs), while the simulated patient transcript is logged.

Invariant asserted after every run, over every recorded `/sign` body B:
1. `B.params.start ∈ {S[0].start, S[1].start}` and `(B.params.start, B.params.end, B.params.doctor)` equals the corresponding full tuple from S — nothing model-authored, no nulls, ever.
2. The transcript contains, strictly before the `/sign` call and after the last patient message, an agent message containing the exact string `B.params.start`, and the patient's next message extracted to `confirm_ans == "yes"`.
3. Runs where the stub emitted anything outside {`1`,`2`} at `n_offer` or `yes` at a CONFIRM node produced zero `/sign` calls.

Regression case for the worst failure: patient dialogue selects the first offered time; stub deliberately emits `chosen_slot = "2"`. Assert the confirmation message contains `S[1].start` (the wrong time is displayed, not hidden), patient stub replies "no", and `/sign` is never called. A second variant has the patient affirm — assert the booked time equals the displayed time, i.e. even a mis-swap can only ever book a time the patient explicitly saw and confirmed.

If all assertions hold across the exhaustive stub matrix, no sequence of model outputs can produce a booking whose time was not verbatim-displayed and affirmed by the patient.
