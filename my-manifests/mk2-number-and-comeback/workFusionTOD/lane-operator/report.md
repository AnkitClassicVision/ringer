# Operator ship decision: Mott SMS recall line, 2026-08-04

CANARY: blue paperclip

## Decision

**Recommend A for today's 11:00 ET opening: leave v94 unchanged, operate it as a monitored one-day exception, and prepare B after the 17:30 ET business-hours gate for the next owner-approved flip.**

This is not an endorsement of the defect. It is the least-bad option available at the decision point. The latest live evidence was recorded at 10:52 ET, eight minutes before opening. Option B still requires about one hour of machine work, including a deliberate validator-assertion amendment, mint, and ladder. The standing gate prohibits sustained harness load Tuesday through Friday from 10:30 to 17:30 ET. C introduces new routing/capability paths without a safe proof window. D removes a recall service whose other proven paths are green for an exposure that is real but has no measured production incidence.

## Operator frame

- **Owner:** Ankit owns the pathway flip, rollback, and any exception to the business-hours harness gate. The operating owner on the Mott side must watch the line and handle escalated office referrals during the opening window.
- **Outcome:** Open the line on v94 at 11:00 ET while containing the known defect to time-of-day/reference-point asks. Preserve the proven date, ambiguity, no-availability, booked-customer, and baseline-regression behavior. Do not attempt a structural repair today.
- **Date/checkpoints:** 11:00 ET launch decision; review the first 20 patient conversations or at 13:00 ET, whichever comes first; review again at 17:30 ET. After 17:30 ET, run B's assertion amendment, mint, and ladder. Ankit alone decides whether and when to flip the unattached mint.
- **Risk:** A patient asking only for a relative time such as “last time of the day” may receive a promise to check followed by silence. A nudge can repeat the same promise. The same node has also produced a filler followed immediately by an office referral, so the failure presentation is nondeterministic.
- **Visibility:** Tag and count conversations containing `last`, `latest`, `first`, `earliest`, `morning`, `afternoon`, `evening`, `before`, `after`, or equivalent time-only language. Separately count (1) filler then answer, (2) filler then office referral, and (3) filler with no substantive answer within two minutes. Record total eligible recall conversations so the failure rate has a denominator. Do not expose patient content in the operator log.

## Morning risk estimate

The fraction of real day-one recall conversations containing a **time-of-day-only ask is unknown**. The supplied evidence consists of two deliberate owner tests, both aimed at this behavior, so 2/2 is a defect reproduction rate, not an incidence estimate. There is no production conversation distribution or historical denominator in the evidence.

For staffing and escalation only, use a provisional **0% to 10% bound**, with **1% to 5% as the planning range**. Recall recipients commonly accept an offered slot, request another date, decline, or do not respond; a relative reference-point request is a narrower branch that occurs after engagement and often after a date has been established. That reasoning supports low-single-digit plausibility, but it is inference, not measured fact. At 20 eligible conversations, even one occurrence means an observed 5%; small samples must not be presented as a stable rate.

## Patient experience and trust cost

- **Worst observed presentation:** “One moment while I check the schedule for you,” then no answer for more than two minutes; after “Hello?” the same promise repeats. This creates an explicit expectation of imminent service and then breaks it. The likely trust cost is higher than honest silence because the system claims it is acting, consumes patient attention, and makes the patient unsure whether the request or booking is still active.
- **Alternate observed presentation:** “Let me check that for you,” followed by an immediate call-the-office referral. This is inconvenient and abandons SMS completion, but it is bounded, truthful about the next action, and materially safer for trust than promise-then-silence.
- **Business effect:** likely lost conversion for the affected conversation, duplicate patient effort, and avoidable skepticism about later automated messages. No evidence supports quantifying revenue loss or patient incidence today.

## Options and rollback

| Option | Today assessment | Rollback / containment |
|---|---|---|
| **A: v94 unchanged** | **Ship with monitoring.** Preserves the broad proven baseline but knowingly exposes a narrow nondeterministic trust failure. | Ankit flips back to v92 if v94 shows any broader regression. For this specific defect, v92 is not shown to be a cure; operational containment is office follow-up/referral and after-hours B. Taking the line offline remains the immediate containment if the threshold below is crossed and no proven patch is ready. |
| **B: strip fillers** | Preferred near-term containment, but not responsibly provable before opening: the live diagnostic ended at 10:52 ET, work is about one hour, and sustained harness load is barred after 10:30 ET. It removes the deceptive promise but does not add capability. Earlier A/B work showed routing/offer parity; the production artifact still needs the named assertion amendment, mint, and ladder. | Mint unattached; Ankit flips. If post-flip ladder or handset behavior differs from expected parity, flip immediately back to v94. Keep the prior mint/version identifier in the flip packet. |
| **C: routing/capability patches** | Do not ship today. New paths, hours of work, nondeterministic node behavior, and no safe business-hours regression window create greater blast radius than the narrow known defect. | Only an unattached mint plus owner flip would be acceptable. Roll back by flipping to v94. If gateway code were touched, use its recorded prior task definition, but no gateway change is authorized or recommended here. |
| **D: offline all day** | Disproportionate as the starting choice because all other named paths are green and incidence is unmeasured. Use as emergency containment, not the default. | Restore the last approved line/pathway only after the owner confirms the trigger has cleared or a proven containment is live. Preserve queued patient follow-up through an owner-approved manual process; do not silently drop replies. |

## Emergency escalation criterion

Escalate to Ankit for an emergency business-hours containment decision if **any one** occurs:

1. two confirmed promise-then-silence failures in the first 20 eligible patient conversations;
2. the observed promise-then-silence rate exceeds 5% once at least 20 eligible conversations exist;
3. one affected patient expresses urgency, access/safety concern, or repeated confusion and does not receive a substantive answer or office referral within two minutes; or
4. the failure appears outside time-of-day/reference-point asks, indicating the blast radius is broader than currently bounded.

The emergency action is not an improvised C patch. The owner chooses between taking the line offline and explicitly authorizing a narrowly scoped B validation/flip exception. No patch ships without the amended validator assertion, mint, focused live proof, rollback identifier, and owner flip.

## Proof required for the after-hours B flip

1. Deliberate validator assertion amendment is reviewed and passes.
2. Strip removes both known filler variants without changing routing, offers, referrals, booking behavior, or gateway inputs.
3. Mint remains unattached until Ankit's decision.
4. Focused ladder covers both observed phrasings, a nudge after the failure, and ordinary date/slot acceptance controls.
5. Post-flip handset measurement confirms no deceptive filler and records whether the terminal behavior is honest silence or office referral.
6. Rollback to v94 is named and executable before the flip.

## Confidence and residual uncertainty

**Recommendation confidence: 0.78.** High confidence that C is unsafe today and B cannot meet the standing proof gate before 11:00 based on the timestamps. Moderate confidence that A is preferable to D because actual patient incidence is unknown and the remaining line behavior is proven green. The decision could flip toward D if early monitoring shows the defect is common, spreads beyond reference-point asks, or cannot be manually contained.
