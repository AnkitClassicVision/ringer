# v62 Design Review — Routing & State: closing number swap, post-booking deferral, come-back path

Scope: v61 graph (41 nodes, 111 edges), build_v61.py, scenarios.py, check_candidate_gate.py, redproof_run.py. Emphasis: edges and state. Note: `check_suppression_delta.py` is imported by redproof_run.py but is **not present in ./source**; suppression-delta behavior is reviewed only through its call signature. Bland's post-End-Call inbound behavior is **unknown** from this material — every claim about it below is labeled.

---

## 1. CHANGE LIST

### The eleven nodes carrying (855) 750-6688 → (212) 219-2219

**n_confirm** (Default, "Booked"). Current TASK: *"If the patient then asks to change, cancel or move it, give them the office number (855) 750-6688 and explain the office will take care of it."*
Proposed: (a) confirmation message must END verbatim: **"You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219"**; (b) the change/cancel/move clause is replaced by: reply verbatim **"For that you'll have to contact the MK2 Optical office at (212) 219-2219"** and take the new e_defer path (never n_office — see routing below). Side effects: "You're all set" matches the gate's invariant-5 claim regex (`you(?:'re| are)\s+(?:booked|scheduled|confirmed|all set)`), so this line may live **only** in n_confirm — the one node the regex exempts. n_confirm carries LANG_REPLY, so a fixed Chinese form of the close must be written into the prompt (new copy; Ankit signoff needed; number stays verbatim). NO_LEAK unaffected. The NEVER clause "Never go back to searching, verifying or booking after this point" stays untouched.

**n_office** (Default, global, autoReturn). Current TASK: *"Give the office number (855) 750-6688 for what they asked about."* Proposed: number swap only; steer-back loop (BACK rule) and globalLabel kept, but globalLabel gains "Does not apply once a booking is confirmed" (mirroring n_negotiate's existing label wording) so it cannot fire post-booking and steer a booked patient toward "the openings still on offer" — an invitation to a second appointment.

**n_faq** (Default, global, autoReturn). Current TASK: *"If they say they want to speak to someone, give them the office number (855) 750-6688."* Same treatment as n_office: number swap, keep pre-booking defer-then-steer behavior, scope the globalLabel to pre-booking.

**e_safe_identity**. Current: *"I couldn't safely continue this scheduling request. Please call Mott Optical at (855) 750-6688."* Proposed: number swap only. Note: this node fires on come-back re-entry if request_data is empty (§2) — it becomes the de-facto fail-safe reply, so the correct number here matters beyond cosmetics.

**e_safe_failure**. Current: *"I couldn't access scheduling right now and no appointment was booked. Please call Mott Optical at (855) 750-6688."* Number swap only.

**e_booking_failed**. Current: *"I couldn't confirm that booking. Please call Mott Optical at (855) 750-6688 so they can check it for you."* Number swap only.

**e_office**. Current: *"Please call Mott Optical at (855) 750-6688."* Number swap only. Stays the pre-booking office-handoff exit; it is NOT the post-booking deferral exit (mandated wording differs).

**e_declined** (global End Call). Current: *"Ok, thank you for letting us know. If you need anything, call the office at (855) 750-6688."* Number swap only.

**e_stop**. Current: *"Understood. If you would like to be taken off our list, please call Mott Optical at (855) 750-6688 and the office can take care of it."* Number swap only. Must NOT gain "you're all set" — the scenario suite rejects that string at e_stop, and it would violate NO_CLAIM.

**e_not_me**. Current: *"Sorry about that. If you would like to be taken off our list, please call Mott Optical at (855) 750-6688 and the office can take care of it."* Number swap only.

**e_existing** (global End Call). Current: *"Please call Mott Optical at (855) 750-6688 and the office can help with that appointment."* Number swap only. Collision risk: post-booking "cancel/move my appointment" matches e_existing's globalLabel ("already has a different appointment they want to cancel or move") as readily as the deferral path. Which global wins is Bland-precedence-dependent — **unknown**; probe needed. Mitigation: tighten e_existing's label to "an appointment made OUTSIDE this conversation."

### Routing and structural changes

**e_booked** (End Call). Current text: *"Thank you. We look forward to seeing you."* Unchanged. It must NOT carry the mandated close: invariant 5 forbids both the claim regex and `\bbook(ed|ing)?\b` in e_booked.text, and "You're all set" trips the claim regex. The mandated close therefore lives in n_confirm's message, which fires before e_booked. Honest gap: whether the patient perceives n_confirm's text or e_booked's text as "the closing message" depends on Bland's node-send sequencing — both send. If Ankit reads "closing message" as the last text, e_booked's line should be dropped or folded into n_confirm and e_booked left as the silent terminator (whether an End Call may send empty text is **unknown** from this material).

**New node e_defer** (End Call), text verbatim: *"For that you'll have to contact the MK2 Optical office at (212) 219-2219"*, outcome `deferred_after_booking` (add to analysis_options outcome enum). The line contains no booking claim, so it is invariant-5-safe in an End Call node. Add a Chinese form to wherever the line is delivered by a Default node.

**n_confirm edges**: today `n_confirm → e_booked` ("confirmation delivered"), `n_confirm → n_office` ("change requested after confirmation"), `n_confirm → e_booked` ("72-hour silence after booking"). v62: retarget "change requested after confirmation" from **n_office → e_defer**; add a second edge `n_confirm → e_defer` ("anything else requested after booking"). Result: adjacency(n_confirm) ⊆ {e_booked, e_defer} — no path from any post-booking state to n_search/n_verify/n_book. This makes the never-rebook guard **structural**, not prompt-only.

**n_identity** (isStart Webhook): add `responseData` entry `booked_already ← $.result.campaign_booked` (gateway extension, §2) and a responsePathway `["booked_already","==","true", {e_defer}]` **ordered before** `["count","==","1", n_ask]`, plus the matching edge. Placement mirrors the n_search outside-hours precedence pattern already enforced by invariant 3.

---

## 2. COME-BACK DESIGN

### What is known vs unknown

Known from the material: outbound sends use `/v1/sms/send` with `new_conversation: true`, `start_node_id`, `request_data`; n_identity is `isStart`; End Call nodes "send one final text and close the conversation"; `/patient-search` maps only `ok, count, patient_first, patient_id, exam_type_id` — **no appointment-status field**. Unknown: what Bland does with an inbound text after End Call. Three plausible behaviors, walked:

**Behavior A — dead thread.** Nothing fires; no `/patient-search` POST reaches the gateway. Patient gets silence. No re-offer, no double-booking, no STOP violation — but the mandated deferral is never delivered. No Bland-only mechanism can fix this; a fix would live in the gateway/carrier layer, outside the pathway.

**Behavior B — re-entry at n_identity.** n_identity fires. Its first three pathways route empty `recall_cell` / `recall_patient_id` / `store` to e_safe_identity; whether request_data survives an inbound re-entry is **unknown**. Sub-case B1 (vars empty): patient gets "I couldn't safely continue this scheduling request. Please call … (212) 219-2219" — not the mandated line, but fails safe: correct number, no re-offer, no booking. Sub-case B2 (vars present, count==1): **the worst path in this review** — n_ask fires the full opener ("This is the very first message this patient receives… When would you like to come in?"), the booked patient names a day, and the spine search→offer→gate→verify→book runs to a **second appointment**. n_confirm's prompt-level never-rebook NEVER clause never engages because this traversal hasn't booked yet *in this run*. e_existing's global might catch "I already have an appointment" phrasing, but "can I come Friday instead" matches nothing protective. This is exactly the failure the gateway extension closes: `campaign_booked == true` routes to e_defer **before** count==1 is evaluated.

**Behavior C — brand-new conversation.** Indistinguishable from B at n_identity: same webhook, same variable-presence question. If request_data is not re-supplied, B1's e_safe_failure path applies. If Bland starts at n_identity with the number only, count can still resolve by phone (identity resolves by PHONE with id as filter — build_v61.py comment), so the booked-flag route is again the only protection against re-offer.

### Probes (must run before trusting any mechanism)

1. **Staging come-back probe**: run a test number to e_booked, then text it inbound. Instrument at the gateway: does a `/patient-search` POST arrive (distinguishes A from B/C), and with what body (distinguishes B1 from B2)?
2. **Post-e_stop / post-e_declined probe**: same, after suppression and decline exits, to learn whether re-entry also re-fires global triggers.
3. **Global-precedence probe**: post-booking "STOP" and "cancel my appointment" in a live thread — does n_suppress_stop beat e_defer, and does e_existing beat e_defer? Global match precedence is **unknown** from the material.

### Gateway extension vs Bland-only

Bland-only alternatives fail on state: pathway variables don't carry "this patient booked" into a re-entry run (request_data is per-send; nothing in the material shows persistence), and under Behavior A no Bland node fires at all. The gateway already knows the booking happened (it signed it). Extending `/patient-search` with `$.result.campaign_booked` is one field, one responseData row, one pathway — and it also serves a suppressed-flag variant later. Cost: a second deployment surface, and ordering matters — **gateway first, graph second**, because a v62 graph routing on a flag the old gateway never emits leaves `booked_already` empty, which matches no route and falls through to count==1 (status quo, not a regression). **Recommend the gateway extension.** Residual uncovered case: Behavior A silence, accepted and documented unless Ankit funds a gateway-level auto-reply.

### STOP/wrong-person on come-back

Under Behavior A, a suppressed patient is safe (silence). Under B2 without a suppression flag, a STOPped patient texting "hi" re-enters at n_ask and is re-messaged — the in-pathway suppression webhooks only fire on STOP/wrong-person *content*. Whether the campaign send layer consults `/sms-suppression` records before any send is **outside this material — unknown**. Minimum v62 mitigation: none available in-graph; flag for the gateway follow-up (`sms_suppressed` on `/patient-search`, routed to a no-op end — noting every End Call still sends one text, so even that is harm-reduction, not silence).

---

## 3. SCENARIO ADDITIONS

- **'post-booking change request defers'** — book through to n_confirm, then "actually can I move it to next Friday?" → expect_node e_defer (or n_confirm emitting the deferral line), expect_text `For that you'll have to contact the MK2 Optical office at \(212\) 219-2219`, reject_text `\d{2}/\d{2}/\d{4}|slot|Reply 1 or 2`. Proves no re-offer, no n_office steer-back.
- **'post-booking extra ask same thread'** — after confirmation, "are my glasses ready yet?" → same deferral expectation; reject_text `get you scheduled|openings|still on offer` (the BACK steer-back). This is the n_office-global leakage case.
- **'post-booking insurance question does not steer back'** — after confirmation, "does my insurance cover the lenses?" → deferral; proves n_faq's label scoping.
- **'text back after close'** — End Call, then inbound "can I change my appointment?" → expect e_defer text, **or documented no-send if probe 1 shows Behavior A**. Expected to fail until the probe lands; a failing case is a finding.
- **'booked patient re-entry is not re-offered'** — harness simulates re-entry at n_identity with gateway returning `campaign_booked: true` → expect e_defer, reject_text `when would you like to come in|Reply 1 or 2`.
- **'unbooked patient re-entry still books'** — same re-entry, `campaign_booked: false` → n_ask opener fires normally (guards the flag's false path).
- **'pre-booking detour keeps new number and steer-back'** — existing 'asks about an order' case, updated: expect_text `212`, reject_text `855`; steer-back behavior unchanged.
- **'Chinese post-booking ask gets Chinese deferral'** — book, then a Chinese extra ask → expect_text `[一-鿿]` AND `212`; proves the fixed Chinese form, not an ad-hoc translation.
- **'STOP after booking still suppresses'** — book, then "STOP" → expect_node e_stop; proves suppression global still wins over deferral (probe 3 dependent).

## 4. GATE AND REDPROOF ADDITIONS

New deterministic rules in check_candidate_gate.py:

- **G1 (number zero/total)**: zero occurrences of `855` in the serialized graph; the literal `(212) 219-2219` present in exactly the mandated carrier set {n_confirm, n_office, n_faq, e_safe_identity, e_safe_failure, e_booking_failed, e_office, e_declined, e_stop, e_not_me, e_existing, e_defer}.
- **G2 (mandated close verbatim, monopoly)**: the exact close string appears in n_confirm.prompt and in **no other node** (extends the invariant-5 monopoly; "You're all set" already trips the claim regex elsewhere).
- **G3 (deferral verbatim)**: e_defer exists, is an End Call, has no outgoing edges, and its text equals the mandated deferral line exactly.
- **G4 (post-booking topology)**: adjacency(n_confirm) ⊆ {e_booked, e_defer}; no path from n_confirm or e_defer to {n_search, n_verify_1, n_verify_2, n_book_1, n_book_2, n_office, n_faq, any offer node}. This upgrades the never-rebook guard from prompt text to structure.
- **G5 (identity precedence)**: n_identity responsePathways contain exactly one `booked_already == true → e_defer` route, ordered before the `count == 1 → n_ask` route (same precedence style as the invariant-3 outside-hours check).
- **G6 (label scoping)**: n_office and n_faq globalLabels contain "once a booking is confirmed" exclusion wording.

Redproof mutations (each must make the gate fail):

- M1: restore `(855) 750-6688` in any one node → caught by G1.
- M2: delete the close line from n_confirm → caught by G2.
- M3: move the close line into e_booked.text → caught by G2 (and existing invariant 5 — the `second_booking_claim` mutation is the template).
- M4: paraphrase e_defer's text ("you will have to contact…") → caught by G3 verbatim check.
- M5: re-add edge n_confirm → n_office (or n_confirm → n_search) → caught by G4.
- M6: delete the booked_already pathway, or reorder it after count==1 → caught by G5.
- M7: strip the post-booking exclusion from n_faq's globalLabel → caught by G6.

## 5. REGRESSION RISKS

- **NO_CLAIM**: the mandated close contains "You're all set", which the invariant-5 regex treats as a booking claim. Any placement outside n_confirm (e_booked, a new Default node, an over-helpful edit to e_stop) fails the gate or, worse, passes a weakened gate. G2 exists precisely to refuse the "put it in the End Call so it's the last text" temptation.
- **Never-rebook-after-success**: v61's guard is prompt text inside n_confirm plus the absence of book edges from n_confirm. v62 must not reintroduce n_confirm → n_office (whose BACK rule solicits another booking) — G4 makes it structural. The residual rebook path is come-back re-entry at n_identity (Behavior B2), closed only by the gateway flag; shipping the graph before the gateway deploys leaves that path open (fails to status quo, not safe).
- **Bilingual switching**: LANG_REPLY instructs replying in the patient's most recent language, which invites ad-hoc translation of the verbatim lines. Fixed Chinese forms must be written into n_confirm's prompt (and the deferral delivery); the gate cannot verify Chinese verbatim — the Chinese scenario is the only check. A post-booking bare "ok" carries no language signal; existing rule keeps the prior language.
- **STOP/wrong-person suppression**: suppression globals are content-triggered; a deferral global or loose e_defer label must never outrank n_suppress_stop/n_suppress_not_me (precedence **unknown**, probe 3). Come-back re-entry of an already-suppressed patient re-messages them at least once under Behavior B2 — flagged as a gateway follow-up; in-graph there is no silent-end primitive.
- **n_office/n_faq autoReturn**: with enableGlobalAutoReturn, firing post-booking returns to the interrupted node (n_confirm) after speaking the steer-back — the damage is in the spoken line, so label scoping (G6) is the fix, not edge surgery.
- **e_existing collision**: post-booking cancel/move phrasing matches e_existing's globalLabel; its text (new number, different wording) is close to but not the mandated line. Label tightening recommended; precedence probe required.

### Brand inconsistency — Ankit's call

26 nodes introduce the bot as "Mott Optical" (opener, WORLD background in every Default prompt, all eleven number-carrying nodes); offers and gates say "at MK2" / "at the MK2 office"; the two mandated lines say "MK2 Optical". v62 as specified makes one phone number answer to two brand names in the same thread ("Please call Mott Optical at (212) 219-2219" from e_stop vs "contact the MK2 Optical office at (212) 219-2219" from e_defer). The mandated lines are fixed, so zero-inconsistency is impossible. **Recommendation: standardize all non-mandated patient-facing copy on "Mott Optical"** (it already is; changing 26 tuned prompts is the larger risk surface) and treat "MK2 Optical" as the mandated office-contact name — but the final naming is Ankit's call, and if he wants full MK2 rebranding it should be a separate, gated pass, not folded into v62.
