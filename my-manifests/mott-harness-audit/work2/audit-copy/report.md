# Copy Audit

## Summary
- The offer message (`n_offer`) exposes the internal store code "MK2" directly to patients, and its prompt wrongly claims the message ends with the Chinese-service line — a copy-paste contradiction that risks that line being repeated outside the opening message.
- `n_faq` answers the insurance-coverage question with a substantive claim ("vision benefits are usually separate coverage with their own copays") instead of purely deferring to office staff, as the copy rules require.
- Appointment times (`slot_1_start`/`slot_2_start`) are passed straight from the booking API into patient messages with no visible formatting step; the prompt merely asserts they are "already formatted," which is an unverified trust assumption.

## Findings

### Finding: Internal location code "MK2" sent verbatim to patients
Evidence: Node `n_offer`, prompt TASK text: "Great news, I have {{slot_1_start}} or {{slot_2_start}} at MK2." and the Chinese form "（地点：MK2）".
Impact: A patient reading "at MK2" has no idea what that means — it reads as an internal shorthand/store code rather than an office name or address they recognize.
Fix: Replace "MK2" with the office's patient-facing name, e.g. "at our [Office Name] location," sourced the same way `patient_first` is.
Priority: P1
Confidence: high

### Finding: n_offer prompt contradicts itself about the Chinese-service line
Evidence: Node `n_offer`, prompt NEVER section: "Send the English message; it ends with the Chinese-service invitation line. That line appears on this opening message ONLY." — but the actual TASK message for `n_offer` ("Great news, I have {{slot_1_start}} or {{slot_2_start}} at MK2...") does not contain that line at all.
Impact: The instruction asserts a fact about this message that isn't true. A small model following the literal instruction "it ends with the Chinese-service invitation line" could append 如需中文服务... to the offer message, duplicating an invitation that the practice's own rule says must appear only once, on the opening text.
Fix: Delete that boilerplate sentence from `n_offer` (and confirm it isn't copy-pasted into any other non-opening node); state instead "Do not add the Chinese-service invitation line here."
Priority: P1
Confidence: high

### Finding: FAQ node answers the coverage question instead of deferring
Evidence: Node `n_faq`, prompt TASK: "If they asked whether insurance COVERS something, say that vision benefits are usually separate coverage with their own copays, and our staff will be able to help them with this."
Impact: The patient receives a substantive claim about how insurance works (separate coverage, has copays) from the bot, not a deferral to office staff. This may be wrong for their specific plan (no copay, bundled coverage, etc.), and conflicts with the practice rule that coverage questions are deferred rather than answered.
Fix: Change the instruction to something purely deferring, e.g. "Say that our office staff can look into their specific benefits and answer that," without asserting how vision benefits typically work.
Priority: P1
Confidence: high

### Finding: Raw appointment times may reach patients unformatted
Evidence: Node `n_search` webhook maps `$.result.slots[0].start` straight to `slot_1_start` with no transform node in the graph; node `n_offer` prompt instructs "Every time shown comes from the schedule already formatted... Present it exactly as given: do not convert it, do not reformat it."
Impact: If the upstream API field is a raw timestamp (e.g. `2026-07-27T11:30:00-04:00`) rather than a human phrase, the model is explicitly told not to reformat it, so the patient could receive a machine-style date/time instead of a weekday/time a person would recognize.
Fix: Either confirm and document that the `/availability` endpoint returns pre-formatted, patient-readable strings, or add an explicit format example (e.g. "Tuesday, July 27 at 11:30am") the model must produce from the raw value.
Priority: P2
Confidence: medium

### Finding: Opening message frames insurance benefits as something to use before they're lost
Evidence: Node `n_ask`, prompt TASK message: "Many vision insurance benefits renew yearly, so don't let your benefits go unused!"
Impact: This isn't a discount or price, but it is a financial-urgency nudge about insurance benefits in the very first message, which invites patients to ask coverage/cost questions the bot is required to defer rather than answer, and sits close to the spirit of the "don't discuss saving money" rule.
Fix: Drop the benefits-renewal sentence and lead with the general "great time for a check-up" framing already present in the message.
Priority: P3
Confidence: low

### Finding: Opening message is long for a single SMS
Evidence: Node `n_ask`, prompt TASK message (English + trailing Chinese invitation line) — approximately 530 characters.
Impact: At roughly 530 characters, the message will arrive as multiple concatenated SMS segments (or an MMS-length message), which some patients' phones display out of order or which reads as a wall of text on first contact.
Fix: Trim to the core points (who's texting, why, the scheduling question, STOP line) and drop secondary marketing detail (lenses/eyewear/sunglasses collection) to a follow-up if needed.
Priority: P3
Confidence: medium

## Clean
- Never use "free": no occurrence of "free" in any prompt or text field.
- No discount/package/saving-money language beyond the borderline benefits line flagged above; no dollar amounts or prices quoted anywhere.
- Cost questions in `n_faq` are handled with a pure deferral ("it depends on their benefits and someone at the office can help with that") — compliant.
- Chinese-service invitation line appears exactly once, on `n_ask` only, in the actual task text of every other Default node (it is absent from the literal TASK messages of `n_reask`, `n_negotiate`, `n_confirm`, `n_office`, `n_faq`).
- Every Default node with multi-turn dialogue instructs replying in the language of the patient's most recent message and switching both directions.
- No node states an appointment is booked/scheduled/held/confirmed except `n_confirm`, and only after a successful `n_book_1`/`n_book_2` webhook response; every other Default node explicitly forbids this and gives a "still getting you scheduled" fallback.
- `e_stop` and `e_not_me` correctly avoid promising removal from any list, instead directing the patient to call the office.
- `n_offer`'s TASK explicitly requires saying plainly that offered times are not what the patient asked for, naming the day they wanted, before offering an alternate day — compliant with the "no surprise days" rule.
- No all-caps patient names or internal record/field names appear in any literal patient-facing message text (internal identifiers like `patient_id`, `exam_type_id`, `book_http_status` only appear in Webhook node bodies/responseData, which are not sent to patients).

## Assumptions
- I could not verify what the `/availability` and `/patient-search` webhooks actually return at runtime; the "raw appointment times" finding assumes the API may return machine-formatted timestamps since no formatting step is visible in this file.
- "MK2" is assumed to be an internal store code rather than a name patients already recognize; if patients are in fact told to call this "the MK2 office" elsewhere by the practice, this finding's severity would be lower.
- SMS length assessment uses character count only; actual segment behavior depends on the carrier/gateway, which is outside this file.
