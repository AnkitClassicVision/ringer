# v62 SPEC — MK2 closing number + post-booking deferral + come-back
Synthesized 2026-07-31 from three independent design reviews (codex gpt-5.6-sol,
grok-4.5, kimi-k3), each validated by executed check against the v61 graph.
Panel verdicts converged on the architecture; divergence on close-line placement
resolved by the existing gate's invariant-5 claim regex (check_candidate_gate.py:284-307).

## Locked by Ankit (2026-07-31)
- (212) 219-2219 replaces (855) 750-6688 everywhere (11 carrier nodes).
- Deferral applies POST-BOOKING ONLY; pre-booking n_office/n_faq steer-back stays.
- Mandated copy, verbatim:
  - CLOSE: "You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219"
  - DEFER: "For that you'll have to contact the MK2 Optical office at (212) 219-2219"

## Design (3/3 panel consensus)
1. **Number swap** in all eleven carriers: n_confirm, n_office, n_faq, e_safe_identity,
   e_safe_failure, e_booking_failed, e_office, e_declined, e_stop, e_not_me, e_existing.
   Text otherwise byte-identical except where below.
2. **CLOSE placement**: ends n_confirm's confirmation message (single bubble:
   confirmation + time + mandated tail; avoid double "all set" phrasing).
   NOT in e_booked — invariant-5 regex forbids the claim there. e_booked text unchanged
   ("Thank you. We look forward to seeing you.").
3. **New End Call node `e_defer`**, text = DEFER verbatim, outcome `deferred_after_booking`
   (added to analysis_options), no outgoing edges.
4. **n_confirm rewire**: "change requested after confirmation" edge retargeted
   n_office → e_defer; add edge "anything else requested after booking" → e_defer.
   Result: adjacency(n_confirm) ⊆ {e_booked, e_defer}. Never-rebook becomes structural.
5. **Global scoping** (kimi): n_office and n_faq globalLabels gain "does not apply once a
   booking is confirmed" exclusion; e_existing label tightened to "an appointment made
   outside this conversation" (post-booking cancel/move must hit e_defer, not e_existing).
6. **Come-back (text-back into finished thread)** — REVISED by Ankit 2026-07-31:
   appointment SEARCH, not a campaign flag. /patient-search response adds
   `$.result.upcoming_appointment` (boolean: patient has a FUTURE appointment at this
   store, any booking channel). n_identity maps it to `booked_already` and routes
   `booked_already == "true" → e_defer` ORDERED BEFORE `count == 1 → n_ask`.
   Rationale: no new write-side state (gateway reads the schedule it already books
   into); covers phone/walk-in bookings; self-heals on cancellation (cancelled patient
   texting back can book again). Superseded alternative: `campaign_booked` write-side
   flag — rejected as stale-prone (keeps deferring after a cancellation) and needing
   new persistence. Guard: the send queue must continue excluding already-scheduled
   patients so the graph route stays a backstop, never a first-touch opener.
   Fail-closed: absent/malformed field falls through to status quo. DEPLOY ORDER:
   gateway first, graph second.
7. **Bilingual** — REVISED by Ankit 2026-07-31: the Chinese renderings must be
   faithful sentence-for-sentence translations of the English mandated lines — same
   statements, nothing added or strengthened. "You're all set." translates as an
   all-arranged statement (e.g. 您都安排好了。), NOT as 预约成功/"booking succeeded"
   phrasing, which claims more than the English does. "the MK2 Optical office" keeps
   the office sense, one consistent term. Digits stay ASCII; brand stays "MK2
   Optical" in Latin script. The live Chinese CLOSE sits in n_confirm.prompt; the
   Chinese DEFER remains proposed copy in the report (End Call text is single-language
   English — documented limitation).

## Gate additions (G1-G6) + redproof (M1-M7)
- G1 zero `855` anywhere; `(212) 219-2219` present in exactly the carrier set + e_defer.
- G2 CLOSE verbatim in n_confirm.prompt and NO other node.
- G3 e_defer exists, End Call, no outgoing edges, text == DEFER exactly.
- G4 adjacency(n_confirm) ⊆ {e_booked, e_defer}; no path from n_confirm/e_defer to
  search/verify/book/offer/n_office/n_faq.
- G5 n_identity booked_already route present, ordered before count==1.
- G6 n_office/n_faq labels carry the post-booking exclusion.
- Redproof mutations M1-M7 per kimi report §4 (restore 855; delete close; move close to
  e_booked; paraphrase e_defer; re-add n_confirm→n_office; delete/reorder booked route;
  strip label exclusion). Each must fail the gate; clean candidate passes; gate still
  fails v61 and any prior graph.

## Scenario additions (union of panel lists, ~12 new + 2 updated)
post-booking change defers · post-booking extra ask (glasses) · post-booking insurance
no-steer-back · text-back after close (probe-dependent) · booked re-entry not re-offered ·
unbooked re-entry still books · pre-booking detour keeps 212 + steer-back · no `855`
anywhere in any thread · STOP after booking still suppresses · wrong-person unchanged ·
Chinese post-booking deferral · never-rebook edge case ("book tuesday instead" after
confirm) · update 2 existing cases expecting `855`.

## Live probes (GATE — real SMS; Ankit approves at moment of action)
P1 post-End-Call inbound: does /patient-search fire, with what request_data body?
P2 re-entry after e_stop / e_declined.
P3 global precedence post-booking: STOP vs e_defer vs e_existing.
P4 booked-flag flip after /sign success.

## Brand naming — DECIDED by Ankit 2026-07-31
**"MK2 Optical" in ALL patient-facing copy.** Rationale (Ankit): the pathway is
per-store; future stores get their own pathways (MK1, MK3, ...), so this pathway's
patient-facing brand is the store name. Every "Mott Optical" in prompt/text fields
becomes "MK2 Optical". Internal identifiers unchanged: gateway URL
(mott-booking-gw.mail.mybcat.com), secret names, request_data fields, node ids.
The Chinese invite line and "at the MK2 office" location phrasing may simplify to
match the single brand, but must not introduce a third name variant.

## Residual accepted risks (documented, not hidden)
- Bland Behavior A (dead thread after End Call): deferral undeliverable in-pathway;
  close line already gave the number. Gateway-level auto-reply is a separate decision.
- Suppressed patient re-entry under Behavior B2 pre-gateway-flag: fails to status quo.
- check_suppression_delta.py absent from review source; suppression delta reviewed by
  call signature only (kimi note).
