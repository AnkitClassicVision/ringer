# MK2 Optical closing-number and come-back job — source context

## What this system is

`v61_graph.json` is the LIVE Bland AI **SMS pathway** for the Mott Optical patient-recall
campaign. Real patients receive a text inviting them to book a comprehensive eye exam at the
MK2 office. The bot converses over SMS, searches real openings through the practice gateway,
books one appointment, and ends. It is deployed to Bland; every prompt string in the graph is
read by a live patient on their phone.

- 41 nodes, 111 edges. `Default` nodes speak; `Webhook` nodes silently call the gateway
  (`https://mott-booking-gw.mail.mybcat.com`); `End Call` nodes send one final text and close
  the conversation.
- Outbound sends use Bland `/v1/sms/send` with `new_conversation: true`, `start_node_id`, and
  `request_data` carrying `campaign`, `store`, `recall_patient_id`, `recall_cell`.
- The identity webhook `n_identity` (`isStart: true`) POSTs to `/patient-search` and maps ONLY
  these response fields: `ok`, `count`, `patient_first`, `patient_id`, `exam_type_id`.
  There is NO appointment-status field in that response today. The gateway is OUR code and can
  be extended if the design needs it.
- `build_v61.py` generates the graph. `scenarios.py` is the 30-scenario conversation suite.
  `check_candidate_gate.py` is the deterministic gate every candidate graph must pass.
  `redproof_run.py` mutates the graph to prove the gate actually catches rule removals.

## The requested change (Ankit, 2026-07-31)

1. After the appointment is made, the closing message the patient receives must end with,
   verbatim: "You're all set. If you have further questions, please call MK2 Optical at
   (212) 219-2219"
2. If, AFTER booking, the patient asks for anything else — in the same thread or by texting
   back later into a finished thread — the reply is, verbatim: "For that you'll have to
   contact the MK2 Optical office at (212) 219-2219"

## Locked decisions (do not relitigate)

- **Phone number**: (212) 219-2219 replaces (855) 750-6688 EVERYWHERE. Eleven v61 nodes carry
  the old number: `n_confirm`, `n_office`, `n_faq`, `e_safe_identity`, `e_safe_failure`,
  `e_booking_failed`, `e_office`, `e_declined`, `e_stop`, `e_not_me`, `e_existing`.
- **Deferral scope**: post-booking only. BEFORE booking, the answer-the-detour-then-steer-back
  loops in `n_office` and `n_faq` stay exactly as engineered (with the new number); they are
  what converts. AFTER the booking succeeds, any further request gets the deferral line.
- The two quoted lines above are mandated copy. English versions are verbatim; the pathway's
  bilingual rule (reply in the patient's language) still applies, so a Chinese-language
  equivalent carrying the same number is expected where the language rules require it.

## Known open questions the design must address

- **Brand naming**: 26 nodes introduce the bot as "Mott Optical" (booking "at the MK2
  office"); the mandated lines say "MK2 Optical". Flag every inconsistency your proposed copy
  creates and recommend one naming, but treat final brand wording as Ankit's call.
- **Come-back mechanics are UNMEASURED.** What Bland does with an inbound patient text after
  an `End Call` node has fired is not known here: it may re-enter the pathway at the
  `isStart` node, may continue dead, may open a new conversation. Do not assume. Your design
  must name the empirical probe(s) that settle it before any mechanism is trusted, and must
  work (or fail safe) under each plausible behavior.
- **Post-booked detection**: if a come-back re-enters at `n_identity`, nothing in the current
  `/patient-search` response says "this patient already booked through this campaign." A
  gateway extension is possible but is a second deployment surface; weigh it against
  Bland-side alternatives.

## Invariants that must survive (from 13 prior hardening rounds)

- NO_CLAIM: only the confirmation step, after the booking webhook reports success, may say an
  appointment is booked/confirmed/held.
- Never re-enter search/verify/book after a successful booking (double-booking guard).
- Language switching per the patient's most recent message; Chinese invite line on opener only.
- NO_LEAK: no internal field names, ids, or captured values in patient-visible text.
- NO_PRICE: no "free", no discounts, no dollar amounts, no coverage claims.
- STOP/wrong-person suppression paths must keep working unchanged.
